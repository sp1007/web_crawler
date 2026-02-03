"""
Minimal CLI for the web_crawler package.

Example:
  webcrawler https://example.com --no-proxy --storage jsonl --output out.jsonl
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Optional

from . import AggregatedStorage, JSONLStorage, MongoDBStorage, PerURLStorage, WebCrawler


def _parse_headers(header_args: Optional[list[str]]) -> dict[str, str]:
    headers: dict[str, str] = {}
    if not header_args:
        return headers
    for h in header_args:
        if ":" not in h:
            raise argparse.ArgumentTypeError(f"Invalid header '{h}'. Expected 'Key: Value'.")
        k, v = h.split(":", 1)
        headers[k.strip()] = v.strip()
    return headers


def _load_urls(args: argparse.Namespace) -> list[str]:
    urls: list[str] = []

    if args.urls_file:
        with open(args.urls_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                urls.append(line)

    if args.urls:
        urls.extend(args.urls)

    # De-duplicate while preserving order
    return list(dict.fromkeys(urls))


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="webcrawler", description="Async web crawler with proxy rotation")

    parser.add_argument("urls", nargs="*", help="URLs to crawl")
    parser.add_argument("--urls-file", help="Path to a file with one URL per line")

    parser.add_argument("--storage", choices=["aggregated", "jsonl", "per-url", "mongodb"], default="aggregated")
    parser.add_argument("--output", help="Output file (aggregated/jsonl) or directory (per-url)")

    parser.add_argument("--workers", type=int, default=8, help="Concurrency level")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout (seconds)")
    parser.add_argument("--retries", type=int, default=3, help="Max retries per URL")
    parser.add_argument("--retry-delay", type=float, default=2, help="Base retry delay (seconds)")

    parser.add_argument("--no-proxy", action="store_true", help="Disable proxy usage")
    parser.add_argument("--validate-proxies", action="store_true", help="Validate proxies before crawling")
    parser.add_argument("--proxy-file", help="Import proxies from a local file (one per line)")

    parser.add_argument("--header", action="append", help="Add request header: 'Key: Value' (can repeat)")
    parser.add_argument("--user-agent", help="Override User-Agent")
    parser.add_argument("--insecure", action="store_true", help="Disable SSL verification (not recommended)")
    parser.add_argument("--no-progress", action="store_true", help="Disable progress bar")

    parser.add_argument("--mongodb-uri", help="MongoDB connection string (required for mongodb storage)")
    parser.add_argument("--mongodb-db", default="web_crawler", help="MongoDB database name")
    parser.add_argument("--mongodb-collection", default="crawl_results", help="MongoDB collection name")

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    urls = _load_urls(args)
    if not urls:
        parser.error("No URLs provided. Pass URLs as args or use --urls-file.")

    headers = _parse_headers(args.header)

    storage = None
    if args.storage == "aggregated":
        storage = AggregatedStorage(output_file=args.output or "crawl_results.json")
    elif args.storage == "jsonl":
        storage = JSONLStorage(output_file=args.output or "crawl_results.jsonl")
    elif args.storage == "per-url":
        storage = PerURLStorage(output_dir=args.output or "crawl_results")
    elif args.storage == "mongodb":
        if not args.mongodb_uri:
            parser.error("--mongodb-uri is required when --storage=mongodb")
        storage = MongoDBStorage(
            connection_string=args.mongodb_uri,
            database=args.mongodb_db,
            collection=args.mongodb_collection,
        )

    crawler = WebCrawler(
        urls=urls,
        storage=storage,
        max_workers=args.workers,
        use_proxy=not args.no_proxy,
        timeout=args.timeout,
        max_retries=args.retries,
        retry_delay=args.retry_delay,
        show_progress=not args.no_progress,
        validate_proxies=args.validate_proxies,
        verify_ssl=not args.insecure,
        headers=headers,
        user_agent=args.user_agent,
    )

    if args.proxy_file and crawler.proxy_manager:
        crawler.proxy_manager.import_proxies(args.proxy_file)

    stats = crawler.crawl()
    sys.stdout.write(json.dumps(stats, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

