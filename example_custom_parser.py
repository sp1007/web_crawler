"""
Example 2: Sử dụng custom parser để extract dữ liệu cụ thể
"""

import logging
from bs4 import BeautifulSoup
from web_crawler import WebCrawler, PerURLStorage

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def custom_parser(url: str, html_content: str) -> dict:
    """
    Custom parser để extract thông tin cụ thể
    
    Args:
        url: URL của trang
        html_content: HTML content
        
    Returns:
        dict: Dữ liệu đã parse
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract title
    title = soup.title.string if soup.title else "No title"
    
    # Extract all headings
    headings = {
        'h1': [h.get_text().strip() for h in soup.find_all('h1')],
        'h2': [h.get_text().strip() for h in soup.find_all('h2')],
        'h3': [h.get_text().strip() for h in soup.find_all('h3')],
    }
    
    # Extract meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    description = meta_desc['content'] if meta_desc and meta_desc.get('content') else ""
    
    # Extract all images
    images = [img.get('src') for img in soup.find_all('img', src=True)]
    
    # Extract all external links
    external_links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('http') and url not in href:
            external_links.append(href)
    
    return {
        'title': title,
        'description': description,
        'headings': headings,
        'images_count': len(images),
        'images': images[:5],  # Top 5 images
        'external_links_count': len(external_links),
        'external_links': external_links[:10]  # Top 10 external links
    }


# URLs để crawl
urls = [
    "https://www.python.org",
    "https://docs.python.org/3/",
    "https://pypi.org",
]

# Tạo crawler với custom parser và PerURLStorage
crawler = WebCrawler(
    urls=urls,
    parser=custom_parser,  # Sử dụng custom parser
    storage=PerURLStorage(output_dir="results_per_url"),  # Lưu từng file riêng
    max_workers=3,
    use_proxy=True
)

# Crawl
stats = crawler.crawl()

print("\n=== Crawl Statistics ===")
print(f"Total URLs: {stats['total']}")
print(f"Success: {stats['success']}")
print(f"Failed: {stats['failed']}")
print(f"Duration: {stats['duration']}s")
print(f"\nResults saved to: results_per_url/")
