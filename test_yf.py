import yfinance as yf

ticker = yf.Ticker("TATAMOTORS.NS")
df = ticker.history(period="1y")
print(df)
