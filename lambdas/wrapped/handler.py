import json
import traceback

from lambdas.common.utility_helpers import build_successful_handler_response, is_called_from_api, build_error_handler_response, validate_input
from lambdas.common.errors import WrappednError
from wrapped_data import update_wrapped_data, get_wrapped_data

HANDLER = 'wrapped'


def handler(event, context):
    try:
        is_api = is_called_from_api(event)

        path = event.get("path").lower()
        body = event.get("body")
        http_method = event.get("httpMethod", "POST")
        response = None
        event_auth = event['headers']['Authorization']

        if path:
            print(f'Path called: {path} \nWith method: {http_method}')

            # Add New Wrapped Data
            if (path == f"/{HANDLER}/data") and (http_method == 'POST'):

                event_body = json.loads(body)
                required_fields = {"email", "refreshToken", "active"}
                optional_fields = {"top_song_ids", "top_artist_ids", "top_genre_ids"}

                if not validate_input(event_body, required_fields, optional_fields):
                    raise Exception("Invalid User Input - missing required field or contains extra field.")

                response = update_wrapped_data(event_body, optional_fields)

            # Get Existing Wrapped Data
            elif (path == f"/{HANDLER}/data") and (http_method == 'GET'):

                query_string_parameters = event.get("queryStringParameters")

                if not validate_input(query_string_parameters, {'email'}):
                    raise Exception("Invalid User Input - missing required field or contains extra field.")

                response = get_wrapped_data(query_string_parameters['email'])

        if response is None:
            raise Exception("Invalid Call.", 400)
        else:
            return build_successful_handler_response(response, is_api)

    except Exception as err:
        message = err.args[0]
        function = f'handler.{__name__}'
        if len(err.args) > 1:
            function = err.args[1]
        print(traceback.print_exc())
        error = WrappednError(message, HANDLER, function) if 'Invalid User Input' not in message else WrappednError(message, HANDLER, function, 400)
        return build_error_handler_response(str(error))
