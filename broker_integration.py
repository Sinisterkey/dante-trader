"""
Broker Integration Module
Handles connectivity with brokerage APIs (MetaTrader 5, Interactive Brokers)
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import logging
import time as time_module
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from config import *

logger = logging.getLogger(__name__)


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class BrokerAPI(ABC):
    """Abstract base class for broker API integration"""
    
    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to broker"""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from broker"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to broker"""
        pass
    
    @abstractmethod
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        pass
    
    @abstractmethod
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol information"""
        pass
    
    @abstractmethod
    def get_historical_data(self, symbol: str, timeframe: str, bars: int = 100) -> pd.DataFrame:
        """Get historical price data"""
        pass
    
    @abstractmethod
    def get_real_time_data(self, symbol: str) -> Dict[str, Any]:
        """Get real-time price data"""
        pass
    
    @abstractmethod
    def place_order(self, symbol: str, order_type: OrderType, side: OrderSide, 
                   volume: float, price: float = 0.0, sl: float = 0.0, 
                   tp: float = 0.0, comment: str = "") -> Dict[str, Any]:
        """Place a trading order"""
        pass
    
    @abstractmethod
    def modify_order(self, ticket: int, sl: float = None, tp: float = None) -> Dict[str, Any]:
        """Modify an existing order"""
        pass
    
    @abstractmethod
    def cancel_order(self, ticket: int) -> Dict[str, Any]:
        """Cancel an order"""
        pass
    
    @abstractmethod
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions"""
        pass
    
    @abstractmethod
    def get_order_history(self, from_date: datetime, to_date: datetime) -> List[Dict[str, Any]]:
        """Get order history"""
        pass


