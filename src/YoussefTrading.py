import logging, re, json, asyncio

from telethon import TelegramClient, events
from pathlib import Path

from BinaryOptionsToolsV2.tracing import start_logs
from PocketOptionAPI import PocketOptionAPI
from utils import waiting_time, getTelegramCredentials, safe_trade

ROOT_PATH = Path(__file__).parents[1]

# Set up logging
logging.basicConfig(
    format='[%(levelname)s %(asctime)s] %(name)s: %(message)s',
    level=logging.INFO
)

telegramCredentials = getTelegramCredentials()
api_id = telegramCredentials['id']
api_hash = telegramCredentials['hash']
session = 'Youseff'

start_logs(path=f"{ROOT_PATH}/logs/{session}/", level="INFO", terminal=False)  # If false then the logs will only be written to the log files

if api_id != '' and api_hash != '':
    with open(f'{ROOT_PATH}/assets/chats.json', 'r', encoding='utf-8') as f:
        chatsList = json.loads(f.read())

    client = TelegramClient(f'{session}-work', api_id, api_hash)
    pocketOption = PocketOptionAPI('real')

    # Handle for Youseff New Message
    @client.on(events.NewMessage(chats=chatsList[session]))
    async def handler(event):
        action = entry = asset = None
        channel = session
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
                logging.error(
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
                logging.error(
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
                logging.error(
                    f'message : {message}'
                    'No entry found'
                )
                return False

            # Set the retry to 0
            retry = 0
            amount = 1.0
            expiration = 5 * 60  # 5 minutes retry
            pocketOption.set_channel_data(channel, {
                'action': action,
                'asset': asset,
                'expiration': expiration,
                'amount': amount,
            })

            logging.info(pocketOption.get_channel_data(channel))

            # Check if the balance limit is reached
            # isBreakBalanceLimit = await pocketOption.isBreakingBalanceLimit()
            # if isBreakBalanceLimit:
            #     logging.info(f'Balance limit reached for {channel}')
            #     return False

            """
            Loop until retry is less than MAX_RETRY
            Trade in the loop
            Break if the trade is a win
            Double the amount set each loop
            If first loop, wait for time else iterate for the next loop
            """
            while retry <= pocketOption.MAX_RETRY:
                if retry > 0:
                    # For each loop, check if balance is breached
                    # isBreakBalanceLimit = await pocketOption.isBreakingBalanceLimit()
                    # if isBreakBalanceLimit:
                    #     logging.info(f'Balance limit reached for {channel}')
                    #     return False
                    pass

                # Wait for the entry time
                if retry > 0 or await waiting_time(entry, timezone_offset=timezone):
                    # Trade
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
                                    logging.error(
                                        f'Trade ID not found in opened trades for {channel} - Trade failed')
                                    return False
                            except Exception as e:
                                logging.error(f'Error during getting opened trades: {e}')
                                return False

                        logging.info(f'END INITIATE TRADE - {tradeID} - WAITING FOR THE RESPONSE')

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
                                    channel_data = pocketOption.get_channel_data(channel)
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
                        elif trade:
                            logging.warning(f'Trade {tradeID} failed ({trade}), retrying...')
                            retry += 1
                            amount *= 2
                            pocketOption.set_value(channel, 'retry', retry)
                            pocketOption.set_value(channel, 'amount', amount)
                    except Exception as e:
                        logging.error(f'Error during trade: {e}')
                        break
                else:
                    logging.warning('Entry time has already passed')
                    pocketOption.remove_channel_data(channel)
                    break

            # We remove when we have bigger value than the retry value
            if pocketOption.has_channel(channel):
                retry = pocketOption.get_value(channel, 'retry')

                if not retry is None and retry > pocketOption.MAX_RETRY:
                    pocketOption.remove_channel_data(channel)

    client.start()
    client.run_until_disconnected()
else:
    logging.error('Empty credentials')