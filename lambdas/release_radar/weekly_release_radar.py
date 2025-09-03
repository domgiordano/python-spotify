import requests
import base64
import traceback
import inspect
from datetime import datetime, timezone
import time
import asyncio

from lambdas.common.ssm_helpers import SPOTIFY_CLIENT_SECRET, SPOTIFY_CLIENT_ID
from lambdas.common.constants import WRAPPED_TABLE_NAME, BLACK_LOGO_BASE_64
from lambdas.common.dynamo_helpers import full_table_scan, update_table_item

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
            artist_latest_release_ids = await asyncio.gather(*tasks)
            print(f"Latest Release IDs: {artist_latest_release_ids}")
            print(len(artist_latest_release_ids))
            # Remove None values
            filtered_release_ids = list(filter(None, artist_latest_release_ids))
            print(f"Filtered Release IDs Found: {filtered_release_ids}")
            print(len(filtered_release_ids))

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

            add_playlist_songs(playlist_id, filtered_release_ids, access_token)
            print("Playlist songs added.")
            
            
            response.append(user['email'])

            print(f"---------- USER ADDED: {user['email']} ----------")

        return response
    except Exception as err:
        print(f"Release Radar Chron Job: {err}")
        raise Exception(f"Release Radar Chron Job: {err}")


def get_active_wrapped_users():
     try:
        table_values = full_table_scan(WRAPPED_TABLE_NAME)
        table_values[:] = [item for item in table_values if item['active']]
        return table_values
     except Exception as err:
        print(f"Get Active Wrapped Users: {err}")
        raise Exception(f"Get Active Wrapped Users: {err}")

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

async def get_followed_artists(access_token):
    try:

        artist_ids = []
        
        # Set up the headers
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
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
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

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
        url = f"{BASE_URL}/playlists/{playlist_id}/tracks"

        body = {
            "uris": []
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=body, headers=headers)

        # Check for errors
        if response.status_code != 201:
            raise Exception(f"Error Deleting songs to playlist: {response.json()}")

    except Exception as err:
        print(f"Delete Playlist Songs: {err}")
        raise Exception(f"Delete Playlist Songs: {err}")
    
def add_playlist_songs(playlist_id, uri_list, access_token):
    try:
        url = f"{BASE_URL}/playlists/{playlist_id}/tracks"

        body = {
            "uris": uri_list
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, json=body, headers=headers)

        # Check for errors
        if response.status_code != 201:
            raise Exception(f"Error adding songs to playlist: {response.json()}")

        return response.json()
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
