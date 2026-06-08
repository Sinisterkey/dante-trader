"""
Position Manager Module
Handles trade execution, position management, and order processing
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import threading
import time as time_module
from broker_integration import BrokerAPI, OrderType, OrderSide, OrderStatus
from config import *
from market_intelligence import MarketIntelligence

logger = logging.getLogger(__name__)


class PositionManager:
    """Manages trading positions and order execution"""
    
    def __init__(self, broker: BrokerAPI, market_intel: MarketIntelligence):
        self.broker = broker
        self.market_intel = market_intel
        self.positions = {}  # ticket -> position info
        self.orders = {}     # ticket -> order info
        self.is_running = False
        self.monitor_thread = None
        self._lock = threading.Lock()
        
    def start(self) -> bool:
        """Start the position manager"""
        if self.is_running:
            logger.warning("Position manager is already running")
            return False
        
        if not self.broker.is_connected():
            if not self.broker.connect():
                logger.error("Failed to connect to broker")
                return False
        
        self.is_running = True
        self.monitor_thread = threading.Thread(target=self._monitor_positions, daemon=True)
        self.monitor_thread.start()
        logger.info("Position manager started")
        return True
    
    def stop(self) -> None:
        """Stop the position manager"""
        self.is_running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        logger.info("Position manager stopped")
    
    def execute_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a trading signal from the agent system"""
        try:
            action = signal.get('action')
            if action == 'NO_TRADE':
                return {"success": False, "reason": "No trade signal"}
            
            symbol = INSTRUMENT  # From config
            side = OrderSide.BUY if action == 'BUY' else OrderSide.SELL
            entry_price = signal.get('entry_price', 0.0)
            stop_loss = signal.get('stop_loss', 0.0)
            take_profit = signal.get('take_profit', 0.0)
            confidence = signal.get('confidence', 0)
            
            # Only execute if confidence is above threshold
            if confidence < 70:  # Minimum confidence threshold
                return {"success": False, "reason": f"Confidence too low: {confidence}%"}
            
            # Check if we can open a new position (risk management)
            if not self._can_open_position():
                return {"success": False, "reason": "Risk limits prevent opening new position"}
            
            # Calculate position size based on risk
            volume = self._calculate_position_size(symbol, entry_price, stop_loss)
            if volume <= 0:
                return {"success": False, "reason": "Invalid position size calculated"}
            
            # Get current market price for validation
            market_data = self.broker.get_real_time_data(symbol)
            if not market_data:
                return {"success": False, "reason": "Unable to get market data"}
            
            current_price = market_data['bid'] if side == OrderSide.SELL else market_data['ask']
            
            # Validate entry price is reasonable
            price_diff_pct = abs(entry_price - current_price) / current_price * 100
            if price_diff_pct > 0.5:  # More than 0.5% difference
                logger.warning(f"Entry price deviation too large: {price_diff_pct:.2f}%")
                # Use current market price instead
                entry_price = current_price
                # Recalculate SL/TP based on actual entry price
                if action == 'BUY':
                    stop_loss = entry_price - (entry_price - signal.get('stop_loss', 0.0))
                    take_profit = entry_price + (signal.get('take_profit', 0.0) - signal.get('entry_price', 0.0))
                else:  # SELL
                    stop_loss = entry_price + (signal.get('stop_loss', 0.0) - entry_price)
                    take_profit = entry_price - (signal.get('entry_price', 0.0) - signal.get('take_profit', 0.0))
            
            # Place the market order
            order_result = self.broker.place_order(
                symbol=symbol,
                order_type=OrderType.MARKET,
                side=side,
                volume=volume,
                sl=stop_loss,
                tp=take_profit,
                comment=f"AI Signal: {action} Conf:{confidence}%"
            )
            
            if not order_result.get('success', False):
                return order_result
            
            # Store the position info
            position_info = {
                'ticket': order_result['order'],
                'symbol': symbol,
                'side': side.value,
                'volume': volume,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'confidence': confidence,
                'signal_reason': signal.get('reason', ''),
                'timestamp': datetime.now(timezone.utc),
                'status': 'open',
                'unrealized_pnl': 0.0,
                'ml_confidence': signal.get('ml_confidence', 0.0),
                'rsi': signal.get('rsi', 50.0),
                'macd': signal.get('macd', 0.0),
                'bb_position': 0.5,
                'atr_normalized': 0.01,
                'volume_ratio': 1.0,
                'price_vs_sma20': signal.get('price_vs_sma20', 0.0),
                'price_vs_sma50': signal.get('price_vs_sma50', 0.0),
                'hour_of_day': datetime.now(timezone.utc).hour,
                'day_of_week': datetime.now(timezone.utc).weekday(),
                'session': 1.0 if self.market_intel.is_london_ny_overlap() else 0.0,
                'volatility_regime': 0.5,
                'trend_alignment': 1.0 if signal.get('trend_aligned', False) else 0.0
            }
            
            with self._lock:
                self.positions[order_result['order']] = position_info
            
            logger.info(f"Position opened: Ticket {order_result['order']}, {side.value} {volume} {symbol} at {entry_price}")
            
            return {
                "success": True,
                "ticket": order_result['order'],
                "position": position_info,
                "message": f"Position opened: {side.value} {volume} {symbol} at {entry_price}"
            }
            
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return {"success": False, "error": str(e)}
    
    def close_position(self, ticket: int, reason: str = "Manual close") -> Dict[str, Any]:
        """Close a position by ticket"""
        try:
            with self._lock:
                if ticket not in self.positions:
                    return {"success": False, "error": f"Position {ticket} not found"}
                
                position = self.positions[ticket]
            
            # For closing, we need to place an opposite order
            side = OrderSide.SELL if position['side'] == 'buy' else OrderSide.BUY
            volume = position['volume']
            symbol = position['symbol']
            
            # Get current market price
            market_data = self.broker.get_real_time_data(symbol)
            if not market_data:
                return {"success": False, "error": "Unable to get market data"}
            
            price = market_data['bid'] if side == OrderSide.SELL else market_data['ask']
            
            # Place the closing order
            close_result = self.broker.place_order(
                symbol=symbol,
                order_type=OrderType.MARKET,
                side=side,
                volume=volume,
                comment=f"Close: {reason}"
            )
            
            if not close_result.get('success', False):
                return close_result
            
            # Calculate P&L
            entry_price = position['entry_price']
            exit_price = price
            if position['side'] == 'buy':
                pnl = (exit_price - entry_price) * volume
            else:  # sell
                pnl = (entry_price - exit_price) * volume
            
            # Update position info
            with self._lock:
                position['exit_price'] = exit_price
                position['exit_time'] = datetime.now(timezone.utc)
                position['pnl'] = pnl
                position['status'] = 'closed'
                position['close_reason'] = reason
                # Move to closed positions or remove from active
                # For simplicity, we'll keep it but mark as closed
            
            logger.info(f"Position closed: Ticket {ticket}, P&L: {pnl:.2f}, Reason: {reason}")
            
            return {
                "success": True,
                "ticket": ticket,
                "pnl": pnl,
                "exit_price": exit_price,
                "message": f"Position closed: P&L {pnl:.2f}"
            }
            
        except Exception as e:
            logger.error(f"Error closing position {ticket}: {e}")
            return {"success": False, "error": str(e)}
    
    def modify_position_sl_tp(self, ticket: int, sl: float = None, tp: float = None) -> Dict[str, Any]:
        """Modify stop loss and/or take profit for a position"""
        try:
            with self._lock:
                if ticket not in self.positions:
                    return {"success": False, "error": f"Position {ticket} not found"}
                
                position = self.positions[ticket]
            
            # Use current values if not specified
            if sl is None:
                sl = position.get('stop_loss', 0.0)
            if tp is None:
                tp = position.get('take_profit', 0.0)
            
            # Modify the order through broker
            result = self.broker.modify_order(ticket, sl=sl, tp=tp)
            
            if result.get('success', False):
                # Update our records
                with self._lock:
                    if sl is not None:
                        position['stop_loss'] = sl
                    if tp is not None:
                        position['take_profit'] = tp
                    position['modified_time'] = datetime.now(timezone.utc)
                
                logger.info(f"Position {ticket} SL/TP modified: SL={sl}, TP={tp}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error modifying position {ticket} SL/TP: {e}")
            return {"success": False, "error": str(e)}
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all currently open positions"""
        with self._lock:
            # Filter to only open positions
            return [pos for pos in self.positions.values() if pos.get('status') == 'open']
    
    def get_position(self, ticket: int) -> Optional[Dict[str, Any]]:
        """Get a specific position by ticket"""
        with self._lock:
            return self.positions.get(ticket)
    
    def _can_open_position(self) -> bool:
        """Check if we can open a new position based on risk limits"""
        try:
            # Check max concurrent positions
            open_positions = self.get_open_positions()
            if len(open_positions) >= MAX_CONCURRENT_POSITIONS:
                logger.warning(f"Max concurrent positions reached: {len(open_positions)}")
                return False
            
            # Check account margin/equity
            account_info = self.broker.get_account_info()
            if not account_info:
                logger.warning("Unable to get account info")
                return False
            
            equity = account_info.get('equity', 0)
            if equity <= 0:
                logger.warning(f"Invalid account equity: {equity}")
                return False
            
            # Additional risk checks could go here
            return True
            
        except Exception as e:
            logger.error(f"Error checking if can open position: {e}")
            return False
    
    def _calculate_position_size(self, symbol: str, entry_price: float, stop_loss: float) -> float:
        """Calculate position size based on risk parameters"""
        try:
            # Get account info
            account_info = self.broker.get_account_info()
            if not account_info:
                logger.warning("Unable to get account info for position sizing")
                return 0.0
            
            equity = account_info.get('equity', 0.0)
            if equity <= 0:
                logger.warning(f"Invalid account equity: {equity}")
                return 0.0
            
            # Get symbol info for contract size and point value
            symbol_info = self.broker.get_symbol_info(symbol)
            if not symbol_info:
                logger.warning(f"Unable to get symbol info for {symbol}")
                return 0.0
            
            # Calculate risk amount
            risk_amount = equity * (RISK_PER_TRADE / 100.0)  # Convert percentage to decimal
            
            # Calculate price difference
            price_diff = abs(entry_price - stop_loss)
            if price_diff <= 0:
                logger.warning(f"Invalid price difference: {price_diff}")
                return 0.0
            
            # For forex, we need to consider the point value
            # For simplicity, we'll assume 1 lot = 100,000 units and point value = 0.0001 for most pairs
            # This would need to be adjusted based on actual symbol info
            point_value = symbol_info.get('point', 0.0001)
            if point_value <= 0:
                point_value = 0.0001  # Default for most forex pairs
            
            # Calculate position size in lots
            # Risk amount = position_size * price_diff / point_value * contract_size
            # Simplified: position_size = risk_amount * point_value / price_diff
            contract_size = symbol_info.get('trade_contract_size', 100000)
            if contract_size <= 0:
                contract_size = 100000  # Standard forex lot
            
            position_size = (risk_amount * point_value) / (price_diff * contract_size)
            
            # Apply minimum and maximum lot sizes
            min_lot = symbol_info.get('volume_min', 0.01)
            max_lot = symbol_info.get('volume_max', 100.0)
            lot_step = symbol_info.get('volume_step', 0.01)
            
            if position_size < min_lot:
                position_size = 0.0  # Too small
            elif position_size > max_lot:
                position_size = max_lot
            else:
                # Round to nearest step
                position_size = round(position_size / lot_step) * lot_step
            
            logger.info(f"Position size calculated: {position_size} lots (risk: {risk_amount:.2f}, equity: {equity:.2f})")
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0
    
    def _monitor_positions(self) -> None:
        """Background thread to monitor open positions"""
        logger.info("Position monitor thread started")
        
        while self.is_running:
            try:
                # Update unrealized P&L for all open positions
                open_positions = self.get_open_positions()
                
                for position in open_positions:
                    ticket = position['ticket']
                    symbol = position['symbol']
                    
                    # Get current market price
                    market_data = self.broker.get_real_time_data(symbol)
                    if not market_data:
                        continue
                    
                    current_price = market_data['bid'] if position['side'] == 'sell' else market_data['ask']
                    entry_price = position['entry_price']
                    volume = position['volume']
                    
                    # Calculate unrealized P&L
                    if position['side'] == 'buy':
                        unrealized_pnl = (current_price - entry_price) * volume
                    else:  # sell
                        unrealized_pnl = (entry_price - current_price) * volume
                    
                    # Update position info
                    with self._lock:
                        if ticket in self.positions:
                            self.positions[ticket]['unrealized_pnl'] = unrealized_pnl
                            self.positions[ticket]['current_price'] = current_price
                            self.positions[ticket]['last_update'] = datetime.now(timezone.utc)
                
                # Sleep for a short interval
                time_module.sleep(1.0)  # Update every second
                
            except Exception as e:
                logger.error(f"Error in position monitor: {e}")
                time_module.sleep(5.0)  # Longer sleep on error
        
        logger.info("Position monitor thread stopped")