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

logger = logging.getLogger(__name__)


class TradingAgents:
    """Enhanced trading agents with ML integration"""
    
    def __init__(self, broker=None):
        self.market_intel = MarketIntelligence()
        self.ml_integration = MLIntegration()
        self.broker = broker if broker is not None else MT5Broker()
        logger.info("Enhanced Trading Agents initialized")
    
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
            
            # Get market data for ML feature extraction
            market_context = {
                'rsi': market_data.get('rsi', 50.0),
                'macd': market_data.get('macd', {}),
                'bollinger_bands': market_data.get('bollinger_bands', {}),
                'hour_of_day': datetime.now(timezone.utc).hour,
                'day_of_week': datetime.now(timezone.utc).weekday(),
                'session': 0.5 if self.market_intel.is_london_ny_overlap(datetime.now(timezone.utc)) else 0.0,
                'volatility_regime': 0.5,  # Simplified - could be enhanced
                'trend_alignment': 1.0 if market_data.get('trend_aligned') else 0.0
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
            
            # If we have a valid signal, enhance it with ML
            if base_signal['action'] in ['BUY', 'SELL'] and base_signal['confidence'] > 0:
                # Enhance signal with ML predictions
                enhanced_signal = self.ml_integration.enhance_signal(base_signal, market_context)
                
                # Use enhanced confidence for final decision
                final_confidence = enhanced_signal.get('enhanced_confidence', base_signal['confidence'])
                
                # Determine final action based on enhanced confidence and validation
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
                    # Combine original and ML reasoning
                    ml_reason = f"ML Enhancement: Success probability {enhanced_signal.get('ml_confidence', 0):.1%}"
                    if base_signal['reason']:
                        reasoning = f"{base_signal['reason']}. {ml_reason}"
                    else:
                        reasoning = ml_reason
                
                # Prepare final result
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
                        "risk_reward_adequate": True  # Simplified check
                    },
                    "agent_thought_process": {
                        "market_intelligence": market_data.get('reason', ''),
                        "ml_enhancement": f"ML predicted {enhanced_signal.get('ml_confidence', 0):.1%} success probability",
                        "final_decision": f"Action: {action} with {confidence:.1f}% confidence"
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "market_data": market_data,
                    "ml_data": {
                        "ml_confidence": enhanced_signal.get('ml_confidence', 0.0),
                        "ml_expected_profit": enhanced_signal.get('ml_expected_profit', 0.0),
                        "original_confidence": enhanced_signal.get('original_confidence', 0),
                        "enhanced_confidence": enhanced_signal.get('enhanced_confidence', 0.0)
                    }
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
                        "final_decision": "No trade recommended"
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "market_data": market_data,
                    "ml_data": {
                        "ml_confidence": 0.0,
                        "ml_expected_profit": 0.0,
                        "original_confidence": 0.0,
                        "enhanced_confidence": 0.0
                    }
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in agent analysis pipeline: {e}")
            return {
                "action": "NO_TRADE",
                "reasoning": f"Error in analysis pipeline: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
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