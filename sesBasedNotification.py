import json
import boto3
from datetime import datetime
from botocore.exceptions import ClientError

def parse_date_time(datetime_str):
    parsed_date_time = datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S.%fZ')
    return parsed_date_time.strftime('%a, %d %b %Y %H:%M:%S GMT')

def get_triggered_by_email(trigger_detail):
    parts = trigger_detail.split('/')
    return parts[2]

def send_email_via_ses(email_subject, email_body):
    try:
        ses_client = boto3.client('ses', region_name='eu-central-1')
        response = ses_client.send_email(
            Source='',
            Destination={[]},
            Message={'Subject': {'Data': email_subject},
                     'Body': {'Html': {'Data': email_body}}}
        )
        return {'statusCode': 200, 'body': json.dumps('Email sent successfully via SES.')}
    except ClientError as e:
        error_message = f"An error occurred while sending the email: {e.response['Error']['Message']}"
        return {'statusCode': 500, 'body': json.dumps(error_message)}

def lambda_handler(event, context):
    codepipeline_client = boto3.client('codepipeline')
    message_detail = json.loads(event['Records'][0]['Sns']['Message'])
    print(message_detail)
    pipeline_name = message_detail['detail']['pipeline']
    pipeline_execution_id = message_detail['detail']['execution-id']
    pipeline_execution_status = message_detail['detail']['state']
    formatted_date_time = parse_date_time(message_detail['detail']['start-time'])

    response_execution_data = codepipeline_client.get_pipeline_execution(
        pipelineName=pipeline_name,
        pipelineExecutionId=pipeline_execution_id
    )
    
    triggered_by_email = get_triggered_by_email(response_execution_data['pipelineExecution']['trigger']['triggerDetail'])
    
    response_state_data = codepipeline_client.get_pipeline_state(name=pipeline_name)
    
    email_subject = f"[{pipeline_execution_status}] AWSPipeline - {pipeline_name} Report"
    email_body = f"<html><body><p>Hi Team,</p><br>"
    email_body += f"<p>Please find the detailed report of the pipeline:</p>"
    email_body += f"<p><b>Name:</b><br>{pipeline_name}</p>"
    email_body += f"<p><b>Triggered By:</b><br>{triggered_by_email}</p>"
    email_body += f"<p><b>Date & Time:</b><br>{formatted_date_time}</p>"

    package_info_value = next((variable['resolvedValue'] for variable in response_execution_data['pipelineExecution']['variables'] if variable['name'] == 'packageName'), None)
    additional_info_value = next((variable['resolvedValue'] for variable in response_execution_data['pipelineExecution']['variables'] if variable['name'] == 'additionalInfo'), None)
    if package_info_value:
        email_body += f"<p><b>Package Name:</b><br>{package_info_value}</p>"
    if additional_info_value:
        email_body += f"<p><b>Additional Info:</b><br>{additional_info_value}</p>"
    
    email_body += f"<p><b>Stages:</b><br>"
    if not response_state_data["stageStates"]:
        email_body += f"<font color='red'>NO STAGES FOUND</font></p>"
        
    for stage in response_state_data["stageStates"]:
        stage_name = stage["stageName"]
        status = stage["latestExecution"]["status"]
        logs_url = stage["actionStates"][0]["latestExecution"].get("externalExecutionUrl", "N/A")
        last_status_change = stage["actionStates"][0]["latestExecution"]["lastStatusChange"].strftime('%a, %d %b %Y %H:%M:%S GMT')
        if last_status_change >= formatted_date_time:
            email_body += f"<br>-&nbsp; <b>Stage Name:</b> {stage_name}<br>"
            email_body += f"&nbsp;&nbsp; <b>Status:</b> {status}<br>"
            if logs_url != "N/A":
                email_body += f"&nbsp;&nbsp; <b>Logs:</b> <a href='{logs_url}'>{logs_url}</a><br>"
            else:
                email_body += f"&nbsp;&nbsp; <b>Logs:</b> {logs_url}<br>"
            email_body += f"&nbsp;&nbsp; <b>----</b><br>"
    
    email_body += "<br><br><p>Regards,<br>Operations Team</p>"
    
    return send_email_via_ses(email_subject, email_body)

