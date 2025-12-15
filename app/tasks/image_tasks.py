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
            # Note: BunnyCDN files are not processed by worker - they use CDN URLs directly
            storage_provider = current_app.config.get('STORAGE_PROVIDER', 'local').lower()
            if not os.path.exists(original_path):
                if storage_provider == 'bunny':
                    # BunnyCDN: Files are served directly from CDN, no worker processing needed
                    current_app.logger.warning(
                        f'⚠️ Image file not found locally for BunnyCDN: {original_path}. '
                        f'BunnyCDN files should be processed synchronously in the web service, not in worker.'
                    )
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
            # For local, keep files (they're already in the right place)
            storage_provider = current_app.config.get('STORAGE_PROVIDER', 'local').lower()
            delete_after = False
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

