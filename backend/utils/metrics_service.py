"""
Metrics Service - Platform Analytics Tracking
==============================================

Tracks processing times, success rates, LLM usage, and throughput
for product management dashboards and exit due diligence.

Deploy to: backend/utils/metrics_service.py

Usage:
    from utils.metrics_service import MetricsService
    
    # Record an upload
    MetricsService.record_upload(
        processor='register',
        project_id='xxx',
        filename='payroll.pdf',
        file_size_bytes=1024000,
        duration_ms=9400,
        success=True,
        rows_processed=150,
        chunks_created=0
    )
    
    # Record an LLM call
    MetricsService.record_llm_call(
        processor='register',
        provider='groq',
        model='llama-3.3-70b-versatile',
        tokens_in=1500,
        tokens_out=800,
        duration_ms=1200,
        cost_usd=0.0
    )
"""

import logging
from datetime import datetime
from typing import Optional
from decimal import Decimal

logger = logging.getLogger(__name__)

# Try to import Supabase
try:
    from utils.database.supabase_client import get_supabase
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("[METRICS] Supabase not available - metrics will not be persisted")


class MetricsService:
    """
    Centralized metrics tracking for XLR8 platform.
    
    All methods are static for easy use throughout the codebase.
    Failures are logged but never raise - metrics should not break processing.
    """
    
    TABLE_NAME = 'platform_metrics'
    
    @staticmethod
    def _get_client():
        """Get Supabase client, return None if unavailable."""
        if not SUPABASE_AVAILABLE:
            return None
        try:
            return get_supabase()
        except Exception as e:
            logger.warning(f"[METRICS] Could not get Supabase client: {e}")
            return None
    
    @staticmethod
    def record_upload(
        processor: str,
        filename: str,
        duration_ms: int,
        success: bool,
        project_id: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
        error_message: Optional[str] = None,
        rows_processed: Optional[int] = None,
        chunks_created: Optional[int] = None,
        rules_extracted: Optional[int] = None
    ) -> bool:
        """
        Record a file upload/processing event.
        
        Args:
            processor: 'register', 'standards', 'structured', 'semantic'
            filename: Name of the file processed
            duration_ms: Total processing time in milliseconds
            success: Whether processing succeeded
            project_id: Optional project UUID
            file_size_bytes: File size in bytes
            error_message: Error details if failed
            rows_processed: Number of data rows processed
            chunks_created: Number of ChromaDB chunks created
            rules_extracted: Number of rules extracted (standards)
        """
        try:
            client = MetricsService._get_client()
            if not client:
                logger.debug(f"[METRICS] Upload metric not persisted (no client): {processor}/{filename}")
                return False
            
            record = {
                'metric_type': 'upload',
                'processor': processor,
                'filename': filename,
                'duration_ms': duration_ms,
                'success': success,
                'project_id': project_id,
                'file_size_bytes': file_size_bytes,
                'error_message': error_message,
                'rows_processed': rows_processed,
                'chunks_created': chunks_created,
                'rules_extracted': rules_extracted
            }
            
            # Remove None values
            record = {k: v for k, v in record.items() if v is not None}
            
            client.table(MetricsService.TABLE_NAME).insert(record).execute()
            logger.info(f"[METRICS] Recorded upload: {processor}/{filename} in {duration_ms}ms (success={success})")
            return True
            
        except Exception as e:
            logger.warning(f"[METRICS] Failed to record upload metric: {e}")
            return False
    
    @staticmethod
    def record_llm_call(
        processor: str,
        provider: str,
        model: str,
        duration_ms: int,
        tokens_in: Optional[int] = None,
        tokens_out: Optional[int] = None,
        cost_usd: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> bool:
        """
        Record an LLM API call.
        
        Args:
            processor: Which processor made the call
            provider: 'groq', 'claude', 'deepseek', 'ollama'
            model: Model name/ID
            duration_ms: Call duration in milliseconds
            tokens_in: Input tokens
            tokens_out: Output tokens
            cost_usd: Estimated cost in USD
            success: Whether call succeeded
            error_message: Error details if failed
            project_id: Optional project UUID
        """
        try:
            client = MetricsService._get_client()
            if not client:
                logger.debug(f"[METRICS] LLM metric not persisted (no client): {provider}/{model}")
                return False
            
            record = {
                'metric_type': 'llm_call',
                'processor': processor,
                'llm_provider': provider,
                'llm_model': model,
                'duration_ms': duration_ms,
                'tokens_in': tokens_in,
                'tokens_out': tokens_out,
                'cost_usd': cost_usd,
                'success': success,
                'error_message': error_message,
                'project_id': project_id
            }
            
            # Remove None values
            record = {k: v for k, v in record.items() if v is not None}
            
            client.table(MetricsService.TABLE_NAME).insert(record).execute()
            logger.debug(f"[METRICS] Recorded LLM call: {provider}/{model} in {duration_ms}ms")
            return True
            
        except Exception as e:
            logger.warning(f"[METRICS] Failed to record LLM metric: {e}")
            return False
    
    @staticmethod
    def record_query(
        query_type: str,
        duration_ms: int,
        success: bool,
        project_id: Optional[str] = None,
        rows_processed: Optional[int] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Record a data query event (chat, BI, etc).
        
        Args:
            query_type: 'chat', 'bi_builder', 'api'
            duration_ms: Query duration
            success: Whether query succeeded
            project_id: Optional project UUID
            rows_processed: Number of rows returned
            error_message: Error details if failed
        """
        try:
            client = MetricsService._get_client()
            if not client:
                return False
            
            record = {
                'metric_type': 'query',
                'processor': query_type,
                'duration_ms': duration_ms,
                'success': success,
                'project_id': project_id,
                'rows_processed': rows_processed,
                'error_message': error_message
            }
            
            record = {k: v for k, v in record.items() if v is not None}
            
            client.table(MetricsService.TABLE_NAME).insert(record).execute()
            return True
            
        except Exception as e:
            logger.warning(f"[METRICS] Failed to record query metric: {e}")
            return False
    
    @staticmethod
    def record_error(
        processor: str,
        error_message: str,
        project_id: Optional[str] = None,
        filename: Optional[str] = None
    ) -> bool:
        """
        Record an error event.
        """
        try:
            client = MetricsService._get_client()
            if not client:
                return False
            
            record = {
                'metric_type': 'error',
                'processor': processor,
                'success': False,
                'error_message': error_message,
                'project_id': project_id,
                'filename': filename
            }
            
            record = {k: v for k, v in record.items() if v is not None}
            
            client.table(MetricsService.TABLE_NAME).insert(record).execute()
            logger.info(f"[METRICS] Recorded error: {processor} - {error_message[:100]}")
            return True
            
        except Exception as e:
            logger.warning(f"[METRICS] Failed to record error metric: {e}")
            return False
    
    # =========================================================================
    # QUERY METHODS - For dashboards and reporting
    # =========================================================================
    
    @staticmethod
    def get_summary(days: int = 7) -> dict:
        """
        Get summary metrics for dashboard.
        
        Returns:
            dict with upload counts, success rates, avg processing times, LLM usage
        """
        try:
            client = MetricsService._get_client()
            if not client:
                return {'error': 'Metrics not available'}
            
            from datetime import timedelta
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            # Get all metrics in timeframe
            result = client.table(MetricsService.TABLE_NAME)\
                .select('*')\
                .gte('created_at', cutoff)\
                .execute()
            
            records = result.data or []
            
            # Aggregate
            uploads = [r for r in records if r.get('metric_type') == 'upload']
            llm_calls = [r for r in records if r.get('metric_type') == 'llm_call']
            errors = [r for r in records if r.get('metric_type') == 'error']
            
            # Upload stats by processor
            upload_stats = {}
            for u in uploads:
                proc = u.get('processor', 'unknown')
                if proc not in upload_stats:
                    upload_stats[proc] = {'count': 0, 'success': 0, 'total_ms': 0, 'total_rows': 0}
                upload_stats[proc]['count'] += 1
                if u.get('success'):
                    upload_stats[proc]['success'] += 1
                upload_stats[proc]['total_ms'] += u.get('duration_ms', 0)
                upload_stats[proc]['total_rows'] += u.get('rows_processed', 0) or 0
            
            # Calculate averages
            for proc, stats in upload_stats.items():
                stats['avg_ms'] = stats['total_ms'] // max(stats['count'], 1)
                stats['success_rate'] = round(stats['success'] / max(stats['count'], 1) * 100, 1)
            
            # LLM stats by provider
            llm_stats = {}
            for l in llm_calls:
                prov = l.get('llm_provider', 'unknown')
                if prov not in llm_stats:
                    llm_stats[prov] = {'calls': 0, 'tokens_in': 0, 'tokens_out': 0, 'total_cost': 0.0}
                llm_stats[prov]['calls'] += 1
                llm_stats[prov]['tokens_in'] += l.get('tokens_in', 0) or 0
                llm_stats[prov]['tokens_out'] += l.get('tokens_out', 0) or 0
                llm_stats[prov]['total_cost'] += float(l.get('cost_usd', 0) or 0)
            
            return {
                'period_days': days,
                'total_uploads': len(uploads),
                'total_llm_calls': len(llm_calls),
                'total_errors': len(errors),
                'upload_stats': upload_stats,
                'llm_stats': llm_stats,
                'error_rate': round(len(errors) / max(len(uploads), 1) * 100, 1)
            }
            
        except Exception as e:
            logger.error(f"[METRICS] Failed to get summary: {e}")
            return {'error': str(e)}
    
    @staticmethod
    def get_trends(days: int = 30, bucket: str = 'day') -> dict:
        """
        Get time-series metrics for trend analysis.
        
        Args:
            days: Number of days to look back
            bucket: 'hour', 'day', 'week'
        
        Returns:
            dict with time-bucketed metrics
        """
        try:
            client = MetricsService._get_client()
            if not client:
                return {'error': 'Metrics not available'}
            
            from datetime import timedelta
            cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
            
            result = client.table(MetricsService.TABLE_NAME)\
                .select('created_at, metric_type, processor, success, duration_ms')\
                .gte('created_at', cutoff)\
                .order('created_at')\
                .execute()
            
            records = result.data or []
            
            # Bucket by time
            buckets = {}
            for r in records:
                ts = r.get('created_at', '')[:10]  # YYYY-MM-DD
                if bucket == 'hour':
                    ts = r.get('created_at', '')[:13]  # YYYY-MM-DDTHH
                elif bucket == 'week':
                    # Get week number
                    from datetime import datetime as dt
                    d = dt.fromisoformat(r.get('created_at', '').replace('Z', '+00:00'))
                    ts = f"{d.year}-W{d.isocalendar()[1]:02d}"
                
                if ts not in buckets:
                    buckets[ts] = {'uploads': 0, 'successes': 0, 'errors': 0, 'total_ms': 0}
                
                if r.get('metric_type') == 'upload':
                    buckets[ts]['uploads'] += 1
                    if r.get('success'):
                        buckets[ts]['successes'] += 1
                    buckets[ts]['total_ms'] += r.get('duration_ms', 0)
                elif r.get('metric_type') == 'error':
                    buckets[ts]['errors'] += 1
            
            # Calculate averages
            for ts, data in buckets.items():
                data['avg_ms'] = data['total_ms'] // max(data['uploads'], 1)
                data['success_rate'] = round(data['successes'] / max(data['uploads'], 1) * 100, 1)
            
            return {
                'period_days': days,
                'bucket': bucket,
                'data': buckets
            }
            
        except Exception as e:
            logger.error(f"[METRICS] Failed to get trends: {e}")
            return {'error': str(e)}
