from lambdas.common.dynamo_helpers import full_table_scan
from lambdas.common.constants import WRAPPED_TABLE_NAME

def get_active_wrapped_users():
     try:
        table_values = full_table_scan(WRAPPED_TABLE_NAME)
        table_values[:] = [item for item in table_values if item['active']]
        return table_values
     except Exception as err:
        print(f"Get Active Wrapped Users: {err}")
        raise Exception(f"Get Active Wrapped Users: {err}")