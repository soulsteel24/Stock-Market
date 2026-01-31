"""Divergence Detection Agent."""
from typing import Dict, Any, List
from app.agents.base_agent import BaseAgent
from app.models.schemas import SentimentType


class DivergenceAgent(BaseAgent):
    """
    Agent that detects divergences between signals.
    
    Divergences:
    - Bullish technicals but declining fundamentals
    - Positive sentiment but negative cash flow
    - High momentum but low quality earnings
    """
    
    def __init__(self):
        super().__init__("Divergence")
    
    async def evaluate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect divergences between different signals."""
        technical = data.get("technical", {})
        financial = data.get("financial", {})
        sentiment = data.get("sentiment")
        
        warnings = []
        divergences = []
        
        # 1. Bullish technicals but declining fundamentals
        tech_bullish = (
            technical.get("price_above_ema", False) and
            technical.get("macd_bullish", False)
        )
        fundamentals_declining = False
        
        eps_growth = financial.get("eps_growth_pct")
        pat_growth = financial.get("pat_growth_pct")
        revenue_growth = financial.get("revenue_growth_pct")
        
        if eps_growth is not None and eps_growth < 0:
            fundamentals_declining = True
        if pat_growth is not None and pat_growth < 0:
            fundamentals_declining = True
        
        if tech_bullish and fundamentals_declining:
            divergences.append({
                "type": "TECH_VS_FUNDAMENTALS",
                "severity": "HIGH",
                "description": "Technicals are bullish but quarterly results show declining EPS/PAT"
            })
            warnings.append({
                "type": "DIVERGENCE",
                "message": "⚠️ DIVERGENCE WARNING: Bullish technicals contradict declining fundamentals",
                "severity": "WARNING"
            })
        
        # 2. Positive sentiment but negative cash flow
        sentiment_positive = (
            sentiment and 
            sentiment.overall_sentiment == SentimentType.POSITIVE
        )
        negative_cash_flow = False
        cash_flow = financial.get("operating_cash_flow_cr")
        if cash_flow is not None and cash_flow < 0:
            negative_cash_flow = True
        
        if sentiment_positive and negative_cash_flow:
            divergences.append({
                "type": "SENTIMENT_VS_CASHFLOW",
                "severity": "MEDIUM",
                "description": "News sentiment is positive but company has negative operating cash flow"
            })
            warnings.append({
                "type": "DIVERGENCE",
                "message": "⚠️ Positive news sentiment despite negative cash flow",
                "severity": "WARNING"
            })
        
        # 3. High momentum (RSI > 60) but low quality earnings
        high_momentum = technical.get("rsi", 0) > 60
        low_quality_earnings = (
            financial.get("debt_to_equity", 0) > 2 or
            negative_cash_flow
        )
        
        if high_momentum and low_quality_earnings:
            divergences.append({
                "type": "MOMENTUM_VS_QUALITY",
                "severity": "MEDIUM",
                "description": "High price momentum but low earnings quality (high debt or negative cash flow)"
            })
            warnings.append({
                "type": "DIVERGENCE",
                "message": "⚠️ High momentum stock with questionable earnings quality",
                "severity": "WARNING"
            })
        
        # 4. Negative sentiment but strong technicals
        sentiment_negative = (
            sentiment and
            sentiment.overall_sentiment == SentimentType.NEGATIVE
        )
        strong_technicals = technical.get("technical_score", 0) >= 70
        
        if sentiment_negative and strong_technicals:
            divergences.append({
                "type": "SENTIMENT_VS_TECHNICALS",
                "severity": "LOW",
                "description": "Negative news sentiment but technicals remain strong"
            })
            # This could be opportunity or trap
            warnings.append({
                "type": "DIVERGENCE",
                "message": "ℹ️ Negative sentiment contrasts with strong technicals - potential opportunity or trap",
                "severity": "INFO"
            })
        
        has_divergence = len(divergences) > 0
        
        self.log_decision(
            f"{'DIVERGENCE DETECTED' if has_divergence else 'NO DIVERGENCE'}",
            f"{len(divergences)} divergence(s) found"
        )
        
        return {
            "agent": self.name,
            "has_divergence": has_divergence,
            "divergence_count": len(divergences),
            "divergences": divergences,
            "warnings": warnings
        }


# Singleton instance
divergence_agent = DivergenceAgent()
