import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from data_fetcher import DataFetcher
from backtesting import Backtester
from config import TradingConfig
import logging
import os
from dotenv import load_dotenv
from typing import Dict, List

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('backtest.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def run_backtest(start_date: str, end_date: str, symbols: List[str] = None, 
                initial_balance: float = 10000):
    """Run backtest for specified period and symbols"""
    # Load environment variables
    load_dotenv()
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        raise ValueError("API credentials not found in environment variables")
    
    logger = setup_logging()
    logger.info(f"Starting backtest from {start_date} to {end_date}")
    
    config = TradingConfig()
    if symbols:
        config.SYMBOLS = symbols
    
    logger.info(f"Testing symbols: {config.SYMBOLS}")
    
    try:
        # Initialize components
        logger.info("Initializing components...")
        data_fetcher = DataFetcher(api_key, api_secret)
        backtester = Backtester(config, initial_balance)
        
        # Fetch historical data
        logger.info("Fetching historical data...")
        historical_data = {}
        for symbol in config.SYMBOLS:
            logger.info(f"Fetching data for {symbol}...")
            for timeframe in config.TIMEFRAMES:
                logger.info(f"Fetching {timeframe} timeframe...")
                df = data_fetcher.get_historical_data(
                    symbol=symbol,
                    interval=timeframe,
                    start_date=start_date,
                    end_date=end_date
                )
                historical_data[f"{symbol}_{timeframe}"] = df
                logger.info(f"Fetched {len(df)} candles for {symbol} {timeframe}")
        
        # Run backtest
        logger.info("Running backtest...")
        results = backtester.run_backtest(historical_data)
        
        # Print results
        logger.info("\nBacktest Results:")
        logger.info("=" * 50)
        #logger.info(f"resultaods:{results}")
        
        """for key, value in results.items():
          print(f"{key}: {value}")
        logger.info(f"Total Trades: {results['metrics']['total_trades']}")
        logger.info(f"Win Rate: {results['metrics']['win_rate']:.2%}")
        logger.info(f"Total Return: {results['metrics']['total_return']:.2%}")
        logger.info(f"Profit Factor: {results['metrics']['profit_factor']:.2f}")
        logger.info(f"Max Drawdown: {results['metrics']['max_drawdown']:.2%}")
        logger.info(f"Final Balance: ${results['metrics']['final_balance']:.2f}")"""
        
        # Print detailed trade history
        logger.info("\nDetailed Trade History:")
        logger.info("=" * 50)
        for trade in results['trades']:
            logger.info(f"""
Trade:
- Symbol: {trade['symbol']}
- Side: {trade['side']}
- Entry Price: ${trade['entry_price']:.2f}
- Exit Price: ${trade['exit_price']:.2f}
- PnL: ${trade['pnl']:.2f} ({trade['pnl_percent']:.2%})
- Entry Time: {trade['entry_time']}
- Exit Time: {trade['exit_time']}
- Reason: {trade['reason']}
""")
        
        # Plot results
        logger.info("Generating plots...")
        plot_backtest_results(results, historical_data)
        for key, value in results.items():
          print(f"{key}: {value}")
        return results
        
    except Exception as e:
        logger.error(f"Error in backtest: {str(e)}")
        raise

def plot_backtest_results(results: Dict, historical_data: Dict):
    """Create interactive plots of backtest results"""
    # Create figure with secondary y-axis
    fig = make_subplots(rows=2, cols=1, 
                       shared_xaxes=True,
                       vertical_spacing=0.03,
                       subplot_titles=('Price Action', 'Account Balance'),
                       row_heights=[0.7, 0.3])
    
    # Plot price action for first symbol
    symbol = list(historical_data.keys())[0]
    df = historical_data[symbol]
    
    fig.add_trace(
        go.Candlestick(x=df.index,
                       open=df['Open'],
                       high=df['High'],
                       low=df['Low'],
                       close=df['Close'],
                       name='Price Action'),
        row=1, col=1
    )
    
    # Plot entry and exit points
    for trade in results['trades']:
        # Entry point
        fig.add_trace(
            go.Scatter(
                x=[trade['entry_time']],
                y=[trade['entry_price']],
                mode='markers',
                marker=dict(
                    symbol='triangle-up' if trade['side'] == 'BUY' else 'triangle-down',
                    size=12,
                    color='green' if trade['side'] == 'BUY' else 'red'
                ),
                name=f"{trade['side']} Entry"
            ),
            row=1, col=1
        )
        
        # Exit point
        fig.add_trace(
            go.Scatter(
                x=[trade['exit_time']],
                y=[trade['exit_price']],
                mode='markers',
                marker=dict(
                    symbol='x',
                    size=12,
                    color='red' if trade['side'] == 'BUY' else 'green'
                ),
                name=f"{trade['side']} Exit"
            ),
            row=1, col=1
        )
    
    # Plot balance history
    balance_df = pd.DataFrame(results['balance_history'])
    fig.add_trace(
        go.Scatter(x=balance_df['timestamp'],
                  y=balance_df['balance'],
                  name='Account Balance'),
        row=2, col=1
    )
    
    # Update layout
    fig.update_layout(
        title='Backtest Results',
        yaxis_title='Price',
        yaxis2_title='Balance',
        xaxis_rangeslider_visible=False
    )
    
    # Show plot
    fig.show()

if __name__ == "_main_":
    # Example usage
    results = run_backtest(
        start_date="2023-01-01",
        end_date="2023-12-31",
        symbols=['BTCUSDT', 'ETHUSDT'],
        initial_balance=10000
)