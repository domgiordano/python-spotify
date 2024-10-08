
import datetime
import decimal
import json
import logging
import os
from urllib3.connection import HTTPConnection
import base64

# Used to ensure we dump our JSON out with a decimal decoder, so that it gets logged okay if a decimal.
from lambdas.common.constants import RESPONSE_HEADERS, ENV

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return int(obj)
        return super(DecimalEncoder, self).default(obj)


def is_called_from_api(event):
    # If body is not a dict, we'll assume it's a string from API Gateway
    return type(event['body']) != dict


def extract_body_from_event(event, is_api):
    if is_api:
        return json.loads(event.get('body'))
    else:
        return event.get('body')


def build_successful_handler_response(body_object, is_api):
    """This function that should be invoked in the except block of customer facing _handler functions
    Returns a successful _handler call."""
    return {
        'statusCode': 200,
        'headers': RESPONSE_HEADERS,
        'body': json.dumps(body_object, cls=DecimalEncoder) if is_api else body_object,
        "isBase64Encoded": False
    }


def build_error_handler_response(error, is_api=True):
    """This function that should be invoked in the except block of customer facing _handler functions.
    Returns a generic error response with a string in the "message" property of the actual error.
    The calling application should examine response body for an 'error' property at root of it.  If that is present,
    then the body would also contain a 'message' property from which you can grab the message text to shown to the
    customer-facing web user, if the handler is to be used by customer apps.  Customer-facing handlers should pass
    in constants.GENERIC_CUSTOMER_FACING_ERROR_MSG as the 'friendly_error_msg'.
    Otherwise, build_successful__handler_response should be invoked as the last statement in the try block of the
    calling _handler function."""
    error_dict = json.loads(error)
    status = error_dict['status']
    del error_dict['status']
    body_object = {"error": error_dict}
    return {
        'statusCode': status,
        'headers': RESPONSE_HEADERS,
        'body': json.dumps(body_object, cls=DecimalEncoder) if is_api else body_object,
        "isBase64Encoded": False
    }


def set_response(statusCode, body):
    return {
        "statusCode": statusCode or 500,
        "headers": {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"},
        "body": body or {"error": {"message": "Something went wrong..."}},
        "isBase64Encoded": False
    }


def log_handler_error(friendly_error_msg, err_args_text, calling_module):
    # logging configuration:
    friendly_error_msg = "log_error called from {0}! FRIENDLY MESSAGE: {1}".format(
        calling_module, friendly_error_msg)
    err_args_text = "log_error called from {0}! ERR ARGS: {1}".format(
        calling_module, err_args_text)

    logger = logging.getLogger()
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - line #: %(lineno)d - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel(logging.DEBUG)
    HTTPConnection.debuglevel = 1

    # Actually perform the logging...
    logger.error(friendly_error_msg)
    logger.error(err_args_text)

def request_on_long():
    """Format = YYYY-MM-DD - Example: 2022-03-02"""

    time_now = datetime.datetime.utcnow()
    date_now = time_now.strftime('%Y-%m-%d')
    return date_now


def request_time():
    """Format = PTAHBMCS where A, B, and C are hours, mins, seconds - Example: PT16H19M10S"""

    time_now = datetime.datetime.utcnow()
    requested_time_template = "PT{}H{}M{}S"
    return requested_time_template.format(time_now.strftime('%H'), time_now.strftime('%M'), time_now.strftime('%S'))


def encoded_key(consumer_key, consumer_secret):
    """Rest authentication for Basic Auth Encoding."""
    data = "%s:%s" % (consumer_key, consumer_secret)
    encoded_bytes = base64.b64encode(data.encode("utf-8"))
    encoded_str = str(encoded_bytes, "utf-8")
    return encoded_str

def format_date(raw_date):
    date_mdy = raw_date.split('/')
    date = datetime.datetime(int(date_mdy[2]), int(date_mdy[0]), int(date_mdy[1]))
    return date


def determine_url_version():
    if ENV == 'prod':
        return 'v1'
    else:
        return 'v2'


def validate_input(input, required_fields={}, optional_fields={}):
    if input is None and not required_fields and not optional_fields:
        return True
    allowed_fields = set(required_fields) | set(optional_fields)
    return required_fields <= set(input.keys()) <= allowed_fields
