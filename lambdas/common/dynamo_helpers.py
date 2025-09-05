from datetime import datetime, timezone
import boto3
from lambdas.common.constants import AWS_DEFAULT_REGION, DYNAMODB_KMS_ALIAS, LOGGER, WRAPPED_TABLE_NAME

log = LOGGER.get_logger(__file__)

dynamodb_res = boto3.resource("dynamodb", region_name=AWS_DEFAULT_REGION)
dynamodb_client = boto3.client("dynamodb", region_name=AWS_DEFAULT_REGION)
kms_res = boto3.client("kms")

HANDLER = 'dynamo_helpers'

# Performs full table scan, and fetches ALL data from table in pages...
def full_table_scan(table_name, **kwargs):
    try:
        table = dynamodb_res.Table(table_name)
        response = table.scan()
        data = response['Items']  # We've got our data now!
        while 'LastEvaluatedKey' in response:  # If we have this field in response...
            # It tells us where we left off, and signifies there's more data to fetch in "pages" after this particular key.
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            data.extend(response['Items'])  # Add more data as each "page" comes in until we're done (LastEvaluatedKey gone)

        # If we passed in these optional keyword args, let's...
        # SORT the data...default is ascending order even if there are no sort args present.
        if 'attribute_name_to_sort_by' in kwargs:
            is_reverse = kwargs['is_reverse'] if 'is_reverse' in kwargs else False
            data = sorted(data, key=lambda i: i[kwargs['attribute_name_to_sort_by']], reverse=is_reverse)

        return data
    except Exception as err:
        log.error(f"Dynamodb Full Table Scan: {err}")
        raise Exception(f"Dynamodb Full Table Scan: {err}")
def table_scan_by_ids(table_name, key, ids, goal_filter, **kwargs):
    try:
        table = dynamodb_res.Table(table_name)
        keys = {
            table.name: {
                'Keys': [{key: id} for id in ids]
            }
        }

        response = dynamodb_res.batch_get_item(RequestItems=keys)
        data = response['Responses'][table.name]

        for offering in data:
            if len(offering['rank_dict']) > 0:
                offering['rank'] = offering['rank_dict'][goal_filter]

        # Sort data
        if 'attribute_name_to_sort_by' in kwargs:
            is_reverse = kwargs['is_reverse'] if 'is_reverse' in kwargs else False
            data = sorted(data, key=lambda i: i[kwargs['attribute_name_to_sort_by']], reverse=is_reverse)

        return data
    except Exception as err:
        log.error(f"Dynamodb Table Scan by IDs: {err}")
        raise Exception(f"Dynamodb Table Scan by IDs: {err}")

# Update Entire Table Item - Send in full dict of item
def delete_table_item(table_name, primary_key, primary_key_value):
    try:
        check_if_item_exist(table_name, primary_key, primary_key_value)
        table = dynamodb_res.Table(table_name)
        response = table.delete_item(
            Key={
                primary_key: primary_key_value
            }
        )
        return response
    except Exception as err:
        log.error(f"Dynamodb Table Delete Table Item: {err}")
        raise Exception(f"Dynamodb Table Delete Table Item: {err}")


# Update Entire Table Item - Send in full dict of item
def update_table_item(table_name, table_item):
    try:
        table = dynamodb_res.Table(table_name)
        response = table.put_item(
            Item=table_item
        )
        return response
    except Exception as err:
        log.error(f"Dynamodb Table Update Table Item: {err}")
        raise Exception(f"Dynamodb Table Update Table Item: {err}")


# Update single field of Table - send in one attribute and key
def update_table_item_field(table_name, primary_key, primary_key_value, attr_key, attr_val):
    try:
        check_if_item_exist(table_name, primary_key, primary_key_value)

        table = dynamodb_res.Table(table_name)
        response = table.update_item(
            Key={
                primary_key: primary_key_value
            },
            UpdateExpression="set #attr_key = :attr_val",
            ExpressionAttributeValues={
                ':attr_val': attr_val
            },
            ExpressionAttributeNames={
                '#attr_key': attr_key
            },
            ReturnValues="UPDATED_NEW"
        )
        return response
    except Exception as err:
        log.error(f"Dynamodb Table Update Table Item Field: {err}")
        raise Exception(f"Dynamodb Table Update Table Item Field: {err}")

