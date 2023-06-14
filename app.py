from flask import Flask, request, render_template,send_file
import backtrader as bt
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import csv
import os

app = Flask(__name__)

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



@app.route('/backtest', methods=['POST'])
def backtest():
    start_date_str = request.form['start_date']
    end_date_str = request.form['end_date']
    stake = float(request.form['stake'])
    stocks = request.form['stocks'].split(',')

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    # Clear trades.csv file
    with open('trades.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'stock', 'action', 'price', 'size'])

    results = {}

    for stock in stocks:
        try:
            cerebro_long = bt.Cerebro()
            cerebro_short = bt.Cerebro()

            cerebro_long.broker.setcash(stake)
            cerebro_short.broker.setcash(stake)

            cerebro_long.addsizer(CustomSizer, stake=stake)
            cerebro_short.addsizer(CustomSizer, stake=stake)

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
            long_value = cerebro_long.broker.getvalue()
            cerebro_short.run()
            short_value = cerebro_short.broker.getvalue()

            yearly_return = ((long_value - stake) / stake) * (365.25 / ((end_date - start_date).days)) * 100

            results[stock] = {
                'long_value': long_value,
                'short_value': short_value,
            }

        except Exception as e:
            print(f'Error encountered: {str(e)}. Skipping {stock}...')

    return render_template('results.html', results=results)

@app.route('/download', methods=['GET'])
def download_file():
    return send_file('trades.csv', as_attachment=True)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

