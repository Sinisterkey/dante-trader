"""
Enhanced Agents Module
CrewAI agent definitions and logic with ML integration
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import pandas as pd
from market_intelligence import MarketIntelligence
from ml_integration import MLIntegration
from broker_integration import MT5Broker
from config import *
from trade_logger import TradeLogger
from performance_analytics import PerformanceAnalytics
from position_manager import PositionManager
try:
    from telegram import Bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    Bot = None

logger = logging.getLogger(__name__)


class TradingAgents:
    """Enhanced trading agents with ML integration"""
    
    def __init__(self, broker=None):
        self.market_intel = MarketIntelligence()
        self.ml_integration = MLIntegration()
        self.broker = broker if broker is not None else MT5Broker()
        self.position_manager = PositionManager(self.broker, self.market_intel)
        self.trade_logger = TradeLogger()
        self.performance_analytics = PerformanceAnalytics(self.trade_logger)
        # Initialize Telegram bot if credentials are available
        self.telegram_bot = None
        if TELEGRAM_AVAILABLE and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            try:
                self.telegram_bot = Bot(token=TELEGRAM_TOKEN)
                logger.info("Telegram bot initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")
        logger.info("Enhanced Trading Agents initialized")
        self.news_agent = self._init_news_agent()
        self.memory_agent = self._init_memory_agent()
    
    def _init_news_agent(self):
        try:
            from backend.news_agent import NewsAgent
            return NewsAgent()
        except Exception as e:
            logger.warning(f"NewsAgent not available: {e}")
            return None
    
    def _init_memory_agent(self):
        try:
            from backend.memory_agent import MemoryAgent
            from backend.db import TradingDatabase
            db = TradingDatabase()
            return MemoryAgent(db)
        except Exception as e:
            logger.warning(f"MemoryAgent not available: {e}")
            return None
    
    def analyze_and_recommend(self) -> Dict[str, Any]:
        """Main analysis pipeline using market intelligence and ML enhancement"""
        try:
            # Fetch market data from broker
            df_m15 = self.broker.get_historical_data(INSTRUMENT, "M15", BARS_TO_FETCH)
            df_h4 = self.broker.get_historical_data(INSTRUMENT, "H4", BARS_TO_FETCH)
            
            if df_m15 is None or df_h4 is None or df_m15.empty or df_h4.empty:
                return {
                    "action": "NO_TRADE",
                    "reasoning": "Failed to fetch market data from broker",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            
            # Get market intelligence signal
            market_data = self.market_intel.generate_signal(df_m15, df_h4)
            
            # Detect market regime
            market_regime = self.market_intel.detect_market_regime(df_m15)
            
            # COLLABORATIVE AGENTS INTEGRATION
            collaborative_context = {}
            
            news_sentiment = None
            if self.news_agent:
                try:
                    news_result = self.news_agent.analyze(INSTRUMENT, hours_lookback=12)
                    news_sentiment = news_result.get('sentiment', 'neutral')
                    collaborative_context['news'] = {'sentiment': news_sentiment, 'confidence': news_result.get('confidence', 0)}
                    logger.info(f"[Collaborative] NewsAgent: {news_sentiment}")
                except Exception as e:
                    logger.warning(f"[Collaborative] NewsAgent error: {e}")
            
            if self.memory_agent and market_data.get('signal') in ['BUY', 'SELL']:
                try:
                    direction = 'LONG' if market_data.get('signal') == 'BUY' else 'SHORT'
                    mem_result = self.memory_agent.analyze(INSTRUMENT, direction)
                    collaborative_context['memory'] = {'winrate': mem_result.get('best_setup_winrate', 0)}
                    logger.info(f"[Collaborative] MemoryAgent: Winrate {mem_result.get('best_setup_winrate', 0)*100:.1f}%")
                except Exception as e:
                    logger.warning(f"[Collaborative] MemoryAgent error: {e}")
            
            # Get market data for ML feature extraction
            market_context = {
                'rsi': market_data.get('rsi', 50.0),
                'macd': market_data.get('macd', {}),
                'bollinger_bands': market_data.get('bollinger_bands', {}),
                'hour_of_day': datetime.now(timezone.utc).hour,
                'day_of_week': datetime.now(timezone.utc).weekday(),
                'session': 0.5 if self.market_intel.is_london_ny_overlap(datetime.now(timezone.utc)) else 0.0,
                'volatility_regime': 0.5 if 'high_vol' in market_regime else 0.0,
                'trend_alignment': 1.0 if market_data.get('trend_aligned') else 0.0,
                'news_sentiment': news_sentiment if news_sentiment else 'neutral'
            }
            
            # Create base signal from market intelligence
            base_signal = {
                'action': market_data.get('signal'),
                'confidence': market_data.get('confidence', 0),
                'reason': market_data.get('reason', ''),
                'entry_price': market_data.get('entry_price'),
                'stop_loss': market_data.get('stop_loss'),
                'take_profit': market_data.get('take_profit'),
                'risk_amount': market_data.get('risk_amount'),
                'ml_confidence': 0.0  # Will be enhanced by ML
            }
            
            # If we have a valid signal, enhance it with ML and collaborative insights
            if base_signal['action'] in ['BUY', 'SELL'] and base_signal['confidence'] > 0:
                enhanced_signal = self.ml_integration.enhance_signal(base_signal, market_context)
                final_confidence = enhanced_signal.get('enhanced_confidence', base_signal['confidence'])
                
                # COLLABORATIVE CONFIDENCE ADJUSTMENT
                if news_sentiment == 'bullish' and base_signal['action'] == 'BUY':
                    final_confidence = min(100, final_confidence + 8)
                elif news_sentiment == 'bearish' and base_signal['action'] == 'SELL':
                    final_confidence = min(100, final_confidence + 8)
                elif news_sentiment in ['bullish', 'bearish']:
                    final_confidence = max(0, final_confidence - 12)
                
                if collaborative_context.get('memory'):
                    mem_boost = collaborative_context['memory'].get('winrate', 0) * 30
                    final_confidence = min(100, final_confidence + mem_boost)
                
                action = base_signal['action']
                reasoning = enhanced_signal.get('reason', base_signal['reason'])
                
                # Additional validation checks
                session_valid = self.market_intel.is_london_ny_overlap()
                trend_aligned = market_data.get('trend_aligned', False)
                
                # Override action if validation fails
                if not session_valid:
                    action = "NO_TRADE"
                    confidence = 0
                    reasoning = "Outside London/NY overlap session - no trading allowed"
                elif not trend_aligned:
                    action = "NO_TRADE"
                    confidence = 0
                    reasoning = f"Signal ({base_signal['action']}) detected but H4 trend ({market_data.get('h4_trend')}) not aligned with M15 trend ({market_data.get('m15_trend')})"
                elif final_confidence < 60:  # Minimum confidence threshold after ML enhancement
                    action = "NO_TRADE"
                    confidence = 0
                    reasoning = f"Enhanced confidence too low: {final_confidence:.1f}%"
                else:
                    action = base_signal['action']
                    confidence = final_confidence
                    ml_reason = f"ML Enhancement: Success probability {enhanced_signal.get('ml_confidence', 0):.1%}"
                    reasoning = f"{base_signal['reason']}. {ml_reason}" if base_signal['reason'] else ml_reason
                    if collaborative_context.get('news'):
                        reasoning += f". News: {collaborative_context['news']['sentiment']}"
                    if collaborative_context.get('memory'):
                        reasoning += f". Memory: {collaborative_context['memory']['winrate']*100:.0f}% winrate"
                
                result = {
                    "action": action,
                    "entry_price": enhanced_signal.get('entry_price'),
                    "stop_loss": enhanced_signal.get('stop_loss'),
                    "take_profit": enhanced_signal.get('take_profit'),
                    "risk_amount": enhanced_signal.get('risk_amount'),
                    "confidence": round(confidence, 1),
                    "reasoning": reasoning,
                    "validation_checks": {
                        "session_valid": session_valid,
                        "trend_aligned": trend_aligned,
                        "risk_reward_adequate": True
                    },
                    "agent_thought_process": {
                        "market_intelligence": market_data.get('reason', ''),
                        "ml_enhancement": f"ML predicted {enhanced_signal.get('ml_confidence', 0):.1%} success probability",
                        "news_sentiment": f"News: {news_sentiment}" if news_sentiment else "News: Neutral",
                        "memory_insights": f"Memory: {collaborative_context['memory'].get('winrate', 0)*100:.0f}% winrate" if collaborative_context.get('memory') else "Memory: No data",
                        "final_decision": f"Action: {action} with {confidence:.1f}% confidence (collective)"
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "market_data": market_data,
                    "ml_data": {
                        "ml_confidence": enhanced_signal.get('ml_confidence', 0.0),
                        "ml_expected_profit": enhanced_signal.get('ml_expected_profit', 0.0),
                        "original_confidence": enhanced_signal.get('original_confidence', 0),
                        "enhanced_confidence": enhanced_signal.get('enhanced_confidence', 0.0)
                    },
                    "market_regime": market_regime,
                    "collaborative_context": collaborative_context
                }
                
            else:
                # No valid signal or low confidence
                session_valid = self.market_intel.is_london_ny_overlap()
                trend_aligned = market_data.get('trend_aligned', False)
                
                if not session_valid:
                    action = "NO_TRADE"
                    confidence = 0
                    reasoning = "Outside London/NY overlap session - no trading allowed"
                elif not trend_aligned:
                    action = "NO_TRADE"
                    confidence = 0
                    reasoning = f"No valid signal detected and H4 trend ({market_data.get('h4_trend')}) not aligned with M15 trend ({market_data.get('m15_trend')})"
                else:
                    action = "NO_TRADE"
                    confidence = 0
                    reasoning = "No valid signal detected"
                
                result = {
                    "action": action,
                    "entry_price": None,
                    "stop_loss": None,
                    "take_profit": None,
                    "risk_amount": None,
                    "confidence": confidence,
                    "reasoning": reasoning,
                    "validation_checks": {
                        "session_valid": session_valid,
                        "trend_aligned": trend_aligned,
                        "risk_reward_adequate": False
                    },
                    "agent_thought_process": {
                        "market_intelligence": market_data.get('reason', 'No signal generated'),
                        "ml_enhancement": "No signal to enhance",
                        "news_sentiment": f"News: {news_sentiment}" if news_sentiment else "News: Not checked",
                        "final_decision": "No trade recommended"
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "market_data": market_data,
                    "ml_data": {
                        "ml_confidence": 0.0,
                        "ml_expected_profit": 0.0,
                        "original_confidence": 0.0,
                        "enhanced_confidence": 0.0
                    },
                    "market_regime": market_regime,
                    "collaborative_context": collaborative_context
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in agent analysis pipeline: {e}")
            return {
                "action": "NO_TRADE",
                "reasoning": f"Error in analysis pipeline: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    def execute_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a trading signal from the agent system"""
        try:
            # Validate signal
            action = signal.get('action')
            if action == 'NO_TRADE':
                return {"success": False, "reason": "No trade signal"}
            
            # Check if we can open a new position (risk management)
            can_open, reason = self.position_manager.can_open_new_position()
            if not can_open:
                return {"success": False, "reason": reason}
            
            # Execute the signal
            result = self.position_manager.execute_signal(signal)
            
            # Log the trade if successful
            if result.get('success', False):
                # Log trade open
                position_data = result.get('position', {})
                if position_data:
                    trade_id = self.trade_logger.log_trade_open(position_data)
                    logger.info(f"Trade opened logged with ID: {trade_id}")
                    
                    # Log system event for trade execution
                    self.trade_logger.log_system_event("trade", f"Executed {action} trade", {
                        "ticket": position_data.get('ticket'),
                        "action": action,
                        "entry_price": position_data.get('entry_price'),
                        "volume": position_data.get('volume'),
                        "confidence": signal.get('confidence'),
                        "reason": signal.get('reasoning', '')
                    })
                    
                    # Send Telegram alert
                    if self.telegram_bot and TELEGRAM_CHAT_ID:
                        try:
                            message = self._format_telegram_message(signal, position_data)
                            self.telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode='HTML')
                            logger.info(f"Telegram alert sent for {action} signal")
                        except Exception as e:
                            logger.error(f"Failed to send Telegram alert: {e}")
                
                # Update performance metrics
                self.performance_analytics.calculate_advanced_metrics([])
                
                # Online learning from trade outcome (will be updated when trade closes)
                # For now, we'll store the signal for later updating when trade closes
                # In a real implementation, we would need to track open trades and update on close
                
                logger.info(f"Signal executed: {action} {signal.get('entry_price')} with confidence {signal.get('confidence')}%")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing signal: {e}")
            return {"success": False, "error": str(e)}
    
    def _format_telegram_message(self, signal: Dict[str, Any], position_data: Dict[str, Any]) -> str:
        """Format signal and position data for Telegram alert"""
        action_emoji = "🟢" if signal['action'] == 'BUY' else "🔴"
        
        message = f"{action_emoji} <b>NAS100 TRADE SIGNAL</b> {action_emoji}\n\n"
        message += f"<b>Action:</b> {signal['action']}\n"
        message += f"<b>Entry:</b> {signal.get('entry_price', 0):.2f}\n"
        message += f"<b>Stop Loss:</b> {signal.get('stop_loss', 0):.2f}\n"
        message += f"<b>Take Profit:</b> {signal.get('take_profit', 0):.2f}\n"
        message += f"<b>Risk Amount:</b> {signal.get('risk_amount', 0):.2f} points\n\n"
        message += f"<b>Confidence:</b> {signal.get('confidence', 0)}%\n"
        message += f"<b>Position Size:</b> {position_data.get('volume', 0):.2f} lots\n\n"
        message += f"<b>Reasoning:</b>\n{signal.get('reasoning', 'No reasoning provided')}\n\n"
        message += f"<b>Time:</b> {signal.get('timestamp', datetime.now(timezone.utc).isoformat())}\n"
        
        return message
    
    def retrain_ml_models(self) -> Dict[str, Any]:
        """Retrain ML models with latest trade data"""
        try:
            logger.info("Starting ML model retraining...")
            result = self.ml_integration.train_models()
            logger.info(f"ML retraining completed: {result}")
            return result
        except Exception as e:
            logger.error(f"Error retraining ML models: {e}")
            return {"success": False, "error": str(e)}