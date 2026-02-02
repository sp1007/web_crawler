# Web Crawler Package

Package Python mạnh mẽ để crawl dữ liệu web với hỗ trợ async, proxy rotation, và nhiều storage backends.

## 🌟 Tính năng

- ✅ **Async I/O** với aiohttp để crawl nhanh
- ✅ **Multi-threading** có thể điều chỉnh (mặc định 8 workers)
- ✅ **Proxy Rotation** tự động lấy proxy từ các nguồn miễn phí + auto-refetch
- ✅ **Progress Bar** 📊 NEW - Thanh tiến độ real-time với tqdm
- ✅ **Chain Crawling** ⭐ NEW - Crawl theo chuỗi nhiều bước (URL1 → URL2 → URL3)
- ✅ **Custom Parser** để xử lý HTML theo ý muốn
- ✅ **3 Storage Backends**:
  - Per-URL Storage (lưu từng file riêng)
  - Aggregated Storage (lưu tất cả vào 1 file)
  - MongoDB Atlas (lưu vào database)
- ✅ **Retry Logic** với backoff
- ✅ **Logging** chi tiết
- ✅ **Statistics** tracking

## 📦 Cài đặt

```bash
# Clone hoặc copy package vào project của bạn
cd your_project
cp -r web_crawler .

# Cài đặt dependencies
pip install -r web_crawler/requirements.txt
```

### Dependencies

```
aiohttp>=3.9.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
motor>=3.3.0  # Optional: chỉ cần nếu dùng MongoDB
```

## 🚀 Sử dụng nhanh

### 1. Sử dụng cơ bản

```python
from web_crawler import WebCrawler

urls = [
    "https://example.com",
    "https://python.org",
]

crawler = WebCrawler(urls=urls)
stats = crawler.crawl()

print(f"Success: {stats['success']}/{stats['total']}")
```

### 2. Custom Parser

```python
from web_crawler import WebCrawler, PerURLStorage
from bs4 import BeautifulSoup

def my_parser(url: str, html: str) -> dict:
    """Parse HTML và trả về data bạn muốn"""
    soup = BeautifulSoup(html, 'html.parser')
    
    return {
        'title': soup.title.string if soup.title else '',
        'headings': [h.get_text() for h in soup.find_all(['h1', 'h2'])],
        'links': [a['href'] for a in soup.find_all('a', href=True)]
    }

crawler = WebCrawler(
    urls=urls,
    parser=my_parser,
    storage=PerURLStorage(output_dir="my_results")
)

crawler.crawl()
```

### 3. Lưu vào MongoDB

```python
from web_crawler import WebCrawler, MongoDBStorage

storage = MongoDBStorage(
    connection_string="mongodb+srv://user:pass@cluster.mongodb.net/",
    database="my_db",
    collection="crawled_data"
)

crawler = WebCrawler(
    urls=urls,
    storage=storage
)

crawler.crawl()
```

### 4. Chain Crawling ⭐ NEW

Crawl theo chuỗi nhiều bước (ví dụ: Category → Products → Details):

```python
from web_crawler import ChainCrawler, ChainStep
from bs4 import BeautifulSoup

# Step 1: Extract product URLs from category
def step1_parser(url, html):
    soup = BeautifulSoup(html, 'html.parser')
    return {'links': [a['href'] for a in soup.find_all('a', class_='product')]}

def step1_extract(data):
    return data['links']

# Step 2: Extract final data from products
def step2_parser(url, html):
    soup = BeautifulSoup(html, 'html.parser')
    return {
        'title': soup.find('h1').get_text(),
        'price': soup.find('span', class_='price').get_text()
    }

# Define chain
steps = [
    ChainStep("Get Products", step1_parser, step1_extract),
    ChainStep("Parse Products", step2_parser, None)  # Final step
]

# Run chain
crawler = ChainCrawler(
    initial_urls=["https://shop.com/category/electronics"],
    steps=steps
)
crawler.crawl()
```

## 📚 Chi tiết API

### WebCrawler

Constructor parameters:

| Parameter | Type | Default | Mô tả |
|-----------|------|---------|-------|
| `urls` | `List[str]` | Required | Danh sách URLs cần crawl |
| `parser` | `Callable` | Default parser | Hàm parse HTML: `(url, html) -> data` |
| `storage` | `StorageBackend` | `AggregatedStorage()` | Backend lưu trữ |
| `max_workers` | `int` | `8` | Số concurrent workers |
| `use_proxy` | `bool` | `True` | Sử dụng proxy hay không |
| `proxy_sources` | `List[str]` | Default sources | Custom proxy sources |
| `timeout` | `int` | `30` | Timeout mỗi request (seconds) |
| `max_retries` | `int` | `3` | Số lần retry khi fail |
| `retry_delay` | `int` | `2` | Delay giữa các retry (seconds) |

Methods:

```python
crawler.crawl() -> dict  # Bắt đầu crawl, trả về statistics
crawler.add_urls(urls: List[str])  # Thêm URLs vào danh sách
```