class MT5Broker(BrokerAPI):
    """MetaTrader 5 broker implementation"""
    
    def __init__(self):
        self.connected = False
        self.login = MT5_LOGIN
        self.password = MT5_PASSWORD
        self.server = MT5_SERVER
        self.timeout = MT5_TIMEOUT
        
    def connect(self) -> bool:
        """Establish connection to MT5 terminal"""
        try:
            if not mt5.initialize():
                logger.error(f"MT5 initialize() failed, error code = {mt5.last_error()}")
                return False
            
            # Login to account
            authorized = mt5.login(login=self.login, password=self.password, server=self.server)
            if not authorized:
                logger.error(f"MT5 login failed, error code = {mt5.last_error()}")
                mt5.shutdown()
                return False
                
            self.connected = True
            logger.info(f"Connected to MT5 account {self.login} on server {self.server}")
            return True
        except Exception as e:
            logger.error(f"MT5 connection error: {e}")
            self.connected = False
            return False
    
    def disconnect(self) -> None:
        """Disconnect from MT5 terminal"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info("Disconnected from MT5")
    
    def is_connected(self) -> bool:
        """Check if MT5 connection is active"""
        return self.connected and mt5.terminal_info() is not None
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        if not self.is_connected():
            if not self.connect():
                logger.error("Failed to reconnect to MT5")
                return {}
        
        try:
            account_info = mt5.account_info()
            if account_info is None:
                logger.warning("Failed to get account info")
                return {}
            
            return account_info._asdict()
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {}
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol information"""
        if not self.is_connected():
            if not self.connect():
                logger.error("Failed to reconnect to MT5")
                return {}
        
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger.warning(f"Failed to get symbol info for {symbol}")
                return {}
            
            return symbol_info._asdict()
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            return {}
    
    def get_historical_data(self, symbol: str, timeframe: str, bars: int = 100) -> pd.DataFrame:
        """Get historical price data"""
        if not self.is_connected():
            if not self.connect():
                logger.error("Failed to reconnect to MT5")
                return self._generate_mock_data(timeframe, bars)
        
        try:
            # Map timeframe strings to MT5 constants
            tf_map = {
                "M1": mt5.TIMEFRAME_M1,
                "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15,
                "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1,
                "W1": mt5.TIMEFRAME_W1,
                "MN1": mt5.TIMEFRAME_MN1
            }
            
            mt5_timeframe = tf_map.get(timeframe)
            if mt5_timeframe is None:
                logger.error(f"Unsupported timeframe: {timeframe}")
                return self._generate_mock_data(timeframe, bars)
            
            # Get historical data
            rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, bars)
            
            if rates is None or len(rates) == 0:
                logger.warning(f"No data received for {symbol} {timeframe}")
                return self._generate_mock_data(timeframe, bars)
            
            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
            # Ensure volume column exists for compatibility with dashboard
            # Use tick_volume as volume proxy (real_volume is often 0 for CFDs)
            if 'volume' not in df.columns:
                df['volume'] = df['tick_volume']
            
            logger.info(f"Fetched {len(df)} bars for {symbol} {timeframe}")
            return df
        except Exception as e:
            logger.error(f"Error fetching data for {symbol} {timeframe}: {e}")
            return self._generate_mock_data(timeframe, bars)
    
    def get_real_time_data(self, symbol: str) -> Dict[str, Any]:
        """Get real-time price data"""
        if not self.is_connected():
            if not self.connect():
                logger.error("Failed to reconnect to MT5")
                return {}
        
        try:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.warning(f"No tick data for {symbol}")
                return {}
            
            return {
                'symbol': symbol,
                'bid': tick.bid,
                'ask': tick.ask,
                'last': tick.last,
                'volume': tick.volume,
                'time': datetime.fromtimestamp(tick.time, tz=timezone.utc),
                'flags': tick.flags
            }
        except Exception as e:
            logger.error(f"Error getting real-time data for {symbol}: {e}")
            return {}
    
    def place_order(self, symbol: str, order_type: OrderType, side: OrderSide, 
                   volume: float, price: float = 0.0, sl: float = 0.0, 
                   tp: float = 0.0, comment: str = "") -> Dict[str, Any]:
        """Place a trading order"""
        if not self.is_connected():
            if not self.connect():
                logger.error("Failed to reconnect to MT5")
                return {"success": False, "error": "Not connected to MT5"}
        
        try:
            # Prepare request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5.ORDER_TYPE_BUY if side == OrderSide.BUY else mt5.ORDER_TYPE_SELL,
                "price": 0.0,  # Will be set based on order type
                "sl": sl,
                "tp": tp,
                "deviation": 20,
                "magic": 234000,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Set price based on order type
            if order_type == OrderType.MARKET:
                tick = mt5.symbol_info_tick(symbol)
                if tick is None:
                    return {"success": False, "error": "No tick data available"}
                request["price"] = tick.ask if side == OrderSide.BUY else tick.bid
                request["type"] = mt5.ORDER_TYPE_BUY if side == OrderSide.BUY else mt5.ORDER_TYPE_SELL
            elif order_type == OrderType.LIMIT:
                request["price"] = price
                request["type"] = mt5.ORDER_TYPE_BUY_LIMIT if side == OrderSide.BUY else mt5.ORDER_TYPE_SELL_LIMIT
            elif order_type == OrderType.STOP:
                request["price"] = price
                request["type"] = mt5.ORDER_TYPE_BUY_STOP if side == OrderSide.BUY else mt5.ORDER_TYPE_SELL_STOP
            elif order_type == OrderType.STOP_LIMIT:
                request["price"] = price
                request["type"] = mt5.ORDER_TYPE_BUY_STOP_LIMIT if side == OrderSide.BUY else mt5.ORDER_TYPE_SELL_STOP_LIMIT
                # For stop-limit, we need to set the stop price as well
                request["stoplimit"] = price
            
            # Send request
            result = mt5.order_send(request)
            
            if result is None:
                logger.error(f"Order send failed, error code = {mt5.last_error()}")
                return {"success": False, "error": f"Order send failed: {mt5.last_error()}"}
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Order failed, retcode={result.retcode}")
                return {"success": False, "error": f"Order failed: {result.retcode}", "result": result._asdict()}
            
            logger.info(f"Order placed successfully: {result.order}")
            return {
                "success": True, 
                "order": result.order,
                "volume": result.volume,
                "price": result.price,
                "result": result._asdict()
            }
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {"success": False, "error": str(e)}
    
    def modify_order(self, ticket: int, sl: float = None, tp: float = None) -> Dict[str, Any]:
        """Modify an existing order"""
        if not self.is_connected():
            if not self.connect():
                logger.error("Failed to reconnect to MT5")
                return {"success": False, "error": "Not connected to MT5"}
        
        try:
            # Get current position/order info
            positions = mt5.positions_get(ticket=ticket)
            if not positions or len(positions) == 0:
                # Try orders if not a position
                orders = mt5.orders_get(ticket=ticket)
                if not orders or len(orders) == 0:
                    logger.error(f"Position or order with ticket {ticket} not found")
                    return {"success": False, "error": "Position or order not found"}
                position = orders[0]
            else:
                position = positions[0]
            
            # Prepare request
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": position.symbol,
            }
            
            if sl is not None:
                request["sl"] = sl
            if tp is not None:
                request["tp"] = tp
            
            # Send request
            result = mt5.order_send(request)
            
            if result is None:
                logger.error(f"Order modify failed, error code = {mt5.last_error()}")
                return {"success": False, "error": f"Order modify failed: {mt5.last_error()}"}
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Order modify failed, retcode={result.retcode}")
                return {"success": False, "error": f"Order modify failed: {result.retcode}"}
            
            logger.info(f"Order {ticket} modified successfully")
            return {"success": True, "result": result._asdict()}
        except Exception as e:
            logger.error(f"Error modifying order: {e}")
            return {"success": False, "error": str(e)}
    
    def cancel_order(self, ticket: int) -> Dict[str, Any]:
        """Cancel an order"""
        if not self.is_connected():
            if not self.connect():
                logger.error("Failed to reconnect to MT5")
                return {"success": False, "error": "Not connected to MT5"}
        
        try:
            # Prepare request
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": ticket,
            }
            
            # Send request
            result = mt5.order_send(request)
            
            if result is None:
                logger.error(f"Order cancel failed, error code = {mt5.last_error()}")
                return {"success": False, "error": f"Order cancel failed: {mt5.last_error()}"}
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"Order cancel failed, retcode={result.retcode}")
                return {"success": False, "error": f"Order cancel failed: {result.retcode}"}
            
            logger.info(f"Order {ticket} cancelled successfully")
            return {"success": True, "result": result._asdict()}
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return {"success": False, "error": str(e)}
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions"""
        if not self.is_connected():
            if not self.connect():
                logger.error("Failed to reconnect to MT5")
                return []
        
        try:
            positions = mt5.positions_get()
            if positions is None:
                logger.warning("No positions retrieved")
                return []
            
            return [pos._asdict() for pos in positions]
        except Exception as e:
            logger.error(f"Error getting open positions: {e}")
            return []
    
    def get_order_history(self, from_date: datetime, to_date: datetime) -> List[Dict[str, Any]]:
        """Get order history"""
        if not self.is_connected():
            if not self.connect():
                logger.error("Failed to reconnect to MT5")
                return []
        
        try:
            # Convert datetime to timestamp
            from_timestamp = int(from_date.timestamp())
            to_timestamp = int(to_date.timestamp())
            
            orders = mt5.history_orders_get(from_timestamp, to_timestamp)
            if orders is None:
                logger.warning("No orders retrieved from history")
                return []
            
            return [order._asdict() for order in orders]
        except Exception as e:
            logger.error(f"Error getting order history: {e}")
            return []
    
    def _generate_mock_data(self, timeframe: str, bars: int = 100) -> pd.DataFrame:
        """Generate mock data for demonstration when MT5 is not available"""
        logger.info(f"Generating mock data for {timeframe}")
        
        # Create timestamps going back from now
        now = datetime.now(timezone.utc)
        if timeframe == "M1":
            delta = pd.Timedelta(minutes=1)
        elif timeframe == "M5":
            delta = pd.Timedelta(minutes=5)
        elif timeframe == "M15":
            delta = pd.Timedelta(minutes=15)
        elif timeframe == "M30":
            delta = pd.Timedelta(minutes=30)
        elif timeframe == "H1":
            delta = pd.Timedelta(hours=1)
        elif timeframe == "H4":
            delta = pd.Timedelta(hours=4)
        elif timeframe == "D1":
            delta = pd.Timedelta(days=1)
        elif timeframe == "W1":
            delta = pd.Timedelta(weeks=1)
        elif timeframe == "MN1":
            delta = pd.Timedelta(days=30)  # Approximate month
        else:
            delta = pd.Timedelta(minutes=15)  # default
            
        times = [now - i * delta for i in range(bars)]
        times.reverse()  # Oldest first
        
        # Generate realistic price data for NAS100
        base_price = 18000.0  # Approximate NAS100 level
        data = []
        
        for i, t in enumerate(times):
            # Add some random walk behavior
            if i == 0:
                open_price = base_price
            else:
                open_price = data[-1]['close']
                
            # Add volatility
            volatility = 0.01  # 1% volatility
            close_price = open_price * (1 + np.random.normal(0, volatility))
            high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, volatility/2)))
            low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, volatility/2)))
            volume = np.random.randint(1000, 10000)
            
            data.append({
                'time': int(t.timestamp()),
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume,
                'tick_volume': volume,
                'spread': 10,
                'real_volume': volume
            })
            
        df = pd.DataFrame(data)
        df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
        return df