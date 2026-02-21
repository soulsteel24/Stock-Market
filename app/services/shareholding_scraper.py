"""Scraper for fundamental shareholding data (FII, DII, Promoters)."""
import logging
import asyncio
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
import requests

logger = logging.getLogger(__name__)


class ShareholdingScraper:
    """Scrapes shareholding patterns from public screeners."""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
    
    async def get_shareholding(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        Fetch shareholding data for a given NSE symbol.
        Returns latest percentages for Promoters, FIIs, and DIIs.
        """
        # Using a thread to safely execute sync requests in async environment
        return await asyncio.get_event_loop().run_in_executor(
            None, self._scrape_screener, symbol
        )
        
    def _scrape_screener(self, symbol: str) -> Optional[Dict[str, float]]:
        """Scrapes screener.in for shareholding data."""
        try:
            # Screener uses standard symbols, mostly same as NSE
            url = f"https://www.screener.in/company/{symbol}/consolidated/"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            # Fallback to standalone if consolidated doesn't exist
            if response.status_code != 200:
                url = f"https://www.screener.in/company/{symbol}/"
                response = requests.get(url, headers=self.headers, timeout=10)
                
            if response.status_code != 200:
                logger.warning(f"Could not fetch shareholding for {symbol} from screener.")
                return None
                
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the Shareholding Pattern section
            section = soup.find('section', id='shareholding')
            if not section:
                return None
                
            table = section.find('table')
            if not table:
                return None
                
            # Parse table rows
            rows = table.find('tbody').find_all('tr')
            
            data = {}
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 2:
                    label = cols[0].text.strip().lower()
                    # Get the most recent quarter (last column)
                    val_str = cols[-1].text.strip()
                    try:
                        val = float(val_str.replace('%', ''))
                    except ValueError:
                        continue
                        
                    if 'promoters' in label:
                        data['promoter_holding_pct'] = val
                    elif 'fii' in label or 'foreign' in label:
                        data['fii_holding_pct'] = val
                    elif 'dii' in label or 'domestic' in label:
                        data['dii_holding_pct'] = val
                    elif 'public' in label:
                        data['public_holding_pct'] = val
            
            # If we successfully parsed at least promoters
            if 'promoter_holding_pct' in data:
                return data
                
            return None
            
        except Exception as e:
            logger.error(f"Error scraping shareholding for {symbol}: {e}")
            return None

shareholding_scraper = ShareholdingScraper()
