import asyncio
import aiohttp
from datetime import datetime, timezone

from lambdas.common.wrapped_helper import get_active_wrapped_users
from lambdas.common.spotify import Spotify
from lambdas.common.constants import WRAPPED_TABLE_NAME, LOGO_BASE_64, BLACK_2025_BASE_64, LOGGER
from lambdas.common.dynamo_helpers import update_table_item

log = LOGGER.get_logger(__file__)

async def aiohttp_wrapped_chron_job(event):
    try:
        log.info("Starting Wrapped Chron Job...")
        wrapped_users = get_active_wrapped_users()

        async with aiohttp.ClientSession() as session:
            tasks = [aiohttp_process_wrapped_user(user, session) for user in wrapped_users]
            response = await asyncio.gather(*tasks, return_exceptions=True)

        log.info(f"Full Response Complete for Users: {response}")
        return response
    except Exception as err:
        log.error(f"AIOHTTP Wrapped Chron Job: {err}")
        raise Exception("AIOHTTP Wrapped Chron Job failed") from err


async def aiohttp_process_wrapped_user(user: dict, session: aiohttp.ClientSession):
    try:
        log.info(f"Found User: {user}")
        spotify = Spotify(user, session)

        # Fetch top tracks and artists concurrently
        await asyncio.gather(
            spotify.top_tracks_short.aiohttp_set_top_tracks(),
            spotify.top_tracks_medium.aiohttp_set_top_tracks(),
            spotify.top_tracks_long.aiohttp_set_top_tracks(),
            spotify.top_artists_short.aiohttp_set_top_artists(),
            spotify.top_artists_medium.aiohttp_set_top_artists(),
            spotify.top_artists_long.aiohttp_set_top_artists()
        )

        tasks = [
            spotify.monthly_spotify_playlist.aiohttp_build_playlist(
                spotify.top_tracks_short.track_uri_list, LOGO_BASE_64
            )
        ]

        if spotify.last_month_number == 6:
            tasks.append(
                spotify.first_half_of_year_spotify_playlist.aiohttp_build_playlist(
                    spotify.top_tracks_medium.track_uri_list, LOGO_BASE_64
                )
            )

        if spotify.last_month_number == 12:
            tasks.append(
                spotify.full_year_spotify_playlist.aiohttp_build_playlist(
                    spotify.top_tracks_long.track_uri_list, BLACK_2025_BASE_64
                )
            )

        await asyncio.gather(*tasks)

        # Create Dicts
        top_tracks_last_month = spotify.get_top_tracks_ids_last_month()
        top_artists_last_month = spotify.get_top_artists_ids_last_month()
        top_genres_last_month = spotify.get_top_genres_last_month()

        # Update User Table
        __update_user_table_entry(user, top_tracks_last_month, top_artists_last_month, top_genres_last_month)

        log.info(f"---------- USER COMPLETE: {spotify.email} ----------")
        return spotify.email
    except Exception as err:
        log.error(f"AIOHTTP Process Wrapped User: {err}")
        raise Exception("AIOHTTP Process Wrapped User failed") from err


def __update_user_table_entry(user, top_tracks_last_month, top_artists_last_month, top_genres_last_month):
    # Tracks
    user['topSongIdsTwoMonthsAgo'] = user.get('topSongIdsLastMonth', {})
    user['topSongIdsLastMonth'] = top_tracks_last_month
    # Artists
    user['topArtistIdsTwoMonthsAgo'] = user.get('topArtistIdsLastMonth', {})
    user['topArtistIdsLastMonth'] = top_artists_last_month
    # Genres
    user['topGenresTwoMonthsAgo'] = user.get('topGenresLastMonth', {})
    user['topGenresLastMonth'] = top_genres_last_month
    # Time Stamp
    user['updatedAt'] = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    update_table_item(WRAPPED_TABLE_NAME, user)
