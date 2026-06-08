try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    yf = None
    YF_AVAILABLE = False
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False
import pandas as pd
import numpy as np
from datetime import datetime, time, timezone
import logging
import time as time_module
from config import *

logger = logging.getLogger(__name__)

class MT5Bridge:
    def __init__(self):
        self.connected = False
        self.connect()
    
    def connect(self):
        """Establish connection to MT5 terminal"""
        if not MT5_AVAILABLE:
            logger.warning("MT5 not available - running in demo mode with mock data")
            self.connected = True  # Demo mode "connected"
            return True
        try:
            if not mt5.initialize():
                logger.error(f"MT5 initialize() failed, error code = {mt5.last_error()}")
                return False
            
            authorized = mt5.login(login=MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
            if not authorized:
                logger.error(f"MT5 login failed, error code = {mt5.last_error()}")
                mt5.shutdown()
                return False
                
            self.connected = True
            logger.info(f"Connected to MT5 account {MT5_LOGIN} on server {MT5_SERVER}")
            return True
        except Exception as e:
            logger.error(f"MT5 connection error: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from MT5 terminal"""
        if self.connected:
            if MT5_AVAILABLE:
                mt5.shutdown()
            self.connected = False
            logger.info("Disconnected from broker")
    
    def is_connected(self):
        """Check if MT5 connection is active"""
        if not MT5_AVAILABLE:
            return self.connected
        return self.connected and mt5.terminal_info() is not None
    
    def fetch_symbol_data(self, symbol, timeframe, bars=100):
        """Fetch historical data for a symbol and timeframe"""
        if not MT5_AVAILABLE and YF_AVAILABLE:
            return self._fetch_yf_data(symbol, timeframe, bars)
        if not MT5_AVAILABLE:
            logger.warning("Neither MT5 nor YF available for market data")
            return pd.DataFrame()
        
        if not self.is_connected():
            if not self.connect():
                logger.error("Failed to reconnect to MT5")
                return self.generate_mock_data(timeframe, bars)
        
        try:
            # Map timeframe strings to MT5 constants
            tf_map = {
                "M15": mt5.TIMEFRAME_M15,
                "H4": mt5.TIMEFRAME_H4
            }
            
            mt5_timeframe = tf_map.get(timeframe)
            if mt5_timeframe is None:
                logger.error(f"Unsupported timeframe: {timeframe}")
                return self.generate_mock_data(timeframe, bars)
            
            # Get historical data
            rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, bars)
            
            if rates is None or len(rates) == 0:
                logger.warning(f"No data received for {symbol} {timeframe}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            logger.info(f"Fetched {len(df)} bars for {symbol} {timeframe}")
            return df
        except Exception as e:
            logger.error(f"Error fetching data for {symbol} {timeframe}: {e}")
            return pd.DataFrame()
    
    def _fetch_yf_data(self, symbol, timeframe, bars=100):
        """Fetch data from Yahoo Finance"""
        if not YF_AVAILABLE:
            return pd.DataFrame()
        try:
            # Convert symbol to Yahoo Finance format
            yf_symbol = self._convert_to_yf_symbol(symbol)
            tf_map = {"M1": "1m", "M5": "5m", "M15": "15m", "M30": "30m", "H1": "1h", "H4": "1h", "D1": "1d"}
            period_map = {"M1": "1d", "M5": "5d", "M15": "1mo", "H1": "6mo", "H4": "6mo", "D1": "1y", "W1": "2y"}
            
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period=period_map.get(timeframe, "1mo"), interval=tf_map.get(timeframe, "1h"))
            df = df.tail(bars)
            df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
            df["tick_volume"] = df["volume"]
            df["real_volume"] = df["volume"]
            logger.info(f"Fetched {len(df)} bars from Yahoo Finance for {yf_symbol}")
            return df
        except Exception as e:
            logger.error(f"Error fetching Yahoo Finance data: {e}")
            return pd.DataFrame()

    def _convert_to_yf_symbol(self, symbol):
        """Convert MT5 symbol to Yahoo Finance symbol"""
        yf_symbols = {
            "ND100m": "^NDX", "NAS100": "^NDX", "NAS": "^NDX", "NDX": "^NDX",
            "XAUUSD": "GC=F", "GOLD": "GC=F", "GC": "GC=F",
            "BTCUSD": "BTC-USD", "BITCOIN": "BTC-USD", "BTC": "BTC-USD",
        }
        return yf_symbols.get(symbol, symbol)

    def generate_mock_data(self, timeframe, bars=100):
        """Generate mock data for demonstration when MT5 is not available"""
        logger.info(f"Generating mock data for {timeframe}")
        
        # Create timestamps going back from now
        now = datetime.now()
        if timeframe == "M15":
            delta = pd.Timedelta(minutes=15)
        elif timeframe == "H4":
            delta = pd.Timedelta(hours=4)
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
                'tick_volume': volume,
                'spread': 10,
                'real_volume': volume
            })
            
        df = pd.DataFrame(data)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

