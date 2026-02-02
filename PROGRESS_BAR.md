# Progress Bar Feature - Complete Guide

## 📊 Overview

Package hiện có **thanh tiến độ (progress bar)** để theo dõi quá trình crawl real-time!

## ✨ Tính năng

- ✅ Real-time progress tracking
- ✅ Visual progress bar với tqdm
- ✅ Hiển thị: Percentage, Current/Total, Time, ETA, Speed
- ✅ Hỗ trợ cả WebCrawler và ChainCrawler
- ✅ Per-step progress trong chain crawling
- ✅ Có thể tắt/bật dễ dàng

## 🚀 Quick Start

### Basic Usage

```python
from web_crawler import WebCrawler

urls = ["https://example.com"] * 50

# WITH progress bar (mặc định)
crawler = WebCrawler(
    urls=urls,
    show_progress=True  # Default = True
)

crawler.crawl()

# Output:
# Crawling URLs: 100%|████████████| 50/50 [00:15<00:00, 3.33url/s]
```

### Disable Progress Bar

```python
# WITHOUT progress bar
crawler = WebCrawler(
    urls=urls,
    show_progress=False
)

crawler.crawl()
# Chỉ có logs, không có progress bar
```

## 🔗 Chain Crawler Progress

Mỗi step trong chain có progress bar riêng:

```python
from web_crawler import ChainCrawler, ChainStep

steps = [
    ChainStep("Step 1", parser1, extract_urls),
    ChainStep("Step 2", parser2, None)
]

crawler = ChainCrawler(
    initial_urls=urls,
    steps=steps,
    show_progress=True  # Progress cho mỗi step
)

crawler.crawl()

# Output:
# Step 1: Extract Links: 100%|████████| 10/10 [00:05<00:00, 2.00url/s]
# Step 2: Parse Content:  100%|████████| 50/50 [00:15<00:00, 3.33url/s]
```

## 📊 Progress Information

Progress bar hiển thị các thông tin:

```
Crawling URLs: 100%|████████████| 50/50 [00:15<00:00, 3.33url/s]
               │    │            │  │    │        │        │
               │    │            │  │    │        │        └─ Speed (URLs/sec)
               │    │            │  │    │        └─ ETA (estimated time)
               │    │            │  │    └─ Time elapsed
               │    │            │  └─ Current/Total
               │    │            └─ Current number
               │    └─ Visual progress bar
               └─ Percentage (0-100%)
```

## 🎯 When to Use

### Use Progress Bar (show_progress=True)

✅ **Good for:**
- Crawling nhiều URLs (>10)
- Interactive/terminal sessions
- Development và debugging
- Muốn biết thời gian còn lại
- Monitor performance

### Disable Progress Bar (show_progress=False)

✅ **Good for:**
- Production logging
- Crawling ít URLs (<5)
- Cron jobs / background tasks
- File output cần clean
- CI/CD pipelines

## 💡 Examples

### Example 1: Development Mode

```python
# Development: Enable progress
crawler = WebCrawler(
    urls=development_urls,
    show_progress=True,
    max_workers=5
)
```

### Example 2: Production Mode

```python
# Production: Disable progress, use clean logs
crawler = WebCrawler(
    urls=production_urls,
    show_progress=False,
    max_workers=20
)
```

### Example 3: Large Crawl

```python
# Large crawl - Progress bar rất hữu ích!
urls = get_urls()  # 1000+ URLs

crawler = WebCrawler(
    urls=urls,
    show_progress=True,  # Track progress!
    max_workers=15
)

stats = crawler.crawl()
# Bạn sẽ thấy progress update real-time
```

### Example 4: Chain Crawl

```python
# Chain with progress per step
crawler = ChainCrawler(
    initial_urls=["https://shop.com/category"],
    steps=[
        ChainStep("Categories", cat_parser, get_products),
        ChainStep("Products", prod_parser, get_details),
        ChainStep("Details", detail_parser, None)
    ],
    show_progress=True  # Progress cho cả 3 steps
)

crawler.crawl()
# Mỗi step sẽ có progress bar riêng!
```

## 🔧 Technical Details

### Implementation

- Sử dụng **tqdm** library
- Async-compatible với `tqdm.asyncio`
- Zero performance overhead khi disabled
- Thread-safe

### Performance Impact

- **With progress**: ~1-2% overhead (negligible)
- **Without progress**: No overhead
- Không ảnh hưởng đến crawl speed

## 🐛 Troubleshooting

### Progress bar không hiện?

```python
# Đảm bảo show_progress=True
crawler = WebCrawler(urls=urls, show_progress=True)
```

### Progress bar bị nhảy?

- Normal behavior với async tasks
- Progress có thể không tuyến tính vì concurrent

### Muốn custom progress format?

```python
# Hiện tại chưa support custom format
# Sẽ thêm trong version tương lai
```

## 📝 Best Practices

1. **Enable trong development**
   ```python
   if ENV == 'development':
       show_progress = True
   else:
       show_progress = False
   ```

2. **Disable trong production logs**
   ```python
   crawler = WebCrawler(
       urls=urls,
       show_progress=False  # Clean logs
   )
   ```

3. **Use với large datasets**
   ```python
   if len(urls) > 50:
       show_progress = True  # Helpful for large crawls
   ```

## 📚 Complete Example

File: `example_progress_bar.py`

```python
from web_crawler import WebCrawler

# Example với nhiều URLs
urls = ["https://example.com"] * 100

print("Starting crawl with progress bar...")

crawler = WebCrawler(
    urls=urls,
    max_workers=10,
    show_progress=True  # Enable progress
)

stats = crawler.crawl()

print(f"\nCompleted!")
print(f"Success: {stats['success']}/{stats['total']}")
print(f"Duration: {stats['duration']}s")
print(f"Speed: {stats['total']/stats['duration']:.1f} URLs/sec")
```

## 🎓 Summary

**Progress Bar giúp bạn:**
- ✅ Theo dõi tiến độ crawl
- ✅ Biết thời gian còn lại
- ✅ Monitor performance
- ✅ Giảm lo lắng khi crawl lâu
- ✅ Debug issues dễ hơn

**Default behavior:**
- `show_progress=True` - Progress bar enabled
- Có thể tắt với `show_progress=False`

---

**Version:** 1.1.0  
**Feature Added:** 2024-02-02  
**Dependencies:** tqdm>=4.66.0
