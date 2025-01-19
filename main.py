import os
from dotenv import load_dotenv
import time
import logging
from data_fetcher import DataFetcher
from patterns import SMCPatternAnalyzer
from trading_bot import TradingBot
from config import TradingConfig

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('trading.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize logger
    logger = setup_logging()
    
    # Load configuration
    config = TradingConfig()
    
    try:
        # Initialize components
        api_key = os.getenv('BINANCE_API_KEY')
        api_secret = os.getenv('BINANCE_API_SECRET')
        # logger.info(f"api_key: {api_key} api_secret: {api_secret} ")
        if not api_key or not api_secret:
            raise ValueError("API credentials not found in environment variables")
        
        data_fetcher = DataFetcher(api_key, api_secret)
        pattern_analyzer = SMCPatternAnalyzer(config)
        trading_bot = TradingBot(api_key, api_secret, config)
        
        logger.info("Trading bot initialized successfully")
        
        while True:
            try:
                for symbol in config.SYMBOLS:
                    for timeframe in config.TIMEFRAMES:
                        # Fetch latest data
                        df = data_fetcher.get_historical_data(
                            symbol=symbol,
                            interval=timeframe,
                            lookback_days=30
                        )
                        #logger.info(f"data_fetcher: {df} symbol: {symbol}")
                        # Analyze patterns
                        patterns = pattern_analyzer.analyze_patterns(df)
                        
                        # Execute trades based on analysis
                        trading_bot.execute_trades(patterns, symbol)
                        
                        # Monitor existing positions
                        trading_bot.monitor_positions()
                        
                        logger.info(f"Completed analysis for {symbol} on {timeframe} timeframe")
                
                # Sleep for 1 minute before next iteration
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in main loop: {str(e)}")
                time.sleep(60)  # Wait before retrying
                
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    main()