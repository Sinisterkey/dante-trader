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
from ml_integration import MLIntegration

logger = logging.getLogger(__name__)

PAGES = {"live": "Live Trading", "backtest": "Multi-Timeframe Testing", "ml_train": "ML Training Studio"}

ALL_TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H2", "H4", "D1"]


def render_backtest():
    st.set_page_config(page_title="Multi-Timeframe Testing", page_icon="📊", layout="wide")
    st.title("📊 Multi-Timeframe Testing Lab")
    st.markdown("Test all timeframes simultaneously and compare performance")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        symbol = st.selectbox("Symbol", options=AVAILABLE_INSTRUMENTS, index=0)
    with col2:
        days_back = st.number_input("Days to Analyze", min_value=30, max_value=730, value=90, step=30)
    
    # Multi-timeframe selector
    st.subheader("Select Timeframes to Test")
    selected_tfs = st.multiselect("Timeframes", options=ALL_TIMEFRAMES, default=["M15", "H1", "H4"], key="tf_select")
    
    if st.button("🚀 Run Multi-Timeframe Test"):
        with st.spinner(f"Testing {len(selected_tfs)} timeframes for {symbol}..."):
            results = run_multi_tf_backtest(symbol, days_back, selected_tfs)
            display_multi_tf_results(results, symbol)
    
    if st.button("📈 Compare All Timeframes Performance"):
        st.session_state.tf_performance = get_tf_performance_history(symbol, ALL_TIMEFRAMES, days_back)
    
    if st.session_state.get('tf_performance'):
        display_tf_performance_chart(st.session_state.get('tf_performance'))


def run_multi_tf_backtest(symbol: str, days: int, timeframes: List[str]) -> Dict[str, Any]:
    """Run backtest across multiple timeframes"""
    results = {"symbol": symbol, "timeframes": {}, "comparison": {}}
    
    for tf in timeframes:
        try:
            tf_result = run_backtest(symbol, days, tf)
            results["timeframes"][tf] = tf_result
            
            if "error" not in tf_result and tf_result["total_trades"] > 0:
                results["comparison"][tf] = {
                    "win_rate": tf_result["win_rate"],
                    "total_pnl": tf_result["total_pnl"],
                    "total_trades": tf_result["total_trades"],
                    "avg_pnl": tf_result["avg_pnl"],
                    "pnl_per_day": tf_result["total_pnl"] / days if days > 0 else 0
                }
        except Exception as e:
            results["timeframes"][tf] = {"error": str(e)}
    
    return results


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


def get_tf_performance_history(symbol: str, timeframes: List[str], days: int) -> Dict[str, Any]:
    """Get historical performance across all timeframes using real backtest data"""
    performance = {}
    for tf in timeframes:
        try:
            result = run_backtest(symbol, days, tf)
            if "error" not in result and result["total_trades"] > 5:
                performance[tf] = {
                    "win_rate": result["win_rate"],
                    "total_pnl": result["total_pnl"],
                    "total_trades": result["total_trades"],
                    "sharpe": result["avg_pnl"] / abs(result.get("max_drawdown", 100)) if result.get("max_drawdown", 100) != 0 else 0
                }
        except Exception as e:
            performance[tf] = {"error": str(e)}
    return performance


def display_tf_performance_chart(performance: Dict[str, Any]):
    """Display performance chart for all timeframes"""
    if not performance:
        return
    
    df_perf = pd.DataFrame(performance).T
    st.subheader("📈 Timeframe Performance History")
    
    fig = px.bar(df_perf.reset_index(), x='index', y='win_rate', color='win_rate',
                 labels={'index': 'Timeframe', 'win_rate': 'Win Rate'},
                 color_continuous_scale=['red', 'yellow', 'green'])
    st.plotly_chart(fig, use_container_width=True)


