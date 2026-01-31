"""Confidence scoring system with uncertainty quantification."""
from typing import Dict, Any, Optional
from app.config import get_settings
from app.models.schemas import SentimentType, SentimentAnalysis

settings = get_settings()


class ConfidenceScorer:
    """Calculate confidence scores for recommendations."""
    
    def __init__(self):
        """Initialize with configurable weights."""
        self.technical_weight = settings.technical_weight
        self.financial_weight = settings.financial_weight
        self.sentiment_weight = settings.sentiment_weight
        self.historical_weight = settings.historical_weight
    
    def calculate(
        self,
        technical_data: Optional[Dict[str, Any]],
        financial_data: Optional[Dict[str, Any]],
        sentiment_data: Optional[SentimentAnalysis],
        historical_accuracy: float = 50.0  # Default when no history
    ) -> Dict[str, float]:
        """Calculate weighted confidence score."""
        
        # Technical score (from technical analyzer)
        technical_score = 50.0
        if technical_data:
            technical_score = technical_data.get("technical_score", 50.0)
        
        # Financial score
        financial_score = self._calculate_financial_score(financial_data)
        
        # Sentiment score
        sentiment_score = self._calculate_sentiment_score(sentiment_data)
        
        # Weighted total
        weighted_total = (
            technical_score * self.technical_weight +
            financial_score * self.financial_weight +
            sentiment_score * self.sentiment_weight +
            historical_accuracy * self.historical_weight
        )
        
        # Agreement bonus: Add points if all signals agree
        agreement_bonus = self._calculate_agreement_bonus(
            technical_score, financial_score, sentiment_score
        )
        
        final_score = min(100, weighted_total + agreement_bonus)
        
        return {
            "technical_score": round(technical_score, 2),
            "financial_score": round(financial_score, 2),
            "sentiment_score": round(sentiment_score, 2),
            "historical_score": round(historical_accuracy, 2),
            "weighted_total": round(final_score, 2)
        }
    
    def _calculate_financial_score(
        self, 
        financial_data: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate score from financial metrics."""
        if not financial_data:
            return 50.0  # Neutral when no data
        
        score = 50.0
        
        # EPS Growth (max ±20)
        eps_growth = financial_data.get("eps_growth_pct")
        if eps_growth is not None:
            if eps_growth >= 15:  # Required threshold
                score += min(20, eps_growth)
            elif eps_growth >= 0:
                score += eps_growth * 0.5
            else:
                score += max(-20, eps_growth * 0.5)
        
        # Debt-to-Equity (max ±15)
        d_to_e = financial_data.get("debt_to_equity")
        if d_to_e is not None:
            if d_to_e < 0.5:
                score += 15  # Low debt
            elif d_to_e < 1.0:
                score += 10
            elif d_to_e > 2.0:
                score -= 10  # High debt
        
        # Positive Cash Flow (max +15)
        cash_flow = financial_data.get("operating_cash_flow_cr")
        if cash_flow is not None:
            if cash_flow > 0:
                score += 15
            elif cash_flow < 0:
                score -= 10
        
        return max(0, min(100, score))
    
    def _calculate_sentiment_score(
        self, 
        sentiment_data: Optional[SentimentAnalysis]
    ) -> float:
        """Calculate score from sentiment analysis."""
        if not sentiment_data:
            return 50.0
        
        base = 50.0
        confidence_factor = sentiment_data.confidence / 100
        
        if sentiment_data.overall_sentiment == SentimentType.POSITIVE:
            return base + (30 * confidence_factor)
        elif sentiment_data.overall_sentiment == SentimentType.NEGATIVE:
            return base - (30 * confidence_factor)
        else:
            return base
    
    def _calculate_agreement_bonus(
        self,
        technical: float,
        financial: float,
        sentiment: float
    ) -> float:
        """Bonus when all signals agree."""
        # Check if all are bullish (>60) or all bearish (<40)
        if all(s > 60 for s in [technical, financial, sentiment]):
            return 10  # All bullish
        elif all(s < 40 for s in [technical, financial, sentiment]):
            return 5  # All bearish (less bonus as we're looking for longs)
        elif all(40 <= s <= 60 for s in [technical, financial, sentiment]):
            return 0  # All neutral
        else:
            return 0  # Mixed signals
    
    def get_confidence_label(self, score: float) -> str:
        """Get human-readable confidence label."""
        if score >= 80:
            return "Very High Confidence"
        elif score >= 65:
            return "High Confidence"
        elif score >= 50:
            return "Moderate Confidence"
        elif score >= 35:
            return "Low Confidence"
        else:
            return "Very Low Confidence"


# Singleton instance
confidence_scorer = ConfidenceScorer()
