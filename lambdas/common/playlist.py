import requests
import time
from lambdas.common.constants import LOGGER

log = LOGGER.get_logger(__file__)

class Playlist:

    BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, user_id: str, name: str, description: str):
        log.info(f"Initializing Playlist '{name}' for user_id '{user_id}.")
        self.user_id = user_id
        self.name = name
        self.description = description
        self.uri_list = None
        self.image = None
        self.playlist = None

    def build_playlist(self, uri_list: list, image: str):
        log.info(f"Building playlist: {self.name}")
        self.uri_list = uri_list
        self.image = image
        self.create_playlist()
        time.sleep(2)
        self.add_playlist_image()
        time.sleep(2)
        self.add_playlist_songs()
        log.info(f"Playlist '{self.name}' Complete!")

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
            log.info(f"Playlist Creation Complete. ID: {self.playlist['id']}")
        except Exception as err:
            log.error(f"Create Playlist: {err}")
            raise Exception(f"Create Playlist: {err}")
    

    async def add_playlist_songs(self):
        try:
            log.info(f"Adding Songs to Playlist {self.playlist['id']}...")
            url = f"{self.BASE_URL}/playlists/{self.playlist['id']}/tracks"

            body = {
                "uris": self.uri_list
            }

            response = requests.post(url, json=body, headers=self.headers)

            # Check for errors
            if response.status_code != 201:
                raise Exception(f"Error adding songs to playlist: {response.json()}")

            log.info(f"Songs added to Playlist. Name: {self.name} ID: {self.playlist['id']}.")
        except Exception as err:
            log.error(f"Adding Playlist Songs: {err}")
            raise Exception(f"Adding Playlist Songs: {err}")


    async def add_playlist_image(self, retried: bool=False):
        try:
            log.info(f"Adding Image to Playlist {self.playlist['id']}...")
            # Prepare the API URL
            url = f'{self.BASE_URL}/playlists/{self.playlist['id']}/images'

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
            
            log.info(f"Image added to Playlist. Name: {self.name} ID: {self.playlist['id']}.")

        except Exception as err:
            log.error(f"Adding Playlist Image: {err}")
            raise Exception(f"Adding Playlist Image: {err}")
    