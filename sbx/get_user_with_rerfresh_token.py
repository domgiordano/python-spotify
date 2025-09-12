import requests

from priv_constants import CLIENT_SECRET, CLIENT_ID, DOM_REFRESH_TOKEN
def get_access_token(refresh_token: str):
    try:
        print("Getting spotify access token..")
        url = "https://accounts.spotify.com/api/token"

        # Prepare the data for the token request
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET
        }

        # Make the request to refresh the token
        response = requests.post(url, data=data)
        response_data = response.json()

        # Check for errors
        if response.status_code != 200:
            raise Exception(f"Error refreshing token: {response_data}")

        print("Successfully retrieved spotify access token!")
        return response_data['access_token']
    except Exception as err:
        print(f"Get Spotify Access Token: {err}")
        raise Exception(f"Get Spotify Access Token: {err}")
    
def get_user(access_token: str):
    try:
        print("Getting spotify user..")
        url = "https://api.spotify.com/v1/me"
        
        # Prepare the data for the token request
        headers = {
          "Authorization": f"Bearer {access_token}"
        }

        # Make the request to refresh the token
        response = requests.get(url, headers=headers)
        print(response)
        user = response.json()
        print(user)

        # Check for errors
        if response.status_code != 200:
            raise Exception(f"Error Getting User: {user}")

        print("Successfully retrieved user!")
        return user
    except Exception as err:
        print(f"Get Spotify User: {err}")
        raise Exception(f"Get Spotify User: {err}")
access_token = get_access_token(DOM_REFRESH_TOKEN)
print(access_token)
user = get_user(access_token)
print(user)