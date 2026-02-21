"""Fundamental analyzer for Indian stocks with financial ratios."""
import logging
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class FundamentalAnalyzer:
    """Analyzes stock fundamentals including P/E, P/B, ROE, and other key ratios."""
    
    # Benchmark values for Indian market
    BENCHMARKS = {
        "pe_ratio": {"low": 15, "fair": 25, "high": 40},
        "pb_ratio": {"low": 1.5, "fair": 3, "high": 6},
        "roe": {"poor": 10, "good": 15, "excellent": 20},
        "debt_to_equity": {"safe": 0.5, "moderate": 1, "risky": 2},
        "current_ratio": {"poor": 1, "good": 1.5, "excellent": 2},
        "dividend_yield": {"low": 0.5, "moderate": 2, "high": 4},
        "eps_growth": {"poor": 0, "moderate": 10, "good": 20}
    }
    
    async def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """Get fundamental data for a stock from NSE/yfinance."""
        try:
            # Try yfinance first for richer fundamental data
            fundamentals = await self._get_yfinance_fundamentals(symbol)
            if fundamentals and (fundamentals.get("pe_ratio") or fundamentals.get("roe") or fundamentals.get("profit_margins")):
                fundamentals["data_source"] = "yfinance"
                return fundamentals
            
            # Fallback to nsepython
            fundamentals = await self._get_nse_fundamentals(symbol)
            if fundamentals:
                fundamentals["data_source"] = "nsepython"
                
            if fundamentals and not "error" in fundamentals:
                # Add shareholding data if available
                from app.services.shareholding_scraper import shareholding_scraper
                shareholding = await shareholding_scraper.get_shareholding(symbol)
                if shareholding:
                    fundamentals.update(shareholding)
                return fundamentals
            
            return {"error": "Could not fetch fundamental data"}
        except Exception as e:
            logger.error(f"Fundamental analysis error for {symbol}: {e}")
            return {"error": str(e)}
    
    async def _get_nse_fundamentals(self, symbol: str) -> Optional[Dict]:
        """Get fundamentals from NSE."""
        try:
            from nsepython import quote_equity
            import asyncio
            
            data = await asyncio.get_event_loop().run_in_executor(
                None, quote_equity, symbol
            )
            
            if not data or "priceInfo" not in data:
                return None
            
            price_info = data.get("priceInfo", {})
            sec_info = data.get("securityInfo", {})
            metadata = data.get("metadata", {})
            
            # Extract key ratios
            face_value = sec_info.get("faceValue", 10)
            
            return {
                "symbol": symbol,
                "company_name": metadata.get("companyName", symbol),
                "industry": metadata.get("industry", "Unknown"),
                "series": metadata.get("series", "EQ"),
                "face_value": face_value,
                "market_cap_cr": self._parse_market_cap(data),
                "pe_ratio": self._safe_float(data.get("metadata", {}).get("pdSymbolPe")),
                "sector_pe": self._safe_float(data.get("metadata", {}).get("pdSectorPe")),
                "book_value": self._safe_float(sec_info.get("bookValue")),
                "price_band": {
                    "upper": price_info.get("upperCP"),
                    "lower": price_info.get("lowerCP")
                },
                "week_52_high": self._safe_float(price_info.get("weekHighLow", {}).get("max")),
                "week_52_low": self._safe_float(price_info.get("weekHighLow", {}).get("min")),
                "current_price": self._safe_float(price_info.get("lastPrice")),
                "fetched_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.warning(f"NSE fundamentals error: {e}")
            return None
    
    async def _get_yfinance_fundamentals(self, symbol: str) -> Optional[Dict]:
        """Get fundamentals from yfinance."""
        try:
            import yfinance as yf
            import asyncio
            
            ticker_symbol = f"{symbol}.NS"
            ticker = yf.Ticker(ticker_symbol)
            
            info = await asyncio.get_event_loop().run_in_executor(
                None, lambda: ticker.info
            )
            
            if not info:
                return None
            
            return {
                "symbol": symbol,
                "company_name": info.get("longName", symbol),
                "industry": info.get("industry", "Unknown"),
                "sector": info.get("sector", "Unknown"),
                "market_cap_cr": round(info.get("marketCap", 0) / 10000000, 2),
                "pe_ratio": self._safe_float(info.get("trailingPE")),
                "forward_pe": self._safe_float(info.get("forwardPE")),
                "pb_ratio": self._safe_float(info.get("priceToBook")),
                "ps_ratio": self._safe_float(info.get("priceToSalesTrailing12Months")),
                "peg_ratio": self._safe_float(info.get("pegRatio")),
                "enterprise_value_cr": round(info.get("enterpriseValue", 0) / 10000000, 2),
                "ev_to_ebitda": self._safe_float(info.get("enterpriseToEbitda")),
                "ebitda": self._safe_float(info.get("ebitda")),
                "ebitda_margins": self._safe_float(info.get("ebitdaMargins")) * 100 if info.get("ebitdaMargins") else None,
                "profit_margins": self._safe_float(info.get("profitMargins")) * 100 if info.get("profitMargins") else None,
                "gross_margins": self._safe_float(info.get("grossMargins")) * 100 if info.get("grossMargins") else None,
                "operating_margins": self._safe_float(info.get("operatingMargins")) * 100 if info.get("operatingMargins") else None,
                "held_percent_insiders": self._safe_float(info.get("heldPercentInsiders")) * 100 if info.get("heldPercentInsiders") else None,
                "held_percent_institutions": self._safe_float(info.get("heldPercentInstitutions")) * 100 if info.get("heldPercentInstitutions") else None,
                "book_value": self._safe_float(info.get("bookValue")),
                "price_to_book": self._safe_float(info.get("priceToBook")),
                "eps_ttm": self._safe_float(info.get("trailingEps")),
                "eps_forward": self._safe_float(info.get("forwardEps")),
                "dividend_yield": self._safe_float(info.get("dividendYield")) * 100 if info.get("dividendYield") else 0,
                "dividend_rate": self._safe_float(info.get("dividendRate")),
                "payout_ratio": self._safe_float(info.get("payoutRatio")) * 100 if info.get("payoutRatio") else None,
                "roe": self._safe_float(info.get("returnOnEquity")) * 100 if info.get("returnOnEquity") else None,
                "roa": self._safe_float(info.get("returnOnAssets")) * 100 if info.get("returnOnAssets") else None,
                "debt_to_equity": self._safe_float(info.get("debtToEquity")) / 100 if info.get("debtToEquity") else None,
                "current_ratio": self._safe_float(info.get("currentRatio")),
                "quick_ratio": self._safe_float(info.get("quickRatio")),
                "revenue_growth": self._safe_float(info.get("revenueGrowth")) * 100 if info.get("revenueGrowth") else None,
                "earnings_growth": self._safe_float(info.get("earningsGrowth")) * 100 if info.get("earningsGrowth") else None,
                "free_cash_flow_cr": round(info.get("freeCashflow", 0) / 10000000, 2) if info.get("freeCashflow") else None,
                "operating_cash_flow_cr": round(info.get("operatingCashflow", 0) / 10000000, 2) if info.get("operatingCashflow") else None,
                "total_revenue_cr": round(info.get("totalRevenue", 0) / 10000000, 2) if info.get("totalRevenue") else None,
                "net_income_to_common_cr": round(info.get("netIncomeToCommon", 0) / 10000000, 2) if info.get("netIncomeToCommon") else None,
                "total_debt_cr": round(info.get("totalDebt", 0) / 10000000, 2) if info.get("totalDebt") else None,
                "total_cash_cr": round(info.get("totalCash", 0) / 10000000, 2) if info.get("totalCash") else None,
                "week_52_high": self._safe_float(info.get("fiftyTwoWeekHigh")),
                "week_52_low": self._safe_float(info.get("fiftyTwoWeekLow")),
                "current_price": self._safe_float(info.get("currentPrice")),
                "target_mean_price": self._safe_float(info.get("targetMeanPrice")),
                "recommendation": info.get("recommendationKey", "hold"),
                "beta": self._safe_float(info.get("beta")),
                "fetched_at": datetime.now().isoformat()
            }
        except Exception as e:
            logger.warning(f"yfinance fundamentals error: {e}")
            return None
    
    def analyze_fundamentals(self, data: Dict) -> Dict[str, Any]:
        """Analyze fundamental data and provide assessment."""
        if not data or "error" in data:
            return {"score": 0, "rating": "Unknown", "analysis": []}
        
        score = 50  # Base score
        analysis = []
        warnings = []
        positives = []
        
        # P/E Ratio Analysis
        pe = data.get("pe_ratio")
        sector_pe = data.get("sector_pe")
        if pe:
            if pe < self.BENCHMARKS["pe_ratio"]["low"]:
                score += 10
                positives.append(f"Attractive P/E ratio of {pe:.1f} (undervalued)")
            elif pe < self.BENCHMARKS["pe_ratio"]["fair"]:
                score += 5
                analysis.append(f"Fair P/E ratio of {pe:.1f}")
            elif pe > self.BENCHMARKS["pe_ratio"]["high"]:
                score -= 10
                warnings.append(f"High P/E ratio of {pe:.1f} (potentially overvalued)")
            
            if sector_pe and pe < sector_pe:
                score += 5
                positives.append(f"Trading below sector P/E ({pe:.1f} vs {sector_pe:.1f})")
        
        # P/B Ratio Analysis
        pb = data.get("pb_ratio")
        if pb:
            if pb < self.BENCHMARKS["pb_ratio"]["low"]:
                score += 8
                positives.append(f"Low P/B ratio of {pb:.2f} (undervalued)")
            elif pb > self.BENCHMARKS["pb_ratio"]["high"]:
                score -= 5
                warnings.append(f"High P/B ratio of {pb:.2f}")
        
        # ROE Analysis
        roe = data.get("roe")
        if roe:
            if roe > self.BENCHMARKS["roe"]["excellent"]:
                score += 12
                positives.append(f"Excellent ROE of {roe:.1f}%")
            elif roe > self.BENCHMARKS["roe"]["good"]:
                score += 6
                positives.append(f"Good ROE of {roe:.1f}%")
            elif roe < self.BENCHMARKS["roe"]["poor"]:
                score -= 8
                warnings.append(f"Poor ROE of {roe:.1f}%")
        
        # Debt to Equity Analysis
        de = data.get("debt_to_equity")
        if de is not None:
            if de < self.BENCHMARKS["debt_to_equity"]["safe"]:
                score += 8
                positives.append(f"Low debt (D/E: {de:.2f})")
            elif de > self.BENCHMARKS["debt_to_equity"]["risky"]:
                score -= 10
                warnings.append(f"High debt (D/E: {de:.2f})")
        
        # Current Ratio Analysis
        cr = data.get("current_ratio")
        if cr:
            if cr > self.BENCHMARKS["current_ratio"]["excellent"]:
                score += 5
                positives.append(f"Strong liquidity (Current Ratio: {cr:.2f})")
            elif cr < self.BENCHMARKS["current_ratio"]["poor"]:
                score -= 8
                warnings.append(f"Weak liquidity (Current Ratio: {cr:.2f})")
        
        # Dividend Yield Analysis
        div_yield = data.get("dividend_yield", 0)
        if div_yield and div_yield > self.BENCHMARKS["dividend_yield"]["high"]:
            score += 5
            positives.append(f"High dividend yield of {div_yield:.2f}%")
        
        # Growth Analysis
        earnings_growth = data.get("earnings_growth")
        revenue_growth = data.get("revenue_growth")
        if earnings_growth and earnings_growth > self.BENCHMARKS["eps_growth"]["good"]:
            score += 8
            positives.append(f"Strong earnings growth of {earnings_growth:.1f}%")
        if revenue_growth and revenue_growth > 10:
            score += 5
            positives.append(f"Good revenue growth of {revenue_growth:.1f}%")
        
        # Profit Margin Analysis
        profit_margin = data.get("profit_margin")
        if profit_margin:
            if profit_margin > 15:
                score += 5
                positives.append(f"Healthy profit margin of {profit_margin:.1f}%")
            elif profit_margin < 5:
                score -= 5
                warnings.append(f"Thin profit margin of {profit_margin:.1f}%")
        
        # Free Cash Flow
        fcf = data.get("free_cash_flow_cr")
        if fcf and fcf > 0:
            score += 5
            positives.append(f"Positive free cash flow of ₹{fcf:.0f} Cr")
        elif fcf and fcf < 0:
            score -= 5
            warnings.append(f"Negative free cash flow")
        
        # Shareholding Analysis
        promoter_pct = data.get("promoter_holding_pct")
        if promoter_pct:
            if promoter_pct > 50:
                score += 5
                positives.append(f"High promoter holding at {promoter_pct:.1f}%")
            elif promoter_pct < 25:
                score -= 5
                warnings.append(f"Low promoter holding at {promoter_pct:.1f}%")
        
        fii_pct = data.get("fii_holding_pct")
        dii_pct = data.get("dii_holding_pct")
        if fii_pct and dii_pct:
            inst_holding = fii_pct + dii_pct
            if inst_holding > 30:
                score += 5
                positives.append(f"Strong institutional backing ({inst_holding:.1f}%)")
        
        # Determine rating
        score = max(0, min(100, score))
        if score >= 75:
            rating = "STRONG"
        elif score >= 60:
            rating = "GOOD"
        elif score >= 45:
            rating = "FAIR"
        elif score >= 30:
            rating = "WEAK"
        else:
            rating = "POOR"
        
        return {
            "fundamental_score": round(score, 1),
            "rating": rating,
            "is_fundamentally_strong": score >= 60,
            "positives": positives,
            "warnings": warnings,
            "analysis": analysis,
            "key_ratios": {
                "pe_ratio": pe,
                "pb_ratio": pb,
                "roe": roe,
                "debt_to_equity": de,
                "current_ratio": cr,
                "dividend_yield": div_yield,
                "profit_margin": profit_margin,
                "earnings_growth": earnings_growth
            }
        }
    
    async def get_stock_news_sentiment(self, symbol: str) -> Dict:
        """Get news specific to the stock and analyze sentiment."""
        try:
            from app.services.financial_news_scraper import financial_news_scraper
            
            news = financial_news_scraper.get_stock_news(symbol, 10)
            
            # Simple sentiment analysis
            positive_keywords = ["surge", "jump", "gain", "profit", "growth", "beat", "upgrade", "buy", "bullish", "record", "high", "strong"]
            negative_keywords = ["fall", "drop", "loss", "miss", "downgrade", "sell", "bearish", "low", "weak", "concern", "risk", "decline"]
            
            positive_count = 0
            negative_count = 0
            neutral_count = 0
            
            for item in news:
                title = item.get("title", "").lower()
                if any(kw in title for kw in positive_keywords):
                    positive_count += 1
                elif any(kw in title for kw in negative_keywords):
                    negative_count += 1
                else:
                    neutral_count += 1
            
            total = len(news)
            if total == 0:
                sentiment = "NEUTRAL"
                confidence = 50
            elif positive_count > negative_count:
                sentiment = "POSITIVE"
                confidence = min(85, 50 + (positive_count / total) * 50)
            elif negative_count > positive_count:
                sentiment = "NEGATIVE"
                confidence = min(85, 50 + (negative_count / total) * 50)
            else:
                sentiment = "NEUTRAL"
                confidence = 50
            
            return {
                "symbol": symbol,
                "news_count": total,
                "positive_count": positive_count,
                "negative_count": negative_count,
                "neutral_count": neutral_count,
                "sentiment": sentiment,
                "confidence": round(confidence, 1),
                "headlines": [n.get("title") for n in news[:5]]
            }
        except Exception as e:
            logger.error(f"News sentiment error: {e}")
            return {"sentiment": "UNKNOWN", "confidence": 0}
    
    async def full_fundamental_analysis(self, symbol: str) -> Dict:
        """Complete fundamental analysis with ratios and news."""
        import asyncio
        
        # Fetch fundamentals and news in parallel
        fund_task = self.get_fundamentals(symbol)
        news_task = self.get_stock_news_sentiment(symbol)
        
        fundamentals, news_sentiment = await asyncio.gather(fund_task, news_task)
        
        # Analyze fundamentals
        analysis = self.analyze_fundamentals(fundamentals)
        
        # Combine scores
        combined_score = analysis.get("fundamental_score", 50) * 0.7 + news_sentiment.get("confidence", 50) * 0.3
        
        # Final recommendation based on fundamentals + news
        if analysis.get("is_fundamentally_strong") and news_sentiment.get("sentiment") == "POSITIVE":
            recommendation = "STRONG BUY"
        elif analysis.get("is_fundamentally_strong"):
            recommendation = "BUY"
        elif analysis.get("rating") in ["WEAK", "POOR"] and news_sentiment.get("sentiment") == "NEGATIVE":
            recommendation = "AVOID"
        elif analysis.get("rating") == "FAIR":
            recommendation = "HOLD"
        else:
            recommendation = "HOLD"
        
        return {
            "symbol": symbol,
            "company_name": fundamentals.get("company_name", symbol),
            "sector": fundamentals.get("sector", fundamentals.get("industry", "Unknown")),
            "current_price": fundamentals.get("current_price"),
            "market_cap_cr": fundamentals.get("market_cap_cr"),
            "fundamental_analysis": analysis,
            "news_sentiment": news_sentiment,
            "combined_score": round(combined_score, 1),
            "recommendation": recommendation,
            "data_source": fundamentals.get("data_source", "unknown"),
            "analyzed_at": datetime.now().isoformat()
        }
    
    def _safe_float(self, value) -> Optional[float]:
        """Safely convert value to float."""
        try:
            if value is None:
                return None
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _parse_market_cap(self, data: Dict) -> Optional[float]:
        """Parse market cap from NSE data."""
        try:
            # Try different fields
            if "securityInfo" in data:
                issued_size = data["securityInfo"].get("issuedSize")
                price = data.get("priceInfo", {}).get("lastPrice")
                if issued_size and price:
                    return round((issued_size * price) / 10000000, 2)
            return None
        except:
            return None


# Singleton instance
fundamental_analyzer = FundamentalAnalyzer()
