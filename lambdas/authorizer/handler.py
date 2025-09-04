

import jwt
from lambdas.common.constants import AWS_ACCOUNT_ID, LOGGER
from lambdas.common.ssm_helpers import API_SECRET_KEY
from lambdas.common.utility_helpers import build_error_handler_response
from lambdas.common.errors import LambdaAuthorizerError

log = LOGGER.get_logger(__file__)

HANDLER = 'authorizer'

def generate_policy(effect, method_arn):
    #Return a valid AWS policy response
    #auth_response = {'principalId': principal_id}
    auth_response = {}
    if effect and method_arn:
        policy_document = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Action': 'execute-api:*',
                    'Effect': effect,
                    'Resource': "arn:aws:execute-api:*:"+ AWS_ACCOUNT_ID + ":*/*/*/*"
                }
            ]
        }
        auth_response['policyDocument'] = policy_document
    return auth_response

def decode_auth_token(auth_token):
    #Decodes the auth token
    try:
        # remove "Bearer " from the token string.
        auth_token = auth_token.replace('Bearer ', '')
        # decode using system environ $SECRET_KEY, will crash if not set.
        return jwt.decode(auth_token, API_SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        'Signature expired. Please log in again.'
        return
    except jwt.InvalidTokenError:
        'Invalid token. Please log in again.'
        return

def handler(event, context):
    try:
        auth_token = event.get('authorizationToken')
        method_arn = event.get('methodArn')

        if auth_token and method_arn:
            # verify the JWT - only for whitelisted endpoints
            user_details = decode_auth_token(auth_token)
            if user_details:
                # if the JWT is valid and not expired return a valid policy.
                return generate_policy('Allow', method_arn)


    except Exception as err:
        message = err.args[0]
        function = 'handler'
        if len(err.args) > 1:
            function = err.args[1]
        log.error('💥 Error in Lambda Authorizer: ' + message)
        error = LambdaAuthorizerError(message, HANDLER, function)
        build_error_handler_response(str(error))
    return generate_policy('Deny', method_arn)
