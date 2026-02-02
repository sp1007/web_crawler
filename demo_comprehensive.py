"""
COMPREHENSIVE DEMO - Showcase tất cả tính năng của Web Crawler Package
"""

import logging
import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from web_crawler import (
    WebCrawler,
    ProxyManager,
    PerURLStorage,
    AggregatedStorage,
)
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


# ============================================================================
# CUSTOM PARSERS
# ============================================================================

def default_parser_demo(url: str, html: str) -> dict:
    """Parser mặc định - extract thông tin cơ bản"""
    soup = BeautifulSoup(html, 'html.parser')
    
    return {
        'title': soup.title.string if soup.title else '',
        'meta_description': soup.find('meta', {'name': 'description'}),
        'h1_count': len(soup.find_all('h1')),
        'link_count': len(soup.find_all('a', href=True)),
        'image_count': len(soup.find_all('img')),
    }


def detailed_parser_demo(url: str, html: str) -> dict:
    """Parser chi tiết - extract nhiều thông tin"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Title
    title = soup.title.string if soup.title else "No title"
    
    # All headings
    headings = {}
    for level in ['h1', 'h2', 'h3', 'h4']:
        headings[level] = [h.get_text().strip() for h in soup.find_all(level)]
    
    # Meta info
    meta_info = {}
    for meta in soup.find_all('meta'):
        name = meta.get('name') or meta.get('property', '')
        content = meta.get('content', '')
        if name:
            meta_info[name] = content
    
    # Links analysis
    links = {'internal': [], 'external': []}
    domain = url.split('/')[2] if len(url.split('/')) > 2 else ''
    
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('http'):
            if domain in href:
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
    
    # Text stats
    text = soup.get_text()
    words = text.split()
    
    return {
        'url': url,
        'crawled_at': datetime.now().isoformat(),
        'title': title,
        'headings': headings,
        'meta_info': meta_info,
        'links': {
            'internal_count': len(links['internal']),
            'external_count': len(links['external']),
            'sample_external': links['external'][:5]
        },
        'images': {
            'count': len(images),
            'sample': images[:3]
        },
        'text_stats': {
            'word_count': len(words),
            'char_count': len(text),
        }
    }


# ============================================================================
# DEMO SCENARIOS
# ============================================================================

def demo_1_basic_usage():
    """Demo 1: Sử dụng cơ bản nhất"""
    print("\n" + "="*80)
    print("DEMO 1: BASIC USAGE - Sử dụng mặc định")
    print("="*80)
    
    urls = [
        "https://example.com",
        "https://httpbin.org/html",
    ]
    
    print(f"\n📋 Crawling {len(urls)} URLs with default settings...")
    
    crawler = WebCrawler(
        urls=urls,
        use_proxy=False  # No proxy for demo
    )
    
    stats = crawler.crawl()
    
    print("\n✅ RESULTS:")
    print(f"   Total:    {stats['total']}")
    print(f"   Success:  {stats['success']}")
    print(f"   Failed:   {stats['failed']}")
    print(f"   Duration: {stats['duration']}s")
    print(f"   Output:   crawl_results.json")


def demo_2_custom_parser():
    """Demo 2: Sử dụng custom parser"""
    print("\n" + "="*80)
    print("DEMO 2: CUSTOM PARSER - Parser tùy chỉnh")
    print("="*80)
    
    urls = [
        "https://example.com",
        "https://httpbin.org/html",
    ]
    
    print(f"\n📋 Crawling {len(urls)} URLs with custom parser...")
    
    crawler = WebCrawler(
        urls=urls,
        parser=detailed_parser_demo,
        use_proxy=False
    )
    
    stats = crawler.crawl()
    
    print("\n✅ RESULTS:")
    print(f"   Total:    {stats['total']}")
    print(f"   Success:  {stats['success']}")
    print(f"   Duration: {stats['duration']}s")


def demo_3_per_url_storage():
    """Demo 3: Lưu kết quả theo từng URL"""
    print("\n" + "="*80)
    print("DEMO 3: PER-URL STORAGE - Lưu từng file riêng")
    print("="*80)
    
    urls = [
        "https://example.com",
        "https://httpbin.org/html",
    ]
    
    output_dir = "demo_per_url_results"
    storage = PerURLStorage(output_dir=output_dir)
    
    print(f"\n📋 Crawling {len(urls)} URLs...")
    print(f"📁 Output directory: {output_dir}/")
    
    crawler = WebCrawler(
        urls=urls,
        parser=detailed_parser_demo,
        storage=storage,
        use_proxy=False
    )
    
    stats = crawler.crawl()
    
    print("\n✅ RESULTS:")
    print(f"   Files saved: {stats['success']}")
    print(f"   Location:    {output_dir}/")
    
    # List created files
    if os.path.exists(output_dir):
        files = os.listdir(output_dir)
        print(f"\n📄 Created files:")
        for f in files[:5]:  # Show first 5
            print(f"   - {f}")


def demo_4_aggregated_storage():
    """Demo 4: Lưu tất cả vào 1 file"""
    print("\n" + "="*80)
    print("DEMO 4: AGGREGATED STORAGE - Lưu tất cả vào 1 file")
    print("="*80)
    
    urls = [
        "https://example.com",
        "https://httpbin.org/html",
    ]
    
    output_file = "demo_aggregated_results.json"
    storage = AggregatedStorage(output_file=output_file)
    
    print(f"\n📋 Crawling {len(urls)} URLs...")
    print(f"📄 Output file: {output_file}")
    
    crawler = WebCrawler(
        urls=urls,
        parser=detailed_parser_demo,
        storage=storage,
        use_proxy=False
    )
    
    stats = crawler.crawl()
    
    print("\n✅ RESULTS:")
    print(f"   Records:  {stats['success']}")
    print(f"   File:     {output_file}")


def demo_5_performance_tuning():
    """Demo 5: Điều chỉnh performance"""
    print("\n" + "="*80)
    print("DEMO 5: PERFORMANCE TUNING - Tùy chỉnh hiệu suất")
    print("="*80)
    
    urls = [
        "https://example.com",
        "https://httpbin.org/html",
        "https://httpbin.org/delay/1",
    ]
    
    print(f"\n📋 Test 1: Fast crawl (nhiều workers, timeout ngắn)")
    crawler_fast = WebCrawler(
        urls=urls,
        max_workers=10,
        timeout=10,
        max_retries=2,
        use_proxy=False
    )
    stats_fast = crawler_fast.crawl()
    print(f"   ⚡ Duration: {stats_fast['duration']}s")
    
    print(f"\n📋 Test 2: Safe crawl (ít workers, timeout dài)")
    crawler_safe = WebCrawler(
        urls=urls,
        max_workers=2,
        timeout=30,
        max_retries=3,
        retry_delay=2,
        use_proxy=False
    )
    stats_safe = crawler_safe.crawl()
    print(f"   🐢 Duration: {stats_safe['duration']}s")
    
    print("\n✅ COMPARISON:")
    print(f"   Fast: {stats_fast['duration']}s - Success: {stats_fast['success']}/{stats_fast['total']}")
    print(f"   Safe: {stats_safe['duration']}s - Success: {stats_safe['success']}/{stats_safe['total']}")


def demo_6_error_handling():
    """Demo 6: Xử lý lỗi"""
    print("\n" + "="*80)
    print("DEMO 6: ERROR HANDLING - Xử lý khi có lỗi")
    print("="*80)
    
    # Mix of valid and invalid URLs
    urls = [
        "https://example.com",
        "https://invalid-url-that-does-not-exist-12345.com",
        "https://httpbin.org/html",
    ]
    
    def safe_parser(url: str, html: str) -> dict:
        """Parser với error handling"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            return {
                'title': soup.title.string if soup.title else '',
                'status': 'success'
            }
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return {
                'error': str(e),
                'status': 'failed'
            }
    
    print(f"\n📋 Crawling {len(urls)} URLs (including invalid ones)...")
    
    crawler = WebCrawler(
        urls=urls,
        parser=safe_parser,
        max_workers=3,
        timeout=10,
        max_retries=2,
        use_proxy=False
    )
    
    stats = crawler.crawl()
    
    print("\n✅ RESULTS:")
    print(f"   Total:    {stats['total']}")
    print(f"   Success:  {stats['success']}")
    print(f"   Failed:   {stats['failed']}")
    print(f"   Success Rate: {stats['success']/stats['total']*100:.1f}%")


# ============================================================================
# MAIN DEMO RUNNER
# ============================================================================

def run_all_demos():
    """Chạy tất cả demos"""
    print("\n" + "="*80)
    print("WEB CRAWLER PACKAGE - COMPREHENSIVE DEMO")
    print("="*80)
    print("\nDemo sẽ showcase các tính năng chính của package:")
    print("1. Basic usage")
    print("2. Custom parser")
    print("3. Per-URL storage")
    print("4. Aggregated storage")
    print("5. Performance tuning")
    print("6. Error handling")
    print("\nNote: Proxy demo bị skip vì proxy miễn phí thường không stable")
    print("="*80)
    
    try:
        # Run all demos
        demo_1_basic_usage()
        demo_2_custom_parser()
        demo_3_per_url_storage()
        demo_4_aggregated_storage()
        demo_5_performance_tuning()
        demo_6_error_handling()
        
        # Summary
        print("\n" + "="*80)
        print("✅ ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("="*80)
        print("\n📚 Để tìm hiểu thêm:")
        print("   - README.md: Overview và quickstart")
        print("   - USAGE_GUIDE.md: Hướng dẫn chi tiết và use cases")
        print("   - examples/: Các example scripts")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ DEMO FAILED: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_demos()
