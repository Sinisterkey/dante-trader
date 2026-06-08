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

PAGES = {"live": "Live Trading", "backtest": "Backtesting"}


def render_backtest():
    st.set_page_config(page_title="Strategy Backtesting", page_icon="📊", layout="wide")
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
        with st.spinner(f"Running backtest for {symbol}..."):
            results = run_backtest(symbol, days_back, timeframe)
            display_backtest_results(results, symbol)


def run_backtest(symbol: str, days: int, timeframe: str) -> Dict[str, Any]:
    try:
        from broker_integration import MT5Broker
        from market_intelligence import MarketIntelligence
        
        broker = MT5Broker()
        bars_needed = min(5000, days * 24 * 4 if timeframe == "H1" else days * 24 * 2 if timeframe == "M30" else days * 24 if timeframe == "M15" else days * 6)
        df = broker.get_historical_data(symbol, timeframe, bars_needed)
        
        if df is None or df.empty:
            return {"error": f"No data for {symbol}"}
        
        if 'time' in df.columns:
            df = df.set_index('time')
        
        mi = MarketIntelligence()
        signals, wins, losses, total_pnl, total_trades = [], 0, 0, 0.0, 0
        
        for i in range(50, len(df) - 5):
            try:
                chunk = df.iloc[max(0, i-50):i]
                sma = mi.calculate_sma(chunk, 50)
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
                if bullish and df['close'].iloc[i] > df['high'].iloc[i-3:i].max():
                    signal, direction = "BUY", 1
                elif bearish and df['close'].iloc[i] < df['low'].iloc[i-3:i].min():
                    signal, direction = "SELL", -1
                
                if signal:
                    future_move = (next_prices.iloc[-1] - current_price) * direction
                    signals.append({"time": str(df.index[i])[:19], "signal": signal, "entry": round(current_price, 2),
                                   "exit": round(next_prices.iloc[-1], 2), "pnl": round(future_move, 2)})
                    if future_move > 0: wins += 1
                    else: losses += 1
                    total_pnl += future_move
                    total_trades += 1
            except: continue
        
        return {"symbol": symbol, "signals": signals[-100:], "total_trades": total_trades, "wins": wins,
                "losses": losses, "win_rate": wins / total_trades if total_trades > 0 else 0,
                "total_pnl": round(total_pnl, 2), "avg_pnl": round(total_pnl / total_trades, 2) if total_trades > 0 else 0}
    except Exception as e:
        return {"error": str(e)}


