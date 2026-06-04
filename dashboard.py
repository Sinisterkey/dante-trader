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
from agents import TradingAgents
from config import *
from trade_logger import TradeLogger
from performance_analytics import PerformanceAnalytics
from risk_engine import RiskEngine

logger = logging.getLogger(__name__)


class TradingDashboard:
    """Enhanced trading dashboard with advanced visualization"""
    
    def __init__(self):
        self.trading_agents = TradingAgents()
        self.trade_logger = TradeLogger()
        self.performance_analytics = PerformanceAnalytics(self.trade_logger)
        self.risk_engine = RiskEngine(None)  # Will be initialized with broker later
        logger.info("Trading Dashboard initialized")
    
    def render_dashboard(self):
        """Render the main dashboard"""
        # Set page config
        st.set_page_config(
            page_title="NAS100 Algorithmic Trading System",
            page_icon="📈",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
        # Custom CSS for better styling
        st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f77b4;
            text-align: center;
            margin-bottom: 1rem;
        }
        .metric-card {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 0.5rem;
            border-left: 4px solid #1f77b4;
        }
        .signal-buy {
            background-color: #d4edda;
            color: #155724;
            padding: 0.5rem;
            border-radius: 0.25rem;
            border-left: 4px solid #28a745;
        }
        .signal-sell {
            background-color: #f8d7da;
            color: #721c24;
            padding: 0.5rem;
            border-radius: 0.25rem;
            border-left: 4px solid #dc3545;
        }
        .signal-neutral {
            background-color: #fff3cd;
            color: #856404;
            padding: 0.5rem;
            border-radius: 0.25rem;
            border-left: 4px solid #ffc107;
        }
        .thought-process {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 0.5rem;
            padding: 1rem;
            height: 400px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Header
        st.markdown('<h1 class="main-header">📈 NAS100 Algorithmic Trading System</h1>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; color: #666;">Powered by AI Agents & Advanced Analytics</p>', unsafe_allow_html=True)
        
        # Main layout
        col1, col2 = st.columns([2, 1])
        
        with col1:
            self._render_charting_window()
        
        with col2:
            self._render_agent_thought_process()
        
        # Second row
        col3, col4 = st.columns([1, 1])
        
        with col3:
            self._render_performance_metrics()
        
        with col4:
            self._render_risk_status()
        
        # Third row - full width
        self._render_trade_history()
        
        # Footer
        st.markdown("---")
        st.markdown(
            f'<p style="text-align: center; color: #888; font-size: 0.9rem;">'
            f'NAS100 Algorithmic Trading System | Last updated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")} UTC'
            f'</p>', 
            unsafe_allow_html=True
        )
    
    def _render_charting_window(self):
        """Render the interactive charting window"""
        st.subheader("📊 Interactive Charting Window")
        
        # Chart controls
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            timeframe = st.selectbox(
                "Timeframe",
                options=["M1", "M5", "M15", "M30", "H1", "H4", "D1"],
                index=2,  # Default to M15
                key="chart_timeframe"
            )
        
        with col2:
            chart_type = st.selectbox(
                "Chart Type",
                options=["Candlestick", "OHLC", "Line"],
                index=0,
                key="chart_type"
            )
        
        with col3:
            show_indicators = st.multiselect(
                "Indicators",
                options=["SMA20", "SMA50", "EMA20", "EMA50", "RSI", "MACD", "Bollinger Bands"],
                default=["SMA20", "SMA50"],
                key="chart_indicators"
            )
        
        # Get market data for charting
        # In a real implementation, this would come from the broker
        # For now, we'll use mock data or try to get real data
        chart_data = self._get_chart_data(timeframe, 100)  # 100 bars
        
        if chart_data is not None and not chart_data.empty:
            # Create the chart
            fig = self._create_chart(chart_data, chart_type, show_indicators)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No chart data available. Please check your data connection.")
    
    def _get_chart_data(self, timeframe: str, bars: int = 100) -> Optional[pd.DataFrame]:
        """Get chart data for visualization"""
        try:
            # Try to get data from a mock market intelligence instance
            # In a real system, this would come from the broker
            market_intel = MarketIntelligence()
            
            # Map timeframe to our internal representation
            # For simplicity, we'll use M15 data regardless of selection for mock data
            # In a real implementation, we'd query the broker for the specific timeframe
            df = market_intel.broker.fetch_symbol_data(INSTRUMENT, timeframe, bars) if hasattr(market_intel, 'broker') else None
            
            if df is None or df.empty:
                # Generate mock data for demonstration
                df = self._generate_mock_chart_data(timeframe, bars)
            
            return df
            
        except Exception as e:
            logger.error(f"Error getting chart data: {e}")
            return self._generate_mock_chart_data(timeframe, bars)
    
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
    
    def _create_chart(self, df: pd.DataFrame, chart_type: str, indicators: List[str]) -> go.Figure:
        """Create the interactive chart"""
        try:
            # Create subplots: main chart and volume
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                subplot_titles=('NAS100 Price Chart', 'Volume'),
                row_width=[0.7, 0.3]
            )
            
            # Main price chart
            if chart_type == "Candlestick":
                fig.add_trace(
                    go.Candlestick(
                        x=df.index,
                        open=df['open'],
                        high=df['high'],
                        low=df['low'],
                        close=df['close'],
                        name="Price"
                    ),
                    row=1, col=1
                )
            elif chart_type == "OHLC":
                fig.add_trace(
                    go.Ohlc(
                        x=df.index,
                        open=df['open'],
                        high=df['high'],
                        low=df['low'],
                        close=df['close'],
                        name="Price"
                    ),
                    row=1, col=1
                )
            elif chart_type == "Line":
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df['close'],
                        mode='lines',
                        name='Close',
                        line=dict(color='blue', width=2)
                    ),
                    row=1, col=1
                )
            
            # Add indicators
            colors = ['orange', 'purple', 'brown', 'pink', 'gray', 'black', 'red']
            color_idx = 0
            
            if "SMA20" in indicators:
                sma20 = df['close'].rolling(window=20).mean()
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=sma20,
                        mode='lines',
                        name='SMA20',
                        line=dict(color=colors[color_idx % len(colors)], width=1)
                    ),
                    row=1, col=1
                )
                color_idx += 1
            
            if "SMA50" in indicators:
                sma50 = df['close'].rolling(window=50).mean()
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=sma50,
                        mode='lines',
                        name='SMA50',
                        line=dict(color=colors[color_idx % len(colors)], width=1)
                    ),
                    row=1, col=1
                )
                color_idx += 1
            
            if "EMA20" in indicators:
                ema20 = df['close'].ewm(span=20, adjust=False).mean()
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=ema20,
                        mode='lines',
                        name='EMA20',
                        line=dict(color=colors[color_idx % len(colors)], width=1)
                    ),
                    row=1, col=1
                )
                color_idx += 1
            
            if "EMA50" in indicators:
                ema50 = df['close'].ewm(span=50, adjust=False).mean()
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=ema50,
                        mode='lines',
                        name='EMA50',
                        line=dict(color=colors[color_idx % len(colors)], width=1)
                    ),
                    row=1, col=1
                )
                color_idx += 1
            
            # Volume chart
            fig.add_trace(
                go.Bar(
                    x=df.index,
                    y=df['volume'],
                    name='Volume',
                    marker_color='lightblue'
                ),
                row=2, col=1
            )
            
            # Update layout
            fig.update_layout(
                title=f"NAS100 - {timeframe} Chart",
                xaxis_rangeslider_visible=False,
                height=600,
                showlegend=True
            )
            
            # Update y-axis labels
            fig.update_yaxes(title_text="Price (USD)", row=1, col=1)
            fig.update_yaxes(title_text="Volume", row=2, col=1)
            
            return fig
            
        except Exception as e:
            logger.error(f"Error creating chart: {e}")
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
    
    def _render_agent_thought_process(self):
        """Render the agent thought process monitor"""
        st.subheader("🧠 Agent Thought Process Monitor")
        
        # Get latest analysis from trading agents
        try:
            # Get analysis from agents
            analysis = self.trading_agents.analyze_and_recommend()
            
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
                
        except Exception as e:
            logger.error(f"Error rendering agent thought process: {e}")
            st.error(f"Error loading agent thoughts: {str(e)}")
            st.markdown('<div class="thought-process">Error loading thought process</div>', unsafe_allow_html=True)
    
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