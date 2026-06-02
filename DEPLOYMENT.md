# Deployment Guide

## Table of Contents
- [Local Deployment](#local-deployment)
- [Docker Deployment](#docker-deployment)
- [Railway.app](#railwayapp)
- [Render.com](#rendercom)
- [Replit](#replit)
- [Troubleshooting](#troubleshooting)

## Local Deployment

### Prerequisites
- Python 3.9+
- MetaTrader 5 terminal installed
- Active MT5 demo account
- Telegram bot token

### Steps

1. **Clone repository**
   ```bash
   git clone <repo>
   cd ai-trading-agent
   ```

2. **Run setup script**
   ```bash
   bash setup.sh
   ```

3. **Configure .env**
   ```bash
   nano .env
   # Fill in your credentials
   ```

4. **Start server**
   ```bash
   cd backend
   python main.py
   ```

5. **Test webhook**
   ```bash
   curl -X POST http://localhost:8000/webhook \
     -H "Content-Type: application/json" \
     -d '{
       "symbol": "EURUSD",
       "action": "BUY",
       "price": 1.0950
     }'
   ```

## Docker Deployment

### Prerequisites
- Docker and Docker Compose installed

### Steps

1. **Create .env file**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Build and start**
   ```bash
   docker-compose up -d
   ```

3. **View logs**
   ```bash
   docker-compose logs -f trading-agent
   ```

4. **Stop**
   ```bash
   docker-compose down
   ```

## Railway.app

### Prerequisites
- GitHub account with repository
- Railway.app account (free)

### Steps

1. **Push to GitHub**
   ```bash
   git push origin main
   ```

2. **Create Railway project**
   - Go to https://railway.app
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your repository

3. **Configure variables**
   - In Railway dashboard, go to Variables
   - Add all variables from .env:
     - MT5_LOGIN
     - MT5_PASSWORD
     - MT5_SERVER
     - TELEGRAM_TOKEN
     - TELEGRAM_CHAT_ID
     - WEBHOOK_SECRET
     - RISK_PER_TRADE
     - etc.

4. **Set start command**
   - In Settings, set:
     - Start Command: `python backend/main.py`
     - Watch Paths: (leave empty)

5. **Deploy**
   - Click "Deploy"
   - Get public URL from Service settings
   - Use as TradingView webhook: `https://your-railway-url.up.railway.app/webhook`

### Railway Console Access
```bash
railway login
railway link
railway up
```

## Render.com

### Prerequisites
- GitHub account with repository
- Render.com account (free)

### Steps

1. **Create Web Service**
   - Go to https://render.com
   - Click "New +"
   - Select "Web Service"
   - Connect GitHub repo

2. **Configure service**
   - Name: `ai-trading-agent`
   - Runtime: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python backend/main.py`
   - Plan: Free

3. **Add environment variables**
   - Click "Environment"
   - Add all variables from .env

4. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment
   - Get URL from service dashboard
   - Use as TradingView webhook

## Replit

### Prerequisites
- Replit.com account (free)

### Steps

1. **Import from GitHub**
   - Go to https://replit.com
   - Click "+" or "Create"
   - Select "Import from GitHub"
   - Paste your repository URL

2. **Configure .replit**
   ```toml
   run = "python backend/main.py"
   
   [env]
   PYTHONUNBUFFERED = "1"
   ```

3. **Add secrets**
   - Click lock icon on left
   - Add all variables from .env:
     - MT5_LOGIN
     - MT5_PASSWORD
     - etc.

4. **Run**
   - Click "Run" button
   - Copy URL: `https://your-replit-url.repl.co`
   - Use as TradingView webhook

### Keep Replit Always On
- Subscribe to Replit Pro (optional) for always-on
- Or use a cron service to ping the URL every 5 minutes

## Troubleshooting

### MT5 Connection Failed
```
Error: "MT5 initialization failed"
```

**Solutions:**
- Ensure MetaTrader 5 is installed
- Check MT5_LOGIN and MT5_PASSWORD in .env
- Verify MT5_SERVER is correct (usually "MetaQuotes-Demo")
- MT5 demo accounts reset after 90 days - create a new one if needed

### Telegram Bot Not Responding
```
Error: "Telegram bot not configured"
```

**Solutions:**
- Verify TELEGRAM_TOKEN is correct
- Get TELEGRAM_CHAT_ID by:
  1. Send `/start` to your bot
  2. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
  3. Look for your chat ID in the response
- Paste correct ID in TELEGRAM_CHAT_ID

### Webhook Not Receiving Signals
```
No POST data reaching /webhook endpoint
```

**Solutions:**
- Check webhook URL is accessible: `curl https://your-url.com/health`
- Verify TradingView webhook URL is correct
- Check firewall/network restrictions
- Enable CORS if needed (modify main.py)
- Test with: `curl -X POST https://your-url.com/webhook -H "Content-Type: application/json" -d '{"symbol":"EURUSD","action":"BUY","price":1.0950}'`

### Database Permission Error
```
sqlite3.OperationalError: attempt to write a readonly database
```

**Solutions:**
- In Docker: ensure `/app/data` is writable
- Locally: check `data/` directory permissions
- Fix with: `chmod 755 data/`

### Out of Memory
```
MemoryError or process killed (free tier limits)
```

**Solutions:**
- Reduce historical candles in MT5 fetch (from 100 to 50)
- Limit concurrent articles in news agent
- Disable news agent temporarily
- Upgrade to paid tier if needed

### Logs Not Showing
```
No output visible in deployment
```

**Solutions:**
- Check LOG_LEVEL is set to INFO or DEBUG
- View persistent logs:
  - Railway: `railway logs -f`
  - Render: Dashboard logs
  - Docker: `docker logs trading-agent -f`

## Performance Tips

### Optimize for Free Tier

1. **Reduce data fetching**
   - Fetch fewer bars: `fetch_multi_timeframe(symbol, bars=50)` instead of 100

2. **Cache news articles**
   - Default TTL is 1 hour - increase if needed

3. **Batch database queries**
   - Use transactions for multiple writes

4. **Monitor memory**
   - Restart daily with cron job if needed

5. **Optimize timeframe analysis**
   - Skip 5M if only doing 4H analysis

## Monitoring & Alerts

### Set up uptime monitoring
- Use Uptimerobot.com (free)
- Monitor: `https://your-url.com/health`
- Alert on failure via Telegram

### Log aggregation (optional)
- Sentry.io for error tracking (free tier)
- LogRocket for session replay
- Papertrail for log storage

## Security Best Practices

1. **Webhook Secret**
   - Use a strong random secret (32+ chars)
   - Include in TradingView webhook headers if possible

2. **Environment Variables**
   - Never commit .env to git
   - Use service provider's secret management
   - Rotate tokens quarterly

3. **Database Backups**
   - Regular SQLite exports: `cp data/trades.db data/trades.backup.db`
   - Store backups securely

4. **Rate Limiting**
   - Consider adding rate limiting for webhook
   - Limit Telegram bot commands per user

## Scaling Considerations

For larger deployment (multiple symbols, many signals):

1. **Upgrade Database**
   - Consider PostgreSQL for multi-user
   - Add connection pooling

2. **Distribute Processing**
   - Use Redis for signal queue
   - Celery for async task processing

3. **Load Balancing**
   - Multiple instances behind nginx
   - Sticky sessions for Telegram state

4. **Paid Alternatives**
   - AWS Lambda for serverless
   - Google Cloud Run
   - DigitalOcean for dedicated VM

---

**Questions?** Check logs with `-v` flag or open an issue on GitHub.
