"""Technical analysis engine using nsepython (primary) and yfinance (fallback)."""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Try nsepython first, fallback to yfinance
try:
    from nsepython import quote_equity, equity_history, indiavix
    NSE_AVAILABLE = True
    logger.info("nsepython loaded successfully")
except ImportError:
    NSE_AVAILABLE = False
    logger.warning("nsepython not available, using yfinance only")

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False
    logger.error("yfinance not available!")


class TechnicalAnalyzer:
    """Technical analysis using NSE Python (primary) + yfinance (fallback)."""
    
    def __init__(self):
        """Initialize technical analyzer."""
        self.nse_available = NSE_AVAILABLE
        self.yf_available = YF_AVAILABLE
    
    def _convert_symbol(self, symbol: str) -> str:
        """Clean symbol for NSE format (no suffix)."""
        return symbol.upper().replace(".NS", "").replace(".BO", "").strip()
    
    def _get_yf_symbol(self, symbol: str) -> str:
        """Convert symbol for yfinance format."""
        clean = self._convert_symbol(symbol)
        return f"{clean}.NS"
    
    async def _fetch_nse_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch data from NSE Python."""
        if not self.nse_available:
            return None
        
        try:
            clean_symbol = self._convert_symbol(symbol)
            
            # Get quote data using quote_equity
            quote = quote_equity(clean_symbol)
            
            if not quote or 'priceInfo' not in quote:
                logger.warning(f"NSE: No data for {clean_symbol}")
                return None
            
            price_info = quote.get('priceInfo', {})
            security_info = quote.get('securityInfo', {})
            info = quote.get('info', {})
            
            current_price = price_info.get('lastPrice', 0)
            prev_close = price_info.get('previousClose', current_price)
            
            # Get historical data for technical indicators
            df = None
            try:
                from datetime import datetime, timedelta
                end_date = datetime.now().strftime("%d-%m-%Y")
                start_date = (datetime.now() - timedelta(days=365)).strftime("%d-%m-%Y")
                hist_data = equity_history(clean_symbol, "EQ", start_date, end_date)
                
                if hist_data is not None and len(hist_data) > 0:
                    df = hist_data.copy()
                    # Try different column names for closing price
                    close_cols = ['CH_CLOSING_PRICE', 'CLOSE', 'close', 'Close', 'LTP', 'LAST']
                    for col in close_cols:
                        if col in df.columns:
                            df['Close'] = pd.to_numeric(df[col], errors='coerce')
                            break
                    
                    if 'Close' not in df.columns:
                        # If no Close column found, try to get from any numeric column
                        for col in df.columns:
                            try:
                                numeric_vals = pd.to_numeric(df[col], errors='coerce')
                                if numeric_vals.notna().sum() > 10:
                                    df['Close'] = numeric_vals
                                    break
                            except:
                                continue
                    
                    df = df.dropna(subset=['Close']) if 'Close' in df.columns else None
                    logger.info(f"NSE history for {clean_symbol}: {len(df) if df is not None else 0} rows")
            except Exception as hist_err:
                logger.warning(f"NSE history error for {clean_symbol}: {hist_err}")
                df = None
            
            return {
                "current_price": current_price,
                "prev_close": prev_close,
                "change_pct": ((current_price - prev_close) / prev_close * 100) if prev_close else 0,
                "high": price_info.get('intraDayHighLow', {}).get('max', current_price),
                "low": price_info.get('intraDayHighLow', {}).get('min', current_price),
                "volume": security_info.get('tradedVolume', 0),
                "market_cap": security_info.get('issuedSize', 0) * current_price / 1e7,  # In Cr
                "historical_df": df,
                "source": "nsepython",
                "company_name": info.get('companyName', clean_symbol),
                "industry": info.get('industry', 'Unknown')
            }
        except Exception as e:
            logger.error(f"NSE fetch error for {symbol}: {e}")
            return None
    
    async def _fetch_yfinance_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch data from yfinance as fallback."""
        if not self.yf_available:
            return None
        
        try:
            yf_symbol = self._get_yf_symbol(symbol)
            ticker = yf.Ticker(yf_symbol)
            
            # Get historical data
            df = ticker.history(period="1y")
            
            if df.empty:
                logger.warning(f"yfinance: No data for {yf_symbol}")
                return None
            
            current_price = df['Close'].iloc[-1]
            prev_close = df['Close'].iloc[-2] if len(df) > 1 else current_price
            
            return {
                "current_price": float(current_price),
                "prev_close": float(prev_close),
                "change_pct": float((current_price - prev_close) / prev_close * 100),
                "high": float(df['High'].iloc[-1]),
                "low": float(df['Low'].iloc[-1]),
                "volume": int(df['Volume'].iloc[-1]),
                "market_cap": 0,  # Would need info call
                "historical_df": df,
                "source": "yfinance"
            }
        except Exception as e:
            logger.error(f"yfinance fetch error for {symbol}: {e}")
            return None
    
    async def analyze(self, symbol: str) -> Dict[str, Any]:
        """
        Perform technical analysis on a stock.
        Uses nsepython as primary, yfinance as fallback.
        """
        clean_symbol = self._convert_symbol(symbol)
        
        # Try NSE first
        data = await self._fetch_nse_data(clean_symbol)
        
        # Fallback to yfinance
        if data is None:
            logger.info(f"Falling back to yfinance for {clean_symbol}")
            data = await self._fetch_yfinance_data(clean_symbol)
        
        if data is None:
            logger.warning(f"No data found for {clean_symbol}")
            return {}
        
        current_price = data.get("current_price", 0)
        df = data.get("historical_df")
        
        # Calculate technical indicators
        result = {
            "symbol": clean_symbol,
            "current_price": current_price,
            "prev_close": data.get("prev_close"),
            "change_pct": data.get("change_pct"),
            "volume": data.get("volume"),
            "market_cap_cr": data.get("market_cap", 0),
            "data_source": data.get("source", "unknown")
        }
        
        if df is not None and len(df) >= 14:
            closes = df['Close'].values if 'Close' in df.columns else None
            
            if closes is not None and len(closes) >= 14:
                # RSI
                result["rsi"] = self._calculate_rsi(closes)
                
                # EMAs
                result["ema_200"] = self._calculate_ema(closes, 200) if len(closes) >= 200 else None
                result["ema_50"] = self._calculate_ema(closes, 50) if len(closes) >= 50 else None
                result["ema_20"] = self._calculate_ema(closes, 20) if len(closes) >= 20 else None
                
                # MACD
                if len(closes) >= 26:
                    macd_data = self._calculate_macd(closes)
                    result["macd"] = macd_data.get("macd")
                    result["macd_signal"] = macd_data.get("signal")
                    result["macd_histogram"] = macd_data.get("histogram")
                
                # Bollinger Bands
                if len(closes) >= 20:
                    bb = self._calculate_bollinger_bands(closes)
                    result["bb_upper"] = bb.get("upper")
                    result["bb_middle"] = bb.get("middle")
                    result["bb_lower"] = bb.get("lower")
                
                # Price position checks
                if result.get("ema_200"):
                    result["price_above_ema"] = current_price > result["ema_200"]
                
                # RSI range check
                rsi = result.get("rsi", 50)
                result["rsi_in_range"] = 40 <= rsi <= 60
                result["rsi_oversold"] = rsi < 30
                result["rsi_overbought"] = rsi > 70
        
        # Calculate overall technical score
        result["technical_score"] = self._calculate_technical_score(result)
        
        return result
    
    def _calculate_rsi(self, prices: np.ndarray, period: int = 14) -> float:
        """Calculate RSI."""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return float(100 - (100 / (1 + rs)))
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> Optional[float]:
        """Calculate EMA."""
        if len(prices) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return float(ema)
    
    def _calculate_macd(self, prices: np.ndarray) -> Dict[str, float]:
        """Calculate MACD."""
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        
        if ema_12 is None or ema_26 is None:
            return {}
        
        macd = ema_12 - ema_26
        
        # Calculate signal line (9-period EMA of MACD)
        # Simplified - using last value
        signal = macd * 0.9  # Approximation
        
        return {
            "macd": macd,
            "signal": signal,
            "histogram": macd - signal
        }
    
    def _calculate_bollinger_bands(self, prices: np.ndarray, period: int = 20) -> Dict[str, float]:
        """Calculate Bollinger Bands."""
        if len(prices) < period:
            return {}
        
        sma = np.mean(prices[-period:])
        std = np.std(prices[-period:])
        
        return {
            "upper": float(sma + (2 * std)),
            "middle": float(sma),
            "lower": float(sma - (2 * std))
        }
    
    def _calculate_technical_score(self, data: Dict[str, Any]) -> float:
        """Calculate overall technical score (0-100)."""
        score = 50.0  # Start neutral
        
        rsi = data.get("rsi", 50)
        if 30 <= rsi <= 70:
            score += 10
        if 40 <= rsi <= 60:
            score += 5
        
        if data.get("price_above_ema"):
            score += 15
        
        macd_hist = data.get("macd_histogram", 0)
        if macd_hist and macd_hist > 0:
            score += 10
        
        current = data.get("current_price", 0)
        bb_lower = data.get("bb_lower", 0)
        bb_upper = data.get("bb_upper", 0)
        
        if current and bb_lower and current > bb_lower:
            score += 5
        if current and bb_upper and current < bb_upper:
            score += 5
        
        return max(0, min(100, score))
    
    async def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get basic stock info."""
        clean_symbol = self._convert_symbol(symbol)
        
        # Try NSE first
        if self.nse_available:
            try:
                quote = quote_equity(clean_symbol)
                if quote and 'info' in quote:
                    info = quote.get('info', {})
                    return {
                        "name": info.get('companyName', clean_symbol),
                        "symbol": clean_symbol,
                        "sector": info.get('industry', 'Unknown'),
                        "market_cap": quote.get('securityInfo', {}).get('issuedSize', 0)
                    }
            except Exception as e:
                logger.warning(f"NSE info fetch error: {e}")
        
        # Fallback to yfinance
        if self.yf_available:
            try:
                ticker = yf.Ticker(self._get_yf_symbol(clean_symbol))
                info = ticker.info
                return {
                    "name": info.get("longName", info.get("shortName", clean_symbol)),
                    "symbol": clean_symbol,
                    "sector": info.get("sector", "Unknown"),
                    "market_cap": info.get("marketCap", 0) / 1e7  # Convert to Cr
                }
            except Exception as e:
                logger.warning(f"yfinance info fetch error: {e}")
        
        return {"name": clean_symbol, "symbol": clean_symbol, "sector": "Unknown"}
    
    async def get_india_vix(self) -> Optional[float]:
        """Get India VIX value."""
        # Try NSE first
        if self.nse_available:
            try:
                vix_value = indiavix()
                if vix_value:
                    return float(vix_value)
            except Exception as e:
                logger.warning(f"NSE VIX fetch error: {e}")
        
        # Fallback to yfinance
        if self.yf_available:
            try:
                vix = yf.Ticker("^INDIAVIX")
                hist = vix.history(period="1d")
                if not hist.empty:
                    return float(hist['Close'].iloc[-1])
            except Exception as e:
                logger.warning(f"yfinance VIX fetch error: {e}")
        
        return None


# Singleton instance
technical_analyzer = TechnicalAnalyzer()