### Storage Backends

#### PerURLStorage

Lưu mỗi URL thành một file JSON riêng.

```python
from web_crawler import PerURLStorage

storage = PerURLStorage(output_dir="results")
```

Output structure:
```
results/
  ├── example.com_abc123.json
  ├── python.org_def456.json
  └── ...
```

#### AggregatedStorage

Lưu tất cả kết quả vào một file JSON.

```python
from web_crawler import AggregatedStorage

storage = AggregatedStorage(output_file="all_results.json")
```

Output structure:
```json
[
  {
    "url": "https://example.com",
    "timestamp": "2024-01-01T12:00:00",
    "data": { ... }
  },
  ...
]
```

#### MongoDBStorage

Lưu vào MongoDB Atlas (hoặc MongoDB bất kỳ).

```python
from web_crawler import MongoDBStorage

storage = MongoDBStorage(
    connection_string="mongodb+srv://...",
    database="web_crawler",
    collection="results"
)
```

### ProxyManager

Quản lý proxy tự động.

```python
from web_crawler import ProxyManager

proxy_manager = ProxyManager(
    custom_sources=[
        "https://api.proxyscrape.com/...",
        "https://custom-proxy-source.com/..."
    ]
)

# Lấy proxy
await proxy_manager.fetch_proxies()

# Get random proxy
proxy = proxy_manager.get_proxy()

# Mark proxy as failed
proxy_manager.mark_failed(proxy)

# Add manual proxies
proxy_manager.add_proxies([
    "http://proxy1.com:8080",
    "http://proxy2.com:8080"
])
```

## 🎯 Examples

Package đi kèm với 4 example files:

1. **example_basic.py** - Sử dụng cơ bản
2. **example_custom_parser.py** - Custom parser để extract dữ liệu cụ thể
3. **example_mongodb.py** - Lưu vào MongoDB
4. **example_advanced.py** - Kết hợp tất cả tính năng

Chạy examples:

```bash
cd web_crawler
python example_basic.py
python example_custom_parser.py
python example_advanced.py
```

## 📊 Statistics

Mỗi lần crawl trả về statistics:

```python
{
    'total': 100,          # Tổng số URLs
    'success': 95,         # Số URLs crawl thành công
    'failed': 5,           # Số URLs thất bại
    'start_time': 1234,    # Timestamp bắt đầu
    'end_time': 1256,      # Timestamp kết thúc
    'duration': 22.5       # Thời gian (seconds)
}
```

## 🔧 Cấu hình Proxy

Package tự động lấy proxy từ các nguồn miễn phí:

- ProxyScrape API
- Có thể thêm nguồn custom

Hoặc thêm proxy thủ công:

```python
crawler = WebCrawler(urls=urls, use_proxy=True)

# Thêm proxy của bạn
crawler.proxy_manager.add_proxies([
    "http://your-proxy-1.com:8080",
    "http://your-proxy-2.com:8080",
    "socks5://your-proxy-3.com:1080"
])

crawler.crawl()
```

## 📝 Logging

Enable logging để theo dõi quá trình crawl:

```python
import logging

logging.basicConfig(
    level=logging.INFO,  # hoặc DEBUG để xem chi tiết hơn
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## ⚙️ Best Practices

### 1. Tuning Performance

```python
# Cho nhiều URLs (1000+)
crawler = WebCrawler(
    urls=urls,
    max_workers=20,  # Tăng workers
    timeout=15,      # Giảm timeout
    max_retries=2    # Giảm retries
)

# Cho ít URLs nhưng cần chính xác
crawler = WebCrawler(
    urls=urls,
    max_workers=5,   # Ít workers hơn
    timeout=60,      # Timeout dài hơn
    max_retries=5    # Nhiều retries hơn
)
```

### 2. Custom Parser Tips

```python
def efficient_parser(url: str, html: str) -> dict:
    """Parser hiệu quả"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Chỉ extract những gì cần thiết
    data = {
        'title': soup.title.string if soup.title else '',
    }
    
    # Sử dụng CSS selectors để nhanh hơn
    products = soup.select('.product-item')
    data['products'] = [p.get_text() for p in products[:10]]
    
    return data
```

### 3. Error Handling

```python
def safe_parser(url: str, html: str) -> dict:
    """Parser với error handling"""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Your parsing logic
        return {'title': soup.title.string}
        
    except Exception as e:
        logging.error(f"Parse error for {url}: {e}")
        return {'error': str(e)}
```

## 🔒 Lưu ý

- **Proxy miễn phí** có thể không ổn định, nên chuẩn bị proxy riêng cho production
- **Respect robots.txt** và terms of service của các websites
- **Rate limiting**: Điều chỉnh `max_workers` phù hợp để tránh overload
- **MongoDB**: Cần cài `motor` package riêng

## 📄 License

MIT License - Free to use and modify

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Support

Nếu có vấn đề, hãy tạo issue hoặc liên hệ support.
