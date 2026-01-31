"""FastAPI routes for the stock analysis API."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
import logging

from app.services.database import get_db
from app.services.stock_analyzer import stock_analyzer
from app.services.memory_loop import memory_loop
from app.services.gemini_client import gemini_client
from app.models.schemas import (
    StockAnalysisRequest,
    BatchAnalysisRequest,
    StockAnalysisResponse,
    BatchAnalysisResponse,
    LessonResponse,
    HealthResponse
)
from app import __version__

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API health status."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        gemini_connected=gemini_client.is_connected(),
        database_connected=True  # Would add actual check
    )


@router.post("/analyze/{symbol}", response_model=StockAnalysisResponse)
async def analyze_stock(
    symbol: str,
    include_news: bool = True,
    include_technicals: bool = True,
    db: Session = Depends(get_db)
):
    """
    Analyze a single stock.
    
    Returns complete analysis with recommendation, price targets,
    confidence score, and SEBI disclaimer.
    """
    try:
        result = await stock_analyzer.analyze_stock(
            symbol=symbol,
            db=db,
            include_news=include_news,
            include_technicals=include_technicals
        )
        
        # Store recommendation for memory loop
        await memory_loop.store_recommendation(
            db=db,
            symbol=result.symbol,
            recommendation_type=result.recommendation.value,
            confidence_score=result.confidence_score,
            entry_price=result.entry_price,
            target_price=result.target_price,
            stop_loss=result.stop_loss,
            investment_thesis=result.investment_thesis,
            technical_score=result.confidence_breakdown.technical_score,
            financial_score=result.confidence_breakdown.financial_score,
            sentiment_score=result.confidence_breakdown.sentiment_score,
            sentiment_type=result.sentiment_analysis.overall_sentiment.value if result.sentiment_analysis else None,
            divergence_warning=len([w for w in result.warnings if "DIVERGENCE" in w.type]) > 0,
            safety_veto_applied=result.safety_veto_applied
        )
        
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Analysis error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/analyze/batch", response_model=BatchAnalysisResponse)
async def analyze_batch(
    request: BatchAnalysisRequest,
    db: Session = Depends(get_db)
):
    """
    Analyze multiple stocks in parallel.
    
    Supports 1-10 stocks per request for efficient batch processing.
    """
    if len(request.symbols) > 10:
        raise HTTPException(
            status_code=400, 
            detail="Maximum 10 stocks per batch request"
        )
    
    try:
        result = await stock_analyzer.analyze_batch(
            symbols=request.symbols,
            db=db,
            include_news=request.include_news,
            include_technicals=request.include_technicals
        )
        
        return BatchAnalysisResponse(
            total_analyzed=result["total_analyzed"],
            successful=result["successful"],
            failed=result["failed"],
            results=result["results"],
            errors=result["errors"]
        )
    except Exception as e:
        logger.error(f"Batch analysis error: {e}")
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")


@router.get("/recommendations")
async def get_recommendations(
    symbol: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get historical recommendations."""
    from app.models.database import Recommendation, Stock
    from sqlalchemy import desc
    
    query = db.query(Recommendation).join(Stock)
    
    if symbol:
        query = query.filter(Stock.symbol == symbol.upper())
    
    recommendations = query.order_by(desc(Recommendation.created_at)).limit(limit).all()
    
    return [
        {
            "id": r.id,
            "symbol": r.stock.symbol,
            "recommendation": r.recommendation_type.value,
            "confidence_score": r.confidence_score,
            "entry_price": r.entry_price,
            "target_price": r.target_price,
            "stop_loss": r.stop_loss_price,
            "outcome": r.outcome.value,
            "created_at": r.created_at.isoformat()
        }
        for r in recommendations
    ]