def render_ml_training():
    st.set_page_config(page_title="ML Training Studio", page_icon="🤖", layout="wide")
    st.title("🤖 ML Training Studio")
    st.markdown("Train and analyze ML models with real trading data")
    
    # Initialize ML integration
    ml = MLIntegration()
    from train_ml import train_initial_models
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("Training Controls")
        if st.button("🚀 Train Initial Models (Synthetic Data)"):
            with st.spinner("Training initial models..."):
                result = train_initial_models()
                st.success(f"Models trained! Accuracy: {result.get('signal_accuracy', 0):.1%}")
        
        if st.button("🔁 Retrain with Real Trades"):
            with st.spinner("Fetching trade data and retraining..."):
                result = ml.train_models()
                if result.get('success'):
                    st.success(f"Retrained! Samples: {result.get('samples_used', 0)}, Accuracy: {result.get('signal_accuracy', 0):.1%}")
                else:
                    st.warning(f"Cannot retrain: {result.get('reason', result.get('error', 'Unknown'))}")
    
    with col2:
        st.subheader("Model Status")
        if ml.signal_classifier:
            st.success("✅ Signal Classifier: Loaded")
            if ml.signal_feature_importance:
                st.write("**Feature Importance (Signal):**")
                sorted_imp = sorted(ml.signal_feature_importance.items(), key=lambda x: x[1], reverse=True)
                for feat, imp in sorted_imp[:5]:
                    st.progress(imp, text=f"{feat}: {imp:.3f}")
        else:
            st.warning("⚠️ Signal Classifier: Not trained")
        
        if ml.profit_regressor:
            st.success("✅ Profit Regressor: Loaded")
            if ml.profit_feature_importance:
                st.write("**Feature Importance (Profit):**")
                sorted_imp = sorted(ml.profit_feature_importance.items(), key=lambda x: x[1], reverse=True)
                for feat, imp in sorted_imp[:5]:
                    st.progress(imp, text=f"{feat}: {imp:.3f}")
        else:
            st.warning("⚠️ Profit Regressor: Not trained")
    
    st.subheader("💡 Feature Definitions")
    features_info = {
        "confidence": "Signal confidence (0-100%)",
        "rsi": "Relative Strength Index (0-100)",
        "macd": "MACD momentum indicator",
        "bb_position": "Price position within Bollinger Bands (0-1)",
        "atr_normalized": "Normalized Average True Range (volatility)",
        "volume_ratio": "Volume vs average ratio",
        "price_vs_sma20": "Price vs 20-period SMA difference (%)",
        "price_vs_sma50": "Price vs 50-period SMA difference (%)",
        "hour_of_day": "Trading hour (0-23)",
        "day_of_week": "Day of week (0-6)",
        "session": "Market session (0=Asian, 0.5=NY overlap, 1=US)",
        "volatility_regime": "High/Low volatility flag (0/1)",
        "trend_alignment": "H1/M15 trend alignment (0/1)"
    }
    
    cols = st.columns(3)
    for i, (feat, desc) in enumerate(features_info.items()):
        with cols[i % 3]:
            st.markdown(f"**{feat}**: {desc}")
    
    st.subheader("📊 Training Data Requirements")
    st.info(f"- Minimum trades needed: {50} (from config ML_TRAINING_THRESHOLD)")
    st.info("- Models use RandomForestClassifier and RandomForestRegressor")
    st.info("- Features are scaled with StandardScaler")
    st.info("- Predictions blended: 70% base confidence + 30% ML prediction")


