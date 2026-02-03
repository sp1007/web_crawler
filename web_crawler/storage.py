"""
Storage backends for crawl results.

All backends implement:
- save(url, data)
- finalize()
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, url: str, data: Any) -> None:
        raise NotImplementedError

    @abstractmethod
    async def finalize(self) -> None:
        raise NotImplementedError


class PerURLStorage(StorageBackend):
    """
    Save one JSON file per URL.
    """

    def __init__(self, output_dir: str = "crawl_results") -> None:
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.saved_count = 0

    def _url_to_filename(self, url: str) -> str:
        parsed = urlparse(url)
        domain = parsed.netloc.replace(":", "_")
        path = parsed.path.replace("/", "_")
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]

        filename = f"{domain}{path}_{url_hash}.json"
        filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        return filename

    async def save(self, url: str, data: Any) -> None:
        filename = self._url_to_filename(url)
        filepath = os.path.join(self.output_dir, filename)

        output = {"url": url, "timestamp": datetime.now().isoformat(), "data": data}

        def _write() -> None:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(output, f, ensure_ascii=False, indent=2)

        try:
            await asyncio.to_thread(_write)
            self.saved_count += 1
        except Exception as e:
            logger.exception("Failed to save data for %s: %s", url, e)

    async def finalize(self) -> None:
        logger.info("PerURLStorage: saved %s files to %s", self.saved_count, self.output_dir)


class AggregatedStorage(StorageBackend):
    """
    Keep all results in memory and write a single JSON array on finalize().

    For very large crawls, consider JSONLStorage instead to avoid RAM growth.
    """

    def __init__(self, output_file: str = "crawl_results.json") -> None:
        self.output_file = output_file
        self.results: list[dict[str, Any]] = []

    async def save(self, url: str, data: Any) -> None:
        self.results.append({"url": url, "timestamp": datetime.now().isoformat(), "data": data})

    async def finalize(self) -> None:
        def _write() -> None:
            with open(self.output_file, "w", encoding="utf-8") as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)

        try:
            await asyncio.to_thread(_write)
            logger.info("AggregatedStorage: saved %s results to %s", len(self.results), self.output_file)
        except Exception as e:
            logger.exception("Failed to save aggregated results: %s", e)


class JSONLStorage(StorageBackend):
    """
    Streaming storage: write one JSON object per line (JSON Lines).

    This is the recommended backend for very large crawls.
    """

    def __init__(
        self,
        output_file: str = "crawl_results.jsonl",
        *,
        flush_every: int = 100,
    ) -> None:
        self.output_file = output_file
        self.flush_every = max(1, int(flush_every))

        self._lock = asyncio.Lock()
        self._file: Optional[Any] = None
        self._pending = 0
        self.saved_count = 0

    def _ensure_open(self) -> Any:
        if self._file is None:
            os.makedirs(os.path.dirname(self.output_file) or ".", exist_ok=True)
            self._file = open(self.output_file, "a", encoding="utf-8")
        return self._file

    async def save(self, url: str, data: Any) -> None:
        record = {"url": url, "timestamp": datetime.now().isoformat(), "data": data}
        line = json.dumps(record, ensure_ascii=False) + "\n"

        async with self._lock:
            f = self._ensure_open()
            f.write(line)
            self.saved_count += 1
            self._pending += 1
            if self._pending >= self.flush_every:
                f.flush()
                self._pending = 0

    async def finalize(self) -> None:
        async with self._lock:
            f = self._file
            self._file = None
        if f is None:
            return
        try:
            f.flush()
        finally:
            f.close()
        logger.info("JSONLStorage: saved %s records to %s", self.saved_count, self.output_file)


class MongoDBStorage(StorageBackend):
    """
    Save results to MongoDB (Atlas or self-hosted).

    Requires: motor
    """

    def __init__(
        self,
        connection_string: str,
        database: str = "web_crawler",
        collection: str = "crawl_results",
    ) -> None:
        self.connection_string = connection_string
        self.database_name = database
        self.collection_name = collection
        self.client = None
        self.collection = None
        self.saved_count = 0

    async def _ensure_connected(self) -> None:
        if self.client is not None:
            return
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
        except ImportError as e:
            raise ImportError("MongoDB storage requires 'motor'. Install with: pip install motor") from e

        self.client = AsyncIOMotorClient(self.connection_string)
        self.collection = self.client[self.database_name][self.collection_name]
        logger.info("Connected to MongoDB: %s.%s", self.database_name, self.collection_name)

    async def save(self, url: str, data: Any) -> None:
        await self._ensure_connected()
        assert self.collection is not None

        document = {"url": url, "timestamp": datetime.now(), "data": data}
        try:
            await self.collection.insert_one(document)
            self.saved_count += 1
        except Exception as e:
            logger.exception("Failed to save data for %s to MongoDB: %s", url, e)

    async def finalize(self) -> None:
        if self.client:
            self.client.close()
            logger.info("MongoDBStorage: saved %s documents", self.saved_count)

