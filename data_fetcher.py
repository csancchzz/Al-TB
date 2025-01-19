from binance.client import Client
import pandas as pd
from datetime import datetime, timedelta
from typing import List

class DataFetcher:
    def __init__(self, api_key: str, api_secret: str):
        self.client = Client(api_key, api_secret)
    
    def get_historical_data(self, symbol: str, interval: str, 
                          start_date: str = None, end_date: str = None,
                          lookback_days: int = 30) -> pd.DataFrame:
        """Fetch historical klines/candlestick data"""
        # Calculate start time if not provided
        if start_date:
            start_time = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start_time = datetime.now() - timedelta(days=lookback_days)
        
        # Calculate end time if provided
        end_time = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        
        # Get klines
        klines = self.client.get_historical_klines(
            symbol=symbol,
            interval=interval,
            start_str=start_time.strftime("%d %b %Y %H:%M:%S"),
            end_str=end_time.strftime("%d %b %Y %H:%M:%S") if end_time else None
        )
        
        # Convert to DataFrame
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'Open', 'High', 'Low', 'Close', 'Volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
        ])
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Convert price columns to float
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            df[col] = df[col].astype(float)
        
        # Set timestamp as index
        df.set_index('timestamp', inplace=True)
        
        return df
    
    def get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol"""
        ticker = self.client.get_symbol_ticker(symbol=symbol)
        return float(ticker['price'])