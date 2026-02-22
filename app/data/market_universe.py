import io
import logging
from typing import List
import pandas as pd
import requests

logger = logging.getLogger(__name__)

NSE_EQUITY_URL = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"

# Fallback top 50 in case NSE website blocks us
FALLBACK_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK",
    "LT", "HCLTECH", "AXISBANK", "ASIANPAINT", "MARUTI",
    "SUNPHARMA", "TITAN", "BAJFINANCE", "DMART", "ULTRACEMCO",
    "WIPRO", "NESTLEIND", "POWERGRID", "ONGC", "NTPC",
    "JSWSTEEL", "TATAMOTORS", "M&M", "ADANIENT", "ADANIPORTS",
    "COALINDIA", "TECHM", "HINDALCO", "INDUSINDBK", "TATASTEEL",
    "GRASIM", "DRREDDY", "CIPLA", "BPCL", "APOLLOHOSP",
    "EICHERMOT", "BRITANNIA", "DIVISLAB", "HEROMOTOCO", "BAJAJ-AUTO",
    "SBILIFE", "HDFCLIFE", "TATACONSUM", "BAJAJFINSV", "UPL"
]

_cached_symbols = []

def fetch_nse_symbols() -> List[str]:
    """Fetch active equity symbols directly from NSE archives."""
    try:
        import subprocess
        # Use curl to bypass NSE blocking that hangs Python requests
        result = subprocess.run(
            ["curl", "-s", "-H", "User-Agent: Mozilla/5.0", NSE_EQUITY_URL],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0 or not result.stdout.strip():
            raise ValueError(f"Curl failed with code {result.returncode}")
            
        # Load directly into pandas
        df = pd.read_csv(io.StringIO(result.stdout))
        
        # Clean column names (strip whitespace)
        df.columns = df.columns.str.strip()
        
        if 'SYMBOL' not in df.columns:
            logger.error("SYMBOL column not found in NSE data.")
            return list(FALLBACK_STOCKS)
            
        # Extract and format symbols
        symbols = df['SYMBOL'].str.strip().tolist()
        formatted_symbols = [sym for sym in symbols if isinstance(sym, str) and sym.strip()]
        
        logger.info(f"Successfully fetched {len(formatted_symbols)} symbols from NSE.")
        return formatted_symbols
        
    except Exception as e:
        logger.error(f"Failed to fetch NSE symbols: {e}")
        logger.warning("Falling back to hardcoded Nifty 50 list.")
        return list(FALLBACK_STOCKS)

def get_all_nse_symbols() -> List[str]:
    """Get all NSE symbols, using in-memory cache if available."""
    global _cached_symbols
    if not _cached_symbols:
        _cached_symbols = fetch_nse_symbols()
    return _cached_symbols
