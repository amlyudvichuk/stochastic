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
            self.data0, period=self.params.lengthK, period_dfast=self.params.smoothK
        )
        self.smaK = bt.indicators.SMA(self.stoch.percK, period=self.params.smoothK)
        self.smaD = bt.indicators.SMA(self.smaK, period=self.params.smoothD)
        self.days_met = 0  # Add a counter for the number of days conditions are met

    def log_indicators(self):
        with open('stochastic.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                self.data0.datetime.date(0).isoformat(),
                self.data0._name,
                self.smaK[0] if len(self.smaK) > 0 else None,
                self.smaD[0] if len(self.smaD) > 0 else None
            ])

    def is_bullish_engulfing(self):
        o1 = self.data0.open[-1]
        c1 = self.data0.close[-1]
        o2 = self.data0.open[0]
        c2 = self.data0.close[0]
        return c2 > o2 and abs(c2-o2) > abs(c1-o1)

    def next(self):
        self.log_indicators()  # Log the stochastic K and D values

        # Check if we have enough data
        if len(self.smaK) > 1 and len(self.smaD) > 1:
            # Check for the conditions
            if self.smaK[0] > self.smaD[0] and 32 < self.smaK[0] < 80:
                self.days_met += 1
                # If conditions are met for 3 days, generate a signal
                if self.days_met > 3 and self.is_bullish_engulfing():
                    print('Signal generated on:', self.data0.datetime.date(0))
            elif self.smaK[0] < self.smaD[0] or not self.is_bullish_engulfing():
                self.days_met = 0  # Reset the counter



start_date = datetime(2020, 1, 1)
end_date = datetime(2023, 1, 1)

# Load the stocks from stocks.csv
stocks = pd.read_csv('stocks.csv', header=None)[0].tolist()

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



