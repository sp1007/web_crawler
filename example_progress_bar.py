"""
Example 6: Progress Bar Demo - Hiển thị thanh tiến độ
"""

import logging
from web_crawler import WebCrawler, ChainCrawler, ChainStep, AggregatedStorage
from bs4 import BeautifulSoup

# Setup logging (INFO để không bị spam console)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def simple_parser(url: str, html: str) -> dict:
    """Simple parser"""
    soup = BeautifulSoup(html, 'html.parser')
    return {
        'title': soup.title.string if soup.title else '',
        'h1_count': len(soup.find_all('h1')),
        'link_count': len(soup.find_all('a')),
    }


def demo_webcrawler_with_progress():
    """Demo 1: WebCrawler with progress bar"""
    print("\n" + "="*80)
    print("DEMO 1: WebCrawler với Progress Bar")
    print("="*80)
    
    # Tạo một list URLs dài hơn để thấy rõ progress
    urls = [
        "https://example.com",
        "https://httpbin.org/html",
        "https://httpbin.org/delay/1",
        "https://www.python.org",
        "https://docs.python.org/3/",
    ] * 3  # 15 URLs total
    
    print(f"\nCrawling {len(urls)} URLs với progress bar enabled...")
    
    # WITH progress bar (mặc định)
    crawler = WebCrawler(
        urls=urls,
        parser=simple_parser,
        max_workers=5,
        use_proxy=False,
        show_progress=True  # Enable progress bar
    )
    
    stats = crawler.crawl()
    
    print(f"\n✅ Completed!")
    print(f"   Success: {stats['success']}/{stats['total']}")
    print(f"   Duration: {stats['duration']}s")


def demo_webcrawler_without_progress():
    """Demo 2: WebCrawler without progress bar"""
    print("\n" + "="*80)
    print("DEMO 2: WebCrawler KHÔNG có Progress Bar")
    print("="*80)
    
    urls = [
        "https://example.com",
        "https://httpbin.org/html",
    ]
    
    print(f"\nCrawling {len(urls)} URLs without progress bar...")
    
    # WITHOUT progress bar
    crawler = WebCrawler(
        urls=urls,
        parser=simple_parser,
        max_workers=2,
        use_proxy=False,
        show_progress=False  # Disable progress bar
    )
    
    stats = crawler.crawl()
    
    print(f"\n✅ Completed!")
    print(f"   Success: {stats['success']}/{stats['total']}")


def demo_chain_crawler_with_progress():
    """Demo 3: ChainCrawler with progress bar"""
    print("\n" + "="*80)
    print("DEMO 3: ChainCrawler với Progress Bar")
    print("="*80)
    
    # Step 1 parser
    def step1_parser(url: str, html: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        links = [a.get('href') for a in soup.find_all('a', href=True) if a.get('href').startswith('http')]
        return {'links': links[:3]}  # Top 3 links
    
    def step1_extract(data: dict) -> list:
        return data['links']
    
    # Step 2 parser
    def step2_parser(url: str, html: str) -> dict:
        soup = BeautifulSoup(html, 'html.parser')
        return {
            'url': url,
            'title': soup.title.string if soup.title else '',
        }
    
    # Define steps
    steps = [
        ChainStep("Extract Links", step1_parser, step1_extract),
        ChainStep("Parse Pages", step2_parser, None)
    ]
    
    print("\nRunning chain crawl với progress bars...")
    
    # Chain crawler with progress
    crawler = ChainCrawler(
        initial_urls=["https://example.com"],
        steps=steps,
        max_workers=3,
        use_proxy=False,
        show_progress=True  # Progress bar cho mỗi step
    )
    
    stats = crawler.crawl()
    
    print(f"\n✅ Chain Completed!")
    print(f"   Total Requests: {stats['total_requests']}")
    print(f"   Final Results: {stats['final_results']}")


def demo_comparison():
    """Demo 4: So sánh có và không có progress bar"""
    print("\n" + "="*80)
    print("DEMO 4: So sánh WITH vs WITHOUT Progress Bar")
    print("="*80)
    
    urls = ["https://example.com", "https://httpbin.org/html"] * 5  # 10 URLs
    
    print("\n--- Test 1: WITH Progress Bar ---")
    crawler1 = WebCrawler(
        urls=urls,
        parser=simple_parser,
        max_workers=5,
        use_proxy=False,
        show_progress=True
    )
    stats1 = crawler1.crawl()
    
    print("\n--- Test 2: WITHOUT Progress Bar ---")
    crawler2 = WebCrawler(
        urls=urls,
        parser=simple_parser,
        max_workers=5,
        use_proxy=False,
        show_progress=False
    )
    stats2 = crawler2.crawl()
    
    print("\n📊 Comparison:")
    print(f"   WITH progress:    {stats1['duration']}s")
    print(f"   WITHOUT progress: {stats2['duration']}s")
    print(f"   Overhead:         {abs(stats1['duration'] - stats2['duration']):.2f}s")


def demo_large_crawl():
    """Demo 5: Large crawl với progress bar"""
    print("\n" + "="*80)
    print("DEMO 5: Large Crawl - Progress Bar rất hữu ích!")
    print("="*80)
    
    # Tạo list URLs lớn
    urls = [
        "https://example.com",
        "https://httpbin.org/html",
        "https://httpbin.org/delay/1",
    ] * 10  # 30 URLs
    
    print(f"\nCrawling {len(urls)} URLs...")
    print("Progress bar giúp bạn theo dõi tiến độ!\n")
    
    crawler = WebCrawler(
        urls=urls,
        parser=simple_parser,
        max_workers=8,
        use_proxy=False,
        show_progress=True,
        storage=AggregatedStorage("large_crawl_results.json")
    )
    
    stats = crawler.crawl()
    
    print(f"\n✅ Large Crawl Completed!")
    print(f"   Total: {stats['total']}")
    print(f"   Success: {stats['success']}")
    print(f"   Failed: {stats['failed']}")
    print(f"   Duration: {stats['duration']}s")
    print(f"   Speed: {stats['total']/stats['duration']:.1f} URLs/second")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("PROGRESS BAR DEMO")
    print("="*80)
    print("\nTính năng progress bar giúp bạn:")
    print("  ✓ Theo dõi tiến độ crawl")
    print("  ✓ Biết còn bao nhiêu URLs")
    print("  ✓ Ước tính thời gian còn lại")
    print("  ✓ Giảm lo lắng khi crawl lâu")
    
    # Run demos
    try:
        demo_webcrawler_with_progress()
        # demo_webcrawler_without_progress()
        # demo_chain_crawler_with_progress()
        # demo_comparison()
        # demo_large_crawl()
        
        print("\n" + "="*80)
        print("✅ All Progress Bar Demos Completed!")
        print("="*80)
        print("\nTip: Set show_progress=True (default) để hiện progress bar")
        print("     Set show_progress=False nếu muốn log đơn giản")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
