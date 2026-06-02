# Quick Start Guide

Get the AI Trading Agent running in 5 minutes.

## 1️⃣ Installation (2 minutes)

```bash
# Clone repository
git clone <repo>
cd ai-trading-agent

# Run setup
bash setup.sh
```

This will:
- ✅ Check Python version
- ✅ Copy .env.example to .env
- ✅ Install dependencies
- ✅ Download NLTK data
- ✅ Initialize database

## 2️⃣ Configuration (2 minutes)

Edit `.env` file with your credentials:

```bash
nano .env
```

**Required settings:**
```
# MetaTrader 5
MT5_LOGIN=your_mt5_login
MT5_PASSWORD=your_mt5_password
MT5_SERVER=MetaQuotes-Demo

# Telegram
TELEGRAM_TOKEN=your_telegram_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Webhook Security
WEBHOOK_SECRET=super_secret_key_32_chars_long
```

### How to get credentials

**MT5 Account:**
1. Download MetaTrader 5
2. Demo account → auto-created on first login
3. Login credentials shown in terminal

**Telegram Token:**
1. Open Telegram, find @BotFather
2. Send `/newbot`
3. Copy the token provided

**Telegram Chat ID:**
1. Message your new bot
2. Run: `curl https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Find your `chat_id` in response

## 3️⃣ Start Server (1 minute)

```bash
# Terminal 1: Start the trading agent
cd backend
python main.py
```

You should see:
```
✅ Database initialized
✅ MT5 connected
✅ All agents initialized
📊 Listening on 0.0.0.0:8000
```

## 4️⃣ Test It Works (Optional)

```bash
# Terminal 2: Send test signal
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "EURUSD",
    "action": "BUY",
    "price": 1.0950,
    "time": "2024-01-15T10:30:00Z"
  }'
```

You should see in agent terminal:
```
✅ Webhook received: EURUSD BUY
Running Chart Agent
Running News Agent
Running Memory Agent
Running Decision Engine
```

And a Telegram message from your bot!

## 5️⃣ Connect TradingView

1. Create any chart alert in TradingView
2. Go to "Alert Settings"
3. Select "Webhook URL"
4. Enter: `http://your-server:8000/webhook` (or public URL if deployed)
5. Message body:
   ```json
   {
     "symbol": "{{symbol}}",
     "action": "{{strategy.order.action}}",
     "price": "{{close}}",
     "time": "{{time}}"
   }
   ```
6. Click "Create Alert"

Now trading signals will flow to your agent!

## 🚀 Deploy to Cloud (Optional)

### Docker (Recommended)

```bash
docker-compose up -d
```

### Railway.app (Easiest)

1. Push to GitHub
2. Go to Railway.app
3. Click "New Project" → "Deploy from GitHub"
4. Select your repo
5. Add env variables from `.env`
6. Get public URL

Done! Use as your TradingView webhook: `https://your-railway-url.up.railway.app/webhook`

## 📊 Monitor Your System

**Check health:**
```bash
curl http://localhost:8000/health
```

**View statistics:**
```bash
curl http://localhost:8000/stats
```

**View open trades:**
```bash
curl http://localhost:8000/trades/open
```

**View trade history:**
```bash
curl http://localhost:8000/trades/history?limit=10
```

Or use Telegram commands:
- `/status` - Current market conditions
- `/stats` - Overall win rate and P&L
- `/history` - Last 10 closed trades
- `/stop` - Disable trading signals
- `/start` - Enable trading signals

## ⚙️ Customization

Edit these files to customize strategy:

**Trading Parameters** (`config.py`):
```python
RISK_PER_TRADE = 0.02        # 2% per trade
MIN_REWARD_RATIO = 2.0        # 1:2 minimum R:R
MAX_CONCURRENT_POSITIONS = 3  # Max open trades
```

**Agent Weights** (how much each agent matters):
```python
CHART_AGENT_WEIGHT = 0.40    # 40% technical analysis
NEWS_AGENT_WEIGHT = 0.30     # 30% news sentiment
MEMORY_AGENT_WEIGHT = 0.30   # 30% historical performance
```

**Decision Thresholds**:
```python
STRONG_SIGNAL_THRESHOLD = 75  # Score to EXECUTE
WEAK_SIGNAL_THRESHOLD = 50    # Score to WAIT
AVOID_SIGNAL_THRESHOLD = 25   # Score to REJECT
```

## 🛠️ Useful Commands

```bash
# View logs
tail -f backend/main.py.log

# Test webhook
make health-check

# Reset database
make db-reset

# Run tests
pytest tests/ -v

# Clean cache
make clean

# Stop server
Ctrl+C

# Check what's running
lsof -i :8000
```

## 🐛 Troubleshooting

**Q: "MT5 initialization failed"**
- A: Check MT5 is installed and credentials in .env are correct

**Q: "Telegram bot not configured"**
- A: Verify TELEGRAM_TOKEN and TELEGRAM_CHAT_ID in .env

**Q: "No data received from MT5"**
- A: Check internet connection and that your MT5 account is active

**Q: "Webhook not receiving signals"**
- A: Test with `curl` command above. Check firewall settings.

**Q: "Database locked"**
- A: Another process is using the DB. Restart the server.

See [DEPLOYMENT.md](DEPLOYMENT.md) for more detailed troubleshooting.

## 📚 Next Steps

1. **Read the Strategy**: See [README.md](README.md) for full strategy details
2. **Backtest**: Test strategy on historical data before live trading
3. **Paper Trade**: Start with demo account to verify signals
4. **Go Live**: Once confident, connect to real trading account
5. **Monitor**: Watch /stats and /history daily

## 💡 Best Practices

- ✅ Start with DEMO account, not real money
- ✅ Use stop losses on ALL trades
- ✅ Never risk more than 2% per trade
- ✅ Keep logs of all trades for analysis
- ✅ Adjust strategy based on win rate
- ✅ Monitor system health daily
- ✅ Have backup plan if system fails

## 📞 Support

- Check logs: `tail -f backend/main.py.log`
- Test API: `curl http://localhost:8000/health`
- Check DB: `sqlite3 data/trades.db "SELECT COUNT(*) FROM trades"`
- Ask in Discord/GitHub issues

---

**Happy Trading! 🚀**

Now that you're set up, go make some trades. And remember: **"In the long run, the market is a weighing machine." - Benjamin Graham**
