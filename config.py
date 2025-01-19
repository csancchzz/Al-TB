from dataclasses import dataclass
from typing import Dict, List

@dataclass
class TradingConfig:
    TIMEFRAMES: List[str] = ('1h', '4h', '1d')
    SYMBOLS: List[str] = ('BTCUSDT', 'ETHUSDT', 'XRPUSDT')
    
    # SMC Pattern Parameters
    LIQUIDITY_THRESHOLD: float = 0.02  # 2% threshold for liquidity levels
    ORDER_BLOCK_LOOKBACK: int = 20     # Candles to look back for order blocks
    IMBALANCE_THRESHOLD: float = 0.015  # 1.5% threshold for fair value gaps
    
    # Trading Parameters
    POSITION_SIZE: float = 0.01        # 1% of account balance
    MAX_POSITIONS: int = 3
    STOP_LOSS_PERCENT: float = 0.02    # 2% stop loss
    TAKE_PROFIT_PERCENT: float = 0.04  # 4% take profit