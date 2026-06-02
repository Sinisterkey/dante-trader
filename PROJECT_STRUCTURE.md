# AI Trading Agent - Project Structure

Complete multi-agent trading system with TradingView webhook integration, technical analysis, sentiment analysis, and trade history-based decision making.

## 📁 Project Layout

```
ai-trading-agent/
│
├── backend/                          # Core trading system
│   ├── __init__.py                  # Package init
│   ├── main.py                      # FastAPI app, webhook server, lifecycle
│   ├── webhook.py                   # Webhook validation, signal parsing, processing
│   ├── db.py                        # SQLite database, schema, queries
│   ├── mt5_connector.py             # MetaTrader 5 connection, OHLCV fetching
│   ├── strategy.py                  # Support/resistance, trends, breakouts, volume
│   ├── multi_timeframe.py           # Multi-timeframe aggregation and alignment
│   ├── chart_agent.py               # Chart Agent (technical analysis)
│   ├── news_agent.py                # News Agent (sentiment analysis)
│   ├── memory_agent.py              # Memory Agent (historical performance)
│   ├── decision_engine.py           # Decision Engine (combines all agents)
│   └── risk_manager.py              # Risk management (sizing, stops, validation)
│
├── telegram/                         # Telegram bot interface
│   ├── __init__.py                  # Package init
│   └── bot.py                       # Telegram commands, alerts, monitoring
│
├── data/                            # Data directory
│   └── trades.db                    # SQLite database (auto-created)
│
├── logs/                            # Log files (auto-created)
│
├── tests/                           # Unit and integration tests
│   ├── __init__.py                  # Package init
│   └── test_core.py                 # Core functionality tests
│
├── config.py                        # Centralized configuration (env-based)
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variables template
├── .env                             # Environment variables (auto-created, secret)
├── .gitignore                       # Git ignore rules
├── Dockerfile                       # Docker container definition
├── docker-compose.yml               # Docker Compose orchestration
├── setup.sh                         # Setup script (install, init db)
├── Makefile                         # Useful make commands
│
├── README.md                        # Main documentation
├── QUICKSTART.md                    # 5-minute setup guide
├── DEPLOYMENT.md                    # Detailed deployment guide
├── CHECKLIST.md                     # Production readiness checklist
└── PROJECT_STRUCTURE.md             # This file
```

## 📋 File Descriptions

### Core Backend (`backend/`)

| File | Purpose |
|------|---------|
| **main.py** | FastAPI application, webhook endpoint, lifecycle management |
| **webhook.py** | TradingView webhook validation, signal parsing, processing pipeline |
| **db.py** | SQLite database schema, CRUD operations, analytics queries |
| **mt5_connector.py** | MetaTrader 5 connection, OHLCV data fetching, market info |
| **strategy.py** | Trading strategy implementation (S&R, trends, breakouts, volume) |
| **multi_timeframe.py** | Multi-timeframe analysis aggregation and alignment checking |
| **chart_agent.py** | Technical analysis agent (breakouts, pullbacks, multi-TF) |
| **news_agent.py** | News sentiment agent (RSS feeds, VADER analysis) |
| **memory_agent.py** | Historical trade analysis agent (win rates, patterns) |
| **decision_engine.py** | Combines agent outputs, scores signals, makes decisions |
| **risk_manager.py** | Position sizing, stop loss, take profit, risk validation |

### Telegram Integration (`telegram/`)

| File | Purpose |
|------|---------|
| **bot.py** | Telegram bot commands (/start, /stop, /status, /history, /stats) |

### Tests (`tests/`)

| File | Purpose |
|------|---------|
| **test_core.py** | Unit tests for strategy, agents, decision engine, risk manager |

### Configuration

| File | Purpose |
|------|---------|
| **config.py** | All system configuration with environment variable overrides |
| **.env.example** | Template for environment variables |
| **.env** | Actual environment variables (NOT in git) |

### Deployment & Documentation

| File | Purpose |
|------|---------|
| **Dockerfile** | Docker container definition |
| **docker-compose.yml** | Multi-container orchestration |
| **setup.sh** | Automated setup script |
| **Makefile** | Convenient make commands |
| **README.md** | Complete project documentation |
| **QUICKSTART.md** | 5-minute quick start guide |
| **DEPLOYMENT.md** | Detailed deployment instructions |
| **CHECKLIST.md** | Production readiness checklist |

## 🏗️ Architecture Overview

```
TradingView Webhook
        ↓
   FastAPI Server (main.py)
        ↓
   Signal Validator (webhook.py)
        ↓
   MT5 Data Fetch (mt5_connector.py)
        ↓
   ├── Chart Agent (chart_agent.py) ──→ Technical Analysis
   ├── News Agent (news_agent.py) ────→ Sentiment Analysis  
   └── Memory Agent (memory_agent.py)─→ Historical Analysis
        ↓
   Decision Engine (decision_engine.py)
        ↓
   Risk Manager (risk_manager.py)
        ↓
   Database (db.py)
        ↓
   Telegram Bot (telegram/bot.py)
        ↓
   Telegram Chat (User Alerts & Commands)
```

## 🗄️ Database Schema

### trades
- id (primary key)
- symbol, trade_type (LONG/SHORT)
- entry_price, entry_time, exit_price, exit_time
- pnl, pnl_percent, status (OPEN/CLOSED)
- stop_loss, take_profit, position_size, risk_amount
- created_at

