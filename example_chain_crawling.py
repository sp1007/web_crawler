"""
Example 5: Chain Crawling - Crawl theo chuỗi nhiều bước
Ví dụ: Category Page → Product List → Product Details → Final Data
"""

import logging
from bs4 import BeautifulSoup
from web_crawler import ChainCrawler, ChainStep, AggregatedStorage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ============================================================================
# SCENARIO 1: E-commerce - Category → Products → Details
# ============================================================================

def step1_category_parser(url: str, html: str) -> dict:
    """
    Step 1: Parse category page, extract product URLs
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Trong thực tế, bạn sẽ tìm các product links
    # Đây là example giả định
    product_links = [a.get('href') for a in soup.find_all('a', class_='product-link')]
    
    return {
        'category': soup.title.string if soup.title else '',
        'product_count': len(product_links),
        'product_links': product_links
    }

def step1_extract_next_urls(data: dict) -> list:
    """Extract product URLs từ category data"""
    # Trong thực tế, return data['product_links']
    # Đây là example với URLs demo
    return [
        "https://example.com/product/1",
        "https://example.com/product/2"
    ]


def step2_product_parser(url: str, html: str) -> dict:
    """
    Step 2: Parse product page, extract detail page URL
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract thông tin cơ bản
    title = soup.find('h1')
    price = soup.find('span', class_='price')
    
    # Tìm link "View Details"
    detail_link = soup.find('a', class_='view-details')
    
    return {
        'title': title.get_text().strip() if title else '',
        'price': price.get_text().strip() if price else '',
        'detail_url': detail_link.get('href') if detail_link else None
    }

def step2_extract_next_urls(data: dict) -> list:
    """Extract detail URL từ product data"""
    if data.get('detail_url'):
        return [data['detail_url']]
    return []


def step3_detail_parser(url: str, html: str) -> dict:
    """
    Step 3: Parse detail page - FINAL STEP
    Extract toàn bộ thông tin chi tiết
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract comprehensive data
    return {
        'url': url,
        'title': soup.find('h1').get_text().strip() if soup.find('h1') else '',
        'description': soup.find('div', class_='description').get_text().strip() if soup.find('div', class_='description') else '',
        'price': soup.find('span', class_='price').get_text().strip() if soup.find('span', class_='price') else '',
        'images': [img.get('src') for img in soup.find_all('img', class_='product-image')],
        'specifications': {},  # Có thể extract specs
        'reviews_count': len(soup.find_all('div', class_='review')),
    }


# ============================================================================
# SCENARIO 2: Simple 2-Step Chain
# ============================================================================

def simple_step1_parser(url: str, html: str) -> dict:
    """Step 1: Extract links from a page"""
    soup = BeautifulSoup(html, 'html.parser')
    links = [a.get('href') for a in soup.find_all('a', href=True) if a.get('href').startswith('http')]
    
    return {
        'page_title': soup.title.string if soup.title else '',
        'links_found': len(links),
        'links': links[:5]  # Top 5 links
    }

def simple_step1_extract_urls(data: dict) -> list:
    """Get the links to crawl in step 2"""
    return data['links']

def simple_step2_parser(url: str, html: str) -> dict:
    """Step 2: Extract final data from linked pages"""
    soup = BeautifulSoup(html, 'html.parser')
    
    return {
        'url': url,
        'title': soup.title.string if soup.title else '',
        'h1_count': len(soup.find_all('h1')),
        'h2_count': len(soup.find_all('h2')),
        'link_count': len(soup.find_all('a')),
        'image_count': len(soup.find_all('img')),
    }


# ============================================================================
# RUN EXAMPLES
# ============================================================================

def demo_simple_2step():
    """Demo: Simple 2-step chain"""
    print("\n" + "="*80)
    print("DEMO: Simple 2-Step Chain Crawling")
    print("="*80)
    
    # Define steps
    steps = [
        ChainStep(
            name="Extract Links",
            parser=simple_step1_parser,
            extract_next_urls=simple_step1_extract_urls
        ),
        ChainStep(
            name="Crawl Linked Pages",
            parser=simple_step2_parser,
            extract_next_urls=None  # Final step
        )
    ]
    
    # Initial URLs
    initial_urls = [
        "https://example.com",
    ]
    
    # Create crawler
    crawler = ChainCrawler(
        initial_urls=initial_urls,
        steps=steps,
        storage=AggregatedStorage("chain_simple_results.json"),
        max_workers=3,
        use_proxy=False,  # No proxy for demo
        max_urls_per_step=3  # Limit URLs per step
    )
    
    # Crawl
    stats = crawler.crawl()
    
    print("\n✅ RESULTS:")
    print(f"   Total Requests: {stats['total_requests']}")
    print(f"   Successful: {stats['successful_requests']}")
    print(f"   Final Results: {stats['final_results']}")
    print(f"   Output: chain_simple_results.json")


def demo_3step_ecommerce():
    """Demo: 3-step e-commerce chain"""
    print("\n" + "="*80)
    print("DEMO: 3-Step E-commerce Chain Crawling")
    print("="*80)
    print("Note: This is a conceptual demo with hypothetical URLs")
    
    # Define steps
    steps = [
        ChainStep(
            name="Category Pages",
            parser=step1_category_parser,
            extract_next_urls=step1_extract_next_urls
        ),
        ChainStep(
            name="Product Pages",
            parser=step2_product_parser,
            extract_next_urls=step2_extract_next_urls
        ),
        ChainStep(
            name="Detail Pages",
            parser=step3_detail_parser,
            extract_next_urls=None  # Final step
        )
    ]
    
    # Initial URLs (category pages)
    initial_urls = [
        "https://example-shop.com/category/electronics",
    ]
    
    # Create crawler
    crawler = ChainCrawler(
        initial_urls=initial_urls,
        steps=steps,
        storage=AggregatedStorage("chain_ecommerce_results.json"),
        max_workers=5,
        use_proxy=False,
        max_urls_per_step=10
    )
    
    # Crawl
    stats = crawler.crawl()
    
    print("\n✅ RESULTS:")
    print(f"   Steps Completed: {stats['steps_completed']}")
    print(f"   Total Requests: {stats['total_requests']}")
    print(f"   Final Results: {stats['final_results']}")
    
    # Show per-step stats
    print("\n📊 Per-Step Statistics:")
    for step_name, step_stats in stats['step_stats'].items():
        print(f"\n   {step_name}:")
        print(f"      Processed: {step_stats['urls_processed']}")
        print(f"      Succeeded: {step_stats['urls_succeeded']}")
        if 'next_urls_found' in step_stats:
            print(f"      Next URLs: {step_stats['next_urls_found']}")


# ============================================================================
# PRACTICAL EXAMPLE: News Website
# ============================================================================

def news_step1_parser(url: str, html: str) -> dict:
    """Step 1: Parse category/homepage, get article URLs"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find article links
    article_links = []
    for a in soup.find_all('a', href=True):
        href = a.get('href')
        if '/article/' in href or '/news/' in href:
            article_links.append(href)
    
    return {'article_links': list(set(article_links))}

