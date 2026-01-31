"""Tests for technical analyzer."""
import pytest
import pandas as pd
import numpy as np
from app.services.technical_analyzer import TechnicalAnalyzer


class TestTechnicalAnalyzer:
    """Test suite for TechnicalAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        return TechnicalAnalyzer()
    
    def test_nse_symbol_conversion(self, analyzer):
        """Test NSE symbol format conversion."""
        assert analyzer.get_nse_symbol("RELIANCE") == "RELIANCE.NS"
        assert analyzer.get_nse_symbol("TCS.NS") == "TCS.NS"
        assert analyzer.get_nse_symbol("INFY") == "INFY.NS"
    
    def test_rsi_calculation(self, analyzer):
        """Test RSI calculation."""
        prices = pd.Series([44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 
                           45.42, 45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28])
        rsi = analyzer.calculate_rsi(prices, period=14)
        
        # RSI should be between 0 and 100
        assert rsi.iloc[-1] >= 0
        assert rsi.iloc[-1] <= 100
    
    def test_ema_calculation(self, analyzer):
        """Test EMA calculation."""
        prices = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        ema = analyzer.calculate_ema(prices, period=5)
        
        # EMA should smooth the prices
        assert len(ema) == len(prices)
        # Later values should be closer to recent prices
        assert ema.iloc[-1] > ema.iloc[0]
    
    def test_sma_calculation(self, analyzer):
        """Test SMA calculation."""
        prices = pd.Series([10, 20, 30, 40, 50])
        sma = analyzer.calculate_sma(prices, period=3)
        
        # SMA of last 3 values should be (30+40+50)/3 = 40
        assert sma.iloc[-1] == 40
    
    def test_technical_score_calculation(self, analyzer):
        """Test technical score bounds."""
        # All bullish signals
        score = analyzer._calculate_technical_score(
            rsi_in_range=True,
            price_above_ema=True,
            golden_cross=True,
            macd_bullish=True,
            current_rsi=50
        )
        assert 0 <= score <= 100
        assert score > 70  # Should be high
        
        # All bearish signals
        score = analyzer._calculate_technical_score(
            rsi_in_range=False,
            price_above_ema=False,
            golden_cross=False,
            macd_bullish=False,
            current_rsi=75
        )
        assert 0 <= score <= 100
        assert score < 50  # Should be low


class TestMACDCalculation:
    """Test MACD indicator calculation."""
    
    def test_macd_components(self):
        analyzer = TechnicalAnalyzer()
        prices = pd.Series(range(1, 51))  # 50 price points
        
        macd_line, signal_line, histogram = analyzer.calculate_macd(prices)
        
        # All components should have same length
        assert len(macd_line) == len(prices)
        assert len(signal_line) == len(prices)
        assert len(histogram) == len(prices)
        
        # Histogram should be difference of MACD and Signal
        np.testing.assert_array_almost_equal(
            histogram.values,
            (macd_line - signal_line).values
        )


class TestBollingerBands:
    """Test Bollinger Bands calculation."""
    
    def test_bollinger_bands_order(self):
        analyzer = TechnicalAnalyzer()
        prices = pd.Series([100 + i for i in range(50)])
        
        upper, middle, lower = analyzer.calculate_bollinger_bands(prices)
        
        # Bands should maintain order: upper > middle > lower
        assert all(upper.dropna() >= middle.dropna())
        assert all(middle.dropna() >= lower.dropna())
