import asyncio
import logging
from datetime import datetime, timedelta
from app.worker import celery_app
from app.services.stock_analyzer import stock_analyzer
from app.services.database import SessionLocal
from app.models.database import Stock

logger = logging.getLogger(__name__)

async def _analyze_stock_async(symbol: str):
    db = SessionLocal()
    try:
        # Perform full analysis
        result = await stock_analyzer.analyze_stock(symbol, db, include_news=True, include_technicals=True)
        
        logger.info(f"Successfully processed {symbol}")
        
    except Exception as e:
        logger.error(f"Error processing {symbol}: {e}")
        db.rollback()
    finally:
        db.close()


@celery_app.task(name="app.tasks.analyze_stock_task")
def analyze_stock_task(symbol: str):
    """Background task to analyze a single stock."""
    # Run the async analyzer inside sync celery task
    asyncio.run(_analyze_stock_async(symbol))


@celery_app.task(name="app.tasks.run_overnight_universe_scan")
def run_overnight_universe_scan():
    """Trigger analysis for the entire stock universe."""
    # Get all stocks from our database, or a predefined universe
    db = SessionLocal()
    try:
        stocks = db.query(Stock).all()
        # If no stocks, maybe pull NIFTY 500 list (for now just use existing)
        symbols = [s.symbol for s in stocks]
        
        if not symbols:
            # Fallback list for testing
            symbols = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS"]
            
        logger.info(f"Starting overnight scan for {len(symbols)} symbols")
        for symbol in symbols:
            analyze_stock_task.delay(symbol)
    finally:
        db.close()
