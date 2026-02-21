"""
Forecast Service using Prophet (via Darts if overhead fits, or direct Prophet).
For simplicity and robustness, we use Prophet directly here as it's great for daily stock data.
"""
import logging
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from prophet import Prophet

logger = logging.getLogger(__name__)

class ForecastService:
    """
    Service for stock price forecasting.
    """
    
    async def predict_prices(self, symbol: str, df: pd.DataFrame, days: int = 7) -> Dict[str, Any]:
        """
        Generate price forecast for the next N days.
        DataFrame must have 'Date' and 'Close' columns (or compatible).
        """
        try:
            if df is None or df.empty or len(df) < 30:
                logger.warning(f"Insufficient data for forecasting {symbol}")
                return {}

            # Prepare data for Prophet: needs columns 'ds' and 'y'
            # Assuming df has index as Date or a 'Date' column
            data = df.copy()
            
            # Reset index if Date is the index
            if not 'Date' in data.columns and isinstance(data.index, pd.DatetimeIndex):
                data = data.reset_index()
                
            # Rename columns
            # Find the date column
            date_col = None
            for col in data.columns:
                if 'date' in col.lower():
                    date_col = col
                    break
            
            if not date_col:
                # Try to use index if it wasn't caught
                if isinstance(data.index, pd.DatetimeIndex):
                    data = data.reset_index()
                    date_col = 'index' # defaults to index name or 'index'
                else:
                    return {}
            
            # Find close column
            close_col = 'Close'
            if 'Close' not in data.columns:
                return {}

            # Prepare for Prophet
            prophet_df = pd.DataFrame()
            prophet_df['ds'] = pd.to_datetime(data[date_col]).dt.tz_localize(None) # Remove timezone for Prophet
            prophet_df['y'] = data[close_col]
            
            # Calculate SMAs on historical data
            data['SMA_20'] = data[close_col].rolling(window=20).mean()
            data['SMA_50'] = data[close_col].rolling(window=50).mean()

            # Fit model with slightly more flexibility
            m = Prophet(daily_seasonality=True, yearly_seasonality=True, changepoint_prior_scale=0.1)
            m.fit(prophet_df)
            
            # Make future dataframe
            future = m.make_future_dataframe(periods=days)
            forecast = m.predict(future)
            
            # Extract next N days
            # The tail contains the 'periods' number of new days
            next_days = forecast.tail(days)
            
            forecast_data = []
            
            # 1. Add historical points (last 60 days)
            hist_tail = data.tail(60)
            for _, row in hist_tail.iterrows():
                forecast_data.append({
                    "date": pd.to_datetime(row[date_col]).strftime('%Y-%m-%d'),
                    "historical_price": round(row[close_col], 2),
                    "sma_20": round(row['SMA_20'], 2) if pd.notna(row['SMA_20']) else None,
                    "sma_50": round(row['SMA_50'], 2) if pd.notna(row['SMA_50']) else None,
                })
                
            # 2. Add forecasted points
            for _, row in next_days.iterrows():
                forecast_data.append({
                    "date": row['ds'].strftime('%Y-%m-%d'),
                    "predicted_price": round(row['yhat'], 2),
                    "lower_bound": round(row['yhat_lower'], 2),
                    "upper_bound": round(row['yhat_upper'], 2)
                })
            
            # Calculate trend
            current_close = prophet_df['y'].iloc[-1]
            last_pred = next_days['yhat'].iloc[-1]
            trend_pct = ((last_pred - current_close) / current_close) * 100
            
            # Determine bullish or bearish
            last_hist = hist_tail.iloc[-1]
            c_price = last_hist[close_col]
            sma20 = last_hist['SMA_20']
            sma50 = last_hist['SMA_50']
            
            bullish_trend = False
            if pd.notna(sma20) and pd.notna(sma50):
                bullish_trend = bool(c_price > sma20 and sma20 > sma50)
            
            return {
                "forecast": forecast_data,
                "trend_pct": round(trend_pct, 2),
                "bullish_trend": bullish_trend,
                "model": "Prophet",
                "days_forecasted": days
            }

        except Exception as e:
            logger.error(f"Forecasting failed for {symbol}: {e}")
            return {}

# Singleton
forecast_service = ForecastService()
