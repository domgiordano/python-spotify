import requests
from lambdas.common.constants import LOGGER

log = LOGGER.get_logger(__file__)

class TrackList:

    BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, term: str):
        self.term: str = term
        self.track_list: list = []
        self.track_uri_list: list = []
        self.track_id_list: list = []
        self.number_of_tracks: int = 0
    
    def __get_uri_list(self):
        return [track['uri'] for track in self.track_list if 'uri' in track]
    def __get_id_list(self):
        return [track['id'] for track in self.track_list if 'id' in track]
    
    async def set_top_tracks(self):
        try:
            self.track_list = await self.get_top_tracks()
            self.track_uri_list = self.__get_uri_list()
            self.track_id_list = self.__get_id_list()
            self.number_of_tracks = len(self.track_list)
        except Exception as err:
            log.error(f"Set User Top Tracks: {err}")
            raise Exception(f"Set User Top Tracks {self.term}: {err}")

    async def get_top_tracks(self):
        try:
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
            raise Exception(f"Get User Top Tracks {self.term}: {err}")