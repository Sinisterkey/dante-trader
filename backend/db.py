import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging
from config import DB_PATH

logger = logging.getLogger(__name__)


class TradingDatabase:
    """SQLite database for trading system."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                trade_type TEXT NOT NULL,  -- LONG or SHORT
                entry_price REAL NOT NULL,
                entry_time TEXT NOT NULL,
                exit_price REAL,
                exit_time TEXT,
                pnl REAL,
                pnl_percent REAL,
                status TEXT NOT NULL,  -- PENDING, OPEN, CLOSED
                stop_loss REAL NOT NULL,
                take_profit REAL,
                position_size REAL,
                risk_amount REAL,
                created_at TEXT NOT NULL
            )
        """)

        # Signals table (incoming TradingView signals)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL,  -- BUY or SELL
                signal_data TEXT NOT NULL,  -- JSON
                webhook_timestamp TEXT NOT NULL,
                received_at TEXT NOT NULL,
                processed BOOLEAN DEFAULT FALSE
            )
        """)

        # Agent outputs (for each decision)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_outputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                trade_id INTEGER,
                agent_name TEXT NOT NULL,  -- chart, news, memory
                output TEXT NOT NULL,  -- JSON
                confidence REAL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(signal_id) REFERENCES signals(id),
                FOREIGN KEY(trade_id) REFERENCES trades(id)
            )
        """)

        # Decision logs (final decision engine output)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decision_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id INTEGER,
                chart_score REAL,
                news_score REAL,
                memory_score REAL,
                final_score REAL,
                decision TEXT,  -- EXECUTE, WAIT, REJECT, BLOCKED
                reasoning TEXT,  -- JSON
                created_at TEXT NOT NULL,
                FOREIGN KEY(signal_id) REFERENCES signals(id)
            )
        """)

        # Indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_created_at ON trades(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signals_received_at ON signals(received_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_outputs_signal_id ON agent_outputs(signal_id)")

        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ==================== SIGNALS ====================

    def log_signal(self, symbol: str, signal_type: str, signal_data: Dict[str, Any], webhook_timestamp: str) -> int:
        """Log incoming webhook signal."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO signals (symbol, signal_type, signal_data, webhook_timestamp, received_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            symbol,
            signal_type,
            json.dumps(signal_data),
            webhook_timestamp,
            datetime.utcnow().isoformat()
        ))

        signal_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return signal_id

    def get_signal(self, signal_id: int) -> Optional[Dict]:
        """Get signal by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM signals WHERE id = ?", (signal_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    # ==================== TRADES ====================

    def create_trade(self, symbol: str, trade_type: str, entry_price: float,
                     stop_loss: float, position_size: float, risk_amount: float) -> int:
        """Create a new trade."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO trades (
                symbol, trade_type, entry_price, entry_time, status,
                stop_loss, position_size, risk_amount, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol,
            trade_type,
            entry_price,
            datetime.utcnow().isoformat(),
            "OPEN",
            stop_loss,
            position_size,
            risk_amount,
            datetime.utcnow().isoformat()
        ))

        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return trade_id

    def update_trade_exit(self, trade_id: int, exit_price: float, pnl: float, pnl_percent: float):
        """Update trade with exit information."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE trades
            SET exit_price = ?, exit_time = ?, pnl = ?, pnl_percent = ?, status = ?
            WHERE id = ?
        """, (
            exit_price,
            datetime.utcnow().isoformat(),
            pnl,
            pnl_percent,
            "CLOSED",
            trade_id
        ))

        conn.commit()
        conn.close()

    def get_open_trades(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get all open trades (optionally filtered by symbol)."""
        conn = self._get_connection()
        cursor = conn.cursor()

        if symbol:
            cursor.execute("SELECT * FROM trades WHERE status = 'OPEN' AND symbol = ?", (symbol,))
        else:
            cursor.execute("SELECT * FROM trades WHERE status = 'OPEN'")

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_closed_trades(self, symbol: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Get closed trades (optionally filtered by symbol)."""
        conn = self._get_connection()
        cursor = conn.cursor()

        if symbol:
            cursor.execute("""
                SELECT * FROM trades WHERE status = 'CLOSED' AND symbol = ?
                ORDER BY exit_time DESC LIMIT ?
            """, (symbol, limit))
        else:
            cursor.execute("""
                SELECT * FROM trades WHERE status = 'CLOSED'
                ORDER BY exit_time DESC LIMIT ?
            """, (limit,))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_trade_by_id(self, trade_id: int) -> Optional[Dict]:
        """Get trade by ID."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
        row = cursor.fetchone()
        conn.close()

        return dict(row) if row else None

    # ==================== AGENT OUTPUTS ====================

    def log_agent_output(self, agent_name: str, output: Dict[str, Any],
                         signal_id: Optional[int] = None, trade_id: Optional[int] = None,
                         confidence: Optional[float] = None) -> int:
        """Log agent output."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO agent_outputs (agent_name, output, signal_id, trade_id, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            agent_name,
            json.dumps(output),
            signal_id,
            trade_id,
            confidence,
            datetime.utcnow().isoformat()
        ))

        agent_output_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return agent_output_id

    def get_agent_outputs_for_signal(self, signal_id: int) -> List[Dict]:
        """Get all agent outputs for a signal."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM agent_outputs WHERE signal_id = ?
            ORDER BY created_at ASC
        """, (signal_id,))

        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    # ==================== DECISION LOGS ====================

    def log_decision(self, signal_id: int, chart_score: float, news_score: float,
                     memory_score: float, final_score: float, decision: str, reasoning: Dict) -> int:
        """Log decision engine output."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO decision_logs (signal_id, chart_score, news_score, memory_score,
                                       final_score, decision, reasoning, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal_id,
            chart_score,
            news_score,
            memory_score,
            final_score,
            decision,
            json.dumps(reasoning),
            datetime.utcnow().isoformat()
        ))

        decision_log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return decision_log_id

    # ==================== ANALYTICS ====================

    def get_win_rate(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Calculate win rate statistics."""
        conn = self._get_connection()
        cursor = conn.cursor()

        if symbol:
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                       SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses,
                       AVG(pnl) as avg_pnl,
                       SUM(pnl) as total_pnl
                FROM trades WHERE status = 'CLOSED' AND symbol = ?
            """, (symbol,))
        else:
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                       SUM(CASE WHEN pnl <= 0 THEN 1 ELSE 0 END) as losses,
                       AVG(pnl) as avg_pnl,
                       SUM(pnl) as total_pnl
                FROM trades WHERE status = 'CLOSED'
            """)

        row = cursor.fetchone()
        conn.close()

        if row["total"] and row["total"] > 0:
            return {
                "total_trades": row["total"],
                "wins": row["wins"] or 0,
                "losses": row["losses"] or 0,
                "win_rate": (row["wins"] or 0) / row["total"],
                "avg_pnl": row["avg_pnl"] or 0,
                "total_pnl": row["total_pnl"] or 0
            }
        return {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0,
            "avg_pnl": 0,
            "total_pnl": 0
        }

    def get_best_setup_winrate(self, symbol: str, trade_type: str) -> Dict[str, Any]:
        """Get win rate for a specific setup type (LONG breakout, SHORT pullback, etc.)."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # This is simplified - in production you'd need to tag trades with their setup type
        cursor.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                   AVG(pnl) as avg_pnl
            FROM trades WHERE status = 'CLOSED' AND symbol = ? AND trade_type = ?
        """, (symbol, trade_type))

        row = cursor.fetchone()
        conn.close()

        if row["total"] and row["total"] > 0:
            return {
                "total": row["total"],
                "wins": row["wins"] or 0,
                "win_rate": (row["wins"] or 0) / row["total"],
                "avg_pnl": row["avg_pnl"] or 0
            }
        return {"total": 0, "wins": 0, "win_rate": 0, "avg_pnl": 0}
