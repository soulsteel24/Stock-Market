"""Value + Momentum Filter Agent."""
from typing import Dict, Any, Optional
from app.agents.base_agent import BaseAgent
from app.config import get_settings

settings = get_settings()


class ValueMomentumAgent(BaseAgent):
    """
    Agent that applies Value + Momentum filters.
    
    Filters:
    - EPS growth > 15%
    - P/E ratio < Sector average
    - Positive Cash Flow
    - RSI between 40-60
    - Price > 200-day EMA
    """
    
    def __init__(self):
        super().__init__("ValueMomentum")
        self.min_eps_growth = settings.min_eps_growth
        self.rsi_lower = settings.rsi_lower_bound
        self.rsi_upper = settings.rsi_upper_bound
    
    async def evaluate(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate stock against Value + Momentum criteria."""
        technical = data.get("technical", {})
        financial = data.get("financial", {})
        stock_info = data.get("stock_info", {})
        
        # Track pass/fail for each criterion
        criteria = {}
        passed_count = 0
        total_criteria = 5
        
        # 1. EPS Growth > 15%
        eps_growth = financial.get("eps_growth_pct")
        if eps_growth is not None:
            criteria["eps_growth"] = {
                "passed": eps_growth >= self.min_eps_growth,
                "value": eps_growth,
                "threshold": f">= {self.min_eps_growth}%"
            }
            if eps_growth >= self.min_eps_growth:
                passed_count += 1
        else:
            criteria["eps_growth"] = {
                "passed": None,
                "value": "N/A",
                "threshold": f">= {self.min_eps_growth}%"
            }
        
        # 2. P/E Ratio < Sector average (we use 25 as general threshold)
        pe_ratio = stock_info.get("pe_ratio")
        sector_pe = 25  # Default sector average
        if pe_ratio is not None:
            criteria["pe_ratio"] = {
                "passed": pe_ratio < sector_pe,
                "value": pe_ratio,
                "threshold": f"< {sector_pe} (sector avg)"
            }
            if pe_ratio < sector_pe:
                passed_count += 1
        else:
            criteria["pe_ratio"] = {
                "passed": None,
                "value": "N/A",
                "threshold": f"< {sector_pe} (sector avg)"
            }
        
        # 3. Positive Cash Flow
        cash_flow = financial.get("operating_cash_flow_cr")
        if cash_flow is not None:
            criteria["cash_flow"] = {
                "passed": cash_flow > 0,
                "value": cash_flow,
                "threshold": "> 0 Cr"
            }
            if cash_flow > 0:
                passed_count += 1
        else:
            # Check if positive_cash_flow flag exists
            positive_cf = financial.get("positive_cash_flow")
            criteria["cash_flow"] = {
                "passed": positive_cf if positive_cf is not None else None,
                "value": "Positive" if positive_cf else "N/A",
                "threshold": "> 0 Cr"
            }
            if positive_cf:
                passed_count += 1
        
        # 4. RSI between 40-60
        rsi = technical.get("rsi")
        if rsi is not None:
            rsi_passed = self.rsi_lower <= rsi <= self.rsi_upper
            criteria["rsi"] = {
                "passed": rsi_passed,
                "value": rsi,
                "threshold": f"{self.rsi_lower}-{self.rsi_upper}"
            }
            if rsi_passed:
                passed_count += 1
        else:
            criteria["rsi"] = {
                "passed": None,
                "value": "N/A",
                "threshold": f"{self.rsi_lower}-{self.rsi_upper}"
            }
        
        # 5. Price > 200-day EMA
        price_above_ema = technical.get("price_above_ema")
        criteria["price_vs_ema"] = {
            "passed": price_above_ema,
            "value": "Above" if price_above_ema else "Below",
            "threshold": "Price > 200-EMA"
        }
        if price_above_ema:
            passed_count += 1
        
        # Calculate filter score
        # Count only criteria that have data
        valid_criteria = sum(1 for c in criteria.values() if c["passed"] is not None)
        passed_criteria = sum(1 for c in criteria.values() if c["passed"] is True)
        
        filter_score = (passed_criteria / valid_criteria * 100) if valid_criteria > 0 else 0
        
        # Determine if passed filter
        passed_filter = passed_criteria >= 3  # At least 3 out of 5
        
        self.log_decision(
            f"{'PASSED' if passed_filter else 'FAILED'} ({passed_criteria}/{valid_criteria})",
            f"Filter score: {filter_score:.0f}%"
        )
        
        return {
            "agent": self.name,
            "passed_filter": passed_filter,
            "filter_score": round(filter_score, 2),
            "passed_count": passed_criteria,
            "total_evaluated": valid_criteria,
            "criteria": criteria
        }


# Singleton instance
value_momentum_agent = ValueMomentumAgent()
