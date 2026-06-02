import pandas as pd
import numpy as np
import logging
from typing import Dict, Optional, Tuple
from config import SR_LOOKBACK_CANDLES, TREND_SMA_FAST, TREND_SMA_SLOW, ATR_PERIOD

logger = logging.getLogger(__name__)


class TradingStrategy:
    """Support/Resistance and trend analysis."""

    @staticmethod
    def calculate_support_resistance(df: pd.DataFrame, lookback: int = SR_LOOKBACK_CANDLES) -> Dict[str, float]:
        """Calculate support and resistance levels.
        
        Resistance = highest high of last N candles (excluding current)
        Support = lowest low of last N candles (excluding current)
        """
        if len(df) < lookback + 1:
            lookback = max(len(df) - 1, 1)

        # Exclude current candle (last row)
        lookback_data = df.iloc[:-1].tail(lookback)

        resistance = lookback_data['high'].max()
        support = lookback_data['low'].min()

        return {
            "resistance": resistance,
            "support": support,
            "midpoint": (resistance + support) / 2
        }

    @staticmethod
    def detect_trend(df: pd.DataFrame, sma_fast: int = TREND_SMA_FAST,
                     sma_slow: int = TREND_SMA_SLOW) -> Dict[str, any]:
        """Detect trend using SMA crossover.
        
        Bullish: Price > SMA50 > SMA200
        Bearish: Price < SMA50 < SMA200
        Neutral: Price oscillates around SMAs
        """
        if len(df) < sma_slow:
            return {"trend": "neutral", "confidence": 0, "reasons": ["Insufficient data"]}

        df = df.copy()
        df['sma_fast'] = df['close'].rolling(window=sma_fast).mean()
        df['sma_slow'] = df['close'].rolling(window=sma_slow).mean()

        current_close = df['close'].iloc[-1]
        current_sma_fast = df['sma_fast'].iloc[-1]
        current_sma_slow = df['sma_slow'].iloc[-1]

        # Get last 5 closes to assess consistency
        recent_closes = df['close'].tail(5).values
        recent_sma_fast = df['sma_fast'].tail(5).values

        reasons = []
        trend_score = 0

        # Bullish signals
        if current_close > current_sma_fast:
            trend_score += 25
            reasons.append(f"Price ({current_close:.5f}) > SMA50 ({current_sma_fast:.5f})")

        if current_sma_fast > current_sma_slow:
            trend_score += 25
            reasons.append(f"SMA50 ({current_sma_fast:.5f}) > SMA200 ({current_sma_slow:.5f})")

        # Count bullish candles
        bullish_candles = sum(1 for c in recent_closes if c > current_sma_fast)
        if bullish_candles >= 4:
            trend_score += 25
            reasons.append(f"{bullish_candles}/5 recent candles above SMA50")

        # Bearish signals (opposite)
        if current_close < current_sma_fast:
            trend_score -= 25
            reasons.append(f"Price ({current_close:.5f}) < SMA50 ({current_sma_fast:.5f})")

        if current_sma_fast < current_sma_slow:
            trend_score -= 25
            reasons.append(f"SMA50 ({current_sma_fast:.5f}) < SMA200 ({current_sma_slow:.5f})")

        bearish_candles = sum(1 for c in recent_closes if c < current_sma_fast)
        if bearish_candles >= 4:
            trend_score -= 25
            reasons.append(f"{bearish_candles}/5 recent candles below SMA50")

        # Determine trend
        if trend_score >= 50:
            trend = "bullish"
        elif trend_score <= -50:
            trend = "bearish"
        else:
            trend = "neutral"

        confidence = min(abs(trend_score), 100)

        return {
            "trend": trend,
            "confidence": confidence,
            "score": trend_score,
            "reasons": reasons,
            "price": current_close,
            "sma_fast": current_sma_fast,
            "sma_slow": current_sma_slow
        }

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> Optional[float]:
        """Calculate Average True Range (ATR)."""
        if len(df) < period:
            return None

        df = df.copy()

        # Calculate True Range
        df['tr'] = np.where(
            df['high'] - df['low'] > abs(df['close'].shift(1) - df['high']),
            df['high'] - df['low'],
            np.where(
                abs(df['close'].shift(1) - df['low']) > abs(df['close'].shift(1) - df['high']),
                abs(df['close'].shift(1) - df['low']),
                abs(df['close'].shift(1) - df['high'])
            )
        )

        # Calculate ATR
        atr = df['tr'].rolling(window=period).mean()
        return atr.iloc[-1]

    @staticmethod
    def detect_breakout(df: pd.DataFrame, sr_levels: Dict[str, float],
                        direction: str = "up") -> Dict[str, any]:
        """Detect if price is breaking out of support/resistance.
        
        Args:
            df: OHLCV DataFrame
            sr_levels: Dict with support/resistance levels
            direction: 'up' for breakout above resistance, 'down' for below support
        """
        if len(df) < 2:
            return {"breakout": False, "confidence": 0, "reasons": []}

        current_close = df['close'].iloc[-1]
        previous_close = df['close'].iloc[-2]
        resistance = sr_levels.get('resistance', float('inf'))
        support = sr_levels.get('support', 0)

        reasons = []
        confidence = 0

        if direction == "up":
            # Breakout above resistance
            if current_close > resistance and previous_close <= resistance:
                breakout = True
                confidence = 75
                reasons.append(f"Price closed above resistance: {current_close:.5f} > {resistance:.5f}")
            elif current_close > resistance:
                breakout = True
                confidence = 50
                reasons.append(f"Price above resistance (may be retesting): {current_close:.5f} > {resistance:.5f}")
            else:
                breakout = False
                reasons.append("No breakout above resistance")

        else:  # down
            # Breakout below support
            if current_close < support and previous_close >= support:
                breakout = True
                confidence = 75
                reasons.append(f"Price closed below support: {current_close:.5f} < {support:.5f}")
            elif current_close < support:
                breakout = True
                confidence = 50
                reasons.append(f"Price below support (may be retesting): {current_close:.5f} < {support:.5f}")
            else:
                breakout = False
                reasons.append("No breakout below support")

        return {
            "breakout": breakout,
            "confidence": confidence,
            "reasons": reasons,
            "current_price": current_close,
            "level": resistance if direction == "up" else support
        }

    @staticmethod
    def detect_pullback(df: pd.DataFrame, sr_levels: Dict[str, float],
                        trend: str = "bullish") -> Dict[str, any]:
        """Detect if price is pulling back to support/resistance in trending market.
        
        Args:
            df: OHLCV DataFrame
            sr_levels: Dict with support/resistance levels
            trend: 'bullish' (pullback to support) or 'bearish' (pullback to resistance)
        """
        if len(df) < 2:
            return {"pullback": False, "confidence": 0, "reasons": []}

        current_close = df['close'].iloc[-1]
        current_low = df['low'].iloc[-1]
        current_high = df['high'].iloc[-1]
        resistance = sr_levels.get('resistance', float('inf'))
        support = sr_levels.get('support', 0)

        reasons = []
        pullback = False
        confidence = 0

        if trend == "bullish":
            # Pullback in bullish trend: price touches support, shows rejection upward
            distance_to_support = current_low - support
            if distance_to_support < (resistance - support) * 0.1:  # Within 10% of support
                pullback = True
                confidence = 60
                reasons.append(f"Price near support: {current_low:.5f} vs {support:.5f}")

                # Check for rejection (close higher than open = bullish candle)
                if current_close > current_low and current_close > (current_low + current_high) / 2:
                    confidence = 80
                    reasons.append("Bullish rejection candle at support")

        else:  # bearish
            # Pullback in bearish trend: price touches resistance, shows rejection downward
            distance_to_resistance = resistance - current_high
            if distance_to_resistance < (resistance - support) * 0.1:  # Within 10% of resistance
                pullback = True
                confidence = 60
                reasons.append(f"Price near resistance: {current_high:.5f} vs {resistance:.5f}")

                # Check for rejection (close lower than open = bearish candle)
                if current_close < current_high and current_close < (current_low + current_high) / 2:
                    confidence = 80
                    reasons.append("Bearish rejection candle at resistance")

        return {
            "pullback": pullback,
            "confidence": confidence,
            "reasons": reasons,
            "current_price": current_close
        }

    @staticmethod
    def analyze_volume(df: pd.DataFrame) -> Dict[str, any]:
        """Analyze volume confirmation."""
        if len(df) < 20:
            return {"volume_confirmed": False, "confidence": 0, "reasons": []}

        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].tail(20).mean()

        reasons = []
        confidence = 0
        volume_confirmed = False

        if current_volume > avg_volume:
            volume_confirmed = True
            ratio = current_volume / avg_volume
            confidence = min(ratio * 50, 100)
            reasons.append(f"Volume above average: {current_volume:.0f} vs {avg_volume:.0f} ({ratio:.2f}x)")
        else:
            reasons.append(f"Volume below average: {current_volume:.0f} vs {avg_volume:.0f}")

        return {
            "volume_confirmed": volume_confirmed,
            "confidence": confidence,
            "current_volume": current_volume,
            "avg_volume": avg_volume,
            "reasons": reasons
        }
