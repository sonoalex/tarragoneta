"""
Celery tasks for image processing
"""
from flask import current_app


def init_image_tasks(celery_app):
    """Initialize Celery tasks for image processing"""
    
    @celery_app.task(name='resize_image_task', bind=True, max_retries=3)
    def resize_image_task(self, item_id, image_filename):
        """
        Celery task to resize an uploaded image into multiple sizes
        
        Args:
            item_id: ID of the InventoryItem
            image_filename: Original image filename
        """
        current_app.logger.info(
            f'🚀 resize_image_task STARTED: item_id={item_id}, image_filename={image_filename}, '
            f'task_id={self.request.id if hasattr(self.request, "id") else "N/A"}'
        )
        try:
            from app.utils import generate_image_sizes
            from app.extensions import db
            from app.models import InventoryItem
            from app.storage import get_storage
            import os
            
            # Get upload folder path
            upload_folder = current_app.config['UPLOAD_FOLDER']
            original_path = os.path.join(upload_folder, image_filename)
            
            # Check if file exists locally
            # If not, and we're using S3, download it from S3 first
            storage_provider = current_app.config.get('STORAGE_PROVIDER', 'local').lower()
            if not os.path.exists(original_path):
                if storage_provider == 's3':
                    current_app.logger.info(f'📥 File not found locally, downloading from S3: {image_filename}')
                    try:
                        from app.storage import get_storage
                        storage = get_storage()
                        # Download from S3
                        if hasattr(storage, 'client') and hasattr(storage, 'bucket'):
                            # Ensure directory exists
                            os.makedirs(upload_folder, exist_ok=True)
                            # Download file from S3
                            storage.client.download_file(storage.bucket, image_filename, original_path)
                            current_app.logger.info(f'✅ Downloaded file from S3: {original_path}')
                        else:
                            current_app.logger.error(f'Storage provider does not support download: {type(storage)}')
                            return False
                    except Exception as e:
                        current_app.logger.error(f'❌ Error downloading file from S3: {e}', exc_info=True)
                        return False
                else:
                    current_app.logger.error(f'Image file not found: {original_path}')
                    return False
            
            # Generate image sizes
            current_app.logger.info(f'🖼️ Generating image sizes for item {item_id}: {image_filename}')
            image_sizes = generate_image_sizes(original_path, image_filename)
            storage = get_storage()
            
            # Update item with the large version as main image_path
            item = InventoryItem.query.get(item_id)
            if not item:
                current_app.logger.error(f'InventoryItem {item_id} not found')
                return False
            
            # Use the 'large' version as the main image_path
            main_image_filename = image_sizes.get('large', image_filename)
            item.image_path = main_image_filename
            
            db.session.commit()

            # Upload all generated files to storage
            # For S3, delete local files after upload (handled by storage provider)
            # For local, keep files (they're already in the right place)
            storage_provider = current_app.config.get('STORAGE_PROVIDER', 'local').lower()
            delete_after = (storage_provider == 's3')
            current_app.logger.info(
                f'📤 Uploading {len(image_sizes)} image sizes to storage '
                f'(provider={storage_provider}, delete_after_upload={delete_after})'
            )
            
            for size_name, fname in image_sizes.items():
                if not fname:
                    continue
                path = os.path.join(upload_folder, fname)
                if os.path.exists(path):
                    try:
                        current_app.logger.info(f'  📤 Uploading {size_name}: {fname}')
                        storage.save(fname, path, delete_after_upload=delete_after)
                        current_app.logger.info(f'  ✅ Uploaded {size_name}: {fname}')
                    except Exception as e:
                        current_app.logger.error(f'  ❌ Error uploading {size_name} {fname}: {e}', exc_info=True)
            
            # Also delete the original file if it still exists (downloaded from S3)
            if storage_provider == 's3' and os.path.exists(original_path):
                try:
                    os.remove(original_path)
                    current_app.logger.info(f'🗑️ Deleted original file after processing: {original_path}')
                except Exception as e:
                    current_app.logger.warning(f'⚠️ Could not delete original file {original_path}: {e}')
            
            current_app.logger.info(
                f'✅ Image sizes generated for item {item_id}: '
                f'thumbnail={image_sizes.get("thumbnail")}, '
                f'medium={image_sizes.get("medium")}, '
                f'large={main_image_filename}'
            )
            
            return True
            
        except Exception as exc:
            current_app.logger.error(
                f'Error resizing image for item {item_id}: {str(exc)}', 
                exc_info=True
            )
            # Retry with exponential backoff
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
    
    # Return the task so it can be stored in app
    return resize_image_task

