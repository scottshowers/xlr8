"""
Background job processing for XLR8
Handles async document uploads and other long-running tasks
"""

from .job_manager import get_job_manager, JobManager
from .document_handler import process_document_upload

__all__ = ['get_job_manager', 'JobManager', 'process_document_upload']
