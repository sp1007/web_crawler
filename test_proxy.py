import asyncio
from web_crawler import ProxyManager

async def test_all():
    proxy_mgr = ProxyManager()
    
    # Fetch proxies
    await proxy_mgr.fetch_proxies()
    print(f"Fetched {len(proxy_mgr.proxies)} proxies")
    
    # Test all với progress bar
    results = await proxy_mgr.test_all_proxies(
        timeout=10,              # Timeout cho mỗi test
        max_concurrent=20,       # Test 20 proxies cùng lúc
        show_progress=True,      # Hiện progress bar
        remove_failed=True       # Tự động xóa proxy failed
    )
    
    print(f"\n📊 Results:")
    print(f"Working: {results['working']}/{results['total']}")
    print(f"Success rate: {results['success_rate']:.1%}")
    
    # Lấy working proxies
    working = proxy_mgr.get_working_proxies()
    print(f"\n✅ {len(working)} working proxies ready!")

asyncio.run(test_all())
