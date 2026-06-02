import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np

from backend.strategy import TradingStrategy
from backend.decision_engine import DecisionEngine
from backend.risk_manager import RiskManager
from backend.db import TradingDatabase


class TestTradingStrategy:
    """Test trading strategy functions."""

    def test_support_resistance_calculation(self):
        """Test support and resistance level calculation."""
        # Create sample OHLCV data
        dates = pd.date_range('2024-01-01', periods=51)
        df = pd.DataFrame({
            'time': dates,
            'open': [1.0900 + i*0.0001 for i in range(51)],
            'high': [1.0950 + i*0.0001 for i in range(51)],
            'low': [1.0850 + i*0.0001 for i in range(51)],
            'close': [1.0920 + i*0.0001 for i in range(51)],
            'volume': [1000000] * 51
        })

        sr = TradingStrategy.calculate_support_resistance(df, lookback=50)

        assert 'support' in sr
        assert 'resistance' in sr
        assert sr['support'] < sr['resistance']

    def test_trend_detection(self):
        """Test trend detection using SMA."""
        dates = pd.date_range('2024-01-01', periods=200)
        # Bullish trend
        close_prices = [1.0900 + i*0.0005 for i in range(200)]

        df = pd.DataFrame({
            'time': dates,
            'close': close_prices,
            'open': close_prices,
            'high': [p + 0.0010 for p in close_prices],
            'low': [p - 0.0010 for p in close_prices],
            'volume': [1000000] * 200
        })

        trend = TradingStrategy.detect_trend(df)

        assert 'trend' in trend
        assert trend['trend'] in ['bullish', 'bearish', 'neutral']

    def test_atr_calculation(self):
        """Test ATR calculation."""
        dates = pd.date_range('2024-01-01', periods=30)
        df = pd.DataFrame({
            'time': dates,
            'high': [1.0950 + np.random.rand()*0.01 for _ in range(30)],
            'low': [1.0850 + np.random.rand()*0.01 for _ in range(30)],
            'close': [1.0900 + np.random.rand()*0.01 for _ in range(30)],
        })

        atr = TradingStrategy.calculate_atr(df, period=14)

        assert atr is not None
        assert atr > 0

    def test_breakout_detection(self):
        """Test breakout detection."""
        dates = pd.date_range('2024-01-01', periods=55)
        df = pd.DataFrame({
            'time': dates,
            'high': [1.0950 + i*0.0001 for i in range(55)],
            'low': [1.0850 + i*0.0001 for i in range(55)],
            'close': [1.0920 + i*0.0001 for i in range(55)],  # Rising close
            'open': [1.0900 + i*0.0001 for i in range(55)],
            'volume': [1000000] * 55
        })

        sr = TradingStrategy.calculate_support_resistance(df)
        breakout = TradingStrategy.detect_breakout(df, sr, direction='up')

        assert 'breakout' in breakout
        assert isinstance(breakout['breakout'], bool)


class TestDecisionEngine:
    """Test decision engine scoring."""

    def test_normalize_agent_output(self):
        """Test agent output normalization."""
        engine = DecisionEngine()

        # Chart agent output
        chart_output = {"agent": "chart", "confidence": 75}
        score = engine._normalize_agent_output(chart_output)
        assert 0 <= score <= 100

        # News agent output
        news_output = {"agent": "news", "score": 0.5}
        score = engine._normalize_agent_output(news_output)
        assert 0 <= score <= 100
        assert score > 50  # Positive sentiment

    def test_determine_decision(self):
        """Test decision determination based on score."""
        engine = DecisionEngine()

        # Strong signal
        decision, reason = engine._determine_decision(80)
        assert decision == "EXECUTE"

        # Weak signal
        decision, reason = engine._determine_decision(60)
        assert decision == "WAIT"

        # Poor signal
        decision, reason = engine._determine_decision(20)
        assert decision == "BLOCKED"

    def test_make_decision(self):
        """Test complete decision making."""
        engine = DecisionEngine()

        chart_output = {
            "agent": "chart",
            "confidence": 80,
            "bias": "bullish",
            "breakout": {"detected": True, "direction": "LONG"}
        }

        news_output = {
            "agent": "news",
            "score": 0.3,
            "confidence": 60
        }

        memory_output = {
            "agent": "memory",
            "best_setup_winrate": 0.60,
            "confidence": 50
        }

        result = engine.make_decision(chart_output, news_output, memory_output)

        assert "decision" in result
        assert "final_score" in result
        assert result["final_score"] >= 0
        assert result["final_score"] <= 100


class TestRiskManager:
    """Test risk management functions."""

    def test_position_sizing(self):
        """Test position size calculation."""
        db = MagicMock()
        rm = RiskManager(db, account_balance=10000)

        result = rm.calculate_position_size(1.0950, 1.0900)

        assert result["position_size"] > 0
        assert result["risk_amount"] > 0

    def test_take_profit_calculation(self):
        """Test take profit level calculation."""
        db = MagicMock()
        rm = RiskManager(db, account_balance=10000)

        entry = 1.0950
        stop_loss = 1.0900
        reward_ratio = 2.0

        result = rm.calculate_take_profit(entry, stop_loss, reward_ratio)

        assert result["take_profit"] != entry
        assert result["reward_ratio"] == reward_ratio

    def test_setup_validation(self):
        """Test trade setup validation."""
        db = MagicMock()
        db.get_open_trades.return_value = []  # No open trades

        rm = RiskManager(db, account_balance=10000)

        entry = 1.0950
        stop_loss = 1.0900
        take_profit = 1.1000

        result = rm.validate_setup(entry, stop_loss, take_profit, min_reward_ratio=2.0)

        assert "valid" in result
        assert "reward_ratio" in result


class TestWebhookValidator:
    """Test webhook validation and parsing."""

    def test_parse_webhook_signal(self):
        """Test webhook signal parsing."""
        from backend.webhook import WebhookValidator

        data = {
            "symbol": "EURUSD",
            "action": "BUY",
            "price": 1.0950,
            "time": "2024-01-15T10:30:00Z"
        }

        signal = WebhookValidator.parse_webhook_signal(data)

        assert signal is not None
        assert signal["symbol"] == "EURUSD"
        assert signal["action"] == "BUY"
        assert signal["price"] == 1.0950

    def test_convert_action_to_trade_type(self):
        """Test action to trade type conversion."""
        from backend.webhook import WebhookValidator

        assert WebhookValidator.convert_action_to_trade_type("BUY") == "LONG"
        assert WebhookValidator.convert_action_to_trade_type("SELL") == "SHORT"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
