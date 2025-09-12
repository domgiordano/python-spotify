import requests
import asyncio
import aiohttp
from datetime import datetime, timedelta
from lambdas.common.ssm_helpers import SPOTIFY_CLIENT_SECRET, SPOTIFY_CLIENT_ID
from lambdas.common.track_list import TrackList
from lambdas.common.artist_list import ArtistList
from lambdas.common.playlist import Playlist
from lambdas.common.constants import LOGGER

log = LOGGER.get_logger(__file__)

class Spotify:

    BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, user: dict, session: aiohttp.ClientSession = None):
        log.info(f"Initializing Spotify Client for User {user['email']}.")
        self.client_id: str= SPOTIFY_CLIENT_ID
        self.aiohttp_session = session
        self.client_secret: str = SPOTIFY_CLIENT_SECRET
        self.user_id: str = user['userId']
        self.email: str = user['email']
        self.refresh_token: str = user['refreshToken']
        self.access_token: str = None if self.aiohttp_session else self.get_access_token()
        self.headers: dict = {} if self.aiohttp_session else {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        # Wrapped
        self.top_tracks_short: TrackList = TrackList('short_term', self.headers, self.aiohttp_session)
        self.top_tracks_medium: TrackList = TrackList('medium_term', self.headers, self.aiohttp_session)
        self.top_tracks_long: TrackList = TrackList('long_term', self.headers, self.aiohttp_session)
        self.top_artists_short: ArtistList = ArtistList('short_term', self.headers, self.aiohttp_session)
        self.top_artists_medium: ArtistList = ArtistList('medium_term', self.headers, self.aiohttp_session)
        self.top_artists_long: ArtistList = ArtistList('long_term', self.headers, self.aiohttp_session)
        self.last_month, self.last_month_number, self.this_year = self.__get_last_month_data()
        self.monthly_spotify_playlist: Playlist = Playlist(
            self.user_id,
            f"Xomify {self.last_month}'{self.this_year}", 
            f"Your Top 25 songs for {self.last_month} - Created by xomify.com", 
            self.headers,
            self.aiohttp_session
        )
        self.first_half_of_year_spotify_playlist: Playlist = Playlist(
            self.user_id,
            f"Xomify First Half '{self.this_year}",
            f"Your Top 25 songs for the First 6 months of '{self.this_year} - Created by xomify.com",
            self.headers,
            self.aiohttp_session
        )
        self.full_year_spotify_playlist: Playlist = Playlist(
            self.user_id,
            f"Xomify 20{self.this_year}",
            f"Your Top 25 songs for 20{self.this_year} - Created by xomify.com",
            self.headers,
            self.aiohttp_session
        )
        # Release Radar
        self.release_radar_playlist: Playlist = Playlist(
            self.user_id,
            f"Xomify Weekly Release Radar",
            f"All your followed artists newest songs - Created by xomify.com",
            self.headers,
            self.aiohttp_session
        )
        self.followed_artists: ArtistList = ArtistList('Following', self.headers, self.aiohttp_session)
        self.release_radar_playlist.set_id(user.get('releaseRadarId', None))
        
    async def aiohttp_initialize(self):
        try:
            self.access_token = await self.aiohttp_get_access_token()
            self.headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
        except Exception as err:
            log.error(f"AIOHTTP Initialize Spotify Token: {err}")
            raise Exception(f"AIOHTTP Initialize Spotify Token: {err}") from err
    def get_access_token(self):
        try:
            log.info("Getting spotify access token..")
            url = "https://accounts.spotify.com/api/token"

            # Prepare the data for the token request
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }

            # Make the request to refresh the token
            response = requests.post(url, data=data)
            response_data = response.json()

            # Check for errors
            if response.status_code != 200:
                raise Exception(f"Error refreshing token: {response_data}")

            log.info("Successfully retrieved spotify access token!")
            return response_data['access_token']
        except Exception as err:
            log.error(f"Get Spotify Access Token: {err}")
            raise Exception(f"Get Spotify Access Token: {err}") from err
        
    async def aiohttp_get_access_token(self):
        try:
            log.info("Getting spotify access token..")
            url = "https://accounts.spotify.com/api/token"

            data = {
                'grant_type': 'refresh_token',
                'refresh_token': self.refresh_token,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
            }

            async with self.aiohttp_session.post(url, data=data) as response:
                response_data = await response.json()

                if response.status != 200:
                    raise Exception(f"Error refreshing token: {response_data}")

                log.info("Successfully retrieved spotify access token!")
                return response_data['access_token']
        except Exception as err:
            log.error(f"AIOHTTP Get Spotify Access Token: {err}")
            raise Exception(f"AIOHTTP Get Spotify Access Token: {err}") from err
        
    async def get_top_tracks(self):
        try:
            log.info(f"Getting Top tracks for User {self.email}...")
            tasks = [
                self.top_tracks_short.set_top_tracks(),
                self.top_tracks_medium.set_top_tracks(),
                self.top_tracks_long.set_top_tracks()
            ]
            await asyncio.gather(*tasks)
            log.info("Top Tracked Retrieved!")
        except Exception as err:
            log.error(f"Get Top Tracks: {err}")
            raise Exception(f"Get Top Tracks: {err}") from err
        
    async def get_top_artists(self):
        try:
            log.info(f"Getting Top Artists for User {self.email}...")
            tasks = [
                self.top_artists_short.set_top_artists(),
                self.top_artists_medium.set_top_artists(),
                self.top_artists_long.set_top_artists()
            ]
            await asyncio.gather(*tasks)
            log.info("Top Artists Retrieved!")
        except Exception as err:
            log.error(f"Get Top Tracks: {err}")
            raise Exception(f"Get Top Tracks: {err}") from err
        
    def get_top_tracks_ids_last_month(self):
        return {
            "short_term": self.top_tracks_short.track_id_list,
            "med_term": self.top_tracks_medium.track_id_list,
            "long_term": self.top_tracks_long.track_id_list
        }
    
    def get_top_artists_ids_last_month(self):
        return {
            "short_term": self.top_artists_short.artist_id_list,
            "med_term": self.top_artists_medium.artist_id_list,
            "long_term": self.top_artists_long.artist_id_list
        }
    
    def get_top_genres_last_month(self):
        return {
            "short_term": self.top_artists_short.top_genres,
            "med_term": self.top_artists_medium.top_genres,
            "long_term": self.top_artists_long.top_genres
        }
    
    def __get_last_month_data(self):
        try:
            # Get the current date
            current_date = datetime.now()

            # Calculate the first day of the current month
            first_of_current_month = current_date.replace(day=1)

            # Calculate the last day of the previous month
            last_day_of_previous_month = first_of_current_month - timedelta(days=1)

            # Get the month name of the previous month
            last_month_name = last_day_of_previous_month.strftime("%B")

            # Get Month Number of previous month
            last_month_number = last_day_of_previous_month.month

            # Get Current Year
            current_year = str(current_date.year)[2:]


            return last_month_name, last_month_number, current_year
        except Exception as err:
            log.error(f"Get Last Month Data: {err}")
            raise Exception(f"Get Last Month Data: {err}") from err