class MarketIntelligence:
    def __init__(self):
        self.bridge = MT5Bridge()
    
    def calculate_swing_levels(self, df, lookback=LOOKBACK_PERIOD):
        """Calculate swing high and low levels (excluding current candle)"""
        if df is None or len(df) < lookback + 1:  # Need extra candle to exclude current
            return None, None
        
        # Exclude current candle (last row) for swing calculation
        lookback_data = df.iloc[:-1].tail(lookback)
        
        swing_high = lookback_data['high'].max()
        swing_low = lookback_data['low'].min()
        
        return swing_high, swing_low
    
    def calculate_sma(self, df, period=SMA_PERIOD):
        """Calculate Simple Moving Average"""
        if df is None or len(df) < period:
            return None
        
        return df['close'].rolling(window=period).mean().iloc[-1]
    
    def calculate_atr(self, df, period=ATR_PERIOD):
        """Calculate Average True Range"""
        if df is None or len(df) < period:
            return None
        
        # Calculate True Range
        df = df.copy()
        df['tr0'] = abs(df['high'] - df['low'])
        df['tr1'] = abs(df['high'] - df['close'].shift())
        df['tr2'] = abs(df['low'] - df['close'].shift())
        df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
        
        # Calculate ATR
        atr = df['tr'].rolling(window=period).mean().iloc[-1]
        return atr
    
    def is_london_ny_overlap(self, timestamp=None):
        """Check if current time is within London/NY overlap (12:00-16:00 GMT)"""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        # Extract hour in GMT
        hour = timestamp.hour
        
        return SESSION_START_HOUR <= hour < SESSION_END_HOUR
    
    def analyze_market(self):
        """Main analysis function that processes market data"""
        if not self.is_london_ny_overlap():
            logger.info("Outside London/NY overlap session - no trading")
            return None
        
        # Fetch data for both timeframes
        df_m15 = self.bridge.fetch_symbol_data(INSTRUMENT, "M15", BARS_TO_FETCH)
        df_h4 = self.bridge.fetch_symbol_data(INSTRUMENT, "H4", BARS_TO_FETCH)
        
        if df_m15 is None or df_h4 is None:
            logger.error("Failed to fetch required market data")
            return None
        
        # Calculate indicators
        swing_high, swing_low = self.calculate_swing_levels(df_m15)
        sma_m15 = self.calculate_sma(df_m15)
        sma_h4 = self.calculate_sma(df_h4)
        atr = self.calculate_atr(df_m15)
        
        if None in [swing_high, swing_low, sma_m15, sma_h4, atr]:
            logger.warning("Insufficient data for indicator calculation")
            return None
        
        # Determine trend direction
        current_price = df_m15['close'].iloc[-1]
        m15_trend = "BULLISH" if current_price > sma_m15 else "BEARISH"
        h4_trend = "BULLISH" if current_price > sma_h4 else "BEARISH"
        
        # Check for alignment
        trend_aligned = (m15_trend == h4_trend)
        
        # Detect swing levels proximity
        proximity_to_swing_high = abs(current_price - swing_high) / swing_high if swing_high != 0 else float('inf')
        proximity_to_swing_low = abs(current_price - swing_low) / swing_low if swing_low != 0 else float('inf')
        
        # Generate signal based on breakout/pullback logic
        signal = None
        reason = ""
        
        # Bullish breakout above swing high
        if (current_price > swing_high and 
            df_m15['close'].iloc[-2] <= swing_high and  # Previous candle was at or below swing high
            trend_aligned and 
            m15_trend == "BULLISH"):
            signal = "BUY"
            reason = f"Bullish breakout above swing high ({swing_high:.2f}) with {m15_trend} trend alignment"
        
        # Bearish breakout below swing low
        elif (current_price < swing_low and 
              df_m15['close'].iloc[-2] >= swing_low and  # Previous candle was at or above swing low
              trend_aligned and 
              m15_trend == "BEARISH"):
            signal = "SELL"
            reason = f"Bearish breakout below swing low ({swing_low:.2f}) with {m15_trend} trend alignment"
        
        # Bullish pullback to swing low in uptrend
        elif (proximity_to_swing_low < 0.002 and  # Within 0.2% of swing low
              h4_trend == "BULLISH" and
              m15_trend == "BULLISH" and
              df_m15['close'].iloc[-1] > df_m15['open'].iloc[-1]):  # Bullish candle
            signal = "BUY"
            reason = f"Bullish pullback to swing low ({swing_low:.2f}) in {h4_trend} H4 trend"
        
        # Bearish pullback to swing high in downtrend
        elif (proximity_to_swing_high < 0.002 and  # Within 0.2% of swing high
              h4_trend == "BEARISH" and
              m15_trend == "BEARISH" and
              df_m15['close'].iloc[-1] < df_m15['open'].iloc[-1]):  # Bearish candle
            signal = "SELL"
            reason = f"Bearish pullback to swing high ({swing_high:.2f}) in {h4_trend} H4 trend"
        
        if signal is None:
            return None
        
        # Calculate trade parameters
        entry_price = current_price
        if signal == "BUY":
            stop_loss = entry_price - (SL_MULTIPLIER * atr)
            take_profit = entry_price + (TP_MULTIPLIER * (entry_price - stop_loss))
        else:  # SELL
            stop_loss = entry_price + (SL_MULTIPLIER * atr)
            take_profit = entry_price - (TP_MULTIPLIER * (stop_loss - entry_price))
        
        # Risk calculation (simplified - would need account info for exact position size)
        risk_amount = abs(entry_price - stop_loss)
        
        result = {
            "signal": signal,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "atr": atr,
            "swing_high": swing_high,
            "swing_low": swing_low,
            "sma_m15": sma_m15,
            "sma_h4": sma_h4,
            "m15_trend": m15_trend,
            "h4_trend": h4_trend,
            "trend_aligned": trend_aligned,
            "reason": reason,
            "timestamp": datetime.utcnow(),
            "risk_amount": risk_amount
        }
        
        logger.info(f"Market Intelligence Signal: {signal} {INSTRUMENT} at {entry_price:.2f}")
        logger.info(f"Reason: {reason}")
        
        return result