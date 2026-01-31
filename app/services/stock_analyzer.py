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
from app.models.schemas import (
    StockAnalysisResponse, 
    RecommendationType,
    TechnicalIndicators,
    FinancialMetrics,
    ConfidenceBreakdown,
    Warning
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
        
        # Parallel data fetching
        tasks = []
        task_map = {}  # Track which index corresponds to which task
        
        if include_technicals:
            task_map[len(tasks)] = "technical"
            tasks.append(technical_analyzer.analyze(symbol))
        
        task_map[len(tasks)] = "info"
        tasks.append(technical_analyzer.get_stock_info(symbol))
        
        if include_news:
            task_map[len(tasks)] = "sentiment"
            tasks.append(sentiment_analyzer.analyze_news(symbol))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Parse results using task_map
        technical_data = {}
        stock_info = {}
        sentiment_data = None
        
        for idx, result in enumerate(results):
            task_type = task_map.get(idx)
            if isinstance(result, Exception):
                logger.error(f"{task_type} failed: {result}")
                continue
            if result is None:
                continue
                
            if task_type == "technical":
                technical_data = result or {}
            elif task_type == "info":
                stock_info = result or {}
            elif task_type == "sentiment":
                sentiment_data = result
        
        current_price = technical_data.get("current_price", 0) if technical_data else 0
        if current_price == 0:
            raise ValueError(f"Could not fetch price data for {symbol}")
        
        # Prepare data for agents
        agent_data = {
            "technical": technical_data,
            "financial": {},  # Would come from PDF/RAG
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
            technical_data
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
            recommendation=final_recommendation
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
            financial_metrics=FinancialMetrics() if not agent_data.get("financial") else None,
            sentiment_analysis=sentiment_data,
            investment_thesis=thesis,
            sources=["Technical Analysis", "News Sentiment"] + (
                ["BSE/NSE Announcements"] if include_news else []
            ),
            warnings=warnings,
            safety_veto_applied=safety_veto_applied,
            analyzed_at=datetime.utcnow()
        )
    
    def _determine_recommendation(
        self,
        filter_result: Dict[str, Any],
        divergence_result: Dict[str, Any],
        risk_reward_result: Dict[str, Any],
        technical_data: Dict[str, Any]
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
        
        # Decision logic
        if passed_filter and meets_ratio and not has_divergence:
            if tech_score >= 70:
                return "BUY"
            elif tech_score >= 50:
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
        
        tasks = [analyze_single(s) for s in symbols]
        all_results = await asyncio.gather(*tasks)
        
        for result in all_results:
            if isinstance(result, StockAnalysisResponse):
                results.append(result)
            else:
                errors.append(result)
        
        return {
            "total_analyzed": len(symbols),
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors
        }


# Singleton instance
stock_analyzer = StockAnalyzer()
