import requests
from datetime import datetime, timezone
import time
import asyncio

from lambdas.common.wrapped_helper import get_active_wrapped_users
from lambdas.common.ssm_helpers import SPOTIFY_CLIENT_SECRET, SPOTIFY_CLIENT_ID
from lambdas.common.constants import WRAPPED_TABLE_NAME, BLACK_LOGO_BASE_64
from lambdas.common.dynamo_helpers import update_table_item

BASE_URL = "https://api.spotify.com/v1"

async def release_radar_chron_job(event):
    try:
        response = []
        wrapped_users = get_active_wrapped_users()
        for user in wrapped_users:

            access_token = get_access_token(user['refreshToken'])

            artist_ids = await get_followed_artists(access_token)
            print(f"Artist IDs found: {len(artist_ids)}")
            
            tasks = [get_artist_latest_release(id, access_token) for id in artist_ids]

            # Get all ids of latest releases for the week
            artist_latest_release_uris = await asyncio.gather(*tasks)
            print(f"Latest Release IDs: {artist_latest_release_uris}")
            print(len(artist_latest_release_uris))
            # Remove None values - split lists
            tracks_uris, albums_uris = __split_spotify_uris(artist_latest_release_uris)
            print(f"Latest Release Albums: {albums_uris}")
            print(len(albums_uris))
            print(f"Latest Release Tracks: {tracks_uris}")
            print(len(tracks_uris))

            # Get all tracks for new albums
            tasks = [get_album_tracks(uri, access_token) for uri in albums_uris]
            all_tracks_from_albums_uris = await asyncio.gather(*tasks)
            flattened_uris = [item for sublist in all_tracks_from_albums_uris for item in sublist]
            print(f"All Tracks from Albums: {flattened_uris}")
            print(len(flattened_uris))
            tracks_uris.extend(flattened_uris)
            # Remove Duplicates
            final_tracks_uris = list(set(tracks_uris))
            print(f"All Tracks total: {len(final_tracks_uris)}")

            playlist_id = user.get('releaseRadarId', None)
            if not playlist_id:
                print("No Playlist ID found yet.")
                playlist_id = create_release_radar_playlist(user['userId'], access_token)
                print(f"Playlist created with ID: {playlist_id}")
                time.sleep(3)
                add_playlist_image(playlist_id, access_token)
                print("Playlist Image added.")
                time.sleep(3)
                # Update the User
                update_user_table_entry(user, playlist_id)
                print("User Table updated with playlist id.")
            else:
                print(f"Playlist ID found: {playlist_id}")
                # Erase Playlist songs
                delete_playlist_songs(playlist_id, access_token)
                print("Playlist songs cleared.")

            add_playlist_songs(playlist_id, final_tracks_uris, access_token)
            print("Playlist songs added.")
            
            
            response.append(user['email'])

            print(f"---------- USER ADDED: {user['email']} ----------")

        return response
    except Exception as err:
        print(f"Release Radar Chron Job: {err}")
        raise Exception(f"Release Radar Chron Job: {err}")

def __split_spotify_uris(uris):
    tracks = [id for id in uris if id and id.startswith("spotify:track:")]
    albums = [id for id in uris if id and id.startswith("spotify:album:")]
    return tracks, albums

def get_access_token(refresh_token):
    try:
        url = "https://accounts.spotify.com/api/token"

        # Prepare the data for the token request
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': SPOTIFY_CLIENT_ID,
            'client_secret': SPOTIFY_CLIENT_SECRET,
        }

        # Make the request to refresh the token
        response = requests.post(url, data=data)
        response_data = response.json()

        # Check for errors
        if response.status_code != 200:
            raise Exception(f"Error refreshing token: {response_data}")

        return response_data['access_token']
    except Exception as err:
        print(f"Get Access Token: {err}")
        raise Exception(f"Get Access Token: {err}")

