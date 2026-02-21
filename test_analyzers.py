import asyncio
from app.services.fundamental_analyzer import fundamental_analyzer
from app.services.technical_analyzer import technical_analyzer

async def test():
    symbol = "RELIANCE"
    print(f"Testing for {symbol}")
    
    tech = await technical_analyzer.analyze(symbol)
    fund = await fundamental_analyzer.full_fundamental_analysis(symbol)
    
    print("--- Technical Analysis ---")
    print({k: tech.get(k) for k in tech if k != 'historical_df'})
    
    print("\n--- Fundamental Analysis ---")
    print({k: fund.get(k) for k in fund if k not in ['raw_fundamentals', 'fundamental_analysis', 'news_sentiment']})
    print("\nFundamental Analysis sub-object:")
    print(fund.get('fundamental_analysis', {}).get('key_ratios'))
    
    print("\nNews Sentiment:")
    print(fund.get('news_sentiment'))
    
if __name__ == "__main__":
    asyncio.run(test())