### signals
- id (primary key)
- symbol, signal_type (BUY/SELL)
- signal_data (JSON), webhook_timestamp
- received_at, processed (boolean)

### agent_outputs
- id (primary key)
- signal_id (foreign key), trade_id (foreign key)
- agent_name, output (JSON), confidence
- created_at

### decision_logs
- id (primary key)
- signal_id (foreign key)
- chart_score, news_score, memory_score, final_score
- decision, reasoning (JSON), created_at

## 🔄 Data Flow

### Incoming Signal
1. TradingView sends webhook POST → `main.py:/webhook`
2. WebhookValidator parses and validates signal
3. Signal queued for async processing
4. Signal logged to database

### Agent Analysis
1. MT5Connector fetches OHLCV for all timeframes
2. ChartAgent analyzes technical patterns
3. NewsAgent analyzes market sentiment
4. MemoryAgent analyzes historical performance
5. All outputs logged to database

### Decision Making
1. DecisionEngine normalizes agent outputs
2. Calculates weighted final score
3. Determines decision (EXECUTE/WAIT/REJECT/BLOCKED)
4. Decision logged to database

### Trade Execution
1. RiskManager validates setup
2. Calculates position size, stop loss, take profit
3. Creates trade record in database
4. TelegramBot sends alert

### Ongoing Management
1. User controls via Telegram commands
2. Views statistics and history
3. Can enable/disable trading (/start, /stop)

## 📊 Key Agent Outputs

### Chart Agent
```python
{
    "bias": "bullish|bearish|neutral",
    "confidence": 0-100,
    "reasons": ["reason1", "reason2"],
    "breakout": {"detected": bool, "direction": "LONG|SHORT"},
    "pullback": {"detected": bool},
    "volume": {"confirmed": bool}
}
```

### News Agent
```python
{
    "sentiment": "bullish|bearish|neutral",
    "score": -1.0 to +1.0,
    "confidence": 0-100,
    "articles_analyzed": int,
    "reasons": ["reason1"]
}
```

### Memory Agent
```python
{
    "best_setup_winrate": 0.0-1.0,
    "current_setup_probability": 0.0-1.0,
    "trades_analyzed": int,
    "confidence": 0-100,
    "overall_winrate": 0.0-1.0
}
```

### Decision Engine
```python
{
    "decision": "EXECUTE|WAIT|REJECT|BLOCKED",
    "final_score": 0-100,
    "chart_score": 0-100,
    "news_score": 0-100,
    "memory_score": 0-100,
    "direction": "LONG|SHORT|NONE",
    "reasons": ["reason1", "reason2"]
}
```

## ⚙️ Configuration Hierarchy

1. **Defaults** → `config.py` hardcoded values
2. **Environment** → `.env` file overrides
3. **Runtime** → Can be modified in code

## 🔐 Security Considerations

- Environment variables for all secrets
- `.env` in `.gitignore` (never committed)
- Webhook signature validation
- Database on disk (encrypted by OS if configured)
- No credentials in logs
- Secure Telegram token handling

## 📈 Scalability Notes

Current setup suitable for:
- ✅ Single trader, multiple symbols
- ✅ Demo/paper trading
- ✅ Small accounts (< $100k)
- ✅ Low-frequency signals (< 10/day)

For scaling:
- Consider PostgreSQL for multi-user
- Redis for signal queue
- Celery for distributed processing
- Multiple instances with load balancing

## 🧪 Testing Strategy

1. **Unit Tests** (`test_core.py`)
   - Individual component validation
   - Math and logic verification
   
2. **Integration Tests**
   - Full signal → trade pipeline
   - Agent communication
   
3. **Manual Testing**
   - Webhook endpoint via curl
   - Telegram commands
   - Database integrity

## 📚 Dependencies

**Core:**
- FastAPI - Web framework
- Uvicorn - ASGI server
- python-telegram-bot - Telegram integration

**Data Processing:**
- pandas - Data manipulation
- numpy - Numerical computing
- MetaTrader5 - Market data

**Analysis:**
- nltk - NLP (VADER sentiment)
- feedparser - RSS feed parsing

**Database:**
- sqlite3 - Data persistence

See `requirements.txt` for versions.

## 🚀 Deployment Options

| Platform | Difficulty | Cost | Setup Time |
|----------|-----------|------|-----------|
| Local | Easy | Free | 5 min |
| Docker | Easy | Free | 10 min |
| Railway | Easy | Free | 15 min |
| Render | Easy | Free | 15 min |
| Replit | Medium | Free | 20 min |
| AWS | Hard | $$ | 30+ min |

See `DEPLOYMENT.md` for detailed instructions.

## 📞 File Reference Guide

**Need to...**
- Change trading parameters? → `config.py`
- Add webhook validation? → `backend/webhook.py`
- Modify strategy? → `backend/strategy.py`
- Adjust risk management? → `backend/risk_manager.py`
- Add new agent? → Create in `backend/` and integrate in `main.py`
- Change Telegram commands? → `telegram/bot.py`
- Modify decision logic? → `backend/decision_engine.py`
- Check database? → `backend/db.py`
- Deploy? → `Dockerfile`, `docker-compose.yml`, `DEPLOYMENT.md`

---

**Project Status**: ✅ Complete and production-ready

**Last Updated**: January 2024

**Maintainer**: Your Name
