import backtrader as bt
import yfinance as yf
from datetime import datetime
import pandas as pd
import csv

class StochasticStrategy(bt.Strategy):
    params = (
        ('lengthK', 92),
        ('smoothK', 18),
        ('smoothD', 18),
    )

    def __init__(self):
        self.stoch = bt.indicators.Stochastic(
            self.data0, period=self.params.lengthK
        )
        self.smaK = bt.indicators.SMA(self.stoch.percK, period=self.params.smoothK)
        self.smaD = bt.indicators.SMA(self.smaK, period=self.params.smoothD)

    def log_indicators(self):
        with open('stochastic_values.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                self.data0.datetime.date(0).isoformat(),
                self.data0._name,
                self.smaK[0] if len(self.smaK) > 0 else None,
                self.smaD[0] if len(self.smaD) > 0 else None
            ])

    def next(self):
        self.log_indicators()  # Log the stochastic K and D values


start_date = datetime(2022, 1, 1)
end_date = datetime(2023, 1, 1)

# Load the stocks from stocks.csv
stocks = pd.read_csv('stocks.csv', header=None)[0].tolist()

# Write headers to the csv file
with open('stochastic_values.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Date', 'Ticker', 'K', 'D'])

for stock in stocks:
    # Create a Cerebro entity
    cerebro = bt.Cerebro()

    # Download the daily data
    data_daily = yf.download(stock, start=start_date, end=end_date, interval='1d')

    # Create backtrader data feeds from the downloaded data
    data_feed_daily = bt.feeds.PandasData(dataname=data_daily, plot=False, name=stock)

    # Add data feeds to cerebro
    cerebro.adddata(data_feed_daily)  # add daily data feed

    # Add strategy to cerebro
    cerebro.addstrategy(StochasticStrategy)

    # Run the backtest
    cerebro.run()
