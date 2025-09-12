import requests
import aiohttp
import time
from datetime import datetime
import asyncio
from lambdas.common.aiohttp_helper import fetch_json
from lambdas.common.constants import LOGGER

log = LOGGER.get_logger(__file__)

class TrackList:

    BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, term: str, headers: dict, session: aiohttp.ClientSession = None):
        log.info(f"Initializing Tracks for term: {term}")
        self.aiohttp_session = session
        self.term: str = term
        self.headers = headers
        self.track_list: list = []
        self.track_uri_list: list = []
        self.album_uri_list_uri_list: list = []
        self.final_tracks_uris: list = []
        self.track_id_list: list = []
        self.number_of_tracks: int = 0
    
    # ------------------------
    # Shared Methods
    # ------------------------
    def __get_uri_list(self):
        return [track['uri'] for track in self.track_list if 'uri' in track]
    def __get_id_list(self):
        return [track['id'] for track in self.track_list if 'id' in track]
    
    # ------------------------
    # Set Tracks
    # ------------------------
    async def set_top_tracks(self):
        try:
            log.info(f"Setting Top Tracks for term: {self.term}")
            self.track_list = await self.get_top_tracks()
            self.track_uri_list = self.__get_uri_list()
            self.track_id_list = self.__get_id_list()
            self.number_of_tracks = len(self.track_list)
            log.info(f"{self.number_of_tracks} Top Tracks Set successfully for term {self.term}!")
        except Exception as err:
            log.error(f"Set User Top Tracks: {err}")
            raise Exception(f"Set User Top Tracks {self.term}: {err}") from err
        
    async def aiohttp_set_top_tracks(self):
        try:
            log.info(f"Setting Top Tracks for term: {self.term}")
            self.track_list = await self.aiohttp_get_top_tracks()
            self.track_uri_list = self.__get_uri_list()
            self.track_id_list = self.__get_id_list()
            self.number_of_tracks = len(self.track_list)
            log.info(f"{self.number_of_tracks} Top Tracks Set successfully for term {self.term}!")
        except Exception as err:
            log.error(f"AIOHTTP Set User Top Tracks: {err}")
            raise Exception(f"AIOHTTP Set User Top Tracks {self.term}: {err}") from err

    # ------------------------
    # Get Tracks
    # ------------------------
    async def get_top_tracks(self):
        try:
            log.info(f"Getting top tracks for term {self.term}...")
            url = f"{self.BASE_URL}/me/top/tracks?limit=25&time_range={self.term}"

            # Make the request
            response = requests.get(url, headers=self.headers)
            response_data = response.json()

            # Check for errors
            if response.status_code != 200:
                raise Exception(f"Error fetching top tracks: {response_data}")

            return response_data['items']  # Return the list of top tracks
        except Exception as err:
            log.error(f"Get User Top Tracks: {err}")
            raise Exception(f"Get User Top Tracks {self.term}: {err}") from err
        
    async def aiohttp_get_top_tracks(self):
        try:
            log.info(f"Getting top tracks for term {self.term}...")
            url = f"{self.BASE_URL}/me/top/tracks"
            params = {"limit": 25, "time_range": self.term}

            data = await fetch_json(self.aiohttp_session, url, headers=self.headers, params=params)
            return data['items']
        except Exception as err:
            log.error(f"AIOHTTP Get User Top Tracks: {err}")
            raise Exception(f"AIOHTTP Get User Top Tracks {self.term}: {err}") from err
    
    # ------------------------
    # Get Latest Release
    # ------------------------
    async def get_artist_latest_release(self, artist_id_list: list):
        try:
            log.info("Getting artsist releases within the last week...")
            tasks = [self.get_latest_releases(id) for id in artist_id_list]
            # Get all ids of latest releases for the week
            artist_latest_release_uris = await asyncio.gather(*tasks)
            combined_artist_latest_release_uris = [item for sublist in artist_latest_release_uris for item in sublist]
            log.debug(f"Latest Release IDs: {combined_artist_latest_release_uris}")
            log.debug(len(combined_artist_latest_release_uris))
            # Remove None values - split lists
            self.track_uri_list, temp_album_uri_list = self.__split_spotify_uris(combined_artist_latest_release_uris)
            # Remove Duplicate Albums
            self.album_uri_list = list(set(temp_album_uri_list))
            log.debug(f"Latest Release Albums: {self.album_uri_list}")
            log.debug(len(self.album_uri_list))
            log.debug(f"Latest Release Tracks: {self.track_uri_list}")
            log.debug(len(self.track_uri_list))

            # Get all tracks for new albums
            all_tracks_from_albums_uris = await self.get_several_albums_tracks()
            log.debug(f"All Tracks from Albums: {all_tracks_from_albums_uris}")
            log.debug(len(all_tracks_from_albums_uris))
            self.track_uri_list.extend(all_tracks_from_albums_uris)
            # Remove Duplicates
            self.final_tracks_uris = list(set(self.track_uri_list))
            log.info(f"All Tracks total: {len(self.final_tracks_uris)}")
        except Exception as err:
            log.error(f"Get Artist Latest Release: {err}")
            raise Exception(f"Get Artist Latest Release: {err}") from err
    
    async def aiohttp_get_artist_latest_release(self, artist_id_list: list):
        try:
            log.info("Getting artist releases within the last week...")
            tasks = [self.aiohttp_get_latest_releases(artist_id) for artist_id in artist_id_list]
            artist_latest_release_uris = await asyncio.gather(*tasks, return_exceptions=True)

            combined = []
            for res in artist_latest_release_uris:
                if isinstance(res, Exception):
                    log.error(f"Error fetching artist release: {res}")
                    continue
                combined.extend(res)

            # Split into tracks vs albums
            self.track_uri_list, temp_album_uri_list = self.__split_spotify_uris(combined)
            # Dedup albums
            self.album_uri_list = list(set(temp_album_uri_list))

            all_tracks_from_albums_uris = await self.aiohttp_get_several_albums_tracks()
            self.track_uri_list.extend(all_tracks_from_albums_uris)
            self.final_tracks_uris = list(set(self.track_uri_list))
            log.info(f"All Tracks total: {len(self.final_tracks_uris)}")
        except Exception as err:
            log.error(f"AIOHTTP Get Artist Latest Release: {err}")
            raise Exception(f"AIOHTTP Get Artist Latest Release: {err}") from err
    
    async def get_latest_releases(self, artist_id: str, offset: int = 0):
        try:
            include_groups = "album,single,appears_on,compilation"
            url = f"{self.BASE_URL}/artists/{artist_id}/albums?&include_groups='{include_groups}'&limit=1&offset={offset}"

            # Make the request
            response = requests.get(url, headers=self.headers)
            response_data = response.json()

            # Check for errors
            if response.status_code == 429:
                log.warning("RATE LIMIT REACHED")
                time.sleep(response.headers['retry-after'] + 1)
                return await self.get_artist_latest_release(artist_id)
            if response.status_code != 200:
                raise Exception(f"Error fetching artist latest release: {response}")
            
            release_uris = []
            for release in response_data['items']:
                for artist in release['artists']:
                    log.debug(f"Artist: {artist['name']}")
                log.debug(f"Album: {release['name']}")
                log.debug(f"Release Date: {release['release_date']}")
                if self.__is_within_a_week(release['release_date']):
                    log.debug("New Release Added.")
                    release_uris.append(release['uri'])
                    release_uris.extend(self.get_latest_releases(artist_id, offset+1))
                else:
                    log.debug("Old Release Skipped.")
                
                print("\n")
            return release_uris

        except Exception as err:
            log.error(f"Get Latest Releases: {err}")
            raise Exception(f"Get Latest Releases: {err}") from err
    
    async def aiohttp_get_latest_releases(self, artist_id: str, offset: int = 0):
        try:
            include_groups = "album,single,appears_on,compilation"
            url = f"{self.BASE_URL}/artists/{artist_id}/albums"
            params = {"include_groups": include_groups, "limit": 1, "offset": offset}

            data = await fetch_json(self.aiohttp_session, url, headers=self.headers, params=params)

            release_uris = []
            for release in data['items']:
                log.debug(f"Album: {release['name']} | Release Date: {release['release_date']}")
                if self.__is_within_a_week(release['release_date']):
                    log.debug("New Release Added.")
                    release_uris.append(release['uri'])
                    # Recurse to fetch the next release
                    release_uris.extend(await self.aiohttp_get_latest_releases(artist_id, offset+1))
                else:
                    log.debug("Old Release Skipped.")
            return release_uris
        except Exception as err:
            log.error(f"AIOHTTP Get Latest Releases: {err}")
            raise Exception(f"AIOHTTP Get Latest Releases: {err}") from err
    
    # ------------------------
    # Get Tracks from Album
    # ------------------------
    async def get_album_tracks(self, album_uri: str):
        try:

            track_uris = []
            
            album_id = album_uri.split(":")[2]
            url = f"{self.BASE_URL}/albums/{album_id}/tracks"

            # Make the request
            response = requests.get(url, headers=self.headers)
            response_data = response.json()

            # Check for errors
            if response.status_code != 200:
                raise Exception(f"Error fetching Album tracks: {response_data}")
                
            track_uris = [track['uri'] for track in response_data['items']]
            
            return track_uris
        except Exception as err:
            log.error(f"Get Album Tracks: {err}")
            raise Exception(f"Get Album Tracks: {err}") from err
    
    async def aiohttp_get_album_tracks(self, album_uri: str):
        try:
            album_id = album_uri.split(":")[2]
            url = f"{self.BASE_URL}/albums/{album_id}/tracks"
            data = await fetch_json(self.aiohttp_session, url, headers=self.headers)
            return [track['uri'] for track in data['items']]
        except Exception as err:
            log.error(f"AIOHTTP Get Album Tracks: {err}")
            raise Exception(f"AIOHTTP Get Album Tracks: {err}") from err
        
    async def get_several_albums_tracks(self):
        try:
            # Extract album IDs from URIs
            album_ids = [uri.split(":")[2] for uri in self.album_uri_list]

            track_uris = []

            # Spotify only allows up to 20 album IDs at a time
            for i in range(0, len(album_ids), 20):
                batch_ids = album_ids[i:i+20]
                ids_param = ",".join(batch_ids)
                url = f"{self.BASE_URL}/albums?ids={ids_param}"

                # Make the request
                response = requests.get(url, headers=self.headers)
                response_data = response.json()

                # Check for errors
                if response.status_code != 200:
                    raise Exception(f"Error fetching albums: {response_data}")

                # Collect tracks from each album
                for album in response_data["albums"]:
                    # For singles, only add the single (sometimes have other songs in there)
                    if album['album_type'] == 'single':
                        track_uris.append(album["tracks"]["items"][0]['uri'])
                    else:
                        for track in album["tracks"]["items"]:
                            track_uris.append(track["uri"])

            return track_uris
        except Exception as err:
            log.error(f"Get Several Albums Tracks: {err}")
            raise Exception(f"Get Several Albums Tracks: {err}") from err
    
    async def aiohttp_get_several_albums_tracks(self):
        try:
            album_ids = [uri.split(":")[2] for uri in self.album_uri_list]
            track_uris = []

            for i in range(0, len(album_ids), 20):
                batch_ids = album_ids[i:i+20]
                ids_param = ",".join(batch_ids)
                url = f"{self.BASE_URL}/albums"
                params = {"ids": ids_param}

                data = await fetch_json(self.aiohttp_session, url, headers=self.headers, params=params)

                for album in data["albums"]:
                    if album['album_type'] == 'single':
                        track_uris.append(album["tracks"]["items"][0]['uri'])
                    else:
                        for track in album["tracks"]["items"]:
                            track_uris.append(track["uri"])

            return track_uris
        except Exception as err:
            log.error(f"AIOHTTP Get Several Albums Tracks: {err}")
            raise Exception(f"AIOHTTP Get Several Albums Tracks: {err}") from err

    # ------------------------
    # Helper Functions
    # ------------------------
    def __is_within_a_week(self, target_date_str: str):
        try:
            if len(target_date_str) < 8:
                return False
            today = datetime.today().date()
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()

            # Calculate the absolute difference in days
            difference_in_days = abs((today - target_date).days)
            log.debug(f"Release Within Last 7 days??: {difference_in_days < 7}")
            return difference_in_days < 7
        except Exception as err:
            log.error(f"Is Date Within a week: {err}")
            raise Exception(f"Is Date Within a week: {err}") from err
        
    def __split_spotify_uris(self, uris):
        tracks = [id for id in uris if id and id.startswith("spotify:track:")]
        albums = [id for id in uris if id and id.startswith("spotify:album:")]
        return tracks, albums