
import asyncio
import sys
import os
import pandas as pd
import yfinance as yf

# Add current directory to path
sys.path.append(os.getcwd())

from app.services.technical_analyzer import technical_analyzer

async def debug_scan():
    print("--- Debugging scan_batched ---")
    
    # Test with a small subset of stocks
    test_stocks = ["RELIANCE", "TCS", "INFY"]
    print(f"Testing symbols: {test_stocks}")
    
    # Manually invoke the download logic to inspect structure
    yf_symbols = [f"{s}.NS" for s in test_stocks]
    print(f"Downloading for: {yf_symbols}")
    
    try:
        data = yf.download(
            yf_symbols, 
            period="1mo",  # Try shorter period
            group_by='ticker', 
            threads=True,
            progress=False
        )
        
        print(f"\nDownload Type: {type(data)}")
        print(f"Columns: {data.columns}")
        if isinstance(data.columns, pd.MultiIndex):
            print("Columns is MultiIndex")
            print(f"Levels: {data.columns.levels}")
            
        print(f"\nShape: {data.shape}")
        print("\nHead:")
        print(data.head())
        
        # Now try to access data like the code does
        print("\n--- Simulating Extraction Loop ---")
        for symbol in test_stocks:
            yf_sym = f"{symbol}.NS"
            print(f"Processing {yf_sym}...")
            try:
                # Logic from technical_analyzer.py
                try:
                    df = data[yf_sym].copy()
                    print(f"  [SUCCESS] Accessed via data['{yf_sym}']")
                except KeyError:
                    print(f"  [FAIL] data['{yf_sym}'] not found")
                    try:
                        df = data[symbol].copy()
                        print(f"  [SUCCESS] Accessed via data['{symbol}']")
                    except KeyError:
                        print(f"  [FAIL] data['{symbol}'] not found")
                        continue
                
                print(f"  Rows: {len(df)}")
                
            except Exception as e:
                print(f"  Error: {e}")

    except Exception as e:
        print(f"Download failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_scan())
