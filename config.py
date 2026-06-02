import os
from dotenv import load_dotenv

load_dotenv()

# MT5 Configuration
MT5_LOGIN = os.getenv("MT5_LOGIN", "12345678")
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "password")
MT5_SERVER = os.getenv("MT5_SERVER", "MetaQuotes-Demo")

# Telegram Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Webhook Configuration
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "trading_secret_key")
FASTAPI_HOST = os.getenv("FASTAPI_HOST", "0.0.0.0")
FASTAPI_PORT = int(os.getenv("FASTAPI_PORT", 8000))

# Trading Configuration
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", 0.02))  # 2% per trade
MIN_REWARD_RATIO = float(os.getenv("MIN_REWARD_RATIO", 2.0))  # 1:2 RR minimum
MAX_CONCURRENT_POSITIONS = int(os.getenv("MAX_CONCURRENT_POSITIONS", 3))
ACCOUNT_BALANCE = float(os.getenv("ACCOUNT_BALANCE", 10000))  # Starting balance

# Agent Weights (Decision Engine)
CHART_AGENT_WEIGHT = float(os.getenv("CHART_AGENT_WEIGHT", 0.40))
NEWS_AGENT_WEIGHT = float(os.getenv("NEWS_AGENT_WEIGHT", 0.30))
MEMORY_AGENT_WEIGHT = float(os.getenv("MEMORY_AGENT_WEIGHT", 0.30))

# Decision Thresholds
STRONG_SIGNAL_THRESHOLD = float(os.getenv("STRONG_SIGNAL_THRESHOLD", 75))
WEAK_SIGNAL_THRESHOLD = float(os.getenv("WEAK_SIGNAL_THRESHOLD", 50))
AVOID_SIGNAL_THRESHOLD = float(os.getenv("AVOID_SIGNAL_THRESHOLD", 25))

# Support & Resistance Configuration
SR_LOOKBACK_CANDLES = int(os.getenv("SR_LOOKBACK_CANDLES", 50))

# Trend Configuration
TREND_SMA_FAST = int(os.getenv("TREND_SMA_FAST", 50))
TREND_SMA_SLOW = int(os.getenv("TREND_SMA_SLOW", 200))

# ATR Configuration
ATR_PERIOD = int(os.getenv("ATR_PERIOD", 14))
ATR_MULTIPLIER = float(os.getenv("ATR_MULTIPLIER", 2.0))

# Database Configuration
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "data", "trades.db"))

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Trading Timeframes
TIMEFRAMES = {
    "M5": 5,      # 5-minute (entry timing)
    "M15": 15,    # 15-minute (confirmation)
    "M30": 30,    # 30-minute (structure)
    "H4": 240,    # 4-hour (trend bias)
}

# News Feed Configuration
NEWS_FEED_URLS = [
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://feeds.finance.yahoo.com/rss/2.0/headline",
    "http://feeds.reuters.com/reuters/businessNews",
]

# Cache TTL (seconds)
NEWS_CACHE_TTL = 3600  # 1 hour
