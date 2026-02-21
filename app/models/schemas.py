"""Pydantic schemas for API request/response validation."""
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from enum import Enum


class RecommendationType(str, Enum):
    """Recommendation types."""
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    WATCHLIST = "WATCHLIST"


class SentimentType(str, Enum):
    """Sentiment classification."""
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"


# ==================== Request Schemas ====================

class StockAnalysisRequest(BaseModel):
    """Request for single stock analysis."""
    symbol: str = Field(..., description="NSE stock symbol (e.g., RELIANCE)")
    include_news: bool = Field(default=True, description="Include news sentiment analysis")
    include_technicals: bool = Field(default=True, description="Include technical analysis")


class BatchAnalysisRequest(BaseModel):
    """Request for multi-stock parallel analysis."""
    symbols: List[str] = Field(..., min_length=1, max_length=10, description="List of NSE symbols")
    include_news: bool = True
    include_technicals: bool = True


class QuarterlyResultUpload(BaseModel):
    """Request for uploading quarterly result PDF."""
    symbol: str
    fiscal_year: str = Field(..., pattern=r"^FY\d{2}$", description="e.g., FY26")
    quarter: str = Field(..., pattern=r"^Q[1-4]$", description="e.g., Q3")


# ==================== Response Schemas ====================

class TechnicalIndicators(BaseModel):
    """Technical analysis indicators."""
    rsi: float = Field(..., ge=0, le=100, description="Relative Strength Index")
    ema_200: float = Field(..., description="200-day EMA")
    current_price: float
    price_above_ema: bool
    rsi_in_range: bool = Field(..., description="RSI between 40-60")


class FinancialMetrics(BaseModel):
    """Financial metrics from quarterly results."""
    revenue_cr: Optional[float] = None
    pat_cr: Optional[float] = None
    ebitda_cr: Optional[float] = None
    eps: Optional[float] = None
    eps_growth_pct: Optional[float] = None
    pe_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    positive_cash_flow: Optional[bool] = None
    promoter_holding_pct: Optional[float] = None
    fii_holding_pct: Optional[float] = None
    dii_holding_pct: Optional[float] = None


class ForecastDataPoint(BaseModel):
    """Single point in a price forecast/history."""
    date: str
    predicted_price: Optional[float] = None
    lower_bound: Optional[float] = None
    upper_bound: Optional[float] = None
    historical_price: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None


class ForecastAnalysis(BaseModel):
    """Forecast analysis result."""
    forecast: List[ForecastDataPoint]
    trend_pct: float
    bullish_trend: bool = False
    model: str
    days_forecasted: int


class SentimentAnalysis(BaseModel):
    """News sentiment analysis result."""
    overall_sentiment: SentimentType
    confidence: float = Field(..., ge=0, le=100)
    normalized_score: float = Field(default=0.0, ge=-1.0, le=1.0)
    positive_count: int = 0
    neutral_count: int = 0
    negative_count: int = 0
    key_headlines: List[str] = []
    ml_breakdown: Optional[Dict[str, float]] = None  # Added for FinBERT


class ConfidenceBreakdown(BaseModel):
    """Breakdown of confidence score components."""
    technical_score: float = Field(..., ge=0, le=100)
    financial_score: float = Field(..., ge=0, le=100)
    sentiment_score: float = Field(..., ge=0, le=100)
    historical_score: float = Field(..., ge=0, le=100)
    weighted_total: float = Field(..., ge=0, le=100)


class Warning(BaseModel):
    """Warning or alert about the analysis."""
    type: str  # e.g., "DIVERGENCE", "SAFETY_VETO", "LOW_LIQUIDITY"
    message: str
    severity: str = "WARNING"  # WARNING, CRITICAL


class AgentDebate(BaseModel):
    """Exposes the internal reasoning of the agents in plain English."""
    momentum_agent: str
    contrarian_agent: str
    safety_veto_agent: str


class StockAnalysisResponse(BaseModel):
    """Complete stock analysis response."""
    # Basic Info
    symbol: str
    name: Optional[str] = None
    sector: Optional[str] = None
    
    # Core Recommendation
    recommendation: RecommendationType
    confidence_score: float = Field(..., ge=0, le=100)
    confidence_breakdown: ConfidenceBreakdown
    
    # Price Targets
    current_price: float
    entry_price: float
    target_price: float
    stop_loss: float
    risk_reward_ratio: str  # e.g., "1:2.5"
    potential_return_pct: float
    potential_loss_pct: float
    
    # Analysis Components
    technical_indicators: TechnicalIndicators
    financial_metrics: Optional[FinancialMetrics] = None
    sentiment_analysis: Optional[SentimentAnalysis] = None
    forecast_analysis: Optional[ForecastAnalysis] = None  # New field
    
    # Explainability
    agent_debate: Optional[AgentDebate] = None
    
    # Investment Thesis
    investment_thesis: List[str] = Field(..., min_length=3, max_length=3)
    sources: List[str] = []
    
    # Warnings
    warnings: List[Warning] = []
    safety_veto_applied: bool = False
    
    # Metadata
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    
    # SEBI Disclaimer
    disclaimer: str = Field(
        default="⚠️ SEBI Disclaimer: This is an AI-generated research tool for educational purposes only. "
                "It does not constitute financial advice. Investments in securities market are subject to market risks. "
                "Read all the related documents carefully before investing. Past performance is not indicative of future returns."
    )


class BatchAnalysisResponse(BaseModel):
    """Response for batch stock analysis."""
    total_analyzed: int
    successful: int
    failed: int
    results: List[StockAnalysisResponse]
    errors: List[dict] = []


class LessonResponse(BaseModel):
    """Response for a learned lesson."""
    id: int
    symbol: str
    lesson_type: str
    lesson_text: str
    primary_cause: str
    created_at: datetime


class HealthResponse(BaseModel):
    """API health check response."""
    status: str = "healthy"
    version: str
    gemini_connected: bool
    database_connected: bool
