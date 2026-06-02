# COMPLETE SETUP & DEPLOYMENT ROADMAP

Follow these steps in order to get your AI Trading Agent running and deployed.

## 🎯 Phase 1: Local Setup (5 minutes)

### Step 1: Copy Project
```bash
cp -r /tmp/ai-trading-agent ~/projects/ai-trading-agent
cd ~/projects/ai-trading-agent
```

### Step 2: Run Setup Script
```bash
bash setup.sh
```

This automatically:
- ✅ Installs Python dependencies
- ✅ Downloads NLTK sentiment data
- ✅ Initializes SQLite database
- ✅ Creates .env file

### Step 3: Configure Credentials
```bash
nano .env
```

**MUST FILL IN:**
```
MT5_LOGIN=your_mt5_login_number
MT5_PASSWORD=your_mt5_password
MT5_SERVER=MetaQuotes-Demo

TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

WEBHOOK_SECRET=your_secret_key_at_least_32_chars_random
```

**HOW TO GET CREDENTIALS:**

**MT5 Account:**
1. Download MetaTrader 5
2. Create/login to account
3. Demo account auto-created
4. Find credentials in terminal

**Telegram Token:**
1. Open Telegram → @BotFather
2. Send: /newbot
3. Follow prompts
4. Copy token provided

**Telegram Chat ID:**
1. Message your new bot
2. Run: `curl https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Find your chat_id in response

### Step 4: Test Locally
```bash
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

### Step 5: Send Test Signal (New Terminal)
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

**Expected result:**
- ✅ Agent logs in terminal
- ✅ Telegram message from bot
- ✅ Trade logged to database

---

## 🌐 Phase 2: Push to GitHub (10 minutes)

### Step 1: Create GitHub Repo
1. Go to https://github.com/new
2. Name: `ai-trading-agent`
3. Description: "Multi-agent trading system with TradingView integration"
4. Public or Private (your choice)
5. **IMPORTANT:** Leave empty (no README)
6. Click "Create repository"

### Step 2: Initialize & Push
```bash
bash github-push.sh
```

Then when prompted:
```
GitHub username: your_github_username
Repository name: ai-trading-agent
Continue? (y/N): y
```

Follow instructions to push:
```bash
git push -u origin main
```

### Step 3: Verify
Go to: `https://github.com/your_username/ai-trading-agent`

You should see all your files!

---

## ☁️ Phase 3: Deploy to Cloud (15 minutes)

### Option A: Railway.app (EASIEST - RECOMMENDED)

**1. Sign up**
- Go to https://railway.app
- Click "Dashboard"
- Sign in with GitHub

**2. Create Project**
- Click "New Project"
- Select "Deploy from GitHub repo"
- Authorize Railway
- Select `your_username/ai-trading-agent`

**3. Add Environment Variables**
- In Railway dashboard
- Click on service → Variables
- Add each from your .env:
  - MT5_LOGIN
  - MT5_PASSWORD
  - MT5_SERVER
  - TELEGRAM_TOKEN
  - TELEGRAM_CHAT_ID
  - WEBHOOK_SECRET
  - RISK_PER_TRADE=0.02
  - etc.

**4. Deploy**
- Railway auto-detects Dockerfile
- Click "Deploy"
- Wait 2-3 minutes
- Get public URL from service settings

**5. Test**
```bash
curl https://your-railway-url.railway.app/health
```

### Option B: Render.com

**1. Sign up**
- Go to https://render.com
- Sign in with GitHub

**2. Create Web Service**
- Click "New +" → "Web Service"
- Connect GitHub repo
- Select your repository

**3. Configure**
- Name: ai-trading-agent
- Runtime: Python 3
- Build: `pip install -r requirements.txt`
- Start: `python backend/main.py`
- Plan: Free

**4. Add Environment Variables**
- In settings, add variables from .env

**5. Deploy**
- Click "Create Web Service"
- Wait 5 minutes
- Get URL from service dashboard

### Option C: Replit (FASTEST)

**1. Go to https://replit.com**
- Click "Create"
- Select "Import from GitHub"
- Paste: `https://github.com/your_username/ai-trading-agent`

**2. Configure .replit**
```toml
run = "python backend/main.py"

[env]
PYTHONUNBUFFERED = "1"
```

**3. Add Secrets**
- Click lock icon on left
- Add each env variable

