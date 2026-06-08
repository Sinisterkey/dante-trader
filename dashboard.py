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
import time as time_module
import threading
from typing import Dict, List, Any, Optional
from telegram import Bot
from agents import TradingAgents
from config import INSTRUMENT, AVAILABLE_INSTRUMENTS
from trade_logger import TradeLogger
from performance_analytics import PerformanceAnalytics
from risk_engine import RiskEngine

logger = logging.getLogger(__name__)


class TradingDashboard:
    """Enhanced trading dashboard with advanced visualization"""
    
    def __init__(self):
        # Initialize broker for data and account operations
        from broker_integration import MT5Broker
        self.broker = MT5Broker()
        self.trading_agents = TradingAgents(self.broker)  # Pass broker to agents
        self.trade_logger = TradeLogger()
        self.performance_analytics = PerformanceAnalytics(self.trade_logger)
        self.risk_engine = RiskEngine(self.broker)  # Initialize with broker instance
        logger.info("Trading Dashboard initialized")
        """Start all trading systems"""
        try:
            # Start position manager
            self.trading_agents.position_manager.start()
            logger.info("Position manager started")
            
            # Log system start
            self.trade_logger.log_system_event("info", "Trading systems started", {})
            
        except Exception as e:
            logger.error(f"Error starting systems: {e}")
    
    def _stop_systems(self):
        """Stop all trading systems"""
        try:
            # Stop position manager
            self.trading_agents.position_manager.stop()
            logger.info("Position manager stopped")
            
            # Log system stop
            self.trade_logger.log_system_event("info", "Trading systems stopped", {})
            
        except Exception as e:
            logger.error(f"Error stopping systems: {e}")
    
    def _analysis_loop(self):
        """Background thread for continuous market analysis"""
        import streamlit as st
        import time as time_module
        from datetime import datetime, timezone
        import logging
        
        logger = logging.getLogger(__name__)
        
        # Initialize session state for this thread if needed
        if 'is_running' not in st.session_state:
            st.session_state.is_running = False
        if 'last_analysis' not in st.session_state:
            st.session_state.last_analysis = None
        if 'analysis_history' not in st.session_state:
            st.session_state.analysis_history = []
        if 'telegram_alerts_sent' not in st.session_state:
            st.session_state.telegram_alerts_sent = set()
        
        # Start systems when analysis begins
        if st.session_state.get('is_running', False) and not getattr(self, '_systems_started', False):
            self._start_systems()
            self._systems_started = True
        
        while st.session_state.get('is_running', False):
            try:
                # Perform analysis
                analysis = self.trading_agents.analyze_and_recommend()
                analysis['timestamp'] = datetime.now(timezone.utc).isoformat()
                
                # Update session state
                st.session_state.last_analysis = analysis
                st.session_state.analysis_history.append(analysis)
                
                # Keep only last 100 analyses
                if len(st.session_state.analysis_history) > 100:
                    st.session_state.analysis_history = st.session_state.analysis_history[-100:]
                
                # Execute trade if signal is valid
                if analysis.get('action') in ['BUY', 'SELL'] and analysis.get('confidence', 0) >= 70:
                    # Execute the signal
                    result = self.trading_agents.execute_signal(analysis)
                    
                    if result.get('success', False):
                        logger.info(f"Trade executed: {analysis['action']} at {analysis.get('entry_price')}")
                        # In a real implementation, we would send a Telegram alert here
                        # For now, we'll just log it
                        logger.info(f"Would send Telegram alert for {analysis['action']} signal")
                        if 'telegram_alerts_sent' not in st.session_state:
                            st.session_state.telegram_alerts_sent = set()
                        signal_id = f"{analysis['action']}_{analysis.get('entry_price', 0)}_{analysis['timestamp'][:16]}"
                        st.session_state.telegram_alerts_sent.add(signal_id)
                    else:
                        logger.warning(f"Trade execution failed: {result.get('error', 'Unknown error')}")
                
                # Wait before next analysis
                time_module.sleep(15)  # UPDATE_INTERVAL from config
                
            except Exception as e:
                logger.error(f"Error in analysis loop: {e}")
                time_module.sleep(15)
                
        # Stop systems when analysis ends
        if getattr(self, '_systems_started', False):
            self._stop_systems()
            self._systems_started = False
    
    def render_dashboard(self):
        """Render the main dashboard"""
        # Initialize session state for current symbol
        if 'current_symbol' not in st.session_state:
            st.session_state.current_symbol = INSTRUMENT
        if 'market_analyses' not in st.session_state:
            st.session_state.market_analyses = {}
        if 'selected_symbols' not in st.session_state:
            st.session_state.selected_symbols = [INSTRUMENT]  # Default to current symbol

        # Set page config
        st.set_page_config(
            page_title="Multi-Market Real-time Trading System",
            page_icon="📈",
            layout="wide",
            initial_sidebar_state="collapsed"
        )
        
        # Custom CSS for better styling - more trading platform like
        st.markdown("""
        <style>
        .main-header {
            font-size: 2.2rem;
            font-weight: bold;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 0.5rem;
        }
        .sub-header {
            font-size: 1.1rem;
            color: #666;
            text-align: center;
            margin-bottom: 1.5rem;
        }
        .metric-card {
            background-color: #f8f9fa;
            padding: 0.75rem;
            border-radius: 0.3rem;
            border-left: 3px solid #1f77b4;
            margin-bottom: 0.5rem;
        }
        .metric-value {
            font-size: 1.5rem;
            font-weight: bold;
        }
        .metric-label {
            font-size: 0.9rem;
            color: #666;
        }
        .signal-buy {
            background-color: #d4edda;
            color: #155724;
            padding: 0.75rem;
            border-radius: 0.3rem;
            border-left: 4px solid #28a745;
            text-align: center;
            margin: 0.5rem 0;
        }
        .signal-sell {
            background-color: #f8d7da;
            color: #721c24;
            padding: 0.75rem;
            border-radius: 0.3rem;
            border-left: 4px solid #dc3545;
            text-align: center;
            margin: 0.5rem 0;
        }
        .signal-neutral {
            background-color: #fff3cd;
            color: #856404;
            padding: 0.75rem;
            border-radius: 0.3rem;
            border-left: 4px solid #ffc107;
            text-align: center;
            margin: 0.5rem 0;
        }
        .thought-process {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 0.3rem;
            padding: 1rem;
            height: 300px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.85rem;
        }
        .stButton>button {
            width: 100%;
            margin: 0.25rem 0;
        }
        .buy-btn {
            background-color: #28a745;
            color: white;
            border: none;
        }
        .buy-btn:hover {
            background-color: #218838;
        }
        .sell-btn {
            background-color: #dc3545;
            color: white;
            border: none;
        }
        .sell-btn:hover {
            background-color: #c82333;
        }
        .status-live {
            color: #28a745;
            font-weight: bold;
        }
        .status-closed {
            color: #dc3545;
            font-weight: bold;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Header
        st.markdown(f'<h1 class="main-header">📈 Multi-Market Trading System</h1>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">Live Market Data • AI Agents • Parallel Analysis</p>', unsafe_allow_html=True)
        
        # Control panel - compact
        col1, col2, col3, col4 = st.columns([1.5, 1, 1, 1.5])
        
        with col1:
            # Multi-symbol selector
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
        
        # Initialize session state variables if they don't exist
        if 'last_analysis' not in st.session_state:
            st.session_state.last_analysis = None
        if 'analysis_history' not in st.session_state:
            st.session_state.analysis_history = []
        if 'is_running' not in st.session_state:
            st.session_state.is_running = False
        if 'telegram_alerts_sent' not in st.session_state:
            st.session_state.telegram_alerts_sent = set()
        if 'last_trade_time' not in st.session_state:
            st.session_state.last_trade_time = None
        
        # Main layout - chart takes most space
        col_chart, col_side = st.columns([3, 1])
        
        with col_chart:
            self._render_charting_window()
        
        with col_side:
            st.subheader("💰 Trading Controls")
            
            # Current signal display
            if 'last_analysis' in st.session_state and st.session_state.last_analysis is not None:
                analysis = st.session_state.last_analysis
                action = analysis.get('action', 'NO_TRADE')
                confidence = analysis.get('confidence', 0)
                
                if action == 'BUY':
                    st.markdown(f'<div class="signal-buy">🟢 BUY SIGNAL<br>Confidence: {confidence}%</div>', unsafe_allow_html=True)
                elif action == 'SELL':
                    st.markdown(f'<div class="signal-sell">🔴 SELL SIGNAL<br>Confidence: {confidence}%</div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="signal-neutral">⚪ NO TRADE<br>Confidence: {confidence}%</div>', unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                col_buy, col_sell = st.columns(2)
                
                with col_buy:
                    if st.button("🟢 BUY", key="buy_btn"):
                        if analysis.get('action') == 'BUY' and analysis.get('confidence', 0) >= 60:
                            with st.spinner("Executing BUY order..."):
                                result = self.trading_agents.execute_signal(analysis)
                                if result.get('success', False):
                                    st.success("BUY order executed!")
                                    st.session_state.last_trade_time = datetime.now(timezone.utc)
                                    st.rerun()
                                else:
                                    st.error(f"Order failed: {result.get('error', 'Unknown error')}")
                        else:
                            st.warning("No valid BUY signal or confidence too low")
                
                with col_sell:
                    if st.button("🔴 SELL", key="sell_btn"):
                        if analysis.get('action') == 'SELL' and analysis.get('confidence', 0) >= 60:
                            with st.spinner("Executing SELL order..."):
                                result = self.trading_agents.execute_signal(analysis)
                                if result.get('success', False):
                                    st.success("SELL order executed!")
                                    st.session_state.last_trade_time = datetime.now(timezone.utc)
                                    st.rerun()
                                else:
                                    st.error(f"Order failed: {result.get('error', 'Unknown error')}")
                        else:
                            st.warning("No valid SELL signal or confidence too low")
                
                if st.session_state.last_trade_time:
                    time_diff = (datetime.now(timezone.utc) - st.session_state.last_trade_time).total_seconds()
                    if time_diff < 60:
                        st.caption(f"Last trade: {int(time_diff)}s ago")
                    elif time_diff < 3600:
                        st.caption(f"Last trade: {int(time_diff/60)}m ago")
                    else:
                        st.caption(f"Last trade: {int(time_diff/3600)}h ago")
            
            st.markdown("<br>", unsafe_allow_html=True)
            self._render_agent_thought_process()
        
        # Footer
        st.markdown("---")
        st.markdown(
            f'<p style="text-align: center; color: #888; font-size: 0.85rem;">'
            f'Multi-Market Trading System | Last updated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")} UTC'
            f'</p>', 
            unsafe_allow_html=True
        )
        
        # Auto-analysis for selected markets (background, no flicker)
        if st.session_state.get('is_running', False):
            st.session_state.market_analyses = self._analyze_multiple_markets(st.session_state.selected_symbols)
    
    def _analyze_multiple_markets(self, symbols: List[str]) -> Dict[str, Any]:
        """Analyze multiple markets in parallel and store results separately"""
        analyses = {}
        for symbol in symbols:
            try:
                df_m15 = self.broker.get_historical_data(symbol, "M15", BARS_TO_FETCH)
                df_h4 = self.broker.get_historical_data(symbol, "H4", BARS_TO_FETCH)
                
                if df_m15 is None or df_h4 is None or df_m15.empty or df_h4.empty:
                    analyses[symbol] = {"error": "No data available"}
                    continue
                
                from market_intelligence import MarketIntelligence
                from ml_integration import MLIntegration
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
        """Render the charting window with real-time price data for all selected markets"""
        symbols = st.session_state.get('selected_symbols', [INSTRUMENT])
        
        # Create tabs for each symbol
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
                        st.error(f"Unable to load chart data for {symbol}. Please check your connection.")
    
    def _create_real_time_chart(self, df: pd.DataFrame, symbol: str = "NAS100") -> go.Figure:
        """Create a real-time chart (non-interactive)"""
        try:
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                subplot_titles=(f'{symbol} Real-time Price', 'Volume'),
                row_width=[0.7, 0.3]
            )
            
            # Main price chart - candlestick
            fig.add_trace(
                go.Candlestick(
                    x=df.index,
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name="NAS100",
                    increasing_line_color='green',
                    decreasing_line_color='red'
                ),
                row=1, col=1
            )
            
            # Add SMA20 and SMA50
            sma20 = df['close'].rolling(window=20).mean()
            sma50 = df['close'].rolling(window=50).mean()
            
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=sma20,
                    mode='lines',
                    name='SMA20',
                    line=dict(color='blue', width=1)
                ),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=sma50,
                    mode='lines',
                    name='SMA50',
                    line=dict(color='purple', width=1)
                ),
                row=1, col=1
            )
            
            # Volume chart
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df['volume'],
                    name='Volume',
                    marker_color='rgba(158,202,225,0.6)',
                    marker_line_color='rgb(8,48,107)',
                    marker_line_width=1
                ),
                row=2, col=1
            )
            
            # Update layout
            fig.update_layout(
                title=f"{symbol} Real-time Price Action (1-minute chart)",
                xaxis_rangeslider_visible=False,
                height=500,
                showlegend=True,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            
            # Update y-axis labels
            fig.update_yaxes(title_text="Price (USD)", row=1, col=1)
            fig.update_yaxes(title_text="Volume", row=2, col=1)
            
            # Remove range slider and make it non-interactive
            fig.update_layout(dragmode=False)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating real-time chart: {e}")
            # Return empty figure on error
            fig = go.Figure()
            fig.add_annotation(
                text="Error loading chart",
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="red")
            )
            return fig
    
    def _get_chart_data(self, symbol: str, timeframe: str, bars: int = 100) -> Optional[pd.DataFrame]:
        """Get chart data for visualization"""
        try:
            df = self.broker.get_historical_data(symbol, timeframe, bars)
            
            if df is None or df.empty:
                logger.warning(f"No data received for {symbol} {timeframe}")
                return pd.DataFrame()
            
            # Set time index for chart
            if 'time' in df.columns:
                df = df.set_index('time')
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting chart data: {e}")
            return pd.DataFrame()
    
    def _generate_mock_chart_data(self, timeframe: str, bars: int = 100) -> pd.DataFrame:
        """Generate mock chart data for demonstration"""
        try:
            # Create timestamps going back from now
            now = datetime.now(timezone.utc)
            if timeframe == "M1":
                delta = pd.Timedelta(minutes=1)
            elif timeframe == "M5":
                delta = pd.Timedelta(minutes=5)
            elif timeframe == "M15":
                delta = pd.Timedelta(minutes=15)
            elif timeframe == "M30":
                delta = pd.Timedelta(minutes=30)
            elif timeframe == "H1":
                delta = pd.Timedelta(hours=1)
            elif timeframe == "H4":
                delta = pd.Timedelta(hours=4)
            elif timeframe == "D1":
                delta = pd.Timedelta(days=1)
            else:
                delta = pd.Timedelta(minutes=15)  # default
                
            times = [now - i * delta for i in range(bars)]
            times.reverse()  # Oldest first
            
            # Generate realistic price data for NAS100
            base_price = 18000.0  # Approximate NAS100 level
            data = []
            
            for i, t in enumerate(times):
                # Add some random walk behavior with trend
                trend = 0.0001 * i  # Slight upward trend
                noise = np.random.normal(0, 0.008)  # 0.8% volatility
                
                if i == 0:
                    open_price = base_price
                else:
                    open_price = data[-1]['close']
                
                # Apply trend and noise
                close_price = open_price * (1 + trend + noise)
                
                # Ensure high/low are realistic
                high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, 0.004)))
                low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, 0.004)))
                volume = np.random.randint(500, 5000)
                
                data.append({
                    'time': t,
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume
                })
                
            df = pd.DataFrame(data)
            df.set_index('time', inplace=True)
            return df
            
        except Exception as e:
            logger.error(f"Error generating mock chart data: {e}")
            return pd.DataFrame()
    
    def _render_agent_thought_process(self):
        """Render the agent thought process monitor"""
        st.subheader("🧠 Agent Thought Process Monitor")
        
        # Get latest analysis from session state (updated by background loop)
        if 'last_analysis' in st.session_state and st.session_state.last_analysis is not None:
            analysis = st.session_state.last_analysis
            # Check how old the analysis is
            try:
                analysis_time = datetime.fromisoformat(analysis['timestamp'].replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                age_seconds = (now - analysis_time).total_seconds()
                if age_seconds > 60:  # older than 60 seconds
                    st.warning(f"Analysis is {age_seconds:.0f} seconds old. Consider restarting the analysis for updated data.")
                else:
                    st.success(f"Analysis updated {age_seconds:.0f} seconds ago")
            except:
                st.info("Analysis timestamp unavailable")
        else:
            st.info("No analysis available yet. Start the analysis to see the agent's thought process.")
            return
        
        # Create thought process display
        thought_process = []
        
        # Add timestamp
        thought_process.append(f"[{analysis.get('timestamp', 'N/A')}] Analysis started")
        
        # Add market intelligence thoughts
        if 'market_data' in analysis:
            market_data = analysis['market_data']
            thought_process.append(f"[Market Intelligence] {market_data.get('reason', 'No reason provided')}")
            thought_process.append(f"[Market Intelligence] Signal: {market_data.get('signal', 'NONE')} "
                                 f"(Confidence: {market_data.get('confidence', 0)}%)")
            thought_process.append(f"[Market Intelligence] Trend: M15={market_data.get('m15_trend', 'N/A')}, "
                                 f"H4={market_data.get('h4_trend', 'N/A')}, Aligned: {market_data.get('trend_aligned', False)}")
            thought_process.append(f"[Market Intelligence] Session: {market_data.get('session', 'UNKNOWN')}")
            thought_process.append(f"[Market Intelligence] Regime: {market_data.get('market_regime', 'UNKNOWN')}")
        
        # Add ML enhancement thoughts
        if 'ml_data' in analysis:
            ml_data = analysis['ml_data']
            thought_process.append(f"[ML Enhancement] Original confidence: {ml_data.get('original_confidence', 0)}%")
            thought_process.append(f"[ML Enhancement] ML success probability: {ml_data.get('ml_confidence', 0):.1f}%")
            thought_process.append(f"[ML Enhancement] Enhanced confidence: {ml_data.get('enhanced_confidence', 0):.1f}%")
            thought_process.append(f"[ML Enhancement] Expected P&L: {ml_data.get('ml_expected_profit', 0):.2f}")
        
        # Add final decision thoughts
        thought_process.append(f"[Decision Engine] Final action: {analysis.get('action', 'N/A')}")
        thought_process.append(f"[Decision Engine] Final confidence: {analysis.get('confidence', 0)}%")
        thought_process.append(f"[Decision Engine] Reasoning: {analysis.get('reasoning', 'No reasoning provided')}")
        
        # Add validation checks
        if 'validation_checks' in analysis:
            checks = analysis['validation_checks']
            thought_process.append(f"[Validation] Session valid: {checks.get('session_valid', False)}")
            thought_process.append(f"[Validation] Trend aligned: {checks.get('trend_aligned', False)}")
            thought_process.append(f"[Validation] Risk/reward adequate: {checks.get('risk_reward_adequate', False)}")
        
        # Display in text area
        thought_text = "\n".join(thought_process)
        st.markdown(f'<div class="thought-process">{thought_text.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
        
        # Display signal status prominently
        action = analysis.get('action', 'NO_TRADE')
        if action == 'BUY':
            st.markdown('<div class="signal-buy"><strong>🟢 BUY SIGNAL</strong></div>', unsafe_allow_html=True)
        elif action == 'SELL':
            st.markdown('<div class="signal-sell"><strong>🔴 SELL SIGNAL</strong></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="signal-neutral"><strong>⚪ NO TRADE</strong></div>', unsafe_allow_html=True)
    
    def _render_performance_metrics(self):
        """Render performance metrics panel"""
        st.subheader("📈 Performance Metrics")
        
        try:
            # Get performance metrics
            metrics = self.performance_analytics.calculate_advanced_metrics([])
            
            if metrics.get("total_trades", 0) == 0:
                st.info("No trade history available for performance metrics")
                return
            
            # Display metrics in cards
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Total Trades", f"{metrics.get('total_trades', 0)}")
                st.metric("Win Rate", f"{metrics.get('win_rate', 0):.1f}%")
                st.metric("Profit Factor", f"{metrics.get('profit_factor', 0):.2f}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Avg Profit", f"${metrics.get('avg_profit', 0):.2f}")
                st.metric("Avg Loss", f"${metrics.get('avg_loss', 0):.2f}")
                st.metric("Expectancy", f"${metrics.get('expectancy', 0):.2f}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Additional metrics
            col3, col4 = st.columns(2)
            
            with col3:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Max Drawdown", f"{metrics.get('max_drawdown', 0):.2f}%")
                st.metric("Sharpe Ratio", f"{metrics.get('sharpe_ratio', 0):.2f}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col4:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Sortino Ratio", f"{metrics.get('sortino_ratio', 0):.2f}")
                st.metric("Calmar Ratio", f"{metrics.get('calmar_ratio', 0):.2f}")
                st.markdown('</div>', unsafe_allow_html=True)
                
        except Exception as e:
            logger.error(f"Error rendering performance metrics: {e}")
            st.error(f"Error loading performance metrics: {str(e)}")
    
    def _render_risk_status(self):
        """Render risk status panel"""
        st.subheader("⚠️ Risk Status")
        
        try:
            # Get risk status
            risk_status = self.risk_engine.get_risk_status()
            
            if "error" in risk_status:
                st.error(f"Error loading risk status: {risk_status['error']}")
                return
            
            # Display risk metrics
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Account Equity", f"${risk_status.get('account_equity', 0):.2f}")
                st.metric("Peak Equity", f"${risk_status.get('peak_equity', 0):.2f}")
                st.metric("Current Drawdown", f"{risk_status.get('current_drawdown', 0):.2f}%")
                st.markdown('</div>', unsafe_allow_html=True)
            
            with col2:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Daily P&L", f"${risk_status.get('daily_pnl', 0):.2f}")
                st.metric("Daily Trades", f"{risk_status.get('daily_trades', 0)}")
                st.metric("Daily Loss Used", f"${risk_status.get('daily_loss_used', 0):.2f}")
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Risk status indicators
            col3, col4 = st.columns(2)
            
            with col3:
                can_trade = risk_status.get('can_trade', False)
                if can_trade:
                    st.success("✅ Trading Allowed")
                else:
                    st.error("❌ Trading Restricted")
                
                margin_level = risk_status.get('margin_level', 0)
                if margin_level > 500:
                    st.success(f"✅ Strong Margin Level: {margin_level:.0f}%")
                elif margin_level > 200:
                    st.warning(f"⚠️ Adequate Margin Level: {margin_level:.0f}%")
                else:
                    st.error(f"❌ Weak Margin Level: {margin_level:.0f}%")
            
            with col4:
                drawdown = risk_status.get('current_drawdown', 0)
                if drawdown < 5:
                    st.success(f"✅ Low Drawdown: {drawdown:.2f}%")
                elif drawdown < 15:
                    st.warning(f"⚠️ Moderate Drawdown: {drawdown:.2f}%")
                else:
                    st.error(f"❌ High Drawdown: {drawdown:.2f}%")
                
                daily_loss_pct = risk_status.get('daily_loss_percent', 0)
                if daily_loss_pct < 50:
                    st.success(f"✅ Daily Loss OK: {daily_loss_pct:.1f}%")
                elif daily_loss_pct < 80:
                    st.warning(f"⚠️ Daily Loss Warning: {daily_loss_pct:.1f}%")
                else:
                    st.error(f"❌ Daily Loss Critical: {daily_loss_pct:.1f}%")
                    
        except Exception as e:
            logger.error(f"Error rendering risk status: {e}")
            st.error(f"Error loading risk status: {str(e)}")
    
    def _render_trade_history(self):
        """Render trade history table"""
        st.subheader("📋 Recent Trade History")
        
        try:
            # Get recent trades
            trades = self.trade_logger.get_closed_trades(limit=20)
            
            if not trades:
                st.info("No trade history available")
                return
            
            # Prepare data for display
            display_data = []
            for trade in trades:
                display_data.append({
                    "Time": trade.get('exit_time', 'N/A')[:19] if trade.get('exit_time') else 'N/A',
                    "Symbol": trade.get('symbol', 'N/A'),
                    "Side": trade.get('side', 'N/A').upper(),
                    "Entry": f"{trade.get('entry_price', 0):.2f}",
                    "Exit": f"{trade.get('exit_price', 0):.2f}",
                    "P&L": f"{trade.get('pnl', 0):.2f}",
                    "%": f"{(trade.get('pnl', 0) / (trade.get('entry_price', 1) * trade.get('volume', 1)) * 100):.2f}",
                    "Confidence": f"{trade.get('confidence', 0)}%"
                })
            
            # Create DataFrame and display
            df = pd.DataFrame(display_data)
            
            # Style the dataframe
            def color_pnl(val):
                try:
                    num_val = float(val.replace('$', '')) if '$' in val else float(val)
                    color = 'green' if num_val > 0 else 'red' if num_val < 0 else 'black'
                    return f'color: {color}'
                except:
                    return ''
            
            styled_df = df.style.applymap(color_pnl, subset=['P&L'])
            st.dataframe(styled_df, use_container_width=True)
            
        except Exception as e:
            logger.error(f"Error rendering trade history: {e}")
            st.error(f"Error loading trade history: {str(e)}")


def render_dashboard():
    """Main function to render the dashboard"""
    dashboard = TradingDashboard()
    dashboard.render_dashboard()


# For direct execution
if __name__ == "__main__":
    render_dashboard()