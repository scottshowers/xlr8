"""
XLR8 UPLOAD ENRICHMENT SERVICE
==============================

THE ONE PLACE for all intelligence enrichment at upload time.

Philosophy: Do the work ONCE at upload, store it, make downstream easy.

This service is called after ANY upload completes (structured, semantic, hybrid).
It handles:
1. DETECTION - Systems, domains, functional areas
2. RELATIONSHIPS - Table relationships (structured only)
3. METRICS - Document intelligence (char count, word count, etc.)
4. ENRICHMENT - ChromaDB chunk metadata updates (queries by filename, no doc_ids needed)

ALL upload paths call this. No exceptions.

Author: XLR8 Team
Version: 2.0.0 - Now queries ChromaDB by filename instead of requiring doc_ids
Deploy to: backend/utils/upload_enrichment.py
"""

import logging
import time
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class EnrichmentResult:
    """Complete enrichment result for an upload."""
    
    success: bool = False
    
    # Detection results
    primary_system: Optional[Dict] = None
    primary_domain: Optional[Dict] = None
    systems: List[Dict] = field(default_factory=list)
    domains: List[Dict] = field(default_factory=list)
    functional_areas: List[Dict] = field(default_factory=list)
    
    # Relationship results (structured only)
    relationships: List[Dict] = field(default_factory=list)
    relationships_count: int = 0
    
    # Document metrics
    char_count: int = 0
    word_count: int = 0
    line_count: int = 0
    document_type: Optional[str] = None
    
    # ChromaDB enrichment
    chunks_enriched: int = 0
    
    # Processing info
    enriched_at: Optional[str] = None
    enrichment_time_ms: int = 0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        result = {
            'success': self.success,
            'primary_system': self.primary_system,
            'primary_domain': self.primary_domain,
            'systems': self.systems,
            'domains': self.domains,
            'functional_areas': self.functional_areas,
            'relationships': self.relationships,
            'relationships_count': self.relationships_count,
            'char_count': self.char_count,
            'word_count': self.word_count,
            'line_count': self.line_count,
            'document_type': self.document_type,
            'chunks_enriched': self.chunks_enriched,
            'enriched_at': self.enriched_at,
            'enrichment_time_ms': self.enrichment_time_ms
        }
        if self.errors:
            result['errors'] = self.errors
        return result


# =============================================================================
# MAIN ENRICHMENT FUNCTION
# =============================================================================