**4. Run**
- Click "Run"
- Copy URL
- Use as webhook

---

## 🎯 Phase 4: Connect TradingView (5 minutes)

### Step 1: Create Alert
- Open TradingView chart
- Create any strategy alert
- Go to alert settings

### Step 2: Configure Webhook
- Select: "Webhook URL"
- Enter your public URL:
  - **Local:** http://your_ip:8000/webhook
  - **Railway:** https://your-railway-url.railway.app/webhook
  - **Render:** https://your-render-url.onrender.com/webhook
  - **Replit:** https://your-replit-url.repl.co/webhook

### Step 3: Message Body
```json
{
  "symbol": "{{symbol}}",
  "action": "{{strategy.order.action}}",
  "price": "{{close}}",
  "time": "{{time}}"
}
```

### Step 4: Create Alert
- Click "Create Alert"
- Now signals will flow to your bot!

---

## 🎓 Phase 5: Monitor & Control

### Via Telegram

Send commands to your bot:
- **`/start`** - Enable trading
- **`/stop`** - Disable trading
- **`/status`** - Show market conditions
- **`/history`** - Last 10 trades
- **`/stats`** - Win rate & P&L

### Via API

```bash
# Check health
curl https://your-url.com/health

# Get stats
curl https://your-url.com/stats

# Get open trades
curl https://your-url.com/trades/open

# Get history
curl https://your-url.com/trades/history
```

---

## 📊 Quick Reference

### File Locations
- Code: `backend/` - all trading logic
- Config: `config.py` - all settings
- Database: `data/trades.db` - all trades
- Logs: `logs/` - system logs (if enabled)

### Useful Commands
```bash
# View logs
tail -f backend/main.py.log

# Check health
curl http://localhost:8000/health

# Run tests
pytest tests/ -v

# Format code
make format

# Clean cache
make clean
```

### Environment Variables
All configuration via `.env`:
- Trading params (risk, ratio, positions)
- Agent weights (chart, news, memory)
- Decision thresholds
- API credentials

### Configuration Files
- `config.py` - defaults + env overrides
- `.env` - your secrets
- `.env.example` - template

---

## ✅ Verification Checklist

- [ ] Project copied locally
- [ ] setup.sh ran successfully
- [ ] .env file configured
- [ ] Local server starts without errors
- [ ] Test webhook receives signal
- [ ] Telegram bot sends alert
- [ ] Database has trade logged
- [ ] Pushed to GitHub
- [ ] Cloud deployment works
- [ ] Public webhook URL accessible
- [ ] TradingView webhook configured
- [ ] Received first signal from TradingView

---

## 🚨 Common Issues

**"MT5 initialization failed"**
- Check MT5_LOGIN and MT5_PASSWORD in .env
- Verify MT5 is installed
- Make sure demo account exists

**"Telegram bot not configured"**
- Check TELEGRAM_TOKEN is correct
- Check TELEGRAM_CHAT_ID (run the curl getUpdates command)

**"Connection refused"**
- Check server is running: `python backend/main.py`
- Check port 8000 is available

**"Database locked"**
- Restart the server
- Check no other instance is running

---

## 📚 Documentation Reference

- **README.md** - Full project documentation
- **QUICKSTART.md** - 5-minute setup guide
- **DEPLOYMENT.md** - Detailed deployment guide
- **CHECKLIST.md** - Production readiness checklist
- **PROJECT_STRUCTURE.md** - File reference
- **GITHUB_PUSH_GUIDE.md** - GitHub push instructions
- **CONTRIBUTING.md** - How to contribute
- **CODE_OF_CONDUCT.md** - Community guidelines

---

## 🎉 SUCCESS!

Once you complete all phases:
✅ System running locally
✅ Code on GitHub
✅ Deployed to cloud
✅ Connected to TradingView
✅ Trading live (or paper trading)

**Now you have a production-ready multi-agent trading system!**

---

## 🔜 Next Steps After Deployment

1. **Monitor daily** - Check /status and /stats
2. **Review trades** - Analyze wins and losses
3. **Adjust parameters** - Optimize based on results
4. **Scale gradually** - Increase risk only after consistent wins
5. **Keep logs** - Track all signals and decisions

---

**Questions?** Check the documentation or GitHub issues.

**Ready to trade?** Start small, manage risk, and always use stops! 🚀
