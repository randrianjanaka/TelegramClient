import pandas as pd
from BinaryOptionsTools import PocketOption
from BinaryOptionsTools import pocketoption
import time


# Load the session and connect to the PocketOption API
ssid = (r'42["auth",{"session":"24k4ea9r0a1qck71rfojrgnl8o","isDemo":1,"uid":96282099,"platform":3}]')

api = PocketOption(ssid, True)

api.connect()

"Oui" if api.check_connect() else 'Non'

# Get current balance
# print(f"GET BALANCE: {api.get_balance()}")

