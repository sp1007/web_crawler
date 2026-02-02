"""
Quick Test - Demo chức năng cơ bản của crawler
"""

import logging
import sys
import os

# Thêm thư mục hiện tại vào Python path
sys.path.insert(0, os.path.dirname(__file__))

from web_crawler import WebCrawler, AggregatedStorage, PerURLStorage
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def simple_parser(url: str, html: str) -> dict:
    """Simple parser để test"""
    soup = BeautifulSoup(html, 'html.parser')
    
    title = soup.title.string if soup.title else "No title"
    
    # Count elements
    headings = len(soup.find_all(['h1', 'h2', 'h3']))
    links = len(soup.find_all('a', href=True))
    images = len(soup.find_all('img'))
    
    return {
        'title': title,
        'headings_count': headings,
        'links_count': links,
        'images_count': images,
        'has_form': len(soup.find_all('form')) > 0
    }


def test_basic():
    """Test 1: Basic crawl với default parser"""
    print("\n" + "="*70)
    print("TEST 1: Basic Crawl với Default Parser và AggregatedStorage")
    print("="*70)
    
    urls = [
        "https://example.com",
        "https://httpbin.org/html",
    ]
    
    crawler = WebCrawler(
        urls=urls,
        max_workers=2,
        use_proxy=False,  # Tắt proxy cho test nhanh
        timeout=15
    )
    
    stats = crawler.crawl()
    
    print(f"\n✓ Success: {stats['success']}/{stats['total']}")
    print(f"✓ Duration: {stats['duration']}s")
    print(f"✓ Output: crawl_results.json")


def test_custom_parser():
    """Test 2: Custom parser với PerURLStorage"""
    print("\n" + "="*70)
    print("TEST 2: Custom Parser với PerURLStorage")
    print("="*70)
    
    urls = [
        "https://example.com",
        "https://httpbin.org/html",
    ]
    
    storage = PerURLStorage(output_dir="test_results")
    
    crawler = WebCrawler(
        urls=urls,
        parser=simple_parser,
        storage=storage,
        max_workers=2,
        use_proxy=False,
        timeout=15
    )
    
    stats = crawler.crawl()
    
    print(f"\n✓ Success: {stats['success']}/{stats['total']}")
    print(f"✓ Duration: {stats['duration']}s")
    print(f"✓ Output: test_results/")


def test_with_proxy():
    """Test 3: Crawl với proxy (optional)"""
    print("\n" + "="*70)
    print("TEST 3: Crawl với Proxy Support")
    print("="*70)
    
    urls = [
        "https://httpbin.org/ip",  # Returns your IP
    ]
    
    crawler = WebCrawler(
        urls=urls,
        max_workers=1,
        use_proxy=True,  # Enable proxy
        timeout=20
    )
    
    stats = crawler.crawl()
    
    print(f"\n✓ Success: {stats['success']}/{stats['total']}")
    print(f"✓ Duration: {stats['duration']}s")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("WEB CRAWLER PACKAGE - QUICK TEST")
    print("="*70)
    
    try:
        # Test 1: Basic
        test_basic()
        
        # Test 2: Custom parser
        test_custom_parser()
        
        # Test 3: With proxy (có thể bỏ qua nếu không có proxy)
        print("\n" + "="*70)
        print("Bỏ qua Test 3 (Proxy) - có thể uncomment để test")
        print("="*70)
        # test_with_proxy()
        
        print("\n" + "="*70)
        print("✓ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*70)
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
