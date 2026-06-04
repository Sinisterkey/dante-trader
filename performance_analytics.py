"""
Performance Analytics Module
Calculates and analyzes trading performance metrics
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd
from trade_logger import TradeLogger

logger = logging.getLogger(__name__)


class PerformanceAnalytics:
    """Calculates and analyzes trading performance metrics"""
    
    def __init__(self, trade_logger: TradeLogger = None):
        self.trade_logger = trade_logger or TradeLogger()
        logger.info("Performance analytics initialized")
    
    def calculate_basic_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate basic performance metrics from a list of trades"""
        if not trades:
            return self._empty_metrics()
        
        try:
            # Filter to only closed trades with P&L
            closed_trades = [t for t in trades if t.get('status') == 'closed' and t.get('pnl') is not None]
            
            if not closed_trades:
                return self._empty_metrics()
            
            total_trades = len(closed_trades)
            winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
            losing_trades = [t for t in closed_trades if t.get('pnl', 0) < 0]
            breakeven_trades = [t for t in closed_trades if t.get('pnl', 0) == 0]
            
            winning_count = len(winning_trades)
            losing_count = len(losing_trades)
            breakeven_count = len(breakeven_trades)
            
            # Win rate
            win_rate = (winning_count / total_trades * 100) if total_trades > 0 else 0.0
            
            # Profit/Loss amounts
            total_pnl = sum(t.get('pnl', 0) for t in closed_trades)
            total_profit = sum(t.get('pnl', 0) for t in winning_trades)
            total_loss = abs(sum(t.get('pnl', 0) for t in losing_trades))
            
            # Averages
            avg_profit = (total_profit / winning_count) if winning_count > 0 else 0.0
            avg_loss = (total_loss / losing_count) if losing_count > 0 else 0.0
            
            # Profit factor and expectancy
            profit_factor = (total_profit / total_loss) if total_loss > 0 else 0.0
            expectancy = (win_rate/100 * avg_profit) - ((1 - win_rate/100) * avg_loss) if avg_loss > 0 else 0.0
            
            # Return metrics
            return {
                "total_trades": total_trades,
                "winning_trades": winning_count,
                "losing_trades": losing_count,
                "breakeven_trades": breakeven_count,
                "win_rate": round(win_rate, 2),
                "total_pnl": round(total_pnl, 2),
                "total_profit": round(total_profit, 2),
                "total_loss": round(total_loss, 2),
                "avg_profit": round(avg_profit, 2),
                "avg_loss": round(avg_loss, 2),
                "profit_factor": round(profit_factor, 2),
                "expectancy": round(expectancy, 2),
                "payoff_ratio": round(avg_profit / avg_loss, 2) if avg_loss > 0 else 0.0
            }
            
        except Exception as e:
            logger.error(f"Error calculating basic metrics: {e}")
            return self._empty_metrics()
    
    def calculate_advanced_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate advanced performance metrics including drawdown and risk-adjusted returns"""
        try:
            # Get basic metrics first
            basic_metrics = self.calculate_basic_metrics(trades)
            if basic_metrics.get("total_trades", 0) == 0:
                return basic_metrics
            
            # Get closed trades sorted by exit time
            closed_trades = [t for t in trades if t.get('status') == 'closed' and t.get('pnl') is not None]
            if not closed_trades:
                return basic_metrics
            
            # Sort by exit time
            closed_trades.sort(key=lambda x: x.get('exit_time', ''))
            
            # Calculate equity curve
            equity_curve = self._calculate_equity_curve(closed_trades)
            
            # Calculate drawdown
            max_drawdown, max_drawdown_duration = self._calculate_max_drawdown(equity_curve)
            
            # Calculate Sharpe ratio (assuming risk-free rate of 0% for simplicity)
            sharpe_ratio = self._calculate_sharpe_ratio(closed_trades)
            
            # Calculate Sortino ratio
            sortino_ratio = self._calculate_sortino_ratio(closed_trades)
            
            # Calculate Calmar ratio
            calmar_ratio = self._calculate_calmar_ratio(closed_trades, max_drawdown)
            
            # Add advanced metrics to basic metrics
            advanced_metrics = {
                "max_drawdown": round(max_drawdown, 2),
                "max_drawdown_duration": max_drawdown_duration,
                "sharpe_ratio": round(sharpe_ratio, 2),
                "sortino_ratio": round(sortino_ratio, 2),
                "calmar_ratio": round(calmar_ratio, 2),
                "recovery_factor": round(basic_metrics["total_pnl"] / max_drawdown, 2) if max_drawdown > 0 else 0.0,
                "ulcer_index": self._calculate_ulcer_index(equity_curve)
            }
            
            # Merge dictionaries
            result = {**basic_metrics, **advanced_metrics}
            return result
            
        except Exception as e:
            logger.error(f"Error calculating advanced metrics: {e}")
            return self.calculate_basic_metrics(trades)  # Fallback to basic metrics
    
    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure"""
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "breakeven_trades": 0,
            "win_rate": 0.0,
            "total_pnl": 0.0,
            "total_profit": 0.0,
            "total_loss": 0.0,
            "avg_profit": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0,
            "expectancy": 0.0,
            "payoff_ratio": 0.0
        }
    
    def _calculate_equity_curve(self, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate equity curve from trades"""
        try:
            if not trades:
                return []
            
            # Sort trades by exit time
            sorted_trades = sorted(trades, key=lambda x: x.get('exit_time', ''))
            
            equity_curve = []
            running_equity = 0.0  # Starting equity
            
            for trade in sorted_trades:
                pnl = trade.get('pnl', 0.0)
                running_equity += pnl
                
                equity_curve.append({
                    "time": trade.get('exit_time'),
                    "equity": running_equity,
                    "pnl": pnl,
                    "trade_id": trade.get('id')
                })
            
            return equity_curve
            
        except Exception as e:
            logger.error(f"Error calculating equity curve: {e}")
            return []
    
    def _calculate_max_drawdown(self, equity_curve: List[Dict[str, Any]]) -> Tuple[float, int]:
        """Calculate maximum drawdown and its duration"""
        try:
            if not equity_curve or len(equity_curve) < 2:
                return 0.0, 0
            
            max_drawdown = 0.0
            max_duration = 0
            peak = equity_curve[0]['equity']
            peak_index = 0
            
            for i, point in enumerate(equity_curve):
                equity = point['equity']
                
                # Update peak
                if equity > peak:
                    peak = equity
                    peak_index = i
                
                # Calculate drawdown
                drawdown = (peak - equity) / peak * 100 if peak > 0 else 0.0
                
                # Update max drawdown
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    max_duration = i - peak_index
            
            return max_drawdown, max_duration
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0.0, 0
    
    def _calculate_sharpe_ratio(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate Sharpe ratio (assuming 0% risk-free rate)"""
        try:
            if not trades:
                return 0.0
            
            # Get daily returns (simplified - using trade P&L as periodic returns)
            returns = [trade.get('pnl', 0.0) for trade in trades if trade.get('status') == 'closed']
            
            if len(returns) < 2:
                return 0.0
            
            # Calculate mean and standard deviation
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            # Sharpe ratio = (mean return - risk-free rate) / std deviation
            # Assuming risk-free rate = 0 for simplicity
            if std_return == 0:
                return 0.0
            
            sharpe_ratio = mean_return / std_return
            return sharpe_ratio
            
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {e}")
            return 0.0
    
    def _calculate_sortino_ratio(self, trades: List[Dict[str, Any]]) -> float:
        """Calculate Sortino ratio (using downside deviation)"""
        try:
            if not trades:
                return 0.0
            
            # Get returns
            returns = [trade.get('pnl', 0.0) for trade in trades if trade.get('status') == 'closed']
            
            if len(returns) < 2:
                return 0.0
            
            # Calculate mean return
            mean_return = np.mean(returns)
            
            # Calculate downside deviation (only negative returns)
            negative_returns = [r for r in returns if r < 0]
            if not negative_returns:
                return float('inf')  # No downside risk
            
            downside_deviation = np.std(negative_returns)
            
            if downside_deviation == 0:
                return 0.0
            
            # Sortino ratio = mean return / downside deviation
            sortino_ratio = mean_return / downside_deviation
            return sortino_ratio
            
        except Exception as e:
            logger.error(f"Error calculating Sortino ratio: {e}")
            return 0.0
    
    def _calculate_calmar_ratio(self, trades: List[Dict[str, Any]], max_drawdown: float) -> float:
        """Calculate Calmar ratio (annual return / max drawdown)"""
        try:
            if not trades or max_drawdown == 0:
                return 0.0
            
            # Calculate annualized return
            # This is simplified - in practice we'd need to know the time period
            total_pnl = sum(t.get('pnl', 0) for t in trades if t.get('status') == 'closed')
            
            # For simplicity, we'll assume the trades represent about 1 year of trading
            # In a real system, we'd calculate based on actual date range
            annual_return = total_pnl  # Simplified assumption
            
            # Calmar ratio = annual return / max drawdown
            calmar_ratio = annual_return / (max_drawdown / 100.0)  # Convert percentage to decimal
            return calmar_ratio
            
        except Exception as e:
            logger.error(f"Error calculating Calmar ratio: {e}")
            return 0.0
    
    def _calculate_ulcer_index(self, equity_curve: List[Dict[str, Any]]) -> float:
        """Calculate Ulcer Index (measure of downside risk)"""
        try:
            if not equity_curve or len(equity_curve) < 2:
                return 0.0
            
            # Calculate drawdown at each point
            peak = equity_curve[0]['equity']
            drawdowns = []
            
            for point in equity_curve:
                equity = point['equity']
                if equity > peak:
                    peak = equity
                
                if peak > 0:
                    drawdown = (peak - equity) / peak * 100
                    drawdowns.append(drawdown)
                else:
                    drawdowns.append(0.0)
            
            # Ulcer Index = sqrt(sum(drawdown^2) / n)
            if not drawdowns:
                return 0.0
            
            squared_drawdowns = [d * d for d in drawdowns]
            mean_squared_drawdown = sum(squared_drawdowns) / len(squared_drawdowns)
            ulcer_index = np.sqrt(mean_squared_drawdown)
            
            return round(ulcer_index, 2)
            
        except Exception as e:
            logger.error(f"Error calculating Ulcer index: {e}")
            return 0.0
    
    def get_performance_by_time_period(self, period: str = "daily") -> List[Dict[str, Any]]:
        """Get performance metrics grouped by time period"""
        try:
            # Get all closed trades
            trades = self.trade_logger.get_closed_trades(limit=10000)
            
            if not trades:
                return []
            
            # Convert to DataFrame for easier grouping
            df = pd.DataFrame(trades)
            if df.empty:
                return []
            
            # Convert exit_time to datetime
            df['exit_time'] = pd.to_datetime(df['exit_time'])
            
            # Group by period
            if period == "daily":
                df['period'] = df['exit_time'].dt.date
            elif period == "weekly":
                df['period'] = df['exit_time'].dt.to_period('W')
            elif period == "monthly":
                df['period'] = df['exit_time'].dt.to_period('M')
            else:
                df['period'] = df['exit_time'].dt.date  # Default to daily
            
            # Group and calculate metrics
            grouped = df.groupby('period').agg({
                'pnl': ['count', 'sum', 'mean'],
                'id': 'count'  # For trade count
            }).reset_index()
            
            # Flatten column multi-index
            grouped.columns = ['period', 'trade_count', 'total_pnl', 'avg_pnl', 'trade_count_dup']
            grouped = grouped.drop('trade_count_dup', axis=1)
            
            # Calculate win rate for each period
            win_rates = []
            for period_val in grouped['period']:
                period_trades = df[df['period'] == period_val]
                if len(period_trades) > 0:
                    winning_trades = len(period_trades[period_trades['pnl'] > 0])
                    win_rate = (winning_trades / len(period_trades)) * 100
                else:
                    win_rate = 0.0
                win_rates.append(round(win_rate, 2))
            
            grouped['win_rate'] = win_rates
            
            # Rename columns for clarity
            grouped = grouped.rename(columns={
                'period': 'period',
                'trade_count': 'trades',
                'total_pnl': 'net_profit',
                'avg_pnl': 'avg_profit_per_trade'
            })
            
            # Convert to list of dictionaries
            result = []
            for _, row in grouped.iterrows():
                result.append({
                    'period': str(row['period']),
                    'trades': int(row['trades']),
                    'win_rate': float(row['win_rate']),
                    'net_profit': round(float(row['net_profit']), 2),
                    'avg_profit': round(float(row['avg_profit']), 2)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating performance by time period: {e}")
            return []
    
    def get_performance_by_symbol(self) -> List[Dict[str, Any]]:
        """Get performance metrics grouped by symbol"""
        try:
            # Get all closed trades
            trades = self.trade_logger.get_closed_trades(limit=10000)
            
            if not trades:
                return []
            
            # Group by symbol
            symbol_stats = {}
            for trade in trades:
                symbol = trade.get('symbol', 'UNKNOWN')
                if symbol not in symbol_stats:
                    symbol_symbol[symbol] = {
                        'trades': 0,
                        'wins': 0,
                        'losses': 0,
                        'pnl': 0.0
                    }
                
                symbol_stats[symbol]['trades'] += 1
                pnl = trade.get('pnl', 0.0)
                symbol_stats[symbol]['pnl'] += pnl
                if pnl > 0:
                    symbol_stats[symbol]['wins'] += 1
                elif pnl < 0:
                    symbol_stats[symbol]['losses'] += 1
            
            # Convert to list and calculate metrics
            result = []
            for symbol, stats in symbol_stats.items():
                total_trades = stats['trades']
                if total_trades > 0:
                    win_rate = (stats['wins'] / total_trades) * 100
                else:
                    win_rate = 0.0
                
                result.append({
                    'symbol': symbol,
                    'trades': total_trades,
                    'wins': stats['wins'],
                    'losses': stats['losses'],
                    'win_rate': round(win_rate, 2),
                    'total_pnl': round(stats['pnl'], 2),
                    'avg_profit': round(stats['pnl'] / stats['wins'], 2) if stats['wins'] > 0 else 0.0,
                    'avg_loss': round(abs(stats['pnl']) / stats['losses'], 2) if stats['losses'] > 0 else 0.0
                })
            
            # Sort by total P&L descending
            result.sort(key=lambda x: x['total_pnl'], reverse=True)
            return result
            
        except Exception as e:
            logger.error(f"Error calculating performance by symbol: {e}")
            return []


# Example usage function
def get_system_performance() -> Dict[str, Any]:
    """Get overall system performance metrics"""
    try:
        trade_logger = TradeLogger()
        analytics = PerformanceAnalytics(trade_logger)
        
        # Get all closed trades
        trades = trade_logger.get_closed_trades(limit=10000)
        
        # Calculate comprehensive metrics
        metrics = analytics.calculate_advanced_metrics(trades)
        
        # Get performance by time period
        daily_performance = analytics.get_performance_by_time_period("daily")
        monthly_performance = analytics.get_performance_by_time_period("monthly")
        
        # Get performance by symbol
        symbol_performance = analytics.get_performance_by_symbol()
        
        return {
            "overall_metrics": metrics,
            "daily_performance": daily_performance,
            "monthly_performance": monthly_performance,
            "symbol_performance": symbol_performance,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting system performance: {e}")
        return {"error": str(e)}