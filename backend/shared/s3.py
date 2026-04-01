import os

import boto3

try:
    from botocore.config import Config
except Exception:  # pragma: no cover - fallback for lightweight test doubles
    Config = None


def _build_s3_client():
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "ap-northeast-2"
    endpoint_url = f"https://s3.{region}.amazonaws.com"
    client_kwargs = {
        "region_name": region,
        "endpoint_url": endpoint_url,
    }
    if Config is not None:
        client_kwargs["config"] = Config(signature_version="s3v4", s3={"addressing_style": "virtual"})
    return boto3.client(
        "s3",
        **client_kwargs,
    )


s3_client = _build_s3_client()


def resolve_bucket_name(bucket: str | None = None) -> str:
    resolved_bucket = bucket or os.environ.get("S3_BUCKET_NAME") or os.environ.get("BUCKET_NAME")
    if not resolved_bucket:
        raise RuntimeError("S3 bucket name is not configured.")
    return resolved_bucket


def generate_presigned_url(
    bucket: str,
    key: str,
    expiration: int = 3600,
    content_type: str | None = None,
) -> str:
    params = {"Bucket": bucket, "Key": key}
    if content_type:
        params["ContentType"] = content_type

    return s3_client.generate_presigned_url(
        "put_object",
        Params=params,
        ExpiresIn=expiration,
    )


def generate_download_url(bucket: str, key: str, expiration: int = 3600) -> str:
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expiration,
    )


def put_object_bytes(
    bucket: str,
    key: str,
    body: bytes,
    content_type: str,
) -> None:
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType=content_type,
    )
