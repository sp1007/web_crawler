# 🆕 Tính năng mới - Version 1.1.0

## 1. ✅ Proxy Management Nâng cao

### Auto-Refetch Proxies
Khi hết proxy available, hệ thống tự động fetch thêm proxy mới:

```python
from web_crawler import WebCrawler

crawler = WebCrawler(
    urls=urls,
    use_proxy=True  # Tự động refetch khi hết proxy
)

stats = crawler.crawl()
```

### Proxy Statistics
Xem thống kê proxy:

```python
from web_crawler import ProxyManager

proxy_mgr = ProxyManager()
await proxy_mgr.fetch_proxies()

stats = proxy_mgr.get_stats()
print(f"Total proxies: {stats['total']}")
print(f"Available: {stats['available']}")
print(f"Failed: {stats['failed']}")
print(f"Failure rate: {stats['failure_rate']:.2%}")
```

### Cơ chế hoạt động:
1. **Fetch initial proxies** khi bắt đầu crawl
2. **Mark failed** khi proxy không hoạt động
3. **Auto-refetch** khi hết proxy available
4. **Reset failed list** nếu vẫn không có proxy

## 2. 🔗 Chain Crawling - Multi-Step Crawling

Crawl theo chuỗi nhiều bước, ví dụ:
- **Step 1:** Category Page → Extract Product URLs
- **Step 2:** Product Pages → Extract Detail URLs
- **Step 3:** Detail Pages → Extract Final Data

### Basic Chain Crawling

```python
from web_crawler import ChainCrawler, ChainStep
from bs4 import BeautifulSoup

# Step 1: Parse và extract URLs
def step1_parser(url: str, html: str) -> dict:
    soup = BeautifulSoup(html, 'html.parser')
    links = [a['href'] for a in soup.find_all('a', href=True)]
    return {'links': links}

def step1_extract_urls(data: dict) -> list:
    return data['links'][:10]  # Top 10 links

# Step 2: Final parsing (no next URLs)
def step2_parser(url: str, html: str) -> dict:
    soup = BeautifulSoup(html, 'html.parser')
    return {
        'title': soup.title.string if soup.title else '',
        'content': soup.get_text()[:500]
    }

# Define chain
steps = [
    ChainStep(
        name="Extract Links",
        parser=step1_parser,
        extract_next_urls=step1_extract_urls
    ),
    ChainStep(
        name="Parse Content",
        parser=step2_parser,
        extract_next_urls=None  # Final step
    )
]

# Run chain
crawler = ChainCrawler(
    initial_urls=["https://example.com"],
    steps=steps,
    max_workers=5
)

stats = crawler.crawl()
```

### E-commerce 3-Step Chain Example

```python
# Step 1: Category → Product URLs
def category_parser(url: str, html: str) -> dict:
    soup = BeautifulSoup(html, 'html.parser')
    product_links = [a['href'] for a in soup.select('.product-link')]
    return {'product_links': product_links}

def extract_product_urls(data: dict) -> list:
    return data['product_links']

# Step 2: Product → Detail URL
def product_parser(url: str, html: str) -> dict:
    soup = BeautifulSoup(html, 'html.parser')
    detail_url = soup.select_one('.view-details')['href']
    return {
        'title': soup.select_one('h1').get_text(),
        'detail_url': detail_url
    }

def extract_detail_url(data: dict) -> list:
    return [data['detail_url']]

# Step 3: Detail → Final Data
def detail_parser(url: str, html: str) -> dict:
    soup = BeautifulSoup(html, 'html.parser')
    return {
        'title': soup.select_one('h1').get_text(),
        'price': soup.select_one('.price').get_text(),
        'description': soup.select_one('.description').get_text(),
        'images': [img['src'] for img in soup.select('.product-image')],
        'specs': {}  # Extract specifications
    }

# Define 3-step chain
steps = [
    ChainStep("Categories", category_parser, extract_product_urls),
    ChainStep("Products", product_parser, extract_detail_url),
    ChainStep("Details", detail_parser, None)  # Final
]

crawler = ChainCrawler(
    initial_urls=["https://shop.com/category/electronics"],
    steps=steps,
    storage=AggregatedStorage("products.json"),
    max_urls_per_step=50  # Limit URLs per step
)

stats = crawler.crawl()
```

