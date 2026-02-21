"""FastAPI main application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import logging
import os

from app import __version__
from app.api.routes import router
from app.services.database import init_db
from app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="Agentic Quantitative Research System",
    description="""
## Senior Quantitative Equity Researcher for NSE/BSE Markets

This API provides AI-powered stock analysis with:
- **Technical Analysis**: RSI, EMA, MACD, Bollinger Bands
- **Sentiment Analysis**: News and announcement sentiment
- **Value+Momentum Filtering**: EPS growth, P/E ratio, cash flow checks
- **Safety Veto System**: VIX-based and leverage checks
- **Memory Loop**: Learning from past predictions

### SEBI Disclaimer
This is an AI-generated research tool for educational purposes only.
It does not constitute financial advice. Investments in securities market
are subject to market risks. Read all the related documents carefully
before investing.
    """,
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["Stock Analysis"])


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger.info("Starting Agentic Quantitative Research System...")
    init_db()
    logger.info(f"Database initialized. API version: {__version__}")
    
    if not settings.gemini_api_key:
        logger.warning("⚠️ GEMINI_API_KEY not set. AI features will be limited.")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Agentic Quantitative Research System",
        "version": __version__,
        "docs": "/docs",
        "health": "/api/v1/health",
        "description": "API backend for Stock Market Analysis"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
