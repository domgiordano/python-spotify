import aiohttp
import asyncio
from lambdas.common.constants import LOGGER

log = LOGGER.get_logger(__file__)

async def fetch_json(session: aiohttp.ClientSession, url: str, headers: dict = None, params: dict = None):
    try:
        async with session.get(url, headers=headers, params=params) as resp:
            if resp.status == 429:
                retry_after = int(resp.headers.get('Retry-After', 1))
                log.warning(f"Rate limit reached for GET {url}. Retrying after {retry_after} seconds...")
                await asyncio.sleep(retry_after + 1)
                return await fetch_json(session, url, headers, params)

            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"Spotify API error {resp.status} at {url}: {text}")

            return await resp.json()
    except Exception as err:
        log.error(f"AIOHTTP Fetch JSON: {err}")
        raise Exception(f"AIOHTTP Fetch JSON: {err}") from err


async def post_json(session: aiohttp.ClientSession, url: str, headers: dict = None, json: dict = None):
    try:
        async with session.post(url, headers=headers, json=json) as resp:
            if resp.status == 429:
                retry_after = int(resp.headers.get('Retry-After', 1))
                log.warning(f"Rate limit reached for POST {url}. Retrying after {retry_after} seconds...")
                await asyncio.sleep(retry_after + 1)
                return await post_json(session, url, headers, json)

            if resp.status != 200 or resp.status != 201:
                text = await resp.text()
                raise Exception(f"Spotify API error {resp.status} at {url}: {text}")

            return await resp.json()
    except Exception as err:
        log.error(f"AIOHTTP Post JSON: {err}")
        raise Exception(f"AIOHTTP Post JSON: {err}") from err