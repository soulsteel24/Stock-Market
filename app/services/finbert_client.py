"""
FinBERT Client for financial sentiment analysis.
Uses HuggingFace transformers locally.
"""
import logging
from typing import List, Dict, Any
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

logger = logging.getLogger(__name__)

class FinbertClient:
    """
    Client for FinBERT sentiment analysis.
    Loads model locally to avoid API costs/latency for bulk operations.
    """
    
    def __init__(self):
        self.pipeline = None
        self.model_name = "Vansh180/FinBERT-India-v1"
        self._is_initialized = False

    def initialize(self):
        """Lazy load the model."""
        if self._is_initialized:
            return

        try:
            logger.info("Loading FinBERT model...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.pipeline = pipeline(
                "sentiment-analysis", 
                model=self.model, 
                tokenizer=self.tokenizer,
                return_all_scores=True
            )
            self._is_initialized = True
            logger.info("FinBERT model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load FinBERT: {e}")
            self.pipeline = None

    async def analyze_batch(self, texts: List[str]) -> Dict[str, Any]:
        """
        Analyze sentiment for a batch of texts.
        Returns aggregated sentiment metrics.
        """
        if not texts:
            return self._empty_result()
            
        if not self._is_initialized:
            self.initialize()
            
        if not self.pipeline:
            logger.warning("FinBERT pipeline not available, returning neutral.")
            return self._empty_result()

        try:
            # Process in batches to avoid OOM
            results = self.pipeline(texts)
            
            # Aggregate results
            positive_score = 0.0
            negative_score = 0.0
            neutral_score = 0.0
            cnt = 0
            
            for res_list in results:
                # res_list is like [{'label': 'positive', 'score': 0.9}, ...]
                # Normalize labels to lower case handling differences in model configs
                scores = {item['label'].lower(): item['score'] for item in res_list}
                
                # Try to map robustly in case labels are slightly different
                pos = scores.get('positive', scores.get('1', 0))
                neu = scores.get('neutral', scores.get('0', 0))
                neg = scores.get('negative', scores.get('-1', scores.get('2', 0)))
                
                positive_score += pos
                neutral_score += neu
                negative_score += neg
                cnt += 1
            
            if cnt == 0:
                return self._empty_result()

            # Average scores
            avg_pos = positive_score / cnt
            avg_neg = negative_score / cnt
            avg_neu = neutral_score / cnt
            
            # Determine overall sentiment
            if avg_pos > avg_neg and avg_pos > avg_neu:
                overall = "POSITIVE"
                confidence = avg_pos
            elif avg_neg > avg_pos and avg_neg > avg_neu:
                overall = "NEGATIVE"
                confidence = avg_neg
            else:
                overall = "NEUTRAL"
                confidence = avg_neu

            normalized_score = avg_pos - avg_neg

            return {
                "overall_sentiment": overall,
                "confidence": round(confidence * 100, 2),
                "normalized_score": round(normalized_score, 4),
                "breakdown": {
                    "positive": round(avg_pos, 4),
                    "neutral": round(avg_neu, 4),
                    "negative": round(avg_neg, 4)
                }
            }
            
        except Exception as e:
            logger.error(f"FinBERT analysis failed: {e}")
            return self._empty_result()

    def _empty_result(self):
        return {
            "overall_sentiment": "NEUTRAL",
            "confidence": 0.0,
            "normalized_score": 0.0,
            "breakdown": {"positive": 0, "neutral": 0, "negative": 0}
        }

# Singleton
finbert_client = FinbertClient()
