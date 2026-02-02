# Web Crawler Package - Cấu trúc Project

## Tổng quan cấu trúc

```
web_crawler/
│
├── __init__.py                 # Package initialization
├── crawler.py                  # Main crawler class
├── proxy_manager.py            # Proxy management
├── storage.py                  # Storage backends
│
├── requirements.txt            # Dependencies
├── setup.py                    # Package setup
├── LICENSE                     # MIT License
├── .gitignore                  # Git ignore file
│
├── README.md                   # Overview và quickstart
├── USAGE_GUIDE.md             # Hướng dẫn chi tiết
├── PROJECT_STRUCTURE.md       # File này
│
├── example_basic.py           # Example 1: Basic usage
├── example_custom_parser.py   # Example 2: Custom parser
├── example_mongodb.py         # Example 3: MongoDB storage
├── example_advanced.py        # Example 4: Advanced features
│
├── test_quick.py              # Quick test script
└── demo_comprehensive.py      # Comprehensive demo
```

## Chi tiết từng file

### Core Package Files

#### `__init__.py`
- Export các class chính: WebCrawler, ProxyManager, Storage classes
- Version info
- Package metadata

#### `crawler.py`
- **Class: WebCrawler**
  - Main crawler logic
  - Async crawling với aiohttp
  - Retry mechanism
  - Statistics tracking
- **Methods:**
  - `__init__()`: Constructor với config
  - `crawl()`: Bắt đầu crawl
  - `add_urls()`: Thêm URLs
  - `_fetch_url()`: Fetch một URL
  - `_process_url()`: Process URL (fetch + parse + save)
  - `_crawl_async()`: Main async logic

#### `proxy_manager.py`
- **Class: ProxyManager**
  - Quản lý proxy list
  - Auto fetch từ proxy sources
  - Proxy rotation
  - Failed proxy tracking
- **Methods:**
  - `fetch_proxies()`: Fetch proxy từ sources
  - `get_proxy()`: Lấy random proxy
  - `mark_failed()`: Đánh dấu proxy failed
  - `add_proxies()`: Thêm proxy thủ công

#### `storage.py`
- **Class: StorageBackend** (Abstract)
  - Base class cho storage
  - Methods: `save()`, `finalize()`

- **Class: PerURLStorage**
  - Lưu từng URL thành file riêng
  - Methods: `save()`, `finalize()`, `_url_to_filename()`

- **Class: AggregatedStorage**
  - Lưu tất cả vào 1 file JSON
  - Methods: `save()`, `finalize()`

- **Class: MongoDBStorage**
  - Lưu vào MongoDB
  - Requires: motor package
  - Methods: `save()`, `finalize()`, `_ensure_connected()`

### Configuration Files

#### `requirements.txt`
Dependencies cần thiết:
- aiohttp: Async HTTP client
- beautifulsoup4: HTML parsing
- lxml: XML/HTML parser
- motor: MongoDB async driver (optional)

#### `setup.py`
- Package installation config
- Metadata
- Dependencies
- Entry points

### Documentation

#### `README.md`
- Package overview
- Features list
- Quick installation
- Basic usage examples
- API reference
- Storage backends explanation

#### `USAGE_GUIDE.md`
- Detailed usage guide
- Use cases
- Troubleshooting
- Performance tuning
- Best practices
- Advanced topics

#### `PROJECT_STRUCTURE.md`
- This file
- Project structure explanation
- File descriptions

### Examples

#### `example_basic.py`
- Simplest usage
- Default parser
- AggregatedStorage
- No proxy

#### `example_custom_parser.py`
- Custom parser function
- PerURLStorage
- Extract specific data

#### `example_mongodb.py`
- MongoDB storage
- Connection setup
- Production-ready example

#### `example_advanced.py`
- All features combined
- Advanced parser
- Custom config
- Performance optimization

### Testing & Demo

#### `test_quick.py`
- Quick functionality test
- 3 test scenarios
- Verify basic operations

#### `demo_comprehensive.py`
- Complete feature showcase
- 6 demo scenarios
- Comparison tests

## Workflow cơ bản

```
1. User tạo WebCrawler với config
   ├── Chọn parser (custom hoặc default)
   ├── Chọn storage backend
   └── Set parameters (workers, timeout, etc.)

2. User gọi crawler.crawl()
   ├── ProxyManager fetch proxies (nếu enabled)
   ├── Tạo async tasks cho từng URL
   │   ├── Fetch URL với retry
   │   ├── Parse HTML với parser
   │   └── Save data với storage
   └── Finalize storage

3. Return statistics
   ├── Success count
   ├── Failed count
   └── Duration
```

## Dependencies Graph

```
WebCrawler
├── depends on: ProxyManager (optional)
├── depends on: StorageBackend (required)
└── uses: aiohttp, asyncio

ProxyManager
├── uses: aiohttp
└── uses: BeautifulSoup

Storage Backends
├── PerURLStorage: uses json, os
├── AggregatedStorage: uses json
└── MongoDBStorage: uses motor
```

## Extension Points

### 1. Custom Parser
```python
def my_parser(url: str, html: str) -> dict:
    # Your logic
    return data
```

### 2. Custom Storage
```python
class MyStorage(StorageBackend):
    async def save(self, url, data):
        # Your logic
        pass
    
    async def finalize(self):
        # Cleanup
        pass
```

### 3. Custom Proxy Sources
```python
proxy_sources = [
    "https://your-api.com/proxies",
    "https://another-source.com/list"
]
crawler = WebCrawler(urls, proxy_sources=proxy_sources)
```

## Data Flow

```
URLs → WebCrawler → ProxyManager (optional)
                  ↓
              aiohttp fetch
                  ↓
              HTML content
                  ↓
              Parser function
                  ↓
              Structured data
                  ↓
              Storage Backend
                  ↓
         Files / MongoDB / Custom
```

## Best Practices for Extension

1. **Custom Parser:**
   - Luôn return dict
   - Handle exceptions internally
   - Log errors
   - Return meaningful data structure

2. **Custom Storage:**
   - Inherit from StorageBackend
   - Implement both save() and finalize()
   - Handle async operations properly
   - Close connections in finalize()

3. **Performance:**
   - Tune max_workers based on use case
   - Use appropriate timeout values
   - Consider retry strategy
   - Monitor success rate

4. **Production:**
   - Use quality proxies
   - Implement proper error handling
   - Add monitoring
   - Use MongoDB for large scale
   - Respect rate limits

## Version History

### v1.0.0 (Current)
- Initial release
- Async crawling with aiohttp
- Proxy rotation
- 3 storage backends
- Custom parser support
- Retry mechanism
- Statistics tracking

## Future Enhancements

Possible future features:
- [ ] Distributed crawling
- [ ] Redis cache support
- [ ] Selenium integration for JS-heavy sites
- [ ] Rate limiting per domain
- [ ] Robots.txt checking
- [ ] Sitemap parsing
- [ ] Crawl scheduling
- [ ] Web dashboard for monitoring

---

**Package maintained by:** Your Name
**Last updated:** 2024-02-02
