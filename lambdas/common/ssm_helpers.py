import boto3
from lambdas.common.constants import PRODUCT

ssm = boto3.client("ssm", verify=False)

__AWS_ROOT = f'/{PRODUCT}/aws/'
__SPOTIFY_ROOT = f'/{PRODUCT}/spotify/'
__API_ROOT = f'/{PRODUCT}/api/'

# AWS
AWS_ACCESS_KEY = ssm.get_parameter(Name=f'{__AWS_ROOT}ACCESS_KEY', WithDecryption=True)['Parameter']['Value']
AWS_SECRET_KEY = ssm.get_parameter(Name=f'{__AWS_ROOT}SECRET_KEY', WithDecryption=True)['Parameter']['Value']

# SPOTIFY
SPOTIFY_CLIENT_ID = ssm.get_parameter(Name=f'{__SPOTIFY_ROOT}CLIENT_ID', WithDecryption=True)['Parameter']['Value']
SPOTIFY_CLIENT_SECRET = ssm.get_parameter(Name=f'{__SPOTIFY_ROOT}CLIENT_SECRET', WithDecryption=True)['Parameter']['Value']

#API
API_SECRET_KEY = ssm.get_parameter(Name=f'{__API_ROOT}API_SECRET_KEY', WithDecryption=True)['Parameter']['Value']
