import requests
import time
from lambdas.common.constants import LOGGER

log = LOGGER.get_logger(__file__)

class Playlist:

    BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, user_id: str, name: str, description: str, headers: dict):
        log.info(f"Initializing Playlist '{name}' for user_id '{user_id}.")
        self.user_id = user_id
        self.name = name
        self.description = description
        self.headers = headers
        self.uri_list = None
        self.image = None
        self.playlist = None
        self.id = None

    async def build_playlist(self, uri_list: list, image: str):
        try:
            log.info(f"Building playlist: {self.name}")
            self.uri_list = uri_list
            self.image = image
            await self.create_playlist()
            time.sleep(2)
            await self.add_playlist_image()
            time.sleep(2)
            await self.add_playlist_songs()
            log.info(f"Playlist '{self.name}' Complete!")
        except Exception as err:
            log.error(f"Build Playlist: {err}")
            raise Exception(f"Build Playlist: {err}")
    async def update_playlist(self, uri_list: list):
        try:
            log.info(f"Updating playlist: {self.name}")
            self.uri_list = uri_list
            await self.delete_playlist_songs()
            time.sleep(1)
            await self.add_playlist_songs()
            log.info(f"Playlist '{self.name}' Complete!")
        except Exception as err:
            log.error(f"Update Playlist: {err}")
            raise Exception(f"Update Playlist: {err}")
        
    def set_id(self, id):
        self.id = id
    async def create_playlist(self):
        try:
            log.info("Creating playlist..")
            url = f"{self.BASE_URL}/users/{self.user_id}/playlists"
            body = {
                "name": self.name,
                "description": self.description,
                "public": True
            }

            response = requests.post(url, json=body, headers=self.headers)

            # Check for errors
            if response.status_code != 201:
                raise Exception(f"Error creating playlist: {response.json()}")

            self.playlist = response.json()
            self.id = self.playlist['id']
            log.info(f"Playlist Creation Complete. ID: {self.id}")
        except Exception as err:
            log.error(f"Create Playlist: {err}")
            raise Exception(f"Create Playlist: {err}")
    

    async def add_playlist_songs(self):
        try:

            # Define batch size
            batch_size = 100

            url = f"{self.BASE_URL}/playlists/{self.id}/tracks"
            # Iterate through track URIs in batches
            for i in range(0, len(self.uri_list), batch_size):
                batch_uris = self.uri_list[i:i + batch_size]

                body = {
                    "uris": batch_uris
                }

                response = requests.post(url, json=body, headers=self.headers)

                if response.status_code == 201:
                    log.info(f"Successfully added {len(batch_uris)} tracks.")
                else:
                    raise Exception(f"Error adding songs to playlist: {response.json()}")

            log.info("Tracks Added Successfully.")
        except Exception as err:
            log.error(f"Add Playlist Songs: {err}")
            raise Exception(f"Add Playlist Songs: {err}")


    async def add_playlist_image(self, retried: bool=False):
        try:
            log.info(f"Adding Image to Playlist {self.id}...")
            # Prepare the API URL
            url = f'{self.BASE_URL}/playlists/{self.id}/images'

            body = self.image.replace('\n', '')

            # Make the PUT request
            response = requests.put(url, body, headers=self.headers)

            # Check the response
            if response.status_code != 202:
                # Retry once
                if not retried:
                    log.error("First attempt failed. Retrying.")
                    self.add_playlist_image(True)
                else:
                    raise Exception(f"Failed to upload image: {response.status_code} {response.text}")
            
            log.info(f"Image added to Playlist. Name: {self.name} ID: {self.id}.")

        except Exception as err:
            log.error(f"Adding Playlist Image: {err}")
            raise Exception(f"Adding Playlist Image: {err}")
        
    async def delete_playlist_songs(self):
        try:

            # Fetch all track URIs in the playlist
            tracks_to_remove = []
            limit = 100
            offset = 0

            while True:
                url = f"{self.BASE_URL}/playlists/{self.id}/tracks?limit={limit}&offset={offset}"
                resp = requests.get(url, headers=self.headers).json()
                items = resp.get("items", [])
                if not items:
                    break
                tracks_to_remove.extend([{"uri": item["track"]["uri"]} for item in items])
                offset += len(items)

            # Step 2: Delete tracks in batches of 100
            for i in range(0, len(tracks_to_remove), 100):
                batch = tracks_to_remove[i:i+100]
                payload = {"tracks": batch}
                del_url = f"{self.BASE_URL}/playlists/{self.id}/tracks"
                resp = requests.delete(del_url, headers=self.headers, json=payload)
                if resp.status_code not in (200, 201):
                    log.info("Error deleting batch:", resp.status_code, resp.text)
                    return

            log.info("Tracks removed successfully.")
        except Exception as err:
            log.error(f"Delete Playlist Songs: {err}")
            raise Exception(f"Delete Playlist Songs: {err}")
    