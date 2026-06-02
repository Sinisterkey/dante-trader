# AI Trading Agent - Multi-Agent Trading System

A production-ready multi-agent trading assistant system that receives TradingView webhook signals, performs multi-timeframe technical analysis, analyzes news sentiment, evaluates historical trade performance, and makes intelligent trading decisions with full Telegram control.

## 🎯 Features

- **🔌 TradingView Integration**: Webhook endpoint for automated signal reception
- **📊 Multi-Timeframe Analysis**: 5-minute (entry), 15-minute (confirmation), 30-minute (structure), 4-hour (trend bias)
- **🤖 Three Specialized Agents**:
  - **Chart Agent**: Technical analysis (support/resistance, breakouts, pullbacks, volume)
  - **News Agent**: Sentiment analysis from RSS feeds using VADER
  - **Memory Agent**: Historical trade pattern recognition and win rate analysis
- **⚖️ Decision Engine**: Weighted scoring combining all agent outputs
- **💰 Risk Management**: ATR-based stops, position sizing, 1:2+ reward/risk validation
- **🔐 SQLite Database**: Complete trade history and decision logging
- **🤖 Telegram Control**: `/start`, `/stop`, `/status`, `/history`, `/stats` commands
- **☁️ Cloud Ready**: Free tier compatible (Railway, Render, Replit)

## 🛠️ Technology Stack

- **FastAPI** - Webhook server and REST API
- **MetaTrader 5** - Market data (OHLCV for all timeframes)
- **NLTK/VADER** - News sentiment analysis
- **SQLite3** - Trade database and logging
- **python-telegram-bot** - Telegram control and alerts
- **Pandas/NumPy** - Data processing and calculations

## 📦 Installation

### Prerequisites

- Python 3.9+
- MetaTrader 5 terminal (free demo account)
- Telegram bot token (create at @BotFather)
- Free cloud hosting account (optional)

### Local Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo>
   cd ai-trading-agent
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create `.env` file** in project root
   ```
   # MetaTrader 5
   MT5_LOGIN=12345678
   MT5_PASSWORD=your_password
   MT5_SERVER=MetaQuotes-Demo

   # Telegram
   TELEGRAM_TOKEN=your_bot_token_from_botfather
   TELEGRAM_CHAT_ID=your_chat_id

   # Webhook Security
   WEBHOOK_SECRET=your_secret_key_min_32_chars

   # Trading Parameters
   RISK_PER_TRADE=0.02
   MIN_REWARD_RATIO=2.0
   MAX_CONCURRENT_POSITIONS=3
   ACCOUNT_BALANCE=10000

   # Agent Weights
   CHART_AGENT_WEIGHT=0.40
   NEWS_AGENT_WEIGHT=0.30
   MEMORY_AGENT_WEIGHT=0.30

   # API Server
   FASTAPI_HOST=0.0.0.0
   FASTAPI_PORT=8000
   ```

4. **Initialize database and download NLTK data**
   ```bash
   python -c "from backend.db import TradingDatabase; TradingDatabase()"
   python -c "import nltk; nltk.download('vader_lexicon')"
   ```

## 🚀 Running the System

### Local Development

```bash
cd backend
python main.py
```

Server will start on `http://localhost:8000`

Check health: `http://localhost:8000/health`

### Docker (For Cloud Deployment)

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD ["python", "backend/main.py"]
```

Build and run:
```bash
docker build -t trading-agent .
docker run -p 8000:8000 --env-file .env trading-agent
```

## 📡 TradingView Webhook Setup

### In TradingView

1. Create an alert on your chart
2. In alert settings, set notification type to "Webhook URL"
3. Webhook URL: `https://your-domain.com/webhook`
4. Message body (JSON):
   ```json
   {
     "symbol": "{{symbol}}",
     "action": "{{strategy.order.action}}",
     "price": "{{close}}",
     "time": "{{timenow}}"
   }
   ```

### Testing Webhook

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "EURUSD",
    "action": "BUY",
    "price": 1.0950,
    "time": "2024-01-15T10:30:00Z"
  }'
