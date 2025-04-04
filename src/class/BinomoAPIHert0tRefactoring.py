from websocket import create_connection
from collections import Counter
import time
import random
import string
import json
import requests
import datetime
import threading
import urllib.parse


class Client:
    def __init__(self):
        # Initialize headers with user agent
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36'
        }

        # Load configuration files
        self._load_configs()

        # Trading settings
        self.amount = 1
        self.walletType = 'demo'

        # Initialize asset information
        self._init_asset_info()

        # WebSocket endpoints
        self.pollHost = "wss://as.binomo.com/"
        self.apiHost = f"wss://ws.binomo.com/?authtoken={self.authToken}&device=web&device_id={self.deviceId}&v=2&vsn=2.0.0"

        # Trading state variables
        self.history = []
        self.lastSend = time.time()
        self.ref = 1
        self.stop = False

        # Initialize WebSocket connection
        self.wsApi = create_connection(self.apiHost, header=self.headers)

        # Start background threads
        self._start_background_threads()

        # Initialize Phoenix channels
        self.phxJoin()
        print("[ CALLBACK OPERATION ] BOT STARTED...")

    def _load_configs(self):
        """Load configuration files for assets and credentials"""
        with open("../../assets/assets.json", "r") as f:
            self.assetList = json.loads(f.read())
        with open("../../assets/binomoCredentials.json", "r") as f:
            self.settings = json.loads(f.read())
            self.authToken = self.settings["authToken"]
            self.currency = self.settings["currency"]
            self.deviceId = self.settings["deviceId"]

    def _init_asset_info(self):
        """Initialize asset ID and RIC based on currency"""
        for asset in self.assetList:
            if asset["name"] == self.currency:
                self.assetId = asset["id"]
                self.assetRic = asset["ric"]

    def _start_background_threads(self):
        """Start WebSocket listener and market polling threads"""
        threading.Thread(target=self.hook, daemon=True).start()
        threading.Thread(target=self.pollingMarket, daemon=True).start()

    def getCurrentBalance(self):
        """Get current wallet balance"""
        headers = {
            'device-id': self.deviceId,
            'device-type': 'web',
            'authorization-token': self.authToken,
            'User-Agent': self.headers['User-Agent']
        }
        res = requests.get("https://api.binomo.com/bank/v1/read?locale=en", headers=headers).json()
        for account in res["data"]:
            if account["account_type"] == self.walletType:
                return account["amount"] / 100

    def getHistoryMarket(self):
        """Fetch market history for current day"""
        now = datetime.datetime.now().strftime("%Y-%m-%d")
        url = f"https://api.binomo.com/platform/candles/{urllib.parse.quote_plus(self.assetRic)}/{now}T00:00:00/60?locale=en"
        return requests.get(url, headers=self.headers).json()["data"]

    def parseBidTime(self, minutes=1):
        """Calculate bid expiration time"""
        now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:00")
        bid = datetime.datetime.strptime(now, "%d/%m/%Y %H:%M:%S") + datetime.timedelta(minutes=minutes)
        return str(int(time.mktime(bid.timetuple())))

    def getBid(self, status, amount):
        """Create a new trading bid"""
        # Determine bid time based on current seconds
        bidTime = self.parseBidTime() if int(datetime.datetime.now().strftime("%S")) < 30 else self.parseBidTime(2)

        # Prepare bid payload
        payload = {
            "topic": "base",
            "event": "create_deal",
            "payload": {
                "amount": amount * 100,
                "asset": self.assetRic,
                "asset_id": self.assetId,
                "asset_name": self.currency,
                "created_at": int(time.time()),
                "currency_iso": "IDR",
                "deal_type": self.walletType,
                "expire_at": bidTime,
                "option_type": "turbo",
                "tournament_id": None,
                "trend": status,
                "is_state": False
            },
            "ref": "~~",
            "join_ref": "~~"
        }
        self.sendWs(json.dumps(payload))

    def hook(self):
        """WebSocket message handler"""
        while True:
            data = json.loads(self.wsApi.recv())

            if data["event"] == "deal_created":
                print(f"[ CALLBACK OPERATION ] CREATED DEAL AMOUNT: {int(data['payload']['amount'] / 100)}")

            elif data["event"] == "asset_changed_v1":
                payment_rate = data["payload"]["trading_tools_settings"]["standard"]["payment_rate_standard"]
                print(f"[ CALLBACK OPERATION ] ASSET RATE CHANGED: {payment_rate}%")

                # Stop trading if rate is too low
                self.stop = payment_rate < 75

            else:
                print(data)

            # Send heartbeat every 35 seconds
            if time.time() - self.lastSend > 35:
                print("[ CALLBACK OPERATION ] PHOENIX HEARTBEAT")
                self.sendWs('{"topic":"phoenix","event":"heartbeat","payload":{},"ref":"~~"}')

    def phxJoin(self):
        """Join Phoenix channels"""
        channels = ["account", "user", "base", "cfd_zero_spread", "marathon"]
        for channel in channels:
            self.sendWs(f'{{"topic":"{channel}","event":"phx_join","payload":{{}},"ref":"~~","join_ref":"~~"}}')
        self.sendWs(f'{{"topic":"asset:{self.assetRic}","event":"phx_join","payload":{{}},"ref":"~~","join_ref":"~~"}}')

    def pollingMarket(self):
        """Poll market data and process candles"""
        ws = create_connection(self.pollHost, header=self.headers)
        ws.send(f'{{"action":"subscribe","rics":["{self.assetRic}"]}}')
        tempData = {}
        reset = False

        while True:
            try:
                self._process_market_data(ws, tempData, reset)
            except:
                # Reconnect on error
                ws = create_connection(self.pollHost, header=self.headers)
                ws.send(f'{{"action":"subscribe","rics":["{self.assetRic}"]}}')

    def sendWs(self, data):
        """Send WebSocket message with incremental reference"""
        self.wsApi.send(data.replace("~~", str(self.ref)))
        self.ref += 1
        self.lastSend = time.time()

    def run(self):
        """Main execution method"""
        currentBalance = self.getCurrentBalance()
        print(currentBalance)

client = Client()
client.run()