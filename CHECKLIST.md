# Production Checklist

Use this checklist before deploying to production.

## 🔐 Security

- [ ] Webhook secret is strong (32+ chars, random)
- [ ] `.env` file is NOT committed to git
- [ ] `.gitignore` includes `.env`
- [ ] All API keys/tokens are in environment variables
- [ ] HTTPS enabled for TradingView webhook
- [ ] Rate limiting configured (if applicable)
- [ ] Database permissions are restrictive
- [ ] No hardcoded credentials in code

## 🧪 Testing

- [ ] Health check endpoint responds (GET /health)
- [ ] Webhook receives test signal successfully
- [ ] All three agents return valid outputs
- [ ] Decision engine combines scores correctly
- [ ] Trade is created in database
- [ ] Telegram alerts are sent
- [ ] Trade history retrieval works (GET /trades/history)
- [ ] Statistics endpoint works (GET /stats)

## ⚙️ Configuration

- [ ] MT5 login/password/server configured
- [ ] Telegram token and chat ID correct
- [ ] RISK_PER_TRADE appropriate (1-2% default)
- [ ] MIN_REWARD_RATIO >= 1.5 (minimum 2.0 recommended)
- [ ] MAX_CONCURRENT_POSITIONS suitable for account
- [ ] ACCOUNT_BALANCE reflects real equity
- [ ] Agent weights sum to 1.0 (40% + 30% + 30%)
- [ ] Decision thresholds make sense (75, 50, 25)

## 📊 Data & Database

- [ ] Database initialized (trades.db exists)
- [ ] Database has proper schema (tables created)
- [ ] Database permissions allow read/write
- [ ] Backup plan for database (daily exports)
- [ ] Log rotation configured
- [ ] Historical candle lookback = 50+ (support/resistance)

## 🤖 Agents

### Chart Agent
- [ ] Support/resistance calculation verified
- [ ] Trend detection (SMA50/200) working
- [ ] Breakout detection working
- [ ] Volume analysis functional
- [ ] Confidence scores reasonable (0-100)

### News Agent
- [ ] RSS feeds accessible
- [ ] VADER sentiment analysis initialized
- [ ] Articles filtered by symbol correctly
- [ ] Sentiment scores in -1 to +1 range
- [ ] Cache TTL set appropriately (default 1 hour)

### Memory Agent
- [ ] Database queries working
- [ ] Win rate calculations correct
- [ ] Sample size warnings in place
- [ ] No division by zero errors
- [ ] Confidence modulated by sample size

## 📡 API & Webhooks

- [ ] FastAPI running without errors
- [ ] FASTAPI_HOST and FASTAPI_PORT configured
- [ ] Webhook endpoint accepting POST requests
- [ ] Webhook signature validation (if enabled)
- [ ] CORS configured properly
- [ ] Request body parsing working
- [ ] Error responses are meaningful

## 💬 Telegram Bot

- [ ] Bot token is valid
- [ ] Chat ID is correct
- [ ] Bot can send messages
- [ ] All commands working (/start, /stop, /status, /history, /stats)
- [ ] Trade alerts formatting correct
- [ ] Error alerts are informative
- [ ] No API rate limits being hit

## 🚀 Deployment

### Local
- [ ] Server starts without errors
- [ ] No port conflicts (default 8000)
- [ ] Logging visible in console
- [ ] Graceful shutdown on Ctrl+C
- [ ] Database persists between restarts

### Docker
- [ ] Dockerfile builds successfully
- [ ] Docker image runs without errors
- [ ] Environment variables passed correctly
- [ ] Data volume persists
- [ ] Container restarts on failure
- [ ] Health check responds

### Cloud (Railway/Render/Replit)
- [ ] Repository pushed to GitHub
- [ ] Project created in service
- [ ] Environment variables configured
- [ ] Build succeeds (no timeout)
- [ ] Deployment completes
- [ ] Public URL accessible
- [ ] Health check responds at public URL
- [ ] Webhook accepts signals at public URL

## 📈 Performance & Monitoring

- [ ] MT5 connection stable
- [ ] Signal processing time < 5 seconds
- [ ] Database queries efficient
- [ ] Memory usage stable (no leaks)
- [ ] No excessive CPU usage
- [ ] Network latency acceptable
- [ ] Uptime monitoring configured (optional)
- [ ] Error tracking configured (optional)

## 📋 TradingView Setup

- [ ] Strategy/alert created
- [ ] Webhook URL correct and accessible
- [ ] Message body JSON properly formatted
- [ ] Symbol variable working: `{{symbol}}`
- [ ] Action variable correct: `{{strategy.order.action}}`
- [ ] Price variable correct: `{{close}}`
- [ ] Time variable correct: `{{time}}`
- [ ] Alert triggered at least once successfully

## 📊 Risk Management

- [ ] Stop loss calculation verified
- [ ] Position size formula correct
- [ ] Risk/reward ratio validation working
- [ ] Max concurrent positions respected
- [ ] Trade database logs all entries
- [ ] P&L calculations accurate
- [ ] No trades opened without stop loss

## 📝 Documentation

- [ ] README.md complete and accurate
- [ ] DEPLOYMENT.md has correct instructions
- [ ] QUICKSTART.md tested and working
- [ ] Code comments explain complex logic
- [ ] Environment variables documented
- [ ] API endpoints documented
- [ ] Strategy explained clearly

## 🛡️ Error Handling

- [ ] MT5 disconnection handled gracefully
- [ ] Missing data handled (no crashes)
- [ ] Invalid webhook data rejected
- [ ] Database errors logged
- [ ] Telegram sending failures logged
- [ ] All exceptions caught and logged
- [ ] Meaningful error messages

## 🔄 Backup & Recovery

- [ ] Database backups automated (if applicable)
- [ ] Code version control (GitHub)
- [ ] Configuration backups (env files)
- [ ] Recovery process documented
- [ ] Test recovery at least once

## 📅 Ongoing Maintenance

- [ ] Check system daily:
  - [ ] `/health` endpoint responds
  - [ ] Telegram bot accessible
  - [ ] Recent trades in database
- [ ] Weekly review:
  - [ ] Win rate analysis
  - [ ] P&L trends
  - [ ] Agent accuracy
- [ ] Monthly review:
  - [ ] Strategy adjustments
  - [ ] Parameter tuning
  - [ ] Performance metrics

## 🎯 Pre-Launch Checklist

Before connecting real TradingView signals:

- [ ] Ran through all checks above
- [ ] Paper-traded for at least 1 week
- [ ] Win rate above 50% in testing
- [ ] Risk management validated
- [ ] All agents outputting reasonable scores
- [ ] Database logging all trades
- [ ] Telegram alerts reliable
- [ ] System stable (no crashes in 24+ hours)

## ⚠️ Safety Checks

Before using real account:

- [ ] Account set to DEMO mode (if applicable)
- [ ] Position sizes validated (1-2% risk)
- [ ] Stop losses on ALL trades
- [ ] Maximum drawdown limits in place
- [ ] Can manually close trades if needed
- [ ] Have tested emergency stop process
- [ ] Understand all strategy logic
- [ ] Ready to lose money (worst case)

---

## Sign-Off

- [ ] I have completed all items above
- [ ] I understand the risks
- [ ] System is ready for production
- [ ] Date: _______________
- [ ] Signed by: _______________

---

**Remember**: Start small, scale carefully, always use stops, and never risk more than you can afford to lose.
