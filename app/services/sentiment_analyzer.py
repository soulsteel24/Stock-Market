"""Sentiment analysis service using Gemini."""
from typing import List, Dict, Any, Optional
import logging
from app.services.gemini_client import gemini_client
from app.services.news_scraper import news_scraper, NewsItem
from transformers import pipeline
from app.models.schemas import SentimentType, SentimentAnalysis

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Sentiment analysis for stock news."""
    
    def __init__(self):
        self.pipe = None
        
    def _get_pipeline(self):
        if not self.pipe:
            logger.info("Loading local FinBERT model...")
            self.pipe = pipeline("text-classification", model="Vansh180/FinBERT-India-v1")
        return self.pipe
    
    async def analyze_news(self, symbol: str) -> Optional[SentimentAnalysis]:
        """Analyze sentiment of news for a stock."""
        # Get news articles (uses sync method with thread pool)
        news_items = news_scraper.get_all_news(symbol)
        
        if not news_items:
            logger.info(f"No news found for {symbol}")
            return SentimentAnalysis(
                overall_sentiment=SentimentType.NEUTRAL,
                confidence=50.0,
                positive_count=0,
                neutral_count=0,
                negative_count=0,
                key_headlines=[]
            )
        
        # Extract titles for analysis
        titles = [item.title for item in news_items]
        
        # Custom FinBERT Analysis (Preferred locally)
        try:
            finbert_pipe = self._get_pipeline()
            results = finbert_pipe(titles)
            
            pos_count = 0
            neu_count = 0
            neg_count = 0
            confidence_sum = 0.0
            
            for res in results:
                label = res['label'].lower()
                if label in ['positive', '1']:
                    pos_count += 1
                elif label in ['negative', '-1', '2']:
                    neg_count += 1
                else:
                    neu_count += 1
                confidence_sum += res['score']
                
            cnt = len(titles)
            avg_confidence = (confidence_sum / cnt) * 100 if cnt > 0 else 50.0
            
            if pos_count > neg_count and pos_count > neu_count:
                overall = SentimentType.POSITIVE
            elif neg_count > pos_count and neg_count > neu_count:
                overall = SentimentType.NEGATIVE
            else:
                overall = SentimentType.NEUTRAL
                
            normalized_score = (pos_count - neg_count) / max(cnt, 1)
            
            return SentimentAnalysis(
                overall_sentiment=overall,
                confidence=round(avg_confidence, 2),
                normalized_score=round(normalized_score, 4),
                positive_count=pos_count,
                neutral_count=neu_count,
                negative_count=neg_count,
                key_headlines=titles[:5]
            )
        except Exception as e:
            logger.warning(f"FinBERT failed, falling back to Gemini: {e}")

        # Fallback to Gemini
        if gemini_client.is_connected():
            result = await gemini_client.analyze_sentiment(titles)
            
            # Count sentiments
            positive = 0
            neutral = 0
            negative = 0
            
            for item in result.get("individual_sentiments", []):
                sentiment = item.get("sentiment", "NEUTRAL").upper()
                if sentiment == "POSITIVE":
                    positive += 1
                elif sentiment == "NEGATIVE":
                    negative += 1
                else:
                    neutral += 1
            
            overall = result.get("overall_sentiment", "NEUTRAL").upper()
            
            normalized_score = (positive - negative) / max(len(titles), 1)
            
            return SentimentAnalysis(
                overall_sentiment=SentimentType(overall),
                confidence=result.get("confidence", 50.0),
                normalized_score=round(normalized_score, 4),
                positive_count=positive,
                neutral_count=neutral,
                negative_count=negative,
                key_headlines=titles[:5]
            )
        else:
            # Fallback: Basic keyword analysis
            return await self._basic_sentiment_analysis(titles)
    
    async def _basic_sentiment_analysis(
        self, 
        titles: List[str]
    ) -> SentimentAnalysis:
        """Basic sentiment analysis using keywords."""
        positive_keywords = [
            'surge', 'jump', 'gain', 'profit', 'growth', 'bullish', 'up',
            'rise', 'upgrade', 'strong', 'beat', 'outperform', 'record',
            'dividend', 'buy', 'positive', 'expansion'
        ]
        negative_keywords = [
            'fall', 'drop', 'loss', 'decline', 'bearish', 'down', 'crash',
            'miss', 'downgrade', 'weak', 'concern', 'risk', 'sell', 'cut',
            'negative', 'warning', 'fraud', 'investigation'
        ]
        
        positive = 0
        negative = 0
        neutral = 0
        
        for title in titles:
            title_lower = title.lower()
            pos_score = sum(1 for kw in positive_keywords if kw in title_lower)
            neg_score = sum(1 for kw in negative_keywords if kw in title_lower)
            
            if pos_score > neg_score:
                positive += 1
            elif neg_score > pos_score:
                negative += 1
            else:
                neutral += 1
        
        total = len(titles)
        if positive > negative and positive > neutral:
            overall = SentimentType.POSITIVE
            confidence = (positive / total) * 100
        elif negative > positive and negative > neutral:
            overall = SentimentType.NEGATIVE
            confidence = (negative / total) * 100
        else:
            overall = SentimentType.NEUTRAL
            confidence = 50.0
        
        normalized_score = (positive - negative) / max(total, 1)
        
        return SentimentAnalysis(
            overall_sentiment=overall,
            confidence=round(confidence, 2),
            normalized_score=round(normalized_score, 4),
            positive_count=positive,
            neutral_count=neutral,
            negative_count=negative,
            key_headlines=titles[:5]
        )
    
    def sentiment_to_score(self, sentiment: SentimentAnalysis) -> float:
        """Convert sentiment to a numerical score (0-100)."""
        base_score = 50
        
        if sentiment.overall_sentiment == SentimentType.POSITIVE:
            score = 70 + (sentiment.confidence - 50) * 0.6
        elif sentiment.overall_sentiment == SentimentType.NEGATIVE:
            score = 30 - (sentiment.confidence - 50) * 0.6
        else:
            score = base_score
        
        return max(0, min(100, score))


# Singleton instance
sentiment_analyzer = SentimentAnalyzer()
