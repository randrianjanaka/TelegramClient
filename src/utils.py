import json, asyncio, logging
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

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

    # Parse entry time
    hour, minute = map(int, entry_time_str.split(':'))

    # Select correct timezone based on offset
    tz_map = {
        -4: 'America/New_York',  # UTC-4
        -3: 'America/Sao_Paulo'  # UTC-3
    }

    # Get source timezone
    source_tz = ZoneInfo(tz_map[timezone_offset])

    # Get current time in source timezone
    now = datetime.now(source_tz)

    # Create target time for today
    target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # If target time is in the past, return None
    if target_time < now:
        return None

    # Calculate wait time in seconds
    wait_seconds = (target_time - now).total_seconds()
    return wait_seconds

async def waiting_time(entry_time, timezone_offset=-4):
    try:
        wait_time = get_wait_time(entry_time, timezone_offset)
        if wait_time is None:
            logging.warning("Entry time has already passed")
            return False

        logging.info(f"Waiting {wait_time} seconds...")
        # await asyncio.sleep(wait_time - 4) # The time to let the API waiting
        await asyncio.sleep(wait_time - 8) # The time to let the API waiting

        return True
    except ValueError as e:
        logging.error(f"Error: {e}")
        return False

def getTelegramCredentials():
    ROOT_PATH = Path(__file__).parents[1]
    with open(f'{ROOT_PATH}/assets/telegramCredentials.json', 'r', encoding='utf-8') as f:
        return json.loads(f.read())

async def safe_trade(pocket_option, channel, check_win = False):
    try:
        return await pocket_option.trade(channel, check_win)
        # return await asyncio.wait_for(
        #     pocket_option.trade(channel, check_win),
        #     timeout=120
        # )
    # except asyncio.TimeoutError:
    #     logging.error("Trade operation timed out")
    #     return False
    except Exception as e:
        logging.error(f"Trade error: {e}")
        return False
