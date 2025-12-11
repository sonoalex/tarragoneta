from flask import current_app

from app.storage.local import LocalStorageProvider
from app.storage.s3 import S3StorageProvider

# Key for storing storage provider in Flask app extensions
_STORAGE_EXTENSION_KEY = 'storage_provider'


def get_storage():
    """
    Return storage provider based on configuration (singleton per app).
    The provider is cached in current_app.extensions to avoid recreating it.
    """
    # Check if we already have a cached instance
    if _STORAGE_EXTENSION_KEY in current_app.extensions:
        return current_app.extensions[_STORAGE_EXTENSION_KEY]
    
    # Create new instance (only once per app)
    provider = current_app.config.get('STORAGE_PROVIDER', 'local').lower()
    current_app.logger.info(f'📦 Storage provider requested: {provider} (creating new instance)')
    
    if provider == 's3':
        s3_config = {
            'S3_BUCKET': current_app.config.get('S3_BUCKET'),
            'S3_ENDPOINT': current_app.config.get('S3_ENDPOINT'),
            'S3_PUBLIC_ENDPOINT': current_app.config.get('S3_PUBLIC_ENDPOINT') or 'not set (using S3_ENDPOINT)',
            'S3_REGION': current_app.config.get('S3_REGION'),
            'S3_USE_SSL': current_app.config.get('S3_USE_SSL'),
            'S3_ACCESS_KEY_ID': '***' if current_app.config.get('S3_ACCESS_KEY_ID') else None,
            'S3_SECRET_ACCESS_KEY': '***' if current_app.config.get('S3_SECRET_ACCESS_KEY') else None,
        }
        current_app.logger.info(f'🔧 S3 config: {s3_config}')
        storage_instance = S3StorageProvider(current_app.config)
    else:
        current_app.logger.info('📁 Using LocalStorageProvider')
        storage_instance = LocalStorageProvider(current_app.config)
    
    # Cache the instance in app extensions (singleton)
    current_app.extensions[_STORAGE_EXTENSION_KEY] = storage_instance
    current_app.logger.debug(f'✅ Storage provider cached in app extensions')
    
    return storage_instance

