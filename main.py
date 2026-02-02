import asyncio
from proxy_manager import ProxyManager


if __name__ == "__main__":
    proxy_manager = ProxyManager()
    asyncio.run(proxy_manager.fetch_proxies())
    print(f"Available proxies: {proxy_manager.proxies}")
    print(f"Total proxies fetched: {len(proxy_manager.proxies)}")
    
    