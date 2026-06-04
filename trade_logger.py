"""
Trade Logger Module
Handles recording and retrieval of trade history and performance data
"""

import sqlite3
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path
import os
from config import *

logger = logging.getLogger(__name__)


class TradeLogger:
    """Logs and manages trade data in SQLite database"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use default path from config or create one
            db_dir = os.path.join(os.path.dirname(__file__), "data")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "trading_system.db")
        
        self.db_path = db_path
        self.connection = None
        self._init_database()
        logger.info(f"Trade logger initialized with database: {self.db_path}")
    
    def _init_database(self) -> None:
        """Initialize the database schema"""
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row  # Enable column access by name
            cursor = self.connection.cursor()
            
            # Create trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket INTEGER UNIQUE,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,  -- 'buy' or 'sell'
                    volume REAL NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT,
                    stop_loss REAL,
                    take_profit REAL,
                    pnl REAL,  -- realized profit/loss
                    unrealized_pnl REAL,  -- current unrealized P&L
                    commission REAL DEFAULT 0.0,
                    swap REAL DEFAULT 0.0,
                    profit REAL,  -- pnl + commission + swap
                    status TEXT NOT NULL,  -- 'open', 'closed', 'cancelled'
                    reason TEXT,  -- reason for opening/closing
                    confidence INTEGER,  -- signal confidence %
                    strategy TEXT,  -- which strategy generated the signal
                    ml_confidence REAL,  -- ML-enhanced confidence
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_ticket ON trades(ticket)")
            
            # Create performance metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,  -- YYYY-MM-DD
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    win_rate REAL DEFAULT 0.0,
                    total_pnl REAL DEFAULT 0.0,
                    avg_profit REAL DEFAULT 0.0,
                    avg_loss REAL DEFAULT 0.0,
                    profit_factor REAL DEFAULT 0.0,
                    expectancy REAL DEFAULT 0.0,
                    max_drawdown REAL DEFAULT 0.0,
                    sharpe_ratio REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Create system events table for logging
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,  -- 'info', 'warning', 'error', 'signal', 'trade'
                    message TEXT NOT NULL,
                    details TEXT,  -- JSON string for additional data
                    timestamp TEXT NOT NULL
                )
            """)
            
            self.connection.commit()
            logger.info("Database schema initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise
    
    def log_trade_open(self, position_data: Dict[str, Any]) -> int:
        """Log a newly opened trade"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                INSERT INTO trades (
                    ticket, symbol, side, volume, entry_price, entry_time,
                    stop_loss, take_profit, reason, confidence, strategy,
                    ml_confidence, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position_data.get('ticket'),
                position_data.get('symbol'),
                position_data.get('side'),
                position_data.get('volume'),
                position_data.get('entry_price'),
                position_data.get('timestamp').isoformat() if isinstance(position_data.get('timestamp'), datetime) else position_data.get('timestamp'),
                position_data.get('stop_loss'),
                position_data.get('take_profit'),
                position_data.get('signal_reason', ''),
                position_data.get('confidence', 0),
                position_data.get('strategy', 'AI_Signal'),
                position_data.get('ml_confidence', 0.0),
                'open',
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat()
            ))
            
            self.connection.commit()
            trade_id = cursor.lastrowid
            logger.info(f"Trade opened logged: Ticket {position_data.get('ticket')}, ID {trade_id}")
            return trade_id
            
        except Exception as e:
            logger.error(f"Error logging trade open: {e}")
            self.connection.rollback()
            return -1
    
    def log_trade_close(self, ticket: int, close_data: Dict[str, Any]) -> bool:
        """Log the closing of a trade"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                UPDATE trades SET
                    exit_price = ?,
                    exit_time = ?,
                    pnl = ?,
                    profit = ?,
                    status = ?,
                    reason = ?,
                    updated_at = ?
                WHERE ticket = ?
            """, (
                close_data.get('exit_price'),
                close_data.get('exit_time').isoformat() if isinstance(close_data.get('exit_time'), datetime) else close_data.get('exit_time'),
                close_data.get('pnl', 0.0),
                close_data.get('pnl', 0.0),  # profit will be same as pnl for now (excluding commission/swap)
                'closed',
                close_data.get('reason', ''),
                datetime.now(timezone.utc).isoformat(),
                ticket
            ))
            
            self.connection.commit()
            rows_affected = cursor.rowcount
            if rows_affected > 0:
                logger.info(f"Trade closed logged: Ticket {ticket}")
                return True
            else:
                logger.warning(f"No trade found with ticket {ticket} to close")
                return False
                
        except Exception as e:
            logger.error(f"Error logging trade close: {e}")
            self.connection.rollback()
            return False
    
    def update_trade_unrealized_pnl(self, ticket: int, unrealized_pnl: float) -> bool:
        """Update the unrealized P&L for an open trade"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute("""
                UPDATE trades SET
                    unrealized_pnl = ?,
                    updated_at = ?
                WHERE ticket = ? AND status = 'open'
            """, (
                unrealized_pnl,
                datetime.now(timezone.utc).isoformat(),
                ticket
            ))
            
            self.connection.commit()
            rows_affected = cursor.rowcount
            return rows_affected > 0
            
        except Exception as e:
            logger.error(f"Error updating unrealized P&L: {e}")
            self.connection.rollback()
            return False
    
    def get_trade(self, ticket: int) -> Optional[Dict[str, Any]]:
        """Get a specific trade by ticket"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM trades WHERE ticket = ?", (ticket,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            logger.error(f"Error getting trade {ticket}: {e}")
            return None
    
    def get_open_trades(self) -> List[Dict[str, Any]]:
        """Get all open trades"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM trades WHERE status = 'open' ORDER BY entry_time DESC")
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting open trades: {e}")
            return []
    
    def get_closed_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get closed trades, most recent first"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM trades 
                WHERE status = 'closed' 
                ORDER BY exit_time DESC 
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting closed trades: {e}")
            return []
    
    def get_trades_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get trades within a date range"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT * FROM trades 
                WHERE datetime(entry_time) BETWEEN ? AND ?
                ORDER BY entry_time DESC
            """, (
                start_date.isoformat(),
                end_date.isoformat()
            ))
            rows = cursor.fetchall()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting trades by date range: {e}")
            return []
    
    def calculate_performance_metrics(self, start_date: datetime = None, end_date: datetime = None) -> Dict[str, Any]:
        """Calculate performance metrics for a date range"""
        try:
            # Get trades for the period
            if start_date is None and end_date is None:
                trades = self.get_closed_trades(limit=10000)  # Get all if no date specified
            else:
                trades = self.get_trades_by_date_range(start_date, end_date)
            
            if not trades:
                return {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0.0,
                    "total_pnl": 0.0,
                    "avg_profit": 0.0,
                    "avg_loss": 0.0,
                    "profit_factor": 0.0,
                    "expectancy": 0.0,
                    "max_drawdown": 0.0
                }
            
            # Calculate metrics
            total_trades = len(trades)
            winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
            losing_trades = [t for t in trades if t.get('pnl', 0) < 0]
            breakeven_trades = [t for t in trades if t.get('pnl', 0) == 0]
            
            winning_count = len(winning_trades)
            losing_count = len(losing_trades)
            
            win_rate = (winning_count / total_trades * 100) if total_trades > 0 else 0.0
            
            total_pnl = sum(t.get('pnl', 0) for t in trades)
            total_profit = sum(t.get('pnl', 0) for t in winning_trades)
            total_loss = abs(sum(t.get('pnl', 0) for t in losing_trades))
            
            avg_profit = (total_profit / winning_count) if winning_count > 0 else 0.0
            avg_loss = (total_loss / losing_count) if losing_count > 0 else 0.0
            
            profit_factor = (total_profit / total_loss) if total_loss > 0 Achieved
            }
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {}