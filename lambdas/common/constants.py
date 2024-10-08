import os
from lambdas.common.secrets_manager_helpers import get_secret

# General
AWS_DEFAULT_REGION ='us-east-1'
AWS_ACCOUNT_ID = os.environ['AWS_ACCOUNT_ID']
PRODUCT = 'xomify'

# Headers
RESPONSE_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Content-Type": "application/json"
}

# Dynamodb
DYNAMODB_KMS_ALIAS = os.environ['DYNAMODB_KMS_ALIAS']
WRAPPED_TABLE_NAME = os.environ['WRAPPED_TABLE_NAME']

# Secrets Manager
API_SECRET_KEY = get_secret('api_secret_key')
