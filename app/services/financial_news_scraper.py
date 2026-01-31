"""Comprehensive financial news scraper for Indian markets."""
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Headers for web scraping
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

# Financial News Sources for India
NEWS_SOURCES = {
    "moneycontrol": {
        "base_url": "https://www.moneycontrol.com",
        "market_news": "https://www.moneycontrol.com/news/business/markets/",
        "stock_search": "https://www.google.com/search?q=site:moneycontrol.com+{symbol}+news"
    },
    "economictimes": {
        "base_url": "https://economictimes.indiatimes.com",
        "market_news": "https://economictimes.indiatimes.com/markets",
        "stock_search": "https://www.google.com/search?q=site:economictimes.indiatimes.com+{symbol}+stock"
    },
    "livemint": {
        "base_url": "https://www.livemint.com",
        "market_news": "https://www.livemint.com/market",
        "stock_search": "https://www.google.com/search?q=site:livemint.com+{symbol}+shares"
    },
    "businessstandard": {
        "base_url": "https://www.business-standard.com",
        "market_news": "https://www.business-standard.com/markets",
        "stock_search": "https://www.google.com/search?q=site:business-standard.com+{symbol}"
    },
    "zeebiz": {
        "base_url": "https://www.zeebiz.com",
        "market_news": "https://www.zeebiz.com/market-news",
        "stock_search": "https://www.google.com/search?q=site:zeebiz.com+{symbol}"
    }
}

# News categories
NEWS_CATEGORIES = {
    "market": "Indian stock market today",
    "nifty": "Nifty 50 index",
    "sensex": "BSE Sensex",
    "ipo": "IPO news India",
    "earnings": "quarterly results India",
    "rbi": "RBI policy news",
    "fii": "FII DII trading activity",
    "global": "global markets impact India"
}


class ComprehensiveNewsScraper:
    """Scrapes financial news from multiple Indian sources."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.cache = {}
        self.cache_ttl = timedelta(minutes=15)
    
    def _fetch_url(self, url: str, timeout: int = 10) -> Optional[BeautifulSoup]:
        """Fetch and parse a URL."""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return None
    
    def get_google_news(self, query: str, num_results: int = 10) -> List[Dict]:
        """Get news from Google News RSS."""
        try:
            # Use Google News RSS
            rss_url = f"https://news.google.com/rss/search?q={query.replace(' ', '+')}+India&hl=en-IN&gl=IN&ceid=IN:en"
            response = self.session.get(rss_url, timeout=10)
            
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.text, 'xml')
            items = soup.find_all('item')[:num_results]
            
            news = []
            for item in items:
                title = item.find('title')
                pub_date = item.find('pubDate')
                source = item.find('source')
                
                news.append({
                    "title": title.text if title else "",
                    "source": source.text if source else "Google News",
                    "published": pub_date.text if pub_date else "",
                    "url": item.find('link').text if item.find('link') else ""
                })
            
            return news
        except Exception as e:
            logger.error(f"Google News error: {e}")
            return []
    
    def get_stock_news(self, symbol: str, num_results: int = 15) -> List[Dict]:
        """Get news for a specific stock."""
        cache_key = f"stock_{symbol}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_ttl:
                return cached_data
        
        all_news = []
        
        # Get from Google News
        queries = [
            f"{symbol} stock",
            f"{symbol} shares",
            f"{symbol} company news"
        ]
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(self.get_google_news, q, 5) for q in queries]
            for future in as_completed(futures, timeout=30):
                try:
                    news = future.result()
                    all_news.extend(news)
                except Exception as e:
                    logger.warning(f"News fetch error: {e}")
        
        # Remove duplicates based on title
        seen_titles = set()
        unique_news = []
        for item in all_news:
            title_key = item["title"][:50].lower()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_news.append(item)
        
        self.cache[cache_key] = (datetime.now(), unique_news[:num_results])
        return unique_news[:num_results]
    
    def get_market_news(self, category: str = "market", num_results: int = 20) -> List[Dict]:
        """Get general market news."""
        cache_key = f"market_{category}"
        if cache_key in self.cache:
            cached_time, cached_data = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_ttl:
                return cached_data
        
        query = NEWS_CATEGORIES.get(category, "Indian stock market")
        news = self.get_google_news(query, num_results)
        
        self.cache[cache_key] = (datetime.now(), news)
        return news
    
    def get_all_financial_news(self, num_per_category: int = 10) -> Dict[str, List[Dict]]:
        """Get news from all financial categories."""
        all_news = {}
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {}
            for category in NEWS_CATEGORIES.keys():
                f = executor.submit(self.get_market_news, category, num_per_category)
                futures[f] = category
            
            for future in as_completed(futures, timeout=60):
                category = futures[future]
                try:
                    all_news[category] = future.result()
                except Exception as e:
                    logger.error(f"Failed to get {category} news: {e}")
                    all_news[category] = []
        
        return all_news
    
    def get_trending_news(self, num_results: int = 30) -> List[Dict]:
        """Get trending financial news."""
        queries = [
            "stock market India today",
            "Nifty Sensex news",
            "FII DII activity today",
            "quarterly results India",
            "IPO listing gains"
        ]
        
        all_news = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(self.get_google_news, q, 6) for q in queries]
            for future in as_completed(futures, timeout=30):
                try:
                    all_news.extend(future.result())
                except:
                    pass
        
        # Deduplicate
        seen = set()
        unique = []
        for item in all_news:
            key = item["title"][:40].lower()
            if key not in seen:
                seen.add(key)
                unique.append(item)
        
        return unique[:num_results]


# Singleton instance
financial_news_scraper = ComprehensiveNewsScraper()
