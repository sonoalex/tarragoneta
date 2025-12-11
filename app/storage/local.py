import os
from flask import url_for, current_app

from app.storage.base import StorageProvider


class LocalStorageProvider(StorageProvider):
    """Store files on local filesystem (static/uploads)."""

    def __init__(self, config):
        self.upload_folder = config.get('UPLOAD_FOLDER', 'static/uploads')
        os.makedirs(self.upload_folder, exist_ok=True)

    def save(self, key: str, file_path: str) -> str:
        # key is typically the filename; store inside upload_folder
        from flask import current_app
        current_app.logger.info(f'💾 LocalStorage.save: key={key}, file_path={file_path}')
        dest_path = os.path.join(self.upload_folder, key)
        # Ensure directory exists
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        if os.path.abspath(file_path) != os.path.abspath(dest_path):
            # Copy
            import shutil
            shutil.copyfile(file_path, dest_path)
            current_app.logger.info(f'✅ LocalStorage: Copied {file_path} to {dest_path}')
        else:
            current_app.logger.info(f'ℹ️ LocalStorage: File already at destination {dest_path}')
        return key

    def url_for(self, key: str) -> str:
        # Build url_for static
        # Strip any leading slashes
        from flask import current_app
        rel_path = key.lstrip('/')
        url = url_for('static', filename=f'uploads/{rel_path}', _external=False)
        current_app.logger.debug(f'🔗 LocalStorage.url_for: key={key} -> {url}')
        return url

