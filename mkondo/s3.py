import os
import logging

import boto3
from botocore.exceptions import ClientError
import dotenv

dotenv.load_dotenv()

session = boto3.session.Session()

client = session.client(
    's3',
    region_name='fra1',
    endpoint_url='https://fra1.digitaloceanspaces.com',
    aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.environ.get('AWS_SECRET_KEY')
)


def get_bucket(bucket_name):
    try:
        bucket = client.get_bucket(bucket_name)
    except ClientError as e:
        bucket = None

    return bucket


def create_presigned_post(object_name, fields=None, conditions=None, expiration=3600):
    try:
        response = client.generate_presigned_post(os.environ.get('DO_BUCKET'), object_name, Fields=fields, Conditions=conditions, ExpiresIn=expiration)
    except ClientError as e:
        logging.error(e)
        return None

    return response
