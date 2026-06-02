import logging
from typing import Dict, List, Optional
import pandas as pd
from backend.strategy import TradingStrategy

logger = logging.getLogger(__name__)


class MultiTimeframeAnalyzer:
    """Combine multi-timeframe analysis for decision making."""

    @staticmethod
    def analyze_all_timeframes(timeframe_data: Dict[str, pd.DataFrame]) -> Dict[str, any]:
        """Analyze all timeframes together.
        
        Returns comprehensive multi-timeframe analysis including:
        - 5M: Entry timing
        - 15M: Confirmation
        - 30M: Structure
        - 4H: Trend bias
        """
        analysis = {}
        timeframe_order = ["M5", "M15", "M30", "H4"]

        for tf in timeframe_order:
            if tf not in timeframe_data:
                logger.warning(f"Missing timeframe data: {tf}")
                continue

            df = timeframe_data[tf]
            if df is None or len(df) == 0:
                continue

            sr_levels = TradingStrategy.calculate_support_resistance(df)
            trend_analysis = TradingStrategy.detect_trend(df)
            atr = TradingStrategy.calculate_atr(df)

            analysis[tf] = {
                "support": sr_levels["support"],
                "resistance": sr_levels["resistance"],
                "trend": trend_analysis["trend"],
                "trend_confidence": trend_analysis["confidence"],
                "trend_reasons": trend_analysis["reasons"],
                "atr": atr,
                "price": df['close'].iloc[-1]
            }

        return analysis

    @staticmethod
    def determine_overall_bias(multi_tf_analysis: Dict[str, Dict]) -> Dict[str, any]:
        """Determine overall market bias from multi-timeframe analysis.
        
        - 4H sets the overall trend bias (highest priority)
        - 30M confirms structure
        - 15M provides confirmation
        - 5M determines entry timing
        """
        if not multi_tf_analysis:
            return {"bias": "neutral", "confidence": 0, "reasoning": []}

        bias_score = 0
        reasoning = []

        # 4H (40% weight) - Trend bias
        if "H4" in multi_tf_analysis:
            h4_trend = multi_tf_analysis["H4"]["trend"]
            if h4_trend == "bullish":
                bias_score += 40
                reasoning.append(f"4H: {h4_trend} ({multi_tf_analysis['H4']['trend_confidence']:.0f}% confidence)")
            elif h4_trend == "bearish":
                bias_score -= 40
                reasoning.append(f"4H: {h4_trend} ({multi_tf_analysis['H4']['trend_confidence']:.0f}% confidence)")

        # 30M (30% weight) - Structure
        if "M30" in multi_tf_analysis:
            m30_trend = multi_tf_analysis["M30"]["trend"]
            if m30_trend == "bullish":
                bias_score += 30
                reasoning.append(f"30M: {m30_trend} ({multi_tf_analysis['M30']['trend_confidence']:.0f}% confidence)")
            elif m30_trend == "bearish":
                bias_score -= 30
                reasoning.append(f"30M: {m30_trend} ({multi_tf_analysis['M30']['trend_confidence']:.0f}% confidence)")

        # 15M (20% weight) - Confirmation
        if "M15" in multi_tf_analysis:
            m15_trend = multi_tf_analysis["M15"]["trend"]
            if m15_trend == "bullish":
                bias_score += 20
                reasoning.append(f"15M: {m15_trend} ({multi_tf_analysis['M15']['trend_confidence']:.0f}% confidence)")
            elif m15_trend == "bearish":
                bias_score -= 20
                reasoning.append(f"15M: {m15_trend} ({multi_tf_analysis['M15']['trend_confidence']:.0f}% confidence)")

        # 5M (10% weight) - Entry timing (can be more volatile)
        if "M5" in multi_tf_analysis:
            m5_trend = multi_tf_analysis["M5"]["trend"]
            if m5_trend == "bullish":
                bias_score += 10
                reasoning.append(f"5M: {m5_trend} ({multi_tf_analysis['M5']['trend_confidence']:.0f}% confidence)")
            elif m5_trend == "bearish":
                bias_score -= 10
                reasoning.append(f"5M: {m5_trend} ({multi_tf_analysis['M5']['trend_confidence']:.0f}% confidence)")

        # Determine overall bias
        if bias_score >= 50:
            overall_bias = "bullish"
        elif bias_score <= -50:
            overall_bias = "bearish"
        else:
            overall_bias = "neutral"

        confidence = min(abs(bias_score), 100)

        return {
            "bias": overall_bias,
            "confidence": confidence,
            "score": bias_score,
            "reasoning": reasoning
        }

    @staticmethod
    def check_alignment(multi_tf_analysis: Dict[str, Dict]) -> Dict[str, any]:
        """Check if all timeframes are aligned in the same direction.
        
        High alignment = strong signal
        Low alignment = conflicting signals
        """
        trends = []

        for tf in ["H4", "M30", "M15", "M5"]:
            if tf in multi_tf_analysis:
                trends.append(multi_tf_analysis[tf]["trend"])

        bullish_count = trends.count("bullish")
        bearish_count = trends.count("bearish")
        neutral_count = trends.count("neutral")
        total = len(trends)

        alignment_score = max(bullish_count, bearish_count) / total if total > 0 else 0
        alignment_percent = alignment_score * 100

        return {
            "alignment_percent": alignment_percent,
            "bullish_timeframes": bullish_count,
            "bearish_timeframes": bearish_count,
            "neutral_timeframes": neutral_count,
            "aligned": alignment_percent >= 75,
            "reasoning": f"{max(bullish_count, bearish_count)}/{total} timeframes in agreement"
        }

    @staticmethod
    def get_entry_level(multi_tf_analysis: Dict[str, Dict], direction: str) -> Optional[Dict]:
        """Determine entry level from multi-timeframe analysis.
        
        LONG entry: Use 5M support as entry trigger
        SHORT entry: Use 5M resistance as entry trigger
        """
        if "M5" not in multi_tf_analysis:
            return None

        m5_data = multi_tf_analysis["M5"]

        if direction == "LONG":
            return {
                "entry_level": m5_data["support"],
                "stop_loss": m5_data["support"] - (m5_data["atr"] or 0.0001) * 2,
                "reason": "Entry at 5M support with pullback confirmation"
            }
        elif direction == "SHORT":
            return {
                "entry_level": m5_data["resistance"],
                "stop_loss": m5_data["resistance"] + (m5_data["atr"] or 0.0001) * 2,
                "reason": "Entry at 5M resistance with pullback confirmation"
            }

        return None
