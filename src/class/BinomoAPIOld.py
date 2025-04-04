import requests, json, uuid, time, copy, logging, threading
from ConfigBinomo import Config
from WebSocketClientBinomo import WebSocketClient

class BinomoAPIOld:
    BASE_URL = 'https://api.binomo.com'
    BASE_URL_UA = 'https://api.apilayer.com/user_agent/generate?desktop=true&linux=true&windows=true&mac=true&chrome=true&firefox=true'

    def __init__(self, AddLogging: bool = False):
        # Get User Agent
        self.userAgent = self.generateUA()

        # Initialize Session
        self.session = requests.Session()
        self.deviceID = self.generateDeviceID()
        self.session.headers.update({
            'User-Agent': self.userAgent,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Device-Id': self.deviceID,
            'Device-Type': 'web',
        })

        # Login credentials
        self.userID = None
        self.token = None
        self.email = None
        self.password = None

        # Setting logger
        self.logger = logging.getLogger(__name__) if AddLogging else None
        if AddLogging:
            logging.basicConfig(level=logging.DEBUG)
            self.logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
        else:
            self.logger = None

        # Log in when initialization
        self.login()

        # Load assets files
        with open('../../assets/assets.json', 'r') as f:
            self.assetList = json.loads(f.read())

        # Initialize asset information
        for asset in self.assetList:
            if asset['name'] == 'USD':
                self.assetID = asset['id']
                self.assetRIC = asset['ric']

        # Trading state variables
        self.lastSend = time.time()
        self.ref = 1
        self.stop = False
        self.assetRic_default = "EURO"

        # Initialize Config
        self.config = Config()

        self.apiHost = f"{self.config.API_HOST}?authtoken={self.token}&device=web&device_id={self.deviceID}&?v=2&vsn=2.0.0"

        # Connect to WebSocket
        if self.logger:
            self.logger.info('Connecting to Binomo API')
        self.ws = WebSocketClient(self.apiHost)
        self.ws.run()

        if self.logger:
            self.logger.info('Connected to Binomo API')

        # Start background threads
        self.startBackgroundThreads()

        # Initialize Phoenix channels
        self.phxJoin()

        if self.logger:
            self.logger.info('BOT STARTED...')

    def login(self):
        """
        Log in to Binomo account using email and password.

        Args:
            email (str): User email
            password (str): User password

        Returns:
            dict: Response containing user information and token
        """
        with open('../../assets/binomoCredentials.json', 'r') as f:
            jsonAccess = json.loads(f.read())
            self.email = jsonAccess['email']
            self.password = jsonAccess['password']

        payload = {
            'email': self.email,
            'password': self.password,
        }

        response = self.session.post(f'{self.BASE_URL}/passport/v2/sign_in?locale=en', json=payload)
        if response.status_code == 200:
            data = response.json()['data']
            self.userID = data['user_id']
            self.token = data['authtoken']

            # Add token in headers
            self.session.headers.update({
                'Authorization-Token': self.token,
            })
        else:
            print(f"Error logging in {response}")
            return None

    def getCurrentBalance(self, walletType='demo'):
        response = self.session.get(f'{self.BASE_URL}/bank/v1/read?locale=en')
        if response.status_code == 200:
            data = response.json()
            for account in data['data']:
                if account['account_type'] == walletType:
                    return account['amount'] / 100
        else:
            print(f"Error getting balance {response}")
            return None

    def generateUA(self):
        with open('../../assets/uaCredentials.json', 'r') as f:
            jsonAccess = json.loads(f.read())
            apilayer_key = jsonAccess['key']

        headers = {
            'apikey': apilayer_key
        }
        response = requests.get(self.BASE_URL_UA, headers=headers)
        if response.status_code == 200:
            return response.json()['ua']
        else:
            print("Error generating user agent")
            return None

    @staticmethod
    def generateDeviceID():
        """
        Generate a unique device ID.

        Returns:
            str: Unique device ID
        """
        return str(uuid.uuid4())

    def phxJoin(self):
        self.sendWs('{"topic":"account","event":"phx_join","payload":{},"ref":"~~","join_ref":"~~"}')
        self.sendWs('{"topic":"user","event":"phx_join","payload":{},"ref":"~~","join_ref":"~~"}')
        self.sendWs('{"topic":"base","event":"phx_join","payload":{},"ref":"~~","join_ref":"~~"}')
        self.sendWs('{"topic":"cfd_zero_spread","event":"phx_join","payload":{},"ref":"~~","join_ref":"~~"}')
        self.sendWs('{"topic":"marathon","event":"phx_join","payload":{},"ref":"~~","join_ref":"~~"}')
        self.sendWs('{"topic":"asset:'+self.assetRic_default+'","event":"phx_join","payload":{},"ref":"~~","join_ref":"~~"}')
        if self.logger:
            self.logger.info("Sent all the requests")

    def sendWs(self,data):
        """Send WebSocket message with incremental reference"""
        self.ws.send(data.replace("~~", str(self.ref)))
        self.ref += 1
        self.lastSend = time.time()

    async def Call(self, ric, duration, amount, is_demo=False):
        duration = int(time.time()) + duration * 1_000_000
        demo_str = None
        if is_demo:
            demo_str = "demo"
        elif not is_demo:
            demo_str = "real"
        payload = {
            "topic": "bo",
            "event": "create",
            "payload": {
                "created_at": int(time.time()),
                "ric": ric,
                "deal_type": demo_str,
                "expire_at": duration,
                "option_type": "turbo",
                "trend": "call",
                "tournament_id": None,
                "is_state": False,
                "amount": amount
            },
            "ref": self.ref+1,
            "join_ref": "9"
        }
        await self.ws.send(json.dumps(payload))

    async def Put(self, ric, duration, amount, is_demo=False):
        duration = int(time.time()) + duration * 1_000_000
        demo_str = None
        if is_demo:
            demo_str = "demo"
        elif not is_demo:
            demo_str = "real"
        payload = {
            "topic": "bo",
            "event": "create",
            "payload": {
                "created_at": int(time.time()),
                "ric": ric,
                "deal_type": demo_str,
                "expire_at": duration,
                "option_type": "turbo",
                "trend": "put",
                "tournament_id": None,
                "is_state": False,
                "amount": amount
            },
            "ref": self.ref+1,
            "join_ref": "9"
        }
        await self.ws.send(json.dumps(payload))

    def startBackgroundThreads(self):
        """
        Start background threads for polling market data and handling WebSocket messages.
        """
        threading.Thread(target=self.pollingMarket, daemon=True).start()
        threading.Thread(target=self.hook, daemon=True).start()

    def hook(self):
        """WebSocket message handler"""
        while True:
            print(self.ws.listen())
            data = json.loads(self.ws.recv())

            if data["event"] == "deal_created":
                if self.logger:
                    self.logger.info(f"[ CALLBACK OPERATION ] CREATED DEAL AMOUNT: {int(data['payload']['amount'] / 100)}")

            elif data["event"] == "asset_changed_v1":
                payment_rate = data["payload"]["trading_tools_settings"]["standard"]["payment_rate_standard"]
                if self.logger:
                    self.logger.info(f"[ CALLBACK OPERATION ] ASSET RATE CHANGED: {payment_rate}%")

                # Stop trading if rate is too low
                self.stop = payment_rate < 75

            else:
                print(data)

            # Send heartbeat every 35 seconds
            if time.time() - self.lastSend > 35:
                print("[ CALLBACK OPERATION ] PHOENIX HEARTBEAT")
                self.sendWs('{"topic":"phoenix","event":"heartbeat","payload":{},"ref":"~~"}')

    def pollingMarket(self):
        """Poll market data and process candles"""
        if self.logger:
            self.logger.info('Polling market data')

        ws = WebSocketClient(self.config.POLL_HOST)
        ws.run()
        ws.send(f'{{"action":"subscribe","rics":["{self.assetRIC}"]}}')
        tempData = {}
        reset = False

        while True:
            try:
                self.process_market_data(ws, tempData, reset)
            except:
                # Reconnect on error
                if self.logger:
                    self.logger.warning("Reconnecting to market data")

                ws = WebSocketClient(self.config.POLL_HOST)
                ws.run()
                ws.send(f'{{"action":"subscribe","rics":["{self.assetRIC}"]}}')

    def process_market_data(self, ws, tempData, reset):
        """Process market data and handle candle formation"""
        data = json.loads(ws.recv())
        if "assets" in data["data"][0]:
            timex = data["data"][0]["assets"][0]["created_at"].split(":")[-1].split(".")[0]
            rate = data["data"][0]["assets"][0]["rate"]
            if timex == "01":
                if reset:
                    if tempData["open"] > tempData["close"]:
                        tempData["stat"] = "put"
                    elif tempData["open"] < tempData["close"]:
                        tempData["stat"] = "call"
                    self.history.append(tempData)
                    print("[ CALLBACK OPERATION ] CANDLE: " + tempData["stat"].upper())
                    tempData = {}
                    reset = False
                if tempData == {}:
                    tempData["low"] = rate
                    tempData["high"] = rate
                    tempData["open"] = rate
                else:
                    tempData["low"] = min(rate, tempData["low"])
                    tempData["high"] = max(rate, tempData["high"])
            elif timex == "00" and tempData != {}:
                if reset == False: reset = True
                tempData["low"] = min(rate, tempData["low"])
                tempData["high"] = max(rate, tempData["high"])
                tempData["close"] = rate


binomoAPI = BinomoAPI(True)
print(binomoAPI.getCurrentBalance('demo'))