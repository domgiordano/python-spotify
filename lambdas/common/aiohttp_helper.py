import aiohttp

from lambdas.common.constants import LOGGER

log = LOGGER.get_logger(__file__)

async def fetch_json(session: aiohttp.ClientSession, url: str, headers: dict = None, params: dict = None):
    try:
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"Spotify API error {resp.status} at {url}: {text}")
            return await resp.json()
    except Exception as err:
        log.error(f"AIOHTTP Fetch JSON: {err}")
        raise Exception(f"AIOHTTP Fetch JSON: {err}") from err

async def post_json(session: aiohttp.ClientSession, url: str, headers: dict = None, data: dict = None):
    try:
        async with session.post(url, headers=headers, data=data) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"Spotify API error {resp.status} at {url}: {text}")
            return await resp.json()
    except Exception as err:
        log.error(f"AIOHTTP Post JSON: {err}")
        raise Exception(f"AIOHTTP Post JSON: {err}") from err