import logging
import hmac
import hashlib
from typing import Dict, Optional, Any
from config import WEBHOOK_SECRET

logger = logging.getLogger(__name__)


class WebhookValidator:
    """Validate TradingView webhook signatures."""

    @staticmethod
    def validate_signature(payload: str, signature: str, secret: str = WEBHOOK_SECRET) -> bool:
        """Validate webhook signature using HMAC-SHA256.
        
        Args:
            payload: Raw request body as string
            signature: Signature from request header
            secret: Webhook secret from config
            
        Returns:
            True if signature is valid
        """
        try:
            # Calculate expected signature
            expected_signature = hmac.new(
                secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()

            # Compare signatures
            return hmac.compare_digest(expected_signature, signature)

        except Exception as e:
            logger.error(f"Error validating signature: {e}")
            return False

    @staticmethod
    def parse_webhook_signal(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse TradingView webhook signal.
        
        Expected format:
        {
            "symbol": "EURUSD",
            "action": "BUY" or "SELL",
            "price": 1.0950,
            "time": "2024-01-15T10:30:00Z"
        }
        """
        try:
            signal = {
                "symbol": data.get("symbol", "").upper(),
                "action": data.get("action", "").upper(),
                "price": float(data.get("price", 0)),
                "time": data.get("time", ""),
                "raw_data": data  # Store original data for logging
            }

            # Validate required fields
            if not signal["symbol"]:
                logger.error("Missing symbol in webhook")
                return None

            if signal["action"] not in ["BUY", "SELL"]:
                logger.error(f"Invalid action: {signal['action']}")
                return None

            if signal["price"] <= 0:
                logger.error(f"Invalid price: {signal['price']}")
                return None

            return signal

        except Exception as e:
            logger.error(f"Error parsing webhook signal: {e}")
            return None

    @staticmethod
    def convert_action_to_trade_type(action: str) -> str:
        """Convert BUY/SELL action to LONG/SHORT trade type.
        
        BUY → LONG
        SELL → SHORT
        """
        if action.upper() == "BUY":
            return "LONG"
        elif action.upper() == "SELL":
            return "SHORT"
        return "UNKNOWN"


class SignalProcessor:
    """Process incoming trading signals through the agent pipeline."""

    def __init__(self, mt5_connector, chart_agent, news_agent, memory_agent,
                 decision_engine, risk_manager, db):
        self.mt5 = mt5_connector
        self.chart_agent = chart_agent
        self.news_agent = news_agent
        self.memory_agent = memory_agent
        self.decision_engine = decision_engine
        self.risk_manager = risk_manager
        self.db = db

    async def process_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Process a trading signal through all agents.
        
        Returns:
            {
                "signal_id": int,
                "status": "PROCESSED" | "REJECTED" | "ERROR",
                "decision": {...},
                "trade_id": optional int if trade was opened
            }
        """
        try:
            symbol = signal["symbol"]
            action = signal["action"]
            trade_type = WebhookValidator.convert_action_to_trade_type(action)

            logger.info(f"Processing signal: {symbol} {action}")

            # 1. Log signal to database
            signal_id = self.db.log_signal(symbol, action, signal, signal.get("time", ""))

            # 2. Fetch multi-timeframe data from MT5
            logger.info(f"Fetching MT5 data for {symbol}")
            timeframe_data = self.mt5.fetch_multi_timeframe(symbol, bars=100)

            if not timeframe_data or len(timeframe_data) < 2:
                logger.error(f"Insufficient MT5 data for {symbol}")
                return {
                    "signal_id": signal_id,
                    "status": "REJECTED",
                    "reason": "Unable to fetch market data from MT5"
                }

            # 3. Run Chart Agent
            logger.info("Running Chart Agent")
            chart_output = self.chart_agent.analyze(timeframe_data, symbol)
            self.db.log_agent_output("chart", chart_output, signal_id=signal_id)

            # 4. Run News Agent
            logger.info("Running News Agent")
            news_output = self.news_agent.analyze(symbol)
            self.db.log_agent_output("news", news_output, signal_id=signal_id)

            # 5. Run Memory Agent
            logger.info("Running Memory Agent")
            memory_output = self.memory_agent.analyze(symbol, trade_type)
            self.db.log_agent_output("memory", memory_output, signal_id=signal_id)

            # 6. Decision Engine
            logger.info("Running Decision Engine")
            decision = self.decision_engine.make_decision(chart_output, news_output, memory_output)

            # Log decision
            self.db.log_decision(
                signal_id,
                decision["chart_score"],
                decision["news_score"],
                decision["memory_score"],
                decision["final_score"],
                decision["decision"],
                {"reasons": decision["reasons"]}
            )

            # 7. Risk Management & Trade Opening
            trade_id = None
            if decision["decision"] == "EXECUTE" and decision["direction"] != "NONE":
                logger.info(f"Executing trade: {decision['direction']}")
                trade_result = await self._execute_trade(
                    symbol,
                    decision["direction"],
                    signal["price"],
                    timeframe_data,
                    signal_id
                )
                if trade_result["success"]:
                    trade_id = trade_result["trade_id"]

            return {
                "signal_id": signal_id,
                "status": "PROCESSED",
                "decision": decision,
                "trade_id": trade_id
            }

        except Exception as e:
            logger.error(f"Error processing signal: {e}")
            return {
                "signal_id": None,
                "status": "ERROR",
                "reason": str(e)
            }

    async def _execute_trade(self, symbol: str, direction: str, entry_price: float,
                            timeframe_data: Dict, signal_id: int) -> Dict[str, Any]:
        """Execute a trade with proper risk management.
        
        Returns:
            {
                "success": bool,
                "trade_id": int if successful,
                "reason": str if failed
            }
        """
        try:
            # Check if we can open a position
            if not self.risk_manager.can_open_position():
                return {
                    "success": False,
                    "reason": "Max concurrent positions reached"
                }

            # Get ATR for stop loss calculation
            atr = None
            if "M5" in timeframe_data:
                from backend.strategy import TradingStrategy
                atr = TradingStrategy.calculate_atr(timeframe_data["M5"])

            # Calculate stop loss
            stop_loss = self.risk_manager.calculate_atr_stop_loss(entry_price, atr, direction)

            # Calculate position size
            position_sizing = self.risk_manager.calculate_position_size(entry_price, stop_loss)

            if position_sizing["position_size"] <= 0:
                return {
                    "success": False,
                    "reason": "Invalid position size"
                }

            # Calculate take profit
            take_profit_calc = self.risk_manager.calculate_take_profit(entry_price, stop_loss)
            take_profit = take_profit_calc["take_profit"]

            # Validate setup
            validation = self.risk_manager.validate_setup(entry_price, stop_loss, take_profit)
            if not validation["valid"]:
                return {
                    "success": False,
                    "reason": f"Setup validation failed: {validation['reasons'][0]}"
                }

            # Create trade in database
            trade_id = self.db.create_trade(
                symbol,
                direction,
                entry_price,
                stop_loss,
                position_sizing["position_size"],
                position_sizing["risk_amount"]
            )

            logger.info(f"Trade opened: ID {trade_id}, {symbol} {direction} @ {entry_price:.5f}")

            return {
                "success": True,
                "trade_id": trade_id,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "position_size": position_sizing["position_size"]
            }

        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return {
                "success": False,
                "reason": str(e)
            }
