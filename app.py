import streamlit as st
import time as time_module
import threading
from datetime import datetime
import logging
import json
from agents import TradingAgents
from config import *
import requests

logger = logging.getLogger(__name__)

# Initialize session state
if 'trading_agents' not in st.session_state:
    st.session_state.trading_agents = TradingAgents()
    
if 'last_analysis' not in st.session_state:
    st.session_state.last_analysis = None
    
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []
    
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
    
if 'telegram_alerts_sent' not in st.session_state:
    st.session_state.telegram_alerts_sent = set()

def send_telegram_alert(message: str):
    """Send alert via Telegram Bot"""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not configured")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        response = requests.post(url, data=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info("Telegram alert sent successfully")
            return True
        else:
            logger.error(f"Failed to send Telegram alert: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending Telegram alert: {e}")
        return False

def format_telegram_message(analysis: Dict[str, Any]) -> str:
    """Format analysis result for Telegram alert"""
    if analysis.get('action') == 'NO_TRADE':
        return None
    
    action_emoji = "🟢" if analysis['action'] == 'BUY' else "🔴"
    
    message = f"{action_emoji} <b>NAS100 TRADE SIGNAL</b> {action_emoji}\n\n"
    message += f"<b>Action:</b> {analysis['action']}\n"
    message += f"<b>Entry:</b> {analysis['entry_price']:.2f}\n"
    message += f"<b>Stop Loss:</b> {analysis['stop_loss']:.2f}\n"
    message += f"<b>Take Profit:</b> {analysis['take_profit']:.2f}\n"
    message += f"<b>Risk Amount:</b> {analysis['risk_amount']:.2f} points\n\n"
    message += f"<b>Reasoning:</b>\n{analysis['reasoning']}\n\n"
    message += f"<b>Time:</b> {analysis['timestamp']}\n"
    
    return message

def analysis_loop():
    """Background thread for continuous market analysis"""
    while st.session_state.is_running:
        try:
            # Perform analysis
            analysis = st.session_state.trading_agents.analyze_and_recommend()
            analysis['timestamp'] = datetime.utcnow().isoformat()
            
            # Update session state
            st.session_state.last_analysis = analysis
            st.session_state.analysis_history.append(analysis)
            
            # Keep only last 100 analyses
            if len(st.session_state.analysis_history) > 100:
                st.session_state.analysis_history = st.session_state.analysis_history[-100:]
            
            # Send Telegram alert for new trade signals
            if (analysis.get('action') in ['BUY', 'SELL'] and 
                analysis.get('confidence', 0) >= 70):  # Only send high confidence signals
                
                # Create unique identifier for this signal to avoid duplicates
                signal_id = f"{analysis['action']}_{analysis['entry_price']}_{analysis['timestamp'][:16]}"
                
                if signal_id not in st.session_state.telegram_alerts_sent:
                    telegram_message = format_telegram_message(analysis)
                    if telegram_message:
                        if send_telegram_alert(telegram_message):
                            st.session_state.telegram_alerts_sent.add(signal_id)
                            logger.info(f"Telegram alert sent for {analysis['action']} signal")
            
            # Wait before next analysis
            time_module.sleep(UPDATE_INTERVAL)
            
        except Exception as e:
            logger.error(f"Error in analysis loop: {e}")
            time_module.sleep(UPDATE_INTERVAL)

