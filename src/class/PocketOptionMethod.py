from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync
import asyncio

class PocketOptionMethod:
    def __init__(self, walletType = 'demo'):
        self.walletType = walletType
        self.ssid = '''42["auth",{"session":"24k4ea9r0a1qck71rfojrgnl8o","isDemo":1,"uid":96282099,"platform":3}]'''

        if 'real' in self.walletType:
            self.ssid = r'''42["auth",{"session":"a:4:{s:10:\"session_id\";s:32:\"b14deaeb687db05a7a49318bdb0973b6\";s:10:\"ip_address\";s:12:\"102.18.29.29\";s:10:\"user_agent\";s:70:\"Mozilla/5.0 (X11; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0\";s:13:\"last_activity\";i:1743529087;}cc8be88ba075e7d0598e1e887eea1e50","isDemo":0,"uid":96282099,"platform":3}]'''

        self.api = PocketOptionAsync(self.ssid)

    async def getBalance(self):
        balance = await self.api.balance()
        return balance

    async def getHistory(self, asset: str, time: int):
        history = await self.api.history(asset, time)
        return history

    async def buy(self, asset: str, amount: float, time: int, check_win = True):
        buy_id, _ = await self.api.buy(asset=asset, amount=amount, time=time, check_win=check_win)
        return buy_id, _

    async def sell(self, asset: str, amount: float, time: int, check_win = True):
        sell_id, _ = await self.api.sell(asset=asset, amount=amount, time=time, check_win=check_win)
        return sell_id, _

    async def getOpenedDeals(self):
        opened_deals = await self.api.opened_deals()
        return opened_deals

    async def getClosedDeals(self):
        closed_deals = await self.api.closed_deals()
        return closed_deals

    async def getTradeData(self, tradeID):
        tradeData = await self.api.check_win(tradeID)
        return tradeData
