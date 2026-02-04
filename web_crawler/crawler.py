"""
WebCrawler - Async web crawler with optional proxy rotation.
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import random
import time
from typing import Any, Callable, Iterable, Optional

import aiohttp
from bs4 import BeautifulSoup
from tqdm import tqdm

from .http_client import SocksSessionPool, build_headers, is_socks_proxy
from .proxy_manager import ProxyManager
from .storage import AggregatedStorage, StorageBackend

logger = logging.getLogger(__name__)


class WebCrawler:
    """
    Async web crawler with:
    - configurable concurrency
    - retry with exponential backoff (+ jitter)
    - optional proxy rotation (HTTP + SOCKS)
    - pluggable storage backends
    """

    def __init__(
        self,
        urls: list[str],
        parser: Optional[Callable[[str, str], Any]] = None,
        storage: Optional[StorageBackend] = None,
        max_workers: int = 8,
        use_proxy: bool = True,
        proxy_sources: Optional[list[str]] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 2,
        show_progress: bool = True,
        force_refresh_proxies: bool = False,
        validate_proxies: bool = True,
        auto_export_proxies: bool = False,
        export_proxies_file: str = "working_proxies.txt",
        headers: Optional[dict[str, str]] = None,
        user_agent: Optional[str] = None,
        follow_redirects: bool = True,
        max_redirects: int = 10,
        verify_ssl: bool = True,
        limit_per_host: int = 5,
        parser_in_thread: bool = False,
        retry_backoff: float = 2.0,
        retry_jitter: float = 0.1,
        retry_on_statuses: Optional[Iterable[int]] = None,
        proxy_test_url: str = "http://httpbin.org/ip",
        proxy_test_timeout: int = 10,
        proxy_test_max_concurrent: int = 20,
        max_socks_sessions: int = 20,
    ) -> None:
        self.urls = list(urls)
        self.parser = parser or self._default_parser
        self.storage = storage or AggregatedStorage()

        self.max_workers = max(1, int(max_workers))
        self.use_proxy = bool(use_proxy)
        self.timeout = int(timeout)
        self.max_retries = max(1, int(max_retries))
        self.retry_delay = float(retry_delay)
        self.show_progress = bool(show_progress)
        self.force_refresh_proxies = bool(force_refresh_proxies)
        self.validate_proxies = bool(validate_proxies)
        self.auto_export_proxies = bool(auto_export_proxies)
        self.export_proxies_file = export_proxies_file

        self.follow_redirects = bool(follow_redirects)
        self.max_redirects = int(max_redirects)
        self.verify_ssl = bool(verify_ssl)
        self.limit_per_host = int(limit_per_host)
        self.parser_in_thread = bool(parser_in_thread)

        self.retry_backoff = float(retry_backoff)
        self.retry_jitter = float(retry_jitter)
        self.retry_on_statuses = set(retry_on_statuses) if retry_on_statuses else {429, 500, 502, 503, 504}

        self.proxy_test_url = proxy_test_url
        self.proxy_test_timeout = int(proxy_test_timeout)
        self.proxy_test_max_concurrent = int(proxy_test_max_concurrent)

        self.headers = build_headers(headers, user_agent=user_agent)
        self._timeout = aiohttp.ClientTimeout(
            total=self.timeout,
            connect=self.timeout,
            sock_connect=self.timeout,
            sock_read=self.timeout,
        )
        self._ssl = None if self.verify_ssl else False

        self.proxy_manager = (
            ProxyManager(custom_sources=proxy_sources, headers=self.headers, verify_ssl=self.verify_ssl)
            if self.use_proxy
            else None
        )

        # SOCKS requests require a dedicated session per proxy, so keep a small LRU.
        self._socks_pool = SocksSessionPool(
            max_sessions=max_socks_sessions,
            timeout=self._timeout,
            headers=self.headers,
            connector_kwargs={"limit": self.max_workers, "limit_per_host": self.limit_per_host},
        )
        self._cache_socks_sessions = max_socks_sessions != 0

        self.stats: dict[str, Any] = {
            "total": len(self.urls),
            "success": 0,
            "failed": 0,
            "start_time": None,
            "end_time": None,
        }

    def _default_parser(self, url: str, html_content: str) -> dict[str, Any]:
        soup = BeautifulSoup(html_content, "html.parser")

        title = soup.title.string if soup.title else ""

        for script in soup(["script", "style"]):
            script.decompose()

        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = " ".join(chunk for chunk in chunks if chunk)

        links = [a.get("href") for a in soup.find_all("a", href=True)]

        return {
            "title": title,
            "text": text[:500],
            "links_count": len(links),
            "links": links[:10],
        }

    def _retry_sleep_seconds(self, attempt: int) -> float:
        base = float(self.retry_delay) * (float(self.retry_backoff) ** attempt)
        if self.retry_jitter <= 0:
            return base
        return base + random.uniform(0.0, float(self.retry_jitter) * base)

    async def _handle_bad_status(
        self,
        url: str,
        status: int,
        headers: "aiohttp.typedefs.LooseHeaders",
        proxy: Optional[str],
        attempt: int,
    ) -> None:
        # Strong proxy-failure signals.
        if proxy and self.proxy_manager and status in {407, 502, 503, 504}:
            self.proxy_manager.mark_failed(proxy)
            if is_socks_proxy(proxy):
                await self._socks_pool.invalidate(proxy)

        # Honor Retry-After for 429 when present.
        if status in self.retry_on_statuses and attempt < self.max_retries - 1:
            retry_after = headers.get("Retry-After")
            if retry_after:
                try:
                    seconds = max(0.0, float(retry_after))
                except ValueError:
                    seconds = 0.0
                if seconds > 0:
                    await asyncio.sleep(seconds)
                    return

        logger.debug("HTTP %s for %s (proxy=%s)", status, url, proxy)

    async def _fetch_url(self, session: aiohttp.ClientSession, url: str) -> tuple[str, Optional[str]]:
        for attempt in range(self.max_retries):
            proxy: Optional[str] = None
            if self.use_proxy and self.proxy_manager:
                proxy = await self.proxy_manager.get_proxy()

            try:
                async def _request_once() -> tuple[int, Optional[str], "aiohttp.typedefs.LooseHeaders"]:
                    if proxy and is_socks_proxy(proxy):
                        socks_session = await self._socks_pool.get(proxy)
                        try:
                            async with socks_session.get(
                                url,
                                ssl=self._ssl,
                                allow_redirects=self.follow_redirects,
                                max_redirects=self.max_redirects,
                            ) as response:
                                status = response.status
                                headers = response.headers
                                if status == 200:
                                    return status, await response.text(errors="ignore"), headers
                                return status, None, headers
                        finally:
                            if not self._cache_socks_sessions:
                                await socks_session.close()

                    async with session.get(
                        url,
                        proxy=proxy,
                        ssl=self._ssl,
                        allow_redirects=self.follow_redirects,
                        max_redirects=self.max_redirects,
                    ) as response:
                        status = response.status
                        headers = response.headers
                        if status == 200:
                            return status, await response.text(errors="ignore"), headers
                        return status, None, headers

                status, html, headers = await asyncio.wait_for(_request_once(), timeout=self.timeout)
                if html is not None:
                    return url, html
                await self._handle_bad_status(url, status, headers, proxy, attempt)

            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                logger.debug("Attempt %s/%s failed for %s: %s", attempt + 1, self.max_retries, url, e)
                if proxy and self.proxy_manager:
                    self.proxy_manager.mark_failed(proxy)
                if proxy and is_socks_proxy(proxy):
                    await self._socks_pool.invalidate(proxy)

            if attempt < self.max_retries - 1:
                await asyncio.sleep(self._retry_sleep_seconds(attempt))

        logger.info("Failed to fetch after %s attempts: %s", self.max_retries, url)
        return url, None

    async def _process_url(self, session: aiohttp.ClientSession, url: str) -> None:
        url, html = await self._fetch_url(session, url)
        if not html:
            self.stats["failed"] += 1
            return

        try:
            if self.parser_in_thread and not inspect.iscoroutinefunction(self.parser):
                data = await asyncio.to_thread(self.parser, url, html)
            else:
                data = self.parser(url, html)
                if inspect.isawaitable(data):
                    data = await data

            await self.storage.save(url, data)
            self.stats["success"] += 1
        except Exception as e:
            logger.exception("Error processing %s: %s", url, e)
            self.stats["failed"] += 1

    async def _maybe_prepare_proxies(self) -> None:
        if not (self.use_proxy and self.proxy_manager):
            return

        if self.force_refresh_proxies or not self.proxy_manager.proxies:
            await self.proxy_manager.fetch_proxies()

        if self.validate_proxies and self.proxy_manager.proxies:
            results = await self.proxy_manager.test_all_proxies(
                test_url=self.proxy_test_url,
                timeout=self.proxy_test_timeout,
                max_concurrent=self.proxy_test_max_concurrent,
                show_progress=self.show_progress,
                remove_failed=True,
            )

            if self.auto_export_proxies:
                self.proxy_manager.export_live_proxies(self.export_proxies_file)
                logger.info("Auto-exported working proxies to %s", self.export_proxies_file)

            logger.info(
                "Proxy validation: working=%s/%s (success_rate=%.1f%%)",
                results["working"],
                results["total"],
                results["success_rate"] * 100.0,
            )

        if not self.proxy_manager.proxies:
            logger.warning("No proxies available; continuing without proxy.")
            self.use_proxy = False

    async def _crawl_async(self) -> None:
        if not self.urls:
            logger.warning("No URLs to crawl.")
            return

        await self._maybe_prepare_proxies()

        connector = aiohttp.TCPConnector(limit=self.max_workers, limit_per_host=self.limit_per_host)

        async with aiohttp.ClientSession(connector=connector, timeout=self._timeout, headers=self.headers) as session:
            worker_count = min(self.max_workers, len(self.urls))

            queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
            for url in self.urls:
                queue.put_nowait(url)
            for _ in range(worker_count):
                queue.put_nowait(None)

            pbar = tqdm(total=len(self.urls), desc="Crawling URLs", unit="url") if self.show_progress else None

            async def worker() -> None:
                while True:
                    url = await queue.get()
                    try:
                        if url is None:
                            return
                        await self._process_url(session, url)
                    finally:
                        queue.task_done()
                        if pbar is not None and url is not None:
                            pbar.update(1)

            try:
                tasks = [asyncio.create_task(worker()) for _ in range(worker_count)]
                await queue.join()
                await asyncio.gather(*tasks)
            finally:
                if pbar is not None:
                    pbar.close()

    async def crawl_async(self) -> dict[str, Any]:
        """
        Run the crawler asynchronously.

        Returns a statistics dict.
        """
        self.stats = {
            "total": len(self.urls),
            "success": 0,
            "failed": 0,
            "start_time": None,
            "end_time": None,
        }

        logger.info("Starting crawl of %s URLs with %s workers...", len(self.urls), self.max_workers)
        self.stats["start_time"] = time.time()

        try:
            await self._crawl_async()
            await self.storage.finalize()
        finally:
            await self._socks_pool.close()

        self.stats["end_time"] = time.time()
        self.stats["duration"] = round(self.stats["end_time"] - self.stats["start_time"], 2)

        logger.info("Crawl completed: %s success, %s failed", self.stats["success"], self.stats["failed"])
        logger.info("Duration: %ss", self.stats["duration"])
        return self.stats

    def crawl(self) -> dict[str, Any]:
        """
        Sync wrapper for crawl_async().

        If you're calling from a context that already has an event loop running
        (Jupyter, FastAPI, etc.), use: `await crawler.crawl_async()`.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.crawl_async())
        raise RuntimeError("WebCrawler.crawl() cannot run inside an existing event loop. Use await crawl_async().")

    def add_urls(self, urls: list[str]) -> None:
        self.urls.extend(urls)
        self.stats["total"] = len(self.urls)
        logger.info("Added %s URLs, total: %s", len(urls), len(self.urls))
