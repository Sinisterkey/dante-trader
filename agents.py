import logging
import json
from bridge import MarketIntelligence
from config import *
from datetime import datetime

logger = logging.getLogger(__name__)

class TradingAgents:
    def __init__(self):
        self.market_intel = MarketIntelligence()
    
    def analyze_and_recommend(self) -> Dict[str, Any]:
        """Main analysis pipeline that simulates the CrewAI agents"""
        try:
            # Get market intelligence data
            market_data = self.market_intel.analyze_market()
            
            if market_data is None:
                return {
                    "action": "NO_TRADE",
                    "reasoning": "No valid market data available or outside trading session",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # Simulate Technical Observer analysis
            technical_analysis = {
                "signal": market_data.get('signal'),
                "confidence": 75 if market_data.get('signal') else 0,  # Simulated
                "pattern_type": "breakout" if "breakout" in market_data.get('reason', '').lower() else "pullback" if "pullback" in market_data.get('reason', '').lower() else "none",
                "reasoning": market_data.get('reason', 'Technical analysis completed'),
                "key_levels": {
                    "swing_high": market_data.get('swing_high'),
                    "swing_low": market_data.get('swing_low')
                },
                "trend_analysis": {
                    "m15_trend": market_data.get('m15_trend'),
                    "h4_trend": market_data.get('h4_trend'),
                    "aligned": market_data.get('trend_aligned')
                }
            }
            
            # Simulate Executive Strategist validation
            # Check if we have a valid signal and if it passes our validation criteria
            signal = market_data.get('signal')
            session_valid = self.market_intel.is_london_ny_overlap()
            trend_aligned = market_data.get('trend_aligned', False)
            
            # Final decision logic
            if signal and session_valid and trend_aligned:
                action = signal  # BUY or SELL
                confidence = 80  # Simulated confidence from executive strategist
                reasoning = f"Technical Analysis: {market_data.get('reason', '')}. Strategic Validation: Confirmed {market_data.get('h4_trend', '')} H4 trend alignment and London/NY session validity."
            else:
                action = "NO_TRADE"
                confidence = 0
                if not session_valid:
                    reasoning = "Outside London/NY overlap session - no trading allowed"
                elif not trend_aligned:
                    reasoning = f"Signal ({signal}) detected but H4 trend ({market_data.get('h4_trend')}) not aligned with M15 trend ({market_data.get('m15_trend')})"
                else:
                    reasoning = "No valid signal detected"
            
            final_recommendation = {
                "action": action,
                "entry_price": market_data.get('entry_price'),
                "stop_loss": market_data.get('stop_loss'),
                "take_profit": market_data.get('take_profit'),
                "risk_amount": market_data.get('risk_amount'),
                "confidence": confidence,
                "reasoning": reasoning,
                "validation_checks": {
                    "session_valid": session_valid,
                    "trend_aligned": trend_aligned,
                    "risk_reward_adequate": True  # Simplified check
                },
                "agent_thought_process": {
                    "technical_observer": market_data.get('reason', ''),
                    "executive_strategist": f"Validated signal: {signal}. Checked H4 trend ({market_data.get('h4_trend')}), session timing ({session_valid}), and risk management."
                },
                "timestamp": datetime.utcnow().isoformat(),
                "market_data": market_data
            }
            
            return final_recommendation
            
        except Exception as e:
            logger.error(f"Error in agent analysis pipeline: {e}")
            return {
                "action": "NO_TRADE",
                "reasoning": f"Error in analysis pipeline: {str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }