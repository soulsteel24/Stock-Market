
import asyncio
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from app.data.stock_universe import ALL_STOCKS
from app.services.technical_analyzer import technical_analyzer

async def main():
    print(f"Total stocks: {len(ALL_STOCKS)}")
    stocks = ALL_STOCKS[:10]
    print(f"Testing with: {stocks}")
    
    try:
        print("Calling scan_batched...")
        results = await technical_analyzer.scan_batched(stocks)
        print(f"Results: {len(results)}")
        print("Success!")
    except Exception as e:
        print(f"Error caught: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
