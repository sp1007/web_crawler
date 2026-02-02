"""
Storage Backends - Các cách lưu trữ dữ liệu crawl
"""

import json
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
from urllib.parse import urlparse
import hashlib

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract base class cho storage backend"""
    
    @abstractmethod
    async def save(self, url: str, data: Any) -> None:
        """Lưu dữ liệu"""
        pass
    
    @abstractmethod
    async def finalize(self) -> None:
        """Hoàn tất và đóng storage"""
        pass


class PerURLStorage(StorageBackend):
    """Lưu kết quả theo từng URL riêng biệt"""
    
    def __init__(self, output_dir: str = "crawl_results"):
        """
        Args:
            output_dir: Thư mục lưu kết quả
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.saved_count = 0
        
    def _url_to_filename(self, url: str) -> str:
        """Convert URL thành tên file an toàn"""
        # Lấy domain và path
        parsed = urlparse(url)
        domain = parsed.netloc.replace(':', '_')
        path = parsed.path.replace('/', '_')
        
        # Tạo hash để đảm bảo unique
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        
        filename = f"{domain}{path}_{url_hash}.json"
        # Loại bỏ ký tự không hợp lệ
        filename = "".join(c for c in filename if c.isalnum() or c in "._-")
        
        return filename
    
    async def save(self, url: str, data: Any) -> None:
        """Lưu dữ liệu của một URL"""
        filename = self._url_to_filename(url)
        filepath = os.path.join(self.output_dir, filename)
        
        output = {
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            self.saved_count += 1
            logger.debug(f"Saved data for {url} to {filename}")
        except Exception as e:
            logger.error(f"Failed to save data for {url}: {e}")
    
    async def finalize(self) -> None:
        """Hoàn tất"""
        logger.info(f"PerURLStorage: Saved {self.saved_count} files to {self.output_dir}")


class AggregatedStorage(StorageBackend):
    """Lưu tất cả kết quả vào một file duy nhất"""
    
    def __init__(self, output_file: str = "crawl_results.json"):
        """
        Args:
            output_file: Đường dẫn file output
        """
        self.output_file = output_file
        self.results: List[Dict[str, Any]] = []
        
    async def save(self, url: str, data: Any) -> None:
        """Thêm dữ liệu vào danh sách"""
        self.results.append({
            "url": url,
            "timestamp": datetime.now().isoformat(),
            "data": data
        })
        logger.debug(f"Added data for {url} to aggregated results")
    
    async def finalize(self) -> None:
        """Lưu tất cả kết quả vào file"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            logger.info(f"AggregatedStorage: Saved {len(self.results)} results to {self.output_file}")
        except Exception as e:
            logger.error(f"Failed to save aggregated results: {e}")


class MongoDBStorage(StorageBackend):
    """Lưu dữ liệu vào MongoDB Atlas"""
    
    def __init__(
        self,
        connection_string: str,
        database: str = "web_crawler",
        collection: str = "crawl_results"
    ):
        """
        Args:
            connection_string: MongoDB Atlas connection string
            database: Tên database
            collection: Tên collection
        """
        self.connection_string = connection_string
        self.database_name = database
        self.collection_name = collection
        self.client = None
        self.collection = None
        self.saved_count = 0
        
    async def _ensure_connected(self) -> None:
        """Đảm bảo kết nối MongoDB"""
        if self.client is None:
            try:
                from motor.motor_asyncio import AsyncIOMotorClient
                self.client = AsyncIOMotorClient(self.connection_string)
                self.collection = self.client[self.database_name][self.collection_name]
                logger.info(f"Connected to MongoDB: {self.database_name}.{self.collection_name}")
            except ImportError:
                raise ImportError(
                    "MongoDB storage requires 'motor' package. "
                    "Install with: pip install motor"
                )
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                raise
    
    async def save(self, url: str, data: Any) -> None:
        """Lưu dữ liệu vào MongoDB"""
        await self._ensure_connected()
        
        document = {
            "url": url,
            "timestamp": datetime.now(),
            "data": data
        }
        
        try:
            await self.collection.insert_one(document)
            self.saved_count += 1
            logger.debug(f"Saved data for {url} to MongoDB")
        except Exception as e:
            logger.error(f"Failed to save data for {url} to MongoDB: {e}")
    
    async def finalize(self) -> None:
        """Đóng kết nối MongoDB"""
        if self.client:
            self.client.close()
            logger.info(f"MongoDBStorage: Saved {self.saved_count} documents to MongoDB")
