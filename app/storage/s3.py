import os
import boto3
from botocore.client import Config
from app.storage.base import StorageProvider


class S3StorageProvider(StorageProvider):
    """S3-compatible storage (Railway Simple S3 / MinIO / AWS S3)."""

    def __init__(self, config):
        from flask import current_app
        self.bucket = config.get('S3_BUCKET')
        self.endpoint = config.get('S3_ENDPOINT')  # Internal endpoint for uploads
        self.public_endpoint = config.get('S3_PUBLIC_ENDPOINT') or self.endpoint  # Public endpoint for URLs
        self.region = config.get('S3_REGION', 'us-east-1')
        self.use_ssl = str(config.get('S3_USE_SSL', 'true')).lower() == 'true'
        access_key = config.get('S3_ACCESS_KEY_ID')
        secret_key = config.get('S3_SECRET_ACCESS_KEY')

        current_app.logger.info(
            f'🔧 S3StorageProvider initialized: '
            f'bucket={self.bucket}, endpoint={self.endpoint}, '
            f'public_endpoint={self.public_endpoint}, '
            f'region={self.region}, use_ssl={self.use_ssl}'
        )

        # Client uses internal endpoint for uploads
        self.client = boto3.client(
            's3',
            endpoint_url=self.endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=self.region,
            use_ssl=self.use_ssl,
            config=Config(signature_version='s3v4')
        )

    def save(self, key: str, file_path: str, delete_after_upload: bool = False) -> str:
        """
        Save file to S3.
        
        Args:
            key: S3 key (path) where to store the file
            file_path: Local path to the file to upload
            delete_after_upload: If True, delete local file after successful upload (only for S3)
        
        Returns:
            The key where the file was stored
        """
        from flask import current_app
        import os
        
        current_app.logger.info(
            f'☁️ S3Storage.save: key={key}, file_path={file_path}, '
            f'file_exists={os.path.exists(file_path) if file_path else False}, '
            f'delete_after_upload={delete_after_upload}'
        )
        
        if not os.path.exists(file_path):
            current_app.logger.error(f'❌ S3Storage.save: File not found: {file_path}')
            raise FileNotFoundError(f'File not found: {file_path}')
        
        try:
            self.client.upload_file(file_path, self.bucket, key)
            current_app.logger.info(f'✅ S3Storage: Successfully uploaded {key} to s3://{self.bucket}/{key}')
            
            # Delete local file after successful upload if requested
            # This is safe for S3 because the file is already in S3
            if delete_after_upload:
                try:
                    os.remove(file_path)
                    current_app.logger.info(f'🗑️ S3Storage: Deleted local file after upload: {file_path}')
                except Exception as e:
                    current_app.logger.warning(f'⚠️ S3Storage: Could not delete local file {file_path}: {e}')
        except Exception as e:
            current_app.logger.error(f'❌ S3Storage.save: Error uploading {key}: {str(e)}', exc_info=True)
            raise
        
        return key

    def url_for(self, key: str) -> str:
        # Public URL (assumes bucket/object is public or MinIO signed policy).
        # Uses S3_PUBLIC_ENDPOINT if available, otherwise falls back to S3_ENDPOINT.
        # If private is needed, switch to generate_presigned_url.
        from flask import current_app
        # Use public endpoint for URLs (accessible from web), internal endpoint for uploads
        endpoint_to_use = self.public_endpoint
        url = f"{endpoint_to_use.rstrip('/')}/{self.bucket}/{key.lstrip('/')}"
        current_app.logger.debug(
            f'🔗 S3Storage.url_for: key={key}, '
            f'public_endpoint={self.public_endpoint}, internal_endpoint={self.endpoint} -> {url}'
        )
        return url