def enrich_upload(
    project: str,
    project_id: Optional[str],
    filename: str,
    upload_type: str,  # 'structured', 'semantic', 'hybrid', 'standards'
    handler=None,  # DuckDB handler for structured
    text_content: Optional[str] = None,  # Raw text for semantic
    columns: Optional[List[str]] = None,  # Column names if available
    sheet_names: Optional[List[str]] = None,  # Excel sheet names
    tables_created: Optional[List[str]] = None,  # DuckDB tables created
    chunks_added: Optional[int] = None,  # Number of ChromaDB chunks added
    job_id: Optional[str] = None
) -> EnrichmentResult:
    """
    Master enrichment function - called for EVERY upload.
    
    This is the ONE place where all upload intelligence happens.
    
    Args:
        project: Project name
        project_id: Project UUID
        filename: Uploaded filename
        upload_type: Type of upload (structured/semantic/hybrid/standards)
        handler: DuckDB structured data handler (for structured uploads)
        text_content: Raw text content (for semantic uploads)
        columns: List of column names (if available)
        sheet_names: Excel sheet names (if available)
        tables_created: List of DuckDB tables created
        chunks_added: Number of ChromaDB chunks added (for logging)
        job_id: Processing job ID for progress updates
        
    Returns:
        EnrichmentResult with all intelligence
    """
    start_time = time.time()
    
    result = EnrichmentResult()
    result.enriched_at = datetime.utcnow().isoformat()
    
    logger.warning(f"[ENRICHMENT] Starting enrichment for {filename} (type={upload_type}, project={project})")
    
    # Update progress if job_id provided
    def update_progress(pct: int, msg: str):
        if job_id:
            try:
                from models.processing_job import ProcessingJobModel
                ProcessingJobModel.update_progress(job_id, pct, msg)
            except Exception:
                pass
    
    # =========================================================================
    # STEP 1: DETECTION - Systems, Domains, Functional Areas
    # =========================================================================
    update_progress(85, "Detecting system context...")
    
    try:
        detection_result = _run_detection(
            project=project,
            project_id=project_id,
            filename=filename,
            handler=handler,
            columns=columns,
            sheet_names=sheet_names
        )
        
        if detection_result:
            result.primary_system = detection_result.get('primary_system')
            result.primary_domain = detection_result.get('primary_domain')
            result.systems = detection_result.get('systems', [])
            result.domains = detection_result.get('domains', [])
            result.functional_areas = detection_result.get('functional_areas', [])
            
            if result.primary_system:
                logger.warning(f"[ENRICHMENT] Detected system: {result.primary_system.get('name', result.primary_system.get('code', 'Unknown'))}")
            if result.primary_domain:
                logger.warning(f"[ENRICHMENT] Detected domain: {result.primary_domain.get('name', result.primary_domain.get('code', 'Unknown'))}")
                
    except Exception as e:
        logger.warning(f"[ENRICHMENT] Detection failed: {e}")
        result.errors.append(f"Detection: {str(e)}")
    
    # =========================================================================
    # STEP 2: RELATIONSHIPS - Table relationships (structured only)
    # =========================================================================
    if upload_type in ('structured', 'hybrid') and handler:
        update_progress(88, "Detecting relationships...")
        
        try:
            relationships = _run_relationship_detection(
                project=project,
                handler=handler,
                tables=tables_created
            )
            
            if relationships:
                result.relationships = relationships
                result.relationships_count = len(relationships)
                logger.warning(f"[ENRICHMENT] Detected {result.relationships_count} relationships")
                
        except Exception as e:
            logger.warning(f"[ENRICHMENT] Relationship detection failed: {e}")
            result.errors.append(f"Relationships: {str(e)}")
    
    # =========================================================================
    # STEP 3: DOCUMENT METRICS
    # =========================================================================
    update_progress(90, "Computing document metrics...")
    
    try:
        metrics = _compute_document_metrics(
            text_content=text_content,
            filename=filename,
            handler=handler,
            tables=tables_created
        )
        
        result.char_count = metrics.get('char_count', 0)
        result.word_count = metrics.get('word_count', 0)
        result.line_count = metrics.get('line_count', 0)
        result.document_type = metrics.get('document_type')
        
    except Exception as e:
        logger.warning(f"[ENRICHMENT] Metrics computation failed: {e}")
        result.errors.append(f"Metrics: {str(e)}")
    
    # =========================================================================
    # STEP 4: CHROMADB METADATA ENRICHMENT (queries by filename, no doc_ids needed)
    # =========================================================================
    if upload_type in ('semantic', 'hybrid', 'standards'):
        update_progress(92, "Enriching ChromaDB metadata...")
        
        try:
            enriched_count = _enrich_chromadb_by_filename(
                filename=filename,
                project=project,
                result=result
            )
            result.chunks_enriched = enriched_count
            if enriched_count > 0:
                logger.warning(f"[ENRICHMENT] Enriched {enriched_count} ChromaDB chunks")
                
        except Exception as e:
            logger.warning(f"[ENRICHMENT] ChromaDB enrichment failed: {e}")
            result.errors.append(f"ChromaDB: {str(e)}")
    
    # =========================================================================
    # STEP 5: PERSIST TO SUPABASE
    # =========================================================================
    update_progress(95, "Storing enrichment data...")
    
    try:
        _persist_enrichment(
            project=project,
            project_id=project_id,
            filename=filename,
            result=result
        )
    except Exception as e:
        logger.warning(f"[ENRICHMENT] Persistence failed: {e}")
        result.errors.append(f"Persistence: {str(e)}")
    
    # =========================================================================
    # COMPLETE
    # =========================================================================
    result.enrichment_time_ms = int((time.time() - start_time) * 1000)
    result.success = len(result.errors) == 0
    
    logger.warning(f"[ENRICHMENT] Complete for {filename} in {result.enrichment_time_ms}ms "
                   f"(detection={'yes' if result.primary_system or result.primary_domain else 'no'}, "
                   f"relationships={result.relationships_count}, chunks_enriched={result.chunks_enriched})")
    
    return result


# =============================================================================
# STEP 1: DETECTION
# =============================================================================

