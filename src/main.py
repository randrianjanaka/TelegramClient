import logging, re, json, asyncio, pytz

from telethon import TelegramClient, events
from datetime import datetime
from zoneinfo import ZoneInfo

from PocketOptionAPI import PocketOptionAPI

def get_wait_time(entry_time_str, timezone_offset=-4):
    """
    Convert entry time from UTC-3 or UTC-4 to local time and calculate seconds to wait

    Args:
        entry_time_str: Time string in format "HH:MM"
        timezone_offset: Timezone offset (-3 or -4)
    Returns:
        Seconds to wait, or None if the time has passed for today
    """
    if timezone_offset not in [-3, -4]:
        raise ValueError("Timezone offset must be -3 or -4")

    # Get current date
    now = datetime.now()
    today = now.date()

    # Parse entry time
    hour, minute = map(int, entry_time_str.split(':'))

    # Select correct timezone based on offset
    tz_map = {
        -4: 'America/New_York',  # UTC-4
        -3: 'America/Sao_Paulo'  # UTC-3
    }

    # Create datetime in source timezone
    tz_entry = pytz.timezone(tz_map[timezone_offset])
    entry_time = datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute))
    entry_time = tz_entry.localize(entry_time)

    # Get current time in local timezone
    now_local = datetime.now(tz=datetime.now().astimezone().tzinfo)

    # Convert entry time to local timezone
    local_entry = entry_time.astimezone()

    # Calculate wait time
    wait_seconds = (local_entry - now_local).total_seconds()

    # If time has passed today, return None
    if wait_seconds < 0:
        return None

    return wait_seconds

async def waiting_time(entry_time, timezone_offset=-4):
    try:
        wait_time = get_wait_time(entry_time, timezone_offset)
        if wait_time is None:
            print("Entry time has already passed")
            return False

        print(f"Waiting {wait_time} seconds...")
        await asyncio.sleep(wait_time - 4) # The time to let the API waiting

        return True
    except ValueError as e:
        print(f"Error: {e}")
        return False

# Set up logging
logging.basicConfig(
    format='[%(levelname) %(asctime)s] %(name)s: %(message)s',
    level=logging.WARNING
)

# Get access
with open('../assets/telegramCredentials.json', 'r', encoding='utf-8') as f:
    jsonAccess = json.loads(f.read())
    api_id = jsonAccess['id']
    api_hash = jsonAccess['hash']


