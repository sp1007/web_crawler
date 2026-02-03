"""
web_crawler package.
"""

from .crawler import WebCrawler
from .chain_crawler import ChainCrawler, ChainStep
from .proxy_manager import ProxyManager
from .storage import AggregatedStorage, JSONLStorage, MongoDBStorage, PerURLStorage, StorageBackend

__version__ = "1.2.0"

__all__ = [
    "WebCrawler",
    "ChainCrawler",
    "ChainStep",
    "ProxyManager",
    "StorageBackend",
    "PerURLStorage",
    "AggregatedStorage",
    "JSONLStorage",
    "MongoDBStorage",
]
