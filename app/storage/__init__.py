from flask import current_app

from app.storage.local import LocalStorageProvider
from app.storage.s3 import S3StorageProvider


def get_storage():
    """Return storage provider based on configuration."""
    provider = current_app.config.get('STORAGE_PROVIDER', 'local').lower()
    current_app.logger.info(f'📦 Storage provider requested: {provider}')
    
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
        return S3StorageProvider(current_app.config)
    
    current_app.logger.info('📁 Using LocalStorageProvider')
    return LocalStorageProvider(current_app.config)

