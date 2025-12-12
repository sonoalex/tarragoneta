import os
import time
from functools import lru_cache
import boto3
from botocore.client import Config
from app.storage.base import StorageProvider


class S3StorageProvider(StorageProvider):
    """S3-compatible storage (Railway Simple S3 / MinIO / AWS S3)."""

    def __init__(self, config):
        from flask import current_app
        # 1. Recuperación de Configuración
        self.bucket = config.get('S3_BUCKET')
        
        # Endpoint interno (Ej: http://storage.railway.internal:9000)
        self.endpoint = config.get('S3_ENDPOINT')  
        
        # Endpoint público (Ej: https://storage-xxxx.up.railway.app)
        # Se asume que el usuario QUITARÁ el :443 manualmente en Railway
        self.public_endpoint = config.get('S3_PUBLIC_ENDPOINT') or self.endpoint
        
        self.region = config.get('S3_REGION', 'us-east-1')
        access_key = config.get('S3_ACCESS_KEY_ID')
        secret_key = config.get('S3_SECRET_ACCESS_KEY')
        
        # La variable S3_USE_SSL está pensada para el cliente INTERNO
        self.use_ssl = str(config.get('S3_USE_SSL', 'true')).lower() == 'true'

        # Cache para URLs (se mantiene la lógica)
        self._url_expires = {}
        self._cache_refresh_threshold = 300 

        current_app.logger.info(
            f'🔧 S3StorageProvider initialized: '
            f'bucket={self.bucket}, endpoint={self.endpoint}, '
            f'public_endpoint={self.public_endpoint}, '
            f'region={self.region}, use_ssl={self.use_ssl}'
        )

        # --- 2. Cliente INTERNO (self.client) para uploads ---
        # Se conecta por la red privada de Railway, usa self.use_ssl (que debería ser False)
        self.client = boto3.client(
            's3',
            endpoint_url=self.endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=self.region,
            use_ssl=self.use_ssl, # Debería ser False (HTTP)
            config=Config(signature_version='s3v4')
        )
        
        # --- 3. Cliente PÚBLICO (self.public_client) para URLs firmadas ---
        if self.public_endpoint != self.endpoint:
            # Determinamos si el cliente público debe usar SSL basado en su URL
            # Esto corrige el problema de usar use_ssl=False para un endpoint HTTPS
            public_use_ssl = self.public_endpoint.lower().startswith('https')

            self.public_client = boto3.client(
                's3',
                endpoint_url=self.public_endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=self.region,
                use_ssl=public_use_ssl, # Forzamos True si la URL es HTTPS
                config=Config(signature_version='s3v4')
            )
        else:
            # Si el endpoint público y el interno son iguales, usamos el mismo cliente
            self.public_client = self.client

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

    @lru_cache(maxsize=128)
    def _generate_presigned_url_cached(self, key: str, expires_in: int) -> str:
        """
        Internal cached method to generate presigned URL.
        Uses functools.lru_cache for caching.
        Note: This method signature must be hashable for lru_cache to work.
        """
        from flask import current_app
        
        try:
            # Generate presigned URL using the public client
            url = self.public_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': key
                },
                ExpiresIn=expires_in,
                ResponseContentType='image/jpeg', 
                ResponseContentDisposition='inline'
            )
            
            # Track expiration time for cache invalidation
            expires_at = time.time() + expires_in
            self._url_expires[key] = expires_at
            
            current_app.logger.debug(
                f'🔗 S3Storage: Generated presigned URL for {key}, expires_in={expires_in}s'
            )
            return url
        except Exception as e:
            current_app.logger.error(
                f'❌ S3Storage: Error generating presigned URL for {key}: {e}',
                exc_info=True
            )
            raise

    def url_for(self, key: str, expires_in: int = 3600) -> str:
        """
        Generate a presigned URL for accessing the object.
        URLs are cached using functools.lru_cache to avoid regenerating them.
        
        Args:
            key: S3 key (path) of the object
            expires_in: URL expiration time in seconds (default: 1 hour)
        
        Returns:
            Presigned URL that allows temporary access to the object
        """
        from flask import current_app
        
        # Normalize key (remove leading slash)
        normalized_key = key.lstrip('/')
        
        # Check if cached URL is still valid (has more than 5 minutes left)
        current_time = time.time()
        if normalized_key in self._url_expires:
            expires_at = self._url_expires[normalized_key]
            if expires_at <= current_time + self._cache_refresh_threshold:
                # URL is expiring soon, clear cache entry to force regeneration
                # We need to clear the specific cache entry
                # Since lru_cache uses function arguments as keys, we can't easily clear
                # a specific entry, so we'll just let it regenerate naturally
                self._url_expires.pop(normalized_key, None)
                current_app.logger.debug(
                    f'🔄 S3Storage.url_for: Cached URL for {key} expiring soon, will regenerate'
                )
            else:
                # URL is still valid, lru_cache will return cached version
                current_app.logger.debug(
                    f'💾 S3Storage.url_for: Using cached URL for {key} '
                    f'(expires in {int(expires_at - current_time)}s)'
                )
        
        try:
            # This will use lru_cache if available, or generate new URL
            url = self._generate_presigned_url_cached(normalized_key, expires_in)
            return url
        except Exception as e:
            # Fallback to simple URL construction (may not work if bucket is private)
            endpoint_to_use = self.public_endpoint
            url = f"{endpoint_to_use.rstrip('/')}/{self.bucket}/{normalized_key}"
            current_app.logger.warning(f'⚠️ Falling back to simple URL: {url}')
            return url

