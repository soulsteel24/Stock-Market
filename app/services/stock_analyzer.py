"""Main stock analyzer orchestrator."""
from typing import Dict, Any, Optional, List
import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.technical_analyzer import technical_analyzer
from app.services.sentiment_analyzer import sentiment_analyzer
from app.services.confidence_scorer import confidence_scorer
from app.services.gemini_client import gemini_client
from app.services.memory_loop import memory_loop
from app.agents.value_momentum_agent import value_momentum_agent
from app.agents.divergence_agent import divergence_agent
from app.agents.risk_reward_agent import risk_reward_agent
from app.agents.safety_veto_agent import safety_veto_agent
from app.services.forecast_service import forecast_service
from app.models.schemas import (
    StockAnalysisResponse, 
    RecommendationType,
    TechnicalIndicators,
    FinancialMetrics,
    ConfidenceBreakdown,
    Warning,
    ForecastAnalysis,
    ForecastDataPoint,
    AgentDebate
)

logger = logging.getLogger(__name__)


class StockAnalyzer:
    """
    Main orchestrator for stock analysis.
    Coordinates all services and agents.
    """
    
    async def analyze_stock(
        self,
        symbol: str,
        db: Optional[Session] = None,
        include_news: bool = True,
        include_technicals: bool = True
    ) -> StockAnalysisResponse:
        """
        Perform complete stock analysis.
        
        Workflow:
        1. Fetch technical data
        2. Get stock info
        3. Analyze news sentiment
        4. Run through all agents
        5. Calculate confidence score
        6. Generate investment thesis
        7. Return complete response
        """
        symbol = symbol.upper().replace(".NS", "")
        logger.info(f"Starting analysis for {symbol}")
        
        
        # NOTE: Changing the parallel flow slightly.
        from app.services.fundamental_analyzer import fundamental_analyzer
        
        # Phase 1: Technicals, Info, and Fundamentals (needed for others)
        phase1_tasks = [
            technical_analyzer.analyze(symbol),
            technical_analyzer.get_stock_info(symbol),
            fundamental_analyzer.full_fundamental_analysis(symbol)
        ]
        
        phase1_results = await asyncio.gather(*phase1_tasks, return_exceptions=True)
        technical_data = phase1_results[0] if not isinstance(phase1_results[0], Exception) else {}
        stock_info = phase1_results[1] if not isinstance(phase1_results[1], Exception) else {}
        fundamental_data = phase1_results[2] if not isinstance(phase1_results[2], Exception) else {}
        
        # Phase 2: Sentiment, Forecast, Agents (Forecast need hist data from technicals)
        phase2_task_map = {}
        phase2_tasks = []
        
        if include_news:
            phase2_task_map[len(phase2_tasks)] = "sentiment"
            phase2_tasks.append(sentiment_analyzer.analyze_news(symbol))
            
        if technical_data.get("historical_df") is not None:
             phase2_task_map[len(phase2_tasks)] = "forecast"
             phase2_tasks.append(forecast_service.predict_prices(symbol, technical_data["historical_df"]))
        
        results = await asyncio.gather(*phase2_tasks, return_exceptions=True)
        
        # Parse Phase 2 results
        sentiment_data = None
        forecast_result = {}
        
        for idx, result in enumerate(results):
            task_type = phase2_task_map.get(idx)
            if isinstance(result, Exception):
                logger.error(f"{task_type} failed: {result}")
                continue
            if result is None:
                continue
                
            if task_type == "sentiment":
                sentiment_data = result
            elif task_type == "forecast":
                forecast_result = result
        
        cp = technical_data.get("current_price") if technical_data else None
        if not cp:
            raise ValueError(f"Could not fetch price data for {symbol}")
        current_price = float(cp)
        
        # Prepare data for agents
        agent_data = {
            "technical": technical_data,
            "financial": fundamental_data.get("fundamental_analysis", {}).get("key_ratios", {}),
            "stock_info": stock_info or {},
            "sentiment": sentiment_data
        }
        
        # Run agents in parallel
        filter_result, divergence_result, risk_reward_result = await asyncio.gather(
            value_momentum_agent.evaluate(agent_data),
            divergence_agent.evaluate(agent_data),
            risk_reward_agent.evaluate(agent_data)
        )
        
        # Determine initial recommendation
        initial_recommendation = self._determine_recommendation(
            filter_result, 
            divergence_result,
            risk_reward_result,
            technical_data,
            forecast_result
        )
        
        # Safety veto check
        safety_result = await safety_veto_agent.evaluate(
            agent_data, 
            initial_recommendation
        )
        
        # Apply veto if needed
        final_recommendation = initial_recommendation
        safety_veto_applied = safety_result.get("vetoed", False)
        
        if safety_veto_applied and initial_recommendation == "BUY":
            final_recommendation = "WATCHLIST"
        
        # Calculate confidence score
        historical_accuracy = 50.0
        if db:
            historical_accuracy = await memory_loop.get_historical_accuracy(db, symbol)
        
        confidence = confidence_scorer.calculate(
            technical_data=technical_data,
            financial_data=agent_data.get("financial"),
            sentiment_data=sentiment_data,
            historical_accuracy=historical_accuracy
        )
        
        # Generate investment thesis
        thesis = await gemini_client.generate_investment_thesis(
            symbol=symbol,
            technical_data=technical_data,
            financial_data=agent_data.get("financial"),
            sentiment_data={
                "sentiment": sentiment_data.overall_sentiment.value if sentiment_data else "NEUTRAL",
                "confidence": sentiment_data.confidence if sentiment_data else 50
            } if sentiment_data else None,
            recommendation=final_recommendation,
            forecast_data=forecast_result
        )
        
        # Compile warnings
        warnings = []
        if divergence_result.get("has_divergence"):
            for w in divergence_result.get("warnings", []):
                warnings.append(Warning(
                    type=w["type"],
                    message=w["message"],
                    severity=w.get("severity", "WARNING")
                ))
        
        if safety_veto_applied:
            for reason in safety_result.get("veto_reasons", []):
                warnings.append(Warning(
                    type="SAFETY_VETO",
                    message=f"🛑 {reason}",
                    severity="CRITICAL"
                ))
        
        for w in safety_result.get("warnings", []):
            warnings.append(Warning(
                type=w["type"],
                message=w["message"],
                severity=w.get("severity", "WARNING")
            ))
        
        # Build Agent Debate
        # 1. Momentum Agent
        m_passed = filter_result.get("passed_count", 0)
        m_total = filter_result.get("total_evaluated", 0)
        m_score = filter_result.get("filter_score", 0)
        
        passing_metrics = []
        for k, v in filter_result.get("criteria", {}).items():
            if v.get("passed") is True:
                passing_metrics.append(k.replace('_', ' ').title())
                
        momentum_text = f"The stock passed {m_passed} out of {m_total} Value/Momentum criteria (Score: {m_score}%). "
        if passing_metrics:
            momentum_text += f"Key passing strengths include: {', '.join(passing_metrics)}."
        else:
            momentum_text += "No strong momentum or value signals detected."
            
        # 2. Contrarian (Divergence) Agent
        if divergence_result.get("has_divergence"):
            div_reasons = [d.get("description", "") for d in divergence_result.get("divergences", [])]
            contrarian_text = f"Detected {len(div_reasons)} bearish divergence(s): " + "; ".join(div_reasons) + "."
        else:
            contrarian_text = "No concerning bearish divergences detected between technicals and fundamentals."
            
        # 3. Safety Veto Agent
        if safety_veto_applied:
            veto_reasons = safety_result.get("veto_reasons", [])
            safety_text = f"Safety Veto applied due to high risk: " + "; ".join(veto_reasons) + ". Buying is restricted."
        else:
            safety_text = "All critical safety and liquidity protocols passed."
            
        agent_debate = AgentDebate(
            momentum_agent=momentum_text,
            contrarian_agent=contrarian_text,
            safety_veto_agent=safety_text
        )
        
        raw_funds = fundamental_data.get("raw_data", fundamental_data) if fundamental_data else {}
        fin_metrics = FinancialMetrics(
            pe_ratio=raw_funds.get("trailing_pe") or raw_funds.get("pe_ratio"),
            trailing_pe=raw_funds.get("trailing_pe"),
            forward_pe=raw_funds.get("forward_pe"),
            price_to_book=raw_funds.get("price_to_book") or raw_funds.get("pb_ratio"),
            eps=raw_funds.get("trailing_eps") or raw_funds.get("eps_ttm"),
            trailing_eps=raw_funds.get("trailing_eps") or raw_funds.get("eps_ttm"),
            profit_margin_pct=raw_funds.get("profit_margins") or raw_funds.get("profit_margin_pct"),
            revenue_growth_pct=raw_funds.get("revenue_growth") or raw_funds.get("revenue_growth_pct"),
            promoter_holding_pct=raw_funds.get("promoter_holding_pct") or raw_funds.get("held_percent_insiders"),
            fii_holding_pct=raw_funds.get("fii_holding_pct") or raw_funds.get("held_percent_institutions"),
            ebitda_cr=raw_funds.get("ebitda"),
            debt_to_equity=raw_funds.get("debt_to_equity"),
            net_income_history=raw_funds.get("net_income_history")
        )

        # Build response
        return StockAnalysisResponse(
            symbol=symbol,
            name=stock_info.get("name") if stock_info else None,
            sector=stock_info.get("sector") if stock_info else None,
            recommendation=RecommendationType(final_recommendation),
            confidence_score=confidence["weighted_total"],
            confidence_breakdown=ConfidenceBreakdown(
                technical_score=confidence["technical_score"],
                financial_score=confidence["financial_score"],
                sentiment_score=confidence["sentiment_score"],
                historical_score=confidence["historical_score"],
                weighted_total=confidence["weighted_total"]
            ),
            current_price=current_price,
            entry_price=risk_reward_result.get("entry_price", current_price),
            target_price=risk_reward_result.get("target_price", current_price * 1.15),
            stop_loss=risk_reward_result.get("stop_loss", current_price * 0.92),
            risk_reward_ratio=risk_reward_result.get("ratio_string", "1:2"),
            potential_return_pct=risk_reward_result.get("potential_return_pct", 15.0),
            potential_loss_pct=risk_reward_result.get("potential_loss_pct", 8.0),
            technical_indicators=TechnicalIndicators(
                rsi=technical_data.get("rsi", 50),
                ema_200=technical_data.get("ema_200", current_price),
                current_price=current_price,
                price_above_ema=technical_data.get("price_above_ema", False),
                rsi_in_range=technical_data.get("rsi_in_range", False)
            ),
            financial_metrics=fin_metrics,
            sentiment_analysis=sentiment_data,
            agent_debate=agent_debate,
            raw_fundamentals=raw_funds,
            investment_thesis=thesis,
            sources=["Technical Analysis", "Fundamental Analysis", "News Sentiment", "AI Forecast"] + (
                ["BSE/NSE Announcements"] if include_news else []
            ),
            forecast_analysis=ForecastAnalysis(**forecast_result) if forecast_result else None,
            warnings=warnings,
            safety_veto_applied=safety_veto_applied,
            analyzed_at=datetime.utcnow()
        )
    
    def _determine_recommendation(
        self,
        filter_result: Dict[str, Any],
        divergence_result: Dict[str, Any],
        risk_reward_result: Dict[str, Any],
        technical_data: Dict[str, Any],
        forecast_result: Dict[str, Any]
    ) -> str:
        """Determine recommendation based on agent outputs."""
        
        # Start with filter result
        passed_filter = filter_result.get("passed_filter", False)
        filter_score = filter_result.get("filter_score", 0)
        
        # Check risk-reward
        meets_ratio = risk_reward_result.get("meets_minimum_ratio", False)
        
        # Check for divergence
        has_divergence = divergence_result.get("has_divergence", False)
        
        # Technical score
        tech_score = technical_data.get("technical_score", 50)
        
        # Forecast Trend
        forecast_trend = forecast_result.get("trend_pct", 0)
        
        # Decision logic
        if passed_filter and meets_ratio and not has_divergence:
            if tech_score >= 70 or forecast_trend > 5.0:
                return "BUY"
            elif tech_score >= 50 or forecast_trend > 0:
                return "WATCHLIST"
            else:
                return "HOLD"
        elif passed_filter and has_divergence:
            return "WATCHLIST"  # Wait for divergence to resolve
        elif not passed_filter and filter_score < 30:
            return "SELL"
        else:
            return "HOLD"
    
    async def analyze_batch(
        self,
        symbols: List[str],
        db: Optional[Session] = None,
        include_news: bool = True,
        include_technicals: bool = True
    ) -> Dict[str, Any]:
        """Analyze multiple stocks in parallel."""
        results = []
        errors = []
        
        async def analyze_single(symbol: str):
            try:
                return await self.analyze_stock(
                    symbol, db, include_news, include_technicals
                )
            except Exception as e:
                logger.error(f"Analysis failed for {symbol}: {e}")
                return {"symbol": symbol, "error": str(e)}
        
        for symbol in symbols:
            result = await analyze_single(symbol)
            if isinstance(result, StockAnalysisResponse):
                results.append(result)
            else:
                errors.append(result)
            await asyncio.sleep(1.5)
        
        return {
            "total_analyzed": len(symbols),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors
        }


# Singleton instance
stock_analyzer = StockAnalyzer()
