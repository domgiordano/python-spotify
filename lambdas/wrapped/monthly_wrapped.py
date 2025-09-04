
import traceback
import inspect
from datetime import datetime, timezone
import asyncio

from lambdas.common.wrapped_helper import get_active_wrapped_users
from lambdas.common.spotify import Spotify
from lambdas.common.constants import WRAPPED_TABLE_NAME, LOGO_BASE_64, BLACK_2025_BASE_64, LOGGER
from lambdas.common.dynamo_helpers import update_table_item

log = LOGGER.get_logger(__file__)

async def wrapped_chron_job(event):
    try:
        log.info("Starting Wrapped Chron Job...")
        response = []
        wrapped_users = get_active_wrapped_users()
        for user in wrapped_users:
            log.info(f"Found User: {user}")
            spotify = Spotify(user)

            await asyncio.run(spotify.get_top_tracks())
            await asyncio.run(spotify.get_top_artists())

            tasks = [
                spotify.monthly_spotify_playlist.build_playlist(spotify.top_tracks_short.track_uri_list, LOGO_BASE_64)
            ]
            if spotify.last_month_number == 6:
                tasks.append(spotify.first_half_of_year_spotify_playlist.build_playlist(spotify.top_tracks_medium, LOGO_BASE_64))

            if spotify.last_month_number == 12:
                tasks.append(spotify.full_year_spotify_playlist.build_playlist(spotify.top_tracks_long, BLACK_2025_BASE_64))

            await asyncio.gather(*tasks)

            # Create Dicts
            log.info("Getting last months top tracks, artists, and genres...")
            top_tracks_last_month = spotify.get_top_tracks_ids_last_month()
            top_artists_last_month = spotify.get_top_artists_ids_last_month
            top_genres_last_month = spotify.get_top_genres_last_month()

            # Update the User
            log.info("Updating User table with data...")
            __update_user_table_entry(user, top_tracks_last_month, top_artists_last_month, top_genres_last_month)

            response.append(spotify.email)

            log.info(f"---------- USER COMPLETE: {spotify.email} ----------")

        return response
    except Exception as err:
        log.error(traceback.log.info_exc())
        frame = inspect.currentframe()
        raise Exception(str(err), f'{__name__}.{frame.f_code.co_name}')

def __update_user_table_entry(user, top_tracks_last_month, top_artists_last_month, top_genres_last_month):
    # Tracks
    user['topSongIdsTwoMonthsAgo'] = user['topSongIdsLastMonth']
    user['topSongIdsLastMonth'] = top_tracks_last_month
    # Artists
    user['topArtistIdsTwoMonthsAgo'] = user['topArtistIdsLastMonth']
    user['topArtistIdsLastMonth'] = top_artists_last_month
    # Genres
    user['topGenresTwoMonthsAgo'] = user['topGenresLastMonth']
    user['topGenresLastMonth'] = top_genres_last_month
    # Time Stamp
    user['updatedAt'] = get_time_stamp()
    update_table_item(WRAPPED_TABLE_NAME, user)

def get_time_stamp():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