def _run_detection(
    project: str,
    project_id: Optional[str],
    filename: str,
    handler=None,
    columns: Optional[List[str]] = None,
    sheet_names: Optional[List[str]] = None
) -> Optional[Dict]:
    """Run detection service to identify systems, domains, and functional areas."""
    
    try:
        # Try to import detection service
        try:
            from utils.detection_service import get_detection_service
        except ImportError:
            try:
                from backend.utils.detection_service import get_detection_service
            except ImportError:
                logger.debug("[ENRICHMENT] Detection service not available")
                return None
        
        service = get_detection_service()
        
        # Collect all columns
        all_columns = list(columns) if columns else []
        all_filenames = {filename}
        all_sheet_names = list(sheet_names) if sheet_names else []
        
        # Get additional columns from DuckDB if handler available
        if handler and hasattr(handler, 'conn') and handler.conn:
            try:
                tables = handler.conn.execute(f"""
                    SELECT table_name, file_name
                    FROM _schema_metadata
                    WHERE project = '{project}'
                """).fetchall()
                
                for table_name, file_name in tables:
                    if file_name:
                        all_filenames.add(file_name)
                    
                    try:
                        cols = handler.conn.execute(f"PRAGMA table_info('{table_name}')").fetchall()
                        for col in cols:
                            col_name = col[1]
                            if col_name and not col_name.startswith('_'):
                                all_columns.append(col_name)
                    except Exception:
                        pass
                        
            except Exception as e:
                logger.debug(f"[ENRICHMENT] Could not query project tables: {e}")
        
        # Run detection
        detection_result = service.detect(
            filename=filename,
            columns=all_columns,
            sheet_names=all_sheet_names,
            all_filenames=list(all_filenames)
        )
        
        return detection_result.to_dict() if detection_result else None
        
    except Exception as e:
        logger.warning(f"[ENRICHMENT] Detection error: {e}")
        return None


# =============================================================================
# STEP 2: RELATIONSHIP DETECTION
# =============================================================================

