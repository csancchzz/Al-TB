import numpy as np
import pandas as pd
from typing import Dict, List, Tuple

class SMCPatternAnalyzer:
    def __init__(self, config):
        self.config = config
    
    def identify_liquidity_levels(self, df: pd.DataFrame) -> List[Dict]:
        """Identify liquidity levels (swing highs/lows)"""
        levels = []
        window = 5
        
        for i in range(window, len(df) - window):
            # Check for swing highs
            if all(df['High'].iloc[i] > df['High'].iloc[i-window:i]) and \
               all(df['High'].iloc[i] > df['High'].iloc[i+1:i+window+1]):
                levels.append({
                    'type': 'resistance',
                    'price': df['High'].iloc[i],
                    'timestamp': df.index[i]
                })
            
            # Check for swing lows
            if all(df['Low'].iloc[i] < df['Low'].iloc[i-window:i]) and \
               all(df['Low'].iloc[i] < df['Low'].iloc[i+1:i+window+1]):
                levels.append({
                    'type': 'support',
                    'price': df['Low'].iloc[i],
                    'timestamp': df.index[i]
                })
        
        return levels
    
    def identify_order_blocks(self, df: pd.DataFrame) -> List[Dict]:
        """Identify bullish and bearish order blocks"""
        order_blocks = []
        
        for i in range(len(df) - 1):
            # Bullish Order Block
            if df['Close'].iloc[i] > df['Open'].iloc[i] and \
               df['Close'].iloc[i+1] < df['Open'].iloc[i+1] and \
               (df['High'].iloc[i+1] - df['Low'].iloc[i+1]) / df['Low'].iloc[i+1] > self.config.LIQUIDITY_THRESHOLD:
                order_blocks.append({
                    'type': 'bullish',
                    'top': df['High'].iloc[i],
                    'bottom': df['Low'].iloc[i],
                    'timestamp': df.index[i]
                })
            
            # Bearish Order Block
            if df['Close'].iloc[i] < df['Open'].iloc[i] and \
               df['Close'].iloc[i+1] > df['Open'].iloc[i+1] and \
               (df['High'].iloc[i+1] - df['Low'].iloc[i+1]) / df['Low'].iloc[i+1] > self.config.LIQUIDITY_THRESHOLD:
                order_blocks.append({
                    'type': 'bearish',
                    'top': df['High'].iloc[i],
                    'bottom': df['Low'].iloc[i],
                    'timestamp': df.index[i]
                })
        
        return order_blocks
    
    def identify_fair_value_gaps(self, df: pd.DataFrame) -> List[Dict]:
        """Identify fair value gaps"""
        gaps = []
        
        for i in range(1, len(df) - 1):
            # Bullish FVG
            if df['Low'].iloc[i+1] > df['High'].iloc[i-1]:
                gap_size = (df['Low'].iloc[i+1] - df['High'].iloc[i-1]) / df['High'].iloc[i-1]
                if gap_size > self.config.IMBALANCE_THRESHOLD:
                    gaps.append({
                        'type': 'bullish',
                        'top': df['Low'].iloc[i+1],
                        'bottom': df['High'].iloc[i-1],
                        'timestamp': df.index[i]
                    })
            
            # Bearish FVG
            if df['High'].iloc[i+1] < df['Low'].iloc[i-1]:
                gap_size = (df['Low'].iloc[i-1] - df['High'].iloc[i+1]) / df['High'].iloc[i+1]
                if gap_size > self.config.IMBALANCE_THRESHOLD:
                    gaps.append({
                        'type': 'bearish',
                        'top': df['Low'].iloc[i-1],
                        'bottom': df['High'].iloc[i+1],
                        'timestamp': df.index[i]
                    })
        
        return gaps
    
    def analyze_patterns(self, df: pd.DataFrame) -> Dict:
        """Complete pattern analysis"""
        return {
            'liquidity_levels': self.identify_liquidity_levels(df),
            'order_blocks': self.identify_order_blocks(df),
            'fair_value_gaps': self.identify_fair_value_gaps(df)
        }