try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False
import pandas as pd
import logging
from typing import Optional, Dict, List
from config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, TIMEFRAMES

logger = logging.getLogger(__name__)


class MT5Connector:
    """MetaTrader 5 connection handler."""

    def __init__(self):
        self.connected = False
        self.connect()

    def connect(self) -> bool:
        """Connect to MT5."""
        if not MT5_AVAILABLE:
            logger.warning("MT5 not available - running in demo mode")
            self.connected = True
            return True
        try:
            if not mt5.initialize(login=int(MT5_LOGIN), password=MT5_PASSWORD, server=MT5_SERVER):
                logger.error(f"MT5 initialization failed: {mt5.last_error()}")
                return False

            self.connected = True
            logger.info(f"Connected to MT5: {MT5_SERVER}")
            return True
        except Exception as e:
            logger.error(f"Error connecting to MT5: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from MT5."""
        try:
            if MT5_AVAILABLE:
                mt5.shutdown()
            self.connected = False
            logger.info("Disconnected from broker")
        except Exception as e:
            logger.error(f"Error disconnecting from broker: {e}")

    def is_connected(self) -> bool:
        """Check if connected to MT5."""
        if not self.connected:
            return self.connect()
        return self.connected

    def fetch_ohlcv(self, symbol: str, timeframe: int, bars: int = 100) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from MT5.
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            timeframe: MT5 timeframe constant (e.g., mt5.TIMEFRAME_M5)
            bars: Number of bars to fetch
            
        Returns:
            DataFrame with OHLCV data, or None if failed
        """
        if not MT5_AVAILABLE:
            logger.info(f"Demo mode: returning mock data for {symbol} {timeframe}")
            return self._generate_mock_data(symbol, timeframe, bars)
        
        try:
            if not self.is_connected():
                logger.error("Not connected to MT5")
                return None

            # Convert timeframe int to MT5 constant
            tf_map = {
                5: mt5.TIMEFRAME_M5,
                15: mt5.TIMEFRAME_M15,
                30: mt5.TIMEFRAME_M30,
                240: mt5.TIMEFRAME_H4,
                1440: mt5.TIMEFRAME_D1,
            }

            mt5_timeframe = tf_map.get(timeframe)
            if not mt5_timeframe:
                logger.error(f"Invalid timeframe: {timeframe}")
                return None

            # Fetch rates
            rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, bars)

            if rates is None or len(rates) == 0:
                logger.warning(f"No data for {symbol} at {timeframe}min")
                return None

            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df = df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'tick_volume': 'volume'
            })

            # Select relevant columns
            df = df[['time', 'open', 'high', 'low', 'close', 'volume']]

            return df

        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            self.disconnect()
            self.connect()
            return None
    
    def _generate_mock_data(self, symbol: str, timeframe: int, bars: int = 100) -> pd.DataFrame:
        """Generate mock OHLCV data for demo mode."""
        from datetime import datetime
        import numpy as np
        
        now = datetime.now()
        if timeframe == 5:
            delta = pd.Timedelta(minutes=5)
        elif timeframe == 15:
            delta = pd.Timedelta(minutes=15)
        elif timeframe == 30:
            delta = pd.Timedelta(minutes=30)
        elif timeframe == 240:
            delta = pd.Timedelta(hours=4)
        elif timeframe == 1440:
            delta = pd.Timedelta(days=1)
        else:
            delta = pd.Timedelta(minutes=15)

        times = [now - i * delta for i in range(bars)]
        times.reverse()

        base_price = 18000.0
        data = []

        for i, t in enumerate(times):
            if i == 0:
                open_price = base_price
            else:
                open_price = data[-1]['close']

            volatility = 0.01
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
                'tick_volume': volume,
            })

        df = pd.DataFrame(data)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df['volume'] = df['tick_volume']
        return df[['time', 'open', 'high', 'low', 'close', 'volume']]

    def fetch_multi_timeframe(self, symbol: str, bars: int = 100) -> Dict[str, pd.DataFrame]:
        """Fetch OHLCV data for multiple timeframes.
        
        Args:
            symbol: Trading symbol
            bars: Number of bars per timeframe
            
        Returns:
            Dictionary with timeframe keys and OHLCV DataFrames as values
        """
        result = {}

        for tf_name, tf_minutes in TIMEFRAMES.items():
            df = self.fetch_ohlcv(symbol, tf_minutes, bars)
            if df is not None:
                result[tf_name] = df
            else:
                logger.warning(f"Failed to fetch {tf_name} data for {symbol}")

        return result

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol."""
        try:
            if not self.is_connected():
                return None

            tick = mt5.symbol_info_tick(symbol)
            if tick:
                return tick.ask
            return None

        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None

    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get symbol information."""
        try:
            if not self.is_connected():
                return None

            info = mt5.symbol_info(symbol)
            if info:
                return {
                    "symbol": info.name,
                    "bid": info.bid,
                    "ask": info.ask,
                    "point": info.point,
                    "digits": info.digits,
                    "spread": info.ask - info.bid,
                    "volume": info.volume
                }
            return None

        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            return None

    def is_market_open(self) -> bool:
        """Check if market is currently open."""
        try:
            if not self.is_connected():
                return False

            # Simple check: if we can get current price for a major symbol, market is open
            price = self.get_current_price("EURUSD")
            return price is not None

        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False
