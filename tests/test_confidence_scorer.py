"""Tests for confidence scorer."""
import pytest
from app.services.confidence_scorer import ConfidenceScorer
from app.models.schemas import SentimentType, SentimentAnalysis


class TestConfidenceScorer:
    """Test suite for ConfidenceScorer."""
    
    @pytest.fixture
    def scorer(self):
        return ConfidenceScorer()
    
    def test_score_with_all_data(self, scorer):
        """Test scoring with all data available."""
        technical = {"technical_score": 75}
        financial = {"eps_growth_pct": 20, "debt_to_equity": 0.5, "operating_cash_flow_cr": 100}
        sentiment = SentimentAnalysis(
            overall_sentiment=SentimentType.POSITIVE,
            confidence=80,
            positive_count=5,
            neutral_count=2,
            negative_count=1,
            key_headlines=[]
        )
        
        result = scorer.calculate(technical, financial, sentiment, 60)
        
        assert "technical_score" in result
        assert "financial_score" in result
        assert "sentiment_score" in result
        assert "weighted_total" in result
        assert 0 <= result["weighted_total"] <= 100
    
    def test_score_with_no_data(self, scorer):
        """Test scoring with no data (all neutral)."""
        result = scorer.calculate(None, None, None)
        
        # All should be neutral (50)
        assert result["technical_score"] == 50
        assert result["financial_score"] == 50
        assert result["sentiment_score"] == 50
    
    def test_agreement_bonus(self, scorer):
        """Test that agreeing signals get a bonus."""
        # All bullish
        bonus = scorer._calculate_agreement_bonus(75, 70, 65)
        assert bonus > 0
        
        # Mixed signals
        bonus = scorer._calculate_agreement_bonus(75, 35, 50)
        assert bonus == 0
    
    def test_confidence_labels(self, scorer):
        """Test confidence score labeling."""
        assert scorer.get_confidence_label(85) == "Very High Confidence"
        assert scorer.get_confidence_label(70) == "High Confidence"
        assert scorer.get_confidence_label(55) == "Moderate Confidence"
        assert scorer.get_confidence_label(40) == "Low Confidence"
        assert scorer.get_confidence_label(25) == "Very Low Confidence"
    
    def test_financial_score_with_good_metrics(self, scorer):
        """Test financial scoring with strong metrics."""
        financial = {
            "eps_growth_pct": 25,
            "debt_to_equity": 0.3,
            "operating_cash_flow_cr": 500
        }
        score = scorer._calculate_financial_score(financial)
        assert score > 70  # Should be high
    
    def test_financial_score_with_poor_metrics(self, scorer):
        """Test financial scoring with weak metrics."""
        financial = {
            "eps_growth_pct": -10,
            "debt_to_equity": 2.5,
            "operating_cash_flow_cr": -100
        }
        score = scorer._calculate_financial_score(financial)
        assert score < 50  # Should be low


class TestSentimentScoring:
    """Test sentiment to score conversion."""
    
    def test_positive_sentiment(self):
        scorer = ConfidenceScorer()
        sentiment = SentimentAnalysis(
            overall_sentiment=SentimentType.POSITIVE,
            confidence=90,
            positive_count=8,
            neutral_count=1,
            negative_count=1,
            key_headlines=[]
        )
        score = scorer._calculate_sentiment_score(sentiment)
        assert score > 60  # Should be high
    
    def test_negative_sentiment(self):
        scorer = ConfidenceScorer()
        sentiment = SentimentAnalysis(
            overall_sentiment=SentimentType.NEGATIVE,
            confidence=80,
            positive_count=1,
            neutral_count=1,
            negative_count=8,
            key_headlines=[]
        )
        score = scorer._calculate_sentiment_score(sentiment)
        assert score < 40  # Should be low
