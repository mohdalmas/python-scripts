# This Python script will handle the commit message and trigger the specific pipeline as required
import boto3
import re
import os
import json
import base64
import subprocess,ast
import shutil


files_to_ignore = [ "readme.md" ]
codecommit_client = boto3.client('codecommit')
codepipeline_client = boto3.client('codepipeline')
commitMessage = ""
substring = "Release "


def lambda_handler(event, context):
    
    # Extract commits
    #old_commit_id = event["detail"]["oldCommitId"]
    new_commit_id = event["detail"]["commitId"]
    
    response = codecommit_client.get_commit(repositoryName=event["detail"]["repositoryName"],commitId=new_commit_id)
    
    #Extracting the Commit Message to verify.
    commitMessage = response["commit"]["message"]
    print(commitMessage)
    
    # #Checking Commit Message Pattern
    if substring in commitMessage:
        print("Release <> Pattern found!")
        print("Running Agile Pipeline...")
        codepipeline_response = codepipeline_client.start_pipeline_execution(name=<Name of Pipeline>)
    else:
        print("Release <> Pattern not found!")
