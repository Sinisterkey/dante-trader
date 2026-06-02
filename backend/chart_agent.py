import logging
import pandas as pd
from typing import Dict, Optional, Any
from backend.strategy import TradingStrategy
from backend.multi_timeframe import MultiTimeframeAnalyzer

logger = logging.getLogger(__name__)


class ChartAgent:
    """Technical analysis agent for chart pattern recognition."""

    def __init__(self):
        self.name = "chart"

    def analyze(self, timeframe_data: Dict[str, pd.DataFrame], symbol: str) -> Dict[str, Any]:
        """Comprehensive chart analysis using multi-timeframe data.
        
        Returns:
            {
                "bias": "bullish | bearish | neutral",
                "confidence": 0-100,
                "reasons": [...],
                "breakout": {...},
                "pullback": {...},
                "multi_timeframe": {...}
            }
        """
        try:
            # Analyze each timeframe
            multi_tf_analysis = MultiTimeframeAnalyzer.analyze_all_timeframes(timeframe_data)

            # Determine overall bias
            bias_analysis = MultiTimeframeAnalyzer.determine_overall_bias(multi_tf_analysis)

            # Check timeframe alignment
            alignment = MultiTimeframeAnalyzer.check_alignment(multi_tf_analysis)

            # Use 5M for breakout detection
            breakout_analysis = self._detect_breakout_opportunity(timeframe_data)

            # Use 5M for pullback detection
            pullback_analysis = self._detect_pullback_opportunity(timeframe_data)

            # Volume confirmation
            volume_analysis = self._check_volume_confirmation(timeframe_data)

            # Compile final analysis
            overall_confidence = self._calculate_overall_confidence(
                bias_analysis,
                alignment,
                breakout_analysis,
                pullback_analysis,
                volume_analysis
            )

            reasons = []
            reasons.extend(bias_analysis.get("reasoning", []))
            reasons.append(alignment.get("reasoning", ""))

            if breakout_analysis.get("detected"):
                reasons.append(f"Breakout detected: {breakout_analysis['reason']}")

            if pullback_analysis.get("detected"):
                reasons.append(f"Pullback detected: {pullback_analysis['reason']}")

            if volume_analysis.get("confirmed"):
                reasons.append(f"Volume confirmed: {volume_analysis['reason']}")

            return {
                "bias": bias_analysis["bias"],
                "confidence": overall_confidence,
                "reasons": [r for r in reasons if r],
                "breakout": breakout_analysis,
                "pullback": pullback_analysis,
                "volume": volume_analysis,
                "multi_timeframe": multi_tf_analysis,
                "alignment": alignment,
                "agent": self.name
            }

        except Exception as e:
            logger.error(f"Error in ChartAgent.analyze: {e}")
            return {
                "bias": "neutral",
                "confidence": 0,
                "reasons": [f"Analysis error: {str(e)}"],
                "agent": self.name
            }

    def _detect_breakout_opportunity(self, timeframe_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Detect breakout opportunities in 5M chart."""
        if "M5" not in timeframe_data or timeframe_data["M5"] is None:
            return {"detected": False, "direction": None, "reason": "No 5M data"}

        df = timeframe_data["M5"]
        sr_levels = TradingStrategy.calculate_support_resistance(df)

        # Check for breakout above resistance
        breakout_up = TradingStrategy.detect_breakout(df, sr_levels, direction="up")
        breakout_down = TradingStrategy.detect_breakout(df, sr_levels, direction="down")

        if breakout_up["breakout"]:
            return {
                "detected": True,
                "direction": "LONG",
                "confidence": breakout_up["confidence"],
                "reason": "Breakout above resistance",
                "level": sr_levels["resistance"],
                "details": breakout_up["reasons"]
            }

        elif breakout_down["breakout"]:
            return {
                "detected": True,
                "direction": "SHORT",
                "confidence": breakout_down["confidence"],
                "reason": "Breakout below support",
                "level": sr_levels["support"],
                "details": breakout_down["reasons"]
            }

        else:
            return {
                "detected": False,
                "direction": None,
                "confidence": 0,
                "reason": "No breakout detected"
            }

    def _detect_pullback_opportunity(self, timeframe_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Detect pullback opportunities in 5M chart."""
        if "M5" not in timeframe_data or timeframe_data["M5"] is None:
            return {"detected": False, "direction": None, "reason": "No 5M data"}

        if "M30" not in timeframe_data or timeframe_data["M30"] is None:
            return {"detected": False, "direction": None, "reason": "No 30M data for structure"}

        df_5m = timeframe_data["M5"]
        df_30m = timeframe_data["M30"]

        # Get 30M trend (structure)
        trend_30m = TradingStrategy.detect_trend(df_30m)
        sr_levels_5m = TradingStrategy.calculate_support_resistance(df_5m)

        # Bullish pullback: 30M is bullish, 5M pulls back to support
        if trend_30m["trend"] == "bullish":
            pullback = TradingStrategy.detect_pullback(df_5m, sr_levels_5m, trend="bullish")
            if pullback["pullback"]:
                return {
                    "detected": True,
                    "direction": "LONG",
                    "confidence": pullback["confidence"],
                    "reason": "Bullish pullback at support (30M trend bullish)",
                    "level": sr_levels_5m["support"],
                    "details": pullback["reasons"]
                }

        # Bearish pullback: 30M is bearish, 5M pulls back to resistance
        elif trend_30m["trend"] == "bearish":
            pullback = TradingStrategy.detect_pullback(df_5m, sr_levels_5m, trend="bearish")
            if pullback["pullback"]:
                return {
                    "detected": True,
                    "direction": "SHORT",
                    "confidence": pullback["confidence"],
                    "reason": "Bearish pullback at resistance (30M trend bearish)",
                    "level": sr_levels_5m["resistance"],
                    "details": pullback["reasons"]
                }

        return {
            "detected": False,
            "direction": None,
            "confidence": 0,
            "reason": "No pullback opportunity detected"
        }

    def _check_volume_confirmation(self, timeframe_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """Check volume confirmation on 5M."""
        if "M5" not in timeframe_data or timeframe_data["M5"] is None:
            return {"confirmed": False, "reason": "No 5M data"}

        df = timeframe_data["M5"]
        volume_analysis = TradingStrategy.analyze_volume(df)

        return {
            "confirmed": volume_analysis["volume_confirmed"],
            "confidence": volume_analysis["confidence"],
            "reason": volume_analysis["reasons"][0] if volume_analysis["reasons"] else "Unknown volume status",
            "current_volume": volume_analysis.get("current_volume"),
            "avg_volume": volume_analysis.get("avg_volume")
        }

    def _calculate_overall_confidence(self, bias_analysis: Dict, alignment: Dict,
                                     breakout: Dict, pullback: Dict, volume: Dict) -> int:
        """Calculate overall confidence score (0-100)."""
        confidence_score = 0

        # Bias confidence (0-30)
        confidence_score += bias_analysis.get("confidence", 0) * 0.3

        # Alignment bonus (0-20)
        if alignment.get("aligned", False):
            confidence_score += 20

        # Setup detection (breakout or pullback) (0-30)
        if breakout.get("detected", False):
            confidence_score += breakout.get("confidence", 0) * 0.3
        elif pullback.get("detected", False):
            confidence_score += pullback.get("confidence", 0) * 0.3

        # Volume confirmation bonus (0-20)
        if volume.get("confirmed", False):
            confidence_score += volume.get("confidence", 0) * 0.2

        return min(int(confidence_score), 100)
