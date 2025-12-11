import os
import boto3
from botocore.client import Config
from app.storage.base import StorageProvider


class S3StorageProvider(StorageProvider):
    """S3-compatible storage (Railway Simple S3 / MinIO / AWS S3)."""

    def __init__(self, config):
        self.bucket = config.get('S3_BUCKET')
        self.endpoint = config.get('S3_ENDPOINT')
        self.region = config.get('S3_REGION', 'us-east-1')
        self.use_ssl = str(config.get('S3_USE_SSL', 'true')).lower() == 'true'
        access_key = config.get('S3_ACCESS_KEY_ID')
        secret_key = config.get('S3_SECRET_ACCESS_KEY')

        # Client
        self.client = boto3.client(
            's3',
            endpoint_url=self.endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=self.region,
            use_ssl=self.use_ssl,
            config=Config(signature_version='s3v4')
        )

    def save(self, key: str, file_path: str) -> str:
        # key can include folders (e.g., inventory/123/file.jpg)
        self.client.upload_file(file_path, self.bucket, key)
        return key

    def url_for(self, key: str) -> str:
        # Public URL (assumes bucket/object is public or MinIO signed policy).
        # If private is needed, switch to generate_presigned_url.
        return f"{self.endpoint.rstrip('/')}/{self.bucket}/{key.lstrip('/')}"

