import backtrader as bt
import yfinance as yf
from datetime import datetime
import pandas as pd
import csv
import os

class CustomSizer(bt.Sizer):
    params = (('stake', 10000),)

    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy:
            size = self.p.stake // data.close[0]
            return size

        position = self.broker.getposition(data)
        if not position.size:
            return 0

        return position.size

class StochasticStrategy(bt.Strategy):
    params = (
        ('lengthK', 92),
        ('smoothK', 18),
        ('smoothD', 18),
    )

    def __init__(self):
        self.stoch = bt.indicators.Stochastic(self.data0, period=self.params.lengthK, period_dfast=self.params.smoothK)
        self.smaK = bt.indicators.SMA(self.stoch.percK, period=self.params.smoothK)
        self.smaD = bt.indicators.SMA(self.smaK, period=self.params.smoothD)
        self.days_met = 0  # Add a counter for the number of days conditions are met
        self.in_market = False

    def is_bullish_engulfing(self):
        o1 = self.data0.open[-1]
        c1 = self.data0.close[-1]
        o2 = self.data0.open[0]
        c2 = self.data0.close[0]
        return c2 > o2 and abs(c2-o2) > abs(c1-o1)

    def log_trade(self, action, price, size):
        with open('trades.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([self.data0.datetime.date(0).isoformat(), self.data0._name, action, price, size])

    def next(self):
        if len(self.stoch) > 1:
            if self.smaK[0] > self.smaD[0] and 32 < self.smaK[0] < 80:
                self.days_met += 1
                if self.days_met >= 3 and self.is_bullish_engulfing() and not self.in_market:
                    self.buy()
                    self.in_market = True
                    self.log_trade('Buy', self.data0.close[0], self.position.size)
            elif self.smaK[0] < self.smaD[0]:
                self.days_met = 0
                if self.in_market:
                    self.sell()
                    self.in_market = False
                    self.log_trade('Sell', self.data0.close[0], self.position.size)

class StochasticShortStrategy(bt.Strategy):
    params = (
        ('lengthK', 92),
        ('smoothK', 18),
        ('smoothD', 18),
    )

    def __init__(self):
        self.stoch = bt.indicators.Stochastic(self.data0, period=self.params.lengthK, period_dfast=self.params.smoothK)
        self.smaK = bt.indicators.SMA(self.stoch.percK, period=self.params.smoothK)
        self.smaD = bt.indicators.SMA(self.smaK, period=self.params.smoothD)
        self.days_met = 0  # Add a counter for the number of days conditions are met
        self.in_market = False

    def is_bearish_engulfing(self):
        o1 = self.data0.open[-1]
        c1 = self.data0.close[-1]
        o2 = self.data0.open[0]
        c2 = self.data0.close[0]
        return c2 < o2 and abs(c2-o2) > abs(c1-o1)

    def log_trade(self, action, price, size):
        with open('trades.csv', 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([self.data0.datetime.date(0).isoformat(), self.data0._name, action, price, size])

    def next(self):
        if len(self.stoch) > 1:
            if self.smaK[0] < self.smaD[0] and self.smaK[0] < 80:
                self.days_met += 1
                if self.days_met >= 3 and self.is_bearish_engulfing() and not self.in_market:
                    self.sell()
                    self.in_market = True
                    self.log_trade('Sell Short', self.data0.close[0], self.position.size)
            elif self.smaK[0] > self.smaD[0]:
                self.days_met = 0
                if self.in_market:
                    self.buy()
                    self.in_market = False
                    self.log_trade('Buy to Cover', self.data0.close[0], self.position.size)


start_date = datetime(2019, 6, 1)
end_date = datetime(2023, 1, 1)

stocks = pd.read_csv('stocks.csv', header=None)[0].tolist()

with open('trades.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Date', 'Symbol', 'Action', 'Price', 'Size'])

if not os.path.exists('trades.csv'):
    with open('trades.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Symbol', 'Action', 'Price', 'Size'])

for stock in stocks:
    try:
        cerebro_long = bt.Cerebro()
        cerebro_short = bt.Cerebro()

        cerebro_long.broker.setcash(10000.0)
        cerebro_short.broker.setcash(10000.0)

        cerebro_long.addsizer(CustomSizer)
        cerebro_short.addsizer(CustomSizer)

        data_daily = yf.download(stock, start=start_date, end=end_date, interval='1d')
        if data_daily.empty:
            print(f"No data for {stock}, skipping...")
            continue

        data_feed_daily = bt.feeds.PandasData(dataname=data_daily, plot=False, name=stock)

        cerebro_long.adddata(data_feed_daily)
        cerebro_long.addstrategy(StochasticStrategy)

        cerebro_short.adddata(data_feed_daily)
        cerebro_short.addstrategy(StochasticShortStrategy)

        print(f'Backtesting for {stock}...')
        cerebro_long.run()
        print(f'Final Portfolio Value for {stock} (Long Strategy): {cerebro_long.broker.getvalue()}')
        cerebro_short.run()
        print(f'Final Portfolio Value for {stock} (Short Strategy): {cerebro_short.broker.getvalue()}')

    except Exception as e:
        print(f'Error encountered: {str(e)}. Skipping {stock}...')
