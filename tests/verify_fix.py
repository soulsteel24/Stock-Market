import asyncio
import sys
import os

# Add app to path
sys.path.append(os.getcwd())

from app.services.premarket_analyzer import pre_market_analyzer
from app.services.stock_analyzer import stock_analyzer

async def verify():
    print("1. Generatign Top Picks (Fresh with Validation)...")
    # Reduce max stocks for speed in test
    print("Starting scan...", flush=True)
    result = await pre_market_analyzer.generate_safe_picks(max_stocks=10)
    
    top_buy = result["buy_recommendations"][0] if result["buy_recommendations"] else None
    
    if not top_buy:
        print("No buy picks found to verify!")
        return

    print(f"Top Buy Pick: {top_buy['symbol']} (Confidence: {top_buy['confidence']})")
    
    print(f"2. analyzing {top_buy['symbol']} via stock_analyzer (Search)...")
    analysis = await stock_analyzer.analyze_stock(top_buy['symbol'], include_news=False)
    
    print(f"Search Recommendation: {analysis.recommendation.value}")
    print(f"Search Confidence: {analysis.confidence_score}")
    
    if analysis.recommendation.value == "BUY":
        print("SUCCESS: Recommendation Matches!")
    else:
        print(f"FAILURE: Mismatch! Dashboard said BUY, Search says {analysis.recommendation.value}")

if __name__ == "__main__":
    asyncio.run(verify())
