# Changelog

All notable changes to this project will be documented in this file.

## [1.2.0] - 2026-02-03

### Added
- `crawl_async()` for `WebCrawler` and `ChainCrawler` (safe to use inside an existing event loop)
- `JSONLStorage` for streaming large crawls without growing RAM
- Minimal CLI: `webcrawler` (via `web_crawler/cli.py`) and `python -m web_crawler`

### Changed
- Default SSL verification is now enabled (`verify_ssl=True` by default)
- `ChainCrawler` now runs each step concurrently (true async workers)
- Retry now uses exponential backoff with jitter

### Fixed
- SOCKS proxies are now supported in `ChainCrawler` and `ProxyManager` validation
- `motor` dependency is no longer required by default (install via extras: `pip install web-crawler[mongodb]`)

## [1.1.0] - 2024-02-02

### Added
- Chain crawling support (`ChainCrawler`, `ChainStep`)
- Progress bars with `tqdm`

### Enhanced
- Proxy management improvements (auto-refetch, validation, statistics)

## [1.0.0] - 2024-02-02

### Added
- Async web crawling with `aiohttp`
- Proxy rotation with free proxy sources
- Custom parser support
- Storage backends:
  - `PerURLStorage`
  - `AggregatedStorage`
  - `MongoDBStorage`

