"""Memory Loop service for learning from past recommendations."""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
import json
import logging
from app.models.database import (
    Stock, Recommendation, Lesson, 
    RecommendationType, OutcomeType, SentimentType
)
from app.services.gemini_client import gemini_client

logger = logging.getLogger(__name__)


class MemoryLoop:
    """
    Memory Loop system for learning from past predictions.
    
    When a recommendation hits stop-loss:
    1. Analyze what went wrong
    2. Generate a lesson
    3. Store for future reference
    4. Feed lessons into agent prompts
    """
    
    async def store_recommendation(
        self,
        db: Session,
        symbol: str,
        recommendation_type: str,
        confidence_score: float,
        entry_price: float,
        target_price: float,
        stop_loss: float,
        investment_thesis: List[str],
        technical_score: float,
        financial_score: float,
        sentiment_score: float,
        sentiment_type: Optional[str] = None,
        divergence_warning: bool = False,
        safety_veto_applied: bool = False,
        veto_reason: Optional[str] = None,
        expiry_days: int = 30
    ) -> Recommendation:
        """Store a new recommendation."""
        
        # Get or create stock
        stock = db.query(Stock).filter(Stock.symbol == symbol).first()
        if not stock:
            stock = Stock(symbol=symbol)
            db.add(stock)
            db.flush()
        
        recommendation = Recommendation(
            stock_id=stock.id,
            recommendation_type=RecommendationType(recommendation_type),
            confidence_score=confidence_score,
            entry_price=entry_price,
            target_price=target_price,
            stop_loss_price=stop_loss,
            risk_reward_ratio=(target_price - entry_price) / (entry_price - stop_loss) if entry_price > stop_loss else 0,
            investment_thesis=json.dumps(investment_thesis),
            technical_score=technical_score,
            financial_score=financial_score,
            sentiment_score=sentiment_score,
            sentiment_type=SentimentType(sentiment_type) if sentiment_type else None,
            divergence_warning=divergence_warning,
            safety_veto_applied=safety_veto_applied,
            veto_reason=veto_reason,
            outcome=OutcomeType.PENDING,
            expiry_date=datetime.utcnow() + timedelta(days=expiry_days)
        )
        
        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)
        
        logger.info(f"Stored recommendation for {symbol}: {recommendation_type}")
        return recommendation
    
    async def update_outcome(
        self,
        db: Session,
        recommendation_id: int,
        outcome: str,
        actual_exit_price: float
    ) -> Recommendation:
        """Update the outcome of a recommendation."""
        recommendation = db.query(Recommendation).filter(
            Recommendation.id == recommendation_id
        ).first()
        
        if not recommendation:
            raise ValueError(f"Recommendation {recommendation_id} not found")
        
        recommendation.outcome = OutcomeType(outcome)
        recommendation.actual_exit_price = actual_exit_price
        recommendation.outcome_date = datetime.utcnow()
        
        # Calculate actual return
        if recommendation.entry_price > 0:
            recommendation.actual_return_pct = (
                (actual_exit_price - recommendation.entry_price) / 
                recommendation.entry_price * 100
            )
        
        db.commit()
        
        # If stop-loss hit, generate lesson
        if outcome == "STOPLOSS_HIT":
            await self.generate_lesson(db, recommendation)
        
        return recommendation
    
    async def generate_lesson(
        self,
        db: Session,
        recommendation: Recommendation
    ) -> Lesson:
        """Generate a lesson from a failed recommendation."""
        stock = recommendation.stock
        
        # Analyze what went wrong
        thesis = json.loads(recommendation.investment_thesis) if recommendation.investment_thesis else []
        
        # Use Gemini to analyze failure
        analysis = await self._analyze_failure(
            symbol=stock.symbol,
            recommendation_type=recommendation.recommendation_type.value,
            confidence_score=recommendation.confidence_score,
            technical_score=recommendation.technical_score,
            financial_score=recommendation.financial_score,
            sentiment_score=recommendation.sentiment_score,
            thesis=thesis,
            divergence_warning=recommendation.divergence_warning
        )
        
        lesson = Lesson(
            recommendation_id=recommendation.id,
            lesson_type="STOPLOSS_HIT",
            lesson_text=analysis.get("lesson", "Analysis unavailable"),
            primary_cause=analysis.get("primary_cause", "Unknown"),
            technical_failure=analysis.get("technical_failure", False),
            fundamental_failure=analysis.get("fundamental_failure", False),
            sentiment_failure=analysis.get("sentiment_failure", False),
            external_factor=analysis.get("external_factor", False),
            adjustment_suggestion=analysis.get("adjustment", ""),
            weight_adjustment=json.dumps(analysis.get("weight_changes", {}))
        )
        
        db.add(lesson)
        db.commit()
        
        logger.warning(f"Generated lesson for {stock.symbol}: {lesson.primary_cause}")
        return lesson
    
    async def _analyze_failure(
        self,
        symbol: str,
        recommendation_type: str,
        confidence_score: float,
        technical_score: float,
        financial_score: float,
        sentiment_score: float,
        thesis: List[str],
        divergence_warning: bool
    ) -> Dict[str, Any]:
        """Use Gemini to analyze why a recommendation failed."""
        if not gemini_client.is_connected():
            return {
                "lesson": "Unable to generate AI analysis - Gemini not configured",
                "primary_cause": "Manual review required",
                "technical_failure": False,
                "fundamental_failure": False,
                "sentiment_failure": False,
                "external_factor": True
            }
        
        prompt = f"""You are analyzing a failed stock recommendation for learning purposes.

Stock: {symbol}
Recommendation: {recommendation_type}
Confidence Score: {confidence_score}%
Technical Score: {technical_score}
Financial Score: {financial_score}
Sentiment Score: {sentiment_score}
Divergence Warning Present: {divergence_warning}
Investment Thesis: {thesis}

The recommendation hit its stop-loss. Analyze what likely went wrong.

Respond ONLY with a JSON object:
{{
    "lesson": "<3-sentence lesson learned>",
    "primary_cause": "<one of: Technical Misjudgment, Fundamental Weakness, Sentiment Shift, Market Volatility, External Event>",
    "technical_failure": <true if technicals were misleading>,
    "fundamental_failure": <true if fundamentals were weak>,
    "sentiment_failure": <true if sentiment analysis was wrong>,
    "external_factor": <true if market/external factors caused failure>,
    "adjustment": "<specific suggestion to improve future analysis>",
    "weight_changes": {{
        "technical_weight": <suggested adjustment, e.g., -0.05>,
        "financial_weight": <adjustment>,
        "sentiment_weight": <adjustment>
    }}
}}"""

        try:
            response = await gemini_client.generate(prompt)
            json_str = response.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.startswith("```"):
                json_str = json_str[3:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            return json.loads(json_str.strip())
        except Exception as e:
            logger.error(f"Lesson generation error: {e}")
            return {
                "lesson": f"The {recommendation_type} recommendation for {symbol} hit stop-loss. Manual review recommended.",
                "primary_cause": "Analysis Error",
                "technical_failure": False,
                "fundamental_failure": False,
                "sentiment_failure": False,
                "external_factor": True
            }
    
    async def get_relevant_lessons(
        self,
        db: Session,
        symbol: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant lessons for informing future decisions."""
        query = db.query(Lesson).join(Recommendation).join(Stock)
        
        if symbol:
            query = query.filter(Stock.symbol == symbol)
        
        lessons = query.order_by(desc(Lesson.created_at)).limit(limit).all()
        
        return [
            {
                "id": lesson.id,
                "symbol": lesson.recommendation.stock.symbol,
                "lesson_type": lesson.lesson_type,
                "lesson_text": lesson.lesson_text,
                "primary_cause": lesson.primary_cause,
                "adjustment_suggestion": lesson.adjustment_suggestion,
                "created_at": lesson.created_at.isoformat()
            }
            for lesson in lessons
        ]
    
    async def get_historical_accuracy(
        self,
        db: Session,
        symbol: Optional[str] = None
    ) -> float:
        """Calculate historical accuracy for confidence scoring."""
        query = db.query(Recommendation).filter(
            Recommendation.outcome != OutcomeType.PENDING
        )
        
        if symbol:
            query = query.join(Stock).filter(Stock.symbol == symbol)
        
        recommendations = query.all()
        
        if not recommendations:
            return 50.0  # Default neutral
        
        successful = sum(1 for r in recommendations if r.outcome == OutcomeType.TARGET_HIT)
        total = len(recommendations)
        
        return (successful / total) * 100


# Singleton instance
memory_loop = MemoryLoop()
