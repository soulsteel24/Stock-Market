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
    
    async def generate_safe_picks(self, max_stocks: int = 500) -> Dict[str, Any]:
        """
        Generate top picks with full AI validation.
        
        1. quick bulk scan to find candidates
        2. full deep analysis on top candidates to verify
        """
        from app.services.technical_analyzer import technical_analyzer
        from app.services.stock_analyzer import stock_analyzer
        from app.data.stock_universe import ALL_STOCKS
            
        stocks = ALL_STOCKS[:max_stocks]
        
        # 1. Bulk Scan (Fast)
        logger.info(f"Starting bulk scan for {len(stocks)} stocks...")
        results_map = await technical_analyzer.scan_batched(stocks)
        
        # Initial sorting buckets
        candidate_buys = []
        candidate_sells = []
        
        for symbol, data in results_map.items():
            tech_score = data.get("technical_score", 50)
            rsi = data.get("rsi")
            price_above_ema = data.get("price_above_ema", False)
            
            # Heuristic Scoring (Initial Filter)
            if rsi and rsi < 35 and tech_score > 60:
                score = min(85, 50 + (35 - rsi) + tech_score / 5)
                candidate_buys.append((symbol, score, data))
            elif rsi and rsi > 65 and tech_score < 40:
                score = min(85, 50 + (rsi - 65) + (100 - tech_score) / 5)
                candidate_sells.append((symbol, score, data))
            elif price_above_ema and tech_score > 70:
                score = 55 + tech_score / 10
                candidate_buys.append((symbol, score, data))
        
        # Sort candidates
        candidate_buys.sort(key=lambda x: x[1], reverse=True)
        candidate_sells.sort(key=lambda x: x[1], reverse=True)
        
        # 2. Validation Step (Deep Analysis)
        # Verify top 10 of each to find the best 5 valid ones
        top_buy_candidates = [x[0] for x in candidate_buys[:10]]
        top_sell_candidates = [x[0] for x in candidate_sells[:10]]
        
        unique_candidates = list(set(top_buy_candidates + top_sell_candidates))
        logger.info(f"Validating {len(unique_candidates)} candidates with full AI model...")
        
        if not unique_candidates:
            return {
                "buy_recommendations": [],
                "sell_recommendations": [],
                "analyzed_count": len(results_map),
                "failed_count": len(stocks) - len(results_map)
            }

        # Run full analysis
        batch_results = await stock_analyzer.analyze_batch(
            symbols=unique_candidates,
            include_news=False,  # Skip news for speed during validation
            include_technicals=True
        )
        
        valid_buys = []
        valid_sells = []
        
        for res in batch_results["results"]:
            symbol = res.symbol
            # Find original data for quick access to some fields if needed
            # (though Full Analysis has better data)
            
            if res.recommendation.value == "BUY":
                valid_buys.append({
                    "symbol": symbol,
                    "signal": "BUY",
                    "confidence": res.confidence_score,
                    "current_price": res.current_price,
                    "rsi": res.technical_indicators.rsi,
                    "change_pct": 0, # Note: Populate if available
                    "tech_score": res.confidence_breakdown.technical_score,
                    "data_source": "full_ai_validated"
                })
            elif res.recommendation.value == "SELL":
                valid_sells.append({
                    "symbol": symbol,
                    "signal": "SELL",
                    "confidence": res.confidence_score,
                    "current_price": res.current_price,
                    "rsi": res.technical_indicators.rsi,
                    "change_pct": 0,
                    "tech_score": res.confidence_breakdown.technical_score,
                    "data_source": "full_ai_validated"
                })
        
        # Sort final results
        valid_buys.sort(key=lambda x: x["confidence"], reverse=True)
        valid_sells.sort(key=lambda x: x["confidence"], reverse=True)
        
        return {
            "buy_recommendations": valid_buys,
            "sell_recommendations": valid_sells,
            "analyzed_count": len(results_map),
            "failed_count": len(stocks) - len(results_map)
        }

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
            # Use the new shared generation logic
            picks = await self.generate_safe_picks(max_stocks)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.cache = {
                "analysis_date": datetime.now().strftime("%Y-%m-%d"),
                "generated_at": datetime.now().isoformat(),
                "market_status": "Pre-Market",
                "analysis_duration_seconds": round(duration, 1),
                "buy_recommendations": picks["buy_recommendations"][:20],
                "sell_recommendations": picks["sell_recommendations"][:20],
                "all_buy_signals": len(picks["buy_recommendations"]),
                "all_sell_signals": len(picks["sell_recommendations"]),
                "total_analyzed": picks["analyzed_count"],
                "total_attempted": max_stocks,
                "failed": picks["failed_count"],
                "disclaimer": "⚠️ Pre-market analysis. Verify with live data before trading."
            }
            
            self.last_analysis_date = self.cache["analysis_date"]
            self._save_cache()
            
            logger.info(f"Pre-market analysis complete in {duration:.1f}s")
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
