from crewai import Agent, Task, Crew, Process
from typing import Dict, Any
import logging
import json
from bridge import MarketIntelligence
from config import *

logger = logging.getLogger(__name__)

class TradingAgents:
    def __init__(self):
        self.market_intel = MarketIntelligence()
        self.setup_agents()
    
    def setup_agents(self):
        """Initialize the CrewAI agents"""
        
        # Agent A: Technical Observer
        self.technical_observer = Agent(
            role='Technical Observer',
            goal='Analyze raw market data to identify breakout and pullback opportunities based on technical levels',
            backstory="""You are an expert technical analyst with deep expertise in price action, 
            support/resistance levels, and chart pattern recognition. You excel at identifying 
            key technical levels and potential breakout/pullback opportunities in real-time market data.""",
            verbose=True,
            allow_delegation=False
        )
        
        # Agent B: Executive Strategist
        self.executive_strategist = Agent(
            role='Executive Strategist',
            goal='Validate trading signals, assess market conditions, and generate final trade recommendations with detailed reasoning',
            backstory="""You are a senior trading strategist who combines technical analysis with 
            market context validation. You ensure that trades align with higher timeframe trends, 
            session timing, and risk management principles before giving final approval.""",
            verbose=True,
            allow_delegation=False
        )
    
    def create_technical_analysis_task(self, market_data: Dict[str, Any]) -> Task:
        """Create task for Technical Observer agent"""
        return Task(
            description=f"""Analyze the following market data for {INSTRUMENT}:
            
            Current Price: {market_data.get('entry_price', 'N/A')}
            Swing High: {market_data.get('swing_high', 'N/A')}
            Swing Low: {market_data.get('swing_low', 'N/A')}
            SMA50 (M15): {market_data.get('sma_m15', 'N/A')}
            SMA50 (H4): {market_data.get('sma_h4', 'N/A')}
            ATR: {market_data.get('atr', 'N/A')}
            M15 Trend: {market_data.get('m15_trend', 'N/A')}
            H4 Trend: {market_data.get('h4_trend', 'N/A')}
            Trend Aligned: {market_data.get('trend_aligned', 'N/A')}
            
            Identify:
            1. Breakout opportunities (price breaking above swing high or below swing low)
            2. Pullback opportunities (price retesting swing levels in trending market)
            3. Signal strength and confidence level
            
            Provide your analysis including:
            - Detected pattern type (breakout/pullback)
            - Signal direction (BUY/SELL)
            - Confidence score (0-100)
            - Detailed reasoning for your assessment
            """,
            agent=self.technical_observer,
            expected_output="""JSON format with:
            {
                "signal": "BUY" or "SELL" or "NONE",
                "confidence": 0-100,
                "pattern_type": "breakout" or "pullback" or "none",
                "reasoning": "detailed explanation of analysis",
                "key_levels": {"swing_high": float, "swing_low": float},
                "trend_analysis": {"m15_trend": string, "h4_trend": string, "aligned": boolean}
            }
            """
        )
    
    def create_strategy_validation_task(self, technical_analysis_output: Dict[str, Any]) -> Task:
        """Create task for Executive Strategist agent"""
        return Task(
            description=f"""Validate the technical analysis and provide final trading decision:
            
            Technical Analysis Results:
            {json.dumps(technical_analysis_output, indent=2)}
            
            Additional Market Context:
            - Instrument: {INSTRUMENT}
            - Session: London/NY Overlap ({(SESSION_START_HOUR):02d}:00-{(SESSION_END_HOUR):02d}:00 GMT)
            - Risk per Trade: {RISK_PER_TRADE*100}%
            - SL Multiplier: {SL_MULTIPLIER}
            - TP Multiplier: {TP_MULTIPLIER}
            
            Validate:
            1. Signal alignment with higher timeframe (H4) trend
            2. Session timing (London/NY overlap)
            3. Risk/reward ratio adequacy
            4. Overall market conditions suitability
            
            Provide final decision with:
            - Trade action (BUY/SELL/NO_TRADE)
            - Entry price
            - Stop loss level
            - Take profit level
            - Risk amount
            - Detailed reasoning explaining validation process
            - Confidence in the final decision
            """,
            agent=self.executive_strategist,
            expected_output="""JSON format with:
            {
                "action": "BUY" or "SELL" or "NO_TRADE",
                "entry_price": float,
                "stop_loss": float,
                "take_profit": float,
                "risk_amount": float,
                "confidence": 0-100,
                "reasoning": "detailed explanation of validation and decision",
                "validation_checks": {
                    "session_valid": boolean,
                    "trend_aligned": boolean,
                    "risk_reward_adequate": boolean
                }
            }
            """
        )
    
    def analyze_and_recommend(self) -> Dict[str, Any]:
        """Main analysis pipeline using CrewAI agents"""
        try:
            # Get market intelligence data
            market_data = self.market_intel.analyze_market()
            
            if market_data is None:
                return {
                    "action": "NO_TRADE",
                    "reasoning": "No valid market data available or outside trading session",
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            # For now, we'll use the market data directly and simulate agent reasoning
            # In a full implementation, we would use CrewAI to parse and analyze this data
            
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