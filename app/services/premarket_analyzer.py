"""Pre-market analysis scheduler for daily stock picks."""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
import threading

logger = logging.getLogger(__name__)

# Cache file for pre-computed daily picks
CACHE_FILE = Path(__file__).parent.parent / "data" / "daily_picks_cache.json"


class PreMarketAnalyzer:
    """Runs pre-market analysis on all stocks before market opens."""
    
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.last_analysis_date: str = ""
        self.is_running = False
        self._load_cache()
    
    def _load_cache(self):
        """Load cached analysis from file."""
        try:
            if CACHE_FILE.exists():
                with open(CACHE_FILE, 'r') as f:
                    data = json.load(f)
                    self.cache = data
                    self.last_analysis_date = data.get("analysis_date", "")
                    logger.info(f"Loaded cache from {self.last_analysis_date}")
        except Exception as e:
            logger.warning(f"Could not load cache: {e}")
    
    def _save_cache(self):
        """Save analysis results to file."""
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CACHE_FILE, 'w') as f:
                json.dump(self.cache, f, indent=2)
            logger.info("Saved analysis cache to file")
        except Exception as e:
            logger.error(f"Could not save cache: {e}")
    
    def get_cached_picks(self) -> Dict[str, Any]:
        """Get cached daily picks if available and fresh."""
        today = datetime.now().strftime("%Y-%m-%d")
        
        if self.cache and self.last_analysis_date == today:
            return self.cache
        
        return None
    
    async def run_full_analysis(self, max_stocks: int = 500) -> Dict[str, Any]:
        """
        Run analysis on all stocks. Call this before market opens.
        
        Best to run via scheduler at 8:30 AM IST.
        """
        if self.is_running:
            logger.warning("Analysis already running")
            return {"status": "already_running"}
        
        self.is_running = True
        start_time = datetime.now()
        logger.info(f"Starting pre-market analysis for {max_stocks} stocks at {start_time}")
        
        try:
            from app.services.technical_analyzer import technical_analyzer
            from app.data.stock_universe import ALL_STOCKS
            
            stocks = ALL_STOCKS[:max_stocks]
            buy_picks = []
            sell_picks = []
            
            # Use bulk scanning (Much faster)
            logger.info(f"Starting bulk scan for {len(stocks)} stocks...")
            results_map = await technical_analyzer.scan_batched(stocks)
            
            analyzed = len(results_map)
            failed = len(stocks) - analyzed
            
            for symbol, data in results_map.items():
                tech_score = data.get("technical_score", 50)
                rsi = data.get("rsi")
                price_above_ema = data.get("price_above_ema", False)
                
                # Scoring logic
                if rsi and rsi < 35 and tech_score > 60:
                    signal = "BUY"
                    confidence = min(85, 50 + (35 - rsi) + tech_score / 5)
                elif rsi and rsi > 65 and tech_score < 40:
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
                
                result = {
                    "symbol": symbol,
                    "signal": signal,
                    "confidence": round(confidence, 1),
                    "current_price": data.get("current_price"),
                    "rsi": rsi,
                    "change_pct": data.get("change_pct", 0),
                    "ema_200": data.get("ema_200"),
                    "tech_score": tech_score,
                    "data_source": "yfinance_bulk"
                }

                if signal == "BUY":
                    buy_picks.append(result)
                elif signal == "SELL":
                    sell_picks.append(result)
            
            # Sort by confidence
            buy_picks.sort(key=lambda x: x["confidence"], reverse=True)
            sell_picks.sort(key=lambda x: x["confidence"], reverse=True)
            
            end_time = datetime.now()
            # ... rest of code unchanged ...
            duration = (end_time - start_time).total_seconds()
            
            self.cache = {
                "analysis_date": datetime.now().strftime("%Y-%m-%d"),
                "generated_at": datetime.now().isoformat(),
                "market_status": "Pre-Market",
                "analysis_duration_seconds": round(duration, 1),
                "buy_recommendations": buy_picks[:20],  # Top 20
                "sell_recommendations": sell_picks[:20],
                "all_buy_signals": len(buy_picks),
                "all_sell_signals": len(sell_picks),
                "total_analyzed": analyzed,
                "total_attempted": len(stocks),
                "failed": failed,
                "disclaimer": "⚠️ Pre-market analysis. Verify with live data before trading."
            }
            
            self.last_analysis_date = self.cache["analysis_date"]
            self._save_cache()
            
            logger.info(f"Pre-market analysis complete: {analyzed} stocks in {duration:.1f}s")
            return self.cache
            
        except Exception as e:
            logger.error(f"Pre-market analysis error: {e}")
            return {"error": str(e)}
        
        finally:
            self.is_running = False
    
    def schedule_daily_analysis(self, hour: int = 8, minute: int = 30):
        """
        Schedule daily pre-market analysis.
        
        Default: 8:30 AM IST (before 9:15 AM market open)
        """
        import schedule
        import time
        
        def run_analysis():
            asyncio.run(self.run_full_analysis(500))
        
        schedule_time = f"{hour:02d}:{minute:02d}"
        schedule.every().day.at(schedule_time).do(run_analysis)
        
        logger.info(f"Scheduled daily analysis at {schedule_time}")
        
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)
        
        thread = threading.Thread(target=run_scheduler, daemon=True)
        thread.start()


# Singleton instance
pre_market_analyzer = PreMarketAnalyzer()
