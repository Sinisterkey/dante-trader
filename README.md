# NAS100 Multi-Agent Trading System

## Overview
This is a modular Multi-Agent Trading System for NAS100 trading that integrates with MetaTrader 5 (MT5), uses CrewAI agents for analysis, provides a Streamlit dashboard for visualization, and sends Telegram alerts for trading signals.

## Features
- NAS100-specific trading strategy based on swing high/low levels, SMA50 trend, and ATR volatility
- London/NY session filtering (12:00-16:00 GMT)
- Multi-timeframe analysis (M15 for signals, H4 for trend confirmation)
- CrewAI multi-agent system:
  - Technical Observer: Identifies breakouts/pullouts based on technical levels
  - Executive Strategist: Validates signals and provides final trade recommendations
- Real-time Streamlit dashboard showing market state and agent thought processes
- Telegram integration for instant trade alerts
- Risk management: SL = 1.5 * ATR, TP = 2.5 * Risk, Risk = 1.5% of equity

## File Structure
- `config.py` - NAS100-specific configuration settings
- `bridge.py` - MT5 connection handling and MarketIntelligence class
- `agents.py` - CrewAI agent implementation (Technical Observer & Executive Strategist)
- `app.py` - Streamlit dashboard with Telegram integration
- `requirements.txt` - Python package dependencies

## Installation
1. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

2. Set up your environment variables in a `.env` file:
   ```
   MT5_LOGIN=your_mt5_login
   MT5_PASSWORD=your_mt5_password
   MT5_SERVER=your_mt5_server
   TELEGRAM_TOKEN=your_telegram_bot_token
   TELEGRAM_CHAT_ID=your_telegram_chat_id
   ```

3. Ensure you have MetaTrader 5 installed and running with access to NAS100 data.

## Usage
1. Start the Streamlit dashboard:
   ```
   streamlit run app.py
   ```

2. Click "Start Analysis" to begin continuous market analysis
3. Use "Manual Analysis" for on-demand analysis
4. View the dashboard for real-time market data, agent reasoning, and trade signals
5. Telegram alerts will be sent when high-confidence trade signals are detected

## Strategy Details
- Instrument: NAS100
- Lookback: 50 candles for Swing High/Low calculation
- Indicators: SMA(50) for trend, ATR(14) for volatility
- Session Filter: Only trade during London/NY Overlap (12:00-16:00 GMT)
- Confirmation: M15 timeframe signals must align with H4 trend
- Risk Management: 
  - Stop Loss = 1.5 * ATR
  - Take Profit = 2.5 * Risk
  - Risk = 1.5% of equity per trade

## Agent Responsibilities
### Technical Observer (Agent A)
- Processes raw MT5 data
- Identifies breakout and pullback opportunities
- Uses SMA50 and swing levels for analysis
- Outputs preliminary signals with confidence

### Executive Strategist (Agent B)
- Validates signals from Technical Observer
- Checks 4H trend alignment and session timing
- Calculates final trade parameters (entry, SL, TP)
- Provides detailed reasoning for decisions

## Disclaimer
This system is for educational purposes only. Trading involves risk, and past performance does not guarantee future results. Always use proper risk management and consider consulting with a financial advisor before making trading decisions.