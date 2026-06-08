"""
Enhanced Market Intelligence Module
Core trading strategy with technical analysis and signal generation
"""

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None
import pandas as pd
import numpy as np
from datetime import datetime, time, timezone
import logging
import time as time_module
from typing import Dict, List, Optional, Any, Tuple
from config import *

logger = logging.getLogger(__name__)


class MarketIntelligence:
    """Enhanced market intelligence for NAS100 trading"""
    
    def __init__(self):
        # Initialize MT5 connection (will be handled by broker)
        pass
    
    def calculate_swing_levels(self, df: pd.DataFrame, lookback: int = LOOKBACK_PERIOD) -> Tuple[Optional[float], Optional[float]]:
        """Calculate swing high and low levels (excluding current candle)"""
        try:
            if df is None or len(df) < lookback + 1:  # Need extra candle to exclude current
                return None, None
            
            # Exclude current candle (last row) for swing calculation
            lookback_data = df.iloc[:-1].tail(lookback)
            
            swing_high = lookback_data['high'].max()
            swing_low = lookback_data['low'].min()
            
            return swing_high, swing_low
            
        except Exception as e:
            logger.error(f"Error calculating swing levels: {e}")
            return None, None
    
    def calculate_sma(self, df: pd.DataFrame, period: int = SMA_PERIOD) -> Optional[float]:
        """Calculate Simple Moving Average"""
        try:
            if df is None or len(df) < period:
                return None
            
            return df['close'].rolling(window=period).mean().iloc[-1]
            
        except Exception as e:
            logger.error(f"Error calculating SMA: {e}")
            return None
    
    def calculate_ema(self, df: pd.DataFrame, period: int = 20) -> Optional[float]:
        """Calculate Exponential Moving Average"""
        try:
            if df is None or len(df) < period:
                return None
            
            return df['close'].ewm(span=period, adjust=False).mean().iloc[-1]
            
        except Exception as e:
            logger.error(f"Error calculating EMA: {e}")
            return None
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index"""
        try:
            if df is None or len(df) < period + 1:
                return None
            
            delta = df['diff'] = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi.iloc[-1]
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return None
    
    def calculate_macd(self, df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, Optional[float]]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        try:
            if df is None or len(df) < slow:
                return {"macd": None, "signal": None, "histogram": None}
            
            ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
            ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            histogram = macd_line - signal_line
            
            return {
                "macd": macd_line.iloc[-1],
                "signal": signal_line.iloc[-1],
                "histogram": histogram.iloc[-1]
            }
            
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            return {"macd": None, "signal": None, "histogram": None}
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> Dict[str, Optional[float]]:
        """Calculate Bollinger Bands"""
        try:
            if df is None or len(df) < period:
                return {"upper": None, "middle": None, "lower": None}
            
            middle = df['close'].rolling(window=period).mean()
            std = df['close'].rolling(window=period).std()
            upper = middle + (std * std_dev)
            lower = middle - (std * std_dev)
            
            return {
                "upper": upper.iloc[-1],
                "middle": middle.iloc[-1],
                "lower": lower.iloc[-1]
            }
            
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            return {"upper": None, "middle": None, "lower": None}
    
    def calculate_atr(self, df: pd.DataFrame, period: int = ATR_PERIOD) -> Optional[float]:
        """Calculate Average True Range"""
        try:
            if df is None or len(df) < period:
                return None
            
            # Calculate True Range
            df = df.copy()
            df['tr0'] = abs(df['high'] - df['low'])
            df['tr1'] = abs(df['high'] - df['close'].shift())
            df['tr2'] = abs(df['low'] - df['close'].shift())
            df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
            
            # Calculate ATR
            atr = df['tr'].rolling(window=period).mean().iloc[-1]
            return atr
            
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return None
    
    def is_london_ny_overlap(self, timestamp: datetime = None) -> bool:
        """Check if current time is within London/NY overlap (12:00-16:00 GMT)"""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            # Extract hour in GMT
            hour = timestamp.hour
            
            return SESSION_START_HOUR <= hour < SESSION_END_HOUR
            
        except Exception as e:
            logger.error(f"Error checking London/NY overlap: {e}")
            return False
    
    def is_asian_session(self, timestamp: datetime = None) -> bool:
        """Check if current time is within Asian session (00:00-08:00 GMT)"""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            # Extract hour in GMT
            hour = timestamp.hour
            
            return 0 <= hour < 8
            
        except Exception as e:
            logger.error(f"Error checking Asian session: {e}")
            return False
    
    def get_market_session(self, timestamp: datetime = None) -> str:
        """Get current market session"""
        try:
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)
            
            hour = timestamp.hour
            
            if 0 <= hour < 8:
                return "Asian"
            elif 8 <= hour < 12:
                return "European"
            elif 12 <= hour < 16:
                return "London/NY Overlap"
            elif 16 <= hour < 20:
                return "US Session"
            else:
                return "Other"
                
        except Exception as e:
            logger.error(f"Error getting market session: {e}")
            return "Unknown"
    
    def align_timeframes(self, df_m15: pd.DataFrame, df_h4: pd.DataFrame) -> bool:
        """Confirm M15 signals align with H4 trend direction"""
        try:
            if df_m15 is None or df_h4 is None:
                return False
            
            if len(df_m15) < 2 or len(df_h4) < 2:
                return False
            
            # Get latest price and SMAs
            current_price = df_m15['close'].iloc[-1]
            sma_m15 = self.calculate_sma(df_m15, SMA_PERIOD)
            sma_h4 = self.calculate_sma(df_h4, SMA_PERIOD)
            
            if sma_m15 is None or sma_h4 is None:
                return False
            
            # Determine trend direction
            m15_trend = "BULLISH" if current_price > sma_m15 else "BEARISH"
            h4_trend = "BULLISH" if current_price > sma_h4 else "BEARISH"
            
            # Check for alignment
            return m15_trend == h4_trend
            
        except Exception as e:
            logger.error(f"Error checking timeframe alignment: {e}")
            return False
    
    def generate_signal(self, df_m15: pd.DataFrame, df_h4: pd.DataFrame) -> Dict[str, Any]:
        """Main signal generation logic combining swing levels, SMAs, and session filter"""
        try:
            # Calculate indicators
            swing_high, swing_low = self.calculate_swing_levels(df_m15)
            sma_m15 = self.calculate_sma(df_m15)
            sma_h4 = self.calculate_sma(df_h4)
            atr = self.calculate_atr(df_m15)
            
            # Calculate additional indicators for confirmation
            rsi = self.calculate_rsi(df_m15)
            macd_data = self.calculate_macd(df_m15)
            bb_data = self.calculate_bollinger_bands(df_m15)
            
            if None in [swing_high, swing_low, sma_m15, sma_h4, atr]:
                logger.warning("Insufficient data for indicator calculation")
                return self._no_signal("Insufficient data for indicator calculation")
            
            # Determine trend direction
            current_price = df_m15['close'].iloc[-1]
            m15_trend = "BULLISH" if current_price > sma_m15 else "BEARISH"
            h4_trend = "BULLISH" if current_price > sma_h4 else "BEARISH"
            
            # Check for alignment
            trend_aligned = (m15_trend == h4_trend)
            
            # Detect swing levels proximity
            proximity_to_swing_high = abs(current_price - swing_high) / swing_high if swing_high != 0 else float('inf')
            proximity_to_swing_low = abs(current_price - swing_low) / swing_low if swing_low != 0 else float('inf')
            
            # Generate signal based on breakout/pullback logic
            signal = None
            reason = ""
            confidence = 0
            
            # Bullish breakout above swing high
            if (current_price > swing_high and 
                df_m15['close'].iloc[-2] <= swing_high and  # Previous candle was at or below swing high
                trend_aligned and 
                m15_trend == "BULLISH"):
                signal = "BUY"
                reason = f"Bullish breakout above swing high ({swing_high:.2f}) with {m15_trend} trend alignment"
                confidence = 70  # Base confidence
                
                # Add confirmation from RSI
                if rsi and rsi > 50:
                    confidence += 10
                    reason += ", RSI bullish"
                
                # Add confirmation from MACD
                if macd_data.get('macd') and macd_data.get('signal') and macd_data['macd'] > macd_data['signal']:
                    confidence += 10
                    reason += ", MACD bullish"
                
                # Add confirmation from Bollinger Bands
                if bb_data.get('lower') and current_price > bb_data['lower']:
                    confidence += 10
                    reason += ", Price above BB lower band"
            
            # Bearish breakout below swing low
            elif (current_price < swing_low and 
                  df_m15['close'].iloc[-2] >= swing_low and  # Previous candle was at or above swing low
                  trend_aligned and 
                  m15_trend == "BEARISH"):
                signal = "SELL"
                reason = f"Bearish breakout below swing low ({swing_low:.2f}) with {m15_trend} trend alignment"
                confidence = 70  # Base confidence
                
                # Add confirmation from RSI
                if rsi and rsi < 50:
                    confidence += 10
                    reason += ", RSI bearish"
                
                # Add confirmation from MACD
                if macd_data.get('macd') and macd_data.get('signal') and macd_data['macd'] < macd_data['signal']:
                    confidence += 10
                    reason += ", MACD bearish"
                
                # Add confirmation from Bollinger Bands
                if bb_data.get('upper') and current_price < bb_data['upper']:
                    confidence += 10
                    reason += ", Price below BB upper band"
            
            # Bullish pullback to swing low in uptrend
            elif (proximity_to_swing_low < 0.002 and  # Within 0.2% of swing low
                  h4_trend == "BULLISH" and
                  m15_trend == "BULLISH" and
                  df_m15['close'].iloc[-1] > df_m15['open'].iloc[-1]):  # Bullish candle
                signal = "BUY"
                reason = f"Bullish pullback to swing low ({swing_low:.2f}) in {h4_trend} H4 trend"
                confidence = 65  # Slightly lower confidence for pullbacks
                
                # Add confirmation from price action
                if df_m15['close'].iloc[-1] > df_m15['high'].iloc[-2]:  # Closed above previous high
                    confidence += 10
                    reason += ", Strong bullish candle"
            
            # Bearish pullback to swing high in downtrend
            elif (proximity_to_swing_high < 0.002 and  # Within 0.2% of swing high
                  h4_trend == "BEARISH" and
                  m15_trend == "BEARISH" and
                  df_m15['close'].iloc[-1] < df_m15['open'].iloc[-1]):  # Bearish candle
                signal = "SELL"
                reason = f"Bearish pullback to swing high ({swing_high:.2f}) in {h4_trend} H4 trend"
                confidence = 65  # Slightly lower confidence for pullbacks
                
                # Add confirmation from price action
                if df_m15['close'].iloc[-1] < df_m15['low'].iloc[-2]:  # Closed below previous low
                    confidence += 10
                    reason += ", Strong bearish candle"
            
            if signal is None:
                return self._no_signal("No clear signal detected")
            
            # Calculate trade parameters
            entry_price = current_price
            if signal == "BUY":
                stop_loss = entry_price - (SL_MULTIPLIER * atr)
                take_profit = entry_price + (TP_MULTIPLIER * (entry_price - stop_loss))
            else:  # SELL
                stop_loss = entry_price + (SL_MULTIPLIER * atr)
                take_profit = entry_price - (TP_MULTIPLIER * (stop_loss - entry_price))
            
            # Risk calculation
            risk_amount = abs(entry_price - stop_loss)
            
            result = {
                "signal": signal,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "atr": atr,
                "swing_high": swing_high,
                "swing_low": swing_low,
                "sma_m15": sma_m15,
                "sma_h4": sma_h4,
                "m15_trend": m15_trend,
                "h4_trend": h4_trend,
                "trend_aligned": trend_aligned,
                "rsi": rsi,
                "macd": macd_data,
                "bollinger_bands": bb_data,
                "reason": reason,
                "confidence": min(confidence, 100),  # Cap at 100%
                "timestamp": datetime.now(timezone.utc),
                "risk_amount": risk_amount,
                "session": self.get_market_session()
            }
            
            logger.info(f"Market Intelligence Signal: {signal} {INSTRUMENT} at {entry_price:.2f}")
            logger.info(f"Reason: {reason}")
            
            return result
        
        except Exception as e:
            logger.error(f"Error in market intelligence signal generation: {e}")
            return self._no_signal(f"Error in signal generation: {str(e)}")
    
    def detect_market_regime(self, df: pd.DataFrame) -> str:
        """Detect market regime based on volatility and trend strength.
        Returns one of: 'trending_low_vol', 'trending_high_vol', 'ranging_low_vol', 'ranging_high_vol'
        """
        try:
            if df is None or len(df) < 20:
                return 'ranging_low_vol'  # default
            
            # Calculate volatility regime using ATR
            atr = self.calculate_atr(df, period=14)
            current_price = df['close'].iloc[-1]
            if atr is None or current_price is None or current_price == 0:
                vol_ratio = 0.01  # default
            else:
                vol_ratio = atr / current_price  # normalized ATR
            
            # Define volatility thresholds (these are examples, can be tuned)
            high_vol_threshold = 0.02  # 2% of price
            low_vol_threshold = 0.005  # 0.5% of price
            
            if vol_ratio > high_vol_threshold:
                volatility_regime = 'high_vol'
            elif vol_ratio < low_vol_threshold:
                volatility_regime = 'low_vol'
            else:
                volatility_regime = 'medium_vol'  # we'll treat medium as low for simplicity in binary classification
            
            # Calculate trend strength using price distance from SMA
            sma = self.calculate_sma(df, period=50)
            if sma is None:
                trend_regime = 'ranging'  # default if no SMA
            else:
                price_sma_diff = abs(current_price - sma) / sma if sma != 0 else 0
                # Trend threshold: if price is more than 1.5 * ATR away from SMA, consider trending
                trend_threshold = 1.5 * (atr if atr is not None else 0) / sma if sma != 0 else 0
                if price_sma_diff > trend_threshold:
                    trend_regime = 'trending'
                else:
                    trend_regime = 'ranging'
            
            # Combine regimes (simplify to two volatility states: high or not high)
            if volatility_regime == 'high_vol':
                vol_state = 'high_vol'
            else:
                vol_state = 'low_vol'  # includes low and medium
            
            return f"{trend_regime}_{vol_state}"
            
        except Exception as e:
            logger.error(f"Error detecting market regime: {e}")
            return 'ranging_low_vol'  # safe default

    def _no_signal(self, reason: str) -> Dict[str, Any]:
        """Return a no-signal result"""
        return {
            "signal": "NO_TRADE",
            "entry_price": 0.0,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "atr": 0.0,
            "swing_high": 0.0,
            "swing_low": 0.0,
            "sma_m15": 0.0,
            "sma_h4": 0.0,
            "m15_trend": "NONE",
            "h4_trend": "NONE",
            "trend_aligned": False,
            "rsi": 0.0,
            "macd": {"macd": 0.0, "signal": 0.0, "histogram": 0.0},
            "bollinger_bands": {"upper": 0.0, "middle": 0.0, "lower": 0.0},
            "reason": reason,
            "confidence": 0,
            "timestamp": datetime.now(timezone.utc),
            "risk_amount": 0.0,
            "session": "UNKNOWN"
        }