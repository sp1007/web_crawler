"""
Example 4: Advanced usage - Kết hợp tất cả tính năng
"""

import logging
from bs4 import BeautifulSoup
from web_crawler import WebCrawler, AggregatedStorage, ProxyManager

# Setup logging với level DEBUG để xem chi tiết
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def advanced_parser(url: str, html_content: str) -> dict:
    """
    Advanced parser - Extract nhiều loại dữ liệu khác nhau
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Basic info
    title = soup.title.string if soup.title else ""
    
    # Meta tags
    meta_info = {}
    for meta in soup.find_all('meta'):
        name = meta.get('name') or meta.get('property', '')
        content = meta.get('content', '')
        if name and content:
            meta_info[name] = content
    
    # All text content
    for script in soup(['script', 'style']):
        script.decompose()
    text = soup.get_text()
    words = text.split()
    
    # Links analysis
    links = {'internal': [], 'external': []}
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('http'):
            if url.split('/')[2] in href:
                links['internal'].append(href)
            else:
                links['external'].append(href)
    
    # Images
    images = []
    for img in soup.find_all('img'):
        images.append({
            'src': img.get('src', ''),
            'alt': img.get('alt', ''),
        })
    
    # Forms
    forms = []
    for form in soup.find_all('form'):
        forms.append({
            'action': form.get('action', ''),
            'method': form.get('method', '').upper(),
            'inputs': len(form.find_all('input'))
        })
    
    return {
        'title': title,
        'meta_info': meta_info,
        'word_count': len(words),
        'links': {
            'internal_count': len(links['internal']),
            'external_count': len(links['external']),
            'external_domains': list(set([l.split('/')[2] for l in links['external'] if len(l.split('/')) > 2]))[:10]
        },
        'images_count': len(images),
        'forms_count': len(forms),
        'forms': forms,
        'has_javascript': len(soup.find_all('script')) > 0,
        'has_css': len(soup.find_all('link', rel='stylesheet')) > 0 or len(soup.find_all('style')) > 0
    }


# Custom proxy sources (có thể thêm proxy của bạn)
custom_proxies = [
    # "http://proxy1.example.com:8080",
    # "http://proxy2.example.com:8080",
]

# URLs để crawl
urls = [
    "https://example.com",
    "https://www.python.org",
    "https://docs.python.org/3/",
    "https://pypi.org",
    "https://httpbin.org/html",
]

# Cấu hình storage
storage = AggregatedStorage(output_file="advanced_results.json")

# Tạo crawler với cấu hình đầy đủ
crawler = WebCrawler(
    urls=urls,
    parser=advanced_parser,  # Custom parser
    storage=storage,  # Aggregated storage
    max_workers=8,  # 8 concurrent workers
    use_proxy=True,  # Sử dụng proxy
    proxy_sources=None,  # Dùng proxy sources mặc định (hoặc thêm custom_proxies)
    timeout=30,  # 30s timeout
    max_retries=3,  # Retry 3 lần
    retry_delay=2  # Delay 2s giữa các retry
)

# Có thể thêm proxy thủ công
if custom_proxies:
    crawler.proxy_manager.add_proxies(custom_proxies)

# Bắt đầu crawl
print("Starting advanced crawl with all features...")
stats = crawler.crawl()

# In kết quả
print("\n" + "="*50)
print("CRAWL COMPLETED")
print("="*50)
print(f"Total URLs:     {stats['total']}")
print(f"Success:        {stats['success']} ({stats['success']/stats['total']*100:.1f}%)")
print(f"Failed:         {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")
print(f"Duration:       {stats['duration']}s")
print(f"Avg per URL:    {stats['duration']/stats['total']:.2f}s")
print(f"\nResults saved to: advanced_results.json")
print("="*50)
