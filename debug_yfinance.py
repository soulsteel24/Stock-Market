import yfinance as yf
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_symbol(symbol):
    logger.info(f"Testing {symbol}...")
    try:
        data = yf.download(symbol, period="1mo", progress=False)
        if data.empty:
            logger.error(f"{symbol} returned EMPTY data.")
        else:
            logger.info(f"{symbol} success! fetched {len(data)} rows. Last price: {data['Close'].iloc[-1]}")
    except Exception as e:
        logger.error(f"{symbol} FAILED with error: {e}")

if __name__ == "__main__":
    print("-" * 50)
    print("Testing YFinance connectivity")
    print("-" * 50)
    
    # Test 1: Known Good
    test_symbol("RELIANCE.NS")
    
    # Test 2: Reported Failing but should be good
    test_symbol("ZOMATO.NS")
    
    # Test 3: Known Dead/Merged
    test_symbol("MINDTREE.NS")
    
    # Test 4: Another Reported Failure
    test_symbol("LTI.NS")
