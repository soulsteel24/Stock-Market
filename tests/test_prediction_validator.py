"""Tests for prediction validator service."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from app.services.prediction_validator import PredictionValidator
from app.models.database import Recommendation, Stock, OutcomeType, RecommendationType

class TestPredictionValidator:
    
    @pytest.fixture
    def validator(self):
        return PredictionValidator()
        
    @pytest.fixture
    def mock_db(self):
        return Mock()
        
    @pytest.fixture
    def mock_stock(self):
        stock = Mock(spec=Stock)
        stock.symbol = "RELIANCE"
        return stock

    def test_validate_buy_target_hit(self, validator, mock_db, mock_stock):
        """Test BUY recommendation hitting target."""
        rec = Mock(spec=Recommendation)
        rec.id = 1
        rec.stock = mock_stock
        rec.recommendation_type = RecommendationType.BUY
        rec.target_price = 2500
        rec.stop_loss_price = 2300
        rec.expiry_date = datetime.utcnow() + timedelta(days=5)
        
        async def run_test():
            # Mock technical analysis data
            with patch('app.services.prediction_validator.technical_analyzer.analyze', new_callable=AsyncMock) as mock_analyze:
                mock_analyze.return_value = {
                    "current_price": 2550,
                    "day_high": 2550,
                    "day_low": 2400
                }
                
                with patch('app.services.prediction_validator.memory_loop.update_outcome', new_callable=AsyncMock) as mock_update:
                    result = await validator.check_single_recommendation(mock_db, rec)
                    
                    assert result["updated"] is True
                    assert result["outcome"] == "TARGET_HIT"
                    mock_update.assert_called_once()
        
        import asyncio
        asyncio.run(run_test())

    def test_validate_buy_stoploss_hit(self, validator, mock_db, mock_stock):
        """Test BUY recommendation hitting stop-loss."""
        rec = Mock(spec=Recommendation)
        rec.stock = mock_stock
        rec.recommendation_type = RecommendationType.BUY
        rec.target_price = 2500
        rec.stop_loss_price = 2300
        rec.expiry_date = datetime.utcnow() + timedelta(days=5)
        
        async def run_test():
            with patch('app.services.prediction_validator.technical_analyzer.analyze', new_callable=AsyncMock) as mock_analyze:
                mock_analyze.return_value = {
                    "current_price": 2200,
                    "day_high": 2350,
                    "day_low": 2200
                }
                
                with patch('app.services.prediction_validator.memory_loop.update_outcome', new_callable=AsyncMock) as mock_update:
                    result = await validator.check_single_recommendation(mock_db, rec)
                    
                    assert result["updated"] is True
                    assert result["outcome"] == "STOPLOSS_HIT"
        
        import asyncio
        asyncio.run(run_test())

    def test_validate_expired(self, validator, mock_db, mock_stock):
        """Test expired recommendation."""
        rec = Mock(spec=Recommendation)
        rec.stock = mock_stock
        rec.recommendation_type = RecommendationType.BUY
        rec.target_price = 2500
        rec.stop_loss_price = 2300
        rec.expiry_date = datetime.utcnow() - timedelta(days=1)  # Expired
        
        async def run_test():
            with patch('app.services.prediction_validator.technical_analyzer.analyze', new_callable=AsyncMock) as mock_analyze:
                mock_analyze.return_value = {
                    "current_price": 2400,
                    "day_high": 2450,
                    "day_low": 2350
                }
                
                with patch('app.services.prediction_validator.memory_loop.update_outcome', new_callable=AsyncMock) as mock_update:
                    result = await validator.check_single_recommendation(mock_db, rec)
                    
                    assert result["updated"] is True
                    assert result["outcome"] == "EXPIRED"

        import asyncio
        asyncio.run(run_test())
