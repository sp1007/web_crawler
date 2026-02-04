"""
web_crawler package.
"""

import asyncio
import sys

def _set_windows_selector_policy() -> None:
    if not sys.platform.startswith('win'):
        return
    try:
        policy = asyncio.get_event_loop_policy()
        proactor_cls = getattr(asyncio, 'WindowsProactorEventLoopPolicy', None)
        selector_cls = getattr(asyncio, 'WindowsSelectorEventLoopPolicy', None)
        if proactor_cls and selector_cls and isinstance(policy, proactor_cls):
            asyncio.set_event_loop_policy(selector_cls())
    except Exception:
        pass

_set_windows_selector_policy()

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
