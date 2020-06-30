#!/usr/bin/env python
## Test an algorithm against maximum history
import sys
if sys.version_info[0] != 3 or sys.version_info[1] < 6:
  print("This script requires Python version >=3.6")
  sys.exit(1)

import alpaca
import datetime
from matplotlib import pyplot
import numpy as np
import sys

class Simulation:

  ## Initialize simulation by loading the appropriate data
  #  @param fromDate datetime.date start date (inclusive)
  #  @param toDate datetime.date end date (inclusive)
  #  @param symbol to load, None will load all symbols from watchlist
  def __init__(self, fromDate, toDate=datetime.date.today(), symbol=None):
    self.api = alpaca.Alpaca()
    self.strategy = None
    self.cash = 0
    self.securities = {}
    self.timestamps = self.api.getTimestamps(fromDate, toDate)
    if symbol:
      self.securities[symbol] = self.api.loadSymbol(symbol, self.timestamps)
    else:
      symbols = self.api.getSymbols()
      for symbol in symbols:
        self.securities[symbol] = self.api.loadSymbol(symbol, self.timestamps)
    if len(self.securities.keys()) == 0:
      print("No symbols loaded")
      sys.exit(1)
    self.closingValue = []
    self.dailyReturn = []

  ## Setup the initial conditions of the simulation
  #  @param strategy object to simulate
  #  @param initialCapital to start the simulation with
  def setup(self, strategy, initialCapital=10000):
    self.initialCapital = initialCapital
    self.strategy = strategy
    self.strategy._setup(self.securities, initialCapital)
    for security in self.securities.values():
      security.setup()

    # TODO test how many historical days the strategy needs

  ## Run a simulation, expects setup to be called just before
  def run(self):
    skipDate = None
    start = datetime.datetime.now()
    for timestamp in self.timestamps[0]:
      if timestamp.date() == skipDate:
        continue
      self.strategy.portfolio._setCurrentTimestamp(timestamp)
      self.strategy.portfolio._processOrders()
      try:
        self.strategy.nextMinute()
      except ValueError:
        print("{} ValueError: likely requesting non existant history, reseting to tomorrow".format(
          timestamp))
        self.setup(self.strategy, self.initialCapital)
        skipDate = timestamp.date()
        self.timestamps[1].remove(self.timestamps[1][0])
        pass

      if timestamp.minute == 59 and timestamp in self.timestamps[2]:
        print("Close", timestamp.date())
        value = self.strategy.portfolio.value()
        if len(self.closingValue) > 0:
          self.dailyReturn.append((value / self.closingValue[-1] - 1) * 100)
        else:
          self.dailyReturn.append(0)
        self.closingValue.append(value)

    print("Elapsed test duration: {}".format(datetime.datetime.now() - start))

  ## Generate a report of the simulation with statistics
  #  @return multiline string
  def report(self):
    report = ""
    sharpe = np.mean(self.dailyReturn) / \
        np.std(self.dailyReturn) * np.sqrt(252)
    report += "Sharpe ratio: {:.3f}\n".format(sharpe)
    report += "Closing value:  ${:10.2f}\n".format(self.closingValue[-1])
    profit = self.closingValue[-1] - self.initialCapital
    profitPercent = profit / self.initialCapital
    # (PeriodPercent + 1)^(number of periods in a trading year)
    profitPercentYr = np.power(
      (profitPercent + 1), 252 / len(self.closingValue)) - 1
    report += "Closing profit: ${:10.2f} = {:.2f}% = {:.2f}%(yr)\n".format(
        profit, profitPercent * 100, profitPercentYr * 100)
    return report

  def plot(self, symbol=None):
    fig, ax1 = pyplot.subplots()
    if symbol:
      # TODO
      pass
    else:
      color = 'tab:red'
      ax1.set_xlabel('Timestamp')
      ax1.set_ylabel('Closing Value ($)', color=color)
      ax1.plot(self.timestamps[1], self.closingValue, color=color)
      ax1.tick_params(axis='y', labelcolor=color)

      ax2 = ax1.twinx()

      color = 'tab:blue'
      ax2.set_ylabel('Daily Return (%)', color=color)
      ax2.plot(self.timestamps[1], self.dailyReturn, color=color)
      ax2.tick_params(axis='y', labelcolor=color)

    fig.tight_layout()
    pyplot.show()