def _run_relationship_detection(
    project: str,
    handler,
    tables: Optional[List[str]] = None
) -> List[Dict]:
    """Run relationship detection using semantic-first matching."""
    
    import signal
    
    # Timeout handler - 5 minutes max for relationship detection
    MAX_RELATIONSHIP_DETECTION_SECONDS = 300
    
    class TimeoutError(Exception):
        pass
    
    def timeout_handler(signum, frame):
        raise TimeoutError("Relationship detection timed out")
    
    try:
        logger.warning(f"[ENRICHMENT] Starting relationship detection for project={project}")
        
        # Import relationship detector
        try:
            from backend.utils.relationship_detector import analyze_project_relationships
        except ImportError:
            try:
                from utils.relationship_detector import analyze_project_relationships
            except ImportError:
                logger.debug("[ENRICHMENT] Relationship detector not available")
                return []
        
        if not handler or not hasattr(handler, 'conn') or not handler.conn:
            logger.warning("[ENRICHMENT] No handler/connection for relationship detection")
            return []
        
        # Get all current tables for project
        try:
            logger.warning(f"[ENRICHMENT] Querying _schema_metadata for {project}...")
            db_tables = handler.conn.execute(f"""
                SELECT table_name, display_name, columns, row_count
                FROM _schema_metadata
                WHERE project = '{project}' AND is_current = TRUE
            """).fetchall()
            logger.warning(f"[ENRICHMENT] Found {len(db_tables)} tables in _schema_metadata")
        except Exception as e:
            logger.warning(f"[ENRICHMENT] Could not get tables: {e}")
            return []
        
        if not db_tables:
            logger.warning("[ENRICHMENT] No tables found in _schema_metadata")
            return []
        
        # Format tables for detector
        import json
        table_list = []
        for table_name, display_name, columns_json, row_count in db_tables:
            try:
                columns = json.loads(columns_json) if columns_json else []
                col_names = [c.get('name', c) if isinstance(c, dict) else c for c in columns]
            except Exception:
                col_names = []
            
            table_list.append({
                'table_name': table_name,
                'display_name': display_name,
                'columns': col_names,
                'row_count': row_count or 0
            })
        
        logger.warning(f"[ENRICHMENT] Prepared {len(table_list)} tables for relationship detection")
        
        # Run async detection with timeout
        import asyncio
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Set timeout (only works on Unix)
            try:
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(MAX_RELATIONSHIP_DETECTION_SECONDS)
            except (ValueError, AttributeError):
                # signal.alarm not available (Windows or non-main thread)
                old_handler = None
            
            logger.warning(f"[ENRICHMENT] Running analyze_project_relationships...")
            detect_result = loop.run_until_complete(
                analyze_project_relationships(project, table_list, handler)
            )
            
            # Cancel timeout
            if old_handler is not None:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
                
        except TimeoutError:
            logger.error(f"[ENRICHMENT] Relationship detection TIMED OUT after {MAX_RELATIONSHIP_DETECTION_SECONDS}s")
            return []
        finally:
            loop.close()
        
        if not detect_result:
            logger.warning("[ENRICHMENT] No detection result returned")
            return []
        
        relationships = detect_result.get('relationships', [])
        logger.warning(f"[ENRICHMENT] Detection complete: {len(relationships)} relationships found")
        
        # Persist to Supabase
        if relationships:
            _persist_relationships(project, relationships)
        
        return relationships
        
    except Exception as e:
        logger.error(f"[ENRICHMENT] Relationship detection error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []


def _persist_relationships(project: str, relationships: List[Dict]) -> None:
    """Persist detected relationships to Supabase with batching."""
    
    if not relationships:
        return
    
    try:
        try:
            from utils.database.supabase_client import get_supabase
        except ImportError:
            try:
                from backend.utils.database.supabase_client import get_supabase
            except ImportError:
                logger.warning("[ENRICHMENT] Supabase client not available - skipping relationship persist")
                return
        
        supabase = get_supabase()
        if not supabase:
            logger.warning("[ENRICHMENT] No Supabase connection - skipping relationship persist")
            return
        
        # Build batch records
        records = []
        for rel in relationships:
            records.append({
                'project_name': project,
                'source_table': rel.get('source_table', ''),
                'source_column': rel.get('source_column', ''),
                'target_table': rel.get('target_table', ''),
                'target_column': rel.get('target_column', ''),
                'confidence': rel.get('confidence', 0.5),
                'relationship_type': rel.get('relationship_type', 'one-to-many'),
                'needs_review': rel.get('confidence', 0.5) < 0.8,
                'confirmed': False
            })
        
        # Batch upsert in chunks of 50 (Supabase limit friendly)
        BATCH_SIZE = 50
        persisted = 0
        
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i:i + BATCH_SIZE]
            try:
                supabase.table('project_relationships').upsert(
                    batch,
                    on_conflict='project_name,source_table,source_column,target_table,target_column'
                ).execute()
                persisted += len(batch)
            except Exception as batch_err:
                logger.warning(f"[ENRICHMENT] Batch {i//BATCH_SIZE + 1} failed: {batch_err}")
                # Continue with remaining batches
        
        logger.warning(f"[ENRICHMENT] Persisted {persisted}/{len(relationships)} relationships to Supabase")
        
    except Exception as e:
        # Don't let persistence failure kill the job
        logger.warning(f"[ENRICHMENT] Relationship persistence failed (non-fatal): {e}")


# =============================================================================
# STEP 3: DOCUMENT METRICS
# =============================================================================

