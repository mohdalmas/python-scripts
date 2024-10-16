# The goal is to run the sql script saved in s after creation of RDS.
import json
import cx_Oracle
import boto3
import logging


# Set up the logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)  # Set the desired log level

def lambda_handler(event, lcontext):        
    # AWS Secrets Manager settings
    secret_name = ""
    region_name = ""
    
    # AWS S3 settings
    s3_bucket = ""
    s3_key = ""
    
    # Create a Secrets Manager client
    session = boto3.session.Session()
    connection = ""
    secrets_client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )
    
    # Retrieve the secret values
    secrets_response = secrets_client.get_secret_value(SecretId=secret_name)
    secrets = secrets_response['SecretString']
    secrets_dict = json.loads(secrets)
    
    # Extract database connection parameters
    db_host = secrets_dict['host']
    db_name = secrets_dict['dbname']
    db_user = secrets_dict['username']
    db_password = secrets_dict['password']
    db_dsn = db_host+"/"+db_name

    # AWS S3 client
    s3_client = session.client(
        service_name='s3',
        region_name=region_name
    )
    
    # Download the SQL script from S3
    s3_response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
    sql_script = s3_response['Body'].read().decode('utf-8')

    # Split the SQL script into individual statements
    sql_statements = sql_script.split(';')

    #logger.info(sql_statements)
    logger.info("SQL Script has been downloaded from S3")
    
    # Check if RDS is reachable before executing the script
    try:
        connection = cx_Oracle.connect(
            dsn=db_dsn,
            user=db_user,
            password=db_password
        )
        logger.info("RDS instance is reachable")
    except cx_Oracle.DatabaseError as e:
        logger.info(f"RDS instance is not reachable. Error: {e}")
        return  # Exit the function if RDS is not reachable 
    
    try:
        # Create a cursor
        cursor = connection.cursor()
        
        # Execute each SQL statement
        for statement in sql_statements:
            if statement.strip():  # Skip empty statements
                try:
                    cursor.execute(statement)
                    connection.commit()
                    logger.info(f"SQL statement executed successfully: {statement}")
                except cx_Oracle.Error as e:
                    logger.info(f"Error executing SQL statement: {statement}, Error: {e}")
    except cx_Oracle.Error as e:
        logger.info(f"Error: {e}")
    finally:
        if connection:
            # Close the cursor and connection
            cursor.close()
            connection.close()

