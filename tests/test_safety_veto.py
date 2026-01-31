"""Tests for safety veto agent."""
import pytest
from unittest.mock import patch, AsyncMock
from app.agents.safety_veto_agent import SafetyVetoAgent


class TestSafetyVetoAgent:
    """Test suite for SafetyVetoAgent."""
    
    @pytest.fixture
    def agent(self):
        return SafetyVetoAgent()
    
    @pytest.mark.asyncio
    async def test_no_veto_for_hold(self, agent):
        """Test that HOLD recommendations are not vetoed."""
        result = await agent.evaluate({}, "HOLD")
        assert result["vetoed"] == False
    
    @pytest.mark.asyncio
    async def test_no_veto_for_sell(self, agent):
        """Test that SELL recommendations are not vetoed."""
        result = await agent.evaluate({}, "SELL")
        assert result["vetoed"] == False
    
    @pytest.mark.asyncio
    @patch('app.agents.safety_veto_agent.technical_analyzer')
    async def test_vix_veto(self, mock_analyzer, agent):
        """Test VIX-based veto."""
        mock_analyzer.get_india_vix = AsyncMock(return_value=30.0)  # Above threshold
        
        data = {
            "technical": {"rsi": 50, "price_change_5d": 0},
            "financial": {"debt_to_equity": 1.0},
            "stock_info": {"market_cap_cr": 1000}
        }
        
        result = await agent.evaluate(data, "BUY")
        
        assert result["vetoed"] == True
        assert any("VIX" in reason for reason in result["veto_reasons"])
    
    @pytest.mark.asyncio
    @patch('app.agents.safety_veto_agent.technical_analyzer')
    async def test_low_market_cap_veto(self, mock_analyzer, agent):
        """Test market cap veto."""
        mock_analyzer.get_india_vix = AsyncMock(return_value=15.0)  # Normal VIX
        
        data = {
            "technical": {"rsi": 50, "price_change_5d": 0},
            "financial": {"debt_to_equity": 1.0},
            "stock_info": {"market_cap_cr": 100}  # Below threshold
        }
        
        result = await agent.evaluate(data, "BUY")
        
        assert result["vetoed"] == True
        assert any("cap" in reason.lower() for reason in result["veto_reasons"])
    
    @pytest.mark.asyncio
    @patch('app.agents.safety_veto_agent.technical_analyzer')
    async def test_overleveraged_veto(self, mock_analyzer, agent):
        """Test debt-to-equity veto."""
        mock_analyzer.get_india_vix = AsyncMock(return_value=15.0)
        
        data = {
            "technical": {"rsi": 50, "price_change_5d": 0},
            "financial": {"debt_to_equity": 4.0},  # Above threshold
            "stock_info": {"market_cap_cr": 1000}
        }
        
        result = await agent.evaluate(data, "BUY")
        
        assert result["vetoed"] == True
        assert any("leveraged" in reason.lower() for reason in result["veto_reasons"])
    
    @pytest.mark.asyncio
    @patch('app.agents.safety_veto_agent.technical_analyzer')
    async def test_sharp_decline_veto(self, mock_analyzer, agent):
        """Test price crash veto."""
        mock_analyzer.get_india_vix = AsyncMock(return_value=15.0)
        
        data = {
            "technical": {"rsi": 50, "price_change_5d": -20},  # Sharp drop
            "financial": {"debt_to_equity": 1.0},
            "stock_info": {"market_cap_cr": 1000}
        }
        
        result = await agent.evaluate(data, "BUY")
        
        assert result["vetoed"] == True
        assert any("decline" in reason.lower() for reason in result["veto_reasons"])
    
    @pytest.mark.asyncio
    @patch('app.agents.safety_veto_agent.technical_analyzer')
    async def test_all_checks_pass(self, mock_analyzer, agent):
        """Test when all safety checks pass."""
        mock_analyzer.get_india_vix = AsyncMock(return_value=15.0)
        
        data = {
            "technical": {"rsi": 50, "price_change_5d": 2},
            "financial": {"debt_to_equity": 0.8},
            "stock_info": {"market_cap_cr": 5000}
        }
        
        result = await agent.evaluate(data, "BUY")
        
        assert result["vetoed"] == False
        assert result["checks_passed"] == result["total_checks"]
    
    def test_override_check(self, agent):
        """Test veto override eligibility."""
        # Hard veto (cannot override)
        hard_veto = {"veto_reasons": ["Market volatility too high (VIX: 30)"]}
        assert agent.can_override_veto(hard_veto) == False
        
        # Soft veto (can override)
        soft_veto = {"veto_reasons": ["Market cap too low"]}
        assert agent.can_override_veto(soft_veto) == True
