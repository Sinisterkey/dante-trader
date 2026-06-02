import logging
import asyncio
import json
import imaplib
import email
import sys
import os
from datetime import datetime
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# Ensure the root directory is in the path for module imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import (
    FASTAPI_HOST, FASTAPI_PORT, LOG_LEVEL,
    EMAIL_SIGNALS_ENABLED, IMAP_SERVER, IMAP_USER, IMAP_PASSWORD,
    IMAP_FOLDER, EMAIL_CHECK_INTERVAL
)
from backend.db import TradingDatabase
from backend.mt5_connector import MT5Connector
from backend.chart_agent import ChartAgent
from backend.news_agent import NewsAgent
from backend.memory_agent import MemoryAgent
from backend.decision_engine import DecisionEngine
from backend.risk_manager import RiskManager
from backend.webhook import WebhookValidator, SignalProcessor
from telegram_handlers.bot import TradingTelegramBot

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trading_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global instances
db = None
mt5 = None
chart_agent = None
news_agent = None
memory_agent = None
decision_engine = None
risk_manager = None
signal_processor = None
telegram_bot = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global db, mt5, chart_agent, news_agent, memory_agent, decision_engine, risk_manager, signal_processor, telegram_bot

    # Startup
    logger.info("🚀 Starting Trading Agent System")
    
    # Initialize database
    db = TradingDatabase()
    logger.info("✅ Database initialized")

    # Initialize MT5
    mt5 = MT5Connector()
    if not mt5.is_connected():
        logger.warning("⚠️ MT5 connection failed - system may not function properly")

    # Initialize agents
    chart_agent = ChartAgent()
    news_agent = NewsAgent()
    memory_agent = MemoryAgent(db)
    decision_engine = DecisionEngine()
    risk_manager = RiskManager(db)
    logger.info("✅ All agents initialized")

    # Initialize signal processor
    signal_processor = SignalProcessor(
        mt5, chart_agent, news_agent, memory_agent,
        decision_engine, risk_manager, db
    )

    # Initialize Telegram bot
    telegram_bot = TradingTelegramBot(db)
    try:
        await telegram_bot.start_bot()
    except Exception as e:
        logger.warning(f"Telegram bot initialization error: {e}")

    # Start email signal listener if enabled
    if EMAIL_SIGNALS_ENABLED:
        asyncio.create_task(email_signal_listener())

    if telegram_bot:
        from config import TELEGRAM_CHAT_ID
        logger.info(f"🤖 Bot is listening for Chat ID: {TELEGRAM_CHAT_ID}")

    logger.info("✅ Trading Agent System ready!")
    logger.info(f"📊 Listening on {FASTAPI_HOST}:{FASTAPI_PORT}")

    yield

    # Shutdown
    logger.info("🛑 Shutting down Trading Agent System")
    
    if mt5:
        mt5.disconnect()
    
    if telegram_bot:
        await telegram_bot.stop_bot()
    
    logger.info("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="AI Trading Agent",
    description="Multi-agent trading system with technical analysis and sentiment",
    version="1.0.0",
    lifespan=lifespan
)


# ==================== ENDPOINTS ====================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "mt5_connected": mt5.is_connected() if mt5 else False,
        "open_trades": len(db.get_open_trades()) if db else 0
    }