def news_step1_extract(data: dict) -> list:
    return data['article_links'][:5]  # Limit to 5 articles

def news_step2_parser(url: str, html: str) -> dict:
    """Step 2: Parse article, extract full content"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract article content
    title = soup.find('h1')
    paragraphs = soup.find_all('p', class_='article-content')
    content = '\n'.join([p.get_text().strip() for p in paragraphs])
    
    return {
        'url': url,
        'title': title.get_text().strip() if title else '',
        'content': content,
        'word_count': len(content.split()),
        'has_images': len(soup.find_all('img')) > 0
    }


def demo_news_crawl():
    """Demo: News website crawling"""
    print("\n" + "="*80)
    print("DEMO: News Website Chain Crawling")
    print("="*80)
    
    steps = [
        ChainStep(
            name="Find Articles",
            parser=news_step1_parser,
            extract_next_urls=news_step1_extract
        ),
        ChainStep(
            name="Extract Content",
            parser=news_step2_parser,
            extract_next_urls=None
        )
    ]
    
    initial_urls = ["https://example-news.com"]
    
    crawler = ChainCrawler(
        initial_urls=initial_urls,
        steps=steps,
        storage=AggregatedStorage("news_articles.json"),
        max_workers=3,
        use_proxy=False
    )
    
    stats = crawler.crawl()
    
    print("\n✅ RESULTS:")
    print(f"   Articles Found: {stats['step_stats'].get('Find Articles', {}).get('next_urls_found', 0)}")
    print(f"   Articles Crawled: {stats['final_results']}")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("CHAIN CRAWLING EXAMPLES")
    print("="*80)
    
    # Run demos
    demo_simple_2step()
    # demo_3step_ecommerce()  # Uncomment to run
    # demo_news_crawl()  # Uncomment to run
    
    print("\n" + "="*80)
    print("✅ Chain Crawling Examples Completed!")
    print("="*80)
