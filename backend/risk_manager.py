import logging
from typing import Dict, Optional, Any
from config import (
    RISK_PER_TRADE,
    MIN_REWARD_RATIO,
    MAX_CONCURRENT_POSITIONS,
    ACCOUNT_BALANCE,
    ATR_MULTIPLIER
)
from backend.db import TradingDatabase

logger = logging.getLogger(__name__)


class RiskManager:
    """Risk management for position sizing, stop loss, and reward calculations."""

    def __init__(self, db: TradingDatabase, account_balance: float = ACCOUNT_BALANCE):
        self.db = db
        self.account_balance = account_balance
        self.risk_per_trade = RISK_PER_TRADE
        self.min_reward_ratio = MIN_REWARD_RATIO
        self.max_concurrent_positions = MAX_CONCURRENT_POSITIONS

    def can_open_position(self) -> bool:
        """Check if we can open a new position (max concurrent positions limit)."""
        open_trades = self.db.get_open_trades()
        if len(open_trades) >= self.max_concurrent_positions:
            logger.warning(f"Max concurrent positions reached ({self.max_concurrent_positions})")
            return False
        return True

    def calculate_position_size(self, entry_price: float, stop_loss: float) -> Dict[str, Any]:
        """Calculate position size based on risk per trade.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            
        Returns:
            {
                "position_size": float,
                "risk_amount": float,
                "reward_at_target": float,
                "reasons": [...]
            }
        """
        try:
            if entry_price == 0 or entry_price == stop_loss:
                logger.error("Invalid entry or stop loss price")
                return {
                    "position_size": 0,
                    "risk_amount": 0,
                    "reward_at_target": 0,
                    "reasons": ["Invalid price inputs"]
                }

            # Calculate risk amount
            risk_amount = self.account_balance * self.risk_per_trade
            
            # Calculate pips at risk
            pips_at_risk = abs(entry_price - stop_loss)

            # Calculate position size (in units)
            # position_size = risk_amount / pips_at_risk
            position_size = risk_amount / pips_at_risk if pips_at_risk > 0 else 0

            reasons = [
                f"Account balance: {self.account_balance:.2f}",
                f"Risk per trade: {self.risk_per_trade*100:.1f}% = {risk_amount:.2f}",
                f"Entry: {entry_price:.5f}, Stop: {stop_loss:.5f} ({pips_at_risk:.5f} risk)",
                f"Position size: {position_size:.4f} units"
            ]

            return {
                "position_size": position_size,
                "risk_amount": risk_amount,
                "pips_at_risk": pips_at_risk,
                "reasons": reasons
            }

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {
                "position_size": 0,
                "risk_amount": 0,
                "reasons": [f"Calculation error: {str(e)}"]
            }

    def calculate_take_profit(self, entry_price: float, stop_loss: float,
                             reward_ratio: Optional[float] = None) -> Dict[str, Any]:
        """Calculate take profit level based on reward/risk ratio.
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            reward_ratio: Risk/reward ratio (default: MIN_REWARD_RATIO)
            
        Returns:
            {
                "take_profit": float,
                "reward_amount": float,
                "reward_ratio": float,
                "reasons": [...]
            }
        """
        try:
            if reward_ratio is None:
                reward_ratio = self.min_reward_ratio

            # Calculate risk amount
            risk_amount = abs(entry_price - stop_loss)

            # Calculate reward amount
            reward_amount = risk_amount * reward_ratio

            # Calculate take profit price
            if entry_price > stop_loss:
                # LONG: take profit above entry
                take_profit = entry_price + reward_amount
            else:
                # SHORT: take profit below entry
                take_profit = entry_price - reward_amount

            reasons = [
                f"Risk/Reward ratio: 1:{reward_ratio:.1f}",
                f"Risk amount: {risk_amount:.5f}",
                f"Target profit: {reward_amount:.5f}",
                f"Take profit price: {take_profit:.5f}"
            ]

            return {
                "take_profit": take_profit,
                "reward_amount": reward_amount,
                "reward_ratio": reward_ratio,
                "reasons": reasons
            }

        except Exception as e:
            logger.error(f"Error calculating take profit: {e}")
            return {
                "take_profit": 0,
                "reward_amount": 0,
                "reasons": [f"Calculation error: {str(e)}"]
            }

    def validate_setup(self, entry_price: float, stop_loss: float, take_profit: float,
                      min_reward_ratio: Optional[float] = None) -> Dict[str, Any]:
        """Validate if a trade setup meets risk management criteria.
        
        Returns:
            {
                "valid": bool,
                "reward_ratio": float,
                "reasons": [...]
            }
        """
        try:
            if min_reward_ratio is None:
                min_reward_ratio = self.min_reward_ratio

            # Calculate risk and reward
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)

            if risk == 0:
                return {
                    "valid": False,
                    "reward_ratio": 0,
                    "reasons": ["Stop loss equals entry price (invalid setup)"]
                }

            reward_ratio = reward / risk

            reasons = []
            valid = True

            # Check if can open position
            if not self.can_open_position():
                valid = False
                reasons.append(f"Max concurrent positions reached ({self.max_concurrent_positions})")

            # Check reward/risk ratio
            if reward_ratio < min_reward_ratio:
                valid = False
                reasons.append(f"Reward/Risk ratio {reward_ratio:.1f}:1 below minimum {min_reward_ratio:.1f}:1")
            else:
                reasons.append(f"Reward/Risk ratio {reward_ratio:.1f}:1 meets minimum {min_reward_ratio:.1f}:1")

            # Check position size sanity
            position_sizing = self.calculate_position_size(entry_price, stop_loss)
            if position_sizing["position_size"] <= 0:
                valid = False
                reasons.append("Invalid position size calculation")

            return {
                "valid": valid,
                "reward_ratio": reward_ratio,
                "reasons": reasons
            }

        except Exception as e:
            logger.error(f"Error validating setup: {e}")
            return {
                "valid": False,
                "reward_ratio": 0,
                "reasons": [f"Validation error: {str(e)}"]
            }

    def calculate_atr_stop_loss(self, price: float, atr: Optional[float], direction: str = "LONG",
                               multiplier: float = ATR_MULTIPLIER) -> float:
        """Calculate stop loss based on ATR.
        
        Args:
            price: Entry price
            atr: Average True Range
            direction: LONG or SHORT
            multiplier: ATR multiplier (default: 2.0)
            
        Returns:
            Stop loss price
        """
        if atr is None or atr == 0:
            logger.warning("Invalid ATR, using fixed stop loss")
            return price * 0.98 if direction == "LONG" else price * 1.02

        atr_stop = atr * multiplier

        if direction == "LONG":
            # Long: stop loss below entry
            return price - atr_stop
        else:
            # Short: stop loss above entry
            return price + atr_stop

    def update_account_balance(self, pnl: float):
        """Update account balance after a trade closes."""
        self.account_balance += pnl
        logger.info(f"Account balance updated: {self.account_balance:.2f}")
