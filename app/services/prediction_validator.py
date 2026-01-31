"""Service for automatically validating predictions against market data."""
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.database import (
    Recommendation, Stock, OutcomeType, ModelPerformance, Lesson
)
from app.services.technical_analyzer import technical_analyzer
from app.services.memory_loop import memory_loop
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class PredictionValidator:
    """
    Automatically validates pending recommendations.
    Checks if target or stop-loss was hit.
    """
    
    async def validate_pending_recommendations(self, db: Session) -> Dict[str, int]:
        """
        Check all pending recommendations against current market prices.
        Run this daily after market close.
        """
        logger.info("Starting automatic prediction validation...")
        
        # Get all pending recommendations
        pending = db.query(Recommendation).filter(
            Recommendation.outcome == OutcomeType.PENDING
        ).all()
        
        if not pending:
            logger.info("No pending recommendations to validate.")
            return {"processed": 0, "updates": 0}
            
        updates = 0
        processed = 0
        
        # Process in batches to avoid rate limits
        batch_size = 10
        for i in range(0, len(pending), batch_size):
            batch = pending[i:i+batch_size]
            tasks = [self.check_single_recommendation(db, r) for r in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for res in results:
                processed += 1
                if res and not isinstance(res, Exception) and res.get("updated"):
                    updates += 1
                    
            # Small delay between batches
            await asyncio.sleep(1)
            
        # After validation, record daily performance
        await self.record_daily_performance(db)
            
        logger.info(f"Validation complete. Processed {processed}, Updated {updates}")
        return {"processed": processed, "updates": updates}
    
    async def check_single_recommendation(
        self, 
        db: Session, 
        recommendation: Recommendation
    ) -> Dict[str, Any]:
        """Check a single recommendation against current price data."""
        try:
            symbol = recommendation.stock.symbol
            
            # Get current price data
            tech_data = await technical_analyzer.analyze(symbol)
            if not tech_data or not tech_data.get("current_price"):
                return {"updated": False, "reason": "No data"}
            
            current_price = tech_data.get("current_price")
            high_price = tech_data.get("day_high", current_price)
            low_price = tech_data.get("day_low", current_price)
            
            outcome = None
            exit_price = 0.0
            
            # Check conditions based on recommendation type
            if recommendation.recommendation_type.value == "BUY":
                if high_price >= recommendation.target_price:
                    outcome = OutcomeType.TARGET_HIT
                    exit_price = recommendation.target_price
                elif low_price <= recommendation.stop_loss_price:
                    outcome = OutcomeType.STOPLOSS_HIT
                    exit_price = recommendation.stop_loss_price
                    
            elif recommendation.recommendation_type.value == "SELL":
                if low_price <= recommendation.target_price:
                    outcome = OutcomeType.TARGET_HIT
                    exit_price = recommendation.target_price
                elif high_price >= recommendation.stop_loss_price:
                    outcome = OutcomeType.STOPLOSS_HIT
                    exit_price = recommendation.stop_loss_price
            
            # Check expiry
            if not outcome and recommendation.expiry_date:
                if datetime.utcnow() > recommendation.expiry_date:
                    outcome = OutcomeType.EXPIRED
                    exit_price = current_price
            
            # If outcome determined, update DB
            if outcome:
                await memory_loop.update_outcome(
                    db=db,
                    recommendation_id=recommendation.id,
                    outcome=outcome.value,
                    actual_exit_price=exit_price
                )
                logger.info(f"Auto-validated {symbol}: {outcome.value}")
                return {"updated": True, "outcome": outcome.value}
                
            return {"updated": False, "reason": "Still active"}
            
        except Exception as e:
            logger.error(f"Error checking {recommendation.stock.symbol}: {e}")
            return {"updated": False, "error": str(e)}

    async def record_daily_performance(self, db: Session):
        """Record daily model performance stats."""
        # Calculate overall accuracy
        completed = db.query(Recommendation).filter(
            Recommendation.outcome.in_([OutcomeType.TARGET_HIT, OutcomeType.STOPLOSS_HIT])
        ).all()
        
        if not completed:
            return
            
        total = len(completed)
        successful = sum(1 for r in completed if r.outcome == OutcomeType.TARGET_HIT)
        accuracy = (successful / total) * 100 if total > 0 else 0
        
        # Create performance record
        perf = ModelPerformance(
            total_predictions=total,
            successful_predictions=successful,
            accuracy_pct=accuracy,
            technical_weight=settings.technical_weight,
            financial_weight=settings.financial_weight,
            sentiment_weight=settings.sentiment_weight,
            notes="Auto-generated daily report"
        )
        
        db.add(perf)
        db.commit()
        logger.info(f"Recorded daily performance: {accuracy:.1f}% accuracy")
        
        # Log to text file
        try:
            log_entry = (
                f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                f"Accuracy: {accuracy:.1f}% | "
                f"Total: {total} | "
                f"Success: {successful}\n"
            )
            
            with open("daily_performance_log.txt", "a") as f:
                f.write(log_entry)
                
            logger.info("Logged performance to daily_performance_log.txt")
        except Exception as e:
            logger.error(f"Failed to write to log file: {e}")



# Singleton instance
prediction_validator = PredictionValidator()
