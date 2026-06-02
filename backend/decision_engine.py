import logging
from typing import Dict, Any, Tuple
from config import (
    CHART_AGENT_WEIGHT,
    NEWS_AGENT_WEIGHT,
    MEMORY_AGENT_WEIGHT,
    STRONG_SIGNAL_THRESHOLD,
    WEAK_SIGNAL_THRESHOLD,
    AVOID_SIGNAL_THRESHOLD
)

logger = logging.getLogger(__name__)


class DecisionEngine:
    """Decision engine that combines agent outputs and makes final trading decision."""

    def __init__(self):
        self.name = "decision_engine"

    def make_decision(self, chart_output: Dict[str, Any], news_output: Dict[str, Any],
                     memory_output: Dict[str, Any]) -> Dict[str, Any]:
        """Make final trading decision based on agent outputs.
        
        Args:
            chart_output: Output from ChartAgent
            news_output: Output from NewsAgent
            memory_output: Output from MemoryAgent
            
        Returns:
            {
                "decision": "EXECUTE | WAIT | REJECT | BLOCKED",
                "final_score": 0-100,
                "chart_score": 0-100,
                "news_score": 0-100,
                "memory_score": 0-100,
                "direction": "LONG | SHORT | NONE",
                "reasons": [...]
            }
        """
        try:
            # Normalize agent outputs to 0-100 scores
            chart_score = self._normalize_agent_output(chart_output)
            news_score = self._normalize_agent_output(news_output)
            memory_score = self._normalize_agent_output(memory_output)

            # Log individual scores
            logger.info(f"Agent scores - Chart: {chart_score:.1f}, News: {news_score:.1f}, Memory: {memory_score:.1f}")

            # Calculate weighted final score
            final_score = (
                (chart_score * CHART_AGENT_WEIGHT) +
                (news_score * NEWS_AGENT_WEIGHT) +
                (memory_score * MEMORY_AGENT_WEIGHT)
            )

            # Determine decision
            decision, decision_reason = self._determine_decision(final_score)

            # Determine trade direction
            direction = self._determine_direction(chart_output)

            # Build reasoning
            reasoning = self._build_reasoning(
                chart_score, news_score, memory_score, final_score,
                decision, direction, chart_output, news_output, memory_output
            )

            return {
                "decision": decision,
                "final_score": final_score,
                "chart_score": chart_score,
                "news_score": news_score,
                "memory_score": memory_score,
                "direction": direction,
                "reasons": reasoning,
                "engine": self.name
            }

        except Exception as e:
            logger.error(f"Error in DecisionEngine.make_decision: {e}")
            return {
                "decision": "BLOCKED",
                "final_score": 0,
                "chart_score": 0,
                "news_score": 0,
                "memory_score": 0,
                "direction": "NONE",
                "reasons": [f"Decision engine error: {str(e)}"],
                "engine": self.name
            }

    def _normalize_agent_output(self, agent_output: Dict[str, Any]) -> float:
        """Normalize agent output to 0-100 score."""
        try:
            # If agent already provides a confidence score, use that
            if "confidence" in agent_output:
                return float(agent_output["confidence"])

            # For chart agent, use confidence if available
            if agent_output.get("agent") == "chart":
                return float(agent_output.get("confidence", 50))

            # For news agent, convert sentiment score (-1 to +1) to 0-100
            if agent_output.get("agent") == "news":
                sentiment_score = agent_output.get("score", 0)
                # -1 = 0, 0 = 50, +1 = 100
                return 50 + (sentiment_score * 50)

            # For memory agent, convert winrate to 0-100
            if agent_output.get("agent") == "memory":
                winrate = agent_output.get("best_setup_winrate", 0.5)
                confidence = agent_output.get("confidence", 0)
                # Winrate becomes 0-100, modulated by confidence in the sample
                return (winrate * 100) * (confidence / 100) if confidence > 0 else 50

            # Default neutral
            return 50

        except Exception as e:
            logger.warning(f"Error normalizing agent output: {e}")
            return 50

    def _determine_decision(self, final_score: float) -> Tuple[str, str]:
        """Determine action based on final score."""
        if final_score >= STRONG_SIGNAL_THRESHOLD:
            return "EXECUTE", f"Strong signal ({final_score:.0f})"
        elif final_score >= WEAK_SIGNAL_THRESHOLD:
            return "WAIT", f"Weak signal ({final_score:.0f}) - wait for stronger confirmation"
        elif final_score >= AVOID_SIGNAL_THRESHOLD:
            return "REJECT", f"Conflicting signals ({final_score:.0f}) - avoid trade"
        else:
            return "BLOCKED", f"Poor market conditions ({final_score:.0f}) - no trade"

    def _determine_direction(self, chart_output: Dict[str, Any]) -> str:
        """Determine trade direction from chart analysis."""
        try:
            # Check breakout direction
            if chart_output.get("breakout", {}).get("detected", False):
                return chart_output["breakout"].get("direction", "NONE")

            # Check pullback direction
            if chart_output.get("pullback", {}).get("detected", False):
                return chart_output["pullback"].get("direction", "NONE")

            # Check overall bias
            bias = chart_output.get("bias", "neutral")
            if bias == "bullish":
                return "LONG"
            elif bias == "bearish":
                return "SHORT"

            return "NONE"

        except Exception as e:
            logger.warning(f"Error determining direction: {e}")
            return "NONE"

    def _build_reasoning(self, chart_score: float, news_score: float, memory_score: float,
                        final_score: float, decision: str, direction: str,
                        chart_output: Dict, news_output: Dict, memory_output: Dict) -> list:
        """Build comprehensive reasoning for the decision."""
        reasons = []

        # Score breakdown
        reasons.append(f"Score breakdown: Chart {chart_score:.0f} + News {news_score:.0f} + Memory {memory_score:.0f} = {final_score:.0f}")

        # Weights explanation
        reasons.append(f"Weights: Chart {CHART_AGENT_WEIGHT*100:.0f}%, News {NEWS_AGENT_WEIGHT*100:.0f}%, Memory {MEMORY_AGENT_WEIGHT*100:.0f}%")

        # Chart insights
        if chart_output.get("reasons"):
            reasons.append(f"Chart: {chart_output['reasons'][0]}")

        # News insights
        if news_output.get("reasons"):
            reasons.append(f"News ({news_output.get('articles_analyzed', 0)} articles): {news_output['reasons'][0]}")
        else:
            reasons.append("News: Neutral sentiment (no recent articles)")

        # Memory insights
        if memory_output.get("reasons"):
            memory_reason = memory_output['reasons'][0]
            # Simplify if too long
            if len(memory_reason) > 100:
                memory_reason = memory_reason[:100] + "..."
            reasons.append(f"Memory: {memory_reason}")

        # Decision reasoning
        reasons.append(f"Decision: {decision}")

        if direction != "NONE":
            reasons.append(f"Direction: {direction}")

        return reasons
