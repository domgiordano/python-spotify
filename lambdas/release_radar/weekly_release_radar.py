import requests
from datetime import datetime, timezone
import asyncio

from lambdas.common.wrapped_helper import get_active_wrapped_users
from lambdas.common.spotify import Spotify
from lambdas.common.constants import WRAPPED_TABLE_NAME, BLACK_LOGO_BASE_64, LOGGER
from lambdas.common.dynamo_helpers import update_table_item


log = LOGGER.get_logger(__file__)

BASE_URL = "https://api.spotify.com/v1"

async def release_radar_chron_job(event):
    try:
        log.info("Starting Release Radar Chron Job...")
        response = []
        wrapped_users = get_active_wrapped_users()
        for user in wrapped_users:
            log.info(f"Found User: {user}")
            spotify = Spotify(user)

            await spotify.followed_artists.get_followed_artists()

            log.info(f"Followed Artist IDs found: {len(spotify.followed_artists.artist_id_list)}")
            
            await spotify.followed_artists.get_followed_artist_latest_release()

            if not spotify.release_radar_playlist.id:
                log.info("No Release Radar Playlist ID found yet.")
                
                await spotify.release_radar_playlist.build_playlist(spotify.followed_artists.artist_tracks.final_tracks_uris, BLACK_LOGO_BASE_64)
                # Update the User
                update_user_table_entry(user, spotify.release_radar_playlist.id)
                log.info(f"User Table updated with playlist id {spotify.release_radar_playlist.id}")
            else:
                log.info(f"Playlist ID found: {spotify.release_radar_playlist.id}")
                # Erase Playlist songs
                await spotify.release_radar_playlist.update_playlist(spotify.followed_artists.artist_tracks.final_tracks_uris)
            
            
            response.append(spotify.email)

            log.info(f"---------- USER COMPLETE: {spotify.email} ----------")

        return response
    except Exception as err:
        log.error(f"Release Radar Chron Job: {err}")
        raise Exception(f"Release Radar Chron Job: {err}")

def update_user_table_entry(user, playlist_id):
    try:
        # Release Radar Id
        user['releaseRadarId'] = playlist_id
        # Time Stamp
        user['updatedAt'] = __get_time_stamp()
        update_table_item(WRAPPED_TABLE_NAME, user)
    except Exception as err:
        log.error(f"Update User Table Entry: {err}")
        raise Exception(f"Update User Table Entry: {err}")

def __get_time_stamp():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
