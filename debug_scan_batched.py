
import asyncio
import sys
import os
import pandas as pd
import logging

# Configure logging to show everything
logging.basicConfig(level=logging.DEBUG)

# Add current directory to path
sys.path.append(os.getcwd())

from app.services.technical_analyzer import technical_analyzer

async def main():
    print("--- Debugging scan_batched Method ---")
    
    # Test with a few known valid symbols
    test_stocks = ["RELIANCE", "TCS", "INFY"]
    print(f"Testing symbols: {test_stocks}")
    
    try:
        # Call the actual method
        results = await technical_analyzer.scan_batched(test_stocks)
        
        print(f"\nResults Count: {len(results)}")
        if results:
            print("First Result:", list(results.values())[0])
        else:
            print("No results returned!")
            
    except Exception as e:
        print(f"Method call failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