def display_multi_tf_results(results: Dict[str, Any], symbol: str):
    """Display multi-timeframe comparison results"""
    if "error" in results:
        st.error(results["error"])
        return
    
    comparison = results.get("comparison", {})
    if not comparison:
        st.warning("No valid results to compare")
        return
    
    st.subheader(f"📊 Timeframe Comparison: {symbol}")
    
    df_comp = pd.DataFrame(comparison).T.sort_values("win_rate", ascending=False)
    
    best_tf = df_comp.index[0]
    st.success(f"🏆 Best performing: **{best_tf}** (Win Rate: {df_comp.loc[best_tf, 'win_rate']*100:.1f}%)")
    
    cols = st.columns(len(comparison))
    for i, tf in enumerate(df_comp.index):
        with cols[i]:
            data = df_comp.loc[tf].to_dict()
            is_best = "🥇" if i == 0 else ""
            st.metric(f"{tf} {is_best}", f"{data['win_rate']*100:.1f}% WR", 
                     f"${data['total_pnl']:.0f} P&L")
    
    st.dataframe(
        df_comp.style.format({
            "win_rate": "{:.1%}",
            "total_pnl": "${:.2f}",
            "avg_pnl": "${:.2f}",
            "pnl_per_day": "${:.2f}"
        }),
        use_container_width=True
    )


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
        if 'selected_tfs' not in st.session_state: st.session_state.selected_tfs = ["M15", "H1"]
        if 'tf_performance' not in st.session_state: st.session_state.tf_performance = {}
        
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
        
        # Get selected timeframes
        selected_tfs = st.session_state.get('selected_tfs', ['M15', 'H1'])
        
        for symbol in symbols:
            try:
                # Collect data for multiple timeframes
                tf_data = {}
                bars_needed = {tf: min(500, 96 * 30) for tf in ['M15', 'H1', 'H4']}
                for tf in selected_tfs:
                    bars = bars_needed.get(tf, 200) if tf in bars_needed else 200
                    tf_data[tf] = self.broker.get_historical_data(symbol, tf, bars)
                
                # Check if we have at least M15 and H4 data
                df_m15 = tf_data.get("M15")
                df_h4 = tf_data.get("H4")
                
                if df_m15 is None or df_h4 is None or df_m15.empty or df_h4.empty:
                    analyses[symbol] = {"error": "No data", "timeframes_tested": list(tf_data.keys())}
                    continue
                
                mi = MarketIntelligence()
                ml = MLIntegration()
                market_data = mi.generate_signal(df_m15, df_h4)
                
                # Quick TF performance test
                tf_perf = {}
                for tf, df in tf_data.items():
                    if df is not None and not df.empty and len(df) > 50:
                        tf_perf[tf] = self._quick_tf_test(df, mi)
                
                base = {'action': market_data.get('signal'), 'confidence': market_data.get('confidence', 0)}
                if base['action'] in ['BUY', 'SELL'] and base['confidence'] > 0:
                    macd_val = market_data.get('macd', {}).get('macd', 0.0) if isinstance(market_data.get('macd'), dict) else 0.0
                    ctx = {'rsi': market_data.get('rsi', 50.0), 'macd': macd_val,
                           'bb_position': market_data.get('bb_position', 0.5),
                           'atr_normalized': market_data.get('atr_normalized', 0.01),
                           'volume_ratio': market_data.get('volume_ratio', 1.0),
                           'price_vs_sma20': market_data.get('price_vs_sma20', 0.0),
                           'price_vs_sma50': market_data.get('price_vs_sma50', 0.0),
                           'hour_of_day': datetime.now(timezone.utc).hour,
                           'day_of_week': datetime.now(timezone.utc).weekday(),
                           'session': 0.5 if mi.is_london_ny_overlap(datetime.now(timezone.utc)) else 0.0,
                           'volatility_regime': 0.5 if 'high_vol' in mi.detect_market_regime(df_m15) else 0.0,
                           'trend_alignment': 1.0 if market_data.get('trend_aligned') else 0.0}
                    enh = ml.enhance_signal(base, ctx)
                    fc = enh.get('enhanced_confidence', base['confidence'])
                    act, conf = (base['action'], fc) if fc >= 60 else ('NO_TRADE', 0)
                else:
                    act, conf = 'NO_TRADE', 0
                
                analyses[symbol] = {
                    "action": act, "confidence": round(conf, 1), "market_data": market_data,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "timeframes_tested": selected_tfs,
                    "tf_performance": tf_perf
                }
            except Exception as e:
                analyses[symbol] = {"error": str(e)}
        return analyses
    
    def _quick_tf_test(self, df: pd.DataFrame, mi: MarketIntelligence) -> Dict[str, Any]:
        """Quick performance estimate on timeframe"""
        wins, total = 0, 0
        for i in range(20, min(50, len(df) - 5)):
            try:
                sma = mi.calculate_sma(df.iloc[:i], 20)
                if sma is None: continue
                price_move = df['close'].iloc[i+5:i+10].mean() - df['close'].iloc[i]
                if df['close'].iloc[i] > sma and price_move > 0: wins += 1
                elif df['close'].iloc[i] < sma and price_move < 0: wins += 1
                total += 1
            except: pass
        return {"quick_winrate": wins / total if total > 0 else 0, "sample_size": total}
    
    def _render_charting_window(self):
        symbols = st.session_state.get('selected_symbols', [INSTRUMENT])
        if len(symbols) > 0:
            tabs = st.tabs(symbols)
            for i, symbol in enumerate(symbols):
                with tabs[i]:
                    df = self._get_chart_data(symbol, "M5", 100)
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
                        
                        # Show TF performance
                        tf_perf = a.get('tf_performance', {})
                        if tf_perf:
                            st.caption("TF Quick Winrates:")
                            for tf, perf in tf_perf.items():
                                st.caption(f"  {tf}: {perf.get('quick_winrate', 0)*100:.0f}%")
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
            tfs = st.session_state.get('selected_tfs', ['M15'])
            st.markdown(f"**Timeframes:** {', '.join(tfs)}")
        
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
                
                tp = [f"[{ana.get('timestamp', 'N/A')}] {sym}", f"TFs: {', '.join(ana.get('timeframes_tested', ['M15']))}"]
                if 'market_data' in ana:
                    md = ana['market_data']
                    tp.append(f"Signal: {md.get('signal')} ({md.get('confidence')}%)")
                    tp.append(f"Trend: {md.get('m15_trend')}/{md.get('h4_trend')}")
                tp.append(f"Action: {ana.get('action')}, Conf: {ana.get('confidence')}%")
                
                # Collaborative agents data
                tf_perf = ana.get('tf_performance', {})
                if tf_perf:
                    tp.append("TF Performance:")
                    for tf, perf in sorted(tf_perf.items(), key=lambda x: x[1].get('quick_winrate', 0), reverse=True):
                        tp.append(f"  {tf}: {perf.get('quick_winrate', 0)*100:.0f}% WR")
                
                st.markdown(f'<div class="thought-process">{"<br>".join(tp)}</div>', unsafe_allow_html=True)
                
                act = ana.get('action', 'NO_TRADE')
                if act == 'BUY': st.markdown('<div class="signal-buy"><strong>🟢 BUY</strong></div>', unsafe_allow_html=True)
                elif act == 'SELL': st.markdown('<div class="signal-sell"><strong>🔴 SELL</strong></div>', unsafe_allow_html=True)
                else: st.markdown('<div class="signal-neutral"><strong>⚪ NO TRADE</strong></div>', unsafe_allow_html=True)


def main():
    page = st.sidebar.selectbox("Navigation", options=list(PAGES.keys()), format_func=lambda x: PAGES[x])
    if page == "backtest":
        render_backtest()
    elif page == "ml_train":
        render_ml_training()
    else:
        TradingDashboard().render_dashboard()


if __name__ == "__main__":
    main()