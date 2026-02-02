"""
Chain Crawler - Crawl theo chuỗi (multi-step crawling)
Ví dụ: URL1 → URL2 → URL3 → Kết quả cuối cùng
"""

import aiohttp
import asyncio
from typing import List, Callable, Optional, Any, Dict
from bs4 import BeautifulSoup
import logging
from tqdm import tqdm

from .proxy_manager import ProxyManager
from .storage import StorageBackend, AggregatedStorage

logger = logging.getLogger(__name__)


class ChainStep:
    """Định nghĩa một bước trong chain"""
    
    def __init__(
        self,
        name: str,
        parser: Callable[[str, str], Any],
        extract_next_urls: Optional[Callable[[Any], List[str]]] = None
    ):
        """
        Args:
            name: Tên của step
            parser: Hàm parse HTML: (url, html) -> data
            extract_next_urls: Hàm extract URLs cho step tiếp theo: (data) -> List[url]
                              Nếu None, đây là step cuối cùng
        """
        self.name = name
        self.parser = parser
        self.extract_next_urls = extract_next_urls
        
    def is_final_step(self) -> bool:
        """Check xem có phải step cuối cùng không"""
        return self.extract_next_urls is None


class ChainCrawler:
    """
    Crawler cho multi-step crawling
    
    Example:
        Step 1: Load category page → extract product URLs
        Step 2: Load product pages → extract detail URLs  
        Step 3: Load detail pages → extract final data
    """
    
    def __init__(
        self,
        initial_urls: List[str],
        steps: List[ChainStep],
        storage: Optional[StorageBackend] = None,
        max_workers: int = 8,
        use_proxy: bool = True,
        proxy_sources: Optional[List[str]] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_delay: int = 2,
        max_urls_per_step: Optional[int] = None,
        show_progress: bool = True
    ):
        """
        Args:
            initial_urls: URLs bắt đầu (step 1)
            steps: List các ChainStep
            storage: Storage backend (chỉ lưu kết quả cuối cùng)
            max_workers: Concurrent workers
            use_proxy: Sử dụng proxy
            proxy_sources: Custom proxy sources
            timeout: Request timeout
            max_retries: Số lần retry
            retry_delay: Delay giữa retries
            max_urls_per_step: Giới hạn số URLs mỗi step (None = không giới hạn)
            show_progress: Hiển thị progress bar (mặc định: True)
        """
        self.initial_urls = initial_urls
        self.steps = steps
        self.storage = storage or AggregatedStorage()
        self.max_workers = max_workers
        self.use_proxy = use_proxy
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_urls_per_step = max_urls_per_step
        self.show_progress = show_progress
        
        self.proxy_manager = ProxyManager(custom_sources=proxy_sources) if use_proxy else None
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'steps_completed': 0,
            'final_results': 0,
            'step_stats': {}
        }
        
    async def _fetch_url(
        self,
        session: aiohttp.ClientSession,
        url: str,
        semaphore: asyncio.Semaphore
    ) -> tuple[str, Optional[str]]:
        """Fetch một URL với retry"""
        async with semaphore:
            for attempt in range(self.max_retries):
                proxy = None
                if self.use_proxy and self.proxy_manager:
                    proxy = await self.proxy_manager.get_proxy()
                
                try:
                    async with session.get(
                        url,
                        proxy=proxy,
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                        ssl=False
                    ) as response:
                        if response.status == 200:
                            html = await response.text()
                            logger.debug(f"✓ Fetched: {url}")
                            return url, html
                        else:
                            logger.warning(f"HTTP {response.status} for {url}")
                            
                except Exception as e:
                    logger.debug(f"Attempt {attempt + 1}/{self.max_retries} failed for {url}: {e}")
                    
                    if proxy and self.proxy_manager:
                        self.proxy_manager.mark_failed(proxy)
                    
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay)
            
            logger.warning(f"✗ Failed to fetch: {url}")
            return url, None
    
    async def _process_step(
        self,
        session: aiohttp.ClientSession,
        step: ChainStep,
        urls: List[str],
        semaphore: asyncio.Semaphore,
        step_index: int
    ) -> List[str]:
        """
        Process một step
        
        Returns:
            List URLs cho step tiếp theo (hoặc empty nếu là final step)
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Step {step_index + 1}/{len(self.steps)}: {step.name}")
        logger.info(f"Processing {len(urls)} URLs...")
        logger.info(f"{'='*60}")
        
        # Giới hạn URLs nếu cần
        if self.max_urls_per_step and len(urls) > self.max_urls_per_step:
            logger.warning(f"Limiting URLs from {len(urls)} to {self.max_urls_per_step}")
            urls = urls[:self.max_urls_per_step]
        
        # Stats cho step này
        step_stats = {
            'urls_processed': 0,
            'urls_succeeded': 0,
            'urls_failed': 0,
            'next_urls_found': 0
        }
        
        next_urls = []
        
        # Fetch và parse tất cả URLs trong step này
        urls_iter = tqdm(urls, desc=f"Step {step_index + 1}: {step.name}", unit="url") if self.show_progress else urls
        
        for url in urls_iter:
            self.stats['total_requests'] += 1
            step_stats['urls_processed'] += 1
            
            # Fetch URL
            _, html = await self._fetch_url(session, url, semaphore)
            
            if not html:
                self.stats['failed_requests'] += 1
                step_stats['urls_failed'] += 1
                continue
            
            self.stats['successful_requests'] += 1
            step_stats['urls_succeeded'] += 1
            
            try:
                # Parse HTML
                data = step.parser(url, html)
                
                # Nếu là final step, lưu kết quả
                if step.is_final_step():
                    await self.storage.save(url, data)
                    self.stats['final_results'] += 1
                    logger.info(f"  ✓ Saved final result from: {url}")
                else:
                    # Extract URLs cho step tiếp theo
                    new_urls = step.extract_next_urls(data)
                    if new_urls:
                        next_urls.extend(new_urls)
                        step_stats['next_urls_found'] += len(new_urls)
                        logger.info(f"  ✓ Found {len(new_urls)} URLs from: {url}")
                    
            except Exception as e:
                logger.error(f"  ✗ Error processing {url}: {e}")
                step_stats['urls_failed'] += 1
        
        # Lưu stats
        self.stats['step_stats'][step.name] = step_stats
        self.stats['steps_completed'] += 1
        
        # Log step summary
        logger.info(f"\nStep {step_index + 1} Summary:")
        logger.info(f"  Processed: {step_stats['urls_processed']}")
        logger.info(f"  Succeeded: {step_stats['urls_succeeded']}")
        logger.info(f"  Failed: {step_stats['urls_failed']}")
        if not step.is_final_step():
            logger.info(f"  Next URLs: {step_stats['next_urls_found']}")
        
        # Remove duplicates
        if next_urls:
            next_urls = list(set(next_urls))
            logger.info(f"  Unique next URLs: {len(next_urls)}")
        
        return next_urls
    
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
        
        # Connector
        connector = aiohttp.TCPConnector(limit=self.max_workers, limit_per_host=5)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            current_urls = self.initial_urls
            
            # Process từng step
            for step_index, step in enumerate(self.steps):
                if not current_urls:
                    logger.warning(f"No URLs to process for step {step_index + 1}. Stopping.")
                    break
                
                # Process step
                current_urls = await self._process_step(
                    session, step, current_urls, semaphore, step_index
                )
                
                # Nếu là final step, không cần tiếp tục
                if step.is_final_step():
                    break
    
    def crawl(self) -> Dict[str, Any]:
        """
        Bắt đầu chain crawl
        
        Returns:
            Dict chứa statistics
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"Starting Chain Crawl")
        logger.info(f"  Initial URLs: {len(self.initial_urls)}")
        logger.info(f"  Steps: {len(self.steps)}")
        logger.info(f"  Workers: {self.max_workers}")
        logger.info(f"{'='*80}")
        
        # Run async crawl
        asyncio.run(self._crawl_async())
        
        # Finalize storage
        asyncio.run(self.storage.finalize())
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Chain Crawl Completed")
        logger.info(f"  Total Requests: {self.stats['total_requests']}")
        logger.info(f"  Successful: {self.stats['successful_requests']}")
        logger.info(f"  Failed: {self.stats['failed_requests']}")
        logger.info(f"  Final Results: {self.stats['final_results']}")
        logger.info(f"{'='*80}")
        
        return self.stats
