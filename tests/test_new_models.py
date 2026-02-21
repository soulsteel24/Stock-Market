"""
Test script for new ML models integration.
"""
import pytest
import pandas as pd
from app.services.finbert_client import finbert_client
from app.services.forecast_service import forecast_service

@pytest.mark.asyncio
async def test_finbert_sentiment():
    print("\nTesting FinBERT...")
    texts = [
        "Reliance Industries reports record profits, stock rallies.",
        "Market crash wipes out investors, grim outlook ahead.",
        "Company announces board meeting date."
    ]
    result = await finbert_client.analyze_batch(texts)
    print("FinBERT Result:", result)
    assert result["overall_sentiment"] in ["POSITIVE", "NEGATIVE", "NEUTRAL"]
    assert result["confidence"] > 0

@pytest.mark.asyncio
async def test_forecast_service():
    print("\nTesting Forecast Service...")
    # Create dummy data
    dates = pd.date_range(start="2023-01-01", periods=100)
    prices = [100 + i + (i%5) for i in range(100)] # Upward trend
    df = pd.DataFrame({"Date": dates, "Close": prices})
    
    result = await forecast_service.predict_prices("TEST", df, days=7)
    print("Forecast Result:", result)
    assert "forecast" in result
    assert len(result["forecast"]) == 7
    assert result["trend_pct"] > 0

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_finbert_sentiment())
    asyncio.run(test_forecast_service())
