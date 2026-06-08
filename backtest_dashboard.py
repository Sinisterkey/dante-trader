"""
Backtesting Dashboard Module
Strategy backtesting with historical data analysis
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
import logging
from typing import Dict, List, Any
from broker_integration import MT5Broker
from market_intelligence import MarketIntelligence
from ml_integration import MLIntegration
from config import AVAILABLE_INSTRUMENTS, BARS_TO_FETCH

logger = logging.getLogger(__name__)

class BacktestDashboard:
    """Backtesting dashboard for strategy validation"""
    
    def __init__(self):
        self.broker = MT5Broker()
    
    def render(self):
        """Render backtesting dashboard"""
        st.set_page_config(
            page_title="Strategy Backtesting",
            page_icon="📊",
            layout="wide"
        )
        
        st.title("📊 Strategy Backtesting")
        st.markdown("Test your trading strategy against historical data")
        
        # Control panel
        col1, col2, col3 = st.columns(3)
        
        with col1:
            symbol = st.selectbox("Symbol", options=AVAILABLE_INSTRUMENTS, index=0)
        
        with col2:
            days_back = st.number_input("Days to Analyze", min_value=30, max_value=730, value=90, step=30)
        
        with col3:
            timeframe = st.selectbox("Timeframe", options=["M15", "H1", "H4"], index=0)
        
        if st.button("🔍 Run Backtest"):
            with st.spinner(f"Running backtest for {symbol} over last {days_back} days..."):
                results = self.run_backtest(symbol, days_back, timeframe)
                self.display_results(results, symbol)
    
    def run_backtest(self, symbol: str, days: int, timeframe: str) -> Dict[str, Any]:
        """Run backtest for given symbol and period"""
        try:
            # Fetch longer historical data
            df = self.broker.get_historical_data(symbol, timeframe, min(days * 10, 1000))
            
            if df is None or df.empty:
                return {"error": "No historical data available"}
            
            # Ensure we have proper columns
            if 'time' in df.columns:
                df = df.set_index('time')
            
            # Calculate backtest metrics
            signals = []
            wins = 0
            losses = 0
            total_trades = 0
            total_pnl = 0.0
            
            mi = MarketIntelligence()
            
            # Walk through data in chunks for signal generation
            for i in range(50, len(df) - 1):
                chunk = df.iloc[i-50:i]
                current_price = df['close'].iloc[i]
                next_price = df['close'].iloc[i+1]
                
                # Generate signal for this point
                try:
                    swing_high, swing_low = mi.calculate_swing_levels(chunk)
                    sma = mi.calculate_sma(chunk)
                    
                    if swing_high and swing_low and sma:
                        signal = None
                        if current_price > swing_high:
                            signal = "BUY"
                        elif current_price < swing_low:
                            signal = "SELL"
                        
                        if signal:
                            # Calculate P&L (simplified - next candle move)
                            move = abs(next_price - current_price)
                            pnl = move if signal == "BUY" else -move
                            
                            signals.append({
                                "time": df.index[i],
                                "signal": signal,
                                "entry": current_price,
                                "exit": next_price,
                                "pnl": pnl
                            })
                            
                            if pnl > 0:
                                wins += 1
                            else:
                                losses += 1
                            total_pnl += pnl
                            total_trades += 1
                except Exception as e:
                    continue
            
            win_rate = wins / total_trades if total_trades > 0 else 0
            
            return {
                "symbol": symbol,
                "signals": signals,
                "total_trades": total_trades,
                "wins": wins,
                "losses": losses,
                "win_rate": win_rate,
                "total_pnl": total_pnl,
                "avg_pnl": total_pnl / total_trades if total_trades > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Backtest error: {e}")
            return {"error": str(e)}
    
    def display_results(self, results: Dict[str, Any], symbol: str):
        """Display backtest results"""
        if "error" in results:
            st.error(results["error"])
            return
        
        st.subheader(f"Backtest Results: {symbol}")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Trades", results["total_trades"])
        with col2:
            st.metric("Win Rate", f"{results['win_rate']*100:.1f}%")
        with col3:
            st.metric("Wins", results["wins"])
        with col4:
            st.metric("Losses", results["losses"])
        
        st.metric("Total P&L", f"${results['total_pnl']:.2f}")
        st.metric("Avg P&L per Trade", f"${results['avg_pnl']:.2f}")
        
        # Show signal table
        if results["signals"]:
            df_signals = pd.DataFrame(results["signals"])
            st.dataframe(df_signals, use_container_width=True)


def render_backtest():
    """Main function"""
    dashboard = BacktestDashboard()
    dashboard.render()


if __name__ == "__main__":
    render_backtest()