def _compute_document_metrics(
    text_content: Optional[str],
    filename: str,
    handler=None,
    tables: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Compute document metrics and infer document type."""
    
    metrics = {}
    
    # Text metrics
    if text_content:
        metrics['char_count'] = len(text_content)
        metrics['word_count'] = len(text_content.split())
        metrics['line_count'] = len(text_content.split('\n'))
    
    # Infer document type from filename
    filename_lower = filename.lower()
    
    if any(p in filename_lower for p in ['register', 'payroll', 'pay_reg']):
        metrics['document_type'] = 'payroll_register'
    elif any(p in filename_lower for p in ['tax', 'w2', 'w-2', '1099', 'sui', 'suta']):
        metrics['document_type'] = 'tax_document'
    elif any(p in filename_lower for p in ['config', 'validation', 'setup', 'mapping']):
        metrics['document_type'] = 'configuration'
    elif any(p in filename_lower for p in ['employee', 'roster', 'headcount', 'census']):
        metrics['document_type'] = 'employee_data'
    elif any(p in filename_lower for p in ['benefit', 'enrollment', 'deduction']):
        metrics['document_type'] = 'benefits_data'
    elif any(p in filename_lower for p in ['gl ', 'general_ledger', 'chart_of_account', 'coa']):
        metrics['document_type'] = 'gl_data'
    elif any(p in filename_lower for p in ['policy', 'handbook', 'guide', 'manual']):
        metrics['document_type'] = 'reference'
    elif any(p in filename_lower for p in ['regulation', 'compliance', 'irs', 'dol']):
        metrics['document_type'] = 'regulatory'
    else:
        metrics['document_type'] = 'general'
    
    return metrics


# =============================================================================
# STEP 4: CHROMADB ENRICHMENT (BY FILENAME)
# =============================================================================

def _enrich_chromadb_by_filename(
    filename: str,
    project: str,
    result: EnrichmentResult
) -> int:
    """
    Enrich ChromaDB chunks by querying for filename.
    
    This approach doesn't require doc_ids - it queries ChromaDB
    for all chunks matching the filename and project.
    """
    
    try:
        import chromadb
        from chromadb.config import Settings
        
        # Get ChromaDB client
        chroma_path = os.getenv('CHROMADB_PATH', '/data/chromadb')
        
        if not os.path.exists(chroma_path):
            logger.debug(f"[ENRICHMENT] ChromaDB path doesn't exist: {chroma_path}")
            return 0
        
        client = chromadb.PersistentClient(
            path=chroma_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        collection = client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Build query - try multiple approaches since metadata structure may vary
        try:
            # Approach 1: Query by filename
            if project == '__STANDARDS__':
                where_filter = {"filename": {"$eq": filename}}
            else:
                where_filter = {
                    "$and": [
                        {"filename": {"$eq": filename}},
                        {"project": {"$eq": project}}
                    ]
                }
            
            existing = collection.get(
                where=where_filter,
                include=['metadatas']
            )
        except Exception as query_e:
            logger.debug(f"[ENRICHMENT] ChromaDB query failed: {query_e}")
            # Try simpler query
            try:
                existing = collection.get(
                    where={"source": {"$eq": filename}},
                    include=['metadatas']
                )
            except Exception:
                return 0
        
        if not existing or not existing.get('ids'):
            logger.debug(f"[ENRICHMENT] No ChromaDB chunks found for {filename}")
            return 0
        
        chunk_ids = existing['ids']
        existing_metadatas = existing.get('metadatas', [])
        
        # Build enrichment metadata
        enrichment = {}
        
        if result.primary_system:
            enrichment['detected_system'] = result.primary_system.get('code', result.primary_system.get('name', ''))
            enrichment['system_name'] = result.primary_system.get('name', '')
        
        if result.primary_domain:
            enrichment['detected_domain'] = result.primary_domain.get('code', result.primary_domain.get('name', ''))
            enrichment['domain_name'] = result.primary_domain.get('name', '')
        
        if result.functional_areas:
            fa_codes = [
                fa.get('code', fa.get('name', '')) 
                for fa in result.functional_areas[:5]
                if isinstance(fa, dict)
            ]
            if fa_codes:
                enrichment['functional_areas'] = ','.join(fa_codes)
        
        if result.document_type:
            enrichment['document_type'] = result.document_type
        
        if result.char_count:
            enrichment['char_count'] = result.char_count
        
        if result.word_count:
            enrichment['word_count'] = result.word_count
        
        enrichment['enriched'] = True
        enrichment['enriched_at'] = result.enriched_at
        
        if not enrichment:
            return 0
        
        # Update each chunk
        updated_metadatas = []
        for i, chunk_id in enumerate(chunk_ids):
            existing_meta = existing_metadatas[i] if i < len(existing_metadatas) else {}
            updated = {**existing_meta, **enrichment}
            # Filter None values (ChromaDB doesn't like None)
            updated = {k: v for k, v in updated.items() if v is not None}
            updated_metadatas.append(updated)
        
        # Batch update
        collection.update(
            ids=chunk_ids,
            metadatas=updated_metadatas
        )
        
        logger.info(f"[ENRICHMENT] Updated {len(chunk_ids)} ChromaDB chunks for {filename}")
        return len(chunk_ids)
        
    except Exception as e:
        logger.warning(f"[ENRICHMENT] ChromaDB enrichment error: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return 0


# =============================================================================
# STEP 5: PERSIST TO SUPABASE
# =============================================================================

def _persist_enrichment(
    project: str,
    project_id: Optional[str],
    filename: str,
    result: EnrichmentResult
) -> None:
    """Persist enrichment results to Supabase."""
    
    try:
        try:
            from utils.database.supabase_client import get_supabase
        except ImportError:
            try:
                from backend.utils.database.supabase_client import get_supabase
            except ImportError:
                return
        
        supabase = get_supabase()
        if not supabase:
            return
        
        # Update project context if we have detection results
        if (result.systems or result.domains) and project_id:
            try:
                context_data = {
                    'project_id': project_id,
                    'detection_summary': {
                        'primary_system': result.primary_system,
                        'primary_domain': result.primary_domain,
                        'systems': result.systems[:5],
                        'domains': result.domains[:5],
                        'functional_areas': result.functional_areas[:10]
                    },
                    'relationships_count': result.relationships_count,
                    'last_enriched_at': result.enriched_at
                }
                
                supabase.table('project_context').upsert(
                    context_data,
                    on_conflict='project_id'
                ).execute()
                
                logger.debug(f"[ENRICHMENT] Updated project_context for {project}")
                
            except Exception as e:
                # Table might not exist - that's ok
                logger.debug(f"[ENRICHMENT] project_context update skipped: {e}")
        
        # Update document_registry with enrichment
        try:
            # Find document by filename
            query = supabase.table('document_registry').select('id').eq('filename', filename)
            if project_id:
                query = query.eq('project_id', project_id)
            
            doc_result = query.limit(1).execute()
            
            if doc_result.data:
                doc_id = doc_result.data[0]['id']
                
                update_data = {
                    'intelligence': result.to_dict(),
                    'enriched_at': result.enriched_at
                }
                
                supabase.table('document_registry').update(update_data).eq('id', doc_id).execute()
                logger.debug(f"[ENRICHMENT] Updated document_registry for {filename}")
                
        except Exception as e:
            logger.debug(f"[ENRICHMENT] document_registry update skipped: {e}")
        
    except Exception as e:
        logger.warning(f"[ENRICHMENT] Persistence error: {e}")


# =============================================================================
# CONVENIENCE WRAPPERS
# =============================================================================

def enrich_structured_upload(
    project: str,
    project_id: Optional[str],
    filename: str,
    handler,
    tables_created: List[str],
    columns: Optional[List[str]] = None,
    sheet_names: Optional[List[str]] = None,
    job_id: Optional[str] = None
) -> EnrichmentResult:
    """Convenience wrapper for structured (Excel/CSV → DuckDB) uploads."""
    
    return enrich_upload(
        project=project,
        project_id=project_id,
        filename=filename,
        upload_type='structured',
        handler=handler,
        tables_created=tables_created,
        columns=columns,
        sheet_names=sheet_names,
        job_id=job_id
    )


def enrich_semantic_upload(
    project: str,
    project_id: Optional[str],
    filename: str,
    text_content: Optional[str] = None,
    chunks_added: Optional[int] = None,
    job_id: Optional[str] = None
) -> EnrichmentResult:
    """Convenience wrapper for semantic (PDF/DOCX → ChromaDB) uploads."""
    
    return enrich_upload(
        project=project,
        project_id=project_id,
        filename=filename,
        upload_type='semantic',
        text_content=text_content,
        chunks_added=chunks_added,
        job_id=job_id
    )


def enrich_hybrid_upload(
    project: str,
    project_id: Optional[str],
    filename: str,
    handler,
    tables_created: List[str],
    text_content: Optional[str] = None,
    chunks_added: Optional[int] = None,
    job_id: Optional[str] = None
) -> EnrichmentResult:
    """Convenience wrapper for hybrid (PDF with tables → both DuckDB and ChromaDB) uploads."""
    
    return enrich_upload(
        project=project,
        project_id=project_id,
        filename=filename,
        upload_type='hybrid',
        handler=handler,
        tables_created=tables_created,
        text_content=text_content,
        chunks_added=chunks_added,
        job_id=job_id
    )


def enrich_standards_upload(
    filename: str,
    text_content: Optional[str] = None,
    chunks_added: Optional[int] = None,
    domain: Optional[str] = None
) -> EnrichmentResult:
    """Convenience wrapper for standards/reference uploads (global, no project)."""
    
    return enrich_upload(
        project='__STANDARDS__',
        project_id=None,
        filename=filename,
        upload_type='standards',
        text_content=text_content,
        chunks_added=chunks_added
    )
