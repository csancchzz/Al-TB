import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime
from patterns import SMCPatternAnalyzer
from config import TradingConfig

class Backtester:
    def __init__(self, config: TradingConfig, initial_balance: float = 10000):
        self.config = config
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.pattern_analyzer = SMCPatternAnalyzer(config)
        self.positions = {}
        self.trades_history = []
        
    def calculate_position_size(self) -> float:
        """Calculate position size based on current balance"""
        return self.balance * self.config.POSITION_SIZE
    
    def open_position(self, symbol: str, side: str, price: float, timestamp: datetime, pattern_info: Dict):
        """Open a new position"""
        if len(self.positions) >= self.config.MAX_POSITIONS:
            return
        
        position_size = self.calculate_position_size()
        cost = position_size
        
        if cost > self.balance:
            return
        
        stop_loss = price * (1 - self.config.STOP_LOSS_PERCENT) if side == 'BUY' else \
                    price * (1 + self.config.STOP_LOSS_PERCENT)
        take_profit = price * (1 + self.config.TAKE_PROFIT_PERCENT) if side == 'BUY' else \
                     price * (1 - self.config.TAKE_PROFIT_PERCENT)
        
        self.positions[symbol] = {
            'side': side,
            'entry_price': price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'position_size': position_size / price,  # Cantidad en la moneda base
            'cost': cost,  # Costo en USDT
            'pattern': pattern_info,
            'timestamp': timestamp
        }
        
        self.balance -= cost
    
    def close_position(self, symbol: str, exit_price: float, timestamp: datetime, reason: str):
        """Close an existing position"""
        if symbol not in self.positions:
            return
        
        position = self.positions[symbol]
        
        # Calcular PnL
        if position['side'] == 'BUY':
            pnl = (exit_price - position['entry_price']) * position['position_size']
        else:
            pnl = (position['entry_price'] - exit_price) * position['position_size']
        
        # Actualizar balance
        self.balance += position['cost'] + pnl
        
        trade_record = {
            'symbol': symbol,
            'side': position['side'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'position_size': position['position_size'],
            'pnl': pnl,
            'pnl_percent': (pnl / position['cost']) * 100,
            'entry_time': position['timestamp'],
            'exit_time': timestamp,
            'reason': reason,
            'pattern': position['pattern']
        }
        
        self.trades_history.append(trade_record)
        del self.positions[symbol]
    
    def run_backtest(self, historical_data: Dict[str, pd.DataFrame]) -> Dict:
        """Run backtest on historical data"""
        results = {
            'trades': [],
            'balance_history': [],
            'metrics': {}
        }
        
        # Reset state
        self.balance = self.initial_balance
        self.positions = {}
        self.trades_history = []
        
        # Ordenar datos históricos por timeframe
        timeframes = {}
        for key, df in historical_data.items():
            symbol, timeframe = key.split('_')
            if symbol not in timeframes:
                timeframes[symbol] = []
            timeframes[symbol].append(timeframe)
        
        # Procesar cada símbolo
        for symbol in self.config.SYMBOLS:
            # Combinar análisis de múltiples timeframes
            for i in range(len(historical_data[f"{symbol}_{self.config.TIMEFRAMES[0]}"])):
                current_time = historical_data[f"{symbol}_{self.config.TIMEFRAMES[0]}"].index[i]
                
                # Analizar patrones en todos los timeframes
                patterns_by_timeframe = {}
                for timeframe in timeframes[symbol]:
                    df_timeframe = historical_data[f"{symbol}_{timeframe}"]
                    current_idx = df_timeframe.index.get_indexer([current_time], method='nearest')[0]
                    if current_idx >= 0:
                        lookback = min(current_idx + 1, 100)
                        analysis_df = df_timeframe.iloc[current_idx-lookback+1:current_idx+1]
                        patterns_by_timeframe[timeframe] = self.pattern_analyzer.analyze_patterns(analysis_df)
                
                # Verificar señales de trading
                buy_signals = 0
                sell_signals = 0
                
                for timeframe_patterns in patterns_by_timeframe.values():
                    if timeframe_patterns['order_blocks']:
                        latest_ob = timeframe_patterns['order_blocks'][-1]
                        if latest_ob['type'] == 'bullish':
                            buy_signals += 1
                        elif latest_ob['type'] == 'bearish':
                            sell_signals += 1
                    
                    if timeframe_patterns['fair_value_gaps']:
                        latest_fvg = timeframe_patterns['fair_value_gaps'][-1]
                        if latest_fvg['type'] == 'bullish':
                            buy_signals += 1
                        elif latest_fvg['type'] == 'bearish':
                            sell_signals += 1
                
                current_price = historical_data[f"{symbol}_{self.config.TIMEFRAMES[0]}"].iloc[i]['Close']
                
                # Gestionar posiciones existentes
                if symbol in self.positions:
                    pos = self.positions[symbol]
                    if pos['side'] == 'BUY':
                        if current_price <= pos['stop_loss']:
                            self.close_position(symbol, current_price, current_time, 'Stop Loss')
                        elif current_price >= pos['take_profit']:
                            self.close_position(symbol, current_price, current_time, 'Take Profit')
                    else:  # SELL
                        if current_price >= pos['stop_loss']:
                            self.close_position(symbol, current_price, current_time, 'Stop Loss')
                        elif current_price <= pos['take_profit']:
                            self.close_position(symbol, current_price, current_time, 'Take Profit')
                
                # Abrir nuevas posiciones
                elif len(self.positions) < self.config.MAX_POSITIONS:
                    if buy_signals >= 2:
                        self.open_position(symbol, 'BUY', current_price, current_time, patterns_by_timeframe)
                    elif sell_signals >= 2:
                        self.open_position(symbol, 'SELL', current_price, current_time, patterns_by_timeframe)
                
                # Registrar historial de balance
                total_position_value = sum(
                    pos['position_size'] * current_price
                    for pos in self.positions.values()
                )
                
                results['balance_history'].append({
                    'timestamp': current_time,
                    'balance': self.balance + total_position_value
                })
        
        # Cerrar posiciones abiertas al final del backtest
        final_prices = {
            symbol: historical_data[f"{symbol}_{self.config.TIMEFRAMES[0]}"].iloc[-1]['Close']
            for symbol in self.config.SYMBOLS
        }
        
        for symbol in list(self.positions.keys()):
            self.close_position(
                symbol,
                final_prices[symbol],
                historical_data[f"{symbol}_{self.config.TIMEFRAMES[0]}"].index[-1],
                'End of Backtest'
            )
        
        results['trades'] = self.trades_history
        results['metrics'] = self.calculate_metrics()
        
        return results
    
    def calculate_metrics(self) -> Dict:
        """Calculate backtest performance metrics"""
        if not self.trades_history:
            return {
                'total_trades': 0,
                'profitable_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'total_return': 0,
                'average_pnl': 0,
                'max_drawdown': 0,
                'final_balance': self.balance,
                'profit_factor': 0
            }
        
        total_trades = len(self.trades_history)
        profitable_trades = len([t for t in self.trades_history if t['pnl'] > 0])
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        pnl_list = [t['pnl'] for t in self.trades_history]
        total_pnl = sum(pnl_list)
        avg_pnl = np.mean(pnl_list) if pnl_list else 0
        
        # Calculate max drawdown
        balance_curve = []
        current_balance = self.initial_balance
        for trade in self.trades_history:
            current_balance += trade['pnl']
            balance_curve.append(current_balance)
        
        max_drawdown = 0
        peak_balance = self.initial_balance
        for balance in balance_curve:
            if balance > peak_balance:
                peak_balance = balance
            drawdown = (peak_balance - balance) / peak_balance
            max_drawdown = max(max_drawdown, drawdown)
        
        # Calculate profit factor
        winning_trades = [t['pnl'] for t in self.trades_history if t['pnl'] > 0]
        losing_trades = [abs(t['pnl']) for t in self.trades_history if t['pnl'] < 0]
        
        profit_factor = sum(winning_trades) / sum(losing_trades) if sum(losing_trades) > 0 else float('inf')
        
        return {
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_return': (total_pnl / self.initial_balance) * 100,
            'average_pnl': avg_pnl,
            'max_drawdown': max_drawdown * 100,
            'final_balance': self.balance,
            'profit_factor': profit_factor
}