def check_if_item_exist(table_name, id_key, id_val, override=False):
    try:
        table = dynamodb_res.Table(table_name)
        response = table.get_item(
            Key={
                id_key: id_val,
            }
        )
        if 'Item' in response:
            return True
        elif override:
            return False
        else:
            raise Exception("Invalid ID (" + id_val + "): Item Does not Exist.")
    except Exception as err:
        log.error(f"Dynamodb Table Check If Item Exists: {err}")
        raise Exception(f"Dynamodb Table Check If Item Exists: {err}")

def get_item_by_key(table_name, id_key, id_val):
    try:

        table = dynamodb_res.Table(table_name)
        response = table.get_item(
            Key={
                id_key: id_val,
            }
        )
        if 'Item' in response:
            return response['Item']
        else:
            raise Exception("Invalid ID (" + id_val + "): Item Does not Exist.")
    except Exception as err:
        log.error(f"Dynamodb Table Get Item By Key: {err}")
        raise Exception(f"Dynamodb Table Get Item By Key: {err}")

def query_table_by_key(table_name, id_key, id_val, ascending=False):
    try:
        table = dynamodb_res.Table(table_name)
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key(id_key).eq(id_val),
            ScanIndexForward=ascending
        )
        return response
    except Exception as err:
        log.error(f"Dynamodb Table Query Table By Key: {err}")
        raise Exception(f"Dynamodb Query Table Item By Key: {err}")
def item_has_property(item, property):
    for field in item:
        if field == property:
            return True

    return False

def emptyTable(table_name, hash_key, hash_key_type):
    try:
        deleteTable(table_name)
        table = createTable(table_name, hash_key, hash_key_type)
        return table
    except Exception as err:
        log.error(f"Dynamodb Table Empty Table: {err}")
        raise Exception(f"Dynamodb Table Empty Table: {err}")

def deleteTable(table_name):
    try:
        return dynamodb_client.delete_table(TableName=table_name)
    except Exception as err:
        log.error(f"Dynamodb Table Delete Table: {err}")
        raise Exception(f"Dynamodb Table Delete Table: {err}")
def createTable(table_name, hash_key, hash_key_type):
    try:
        #Wait for table to be deleted
        waiter = dynamodb_client.get_waiter('table_not_exists')
        waiter.wait(TableName=table_name)
        # Get KMS Key
        kms_key = kms_res.describe_key(
            KeyId=DYNAMODB_KMS_ALIAS
        )
        #Create table
        table = dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': hash_key,
                    'KeyType': 'HASH'
                }
            ],
            AttributeDefinitions= [
                {
                    'AttributeName': hash_key,
                    'AttributeType': hash_key_type
                }
            ],
            StreamSpecification={
                'StreamEnabled': True,
                'StreamViewType': 'NEW_AND_OLD_IMAGES'
            },
            SSESpecification={
                'Enabled': True,
                'SSEType': 'KMS',
                'KMSMasterKeyId': kms_key['KeyMetadata']['Arn']
            },
            BillingMode='PAY_PER_REQUEST'
        )

        #Wait for table to exist
        waiter = dynamodb_client.get_waiter('table_exists')
        waiter.wait(TableName=table_name)

        return table
    except Exception as err:
        log.error(f"Dynamodb Table Create Table: {err}")
        raise Exception(f"Dynamodb Table Create Table: {err}")
    

## USER TABLE
def update_user_table_release_radar_id(user: dict, playlist_id: str):
    try:
        # Release Radar Id
        user['releaseRadarId'] = playlist_id
        # Time Stamp
        user['updatedAt'] = __get_time_stamp()
        update_table_item(WRAPPED_TABLE_NAME, user)
    except Exception as err:
        log.error(f"Update User Table Entry: {err}")
        raise Exception(f"Update User Table Entry: {err}")
    
def update_user_table_refresh_token(email: str, refresh_token: str):
    try:
        # Get User Data
        user = get_item_by_key(WRAPPED_TABLE_NAME, 'email', email)
        # Release Radar Id
        user['refreshToken'] = refresh_token
        # Active
        user['active'] = True
        # Time Stamp
        user['updatedAt'] = __get_time_stamp()
        update_table_item(WRAPPED_TABLE_NAME, user)
    except Exception as err:
        log.error(f"Update User Table Refresh Token: {err}")
        raise Exception(f"Update User Table Refresh Token: {err}")
    
    
def __get_time_stamp():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

def get_user_table_data(email: str):
    try:
        # Get User Data
        user = get_item_by_key(WRAPPED_TABLE_NAME, 'email', email)
        return user
    except Exception as err:
        log.error(f"Get User Table Data: {err}")
        raise Exception(f"Get User Table Data: {err}")

