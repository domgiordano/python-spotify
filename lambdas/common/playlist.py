import requests
import time

class Playlist:

    BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, user_id: str, name: str, description: str):
        self.user_id = user_id
        self.name = name
        self.description = description
        self.uri_list = None
        self.image = None
        self.playlist = None

    def build_playlist(self, uri_list: list, image: str):
        self.uri_list = uri_list
        self.image = image
        self.create_playlist()
        time.sleep(2)
        self.add_playlist_image()
        time.sleep(2)
        self.add_playlist_songs()

    async def create_playlist(self):
        try:
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

            return response.json()  # Return the response as a JSON object
        except Exception as err:
            print(f"Create Playlist: {err}")
            raise Exception(f"Create Playlist: {err}")
    

    async def add_playlist_songs(self):
        try:
            url = f"{self.BASE_URL}/playlists/{self.playlist['id']}/tracks"

            body = {
                "uris": self.uri_list
            }

            response = requests.post(url, json=body, headers=self.headers)

            # Check for errors
            if response.status_code != 201:
                raise Exception(f"Error adding songs to playlist: {response.json()}")

            return response.json()
        except Exception as err:
            print(f"Adding Playlist Songs: {err}")
            raise Exception(f"Adding Playlist Songs: {err}")


    async def add_playlist_image(self, retried: bool=False):
        try:

            # Prepare the API URL
            url = f'{self.BASE_URL}/playlists/{self.playlist['id']}/images'

            body = self.image.replace('\n', '')

            # Make the PUT request
            response = requests.put(url, body, headers=self.headers)

            # Check the response
            if response.status_code != 202:
                # Retry once
                if not retried:
                    self.add_playlist_image(True)
                else:
                    raise Exception(f"Failed to upload image: {response.status_code} {response.text}")

        except Exception as err:
            print(f"Adding Playlist Image: {err}")
            raise Exception(f"Adding Playlist Image: {err}")
    