if api_id != '' and api_hash != '':
    with open('../assets/chats.json', 'r', encoding='utf-8') as f:
        chatsList = json.loads(f.read())

    client = TelegramClient('anon', api_id, api_hash)
    pocketOption = PocketOptionAPI()

    # Handle for OTC Pro Trading Robot New Message
    @client.on(events.NewMessage(chats=chatsList['OPTR']))
    async def handler(event):
        asset = expiration = action = None
        channel = 'OTPR'

        message = event.raw_text
        pattern = r'(Preparing trading asset|Summary:|Result:)'
        matchpattern = re.search(pattern, message, re.IGNORECASE)

        if matchpattern:
            matchpatterngroup = matchpattern.group(1)
            checkasset = checkexpiration = checkaction = True

            if 'Preparing trading asset' in matchpatterngroup:
                checkexpiration = checkaction = False
            elif 'Summary:' in matchpatterngroup:
                checkasset = False

            # Get the asset
            regexasset = r'([A-Z]{3})/.*([A-Z]{3})\s+OTC'
            matchasset = re.search(regexasset, message)

            if checkasset and matchasset:
                asset = f'{matchasset.group(1)}{matchasset.group(2)}_otc'
            elif checkasset:
                print(
                    f'message : {message}'
                    'No assets found'
                )
                return False

            # Get the expiration time
            regexexpiration = r'Expiration time:\s+(\d)'
            matchexpiration = re.search(regexexpiration, message, re.IGNORECASE)

            if checkexpiration and matchexpiration:
                expiration = f'{matchexpiration.group(1)}'
            elif checkexpiration:
                print(
                    f'message : {message}'
                    'No expiration found'
                )
                return False

            # Get the action (SELL/BUY)
            regexaction = r'(BUY|SELL)'
            matchaction = re.search(regexaction, message, re.IGNORECASE)

            if checkaction and matchaction:
                action = f'{matchaction.group(1)}'
            elif checkaction:
                print(
                    f'message : {message}'
                    'No action found'
                )
                return False

            if 'Preparing trading asset' in matchpatterngroup:
                print(f'Initialization asset : {asset}')

                if pocketOption.has_channel(channel):
                    pocketOption.remove_channel_data(channel)

                pocketOption.set_value(channel, 'asset', asset)
            elif 'Summary:' in matchpatterngroup:
                pocketOption.set_value(channel, 'expiration', int(expiration) * 60)
                pocketOption.set_value(channel, 'action', action)
                pocketOption.set_value(channel, 'amount', 1.0)
                pocketOption.set_value(channel, 'retry', 0)

                print(f'Before trade: {pocketOption.get_channel_data(channel)}')

                await asyncio.sleep(5)
                trade = await pocketOption.trade(channel, check_win=False)

                pocketOption.set_value(channel, 'tradeID', trade)

                print(f'After trade: {pocketOption.get_channel_data(channel)}')
            else:
                tradeID = pocketOption.get_value(channel, 'tradeID')
                # TODO: CHECK IF THE ID EXIST
                # ELSEWHERE WE ARE GOING TO CHECK OPEN DEALS AND CLOSED DEALS
                # IF NEEDED CHECK THE LAST LAUNCH TIME TOO
                data = await pocketOption.getTradeData(tradeID)
                result = data['result']

                print(f'Results last launch : {result, tradeID}')

                if result in ['win', 'draw']:
                    pocketOption.remove_channel_data(channel)
                else:
                    print(f'Retrying...')
                    retry = pocketOption.get_value(channel, 'retry') + 1
                    pocketOption.set_value(channel, 'retry', retry)

                    print(f'RetryCount : {retry}')

                    if retry <= pocketOption.MAX_RETRY:
                        pocketOption.set_value(channel, 'amount', amount * 2)
                        pocketOption.set_value(channel, 'expiration', int(expiration) * 60)

                        print(f'Before trade: {pocketOption.get_channel_data(channel)}')

                        await asyncio.sleep(1)
                        if retry == pocketOption.MAX_RETRY:
                            trade = await pocketOption.trade(channel)

                            print(f'After last trade: {pocketOption.get_channel_data(channel), trade}')

                            pocketOption.remove_channel_data(channel)
                        else:
                            trade = await pocketOption.trade(channel, check_win=False)
                            pocketOption.set_value(channel, 'tradeID', trade)

                            print(f'After trade: {pocketOption.get_channel_data(channel)}')


    # Handle for Notorious Silva Signals 🥇
    # @client.on(events.NewMessage(chats=chatsList['NSilva']))
    # async def handler(event):
    #     action = entry = None
    #     channel = 'NSilva'
    #
    #     message = event.raw_text
    #     pattern = r'Martingale levels'
    #     matchpattern = re.search(pattern, message, re.IGNORECASE)
    #
    #     if matchpattern:
    #         # Get the action (CALL/PUT)
    #         regexaction = r'(CALL|PUT)'
    #         matchaction = re.search(regexaction, message, re.IGNORECASE)
    #
    #         if matchaction:
    #             action = f'{matchaction.group(1)}'
    #         else:
    #             print(
    #                 f'message : {message}'
    #                 'No action found'
    #             )
    #             return False
    #
    #         # Get the entry point (H:M)
    #         regexentry = r'(\d{1,2}:\d{2})'
    #         matchentry = re.search(regexentry, message)
    #
    #         if matchentry:
    #             entry = f'{matchentry.group(1)}'
    #         else:
    #             print(
    #                 f'message : {message}'
    #                 'No entry found'
    #             )
    #             return False

    # Handle for Youseff New Message
    @client.on(events.NewMessage(chats=chatsList['Youseff']))
    async def handler(event):
        action = entry = asset = None
        channel = 'Youseff'
        timezone = -4

        message = event.raw_text
        pattern = r'Martingale levels'
        matchpattern = re.search(pattern, message, re.IGNORECASE)

        if matchpattern:
            # Get the action (BUY/SELL)
            regexaction = r'(BUY|SELL)'
            matchaction = re.search(regexaction, message, re.IGNORECASE)

            if matchaction:
                action = f'{matchaction.group(1)}'
            else:
                print(
                    f'message : {message}'
                    'No action found'
                )
                return False

            # Get the asset
            regexasset = r'([A-Z]{3})\/.*([A-Z]{3}).*OTC'
            matchasset = re.search(regexasset, message)

            if matchasset:
                asset = f'{matchasset.group(1)}{matchasset.group(2)}_otc'
            else:
                print(
                    f'message : {message}'
                    'No assets found'
                )
                return False

            # Get the entry point (H:M)
            regexentry = r'(\d{1,2}:\d{2})'
            matchentry = re.search(regexentry, message)

            if matchentry:
                entry = f'{matchentry.group(1)}'
            else:
                print(
                    f'message : {message}'
                    'No entry found'
                )
                return False

            # Set the retry to 0
            retry = 0
            amount = 1.0
            pocketOption.set_channel_data(channel, {
                'action': action,
                'asset': asset,
                'expiration': 5 * 60,  # 5 minutes retry
                'amount': amount,
            })

            print(pocketOption.get_channel_data(channel))

            """
            Loop until retry is less than MAX_RETRY
            Trade in the loop
            Break if the trade is a win
            Double the amount set each loop
            If first loop, wait for time else iterate for the next loop
            """
            while retry <= pocketOption.MAX_RETRY:
                # Wait for the entry time
                if retry > 0 or await waiting_time(entry, timezone_offset=timezone):
                    # Trade
                    trade = await pocketOption.trade(channel)
                    if trade:
                        print(f'Trade successful: {trade}')
                        pocketOption.remove_channel_data(channel)
                        break
                    else:
                        print('Trade failed, retrying...')
                        retry += 1
                        amount *= 2
                        pocketOption.set_value(channel, 'retry', retry)
                        pocketOption.set_value(channel, 'amount', amount)
                else:
                    print('Entry time has already passed')
                    pocketOption.remove_channel_data(channel)
                    break

            # We remove when we have bigger value than the retry value
            if pocketOption.has_channel(channel) and pocketOption.get_value(channel, 'retry') > pocketOption.MAX_RETRY:
                pocketOption.remove_channel_data(channel)

    # Handle generally for TEST : TO DELETE
    # @client.on(events.NewMessage)
    # async def handler(event):
    #     message = event.raw_text
    #     regex = r'(?:Preparing trading asset|Summary:|Result:)'
    #     print(
    #         'New message General',
    #         f'message: {message}',
    #         re.search(regex, message, re.IGNORECASE)
    #     )


    async def main():
        pass

    client.start()
    client.run_until_disconnected()
else:
    print('Empty credentials')
