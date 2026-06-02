import logging
from typing import Dict, Optional, Any
from backend.db import TradingDatabase

logger = logging.getLogger(__name__)


class MemoryAgent:
    """Historical trade analysis and pattern recognition agent."""

    def __init__(self, db: TradingDatabase):
        self.name = "memory"
        self.db = db

    def analyze(self, symbol: str, trade_type: str) -> Dict[str, Any]:
        """Analyze historical performance for a symbol and trade type.
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            trade_type: 'LONG' or 'SHORT'
            
        Returns:
            {
                "best_setup_winrate": float (0-1),
                "current_setup_probability": float (0-1),
                "confidence": 0-100,
                "reasons": [...]
            }
        """
        try:
            # Get all closed trades for this symbol and type
            winrate_stats = self.db.get_best_setup_winrate(symbol, trade_type)

            # Get overall symbol statistics
            overall_stats = self.db.get_win_rate(symbol)

            # Get overall stats across all trades
            global_stats = self.db.get_win_rate()

            # Calculate probability and confidence
            setup_winrate = winrate_stats.get("win_rate", 0)
            setup_trades = winrate_stats.get("total", 0)

            # Confidence based on sample size
            if setup_trades >= 20:
                confidence = 90
                sample_quality = "excellent"
            elif setup_trades >= 10:
                confidence = 70
                sample_quality = "good"
            elif setup_trades >= 5:
                confidence = 50
                sample_quality = "fair"
            elif setup_trades > 0:
                confidence = 30
                sample_quality = "limited"
            else:
                confidence = 0
                sample_quality = "insufficient"

            reasons = self._generate_insights(
                symbol,
                trade_type,
                setup_winrate,
                setup_trades,
                overall_stats,
                global_stats,
                sample_quality
            )

            return {
                "best_setup_winrate": setup_winrate,
                "current_setup_probability": setup_winrate,  # Can be adjusted by other factors
                "trades_analyzed": setup_trades,
                "confidence": confidence,
                "reasons": reasons,
                "setup_quality": sample_quality,
                "overall_winrate": overall_stats.get("win_rate", 0),
                "global_winrate": global_stats.get("win_rate", 0),
                "agent": self.name
            }

        except Exception as e:
            logger.error(f"Error in MemoryAgent.analyze: {e}")
            return {
                "best_setup_winrate": 0.5,  # Default neutral probability
                "current_setup_probability": 0.5,
                "trades_analyzed": 0,
                "confidence": 0,
                "reasons": [f"Analysis error: {str(e)}"],
                "agent": self.name
            }

    def _generate_insights(self, symbol: str, trade_type: str, setup_winrate: float,
                           setup_trades: int, overall_stats: Dict, global_stats: Dict,
                           sample_quality: str) -> list:
        """Generate reasoning and insights from historical data."""
        insights = []

        # Sample size feedback
        if setup_trades == 0:
            insights.append(f"No historical trades for {symbol} {trade_type} - using neutral probability")
            return insights

        if sample_quality == "limited":
            insights.append(f"Only {setup_trades} trades for this setup (small sample size - caution advised)")
        else:
            insights.append(f"Historical sample: {setup_trades} {trade_type} trades for {symbol}")

        # Winrate interpretation
        if setup_winrate >= 0.65:
            insights.append(f"Excellent track record: {setup_winrate*100:.1f}% win rate for this setup")
        elif setup_winrate >= 0.55:
            insights.append(f"Good track record: {setup_winrate*100:.1f}% win rate (above 50%)")
        elif setup_winrate >= 0.45:
            insights.append(f"Fair track record: {setup_winrate*100:.1f}% win rate (near breakeven)")
        else:
            insights.append(f"Poor track record: {setup_winrate*100:.1f}% win rate (below 50% - consider skipping)")

        # Comparison to overall symbol performance
        overall_wr = overall_stats.get("win_rate", 0)
        if overall_wr > 0:
            if setup_winrate > overall_wr:
                diff = (setup_winrate - overall_wr) * 100
                insights.append(f"This setup outperforms {symbol} overall by {diff:.1f}%")
            elif setup_winrate < overall_wr:
                diff = (overall_wr - setup_winrate) * 100
                insights.append(f"This setup underperforms {symbol} overall by {diff:.1f}%")

        # Comparison to global performance
        global_wr = global_stats.get("win_rate", 0)
        if global_wr > 0 and setup_winrate > global_wr:
            diff = (setup_winrate - global_wr) * 100
            insights.append(f"This setup beats overall system average by {diff:.1f}%")

        # Risk/reward from historical trades
        if setup_trades > 0:
            avg_pnl = overall_stats.get("avg_pnl", 0)
            total_pnl = overall_stats.get("total_pnl", 0)
            if avg_pnl > 0:
                insights.append(f"Average profit per {trade_type} trade: +{avg_pnl:.2f}")
            elif avg_pnl < 0:
                insights.append(f"Average loss per {trade_type} trade: {avg_pnl:.2f}")

        return insights

    def get_probability_adjustment(self, symbol: str, trade_type: str) -> float:
        """Get a probability adjustment factor based on historical performance.
        
        Returns a multiplier (0.5 to 1.5) to adjust decision engine confidence.
        """
        try:
            winrate_stats = self.db.get_best_setup_winrate(symbol, trade_type)
            setup_winrate = winrate_stats.get("win_rate", 0.5)

            # Adjust confidence based on historical winrate
            # 60% historical winrate = 1.2x multiplier
            # 50% historical winrate = 1.0x multiplier (neutral)
            # 40% historical winrate = 0.8x multiplier
            adjustment = 0.5 + (setup_winrate)

            return min(adjustment, 1.5)  # Cap at 1.5x

        except Exception as e:
            logger.error(f"Error calculating probability adjustment: {e}")
            return 1.0  # Neutral if error

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics across all trades."""
        try:
            stats = self.db.get_win_rate()
            return {
                "total_trades": stats.get("total_trades", 0),
                "total_wins": stats.get("wins", 0),
                "total_losses": stats.get("losses", 0),
                "win_rate": stats.get("win_rate", 0),
                "avg_pnl": stats.get("avg_pnl", 0),
                "total_pnl": stats.get("total_pnl", 0)
            }
        except Exception as e:
            logger.error(f"Error getting summary stats: {e}")
            return {}
