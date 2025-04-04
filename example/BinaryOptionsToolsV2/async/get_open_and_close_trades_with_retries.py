# from BinaryOptionsToolsV2.pocketoption import PocketOptionAsync
from PocketOptionAPI import PocketOptionAPI
import asyncio
import logging

async def main():
    api = PocketOptionAPI('real')

    try:
        opened_deals = await api.getOpenedDeals()
        print(f"Opened deals: {opened_deals}\n")

        closed_deals = await api.getClosedDeals()
        print(f"Closed deals: {closed_deals}\n")

        tradeData = await api.getTradeData('3948424b-1458-4707-a152-6ba1344f9dff')
        print(f"Trade data: {tradeData}\n")

    except Exception as e:
        logging.error(f"Erreur finale : {str(e)}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

# async def execute_with_retry(func, *args, **kwargs):
#     max_retries = 3
#     delay_seconds = 5
#
#     for attempt in range(max_retries):
#         try:
#             logging.info(f'Tentative {attempt + 1}/{max_retries}')
#
#             result = await func(*args, **kwargs)
#
#             if result == []:
#                 logging.warning('Aucun résultat trouvé, nouvelle tentative...')
#                 await asyncio.sleep(delay_seconds)
#                 continue
#
#             return result
#         except Exception as e:
#             if attempt < max_retries - 1:
#                 logging.warning(f'Échec de la tentative {attempt + 1}: {str(e)}')
#                 logging.info(f'Nouvelle tentative dans {delay_seconds} secondes')
#                 await asyncio.sleep(delay_seconds)
#             else:
#                 logging.error(f'Échec après {max_retries} tentatives: {str(e)}')
#                 raise
#
#
# async def main(ssid: str):
#     api = PocketOptionAsync(ssid)
#
#     try:
#         opened_deals = await execute_with_retry(api.opened_deals)
#         print(f"Opened deals: {opened_deals}\n")
#
#         closed_deals = await execute_with_retry(api.closed_deals)
#         print(f"Closed deals: {closed_deals}\n")
#
#     except Exception as e:
#         logging.error(f"Erreur finale : {str(e)}")
#
#
# if __name__ == '__main__':
#     logging.basicConfig(level=logging.INFO)
#     ssid = input('Please enter your ssid: ')
#     asyncio.run(main(ssid))