"""
Example 1: Sử dụng cơ bản với parser mặc định và AggregatedStorage
"""

import logging
from web_crawler import WebCrawler, AggregatedStorage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Danh sách URLs cần crawl
urls = [
    "https://example.com",
    "https://httpbin.org/html",
    "https://www.python.org",
    "https://docs.python.org/3/",
]

# Tạo crawler với cấu hình mặc định
crawler = WebCrawler(
    urls=urls,
    max_workers=5,
    use_proxy=True,  # Sử dụng proxy
    timeout=15
)

# Bắt đầu crawl
stats = crawler.crawl()

print("\n=== Crawl Statistics ===")
print(f"Total URLs: {stats['total']}")
print(f"Success: {stats['success']}")
print(f"Failed: {stats['failed']}")
print(f"Duration: {stats['duration']}s")
print(f"\nResults saved to: crawl_results.json")
