"""
HTTP helpers shared across the package.

Key goals:
- Keep reasonable, browser-like default headers to reduce trivial blocks.
- Support both HTTP(S) proxies and SOCKS proxies.
- Reuse SOCKS sessions/connectors (creating a new session per request is expensive).
"""

from __future__ import annotations

import asyncio
from collections import OrderedDict
from typing import Any, Mapping, MutableMapping, Optional

import aiohttp
from aiohttp_socks import ProxyConnector


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def is_socks_proxy(proxy: Optional[str]) -> bool:
    if not proxy:
        return False
    p = proxy.lower()
    return p.startswith("socks5://") or p.startswith("socks4://") or p.startswith("socks://")


def build_headers(
    headers: Optional[Mapping[str, str]] = None,
    *,
    user_agent: Optional[str] = None,
) -> dict[str, str]:
    merged: dict[str, str] = {
        "User-Agent": user_agent or DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }

    if headers:
        # Preserve caller intent (their keys win).
        for k, v in headers.items():
            merged[str(k)] = str(v)
    return merged


class SocksSessionPool:
    """
    Cache/reuse a limited number of aiohttp sessions pinned to a SOCKS proxy.

    aiohttp can't use SOCKS proxies via the per-request `proxy=` argument, so we
    need a dedicated session (with ProxyConnector) per proxy. Creating sessions
    for every request is expensive, so we keep a small LRU cache.
    """

    def __init__(
        self,
        *,
        max_sessions: int = 20,
        timeout: Optional[aiohttp.ClientTimeout] = None,
        headers: Optional[Mapping[str, str]] = None,
        connector_kwargs: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self._max_sessions = max(0, int(max_sessions))
        self._timeout = timeout
        self._headers = dict(headers) if headers else None
        self._connector_kwargs = dict(connector_kwargs) if connector_kwargs else {}

        self._lock = asyncio.Lock()
        self._sessions: "OrderedDict[str, aiohttp.ClientSession]" = OrderedDict()

    async def get(self, proxy: str) -> aiohttp.ClientSession:
        if self._max_sessions == 0:
            # Degenerate mode: no caching; caller should close the session.
            connector = ProxyConnector.from_url(proxy, **self._connector_kwargs)
            return aiohttp.ClientSession(connector=connector, timeout=self._timeout, headers=self._headers)

        async with self._lock:
            session = self._sessions.get(proxy)
            if session and not session.closed:
                self._sessions.move_to_end(proxy)
                return session

            if session and session.closed:
                self._sessions.pop(proxy, None)

            # LRU eviction.
            while len(self._sessions) >= self._max_sessions:
                _, old = self._sessions.popitem(last=False)
                await old.close()

            connector = ProxyConnector.from_url(proxy, **self._connector_kwargs)
            session = aiohttp.ClientSession(connector=connector, timeout=self._timeout, headers=self._headers)
            self._sessions[proxy] = session
            return session

    async def invalidate(self, proxy: str) -> None:
        async with self._lock:
            session = self._sessions.pop(proxy, None)
        if session and not session.closed:
            await session.close()

    async def close(self) -> None:
        async with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for session in sessions:
            if not session.closed:
                await session.close()

