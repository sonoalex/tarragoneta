from flask import current_app

from app.storage.local import LocalStorageProvider
from app.storage.s3 import S3StorageProvider


def get_storage():
    """Return storage provider based on configuration."""
    provider = current_app.config.get('STORAGE_PROVIDER', 'local').lower()
    if provider == 's3':
        return S3StorageProvider(current_app.config)
    return LocalStorageProvider(current_app.config)

