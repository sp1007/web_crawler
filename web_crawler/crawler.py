"""
Web Crawler - Main crawler class với async và proxy support
"""

import aiohttp
from aiohttp_socks import ProxyConnector
import asyncio
from typing import List, Callable, Optional, Any
from bs4 import BeautifulSoup
import logging
from concurrent.futures import ThreadPoolExecutor
import time
from tqdm.asyncio import tqdm as async_tqdm

from .proxy_manager import ProxyManager
from .storage import StorageBackend, AggregatedStorage

logger = logging.getLogger(__name__)


class WebCrawler:
    """
    Async Web Crawler với proxy rotation và customizable parser
    """
    
    def __init__(
        self,
        urls: List[str],
        parser: Optional[Callable[[str, str], Any]] = None,
        storage: Optional[StorageBackend] = None,
        max_workers: int = 8,
        use_proxy: bool = True,
        proxy_sources: Optional[List[str]] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 2,
        show_progress: bool = True
    ):
        """
        Args:
            urls: Danh sách URLs cần crawl
            parser: Hàm custom để parse HTML (url, html_content) -> data
            storage: Storage backend (mặc định: AggregatedStorage)
            max_workers: Số lượng concurrent workers (mặc định: 8)
            use_proxy: Sử dụng proxy hay không
            proxy_sources: Custom proxy sources
            timeout: Timeout cho mỗi request (seconds)
            max_retries: Số lần retry khi thất bại
            retry_delay: Delay giữa các retry (seconds)
            show_progress: Hiển thị progress bar (mặc định: True)
        """
        self.urls = urls
        self.parser = parser or self._default_parser
        self.storage = storage or AggregatedStorage()
        self.max_workers = max_workers
        self.use_proxy = use_proxy
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.show_progress = show_progress
        
        # Proxy manager
        self.proxy_manager = ProxyManager(custom_sources=proxy_sources) if use_proxy else None
        
        # Statistics
        self.stats = {
            'total': len(urls),
            'success': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }
        
    def _default_parser(self, url: str, html_content: str) -> dict:
        """Parser mặc định - trích xuất text và links"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Lấy title
        title = soup.title.string if soup.title else ""
        
        # Lấy text content
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Lấy links
        links = [a.get('href') for a in soup.find_all('a', href=True)]
        
        return {
            'title': title,
            'text': text[:500],  # Giới hạn text
            'links_count': len(links),
            'links': links[:10]  # Lấy 10 links đầu tiên
        }
    
    async def _fetch_url(
        self,
        session: aiohttp.ClientSession,
        url: str,
        semaphore: asyncio.Semaphore
    ) -> tuple[str, Optional[str]]:
        """Fetch một URL với retry và proxy support"""
        async with semaphore:
            for attempt in range(self.max_retries):
                proxy = None
                if self.use_proxy and self.proxy_manager:
                    proxy = await self.proxy_manager.get_proxy()
                
                try:
                    if proxy and proxy.startswith("socks"):
                        connector = ProxyConnector.from_url(proxy)
                        async with aiohttp.ClientSession(connector=connector) as proxy_session:
                            async with proxy_session.get(
                                url,
                                timeout=aiohttp.ClientTimeout(total=self.timeout),
                                ssl=False
                            ) as response:
                                if response.status == 200:
                                    html = await response.text()
                                    logger.info(f"✓ Successfully fetched: {url} via {proxy}")
                                    return url, html
                                else:
                                    logger.warning(f"HTTP {response.status} for {url} via {proxy}")
                    else:
                        async with session.get(
                            url,
                            proxy=proxy,
                            timeout=aiohttp.ClientTimeout(total=self.timeout),
                            ssl=False
                        ) as response:
                            if response.status == 200:
                                html = await response.text()
                                logger.info(f"✓ Successfully fetched: {url}")
                                return url, html
                            else:
                                logger.warning(f"HTTP {response.status} for {url}")
                            
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed for {url}: {e}")
                    
                    # Mark proxy as failed
                    if proxy and self.proxy_manager:
                        self.proxy_manager.mark_failed(proxy)
                    
                    # Retry delay
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
            
            logger.error(f"✗ Failed to fetch after {self.max_retries} attempts: {url}")
            return url, None
    
    async def _process_url(
        self,
        session: aiohttp.ClientSession,
        url: str,
        semaphore: asyncio.Semaphore
    ) -> None:
        """Process một URL: fetch + parse + save"""
        url, html = await self._fetch_url(session, url, semaphore)
        
        if html:
            try:
                # Parse HTML
                data = self.parser(url, html)
                
                # Save to storage
                await self.storage.save(url, data)
                
                self.stats['success'] += 1
            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                self.stats['failed'] += 1
        else:
            self.stats['failed'] += 1
    
    async def _crawl_async(self) -> None:
        """Main async crawl logic"""
        # Fetch proxies nếu cần
        if self.use_proxy and self.proxy_manager:
            await self.proxy_manager.fetch_proxies()
            if not self.proxy_manager.proxies:
                logger.warning("No proxies available, continuing without proxy...")
                self.use_proxy = False
        
        # Semaphore để limit concurrent requests
        semaphore = asyncio.Semaphore(self.max_workers)
        
        # Custom connector với connection pooling
        connector = aiohttp.TCPConnector(limit=self.max_workers, limit_per_host=5)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            tasks = [
                self._process_url(session, url, semaphore)
                for url in self.urls
            ]
            
            # Sử dụng tqdm progress bar nếu enabled
            if self.show_progress:
                await async_tqdm.gather(
                    *tasks,
                    desc="Crawling URLs",
                    total=len(tasks),
                    unit="url"
                )
            else:
                await asyncio.gather(*tasks)

    async def _run(self):
        await self._crawl_async()
        await self.storage.finalize()
    
    def crawl(self) -> dict:
        """
        Bắt đầu crawl
        
        Returns:
            dict: Statistics về quá trình crawl
        """
        logger.info(f"Starting crawl of {len(self.urls)} URLs with {self.max_workers} workers...")
        
        self.stats['start_time'] = time.time()
        
        # # Run async crawl
        # asyncio.run(self._crawl_async())
        
        # # Finalize storage
        # asyncio.run(self.storage.finalize())
        asyncio.run(self._run())
        
        self.stats['end_time'] = time.time()
        self.stats['duration'] = round(self.stats['end_time'] - self.stats['start_time'], 2)
        
        logger.info(f"Crawl completed: {self.stats['success']} success, {self.stats['failed']} failed")
        logger.info(f"Duration: {self.stats['duration']}s")
        
        return self.stats
    
    def add_urls(self, urls: List[str]) -> None:
        """Thêm URLs vào danh sách crawl"""
        self.urls.extend(urls)
        self.stats['total'] = len(self.urls)
        logger.info(f"Added {len(urls)} URLs, total: {len(self.urls)}")
