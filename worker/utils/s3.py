import json
import os
from typing import Any

import boto3


s3_client = boto3.client('s3')


def resolve_bucket_name() -> str:
    bucket_name = os.environ.get('S3_BUCKET') or os.environ.get('S3_BUCKET_NAME') or os.environ.get('BUCKET_NAME')
    if not bucket_name:
        raise RuntimeError('S3 bucket name is not configured for the worker.')
    return bucket_name


def get_object_bytes(key: str, bucket_name: str | None = None) -> bytes:
    response = s3_client.get_object(Bucket=bucket_name or resolve_bucket_name(), Key=key)
    return response['Body'].read()


def put_json_document(key: str, payload: dict[str, Any], bucket_name: str | None = None) -> None:
    s3_client.put_object(
        Bucket=bucket_name or resolve_bucket_name(),
        Key=key,
        Body=json.dumps(payload, indent=2, default=str).encode('utf-8'),
        ContentType='application/json',
    )