@router.post("/recommendations/{recommendation_id}/outcome")
async def update_recommendation_outcome(
    recommendation_id: int,
    outcome: str,
    exit_price: float,
    db: Session = Depends(get_db)
):
    """
    Update the outcome of a recommendation.
    
    Valid outcomes: TARGET_HIT, STOPLOSS_HIT, EXPIRED
    """
    valid_outcomes = ["TARGET_HIT", "STOPLOSS_HIT", "EXPIRED"]
    if outcome not in valid_outcomes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid outcome. Must be one of: {valid_outcomes}"
        )
    
    try:
        result = await memory_loop.update_outcome(
            db=db,
            recommendation_id=recommendation_id,
            outcome=outcome,
            actual_exit_price=exit_price
        )
        return {"message": "Outcome updated", "recommendation_id": result.id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/lessons", response_model=List[LessonResponse])
async def get_lessons(
    symbol: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get learned lessons from past predictions."""
    lessons = await memory_loop.get_relevant_lessons(
        db=db,
        symbol=symbol.upper() if symbol else None,
        limit=limit
    )
    
    return [
        LessonResponse(
            id=lesson["id"],
            symbol=lesson["symbol"],
            lesson_type=lesson["lesson_type"],
            lesson_text=lesson["lesson_text"],
            primary_cause=lesson["primary_cause"],
            created_at=lesson["created_at"]
        )
        for lesson in lessons
    ]


@router.get("/technical/{symbol}")
async def get_technical_analysis(symbol: str):
    """Get raw technical analysis data for a stock."""
    from app.services.technical_analyzer import technical_analyzer
    
    result = await technical_analyzer.analyze(symbol)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Could not fetch data for {symbol}"
        )
    
    return result


@router.get("/sentiment/{symbol}")
async def get_sentiment_analysis(symbol: str):
    """Get sentiment analysis for a stock."""
    from app.services.sentiment_analyzer import sentiment_analyzer
    
    result = await sentiment_analyzer.analyze_news(symbol)
    return {
        "symbol": symbol,
        "overall_sentiment": result.overall_sentiment.value,
        "confidence": result.confidence,
        "positive_count": result.positive_count,
        "neutral_count": result.neutral_count,
        "negative_count": result.negative_count,
        "key_headlines": result.key_headlines
    }


@router.get("/market/vix")
async def get_india_vix():
    """Get current India VIX value."""
    from app.services.technical_analyzer import technical_analyzer
    from app.config import get_settings
    
    settings = get_settings()
    vix = await technical_analyzer.get_india_vix()
    
    return {
        "india_vix": vix,
        "threshold": settings.vix_threshold,
        "high_volatility": vix > settings.vix_threshold if vix else None
    }


@router.get("/fundamentals/{symbol}")
async def get_fundamentals(symbol: str):
    """
    Get comprehensive fundamental analysis for a stock.
    
    Includes:
    - P/E, P/B, PEG ratios
    - ROE, ROA, Profit margins
    - Debt/Equity, Current ratio
    - Earnings growth, Revenue growth
    - Stock-specific news sentiment
    - Overall fundamental score and recommendation
    """
    from app.services.fundamental_analyzer import fundamental_analyzer
    
    result = await fundamental_analyzer.full_fundamental_analysis(symbol.upper())
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.get("/fundamentals/{symbol}/ratios")
async def get_ratios_only(symbol: str):
    """Get just the key financial ratios for a stock."""
    from app.services.fundamental_analyzer import fundamental_analyzer
    
    data = await fundamental_analyzer.get_fundamentals(symbol.upper())
    
    if not data or "error" in data:
        raise HTTPException(status_code=404, detail="Could not fetch fundamentals")
    
    return {
        "symbol": symbol.upper(),
        "company_name": data.get("company_name"),
        "pe_ratio": data.get("pe_ratio"),
        "pb_ratio": data.get("pb_ratio"),
        "roe": data.get("roe"),
        "debt_to_equity": data.get("debt_to_equity"),
        "current_ratio": data.get("current_ratio"),
        "dividend_yield": data.get("dividend_yield"),
        "eps_ttm": data.get("eps_ttm"),
        "profit_margin": data.get("profit_margin"),
        "market_cap_cr": data.get("market_cap_cr"),
        "data_source": data.get("data_source")
    }


@router.get("/fundamentals/{symbol}/news")
async def get_stock_news(symbol: str, limit: int = 10):
    """Get news and sentiment for a specific stock."""
    from app.services.fundamental_analyzer import fundamental_analyzer
    from app.services.financial_news_scraper import financial_news_scraper
    
    # Get sentiment analysis
    sentiment = await fundamental_analyzer.get_stock_news_sentiment(symbol.upper())
    
    # Get full news articles
    news = financial_news_scraper.get_stock_news(symbol.upper(), limit)
    
    return {
        "symbol": symbol.upper(),
        "sentiment": sentiment,
        "news": news
    }



# Nifty 50 stocks for daily scanning
NIFTY_50_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK",
    "LT", "HCLTECH", "AXISBANK", "ASIANPAINT", "MARUTI",
    "SUNPHARMA", "TITAN", "BAJFINANCE", "DMART", "ULTRACEMCO",
    "WIPRO", "NESTLEIND", "POWERGRID", "ONGC", "NTPC",
    "JSWSTEEL", "TATAMOTORS", "M&M", "ADANIENT", "ADANIPORTS",
    "COALINDIA", "TECHM", "HINDALCO", "INDUSINDBK", "TATASTEEL",
    "GRASIM", "DRREDDY", "CIPLA", "BPCL", "APOLLOHOSP",
    "EICHERMOT", "BRITANNIA", "DIVISLAB", "HEROMOTOCO", "BAJAJ-AUTO",
    "SBILIFE", "HDFCLIFE", "TATACONSUM", "BAJAJFINSV", "UPL"
]


@router.get("/top-picks")
async def get_top_picks(
    limit: int = 5,
    max_stocks: int = 500,
    use_cache: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get top buy and sell recommendations from ALL stocks.
    
    Analyzes up to 500 stocks and returns:
    - Top 5 BUY recommendations (highest confidence)
    - Top 5 SELL recommendations (highest confidence)
    
    Uses pre-market cached results if available (faster).
    Set use_cache=false to force fresh analysis.
    """
    from app.services.premarket_analyzer import pre_market_analyzer
    
    # Check for cached results
    if use_cache:
        cached = pre_market_analyzer.get_cached_picks()
        if cached:
            return {
                **cached,
                "buy_recommendations": cached.get("buy_recommendations", [])[:limit],
                "sell_recommendations": cached.get("sell_recommendations", [])[:limit],
                "from_cache": True
            }
    
    # No cache - run fresh analysis
    import asyncio
    from app.services.technical_analyzer import technical_analyzer
    from app.data.stock_universe import ALL_STOCKS
    
    buy_picks = []
    sell_picks = []
    analyzed_count = 0
    failed_count = 0
    
    # Use full stock universe (up to max_stocks)
    stocks_to_analyze = ALL_STOCKS[:max_stocks]
    
    async def analyze_quick(symbol: str):
        """Quick analysis for ranking."""
        try:
            tech_data = await technical_analyzer.analyze(symbol)
            if not tech_data or not tech_data.get("current_price"):
                return None
            
            rsi = tech_data.get("rsi", 50)
            price_above_ema = tech_data.get("price_above_ema", False)
            tech_score = tech_data.get("technical_score", 50)
            
            # Scoring logic
            if rsi < 35 and tech_score > 60:
                signal = "BUY"
                confidence = min(85, 50 + (35 - rsi) + tech_score / 5)
            elif rsi > 65 and tech_score < 40:
                signal = "SELL"
                confidence = min(85, 50 + (rsi - 65) + (100 - tech_score) / 5)
            elif price_above_ema and tech_score > 70:
                signal = "BUY"
                confidence = 55 + tech_score / 10
            elif not price_above_ema and tech_score < 35:
                signal = "SELL"
                confidence = 55 + (100 - tech_score) / 10
            else:
                signal = "HOLD"
                confidence = 50
            
            return {
                "symbol": symbol,
                "signal": signal,
                "confidence": round(confidence, 1),
                "current_price": tech_data.get("current_price"),
                "rsi": round(rsi, 1) if rsi else None,
                "change_pct": round(tech_data.get("change_pct", 0), 2),
                "data_source": tech_data.get("data_source", "unknown")
            }
        except Exception as e:
            return None
    
    # Analyze stocks in parallel (batches of 20 for speed)
    batch_size = 20
    for i in range(0, len(stocks_to_analyze), batch_size):
        batch = stocks_to_analyze[i:i+batch_size]
        tasks = [analyze_quick(s) for s in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if result and not isinstance(result, Exception):
                analyzed_count += 1
                if result["signal"] == "BUY":
                    buy_picks.append(result)
                elif result["signal"] == "SELL":
                    sell_picks.append(result)
            else:
                failed_count += 1
    
    # Sort by confidence (descending)
    buy_picks.sort(key=lambda x: x["confidence"], reverse=True)
    sell_picks.sort(key=lambda x: x["confidence"], reverse=True)
    
    return {
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "market_status": "Open" if 9 <= __import__("datetime").datetime.now().hour < 16 else "Closed",
        "buy_recommendations": buy_picks[:limit],
        "sell_recommendations": sell_picks[:limit],
        "total_analyzed": analyzed_count,
        "total_attempted": len(stocks_to_analyze),
        "failed": failed_count,
        "disclaimer": "⚠️ This is AI-generated analysis for educational purposes only. Not financial advice."
    }



@router.get("/stocks/list")
async def get_stock_list(sector: Optional[str] = None):
    """Get list of available stocks for analysis."""
    from app.data.stock_universe import (
        ALL_STOCKS, NIFTY_50, NIFTY_NEXT_50, NIFTY_MIDCAP_100,
        SECTOR_STOCKS, get_stocks_by_sector
    )
    
    if sector:
        stocks = get_stocks_by_sector(sector)
        return {
            "sector": sector,
            "stocks": stocks,
            "total_count": len(stocks)
        }
    
    return {
        "nifty_50": NIFTY_50,
        "nifty_next_50": NIFTY_NEXT_50[:20],  # Sample
        "sectors": list(SECTOR_STOCKS.keys()),
        "total_stocks": len(ALL_STOCKS),
        "note": "Use ?sector=banking|it|pharma|auto|fmcg|metal|energy|realty for sector-specific lists"
    }


@router.get("/news/financial")
async def get_financial_news(category: str = "market", limit: int = 20):
    """
    Get comprehensive financial news.
    
    Categories: market, nifty, sensex, ipo, earnings, rbi, fii, global
    """
    from app.services.financial_news_scraper import financial_news_scraper
    
    news = financial_news_scraper.get_market_news(category, limit)
    
    return {
        "category": category,
        "news": news,
        "count": len(news),
        "available_categories": ["market", "nifty", "sensex", "ipo", "earnings", "rbi", "fii", "global"]
    }


@router.get("/news/trending")
async def get_trending_news(limit: int = 30):
    """Get trending financial news from multiple sources."""
    from app.services.financial_news_scraper import financial_news_scraper
    
    news = financial_news_scraper.get_trending_news(limit)
    
    return {
        "news": news,
        "count": len(news),
        "source": "Google News RSS"
    }


@router.get("/news/all")
async def get_all_financial_news():
    """Get news from all financial categories."""
    from app.services.financial_news_scraper import financial_news_scraper
    
    all_news = financial_news_scraper.get_all_financial_news(10)
    
    return {
        "categories": all_news,
        "total_articles": sum(len(v) for v in all_news.values())
    }


@router.get("/top-picks/sector/{sector}")
async def get_sector_top_picks(
    sector: str,
    limit: int = 5,
    db: Session = Depends(get_db)
):
    """
    Get top buy and sell recommendations for a specific sector.
    
    Sectors: banking, it, pharma, auto, fmcg, metal, energy, realty
    """
    import asyncio
    from app.data.stock_universe import get_stocks_by_sector
    from app.services.technical_analyzer import technical_analyzer
    
    stocks = get_stocks_by_sector(sector)
    if not stocks:
        raise HTTPException(status_code=404, detail=f"Unknown sector: {sector}")
    
    buy_picks = []
    sell_picks = []
    
    async def analyze_quick(symbol: str):
        try:
            tech_data = await technical_analyzer.analyze(symbol)
            if not tech_data or not tech_data.get("current_price"):
                return None
            
            rsi = tech_data.get("rsi", 50)
            tech_score = tech_data.get("technical_score", 50)
            price_above_ema = tech_data.get("price_above_ema", False)
            
            if rsi < 35 and tech_score > 60:
                signal = "BUY"
                confidence = min(85, 50 + (35 - rsi) + tech_score / 5)
            elif rsi > 65 and tech_score < 40:
                signal = "SELL"
                confidence = min(85, 50 + (rsi - 65))
            elif price_above_ema and tech_score > 70:
                signal = "BUY"
                confidence = 55 + tech_score / 10
            else:
                signal = "HOLD"
                confidence = 50
            
            return {
                "symbol": symbol,
                "signal": signal,
                "confidence": round(confidence, 1),
                "current_price": tech_data.get("current_price"),
                "rsi": round(rsi, 1) if rsi else None,
                "change_pct": round(tech_data.get("change_pct", 0), 2)
            }
        except:
            return None
    
    tasks = [analyze_quick(s) for s in stocks[:15]]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if result and not isinstance(result, Exception):
            if result["signal"] == "BUY":
                buy_picks.append(result)
            elif result["signal"] == "SELL":
                sell_picks.append(result)
    
    buy_picks.sort(key=lambda x: x["confidence"], reverse=True)
    sell_picks.sort(key=lambda x: x["confidence"], reverse=True)
    
    return {
        "sector": sector,
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "buy_recommendations": buy_picks[:limit],
        "sell_recommendations": sell_picks[:limit],
        "stocks_analyzed": len(stocks[:15])
    }


@router.post("/premarket/run")
async def run_premarket_analysis(
    max_stocks: int = 500,
    background_tasks: BackgroundTasks = None
):
    """
    Trigger pre-market analysis for all stocks.
    
    Run this before 9:15 AM IST to have cached results ready.
    Analysis of 500 stocks takes approximately 10-15 minutes.
    """
    from app.services.premarket_analyzer import pre_market_analyzer
    
    if pre_market_analyzer.is_running:
        return {
            "status": "already_running",
            "message": "Pre-market analysis is already in progress"
        }
    
    # Run in background
    import asyncio
    asyncio.create_task(pre_market_analyzer.run_full_analysis(max_stocks))
    
    return {
        "status": "started",
        "message": f"Pre-market analysis started for {max_stocks} stocks",
        "note": "Results will be cached and available via /top-picks endpoint"
    }


@router.get("/premarket/status")
async def get_premarket_status():
    """Get status of pre-market analysis and cached data."""
    from app.services.premarket_analyzer import pre_market_analyzer
    
    cached = pre_market_analyzer.get_cached_picks()
    
    return {
        "is_running": pre_market_analyzer.is_running,
        "last_analysis_date": pre_market_analyzer.last_analysis_date,
        "cache_available": cached is not None,
        "cached_stats": {
            "total_analyzed": cached.get("total_analyzed") if cached else 0,
            "buy_signals": cached.get("all_buy_signals") if cached else 0,
            "sell_signals": cached.get("all_sell_signals") if cached else 0,
            "generated_at": cached.get("generated_at") if cached else None
        } if cached else None
    }
