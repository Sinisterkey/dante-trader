"""
Enhanced Dashboard Module
Advanced GUI with Agent Thought Process Monitor and Interactive Charting
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from datetime import datetime, timezone
import logging
import json
from typing import Dict, List, Any, Optional

from config import INSTRUMENT, AVAILABLE_INSTRUMENTS, BARS_TO_FETCH
from trade_logger import TradeLogger
from performance_analytics import PerformanceAnalytics
from risk_engine import RiskEngine
from agents import TradingAgents

logger = logging.getLogger(__name__)

# Page selection
PAGES = {
    "live": "Live Trading",
    "backtest": "Backtesting",
}

def render_backtest():
    """Render backtesting page"""
    st.set_page_config(
        page_title="Strategy Backtesting",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("📊 Strategy Backtesting")
    st.markdown("Test your trading strategy against historical data")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        symbol = st.selectbox("Symbol", options=AVAILABLE_INSTRUMENTS, index=0)
    
    with col2:
        days_back = st.number_input("Days to Analyze", min_value=30, max_value=730, value=90, step=30)
    
    with col3:
        timeframe = st.selectbox("Timeframe", options=["M15", "H1", "H4"], index=0)
    
    if st.button("🔍 Run Backtest"):
        with st.spinner(f"Running backtest for {symbol} over last {days_back} days..."):
            results = run_backtest(symbol, days_back, timeframe)
            display_backtest_results(results, symbol)


"""Run backtest for given symbol and period"""
    try:
        from broker_integration import MT5Broker
        from market_intelligence import MarketIntelligence
        
        broker = MT5Broker()
        bars_needed = min(days * 24 * 4 if timeframe == "H1" else days * 24 * 2 if timeframe == "M30" else days * 24 if timeframe == "M15" else days * 6, 2000)
        
        df = broker.get_historical_data(symbol, timeframe, bars_needed)
        
        if df is None or df.empty:
            return {"error": "No historical data available"}
        
        if 'time' in df.columns:
            df = df.set_index('time')
        
        mi = MarketIntelligence()
        
        signals = []
        wins = 0
        losses = 0
        total_pnl = 0.0
        total_trades = 0
        
        for i in range(50, len(df) - 5):
            try:
                chunk = df.iloc[max(0, i-50):i]
                sma = mi.calculate_sma(chunk)
                
                if sma is None:
                    continue
                
                current_price = df['close'].iloc[i]
                next_prices = df['close'].iloc[i+1:i+5]
                
                if len(next_prices) == 0:
                    continue
                
                bullish = current_price > sma
                bearish = current_price < sma
                
                signal = None
                direction = 0
                if bullish and df['close'].iloc[i] > df['high'].iloc[i-1]:
                    signal = "BUY"
                    direction = 1
                elif bearish and df['close'].iloc[i] < df['low'].iloc[i-1]:
                    signal = "SELL"
                    direction = -1
                
                if signal:
                    future_move = (next_prices.iloc[-1] - current_price) * direction
                    signals.append({
                        "time": str(df.index[i])[:19],
                        "signal": signal,
                        "entry": round(current_price, 2),
                        "exit": round(next_prices.iloc[-1], 2),
                        "pnl": round(future_move, 2)
                    })
                    if future_move > 0:
                        wins += 1
                    else:
                        losses += 1
                    total_pnl += future_move
                    total_trades += 1
            except Exception:
                continue
        
        return {
            "symbol": symbol,
            "signals": signals[-50:],
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "win_rate": wins / total_trades if total_trades > 0 else 0,
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(total_pnl / total_trades, 2) if total_trades > 0 else 0
        }
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        return {"error": str(e)}


def display_backtest_results(results: Dict[str, Any], symbol: str):
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
    
    if results["signals"]:
        df_signals = pd.DataFrame(results["signals"])
        st.dataframe(df_signals, use_container_width=True)


class TradingDashboard:
    """Enhanced trading dashboard with advanced visualization"""
    
    def __init__(self):
        from broker_integration import MT5Broker
        self.broker = MT5Broker()
        self.trading_agents = TradingAgents(self.broker)
        self.trade_logger = TradeLogger()
        self.performance_analytics = PerformanceAnalytics(self.trade_logger)
        self.risk_engine = RiskEngine(self.broker)
        logger.info("Trading Dashboard initialized")
    
    def render_dashboard(self):
        if 'current_symbol' not in st.session_state:
            st.session_state.current_symbol = INSTRUMENT
        if 'market_analyses' not in st.session_state:
            st.session_state.market_analyses = {}
        if 'selected_symbols' not in st.session_state:
            st.session_state.selected_symbols = [INSTRUMENT]
        
        st.set_page_config(
            page_title="Multi-Market Real-time Trading System",
            page_icon="📈",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
        
        st.markdown("""
        <style>
        .main-header { font-size: 2.2rem; font-weight: bold; color: #1f77b4; text-align: center; margin-bottom: 0.5rem; }
        .sub-header { font-size: 1.1rem; color: #666; text-align: center; margin-bottom: 1.5rem; }
        .signal-buy { background-color: #d4edda; color: #155724; padding: 0.75rem; border-radius: 0.3rem; border-left: 4px solid #28a745; text-align: center; margin: 0.5rem 0; }
        .signal-sell { background-color: #f8d7da; color: #721c24; padding: 0.75rem; border-radius: 0.3rem; border-left: 4px solid #dc3545; text-align: center; margin: 0.5rem 0; }
        .signal-neutral { background-color: #fff3cd; color: #856404; padding: 0.75rem; border-radius: 0.3rem; border-left: 4px solid #ffc107; text-align: center; margin: 0.5rem 0; }
        .thought-process { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 0.3rem; padding: 1rem; height: 300px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 0.85rem; }
        .status-live { color: #28a745; font-weight: bold; }
        .status-closed { color: #dc3545; font-weight: bold; }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown('<h1 class="main-header">📈 Multi-Market Trading System</h1>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">Live Market Data • AI Agents • Parallel Analysis</p>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns([1.5, 1, 1, 1.5])
        
        with col1:
            selected_symbols = st.multiselect("Markets to Analyze", options=AVAILABLE_INSTRUMENTS,
                                             default=st.session_state.get('selected_symbols', [INSTRUMENT]),
                                             key="symbols_multiselect")
            st.session_state.selected_symbols = selected_symbols
        
        with col2:
            if st.button("▶️ Start All" if not st.session_state.get('is_running', False) else "⏸️ Stop All"):
                st.session_state.is_running = not st.session_state.get('is_running', False)
                if st.session_state.is_running:
                    st.success("Analysis started!")
                else:
                    st.info("Analysis stopped.")
                st.rerun()
        
        with col3:
            if st.button("🔄 Analyze Now"):
                with st.spinner("Analyzing markets..."):
                    analyses = self._analyze_multiple_markets(st.session_state.selected_symbols)
                    st.session_state.market_analyses = analyses
        
        with col4:
            st.markdown(f"**Session:** {'🟢 LIVE' if self.trading_agents.market_intel.is_london_ny_overlap() else '🔴 CLOSED'}")
        
        if 'last_analysis' not in st.session_state:
            st.session_state.last_analysis = None
        if 'analysis_history' not in st.session_state:
            st.session_state.analysis_history = []
        if 'is_running' not in st.session_state:
            st.session_state.is_running = False
        
        col_chart, col_side = st.columns([3, 1])
        
        with col_chart:
            self._render_charting_window()
        
        with col_side:
            st.subheader("💰 Trading Controls")
            self._render_agent_thought_process()
        
        st.markdown("---")
        st.markdown(
            f'<p style="text-align: center; color: #888; font-size: 0.85rem;">'
            f'Multi-Market Trading System | Last updated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")} UTC'
            f'</p>', unsafe_allow_html=True
        )
        
        if st.session_state.get('is_running', False):
            st.session_state.market_analyses = self._analyze_multiple_markets(st.session_state.selected_symbols)
    
    def _analyze_multiple_markets(self, symbols: List[str]) -> Dict[str, Any]:
        analyses = {}
        from market_intelligence import MarketIntelligence
        from ml_integration import MLIntegration
        
        for symbol in symbols:
            try:
                df_m15 = self.broker.get_historical_data(symbol, "M15", 200)
                df_h4 = self.broker.get_historical_data(symbol, "H4", 200)
                
                if df_m15 is None or df_h4 is None or df_m15.empty or df_h4.empty:
                    analyses[symbol] = {"error": "No data available"}
                    continue
                
                mi = MarketIntelligence()
                ml = MLIntegration()
                
                market_data = mi.generate_signal(df_m15, df_h4)
                market_regime = mi.detect_market_regime(df_m15)
                
                base_signal = {
                    'action': market_data.get('signal'),
                    'confidence': market_data.get('confidence', 0),
                }
                
                if base_signal['action'] in ['BUY', 'SELL'] and base_signal['confidence'] > 0:
                    market_context = {
                        'rsi': market_data.get('rsi', 50.0),
                        'macd': market_data.get('macd', {}),
                        'hour_of_day': datetime.now(timezone.utc).hour,
                        'day_of_week': datetime.now(timezone.utc).weekday(),
                    }
                    enhanced = ml.enhance_signal(base_signal, market_context)
                    final_conf = enhanced.get('enhanced_confidence', base_signal['confidence'])
                    action = base_signal['action'] if final_conf >= 60 else 'NO_TRADE'
                    confidence = final_conf if final_conf >= 60 else 0
                else:
                    action = 'NO_TRADE'
                    confidence = 0
                
                analyses[symbol] = {
                    "action": action,
                    "confidence": round(confidence, 1),
                    "market_data": market_data,
                    "market_regime": market_regime,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                analyses[symbol] = {"error": str(e)}
        
        return analyses
    
    def _render_charting_window(self):
        symbols = st.session_state.get('selected_symbols', [INSTRUMENT])
        
        if len(symbols) > 0:
            tabs = st.tabs(symbols)
            for i, symbol in enumerate(symbols):
                with tabs[i]:
                    chart_data = self._get_chart_data(symbol, "M1", 100)
                    
                    if chart_data is not None and not chart_data.empty:
                        fig = self._create_real_time_chart(chart_data, symbol)
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                        
                        analysis = st.session_state.get('market_analyses', {}).get(symbol, {})
                        last_price = chart_data['close'].iloc[-1] if len(chart_data) > 0 else 0
                        prev_price = chart_data['close'].iloc[-2] if len(chart_data) > 1 else last_price
                        price_change = last_price - prev_price
                        price_change_pct = (price_change / prev_price * 100) if prev_price != 0 else 0
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric(f"{symbol} Price", f"{last_price:.2f}", 
                                     f"{price_change:+.2f} ({price_change_pct:+.2f}%)")
                        with col2:
                            st.metric("Signal", analysis.get('action', 'NO_TRADE'))
                        with col3:
                            st.metric("Confidence", f"{analysis.get('confidence', 0)}%")
                    else:
                        st.error(f"Unable to load chart data for {symbol}.")
    
    def _create_real_time_chart(self, df: pd.DataFrame, symbol: str = "NAS100") -> go.Figure:
        try:
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                subplot_titles=(f'{symbol} Price Action', 'Volume'),
                row_width=[0.7, 0.3]
            )
            
            fig.add_trace(
                go.Candlestick(
                    x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'],
                    name=symbol,
                    increasing_line_color='green', decreasing_line_color='red'
                ),
                row=1, col=1
            )
            
            sma20 = df['close'].rolling(window=20).mean()
            sma50 = df['close'].rolling(window=50).mean()
            
            fig.add_trace(
                go.Scatter(x=df.index, y=sma20, mode='lines', name='SMA20',
                          line=dict(color='blue', width=1)), row=1, col=1
            )
            fig.add_trace(
                go.Scatter(x=df.index, y=sma50, mode='lines', name='SMA50',
                          line=dict(color='purple', width=1)), row=1, col=1
            )
            
            fig.add_trace(
                go.Bar(x=df.index, y=df['volume'], name='Volume',
                      marker_color='rgba(158,202,225,0.6)'), row=2, col=1
            )
            
            fig.update_layout(
                title=f"{symbol} Real-time Price Action",
                xaxis_rangeslider_visible=False, height=500, showlegend=True
            )
            fig.update_yaxes(title_text="Price (USD)", row=1, col=1)
            fig.update_yaxes(title_text="Volume", row=2, col=1)
            fig.update_layout(dragmode=False)
            
            return fig
        except Exception as e:
            logger.error(f"Error creating chart: {e}")
            return go.Figure()
    
    def _get_chart_data(self, symbol: str, timeframe: str, bars: int = 100) -> Optional[pd.DataFrame]:
        try:
            df = self.broker.get_historical_data(symbol, timeframe, bars)
            if df is None or df.empty:
                return pd.DataFrame()
            if 'time' in df.columns:
                df = df.set_index('time')
            return df
        except Exception as e:
            logger.error(f"Error getting chart data: {e}")
            return pd.DataFrame()
    
    def _render_agent_thought_process(self):
        st.subheader("🧠 Agent Thought Process Monitor")
        
        market_analyses = st.session_state.get('market_analyses', {})
        
        if not market_analyses:
            if st.session_state.get('is_running', False):
                st.info("Analysis running... waiting for data.")
            else:
                st.info("No analysis available. Select markets and click 'Analyze Now'.")
            return
        
        symbols = list(market_analyses.keys())
        if len(symbols) > 1:
            tabs = st.tabs(symbols)
        else:
            tabs = [st.container()]
        
        for i, symbol in enumerate(symbols):
            with (tabs[i] if len(tabs) > 1 else tabs[0]):
                analysis = market_analyses[symbol]
                if 'error' in analysis:
                    st.error(f"Error analyzing {symbol}: {analysis['error']}")
                    continue
                
                thought_process = []
                thought_process.append(f"[{analysis.get('timestamp', 'N/A')}] {symbol}")
                
                if 'market_data' in analysis:
                    md = analysis['market_data']
                    thought_process.append(f"[Market Intel] Signal: {md.get('signal', 'NONE')} ({md.get('confidence', 0)}%)")
                    thought_process.append(f"[Market Intel] M15={md.get('m15_trend')}, H4={md.get('h4_trend')}")
                
                thought_process.append(f"[Decision] Action: {analysis.get('action')}")
                thought_process.append(f"[Decision] Confidence: {analysis.get('confidence')}%")
                
                st.markdown(f'<div class="thought-process">{"<br>".join(thought_process)}</div>', unsafe_allow_html=True)
                
                action = analysis.get('action', 'NO_TRADE')
                if action == 'BUY':
                    st.markdown('<div class="signal-buy"><strong>🟢 BUY SIGNAL</strong></div>', unsafe_allow_html=True)
                elif action == 'SELL':
                    st.markdown('<div class="signal-sell"><strong>🔴 SELL SIGNAL</strong></div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="signal-neutral"><strong>⚪ NO TRADE</strong></div>', unsafe_allow_html=True)


def main():
    """Main function to render the dashboard"""
    page = st.sidebar.selectbox("Navigation", options=list(PAGES.keys()), format_func=lambda x: PAGES[x])
    
    if page == "backtest":
        render_backtest()
    else:
        dashboard = TradingDashboard()
        dashboard.render_dashboard()


if __name__ == "__main__":
    main()