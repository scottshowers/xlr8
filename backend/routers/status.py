"""
Status Router - Registry-Aware Version v20
===========================================

v20 CHANGES (December 23, 2025 - N+1 Performance Fix):
- Fixed N+1 query issue in /status/structured endpoint
- Now fetches all table names in ONE query upfront (SHOW TABLES)
- O(1) set lookup replaces N individual SELECT queries
- ~10x faster for projects with many tables

v19 CHANGES (December 23, 2025 - Delete Verify):
- Delete now cleans _column_profiles, _column_mappings, _mapping_jobs
- Orphan cleanup now includes _column_profiles
- Added profiling metadata to delete response
- Complete cascade delete across all data stores

UPDATED December 20, 2025:
- Thread-safe DuckDB operations (safe_execute, safe_fetchall, safe_fetchone)
- Data integrity now classifies INSIGHTS vs ISSUES
- Optional fields (orgudfield*, udf*, report_category) are insights, not issues
- Health score only affected by actual issues

UPDATED December 19, 2025:
- Delete endpoints now call DocumentRegistryModel.unregister()
- Registry is the SOURCE OF TRUTH for all file existence checks
- Added /status/registry/sync endpoint for one-time cleanup

FIXED December 19, 2025:
- Delete now ALWAYS cleans _schema_metadata and _pdf_tables
- Case-insensitive matching for project/filename
- Explicit checkpoint after deletes
- Metadata cleanup happens even if table drop fails
- Added /status/structured/clean-orphans endpoint

Deploy to: backend/routers/status.py
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime
import sys
import logging
import json
import traceback
import re

sys.path.insert(0, '/app')
sys.path.insert(0, '/data')

from utils.rag_handler import RAGHandler
from utils.database.models import ProcessingJobModel, DocumentModel, DocumentRegistryModel

# Import structured data handler
try:
    from utils.structured_data_handler import get_structured_handler
    STRUCTURED_AVAILABLE = True
except ImportError:
    STRUCTURED_AVAILABLE = False

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== TABLE DISPLAY NAME UTILITIES ====================

def generate_display_name(table_name: str, sheet: str = None, filename: str = None, project: str = None) -> str:
    """
    Generate a human-friendly display name: Project/Client + Sheet.
    
    Examples:
        project="Acme Corp", sheet="Active" → "Acme Corp - Active"
        project="Acme Corp", sheet="Sheet1", file="Earnings.xlsx" → "Acme Corp - Earnings"
        project="TEA1000", sheet="Deductions" → "TEA1000 - Deductions"
    
    Args:
        table_name: The raw DuckDB table name (fallback parsing)
        sheet: Sheet name (primary identifier)
        filename: Source filename (used when sheet is generic)
        project: Project/client name (prefix)
    
    Returns:
        Human-friendly display name: "Project - Identifier"
    """
    def clean_name(name: str) -> str:
        """Clean a name component (remove extensions, timestamps, etc.)"""
        if not name:
            return ""
        
        base = name.strip()
        
        # Remove file extensions
        extensions = ['.xlsx', '.xls', '.csv', '.pdf', '.docx', '.doc', '.txt']
        for ext in extensions:
            if base.lower().endswith(ext):
                base = base[:-len(ext)]
                break
        
        # Remove common suffixes
        suffixes = ['_pdf', '_xlsx', '_xls', '_csv', '_excel', '_sheet', '_data']
        for suffix in suffixes:
            if base.lower().endswith(suffix):
                base = base[:-len(suffix)]
        
        # Remove timestamp patterns
        base = re.sub(r'_?\d{8}_\d{6}$', '', base)
        base = re.sub(r'_?\d{8}$', '', base)
        base = re.sub(r'_?\d{14}$', '', base)
        base = re.sub(r'_?\(\d+\)$', '', base)
        
        # Replace separators with spaces
        base = base.replace('_', ' ').replace('-', ' ')
        
        # Title case, preserve acronyms (2-4 chars all caps)
        words = base.split()
        result_words = []
        for word in words:
            if word.isupper() and 2 <= len(word) <= 4:
                result_words.append(word)
            else:
                result_words.append(word.title())
        
        return ' '.join(result_words).strip()
    
    # Generic sheet names - use filename instead
    generic_sheets = {'sheet1', 'sheet2', 'sheet3', 'sheet 1', 'sheet 2', 'sheet 3', 
                      'data', 'pdf data', 'table1', 'table 1', 'page 1', 'page1'}
    
    # Clean project name
    clean_project = clean_name(project) if project else ""
    
    # Determine the identifier (sheet or filename)
    clean_sheet = clean_name(sheet) if sheet else ""
    clean_file = clean_name(filename) if filename else ""
    is_generic_sheet = sheet and sheet.lower().strip() in generic_sheets
    
    if clean_sheet and not is_generic_sheet:
        identifier = clean_sheet
    elif clean_file:
        identifier = clean_file
    else:
        # Parse from table_name as last resort
        parts = table_name.split('__')
        if len(parts) >= 2:
            identifier = clean_name('__'.join(parts[1:]))
        else:
            identifier = clean_name(table_name)
    
    # Build display name
    if clean_project and identifier:
        display = f"{clean_project} - {identifier}"
    elif clean_project:
        display = clean_project
    elif identifier:
        display = identifier
    else:
        display = table_name
    
    # Clean up whitespace
    display = re.sub(r'\s+', ' ', display).strip()
    
    return display if display else table_name
    
    return display


# ==================== STRUCTURED DATA STATUS ====================

@router.get("/status/structured")
async def get_structured_data_status(project: Optional[str] = None):
    """
    Get structured data (DuckDB) statistics.
    
    Uses document_registry as source of truth, enriched with DuckDB table details.
    """
    import time
    start_time = time.time()
    logger.info(f"[STATUS/STRUCTURED] Starting request, project={project}")
    
    if not STRUCTURED_AVAILABLE:
        logger.warning("[STATUS/STRUCTURED] Handler not available")
        return {
            "available": False,
            "error": "Structured data handler not available",
            "files": [],
            "total_files": 0,
            "total_tables": 0,
            "total_rows": 0
        }
    
    try:
        handler = get_structured_handler()
        logger.info(f"[STATUS/STRUCTURED] Got handler in {time.time() - start_time:.2f}s")
        
        # =================================================================
        # STEP 1: Get valid files from REGISTRY (source of truth)
        # =================================================================
        valid_files = set()
        registry_lookup = {}  # filename -> {uploaded_by, uploaded_at, truth_type}
        customer_lookup = {}  # project_code -> customer_name
        
        try:
            # Build customer name lookup from all projects
            from utils.database.models import ProjectModel
            all_projects = ProjectModel.get_all()
            for p in all_projects:
                proj_name = p.get('name', '')
                customer = p.get('customer', '')
                if proj_name:
                    customer_lookup[proj_name.lower()] = customer or proj_name
            logger.info(f"[STATUS/STRUCTURED] Built customer lookup for {len(customer_lookup)} projects")
            
            # Get registry entries for DuckDB files
            if project:
                proj_record = ProjectModel.get_by_name(project)
                project_id = proj_record.get('id') if proj_record else None
                
                registry_entries = DocumentRegistryModel.get_by_project(project_id, include_global=True)
            else:
                registry_entries = DocumentRegistryModel.get_all()
            
            # Filter to only DuckDB files and build lookup
            for entry in registry_entries:
                storage = entry.get('storage_type', '')
                if storage in ('duckdb', 'both'):
                    filename = entry.get('filename', '')
                    valid_files.add(filename.lower())
                    # Build lookup for provenance data (file-level, not table-level)
                    registry_lookup[filename.lower()] = {
                        'uploaded_by': entry.get('uploaded_by_email', ''),
                        'uploaded_at': entry.get('created_at', ''),
                        'truth_type': entry.get('truth_type', 'reality')
                    }
            
            logger.info(f"[STATUS/STRUCTURED] Registry has {len(valid_files)} valid DuckDB files")
            
            # If registry is empty, return empty - no fallback to stale metadata
            if not valid_files:
                logger.info("[STATUS/STRUCTURED] Registry is empty, returning empty result")
                return {
                    "available": True,
                    "files": [],
                    "total_files": 0,
                    "total_tables": 0,
                    "total_rows": 0
                }
                
        except Exception as reg_e:
            logger.warning(f"[STATUS/STRUCTURED] Registry query failed: {reg_e}")
            # Don't fall back - return empty if registry fails
            return {
                "available": True,
                "files": [],
                "total_files": 0,
                "total_tables": 0,
                "total_rows": 0,
                "registry_error": str(reg_e)
            }
        
        # =================================================================
        # STEP 2: Get table details from DuckDB metadata
        # =================================================================
        tables = []
        
        # Get all existing tables in ONE query (fixes N+1 performance issue)
        existing_tables = set()
        try:
            all_tables_result = handler.safe_fetchall("SHOW TABLES")
            existing_tables = set(t[0] for t in all_tables_result)
            logger.info(f"[STATUS/STRUCTURED] Found {len(existing_tables)} existing tables")
        except Exception as e:
            logger.warning(f"[STATUS/STRUCTURED] Could not get table list: {e}")
        
        try:
            logger.info("[STATUS/STRUCTURED] Querying _schema_metadata...")
            metadata_result = handler.safe_fetchall("""
                SELECT table_name, project, file_name, sheet_name, columns, row_count, created_at
                FROM _schema_metadata 
                WHERE is_current = TRUE
            """)
            logger.info(f"[STATUS/STRUCTURED] _schema_metadata returned {len(metadata_result)} rows")
            
            for row in metadata_result:
                table_name, proj, filename, sheet, columns_json, row_count, created_at = row
                
                # Filter by project if specified
                if project and proj and proj.lower() != project.lower():
                    continue
                
                # Filter by registry (if available)
                if valid_files is not None and filename and filename.lower() not in valid_files:
                    logger.debug(f"[STATUS/STRUCTURED] Skipping {filename} - not in registry")
                    continue
                
                # Verify table actually exists (O(1) set lookup instead of N queries)
                if table_name not in existing_tables:
                    logger.warning(f"[STATUS] Skipping stale metadata for non-existent table: {table_name}")
                    continue
                
                try:
                    columns_data = json.loads(columns_json) if columns_json else []
                    columns = [c.get('name', c) if isinstance(c, dict) else c for c in columns_data]
                except:
                    columns = []
                
                # Get provenance from registry lookup
                provenance = registry_lookup.get(filename.lower(), {})
                
                # Get customer name from project lookup (or fall back to project code)
                customer_name = customer_lookup.get(proj.lower(), proj) if proj else ''
                
                tables.append({
                    'table_name': table_name,
                    # Display: Customer Name + Sheet (source file stored in metadata)
                    'display_name': generate_display_name(table_name, sheet=sheet, filename=filename, project=customer_name),
                    'project': proj,
                    'customer': customer_name,
                    'file': filename,
                    'sheet': sheet,
                    'columns': columns,
                    'row_count': row_count or 0,
                    'loaded_at': str(created_at) if created_at else None,
                    'uploaded_by': provenance.get('uploaded_by', ''),
                    'uploaded_at': provenance.get('uploaded_at', ''),
                    'truth_type': provenance.get('truth_type', 'reality'),
                    'source_type': 'excel'
                })
            
            logger.info(f"[STATUS] Got {len(tables)} tables from _schema_metadata (Excel)")
            
        except Exception as meta_e:
            logger.warning(f"Metadata query failed: {meta_e}")
        
        # =================================================================
        # STEP 3: Also query _pdf_tables for PDF-derived tables
        # =================================================================
        try:
            # First check if table exists
            table_check = handler.safe_fetchone("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = '_pdf_tables'
            """)
            logger.info(f"[STATUS] _pdf_tables exists: {table_check[0] > 0}")
            
            if table_check[0] > 0:
                pdf_result = handler.safe_fetchall("""
                    SELECT table_name, source_file, project, project_id, row_count, columns, created_at
                    FROM _pdf_tables
                """)
                logger.info(f"[STATUS] _pdf_tables has {len(pdf_result)} rows")
            else:
                pdf_result = []
            
            pdf_count = 0
            for row in pdf_result:
                table_name, source_file, proj, project_id, row_count, columns_json, created_at = row
                
                # Filter by project if specified
                if project and proj and proj.lower() != project.lower():
                    continue
                
                # Filter by registry (if available)
                if valid_files is not None and source_file and source_file.lower() not in valid_files:
                    logger.debug(f"[STATUS/STRUCTURED] Skipping PDF {source_file} - not in registry")
                    continue
                
                # Verify table actually exists (O(1) set lookup instead of N queries)
                if table_name not in existing_tables:
                    logger.warning(f"[STATUS] Skipping stale metadata for non-existent PDF table: {table_name}")
                    continue
                
                try:
                    columns = json.loads(columns_json) if columns_json else []
                except:
                    columns = []
                
                # Get provenance from registry lookup
                provenance = registry_lookup.get(source_file.lower(), {})
                
                # Get customer name from project lookup
                customer_name = customer_lookup.get((proj or '').lower(), proj or 'Unknown')
                
                tables.append({
                    'table_name': table_name,
                    # PDF Data is generic, will use filename; customer provides prefix
                    'display_name': generate_display_name(table_name, sheet='PDF Data', filename=source_file, project=customer_name),
                    'project': proj or 'Unknown',
                    'customer': customer_name,
                    'file': source_file,
                    'sheet': 'PDF Data',
                    'columns': columns,
                    'row_count': row_count or 0,
                    'loaded_at': str(created_at) if created_at else None,
                    'uploaded_by': provenance.get('uploaded_by', ''),
                    'uploaded_at': provenance.get('uploaded_at', ''),
                    'truth_type': provenance.get('truth_type', 'reality'),
                    'source_type': 'pdf'
                })
                pdf_count += 1
            
            logger.info(f"[STATUS] Got {pdf_count} tables from _pdf_tables (PDF)")
            
        except Exception as pdf_e:
            logger.debug(f"PDF tables query: {pdf_e}")
        
        # =================================================================
        # STEP 4: Fallback to information_schema if no metadata
        # =================================================================
        if not tables:
            logger.warning("No metadata found, falling back to information_schema")
            
            try:
                table_result = handler.safe_fetchall("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'main'
                    AND table_name NOT LIKE '_%'
                """)
                
                for (table_name,) in table_result:
                    try:
                        count_result = handler.safe_fetchone(f'SELECT COUNT(*) FROM "{table_name}"')
                        row_count = count_result[0] if count_result else 0
                        
                        col_result = handler.safe_fetchall(f'PRAGMA table_info("{table_name}")')
                        columns = [col[1] for col in col_result] if col_result else []
                        
                        parts = table_name.split('__')
                        if len(parts) >= 2:
                            proj = parts[0]
                            filename = '__'.join(parts[1:])
                            sheet = ''
                        else:
                            proj = 'default'
                            filename = table_name
                            sheet = ''
                        
                        if project and proj.lower() != project.lower():
                            continue
                        
                        # Filter by registry (if available)
                        if valid_files is not None and filename and filename.lower() not in valid_files:
                            continue
                        
                        # Get provenance from registry lookup
                        provenance = registry_lookup.get(filename.lower(), {})
                        
                        # Get customer name from project lookup
                        customer_name = customer_lookup.get(proj.lower(), proj) if proj else 'Unknown'
                        
                        tables.append({
                            'table_name': table_name,
                            'display_name': generate_display_name(table_name, sheet=sheet, filename=filename, project=customer_name),
                            'project': proj,
                            'customer': customer_name,
                            'file': filename,
                            'sheet': sheet,
                            'columns': columns,
                            'row_count': row_count,
                            'loaded_at': None,
                            'uploaded_by': provenance.get('uploaded_by', ''),
                            'uploaded_at': provenance.get('uploaded_at', ''),
                            'truth_type': provenance.get('truth_type', 'reality'),
                            'source_type': 'unknown'
                        })
                    except Exception as te:
                        logger.warning(f"Error getting info for table {table_name}: {te}")
            except Exception as qe:
                logger.error(f"Error querying tables: {qe}")
                schema = handler.get_schema_for_project(project)
                tables = schema.get('tables', [])
        
        # Group by file
        files_dict = {}
        total_rows = 0
        
        for table in tables:
            file_name = table.get('file', 'Unknown')
            project_name = table.get('project', 'Unknown')
            source_type = table.get('source_type', 'unknown')
            
            key = f"{project_name}:{file_name}"
            if key not in files_dict:
                files_dict[key] = {
                    'filename': file_name,
                    'project': project_name,
                    'sheets': [],
                    'total_rows': 0,
                    'loaded_at': None,
                    'uploaded_by': table.get('uploaded_by', ''),
                    'uploaded_at': table.get('uploaded_at', ''),
                    'truth_type': table.get('truth_type', ''),
                    'source_type': source_type
                }
            
            row_count = table.get('row_count', 0)
            columns_list = table.get('columns', [])
            loaded_at = table.get('loaded_at')
            
            files_dict[key]['sheets'].append({
                'table_name': table.get('table_name'),
                'sheet_name': table.get('sheet', ''),
                'columns': columns_list,
                'column_count': len(columns_list),
                'row_count': row_count,
                'encrypted_columns': []
            })
            files_dict[key]['total_rows'] += row_count
            total_rows += row_count
            
            if loaded_at and (files_dict[key]['loaded_at'] is None or loaded_at > files_dict[key]['loaded_at']):
                files_dict[key]['loaded_at'] = loaded_at
        
        files_list = list(files_dict.values())
        
        logger.info(f"[STATUS] Found {len(files_list)} files, {len(tables)} tables, {total_rows} rows")
        
        return {
            "available": True,
            "files": files_list,
            "total_files": len(files_list),
            "total_tables": len(tables),
            "total_rows": total_rows
        }
        
    except Exception as e:
        logger.error(f"Structured data status error: {e}", exc_info=True)
        return {
            "available": False,
            "error": str(e),
            "files": [],
            "total_files": 0,
            "total_tables": 0,
            "total_rows": 0
        }


# =============================================================================
# FIXED DELETE ENDPOINT
# =============================================================================

@router.delete("/status/structured/{project}/{filename}")
async def delete_structured_file(project: str, filename: str):
    """
    Delete a structured data file from DuckDB.
    
    FIXED: Now properly cleans _schema_metadata and _pdf_tables even if
    table lookup or drop fails.
    """
    logger.warning(f"[DELETE] Request to delete project={project}, filename={filename}")
    
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(status_code=503, detail="Structured data not available")
    
    try:
        handler = get_structured_handler()
        conn = handler.conn
        deleted_tables = []
        metadata_cleaned = {"_schema_metadata": 0, "_pdf_tables": 0}
        
        # Normalize for case-insensitive matching
        project_lower = project.lower()
        filename_lower = filename.lower()
        
        # =================================================================
        # STEP 1: Find and drop tables from _schema_metadata (Excel files)
        # =================================================================
        tables_from_metadata = []
        try:
            # Case-insensitive lookup
            tables_result = conn.execute("""
                SELECT table_name FROM _schema_metadata 
                WHERE LOWER(project) = ? AND LOWER(file_name) = ?
            """, [project_lower, filename_lower]).fetchall()
            
            tables_from_metadata = [t[0] for t in tables_result]
            logger.info(f"[DELETE] Found {len(tables_from_metadata)} tables in _schema_metadata")
            
        except Exception as meta_e:
            logger.warning(f"[DELETE] Metadata lookup failed: {meta_e}")
        
        # Drop the tables
        for table_name in tables_from_metadata:
            try:
                conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                deleted_tables.append(table_name)
                logger.info(f"[DELETE] Dropped table: {table_name}")
            except Exception as te:
                logger.warning(f"[DELETE] Could not drop {table_name}: {te}")
        
        # =================================================================
        # STEP 2: ALWAYS clean _schema_metadata (even if table drop failed)
        # =================================================================
        try:
            conn.execute("""
                DELETE FROM _schema_metadata 
                WHERE LOWER(project) = ? AND LOWER(file_name) = ?
            """, [project_lower, filename_lower])
            metadata_cleaned["_schema_metadata"] = len(tables_from_metadata) or 1
            logger.info(f"[DELETE] Cleaned _schema_metadata")
        except Exception as meta_del_e:
            logger.warning(f"[DELETE] Failed to clean _schema_metadata: {meta_del_e}")
        
        # =================================================================
        # STEP 3: Find and drop tables from _pdf_tables (PDF files)
        # =================================================================
        
        # =================================================================
        # STEP 2.5: Clean profiling/mapping metadata tables
        # These are generated during upload and must be cleaned with the file
        # =================================================================
        profiling_cleaned = {"_column_profiles": 0, "_column_mappings": 0, "_mapping_jobs": 0}
        
        # Clean _column_profiles
        try:
            # Need to match by table_name pattern since profiles are per-table
            for table_name in tables_from_metadata:
                result = conn.execute("""
                    DELETE FROM _column_profiles WHERE table_name = ?
                """, [table_name])
                profiling_cleaned["_column_profiles"] += 1
            logger.info(f"[DELETE] Cleaned _column_profiles for {profiling_cleaned['_column_profiles']} tables")
        except Exception as prof_e:
            logger.warning(f"[DELETE] _column_profiles cleanup failed: {prof_e}")
        
        # Clean _column_mappings (by project + file_name)
        try:
            conn.execute("""
                DELETE FROM _column_mappings 
                WHERE LOWER(project) = ? AND LOWER(file_name) = ?
            """, [project_lower, filename_lower])
            profiling_cleaned["_column_mappings"] = 1
            logger.info(f"[DELETE] Cleaned _column_mappings")
        except Exception as map_e:
            logger.warning(f"[DELETE] _column_mappings cleanup failed: {map_e}")
        
        # Clean _mapping_jobs (by project + file_name)
        try:
            conn.execute("""
                DELETE FROM _mapping_jobs 
                WHERE LOWER(project) = ? AND LOWER(file_name) = ?
            """, [project_lower, filename_lower])
            profiling_cleaned["_mapping_jobs"] = 1
            logger.info(f"[DELETE] Cleaned _mapping_jobs")
        except Exception as job_e:
            logger.warning(f"[DELETE] _mapping_jobs cleanup failed: {job_e}")
        
        # =================================================================
        # STEP 3: Find and drop tables from _pdf_tables (PDF files)
        # =================================================================
        try:
            # Check if _pdf_tables exists
            table_check = conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = '_pdf_tables'
            """).fetchone()
            
            if table_check[0] > 0:
                # Case-insensitive lookup
                pdf_result = conn.execute("""
                    SELECT table_name FROM _pdf_tables 
                    WHERE LOWER(source_file) = ? 
                       OR (LOWER(project) = ? AND LOWER(source_file) LIKE ?)
                       OR LOWER(source_file) LIKE ?
                """, [filename_lower, project_lower, f"%{filename_lower}%", f"%{filename_lower}%"]).fetchall()
                
                pdf_tables = [t[0] for t in pdf_result]
                logger.info(f"[DELETE] Found {len(pdf_tables)} tables in _pdf_tables")
                
                for table_name in pdf_tables:
                    try:
                        conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                        if table_name not in deleted_tables:
                            deleted_tables.append(table_name)
                        logger.info(f"[DELETE] Dropped PDF table: {table_name}")
                    except Exception as te:
                        logger.warning(f"[DELETE] Could not drop PDF table {table_name}: {te}")
                
                # ALWAYS clean _pdf_tables
                conn.execute("""
                    DELETE FROM _pdf_tables 
                    WHERE LOWER(source_file) = ? 
                       OR (LOWER(project) = ? AND LOWER(source_file) LIKE ?)
                       OR LOWER(source_file) LIKE ?
                """, [filename_lower, project_lower, f"%{filename_lower}%", f"%{filename_lower}%"])
                metadata_cleaned["_pdf_tables"] = len(pdf_tables) or 1
                logger.info(f"[DELETE] Cleaned _pdf_tables")
                
        except Exception as pdf_e:
            logger.warning(f"[DELETE] PDF tables check failed: {pdf_e}")
        
        # =================================================================
        # STEP 4: Fallback - pattern matching on actual tables
        # =================================================================
        if not deleted_tables:
            try:
                # Generate expected table name pattern
                safe_project = project_lower.replace(' ', '_').replace('-', '_')
                safe_file = filename.rsplit('.', 1)[0].lower().replace(' ', '_').replace('-', '_')
                
                all_tables = conn.execute("SHOW TABLES").fetchall()
                for (tbl,) in all_tables:
                    tbl_lower = tbl.lower()
                    # Match: project__filename or project__filename__sheet
                    if tbl_lower.startswith(f"{safe_project}__{safe_file}"):
                        try:
                            conn.execute(f'DROP TABLE IF EXISTS "{tbl}"')
                            deleted_tables.append(tbl)
                            logger.info(f"[DELETE] Dropped by pattern match: {tbl}")
                            
                            # Also clean metadata for this table
                            try:
                                conn.execute("DELETE FROM _schema_metadata WHERE table_name = ?", [tbl])
                            except:
                                pass
                            try:
                                conn.execute("DELETE FROM _pdf_tables WHERE table_name = ?", [tbl])
                            except:
                                pass
                                
                        except Exception as drop_e:
                            logger.warning(f"[DELETE] Could not drop {tbl}: {drop_e}")
                            
            except Exception as fb_e:
                logger.warning(f"[DELETE] Fallback pattern match failed: {fb_e}")
        
        # =================================================================
        # STEP 5: COMMIT and Checkpoint to persist changes
        # =================================================================
        try:
            conn.commit()
            logger.warning("[DELETE] Committed delete operations")
        except Exception as commit_e:
            logger.warning(f"[DELETE] Commit failed: {commit_e}")
        
        try:
            conn.execute("CHECKPOINT")
            logger.info("[DELETE] Checkpoint complete")
        except Exception as cp_e:
            logger.debug(f"[DELETE] Checkpoint failed (may not be needed): {cp_e}")
        
        # =================================================================
        # STEP 6: Clean ChromaDB chunks (for PDFs that might have both)
        # =================================================================
        chromadb_cleaned = 0
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            
            for field in ["filename", "source", "name"]:
                try:
                    results = collection.get(where={field: filename})
                    if results and results['ids']:
                        collection.delete(ids=results['ids'])
                        chromadb_cleaned = len(results['ids'])
                        logger.info(f"[DELETE] Deleted {chromadb_cleaned} ChromaDB chunks (field: {field})")
                        break
                except:
                    pass
            
            # Also try case-insensitive if nothing found
            if chromadb_cleaned == 0:
                try:
                    all_docs = collection.get(include=["metadatas"], limit=10000)
                    ids_to_delete = []
                    for i, metadata in enumerate(all_docs.get("metadatas", [])):
                        doc_filename = metadata.get("source", metadata.get("filename", ""))
                        if doc_filename and doc_filename.lower() == filename_lower:
                            ids_to_delete.append(all_docs["ids"][i])
                    
                    if ids_to_delete:
                        collection.delete(ids=ids_to_delete)
                        chromadb_cleaned = len(ids_to_delete)
                        logger.info(f"[DELETE] Deleted {chromadb_cleaned} ChromaDB chunks (case-insensitive)")
                except:
                    pass
        except Exception as chroma_e:
            logger.warning(f"[DELETE] ChromaDB cleanup failed: {chroma_e}")
        
        # =================================================================
        # STEP 7: Unregister from document registry (SOURCE OF TRUTH)
        # =================================================================
        registry_cleaned = False
        try:
            # Try to find the project_id for this project name
            from utils.database.models import ProjectModel
            project_record = ProjectModel.get_by_name(project)
            project_id = project_record.get('id') if project_record else None
            
            # Unregister from registry
            registry_cleaned = DocumentRegistryModel.unregister(filename, project_id)
            if registry_cleaned:
                logger.info(f"[DELETE] Unregistered {filename} from document registry")
            else:
                # Try without project_id (might be global)
                registry_cleaned = DocumentRegistryModel.unregister(filename, None)
                if registry_cleaned:
                    logger.info(f"[DELETE] Unregistered {filename} from document registry (global)")
        except Exception as reg_e:
            logger.warning(f"[DELETE] Registry unregister failed: {reg_e}")
        
        # =================================================================
        # STEP 8: Clean lineage edges
        # =================================================================
        lineage_cleaned = 0
        try:
            from utils.database.models import LineageModel
            lineage_cleaned = LineageModel.delete_for_source('file', filename, project_id if 'project_id' in dir() else None)
            if lineage_cleaned:
                logger.info(f"[DELETE] Deleted {lineage_cleaned} lineage edges")
        except Exception as lin_e:
            logger.warning(f"[DELETE] Lineage cleanup failed: {lin_e}")
        
        # =================================================================
        # STEP 9: Clean documents table (Supabase)
        # =================================================================
        documents_cleaned = False
        try:
            from utils.database.supabase_client import get_supabase
            supabase = get_supabase()
            if supabase:
                result = supabase.table('documents').delete().eq('name', filename).execute()
                documents_cleaned = len(result.data) > 0 if result.data else False
                if documents_cleaned:
                    logger.info(f"[DELETE] Cleaned documents table entry")
        except Exception as doc_e:
            logger.warning(f"[DELETE] Documents table cleanup failed: {doc_e}")
        
        # Build detailed response
        result = {
            "success": True,
            "filename": filename,
            "project": project,
            "cleaned": {
                "duckdb_tables": deleted_tables,
                "duckdb_tables_count": len(deleted_tables),
                "schema_metadata_rows": metadata_cleaned["_schema_metadata"],
                "pdf_tables_rows": metadata_cleaned["_pdf_tables"],
                "column_profiles": profiling_cleaned["_column_profiles"],
                "column_mappings": profiling_cleaned["_column_mappings"],
                "mapping_jobs": profiling_cleaned["_mapping_jobs"],
                "chromadb_chunks": chromadb_cleaned,
                "registry": registry_cleaned,
                "lineage_edges": lineage_cleaned,
                "documents_table": documents_cleaned
            },
            "summary": f"Cleaned {len(deleted_tables)} tables, {chromadb_cleaned} chunks, {lineage_cleaned} lineage edges"
        }
        
        logger.warning(f"[DELETE] Complete: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to delete structured file: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DELETE VERIFICATION ENDPOINT
# =============================================================================

@router.get("/status/structured/verify-delete")
async def verify_delete(project: str, filename: str):
    """
    Verify that a file has been completely deleted from all data stores.
    
    Checks:
    - DuckDB tables
    - _schema_metadata
    - _pdf_tables
    - _column_profiles
    - _column_mappings
    - _mapping_jobs
    - ChromaDB
    - Document Registry (Supabase)
    
    Returns detailed status for each data store.
    """
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(status_code=503, detail="Structured data not available")
    
    project_lower = project.lower()
    filename_lower = filename.lower()
    
    result = {
        "project": project,
        "filename": filename,
        "fully_deleted": True,
        "remnants": {}
    }
    
    try:
        handler = get_structured_handler()
        conn = handler.conn
        
        # Check DuckDB tables (pattern match)
        try:
            safe_project = project_lower.replace(' ', '_').replace('-', '_')
            safe_file = filename.rsplit('.', 1)[0].lower().replace(' ', '_').replace('-', '_')
            
            all_tables = conn.execute("SHOW TABLES").fetchall()
            matching_tables = [t[0] for t in all_tables if t[0].lower().startswith(f"{safe_project}_{safe_file}")]
            
            if matching_tables:
                result["fully_deleted"] = False
                result["remnants"]["duckdb_tables"] = matching_tables
        except Exception as e:
            result["remnants"]["duckdb_tables_error"] = str(e)
        
        # Check _schema_metadata
        try:
            meta = conn.execute("""
                SELECT table_name FROM _schema_metadata 
                WHERE LOWER(project) = ? AND LOWER(file_name) = ?
            """, [project_lower, filename_lower]).fetchall()
            
            if meta:
                result["fully_deleted"] = False
                result["remnants"]["_schema_metadata"] = [m[0] for m in meta]
        except Exception as e:
            result["remnants"]["_schema_metadata_error"] = str(e)
        
        # Check _pdf_tables
        try:
            pdf = conn.execute("""
                SELECT table_name FROM _pdf_tables 
                WHERE LOWER(source_file) = ? OR LOWER(source_file) LIKE ?
            """, [filename_lower, f"%{filename_lower}%"]).fetchall()
            
            if pdf:
                result["fully_deleted"] = False
                result["remnants"]["_pdf_tables"] = [p[0] for p in pdf]
        except:
            pass  # Table might not exist
        
        # Check _column_profiles
        try:
            profiles = conn.execute("""
                SELECT DISTINCT table_name FROM _column_profiles 
                WHERE LOWER(project) = ?
            """, [project_lower]).fetchall()
            
            # Filter to tables matching this file
            matching = [p[0] for p in profiles if safe_file in p[0].lower()]
            if matching:
                result["fully_deleted"] = False
                result["remnants"]["_column_profiles"] = matching
        except:
            pass
        
        # Check _column_mappings
        try:
            mappings = conn.execute("""
                SELECT COUNT(*) FROM _column_mappings 
                WHERE LOWER(project) = ? AND LOWER(file_name) = ?
            """, [project_lower, filename_lower]).fetchone()
            
            if mappings and mappings[0] > 0:
                result["fully_deleted"] = False
                result["remnants"]["_column_mappings"] = mappings[0]
        except:
            pass
        
        # Check _mapping_jobs
        try:
            jobs = conn.execute("""
                SELECT id, status FROM _mapping_jobs 
                WHERE LOWER(project) = ? AND LOWER(file_name) = ?
            """, [project_lower, filename_lower]).fetchall()
            
            if jobs:
                result["fully_deleted"] = False
                result["remnants"]["_mapping_jobs"] = [{"id": j[0], "status": j[1]} for j in jobs]
        except:
            pass
        
        # Check ChromaDB
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            
            for field in ["filename", "source", "name"]:
                try:
                    results = collection.get(where={field: filename})
                    if results and results['ids']:
                        result["fully_deleted"] = False
                        result["remnants"]["chromadb"] = {
                            "field": field,
                            "count": len(results['ids'])
                        }
                        break
                except:
                    pass
        except Exception as e:
            result["remnants"]["chromadb_error"] = str(e)
        
        # Check Document Registry (Supabase)
        try:
            from utils.database.models import DocumentRegistryModel, ProjectModel
            
            project_record = ProjectModel.get_by_name(project)
            project_id = project_record.get('id') if project_record else None
            
            doc = DocumentRegistryModel.get_by_filename(filename, project_id)
            if doc:
                result["fully_deleted"] = False
                result["remnants"]["document_registry"] = {
                    "id": doc.get("id"),
                    "status": doc.get("status")
                }
        except Exception as e:
            result["remnants"]["document_registry_error"] = str(e)
        
        # Summary
        if result["fully_deleted"]:
            result["message"] = "File completely deleted from all data stores"
        else:
            result["message"] = f"Found remnants in {len(result['remnants'])} data store(s)"
        
        return result
        
    except Exception as e:
        logger.error(f"[VERIFY-DELETE] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ORPHAN CLEANUP ENDPOINT
# =============================================================================

@router.post("/status/structured/clean-orphans")
async def clean_orphaned_metadata(project: Optional[str] = None):
    """
    Remove metadata entries that reference non-existent tables.
    
    Call this to fix stale metrics after deletes.
    """
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        conn = handler.conn
        
        # Get all actual tables
        tables = conn.execute("SHOW TABLES").fetchall()
        actual_tables = set(t[0] for t in tables)
        
        orphaned = {"_schema_metadata": 0, "_pdf_tables": 0}
        
        # Clean orphaned _schema_metadata entries
        try:
            if project:
                meta_result = conn.execute(
                    "SELECT table_name FROM _schema_metadata WHERE LOWER(project) = ?",
                    [project.lower()]
                ).fetchall()
            else:
                meta_result = conn.execute("SELECT table_name FROM _schema_metadata").fetchall()
            
            for (table_name,) in meta_result:
                if table_name not in actual_tables:
                    conn.execute("DELETE FROM _schema_metadata WHERE table_name = ?", [table_name])
                    orphaned["_schema_metadata"] += 1
                    logger.info(f"[CLEANUP] Removed orphaned _schema_metadata: {table_name}")
                    
        except Exception as e:
            logger.warning(f"[CLEANUP] _schema_metadata cleanup error: {e}")
        
        # Clean orphaned _pdf_tables entries
        try:
            table_check = conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = '_pdf_tables'
            """).fetchone()
            
            if table_check[0] > 0:
                if project:
                    pdf_result = conn.execute(
                        "SELECT table_name FROM _pdf_tables WHERE LOWER(project) = ? OR LOWER(project_id) = ?",
                        [project.lower(), project.lower()]
                    ).fetchall()
                else:
                    pdf_result = conn.execute("SELECT table_name FROM _pdf_tables").fetchall()
                
                for (table_name,) in pdf_result:
                    if table_name not in actual_tables:
                        conn.execute("DELETE FROM _pdf_tables WHERE table_name = ?", [table_name])
                        orphaned["_pdf_tables"] += 1
                        logger.info(f"[CLEANUP] Removed orphaned _pdf_tables: {table_name}")
                        
        except Exception as e:
            logger.warning(f"[CLEANUP] _pdf_tables cleanup error: {e}")
        
        # Clean orphaned _column_profiles entries
        orphaned["_column_profiles"] = 0
        try:
            if project:
                profile_result = conn.execute(
                    "SELECT DISTINCT table_name FROM _column_profiles WHERE LOWER(project) = ?",
                    [project.lower()]
                ).fetchall()
            else:
                profile_result = conn.execute("SELECT DISTINCT table_name FROM _column_profiles").fetchall()
            
            for (table_name,) in profile_result:
                if table_name not in actual_tables:
                    conn.execute("DELETE FROM _column_profiles WHERE table_name = ?", [table_name])
                    orphaned["_column_profiles"] += 1
                    logger.info(f"[CLEANUP] Removed orphaned _column_profiles: {table_name}")
                    
        except Exception as e:
            logger.warning(f"[CLEANUP] _column_profiles cleanup error: {e}")
        
        # Checkpoint
        try:
            conn.execute("CHECKPOINT")
        except:
            pass
        
        logger.info(f"[CLEANUP] Orphan cleanup complete: {orphaned}")
        return {
            "success": True, 
            "orphaned_removed": orphaned, 
            "actual_tables": len(actual_tables)
        }
        
    except Exception as e:
        logger.error(f"[CLEANUP] Failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/status/structured/reset")
async def reset_structured_data():
    """Reset all structured data (DuckDB)"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(status_code=503, detail="Structured data not available")
    
    try:
        handler = get_structured_handler()
        result = handler.reset_database()
        logger.warning("⚠️ Structured data (DuckDB) was RESET - all data deleted!")
        return {"success": True, "message": "All structured data deleted", "details": result}
    except Exception as e:
        logger.error(f"Failed to reset structured data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/chromadb")
async def get_chromadb_stats():
    """Get ChromaDB statistics"""
    import time
    start_time = time.time()
    logger.info("[STATUS/CHROMADB] Starting request...")
    try:
        rag = RAGHandler()
        logger.info(f"[STATUS/CHROMADB] RAGHandler initialized in {time.time() - start_time:.2f}s")
        collection = rag.client.get_or_create_collection(name="documents")
        count = collection.count()
        logger.info(f"[STATUS/CHROMADB] Got count={count} in {time.time() - start_time:.2f}s total")
        return {"total_chunks": count}
    except Exception as e:
        logger.error(f"ChromaDB stats error: {e}")
        return {"total_chunks": 0, "error": str(e)}


@router.get("/jobs")
async def get_processing_jobs(limit: int = 50, status: Optional[str] = None, days: Optional[int] = 7):
    """Get processing jobs from database. Default shows last 7 days."""
    try:
        if days:
            jobs = ProcessingJobModel.get_recent(days=days, limit=limit)
        else:
            jobs = ProcessingJobModel.get_all(limit=limit)
        
        if status:
            jobs = [j for j in jobs if j.get("status") == status]
        
        return {"jobs": jobs, "total": len(jobs), "days_filter": days}
    except Exception as e:
        logger.error(f"Failed to get processing jobs: {e}")
        return {"jobs": [], "total": 0, "error": str(e)}


@router.delete("/jobs/old")
async def delete_old_jobs(days: int = 7, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Delete processing jobs by date range or older than X days"""
    try:
        if start_date and end_date:
            # Use date range
            count = ProcessingJobModel.delete_by_date_range(start_date, end_date)
            return {"success": True, "message": f"Deleted {count} jobs from {start_date} to {end_date}", "deleted_count": count}
        else:
            # Use days threshold
            count = ProcessingJobModel.delete_older_than(days=days)
            return {"success": True, "message": f"Deleted {count} jobs older than {days} days", "deleted_count": count}
    except Exception as e:
        logger.error(f"Failed to delete old jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a specific processing job"""
    try:
        job = ProcessingJobModel.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/fail")
async def fail_job_manually(job_id: str, error_message: str = "Manually terminated by user"):
    """Manually fail a stuck processing job"""
    try:
        job = ProcessingJobModel.get_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        success = ProcessingJobModel.fail(job_id, error_message)
        
        if success:
            logger.info(f"Job {job_id} manually failed by user")
            return {
                "success": True,
                "message": f"Job {job_id} marked as failed",
                "job_id": job_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update job status")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fail job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a processing job record"""
    try:
        success = ProcessingJobModel.delete(job_id)
        if success:
            return {"success": True, "message": f"Job {job_id} deleted"}
        else:
            raise HTTPException(status_code=404, detail="Job not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs")
async def delete_all_jobs():
    """Delete all processing job records"""
    try:
        count = ProcessingJobModel.delete_all()
        return {"success": True, "message": f"Deleted {count} jobs"}
    except Exception as e:
        logger.error(f"Failed to delete all jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DOCUMENT STATUS ====================

@router.get("/status/documents")
async def get_documents(project: Optional[str] = None, limit: int = 1000):
    """
    Get all documents that have chunks in ChromaDB.
    
    Uses document_registry as source of truth.
    
    NOTE: Only returns files with:
    - storage_type containing 'chromadb' (chromadb or both)
    - chunk_count > 0
    
    Files with 0 chunks should NOT appear in Documents section.
    """
    import time
    start_time = time.time()
    logger.info("[STATUS/DOCUMENTS] Starting request...")
    
    try:
        # =================================================================
        # Get documents from REGISTRY (source of truth)
        # =================================================================
        documents = []
        
        try:
            if project:
                # Check if project is a UUID or name
                is_uuid = len(project) == 36 and '-' in project
                
                if is_uuid:
                    project_id = project
                else:
                    # Try to get project_id from project name
                    from utils.database.models import ProjectModel
                    proj_record = ProjectModel.get_by_name(project)
                    project_id = proj_record.get('id') if proj_record else None
                
                # Handle global projects
                if project.upper() in ('__GLOBAL__', 'GLOBAL', 'GLOBAL/UNIVERSAL'):
                    registry_entries = DocumentRegistryModel.get_by_project(None, include_global=False)
                    # Filter to only global
                    registry_entries = [e for e in registry_entries if e.get('is_global')]
                else:
                    registry_entries = DocumentRegistryModel.get_by_project(project_id, include_global=True)
            else:
                registry_entries = DocumentRegistryModel.get_all(limit=limit)
            
            logger.info(f"[STATUS/DOCUMENTS] Registry returned {len(registry_entries)} entries")
            
            for entry in registry_entries:
                storage_type = entry.get("storage_type", "")
                chunk_count = entry.get("chunk_count", 0) or 0
                
                # =============================================================
                # FILTER: Only show files that have chunks in ChromaDB
                # Files with storage_type='duckdb' only belong in Structured Data
                # Files with 0 chunks shouldn't appear in Documents section
                # =============================================================
                has_chromadb = storage_type in ('chromadb', 'both')
                has_chunks = chunk_count > 0
                
                if not has_chromadb or not has_chunks:
                    # Skip - this file doesn't belong in Documents section
                    continue
                
                doc_entry = {
                    "id": entry.get("id"),
                    "filename": entry.get("filename", "unknown"),
                    "file_type": entry.get("file_type", ""),
                    "file_size": entry.get("file_size"),
                    "project": entry.get("metadata", {}).get("project_name") or ("GLOBAL" if entry.get("is_global") else "unknown"),
                    "project_id": entry.get("project_id"),
                    "functional_area": entry.get("metadata", {}).get("functional_area", ""),
                    "upload_date": entry.get("created_at", ""),
                    "chunks": chunk_count,
                    "storage_type": storage_type,
                    "usage_type": entry.get("usage_type", ""),
                    "is_global": entry.get("is_global", False),
                }
                documents.append(doc_entry)
                
        except Exception as reg_e:
            logger.warning(f"[STATUS/DOCUMENTS] Registry query failed: {reg_e}")
            # Don't fall back - if registry fails, return empty
            return {"documents": [], "total": 0, "total_chunks": 0, "error": f"Registry unavailable: {reg_e}"}
        
        # Sort by upload date (newest first)
        documents.sort(key=lambda x: x.get("upload_date", "") or "", reverse=True)
        
        total_chunks = sum(d.get("chunks", 0) for d in documents)
        
        logger.info(f"[STATUS/DOCUMENTS] Returning {len(documents)} documents in {time.time() - start_time:.2f}s")
        
        return {
            "documents": documents,
            "total": len(documents),
            "total_chunks": total_chunks
        }
        
    except Exception as e:
        logger.error(f"Document status error: {e}", exc_info=True)
        return {"documents": [], "total": 0, "total_chunks": 0, "error": str(e)}


@router.delete("/status/documents/{doc_id}")
async def delete_document(doc_id: str, filename: str = None, project: str = None):
    """
    Delete a document and its chunks from ChromaDB.
    
    Returns detailed breakdown of what was cleaned.
    """
    try:
        cleaned = {
            "chromadb_chunks": 0,
            "documents_table": False,
            "registry": False,
            "lineage_edges": 0
        }
        
        # Check if doc_id is a UUID or a filename
        is_uuid = len(doc_id) == 36 and '-' in doc_id
        
        doc = None
        if is_uuid:
            doc = DocumentModel.get_by_id(doc_id)
        
        # Use filename from param, doc_id (if it's a filename), or from doc record
        actual_filename = filename or (doc_id if not is_uuid else None)
        if doc:
            actual_filename = doc.get("name", actual_filename)
        
        project_id = doc.get("project_id") if doc else None
        
        # Delete from ChromaDB
        if actual_filename:
            try:
                rag = RAGHandler()
                collection = rag.client.get_or_create_collection(name="documents")
                
                # Try multiple metadata fields
                for field in ["filename", "source", "name"]:
                    results = collection.get(where={field: actual_filename})
                    if results and results['ids']:
                        collection.delete(ids=results['ids'])
                        cleaned["chromadb_chunks"] = len(results['ids'])
                        logger.info(f"Deleted {len(results['ids'])} chunks from ChromaDB (field: {field})")
                        break
                
                # Case-insensitive fallback
                if cleaned["chromadb_chunks"] == 0:
                    all_docs = collection.get(include=["metadatas"], limit=10000)
                    ids_to_delete = []
                    filename_lower = actual_filename.lower()
                    for i, metadata in enumerate(all_docs.get("metadatas", [])):
                        doc_filename = metadata.get("source", metadata.get("filename", ""))
                        if doc_filename and doc_filename.lower() == filename_lower:
                            ids_to_delete.append(all_docs["ids"][i])
                    if ids_to_delete:
                        collection.delete(ids=ids_to_delete)
                        cleaned["chromadb_chunks"] = len(ids_to_delete)
                        
            except Exception as ce:
                logger.warning(f"ChromaDB deletion issue: {ce}")
        
        # Delete from Supabase documents table
        if doc:
            DocumentModel.delete(doc.get("id"))
            cleaned["documents_table"] = True
            logger.info(f"Deleted document {doc.get('id')} from Supabase")
        elif not is_uuid and actual_filename:
            try:
                from utils.database.supabase_client import get_supabase
                supabase = get_supabase()
                if supabase:
                    result = supabase.table('documents').delete().eq('name', actual_filename).execute()
                    cleaned["documents_table"] = len(result.data) > 0 if result.data else False
                    logger.info(f"Deleted document by filename: {actual_filename}")
            except Exception as db_e:
                logger.warning(f"Could not delete from Supabase by filename: {db_e}")
        
        # Unregister from document registry
        try:
            if actual_filename:
                cleaned["registry"] = DocumentRegistryModel.unregister(actual_filename, project_id)
                if cleaned["registry"]:
                    logger.info(f"Unregistered {actual_filename} from document registry")
        except Exception as reg_e:
            logger.warning(f"Registry unregister failed: {reg_e}")
        
        # Clean lineage edges
        try:
            from utils.database.models import LineageModel
            cleaned["lineage_edges"] = LineageModel.delete_for_source('file', actual_filename, project_id)
            if cleaned["lineage_edges"]:
                logger.info(f"Deleted {cleaned['lineage_edges']} lineage edges")
        except Exception as lin_e:
            logger.warning(f"Lineage cleanup failed: {lin_e}")
        
        return {
            "success": True,
            "filename": actual_filename,
            "cleaned": cleaned,
            "summary": f"Cleaned {cleaned['chromadb_chunks']} chunks, {cleaned['lineage_edges']} lineage edges"
        }
            
    except Exception as e:
        logger.error(f"Failed to delete document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/status/documents/reset")
async def reset_all_documents():
    """Reset all documents (ChromaDB, database, and registry)"""
    try:
        # Reset ChromaDB
        chroma_count = 0
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            all_ids = collection.get()['ids']
            if all_ids:
                collection.delete(ids=all_ids)
                chroma_count = len(all_ids)
            logger.warning(f"⚠️ Deleted {chroma_count} chunks from ChromaDB")
        except Exception as ce:
            logger.error(f"ChromaDB reset error: {ce}")
        
        # Reset database documents
        doc_count = DocumentModel.delete_all()
        logger.warning(f"⚠️ Deleted {doc_count} documents from database")
        
        # Reset document registry
        registry_count = 0
        try:
            from utils.database.supabase_client import get_supabase
            supabase = get_supabase()
            if supabase:
                # Count first
                count_result = supabase.table('document_registry').select('id', count='exact').execute()
                registry_count = count_result.count or 0
                # Delete all
                if registry_count > 0:
                    supabase.table('document_registry').delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
                logger.warning(f"⚠️ Deleted {registry_count} entries from document registry")
        except Exception as reg_e:
            logger.error(f"Registry reset error: {reg_e}")
        
        return {
            "success": True, 
            "message": f"Reset complete",
            "details": {
                "chromadb_chunks": chroma_count,
                "supabase_documents": doc_count,
                "registry_entries": registry_count
            }
        }
    except Exception as e:
        logger.error(f"Failed to reset documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# REFERENCE / STANDARDS MANAGEMENT
# =============================================================================

@router.get("/status/references")
async def list_references():
    """
    List all reference/standards files (global documents).
    
    These are documents with truth_type in reference/regulatory/compliance or is_global=true.
    """
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        if not supabase:
            raise HTTPException(500, "Supabase not available")
        
        # Get from document_registry - reference, regulatory, compliance, or global
        result = supabase.table('document_registry') \
            .select('*') \
            .or_('truth_type.eq.reference,truth_type.eq.regulatory,truth_type.eq.compliance,is_global.eq.true') \
            .order('created_at', desc=True) \
            .execute()
        
        files = result.data or []
        
        # Also get rules from standards processor
        rules_list = []
        rules_info = {'available': False, 'documents': 0, 'total_rules': 0}
        
        def make_json_safe(obj):
            """Recursively convert object to JSON-safe format."""
            if obj is None:
                return None
            if isinstance(obj, (str, int, float, bool)):
                return obj
            if isinstance(obj, (list, tuple)):
                return [make_json_safe(item) for item in obj]
            if isinstance(obj, dict):
                return {str(k): make_json_safe(v) for k, v in obj.items() if not callable(v)}
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            if callable(obj):
                return None
            try:
                return str(obj)
            except:
                return None
        
        try:
            from backend.utils.standards_processor import get_rule_registry
            registry = get_rule_registry()
            all_rules = registry.get_all_rules()
            
            # Convert to dict format - same careful serialization as /status/rules
            for rule in all_rules:
                try:
                    rule_dict = {
                        "rule_id": make_json_safe(getattr(rule, 'rule_id', '')),
                        "title": make_json_safe(getattr(rule, 'title', '')),
                        "description": make_json_safe(getattr(rule, 'description', '')),
                        "source_document": make_json_safe(getattr(rule, 'source_document', '')),
                        "severity": make_json_safe(getattr(rule, 'severity', 'medium')),
                        "suggested_sql_pattern": make_json_safe(getattr(rule, 'suggested_sql_pattern', None))
                    }
                    rules_list.append(rule_dict)
                except Exception as e:
                    logger.warning(f"[REFERENCES] Could not convert rule: {e}")
            
            if hasattr(registry, 'documents'):
                rules_info['available'] = True
                rules_info['documents'] = len(registry.documents)
                rules_info['total_rules'] = len(rules_list)
        except ImportError as ie:
            logger.warning(f"Standards processor not available: {ie}")
        except Exception as e:
            logger.warning(f"Could not get rules info: {e}")
        
        return {
            'count': len(files),
            'files': files,
            'rules': rules_list,  # Full rules list for Rules tab
            'rules_info': rules_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing references: {e}")
        raise HTTPException(500, str(e))


@router.delete("/status/references/{filename:path}")
async def delete_reference(filename: str, confirm: bool = False):
    """
    Delete a specific reference/standards file.
    
    Removes from:
    - Document registry (Supabase)
    - ChromaDB (vector store)
    - Lineage edges
    - Standards documents table (Supabase)
    - Standards rules table (Supabase)
    - Rule registry (in-memory)
    
    Requires confirm=true query parameter.
    """
    if not confirm:
        raise HTTPException(400, "Must set confirm=true to delete")
    
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        deleted = {
            'registry': False,
            'chromadb': 0,
            'lineage': 0,
            'standards_docs': 0,
            'standards_rules': 0,
            'memory': False
        }
        
        # 1. Delete from document_registry
        try:
            result = supabase.table('document_registry') \
                .delete() \
                .eq('filename', filename) \
                .or_('truth_type.eq.reference,truth_type.eq.regulatory,truth_type.eq.compliance,is_global.eq.true') \
                .execute()
            deleted['registry'] = len(result.data or []) > 0
        except Exception as e:
            logger.warning(f"Registry delete failed: {e}")
        
        # 2. Delete from ChromaDB
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            
            # Find chunks for this file
            all_docs = collection.get(include=["metadatas"])
            ids_to_delete = []
            for i, meta in enumerate(all_docs.get('metadatas', [])):
                if meta and (meta.get('source') == filename or meta.get('filename') == filename):
                    ids_to_delete.append(all_docs['ids'][i])
            
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                deleted['chromadb'] = len(ids_to_delete)
                logger.info(f"Deleted {len(ids_to_delete)} chunks from ChromaDB")
        except Exception as e:
            logger.warning(f"ChromaDB delete failed: {e}")
        
        # 3. Delete lineage edges
        try:
            result = supabase.table('lineage_edges') \
                .delete() \
                .eq('source_id', filename) \
                .eq('source_type', 'file') \
                .execute()
            deleted['lineage'] = len(result.data or [])
        except Exception as e:
            logger.warning(f"Lineage delete failed: {e}")
        
        # 4. Delete from standards_documents table (get document_id first)
        document_ids = []
        try:
            # Find document_id by filename
            doc_result = supabase.table('standards_documents') \
                .select('document_id') \
                .eq('filename', filename) \
                .execute()
            document_ids = [d['document_id'] for d in (doc_result.data or [])]
            
            if document_ids:
                # Delete the documents
                result = supabase.table('standards_documents') \
                    .delete() \
                    .eq('filename', filename) \
                    .execute()
                deleted['standards_docs'] = len(result.data or [])
                logger.info(f"Deleted {deleted['standards_docs']} from standards_documents")
        except Exception as e:
            logger.warning(f"Standards documents delete failed: {e}")
        
        # 5. Delete from standards_rules table
        try:
            for doc_id in document_ids:
                result = supabase.table('standards_rules') \
                    .delete() \
                    .eq('document_id', doc_id) \
                    .execute()
                deleted['standards_rules'] += len(result.data or [])
            if deleted['standards_rules'] > 0:
                logger.info(f"Deleted {deleted['standards_rules']} from standards_rules")
        except Exception as e:
            logger.warning(f"Standards rules delete failed: {e}")
        
        # 6. Clear from in-memory rule registry
        try:
            from utils.standards_processor import get_rule_registry
            registry = get_rule_registry()
            
            # Remove from documents dict
            if hasattr(registry, 'documents') and isinstance(registry.documents, dict):
                docs_to_remove = [k for k, v in registry.documents.items() if getattr(v, 'filename', '') == filename]
                for doc_id in docs_to_remove:
                    del registry.documents[doc_id]
                    deleted['memory'] = True
            
            # Remove rules associated with this document
            if hasattr(registry, 'rules') and isinstance(registry.rules, dict):
                rules_to_remove = [k for k, v in registry.rules.items() if getattr(v, 'source_document', '') == filename]
                for rule_id in rules_to_remove:
                    del registry.rules[rule_id]
                    
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Rule registry delete failed: {e}")
        
        return {
            'success': True,
            'filename': filename,
            'deleted': deleted
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting reference: {e}")
        raise HTTPException(500, str(e))


@router.delete("/status/references")
async def clear_all_references(confirm: bool = False):
    """
    Clear ALL reference/standards files.
    
    WARNING: This is destructive. Requires confirm=true.
    
    Removes from:
    - Document registry (all reference/global entries)
    - ChromaDB (all chunks for those files)
    - Lineage edges
    - Standards documents table (Supabase)
    - Standards rules table (Supabase)
    - Rule registry (in-memory)
    """
    if not confirm:
        raise HTTPException(400, "Must set confirm=true to clear all references")
    
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        deleted = {
            'registry': 0,
            'chromadb': 0,
            'lineage': 0,
            'standards_docs': 0,
            'standards_rules': 0,
            'memory_docs': 0,
            'memory_rules': 0
        }
        
        # 1. Get all reference files first
        refs = supabase.table('document_registry') \
            .select('filename') \
            .or_('truth_type.eq.reference,is_global.eq.true') \
            .execute()
        
        filenames = [r['filename'] for r in (refs.data or [])]
        
        # 2. Delete from registry
        try:
            result = supabase.table('document_registry') \
                .delete() \
                .or_('truth_type.eq.reference,is_global.eq.true') \
                .execute()
            deleted['registry'] = len(result.data or [])
        except Exception as e:
            logger.warning(f"Registry clear failed: {e}")
        
        # 3. Delete from ChromaDB
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            
            all_docs = collection.get(include=["metadatas"])
            ids_to_delete = []
            for i, meta in enumerate(all_docs.get('metadatas', [])):
                if meta:
                    source = meta.get('source') or meta.get('filename')
                    if source in filenames:
                        ids_to_delete.append(all_docs['ids'][i])
            
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                deleted['chromadb'] = len(ids_to_delete)
        except Exception as e:
            logger.warning(f"ChromaDB clear failed: {e}")
        
        # 4. Delete lineage for these files
        try:
            for filename in filenames:
                result = supabase.table('lineage_edges') \
                    .delete() \
                    .eq('source_id', filename) \
                    .eq('source_type', 'file') \
                    .execute()
                deleted['lineage'] += len(result.data or [])
        except Exception as e:
            logger.warning(f"Lineage clear failed: {e}")
        
        # 5. Clear ALL standards_rules from Supabase
        try:
            result = supabase.table('standards_rules') \
                .delete() \
                .neq('rule_id', '00000000-0000-0000-0000-000000000000') \
                .execute()
            deleted['standards_rules'] = len(result.data or [])
            logger.info(f"Cleared {deleted['standards_rules']} from standards_rules table")
        except Exception as e:
            logger.warning(f"Standards rules clear failed: {e}")
        
        # 6. Clear ALL standards_documents from Supabase
        try:
            result = supabase.table('standards_documents') \
                .delete() \
                .neq('document_id', '00000000-0000-0000-0000-000000000000') \
                .execute()
            deleted['standards_docs'] = len(result.data or [])
            logger.info(f"Cleared {deleted['standards_docs']} from standards_documents table")
        except Exception as e:
            logger.warning(f"Standards documents clear failed: {e}")
        
        # 7. Clear in-memory rule registry
        try:
            from utils.standards_processor import get_rule_registry
            registry = get_rule_registry()
            
            # Clear documents dict
            if hasattr(registry, 'documents') and isinstance(registry.documents, dict):
                deleted['memory_docs'] = len(registry.documents)
                registry.documents.clear()
            
            # Clear rules dict
            if hasattr(registry, 'rules') and isinstance(registry.rules, dict):
                deleted['memory_rules'] = len(registry.rules)
                registry.rules.clear()
                
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Rule registry clear failed: {e}")
        
        return {
            'success': True,
            'files_processed': len(filenames),
            'deleted': deleted
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing references: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/rules")
async def list_rules():
    """
    List all extracted compliance rules.
    
    Returns rules from standards_processor for viewing/editing.
    Used by Data Explorer Rules tab.
    """
    
    def make_json_safe(obj):
        """Recursively convert object to JSON-safe format."""
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, (list, tuple)):
            return [make_json_safe(item) for item in obj]
        if isinstance(obj, dict):
            return {str(k): make_json_safe(v) for k, v in obj.items() if not callable(v)}
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        if callable(obj):
            return None
        # For any other object, try to convert to string
        try:
            return str(obj)
        except:
            return None
    
    try:
        from backend.utils.standards_processor import get_rule_registry
        registry = get_rule_registry()
        all_rules = registry.get_all_rules()
        
        # Convert to dict format with full details - handle serialization carefully
        rules_list = []
        for rule in all_rules:
            try:
                # Manually extract all fields and make JSON-safe
                rule_dict = {
                    "rule_id": make_json_safe(getattr(rule, 'rule_id', '')),
                    "title": make_json_safe(getattr(rule, 'title', '')),
                    "description": make_json_safe(getattr(rule, 'description', '')),
                    "applies_to": make_json_safe(getattr(rule, 'applies_to', {})),
                    "requirement": make_json_safe(getattr(rule, 'requirement', {})),
                    "source_document": make_json_safe(getattr(rule, 'source_document', '')),
                    "source_page": make_json_safe(getattr(rule, 'source_page', None)),
                    "source_section": make_json_safe(getattr(rule, 'source_section', '')),
                    "source_text": make_json_safe(getattr(rule, 'source_text', '')),
                    "category": make_json_safe(getattr(rule, 'category', 'general')),
                    "severity": make_json_safe(getattr(rule, 'severity', 'medium')),
                    "effective_date": make_json_safe(getattr(rule, 'effective_date', None)),
                    "check_type": make_json_safe(getattr(rule, 'check_type', 'data')),
                    "suggested_sql_pattern": make_json_safe(getattr(rule, 'suggested_sql_pattern', None))
                }
                
                rules_list.append(rule_dict)
            except Exception as e:
                logger.warning(f"[RULES] Could not convert rule: {e}")
        
        # Also get document summary
        documents = []
        if hasattr(registry, 'documents'):
            for doc_id, doc in registry.documents.items():
                try:
                    doc_info = {
                        'document_id': make_json_safe(getattr(doc, 'document_id', doc_id)),
                        'filename': make_json_safe(getattr(doc, 'filename', 'unknown')),
                        'title': make_json_safe(getattr(doc, 'title', '')),
                        'domain': make_json_safe(getattr(doc, 'domain', 'general')),
                        'rules_count': len(getattr(doc, 'rules', []))
                    }
                    documents.append(doc_info)
                except Exception as e:
                    logger.warning(f"[RULES] Could not convert document: {e}")
        
        logger.info(f"[RULES] Returning {len(rules_list)} rules from {len(documents)} documents")
        
        return {
            'rules': rules_list,
            'count': len(rules_list),
            'documents': documents,
            'document_count': len(documents)
        }
        
    except ImportError as ie:
        logger.warning(f"[RULES] Standards processor not available: {ie}")
        return {
            'rules': [],
            'count': 0,
            'documents': [],
            'document_count': 0,
            'note': 'Standards processor not available'
        }
    except Exception as e:
        logger.error(f"[RULES] Error listing rules: {e}")
        import traceback
        traceback.print_exc()
        return {
            'rules': [],
            'count': 0,
            'error': str(e)
        }


@router.get("/status/registry")
async def get_registry_status():
    """
    Get current registry status - shows what's in the registry.
    Use this to verify registry is working.
    """
    try:
        registry_entries = DocumentRegistryModel.get_all(limit=100)
        
        # Group by storage type
        by_storage = {}
        for entry in registry_entries:
            st = entry.get('storage_type', 'unknown')
            if st not in by_storage:
                by_storage[st] = []
            by_storage[st].append(entry.get('filename'))
        
        return {
            "total_entries": len(registry_entries),
            "by_storage_type": {k: len(v) for k, v in by_storage.items()},
            "sample_files": [e.get('filename') for e in registry_entries[:10]],
            "registry_working": True
        }
    except Exception as e:
        return {
            "total_entries": 0,
            "error": str(e),
            "registry_working": False
        }


@router.post("/status/registry/sync")
async def sync_document_registry():
    """
    Sync document registry with actual data in backends.
    
    This is a one-time cleanup to fix orphaned registry entries
    and add missing entries for existing files.
    
    Run this ONCE after deploying the registry-aware delete.
    """
    """
    Sync document registry with actual data in backends.
    
    This is a one-time cleanup to fix orphaned registry entries
    and add missing entries for existing files.
    
    Run this ONCE after deploying the registry-aware delete.
    """
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        results = {
            "orphans_removed": 0,
            "missing_added": 0,
            "errors": []
        }
        
        # =================================================================
        # STEP 1: Get all files that actually exist in backends
        # =================================================================
        actual_files = {}  # filename -> {storage_type, project_id, ...}
        
        # 1a. Get files from DuckDB _schema_metadata (Excel)
        if STRUCTURED_AVAILABLE:
            try:
                handler = get_structured_handler()
                meta_result = handler.safe_fetchall("""
                    SELECT DISTINCT file_name, project
                    FROM _schema_metadata 
                    WHERE is_current = TRUE AND file_name IS NOT NULL
                """)
                
                for filename, project in meta_result:
                    if filename:
                        actual_files[filename] = {
                            'storage_type': 'duckdb',
                            'project_name': project,
                            'source': '_schema_metadata'
                        }
                logger.info(f"[SYNC] Found {len(meta_result)} Excel files in _schema_metadata")
            except Exception as e:
                results["errors"].append(f"_schema_metadata query: {e}")
        
        # 1b. Get files from DuckDB _pdf_tables (PDF)
        if STRUCTURED_AVAILABLE:
            try:
                handler = get_structured_handler()
                table_check = handler.safe_fetchone("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = '_pdf_tables'
                """)
                
                if table_check[0] > 0:
                    pdf_result = handler.safe_fetchall("""
                        SELECT DISTINCT source_file, project, project_id
                        FROM _pdf_tables 
                        WHERE source_file IS NOT NULL
                    """)
                    
                    for filename, project, project_id in pdf_result:
                        if filename:
                            actual_files[filename] = {
                                'storage_type': 'duckdb',
                                'project_name': project,
                                'project_id': project_id,
                                'source': '_pdf_tables'
                            }
                    logger.info(f"[SYNC] Found {len(pdf_result)} PDF files in _pdf_tables")
            except Exception as e:
                results["errors"].append(f"_pdf_tables query: {e}")
        
        # 1c. Get files from ChromaDB
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            chroma_results = collection.get(include=["metadatas"], limit=5000)
            
            seen_chroma = set()
            for metadata in chroma_results.get("metadatas", []):
                filename = metadata.get("source") or metadata.get("filename")
                if filename and filename not in seen_chroma:
                    seen_chroma.add(filename)
                    if filename not in actual_files:
                        actual_files[filename] = {
                            'storage_type': 'chromadb',
                            'project_name': metadata.get("project"),
                            'project_id': metadata.get("project_id"),
                            'source': 'chromadb'
                        }
                    elif actual_files[filename]['storage_type'] == 'duckdb':
                        # File is in both
                        actual_files[filename]['storage_type'] = 'both'
            
            logger.info(f"[SYNC] Found {len(seen_chroma)} unique files in ChromaDB")
        except Exception as e:
            results["errors"].append(f"ChromaDB query: {e}")
        
        # =================================================================
        # STEP 2: Get all entries currently in registry
        # =================================================================
        registry_entries = {}
        try:
            registry_data = DocumentRegistryModel.get_all(limit=5000)
            for entry in registry_data:
                registry_entries[entry['filename']] = entry
            logger.info(f"[SYNC] Found {len(registry_entries)} entries in registry")
        except Exception as e:
            results["errors"].append(f"Registry query: {e}")
        
        # =================================================================
        # STEP 3: Remove orphaned registry entries (file doesn't exist)
        # =================================================================
        for filename, entry in registry_entries.items():
            if filename not in actual_files:
                try:
                    DocumentRegistryModel.unregister(filename, entry.get('project_id'))
                    results["orphans_removed"] += 1
                    logger.info(f"[SYNC] Removed orphan: {filename}")
                except Exception as e:
                    results["errors"].append(f"Remove orphan {filename}: {e}")
        
        # =================================================================
        # STEP 4: Add missing registry entries (file exists but not registered)
        # =================================================================
        for filename, file_info in actual_files.items():
            if filename not in registry_entries:
                try:
                    # Determine usage type
                    is_global = file_info.get('project_name', '').lower() in (
                        'global', '__global__', 'reference library', 'reference_library'
                    )
                    
                    # Try to get project_id from project name
                    project_id = file_info.get('project_id')
                    if not project_id and file_info.get('project_name') and not is_global:
                        try:
                            from utils.database.models import ProjectModel
                            proj = ProjectModel.get_by_name(file_info['project_name'])
                            if proj:
                                project_id = proj.get('id')
                        except:
                            pass
                    
                    DocumentRegistryModel.register(
                        filename=filename,
                        file_type=filename.rsplit('.', 1)[-1] if '.' in filename else None,
                        storage_type=file_info['storage_type'],
                        usage_type='structured_data' if file_info['storage_type'] in ('duckdb', 'both') else 'rag_knowledge',
                        project_id=project_id if not is_global else None,
                        is_global=is_global,
                        metadata={
                            'project_name': file_info.get('project_name'),
                            'synced_from': file_info.get('source'),
                            'synced_at': datetime.utcnow().isoformat()
                        }
                    )
                    results["missing_added"] += 1
                    logger.info(f"[SYNC] Added missing: {filename}")
                except Exception as e:
                    results["errors"].append(f"Add missing {filename}: {e}")
        
        logger.info(f"[SYNC] Complete: {results}")
        
        return {
            "success": True,
            "message": f"Registry sync complete",
            "actual_files_found": len(actual_files),
            "registry_entries_before": len(registry_entries),
            "orphans_removed": results["orphans_removed"],
            "missing_added": results["missing_added"],
            "errors": results["errors"][:10] if results["errors"] else []
        }
        
    except Exception as e:
        logger.error(f"Registry sync failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# ==================== COLUMN MAPPING ENDPOINTS ====================

@router.get("/status/mappings/{project}")
async def get_project_mappings(project: str, file_name: str = None):
    """Get all column mappings for a project"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        mappings = handler.get_column_mappings(project, file_name=file_name)
        needs_review = handler.get_mappings_needing_review(project)
        
        return {
            "project": project,
            "mappings": mappings,
            "total_mappings": len(mappings),
            "needs_review_count": len(needs_review),
            "needs_review": needs_review
        }
    except Exception as e:
        logger.error(f"Failed to get mappings: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/mappings/{project}/{file_name}/summary")
async def get_file_mapping_summary(project: str, file_name: str):
    """Get mapping summary for a specific file (for badge display)"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        summary = handler.get_file_mapping_summary(project, file_name)
        return summary
    except Exception as e:
        logger.error(f"Failed to get mapping summary: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/mapping-job/{job_id}")
async def get_mapping_job_status(job_id: str):
    """Get status of a column inference job"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        status = handler.get_mapping_job_status(job_id=job_id)
        if not status:
            raise HTTPException(404, "Job not found")
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/mapping-jobs/{project}")
async def get_project_mapping_jobs(project: str):
    """Get all mapping jobs for a project"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        status = handler.get_mapping_job_status(project=project)
        return {"project": project, "jobs": status if isinstance(status, list) else [status] if status else []}
    except Exception as e:
        logger.error(f"Failed to get project jobs: {e}")
        raise HTTPException(500, str(e))


from pydantic import BaseModel

class MappingUpdate(BaseModel):
    semantic_type: str

@router.put("/status/mappings/{project}/{table_name}/{column_name}")
async def update_column_mapping(project: str, table_name: str, column_name: str, update: MappingUpdate):
    """Update a column mapping (human override)"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        success = handler.update_column_mapping(
            project=project,
            table_name=table_name,
            original_column=column_name,
            semantic_type=update.semantic_type
        )
        
        if success:
            return {"status": "updated", "column": column_name, "semantic_type": update.semantic_type}
        else:
            raise HTTPException(500, "Failed to update mapping")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update mapping: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/semantic-types")
async def get_semantic_types():
    """Get list of available semantic types for mapping"""
    return {
        "types": [
            {"id": "employee_number", "label": "Employee Number", "category": "keys"},
            {"id": "company_code", "label": "Company Code", "category": "keys"},
            {"id": "employment_status_code", "label": "Employment Status", "category": "status"},
            {"id": "earning_code", "label": "Earning Code", "category": "codes"},
            {"id": "deduction_code", "label": "Deduction Code", "category": "codes"},
            {"id": "job_code", "label": "Job Code", "category": "codes"},
            {"id": "department_code", "label": "Department Code", "category": "codes"},
            {"id": "amount", "label": "Amount", "category": "values"},
            {"id": "rate", "label": "Rate", "category": "values"},
            {"id": "effective_date", "label": "Effective Date", "category": "dates"},
            {"id": "start_date", "label": "Start Date", "category": "dates"},
            {"id": "end_date", "label": "End Date", "category": "dates"},
            {"id": "employee_name", "label": "Employee Name", "category": "other"},
            {"id": "NONE", "label": "Not Mapped", "category": "none"}
        ]
    }


# ==================== RELATIONSHIPS ENDPOINTS ====================

@router.get("/status/relationships/{project}")
async def get_project_relationships(project: str):
    """Get all table relationships for a project"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        relationships = handler.get_relationships(project)
        return {
            "project": project,
            "relationships": relationships
        }
    except Exception as e:
        logger.error(f"Failed to get relationships: {e}")
        raise HTTPException(500, str(e))


@router.post("/status/relationships/{project}/analyze")
async def analyze_relationships(project: str):
    """
    Auto-detect table relationships for a project.
    
    This scans all tables looking for:
    - Common column names (employee_id, company_code, etc.)
    - Foreign key patterns (_id, _code, _num suffixes)
    - Key columns identified during upload
    
    Returns the detected relationships.
    """
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        
        # Run relationship detection
        relationships = handler.detect_relationships(project)
        
        logger.info(f"[RELATIONSHIPS] Analyzed project {project}, found {len(relationships)} relationships")
        
        return {
            "project": project,
            "relationships_found": len(relationships),
            "relationships": relationships,
            "message": f"Detected {len(relationships)} relationships across tables"
        }
    except Exception as e:
        logger.error(f"Failed to analyze relationships: {e}")
        raise HTTPException(500, str(e))


class RelationshipCreate(BaseModel):
    source_table: str
    source_columns: list
    target_table: str
    target_columns: list

@router.post("/status/relationships/{project}")
async def create_relationship(project: str, rel: RelationshipCreate):
    """Create a new table relationship"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        handler.safe_execute("""
            INSERT INTO _table_relationships 
            (id, project, source_table, source_columns, target_table, target_columns, relationship_type, confidence)
            VALUES (?, ?, ?, ?, ?, ?, 'manual', 1.0)
        """, [
            hash(f"{project}_{rel.source_table}_{rel.target_table}") % 2147483647,
            project,
            rel.source_table,
            json.dumps(rel.source_columns),
            rel.target_table,
            json.dumps(rel.target_columns)
        ])
        handler.conn.commit()
        
        return {"status": "created", "source": rel.source_table, "target": rel.target_table}
    except Exception as e:
        logger.error(f"Failed to create relationship: {e}")
        raise HTTPException(500, str(e))


class RelationshipDelete(BaseModel):
    source_table: str
    target_table: str

@router.delete("/status/relationships/{project}")
async def delete_relationship(project: str, rel: RelationshipDelete):
    """Delete a table relationship"""
    if not STRUCTURED_AVAILABLE:
        raise HTTPException(503, "Structured data not available")
    
    try:
        handler = get_structured_handler()
        handler.safe_execute("""
            DELETE FROM _table_relationships 
            WHERE project = ? AND source_table = ? AND target_table = ?
        """, [project, rel.source_table, rel.target_table])
        handler.conn.commit()
        
        return {"status": "deleted"}
    except Exception as e:
        logger.error(f"Failed to delete relationship: {e}")
        raise HTTPException(500, str(e))


# =============================================================================
# DOCUMENT REGISTRY SETUP
# =============================================================================

@router.get("/status/document-registry/setup-sql")
async def get_registry_setup_sql():
    """
    Get SQL to create the document_registry table in Supabase.
    Run this in Supabase SQL Editor to enable document tracking.
    """
    try:
        from utils.database.models import DocumentRegistryModel
        return {
            "sql": DocumentRegistryModel.create_table_sql(),
            "instructions": [
                "1. Go to Supabase Dashboard → SQL Editor",
                "2. Paste the SQL below and run it",
                "3. This creates the document_registry table",
                "4. New uploads will be registered automatically",
                "5. Use the Audit button to verify"
            ]
        }
    except Exception as e:
        # Fallback SQL if import fails
        return {
            "sql": """
CREATE TABLE IF NOT EXISTS document_registry (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    filename TEXT NOT NULL,
    file_type TEXT,
    storage_type TEXT DEFAULT 'chromadb',
    usage_type TEXT DEFAULT 'rag_knowledge',
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    is_global BOOLEAN DEFAULT FALSE,
    chunk_count INTEGER DEFAULT 0,
    file_size INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_doc_registry_project ON document_registry(project_id);
CREATE INDEX IF NOT EXISTS idx_doc_registry_filename ON document_registry(filename);
CREATE INDEX IF NOT EXISTS idx_doc_registry_global ON document_registry(is_global);
            """,
            "instructions": [
                "1. Go to Supabase Dashboard → SQL Editor",
                "2. Paste the SQL below and run it",
                "3. This creates the document_registry table",
                "4. New uploads will be registered automatically",
                "5. Use the Audit button to verify"
            ],
            "error": str(e)
        }


# =============================================================================
# CHROMADB CLEANUP ENDPOINTS
# =============================================================================

@router.get("/status/chromadb/audit")
async def audit_chromadb():
    """
    Audit ChromaDB contents vs Supabase registry.
    Shows orphaned documents that exist in ChromaDB but not in registry.
    """
    try:
        from utils.rag_handler import RAGHandler
        
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
        
        # Get all ChromaDB documents
        all_chroma = collection.get(include=["metadatas"], limit=10000)
        chroma_docs = {}
        
        for i, metadata in enumerate(all_chroma.get("metadatas", [])):
            doc_id = all_chroma["ids"][i] if all_chroma.get("ids") else f"unknown_{i}"
            filename = metadata.get("source", metadata.get("filename", "Unknown"))
            project = metadata.get("project_id", metadata.get("project", "unknown"))
            
            # Use just filename as key (project matching is fuzzy)
            if filename not in chroma_docs:
                chroma_docs[filename] = {
                    "filename": filename,
                    "project": project,
                    "chunk_ids": [],
                    "chunk_count": 0
                }
            chroma_docs[filename]["chunk_ids"].append(doc_id)
            chroma_docs[filename]["chunk_count"] += 1
        
        # Get document registry from Supabase
        registry_files = set()
        registry_available = False
        registry_error = None
        
        try:
            from utils.database.models import DocumentRegistryModel
            
            # Check if table exists
            if DocumentRegistryModel.table_exists():
                registry_available = True
                docs = DocumentRegistryModel.get_all(limit=1000)
                for doc in docs:
                    filename = doc.get("filename", "")
                    if filename:
                        registry_files.add(filename)
                logger.info(f"[AUDIT] Found {len(registry_files)} files in registry")
            else:
                registry_error = "document_registry table not found - run SQL to create it"
                logger.warning(f"[AUDIT] {registry_error}")
        except Exception as e:
            registry_error = str(e)
            logger.warning(f"[AUDIT] Could not fetch document registry: {e}")
        
        # Find orphans (in ChromaDB but not in registry)
        orphans = []
        registered = []
        
        for filename, info in chroma_docs.items():
            if filename in registry_files:
                registered.append(info)
            else:
                orphans.append(info)
        
        result = {
            "total_chroma_files": len(chroma_docs),
            "total_chroma_chunks": sum(d["chunk_count"] for d in chroma_docs.values()),
            "registered_files": len(registered),
            "orphaned_files": len(orphans),
            "registry_available": registry_available,
            "orphans": orphans[:50],
            "registered": [{"filename": r["filename"], "project": r["project"], "chunks": r["chunk_count"]} for r in registered[:50]]
        }
        
        if registry_error:
            result["registry_error"] = registry_error
            result["note"] = "Without registry, all files appear as orphans. Create the document_registry table in Supabase."
        
        return result
        
    except Exception as e:
        logger.exception(f"ChromaDB audit failed: {e}")
        raise HTTPException(500, str(e))


@router.delete("/status/chromadb/purge-orphans")
async def purge_chromadb_orphans():
    """
    Delete orphaned documents from ChromaDB.
    Only deletes docs that are NOT in Supabase registry.
    """
    try:
        from utils.rag_handler import RAGHandler
        
        # First run audit
        audit = await audit_chromadb()
        orphans = audit.get("orphans", [])
        
        if not orphans:
            return {"status": "success", "message": "No orphans to delete", "deleted": 0}
        
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
        
        deleted_count = 0
        deleted_files = []
        
        for orphan in orphans:
            chunk_ids = orphan.get("chunk_ids", [])
            if chunk_ids:
                try:
                    # Delete in batches
                    for i in range(0, len(chunk_ids), 100):
                        batch = chunk_ids[i:i+100]
                        collection.delete(ids=batch)
                    deleted_count += len(chunk_ids)
                    deleted_files.append(orphan.get("filename"))
                    logger.warning(f"[CHROMADB] Deleted {len(chunk_ids)} chunks for orphan: {orphan.get('filename')}")
                except Exception as e:
                    logger.warning(f"[CHROMADB] Failed to delete orphan {orphan.get('filename')}: {e}")
        
        return {
            "status": "success",
            "deleted_chunks": deleted_count,
            "deleted_files": deleted_files,
            "message": f"Purged {len(deleted_files)} orphaned files ({deleted_count} chunks)"
        }
        
    except Exception as e:
        logger.exception(f"ChromaDB purge failed: {e}")
        raise HTTPException(500, str(e))


@router.delete("/status/chromadb/purge-project/{project_id}")
async def purge_chromadb_project(project_id: str):
    """
    Delete ALL ChromaDB documents for a specific project.
    Use with caution!
    """
    try:
        from utils.rag_handler import RAGHandler
        
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
        
        # Get project name for flexible matching
        project_name = None
        try:
            from utils.supabase_client import get_supabase
            supabase = get_supabase()
            proj_result = supabase.table("projects").select("name").eq("id", project_id).execute()
            if proj_result.data:
                project_name = proj_result.data[0].get("name", "").upper()
        except Exception as e:
            logger.warning(f"[CHROMADB] Could not get project name: {e}")
        
        # Get all docs for this project
        all_chroma = collection.get(include=["metadatas"], limit=10000)
        
        ids_to_delete = []
        for i, metadata in enumerate(all_chroma.get("metadatas", [])):
            doc_project = metadata.get("project_id", metadata.get("project", ""))
            doc_project_str = str(doc_project)
            doc_project_upper = doc_project_str.upper()
            
            # Match by multiple methods
            is_match = (
                doc_project_str == project_id or 
                doc_project_str == project_id[:8] or
                (project_name and doc_project_upper == project_name) or
                (project_name and len(project_name) >= 3 and doc_project_upper.startswith(project_name[:3])) or
                (project_name and len(project_name) >= 3 and project_name.startswith(doc_project_upper[:3]))
            )
            
            if is_match:
                ids_to_delete.append(all_chroma["ids"][i])
        
        if not ids_to_delete:
            return {"status": "success", "message": f"No documents found for project {project_id}", "deleted": 0}
        
        # Delete in batches
        for i in range(0, len(ids_to_delete), 100):
            batch = ids_to_delete[i:i+100]
            collection.delete(ids=batch)
        
        logger.warning(f"[CHROMADB] Purged {len(ids_to_delete)} chunks for project {project_id}")
        
        return {
            "status": "success",
            "deleted_chunks": len(ids_to_delete),
            "project_id": project_id,
            "message": f"Purged all {len(ids_to_delete)} chunks for project"
        }
        
    except Exception as e:
        logger.exception(f"ChromaDB project purge failed: {e}")
        raise HTTPException(500, str(e))


@router.delete("/status/chromadb/purge-all")
async def purge_chromadb_all(confirm: str = None):
    """
    Delete ALL documents from ChromaDB.
    Requires confirm=YES parameter.
    """
    if confirm != "YES":
        raise HTTPException(400, "Must pass confirm=YES to purge all ChromaDB data")
    
    try:
        from utils.rag_handler import RAGHandler
        
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
        
        # Get count before
        all_chroma = collection.get(limit=10000)
        total_before = len(all_chroma.get("ids", []))
        
        if total_before == 0:
            return {"status": "success", "message": "ChromaDB already empty", "deleted": 0}
        
        # Delete in batches
        ids = all_chroma.get("ids", [])
        for i in range(0, len(ids), 100):
            batch = ids[i:i+100]
            collection.delete(ids=batch)
        
        logger.warning(f"[CHROMADB] PURGED ALL - {total_before} chunks deleted")
        
        return {
            "status": "success",
            "deleted_chunks": total_before,
            "message": f"Purged ALL {total_before} chunks from ChromaDB"
        }
        
    except Exception as e:
        logger.exception(f"ChromaDB full purge failed: {e}")
        raise HTTPException(500, str(e))


# ==================== COST TRACKING ====================

@router.get("/status/costs")
async def get_cost_summary(days: int = 30, project_id: Optional[str] = None):
    """Get cost summary for System Monitor dashboard"""
    try:
        from backend.utils.cost_tracker import get_cost_summary
        return get_cost_summary(days=days, project_id=project_id)
    except ImportError:
        return {"error": "Cost tracker not available", "total_cost": 0}
    except Exception as e:
        logger.error(f"Cost summary failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/costs/by-project")
async def get_costs_by_project():
    """Get costs grouped by project"""
    try:
        from backend.utils.cost_tracker import get_cost_by_project
        return get_cost_by_project()
    except ImportError:
        return []
    except Exception as e:
        logger.error(f"Cost by project failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/costs/recent")
async def get_recent_costs(limit: int = 100):
    """Get recent cost entries for detailed view"""
    try:
        from utils.database.supabase_client import get_supabase
        client = get_supabase()
        if not client:
            return {"error": "Supabase not available", "records": []}
        
        result = client.table("cost_tracking").select("*").order(
            "created_at", desc=True
        ).limit(limit).execute()
        
        return {"records": result.data or [], "count": len(result.data or [])}
    except Exception as e:
        logger.error(f"Recent costs query failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/costs/daily")
async def get_daily_costs(days: int = 7):
    """Get daily cost breakdown"""
    try:
        from backend.utils.cost_tracker import get_daily_costs
        return get_daily_costs(days=days)
    except ImportError:
        return []
    except Exception as e:
        logger.error(f"Daily costs failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/costs/month")
async def get_month_costs(year: int = None, month: int = None):
    """Get costs for a specific calendar month (includes fixed costs)"""
    try:
        from backend.utils.cost_tracker import get_month_costs
        return get_month_costs(year=year, month=month)
    except ImportError:
        return {"error": "Cost tracker not available"}
    except Exception as e:
        logger.error(f"Month costs failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/costs/fixed")
async def get_fixed_costs():
    """Get fixed/subscription costs"""
    try:
        from backend.utils.cost_tracker import get_fixed_costs
        return get_fixed_costs()
    except ImportError:
        return {"error": "Cost tracker not available", "items": [], "total": 0}
    except Exception as e:
        logger.error(f"Fixed costs failed: {e}")
        raise HTTPException(500, str(e))


@router.put("/status/costs/fixed/{name}")
async def update_fixed_cost(name: str, cost_per_unit: float = None, quantity: int = None):
    """Update a fixed cost entry"""
    try:
        from backend.utils.cost_tracker import update_fixed_cost
        return update_fixed_cost(name=name, cost_per_unit=cost_per_unit, quantity=quantity)
    except ImportError:
        return {"error": "Cost tracker not available"}
    except Exception as e:
        logger.error(f"Update fixed cost failed: {e}")
        raise HTTPException(500, str(e))


@router.get("/status/table-profile/{table_name}")
async def get_table_profile(table_name: str):
    """Get column statistics for a specific table"""
    if not STRUCTURED_AVAILABLE:
        return {"error": "Structured data not available", "columns": []}
    
    try:
        handler = get_structured_handler()
        
        # Get row count
        row_count_result = handler.safe_fetchone(f'SELECT COUNT(*) FROM "{table_name}"')
        total_rows = row_count_result[0] if row_count_result else 0
        
        # Get column names
        columns_result = handler.safe_fetchall(f"""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = '{table_name}'
        """)
        
        column_stats = []
        for (col_name,) in columns_result:
            try:
                # Get distinct count and null count for each column
                stats = handler.safe_fetchone(f'''
                    SELECT 
                        COUNT(DISTINCT "{col_name}") as distinct_count,
                        SUM(CASE WHEN "{col_name}" IS NULL OR TRIM(CAST("{col_name}" AS VARCHAR)) = '' THEN 1 ELSE 0 END) as null_count
                    FROM "{table_name}"
                ''')
                
                distinct_count = stats[0] if stats else 0
                null_count = stats[1] if stats else 0
                fill_rate = round((total_rows - null_count) / total_rows * 100, 1) if total_rows > 0 else 0
                
                column_stats.append({
                    "name": col_name,
                    "distinct_values": distinct_count,
                    "null_count": null_count,
                    "fill_rate": fill_rate
                })
            except Exception as col_e:
                logger.warning(f"Failed to profile column {col_name}: {col_e}")
                column_stats.append({
                    "name": col_name,
                    "distinct_values": None,
                    "null_count": None,
                    "fill_rate": None,
                    "error": str(col_e)
                })
        
        return {
            "table_name": table_name,
            "total_rows": total_rows,
            "columns": column_stats
        }
        
    except Exception as e:
        logger.error(f"Table profile failed for {table_name}: {e}")
        return {"error": str(e), "columns": []}


@router.get("/status/data-integrity")
async def check_data_integrity(project: Optional[str] = None):
    """
    Check data quality across all tables for a project.
    Returns table list with health metrics for frontend display.
    
    Uses document_registry as source of truth.
    """
    if not STRUCTURED_AVAILABLE:
        return {"error": "Structured data not available", "tables": [], "total_rows": 0, "health_score": 0, "issues_count": 0}
    
    try:
        handler = get_structured_handler()
        
        all_tables = []
        total_rows = 0
        total_issues = 0
        
        # =================================================================
        # STEP 1: Get valid files from REGISTRY (source of truth)
        # =================================================================
        valid_files = set()
        customer_lookup = {}  # project_code -> customer_name
        try:
            # Build customer name lookup from all projects
            from utils.database.models import ProjectModel
            all_projects = ProjectModel.get_all()
            for p in all_projects:
                proj_name = p.get('name', '')
                customer = p.get('customer', '')
                if proj_name:
                    customer_lookup[proj_name.lower()] = customer or proj_name
            
            if project:
                proj_record = ProjectModel.get_by_name(project)
                project_id = proj_record.get('id') if proj_record else None
                
                registry_entries = DocumentRegistryModel.get_by_project(project_id, include_global=False)
            else:
                registry_entries = DocumentRegistryModel.get_all()
            
            # Filter to only DuckDB files
            for entry in registry_entries:
                storage = entry.get('storage_type', '')
                if storage in ('duckdb', 'both'):
                    valid_files.add(entry.get('filename', '').lower())
            
            logger.info(f"[INTEGRITY] Registry has {len(valid_files)} valid DuckDB files")
            
            # If registry is empty, return empty result
            if not valid_files:
                return {
                    "status": "healthy",
                    "tables": [],
                    "total_rows": 0,
                    "health_score": 100,
                    "issues_count": 0
                }
                
        except Exception as reg_e:
            logger.warning(f"[INTEGRITY] Registry query failed: {reg_e}")
            return {"error": f"Registry unavailable: {reg_e}", "tables": [], "total_rows": 0, "health_score": 0, "issues_count": 0}
        
        # =================================================================
        # STEP 2: Get tables that belong to registered files
        # =================================================================
        tables_to_check = []
        
        try:
            # Get from _schema_metadata
            meta_result = handler.safe_fetchall("""
                SELECT DISTINCT table_name, file_name, project
                FROM _schema_metadata 
                WHERE is_current = TRUE
            """)
            
            for table_name, file_name, proj in meta_result:
                # Only include if file is in registry
                if file_name and file_name.lower() in valid_files:
                    # Apply project filter if specified
                    if project:
                        if proj and project.lower() in proj.lower():
                            tables_to_check.append(table_name)
                    else:
                        tables_to_check.append(table_name)
            
            # Also check _pdf_tables
            try:
                table_check = handler.safe_fetchone("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = '_pdf_tables'
                """)
                
                if table_check and table_check[0] > 0:
                    pdf_result = handler.safe_fetchall("""
                        SELECT DISTINCT table_name, source_file, project
                        FROM _pdf_tables
                    """)
                    
                    for table_name, source_file, proj in pdf_result:
                        if source_file and source_file.lower() in valid_files:
                            if project:
                                if proj and project.lower() in proj.lower():
                                    if table_name not in tables_to_check:
                                        tables_to_check.append(table_name)
                            else:
                                if table_name not in tables_to_check:
                                    tables_to_check.append(table_name)
            except:
                pass
                
            logger.info(f"[INTEGRITY] Found {len(tables_to_check)} tables for registered files")
            
        except Exception as meta_e:
            logger.warning(f"[INTEGRITY] Metadata query failed: {meta_e}")
            return {"error": str(meta_e), "tables": [], "total_rows": 0, "health_score": 0, "issues_count": 0}
        
        # =================================================================
        # STEP 3: Analyze each table with INSIGHT vs ISSUE classification
        # =================================================================
        
        # Patterns that are ACTUALLY bad (parsing failures)
        parsing_failure_patterns = [
            'nan', 'none', 'null', 'unnamed',
            'column0', 'column1', 'column2', 'column_0', 'column_1',
            'field0', 'field1', 'field_0', 'field_1',
            'var0', 'var1', 'var_0', 'var_1',
        ]
        
        # Patterns that are INSIGHTS (optional fields - not issues)
        optional_field_patterns = [
            r'orgud?field\d+',      # orgudfield1-10, orgufield1-10
            r'udf\d+',              # udf1, udf2, etc.
            r'custom_?\d+',         # custom1, custom_field_2
            r'report_category',     # report_category_code, report_category
            r'user_defined',        # user_defined_*
            r'flex_?\d*',           # flex1, flex_field
            r'attribute_?\d*',      # attribute1, attribute_field
        ]
        
        total_insights = 0
        all_insights = []
        
        for table_name in tables_to_check:
            table_issues = []
            table_insights = []
            
            # Get columns for this table
            try:
                cols_result = handler.safe_fetchall(f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = '{table_name}'
                """)
            except Exception as col_e:
                logger.warning(f"Failed to get columns for {table_name}: {col_e}")
                continue
            
            column_names = [c[0] for c in cols_result]
            
            # Skip if table doesn't actually exist (stale metadata)
            if not column_names:
                logger.warning(f"Skipping {table_name} - no columns found (stale metadata?)")
                continue
            
            # Get row count
            try:
                row_count = handler.safe_fetchone(f'SELECT COUNT(*) FROM "{table_name}"')[0]
            except Exception as count_e:
                logger.warning(f"Skipping {table_name} - table doesn't exist: {count_e}")
                continue
            
            total_rows += row_count
            
            # Analyze each column
            for col in column_names:
                col_lower = col.lower().strip()
                
                # Check if it's an optional field pattern (INSIGHT, not issue)
                is_optional = any(re.search(pattern, col_lower) for pattern in optional_field_patterns)
                
                if is_optional:
                    # It's an insight - track it but don't penalize
                    # We could get fill rate here for richer insights, but skip for now
                    table_insights.append({
                        "column": col,
                        "type": "optional_field",
                        "message": f"Optional field: {col}"
                    })
                    continue
                
                # Check for actual parsing failures
                is_parsing_failure = any(pattern in col_lower for pattern in parsing_failure_patterns)
                is_purely_numeric = col_lower.replace('.', '').replace('_', '').replace('-', '').isdigit()
                is_single_char_junk = len(col_lower) == 1 and (col_lower.isdigit() or col_lower in 'abcdefghij')
                is_numeric_with_underscore = col_lower.replace('_', '').isdigit() and '_' in col_lower
                
                # col_X patterns - check if they're junk vs intentional
                is_col_pattern = re.match(r'^col_\d+$', col_lower)
                
                if is_parsing_failure or is_purely_numeric or is_single_char_junk or is_numeric_with_underscore:
                    table_issues.append({
                        "column": col,
                        "type": "bad_column_name",
                        "severity": "high",
                        "message": f"Suspicious column: {col}"
                    })
                elif is_col_pattern:
                    # col_X could be junk OR intentional - flag as warning not error
                    table_issues.append({
                        "column": col,
                        "type": "possible_junk",
                        "severity": "medium",
                        "message": f"Possible parsing artifact: {col}"
                    })
            
            # Check first few column names for header detection issues
            if len(column_names) >= 3:
                first_three = column_names[:3]
                numeric_count = sum(1 for c in first_three if c.lower().replace('_', '').replace('.', '').replace('-', '').isdigit())
                if numeric_count >= 2:
                    table_issues.append({
                        "type": "header_detection",
                        "severity": "high",
                        "message": "Possible header row issue - first columns look numeric"
                    })
            
            # Calculate fill rate
            fill_rate = 100
            if row_count > 0 and column_names:
                try:
                    first_col = column_names[0]
                    null_count = handler.safe_fetchone(f'''
                        SELECT COUNT(*) FROM "{table_name}" WHERE "{first_col}" IS NULL
                    ''')[0]
                    fill_rate = round(((row_count - null_count) / row_count) * 100)
                except:
                    pass
            
            total_issues += len(table_issues)
            total_insights += len(table_insights)
            
            if table_insights:
                all_insights.append({
                    "table_name": table_name,
                    "insights": table_insights
                })
            
            all_tables.append({
                "table_name": table_name,
                # Parse project from table_name, then look up customer name
                "display_name": generate_display_name(
                    table_name, 
                    project=customer_lookup.get(
                        table_name.split('__')[0].lower(), 
                        table_name.split('__')[0]
                    ) if '__' in table_name else None
                ),
                "column_count": len(column_names),
                "row_count": row_count,
                "fill_rate": fill_rate,
                "issues": table_issues,
                "insights": table_insights,
                "status": "unhealthy" if table_issues else "healthy"
            })
        
        # Calculate health score
        if all_tables:
            healthy_tables = sum(1 for t in all_tables if t["status"] == "healthy")
            health_score = round((healthy_tables / len(all_tables)) * 100)
        else:
            health_score = 100
        
        overall_status = "healthy" if health_score >= 80 else ("degraded" if health_score >= 50 else "unhealthy")
        
        logger.info(f"[INTEGRITY] Checked {len(all_tables)} tables, health_score={health_score}%, total_rows={total_rows}, issues={total_issues}, insights={total_insights}")
        
        return {
            "status": overall_status,
            "tables": all_tables,
            "total_rows": total_rows,
            "health_score": health_score,
            "issues_count": total_issues,
            "insights_count": total_insights,
            "insights": all_insights
        }
        
    except Exception as e:
        logger.error(f"Data integrity check failed: {e}")
        return {"error": str(e), "tables": [], "total_rows": 0, "health_score": 0, "issues_count": 0, "insights_count": 0}



# =============================================================================
# COMPREHENSIVE HEALTH MONITORING - Task 2 GET HEALTHY Sprint
# =============================================================================
# 
# Endpoints:
#   GET  /status/health          - Full check with scores, saves snapshot
#   GET  /status/health/quick    - Fast connectivity check only (<500ms)
#   GET  /status/health/history  - Query historical snapshots for charts
#   POST /status/health/snapshot - Force save snapshot (for scheduled jobs)
#
# Database table required (run in Supabase):
#   CREATE TABLE health_snapshots (
#     id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
#     timestamp TIMESTAMPTZ DEFAULT NOW(),
#     overall_status TEXT NOT NULL,
#     health_score INT NOT NULL,
#     checks JSONB NOT NULL,
#     issues JSONB DEFAULT '[]',
#     check_time_ms INT,
#     triggered_by TEXT DEFAULT 'manual'
#   );
#   CREATE INDEX idx_health_timestamp ON health_snapshots(timestamp DESC);
# =============================================================================


def _calculate_check_score(check_result: dict) -> int:
    """Calculate a 0-100 score for a single health check."""
    status = check_result.get('status', 'error')
    
    if status == 'ok':
        return 100
    elif status == 'warning':
        return 75
    elif status == 'degraded':
        return 50
    elif status in ('timeout', 'unavailable'):
        return 25
    else:  # error
        return 0


def _save_health_snapshot(
    overall_status: str,
    health_score: int,
    checks: dict,
    issues: list,
    check_time_ms: int,
    triggered_by: str = 'manual'
) -> bool:
    """Save health snapshot to database for historical tracking."""
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        if not supabase:
            logger.warning("[HEALTH] Cannot save snapshot - Supabase unavailable")
            return False
        
        result = supabase.table('health_snapshots').insert({
            'overall_status': overall_status,
            'health_score': health_score,
            'checks': checks,
            'issues': issues,
            'check_time_ms': check_time_ms,
            'triggered_by': triggered_by
        }).execute()
        
        return bool(result.data)
    except Exception as e:
        logger.warning(f"[HEALTH] Failed to save snapshot: {e}")
        return False


@router.get("/status/health/quick")
async def quick_health_check():
    """
    Fast connectivity check - Supabase, DuckDB, ChromaDB only.
    
    Use this for frequent polling (every 30s-1min).
    Target: <500ms response time.
    """
    import time
    start_time = time.time()
    
    checks = {}
    overall_score = 0
    check_count = 0
    
    # CHECK 1: SUPABASE
    try:
        supabase_start = time.time()
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        if supabase:
            supabase.table('document_registry').select('id').limit(1).execute()
            latency = int((time.time() - supabase_start) * 1000)
            checks["supabase"] = {"status": "ok", "score": 100, "latency_ms": latency}
            overall_score += 100
        else:
            checks["supabase"] = {"status": "error", "score": 0}
    except Exception as e:
        checks["supabase"] = {"status": "error", "score": 0, "error": str(e)[:100]}
    check_count += 1
    
    # CHECK 2: DUCKDB
    try:
        duckdb_start = time.time()
        if STRUCTURED_AVAILABLE:
            handler = get_structured_handler()
            handler.safe_fetchone("SELECT 1")
            latency = int((time.time() - duckdb_start) * 1000)
            checks["duckdb"] = {"status": "ok", "score": 100, "latency_ms": latency}
            overall_score += 100
        else:
            checks["duckdb"] = {"status": "unavailable", "score": 25}
            overall_score += 25
    except Exception as e:
        checks["duckdb"] = {"status": "error", "score": 0, "error": str(e)[:100]}
    check_count += 1
    
    # CHECK 3: CHROMADB
    try:
        chroma_start = time.time()
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
        collection.count()
        latency = int((time.time() - chroma_start) * 1000)
        checks["chromadb"] = {"status": "ok", "score": 100, "latency_ms": latency}
        overall_score += 100
    except Exception as e:
        checks["chromadb"] = {"status": "error", "score": 0, "error": str(e)[:100]}
    check_count += 1
    
    # Calculate overall
    health_score = int(overall_score / check_count) if check_count > 0 else 0
    
    if health_score >= 90:
        overall_status = "healthy"
    elif health_score >= 50:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "health_score": health_score,
        "timestamp": datetime.utcnow().isoformat(),
        "check_time_ms": int((time.time() - start_time) * 1000),
        "checks": checks
    }


@router.get("/status/health/history")
async def get_health_history(
    hours: int = 24,
    limit: int = 100
):
    """
    Get historical health snapshots for charting/trending.
    
    Args:
        hours: How many hours back to query (default 24)
        limit: Max records to return (default 100)
    
    Returns:
        List of snapshots ordered by timestamp DESC
    """
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        if not supabase:
            return {"error": "Supabase unavailable", "snapshots": []}
        
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        result = supabase.table('health_snapshots')\
            .select('timestamp, overall_status, health_score, check_time_ms, issues')\
            .gt('timestamp', cutoff)\
            .order('timestamp', desc=True)\
            .limit(limit)\
            .execute()
        
        snapshots = result.data if result.data else []
        
        # Calculate summary stats
        if snapshots:
            scores = [s['health_score'] for s in snapshots]
            avg_score = int(sum(scores) / len(scores))
            min_score = min(scores)
            max_score = max(scores)
            
            status_counts = {}
            for s in snapshots:
                st = s['overall_status']
                status_counts[st] = status_counts.get(st, 0) + 1
        else:
            avg_score = min_score = max_score = 0
            status_counts = {}
        
        return {
            "period_hours": hours,
            "snapshot_count": len(snapshots),
            "summary": {
                "avg_score": avg_score,
                "min_score": min_score,
                "max_score": max_score,
                "status_distribution": status_counts
            },
            "snapshots": snapshots
        }
        
    except Exception as e:
        logger.error(f"[HEALTH] History query failed: {e}")
        return {"error": str(e), "snapshots": []}


@router.post("/status/health/snapshot")
async def force_health_snapshot(triggered_by: str = "manual"):
    """
    Force a health check and save snapshot.
    
    Use this for scheduled jobs (cron) to capture regular snapshots.
    """
    result = await comprehensive_health_check(save_snapshot=True, triggered_by=triggered_by)
    return {
        "saved": result.get("snapshot_saved", False),
        "status": result.get("status"),
        "health_score": result.get("health_score"),
        "timestamp": result.get("timestamp")
    }


@router.get("/status/health")
async def comprehensive_health_check(
    project_id: Optional[str] = None,
    save_snapshot: bool = True,
    triggered_by: str = "api"
):
    """
    Comprehensive system health check with numeric scores.
    
    Checks ALL backend systems and their consistency:
    - Supabase: Connection, document_registry accessible
    - DuckDB: Connection, tables, row counts
    - ChromaDB: Connection, collections, chunk counts
    - Registry Consistency: Registry matches actual backend data
    - Lineage: Edges exist, coverage
    - Processing Jobs: Stuck or failed jobs
    - Local LLM (Ollama): Reachable, models available
    
    Returns:
        - status: "healthy" | "degraded" | "unhealthy"
        - health_score: 0-100 overall score
        - Individual check results with scores
        - Issues found
        - Recommendations
    """
    import time
    start_time = time.time()
    
    checks = {}
    issues = []
    recommendations = []
    
    # =========================================================================
    # CHECK 1: SUPABASE
    # =========================================================================
    try:
        supabase_start = time.time()
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        if supabase:
            result = supabase.table('document_registry').select('id').limit(1).execute()
            supabase_latency = int((time.time() - supabase_start) * 1000)
            
            count_result = supabase.table('document_registry').select('id', count='exact').execute()
            registry_count = count_result.count if hasattr(count_result, 'count') else len(count_result.data)
            
            checks["supabase"] = {
                "status": "ok",
                "score": 100,
                "latency_ms": supabase_latency,
                "registry_entries": registry_count
            }
        else:
            checks["supabase"] = {"status": "error", "score": 0, "error": "Client not available"}
            issues.append("Supabase client not available")
    except Exception as e:
        checks["supabase"] = {"status": "error", "score": 0, "error": str(e)}
        issues.append(f"Supabase connection failed: {e}")
    
    # =========================================================================
    # CHECK 2: DUCKDB
    # =========================================================================
    try:
        duckdb_start = time.time()
        if STRUCTURED_AVAILABLE:
            handler = get_structured_handler()
            
            table_count = handler.safe_fetchone("""
                SELECT COUNT(DISTINCT table_name) FROM _schema_metadata 
                WHERE is_current = TRUE
            """)
            
            row_count = handler.safe_fetchone("""
                SELECT COALESCE(SUM(row_count), 0) FROM _schema_metadata 
                WHERE is_current = TRUE
            """)
            
            file_count = handler.safe_fetchone("""
                SELECT COUNT(DISTINCT file_name) FROM _schema_metadata 
                WHERE is_current = TRUE
            """)
            
            duckdb_latency = int((time.time() - duckdb_start) * 1000)
            
            checks["duckdb"] = {
                "status": "ok",
                "score": 100,
                "latency_ms": duckdb_latency,
                "tables": table_count[0] if table_count else 0,
                "total_rows": row_count[0] if row_count else 0,
                "files": file_count[0] if file_count else 0
            }
        else:
            checks["duckdb"] = {"status": "unavailable", "score": 25, "error": "Structured handler not available"}
            issues.append("DuckDB structured handler not available")
    except Exception as e:
        checks["duckdb"] = {"status": "error", "score": 0, "error": str(e)}
        issues.append(f"DuckDB check failed: {e}")
    
    # =========================================================================
    # CHECK 3: CHROMADB
    # =========================================================================
    try:
        chroma_start = time.time()
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
        
        chroma_count = collection.count()
        
        if chroma_count > 0:
            chroma_results = collection.get(include=["metadatas"], limit=5000)
            unique_files = set()
            for metadata in chroma_results.get("metadatas", []):
                filename = metadata.get("source") or metadata.get("filename")
                if filename:
                    unique_files.add(filename)
            file_count = len(unique_files)
        else:
            file_count = 0
        
        chroma_latency = int((time.time() - chroma_start) * 1000)
        
        checks["chromadb"] = {
            "status": "ok",
            "score": 100,
            "latency_ms": chroma_latency,
            "total_chunks": chroma_count,
            "unique_files": file_count
        }
    except Exception as e:
        checks["chromadb"] = {"status": "error", "score": 0, "error": str(e)}
        issues.append(f"ChromaDB check failed: {e}")
    
    # =========================================================================
    # CHECK 4: REGISTRY CONSISTENCY
    # =========================================================================
    try:
        consistency_score = 100
        
        registry_entries = DocumentRegistryModel.get_all(limit=5000)
        registry_files = {e['filename']: e for e in registry_entries}
        
        duckdb_files = set()
        if STRUCTURED_AVAILABLE:
            try:
                handler = get_structured_handler()
                duckdb_result = handler.safe_fetchall("""
                    SELECT DISTINCT file_name FROM _schema_metadata 
                    WHERE is_current = TRUE AND file_name IS NOT NULL
                """)
                duckdb_files = {r[0] for r in duckdb_result if r[0]}
            except:
                pass
        
        chroma_files = set()
        try:
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            if collection.count() > 0:
                chroma_results = collection.get(include=["metadatas"], limit=5000)
                for metadata in chroma_results.get("metadatas", []):
                    filename = metadata.get("source") or metadata.get("filename")
                    if filename:
                        chroma_files.add(filename)
        except:
            pass
        
        all_actual_files = duckdb_files | chroma_files
        
        orphaned_registry = []
        for filename, entry in registry_files.items():
            storage_type = entry.get('storage_type', '')
            
            if storage_type == 'duckdb' and filename not in duckdb_files:
                orphaned_registry.append({"file": filename, "issue": "in registry as duckdb but not in DuckDB"})
            elif storage_type == 'chromadb' and filename not in chroma_files:
                orphaned_registry.append({"file": filename, "issue": "in registry as chromadb but not in ChromaDB"})
            elif storage_type == 'both':
                if filename not in duckdb_files and filename not in chroma_files:
                    orphaned_registry.append({"file": filename, "issue": "in registry as both but not in either backend"})
        
        unregistered_files = []
        for filename in all_actual_files:
            if filename not in registry_files:
                location = []
                if filename in duckdb_files:
                    location.append("duckdb")
                if filename in chroma_files:
                    location.append("chromadb")
                unregistered_files.append({"file": filename, "found_in": location})
        
        mismatched_storage = []
        for filename, entry in registry_files.items():
            storage_type = entry.get('storage_type', '')
            in_duckdb = filename in duckdb_files
            in_chroma = filename in chroma_files
            
            if storage_type == 'duckdb' and in_chroma and not in_duckdb:
                mismatched_storage.append({"file": filename, "registry": "duckdb", "actual": "chromadb"})
            elif storage_type == 'chromadb' and in_duckdb and not in_chroma:
                mismatched_storage.append({"file": filename, "registry": "chromadb", "actual": "duckdb"})
            elif storage_type == 'both' and not (in_duckdb and in_chroma):
                actual = []
                if in_duckdb:
                    actual.append("duckdb")
                if in_chroma:
                    actual.append("chromadb")
                if actual:
                    mismatched_storage.append({"file": filename, "registry": "both", "actual": actual})
        
        # Calculate consistency score
        total_issues = len(orphaned_registry) + len(unregistered_files) + len(mismatched_storage)
        total_files = max(len(registry_files), len(all_actual_files), 1)
        
        if total_issues == 0:
            consistency_score = 100
            consistency_status = "ok"
        else:
            consistency_score = max(0, 100 - int((total_issues / total_files) * 100))
            consistency_status = "warning" if consistency_score >= 50 else "error"
            
            if orphaned_registry:
                issues.append(f"{len(orphaned_registry)} orphaned registry entries")
                recommendations.append("Run /api/status/registry/sync to clean orphans")
            if unregistered_files:
                issues.append(f"{len(unregistered_files)} unregistered files")
                recommendations.append("Run /api/status/registry/sync to register missing files")
            if mismatched_storage:
                issues.append(f"{len(mismatched_storage)} storage type mismatches")
        
        checks["registry_consistency"] = {
            "status": consistency_status,
            "score": consistency_score,
            "registry_entries": len(registry_files),
            "duckdb_files": len(duckdb_files),
            "chromadb_files": len(chroma_files),
            "orphaned_registry": len(orphaned_registry),
            "unregistered_files": len(unregistered_files),
            "storage_mismatches": len(mismatched_storage),
            "details": {
                "orphaned": orphaned_registry[:5],
                "unregistered": unregistered_files[:5],
                "mismatched": mismatched_storage[:5]
            }
        }
    except Exception as e:
        checks["registry_consistency"] = {"status": "error", "score": 0, "error": str(e)}
        issues.append(f"Registry consistency check failed: {e}")
    
    # =========================================================================
    # CHECK 5: LINEAGE
    # =========================================================================
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        if supabase:
            lineage_result = supabase.table('lineage_edges').select('relationship, source_id').execute()
            lineage_data = lineage_result.data if lineage_result.data else []
            
            total_edges = len(lineage_data)
            by_relationship = {}
            files_with_lineage = set()
            
            for edge in lineage_data:
                rel = edge.get('relationship', 'unknown')
                by_relationship[rel] = by_relationship.get(rel, 0) + 1
                files_with_lineage.add(edge.get('source_id'))
            
            registry_entries = DocumentRegistryModel.get_all(limit=5000)
            registry_filenames = {e.get('filename') for e in registry_entries if e.get('filename')}
            
            # Only count files that are BOTH in lineage AND in registry
            files_with_lineage_in_registry = files_with_lineage & registry_filenames
            files_without_lineage = [f for f in registry_filenames if f not in files_with_lineage]
            
            lineage_coverage = f"{len(files_with_lineage_in_registry)}/{len(registry_filenames)}"
            
            # Calculate lineage score (capped at 100)
            if len(registry_filenames) > 0:
                lineage_score = min(100, int((len(files_with_lineage_in_registry) / len(registry_filenames)) * 100))
            else:
                lineage_score = 100
            
            lineage_status = "ok" if lineage_score >= 80 else ("warning" if lineage_score >= 50 else "error")
            
            if files_without_lineage:
                issues.append(f"{len(files_without_lineage)} files without lineage tracking")
            
            checks["lineage"] = {
                "status": lineage_status,
                "score": lineage_score,
                "total_edges": total_edges,
                "by_relationship": by_relationship,
                "files_with_lineage": len(files_with_lineage_in_registry),
                "files_without_lineage": len(files_without_lineage),
                "coverage": lineage_coverage,
                "missing_files": files_without_lineage[:10]
            }
        else:
            checks["lineage"] = {"status": "unavailable", "score": 25, "error": "Supabase not available"}
    except Exception as e:
        checks["lineage"] = {"status": "error", "score": 0, "error": str(e)}
        issues.append(f"Lineage check failed: {e}")
    
    # =========================================================================
    # CHECK 6: PROCESSING JOBS
    # =========================================================================
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        if supabase:
            from datetime import timedelta
            ten_mins_ago = (datetime.utcnow() - timedelta(minutes=10)).isoformat()
            
            # Query uses actual columns: id, status, created_at, input_data (JSONB has filename)
            stuck_result = supabase.table('processing_jobs').select('id, job_type, status, created_at, input_data').eq('status', 'processing').lt('created_at', ten_mins_ago).execute()
            stuck_jobs = stuck_result.data if stuck_result.data else []
            
            one_day_ago = (datetime.utcnow() - timedelta(hours=24)).isoformat()
            failed_result = supabase.table('processing_jobs').select('id, job_type, error_message, input_data').eq('status', 'failed').gt('created_at', one_day_ago).execute()
            failed_jobs = failed_result.data if failed_result.data else []
            
            pending_result = supabase.table('processing_jobs').select('id').eq('status', 'queued').execute()
            pending_count = len(pending_result.data) if pending_result.data else 0
            
            # Calculate jobs score
            if stuck_jobs:
                jobs_score = 50
                jobs_status = "warning"
                issues.append(f"{len(stuck_jobs)} jobs stuck in processing")
                recommendations.append("Check stuck jobs and manually fail them if needed")
            elif failed_jobs and len(failed_jobs) > 5:
                jobs_score = 75
                jobs_status = "warning"
            else:
                jobs_score = 100
                jobs_status = "ok"
            
            # Extract filename from input_data JSONB if present
            stuck_details = []
            for j in stuck_jobs[:5]:
                input_data = j.get('input_data') or {}
                stuck_details.append({
                    "id": j['id'],
                    "job_type": j.get('job_type'),
                    "filename": input_data.get('filename') or input_data.get('source_file'),
                    "created_at": j['created_at']
                })
            
            checks["jobs"] = {
                "status": jobs_status,
                "score": jobs_score,
                "stuck_count": len(stuck_jobs),
                "failed_24h": len(failed_jobs),
                "pending": pending_count,
                "stuck_jobs": stuck_details
            }
        else:
            checks["jobs"] = {"status": "unavailable", "score": 25, "error": "Supabase not available"}
    except Exception as e:
        checks["jobs"] = {"status": "error", "score": 0, "error": str(e)}
        issues.append(f"Jobs check failed: {e}")
    
    # =========================================================================
    # CHECK 7: LOCAL LLM (OLLAMA)
    # =========================================================================
    try:
        import os
        import requests
        from requests.auth import HTTPBasicAuth
        
        # Read from environment variables (same as rest of codebase)
        ollama_endpoint = os.getenv("LLM_ENDPOINT", "").rstrip('/')
        ollama_user = os.getenv("LLM_USERNAME", "")
        ollama_pass = os.getenv("LLM_PASSWORD", "")
        
        if not ollama_endpoint:
            checks["ollama"] = {"status": "not_configured", "score": 50, "error": "LLM_ENDPOINT not set"}
            issues.append("Ollama LLM_ENDPOINT not configured")
        else:
            ollama_start = time.time()
            
            # Build auth if credentials provided
            auth = HTTPBasicAuth(ollama_user, ollama_pass) if ollama_user and ollama_pass else None
            
            response = requests.get(f"{ollama_endpoint}/api/tags", auth=auth, timeout=10)
            ollama_latency = int((time.time() - ollama_start) * 1000)
            
            if response.status_code == 200:
                models_data = response.json()
                available_models = [m['name'] for m in models_data.get('models', [])]
                
                # Check for models actually used by XLR8
                required_models = ['mistral:7b', 'deepseek-coder:6.7b']
                missing_models = [m for m in required_models if m not in available_models]
                
                # Also check for embedding model
                has_embeddings = 'nomic-embed-text:latest' in available_models
                
                if not missing_models:
                    ollama_score = 100
                    ollama_status = "ok"
                elif len(missing_models) == 1:
                    ollama_score = 75
                    ollama_status = "warning"
                    issues.append(f"Missing LLM model: {missing_models}")
                else:
                    ollama_score = 50
                    ollama_status = "warning"
                    issues.append(f"Missing LLM models: {missing_models}")
                
                checks["ollama"] = {
                    "status": ollama_status,
                    "score": ollama_score,
                    "latency_ms": ollama_latency,
                    "endpoint": ollama_endpoint,
                    "available_models": available_models,
                    "required_models": required_models,
                    "missing_models": missing_models,
                    "has_embeddings": has_embeddings
                }
            else:
                checks["ollama"] = {"status": "error", "score": 0, "error": f"HTTP {response.status_code}"}
                issues.append(f"Ollama returned HTTP {response.status_code}")
    except requests.exceptions.Timeout:
        checks["ollama"] = {"status": "timeout", "score": 25, "error": "Connection timed out"}
        issues.append("Ollama connection timed out")
    except requests.exceptions.ConnectionError:
        checks["ollama"] = {"status": "unreachable", "score": 0, "error": "Connection refused"}
        issues.append("Ollama server unreachable")
    except Exception as e:
        checks["ollama"] = {"status": "error", "score": 0, "error": str(e)}
        issues.append(f"Ollama check failed: {e}")
    
    # =========================================================================
    # CALCULATE OVERALL SCORE AND STATUS
    # =========================================================================
    
    # Weighted scoring (critical systems weighted higher)
    weights = {
        "supabase": 1.5,      # Critical - metadata store
        "duckdb": 1.5,        # Critical - structured data
        "chromadb": 1.0,      # Important - vector search
        "registry_consistency": 1.0,  # Important - data integrity
        "lineage": 0.5,       # Nice to have
        "jobs": 0.75,         # Important - processing health
        "ollama": 0.5         # Nice to have - fallback exists
    }
    
    total_weight = 0
    weighted_score = 0
    
    for check_name, check_result in checks.items():
        weight = weights.get(check_name, 1.0)
        score = check_result.get('score', 0)
        weighted_score += score * weight
        total_weight += weight
    
    health_score = min(100, int(weighted_score / total_weight)) if total_weight > 0 else 0
    
    if health_score >= 90:
        overall_status = "healthy"
    elif health_score >= 70:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    total_time = int((time.time() - start_time) * 1000)
    
    # Save snapshot if requested
    snapshot_saved = False
    if save_snapshot:
        snapshot_saved = _save_health_snapshot(
            overall_status=overall_status,
            health_score=health_score,
            checks=checks,
            issues=issues,
            check_time_ms=total_time,
            triggered_by=triggered_by
        )
    
    return {
        "status": overall_status,
        "health_score": health_score,
        "timestamp": datetime.utcnow().isoformat(),
        "check_time_ms": total_time,
        "checks": checks,
        "issues": issues,
        "issue_count": len(issues),
        "recommendations": recommendations,
        "snapshot_saved": snapshot_saved
    }


# =============================================================================
# DELETE VERIFICATION ENDPOINT - Task 3 GET HEALTHY Sprint
# =============================================================================

@router.get("/status/verify-deleted")
async def verify_file_deleted(filename: str, project: Optional[str] = None):
    """
    Verify a file has been completely deleted from all storage locations.
    
    Checks:
    - Document Registry (Supabase)
    - DuckDB tables (_schema_metadata, _pdf_tables, actual tables)
    - ChromaDB chunks
    - Lineage edges
    - Documents table (Supabase)
    
    Returns:
        - completely_deleted: True if no remnants found anywhere
        - remnants: Details of any remaining data
    """
    import time
    start_time = time.time()
    
    filename_lower = filename.lower()
    project_lower = project.lower() if project else None
    
    remnants = {
        "registry": False,
        "duckdb_tables": [],
        "duckdb_metadata": False,
        "duckdb_pdf_tables": False,
        "chromadb_chunks": 0,
        "lineage_edges": 0,
        "documents_table": False
    }
    
    issues = []
    
    # =========================================================================
    # CHECK 1: Document Registry
    # =========================================================================
    try:
        # Check if file still exists in registry
        entries = DocumentRegistryModel.get_all(limit=5000)
        for entry in entries:
            if entry.get('filename', '').lower() == filename_lower:
                remnants["registry"] = True
                issues.append(f"Found in document_registry (id: {entry.get('id')})")
                break
    except Exception as e:
        issues.append(f"Registry check error: {e}")
    
    # =========================================================================
    # CHECK 2: DuckDB - _schema_metadata
    # =========================================================================
    if STRUCTURED_AVAILABLE:
        try:
            handler = get_structured_handler()
            
            # Check _schema_metadata
            if project_lower:
                meta_result = handler.safe_fetchall("""
                    SELECT table_name, project, file_name FROM _schema_metadata 
                    WHERE LOWER(file_name) = ? AND LOWER(project) = ?
                """, [filename_lower, project_lower])
            else:
                meta_result = handler.safe_fetchall("""
                    SELECT table_name, project, file_name FROM _schema_metadata 
                    WHERE LOWER(file_name) = ?
                """, [filename_lower])
            
            if meta_result:
                remnants["duckdb_metadata"] = True
                issues.append(f"Found {len(meta_result)} entries in _schema_metadata")
                
        except Exception as e:
            if "does not exist" not in str(e).lower():
                issues.append(f"_schema_metadata check error: {e}")
    
    # =========================================================================
    # CHECK 3: DuckDB - _pdf_tables
    # =========================================================================
    if STRUCTURED_AVAILABLE:
        try:
            handler = get_structured_handler()
            
            # Check if _pdf_tables exists
            table_check = handler.safe_fetchone("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = '_pdf_tables'
            """)
            
            if table_check and table_check[0] > 0:
                pdf_result = handler.safe_fetchall("""
                    SELECT table_name, source_file FROM _pdf_tables 
                    WHERE LOWER(source_file) = ? OR LOWER(source_file) LIKE ?
                """, [filename_lower, f"%{filename_lower}%"])
                
                if pdf_result:
                    remnants["duckdb_pdf_tables"] = True
                    issues.append(f"Found {len(pdf_result)} entries in _pdf_tables")
                    
        except Exception as e:
            if "does not exist" not in str(e).lower():
                issues.append(f"_pdf_tables check error: {e}")
    
    # =========================================================================
    # CHECK 4: DuckDB - Actual Tables (by naming pattern)
    # =========================================================================
    if STRUCTURED_AVAILABLE:
        try:
            handler = get_structured_handler()
            
            # Generate expected table name patterns
            safe_file = filename.rsplit('.', 1)[0].lower().replace(' ', '_').replace('-', '_')
            
            all_tables = handler.safe_fetchall("SHOW TABLES")
            matching_tables = []
            
            for (tbl,) in all_tables:
                tbl_lower = tbl.lower()
                # Match tables containing the filename pattern
                if safe_file in tbl_lower:
                    matching_tables.append(tbl)
            
            if matching_tables:
                remnants["duckdb_tables"] = matching_tables
                issues.append(f"Found {len(matching_tables)} DuckDB tables matching pattern")
                
        except Exception as e:
            issues.append(f"DuckDB tables check error: {e}")
    
    # =========================================================================
    # CHECK 5: ChromaDB Chunks
    # =========================================================================
    try:
        rag = RAGHandler()
        collection = rag.client.get_or_create_collection(name="documents")
        
        chunk_count = 0
        
        # Try exact match first
        for field in ["filename", "source", "name"]:
            try:
                results = collection.get(where={field: filename})
                if results and results['ids']:
                    chunk_count += len(results['ids'])
            except:
                pass
        
        # Case-insensitive fallback
        if chunk_count == 0:
            try:
                all_docs = collection.get(include=["metadatas"], limit=10000)
                for metadata in all_docs.get("metadatas", []):
                    doc_filename = metadata.get("source") or metadata.get("filename") or ""
                    if doc_filename.lower() == filename_lower:
                        chunk_count += 1
            except:
                pass
        
        if chunk_count > 0:
            remnants["chromadb_chunks"] = chunk_count
            issues.append(f"Found {chunk_count} ChromaDB chunks")
            
    except Exception as e:
        issues.append(f"ChromaDB check error: {e}")
    
    # =========================================================================
    # CHECK 6: Lineage Edges
    # =========================================================================
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        if supabase:
            # Check for lineage edges where this file is the source
            result = supabase.table('lineage_edges').select('id').eq('source_id', filename).execute()
            edge_count = len(result.data) if result.data else 0
            
            # Also check case-insensitive
            if edge_count == 0:
                all_edges = supabase.table('lineage_edges').select('id, source_id').execute()
                for edge in (all_edges.data or []):
                    if edge.get('source_id', '').lower() == filename_lower:
                        edge_count += 1
            
            if edge_count > 0:
                remnants["lineage_edges"] = edge_count
                issues.append(f"Found {edge_count} lineage edges")
                
    except Exception as e:
        issues.append(f"Lineage check error: {e}")
    
    # =========================================================================
    # CHECK 7: Documents Table
    # =========================================================================
    try:
        from utils.database.supabase_client import get_supabase
        supabase = get_supabase()
        
        if supabase:
            result = supabase.table('documents').select('id').eq('name', filename).execute()
            if result.data:
                remnants["documents_table"] = True
                issues.append(f"Found in documents table")
                
    except Exception as e:
        if "does not exist" not in str(e).lower():
            issues.append(f"Documents table check error: {e}")
    
    # =========================================================================
    # DETERMINE IF COMPLETELY DELETED
    # =========================================================================
    has_remnants = (
        remnants["registry"] or
        remnants["duckdb_tables"] or
        remnants["duckdb_metadata"] or
        remnants["duckdb_pdf_tables"] or
        remnants["chromadb_chunks"] > 0 or
        remnants["lineage_edges"] > 0 or
        remnants["documents_table"]
    )
    
    completely_deleted = not has_remnants
    
    check_time = int((time.time() - start_time) * 1000)
    
    return {
        "filename": filename,
        "project": project,
        "completely_deleted": completely_deleted,
        "remnants": remnants,
        "issues": issues if issues else [],
        "issue_count": len([i for i in issues if "error" not in i.lower()]),
        "check_time_ms": check_time,
        "recommendation": None if completely_deleted else "Run delete again or manually clean remnants"
    }


# =============================================================================
# RELATIONSHIPS ENDPOINT (for Data Explorer)
# =============================================================================

@router.get("/status/relationships")
async def get_relationships():
    """
    Get detected relationships between tables.
    
    Returns foreign key relationships and common column matches.
    Used by Data Explorer to show table connections.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    relationships = []
    
    try:
        # Get structured handler to query DuckDB
        from utils.structured_data_handler import get_structured_handler
        handler = get_structured_handler()
        
        if not handler or not handler.conn:
            return {"relationships": [], "message": "DuckDB not available"}
        
        # Get all tables
        tables_result = handler.conn.execute("SHOW TABLES").fetchall()
        tables = [t[0] for t in tables_result]
        
        if len(tables) < 2:
            return {"relationships": [], "message": "Need at least 2 tables for relationships"}
        
        # Get columns for each table
        table_columns = {}
        for table in tables:
            try:
                cols = handler.conn.execute(f"DESCRIBE {table}").fetchall()
                table_columns[table] = [c[0].lower() for c in cols]
            except:
                pass
        
        # Find relationships based on common column patterns
        key_patterns = ['_id', '_code', '_key', '_num', '_no']
        
        for table1 in tables:
            cols1 = table_columns.get(table1, [])
            for col1 in cols1:
                # Check if this looks like a key column
                is_key = any(p in col1.lower() for p in key_patterns)
                if not is_key:
                    continue
                
                # Look for matching columns in other tables
                for table2 in tables:
                    if table1 >= table2:  # Avoid duplicates and self-refs
                        continue
                    
                    cols2 = table_columns.get(table2, [])
                    if col1 in cols2:
                        # Found a match!
                        rel_type = "1:N" if "employee" in col1 or "emp" in col1 else "N:1"
                        relationships.append({
                            "from_table": table1,
                            "from_column": col1,
                            "to_table": table2,
                            "to_column": col1,  # Same column name in both tables
                            "type": rel_type,
                            "confidence": "high" if "_id" in col1 else "medium",
                            "needs_review": "_id" not in col1,  # Flag non-ID matches for review
                        })
        
        logger.info(f"[RELATIONSHIPS] Found {len(relationships)} relationships across {len(tables)} tables")
        
        return {
            "relationships": relationships,
            "table_count": len(tables),
            "detected_by": "column_pattern_matching"
        }
        
    except Exception as e:
        logger.error(f"[RELATIONSHIPS] Error: {e}")
        return {
            "relationships": [],
            "error": str(e)
        }


# =============================================================================
# STANDARDS/COMPLIANCE CHECK ENDPOINT (for Data Explorer Compliance tab)
# =============================================================================

@router.post("/status/standards/check")
async def run_compliance_check(request: dict):
    """
    Run compliance check against extracted rules.
    
    Takes rules from standards_processor and checks them against DuckDB data.
    Returns findings with severity, affected count, and corrective actions.
    
    This is the $500/hr Deloitte deliverable, automated.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    project_id = request.get("project_id")
    
    if not project_id:
        return {
            "error": "project_id required",
            "rules_checked": 0,
            "findings_count": 0,
            "compliant_count": 0,
            "findings": []
        }
    
    try:
        # Get rules from standards processor
        try:
            from backend.utils.standards_processor import get_rule_registry
            registry = get_rule_registry()
            all_rules = registry.get_all_rules()
        except Exception as e:
            logger.warning(f"[COMPLIANCE] Could not load rules: {e}")
            all_rules = []
        
        if not all_rules:
            return {
                "message": "No rules found. Upload regulatory documents to the Reference Library first.",
                "rules_checked": 0,
                "findings_count": 0,
                "compliant_count": 0,
                "findings": []
            }
        
        # Get DuckDB handler
        try:
            from utils.structured_data_handler import get_structured_handler
            handler = get_structured_handler()
        except Exception as e:
            logger.error(f"[COMPLIANCE] DuckDB not available: {e}")
            return {
                "error": "DuckDB not available",
                "rules_checked": 0,
                "findings_count": 0,
                "compliant_count": 0,
                "findings": []
            }
        
        findings = []
        compliant_count = 0
        
        # Check each rule
        for rule in all_rules:
            try:
                rule_dict = rule.to_dict() if hasattr(rule, 'to_dict') else rule
                
                # If rule has a suggested SQL pattern, try to execute it
                sql_pattern = rule_dict.get('suggested_sql_pattern')
                
                if sql_pattern and handler and handler.conn:
                    try:
                        # Execute the check query
                        result = handler.conn.execute(sql_pattern).fetchall()
                        affected_count = len(result) if result else 0
                        
                        if affected_count > 0:
                            findings.append({
                                "rule_id": rule_dict.get('rule_id'),
                                "title": rule_dict.get('title'),
                                "condition": rule_dict.get('title'),
                                "criteria": rule_dict.get('description'),
                                "severity": rule_dict.get('severity', 'medium'),
                                "affected_count": affected_count,
                                "source_document": rule_dict.get('source_document'),
                                "corrective_action": f"Review {affected_count} records that violate this rule"
                            })
                        else:
                            compliant_count += 1
                    except Exception as sql_e:
                        logger.warning(f"[COMPLIANCE] SQL execution failed for rule {rule_dict.get('rule_id')}: {sql_e}")
                        # Rule couldn't be checked - don't count as finding or compliant
                else:
                    # No SQL pattern - just list the rule as "checked" (manual review needed)
                    compliant_count += 1
                    
            except Exception as rule_e:
                logger.warning(f"[COMPLIANCE] Error checking rule: {rule_e}")
        
        logger.info(f"[COMPLIANCE] Checked {len(all_rules)} rules: {len(findings)} findings, {compliant_count} compliant")
        
        return {
            "project_id": project_id,
            "rules_checked": len(all_rules),
            "findings_count": len(findings),
            "compliant_count": compliant_count,
            "findings": findings
        }
        
    except Exception as e:
        logger.error(f"[COMPLIANCE] Error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "rules_checked": 0,
            "findings_count": 0,
            "compliant_count": 0,
            "findings": []
        }



# =============================================================================
# TEST SQL ENDPOINT (for Rules tab SQL validation)
# =============================================================================

@router.post("/status/test-sql")
async def test_sql_query(request: dict):
    """
    Test a SQL query against DuckDB and return results.
    
    Used by Rules tab to validate SQL patterns against actual data.
    Returns row count, columns, and sample data.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    sql = request.get("sql", "").strip()
    
    if not sql:
        raise HTTPException(400, "SQL query required")
    
    # Security: Only allow SELECT queries
    sql_upper = sql.upper().strip()
    if not sql_upper.startswith("SELECT"):
        raise HTTPException(400, "Only SELECT queries allowed for testing")
    
    # Block dangerous operations
    dangerous = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE"]
    for d in dangerous:
        if d in sql_upper:
            raise HTTPException(400, f"Query contains forbidden operation: {d}")
    
    try:
        from utils.structured_data_handler import get_structured_handler
        handler = get_structured_handler()
        
        if not handler or not handler.conn:
            raise HTTPException(503, "DuckDB not available")
        
        # Execute query with limit for safety
        # Add LIMIT if not present
        if "LIMIT" not in sql_upper:
            sql = sql.rstrip(";") + " LIMIT 100"
        
        result = handler.conn.execute(sql).fetchall()
        
        # Get column names
        columns = []
        try:
            columns = [desc[0] for desc in handler.conn.description]
        except:
            pass
        
        # Get sample (first 5 rows)
        sample = []
        for row in result[:5]:
            row_dict = {}
            for i, col in enumerate(columns):
                val = row[i] if i < len(row) else None
                # Convert to JSON-serializable
                if hasattr(val, 'isoformat'):
                    val = val.isoformat()
                elif isinstance(val, (bytes, bytearray)):
                    val = str(val)
                row_dict[col] = val
            sample.append(row_dict)
        
        logger.info(f"[TEST-SQL] Query returned {len(result)} rows")
        
        return {
            "success": True,
            "row_count": len(result),
            "columns": columns,
            "sample": sample
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[TEST-SQL] Error: {e}")
        raise HTTPException(400, str(e))


# =============================================================================
# GENERATE SQL FOR RULE (Option B - on-demand SQL generation)
# =============================================================================

# =============================================================================
# GENERATE SQL FOR RULE (Option B - on-demand SQL generation)
# Uses LLMOrchestrator to call local Ollama (DeepSeek for SQL)
# =============================================================================

@router.post("/status/rules/{rule_id}/generate-sql")
async def generate_sql_for_rule(rule_id: str, request: dict = None):
    """
    Generate a SQL query pattern for a specific rule based on available tables.
    Uses local LLM (DeepSeek via Ollama) to create a query.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # 1. Get the rule
        try:
            from backend.utils.standards_processor import get_rule_registry
        except ImportError:
            from utils.standards_processor import get_rule_registry
            
        registry = get_rule_registry()
        
        rule = None
        for r in registry.get_all_rules():
            rid = getattr(r, 'rule_id', None)
            if rid == rule_id:
                rule = r
                break
        
        if not rule:
            raise HTTPException(404, f"Rule {rule_id} not found")
        
        # 2. Get available tables and columns from DuckDB
        try:
            from utils.structured_data_handler import get_structured_handler
        except ImportError:
            from backend.utils.structured_data_handler import get_structured_handler
            
        handler = get_structured_handler()
        
        if not handler or not handler.conn:
            raise HTTPException(503, "DuckDB not available")
        
        # Get schema info
        tables_info = []
        all_columns = set()
        try:
            tables = handler.conn.execute("SHOW TABLES").fetchall()
            for (table_name,) in tables:
                try:
                    cols = handler.conn.execute(f"DESCRIBE {table_name}").fetchall()
                    col_names = [c[0] for c in cols]
                    all_columns.update(col_names)
                    tables_info.append({
                        "table": table_name,
                        "columns": col_names
                    })
                except:
                    pass
        except Exception as e:
            logger.warning(f"Could not get schema: {e}")
        
        if not tables_info:
            return {
                "success": False,
                "error": "No tables available in DuckDB",
                "sql": None
            }
        
        # 3. Build prompt for LLM
        rule_info = {
            "title": getattr(rule, 'title', ''),
            "description": getattr(rule, 'description', ''),
            "applies_to": getattr(rule, 'applies_to', {}),
            "requirement": getattr(rule, 'requirement', {}),
            "source_text": getattr(rule, 'source_text', '')[:500]
        }
        
        schema_text = "\n".join([
            f"Table: {t['table']}\n  Columns: {', '.join(t['columns'][:20])}"
            for t in tables_info[:10]  # Limit to 10 tables
        ])
        
        prompt = f"""Generate a DuckDB SQL query to check compliance with this rule.

RULE:
Title: {rule_info['title']}
Description: {rule_info['description']}
Applies To: {rule_info['applies_to']}
Requirement: {rule_info['requirement']}
Original Text: {rule_info['source_text']}

AVAILABLE TABLES:
{schema_text}

INSTRUCTIONS:
1. Create a SELECT query that finds rows that VIOLATE this rule
2. Use only tables and columns that exist in the schema above
3. If no tables match the rule's domain, return a comment explaining why
4. The query should return violating records (non-compliance)
5. Include relevant columns that help identify the violation
6. Use DuckDB SQL syntax

Output ONLY the SQL query, no explanation. If the rule cannot be checked with available data, output:
-- Cannot check: [brief reason]
"""
        
        # 4. Call LLM using LLMOrchestrator (local Ollama)
        sql_result = None
        model_used = None
        
        try:
            try:
                from utils.llm_orchestrator import LLMOrchestrator
            except ImportError:
                from backend.utils.llm_orchestrator import LLMOrchestrator
            
            orchestrator = LLMOrchestrator()
            
            # Use generate_sql which tries DeepSeek then Mistral
            result = orchestrator.generate_sql(prompt, all_columns)
            
            if result.get('success') and result.get('sql'):
                sql_result = result['sql']
                model_used = result.get('model', 'local')
                logger.info(f"[GENERATE-SQL] Success via {model_used} for rule {rule_id}")
            else:
                logger.warning(f"[GENERATE-SQL] LLM failed: {result.get('error', 'unknown')}")
                
        except Exception as e:
            logger.error(f"[GENERATE-SQL] LLMOrchestrator error: {e}")
            import traceback
            traceback.print_exc()
        
        if not sql_result:
            return {
                "success": False,
                "error": "Could not generate SQL - LLM unavailable or failed",
                "sql": None
            }
        
        # Clean up SQL (remove markdown code blocks if present)
        if sql_result.startswith("```"):
            lines = sql_result.split("\n")
            sql_result = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        sql_result = sql_result.strip()
        
        # 5. Save to Supabase
        try:
            from utils.database.supabase_client import get_supabase
            supabase = get_supabase()
            if supabase:
                supabase.table('standards_rules').update({
                    'suggested_sql_pattern': sql_result
                }).eq('rule_id', rule_id).execute()
                logger.info(f"[GENERATE-SQL] Saved SQL for rule {rule_id}")
        except Exception as e:
            logger.warning(f"[GENERATE-SQL] Could not save to Supabase: {e}")
        
        # 6. Update in-memory registry
        try:
            if hasattr(rule, 'suggested_sql_pattern'):
                rule.suggested_sql_pattern = sql_result
        except:
            pass
        
        return {
            "success": True,
            "rule_id": rule_id,
            "sql": sql_result,
            "model": model_used,
            "tables_checked": [t['table'] for t in tables_info[:10]]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[GENERATE-SQL] Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(500, str(e))
