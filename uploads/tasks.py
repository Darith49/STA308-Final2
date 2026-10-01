import logging
from services.importers import run_import_pipeline

logger = logging.getLogger(__name__)

try:
    from celery import shared_task
    @shared_task(bind=True)
    def process_upload_task(self, upload_id):
        logger.info(f"Processing upload {upload_id} asynchronously via Celery...")
        return run_import_pipeline(upload_id)
except ImportError:
    def process_upload_task(upload_id):
        logger.info(f"Processing upload {upload_id} synchronously...")
        return run_import_pipeline(upload_id)
