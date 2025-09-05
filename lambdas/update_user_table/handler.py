import json
import traceback

from lambdas.common.utility_helpers import build_successful_handler_response, is_called_from_api, build_error_handler_response, validate_input
from lambdas.common.errors import UpdateUserTableError
from lambdas.common.dynamo_helpers import update_user_table_refresh_token, get_user_table_data
from lambdas.common.constants import LOGGER

log = LOGGER.get_logger(__file__)

HANDLER = 'user'


def handler(event, context):
    try:

        is_api = is_called_from_api(event)

        path = event.get("path").lower()
        body = event.get("body")
        http_method = event.get("httpMethod", "POST")
        response = None

        if path:
            log.info(f'Path called: {path} \nWith method: {http_method}')

            # Update User Table
            if (path == f"/{HANDLER}/user-table") and (http_method == 'POST'):

                event_body = json.loads(body)
                required_fields = {"email",  "refreshToken"}

                if not validate_input(event_body, required_fields):
                    raise Exception("Invalid User Input - missing required field or contains extra field.")

                response = update_user_table_refresh_token(event_body['email'], event_body['refreshToken'])
            # GET user table
            if (path == f"/{HANDLER}/user-table")  and (http_method == 'GET'):

                query_string_parameters = event.get("queryStringParameters")

                if not validate_input(query_string_parameters, {'email'}):
                    raise Exception("Invalid User Input - missing required field or contains extra field.")

                response = get_user_table_data(query_string_parameters['email'])

        if response is None:
            raise Exception("Invalid Call.", 400)
        else:
            return build_successful_handler_response(response, is_api)

    except Exception as err:
        message = err.args[0]
        function = f'handler.{__name__}'
        if len(err.args) > 1:
            function = err.args[1]
        log.error(traceback.print_exc())
        error = UpdateUserTableError(message, HANDLER, function) if 'Invalid User Input' not in message else UpdateUserTableError(message, HANDLER, function, 400)
        return build_error_handler_response(str(error))
