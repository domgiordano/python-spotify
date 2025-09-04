import requests
from lambdas.common.constants import LOGGER

log = LOGGER.get_logger(__file__)

class ArtistList:

    BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, term: str):
        log.info(f"Initializing Artist for term: {term}")
        self.term: str = term
        self.artist_list: list = []
        self.artist_uri_list: list = []
        self.artist_id_list: list = []
        self.number_of_artists: int = 0
        self.top_genres: list = None
    
    def __get_uri_list(self):
        return [artist['uri'] for artist in self.artist_list if 'uri' in artist]
    def __get_id_list(self):
        return [artist['id'] for artist in self.artist_list if 'id' in artist]
    
    async def set_top_artists(self):
        try:
            log.info(f"Setting Top Artists for term: {self.term}")
            self.artist_list = await self.get_top_artists()
            self.artist_uri_list = self.__get_uri_list()
            self.artist_id_list = self.__get_id_list()
            self.get_top_genres()
            self.number_of_artists = len(self.artist_list)
            log.info("Top Artists Set successfully!")
        except Exception as err:
            log.error(f"Set User Top Artists: {err}")
            raise Exception(f"Set User Top Artists {self.term}: {err}")
        
    async def get_top_artists(self):
        try:
            url = f"{self.BASE_URL}/me/top/artists?limit=25&time_range={self.term}"

            # Make the request
            response = requests.get(url, headers=self.headers)
            response_data = response.json()

            # Check for errors
            if response.status_code != 200:
                raise Exception(f"Error fetching top artists for term: {self.term}")

            return response_data['items']  # Return the list of top artists
        except Exception as err:
            log.error(f"Get User Top Artists: {err}")
            raise Exception(f"Get User Top Artists {self.term}: {err}")
    
    def get_top_genres(self):
        try:
            log.info(f"Getting top Genres for term {self.term}...")
            # Collect all genres from the list of artists
            genres = []
            for artist in self.artist_list:
                genres.extend(artist.get('genres', []))  # Use .get to avoid errors if 'genres' key is missing

            # Count the occurrences of each genre
            top_genres = {}
            for genre in genres:
                top_genres[genre] = top_genres.get(genre, 0) + 1
            self.top_genres = top_genres
            log.info("Top Genres Retrieved successfully!")
        except Exception as err:
            log.error(f"Get Top Genres: {err}")
            raise Exception(f"Get Top Genres: {err}")