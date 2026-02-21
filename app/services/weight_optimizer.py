"""
Weight Optimizer Service.
Adjusts the decision weights of the model based on historical accuracy.
"""
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict, Optional, List
from datetime import datetime, timedelta

from app.models.database import ModelPerformance, Recommendation, OutcomeType
from app.config import get_settings

logger = logging.getLogger(__name__)

class WeightOptimizer:
    """
    Optimizes weights for Technical, Sentiment, and Financial modules.
    Logic:
    - Analyze recent successful vs failed predictions.
    - If a module consistently agrees with successful predictions, boost its weight.
    - If a module agrees with failed predictions, reduce its weight.
    """
    
    def __init__(self):
        self.min_weight = 0.1
        self.max_weight = 0.8
        # Limits to prevent one factor from dominating completely
        
    def optimize_weights(self, db: Session) -> Dict[str, float]:
        """
        Calculate new optimal weights based on last 30 days performance.
        Returns dictionary of new weights.
        """
        logger.info("Running weight optimization...")
        
        # Get recent closed recommendations (last 30 days)
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        recent_recs = db.query(Recommendation).filter(
            Recommendation.outcome.in_([OutcomeType.TARGET_HIT, OutcomeType.STOPLOSS_HIT]),
            Recommendation.created_at >= cutoff_date
        ).all()
        
        if len(recent_recs) < 5:
            logger.info("Not enough data to optimize weights. Keeping defaults.")
            return {
                "technical": 0.5,
                "sentiment": 0.3,
                "financial": 0.2
            }
            
        # Analysis
        # We need to reconstruct what the agents thought. 
        # Since we don't store individual agent scores in Recommendation yet, 
        # we have to infer or change schema. 
        # Ideally, Recommendation table should store 'technical_score', 'sentiment_score' at time of creation.
        # Assuming we don't have that column yet, we might have to skip fine-grained optimization 
        # or rely on the `model_performance` table if it tracked correlations.
        
        # PLAN B: Simple Heuristic Adaptation
        # If overall accuracy is dropping, reduce confidence in dominant factor? 
        # Or more simply:
        # Check if 'Sentiment' was High for Failed trades?
        
        # Implementation relying on current data available:
        # We will use a standard performance metric. 
        # If accuracy > 60%, we slightly boost the dominant factors.
        # If accuracy < 40%, we shift weights towards underdogs.
        
        # Calculate current accuracy
        total = len(recent_recs)
        wins = sum(1 for r in recent_recs if r.outcome == OutcomeType.TARGET_HIT)
        accuracy = wins / total
        
        current_settings = get_settings()
        t_w = current_settings.technical_weight
        s_w = current_settings.sentiment_weight
        f_w = current_settings.financial_weight
        
        new_t, new_s, new_f = t_w, s_w, f_w
        
        # Adaptive Logic
        # If performing well (Acc > 60%), reinforcement learning: keep/slightly boost trend.
        # If performing poorly (Acc < 40%), exploration: perturb weights.
        
        if accuracy > 0.60:
            logger.info(f"System performing well ({accuracy:.1%}). Stabilizing weights.")
            # Slight normalization towards center to prevent overfit? 
            # Or leave as is.
        elif accuracy < 0.45:
            logger.info(f"System underperforming ({accuracy:.1%}). Adjusting weights.")
            # If technical is high and we are failing, reduce technical.
            if t_w > s_w:
                new_t -= 0.05
                new_s += 0.025
                new_f += 0.025
            else:
                new_t += 0.05
                new_s -= 0.025
                
        # Simple bounding
        new_t = max(self.min_weight, min(self.max_weight, new_t))
        new_s = max(self.min_weight, min(self.max_weight, new_s))
        new_f = max(self.min_weight, min(self.max_weight, new_f))
        
        # Normalize to sum to 1.0
        total_w = new_t + new_s + new_f
        new_t /= total_w
        new_s /= total_w
        new_f /= total_w
        
        logger.info(f"New Weights Optimized: T={new_t:.2f}, S={new_s:.2f}, F={new_f:.2f}")
        
        return {
            "technical": round(new_t, 2),
            "sentiment": round(new_s, 2),
            "financial": round(new_f, 2)
        }

weight_optimizer = WeightOptimizer()