### Chain Crawling Configuration

```python
crawler = ChainCrawler(
    initial_urls=urls,
    steps=steps,
    storage=storage,
    max_workers=8,          # Concurrent workers
    use_proxy=True,         # Use proxies
    timeout=30,             # Request timeout
    max_retries=3,          # Retry attempts
    retry_delay=2,          # Delay between retries
    max_urls_per_step=100   # Limit URLs per step (None = unlimited)
)
```

### Chain Statistics

```python
stats = crawler.crawl()

print(f"Total Requests: {stats['total_requests']}")
print(f"Successful: {stats['successful_requests']}")
print(f"Failed: {stats['failed_requests']}")
print(f"Final Results: {stats['final_results']}")

# Per-step stats
for step_name, step_stats in stats['step_stats'].items():
    print(f"\n{step_name}:")
    print(f"  Processed: {step_stats['urls_processed']}")
    print(f"  Succeeded: {step_stats['urls_succeeded']}")
    print(f"  Next URLs: {step_stats.get('next_urls_found', 'N/A')}")
```

## 3. 📊 Progress Bar - Visual Progress Tracking

Hiển thị thanh tiến độ real-time khi crawl để theo dõi tiến trình.

### Basic Usage

```python
from web_crawler import WebCrawler

# WITH progress bar (mặc định)
crawler = WebCrawler(
    urls=urls,
    show_progress=True  # Mặc định = True
)
crawler.crawl()

# Output:
# Crawling URLs: 100%|████████████| 50/50 [00:15<00:00, 3.33url/s]
```

### Without Progress Bar

```python
# Không hiện progress bar
crawler = WebCrawler(
    urls=urls,
    show_progress=False
)
crawler.crawl()
```

### Chain Crawler Progress

Progress bar cho từng step trong chain:

```python
from web_crawler import ChainCrawler, ChainStep

crawler = ChainCrawler(
    initial_urls=urls,
    steps=steps,
    show_progress=True  # Progress bar cho mỗi step
)
crawler.crawl()

# Output:
# Step 1: Extract Links: 100%|████████| 10/10 [00:05<00:00, 2.00url/s]
# Step 2: Parse Content:  100%|████████| 50/50 [00:15<00:00, 3.33url/s]
```

### Progress Information

Progress bar hiển thị:
- **Percentage**: % hoàn thành (0-100%)
- **Progress bar**: Visual representation
- **Current/Total**: Số URL đã crawl / Tổng số URL
- **Time elapsed**: Thời gian đã trôi qua
- **ETA**: Thời gian ước tính còn lại
- **Speed**: Số URLs/giây

### When to Use

**Use Progress Bar (show_progress=True) when:**
- Crawling nhiều URLs (>10)
- Muốn theo dõi tiến độ
- Run interactive/terminal
- Debugging performance issues

**Disable Progress Bar (show_progress=False) when:**
- Running trong production logs
- Crawling rất ít URLs (<5)
- Output cần clean (không có extra UI)
- Running trong cron jobs/background tasks

### Example

```python
# Large crawl với progress
urls = ["https://example.com"] * 100

crawler = WebCrawler(
    urls=urls,
    max_workers=10,
    show_progress=True
)

stats = crawler.crawl()
# Progress bar sẽ update real-time!
```

## 4. 📝 Use Cases

### Use Case 1: News Website
```
Step 1: Homepage → Extract article URLs
Step 2: Article pages → Extract full content
```

### Use Case 2: Job Board
```
Step 1: Job listings → Extract job URLs
Step 2: Job pages → Extract application URLs
Step 3: Application pages → Extract final details
```

### Use Case 3: Real Estate
```
Step 1: Search results → Extract property URLs
Step 2: Property pages → Extract photo gallery URLs
Step 3: Gallery pages → Extract high-res images
```

