"""Google Gemini AI client for LLM reasoning."""
import google.generativeai as genai
from typing import Optional, List, Dict, Any
import json
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiClient:
    """Client for Google Gemini AI API."""
    
    def __init__(self):
        """Initialize Gemini client."""
        self.api_key = settings.gemini_api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
        else:
            logger.warning("Gemini API key not configured")
            self.model = None
    
    def is_connected(self) -> bool:
        """Check if Gemini is properly configured."""
        return self.model is not None and self.api_key != ""
    
    async def generate(self, prompt: str, temperature: float = 0.3) -> str:
        """Generate response from Gemini."""
        if not self.model:
            raise ValueError("Gemini API not configured. Set GEMINI_API_KEY in .env")
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=2048,
                )
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise
    
    async def analyze_sentiment(self, texts: List[str]) -> Dict[str, Any]:
        """Analyze sentiment of news texts."""
        if not texts:
            return {
                "overall": "NEUTRAL",
                "confidence": 50.0,
                "breakdown": {"positive": 0, "neutral": 0, "negative": 0}
            }
        
        prompt = f"""You are a financial sentiment analyst for Indian stock markets.
Analyze the sentiment of the following news headlines/content and classify as POSITIVE, NEUTRAL, or NEGATIVE.

News Items:
{chr(10).join([f'{i+1}. {text}' for i, text in enumerate(texts)])}

Respond in JSON format only:
{{
    "overall_sentiment": "POSITIVE" | "NEUTRAL" | "NEGATIVE",
    "confidence": <0-100>,
    "individual_sentiments": [
        {{"text": "...", "sentiment": "...", "reason": "..."}}
    ],
    "key_factors": ["factor1", "factor2"]
}}"""

        try:
            response = await self.generate(prompt)
            # Extract JSON from response
            json_str = response.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.startswith("```"):
                json_str = json_str[3:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            return json.loads(json_str.strip())
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
            return {
                "overall_sentiment": "NEUTRAL",
                "confidence": 50.0,
                "individual_sentiments": [],
                "key_factors": []
            }
    
    async def generate_investment_thesis(
        self,
        symbol: str,
        technical_data: Dict[str, Any],
        financial_data: Optional[Dict[str, Any]],
        sentiment_data: Optional[Dict[str, Any]],
        recommendation: str
    ) -> List[str]:
        """Generate 3-point investment thesis."""
        prompt = f"""You are a Senior Quantitative Equity Researcher for NSE/BSE markets.
Generate a concise 3-point investment thesis for {symbol}.

Recommendation: {recommendation}

Technical Analysis:
- RSI: {technical_data.get('rsi', 'N/A')}
- Price vs 200-EMA: {'Above' if technical_data.get('price_above_ema') else 'Below'}
- Current Price: ₹{technical_data.get('current_price', 'N/A')}

Financial Data: {json.dumps(financial_data) if financial_data else 'Not available'}

Sentiment Analysis: {json.dumps(sentiment_data) if sentiment_data else 'Not analyzed'}

Provide exactly 3 bullet points that justify the {recommendation} recommendation.
Each point should cite specific data.
Format: Return ONLY a JSON array of 3 strings, nothing else.
Example: ["Point 1", "Point 2", "Point 3"]"""

        try:
            response = await self.generate(prompt)
            json_str = response.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.startswith("```"):
                json_str = json_str[3:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            thesis = json.loads(json_str.strip())
            return thesis[:3] if len(thesis) >= 3 else thesis + ["Insufficient data for additional points"] * (3 - len(thesis))
        except Exception as e:
            logger.error(f"Investment thesis generation error: {e}")
            return [
                f"Technical indicators suggest {recommendation} stance based on RSI and EMA levels.",
                f"Market sentiment and trading patterns support current positioning.",
                f"Risk-reward profile aligns with the {recommendation} recommendation."
            ]
    
    async def extract_financial_metrics(self, pdf_text: str, symbol: str) -> Dict[str, Any]:
        """Extract financial metrics from quarterly result PDF text."""
        prompt = f"""You are a financial data extraction specialist.
Extract key financial metrics from the following quarterly results text for {symbol}.

Text:
{pdf_text[:5000]}  # Limit to first 5000 chars

Extract and return ONLY a JSON object with these fields (use null if not found):
{{
    "revenue_cr": <number or null>,
    "pat_cr": <number or null>,
    "ebitda_cr": <number or null>,
    "eps": <number or null>,
    "debt_to_equity": <number or null>,
    "revenue_growth_pct": <number or null>,
    "pat_growth_pct": <number or null>,
    "eps_growth_pct": <number or null>,
    "operating_cash_flow_cr": <number or null>,
    "fiscal_year": "<string or null>",
    "quarter": "<string or null>"
}}

All monetary values should be in Crores (Cr).
Return ONLY the JSON object, nothing else."""

        try:
            response = await self.generate(prompt)
            json_str = response.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.startswith("```"):
                json_str = json_str[3:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            return json.loads(json_str.strip())
        except Exception as e:
            logger.error(f"Financial extraction error: {e}")
            return {}


# Singleton instance
gemini_client = GeminiClient()
