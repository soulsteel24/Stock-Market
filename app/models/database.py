"""SQLAlchemy database models for the Memory Loop system."""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Enum, ForeignKey, Boolean
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class RecommendationType(enum.Enum):
    """Recommendation types for stock analysis."""
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    WATCHLIST = "WATCHLIST"


class SentimentType(enum.Enum):
    """Sentiment classification for news analysis."""
    POSITIVE = "POSITIVE"
    NEUTRAL = "NEUTRAL"
    NEGATIVE = "NEGATIVE"


class OutcomeType(enum.Enum):
    """Outcome of a recommendation."""
    PENDING = "PENDING"
    TARGET_HIT = "TARGET_HIT"
    STOPLOSS_HIT = "STOPLOSS_HIT"
    EXPIRED = "EXPIRED"


class Stock(Base):
    """Stock metadata and sector information."""
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(200))
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap_cr = Column(Float)  # Market cap in Crores
    
    # Relationships
    recommendations = relationship("Recommendation", back_populates="stock")
    quarterly_results = relationship("QuarterlyResult", back_populates="stock")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QuarterlyResult(Base):
    """Extracted financial metrics from quarterly result PDFs."""
    __tablename__ = "quarterly_results"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    
    # Quarter Information
    fiscal_year = Column(String(10))  # e.g., "FY26"
    quarter = Column(String(5))  # e.g., "Q3"
    
    # Key Financial Metrics
    revenue_cr = Column(Float)  # Revenue in Crores
    pat_cr = Column(Float)  # Profit After Tax in Crores
    ebitda_cr = Column(Float)  # EBITDA in Crores
    eps = Column(Float)  # Earnings Per Share
    
    # Ratios
    debt_to_equity = Column(Float)
    pe_ratio = Column(Float)
    roe = Column(Float)  # Return on Equity
    
    # Growth Metrics (YoY)
    revenue_growth_pct = Column(Float)
    pat_growth_pct = Column(Float)
    eps_growth_pct = Column(Float)
    
    # Cash Flow
    operating_cash_flow_cr = Column(Float)
    free_cash_flow_cr = Column(Float)
    
    # Source
    pdf_source = Column(String(500))
    extracted_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    stock = relationship("Stock", back_populates="quarterly_results")


class Recommendation(Base):
    """Past recommendations with outcomes for learning."""
    __tablename__ = "recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, ForeignKey("stocks.id"), nullable=False)
    
    # Recommendation Details
    recommendation_type = Column(Enum(RecommendationType), nullable=False)
    confidence_score = Column(Float)  # 0-100
    
    # Price Levels
    entry_price = Column(Float, nullable=False)
    target_price = Column(Float, nullable=False)
    stop_loss_price = Column(Float, nullable=False)
    risk_reward_ratio = Column(Float)
    
    # Analysis Summary
    investment_thesis = Column(Text)  # JSON array of 3 points
    technical_score = Column(Float)
    financial_score = Column(Float)
    sentiment_score = Column(Float)
    sentiment_type = Column(Enum(SentimentType))
    
    # Warnings and Flags
    divergence_warning = Column(Boolean, default=False)
    safety_veto_applied = Column(Boolean, default=False)
    veto_reason = Column(String(500))
    
    # Outcome Tracking
    outcome = Column(Enum(OutcomeType), default=OutcomeType.PENDING)
    actual_exit_price = Column(Float)
    actual_return_pct = Column(Float)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    outcome_date = Column(DateTime)
    expiry_date = Column(DateTime)  # When recommendation expires
    
    # Relationships
    stock = relationship("Stock", back_populates="recommendations")
    lessons = relationship("Lesson", back_populates="recommendation")


class Lesson(Base):
    """Learnings from wrong predictions - Memory Loop."""
    __tablename__ = "lessons"
    
    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(Integer, ForeignKey("recommendations.id"), nullable=False)
    
    # Lesson Details
    lesson_type = Column(String(50))  # e.g., "STOPLOSS_HIT", "FALSE_POSITIVE"
    lesson_text = Column(Text, nullable=False)
    
    # What Went Wrong
    primary_cause = Column(String(200))
    technical_failure = Column(Boolean, default=False)
    fundamental_failure = Column(Boolean, default=False)
    sentiment_failure = Column(Boolean, default=False)
    external_factor = Column(Boolean, default=False)
    
    # Actionable Insights
    adjustment_suggestion = Column(Text)
    weight_adjustment = Column(Text)  # JSON for weight changes
    
    # Usage Tracking
    times_referenced = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    recommendation = relationship("Recommendation", back_populates="lessons")


class NewsItem(Base):
    """News and announcements for sentiment analysis."""
    __tablename__ = "news_items"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True)
    
    # News Details
    title = Column(String(500), nullable=False)
    content = Column(Text)
    source = Column(String(100))
    url = Column(String(500))
    
    # Sentiment
    sentiment = Column(Enum(SentimentType))
    sentiment_confidence = Column(Float)
    
    # Timestamps
    published_at = Column(DateTime)
    scraped_at = Column(DateTime, default=datetime.utcnow)


class MarketCondition(Base):
    """Market-wide conditions for safety checks."""
    __tablename__ = "market_conditions"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Volatility
    india_vix = Column(Float)
    nifty_50 = Column(Float)
    nifty_bank = Column(Float)
    
    # Market Sentiment
    advance_decline_ratio = Column(Float)
    fii_activity_cr = Column(Float)  # FII buying/selling in Crores
    dii_activity_cr = Column(Float)  # DII buying/selling in Crores
    
    recorded_at = Column(DateTime, default=datetime.utcnow)
