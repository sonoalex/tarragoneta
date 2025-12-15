from flask import current_app

from app.storage.local import LocalStorageProvider
from app.storage.bunny import BunnyStorageProvider

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
    
    if provider == 'bunny':
        bunny_config = {
            'BUNNY_STORAGE_ZONE': current_app.config.get('BUNNY_STORAGE_ZONE'),
            'BUNNY_STORAGE_API_KEY': '***' if current_app.config.get('BUNNY_STORAGE_API_KEY') else None,
            'BUNNY_PULL_ZONE': current_app.config.get('BUNNY_PULL_ZONE'),
            'BUNNY_STORAGE_REGION': current_app.config.get('BUNNY_STORAGE_REGION'),
        }
        current_app.logger.info(f'🔧 BunnyCDN config: {bunny_config}')
        storage_instance = BunnyStorageProvider(current_app.config)
    else:
        current_app.logger.info('📁 Using LocalStorageProvider')
        storage_instance = LocalStorageProvider(current_app.config)
    
    # Cache the instance in app extensions (singleton)
    current_app.extensions[_STORAGE_EXTENSION_KEY] = storage_instance
    current_app.logger.debug(f'✅ Storage provider cached in app extensions')
    
    return storage_instance