```

## 📊 API Endpoints

### Health Check
```
GET /health
```

Returns system status and MT5 connection.

### Webhook Signal
```
POST /webhook
Content-Type: application/json

{
  "symbol": "EURUSD",
  "action": "BUY",
  "price": 1.0950,
  "time": "2024-01-15T10:30:00Z"
}
```

### Statistics
```
GET /stats
```

Returns overall trading statistics.

### Open Trades
```
GET /trades/open
```

Returns all currently open positions.

### Trade History
```
GET /trades/history?limit=50&symbol=EURUSD
```

Returns closed trades with P&L.

## 🤖 Telegram Commands

After starting the bot with your chat ID:

- **`/start`** - Enable trading signals
- **`/stop`** - Disable trading (no new entries)
- **`/status`** - Show current market conditions
- **`/history`** - Show last 10 closed trades
- **`/stats`** - Show overall statistics (win rate, total P&L, etc.)

## 🧠 How the System Works

### 1. Signal Reception
TradingView webhook sends a BUY/SELL signal → FastAPI `/webhook` endpoint

### 2. Multi-Timeframe Data Fetching
- Connect to MT5
- Fetch 100 bars of OHLCV for 5M, 15M, 30M, 4H timeframes

### 3. Agent Analysis (Parallel)

**Chart Agent**:
- Calculate support/resistance (50-candle range)
- Detect breakouts and pullbacks
- Analyze volume confirmation
- Multi-timeframe trend analysis (SMA50/200)
- Output: bias (bullish/bearish/neutral) + confidence

**News Agent**:
- Fetch RSS feeds (Bloomberg, Reuters, Yahoo Finance)
- Apply VADER sentiment to articles
- Filter by symbol
- Output: sentiment + score (-1 to +1)

**Memory Agent**:
- Query database for similar past trades
- Calculate win rate for this setup
- Analyze P&L patterns
- Output: historical probability + confidence

### 4. Decision Engine
```
final_score = (chart_score × 40%) + (news_score × 30%) + (memory_score × 30%)

if final_score >= 75 → EXECUTE
if final_score >= 50 → WAIT (no entry)
if final_score >= 25 → REJECT (conflicting)
if final_score < 25 → BLOCKED (poor conditions)
```

### 5. Risk Management
- Calculate ATR-based stop loss (2× ATR)
- Calculate position size (1-2% risk)
- Validate 1:2+ reward/risk ratio
- Check max concurrent positions (3)
- Log all trades to SQLite

### 6. Telegram Notifications
- Trade opened alert
- Signal analysis summary
- Error notifications
- Status updates

### 7. Database Logging
- All trades: entry, exit, P&L, timestamps
- All signals: webhook data, timestamp
- Agent outputs: reasoning and confidence
- Decision logs: final score and decision

## 📈 Trading Strategy

### Support & Resistance
- Resistance = highest high of last 50 candles (excluding current)
- Support = lowest low of last 50 candles (excluding current)

### Entry Conditions

**LONG**:
- Price breaks above resistance (5M)
- 15M + 30M trend bullish
- 4H trend bullish (preferred)
- Volume above average
- News sentiment neutral or positive

**SHORT**:
- Price breaks below support (5M)
- 15M + 30M trend bearish
- 4H trend bearish (preferred)
- Volume confirmation
- News sentiment bearish

### Pullback Logic
- Buy when price retests support in bullish trend with upward rejection
- Sell when price retests resistance in bearish trend with downward rejection

### Stop Loss
- ATR-based: entry ± (ATR × 2)

### Risk Management
- Risk per trade: 1-2% of account
- Minimum reward ratio: 1:2
- Max concurrent positions: 3

## 🌐 Cloud Deployment

### Railway.app (Recommended)

1. Create account at railway.app
2. Connect GitHub repo
3. Create `.env` file in dashboard
4. Deploy

```yaml
# railway.toml
[build]
provider = "dockerfile"

