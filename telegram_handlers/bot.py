import logging
from typing import Optional
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
from backend.db import TradingDatabase
from backend.memory_agent import MemoryAgent

logger = logging.getLogger(__name__)


class TradingTelegramBot:
    """Telegram bot for trading control and notifications."""

    def __init__(self, db: TradingDatabase):
        self.db = db
        self.memory_agent = MemoryAgent(db)
        self.token = TELEGRAM_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self.bot = Bot(token=self.token) if self.token else None
        self.trading_enabled = True
        self.app = None

    async def start_bot(self):
        """Start the Telegram bot."""
        if not self.token or not self.chat_id:
            logger.warning("Telegram bot not configured (missing token or chat_id)")
            return

        try:
            self.app = Application.builder().token(self.token).build()

            # Add command handlers
            self.app.add_handler(CommandHandler("start", self.handle_start))
            self.app.add_handler(CommandHandler("stop", self.handle_stop))
            self.app.add_handler(CommandHandler("status", self.handle_status))
            self.app.add_handler(CommandHandler("history", self.handle_history))
            self.app.add_handler(CommandHandler("stats", self.handle_stats))

            # Start polling
            await self.app.initialize()
            await self.app.start()
            logger.info("Telegram bot started successfully")

        except Exception as e:
            logger.error(f"Error starting Telegram bot: {e}")

    async def stop_bot(self):
        """Stop the Telegram bot."""
        try:
            if self.app:
                await self.app.stop()
                logger.info("Telegram bot stopped")
        except Exception as e:
            logger.error(f"Error stopping Telegram bot: {e}")

    # ==================== COMMAND HANDLERS ====================

    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        self.trading_enabled = True
        message = "✅ Trading signals ENABLED\n\n"
        message += "The system will now send trading alerts. Use /stop to disable."
        await update.message.reply_text(message)

    async def handle_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command."""
        self.trading_enabled = False
        message = "🛑 Trading signals DISABLED\n\n"
        message += "The system will not execute any trades. Use /start to re-enable."
        await update.message.reply_text(message)

    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        try:
            trading_status = "🟢 ENABLED" if self.trading_enabled else "🔴 DISABLED"
            message = f"📊 TRADING STATUS\n\n"
            message += f"Trading: {trading_status}\n"

            # Get market info
            message += "\nNo live market data available in demo mode.\n"

            # Get open positions
            open_trades = self.db.get_open_trades()
            message += f"\n📈 Open Positions: {len(open_trades)}\n"

            if open_trades:
                for trade in open_trades[:3]:  # Show top 3
                    message += f"  • {trade['symbol']} {trade['trade_type']} @ {trade['entry_price']:.5f}\n"

            await update.message.reply_text(message)

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def handle_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /history command."""
        try:
            closed_trades = self.db.get_closed_trades(limit=10)

            message = "📋 RECENT TRADES (Last 10 Closed)\n\n"

            if not closed_trades:
                message += "No closed trades yet."
            else:
                for trade in closed_trades:
                    status_emoji = "✅" if trade['pnl'] > 0 else "❌"
                    message += f"{status_emoji} {trade['symbol']} {trade['trade_type']}\n"
                    message += f"  Entry: {trade['entry_price']:.5f} → {trade['exit_price']:.5f}\n"
                    message += f"  P&L: {trade['pnl']:.2f} ({trade['pnl_percent']:.2f}%)\n\n"

            await update.message.reply_text(message)

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    async def handle_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command."""
        try:
            stats = self.memory_agent.get_summary_stats()

            message = "📊 OVERALL STATISTICS\n\n"
            message += f"Total Trades: {stats.get('total_trades', 0)}\n"
            message += f"Wins: {stats.get('total_wins', 0)}\n"
            message += f"Losses: {stats.get('total_losses', 0)}\n"

            win_rate = stats.get('win_rate', 0)
            message += f"Win Rate: {win_rate*100:.1f}%\n"

            avg_pnl = stats.get('avg_pnl', 0)
            total_pnl = stats.get('total_pnl', 0)
            message += f"Avg P&L: {avg_pnl:.2f}\n"
            message += f"Total P&L: {total_pnl:.2f}\n"

            await update.message.reply_text(message)

        except Exception as e:
            await update.message.reply_text(f"❌ Error: {str(e)}")

    # ==================== ALERTS ====================

    async def send_trade_alert(self, trade_data: dict):
        """Send alert when a trade is opened."""
        if not self.bot or not self.chat_id:
            logger.warning("Telegram bot not configured, skipping alert")
            return

        try:
            message = f"🚀 NEW TRADE OPENED\n\n"
            message += f"Symbol: {trade_data['symbol']}\n"
            message += f"Type: {trade_data['trade_type']}\n"
            message += f"Entry: {trade_data['entry_price']:.5f}\n"
            message += f"Stop Loss: {trade_data['stop_loss']:.5f}\n"
            message += f"Position Size: {trade_data['position_size']:.4f}\n"
            message += f"Risk: {trade_data['risk_amount']:.2f}\n"

            await self.bot.send_message(chat_id=self.chat_id, text=message)
            logger.info(f"Trade alert sent for {trade_data['symbol']}")

        except Exception as e:
            logger.error(f"Error sending trade alert: {e}")

    async def send_signal_alert(self, signal_data: dict, decision_data: dict):
        """Send alert for signal analysis."""
        if not self.bot or not self.chat_id:
            return

        try:
            message = f"📊 SIGNAL ANALYSIS\n\n"
            message += f"Symbol: {signal_data['symbol']}\n"
            message += f"Action: {signal_data['action']}\n"
            message += f"Score: {decision_data['final_score']:.0f}/100\n"
            message += f"Decision: {decision_data['decision']}\n"

            await self.bot.send_message(chat_id=self.chat_id, text=message)

        except Exception as e:
            logger.error(f"Error sending signal alert: {e}")

    async def send_error_alert(self, error_message: str):
        """Send error notification."""
        if not self.bot or not self.chat_id:
            return

        try:
            message = f"⚠️ ERROR\n\n{error_message}"
            await self.bot.send_message(chat_id=self.chat_id, text=message)

        except Exception as e:
            logger.error(f"Error sending error alert: {e}")

    async def send_status_update(self, status_message: str):
        """Send status update."""
        if not self.bot or not self.chat_id:
            return

        try:
            message = f"ℹ️ UPDATE\n\n{status_message}"
            await self.bot.send_message(chat_id=self.chat_id, text=message)

        except Exception as e:
            logger.error(f"Error sending status update: {e}")
