from datetime import datetime
from typing import List, Optional
import pandas as pd
from .connection import DatabaseConnection

class TradeRepository:
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
    
    def save_trade(self, trade: dict):
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO trades 
                (symbol, entry_time, exit_time, entry_price, exit_price, 
                 quantity, side, pnl, strategy, mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade['symbol'],
                trade['entry_time'].isoformat(),
                trade['exit_time'].isoformat() if trade.get('exit_time') else None,
                trade['entry_price'],
                trade.get('exit_price'),
                trade['quantity'],
                trade['side'],
                trade.get('pnl'),
                trade.get('strategy'),
                trade.get('mode', 'backtest')
            ))
    
    def get_trades(self, symbol: Optional[str] = None, 
                  start_date: Optional[datetime] = None,
                  end_date: Optional[datetime] = None) -> pd.DataFrame:
        with self.db.get_connection() as conn:
            query = "SELECT * FROM trades WHERE 1=1"
            params = []
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            if start_date:
                query += " AND entry_time >= ?"
                params.append(start_date.isoformat())
            if end_date:
                query += " AND entry_time <= ?"
                params.append(end_date.isoformat())
            
            query += " ORDER BY entry_time DESC"
            df = pd.read_sql_query(query, conn, params=params)
            
            if not df.empty:
                df['entry_time'] = pd.to_datetime(df['entry_time'])
                if 'exit_time' in df.columns:
                    df['exit_time'] = pd.to_datetime(df['exit_time'])
            
            return df
    
    def get_trade_summary(self, mode: Optional[str] = None) -> dict:
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            where_clause = "WHERE mode = ?" if mode else ""
            params = [mode] if mode else []
            
            cursor.execute(f'''
                SELECT 
                    COUNT(*) as total_trades,
                    SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
                    SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losing_trades,
                    SUM(pnl) as total_pnl,
                    AVG(pnl) as avg_pnl,
                    MAX(pnl) as max_win,
                    MIN(pnl) as max_loss
                FROM trades {where_clause}
            ''', params)
            
            row = cursor.fetchone()
            return {
                'total_trades': row[0] or 0,
                'winning_trades': row[1] or 0,
                'losing_trades': row[2] or 0,
                'total_pnl': row[3] or 0.0,
                'avg_pnl': row[4] or 0.0,
                'max_win': row[5] or 0.0,
                'max_loss': row[6] or 0.0,
                'win_rate': (row[1] / row[0] * 100) if row[0] else 0.0
            }

    def log_strategy_state(self, pair: str, z_score: float, beta: float, spread: float, ai_conf: float = 0.0, signal_type: str = "NONE", timestamp: datetime = None):
        """
        Log strategy internal state for dashboard.
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                if timestamp:
                    cursor.execute('''
                        INSERT INTO strategy_logs (pair, z_score, beta, spread, ai_confidence, signal_type, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (pair, z_score, beta, spread, ai_conf, signal_type, timestamp))
                else:
                    cursor.execute('''
                        INSERT INTO strategy_logs (pair, z_score, beta, spread, ai_confidence, signal_type)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (pair, z_score, beta, spread, ai_conf, signal_type))
                conn.commit()
        except Exception as e:
            print(f"Error logging strategy state: {e}")

    def log_performance_metrics(self, metrics: List[dict]):
        """
        Bulk log per-symbol metrics for tuning analysis.
        metrics: list of dicts with {symbol, basket, z_score, price, residual, residual_std, threshold, in_pos}
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany('''
                    INSERT INTO strategy_metrics 
                    (symbol, basket_name, z_score, price, residual, residual_std, threshold_used, in_position, hurst, half_life, adx, regime)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', [
                    (m['symbol'], m['basket'], m['z_score'], m['price'], 
                     m['residual'], m['residual_std'], m['threshold'], 1 if m['in_pos'] else 0,
                     m.get('hurst'), m.get('half_life'), m.get('adx'), m.get('regime'))
                    for m in metrics
                ])
                conn.commit()
        except Exception as e:
            logger.error(f"Error logging performance metrics: {e}")
