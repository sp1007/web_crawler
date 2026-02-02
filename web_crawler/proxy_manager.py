"""
Proxy Manager - Tự động lấy và quản lý danh sách proxy
"""

import aiohttp
import asyncio
import re
from typing import List, Optional
from bs4 import BeautifulSoup
import random
import logging

logger = logging.getLogger(__name__)


class ProxyManager:
    """Quản lý danh sách proxy và rotation"""
    
    # Các nguồn proxy miễn phí
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
    
    def __init__(self, custom_sources: Optional[List[str]] = None):
        """
        Args:
            custom_sources: Danh sách custom proxy sources (optional)
        """
        self.proxies: List[str] = []
        self.sources = custom_sources if custom_sources else self.PROXY_SOURCES
        self.failed_proxies = set()
        
    async def fetch_proxies(self) -> None:
        """Lấy danh sách proxy từ các nguồn"""
        logger.info(f"Fetching proxies from {len(self.sources)} sources...")
        
        async with aiohttp.ClientSession() as session:
            tasks = [self._fetch_from_source(session, source) for source in self.sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
        # Gộp tất cả proxies và loại bỏ duplicates
        all_proxies = []
        for result in results:
            if isinstance(result, list):
                all_proxies.extend(result)
        
        self.proxies = list(set(all_proxies))
        logger.info(f"Fetched {len(self.proxies)} unique proxies")
        
    async def _fetch_from_source(self, session: aiohttp.ClientSession, source: str) -> List[str]:
        """Lấy proxy từ một nguồn cụ thể"""
        try:
            async with session.get(source, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    content = await response.text()
                    return self._parse_proxy_list(content, source)
        except Exception as e:
            logger.warning(f"Failed to fetch from {source}: {e}")
        return []
    
    def _parse_proxy_list(self, content: str, source: str) -> List[str]:
        """Parse danh sách proxy từ response"""
        proxies = []
        # Nếu là plain text (mỗi dòng 1 proxy)
        if "api.proxyscrape.com" in source:
            lines = content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and '://' in line:
                    proxies.append(line)
        elif "cdn.jsdelivr.net/gh/databay-labs" in source:
            lines = content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and ':' in line:
                    if 'socks5' in source:
                        proxies.append(f"socks5://{line}")
                    else:
                        proxies.append(f"http://{line}")
        elif "www.freeproxy.world" in source:
            proxies.extend(self._parse_freeproxy_world(content))
        elif "proxydb.net" in source:
            proxies.extend(self.parse_proxydb_net(content))
        else:
            # Thử parse HTML
            try:
                soup = BeautifulSoup(content, 'html.parser')
                # Pattern để tìm IP:PORT
                pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}\b')
                
                # Tìm trong text
                text = soup.get_text()
                matches = pattern.findall(text)
                for match in matches:
                    # Thêm protocol
                    proxies.append(f"http://{match}")
                    
            except Exception as e:
                logger.warning(f"Failed to parse HTML from {source}: {e}")
        
        return proxies
    
    def _parse_freeproxy_world(self, content: str) -> List[str]:
        """Cách parse riêng cho freeproxy.world nếu cần"""
        proxies = []
        try:
            soup = BeautifulSoup(content, 'html.parser')
            info_containers = soup.select('div.table-container table tbody tr')
            if info_containers and len(info_containers) > 0:
                for row in info_containers:
                    cols = row.select('td')
                    if len(cols) >= 8 and cols[6].get_text(strip=True) != 'No':
                        ip = cols[0].get_text(strip=True)
                        port = cols[1].get_text(strip=True)
                        types = cols[5].select('a')
                        if types and len(types) > 0:
                            for type in types:
                                protocol = type.get_text(strip=True).lower()
                                proxy = f"{protocol}://{ip}:{port}"
                                proxies.append(proxy)
        except Exception as e:
            logger.warning(f"Failed to parse freeproxy.world: {e}")
        return proxies
    
    def parse_proxydb_net(self, content: str) -> List[str]:
        """Cách parse riêng cho proxydb.net nếu cần"""
        proxies = []
        try:
            soup = BeautifulSoup(content, 'html.parser')
            info_containers = soup.select('div.table-responsive tbody tr')
            if info_containers and len(info_containers) > 0:
                for row in info_containers:
                    cols = row.select('td')
                    if len(cols) >= 9:
                        ip = cols[0].get_text(strip=True)
                        port = cols[1].select_one('a').get_text(strip=True)
                        protocol = cols[2].get_text(strip=True).lower()
                        proxy = f"{protocol}://{ip}:{port}"
                        proxies.append(proxy)
        except Exception as e:
            logger.warning(f"Failed to parse proxydb.net: {e}")
        return proxies
    
    async def get_proxy(self) -> Optional[str]:
        """Lấy một proxy ngẫu nhiên, tự động refetch nếu hết"""
        available_proxies = [p for p in self.proxies if p not in self.failed_proxies]
        
        if not available_proxies:
            # Nếu hết proxy, thử fetch lại
            logger.warning("No available proxies, attempting to fetch new ones...")
            await self.fetch_proxies()
            available_proxies = [p for p in self.proxies if p not in self.failed_proxies]
            
            # Nếu vẫn không có, reset failed list
            if not available_proxies:
                logger.warning("Still no proxies, resetting failed list...")
                self.failed_proxies.clear()
                available_proxies = self.proxies
            
        if available_proxies:
            return random.choice(available_proxies)
        
        logger.error("No proxies available at all!")
        return None
    
    def get_stats(self) -> dict:
        """Thống kê proxy"""
        return {
            'total': len(self.proxies),
            'failed': len(self.failed_proxies),
            'available': len([p for p in self.proxies if p not in self.failed_proxies]),
            'failure_rate': len(self.failed_proxies) / len(self.proxies) if self.proxies else 0
        }
    
    def mark_failed(self, proxy: str) -> None:
        """Đánh dấu proxy thất bại"""
        self.failed_proxies.add(proxy)
        logger.debug(f"Marked proxy as failed: {proxy}")
    
    def add_proxies(self, proxies: List[str]) -> None:
        """Thêm proxy thủ công"""
        self.proxies.extend(proxies)
        self.proxies = list(set(self.proxies))
        logger.info(f"Added {len(proxies)} proxies, total: {len(self.proxies)}")
        
    def add_source(self, source: str) -> None:
        """Thêm nguồn proxy mới"""
        if source not in self.sources:
            self.sources.append(source)
            logger.info(f"Added new proxy source: {source}")
