"""Application configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    gemini_api_key: str = ""
    
    # Database
    database_url: str = "sqlite:///./stock_analyst.db"
    
    # Application
    debug: bool = True
    log_level: str = "INFO"
    
    # Safety Thresholds
    vix_threshold: float = 25.0  # Veto BUY if VIX > this value
    min_market_cap_cr: float = 500.0  # Minimum market cap in Crores
    
    # Analysis Parameters
    rsi_lower_bound: float = 40.0
    rsi_upper_bound: float = 60.0
    ema_period: int = 200
    min_eps_growth: float = 15.0  # Percentage
    min_risk_reward_ratio: float = 2.0  # 1:2 ratio
    
    # Confidence Score Weights
    technical_weight: float = 0.30
    financial_weight: float = 0.35
    sentiment_weight: float = 0.20
    historical_weight: float = 0.15
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
