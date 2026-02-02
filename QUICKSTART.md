# 🚀 QUICKSTART - Bắt đầu trong 5 phút

## Bước 1: Cài đặt

```bash
# Copy package vào project của bạn
cd /path/to/your/project
cp -r web_crawler .

# Cài đặt dependencies
pip install -r web_crawler/requirements.txt
```

## Bước 2: Sử dụng ngay

### Option A: Crawl đơn giản nhất

```python
from web_crawler import WebCrawler

# Danh sách URLs
urls = [
    "https://example.com",
    "https://python.org",
]

# Tạo crawler và chạy
crawler = WebCrawler(urls=urls, use_proxy=False)
stats = crawler.crawl()

print(f"✓ Crawled {stats['success']} pages successfully!")
print(f"✓ Results saved to: crawl_results.json")
```

### Option B: Với custom parser

```python
from web_crawler import WebCrawler
from bs4 import BeautifulSoup

def my_parser(url: str, html: str) -> dict:
    soup = BeautifulSoup(html, 'html.parser')
    return {
        'title': soup.title.string if soup.title else '',
        'links': [a['href'] for a in soup.find_all('a', href=True)[:10]]
    }

urls = ["https://example.com"]
crawler = WebCrawler(urls=urls, parser=my_parser)
crawler.crawl()
```

### Option C: Lưu từng file riêng

```python
from web_crawler import WebCrawler, PerURLStorage

urls = ["https://example.com", "https://python.org"]

storage = PerURLStorage(output_dir="my_results")
crawler = WebCrawler(urls=urls, storage=storage)
crawler.crawl()

# Results in: my_results/
```

### Option D: Lưu vào MongoDB

```python
from web_crawler import WebCrawler, MongoDBStorage

# Thay connection string của bạn
MONGODB_URI = "mongodb+srv://user:pass@cluster.mongodb.net/"

storage = MongoDBStorage(
    connection_string=MONGODB_URI,
    database="my_db",
    collection="crawled_data"
)

urls = ["https://example.com"]
crawler = WebCrawler(urls=urls, storage=storage)
crawler.crawl()
```

## Bước 3: Chạy examples

```bash
cd web_crawler

# Example 1: Basic
python example_basic.py

# Example 2: Custom Parser
python example_custom_parser.py

# Example 3: Advanced
python example_advanced.py

# Quick Test
python test_quick.py

# Full Demo
python demo_comprehensive.py
```

## Common Tasks

### Task 1: Crawl với proxy
```python
crawler = WebCrawler(
    urls=urls,
    use_proxy=True  # Tự động lấy proxy miễn phí
)
```

### Task 2: Crawl nhanh
```python
crawler = WebCrawler(
    urls=urls,
    max_workers=20,  # Nhiều workers
    timeout=10,      # Timeout ngắn
    use_proxy=False
)
```

### Task 3: Crawl an toàn
```python
crawler = WebCrawler(
    urls=urls,
    max_workers=3,   # Ít workers
    timeout=60,      # Timeout dài
    max_retries=5,   # Retry nhiều
    use_proxy=True
)
```

## Configuration Reference

| Parameter | Default | Mô tả |
|-----------|---------|-------|
| `urls` | Required | List URLs cần crawl |
| `parser` | Default | Hàm parse: `(url, html) -> dict` |
| `storage` | Aggregated | Storage backend |
| `max_workers` | 8 | Concurrent workers |
| `use_proxy` | True | Dùng proxy hay không |
| `timeout` | 30 | Timeout (seconds) |
| `max_retries` | 3 | Số lần retry |
| `retry_delay` | 2 | Delay giữa retries |

## Troubleshooting

**Problem: Bị timeout**
```python
crawler = WebCrawler(urls=urls, timeout=60)
```

**Problem: Bị block IP**
```python
crawler = WebCrawler(urls=urls, use_proxy=True)
```

**Problem: Parser lỗi**
```python
def safe_parser(url, html):
    try:
        # your logic
        return {...}
    except Exception as e:
        return {'error': str(e)}
```

## Đọc thêm

- **README.md**: Overview và API reference
- **USAGE_GUIDE.md**: Hướng dẫn chi tiết và use cases
- **PROJECT_STRUCTURE.md**: Cấu trúc project
- **examples/*.py**: Example scripts

## Support

Có vấn đề? Check:
1. README.md
2. USAGE_GUIDE.md  
3. Examples trong thư mục web_crawler/

---

**Happy Crawling! 🕷️**
