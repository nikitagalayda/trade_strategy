# Class name must be Strategy
class Strategy():
    # option setting needed
    def __setitem__(self, key, value):
        self.options[key] = value

    # option setting needed
    def __getitem__(self, key):
        return self.options.get(key, '')

    def __init__(self):
        # strategy property
        self.subscribedBooks = {
            'Binance': {
                'pairs': ['BTC-USDT'],
            },
        }
        self.period = 10 * 60
        self.options = {}

        # user defined class attribute
        self.last_type = 'sell'
        self.last_cycle_status = None
        self.close_price_trace = np.array([])
        self.close_volume_trace = np.array([])
        self.low_price_trace = np.array([])
        self.high_price_trace = np.array([])
        self.action_trace = np.array([])
        self.cycle_score_trace = np.array([])
        self.ma_long = 10
        self.ma_short = 5
        self.UP = 1
        self.DOWN = -1
        self.cycle_score = 0
        self.threshold = 0.8
        self.cycle_trend_threshold = 0.6

    def get_ema(self, data):
        s_t3 = talib.EMA(data, self.ma_short)[-1]
        l_t3 = talib.EMA(data, self.ma_long)[-1]

        if np.isnan(l_t3) or np.isnan(s_t3):
            return None
        if s_t3 > l_t3:
            return self.UP
        else:
            return self.DOWN

    def get_adx(self, data, timeperiod):
        adx = talib.ADX(self.high_price_trace, self.low_price_trace, data, 5)
        return adx[-1] / 100.0
    
    def get_cycle_trend(self):
        # Log(self.cycle_score_trace)
        # if len(self.cycle_score_trace < 5):
        #     return 0.0
        # if self.cycle_score_trace.size < self.ma_long:
        #     return 0.0
        tmp_min = np.amin(self.cycle_score_trace)
        c = self.cycle_score_trace + tmp_min

        l_min = np.amin(c)
        l_max = np.amax(c)
        avg = np.average(c)

        res = 2*((avg - l_min) / (l_max - l_min)) - 1

        return res
	
    # called every self.period
    def trade(self, information):
        # Log(str(self.close_price_trace))
        # for single pair strategy, user can choose which exchange/pair to use when launch, get current exchange/pair from information
        exchange = list(information['candles'])[0]
        pair = list(information['candles'][exchange])[0]
        target_currency = pair.split('-')[0]  #ETH
        base_currency = pair.split('-')[1]  #USDT
        base_currency_amount = self['assets'][exchange][base_currency] 
        target_currency_amount = self['assets'][exchange][target_currency] 

        
        # add data into traces
        close_price = information['candles'][exchange][pair][0]['close']
        close_volume = information['candles'][exchange][pair][0]['volume']
        low_price = information['candles'][exchange][pair][0]['low']
        high_price = information['candles'][exchange][pair][0]['high']

        self.close_price_trace = np.append(self.close_price_trace, [float(close_price)])
        self.close_volume_trace = np.append(self.close_volume_trace, [float(close_volume)])
        self.low_price_trace = np.append(self.low_price_trace, [float(low_price)])
        self.high_price_trace = np.append(self.high_price_trace, [float(high_price)])

        # only keep max length of ma_long count elements
        self.close_price_trace = self.close_price_trace[-self.ma_long:]
        self.close_volume_trace = self.close_volume_trace[-self.ma_long:]
        self.low_price_trace = self.low_price_trace[-self.ma_long:]
        self.high_price_trace = self.high_price_trace[-self.ma_long:]

        # trend calculations
        close_price_ema = self.get_ema(self.close_price_trace)
        close_volume_ema = self.get_ema(self.close_volume_trace)
        # s_adx = self.get_adx(self.close_price_trace, self.ma_short)
        l_adx = self.get_adx(self.close_price_trace, self.ma_long)

        self.cycle_score = (close_price_ema)*(0.8*close_volume_ema + l_adx) / 1.8
        # Log(self.cycle_score)
        self.cycle_score_trace = np.append(self.cycle_score_trace, [self.cycle_score])
        self.cycle_score_trace = self.cycle_score_trace[-self.ma_long:]

        cycle_trend = self.get_cycle_trend()
        # Log(str(cycle_trend))
        
        # sign = direction
        # value = magnitude
        # Log(str(self.cycle_score))
        
        # if self.cycle_score > self.threshold and self.last_type == 'sell' and self.last_cycle_status < 0.5:
        # market looking up, and scores have been going up
        # Log(str(self.cycle_score_trace))
        if self.last_type == 'sell' and (self.cycle_score > self.threshold and cycle_trend > 0.2) and self.cycle_score_trace[-2] < 0.3:
        # if self.cycle_score > self.threshold:
            self.action_trace = np.append(self.action_trace, [1])
            # Log('buying 1 unit of ' + str(target_currency))
            self.last_type = 'buy'
            return [
                {
                    'exchange': exchange,
                    'amount': 0.5,
                    'price': -1,
                    'type': 'MARKET',
                    'pair': pair,
                }
            ]
        # elif self.cycle_score < 0.4 and self.last_type == 'buy' and self.last_cycle_status > self.threshold:
        elif self.last_type == 'buy' and (self.cycle_score < 0.3 and cycle_trend < 0) and self.cycle_score_trace[-2] > 0.5:
        # if self.cycle_score < -self.threshold:
            self.action_trace = np.append(self.action_trace, [-1])
            # Log('assets before selling: ' + str(self['assets'][exchange][base_currency]))
            self.last_type = 'sell'
            return [
                {
                    'exchange': exchange,
                    'amount': -0.5,
                    'price': -1,
                    'type': 'MARKET',
                    'pair': pair,
                }
            ]
        # buy at the dip
        # elif (self.cycle_score < 0.3 and cycle_trend < 0):
        #     self.action_trace = np.append(self.action_trace, [1])
        #     # Log('assets before selling: ' + str(self['assets'][exchange][base_currency]))
        #     self.last_type = 'buy'
        #     return [
        #         {
        #             'exchange': exchange,
        #             'amount': 1,
        #             'price': -1,
        #             'type': 'MARKET',
        #             'pair': pair,
        #         }
        #     ]
        self.last_cycle_status = self.cycle_score

        return []
	

    def on_order_state_change(self, order):
        # pass
        Log("on order state change message: " + str(order) + " order price: " + str(order["price"]))
        Log('price Trace: ' + str(self.close_price_trace))
