# Quick Reference Card

## 🚀 Installation
```bash
pip install -r requirements.txt
```

## 📖 Basic Usage

### Simple Crawl
```python
from web_crawler import WebCrawler
crawler = WebCrawler(urls=["https://example.com"])
crawler.crawl()
```

### With Custom Parser
```python
def parser(url, html):
    soup = BeautifulSoup(html, 'html.parser')
    return {'title': soup.title.string}

crawler = WebCrawler(urls=urls, parser=parser)
```

### Chain Crawling
```python
from web_crawler import ChainCrawler, ChainStep

steps = [
    ChainStep("Step1", parser1, extract_urls),
    ChainStep("Step2", parser2, None)  # Final
]
crawler = ChainCrawler(initial_urls=urls, steps=steps)
```

## 🔧 Configuration

### WebCrawler
| Parameter | Default | Description |
|-----------|---------|-------------|
| urls | Required | List of URLs |
| parser | Default | Parse function |
| storage | Aggregated | Storage backend |
| max_workers | 8 | Concurrent workers |
| use_proxy | True | Use proxies |
| timeout | 30 | Request timeout |
| max_retries | 3 | Retry attempts |
| show_progress | True | Show progress bar |

### ChainCrawler
| Parameter | Default | Description |
|-----------|---------|-------------|
| initial_urls | Required | Starting URLs |
| steps | Required | List of ChainStep |
| max_urls_per_step | None | URL limit per step |
| (others) | Same as WebCrawler | Same configs |

## 💾 Storage Backends

### Per-URL Storage
```python
from web_crawler import PerURLStorage
storage = PerURLStorage(output_dir="results")
```

### Aggregated Storage
```python
from web_crawler import AggregatedStorage
storage = AggregatedStorage(output_file="results.json")
```

### MongoDB Storage
```python
from web_crawler import MongoDBStorage
storage = MongoDBStorage(
    connection_string="mongodb+srv://...",
    database="db",
    collection="collection"
)
```

## 🔗 Chain Steps

### Define Step
```python
from web_crawler import ChainStep

step = ChainStep(
    name="Step Name",
    parser=parser_function,
    extract_next_urls=extract_function  # None for final step
)
```

### Parser Function
```python
def parser(url: str, html: str) -> dict:
    # Parse HTML
    return {...}
```

### Extract URLs Function
```python
def extract_urls(data: dict) -> list:
    # Extract URLs from data
    return [url1, url2, ...]
```

## 📊 Progress Bar

### Enable/Disable
```python
# With progress bar (default)
crawler = WebCrawler(urls=urls, show_progress=True)

# Without progress bar
crawler = WebCrawler(urls=urls, show_progress=False)
```

### Progress Info
Shows: Percentage, Progress bar, Current/Total, Time, ETA, Speed

```
Crawling URLs: 100%|████████████| 50/50 [00:15<00:00, 3.33url/s]
```

## 🌐 Proxy Management

### Auto-fetch Proxies
```python
crawler = WebCrawler(urls=urls, use_proxy=True)
```

### Manual Proxies
```python
crawler = WebCrawler(urls=urls, use_proxy=True)
crawler.proxy_manager.add_proxies([
    "http://proxy1.com:8080",
    "http://proxy2.com:8080"
])
```

### Proxy Stats
```python
stats = crawler.proxy_manager.get_stats()
# {'total': 100, 'available': 80, 'failed': 20, 'failure_rate': 0.2}
```

## 📊 Statistics

### WebCrawler Stats
```python
stats = crawler.crawl()
# {
#     'total': 10,
#     'success': 8,
#     'failed': 2,
#     'duration': 15.5
# }
```

### ChainCrawler Stats
```python
stats = crawler.crawl()
# {
#     'total_requests': 50,
#     'successful_requests': 45,
#     'failed_requests': 5,
#     'final_results': 20,
#     'step_stats': {
#         'Step1': {...},
#         'Step2': {...}
#     }
# }
```

## 🐛 Error Handling

### Safe Parser
```python
def safe_parser(url, html):
    try:
        # parsing logic
        return {...}
    except Exception as e:
        return {'error': str(e)}
```

## 📝 Common Patterns

### E-commerce Chain
```python
steps = [
    ChainStep("Categories", category_parser, get_products),
    ChainStep("Products", product_parser, get_details),
    ChainStep("Details", detail_parser, None)
]
```

### News Crawl Chain
```python
steps = [
    ChainStep("Homepage", homepage_parser, get_articles),
    ChainStep("Articles", article_parser, None)
]
```

## ⚡ Performance Tips

### Fast Crawl
```python
crawler = WebCrawler(
    urls=urls,
    max_workers=20,
    timeout=10,
    use_proxy=False
)
```

### Safe Crawl
```python
crawler = WebCrawler(
    urls=urls,
    max_workers=3,
    timeout=60,
    max_retries=5,
    use_proxy=True
)
```

## 🔍 Debugging

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Proxy Stats
```python
stats = proxy_manager.get_stats()
print(f"Available: {stats['available']}/{stats['total']}")
print(f"Failure rate: {stats['failure_rate']:.2%}")
```

## 📚 Files

- **README.md** - Overview
- **QUICKSTART.md** - 5-min guide
- **USAGE_GUIDE.md** - Detailed guide
- **NEW_FEATURES.md** - v1.1 features
- **example_*.py** - Examples
- **test_quick.py** - Quick test

## 🆘 Help

**Timeout issues?**
```python
crawler = WebCrawler(urls=urls, timeout=60)
```

**IP blocked?**
```python
crawler = WebCrawler(urls=urls, use_proxy=True)
```

**Chain not working?**
- Check extract_next_urls returns list
- Verify last step has extract_next_urls=None
- Check logs for errors

**No results?**
- Verify parser returns dict
- Check storage.finalize() is called
- Enable DEBUG logging

---

**Version:** 1.1.0 | **License:** MIT
