import requests, json, uuid, time, logging, os
from pathlib import Path
from ConfigBinomo import Config
from WebSocketClientBinomo import WebSocketClient

class BinomoAPI:
    BASE_URL = 'https://api.binomo.com'
    BASE_URL_UA = 'https://api.apilayer.com/user_agent/generate?desktop=true&linux=true&windows=true&mac=true&chrome=true&firefox=true'
    ROOT_PATH = Path(__file__).parents[2]

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
        with open(f'{self.ROOT_PATH}/assets/assets.json', 'r') as f:
            self.assetList = json.loads(f.read())

        # Initialize asset information
        self.assetRIC = 'EURO'
        for asset in self.assetList:
            if asset['name'] == 'USD':
                self.assetID = asset['id']
                self.assetRIC = asset['ric']

        # Trading state variables
        self.lastSend = time.time()
        self.ref = 1

        # Initialize Config
        self.config = Config()

        # Connect to WebSocket
        self.apiHost = f"{self.config.API_HOST}?authtoken={self.token}&device=web&device_id={self.deviceID}&?v=2&vsn=2.0.0"
        if self.logger:
            self.logger.info('Connecting to Binomo API')

        self.ws = WebSocketClient(self.apiHost)
        self.ws.run()

        if self.logger:
            self.logger.info('Connected to Binomo API')

        # Initialize Phoenix channels
        self.phxJoin()

        if self.logger:
            self.logger.info('BOT STARTED...')

    async def connect(self):
        self.login()
        self.ws = WebSocketClient(self.apiHost)
        await self.ws.run()

    def login(self):
        """
        Log in to Binomo account using email and password.

        Args:
            email (str): User email
            password (str): User password

        Returns:
            dict: Response containing user information and token
        """
        with open(f'{self.ROOT_PATH}/assets/binomoCredentials.json', 'r') as f:
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
        with open(f'{self.ROOT_PATH}/assets/uaCredentials.json', 'r') as f:
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

    async def phxJoin(self):
        await self.sendWs('{"topic":"account","event":"phx_join","payload":{},"ref":"~~","join_ref":"~~"}')
        await self.sendWs('{"topic":"user","event":"phx_join","payload":{},"ref":"~~","join_ref":"~~"}')
        await self.sendWs('{"topic":"base","event":"phx_join","payload":{},"ref":"~~","join_ref":"~~"}')
        await self.sendWs('{"topic":"cfd_zero_spread","event":"phx_join","payload":{},"ref":"~~","join_ref":"~~"}')
        await self.sendWs('{"topic":"marathon","event":"phx_join","payload":{},"ref":"~~","join_ref":"~~"}')
        await self.sendWs(
            '{"topic":"asset:' + self.assetRIC + '","event":"phx_join","payload":{},"ref":"~~","join_ref":"~~"}')

        if self.logger:
            self.logger.info('Sent all the requests')

    async def sendWs(self,data):
        await self.ws.send(data.replace("~~",str(self.ref)))
        self.ref+=1
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

        # # Check if the websocket is connected
        # isConnected = await self.ws.isConnected()
        # if isConnected:
        #     await self.ws.send(json.dumps(payload))
        # else:
        #     await self.connect()
        #
        #     if isConnected:
        #         await self.Call(ric, duration, amount, is_demo=is_demo)
        #     else:
        #         if self.logger:
        #             self.logger.error('Reconnecting failed')
        await self.sendWs(json.dumps(payload))

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
