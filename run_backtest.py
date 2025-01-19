from backtest_runner import run_backtest

run_backtest(
    start_date="2023-01-01",
    end_date="2023-06-30",
    symbols=['BTCUSDT', 'ETHUSDT'],
    initial_balance=10000
)