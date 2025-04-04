import asyncio, sys, logging

from PocketOptionMethod import PocketOptionMethod

class PocketOptionAPI:
    MAX_RETRY = 2
    LIMIT_BALANCE = 25
    MAX_BID = 4 # All trade will be $1 so with Martingale 2 as limit, 4 is the max bid

    def __init__(self, walletType = 'demo'):
        self._variables = {}
        self.walletType = walletType

    @property
    def variables(self):
        return self._variables

    @variables.setter
    def variables(self, value):
        if not isinstance(value, dict):
            raise TypeError("Value must be a dictionary")
        self._variables = value

    def get_channel_data(self, channel):
        return self._variables.get(channel, {})

    def set_channel_data(self, channel, data):
        if not isinstance(data, dict):
            raise TypeError("Channel data must be a dictionary")
        required_keys = {"asset", "action", "expiration", "amount"}
        if not all(key in data for key in required_keys):
            raise KeyError(f"Data must contain keys: {required_keys}")
        self._variables[channel] = data

    def remove_channel_data(self, channel):
        """
            Remove all data for a specific channel.
            Returns True if channel was removed, False if it didn't exist.
            """
        if channel in self._variables:
            del self._variables[channel]
            return True
        return False

    def has_channel(self, channel):
        """
        Check if a channel exists in the variables.
        Returns True if channel exists, False otherwise.
        """
        return channel in self._variables

    def get_value(self, channel, key):
        channel_data = self.get_channel_data(channel)
        return channel_data.get(key)

    def set_value(self, channel, key, value):
        if channel not in self._variables:
            self._variables[channel] = {}
        if key != "channel":
            self._variables[channel][key] = value

    async def trade(self, channel, check_win = False):
        up = ['BUY', 'CALL']
        down = ['SELL', 'PUT']

        # Get the channel data
        channel_data = self.get_channel_data(channel)
        asset = channel_data.get("asset")
        action = channel_data.get("action")
        expiration = channel_data.get("expiration")
        amount = channel_data.get("amount")

        if not asset or not action or not expiration or not amount:
            raise ValueError("Missing required data for trading")

        pocketOptionMethod = PocketOptionMethod(self.walletType)

        if action in up:
            tradeID, _ = await pocketOptionMethod.buy(asset=asset, amount=amount, time=expiration, check_win=check_win)

            if check_win:
                print(_)
                if _.get('result') in ['win', 'draw']:
                    return True
                else:
                    return False
            else:
                return tradeID
        elif action in down:
            tradeID, _ = await pocketOptionMethod.sell(asset=asset, amount=amount, time=expiration, check_win=check_win)

            if check_win:
                print(_)
                if _.get('result') in ['win', 'draw']:
                    return True
                else:
                    return False
            else:
                return tradeID
        else:
            raise ValueError(f'Incorrect action : {action}')

    async def getTradeData(self, tradeID):
        try:
            pocketOptionMethod = PocketOptionMethod(self.walletType)
            await asyncio.sleep(5)

            # 1st tentative : With check_win
            tradeData = await pocketOptionMethod.getTradeData(tradeID)

            if not tradeData:
                # Check in closed deals
                closed_deals = await pocketOptionMethod.getClosedDeals()
                tradeData = next((trade for trade in closed_deals if str(trade.get('id')) == str(tradeID)), None)

            return tradeData
        except Exception as e:
            logging.error(f'Error when fetching tradeData for trade {tradeID}: {str(e)}')
            return None

    async def getBalanceAmount(self):
        pocketOptionMethod = PocketOptionMethod(self.walletType)
        await asyncio.sleep(5)
        balance = await pocketOptionMethod.getBalance()
        return balance

    async def isBreakingBalanceLimit(self):
        # Check if the balance is below the limit
        balance = await self.getBalanceAmount()
        if balance < self.LIMIT_BALANCE:
            print(f"Balance {balance} is below the limit.")
            return True

        return False

    async def getOpenedDeals(self):
        pocketOptionMethod = PocketOptionMethod(self.walletType)
        opened_deals = await pocketOptionMethod.getOpenedDeals()
        return opened_deals

    async def getClosedDeals(self):
        pocketOptionMethod = PocketOptionMethod(self.walletType)
        closed_deals = await pocketOptionMethod.getClosedDeals()
        return closed_deals