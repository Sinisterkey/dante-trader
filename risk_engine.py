"""
Risk Engine Module
Handles dynamic position sizing and risk management
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from broker_integration import BrokerAPI
from config import *

logger = logging.getLogger(__name__)


class RiskEngine:
    """Manages risk and position sizing for the trading system"""
    
    def __init__(self, broker: BrokerAPI):
        self.broker = broker
        self.logger = logging.getLogger(__name__ + ".RiskEngine")
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.last_reset_date = datetime.now(timezone.utc).date()
        self.peak_equity = 0.0
        self.current_equity = 0.0
        
    def update_account_info(self) -> None:
        """Update account information from broker"""
        try:
            account_info = self.broker.get_account_info()
            if account_info:
                self.current_equity = account_info.get('equity', 0.0)
                # Update peak equity
                if self.current_equity > self.peak_equity:
                    self.peak_equity = self.current_equity
                    
                # Reset daily stats if new day
                today = datetime.now(timezone.utc).date()
                if today != self.last_reset_date:
                    self.daily_pnl = 0.0
                    self.daily_trades = 0
                    self.last_reset_date = today
                    
        except Exception as e:
            self.logger.error(f"Error updating account info: {e}")
    
    def calculate_position_size(self, signal: Dict[str, Any]) -> float:
        """Calculate appropriate position size based on risk parameters and signal"""
        try:
            # Update account info
            self.update_account_info()
            
            # Get signal details
            action = signal.get('action')
            if action == 'NO_TRADE':
                return 0.0
            
            symbol = INSTRUMENT
            entry_price = signal.get('entry_price', 0.0)
            stop_loss = signal.get('stop_loss', 0.0)
            
            if entry_price <= 0 or stop_loss <= 0:
                self.logger.warning(f"Invalid prices: entry={entry_price}, sl={stop_loss}")
                return 0.0
            
            # Get symbol info
            symbol_info = self.broker.get_symbol_info(symbol)
            if not symbol_info:
                self.logger.warning(f"Unable to get symbol info for {symbol}")
                return 0.0
            
            # Calculate risk amount based on equity
            risk_percent = RISK_PER_TRADE / 100.0  # Convert percentage to decimal
            risk_amount = self.current_equity * risk_percent
            
            # Apply daily loss limit
            max_daily_loss = self.current_equity * (MAX_DAILY_LOSS / 100.0)
            if abs(self.daily_pnl) >= max_daily_loss:
                self.logger.warning(f"Daily loss limit reached: {self.daily_pnl:.2f} >= {max_daily_loss:.2f}")
                return 0.0
            
            # Apply drawdown-based reduction
            drawdown_factor = self._calculate_drawdown_factor()
            risk_amount *= drawdown_factor
            
            # Calculate price risk per unit
            price_risk = abs(entry_price - stop_loss)
            if price_risk <= 0:
                self.logger.warning(f"Invalid price risk: {price_risk}")
                return 0.0
            
            # Get contract size and point value
            contract_size = symbol_info.get('trade_contract_size', 100000)
            point_value = symbol_info.get('point', 0.0001)
            
            if contract_size <= 0:
                contract_size = 100000
            if point_value <= 0:
                point_value = 0.0001
            
            # Calculate position size in lots
            # Risk amount = position_size * price_risk / point_value * contract_size
            position_size = (risk_amount * point_value) / (price_risk * contract_size)
            
            # Apply volatility adjustment
            volatility_factor = self._get_volatility_adjustment(symbol)
            position_size *= volatility_factor
            
            # Apply confidence adjustment
            confidence = signal.get('confidence', 50)
            confidence_factor = confidence / 100.0  # 0.5 confidence = 50% size
            position_size *= confidence_factor
            
            # Apply ML confidence adjustment if available
            ml_confidence = signal.get('ml_confidence', 0.0)
            if ml_confidence > 0:
                ml_factor = 0.5 + (ml_confidence / 200.0)  # 0.0 to 1.0 maps to 0.5 to 1.0
                position_size *= ml_factor
            
            # Apply position limits
            min_lot = symbol_info.get('volume_min', 0.01)
            max_lot = symbol_info.get('volume_max', 100.0)
            lot_step = symbol_info.get('volume_step', 0.01)
            
            if position_size < min_lot:
                position_size = 0.0  # Too small to trade
            elif position_size > max_lot:
                position_size = max_lot
            else:
                # Round to nearest step
                position_size = round(position_size / lot_step) * lot_step
            
            # Final validation
            if position_size < min_lot:
                position_size = 0.0
            
            self.logger.info(f"Position size calculated: {position_size} lots "
                           f"(equity: {self.current_equity:.2f}, risk: {risk_amount:.2f}, "
                           f"price_risk: {price_risk:.5f}, confidence: {confidence}%)")
            
            return position_size
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def _calculate_drawdown_factor(self) -> float:
        """Calculate position size reduction based on current drawdown"""
        try:
            if self.peak_equity <= 0:
                return 1.0
            
            current_drawdown = (self.peak_equity - self.current_equity) / self.peak_equity * 100
            
            # No reduction if drawdown is low
            if current_drawdown < 5.0:  # Less than 5% drawdown
                return 1.0
            
            # Linear reduction: 5% drawdown = 1.0 factor, 20% drawdown = 0.5 factor
            # Beyond 20% drawdown, stop trading
            if current_drawdown >= 20.0:
                return 0.0  # Don't trade
            
            # Linear interpolation
            factor = 1.0 - ((current_drawdown - 5.0) / 15.0 * 0.5)
            return max(0.0, factor)
            
        except Exception as e:
            self.logger.error(f"Error calculating drawdown factor: {e}")
            return 1.0
    
    def _get_volatility_adjustment(self, symbol: str) -> float:
        """Get volatility-based position size adjustment"""
        try:
            # Get recent historical data to calculate volatility
            df = self.broker.get_historical_data(symbol, "H1", 50)  # 50 hours of data
            if df is None or len(df) < 10:
                return 1.0  # Default if no data
            
            # Calculate ATR-based volatility
            df = df.copy()
            df['tr0'] = abs(df['high'] - df['low'])
            df['tr1'] = abs(df['high'] - df['close'].shift())
            df['tr2'] = abs(df['low'] - df['close'].shift())
            df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
            atr = df['tr'].rolling(window=14).mean().iloc[-1]
            
            # Calculate average ATR over longer period for comparison
            df_long = self.broker.get_historical_data(symbol, "H1", 200)  # 200 hours
            if df_long is None or len(df_long) < 20:
                return 1.0
                
            df_long = df_long.copy()
            df_long['tr0'] = abs(df_long['high'] - df_long['low'])
            df_long['tr1'] = abs(df_long['high'] - df_long['close'].shift())
            df_long['tr2'] = abs(df_long['low'] - df_long['close'].shift())
            df_long['tr'] = df_long[['tr0', 'tr1', 'tr2']].max(axis=1)
            avg_atr = df_long['tr'].rolling(window=14).mean().iloc[-1]
            
            if avg_atr <= 0:
                return 1.0
            
            # Volatility ratio: current ATR vs average ATR
            volatility_ratio = atr / avg_atr
            
            # Inverse relationship: higher volatility = smaller position
            # Volatility ratio of 1.0 = factor of 1.0
            # Volatility ratio of 2.0 = factor of 0.5
            # Volatility ratio of 0.5 = factor of 1.5
            if volatility_ratio <= 0:
                return 1.0
            
            volatility_factor = 1.0 / volatility_ratio
            
            # Limit the adjustment to reasonable bounds
            volatility_factor = max(0.5, min(2.0, volatility_factor))
            
            return volatility_factor
            
        except Exception as e:
            self.logger.error(f"Error calculating volatility adjustment: {e}")
            return 1.0
    
    def can_open_new_position(self) -> Tuple[bool, str]:
        """Check if a new position can be opened based on risk limits"""
        try:
            # Update account info
            self.update_account_info()
            
            # Check daily loss limit
            max_daily_loss = self.current_equity * (MAX_DAILY_LOSS / 100.0)
            if abs(self.daily_pnl) >= max_daily_loss:
                return False, f"Daily loss limit reached: {abs(self.daily_pnl):.2f} >= {max_daily_loss:.2f}"
            
            # Check drawdown limit
            if self.peak_equity > 0:
                current_drawdown = (self.peak_equity - self.current_equity) / self.peak_equity * 100
                if current_drawdown >= MAX_DRAWDOWN:
                    return False, f"Maximum drawdown reached: {current_drawdown:.2f}% >= {MAX_DRAWDOWN}%"
            
            # Check max concurrent positions would be handled by position manager
            
            # Check if we have sufficient margin
            account_info = self.broker.get_account_info()
            if not account_info:
                return False, "Unable to get account information"
            
            margin_free = account_info.get('margin_free', 0)
            margin_level = account_info.get('margin_level', 0)
            
            if margin_level < 200:  # Less than 200% margin level
                return False, f"Insufficient margin: {margin_level:.1f}%"
            
            return True, "Risk checks passed"
            
        except Exception as e:
            self.logger.error(f"Error checking if can open position: {e}")
            return False, f"Error in risk check: {str(e)}"
    
    def update_daily_pnl(self, pnl_change: float) -> None:
        """Update daily P&L tracking"""
        self.daily_pnl += pnl_change
        self.daily_trades += 1
        self.logger.debug(f"Daily P&L updated: {self.daily_pnl:.2f} (change: {pnl_change:.2f})")
    
    def get_risk_status(self) -> Dict[str, Any]:
        """Get current risk status"""
        try:
            self.update_account_info()
            
            # Calculate current drawdown
            current_drawdown = 0.0
            if self.peak_equity > 0:
                current_drawdown = (self.peak_equity - self.current_equity) / self.peak_equity * 100
            
            # Calculate daily loss limit
            max_daily_loss = self.current_equity * (MAX_DAILY_LOSS / 100.0)
            daily_loss_used = abs(self.daily_pnl)
            daily_loss_remaining = max(0, max_daily_loss - daily_loss_used)
            
            # Get account info
            account_info = self.broker.get_account_info()
            
            return {
                "account_equity": self.current_equity,
                "peak_equity": self.peak_equity,
                "current_drawdown": round(current_drawdown, 2),
                "max_drawdown_limit": MAX_DRAWDOWN,
                "daily_pnl": round(self.daily_pnl, 2),
                "daily_trades": self.daily_trades,
                "daily_loss_limit": round(max_daily_loss, 2),
                "daily_loss_used": round(daily_loss_used, 2),
                "daily_loss_remaining": round(daily_loss_remaining, 2),
                "daily_loss_percent": round((daily_loss_used / max_daily_loss * 100) if max_daily_loss > 0 else 0, 2),
                "margin_level": account_info.get('margin_level', 0) if account_info else 0,
                "can_trade": self.can_open_new_position()[0],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting risk status: {e}")
            return {"error": str(e)}