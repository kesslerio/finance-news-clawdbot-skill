#!/usr/bin/env python3
"""
News Fetcher - Aggregate news from multiple sources.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
import xml.etree.ElementTree as ET
import urllib.request
import urllib.error

SCRIPT_DIR = Path(__file__).parent
CONFIG_DIR = SCRIPT_DIR.parent / "config"
CACHE_DIR = SCRIPT_DIR.parent / "cache"

# Ensure cache directory exists
CACHE_DIR.mkdir(exist_ok=True)


def load_sources():
    """Load source configuration."""
    with open(CONFIG_DIR / "sources.json", 'r') as f:
        return json.load(f)


def fetch_rss(url: str, limit: int = 10) -> list[dict]:
    """Fetch and parse RSS feed."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Clawdbot/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read()
        
        root = ET.fromstring(content)
        items = []
        
        # Handle both RSS 2.0 and Atom formats
        for item in root.findall('.//item')[:limit]:
            title = item.find('title')
            link = item.find('link')
            pub_date = item.find('pubDate')
            description = item.find('description')
            
            items.append({
                'title': title.text if title is not None else '',
                'link': link.text if link is not None else '',
                'date': pub_date.text if pub_date is not None else '',
                'description': (description.text or '')[:200] if description is not None else ''
            })
        
        return items
    except Exception as e:
        print(f"⚠️ Error fetching {url}: {e}", file=sys.stderr)
        return []


def fetch_market_data(symbols: list[str]) -> dict:
    """Fetch market data using openbb-quote."""
    results = {}
    
    for symbol in symbols:
        try:
            result = subprocess.run(
                ['/home/art/.local/bin/openbb-quote', symbol],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                results[symbol] = data
        except Exception as e:
            print(f"⚠️ Error fetching {symbol}: {e}", file=sys.stderr)
    
    return results


def fetch_ticker_news(symbol: str, limit: int = 5) -> list[dict]:
    """Fetch news for a specific ticker via Yahoo Finance RSS."""
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
    return fetch_rss(url, limit)


def get_cached_news(cache_key: str) -> dict | None:
    """Get cached news if fresh (< 15 minutes)."""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    if cache_file.exists():
        mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
        if datetime.now() - mtime < timedelta(minutes=15):
            with open(cache_file, 'r') as f:
                return json.load(f)
    
    return None


def save_cache(cache_key: str, data: dict):
    """Save news to cache."""
    cache_file = CACHE_DIR / f"{cache_key}.json"
    with open(cache_file, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def fetch_all_news(args):
    """Fetch news from all configured sources."""
    sources = load_sources()
    cache_key = f"all_news_{datetime.now().strftime('%Y%m%d_%H')}"
    
    # Check cache first
    if not args.force:
        cached = get_cached_news(cache_key)
        if cached:
            print(json.dumps(cached, indent=2))
            return
    
    news = {
        'fetched_at': datetime.now().isoformat(),
        'sources': {}
    }
    
    # Fetch RSS feeds
    for source_id, feeds in sources['rss_feeds'].items():
        news['sources'][source_id] = {
            'name': feeds.get('name', source_id),
            'articles': []
        }
        
        for feed_name, feed_url in feeds.items():
            if feed_name == 'name':
                continue
            
            articles = fetch_rss(feed_url, args.limit)
            for article in articles:
                article['feed'] = feed_name
            news['sources'][source_id]['articles'].extend(articles)
    
    # Save to cache
    save_cache(cache_key, news)
    
    if args.json:
        print(json.dumps(news, indent=2))
    else:
        for source_id, source_data in news['sources'].items():
            print(f"\n### {source_data['name']}\n")
            for article in source_data['articles'][:args.limit]:
                print(f"• {article['title']}")
                if args.verbose and article.get('description'):
                    print(f"  {article['description'][:100]}...")


def fetch_market_news(args):
    """Fetch market overview (indices + top headlines)."""
    sources = load_sources()
    
    result = {
        'fetched_at': datetime.now().isoformat(),
        'markets': {},
        'headlines': []
    }
    
    # Fetch market indices
    for region, config in sources['markets'].items():
        result['markets'][region] = {
            'name': config['name'],
            'indices': {}
        }
        
        for symbol in config['indices']:
            data = fetch_market_data([symbol])
            if symbol in data:
                result['markets'][region]['indices'][symbol] = {
                    'name': config['index_names'].get(symbol, symbol),
                    'data': data[symbol]
                }
    
    # Fetch top headlines from CNBC and Yahoo
    for source in ['cnbc', 'yahoo']:
        if source in sources['rss_feeds']:
            feeds = sources['rss_feeds'][source]
            feed_url = feeds.get('top') or feeds.get('markets') or list(feeds.values())[1]
            articles = fetch_rss(feed_url, 5)
            for article in articles:
                article['source'] = feeds.get('name', source)
            result['headlines'].extend(articles)
    
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("\n📊 Market Overview\n")
        for region, data in result['markets'].items():
            print(f"**{data['name']}**")
            for symbol, idx in data['indices'].items():
                if 'data' in idx and idx['data']:
                    price = idx['data'].get('price', 'N/A')
                    change_pct = idx['data'].get('change_percent', 0)
                    emoji = '📈' if change_pct >= 0 else '📉'
                    print(f"  {emoji} {idx['name']}: {price} ({change_pct:+.2f}%)")
            print()
        
        print("\n🔥 Top Headlines\n")
        for article in result['headlines'][:args.limit]:
            print(f"• [{article['source']}] {article['title']}")


def fetch_portfolio_news(args):
    """Fetch news for portfolio stocks."""
    # Get symbols from portfolio
    result = subprocess.run(
        ['python3', SCRIPT_DIR / 'portfolio.py', 'symbols'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print("❌ Failed to load portfolio", file=sys.stderr)
        sys.exit(1)
    
    symbols = result.stdout.strip().split(',')
    
    news = {
        'fetched_at': datetime.now().isoformat(),
        'stocks': {}
    }
    
    for symbol in symbols:
        if not symbol:
            continue
        
        articles = fetch_ticker_news(symbol, args.limit)
        quotes = fetch_market_data([symbol])
        
        news['stocks'][symbol] = {
            'quote': quotes.get(symbol, {}),
            'articles': articles
        }
    
    if args.json:
        print(json.dumps(news, indent=2))
    else:
        print(f"\n📊 Portfolio News ({len(symbols)} stocks)\n")
        for symbol, data in news['stocks'].items():
            quote = data.get('quote', {})
            price = quote.get('price', 'N/A')
            change_pct = quote.get('change_percent', 0)
            emoji = '📈' if change_pct >= 0 else '📉'
            
            print(f"\n**{symbol}** {emoji} ${price} ({change_pct:+.2f}%)")
            for article in data['articles'][:3]:
                print(f"  • {article['title'][:80]}...")


def main():
    parser = argparse.ArgumentParser(description='News Fetcher')
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    parser.add_argument('--limit', type=int, default=5, help='Max articles per source')
    parser.add_argument('--force', action='store_true', help='Bypass cache')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show descriptions')
    
    subparsers = parser.add_subparsers(dest='command', required=True)
    
    # All news
    all_parser = subparsers.add_parser('all', help='Fetch all news sources')
    all_parser.set_defaults(func=fetch_all_news)
    
    # Market news
    market_parser = subparsers.add_parser('market', help='Market overview + headlines')
    market_parser.set_defaults(func=fetch_market_news)
    
    # Portfolio news
    portfolio_parser = subparsers.add_parser('portfolio', help='News for portfolio stocks')
    portfolio_parser.set_defaults(func=fetch_portfolio_news)
    
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
