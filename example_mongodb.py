"""
Example 3: Lưu dữ liệu vào MongoDB Atlas
"""

import logging
from web_crawler import WebCrawler, MongoDBStorage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# MongoDB connection string (thay thế bằng connection string thực tế)
MONGODB_URI = "mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority"

# URLs để crawl
urls = [
    "https://example.com",
    "https://httpbin.org/html",
    "https://www.python.org",
]

# Tạo MongoDB storage
storage = MongoDBStorage(
    connection_string=MONGODB_URI,
    database="web_crawler_db",
    collection="crawled_pages"
)

# Tạo crawler
crawler = WebCrawler(
    urls=urls,
    storage=storage,  # Sử dụng MongoDB storage
    max_workers=5,
    use_proxy=True
)

# Crawl
stats = crawler.crawl()

print("\n=== Crawl Statistics ===")
print(f"Total URLs: {stats['total']}")
print(f"Success: {stats['success']}")
print(f"Failed: {stats['failed']}")
print(f"Duration: {stats['duration']}s")
print(f"\nResults saved to MongoDB")
