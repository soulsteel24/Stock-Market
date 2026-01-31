"""Risk-Reward Calculation Agent."""
from typing import Dict, Any, Optional, Tuple
from app.agents.base_agent import BaseAgent
from app.config import get_settings

settings = get_settings()


class RiskRewardAgent(BaseAgent):
    """
    Agent that calculates entry, target, stop-loss and risk-reward ratio.
    
    Enforces minimum 1:2 risk-reward ratio.
    """
    
    def __init__(self):
        super().__init__("RiskReward")
        self.min_ratio = settings.min_risk_reward_ratio
    
    async def evaluate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate risk-reward parameters."""
        technical = data.get("technical", {})
        current_price = technical.get("current_price", 0)
        
        if current_price <= 0:
            return {
                "agent": self.name,
                "error": "Invalid current price",
                "passed": False
            }
        
        # Calculate price levels
        entry, target, stop_loss = self._calculate_levels(technical, current_price)
        
        # Calculate risk-reward
        risk = entry - stop_loss
        reward = target - entry
        
        if risk <= 0:
            risk = current_price * 0.05  # Default 5% risk
        
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        # Calculate percentages
        potential_return = ((target - entry) / entry) * 100
        potential_loss = ((entry - stop_loss) / entry) * 100
        
        # Check if meets minimum ratio
        meets_ratio = risk_reward_ratio >= self.min_ratio
        
        self.log_decision(
            f"{'APPROVED' if meets_ratio else 'REJECTED'}",
            f"Risk:Reward = 1:{risk_reward_ratio:.2f} (minimum 1:{self.min_ratio})"
        )
        
        return {
            "agent": self.name,
            "entry_price": round(entry, 2),
            "target_price": round(target, 2),
            "stop_loss": round(stop_loss, 2),
            "risk_reward_ratio": round(risk_reward_ratio, 2),
            "ratio_string": f"1:{risk_reward_ratio:.1f}",
            "potential_return_pct": round(potential_return, 2),
            "potential_loss_pct": round(potential_loss, 2),
            "meets_minimum_ratio": meets_ratio,
            "minimum_required": self.min_ratio
        }
    
    def _calculate_levels(
        self, 
        technical: Dict[str, Any],
        current_price: float
    ) -> Tuple[float, float, float]:
        """Calculate entry, target, and stop-loss levels."""
        
        # Get technical indicators
        ema_200 = technical.get("ema_200", current_price)
        ema_50 = technical.get("ema_50", current_price)
        bb_upper = technical.get("bb_upper", current_price * 1.1)
        bb_lower = technical.get("bb_lower", current_price * 0.9)
        high_52w = technical.get("high_52w", current_price * 1.2)
        low_52w = technical.get("low_52w", current_price * 0.8)
        rsi = technical.get("rsi", 50)
        
        # Entry price strategy
        # If oversold (RSI < 40), enter at current price
        # If neutral, enter at slight pullback
        # If overbought, wait for pullback
        if rsi < 40:
            entry = current_price
        elif rsi < 60:
            entry = current_price * 0.99  # 1% below current
        else:
            entry = min(current_price * 0.97, ema_50)  # Wait for pullback
        
        # Target price strategy
        # Use Bollinger Band upper or resistance levels
        target_options = [
            bb_upper,
            high_52w * 0.95,  # Just below 52-week high
            current_price * 1.15,  # 15% upside
        ]
        target = min(target_options)  # Conservative target
        
        # Stop-loss strategy
        # Use lower of: Bollinger lower, 200 EMA, or fixed %
        stop_options = [
            bb_lower,
            ema_200 * 0.98,  # Just below 200 EMA
            current_price * 0.92,  # 8% below current
            low_52w * 1.05,  # Just above 52-week low
        ]
        stop_loss = max(stop_options)  # Tightest stop that makes sense
        
        # Ensure proper order
        if entry >= target:
            target = entry * 1.15
        if stop_loss >= entry:
            stop_loss = entry * 0.92
        
        return entry, target, stop_loss
    
    def adjust_for_volatility(
        self,
        entry: float,
        target: float,
        stop_loss: float,
        volatility: float  # e.g., VIX value
    ) -> Tuple[float, float, float]:
        """Adjust levels based on market volatility."""
        if volatility > 20:
            # Higher volatility = wider stops
            multiplier = 1 + (volatility - 20) / 100
            stop_loss = entry - (entry - stop_loss) * multiplier
            target = entry + (target - entry) * multiplier
        
        return entry, target, stop_loss


# Singleton instance
risk_reward_agent = RiskRewardAgent()
