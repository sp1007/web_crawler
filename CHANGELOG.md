# Changelog

All notable changes to this project will be documented in this file.

## [1.1.0] - 2024-02-02

### ⭐ Added
- **Chain Crawling** - Multi-step crawling support
  - New `ChainCrawler` class for sequential URL extraction
  - New `ChainStep` class to define crawl steps
  - Support for unlimited chain depth
  - Per-step statistics tracking
  - URL limiting per step with `max_urls_per_step`
  - Example file: `example_chain_crawling.py`

- **Progress Bar** 📊 - Visual progress tracking
  - Real-time progress bar with tqdm
  - Shows current progress, speed, and ETA
  - Works for both WebCrawler and ChainCrawler
  - Per-step progress in chain crawling
  - Can be disabled with `show_progress=False`
  - Example file: `example_progress_bar.py`

### 🔧 Enhanced
- **Proxy Management**
  - Auto-refetch proxies when running out
  - Better proxy validation
  - New `get_stats()` method for proxy statistics
  - Improved error handling and logging
  - Automatic failed proxy list reset

### 📚 Documentation
- Added `NEW_FEATURES.md` - Detailed guide for new features
- Updated `README.md` with chain crawling examples
- Added chain crawling examples and use cases
- Updated API documentation

### 🐛 Fixed
- Proxy exhaustion issues
- Better error messages for proxy failures
- Improved async proxy management

## [1.0.0] - 2024-02-02

### Initial Release
- Async web crawling with aiohttp
- Multi-threading support (configurable workers)
- Proxy rotation with free proxy sources
- Custom parser support
- Three storage backends:
  - PerURLStorage
  - AggregatedStorage
  - MongoDBStorage
- Retry mechanism with exponential backoff
- Comprehensive logging
- Statistics tracking
- Complete documentation
- Multiple examples
- Quick test suite

### Features
- WebCrawler class for single-step crawling
- ProxyManager for proxy management
- StorageBackend abstract class
- Full async/await support
- Error handling and recovery
- Configurable timeouts and retries

### Documentation
- README.md
- USAGE_GUIDE.md
- PROJECT_STRUCTURE.md
- QUICKSTART.md
- Examples (basic, custom parser, MongoDB, advanced)
- Test files

---

**Legend:**
- ⭐ Added: New features
- 🔧 Enhanced: Improvements to existing features
- 🐛 Fixed: Bug fixes
- 📚 Documentation: Documentation updates
- ⚠️ Deprecated: Features to be removed
- 🗑️ Removed: Removed features