def display_backtest_results(results: Dict[str, Any], symbol: str):
    if "error" in results:
        st.error(results["error"])
        return
    
    st.subheader(f"Backtest Results: {symbol}")
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Total Trades", results["total_trades"])
    with col2: st.metric("Win Rate", f"{results['win_rate']*100:.1f}%")
    with col3: st.metric("Wins", results["wins"])
    with col4: st.metric("Losses", results["losses"])
    st.metric("Total P&L", f"${results['total_pnl']:.2f}")
    st.metric("Avg P&L", f"${results['avg_pnl']:.2f}")
    
    if results["signals"]:
        df_signals = pd.DataFrame(results["signals"])
        st.dataframe(df_signals, use_container_width=True)
        
        # Candlestick chart with trade markers
        try:
            from broker_integration import MT5Broker
            broker = MT5Broker()
            chart_df = broker.get_historical_data(symbol, "M15", 200)
            if chart_df is not None and not chart_df.empty and 'time' in chart_df.columns:
                chart_df = chart_df.set_index('time')
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03)
                fig.add_trace(go.Candlestick(x=chart_df.index, open=chart_df['open'], high=chart_df['high'],
                                            low=chart_df['low'], close=chart_df['close']), row=1, col=1)
                fig.update_layout(height=400, showlegend=False, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
        except: pass


class TradingDashboard:
    def __init__(self):
        from broker_integration import MT5Broker
        self.broker = MT5Broker()
        self.trading_agents = TradingAgents(self.broker)
        self.trade_logger = TradeLogger()
        self.performance_analytics = PerformanceAnalytics(self.trade_logger)
        self.risk_engine = RiskEngine(self.broker)
    
    def render_dashboard(self):
        if 'market_analyses' not in st.session_state: st.session_state.market_analyses = {}
        if 'selected_symbols' not in st.session_state: st.session_state.selected_symbols = [INSTRUMENT]
        
        st.markdown("""<style>
        .signal-buy {background-color:#d4edda;color:#155724;padding:0.5rem;border-radius:0.3rem;margin:0.2rem 0;}
        .signal-sell {background-color:#f8d7da;color:#721c24;padding:0.5rem;border-radius:0.3rem;margin:0.2rem 0;}
        .signal-neutral {background-color:#fff3cd;color:#856404;padding:0.5rem;border-radius:0.3rem;margin:0.2rem 0;}
        .thought-process {background-color:#f8f9fa;border:1px solid #dee2e6;border-radius:0.3rem;padding:1rem;max-height:250px;overflow-y:auto;font-family:monospace;font-size:0.8rem;}
        </style>""", unsafe_allow_html=True)
        
        st.title("📈 Multi-Market Trading System")
        
        col1, col2, col3, col4 = st.columns([1.5, 1, 1, 1])
        with col1:
            selected = st.multiselect("Markets", options=AVAILABLE_INSTRUMENTS,
                                   default=st.session_state.get('selected_symbols', [INSTRUMENT]))
            st.session_state.selected_symbols = selected
        with col2:
            if st.button("▶️ Start All" if not st.session_state.get('is_running', False) else "⏸️ Stop All"):
                st.session_state.is_running = not st.session_state.get('is_running', False)
                st.info("Analysis started!" if st.session_state.is_running else "Analysis stopped.")
        with col3:
            if st.button("🔄 Analyze Now"):
                analyses = self._analyze_multiple_markets(selected)
                st.session_state.market_analyses = analyses
        with col4:
            st.markdown(f"**Session:** {'🟢 LIVE' if self.trading_agents.market_intel.is_london_ny_overlap() else '🔴 CLOSED'}")
        
        c1, c2 = st.columns([3, 1])
        with c1: self._render_charting_window()
        with c2: self._render_agent_thought_process()
        
        if st.session_state.get('is_running', False):
            st.session_state.market_analyses = self._analyze_multiple_markets(selected)
    
    def _analyze_multiple_markets(self, symbols):
        analyses = {}
        from market_intelligence import MarketIntelligence
        from ml_integration import MLIntegration
        
        for symbol in symbols:
            try:
                df_m15 = self.broker.get_historical_data(symbol, "M15", 200)
                df_h4 = self.broker.get_historical_data(symbol, "H4", 200)
                
                if df_m15 is None or df_h4 is None or df_m15.empty or df_h4.empty:
                    analyses[symbol] = {"error": "No data", "timeframe": "M15"}
                    continue
                
                mi = MarketIntelligence()
                ml = MLIntegration()
                market_data = mi.generate_signal(df_m15, df_h4)
                
                base = {'action': market_data.get('signal'), 'confidence': market_data.get('confidence', 0)}
                if base['action'] in ['BUY', 'SELL'] and base['confidence'] > 0:
                    ctx = {'rsi': market_data.get('rsi', 50.0), 'macd': market_data.get('macd', {}),
                           'hour_of_day': datetime.now(timezone.utc).hour, 'day_of_week': datetime.now(timezone.utc).weekday()}
                    enh = ml.enhance_signal(base, ctx)
                    fc = enh.get('enhanced_confidence', base['confidence'])
                    act, conf = (base['action'], fc) if fc >= 60 else ('NO_TRADE', 0)
                else:
                    act, conf = 'NO_TRADE', 0
                
                analyses[symbol] = {"action": act, "confidence": round(conf, 1), "market_data": market_data,
                                  "timestamp": datetime.now(timezone.utc).isoformat(), "timeframe": "M15"}
            except Exception as e:
                analyses[symbol] = {"error": str(e), "timeframe": "M15"}
        return analyses
    
    def _render_charting_window(self):
        symbols = st.session_state.get('selected_symbols', [INSTRUMENT])
        if len(symbols) > 0:
            tabs = st.tabs(symbols)
            for i, symbol in enumerate(symbols):
                with tabs[i]:
                    df = self._get_chart_data(symbol, "M1", 100)
                    if df is not None and not df.empty:
                        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03)
                        fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'],
                                                     low=df['low'], close=df['close']), row=1, col=1)
                        fig.update_layout(height=400, showlegend=False, xaxis_rangeslider_visible=False)
                        st.plotly_chart(fig, use_container_width=True)
                        
                        a = st.session_state.market_analyses.get(symbol, {})
                        p = df['close'].iloc[-1] if len(df) > 0 else 0
                        st.metric(f"{symbol}", f"{p:.2f}")
                        st.metric("Signal", a.get('action', 'NO_TRADE'))
                        st.metric("Confidence", f"{a.get('confidence', 0)}%")
                    else:
                        st.error(f"No data for {symbol}")
    
    def _get_chart_data(self, symbol, timeframe, bars=100):
        try:
            df = self.broker.get_historical_data(symbol, timeframe, bars)
            if df is None or df.empty: return pd.DataFrame()
            if 'time' in df.columns: df = df.set_index('time')
            return df
        except: return pd.DataFrame()
    
    def _render_agent_thought_process(self):
        st.subheader("🧠 Agent Thought Process")
        
        col_refresh, col_tf = st.columns([1, 2])
        with col_refresh:
            if st.button("🔄 Refresh Process"):
                st.session_state.market_analyses = self._analyze_multiple_markets(st.session_state.get('selected_symbols', [INSTRUMENT]))
        with col_tf:
            tf = st.session_state.get('analysis_timeframe', 'M15')
            st.markdown(f"**Timeframe:** {tf}")
        
        ma = st.session_state.get('market_analyses', {})
        if not ma:
            st.info("No analysis available. Click 'Analyze Now'.")
            return
        
        syms = list(ma.keys())
        tabs = st.tabs(syms) if len(syms) > 1 else [st.container()]
        
        for i, sym in enumerate(syms):
            with (tabs[i] if len(tabs) > 1 else tabs[0]):
                ana = ma[sym]
                if 'error' in ana:
                    st.error(f"{sym}: {ana['error']}")
                    continue
                
                tp = [f"[{ana.get('timestamp', 'N/A')}] {sym}", f"TF: {ana.get('timeframe', 'M15')}"]
                if 'market_data' in ana:
                    md = ana['market_data']
                    tp.append(f"Signal: {md.get('signal')} ({md.get('confidence')}%)")
                    tp.append(f"Trend: {md.get('m15_trend')}/{md.get('h4_trend')}")
                tp.append(f"Action: {ana.get('action')}, Conf: {ana.get('confidence')}%")
                
                st.markdown(f'<div class="thought-process">{"<br>".join(tp)}</div>', unsafe_allow_html=True)
                
                act = ana.get('action', 'NO_TRADE')
                if act == 'BUY': st.markdown('<div class="signal-buy"><strong>🟢 BUY</strong></div>', unsafe_allow_html=True)
                elif act == 'SELL': st.markdown('<div class="signal-sell"><strong>🔴 SELL</strong></div>', unsafe_allow_html=True)
                else: st.markdown('<div class="signal-neutral"><strong>⚪ NO TRADE</strong></div>', unsafe_allow_html=True)


def main():
    page = st.sidebar.selectbox("Navigation", options=list(PAGES.keys()), format_func=lambda x: PAGES[x])
    if page == "backtest":
        render_backtest()
    else:
        TradingDashboard().render_dashboard()


if __name__ == "__main__":
    main()