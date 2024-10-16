# The goal is to create a replica rds using the IP & snapshot identifier saved by deletion script.
# Rest other specific details we can mention here.
import json
import boto3
import logging
import time

# Constants
S3_BUCKET_NAME = ''
S3_IP_OBJECT_KEY = ''
S3_SNAPSHOT_OBJECT_KEY = ''

def get_data_from_s3(s3_client, object_key):
    try:
        response = s3_client.get_object(
            Bucket=S3_BUCKET_NAME,
            Key=object_key
        )
        data = response['Body'].read().decode('utf-8')
        return data
    except Exception as e:
        raise Exception(f'Error fetching data from S3: {str(e)}')

# Define a function to create a replica RDS instance
def create_replica_rds_instance(rds_client, replica_rds_instance_name, latest_snapshot_identifier, subnet_group_name, security_group_ids,replica_ip,db_name,db_parameter_group, logger):

    max_retries = 5  # Set the maximum number of retries
    retries = 0

    while retries < max_retries:
        try:
            # Create a new replica RDS instance from the latest snapshot
            response = rds_client.restore_db_instance_from_db_snapshot(
                DBInstanceIdentifier=replica_rds_instance_name,
                DBSnapshotIdentifier=latest_snapshot_identifier,
                DBInstanceClass='db.r6i.8xlarge',
                MultiAZ=False,
                PubliclyAccessible=False,
                DBSubnetGroupName=subnet_group_name,
                VpcSecurityGroupIds=security_group_ids,
                DBName=db_name,
                CopyTagsToSnapshot=True,
                DBParameterGroupName=db_parameter_group,
                Tags=[
                ]
            )
            logger.info("Creating Replica DB Instance")
            
            return {
                'statusCode': 200,
                'body': 'Successfully created the replica RDS instance and decommissioned the previous day\'s replica.'
            }
        except Exception as e:
            logger.error(f"Exception caught during replica creation: {str(e)}")
            retries += 1

            if retries < max_retries:
                logger.info(f"Retrying in 30 seconds (Attempt {retries}/{max_retries})...")
                time.sleep(30)  # Sleep for 30 seconds before retrying
            else:
                logger.error("Maximum number of retries reached. Replica creation failed.")
                return {
                    'statusCode': 500,
                    'body': f'Error: Maximum number of retries reached. Replica creation failed. Exception: {str(e)}'
                }


def lambda_handler(event, context):

    replica_rds_instance_name = ""
    subnet_group_name = ""
    security_group_ids = [""]
    db_name=""
    db_parameter_group = ""
###
    rds_client = boto3.client('rds')
    s3_client = boto3.client('s3')

    # Initialize the logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.info(event)
    
    try:
         # Fetch the replica IP address from S3
        replica_ip = get_data_from_s3(s3_client, S3_IP_OBJECT_KEY)
        print(f'Replica IP Address: {replica_ip}')
        
        # Fetch the latest snapshot identifier from S3
        latest_snapshot_identifier = get_data_from_s3(s3_client, S3_SNAPSHOT_OBJECT_KEY)
        print(f'Latest Snapshot Identifier: {latest_snapshot_identifier}')
        
        # Create a new replica RDS instance from the latest snapshot
        # Call the create_replica_rds_instance function
        create_replica_rds_instance(rds_client, replica_rds_instance_name, latest_snapshot_identifier, subnet_group_name, security_group_ids,replica_ip,db_name,db_parameter_group, logger)

    except Exception as e:
        logger.error(f'Error: {str(e)}')
        return {
            'statusCode': 500,
            'body': f'Error: {str(e)}'
        }
    