@app.post("/webhook")
async def webhook_endpoint(request: Request, x_signature: str = Header(None)):
    """TradingView webhook endpoint.
    
    Expected POST body:
    {
        "symbol": "EURUSD",
        "action": "BUY",
        "price": 1.0950,
        "time": "2024-01-15T10:30:00Z"
    }
    """
    try:
        # Get request body
        body = await request.body()
        body_str = body.decode('utf-8')

        # Validate signature
        if x_signature:
            if not WebhookValidator.validate_signature(body_str, x_signature):
                logger.warning("Webhook signature validation failed")
                raise HTTPException(status_code=401, detail="Invalid signature")

        # Parse JSON
        data = json.loads(body_str)

        # Parse signal
        signal = WebhookValidator.parse_webhook_signal(data)
        if not signal:
            raise HTTPException(status_code=400, detail="Invalid signal format")

        logger.info(f"✅ Webhook received: {signal['symbol']} {signal['action']}")

        # Process signal asynchronously
        asyncio.create_task(process_signal_async(signal))

        return {
            "status": "received",
            "symbol": signal["symbol"],
            "action": signal["action"],
            "message": "Signal queued for processing"
        }

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get trading statistics."""
    try:
        if not memory_agent:
            return {"error": "System not initialized"}

        stats = memory_agent.get_summary_stats()
        open_trades = db.get_open_trades()

        return {
            "total_trades": stats.get("total_trades", 0),
            "total_wins": stats.get("total_wins", 0),
            "total_losses": stats.get("total_losses", 0),
            "win_rate": stats.get("win_rate", 0),
            "avg_pnl": stats.get("avg_pnl", 0),
            "total_pnl": stats.get("total_pnl", 0),
            "open_positions": len(open_trades),
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trades/open")
async def get_open_trades():
    """Get all open trades."""
    try:
        trades = db.get_open_trades()
        return {
            "count": len(trades),
            "trades": trades,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting open trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/trades/history")
async def get_trade_history(limit: int = 50, symbol: str = None):
    """Get closed trade history."""
    try:
        trades = db.get_closed_trades(symbol=symbol, limit=limit)
        return {
            "count": len(trades),
            "trades": trades,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting trade history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== HELPERS ====================

async def email_signal_listener():
    """Background task to poll email for TradingView signals."""
    logger.info("📧 Email signal listener active")
    
    while True:
        try:
            def fetch_emails():
            def fetch_emails_from_imap():
                signals = []
                try:
                    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
                    mail.login(IMAP_USER, IMAP_PASSWORD)
                    mail.login(IMAP_USER, IMAP_PASSWORD.replace(" ", ""))
                    mail.select(IMAP_FOLDER)
                    
                    # Search for unread emails from TradingView
                    status, messages = mail.search(None, '(UNSEEN FROM "noreply@tradingview.com")')
                    
                    if status == 'OK':
                        for num in messages[0].split():
                            status, data = mail.fetch(num, '(RFC822)')
                            if status == 'OK':
                                msg = email.message_from_bytes(data[0][1])
                                body = ""
                                if msg.is_multipart():
                                    for part in msg.walk():
                                        if part.get_content_type() == "text/plain":
                                            body = part.get_payload(decode=True).decode()
                                            break
                                else:
                                    body = msg.get_payload(decode=True).decode()
                                
                                # Extract JSON from email body
                                try:
                                    start = body.find('{')
                                    end = body.rfind('}') + 1
                                    if start != -1 and end != -1:
                                        signals.append(json.loads(body[start:end]))
                                except Exception as e:
                                    logger.error(f"Failed to parse signal from email body: {e}")
                    mail.close()
                    mail.logout()
                except Exception as e:
                    logger.error(f"IMAP Error: {e}")
                    logger.error(f"📧 IMAP Error: {e}")
                return signals

            new_signals = await asyncio.to_thread(fetch_emails)
            new_signals = await asyncio.to_thread(fetch_emails_from_imap)
            if new_signals:
                logger.info(f"📧 Found {len(new_signals)} new signals via email")

            for signal_data in new_signals:
                signal = WebhookValidator.parse_webhook_signal(signal_data)
                if signal:
                    logger.info(f"📧 Signal received via email: {signal['symbol']} {signal['action']}")
                    asyncio.create_task(process_signal_async(signal))
        except Exception as e:
            logger.error(f"Email loop error: {e}")
        await asyncio.sleep(EMAIL_CHECK_INTERVAL)

async def process_signal_async(signal: dict):
    """Process signal asynchronously."""
    try:
        if not signal_processor:
            logger.error("Signal processor not initialized")
            return

        # Check if trading is enabled in Telegram bot
        if telegram_bot and not telegram_bot.trading_enabled:
            logger.info("Trading disabled via Telegram /stop command")
            await telegram_bot.send_status_update(f"Trading disabled. Signal received for {signal['symbol']} but not processed.")
            return

        # Process signal
        result = await signal_processor.process_signal(signal)

        # Send alerts
        if result["status"] == "PROCESSED":
            decision = result.get("decision", {})

            # Send signal alert
            await telegram_bot.send_signal_alert(signal, decision)

            # Send trade alert if executed
            if result.get("trade_id"):
                trade = db.get_trade_by_id(result["trade_id"])
                if trade:
                    await telegram_bot.send_trade_alert(trade)

        elif result["status"] == "ERROR":
            await telegram_bot.send_error_alert(f"Signal processing error: {result.get('reason', 'Unknown')}")

    except Exception as e:
        logger.error(f"Error in async signal processing: {e}")
        if telegram_bot:
            await telegram_bot.send_error_alert(f"System error: {str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    if mt5:
        mt5.disconnect()
    if telegram_bot:
        await telegram_bot.stop_bot()


# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting FastAPI server on {FASTAPI_HOST}:{FASTAPI_PORT}")

    uvicorn.run(
        app,
        host=FASTAPI_HOST,
        port=FASTAPI_PORT,
        log_level=LOG_LEVEL.lower()
    )
