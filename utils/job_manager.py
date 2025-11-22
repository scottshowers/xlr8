"""
Background Job Manager for XLR8
Handles async document processing without blocking UI

Architecture:
- Jobs stored in Supabase (processing_jobs table)
- Python threading for background execution
- Real-time progress updates
- Graceful failure handling
"""

import threading
import queue
import time
import uuid
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)


class JobManager:
    """
    Manages background job processing
    
    Singleton pattern - one worker thread processes jobs from queue
    """
    
    _instance = None
    _worker_thread = None
    _job_queue = None
    _is_running = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._job_queue = queue.Queue()
            cls._is_running = True
            cls._start_worker()
        return cls._instance
    
    @classmethod
    def _start_worker(cls):
        """Start background worker thread"""
        if cls._worker_thread is None or not cls._worker_thread.is_alive():
            cls._worker_thread = threading.Thread(
                target=cls._worker_loop,
                daemon=True,
                name="XLR8-JobWorker"
            )
            cls._worker_thread.start()
            logger.info("Background job worker started")
    
    @classmethod
    def _worker_loop(cls):
        """Main worker loop - processes jobs from queue"""
        logger.info("Worker loop started")
        
        while cls._is_running:
            try:
                # Get job from queue (blocks up to 1 second)
                try:
                    job_data = cls._job_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                logger.info(f"Worker picked up job: {job_data.get('job_id')}")
                
                # Process the job
                cls._process_job(job_data)
                
                # Mark as done
                cls._job_queue.task_done()
                
            except Exception as e:
                logger.error(f"Worker error: {e}", exc_info=True)
                time.sleep(1)  # Brief pause on error
        
        logger.info("Worker loop stopped")
    
    @classmethod
    def _process_job(cls, job_data: Dict[str, Any]):
        """
        Process a single job
        
        Args:
            job_data: {
                'job_id': str,
                'job_type': str,
                'handler': callable,
                'input_data': dict,
                'supabase_client': Client
            }
        """
        job_id = job_data['job_id']
        job_type = job_data['job_type']
        handler = job_data['handler']
        input_data = job_data['input_data']
        supabase = job_data.get('supabase_client')
        
        logger.info(f"[JOB {job_id}] Starting {job_type}")
        
        # Update status to processing
        if supabase:
            try:
                supabase.table('processing_jobs').update({
                    'status': 'processing',
                    'started_at': datetime.utcnow().isoformat(),
                    'progress': {'current': 0, 'total': 100, 'message': 'Starting...'}
                }).eq('id', job_id).execute()
            except Exception as e:
                logger.error(f"Failed to update job status: {e}")
        
        # Progress callback for real-time updates
        def progress_callback(current: int, total: int, message: str):
            if supabase:
                try:
                    supabase.table('processing_jobs').update({
                        'progress': {
                            'current': current,
                            'total': total,
                            'message': message
                        }
                    }).eq('id', job_id).execute()
                    logger.debug(f"[JOB {job_id}] Progress: {current}/{total} - {message}")
                except Exception as e:
                    logger.error(f"Failed to update progress: {e}")
        
        try:
            # Execute the handler with progress callback
            result = handler(input_data, progress_callback)
            
            # Mark as completed
            if supabase:
                supabase.table('processing_jobs').update({
                    'status': 'completed',
                    'completed_at': datetime.utcnow().isoformat(),
                    'result_data': result,
                    'progress': {'current': 100, 'total': 100, 'message': 'Complete!'}
                }).eq('id', job_id).execute()
            
            logger.info(f"[JOB {job_id}] Completed successfully")
        
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            
            logger.error(f"[JOB {job_id}] Failed: {error_msg}", exc_info=True)
            
            # Mark as failed
            if supabase:
                try:
                    supabase.table('processing_jobs').update({
                        'status': 'failed',
                        'completed_at': datetime.utcnow().isoformat(),
                        'error_message': f"{error_msg}\n\n{error_trace}",
                        'progress': {'current': 0, 'total': 100, 'message': f'Error: {error_msg}'}
                    }).eq('id', job_id).execute()
                except Exception as update_error:
                    logger.error(f"Failed to update error status: {update_error}")
    
    def submit_job(
        self,
        job_type: str,
        handler: Callable,
        input_data: Dict[str, Any],
        project_id: Optional[str] = None,
        user_id: Optional[str] = None,
        supabase_client = None
    ) -> str:
        """
        Submit a job for background processing
        
        Args:
            job_type: Type of job ('document_upload', 'excel_generation', etc.)
            handler: Function to execute - must accept (input_data, progress_callback)
            input_data: Data to pass to handler
            project_id: Associated project
            user_id: User who submitted job
            supabase_client: Supabase client for progress updates
            
        Returns:
            job_id: UUID of created job
            
        Example:
            def process_document(input_data, progress_callback):
                progress_callback(0, 100, "Starting...")
                # ... do work ...
                progress_callback(100, 100, "Done!")
                return {'chunks_added': 42}
            
            job_id = job_manager.submit_job(
                job_type='document_upload',
                handler=process_document,
                input_data={'file': 'data.xlsx'},
                project_id='project-123'
            )
        """
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        logger.info(f"[JOB {job_id}] Submitting {job_type}")
        
        # Create job record in Supabase
        if supabase_client:
            try:
                supabase_client.table('processing_jobs').insert({
                    'id': job_id,
                    'job_type': job_type,
                    'status': 'queued',
                    'input_data': input_data,
                    'project_id': project_id,
                    'user_id': user_id,
                    'progress': {'current': 0, 'total': 100, 'message': 'Queued'}
                }).execute()
                
                logger.info(f"[JOB {job_id}] Created in database")
            except Exception as e:
                logger.error(f"Failed to create job in database: {e}")
                raise
        
        # Add to processing queue
        self._job_queue.put({
            'job_id': job_id,
            'job_type': job_type,
            'handler': handler,
            'input_data': input_data,
            'supabase_client': supabase_client
        })
        
        logger.info(f"[JOB {job_id}] Queued for processing (queue size: {self._job_queue.qsize()})")
        
        return job_id
    
    def get_job_status(self, job_id: str, supabase_client) -> Optional[Dict[str, Any]]:
        """
        Get current status of a job
        
        Args:
            job_id: Job UUID
            supabase_client: Supabase client
            
        Returns:
            Job data or None
        """
        try:
            result = supabase_client.table('processing_jobs').select('*').eq('id', job_id).execute()
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            return None
    
    @classmethod
    def shutdown(cls):
        """Gracefully shutdown worker (for testing/cleanup)"""
        cls._is_running = False
        if cls._worker_thread:
            cls._worker_thread.join(timeout=5)
        logger.info("Job manager shutdown complete")


# Singleton instance
_job_manager = None


def get_job_manager() -> JobManager:
    """Get singleton JobManager instance"""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager
