import asyncio
import aiohttp
from lambdas.common.wrapped_helper import get_active_release_radar_users
from lambdas.common.spotify import Spotify
from lambdas.common.constants import BLACK_LOGO_BASE_64, LOGGER
from lambdas.common.dynamo_helpers import update_user_table_release_radar_id

log = LOGGER.get_logger(__file__)

async def aiohttp_release_radar_chron_job(event):
    try:
        log.info("Starting Release Radar Chron Job...")
        release_radar_users = get_active_release_radar_users()

        async with aiohttp.ClientSession() as session:
            tasks = [aiohttp_process_user(user, session) for user in release_radar_users]
            response = await asyncio.gather(*tasks, return_exceptions=True)

        log.info(f"Full Response Complete for Users: {response}")
        return response
    except Exception as err:
        log.error(f"AIOHTTP Release Radar Chron Job: {err}")
        raise Exception(f"AIOHTTP Release Radar Chron Job: {err}") from err

async def aiohttp_process_user(user: dict, session: aiohttp.ClientSession):
    try:
        log.info(f"Found User: {user}")
        spotify = Spotify(user, session)

        await spotify.followed_artists.aiohttp_get_followed_artists()
        log.info(f"Followed Artist IDs found: {len(spotify.followed_artists.artist_id_list)}")

        await spotify.followed_artists.aiohttp_get_followed_artist_latest_release()

        if not spotify.release_radar_playlist.id:
            log.info("No Release Radar Playlist ID found yet.")
            await spotify.release_radar_playlist.aiohttp_build_playlist(
                spotify.followed_artists.artist_tracks.final_tracks_uris,
                BLACK_LOGO_BASE_64
            )
            update_user_table_release_radar_id(user, spotify.release_radar_playlist.id)
            log.info(f"User Table updated with playlist id {spotify.release_radar_playlist.id}")
        else:
            log.info(f"Playlist ID found: {spotify.release_radar_playlist.id}")
            await spotify.release_radar_playlist.aiohttp_update_playlist(
                spotify.followed_artists.artist_tracks.final_tracks_uris
            )

        log.info(f"---------- USER COMPLETE: {spotify.email} ----------")
        return spotify.email
    except Exception as err:
        log.error(f"AIOHTTP Process User: {err}")
        raise Exception(f"AIOHTTP Process User: {err}") from err
