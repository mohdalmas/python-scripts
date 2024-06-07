import os
import email
import boto3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email import encoders
from botocore.exceptions import ClientError

# Email details
sender = 'TMNL-BillingOps@wipro.com'
recipients = ['TMNL-BillingOps@wipro.com', 'b2c_giants@odido.nl']
cc_recipients = ['mohd.almas@odido.nl']
subject = f'Checkmarx PDF Report for Pipeline $AWS_PIPELINE_NAME'
body_text = f"""
Hi Team,

Please check the attached report for the following pipeline execution.

Pipeline Name: $AWS_PIPELINE_NAME
Pipeline Execution: $AWS_PIPELINE_ID

Regards,
Billing Team
"""

# Function to send the email with attachment using send_raw_email
def send_email_with_attachment():
  try:
    # Create a multipart message
    message = MIMEMultipart('mixed')
   message['From'] = sender
   message['To'] = ', '.join(recipients)
   message['Cc'] = ', '.join(cc_recipients)
   message['Subject'] = subject

    # Attach the email body
    body_text = f"""
    Hi Team,
    
    Please check the attached checkmarx report for the following pipeline execution.
    
    Pipeline Name: $AWS_PIPELINE_NAME
    Pipeline Execution: $AWS_PIPELINE_ID
    
    Regards,
    Billing Team
    """
    body_text_mime = MIMEText(body_text, 'plain')
    message.attach(body_text_mime)

    # Define the attachment part
    attachment_path = '/tmp/SAST_checkmarx.pdf'  # Replace with your actual path
    att = MIMEApplication(open(attachment_path, 'rb').read())
    att.add_header('Content-Disposition','attachment',filename=os.path.basename(attachment_path))

    # Attach the part to the message
    message.attach(att)
    # Create SES client (unchanged)
    ses = boto3.client('ses', region_name='$AWS_DEFAULT_REGION')

    # Send the raw email (unchanged)
    response = ses.send_raw_email(
        Source=message['From'],
        Destinations=[message['To']],
        RawMessage={'Data': message.as_string()}
    )
    print("Email sent! Message ID:", response['MessageId'])

  except ClientError as e:
    print("Error:", e.response['Error']['Message'])

# Call the function to send the email
send_email_with_attachment()