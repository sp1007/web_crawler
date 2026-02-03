"""
ProxyManager - fetch, parse, rotate, validate proxies (HTTP + SOCKS).

Notes:
- Free proxies are inherently unstable; treat them as best-effort.
- SOCKS proxies can't be used via aiohttp's per-request `proxy=` argument.
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import re
import time
from typing import Any, Optional

import aiohttp
from aiohttp_socks import ProxyConnector
from bs4 import BeautifulSoup
from tqdm.asyncio import tqdm as async_tqdm

from .http_client import build_headers, is_socks_proxy

logger = logging.getLogger(__name__)


class ProxyManager:
    # Public/free proxy sources (best-effort).
    PROXY_SOURCES = [
        "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=text",
        "https://www.freeproxy.world/?type=&anonymity=&country=CN&page=1",
        "https://www.freeproxy.world/?type=&anonymity=&country=CN&page=2",
        "https://www.freeproxy.world/?type=&anonymity=&country=CN&page=3",
        "https://www.freeproxy.world/?type=&anonymity=&country=CN&page=4",
        "https://proxydb.net/?anonlvl=4&country=CN&offset=0",
        "https://proxydb.net/?anonlvl=4&country=CN&offset=30",
        "https://proxydb.net/?anonlvl=4&country=CN&offset=60",
        "https://proxydb.net/?anonlvl=4&country=CN&offset=90",
        "https://cdn.jsdelivr.net/gh/databay-labs/free-proxy-list/socks5.txt",
        "https://cdn.jsdelivr.net/gh/databay-labs/free-proxy-list/http.txt",
    ]

    def __init__(
        self,
        custom_sources: Optional[list[str]] = None,
        *,
        headers: Optional[dict[str, str]] = None,
        user_agent: Optional[str] = None,
        verify_ssl: bool = True,
    ) -> None:
        self.proxies: list[str] = []
        self.sources = custom_sources if custom_sources else list(self.PROXY_SOURCES)
        self.failed_proxies: set[str] = set()

        self.headers = build_headers(headers, user_agent=user_agent)
        self.verify_ssl = bool(verify_ssl)
        self._ssl = None if self.verify_ssl else False

    async def fetch_proxies(self) -> None:
        logger.info("Fetching proxies from %s sources...", len(self.sources))

        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout, headers=self.headers) as session:
            tasks = [self._fetch_from_source(session, source) for source in self.sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        all_proxies: list[str] = []
        for result in results:
            if isinstance(result, list):
                all_proxies.extend(result)

        # De-duplicate and drop obvious invalid entries.
        deduped = list(dict.fromkeys(p.strip() for p in all_proxies if p and ":" in p))
        self.proxies = deduped
        logger.info("Fetched %s unique proxies", len(self.proxies))

    async def _fetch_from_source(self, session: aiohttp.ClientSession, source: str) -> list[str]:
        try:
            async with session.get(source, ssl=self._ssl) as response:
                if response.status != 200:
                    logger.debug("Proxy source HTTP %s: %s", response.status, source)
                    return []
                content = await response.text(errors="ignore")
                return self._parse_proxy_list(content, source)
        except Exception as e:
            logger.debug("Failed to fetch proxies from %s: %s", source, e)
            return []

    def _parse_proxy_list(self, content: str, source: str) -> list[str]:
        proxies: list[str] = []

        if "api.proxyscrape.com" in source:
            for line in content.splitlines():
                line = line.strip()
                if not line:
                    continue
                # The API may already include the protocol (e.g. http://ip:port).
                if "://" in line:
                    proxies.append(line)
                elif ":" in line:
                    proxies.append(f"http://{line}")
            return proxies

        if "cdn.jsdelivr.net/gh/databay-labs" in source:
            for line in content.splitlines():
                line = line.strip()
                if not line or ":" not in line:
                    continue
                if "socks5" in source:
                    proxies.append(f"socks5://{line}")
                else:
                    proxies.append(f"http://{line}")
            return proxies

        if "www.freeproxy.world" in source:
            return self._parse_freeproxy_world(content)

        if "proxydb.net" in source:
            return self._parse_proxydb_net(content)

        # Generic fallback: scrape IP:PORT patterns from HTML/text.
        try:
            soup = BeautifulSoup(content, "html.parser")
            text = soup.get_text(" ", strip=True)
        except Exception:
            text = content

        pattern = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}\b")
        for match in pattern.findall(text):
            proxies.append(f"http://{match}")
        return proxies

    def _parse_freeproxy_world(self, content: str) -> list[str]:
        proxies: list[str] = []
        try:
            soup = BeautifulSoup(content, "html.parser")
            for row in soup.select("div.table-container table tbody tr"):
                cols = row.select("td")
                # The site layout can change; this is best-effort.
                if len(cols) < 8:
                    continue

                # Skip proxies that are explicitly marked as not alive/valid.
                if cols[6].get_text(strip=True).lower() == "no":
                    continue

                ip = cols[0].get_text(strip=True)
                port = cols[1].get_text(strip=True)
                types = cols[5].select("a")
                if not ip or not port or not types:
                    continue

                for t in types:
                    protocol = t.get_text(strip=True).lower()
                    if protocol in {"http", "https", "socks4", "socks5"}:
                        proxies.append(f"{protocol}://{ip}:{port}")
        except Exception as e:
            logger.debug("Failed to parse freeproxy.world: %s", e)
        return proxies

    def _parse_proxydb_net(self, content: str) -> list[str]:
        proxies: list[str] = []
        try:
            soup = BeautifulSoup(content, "html.parser")
            for row in soup.select("div.table-responsive tbody tr"):
                cols = row.select("td")
                if len(cols) < 9:
                    continue

                ip = cols[0].get_text(strip=True)
                port_el = cols[1].select_one("a")
                port = port_el.get_text(strip=True) if port_el else cols[1].get_text(strip=True)
                protocol = cols[2].get_text(strip=True).lower()

                if ip and port and protocol in {"http", "https", "socks4", "socks5"}:
                    proxies.append(f"{protocol}://{ip}:{port}")
        except Exception as e:
            logger.debug("Failed to parse proxydb.net: %s", e)
        return proxies

    # Backwards-compatible alias (older code may call this directly).
    def parse_proxydb_net(self, content: str) -> list[str]:
        return self._parse_proxydb_net(content)

    async def get_proxy(self) -> Optional[str]:
        available = [p for p in self.proxies if p not in self.failed_proxies]
        if not available:
            logger.debug("No available proxies, attempting to fetch new ones...")
            await self.fetch_proxies()
            available = [p for p in self.proxies if p not in self.failed_proxies]

            if not available:
                logger.debug("Still no proxies, resetting failed list...")
                self.failed_proxies.clear()
                available = list(self.proxies)

        if not available:
            return None
        return random.choice(available)

    def get_stats(self) -> dict[str, Any]:
        total = len(self.proxies)
        failed = len(self.failed_proxies)
        return {
            "total": total,
            "failed": failed,
            "available": total - failed,
            "failure_rate": (failed / total) if total else 0.0,
        }

    def mark_failed(self, proxy: str) -> None:
        self.failed_proxies.add(proxy)

    def add_proxies(self, proxies: list[str]) -> None:
        self.proxies = list(dict.fromkeys(self.proxies + proxies))
        logger.info("Added %s proxies, total: %s", len(proxies), len(self.proxies))

    def add_source(self, source: str) -> None:
        if source not in self.sources:
            self.sources.append(source)
            logger.info("Added new proxy source: %s", source)

    async def test_proxy(
        self,
        proxy: str,
        test_url: str = "http://httpbin.org/ip",
        timeout: int = 10,
        *,
        session: Optional[aiohttp.ClientSession] = None,
        verify_ssl: Optional[bool] = None,
    ) -> tuple[str, bool, str]:
        """
        Return: (proxy, success, info)
        - info is response time string for success, else error summary
        """
        ssl = None if (self.verify_ssl if verify_ssl is None else bool(verify_ssl)) else False

        start = time.perf_counter()
        try:
            if is_socks_proxy(proxy):
                connector = ProxyConnector.from_url(proxy)
                client_timeout = aiohttp.ClientTimeout(total=timeout)
                async with aiohttp.ClientSession(connector=connector, timeout=client_timeout, headers=self.headers) as s:
                    async with s.get(test_url, ssl=ssl) as response:
                        if response.status == 200:
                            return proxy, True, f"{time.perf_counter() - start:.2f}s"
                        return proxy, False, f"HTTP {response.status}"

            # HTTP(S) proxy path
            if session is None:
                client_timeout = aiohttp.ClientTimeout(total=timeout)
                async with aiohttp.ClientSession(timeout=client_timeout, headers=self.headers) as s:
                    async with s.get(test_url, proxy=proxy, ssl=ssl) as response:
                        if response.status == 200:
                            return proxy, True, f"{time.perf_counter() - start:.2f}s"
                        return proxy, False, f"HTTP {response.status}"

            async with session.get(test_url, proxy=proxy, ssl=ssl) as response:
                if response.status == 200:
                    return proxy, True, f"{time.perf_counter() - start:.2f}s"
                return proxy, False, f"HTTP {response.status}"

        except asyncio.TimeoutError:
            return proxy, False, "Timeout"
        except Exception as e:
            msg = str(e).strip()
            return proxy, False, (msg[:80] if msg else "Error")

    async def test_all_proxies(
        self,
        test_url: str = "http://httpbin.org/ip",
        timeout: int = 10,
        max_concurrent: int = 20,
        show_progress: bool = True,
        remove_failed: bool = True,
        *,
        verify_ssl: Optional[bool] = None,
    ) -> dict[str, Any]:
        if not self.proxies:
            logger.warning("No proxies to test")
            return {
                "total": 0,
                "working": 0,
                "failed": 0,
                "success_rate": 0.0,
                "working_proxies": [],
                "failed_proxies": [],
            }

        semaphore = asyncio.Semaphore(max(1, int(max_concurrent)))
        client_timeout = aiohttp.ClientTimeout(total=timeout)

        async def test_with_semaphore(proxy: str, http_session: aiohttp.ClientSession) -> tuple[str, bool, str]:
            async with semaphore:
                # Reuse session for HTTP proxies only; SOCKS proxies require their own connector.
                sess = None if is_socks_proxy(proxy) else http_session
                return await self.test_proxy(proxy, test_url, timeout, session=sess, verify_ssl=verify_ssl)

        working_proxies: list[dict[str, str]] = []
        failed_proxies: list[dict[str, str]] = []

        async with aiohttp.ClientSession(timeout=client_timeout, headers=self.headers) as http_session:
            tasks = [test_with_semaphore(proxy, http_session) for proxy in self.proxies]
            if show_progress:
                results = await async_tqdm.gather(*tasks, desc="Testing proxies", unit="proxy")
            else:
                results = await asyncio.gather(*tasks)

        for proxy, success, info in results:
            if success:
                working_proxies.append({"proxy": proxy, "response_time": info})
            else:
                failed_proxies.append({"proxy": proxy, "error": info})
                if remove_failed:
                    self.mark_failed(proxy)

        if remove_failed and self.failed_proxies:
            self.proxies = [p for p in self.proxies if p not in self.failed_proxies]

        total = len(results)
        working = len(working_proxies)
        failed = len(failed_proxies)
        return {
            "total": total,
            "working": working,
            "failed": failed,
            "success_rate": (working / total) if total else 0.0,
            "working_proxies": working_proxies,
            "failed_proxies": failed_proxies,
        }

    def get_working_proxies(self) -> list[str]:
        return [p for p in self.proxies if p not in self.failed_proxies]

    def export_live_proxies(self, filepath: str) -> None:
        working = self.get_working_proxies()
        with open(filepath, "w", encoding="utf-8") as f:
            for proxy in working:
                f.write(f"{proxy}\n")
        logger.info("Exported %s working proxies to %s", len(working), filepath)

    def import_proxies(self, filepath: str) -> None:
        if not os.path.isfile(filepath):
            logger.warning("Proxy file not found: %s", filepath)
            return
        with open(filepath, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        self.add_proxies(lines)
        logger.info("Imported %s proxies from %s", len(lines), filepath)
