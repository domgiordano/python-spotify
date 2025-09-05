from datetime import datetime, timezone

from lambdas.common.dynamo_helpers import update_table_item, get_item_by_key, check_if_item_exist
from lambdas.common.constants import WRAPPED_TABLE_NAME, LOGGER

log = LOGGER.get_logger(__file__)


def update_wrapped_data(data: dict, optional_fields={}):
    try:
        for field in optional_fields:
            if field not in data:
                data[field] = None
        db_entry = add_time_stamp(data)
        response = update_table_item(WRAPPED_TABLE_NAME, db_entry)
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return 'User Opted into Mothly Wrapped Success.'
        else:
            raise Exception('Failed to Opt User into Monthly Wrapped')
    except Exception as err:
        log.error(f"Update Wrapped Data: {err}")
        raise Exception(f"Update Wrapped Data: {err}")

def get_wrapped_data(email: str):
    try:
        if check_if_item_exist(WRAPPED_TABLE_NAME, 'email', email, True):
            response = get_item_by_key(WRAPPED_TABLE_NAME, 'email', email)
            return response
        else:
            return {'active': False}
    except Exception as err:
        log.error(f"Get Wrapped Data: {err}")
        raise Exception(f"Get Wrapped Data: {err}")

def add_time_stamp(data):
    time_stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    data['updatedAt'] = time_stamp
    return data
