import requests
import base64
import traceback
import inspect
from datetime import datetime, timedelta, timezone
import time

from lambdas.common.ssm_helpers import SPOTIFY_CLIENT_SECRET, SPOTIFY_CLIENT_ID
from lambdas.common.constants import WRAPPED_TABLE_NAME, LOGO_BASE_64
from lambdas.common.dynamo_helpers import full_table_scan, update_table_item

BASE_URL = "https://api.spotify.com/v1"

def wrapped_chron_job(event):
    try:
        response = []
        wrapped_users = get_active_wrapped_users()
        for user in wrapped_users:

            access_token = get_access_token(user['refreshToken'])
            top_tracks = get_top_tracks(access_token)
            top_tracks_uri_list = [track['uri'] for track in top_tracks if 'uri' in track]
            playlist = create_playlist(user['userId'], access_token)
            add_playlist_songs(playlist['id'], top_tracks_uri_list, access_token)
            time.sleep(5)
            add_playlist_image(playlist['id'], access_token)

            # Update the User
            update_user_table_entry(user)

            response.append(user['email'])

        return response
    except Exception as err:
        print(traceback.print_exc())
        frame = inspect.currentframe()
        raise Exception(str(err), f'{__name__}.{frame.f_code.co_name}')


def get_active_wrapped_users():
     table_values = full_table_scan(WRAPPED_TABLE_NAME)
     table_values[:] = [item for item in table_values if item['active']]
     return table_values

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
        print(traceback.print_exc())
        frame = inspect.currentframe()
        raise Exception(str(err), f'{__name__}.{frame.f_code.co_name}')

def get_top_tracks(access_token):
    try:
        url = f"{BASE_URL}/me/top/tracks?limit=25&time_range=short_term"

        # Set up the headers
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        # Make the request
        response = requests.get(url, headers=headers)
        response_data = response.json()

        # Check for errors
        if response.status_code != 200:
            raise Exception(f"Error fetching top tracks: {response_data}")

        return response_data['items']  # Return the list of top tracks
    except Exception as err:
            print(traceback.print_exc())
            frame = inspect.currentframe()
            raise Exception(str(err), f'{__name__}.{frame.f_code.co_name}')

def create_playlist(user_id, access_token):
    try:
        url = f"{BASE_URL}/users/{user_id}/playlists"
        last_month = get_last_month_name()
        body = {
            "name": f"Xomify {last_month} Monthly Wrapped",
            "description": f"Your Top 25 songs for {last_month} - Created by xomify.com",
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

        return response.json()  # Return the response as a JSON object
    except Exception as err:
            print(traceback.print_exc())
            frame = inspect.currentframe()
            raise Exception(str(err), f'{__name__}.{frame.f_code.co_name}')

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
            print(traceback.print_exc())
            frame = inspect.currentframe()
            raise Exception(str(err), f'{__name__}.{frame.f_code.co_name}')

def add_playlist_image(playlist_id, access_token):
    try:

        # Prepare the API URL
        url = f'{BASE_URL}/playlists/{playlist_id}/images'

        body = LOGO_BASE_64.replace('\n', '')

        # Set the headers
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'image/jpeg',
        }

        # Make the PUT request
        response = requests.put(url, body, headers=headers)

        # Check the response
        if response.status_code != 202:
            raise Exception(f"Failed to upload image: {response.status_code} {response.text}")

    except Exception as err:
            print(traceback.print_exc())
            frame = inspect.currentframe()
            raise Exception(str(err), f'{__name__}.{frame.f_code.co_name}')


def update_user_table_entry(user):
    # TODO: Update Last months and this months songs/artists/genres for the page
    user['updatedAt'] = get_time_stamp()
    update_table_item(WRAPPED_TABLE_NAME, user)

def get_time_stamp():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')


def get_last_month_name():
    try:
        # Get the current date
        current_date = datetime.now()

        # Calculate the first day of the current month
        first_of_current_month = current_date.replace(day=1)

        # Calculate the last day of the previous month
        last_day_of_previous_month = first_of_current_month - timedelta(days=1)

        # Get the month name of the previous month
        last_month_name = last_day_of_previous_month.strftime("%B")

        return last_month_name
    except Exception as err:
            print(traceback.print_exc())
            frame = inspect.currentframe()
            raise Exception(str(err), f'{__name__}.{frame.f_code.co_name}')

