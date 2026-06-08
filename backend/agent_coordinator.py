"""
Unified Agent Coordinator
Integrates all backend agents and enables cross-communication for collective decision making
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from config import INSTRUMENT, BARS_TO_FETCH

logger = logging.getLogger(__name__)


class AgentCoordinator:
    """Coordinates all agents for collective market analysis"""
    
    def __init__(self, broker=None):
        from market_intelligence import MarketIntelligence
        from ml_integration import MLIntegration
        from broker_integration import MT5Broker
        from backend.news_agent import NewsAgent
        from backend.memory_agent import MemoryAgent
        
        self.broker = broker or MT5Broker()
        self.market_intel = MarketIntelligence()
        self.ml = MLIntegration()
        self.news_agent = NewsAgent()
        self.memory_agent = MemoryAgent(self._get_db())
        
        logger.info("AgentCoordinator initialized with all agents")
    
    def _get_db(self):
        """Get database connection for memory agent"""
        try:
            from backend.db import TradingDatabase
            return TradingDatabase()
        except Exception:
            return None
    
    def analyze_market(self, symbol: str, timeframes: List[str] = None) -> Dict[str, Any]:
        """Run all agents and synthesize collective decision"""
        if timeframes is None:
            timeframes = {"M15": 200, "M5": 100, "H4": 100, "H1": 100}
        
        results = {
            "symbol": symbol,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agents": {},
            "collective_decision": "NO_TRADE",
            "confidence": 0,
            "reasoning": []
        }
        
        # 1. Market Intelligence Agent - Technical Analysis
        try:
            df_m15 = self.broker.get_historical_data(symbol, "M15", timeframes["M15"])
            df_h4 = self.broker.get_historical_data(symbol, "H4", timeframes["H4"])
            
            if df_m15 is not None and df_h4 is not None and not df_m15.empty and not df_h4.empty:
                mi_signal = self.market_intel.generate_signal(df_m15, df_h4)
                mi_regime = self.market_intel.detect_market_regime(df_m15)
                
                results["agents"]["market_intel"] = {
                    "signal": mi_signal.get("signal"),
                    "confidence": mi_signal.get("confidence", 0),
                    "trend": mi_signal.get("m15_trend"),
                    "regime": mi_regime,
                    "rsi": mi_signal.get("rsi"),
                    "reasoning": mi_signal.get("reason", "")
                }
                results["reasoning"].append(f"[MI] {mi_signal.get('reason', 'No signal')}")
        except Exception as e:
            logger.error(f"MarketIntel error: {e}")
            results["agents"]["market_intel"] = {"error": str(e)}
        
        # 2. News Agent - Sentiment Analysis
        try:
            news_result = self.news_agent.analyze(symbol, hours_lookback=12)
            results["agents"]["news"] = news_result
            
            if news_result.get("sentiment") != "neutral":
                results["reasoning"].append(f"[News] {news_result.get('sentiment')} sentiment ({news_result.get('confidence')}%)")
        except Exception as e:
            logger.error(f"NewsAgent error: {e}")
            results["agents"]["news"] = {"error": str(e)}
        
        # 3. Memory Agent - Historical Performance
        try:
            mi_data = results["agents"].get("market_intel", {})
            trend = mi_data.get("trend", "NONE")
            if trend in ["BULLISH", "BEARISH"]:
                mem_result = self.memory_agent.analyze(symbol, "LONG" if trend == "BULLISH" else "SHORT")
                results["agents"]["memory"] = mem_result
                
                if mem_result.get("confidence", 0) > 0:
                    results["reasoning"].append(f"[Memory] Historical winrate: {mem_result.get('best_setup_winrate', 0)*100:.1f}%")
        except Exception as e:
            logger.error(f"MemoryAgent error: {e}")
            results["agents"]["memory"] = {"error": str(e)}
        
        # 4. ML Enhancement - Collective Confidence
        try:
            mi_conf = results["agents"].get("market_intel", {}).get("confidence", 50)
            news_conf = results["agents"].get("news", {}).get("confidence", 0)
            mem_conf = results["agents"].get("memory", {}).get("confidence", 0)
            
            # Combine agent confidences
            # MarketIntel (70%) + News (15%) + Memory (15%)
            collective_conf = (mi_conf * 0.7 + news_conf * 0.15 + mem_conf * 0.15)
            results["confidence"] = round(collective_conf, 1)
            
            # Determine action based on consensus
            mi_signal = results["agents"].get("market_intel", {}).get("signal")
            if mi_signal in ["BUY", "SELL"] and collective_conf >= 60:
                results["collective_decision"] = mi_signal
            elif mi_signal in ["BUY", "SELL"]:
                results["collective_decision"] = "NO_TRADE"  # Low collective confidence
                results["reasoning"].append(f"[Decision] Confidence too low ({collective_conf:.1f}%)")
        except Exception as e:
            logger.error(f"ML synthesis error: {e}")
        
        logger.info(f"Agent collective decision for {symbol}: {results['collective_decision']} ({results['confidence']}%)")
        return results
    
    def get_agent_weights(self, symbol: str) -> Dict[str, float]:
        """Adjust agent weights based on historical performance"""
        # This would be learned over time - for now use static weights
        # Memory agent can provide weight adjustments based on past performance
        return {
            "market_intel": 0.7,
            "news": 0.15,
            "memory": 0.15
        }