[deploy]
startCommand = "python backend/main.py"
```

### Render.com

1. Create account at render.com
2. Create new Web Service
3. Connect GitHub repo
4. Set environment variables
5. Deploy

### Replit

1. Create account at replit.com
2. Import from GitHub
3. Set environment variables in `.replit`
4. Click "Run"

## 📊 Database Schema

### trades
```
id (PK), symbol, trade_type (LONG/SHORT), entry_price, entry_time,
exit_price, exit_time, pnl, pnl_percent, status (OPEN/CLOSED),
stop_loss, take_profit, position_size, risk_amount, created_at
```

### signals
```
id (PK), symbol, signal_type (BUY/SELL), signal_data (JSON),
webhook_timestamp, received_at, processed (BOOL)
```

### agent_outputs
```
id (PK), signal_id (FK), trade_id (FK), agent_name, output (JSON),
confidence, created_at
```

### decision_logs
```
id (PK), signal_id (FK), chart_score, news_score, memory_score,
final_score, decision, reasoning (JSON), created_at
```

## 🔧 Configuration

All settings are in `config.py` with environment variable overrides via `.env`:

### Trading Parameters
- `RISK_PER_TRADE` - Risk per trade (default: 2%)
- `MIN_REWARD_RATIO` - Minimum R:R ratio (default: 2.0)
- `MAX_CONCURRENT_POSITIONS` - Max open trades (default: 3)
- `ACCOUNT_BALANCE` - Starting equity (default: 10000)

### Decision Thresholds
- `STRONG_SIGNAL_THRESHOLD` - Score to EXECUTE (default: 75)
- `WEAK_SIGNAL_THRESHOLD` - Score to WAIT (default: 50)
- `AVOID_SIGNAL_THRESHOLD` - Score to REJECT (default: 25)

### Agent Weights
- `CHART_AGENT_WEIGHT` - Chart importance (default: 40%)
- `NEWS_AGENT_WEIGHT` - News importance (default: 30%)
- `MEMORY_AGENT_WEIGHT` - Memory importance (default: 30%)

## 🧪 Testing

### Unit Tests
```bash
pytest tests/ -v
```

### Manual Signal Testing
```bash
# Send test signal
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "EURUSD",
    "action": "BUY",
    "price": 1.0950,
    "time": "2024-01-15T10:30:00Z"
  }'

# Check system status
curl http://localhost:8000/health

# Get statistics
curl http://localhost:8000/stats
```

## 📝 Logging

Logs are output to console with format:
```
YYYY-MM-DD HH:MM:SS - module_name - LEVEL - message
```

Set log level in `.env`:
```
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

## ⚠️ Limitations & Future Improvements

### Current Limitations
- MT5 demo account may reset after 90 days inactivity
- News sentiment 5-30 min delayed vs real-time
- Single broker connection (MT5 only)
- No position management (scalping, hedging)

### Future Enhancements
- Real-time price alerts instead of polling
- Multiple broker support (Forex.com, IG, etc.)
- Advanced money management (Kelly criterion, Sharpe optimization)
- Backtesting engine
- Pattern recognition (chart patterns, candlestick sequences)
- Advanced sentiment (real-time Twitter, options flow)
- Machine learning for signal optimization

## 🚨 Risk Disclaimer

**This is a trading system for educational purposes. Use at your own risk.**

- Past performance does not guarantee future results
- Forex and trading carry significant risk
- You can lose more than your initial investment
- Always use stop losses and risk management
- Start with small accounts and paper trading
- Monitor the system regularly

## 📞 Support

For issues or questions:
1. Check logs: `docker logs <container_id>`
2. Test webhook: POST to `/webhook` manually
3. Verify `.env` variables: `python -c "from config import *; print(TELEGRAM_TOKEN)"`
4. Check database: `sqlite3 data/trades.db ".tables"`

## 📄 License

MIT License - See LICENSE file

## 🙏 Acknowledgments

- TradingView for webhook signals
- MetaTrader 5 for market data
- VADER Sentiment for NLP analysis
- FastAPI for REST framework
- Telegram for bot API

---

**Built with ❤️ for traders. Trade smart, manage risk, win consistently.**
