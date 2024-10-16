#The Goal is to delete the replica rds and create a new replica rds using latest snapshotidentifier.
# This script is saving the latest snapshot identified from Current running replica.
# Deleting the Existing replica or calling the creation replica if no replica exist.

import json
import boto3
import logging
import datetime

# Constants
S3_BUCKET_NAME = ''
S3_IP_OBJECT_KEY = ''
S3_SNAPSHOT_OBJECT_KEY = ''
REPLICA_RDS_INSTANCE_NAME = ''
SOURCE_RDS_INSTANCE_NAME = ''
LAMBDA_FUNCTION_NAME = ''


def get_replica_ip(rds_client, replica_rds_instance_name):
    try:
        response = rds_client.describe_db_instances(DBInstanceIdentifier=replica_rds_instance_name)
        replica_instances = response.get('DBInstances', [])
        
        if replica_instances:
            return replica_instances[0]['Endpoint']['Address']
        else:
            raise Exception(f'Replica RDS instance ({replica_rds_instance_name}) not found.')
    except Exception as e:
        raise Exception(f'Error fetching replica IP address: {str(e)}')

def save_to_s3(s3_client, object_key, data):
    try:
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=object_key,
            Body=data.encode('utf-8')
        )
        return f'Data saved to S3 bucket: {S3_BUCKET_NAME}/{object_key}'
    except Exception as e:
        raise Exception(f'Error saving data to S3: {str(e)}')

def invoke_db_creation_lambda(lambda_client, function_name):
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='Event'
        )
        return response
    except Exception as e:
        raise Exception(f'Error invoking Lambda function: {str(e)}')

def lambda_handler(event, context):
    rds_client = boto3.client('rds')
    s3_client = boto3.client('s3')
    lambda_client = boto3.client('lambda')
    
    # Initialize the logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Get the current date in YYYY-MM-DD format
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    try:     
        # Get the identifier of the latest automated snapshot for the source RDS instance
        response = rds_client.describe_db_snapshots(
            DBInstanceIdentifier=SOURCE_RDS_INSTANCE_NAME,
            SnapshotType='automated',
            MaxRecords=100,
            IncludeShared=False,
            IncludePublic=False
        )

        if not response['DBSnapshots']:
            raise ValueError("No automated snapshots found for the source RDS instance.")

        # Sort the snapshots by snapshot creation time to get the latest one
        snapshots = sorted(response['DBSnapshots'], key=lambda x: x['SnapshotCreateTime'], reverse=True)
        latest_snapshot_identifier = snapshots[0]['DBSnapshotIdentifier']
        logger.info(latest_snapshot_identifier)

        # Check if the snapshot's creation date matches the current date
        if current_date not in latest_snapshot_identifier:
            raise ValueError("The latest automated snapshot was not created today.")

        # Fetch the IP address of the replica RDS instance
        replica_ip = get_replica_ip(rds_client, REPLICA_RDS_INSTANCE_NAME)
        logger.info(f'Replica RDS Instance IP Address: {replica_ip}')
        
        # Save the replica IP address to S3
        save_ip_result = save_to_s3(s3_client, S3_IP_OBJECT_KEY, replica_ip)
        logger.info(save_ip_result)

        # Save the latest snapshot identifier to S3
        save_snapshot_result = save_to_s3(s3_client, S3_SNAPSHOT_OBJECT_KEY, latest_snapshot_identifier)
        logger.info(save_snapshot_result)
        
        # Check if the previous day's replica exists and delete it if found
        try:
            response = rds_client.describe_db_instances(DBInstanceIdentifier=REPLICA_RDS_INSTANCE_NAME)
            if 'DBInstances' in response and len(response['DBInstances']) > 0:
                # The previous day's replica exists. Delete it.
                rds_client.delete_db_instance(
                    DBInstanceIdentifier=REPLICA_RDS_INSTANCE_NAME,
                    SkipFinalSnapshot=True
                )
                logger.info(f"Deleting DB '{REPLICA_RDS_INSTANCE_NAME}'")
        except rds_client.exceptions.DBInstanceNotFoundFault:
            # The previous day's replica does not exist. No need to delete it.
            logger.info(f"Replica '{REPLICA_RDS_INSTANCE_NAME}' does not exist.")
            logger.info("Invoking the DB Creation Function directly.")
            invoke_db_creation_lambda(lambda_client, LAMBDA_FUNCTION_NAME)
            
    except Exception as e:
        logger.error(f'Error: {str(e)}')
        return {
            'statusCode': 500,
            'body': f'Error: {str(e)}'
        }

