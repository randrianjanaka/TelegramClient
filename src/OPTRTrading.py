import logging, re, json, asyncio

from telethon import TelegramClient, events
from pathlib import Path

from BinaryOptionsToolsV2.tracing import start_logs
from PocketOptionAPI import PocketOptionAPI
from utils import getTelegramCredentials, safe_trade

ROOT_PATH = Path(__file__).parents[1]

# Set up logging
logging.basicConfig(
    format='[%(levelname)s %(asctime)s] %(name)s: %(message)s',
    level=logging.INFO
)

telegramCredentials = getTelegramCredentials()
api_id = telegramCredentials['id']
api_hash = telegramCredentials['hash']
session = 'OPTR'

start_logs(path=f"{ROOT_PATH}/logs/{session}/", level="INFO", terminal=False)  # If false then the logs will only be written to the log files

if api_id != '' and api_hash != '':
    with open(f'{ROOT_PATH}/assets/chats.json', 'r', encoding='utf-8') as f:
        chatsList = json.loads(f.read())

    client = TelegramClient(f'{session}-work', api_id, api_hash)
    pocketOption = PocketOptionAPI('real')


    # Handle for OTC Pro Trading Robot New Message
    @client.on(events.NewMessage(chats=chatsList[session]))
    async def handler(event):
        asset = expiration = action = None
        channel = session

        message = event.raw_text
        pattern = r'(Preparing trading asset|Summary:|Result:|Profit|Loss)'
        matchpattern = re.search(pattern, message, re.IGNORECASE)

        if matchpattern:
            matchpatterngroup = matchpattern.group(1)
            checkasset = checkexpiration = checkaction = True

            if 'Preparing trading asset' in matchpatterngroup:
                checkexpiration = checkaction = False
            elif 'Summary:' in matchpatterngroup:
                checkasset = False
            elif 'Profit' in matchpatterngroup or 'Loss' in matchpatterngroup:
                checkasset = checkexpiration = checkaction = False

            # Get the asset
            regexasset = r'([A-Z]{3})/.*([A-Z]{3})\s+OTC'
            matchasset = re.search(regexasset, message)

            if checkasset and matchasset:
                asset = f'{matchasset.group(1)}{matchasset.group(2)}_otc'
            elif checkasset:
                logging.error(
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
                logging.error(
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
                logging.error(
                    f'message : {message}'
                    'No action found'
                )
                return False

            # Check if the balance limit is reached
            # isBreakBalanceLimit = await pocketOption.isBreakingBalanceLimit()
            # if isBreakBalanceLimit:
            #     logging.info(f'Balance limit reached for {channel}')
            #     return False

            if 'Preparing trading asset' in matchpatterngroup:
                logging.info(f'Initialization asset : {asset}')

                if pocketOption.has_channel(channel):
                    pocketOption.remove_channel_data(channel)

                pocketOption.set_value(channel, 'asset', asset)
            elif 'Summary:' in matchpatterngroup:
                expiration = int(expiration) * 60
                pocketOption.set_value(channel, 'expiration', expiration)
                pocketOption.set_value(channel, 'action', action)
                pocketOption.set_value(channel, 'amount', 1.0)
                pocketOption.set_value(channel, 'retry', 0)

                logging.info(pocketOption.get_channel_data(channel))

                try:
                    logging.info('INITIATE TRADE')
                    tradeID = await safe_trade(pocketOption, channel)

                    if not tradeID:
                        try:
                            # WAIT FOR THE TRADE TO BE REGISTERED
                            await asyncio.sleep(5)

                            # GET ALL OPENED DEALS
                            opened_trades = await pocketOption.getOpenedDeals()

                            logging.info(f'Opened trades : {opened_trades}')

                            if not opened_trades:
                                # TODO: THINK IF WE NEED TO RE-INITIATE THE TRADE
                                logging.error(f'Empty opened trades for {channel}')
                                return False

                            # SEARCH FOR THE TRADE ID USING THE CHANNEL DATA
                            channel_data = pocketOption.get_channel_data(channel)
                            for trade in opened_trades:
                                if (
                                    trade.get('asset') == channel_data.get('asset')
                                    and trade.get('amount') == channel_data.get('amount')
                                ):
                                    tradeID = trade.get('id')
                                    logging.info(f'Trade ID found in opened trades: {tradeID}')
                                    break

                            if not tradeID:
                                logging.error(f'Trade ID not found in opened trades for {channel} - Trade failed')
                                return False
                        except Exception as e:
                            logging.error(f'Error during getting opened trades: {e}')
                            return False

                    pocketOption.set_value(channel, 'tradeID', tradeID)

                    logging.info(f'END INITIATE TRADE - {tradeID} / {pocketOption.get_channel_data(channel)} - WAITING FOR THE RESPONSE')

                except Exception as e:
                    logging.error(f'Error during trade: {e}')
                    pocketOption.remove_channel_data(channel)
                    return False
            elif 'Profit' in matchpatterngroup or 'Loss' in matchpatterngroup:
                # TODO CHECK THE STATUS OF OUR TRADE
                pass
            else:
                # ========================================== TO ACTIVATE WHEN FINDING HOW TO PROCEED WITH THE TIME DIFFERENCE PLACING BET
                logging.info('==================== SAFE OPTION ======================')
                tradeID = pocketOption.get_value(channel, 'tradeID')

                if not tradeID:
                    logging.warning(f'Failed getting tradeID directly - Checking in open / closed deals')

                    try:
                        # SEARCH FOR THE TRADE ID IN THE OPENED DEALS AND CLOSED DEALS
                        opened_trades = await pocketOption.getOpenedDeals()
                        closed_trades = await pocketOption.getClosedDeals()

                        # SEARCH FOR THE TRADE ID USING THE CHANNEL DATA
                        channel_data = pocketOption.get_channel_data(channel)

                        # VARIABLE TO CHECK IF THE TRADE ID IS FOUND
                        isFound = False

                        if not opened_trades and not closed_trades:
                            logging.error(f'Opened and closed trades not found for {channel}')
                            return False

                        for trade in opened_trades:
                            if (
                                trade.get('asset') == channel_data.get('asset')
                                and trade.get('amount') == channel_data.get('amount')
                            ):
                                tradeID = trade.get('id')
                                isFound = True
                                logging.info(f'Trade ID found in opened trades: {tradeID}')
                                break

                        if not isFound:
                            for trade in closed_trades:
                                if (
                                    trade.get('asset') == channel_data.get('asset')
                                    and trade.get('amount') == channel_data.get('amount')
                                ):
                                    tradeID = trade.get('id')
                                    isFound = True
                                    logging.info(f'Trade ID found in closed trades: {tradeID}')
                                    break

                        if not isFound:
                            logging.error(f'Trade ID not found in opened or closed trades for {channel} - Safe Trade failed')
                            return False

                    except Exception as e:
                        logging.error(f'Error during getting opened trades and closed trades: {e}')
                        return False

                try:
                    tradeData = await pocketOption.getTradeData(tradeID)

                    if not tradeData:
                        logging.warning(f'Failed getting data directly for {tradeID} - Trying to search inside closed trade')

                        try:
                            # WAIT FOR THE TRADE TO BE REGISTERED
                            await asyncio.sleep(5)

                            # GET ALL OPENED DEALS
                            closed_trades = await pocketOption.getClosedDeals()

                            logging.info(f'Closed trades : {closed_trades}')

                            if not closed_trades:
                                logging.error(f'Closed trades not found for {channel}')
                                return False

                            # SEARCH FOR THE TRADE ID USING THE CHANNEL DATA
                            for trade in closed_trades:
                                if (trade.get('id') == tradeID):
                                    tradeData = trade
                                    logging.info(f'Trade found in closed trades: {tradeData}')
                                    break

                            if not tradeData:
                                logging.error(
                                    f'Trade not found in closed trades for {channel} - Trade failed')
                                return False
                        except Exception as e:
                            logging.error(f'Error during getting closed trades: {e}')
                            return False

                    if 'result' in tradeData:
                        trade = tradeData['result']
                    else:
                        if tradeData['profit'] >= 0:
                            trade = 'win'
                        else:
                            trade = 'loss'

                    logging.info(f'GOT RESPONSE : {tradeData}')
                except Exception as e:
                    logging.error(f'Error during retrieving trade data: {e}')
                    return False

                if trade in ['win', 'draw']:
                    logging.info(f'Trade successful: {trade}')
                    pocketOption.remove_channel_data(channel)
                    return True
                else:
                    logging.warning(f'Trade {tradeID} failed ({trade}), retrying...')
                    retry = pocketOption.get_value(channel, 'retry') + 1
                    pocketOption.set_value(channel, 'retry', retry)

                    logging.info(f'RetryCount : {retry}')

                    if retry <= pocketOption.MAX_RETRY:
                        expiration = int(expiration) * 60
                        amount = pocketOption.get_value(channel, 'amount')
                        pocketOption.set_value(channel, 'amount', amount * 2)
                        pocketOption.set_value(channel, 'expiration', expiration)

                        await asyncio.sleep(1)

                        logging.info(f'Safe option {retry} : Init trade - {pocketOption.get_channel_data(channel)}')

                        if retry == pocketOption.MAX_RETRY:
                            tradeID = await safe_trade(pocketOption, channel)

                            if not tradeID:
                                try:
                                    # WAIT FOR THE TRADE TO BE REGISTERED
                                    await asyncio.sleep(5)

                                    # GET ALL OPENED DEALS
                                    opened_trades = await pocketOption.getOpenedDeals()

                                    logging.info(f'Opened trades : {opened_trades}')

                                    if not opened_trades:
                                        # TODO: THINK IF WE NEED TO RE-INITIATE THE TRADE
                                        logging.error(f'Empty opened trades for {channel}')
                                        return False

                                    # SEARCH FOR THE TRADE ID USING THE CHANNEL DATA
                                    channel_data = pocketOption.get_channel_data(channel)
                                    for trade in opened_trades:
                                        if (
                                                trade.get('asset') == channel_data.get('asset')
                                                and trade.get('amount') == channel_data.get('amount')
                                        ):
                                            tradeID = trade.get('id')
                                            logging.info(f'Trade ID found in opened trades: {tradeID}')
                                            break

                                    if not tradeID:
                                        logging.error(
                                            f'Trade ID not found in opened trades for {channel} - Safe Trade {retry} failed')
                                        return False
                                except Exception as e:
                                    logging.error(f'Error during getting opened trades: {e}')
                                    return False

                            logging.info(f'Safe option {retry} : End init trade - {pocketOption.get_channel_data(channel), tradeID}')

                            try:
                                tradeData = await pocketOption.getTradeData(tradeID)

                                if not tradeData:
                                    logging.warning(
                                        f'Failed getting data directly for {tradeID} - Trying to search inside closed trade')

                                    try:
                                        # WAIT FOR THE TRADE TO BE REGISTERED
                                        await asyncio.sleep(5)

                                        # GET ALL OPENED DEALS
                                        closed_trades = await pocketOption.getClosedDeals()

                                        logging.info(f'Closed trades : {closed_trades}')

                                        if not closed_trades:
                                            logging.error(f'Closed trades not found for {channel}')
                                            return False

                                        # SEARCH FOR THE TRADE ID USING THE CHANNEL DATA
                                        for trade in closed_trades:
                                            if (trade.get('id') == tradeID):
                                                tradeData = trade
                                                logging.info(f'Trade found in closed trades: {tradeData}')
                                                break

                                        if not tradeData:
                                            logging.error(
                                                f'Trade not found in closed trades for {channel} - Trade failed')
                                            return False
                                    except Exception as e:
                                        logging.error(f'Error during getting closed trades: {e}')
                                        return False

                                if 'result' in tradeData:
                                    trade = tradeData['result']
                                else:
                                    if tradeData['profit'] >= 0:
                                        trade = 'win'
                                    else:
                                        trade = 'loss'

                                logging.info(f'GOT RESPONSE : {tradeData}')
                            except Exception as e:
                                logging.error(f'Error during retrieving trade data : {e}')
                                return False

                            if trade in ['win', 'draw']:
                                logging.info(f'Trade successful: {trade}')
                            else:
                                logging.warning(f'Trade failed : {trade}')

                            pocketOption.remove_channel_data(channel)
                        else:
                            tradeID = await safe_trade(pocketOption, channel)

                            if not tradeID:
                                try:
                                    # WAIT FOR THE TRADE TO BE REGISTERED
                                    await asyncio.sleep(5)

                                    # GET ALL OPENED DEALS
                                    opened_trades = await pocketOption.getOpenedDeals()

                                    logging.info(f'Opened trades : {opened_trades}')

                                    if not opened_trades:
                                        # TODO: THINK IF WE NEED TO RE-INITIATE THE TRADE
                                        logging.error(f'Empty opened trades for {channel}')
                                        return False

                                    # SEARCH FOR THE TRADE ID USING THE CHANNEL DATA
                                    channel_data = pocketOption.get_channel_data(channel)
                                    for trade in opened_trades:
                                        if (
                                                trade.get('asset') == channel_data.get('asset')
                                                and trade.get('amount') == channel_data.get('amount')
                                        ):
                                            tradeID = trade.get('id')
                                            logging.info(f'Trade ID found in opened trades: {tradeID}')
                                            break

                                    if not tradeID:
                                        logging.error(
                                            f'Trade ID not found in opened trades for {channel} - Safe Trade {retry} failed')
                                        return False
                                except Exception as e:
                                    logging.error(f'Error during getting opened trades: {e}')
                                    return False

                            pocketOption.set_value(channel, 'tradeID', tradeID)

                            logging.info(
                                f'Safe option {retry} : End init trade - {pocketOption.get_channel_data(channel), tradeID}')

    client.start()
    client.run_until_disconnected()
else:
    logging.error('Empty credentials')