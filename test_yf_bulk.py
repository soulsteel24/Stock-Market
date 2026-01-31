import yfinance as yf
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_download():
    symbols = ["RELIANCE.NS", "TCS.NS", "INFY.NS"]
    print(f"Downloading {len(symbols)} stocks with threads=False...")
    
    try:
        data = yf.download(
            symbols, 
            period="1y", 
            group_by='ticker', 
            threads=False,
            progress=False
        )
        
        print("\nDownload complete.")
        print(f"Data shape: {data.shape}")
        
        if not data.empty:
            print("RELIANCE.NS Close:")
            try:
                print(data["RELIANCE.NS"]["Close"].tail())
            except KeyError:
                print("Could not access RELIANCE.NS data structure directly")
                print(data.columns)
            
            return True
        else:
            print("Data is empty!")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_download()
