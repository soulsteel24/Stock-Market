import yfinance as yf
import json

def test_stock_details(symbol):
    print(f"Fetching details for {symbol}...")
    ticker = yf.Ticker(symbol)
    
    # 1. Info Dict (Fundamentals)
    try:
        info = ticker.info
        print("\n--- Key Fundamentals ---")
        keys_of_interest = [
            'forwardPE', 'trailingPE', 'marketCap', 
            'profitMargins', 'ebitda', 'returnOnEquity',
            'debtToEquity', 'currentRatio', 'heldPercentInsiders', 
            'heldPercentInstitutions'
        ]
        for k in keys_of_interest:
            print(f"{k}: {info.get(k)}")
    except Exception as e:
        print(f"Error fetching info: {e}")

    # 2. Financials (Net Profit check)
    try:
        print("\n--- Financials ---")
        fin = ticker.financials
        if not fin.empty:
            print(fin.head(5))
        else:
            print("No financials found.")
    except Exception as e:
        print(f"Error fetching financials: {e}")

if __name__ == "__main__":
    test_stock_details("RELIANCE.NS")