### Use Case 4: Academic Papers
```
Step 1: Search results → Extract paper URLs
Step 2: Paper pages → Extract PDF URLs
Step 3: PDF pages → Extract citations
```

## 4. 🎯 Best Practices

### Chain Crawling
1. **Start small**: Test với 1-2 URLs trước khi scale
2. **Use max_urls_per_step**: Tránh crawl quá nhiều URLs
3. **Validate data**: Check data ở mỗi step
4. **Handle errors**: Mỗi parser nên có error handling
5. **Log progress**: Monitor từng step

### Proxy Management
1. **Use quality proxies**: Free proxies không stable
2. **Monitor stats**: Check failure rate thường xuyên
3. **Add manual proxies**: Bổ sung proxy riêng
4. **Adjust retry**: Tăng max_retries nếu cần

### Error Handling
```python
def safe_parser(url: str, html: str) -> dict:
    try:
        soup = BeautifulSoup(html, 'html.parser')
        # Your parsing logic
        return {...}
    except Exception as e:
        logger.error(f"Parse error for {url}: {e}")
        return {
            'url': url,
            'error': str(e),
            'status': 'failed'
        }
```

## 5. 📊 Comparison

### Regular Crawler vs Chain Crawler

| Feature | WebCrawler | ChainCrawler |
|---------|------------|--------------|
| Use case | Single-step crawling | Multi-step crawling |
| URL source | Predefined list | Dynamic extraction |
| Complexity | Simple | Medium-High |
| Flexibility | High | Very High |
| Setup | Easy | Medium |

### When to use what?

**Use WebCrawler when:**
- Bạn có list URLs cố định
- Chỉ cần crawl 1 lần
- Data structure đơn giản

**Use ChainCrawler when:**
- URLs phụ thuộc vào data từ step trước
- Cần crawl nhiều level deep
- Data structure phức tạp
- Cần extract URLs động

## 6. 🔧 Advanced Configuration

### Custom Proxy Sources
```python
custom_sources = [
    "https://your-premium-proxy-api.com/list",
    "https://api.proxyscrape.com/v4/free-proxy-list/get?..."
]

crawler = ChainCrawler(
    initial_urls=urls,
    steps=steps,
    proxy_sources=custom_sources
)
```

### Manual Proxy Addition
```python
crawler = ChainCrawler(
    initial_urls=urls,
    steps=steps,
    use_proxy=True
)

# Add your own proxies
crawler.proxy_manager.add_proxies([
    "http://premium-proxy-1.com:8080",
    "http://premium-proxy-2.com:8080",
    "socks5://premium-proxy-3.com:1080"
])

crawler.crawl()
```

### Conditional Step Logic
```python
def conditional_extract(data: dict) -> list:
    """Only extract URLs if condition met"""
    if data.get('has_details'):
        return data['detail_urls']
    return []  # Skip next step

step = ChainStep(
    name="Conditional Step",
    parser=parser,
    extract_next_urls=conditional_extract
)
```

## 7. 📦 Complete Example

Xem file `example_chain_crawling.py` để có ví dụ đầy đủ về:
- Simple 2-step chain
- 3-step e-commerce chain
- News website crawling
- Real-world scenarios

## 8. 🐛 Troubleshooting

**Problem: Chain stops early**
- Check if extract_next_urls returns empty list
- Verify parser is extracting URLs correctly
- Check logs for errors

**Problem: Too many URLs in later steps**
- Use `max_urls_per_step` parameter
- Filter URLs in extract_next_urls function
- Add URL validation

**Problem: Proxies running out**
- System auto-refetches, but may take time
- Add manual proxies for better stability
- Increase retry_delay to reduce proxy burn

**Problem: Data not being saved**
- Ensure last step has `extract_next_urls=None`
- Check storage.finalize() is called
- Verify parser returns valid dict

## 9. 📚 Resources

- **example_chain_crawling.py**: Complete examples
- **USAGE_GUIDE.md**: Detailed usage guide
- **README.md**: API reference

---

**Version:** 1.1.0  
**Updated:** 2024-02-02  
**New Features:** Chain Crawling + Enhanced Proxy Management