def main():
    st.set_page_config(
        page_title="NAS100 Multi-Agent Trading System",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("📈 NAS100 Multi-Agent Trading System")
    st.caption("Powered by CrewAI Agents & MetaTrader 5")
    
    # Control panel
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("▶️ Start Analysis" if not st.session_state.is_running else "⏸️ Stop Analysis"):
            st.session_state.is_running = not st.session_state.is_running
            if st.session_state.is_running:
                # Start background thread
                analysis_thread = threading.Thread(target=analysis_loop, daemon=True)
                analysis_thread.start()
                st.success("Analysis started!")
            else:
                st.info("Analysis stopped.")
            st.rerun()
    
    with col2:
        if st.button("🔄 Manual Analysis"):
            with st.spinner("Performing analysis..."):
                analysis = st.session_state.trading_agents.analyze_and_recommend()
                analysis['timestamp'] = datetime.utcnow().isoformat()
                st.session_state.last_analysis = analysis
                st.session_state.analysis_history.append(analysis)
                if len(st.session_state.analysis_history) > 100:
                    st.session_state.analysis_history = st.session_state.analysis_history[-100:]
            st.rerun()
    
    with col3:
        session_status = "🟢 Active" if (st.session_state.trading_agents.market_intel.is_london_ny_overlap() if hasattr(st.session_state, 'trading_agents') else False) else "🔴 Inactive"
        st.metric("London/NY Session", session_status)
    
    # Display current analysis
    if st.session_state.last_analysis:
        analysis = st.session_state.last_analysis
        
        # Create columns for key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            action = analysis.get('action', 'NO_TRADE')
            if action == 'BUY':
                st.metric("Signal", "🟢 BUY", delta="Long")
            elif action == 'SELL':
                st.metric("Signal", "🔴 SELL", delta="Short")
            else:
                st.metric("Signal", "⚪ NO TRADE", delta="Wait")
        
        with col2:
            st.metric("Confidence", f"{analysis.get('confidence', 0)}%")
        
        with col3:
            if analysis.get('entry_price'):
                st.metric("Entry Price", f"{analysis['entry_price']:.2f}")
            else:
                st.metric("Entry Price", "N/A")
        
        with col4:
            st.metric("Last Update", analysis.get('timestamp', 'N/A')[:19].replace('T', ' '))
        
        # Display reasoning in expandable section
        with st.expander("📋 Detailed Reasoning", expanded=True):
            st.write(analysis.get('reasoning', 'No reasoning available'))
        
        # Display agent thought process
        if 'agent_thought_process' in analysis:
            with st.expander("🧠 Agent Inner Monologue", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Technical Observer")
                    st.write(analysis['agent_thought_process'].get('technical_observer', 'No data'))
                
                with col2:
                    st.subheader("Executive Strategist")
                    st.write(analysis['agent_thought_process'].get('executive_strategist', 'No data'))
        
        # Display market data if available
        if 'market_data' in analysis and analysis['market_data']:
            with st.expander("📊 Market Data Details", expanded=False):
                market_data = analysis['market_data']
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Price Levels**")
                    st.write(f"Entry: {market_data.get('entry_price', 'N/A'):.2f}")
                    st.write(f"Swing High: {market_data.get('swing_high', 'N/A'):.2f}")
                    st.write(f"Swing Low: {market_data.get('swing_low', 'N/A'):.2f}")
                    st.write(f"ATR: {market_data.get('atr', 'N/A'):.4f}")
                
                with col2:
                    st.write("**Trend Analysis**")
                    st.write(f"M15 Trend: {market_data.get('m15_trend', 'N/A')}")
                    st.write(f"H4 Trend: {market_data.get('h4_trend', 'N/A')}")
                    st.write(f"Trend Aligned: {'✅ Yes' if market_data.get('trend_aligned') else '❌ No'}")
                    st.write(f"Session Valid: {'✅ Yes' if analysis.get('validation_checks', {}).get('session_valid') else '❌ No'}")
    else:
        st.info("Click 'Start Analysis' or 'Manual Analysis' to begin market analysis.")
    
    # Display analysis history
    if st.session_state.analysis_history:
        st.subheader("📈 Analysis History")
        
        # Create a simplified history view
        history_data = []
        for analysis in reversed(st.session_state.analysis_history[-20:]):  # Last 20 analyses
            history_data.append({
                "Time": analysis.get('timestamp', 'N/A')[:19].replace('T', ' '),
                "Signal": analysis.get('action', 'NO_TRADE'),
                "Confidence": f"{analysis.get('confidence', 0)}%",
                "Entry": f"{analysis.get('entry_price', 0):.2f}" if analysis.get('entry_price') else "N/A",
                "Reason": analysis.get('reasoning', 'N/A')[:50] + "..." if len(analysis.get('reasoning', '')) > 50 else analysis.get('reasoning', 'N/A')
            })
        
        if history_data:
            st.dataframe(history_data, use_container_width=True)
    
    # Footer
    st.markdown("--")
    st.caption(f"NAS100 Multi-Agent Trading System | Data updates every {UPDATE_INTERVAL} seconds")

if __name__ == "__main__":
    main()