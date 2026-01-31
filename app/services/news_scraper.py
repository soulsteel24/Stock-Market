"""News scraper for BSE/NSE announcements and financial news."""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from datetime import datetime
import logging
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """News item data class."""
    title: str
    content: Optional[str]
    source: str
    url: Optional[str]
    published_at: Optional[datetime]


class NewsScraper:
    """Scraper for financial news from multiple sources."""
    
    def __init__(self):
        """Initialize news scraper."""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.timeout = 10
    
    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch page content."""
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            if response.status_code == 200:
                return response.text
            logger.warning(f"Failed to fetch {url}: Status {response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def scrape_moneycontrol_news(self, symbol: str) -> List[NewsItem]:
        """Scrape news from MoneyControl."""
        news_items = []
        url = f"https://www.moneycontrol.com/news/tags/{symbol.lower()}.html"
        
        try:
            html = self.fetch_page(url)
            if not html:
                return news_items
            
            soup = BeautifulSoup(html, 'html.parser')
            articles = soup.find_all('li', class_='clearfix')[:10]
            
            for article in articles:
                title_elem = article.find('h2')
                if title_elem:
                    link = title_elem.find('a')
                    news_items.append(NewsItem(
                        title=title_elem.get_text(strip=True),
                        content=None,
                        source="MoneyControl",
                        url=link['href'] if link else None,
                        published_at=None
                    ))
        except Exception as e:
            logger.error(f"MoneyControl scraping error: {e}")
        
        return news_items
    
    def scrape_economic_times_news(self, symbol: str) -> List[NewsItem]:
        """Scrape news from Economic Times."""
        news_items = []
        url = f"https://economictimes.indiatimes.com/topic/{symbol}"
        
        try:
            html = self.fetch_page(url)
            if not html:
                return news_items
            
            soup = BeautifulSoup(html, 'html.parser')
            articles = soup.find_all('div', class_='clr flt topicstry')[:10]
            
            for article in articles:
                title_elem = article.find('a')
                if title_elem:
                    news_items.append(NewsItem(
                        title=title_elem.get_text(strip=True),
                        content=None,
                        source="Economic Times",
                        url=f"https://economictimes.indiatimes.com{title_elem.get('href', '')}",
                        published_at=None
                    ))
        except Exception as e:
            logger.error(f"Economic Times scraping error: {e}")
        
        return news_items
    
    def get_google_finance_news(self, symbol: str) -> List[NewsItem]:
        """Get news from Google Finance."""
        news_items = []
        url = f"https://www.google.com/finance/quote/{symbol}:NSE"
        
        try:
            html = self.fetch_page(url)
            if not html:
                return news_items
            
            soup = BeautifulSoup(html, 'html.parser')
            # Look for news articles
            articles = soup.find_all('div', {'data-article-source-name': True})[:10]
            
            for article in articles:
                title_elem = article.find('a')
                source = article.get('data-article-source-name', 'Google Finance')
                if title_elem:
                    news_items.append(NewsItem(
                        title=title_elem.get_text(strip=True),
                        content=None,
                        source=source,
                        url=title_elem.get('href'),
                        published_at=None
                    ))
        except Exception as e:
            logger.error(f"Google Finance scraping error: {e}")
        
        return news_items
    
    def get_all_news(self, symbol: str) -> List[NewsItem]:
        """Aggregate news from all sources using thread pool."""
        all_news = []
        
        # Use ThreadPoolExecutor for concurrent fetching
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self.scrape_moneycontrol_news, symbol): "moneycontrol",
                executor.submit(self.scrape_economic_times_news, symbol): "et",
                executor.submit(self.get_google_finance_news, symbol): "google"
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        all_news.extend(result)
                except Exception as e:
                    logger.error(f"News scraping error: {e}")
        
        # Remove duplicates based on title
        seen_titles = set()
        unique_news = []
        for item in all_news:
            if item.title not in seen_titles:
                seen_titles.add(item.title)
                unique_news.append(item)
        
        return unique_news[:15]  # Return max 15 items
    
    # Async wrapper for compatibility with existing code
    async def get_all_news_async(self, symbol: str) -> List[NewsItem]:
        """Async wrapper for get_all_news."""
        return self.get_all_news(symbol)
    
    def news_to_dict(self, news_items: List[NewsItem]) -> List[Dict]:
        """Convert news items to dictionaries."""
        return [
            {
                "title": item.title,
                "content": item.content,
                "source": item.source,
                "url": item.url,
                "published_at": item.published_at.isoformat() if item.published_at else None
            }
            for item in news_items
        ]


# Singleton instance
news_scraper = NewsScraper()
