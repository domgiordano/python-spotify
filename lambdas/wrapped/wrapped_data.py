import traceback
import inspect
from datetime import datetime, timezone

from lambdas.common.dynamo_helpers import update_table_item, get_item_by_key, check_if_item_exist
from lambdas.common.constants import WRAPPED_TABLE_NAME


def update_wrapped_data(data: dict, optional_fields={}):
    try:
        for field in optional_fields:
            if field not in data:
                data[field] = None
        db_entry = add_time_stamp(data)
        response = update_table_item(WRAPPED_TABLE_NAME, db_entry)
        return response
    except Exception as err:
        print(traceback.print_exc())
        frame = inspect.currentframe()
        raise Exception(str(err), f'{__name__}.{frame.f_code.co_name}')

def get_wrapped_data(email: str):
    try:
        if check_if_item_exist(WRAPPED_TABLE_NAME, 'email', email, True):
            response = get_item_by_key(WRAPPED_TABLE_NAME, 'email', email)
            return response['Item']
        else:
            return False
    except Exception as err:
        print(traceback.print_exc())
        frame = inspect.currentframe()
        raise Exception(str(err), f'{__name__}.{frame.f_code.co_name}')

def add_time_stamp(data):
    time_stamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
    data['updatedAt'] = time_stamp
    return data
