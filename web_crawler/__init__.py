"""
Web Crawler Package - Async web scraping với aiohttp
Hỗ trợ proxy rotation, multi-threading, chain crawling và nhiều storage backends
"""

from .crawler import WebCrawler
from .chain_crawler import ChainCrawler, ChainStep
from .proxy_manager import ProxyManager
from .storage import (
    StorageBackend,
    PerURLStorage,
    AggregatedStorage,
    MongoDBStorage
)

__version__ = "1.0.0"
__all__ = [
    "WebCrawler",
    "ChainCrawler",
    "ChainStep",
    "ProxyManager",
    "StorageBackend",
    "PerURLStorage",
    "AggregatedStorage",
    "MongoDBStorage"
]
