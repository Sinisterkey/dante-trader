import os
from dotenv import load_dotenv

load_dotenv()

# NAS100 Specific Configuration
INSTRUMENT = "NAS100"  # or "^NDX" for NASDAQ index
LOOKBACK_PERIOD = 50   # For swing high/low calculation

# Timeframes (in minutes)
TIMEFRAMES = {
    "M15": 15,   # Primary trading timeframe
    "H4": 240    # Trend filter timeframe
}

# Session Filter: London/NY Overlap (GMT)
SESSION_START_HOUR = 12  # 12:00 GMT
SESSION_END_HOUR = 16    # 16:00 GMT

# Technical Indicators
SMA_PERIOD = 50        # For trend analysis
ATR_PERIOD = 14        # For volatility calculation

# Risk Management
RISK_PER_TRADE = 0.015     # 1.5% of equity per trade
SL_MULTIPLIER = 1.5        # Stop Loss = ATR * SL_MULTIPLIER
TP_MULTIPLIER = 2.5        # Take Profit = Risk * TP_MULTIPLIER

# MT5 Configuration
MT5_LOGIN = os.getenv("MT5_LOGIN", "12345678")
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "password")
MT5_SERVER = os.getenv("MT5_SERVER", "MetaQuotes-Demo")
MT5_TIMEOUT = 60000  # 60 seconds timeout

# Telegram Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Data Fetching
BARS_TO_FETCH = 100    # Number of historical bars to fetch for analysis
UPDATE_INTERVAL = 15   # Seconds between data updates (should match timeframe)

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# File paths
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")