def __get_headers(access_token: str):
    return {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
async def get_album_tracks(album_uri: str, access_token: str):
    try:

        track_uris = []
        
        # Set up the headers
        headers = __get_headers(access_token)
        album_id = album_uri.split(":")[2]
        url = f"{BASE_URL}/albums/{album_id}/tracks"

        # Make the request
        response = requests.get(url, headers=headers)
        response_data = response.json()

        # Check for errors
        if response.status_code != 200:
            raise Exception(f"Error fetching Album tracks: {response_data}")
            
        track_uris = [track['uri'] for track in response_data['items']]
        
        return track_uris
    except Exception as err:
        print(f"Get Album Tracks: {err}")
        raise Exception(f"Get Album Tracks: {err}")
    
async def get_followed_artists(access_token):
    try:

        artist_ids = []
        
        # Set up the headers
        headers = __get_headers(access_token)
        url = f"{BASE_URL}/me/following?type=artist&limit=50"
        more_artists = True
        while(more_artists):
            
            # Make the request
            response = requests.get(url, headers=headers)
            response_data = response.json()

            # Check for errors
            if response.status_code != 200:
                raise Exception(f"Error fetching followed artists: {response_data}")
            
            ids = [artist['id'] for artist in response_data['artists']['items']]
            artist_ids.extend(ids)
            if not response_data['artists']['next']:
                more_artists = False
            else:
                url = response_data['artists']['next']
        
        return artist_ids
    except Exception as err:
        print(f"Get Followed Artists: {err}")
        raise Exception(f"Get Followed Artists: {err}")

async def get_artist_latest_release(artist_id, access_token):
    try:
        url = f"{BASE_URL}/artists/{artist_id}/albums?limit=1&offset=0"

        # Set up the headers
        headers = __get_headers(access_token)

        # Make the request
        response = requests.get(url, headers=headers)
        response_data = response.json()

        # Check for errors
        if response.status_code == 429:
            print("RATE LIMIT REACHED")
            time.sleep(response.headers['retry-after'] + 2)
            return await get_artist_latest_release(artist_id, access_token)
        if response.status_code != 200:
            raise Exception(f"Error fetching artist latest release: {response}")
        
        if __is_within_a_week(response_data['items'][0]['release_date']):
            return response_data['items'][0]['uri']
        else:
             return None

    except Exception as err:
        print(f"Get Artist Latest Release: {err}")
        raise Exception(f"Get Artist Latest Release: {err}")

def __is_within_a_week(target_date_str):
    try:
        today = datetime.today().date()
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()

        # Calculate the absolute difference in days
        difference_in_days = abs((today - target_date).days)
        print(difference_in_days <= 7)
        return difference_in_days <= 7
    except Exception as err:
        print(f"Is Date Within a week: {err}")
        raise Exception(f"Is Date Within a week: {err}")

def create_release_radar_playlist(user_id, access_token):
    try:
        url = f"{BASE_URL}/users/{user_id}/playlists"
        body = {
            "name": f"Xomify Weekly Release Radar",
            "description": f"All your followed artists newest songs - Created by xomify.com",
            "public": True
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=body, headers=headers)

        # Check for errors
        if response.status_code != 201:
            raise Exception(f"Error creating playlist: {response.json()}")

        return response.json()['id']  # Return the playlist id
    except Exception as err:
        print(f"Create Release Radar Playlist: {err}")
        raise Exception(f"Create Release Radar Playlist: {err}")
def delete_playlist_songs(playlist_id, access_token):
    try:
        headers = __get_headers(access_token)

        # Step 1: Fetch all track URIs in the playlist
        tracks_to_remove = []
        limit = 100
        offset = 0

        while True:
            url = f"{BASE_URL}/playlists/{playlist_id}/tracks?limit={limit}&offset={offset}"
            resp = requests.get(url, headers=headers).json()
            items = resp.get("items", [])
            if not items:
                break
            tracks_to_remove.extend([{"uri": item["track"]["uri"]} for item in items])
            offset += len(items)

        # Step 2: Delete tracks in batches of 100
        for i in range(0, len(tracks_to_remove), 100):
            batch = tracks_to_remove[i:i+100]
            payload = {"tracks": batch}
            del_url = f"{BASE_URL}/playlists/{playlist_id}/tracks"
            resp = requests.delete(del_url, headers=headers, json=payload)
            if resp.status_code not in (200, 201):
                print("Error deleting batch:", resp.status_code, resp.text)
                return

        print("Tracks removed successfully.")
    except Exception as err:
        print(f"Delete Playlist Songs: {err}")
        raise Exception(f"Delete Playlist Songs: {err}")
    
def add_playlist_songs(playlist_id, uri_list, access_token):
    try:

        # Define batch size
        batch_size = 100

        headers = __get_headers(access_token)
        url = f"{BASE_URL}/playlists/{playlist_id}/tracks"
        # Iterate through track URIs in batches
        for i in range(0, len(uri_list), batch_size):
            batch_uris = uri_list[i:i + batch_size]

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            body = {
                "uris": batch_uris
            }

            response = requests.post(url, json=body, headers=headers)

            if response.status_code == 201:
                print(f"Successfully added {len(batch_uris)} tracks.")
            else:
                raise Exception(f"Error adding songs to playlist: {response.json()}")

        print("Tracks Added Successfully.")
    except Exception as err:
        print(f"Add Playlist Songs: {err}")
        raise Exception(f"Add Playlist Songs: {err}")

def add_playlist_image(playlist_id, access_token, retried=False):
    try:

        # Prepare the API URL
        url = f'{BASE_URL}/playlists/{playlist_id}/images'

        body = BLACK_LOGO_BASE_64.replace('\n', '')

        # Set the headers
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'image/jpeg',
        }

        # Make the PUT request
        response = requests.put(url, body, headers=headers)

        # Check the response
        if response.status_code != 202:
            # Retry once
            if not retried:
                 add_playlist_image(playlist_id, access_token, True)
            else:
                raise Exception(f"Failed to upload image: {response.status_code} {response.text}")

    except Exception as err:
        print(f"Add Playlist Image: {err}")
        raise Exception(f"Add Playlist Image: {err}")

def update_user_table_entry(user, playlist_id):
    try:
        # Release Radar Id
        user['releaseRadarId'] = playlist_id
        # Time Stamp
        user['updatedAt'] = __get_time_stamp()
        update_table_item(WRAPPED_TABLE_NAME, user)
    except Exception as err:
        print(f"Update User Table Entry: {err}")
        raise Exception(f"Update User Table Entry: {err}")

def __get_time_stamp():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
