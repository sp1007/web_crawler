"""
ChainCrawler - multi-step crawling (URL list -> URL list -> ... -> final results).
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import random
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional

import aiohttp
from tqdm import tqdm

from .http_client import SocksSessionPool, build_headers, is_socks_proxy
from .proxy_manager import ProxyManager
from .storage import AggregatedStorage, StorageBackend

logger = logging.getLogger(__name__)


class ChainStep:
    """
    One step in the chain.

    - parser(url, html) -> data
    - extract_next_urls(data) -> list[str] (optional; if omitted this is the final step)
    """

    def __init__(
        self,
        name: str,
        parser: Callable[[str, str], Any],
        extract_next_urls: Optional[Callable[[Any], list[str]]] = None,
    ) -> None:
        self.name = name
        self.parser = parser
        self.extract_next_urls = extract_next_urls

    def is_final_step(self) -> bool:
        return self.extract_next_urls is None


@dataclass
class _WorkerResult:
    next_urls: list[str]
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    next_urls_found: int = 0
    final_saved: int = 0


class ChainCrawler:
    """
    Multi-step crawler.

    Each step processes a list of URLs and may produce the next list of URLs.
    Only final-step results are persisted to storage.
    """

    def __init__(
        self,
        initial_urls: list[str],
        steps: list[ChainStep],
        storage: Optional[StorageBackend] = None,
        max_workers: int = 8,
        use_proxy: bool = True,
        proxy_sources: Optional[list[str]] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 2,
        max_urls_per_step: Optional[int] = None,
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
        self.initial_urls = list(initial_urls)
        self.steps = list(steps)
        self.storage = storage or AggregatedStorage()

        self.max_workers = max(1, int(max_workers))
        self.use_proxy = bool(use_proxy)
        self.timeout = int(timeout)
        self.max_retries = max(1, int(max_retries))
        self.retry_delay = float(retry_delay)
        self.max_urls_per_step = max_urls_per_step
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
        self._timeout = aiohttp.ClientTimeout(total=self.timeout)
        self._ssl = None if self.verify_ssl else False

        self.proxy_manager = (
            ProxyManager(custom_sources=proxy_sources, headers=self.headers, verify_ssl=self.verify_ssl)
            if self.use_proxy
            else None
        )

        self._socks_pool = SocksSessionPool(
            max_sessions=max_socks_sessions,
            timeout=self._timeout,
            headers=self.headers,
            connector_kwargs={"limit": self.max_workers, "limit_per_host": self.limit_per_host},
        )
        self._cache_socks_sessions = max_socks_sessions != 0

        self.stats: dict[str, Any] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "steps_completed": 0,
            "final_results": 0,
            "step_stats": {},
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
        response: aiohttp.ClientResponse,
        proxy: Optional[str],
        attempt: int,
    ) -> None:
        if proxy and self.proxy_manager and status in {407, 502, 503, 504}:
            self.proxy_manager.mark_failed(proxy)
            if is_socks_proxy(proxy):
                await self._socks_pool.invalidate(proxy)

        if status in self.retry_on_statuses and attempt < self.max_retries - 1:
            retry_after = response.headers.get("Retry-After")
            if retry_after:
                try:
                    seconds = max(0.0, float(retry_after))
                except ValueError:
                    seconds = 0.0
                if seconds > 0:
                    await asyncio.sleep(seconds)
                    return

        logger.debug("HTTP %s for %s (proxy=%s)", status, url, proxy)

    async def _fetch_url(self, session: aiohttp.ClientSession, url: str) -> Optional[str]:
        for attempt in range(self.max_retries):
            proxy: Optional[str] = None
            if self.use_proxy and self.proxy_manager:
                proxy = await self.proxy_manager.get_proxy()

            try:
                if proxy and is_socks_proxy(proxy):
                    socks_session = await self._socks_pool.get(proxy)
                    try:
                        async with socks_session.get(
                            url,
                            ssl=self._ssl,
                            allow_redirects=self.follow_redirects,
                            max_redirects=self.max_redirects,
                        ) as response:
                            if response.status == 200:
                                return await response.text(errors="ignore")
                            await self._handle_bad_status(url, response.status, response, proxy, attempt)
                    finally:
                        if not self._cache_socks_sessions:
                            await socks_session.close()
                else:
                    async with session.get(
                        url,
                        proxy=proxy,
                        ssl=self._ssl,
                        allow_redirects=self.follow_redirects,
                        max_redirects=self.max_redirects,
                    ) as response:
                        if response.status == 200:
                            return await response.text(errors="ignore")
                        await self._handle_bad_status(url, response.status, response, proxy, attempt)

            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                logger.debug("Attempt %s/%s failed for %s: %s", attempt + 1, self.max_retries, url, e)
                if proxy and self.proxy_manager:
                    self.proxy_manager.mark_failed(proxy)
                if proxy and is_socks_proxy(proxy):
                    await self._socks_pool.invalidate(proxy)

            if attempt < self.max_retries - 1:
                await asyncio.sleep(self._retry_sleep_seconds(attempt))

        return None

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

    async def _process_step(
        self,
        session: aiohttp.ClientSession,
        step: ChainStep,
        urls: list[str],
        step_index: int,
    ) -> list[str]:
        if self.max_urls_per_step is not None and len(urls) > self.max_urls_per_step:
            logger.warning("Limiting step %s URLs from %s to %s", step_index + 1, len(urls), self.max_urls_per_step)
            urls = urls[: self.max_urls_per_step]

        if not urls:
            return []

        worker_count = min(self.max_workers, len(urls))
        queue: asyncio.Queue[Optional[str]] = asyncio.Queue()
        for url in urls:
            queue.put_nowait(url)
        for _ in range(worker_count):
            queue.put_nowait(None)

        pbar = (
            tqdm(total=len(urls), desc=f"Step {step_index + 1}: {step.name}", unit="url")
            if self.show_progress
            else None
        )

        async def worker() -> _WorkerResult:
            result = _WorkerResult(next_urls=[])
            while True:
                url = await queue.get()
                try:
                    if url is None:
                        return result

                    result.processed += 1
                    self.stats["total_requests"] += 1

                    html = await self._fetch_url(session, url)
                    if not html:
                        result.failed += 1
                        self.stats["failed_requests"] += 1
                        continue

                    try:
                        if self.parser_in_thread and not inspect.iscoroutinefunction(step.parser):
                            data = await asyncio.to_thread(step.parser, url, html)
                        else:
                            data = step.parser(url, html)
                            if inspect.isawaitable(data):
                                data = await data

                        if step.is_final_step():
                            await self.storage.save(url, data)
                            result.final_saved += 1
                            self.stats["final_results"] += 1
                        else:
                            new_urls = step.extract_next_urls(data) if step.extract_next_urls else []
                            if new_urls:
                                result.next_urls.extend(new_urls)
                                result.next_urls_found += len(new_urls)

                        result.succeeded += 1
                        self.stats["successful_requests"] += 1
                    except Exception as e:
                        logger.exception("Error processing %s in step '%s': %s", url, step.name, e)
                        result.failed += 1
                        self.stats["failed_requests"] += 1
                finally:
                    queue.task_done()
                    if pbar is not None and url is not None:
                        pbar.update(1)

        try:
            tasks = [asyncio.create_task(worker()) for _ in range(worker_count)]
            await queue.join()
            results = await asyncio.gather(*tasks)
        finally:
            if pbar is not None:
                pbar.close()

        # Merge worker results.
        next_urls: list[str] = []
        step_stats = {
            "urls_processed": 0,
            "urls_succeeded": 0,
            "urls_failed": 0,
            "next_urls_found": 0,
            "final_saved": 0,
        }
        for r in results:
            step_stats["urls_processed"] += r.processed
            step_stats["urls_succeeded"] += r.succeeded
            step_stats["urls_failed"] += r.failed
            step_stats["next_urls_found"] += r.next_urls_found
            step_stats["final_saved"] += r.final_saved
            if r.next_urls:
                next_urls.extend(r.next_urls)

        # De-duplicate for the next step.
        if next_urls:
            next_urls = list(dict.fromkeys(next_urls))

        self.stats["step_stats"][step.name] = step_stats
        self.stats["steps_completed"] += 1

        logger.info(
            "Step %s/%s '%s': processed=%s ok=%s failed=%s next_urls=%s",
            step_index + 1,
            len(self.steps),
            step.name,
            step_stats["urls_processed"],
            step_stats["urls_succeeded"],
            step_stats["urls_failed"],
            step_stats["next_urls_found"],
        )

        return next_urls

    async def _crawl_async(self) -> None:
        if not self.steps:
            logger.warning("No steps configured.")
            return

        await self._maybe_prepare_proxies()

        connector = aiohttp.TCPConnector(limit=self.max_workers, limit_per_host=self.limit_per_host)
        async with aiohttp.ClientSession(connector=connector, timeout=self._timeout, headers=self.headers) as session:
            current_urls = list(self.initial_urls)

            for step_index, step in enumerate(self.steps):
                if not current_urls:
                    logger.warning("No URLs to process for step %s. Stopping.", step_index + 1)
                    break

                current_urls = await self._process_step(session, step, current_urls, step_index)
                if step.is_final_step():
                    break

    async def crawl_async(self) -> dict[str, Any]:
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "steps_completed": 0,
            "final_results": 0,
            "step_stats": {},
        }

        logger.info(
            "Starting Chain Crawl: initial_urls=%s steps=%s workers=%s",
            len(self.initial_urls),
            len(self.steps),
            self.max_workers,
        )

        try:
            await self._crawl_async()
            await self.storage.finalize()
        finally:
            await self._socks_pool.close()

        logger.info(
            "Chain Crawl Completed: total=%s ok=%s failed=%s final=%s",
            self.stats["total_requests"],
            self.stats["successful_requests"],
            self.stats["failed_requests"],
            self.stats["final_results"],
        )
        return self.stats

    def crawl(self) -> dict[str, Any]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.crawl_async())
        raise RuntimeError("ChainCrawler.crawl() cannot run inside an existing event loop. Use await crawl_async().")
