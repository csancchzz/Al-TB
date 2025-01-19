from binance.client import Client
from binance.enums import *
import pandas as pd
from typing import Dict, List
import logging
from datetime import datetime

class TradingBot:
    def __init__(self, api_key: str, api_secret: str, config):
        self.client = Client(api_key, api_secret)
        self.config = config
        self.open_positions = {}
        self.setup_logging()
    
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('trading_bot.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def calculate_position_size(self, symbol: str) -> float:
        """Calculate position size based on account balance and risk parameters"""
        account_info = self.client.get_account()
        balance = float([asset for asset in account_info['balances'] 
                        if asset['asset'] == 'USDT'][0]['free'])
        position_size = balance * self.config.POSITION_SIZE
        return position_size
    
    def place_order(self, symbol: str, side: str, pattern_info: Dict) -> Dict:
        """Place a new order based on pattern analysis"""
        try:
            position_size = self.calculate_position_size(symbol)
            current_price = float(self.client.get_symbol_ticker(symbol=symbol)['price'])
            
            # Calculate stop loss and take profit levels
            if side == 'BUY':
                stop_loss = current_price * (1 - self.config.STOP_LOSS_PERCENT)
                take_profit = current_price * (1 + self.config.TAKE_PROFIT_PERCENT)
            else:
                stop_loss = current_price * (1 + self.config.STOP_LOSS_PERCENT)
                take_profit = current_price * (1 - self.config.TAKE_PROFIT_PERCENT)
            
            # Place main order
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type=ORDER_TYPE_MARKET,
                quantity=position_size
            )
            
            # Place stop loss
            sl_order = self.client.create_order(
                symbol=symbol,
                side='SELL' if side == 'BUY' else 'BUY',
                type=ORDER_TYPE_STOP_LOSS_LIMIT,
                timeInForce=TIME_IN_FORCE_GTC,
                quantity=position_size,
                stopPrice=stop_loss,
                price=stop_loss
            )
            
            # Place take profit
            tp_order = self.client.create_order(
                symbol=symbol,
                side='SELL' if side == 'BUY' else 'BUY',
                type=ORDER_TYPE_LIMIT,
                timeInForce=TIME_IN_FORCE_GTC,
                quantity=position_size,
                price=take_profit
            )
            
            self.open_positions[symbol] = {
                'side': side,
                'entry_price': current_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'position_size': position_size,
                'pattern': pattern_info,
                'timestamp': datetime.now()
            }
            
            self.logger.info(f"New position opened for {symbol}: {self.open_positions[symbol]}")
            return order
            
        except Exception as e:
            self.logger.error(f"Error placing order: {str(e)}")
            return None
    
    def check_pattern_validity(self, pattern_info: Dict) -> bool:
        """Validate pattern before placing trade"""
        # Add your pattern validation logic here
        return True
    
    def execute_trades(self, patterns: Dict, symbol: str):
        """Execute trades based on pattern analysis"""
        if len(self.open_positions) >= self.config.MAX_POSITIONS:
            self.logger.info("Maximum positions reached")
            return
        
        if symbol in self.open_positions:
            self.logger.info(f"Position already open for {symbol}")
            return
        
        # Check for strong buy signals
        buy_signals = 0
        if patterns['order_blocks']:
            latest_ob = patterns['order_blocks'][-1]
            if latest_ob['type'] == 'bullish':
                buy_signals += 1
        
        if patterns['fair_value_gaps']:
            latest_fvg = patterns['fair_value_gaps'][-1]
            if latest_fvg['type'] == 'bullish':
                buy_signals += 1
        
        # Check for strong sell signals
        sell_signals = 0
        if patterns['order_blocks']:
            latest_ob = patterns['order_blocks'][-1]
            if latest_ob['type'] == 'bearish':
                sell_signals += 1
        
        if patterns['fair_value_gaps']:
            latest_fvg = patterns['fair_value_gaps'][-1]
            if latest_fvg['type'] == 'bearish':
                sell_signals += 1
        
        # Execute trades based on signals
        if buy_signals >= 2:
            self.place_order(symbol, 'BUY', patterns)
        elif sell_signals >= 2:
            self.place_order(symbol, 'SELL', patterns)
    
    def monitor_positions(self):
        """Monitor and manage open positions"""
        for symbol, position in list(self.open_positions.items()):
            current_price = float(self.client.get_symbol_ticker(symbol=symbol)['price'])
            
            # Check stop loss
            if position['side'] == 'BUY' and current_price <= position['stop_loss']:
                self.close_position(symbol, 'Stop loss hit')
            elif position['side'] == 'SELL' and current_price >= position['stop_loss']:
                self.close_position(symbol, 'Stop loss hit')
            
            # Check take profit
            if position['side'] == 'BUY' and current_price >= position['take_profit']:
                self.close_position(symbol, 'Take profit hit')
            elif position['side'] == 'SELL' and current_price <= position['take_profit']:
                self.close_position(symbol, 'Take profit hit')
    
    def close_position(self, symbol: str, reason: str):
        """Close an open position"""
        try:
            position = self.open_positions[symbol]
            
            # Close position with market order
            order = self.client.create_order(
                symbol=symbol,
                side='SELL' if position['side'] == 'BUY' else 'BUY',
                type=ORDER_TYPE_MARKET,
                quantity=position['position_size']
            )
            
            self.logger.info(f"Position closed for {symbol}. Reason: {reason}")
            del self.open_positions[symbol]
            
        except Exception as e:
            self.logger.error(f"Error closing position: {str(e)}")