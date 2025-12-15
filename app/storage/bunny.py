import os
import requests
from app.storage.base import StorageProvider


class BunnyStorageProvider(StorageProvider):
    """BunnyCDN storage provider."""

    def __init__(self, config):
        from flask import current_app
        
        # Debug: Log available environment variables
        bunny_env_vars = {k: '***' if 'KEY' in k or 'PASSWORD' in k else v 
                         for k, v in os.environ.items() 
                         if any(x in k.upper() for x in ['BUNNY', 'CDN'])}
        current_app.logger.info(f'🔍 Available BunnyCDN-related env vars: {list(bunny_env_vars.keys())}')
        
        # Recuperación de Configuración
        self.storage_zone = config.get('BUNNY_STORAGE_ZONE') or os.environ.get('BUNNY_STORAGE_ZONE', '')
        current_app.logger.debug(
            f'📦 BUNNY_STORAGE_ZONE from config: {config.get("BUNNY_STORAGE_ZONE")}, '
            f'from env: {os.environ.get("BUNNY_STORAGE_ZONE", "NOT_SET")}, '
            f'final: {self.storage_zone}'
        )
        
        self.storage_api_key = config.get('BUNNY_STORAGE_API_KEY') or os.environ.get('BUNNY_STORAGE_API_KEY', '')
        current_app.logger.debug(
            f'🔑 BUNNY_STORAGE_API_KEY from config: {bool(config.get("BUNNY_STORAGE_API_KEY"))}, '
            f'from env: {bool(os.environ.get("BUNNY_STORAGE_API_KEY"))}, '
            f'final: {bool(self.storage_api_key)}'
        )
        
        # Pull Zone (CDN) - Para generar las URLs públicas
        self.pull_zone = config.get('BUNNY_PULL_ZONE') or os.environ.get('BUNNY_PULL_ZONE', '')
        current_app.logger.debug(
            f'🌐 BUNNY_PULL_ZONE from config: {config.get("BUNNY_PULL_ZONE")}, '
            f'from env: {os.environ.get("BUNNY_PULL_ZONE", "NOT_SET")}, '
            f'final: {self.pull_zone}'
        )
        
        # Región del storage (opcional, por defecto usa el endpoint principal)
        # Regiones disponibles: de (Falkenstein), ny (New York), la (Los Angeles), 
        # sg (Singapore), syd (Sydney), uk (London), se (Stockholm), br (São Paulo)
        self.storage_region = config.get('BUNNY_STORAGE_REGION') or os.environ.get('BUNNY_STORAGE_REGION', '')
        
        # Construir endpoint del Storage API
        if self.storage_region:
            self.storage_endpoint = f'https://{self.storage_region}.storage.bunnycdn.com/{self.storage_zone}'
        else:
            self.storage_endpoint = f'https://storage.bunnycdn.com/{self.storage_zone}'
        
        # Validar variables requeridas
        if not self.storage_zone:
            current_app.logger.error('❌ BUNNY_STORAGE_ZONE not configured!')
            raise ValueError('BUNNY_STORAGE_ZONE is required. Please set BUNNY_STORAGE_ZONE environment variable.')
        
        if not self.storage_api_key:
            current_app.logger.error('❌ BUNNY_STORAGE_API_KEY not configured!')
            raise ValueError('BUNNY_STORAGE_API_KEY is required. Please set BUNNY_STORAGE_API_KEY environment variable.')
        
        if not self.pull_zone:
            current_app.logger.error('❌ BUNNY_PULL_ZONE not configured!')
            raise ValueError('BUNNY_PULL_ZONE is required. Please set BUNNY_PULL_ZONE environment variable.')
        
        # Session para reutilizar conexiones HTTP
        self.session = requests.Session()
        self.session.headers.update({
            'AccessKey': self.storage_api_key,
        })
        
        current_app.logger.info(
            f'🔧 BunnyStorageProvider initialized: '
            f'storage_zone={self.storage_zone}, '
            f'pull_zone={self.pull_zone}, '
            f'endpoint={self.storage_endpoint}'
        )

    def save(self, key: str, file_path: str, delete_after_upload: bool = False) -> str:
        """
        Save file to BunnyCDN Storage.
        
        Args:
            key: Storage path where to store the file (e.g., 'images/user123/photo.jpg')
            file_path: Local path to the file to upload
            delete_after_upload: If True, delete local file after successful upload
        
        Returns:
            The key where the file was stored
        """
        from flask import current_app
        
        # Normalize key (remove leading slash)
        normalized_key = key.lstrip('/')
        
        current_app.logger.info(
            f'☁️ BunnyStorage.save: key={normalized_key}, file_path={file_path}, '
            f'file_exists={os.path.exists(file_path) if file_path else False}, '
            f'delete_after_upload={delete_after_upload}'
        )
        
        if not os.path.exists(file_path):
            current_app.logger.error(f'❌ BunnyStorage.save: File not found: {file_path}')
            raise FileNotFoundError(f'File not found: {file_path}')
        
        try:
            # Construir URL del Storage API
            upload_url = f'{self.storage_endpoint}/{normalized_key}'
            
            current_app.logger.debug(f'📤 BunnyStorage: Uploading to {upload_url}')
            
            # Detectar Content-Type basado en extensión
            import mimetypes
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = 'application/octet-stream'
            
            # Leer archivo
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Upload a BunnyCDN Storage usando PUT
            response = self.session.put(
                upload_url,
                data=file_data,
                headers={'Content-Type': content_type},
                timeout=60
            )
            
            if response.status_code == 201:
                current_app.logger.info(
                    f'✅ BunnyStorage: Successfully uploaded {normalized_key} '
                    f'to {self.storage_zone}/{normalized_key}'
                )
                
                # Delete local file after successful upload if requested
                if delete_after_upload:
                    try:
                        os.remove(file_path)
                        current_app.logger.info(
                            f'🗑️ BunnyStorage: Deleted local file after upload: {file_path}'
                        )
                    except Exception as e:
                        current_app.logger.warning(
                            f'⚠️ BunnyStorage: Could not delete local file {file_path}: {e}'
                        )
            else:
                error_msg = f'Upload failed with status {response.status_code}: {response.text}'
                current_app.logger.error(f'❌ BunnyStorage.save: {error_msg}')
                raise Exception(error_msg)
                
        except requests.exceptions.RequestException as e:
            current_app.logger.error(
                f'❌ BunnyStorage.save: Network error uploading {normalized_key}: {str(e)}',
                exc_info=True
            )
            raise
        except Exception as e:
            current_app.logger.error(
                f'❌ BunnyStorage.save: Error uploading {normalized_key}: {str(e)}',
                exc_info=True
            )
            raise
        
        return normalized_key

    def url_for(self, key: str, expires_in: int = 604800) -> str:
        """
        Generate a public CDN URL for accessing the object.
        
        BunnyCDN URLs are públicas por defecto (no necesitan presigned URLs).
        El parámetro expires_in se mantiene por compatibilidad pero no se usa.
        
        Args:
            key: Storage path of the object (e.g., 'images/user123/photo.jpg')
            expires_in: Ignored (kept for API compatibility)
        
        Returns:
            Public CDN URL (e.g., 'https://your-pull-zone.b-cdn.net/images/user123/photo.jpg')
        """
        from flask import current_app
        
        # Normalize key (remove leading slash)
        normalized_key = key.lstrip('/')
        
        # Normalizar pull zone (puede venir con o sin protocolo)
        pull_zone = (self.pull_zone or '').strip()
        # Aceptar tanto 'tarracograf-cat.b-cdn.net' como 'https://tarracograf-cat.b-cdn.net'
        if pull_zone.startswith('https://'):
            pull_zone = pull_zone[len('https://') :]
        elif pull_zone.startswith('http://'):
            pull_zone = pull_zone[len('http://') :]
        pull_zone = pull_zone.rstrip('/')  # quitar slash final si lo hay
        # Si el usuario ha puesto solo el nombre corto de la zona (ej: 'tarracograf-cat'),
        # añadir el sufijo por defecto de BunnyCDN (.b-cdn.net)
        if pull_zone and '.' not in pull_zone:
            pull_zone = f'{pull_zone}.b-cdn.net'
        
        # Construir URL pública del CDN
        # BunnyCDN URLs son públicas por defecto, no necesitan firma
        cdn_url = f'https://{pull_zone}/{normalized_key}'
        
        current_app.logger.debug(f'🔗 BunnyStorage.url_for: Generated CDN URL for {normalized_key}')
        current_app.logger.debug(f'🔗 Full CDN URL: {cdn_url}')
        
        return cdn_url
    
    def url_for_resized(self, key: str, width: int = None, height: int = None, 
                       quality: int = None, format: str = None, **kwargs) -> str:
        """
        Generate a CDN URL with BunnyCDN Optimizer transformations.
        
        Requiere que BunnyCDN Optimizer esté activado en tu Pull Zone.
        
        Args:
            key: Storage path of the object
            width: Width in pixels
            height: Height in pixels
            quality: JPEG/WebP quality (1-100)
            format: Output format ('webp', 'jpg', 'png', etc.)
            **kwargs: Additional optimizer params (crop, aspect_ratio, blur, etc.)
        
        Returns:
            CDN URL with transformation parameters
        
        Examples:
            url_for_resized('images/photo.jpg', width=400)
            # https://your-pull-zone.b-cdn.net/images/photo.jpg?width=400
            
            url_for_resized('images/photo.jpg', width=400, height=300, format='webp')
            # https://your-pull-zone.b-cdn.net/images/photo.jpg?width=400&height=300&format=webp
        """
        from flask import current_app
        
        # Obtener URL base
        base_url = self.url_for(key)
        
        # Construir parámetros de transformación
        params = []
        
        if width:
            params.append(f'width={width}')
        if height:
            params.append(f'height={height}')
        if quality:
            params.append(f'quality={quality}')
        if format:
            params.append(f'format={format}')
        
        # Parámetros adicionales
        for param_key, param_value in kwargs.items():
            params.append(f'{param_key}={param_value}')
        
        if params:
            transformed_url = f"{base_url}?{'&'.join(params)}"
        else:
            transformed_url = base_url
        
        current_app.logger.debug(
            f'🎨 BunnyStorage.url_for_resized: Generated transformed URL with params: {params}'
        )
        
        return transformed_url
    
    def delete(self, key: str) -> bool:
        """
        Delete file from BunnyCDN Storage.
        
        Args:
            key: Storage path of the file to delete
        
        Returns:
            True if deletion was successful, False otherwise
        """
        from flask import current_app
        
        # Normalize key
        normalized_key = key.lstrip('/')
        
        current_app.logger.info(f'🗑️ BunnyStorage.delete: Deleting {normalized_key}')
        
        try:
            delete_url = f'{self.storage_endpoint}/{normalized_key}'
            
            response = self.session.delete(delete_url, timeout=30)
            
            if response.status_code == 200:
                current_app.logger.info(f'✅ BunnyStorage: Successfully deleted {normalized_key}')
                return True
            else:
                current_app.logger.error(
                    f'❌ BunnyStorage.delete: Failed with status {response.status_code}: {response.text}'
                )
                return False
                
        except Exception as e:
            current_app.logger.error(
                f'❌ BunnyStorage.delete: Error deleting {normalized_key}: {str(e)}',
                exc_info=True
            )
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if a file exists in BunnyCDN Storage.
        
        Args:
            key: Storage path to check
        
        Returns:
            True if file exists, False otherwise
        """
        from flask import current_app
        
        # Normalize key
        normalized_key = key.lstrip('/')
        
        try:
            # BunnyCDN no tiene un HEAD directo, usamos GET con rango 0-0
            check_url = f'{self.storage_endpoint}/{normalized_key}'
            
            response = self.session.get(
                check_url,
                headers={'Range': 'bytes=0-0'},
                timeout=10
            )
            
            exists = response.status_code in [200, 206]
            
            current_app.logger.debug(
                f'🔍 BunnyStorage.exists: {normalized_key} exists={exists}'
            )
            
            return exists
            
        except Exception as e:
            current_app.logger.error(
                f'❌ BunnyStorage.exists: Error checking {normalized_key}: {str(e)}'
            )
            return False
    

