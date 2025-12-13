import os
import time
from collections import OrderedDict
import boto3
from botocore.client import Config
from app.storage.base import StorageProvider


class S3StorageProvider(StorageProvider):
    """S3-compatible storage (Railway Simple S3 / MinIO / AWS S3)."""

    def __init__(self, config):
        from flask import current_app
        import os
        
        # Debug: Log available environment variables (only keys, not values for security)
        s3_env_vars = {k: '***' if 'KEY' in k or 'SECRET' in k else v 
                      for k, v in os.environ.items() 
                      if any(x in k.upper() for x in ['BUCKET', 'ENDPOINT', 'REGION', 'ACCESS_KEY', 'SECRET_ACCESS', 'S3_'])}
        current_app.logger.info(f'🔍 Available S3-related env vars: {list(s3_env_vars.keys())}')
        
        # 1. Recuperación de Configuración
        # Leer directamente de variables de entorno si no están en config
        # Esto es necesario porque Railway puede no pasar todas las variables a Flask config
        self.bucket = config.get('BUCKET') or os.environ.get('BUCKET', '')
        current_app.logger.debug(f'📦 BUCKET from config: {config.get("BUCKET")}, from env: {os.environ.get("BUCKET", "NOT_SET")}, final: {self.bucket}')
        
        # Endpoint interno (Ej: http://storage.railway.internal:9000)
        self.endpoint = config.get('ENDPOINT') or os.environ.get('ENDPOINT', '')
        current_app.logger.debug(f'🌐 ENDPOINT from config: {config.get("ENDPOINT")}, from env: {os.environ.get("ENDPOINT", "NOT_SET")}, final: {self.endpoint}')
        
        # Endpoint público (Ej: https://storage-xxxx.up.railway.app)
        # Se asume que el usuario QUITARÁ el :443 manualmente en Railway
        public_endpoint_config = config.get('PUBLIC_ENDPOINT') or os.environ.get('S3_PUBLIC_ENDPOINT', '')
        self.public_endpoint = public_endpoint_config or self.endpoint
        
        # Railway S3 puede usar 'auto' o una región específica
        # Si no está configurada, usar 'auto' que es más compatible con Railway
        self.region = config.get('REGION') or os.environ.get('REGION', 'auto')
        access_key = config.get('ACCESS_KEY_ID') or os.environ.get('ACCESS_KEY_ID', '')
        secret_key = config.get('SECRET_ACCESS_KEY') or os.environ.get('SECRET_ACCESS_KEY', '')
        
        current_app.logger.debug(
            f'🔑 ACCESS_KEY_ID from config: {bool(config.get("ACCESS_KEY_ID"))}, '
            f'from env: {bool(os.environ.get("ACCESS_KEY_ID"))}, final: {bool(access_key)}'
        )
        
        # Validar que las variables requeridas estén presentes
        if not self.bucket:
            current_app.logger.error('❌ BUCKET not configured! Check environment variables BUCKET or S3_BUCKET')
            raise ValueError('BUCKET is required but not set. Please set BUCKET environment variable.')
        if not self.endpoint:
            current_app.logger.error('❌ ENDPOINT not configured! Check environment variables ENDPOINT or S3_ENDPOINT')
            raise ValueError('ENDPOINT is required but not set. Please set ENDPOINT environment variable.')
        if not access_key:
            current_app.logger.error('❌ ACCESS_KEY_ID not configured! Check environment variable ACCESS_KEY_ID')
            raise ValueError('ACCESS_KEY_ID is required but not set. Please set ACCESS_KEY_ID environment variable.')
        if not secret_key:
            current_app.logger.error('❌ SECRET_ACCESS_KEY not configured! Check environment variable SECRET_ACCESS_KEY')
            raise ValueError('SECRET_ACCESS_KEY is required but not set. Please set SECRET_ACCESS_KEY environment variable.')
        
        # La variable S3_USE_SSL está pensada para el cliente INTERNO
        # Si no está configurada, detectar automáticamente basado en el endpoint
        use_ssl_config = config.get('S3_USE_SSL')
        if use_ssl_config is None or use_ssl_config == '':
            # Auto-detect SSL based on endpoint protocol
            self.use_ssl = self.endpoint.lower().startswith('https')
        else:
            self.use_ssl = str(use_ssl_config).lower() in ('true', '1', 'yes')

        # Cache deshabilitado temporalmente para debugging
        # self._url_expires = {}
        # self._cache_refresh_threshold = 300  # 5 minutos antes de expirar, regenerar URL
        # self._presigned_cache = OrderedDict()
        # self._cache_max_size = 5000 

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
            config=Config(
                signature_version='s3v4',
                connect_timeout=30,  # 30 segundos timeout para conexión (aumentado)
                read_timeout=60,     # 60 segundos timeout para lectura (aumentado)
                retries={'max_attempts': 3}  # Máximo 3 intentos
            )
        )
        
        # --- 3. Cliente PÚBLICO (self.public_client) para URLs firmadas ---
        # IMPORTANTE: Para Railway S3, debemos usar el endpoint PÚBLICO para generar presigned URLs
        # porque las URLs presigned deben apuntar al endpoint público donde se accederán
        # Pero la firma se genera con las credenciales que funcionan en ambos endpoints
        if self.public_endpoint != self.endpoint:
            # Determinamos si el cliente público debe usar SSL basado en su URL
            public_use_ssl = self.public_endpoint.lower().startswith('https')

            self.public_client = boto3.client(
                's3',
                endpoint_url=self.public_endpoint,  # Usar endpoint público para presigned URLs
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=self.region,
                use_ssl=public_use_ssl,
                config=Config(
                    signature_version='s3v4',
                    connect_timeout=30,
                    read_timeout=60,
                    retries={'max_attempts': 1},
                    # Forzar que use el endpoint público en la URL generada
                    s3={
                        'addressing_style': 'path'  # Usar path-style URLs
                    }
                )
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

    def _generate_presigned_url_cached(self, key: str, expires_in: int) -> str:
        """
        Generate presigned URL without cache (for debugging).
        """
        from flask import current_app
        
        try:
            # Generate presigned URL using the public client
            # Note: generate_presigned_url does NOT make a network call, it only signs locally
            current_app.logger.debug(
                f'🔗 S3Storage: Generating presigned URL for key={key}, '
                f'bucket={self.bucket}, endpoint={self.public_endpoint}, '
                f'expires_in={expires_in}s'
            )
            
            # Log configuration before generating URL
            current_app.logger.debug(
                f'🔧 S3Storage: Generating presigned URL with config: '
                f'bucket={self.bucket}, endpoint={self.public_endpoint}, '
                f'region={self.region}, expires_in={expires_in}'
            )
            
            # Generate presigned URL (this is a local operation, no network call)
            url = self.public_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': key,
                    'ResponseContentType': 'image/jpeg',
                    'ResponseContentDisposition': 'inline'
                },
                ExpiresIn=expires_in
            )
            
            if not url:
                raise ValueError(f'Failed to generate presigned URL for {key} (returned None)')
            
            # Log generated URL (first 200 chars for debugging)
            current_app.logger.info(
                f'✅ S3Storage: Generated presigned URL for {key}, '
                f'expires_in={expires_in}s, url_length={len(url)}, '
                f'url_preview={url[:200]}...'
            )
            
            return url
        except Exception as e:
            current_app.logger.error(
                f'❌ S3Storage: Error generating presigned URL for {key}: {e}',
                exc_info=True
            )
            raise

    def url_for(self, key: str, expires_in: int = 604800) -> str:
        """
        Generate a presigned URL for accessing the object.
        Railway S3 requires presigned URLs (buckets are private by default).
        
        Args:
            key: S3 key (path) of the object
            expires_in: URL expiration time in seconds (default: 7 days = 604800 seconds)
        
        Returns:
            Presigned URL that allows temporary access to the object
        """
        from flask import current_app
        
        # Normalize key (remove leading slash)
        normalized_key = key.lstrip('/')
        
        try:
            # Generate presigned URL using cached method
            # Railway S3 requires presigned URLs - buckets are always private
            url = self._generate_presigned_url_cached(normalized_key, expires_in)
            current_app.logger.debug(f'✅ S3Storage.url_for: Generated presigned URL for {key}')
            return url
        except Exception as e:
            current_app.logger.error(
                f'❌ S3Storage.url_for: Error generating presigned URL for {key}: {e}',
                exc_info=True
            )
            # Fallback: try to construct a simple URL (won't work if bucket is private)
            endpoint_to_use = self.public_endpoint.rstrip('/')
            if not endpoint_to_use.startswith('http://') and not endpoint_to_use.startswith('https://'):
                endpoint_to_use = f"https://{endpoint_to_use}"
            url = f"{endpoint_to_use}/{self.bucket}/{normalized_key}"
            current_app.logger.warning(f'⚠️ Falling back to simple URL (may not work): {url}')
            return url

