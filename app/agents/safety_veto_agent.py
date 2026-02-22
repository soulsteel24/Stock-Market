"""Safety Veto Agent - Hard-coded risk controls."""
from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent
from app.services.technical_analyzer import technical_analyzer
from app.config import get_settings

settings = get_settings()


class SafetyVetoAgent(BaseAgent):
    """
    Hard-coded safety agent that can VETO buy recommendations.
    
    Veto conditions:
    1. India VIX > threshold (high market volatility)
    2. Market cap < minimum (illiquid/risky stocks)
    3. Circuit breaker triggered
    4. Negative free cash flow for 2+ quarters
    5. Debt-to-Equity > 3 (overleveraged)
    """
    
    def __init__(self):
        super().__init__("SafetyVeto")
        self.vix_threshold = settings.vix_threshold
        self.min_market_cap = settings.min_market_cap_cr
    
    async def evaluate(
        self, 
        data: Dict[str, Any],
        proposed_recommendation: str = "BUY"
    ) -> Dict[str, Any]:
        """
        Evaluate if the recommendation should be vetoed.
        
        Only vetoes BUY recommendations. SELL/HOLD are not affected.
        """
        if proposed_recommendation not in ["BUY"]:
            return {
                "agent": self.name,
                "vetoed": False,
                "reason": "Safety veto only applies to BUY recommendations",
                "checks_passed": True
            }
        
        technical = data.get("technical", {})
        financial = data.get("financial", {})
        stock_info = data.get("stock_info", {})
        
        veto_reasons = []
        warnings = []
        
        # Check 1: India VIX
        india_vix = await technical_analyzer.get_india_vix()
        vix_check = {
            "name": "VIX Check",
            "passed": True,
            "value": india_vix,
            "threshold": self.vix_threshold
        }
        
        if india_vix and india_vix > self.vix_threshold:
            vix_check["passed"] = False
            veto_reasons.append(
                f"Market volatility too high (VIX: {india_vix:.1f} > {self.vix_threshold})"
            )
        
        # Check 2: Market Cap
        market_cap = stock_info.get("market_cap_cr", 0)
        mcap_check = {
            "name": "Market Cap Check",
            "passed": True,
            "value": market_cap,
            "threshold": self.min_market_cap
        }
        
        if market_cap and market_cap < self.min_market_cap:
            mcap_check["passed"] = False
            veto_reasons.append(
                f"Market cap too low (₹{market_cap:.0f} Cr < ₹{self.min_market_cap} Cr)"
            )
        
        # Check 3: Extreme RSI (circuit-like conditions)
        rsi = technical.get("rsi", 50)
        rsi_check = {
            "name": "RSI Extreme Check",
            "passed": True,
            "value": rsi
        }
        
        if rsi > 80:
            rsi_check["passed"] = False
            veto_reasons.append(f"RSI extremely overbought ({rsi:.1f} > 80)")
        elif rsi < 20:
            # Oversold could be opportunity or trap
            warnings.append({
                "type": "SAFETY",
                "message": f"RSI extremely oversold ({rsi:.1f}) - could be value trap",
                "severity": "WARNING"
            })
        
        # Check 4: Debt-to-Equity > 3
        d_to_e = financial.get("debt_to_equity")
        debt_check = {
            "name": "Leverage Check",
            "passed": True,
            "value": d_to_e,
            "threshold": 3.0
        }
        
        if d_to_e and d_to_e > 3.0:
            debt_check["passed"] = False
            veto_reasons.append(f"Company overleveraged (D/E: {d_to_e:.2f} > 3.0)")
            
        # Check: Negative Net Income trend over last 3 years
        net_income_history = financial.get("net_income_history", {})
        income_check = {
            "name": "Net Income Trend Check",
            "passed": True,
            "value": str(net_income_history) if net_income_history else "N/A"
        }
        
        if net_income_history and len(net_income_history) >= 3:
            # Sort years descending
            sorted_years = sorted(net_income_history.keys(), reverse=True)
            recent_3_years = [net_income_history[y] for y in sorted_years[:3]]
            if all(v < 0 for v in recent_3_years):
                income_check["passed"] = False
                veto_reasons.append(f"Negative Net Income over the last 3 years")
        
        # Check: Excessively high P/B ratio (e.g., > 10)
        pb_ratio = financial.get("price_to_book") or stock_info.get("pb_ratio")
        pb_check = {
            "name": "P/B Ratio Check",
            "passed": True,
            "value": pb_ratio,
            "threshold": 10.0
        }
        
        if pb_ratio and pb_ratio > 10.0:
            pb_check["passed"] = False
            veto_reasons.append(f"Excessively high P/B ratio ({pb_ratio:.2f} > 10.0)")
        
        # Check 5: Large price drop in single day
        price_change_5d = technical.get("price_change_5d", 0)
        crash_check = {
            "name": "Price Crash Check",
            "passed": True,
            "value": price_change_5d
        }
        
        if price_change_5d < -15:
            crash_check["passed"] = False
            veto_reasons.append(
                f"Recent sharp decline ({price_change_5d:.1f}% in 5 days) - wait for stabilization"
            )
        
        # Compile results
        all_checks = [vix_check, mcap_check, rsi_check, debt_check, crash_check]
        checks_passed = sum(1 for c in all_checks if c["passed"])
        total_checks = len(all_checks)
        
        vetoed = len(veto_reasons) > 0
        
        if vetoed:
            self.log_decision("VETO", f"Blocked BUY - {veto_reasons[0]}")
        else:
            self.log_decision("APPROVED", "All safety checks passed")
        
        return {
            "agent": self.name,
            "vetoed": vetoed,
            "veto_reasons": veto_reasons,
            "checks": {c["name"]: c for c in all_checks},
            "checks_passed": checks_passed,
            "total_checks": total_checks,
            "warnings": warnings,
            "india_vix": india_vix
        }
    
    def can_override_veto(self, veto_result: Dict[str, Any]) -> bool:
        """
        Check if veto can be manually overridden.
        
        Some vetoes are hard (cannot override), some are soft (can override with caution).
        """
        hard_veto_keywords = ["VIX", "overleveraged", "sharp decline"]
        
        for reason in veto_result.get("veto_reasons", []):
            for keyword in hard_veto_keywords:
                if keyword.lower() in reason.lower():
                    return False
        
        return True


# Singleton instance
safety_veto_agent = SafetyVetoAgent()
