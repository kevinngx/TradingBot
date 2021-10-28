class HyperActiveVioletDinosaur(QCAlgorithm):
    
    '''
    Breakout Strategy
    - Cut losses short
    - Let winners run
    
    Buy Condition:
    - Look at past highs of an instrument and buy if the stock breaks out of it's last high
    - Look at closing prices of previous n days for the highest price (n = lookback) 
    - We will use a volatility adjusted lookback length
    - If volatility is high, we look further back 
    - Algorithm will adapt to volatility levels
    - Highest price is the breakout level
    
    Sell Condition:
    - Set a trading stop loss for when the stock drops M% below the previous high
    
    '''

    def Initialize(self):
        
        # Set initial cash amount for the bot, but in reality this will come from the trading account
        self.SetCash(100000)
        
        # Set dates for backtesting
        self.SetStartDate(2020, 10, 28)
        self.SetEndDate(2021, 10, 28)
        
        # Set security for testing
        self.symbol = self.AddEquity("BTC", Resolution.Daily).Symbol
        
        # Set the initial lookback, noting this will change later, as well as caps/floors for the lookback
        self.lookback = 20
        self.ceiling = 30
        self.floor = 10
        
        # Set the stop loss parameters
        self.initialStopRisk = 0.98 # Stop loss will allow for a 2% 
        self.trailingStopRisk = 0.9 # How close our trading stop will trail the price --> trail the price by 10%
        
        self.Schedule.On(self.DateRules.EveryDay(self.symbol), self.TimeRules.AfterMarketOpen(self.symbol, 20), Action(self.EveryMarketOpen))


    def OnData(self, data):
        '''
            OnData event is the primary entry point for your algorithm. Each new data point will be pumped in here.
            data: Slice object keyed by symbol containing the stock data
        '''

        self.Plot("Data Chart", self.symbol, self.Securities[self.symbol].Close)
        
    
    def EveryMarketOpen(self):
        # 30 day volatility today, compared to same value yesterday
        close = self.History(self.symbol, 31, Resolution.Daily)["close"] # returns a df containing high, low, close and open prices
        today_volatility = np.std(close[1:31])
        yesterday_volatility = np.std(close[0:30])
        delta_volatility = (today_volatility - yesterday_volatility) / today_volatility
        
        self.lookback = round(self.lookback * (1 + delta_volatility))
        
        if self.lookback > self.ceiling:
            self.lookback = self.ceiling
        elif self.lookback < self.floor:
            self.lookback = self.floor
            
        self.high = self.History(self.symbol, self.lookback, Resolution.Daily)["high"]
        
        # Buy if the previous high (self.Securities[self.symbol].Close) is higher than the highest high 
        # Check #1 = checks we are not currently invested
        # Check #2 = check the breakout is actually happenning
        if not self.Securities[self.symbol].Invested and self.Securities[self.symbol].Close >= max(self.high[:-1]) :
            # Buy at the market price
            self.SetHoldings(self.symbol, 1) # Stock to be traded and percentage (0.00 -> 1.00)
            self.breakoutlvl = max(self.high[:-1])
            self.highestPrice = self.breakoutlvl
            
        # Set trading stop loss
        if self.Securities[self.symbol].Invested:
            if not self.Transactions.GetOpenOrders(self.symbol):
                self.stopMarketTicket = self.StopMarketOrder(self.symbol, \
                                                            -self.Portfolio[self.symbol].Quantity, \
                                                            self.initialStopRisk * self.breakoutlvl)
                                                            
            if self.Securities[self.symbol].Close > self.highestPrice and \
            self.initialStopRisk * self.breakoutlvl < self.Securities[self.symbol].Close * self.trailingStopRisk:
                self.highestPrice = self.Securities[self.symbol].Close
                updateFields = UpdateOrderFields()
                updateFields.StopPrice = self.Securities[self.symbol].Close * self.trailingStopRisk
                self.stopMarketTicket.Update(updateFields)
                self.Debug(updateFields.StopPrice)
                
            self.Plot("Data Chart", "Stop Price", self.stopMarketTicket.Get(OrderField.StopPrice))
            