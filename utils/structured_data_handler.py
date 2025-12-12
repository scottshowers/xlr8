"""
Structured Data Handler - DuckDB Storage for Excel/CSV
=======================================================

Stores tabular data in DuckDB for fast SQL queries.
Each project gets isolated tables. Cross-sheet joins supported.

SECURITY FEATURES:
- Field-level encryption for PII (SSN, DOB, etc.)
- Encryption at rest using AES-256-GCM (authenticated encryption)

VERSIONING FEATURES:
- Load versioning for comparison
- Diff detection (new, changed, deleted records)

Author: XLR8 Team
"""

import os
import re
import json
import logging
import pandas as pd
import duckdb
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import hashlib
import base64

# Encryption imports
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.fernet import Fernet  # Keep for backward compatibility
    import base64
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    logging.warning("cryptography not installed - PII encryption disabled. Run: pip install cryptography")

# Openpyxl for colored header detection
try:
    from openpyxl import load_workbook
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
    logging.warning("openpyxl not installed - colored header detection disabled")

logger = logging.getLogger(__name__)

# DuckDB storage location
DUCKDB_PATH = "/data/structured_data.duckdb"
ENCRYPTION_KEY_PATH = "/data/.encryption_key_v2"  # New path for AES-256 key

# PII field patterns to encrypt
PII_PATTERNS = [
    r'ssn', r'social.*sec', r'social_security',
    r'tax.*id', r'tin',
    r'bank.*account', r'routing.*number', r'account.*number',
    r'credit.*card', r'card.*number',
    r'passport', r'license.*number', r'driver.*lic',
    r'salary', r'pay.*rate', r'wage', r'compensation',
    r'dob', r'date.*birth', r'birth.*date', r'birthdate',
]


# =========================================================================
# INFERENCE JOB QUEUE - processes one file at a time to avoid overload
# =========================================================================
import queue
import threading

_inference_queue = queue.Queue()
_inference_worker_started = False
_inference_lock = threading.Lock()

def _inference_worker():
    """Background worker that processes inference jobs one at a time"""
    logger.info("[INFERENCE_QUEUE] Worker started")
    while True:
        try:
            job = _inference_queue.get(timeout=60)  # Wait up to 60s for job
            if job is None:  # Poison pill
                break
            
            handler, job_id, project, file_name, tables_info = job
            logger.info(f"[INFERENCE_QUEUE] Processing job {job_id} for {file_name} ({len(tables_info)} tables)")
            
            try:
                handler.run_inference_for_file(job_id, project, file_name, tables_info)
            except Exception as e:
                logger.error(f"[INFERENCE_QUEUE] Job {job_id} failed: {e}")
            
            _inference_queue.task_done()
            
        except queue.Empty:
            # No jobs, just keep waiting
            continue
        except Exception as e:
            logger.error(f"[INFERENCE_QUEUE] Worker error: {e}")

def _ensure_worker_started():
    """Start the worker thread if not already running"""
    global _inference_worker_started
    with _inference_lock:
        if not _inference_worker_started:
            worker = threading.Thread(target=_inference_worker, daemon=True)
            worker.start()
            _inference_worker_started = True
            logger.info("[INFERENCE_QUEUE] Worker thread initialized")

def queue_inference_job(handler, job_id: str, project: str, file_name: str, tables_info: list):
    """Add an inference job to the queue"""
    _ensure_worker_started()
    _inference_queue.put((handler, job_id, project, file_name, tables_info))
    queue_size = _inference_queue.qsize()
    logger.info(f"[INFERENCE_QUEUE] Queued job {job_id}, queue size: {queue_size}")


class FieldEncryptor:
    """
    Handles field-level encryption for PII data using AES-256-GCM.
    
    - AES-256-GCM: Authenticated encryption with 256-bit key
    - 96-bit random nonce per encryption
    - Format: "ENC256:" + base64(nonce + ciphertext + tag)
    - Backward compatible: can still decrypt old "ENC:" Fernet data
    
    Future KMS integration point: Replace _get_key() method
    """
    
    def __init__(self, key_path: str = ENCRYPTION_KEY_PATH):
        self.key_path = key_path
        self.aesgcm = None
        self.fernet = None  # For backward compatibility
        
        if ENCRYPTION_AVAILABLE:
            self._init_encryption()
    
    def _init_encryption(self):
        """Initialize or load AES-256 encryption key"""
        try:
            key = self._get_key()
            self.aesgcm = AESGCM(key)
            logger.info("AES-256-GCM encryption initialized successfully")
            
            # Also init Fernet for backward compatibility with old data
            old_key_path = "/data/.encryption_key"
            if os.path.exists(old_key_path):
                try:
                    with open(old_key_path, 'rb') as f:
                        fernet_key = f.read()
                    self.fernet = Fernet(fernet_key)
                    logger.info("Fernet backward compatibility enabled")
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Encryption initialization failed: {e}")
            self.aesgcm = None
    
    def _get_key(self) -> bytes:
        """
        Get or generate AES-256 key (32 bytes).
        
        Future KMS integration: Override this method to fetch from KMS
        Example:
            def _get_key(self):
                import boto3
                kms = boto3.client('kms')
                response = kms.generate_data_key(KeyId='alias/pii-key', KeySpec='AES_256')
                return response['Plaintext']
        """
        if os.path.exists(self.key_path):
            with open(self.key_path, 'rb') as f:
                key = f.read()
                if len(key) != 32:
                    raise ValueError("Invalid key length, expected 32 bytes")
                return key
        else:
            # Generate new 256-bit key
            key = os.urandom(32)
            os.makedirs(os.path.dirname(self.key_path), exist_ok=True)
            with open(self.key_path, 'wb') as f:
                f.write(key)
            os.chmod(self.key_path, 0o600)  # Restrict permissions
            logger.info("Generated new AES-256 encryption key")
            return key
    
    def is_pii_column(self, column_name: str) -> bool:
        """Check if column likely contains PII"""
        col_lower = column_name.lower()
        for pattern in PII_PATTERNS:
            if re.search(pattern, col_lower):
                return True
        return False
    
    def encrypt(self, value: Any) -> str:
        """Encrypt a value using AES-256-GCM"""
        if not self.aesgcm or value is None or pd.isna(value):
            return value
        
        try:
            # Convert to string and encode
            val_bytes = str(value).encode('utf-8')
            
            # Generate random 96-bit nonce (12 bytes)
            nonce = os.urandom(12)
            
            # Encrypt (returns ciphertext + 16-byte auth tag)
            ciphertext = self.aesgcm.encrypt(nonce, val_bytes, None)
            
            # Combine: nonce + ciphertext (includes tag)
            encrypted_data = nonce + ciphertext
            
            # Base64 encode and prefix
            encoded = base64.b64encode(encrypted_data).decode('utf-8')
            return f"ENC256:{encoded}"
            
        except Exception as e:
            logger.warning(f"Encryption failed for value: {e}")
            return value
    
    def decrypt(self, value: Any) -> str:
        """Decrypt a value (handles both AES-256-GCM and legacy Fernet)"""
        if value is None or pd.isna(value):
            return value
        
        try:
            val_str = str(value)
            
            # Handle AES-256-GCM encrypted values
            if val_str.startswith("ENC256:"):
                if not self.aesgcm:
                    return value
                    
                encoded = val_str[7:]  # Remove "ENC256:" prefix
                encrypted_data = base64.b64decode(encoded)
                
                # Extract nonce (first 12 bytes) and ciphertext+tag (rest)
                nonce = encrypted_data[:12]
                ciphertext = encrypted_data[12:]
                
                # Decrypt
                plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
                return plaintext.decode('utf-8')
            
            # Handle legacy Fernet encrypted values (backward compatibility)
            elif val_str.startswith("ENC:"):
                if not self.fernet:
                    logger.warning("Legacy encrypted data found but Fernet not available")
                    return value
                    
                encrypted_data = val_str[4:].encode()
                decrypted = self.fernet.decrypt(encrypted_data)
                return decrypted.decode()
            
            # Not encrypted
            return value
            
        except Exception as e:
            logger.warning(f"Decryption failed: {e}")
            return value
    
    def encrypt_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
        """Encrypt PII columns in a DataFrame"""
        encrypted_cols = []
        df = df.copy()
        
        for col in df.columns:
            if self.is_pii_column(col):
                df[col] = df[col].apply(self.encrypt)
                encrypted_cols.append(col)
                logger.info(f"Encrypted PII column: {col} (AES-256-GCM)")
        
        return df, encrypted_cols
    
    def decrypt_dataframe(self, df: pd.DataFrame, encrypted_cols: List[str] = None) -> pd.DataFrame:
        """Decrypt PII columns in a DataFrame"""
        df = df.copy()
        
        # If no encrypted_cols specified, check all columns for ENC prefix
        if encrypted_cols is None:
            encrypted_cols = []
            for col in df.columns:
                if df[col].dtype == object:
                    sample = df[col].dropna().head(1)
                    if len(sample) > 0:
                        sample_val = str(sample.iloc[0])
                        if sample_val.startswith("ENC256:") or sample_val.startswith("ENC:"):
                            encrypted_cols.append(col)
        
        for col in encrypted_cols:
            if col in df.columns:
                df[col] = df[col].apply(self.decrypt)
        
        return df


class StructuredDataHandler:
    """
    Handles structured data storage and querying via DuckDB.
    
    Features:
    - Auto-detect schema from Excel/CSV
    - Project isolation (table prefixes)
    - Cross-sheet joins via common keys (Employee ID, etc.)
    - Natural language to SQL translation
    - Export results to Excel/CSV
    - PII encryption at rest
    - Load versioning and comparison
    """
    
    def __init__(self, db_path: str = DUCKDB_PATH):
        """Initialize DuckDB connection and create required directories"""
        # Create all required directories
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        os.makedirs("/data/exports", exist_ok=True)
        
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        self.encryptor = FieldEncryptor()
        self._init_metadata_table()
        logger.warning(f"[HANDLER] StructuredDataHandler initialized with {db_path}")
    
    def _init_metadata_table(self):
        """Create metadata table to track schemas and versions"""
        try:
            # Try to drop old tables if they have incompatible schema
            # This handles upgrades from old versions
            try:
                # Check if old schema exists (with PRIMARY KEY constraint)
                result = self.conn.execute("""
                    SELECT COUNT(*) FROM information_schema.columns 
                    WHERE table_name = '_schema_metadata'
                """).fetchone()
                
                if result and result[0] > 0:
                    # Table exists - check if it has the old schema by trying an insert
                    # If it fails, we need to recreate
                    logger.info("Metadata tables exist, checking compatibility...")
            except:
                pass
            
            # Create sequences for auto-increment
            self.conn.execute("""
                CREATE SEQUENCE IF NOT EXISTS schema_metadata_seq START 1
            """)
            
            self.conn.execute("""
                CREATE SEQUENCE IF NOT EXISTS load_versions_seq START 1
            """)
            
            # Create metadata table (will be no-op if already exists with same schema)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS _schema_metadata (
                    id INTEGER DEFAULT nextval('schema_metadata_seq'),
                    project VARCHAR NOT NULL,
                    file_name VARCHAR NOT NULL,
                    sheet_name VARCHAR NOT NULL,
                    table_name VARCHAR NOT NULL,
                    columns JSON,
                    row_count INTEGER,
                    likely_keys JSON,
                    encrypted_columns JSON,
                    version INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_current BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Load versions table for tracking
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS _load_versions (
                    id INTEGER DEFAULT nextval('load_versions_seq'),
                    project VARCHAR NOT NULL,
                    file_name VARCHAR NOT NULL,
                    version INTEGER NOT NULL,
                    row_count INTEGER,
                    checksum VARCHAR,
                    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes VARCHAR
                )
            """)
            
            # Table relationships for JOINs
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS _table_relationships (
                    id INTEGER,
                    project VARCHAR NOT NULL,
                    source_table VARCHAR NOT NULL,
                    source_columns JSON NOT NULL,
                    target_table VARCHAR NOT NULL,
                    target_columns JSON NOT NULL,
                    relationship_type VARCHAR DEFAULT 'foreign_key',
                    confidence FLOAT DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Column semantic mappings (Claude-inferred + human overrides)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS _column_mappings (
                    id INTEGER,
                    project VARCHAR NOT NULL,
                    file_name VARCHAR NOT NULL,
                    table_name VARCHAR NOT NULL,
                    original_column VARCHAR NOT NULL,
                    semantic_type VARCHAR NOT NULL,
                    confidence FLOAT DEFAULT 0.5,
                    is_override BOOLEAN DEFAULT FALSE,
                    needs_review BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Mapping inference job status
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS _mapping_jobs (
                    id VARCHAR PRIMARY KEY,
                    project VARCHAR NOT NULL,
                    file_name VARCHAR NOT NULL,
                    status VARCHAR DEFAULT 'pending',
                    total_tables INTEGER DEFAULT 0,
                    completed_tables INTEGER DEFAULT 0,
                    mappings_found INTEGER DEFAULT 0,
                    needs_review_count INTEGER DEFAULT 0,
                    error_message VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # =================================================================
            # COLUMN PROFILES TABLE - Phase 1 Data Foundation
            # Stores detailed statistics about each column for intelligent
            # query generation and clarification decisions.
            # =================================================================
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS _column_profiles (
                    id INTEGER,
                    project VARCHAR NOT NULL,
                    table_name VARCHAR NOT NULL,
                    column_name VARCHAR NOT NULL,
                    
                    -- Data type info
                    inferred_type VARCHAR,           -- 'numeric', 'categorical', 'date', 'text', 'boolean'
                    original_dtype VARCHAR,          -- pandas dtype
                    
                    -- Basic stats
                    total_count INTEGER,             -- total rows
                    null_count INTEGER,              -- nulls/blanks
                    distinct_count INTEGER,          -- unique values
                    
                    -- For numeric columns
                    min_value DOUBLE,
                    max_value DOUBLE,
                    mean_value DOUBLE,
                    
                    -- For categorical columns (distinct_count <= 100)
                    distinct_values JSON,            -- ['A', 'T', 'L', ...]
                    value_distribution JSON,         -- {'A': 1500, 'T': 200, 'L': 50}
                    
                    -- For date columns
                    min_date VARCHAR,
                    max_date VARCHAR,
                    
                    -- Sample values (first 5 non-null)
                    sample_values JSON,
                    
                    -- Metadata
                    is_likely_key BOOLEAN DEFAULT FALSE,
                    is_categorical BOOLEAN DEFAULT FALSE,
                    
                    -- FILTER INTELLIGENCE (Phase 2.5)
                    filter_category VARCHAR,         -- 'status', 'company', 'organization', 'location', 'pay_type', 'employee_type', 'job', NULL
                    filter_priority INTEGER DEFAULT 0,  -- Higher = more likely to need clarification
                    
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    
                    -- Unique constraint
                    UNIQUE(project, table_name, column_name)
                )
            """)
            
            # MIGRATION: Add new columns if they don't exist (for existing databases)
            try:
                # Check if filter_category column exists
                cols = self.conn.execute("PRAGMA table_info(_column_profiles)").fetchall()
                col_names = [c[1] for c in cols]
                
                if 'filter_category' not in col_names:
                    logger.warning("[MIGRATION] Adding filter_category column to _column_profiles")
                    self.conn.execute("ALTER TABLE _column_profiles ADD COLUMN filter_category VARCHAR")
                
                if 'filter_priority' not in col_names:
                    logger.warning("[MIGRATION] Adding filter_priority column to _column_profiles")
                    self.conn.execute("ALTER TABLE _column_profiles ADD COLUMN filter_priority INTEGER DEFAULT 0")
                
                self.conn.commit()
            except Exception as mig_e:
                logger.warning(f"[MIGRATION] Column check/add: {mig_e}")
            
            self.conn.commit()
            logger.info("Metadata tables initialized successfully")
            
        except Exception as e:
            logger.warning(f"Metadata table init issue: {e}, attempting to recreate...")
            try:
                # Drop and recreate if there's a conflict
                self.conn.execute("DROP TABLE IF EXISTS _schema_metadata")
                self.conn.execute("DROP TABLE IF EXISTS _load_versions")
                self.conn.execute("DROP SEQUENCE IF EXISTS schema_metadata_seq")
                self.conn.execute("DROP SEQUENCE IF EXISTS load_versions_seq")
                self.conn.commit()
                
                # Recursive call to create fresh
                self._init_metadata_table()
            except Exception as e2:
                logger.error(f"Failed to recreate metadata tables: {e2}")
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize table/column names for SQL"""
        # Remove special chars, replace spaces with underscores
        sanitized = re.sub(r'[^\w\s]', '', str(name))
        sanitized = re.sub(r'\s+', '_', sanitized.strip())
        sanitized = sanitized.lower()
        # Ensure it doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = 'col_' + sanitized
        return sanitized or 'unnamed'
    
    def _split_horizontal_tables(self, file_path: str, sheet_name: str) -> List[Tuple[str, pd.DataFrame]]:
        """
        Detect and split horizontally arranged tables within a single sheet.
        Tables are separated by blank columns.
        
        Returns: List of (sub_table_name, dataframe) tuples
        """
        try:
            # Read raw sheet without header to detect structure
            raw_df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
            
            if raw_df.empty:
                return []
            
            # Find blank columns (all cells are NaN or empty)
            blank_cols = []
            for col_idx in range(len(raw_df.columns)):
                col_data = raw_df.iloc[:, col_idx]
                # Check if column is entirely blank
                is_blank = col_data.isna().all() or (col_data.astype(str).str.strip() == '').all()
                if is_blank:
                    blank_cols.append(col_idx)
            
            # If no blank columns or less than 2 column groups, no split needed
            if not blank_cols:
                return []
            
            # Find column groups (consecutive non-blank columns)
            all_cols = set(range(len(raw_df.columns)))
            non_blank_cols = sorted(all_cols - set(blank_cols))
            
            if not non_blank_cols:
                return []
            
            # Group consecutive columns
            groups = []
            current_group = [non_blank_cols[0]]
            
            for col_idx in non_blank_cols[1:]:
                if col_idx == current_group[-1] + 1:
                    current_group.append(col_idx)
                else:
                    if len(current_group) >= 2:  # Need at least 2 columns for a valid table
                        groups.append(current_group)
                    current_group = [col_idx]
            
            if len(current_group) >= 2:
                groups.append(current_group)
            
            # If only one group, no horizontal split needed
            if len(groups) <= 1:
                return []
            
            logger.info(f"Sheet '{sheet_name}': Found {len(groups)} horizontal tables")
            
            # Extract each table group
            result = []
            for group_cols in groups:
                try:
                    # Extract columns for this group
                    sub_df = raw_df.iloc[:, group_cols].copy()
                    
                    # Use first row as header
                    sub_df.columns = sub_df.iloc[0].fillna('').astype(str).tolist()
                    sub_df = sub_df.iloc[1:]  # Remove header row from data
                    
                    # Drop empty rows
                    sub_df = sub_df.dropna(how='all')
                    
                    if sub_df.empty or len(sub_df.columns) < 2:
                        continue
                    
                    # Get table name from first column header (e.g., "Benefit Change Reasons")
                    first_header = str(sub_df.columns[0]).strip()
                    if first_header and first_header.lower() not in ['unnamed', '', 'nan']:
                        # Try to extract a meaningful name
                        sub_table_name = first_header.split('\n')[0][:50]  # First 50 chars, first line
                    else:
                        sub_table_name = f"section_{len(result) + 1}"
                    
                    result.append((sub_table_name, sub_df))
                    logger.info(f"  - Extracted: '{sub_table_name}' ({len(sub_df)} rows, {len(sub_df.columns)} cols)")
                    
                except Exception as e:
                    logger.warning(f"Failed to extract column group: {e}")
                    continue
            
            return result
            
        except Exception as e:
            logger.warning(f"Horizontal table detection failed for '{sheet_name}': {e}")
            return []
    
    def _generate_table_name(self, project: str, file_name: str, sheet_name: str) -> str:
        """Generate unique table name for a sheet"""
        project_clean = self._sanitize_name(project)
        file_clean = self._sanitize_name(file_name.rsplit('.', 1)[0])  # Remove extension
        sheet_clean = self._sanitize_name(sheet_name)
        return f"{project_clean}__{file_clean}__{sheet_clean}"
    
    def _detect_column_types(self, df: pd.DataFrame) -> Dict[str, str]:
        """Detect SQL types for DataFrame columns"""
        type_map = {}
        for col in df.columns:
            sample = df[col].dropna()
            if len(sample) == 0:
                type_map[col] = 'VARCHAR'
                continue
            
            # Check if it's numeric
            if pd.api.types.is_numeric_dtype(sample):
                if pd.api.types.is_integer_dtype(sample):
                    type_map[col] = 'INTEGER'
                else:
                    type_map[col] = 'DOUBLE'
            # Check if it's datetime
            elif pd.api.types.is_datetime64_any_dtype(sample):
                type_map[col] = 'TIMESTAMP'
            else:
                # Try to detect dates in string format
                try:
                    pd.to_datetime(sample.head(10), errors='raise')
                    type_map[col] = 'DATE'
                except:
                    type_map[col] = 'VARCHAR'
        
        return type_map
    
    def _detect_key_columns(self, df: pd.DataFrame) -> List[str]:
        """Detect likely key/join columns (Employee ID, SSN, etc.)"""
        key_patterns = [
            r'emp.*id', r'employee.*id', r'ee.*id', r'worker.*id',
            r'ssn', r'social.*sec',
            r'badge', r'payroll.*id', r'person.*id',
            r'^id$', r'.*_id$'
        ]
        
        likely_keys = []
        for col in df.columns:
            col_lower = col.lower()
            for pattern in key_patterns:
                if re.search(pattern, col_lower):
                    # Verify it has mostly unique values
                    unique_ratio = df[col].nunique() / len(df) if len(df) > 0 else 0
                    if unique_ratio > 0.5:  # At least 50% unique
                        likely_keys.append(col)
                    break
        
        return likely_keys
    
    def detect_relationships(self, project: str) -> List[Dict[str, Any]]:
        """
        Detect relationships between tables in a project.
        
        UKG KEY CONCEPT: Composite key of company_code + employee_number
        (Same employee number can exist in different companies)
        
        Returns list of detected relationships.
        """
        relationships = []
        
        try:
            # Get all tables for this project
            tables_result = self.conn.execute("""
                SELECT table_name, sheet_name, columns
                FROM _schema_metadata
                WHERE project = ? AND is_current = TRUE
            """, [project]).fetchall()
            
            if not tables_result:
                return relationships
            
            # Build column map: table_name -> set of columns
            table_columns = {}
            for table_name, sheet_name, columns_json in tables_result:
                try:
                    columns = json.loads(columns_json) if columns_json else []
                    col_names = [c.get('name', c) if isinstance(c, dict) else c for c in columns]
                    table_columns[table_name] = {
                        'sheet': sheet_name,
                        'columns': set(col_names),
                        'column_list': col_names
                    }
                except:
                    continue
            
            # UKG Composite Key Patterns (priority order)
            ukg_key_patterns = [
                # Composite: company + employee (most important for UKG)
                (['company_code', 'employee_number'], 'ukg_composite'),
                (['company', 'employee_number'], 'ukg_composite'),
                (['co_code', 'ee_number'], 'ukg_composite'),
                
                # Single key fallbacks
                (['employee_number'], 'employee_key'),
                (['employee_id'], 'employee_key'),
                (['ee_number'], 'employee_key'),
            ]
            
            # Find tables with employee data (not config tables)
            employee_tables = []
            for table_name, info in table_columns.items():
                cols_lower = {c.lower() for c in info['columns']}
                
                # Must have employee-related columns
                has_employee_col = any(
                    'employee' in c or 'ee_' in c or 'emp_' in c 
                    for c in cols_lower
                )
                
                if has_employee_col:
                    employee_tables.append(table_name)
            
            logger.info(f"[RELATIONSHIPS] Found {len(employee_tables)} employee data tables")
            
            # For each pair of employee tables, find matching key columns
            processed_pairs = set()
            
            for source_table in employee_tables:
                source_info = table_columns[source_table]
                source_cols_lower = {c.lower(): c for c in source_info['columns']}
                
                for target_table in employee_tables:
                    if source_table == target_table:
                        continue
                    
                    # Avoid duplicate pairs
                    pair_key = tuple(sorted([source_table, target_table]))
                    if pair_key in processed_pairs:
                        continue
                    processed_pairs.add(pair_key)
                    
                    target_info = table_columns[target_table]
                    target_cols_lower = {c.lower(): c for c in target_info['columns']}
                    
                    # Try each key pattern
                    for key_cols, key_type in ukg_key_patterns:
                        # Check if both tables have all key columns
                        source_matches = []
                        target_matches = []
                        
                        for key_col in key_cols:
                            # Find matching column in source (fuzzy match)
                            source_match = None
                            for col_lower, col_orig in source_cols_lower.items():
                                if key_col in col_lower or col_lower in key_col:
                                    source_match = col_orig
                                    break
                            
                            # Find matching column in target
                            target_match = None
                            for col_lower, col_orig in target_cols_lower.items():
                                if key_col in col_lower or col_lower in key_col:
                                    target_match = col_orig
                                    break
                            
                            if source_match and target_match:
                                source_matches.append(source_match)
                                target_matches.append(target_match)
                        
                        # If all key columns found in both tables, we have a relationship
                        if len(source_matches) == len(key_cols) and len(target_matches) == len(key_cols):
                            relationship = {
                                'source_table': source_table,
                                'source_sheet': source_info['sheet'],
                                'source_columns': source_matches,
                                'target_table': target_table,
                                'target_sheet': target_info['sheet'],
                                'target_columns': target_matches,
                                'key_type': key_type,
                                'confidence': 1.0 if key_type == 'ukg_composite' else 0.8
                            }
                            relationships.append(relationship)
                            
                            logger.info(f"[RELATIONSHIPS] Found: {source_info['sheet']}.{source_matches} -> {target_info['sheet']}.{target_matches} ({key_type})")
                            break  # Use first matching pattern (highest priority)
            
            # Store relationships in database
            if relationships:
                # Clear old relationships for this project
                self.conn.execute("""
                    DELETE FROM _table_relationships WHERE project = ?
                """, [project])
                
                # Insert new relationships
                for rel in relationships:
                    self.conn.execute("""
                        INSERT INTO _table_relationships 
                        (id, project, source_table, source_columns, target_table, target_columns, relationship_type, confidence)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        len(relationships),
                        project,
                        rel['source_table'],
                        json.dumps(rel['source_columns']),
                        rel['target_table'],
                        json.dumps(rel['target_columns']),
                        rel['key_type'],
                        rel['confidence']
                    ])
                
                self.conn.commit()
                logger.info(f"[RELATIONSHIPS] Stored {len(relationships)} relationships for project {project}")
            
            return relationships
            
        except Exception as e:
            logger.error(f"[RELATIONSHIPS] Detection failed: {e}")
            return []
    
    def get_relationships(self, project: str) -> List[Dict[str, Any]]:
        """Get stored relationships for a project"""
        try:
            result = self.conn.execute("""
                SELECT source_table, source_columns, target_table, target_columns, 
                       relationship_type, confidence
                FROM _table_relationships
                WHERE project = ?
            """, [project]).fetchall()
            
            relationships = []
            for row in result:
                relationships.append({
                    'source_table': row[0],
                    'source_columns': json.loads(row[1]) if row[1] else [],
                    'target_table': row[2],
                    'target_columns': json.loads(row[3]) if row[3] else [],
                    'relationship_type': row[4],
                    'confidence': row[5]
                })
            
            return relationships
        except Exception as e:
            logger.warning(f"Failed to get relationships: {e}")
            return []
    
    # =========================================================================
    # COLUMN MAPPING METHODS (Claude-inferred + human override)
    # =========================================================================
    
    def infer_column_mappings(self, project: str, file_name: str, table_name: str, 
                               columns: List[str], sample_data: List[Dict]) -> List[Dict]:
        """
        Use Claude to infer semantic meaning of columns.
        
        Args:
            project: Project name
            file_name: Source file name
            table_name: DuckDB table name
            columns: List of column names
            sample_data: First few rows of data
            
        Returns:
            List of mapping dicts with confidence scores
        """
        mappings = []
        
        try:
            # Prepare sample data string
            sample_str = ""
            for i, row in enumerate(sample_data[:5]):
                sample_str += f"Row {i+1}: {row}\n"
            
            # Build prompt for Claude
            prompt = f"""Analyze these column names and sample data to identify semantic types.

COLUMN NAMES:
{columns}

SAMPLE DATA:
{sample_str}

For each column, identify if it matches one of these semantic types:
- employee_number: Employee ID/number (unique identifier for employees)
- company_code: Company/organization code
- employment_status_code: Employment status (A=Active, T=Terminated, L=Leave, etc.)
- earning_code: Earning type codes
- deduction_code: Deduction/benefit codes
- job_code: Job/position codes
- department_code: Department/org unit codes
- amount: Monetary amounts (pay, deductions, etc.)
- rate: Pay rates (hourly, salary)
- effective_date: Date fields for effective dates
- start_date: Start dates
- end_date: End dates
- employee_name: Employee name field
- NONE: Does not match any semantic type

Respond with JSON array only, no explanation:
[
  {{"column": "column_name", "semantic_type": "type_or_NONE", "confidence": 0.0-1.0}},
  ...
]

Include ALL columns. Use confidence 0.9+ for obvious matches, 0.7-0.9 for likely matches, below 0.7 for uncertain."""

            # Call Claude for inference
            import anthropic
            import os
            
            api_key = os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('CLAUDE_API_KEY')
            if not api_key:
                logger.warning("[MAPPINGS] No API key available for inference")
                return self._fallback_column_inference(columns)
            
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text.strip()
            
            # Parse JSON response
            # Handle markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            inferred = json.loads(response_text)
            
            # Store mappings
            for item in inferred:
                col = item.get('column', '')
                sem_type = item.get('semantic_type', 'NONE')
                confidence = item.get('confidence', 0.5)
                
                if sem_type and sem_type != 'NONE':
                    needs_review = confidence < 0.85
                    
                    mapping = {
                        'project': project,
                        'file_name': file_name,
                        'table_name': table_name,
                        'original_column': col,
                        'semantic_type': sem_type,
                        'confidence': confidence,
                        'is_override': False,
                        'needs_review': needs_review
                    }
                    mappings.append(mapping)
                    
                    # Store in database
                    self._store_column_mapping(mapping)
            
            logger.info(f"[MAPPINGS] Inferred {len(mappings)} semantic mappings for {table_name}")
            return mappings
            
        except Exception as e:
            logger.warning(f"[MAPPINGS] Claude inference failed: {e}, using fallback")
            return self._fallback_column_inference(columns, project, file_name, table_name)
    
    def _fallback_column_inference(self, columns: List[str], project: str = None, 
                                    file_name: str = None, table_name: str = None) -> List[Dict]:
        """Pattern-based fallback when Claude is unavailable"""
        mappings = []
        
        patterns = {
            'employee_number': [r'employee.*num', r'emp.*num', r'ee.*num', r'emp.*id', r'employee.*id', r'^emp_no$', r'^ee_id$'],
            'company_code': [r'company.*code', r'co.*code', r'comp.*code', r'home.*company'],
            'employment_status_code': [r'employment.*status', r'emp.*status', r'status.*code'],
            'earning_code': [r'earning.*code', r'earn.*code'],
            'deduction_code': [r'deduction.*code', r'ded.*code', r'benefit.*code'],
            'job_code': [r'job.*code', r'position.*code'],
            'department_code': [r'dept.*code', r'department.*code', r'org.*level'],
            'amount': [r'amount', r'amt$', r'_amt$'],
            'rate': [r'rate$', r'pay.*rate', r'hourly.*rate', r'salary'],
            'effective_date': [r'effective.*date', r'eff.*date'],
            'employee_name': [r'^name$', r'employee.*name', r'emp.*name', r'full.*name']
        }
        
        for col in columns:
            col_lower = col.lower()
            for sem_type, pattern_list in patterns.items():
                for pattern in pattern_list:
                    if re.search(pattern, col_lower):
                        mapping = {
                            'project': project,
                            'file_name': file_name,
                            'table_name': table_name,
                            'original_column': col,
                            'semantic_type': sem_type,
                            'confidence': 0.7,  # Lower confidence for pattern matching
                            'is_override': False,
                            'needs_review': True
                        }
                        mappings.append(mapping)
                        
                        if project and file_name and table_name:
                            self._store_column_mapping(mapping)
                        break
                else:
                    continue
                break
        
        return mappings
    
    def _store_column_mapping(self, mapping: Dict):
        """Store a single column mapping in database"""
        try:
            # Check if mapping already exists
            existing = self.conn.execute("""
                SELECT id FROM _column_mappings 
                WHERE project = ? AND table_name = ? AND original_column = ?
            """, [mapping['project'], mapping['table_name'], mapping['original_column']]).fetchone()
            
            if existing:
                # Update existing (only if not an override)
                self.conn.execute("""
                    UPDATE _column_mappings 
                    SET semantic_type = ?, confidence = ?, needs_review = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE project = ? AND table_name = ? AND original_column = ? AND is_override = FALSE
                """, [
                    mapping['semantic_type'],
                    mapping['confidence'],
                    mapping['needs_review'],
                    mapping['project'],
                    mapping['table_name'],
                    mapping['original_column']
                ])
            else:
                # Insert new
                self.conn.execute("""
                    INSERT INTO _column_mappings 
                    (id, project, file_name, table_name, original_column, semantic_type, 
                     confidence, is_override, needs_review)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    hash(f"{mapping['project']}_{mapping['table_name']}_{mapping['original_column']}") % 2147483647,
                    mapping['project'],
                    mapping['file_name'],
                    mapping['table_name'],
                    mapping['original_column'],
                    mapping['semantic_type'],
                    mapping['confidence'],
                    mapping['is_override'],
                    mapping['needs_review']
                ])
            
            self.conn.commit()
        except Exception as e:
            logger.warning(f"[MAPPINGS] Failed to store mapping: {e}")
    
    def get_column_mappings(self, project: str, file_name: str = None, 
                            table_name: str = None) -> List[Dict]:
        """
        Get column mappings for a project/file/table.
        
        Args:
            project: Project name (required)
            file_name: Optional file filter
            table_name: Optional table filter
            
        Returns:
            List of mapping dicts
        """
        try:
            query = "SELECT * FROM _column_mappings WHERE project = ?"
            params = [project]
            
            if file_name:
                query += " AND file_name = ?"
                params.append(file_name)
            
            if table_name:
                query += " AND table_name = ?"
                params.append(table_name)
            
            query += " ORDER BY table_name, original_column"
            
            result = self.conn.execute(query, params).fetchall()
            
            mappings = []
            for row in result:
                mappings.append({
                    'id': row[0],
                    'project': row[1],
                    'file_name': row[2],
                    'table_name': row[3],
                    'original_column': row[4],
                    'semantic_type': row[5],
                    'confidence': row[6],
                    'is_override': row[7],
                    'needs_review': row[8],
                    'created_at': str(row[9]) if row[9] else None,
                    'updated_at': str(row[10]) if row[10] else None
                })
            
            return mappings
            
        except Exception as e:
            logger.warning(f"[MAPPINGS] Failed to get mappings: {e}")
            return []
    
    def update_column_mapping(self, project: str, table_name: str, 
                               original_column: str, semantic_type: str) -> bool:
        """
        Human override of a column mapping.
        
        Args:
            project: Project name
            table_name: Table name
            original_column: Column to update
            semantic_type: New semantic type (or 'NONE' to remove)
            
        Returns:
            True if successful
        """
        try:
            if semantic_type == 'NONE':
                # Remove the mapping
                self.conn.execute("""
                    DELETE FROM _column_mappings 
                    WHERE project = ? AND table_name = ? AND original_column = ?
                """, [project, table_name, original_column])
            else:
                # Check if exists
                existing = self.conn.execute("""
                    SELECT id FROM _column_mappings 
                    WHERE project = ? AND table_name = ? AND original_column = ?
                """, [project, table_name, original_column]).fetchone()
                
                if existing:
                    # Update with override flag
                    self.conn.execute("""
                        UPDATE _column_mappings 
                        SET semantic_type = ?, confidence = 1.0, is_override = TRUE, 
                            needs_review = FALSE, updated_at = CURRENT_TIMESTAMP
                        WHERE project = ? AND table_name = ? AND original_column = ?
                    """, [semantic_type, project, table_name, original_column])
                else:
                    # Insert new override
                    self.conn.execute("""
                        INSERT INTO _column_mappings 
                        (id, project, file_name, table_name, original_column, semantic_type, 
                         confidence, is_override, needs_review)
                        VALUES (?, ?, '', ?, ?, ?, 1.0, TRUE, FALSE)
                    """, [
                        hash(f"{project}_{table_name}_{original_column}") % 2147483647,
                        project,
                        table_name,
                        original_column,
                        semantic_type
                    ])
            
            self.conn.commit()
            logger.info(f"[MAPPINGS] Updated {original_column} -> {semantic_type}")
            return True
            
        except Exception as e:
            logger.error(f"[MAPPINGS] Failed to update mapping: {e}")
            return False
    
    def get_semantic_column(self, project: str, table_name: str, 
                            semantic_type: str) -> Optional[str]:
        """
        Find which column maps to a semantic type.
        Used by JOIN logic to find employee_number, company_code, etc.
        
        Args:
            project: Project name
            table_name: Table name
            semantic_type: What we're looking for (e.g., 'employee_number')
            
        Returns:
            Column name or None
        """
        try:
            result = self.conn.execute("""
                SELECT original_column FROM _column_mappings
                WHERE project = ? AND table_name = ? AND semantic_type = ?
                ORDER BY confidence DESC
                LIMIT 1
            """, [project, table_name, semantic_type]).fetchone()
            
            return result[0] if result else None
            
        except Exception as e:
            logger.warning(f"[MAPPINGS] Failed to get semantic column: {e}")
            return None
    
    def get_mappings_needing_review(self, project: str) -> List[Dict]:
        """Get all mappings flagged for review"""
        try:
            result = self.conn.execute("""
                SELECT * FROM _column_mappings 
                WHERE project = ? AND needs_review = TRUE
                ORDER BY confidence ASC, table_name, original_column
            """, [project]).fetchall()
            
            mappings = []
            for row in result:
                mappings.append({
                    'id': row[0],
                    'project': row[1],
                    'file_name': row[2],
                    'table_name': row[3],
                    'original_column': row[4],
                    'semantic_type': row[5],
                    'confidence': row[6],
                    'is_override': row[7],
                    'needs_review': row[8]
                })
            
            return mappings
            
        except Exception as e:
            logger.warning(f"[MAPPINGS] Failed to get review items: {e}")
            return []
    
    # =========================================================================
    # MAPPING JOB MANAGEMENT (Background inference tracking)
    # =========================================================================
    
    def create_mapping_job(self, job_id: str, project: str, file_name: str, 
                           total_tables: int) -> Dict:
        """Create a new mapping inference job"""
        try:
            self.conn.execute("""
                INSERT INTO _mapping_jobs 
                (id, project, file_name, status, total_tables, completed_tables, 
                 mappings_found, needs_review_count)
                VALUES (?, ?, ?, 'running', ?, 0, 0, 0)
            """, [job_id, project, file_name, total_tables])
            self.conn.commit()
            
            return {
                'id': job_id,
                'project': project,
                'file_name': file_name,
                'status': 'running',
                'total_tables': total_tables
            }
        except Exception as e:
            logger.error(f"[MAPPING_JOB] Failed to create job: {e}")
            return None
    
    def update_mapping_job(self, job_id: str, completed_tables: int = None,
                           mappings_found: int = None, needs_review_count: int = None,
                           status: str = None, error_message: str = None):
        """Update mapping job progress"""
        try:
            updates = ["updated_at = CURRENT_TIMESTAMP"]
            params = []
            
            if completed_tables is not None:
                updates.append("completed_tables = ?")
                params.append(completed_tables)
            if mappings_found is not None:
                updates.append("mappings_found = ?")
                params.append(mappings_found)
            if needs_review_count is not None:
                updates.append("needs_review_count = ?")
                params.append(needs_review_count)
            if status is not None:
                updates.append("status = ?")
                params.append(status)
            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)
            
            params.append(job_id)
            
            self.conn.execute(f"""
                UPDATE _mapping_jobs 
                SET {', '.join(updates)}
                WHERE id = ?
            """, params)
            self.conn.commit()
            
        except Exception as e:
            logger.warning(f"[MAPPING_JOB] Failed to update job: {e}")
    
    def get_mapping_job_status(self, job_id: str = None, project: str = None, 
                                file_name: str = None) -> Optional[Dict]:
        """Get mapping job status by ID or project/file"""
        try:
            if job_id:
                result = self.conn.execute("""
                    SELECT * FROM _mapping_jobs WHERE id = ?
                """, [job_id]).fetchone()
            elif project and file_name:
                result = self.conn.execute("""
                    SELECT * FROM _mapping_jobs 
                    WHERE project = ? AND file_name = ?
                    ORDER BY created_at DESC LIMIT 1
                """, [project, file_name]).fetchone()
            else:
                return None
            
            if result:
                return {
                    'id': result[0],
                    'project': result[1],
                    'file_name': result[2],
                    'status': result[3],
                    'total_tables': result[4],
                    'completed_tables': result[5],
                    'mappings_found': result[6],
                    'needs_review_count': result[7],
                    'error_message': result[8],
                    'created_at': str(result[9]) if result[9] else None,
                    'updated_at': str(result[10]) if result[10] else None
                }
            return None
            
        except Exception as e:
            logger.warning(f"[MAPPING_JOB] Failed to get status: {e}")
            return None
    
    def get_file_mapping_summary(self, project: str, file_name: str) -> Dict:
        """Get mapping summary for a file (for UI display)"""
        try:
            # Get job status
            job = self.get_mapping_job_status(project=project, file_name=file_name)
            
            # Get actual mapping counts
            mapping_result = self.conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN needs_review = TRUE THEN 1 ELSE 0 END) as needs_review
                FROM _column_mappings 
                WHERE project = ? AND file_name = ?
            """, [project, file_name]).fetchone()
            
            total_mappings = mapping_result[0] if mapping_result else 0
            needs_review_count = mapping_result[1] if mapping_result else 0
            
            # Get all mappings for this file
            mappings = self.get_column_mappings(project, file_name=file_name)
            
            return {
                'status': job['status'] if job else ('complete' if total_mappings > 0 else 'none'),
                'total_mappings': total_mappings,
                'needs_review_count': needs_review_count,
                'mappings': mappings,
                'job': job
            }
            
        except Exception as e:
            logger.warning(f"[MAPPING_JOB] Failed to get summary: {e}")
            return {'status': 'error', 'total_mappings': 0, 'needs_review_count': 0, 'mappings': []}
    
    def run_inference_for_file(self, job_id: str, project: str, file_name: str,
                                tables_info: List[Dict]):
        """
        Run column inference for all tables in a file.
        Called in background thread - uses separate DB connection for thread safety.
        """
        # Create separate connection for this thread
        thread_conn = None
        try:
            thread_conn = duckdb.connect(self.db_path)
            logger.info(f"[MAPPING_JOB] Started background inference with separate connection")
            
            total_mappings = 0
            total_needs_review = 0
            
            for i, table_info in enumerate(tables_info):
                table_name = table_info.get('table_name', '')
                columns = table_info.get('columns', [])
                sample_data = table_info.get('sample_data', [])
                
                logger.info(f"[MAPPING_JOB] Inferring {table_name} ({i+1}/{len(tables_info)})")
                
                # Run inference (uses thread connection)
                mappings = self._infer_column_mappings_threaded(
                    thread_conn=thread_conn,
                    project=project,
                    file_name=file_name,
                    table_name=table_name,
                    columns=columns,
                    sample_data=sample_data
                )
                
                # Count results
                total_mappings += len(mappings)
                total_needs_review += sum(1 for m in mappings if m.get('needs_review'))
                
                # Update progress (uses thread connection)
                self._update_mapping_job_threaded(
                    thread_conn,
                    job_id,
                    completed_tables=i + 1,
                    mappings_found=total_mappings,
                    needs_review_count=total_needs_review
                )
            
            # Mark complete
            self._update_mapping_job_threaded(thread_conn, job_id, status='complete')
            logger.info(f"[MAPPING_JOB] Complete: {total_mappings} mappings, {total_needs_review} need review")
            
        except Exception as e:
            logger.error(f"[MAPPING_JOB] Inference failed: {e}")
            if thread_conn:
                try:
                    self._update_mapping_job_threaded(thread_conn, job_id, status='error', error_message=str(e))
                except:
                    pass
        finally:
            if thread_conn:
                try:
                    thread_conn.close()
                    logger.info("[MAPPING_JOB] Closed background thread connection")
                except:
                    pass
    
    def _infer_column_mappings_threaded(self, thread_conn, project: str, file_name: str, 
                                         table_name: str, columns: List[str], 
                                         sample_data: List[Dict]) -> List[Dict]:
        """Thread-safe version of infer_column_mappings using provided connection"""
        mappings = []
        
        try:
            # Prepare sample data string
            sample_str = ""
            for i, row in enumerate(sample_data[:5]):
                sample_str += f"Row {i+1}: {row}\n"
            
            # Build prompt for Claude
            prompt = f"""Analyze these column names and sample data to identify semantic types.

COLUMN NAMES:
{columns}

SAMPLE DATA:
{sample_str}

For each column, identify if it matches one of these semantic types:
- employee_number: Employee ID/number (unique identifier for employees)
- company_code: Company/organization code
- employment_status_code: Employment status (A=Active, T=Terminated, L=Leave, etc.)
- earning_code: Earning type codes
- deduction_code: Deduction/benefit codes
- job_code: Job/position codes
- department_code: Department/org unit codes
- amount: Monetary amounts (pay, deductions, etc.)
- rate: Pay rates (hourly, salary)
- effective_date: Date fields for effective dates
- start_date: Start dates
- end_date: End dates
- employee_name: Employee name field
- NONE: Does not match any semantic type

Respond with JSON array only, no explanation:
[
  {{"column": "column_name", "semantic_type": "type_or_NONE", "confidence": 0.0-1.0}},
  ...
]

Include ALL columns. Use confidence 0.9+ for obvious matches, 0.7-0.9 for likely matches, below 0.7 for uncertain."""

            # Call Claude for inference
            import anthropic
            
            api_key = os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('CLAUDE_API_KEY')
            if not api_key:
                logger.warning("[MAPPINGS] No API key available for inference")
                return self._fallback_column_inference_threaded(thread_conn, columns, project, file_name, table_name)
            
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text.strip()
            
            # Parse JSON response
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            inferred = json.loads(response_text)
            
            # Store mappings using thread connection
            for item in inferred:
                col = item.get('column', '')
                sem_type = item.get('semantic_type', 'NONE')
                confidence = item.get('confidence', 0.5)
                
                if sem_type and sem_type != 'NONE':
                    needs_review = confidence < 0.85
                    
                    mapping = {
                        'project': project,
                        'file_name': file_name,
                        'table_name': table_name,
                        'original_column': col,
                        'semantic_type': sem_type,
                        'confidence': confidence,
                        'is_override': False,
                        'needs_review': needs_review
                    }
                    mappings.append(mapping)
                    
                    # Store using thread connection
                    self._store_column_mapping_threaded(thread_conn, mapping)
            
            logger.info(f"[MAPPINGS] Inferred {len(mappings)} semantic mappings for {table_name}")
            return mappings
            
        except Exception as e:
            logger.warning(f"[MAPPINGS] Claude inference failed: {e}, using fallback")
            return self._fallback_column_inference_threaded(thread_conn, columns, project, file_name, table_name)
    
    def _fallback_column_inference_threaded(self, thread_conn, columns: List[str], 
                                             project: str, file_name: str, table_name: str) -> List[Dict]:
        """Thread-safe pattern-based fallback"""
        mappings = []
        
        patterns = {
            'employee_number': [r'employee.*num', r'emp.*num', r'ee.*num', r'emp.*id', r'employee.*id', r'^emp_no$', r'^ee_id$'],
            'company_code': [r'company.*code', r'co.*code', r'comp.*code', r'home.*company'],
            'employment_status_code': [r'employment.*status', r'emp.*status', r'status.*code'],
            'earning_code': [r'earning.*code', r'earn.*code'],
            'deduction_code': [r'deduction.*code', r'ded.*code', r'benefit.*code'],
            'job_code': [r'job.*code', r'position.*code'],
            'department_code': [r'dept.*code', r'department.*code', r'org.*level'],
            'amount': [r'amount', r'amt$', r'_amt$'],
            'rate': [r'rate$', r'pay.*rate', r'hourly.*rate', r'salary'],
            'effective_date': [r'effective.*date', r'eff.*date'],
            'employee_name': [r'^name$', r'employee.*name', r'emp.*name', r'full.*name']
        }
        
        for col in columns:
            col_lower = col.lower()
            for sem_type, pattern_list in patterns.items():
                for pattern in pattern_list:
                    if re.search(pattern, col_lower):
                        mapping = {
                            'project': project,
                            'file_name': file_name,
                            'table_name': table_name,
                            'original_column': col,
                            'semantic_type': sem_type,
                            'confidence': 0.7,
                            'is_override': False,
                            'needs_review': True
                        }
                        mappings.append(mapping)
                        self._store_column_mapping_threaded(thread_conn, mapping)
                        break
                else:
                    continue
                break
        
        return mappings
    
    def _store_column_mapping_threaded(self, thread_conn, mapping: Dict):
        """Thread-safe mapping storage"""
        try:
            # Check if mapping already exists
            existing = thread_conn.execute("""
                SELECT id FROM _column_mappings 
                WHERE project = ? AND table_name = ? AND original_column = ?
            """, [mapping['project'], mapping['table_name'], mapping['original_column']]).fetchone()
            
            if existing:
                thread_conn.execute("""
                    UPDATE _column_mappings 
                    SET semantic_type = ?, confidence = ?, needs_review = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE project = ? AND table_name = ? AND original_column = ? AND is_override = FALSE
                """, [
                    mapping['semantic_type'],
                    mapping['confidence'],
                    mapping['needs_review'],
                    mapping['project'],
                    mapping['table_name'],
                    mapping['original_column']
                ])
            else:
                thread_conn.execute("""
                    INSERT INTO _column_mappings 
                    (id, project, file_name, table_name, original_column, semantic_type, 
                     confidence, is_override, needs_review)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    hash(f"{mapping['project']}_{mapping['table_name']}_{mapping['original_column']}") % 2147483647,
                    mapping['project'],
                    mapping['file_name'],
                    mapping['table_name'],
                    mapping['original_column'],
                    mapping['semantic_type'],
                    mapping['confidence'],
                    mapping['is_override'],
                    mapping['needs_review']
                ])
            
            thread_conn.commit()
        except Exception as e:
            logger.warning(f"[MAPPINGS] Failed to store mapping: {e}")
    
    def _update_mapping_job_threaded(self, thread_conn, job_id: str, completed_tables: int = None,
                                      mappings_found: int = None, needs_review_count: int = None,
                                      status: str = None, error_message: str = None):
        """Thread-safe job update"""
        try:
            updates = ["updated_at = CURRENT_TIMESTAMP"]
            params = []
            
            if completed_tables is not None:
                updates.append("completed_tables = ?")
                params.append(completed_tables)
            if mappings_found is not None:
                updates.append("mappings_found = ?")
                params.append(mappings_found)
            if needs_review_count is not None:
                updates.append("needs_review_count = ?")
                params.append(needs_review_count)
            if status is not None:
                updates.append("status = ?")
                params.append(status)
            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)
            
            params.append(job_id)
            
            thread_conn.execute(f"""
                UPDATE _mapping_jobs 
                SET {', '.join(updates)}
                WHERE id = ?
            """, params)
            thread_conn.commit()
        except Exception as e:
            logger.warning(f"[MAPPING_JOB] Failed to update job: {e}")
    
    def _get_next_version(self, project: str, file_name: str) -> int:
        """Get next version number for a file"""
        result = self.conn.execute("""
            SELECT COALESCE(MAX(version), 0) + 1 
            FROM _load_versions 
            WHERE project = ? AND file_name = ?
        """, [project, file_name]).fetchone()
        return result[0] if result else 1
    
    def _compute_checksum(self, df: pd.DataFrame) -> str:
        """Compute checksum of DataFrame for change detection"""
        # Use first 1000 rows for checksum (performance)
        sample = df.head(1000)
        data_str = sample.to_json()
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def store_excel(
        self,
        file_path: str,
        project: str,
        file_name: str,
        encrypt_pii: bool = False,  # Disabled - security at perimeter (Railway, API auth, HTTPS)
        keep_previous_version: bool = True
    ) -> Dict[str, Any]:
        """
        Store Excel file in DuckDB with encryption and versioning.
        Each sheet becomes a table.
        
        Args:
            file_path: Path to Excel file
            project: Project name
            file_name: Original filename
            encrypt_pii: Whether to encrypt PII columns
            keep_previous_version: Whether to keep previous version for comparison
        
        Returns schema info for Claude to use in queries.
        """
        results = {
            'project': project,
            'file_name': file_name,
            'sheets': [],
            'total_rows': 0,
            'tables_created': [],
            'encrypted_columns': [],
            'version': 1
        }
        
        try:
            # Get version number
            version = self._get_next_version(project, file_name)
            results['version'] = version
            
            # =================================================================
            # SPECIAL HANDLING FOR GLOBAL YEAR-END FILES
            # When uploading a new Year-End file to GLOBAL, mark ALL other
            # year-end files as not current (even with different filenames)
            # =================================================================
            if project.lower() == 'global':
                file_lower = file_name.lower()
                is_year_end = any(kw in file_lower for kw in ['year-end', 'year_end', 'yearend', 'checklist'])
                
                if is_year_end:
                    logger.info(f"[STORE_EXCEL] Detected GLOBAL Year-End file: {file_name}")
                    # Mark ALL other year-end files as not current
                    self.conn.execute("""
                        UPDATE _schema_metadata 
                        SET is_current = FALSE 
                        WHERE LOWER(project) = 'global'
                        AND file_name != ?
                        AND (
                            LOWER(file_name) LIKE '%year-end%'
                            OR LOWER(file_name) LIKE '%year_end%'
                            OR LOWER(file_name) LIKE '%yearend%'
                            OR LOWER(file_name) LIKE '%checklist%'
                        )
                    """, [file_name])
                    logger.info(f"[STORE_EXCEL] Marked other Year-End files as not current")
            
            # If keeping previous version, rename old tables
            if keep_previous_version and version > 1:
                self._archive_previous_version(project, file_name, version - 1)
            
            # Read all sheets
            excel_file = pd.ExcelFile(file_path)
            
            all_encrypted_cols = []
            
            for sheet_name in excel_file.sheet_names:
                try:
                    # =====================================================
                    # CHECK FOR HORIZONTAL TABLES (tables side-by-side)
                    # =====================================================
                    horizontal_tables = self._split_horizontal_tables(file_path, sheet_name)
                    
                    if horizontal_tables:
                        # Process each horizontal sub-table separately
                        for sub_table_name, sub_df in horizontal_tables:
                            try:
                                # Sanitize column names
                                sub_df.columns = [self._sanitize_name(str(c)) for c in sub_df.columns]
                                
                                # Handle duplicate column names
                                seen = {}
                                new_cols = []
                                for col in sub_df.columns:
                                    if col in seen:
                                        seen[col] += 1
                                        new_cols.append(f"{col}_{seen[col]}")
                                    else:
                                        seen[col] = 0
                                        new_cols.append(col)
                                sub_df.columns = new_cols
                                
                                # Force all columns to string
                                for col in sub_df.columns:
                                    sub_df[col] = sub_df[col].fillna('').astype(str)
                                    sub_df[col] = sub_df[col].replace({'nan': '', 'None': '', 'NaT': ''})
                                
                                # Generate combined sheet name: "Change Reasons - Benefit Change Reasons"
                                combined_sheet = f"{sheet_name} - {sub_table_name}"
                                
                                # Encrypt PII if needed
                                encrypted_cols = []
                                if encrypt_pii and self.encryptor.fernet:
                                    sub_df, encrypted_cols = self.encryptor.encrypt_dataframe(sub_df)
                                    all_encrypted_cols.extend(encrypted_cols)
                                
                                # Generate table name
                                table_name = self._generate_table_name(project, file_name, combined_sheet)
                                
                                # Drop existing and create table
                                self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                                self.conn.register('temp_df', sub_df)
                                self.conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_df")
                                self.conn.unregister('temp_df')
                                
                                # Store metadata
                                columns_info = [
                                    {'name': col, 'type': 'VARCHAR', 'encrypted': col in encrypted_cols}
                                    for col in sub_df.columns
                                ]
                                
                                self.conn.execute("""
                                    INSERT INTO _schema_metadata 
                                    (id, project, file_name, sheet_name, table_name, columns, row_count, likely_keys, encrypted_columns, version, is_current)
                                    VALUES (nextval('schema_metadata_seq'), ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE)
                                """, [
                                    project,
                                    file_name,
                                    combined_sheet,
                                    table_name,
                                    json.dumps(columns_info),
                                    len(sub_df),
                                    json.dumps([]),
                                    json.dumps(encrypted_cols),
                                    version
                                ])
                                
                                results['sheets'].append({
                                    'name': combined_sheet,
                                    'table_name': table_name,
                                    'rows': len(sub_df),
                                    'columns': list(sub_df.columns),
                                    'encrypted_columns': encrypted_cols
                                })
                                results['total_rows'] += len(sub_df)
                                results['tables_created'].append(table_name)
                                
                                # Profile horizontal sub-table
                                try:
                                    profile_result = self.profile_columns(project, table_name)
                                    results['sheets'][-1]['column_profiles'] = profile_result.get('profiles', {})
                                    results['sheets'][-1]['categorical_columns'] = profile_result.get('categorical_columns', [])
                                except Exception as profile_e:
                                    logger.warning(f"[PROFILING] Failed for horizontal sub-table {table_name}: {profile_e}")
                                
                                logger.info(f"Created horizontal sub-table: {table_name} ({len(sub_df)} rows)")
                                
                            except Exception as sub_e:
                                logger.error(f"Failed to process horizontal sub-table '{sub_table_name}': {sub_e}")
                        
                        # Skip normal processing for this sheet - we handled it horizontally
                        continue
                    
                    # =====================================================
                    # NORMAL SHEET PROCESSING (no horizontal split)
                    # =====================================================
                    # Read sheet - SMART HEADER DETECTION
                    # Strategy: Look for colored (blue) header rows first, then fall back to text analysis
                    df = None
                    best_header_row = 0
                    
                    # Try to detect colored header row using openpyxl
                    if OPENPYXL_AVAILABLE:
                        try:
                            wb = load_workbook(file_path, read_only=True, data_only=True)
                            if sheet_name in wb.sheetnames:
                                ws = wb[sheet_name]
                                
                                # Check first 15 rows for colored cells (headers are usually colored)
                                for row_idx in range(1, 16):
                                    colored_cells = 0
                                    total_cells = 0
                                    
                                    for col_idx in range(1, min(20, (ws.max_column or 0) + 1)):
                                        try:
                                            cell = ws.cell(row=row_idx, column=col_idx)
                                            if cell.value is not None:
                                                total_cells += 1
                                                # Check if cell has fill color (not white/no fill)
                                                if cell.fill and cell.fill.fgColor and cell.fill.fgColor.rgb:
                                                    color = str(cell.fill.fgColor.rgb)
                                                    # Skip white, no fill, or default
                                                    if color not in ['00000000', 'FFFFFFFF', '00FFFFFF', None, 'None']:
                                                        colored_cells += 1
                                        except:
                                            continue
                                    
                                    # If most cells in this row are colored, it's likely the header
                                    if total_cells >= 3 and colored_cells >= total_cells * 0.5:
                                        best_header_row = row_idx - 1  # pandas uses 0-based indexing
                                        logger.info(f"Sheet '{sheet_name}': Detected colored header at row {row_idx}")
                                        break
                                
                                wb.close()
                        except Exception as e:
                            logger.warning(f"Color detection failed for '{sheet_name}': {e}")
                    
                    # If no colored header found, try text-based detection
                    if best_header_row == 0:
                        min_unnamed = float('inf')
                        for header_row in range(11):  # Try rows 0-10
                            try:
                                test_df = pd.read_excel(
                                    file_path, 
                                    sheet_name=sheet_name, 
                                    header=header_row,
                                    nrows=5
                                )
                                
                                # Count unnamed columns
                                unnamed_count = sum(1 for c in test_df.columns if str(c).startswith('Unnamed'))
                                total_cols = len([c for c in test_df.columns if not str(c).startswith('Unnamed')])
                                
                                if total_cols < 2:
                                    continue
                                
                                if unnamed_count < min_unnamed:
                                    min_unnamed = unnamed_count
                                    best_header_row = header_row
                                    
                                if unnamed_count == 0:
                                    break
                                    
                            except:
                                continue
                    
                    # Read with detected header row
                    try:
                        df = pd.read_excel(
                            file_path, 
                            sheet_name=sheet_name, 
                            header=best_header_row
                        )
                        logger.info(f"Sheet '{sheet_name}': Using header row {best_header_row}")
                    except Exception as e:
                        logger.error(f"Failed to read sheet '{sheet_name}': {e}")
                        continue
                    
                    if df is None or df.empty:
                        logger.warning(f"Sheet '{sheet_name}' is empty, skipping")
                        continue
                    
                    # Drop completely empty rows/columns
                    df = df.dropna(how='all').dropna(axis=1, how='all')
                    
                    if df.empty:
                        continue
                    
                    # Sanitize column names
                    df.columns = [self._sanitize_name(str(c)) for c in df.columns]
                    
                    # Handle duplicate column names
                    seen = {}
                    new_cols = []
                    for col in df.columns:
                        if col in seen:
                            seen[col] += 1
                            new_cols.append(f"{col}_{seen[col]}")
                        else:
                            seen[col] = 0
                            new_cols.append(col)
                    df.columns = new_cols
                    
                    # FORCE ALL COLUMNS TO STRING to avoid DuckDB type inference issues
                    # This prevents errors like "Could not convert 'Amount' to DOUBLE"
                    for col in df.columns:
                        # Convert to string, then replace NaN/None with empty string
                        df[col] = df[col].fillna('').astype(str)
                        # Replace string 'nan' and 'None' that result from conversion
                        df[col] = df[col].replace({'nan': '', 'None': '', 'NaT': ''})
                    
                    # ENCRYPT PII COLUMNS
                    encrypted_cols = []
                    if encrypt_pii and self.encryptor.fernet:
                        df, encrypted_cols = self.encryptor.encrypt_dataframe(df)
                        all_encrypted_cols.extend(encrypted_cols)
                        if encrypted_cols:
                            logger.info(f"Encrypted {len(encrypted_cols)} PII columns in '{sheet_name}'")
                    
                    # Generate table name
                    table_name = self._generate_table_name(project, file_name, sheet_name)
                    
                    # Drop existing current table if exists
                    self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                    
                    # Create table from DataFrame - all VARCHAR columns
                    self.conn.register('temp_df', df)
                    self.conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_df")
                    self.conn.unregister('temp_df')
                    
                    # Detect key columns
                    likely_keys = self._detect_key_columns(df)
                    
                    # Store metadata
                    columns_info = [
                        {'name': col, 'type': str(df[col].dtype), 'encrypted': col in encrypted_cols}
                        for col in df.columns
                    ]
                    
                    # Mark previous metadata as not current
                    self.conn.execute("""
                        UPDATE _schema_metadata 
                        SET is_current = FALSE 
                        WHERE project = ? AND file_name = ? AND sheet_name = ?
                    """, [project, file_name, sheet_name])
                    
                    self.conn.execute("""
                        INSERT INTO _schema_metadata 
                        (id, project, file_name, sheet_name, table_name, columns, row_count, likely_keys, encrypted_columns, version, is_current)
                        VALUES (nextval('schema_metadata_seq'), ?, ?, ?, ?, ?, ?, ?, ?, ?, TRUE)
                    """, [
                        project,
                        file_name,
                        sheet_name,
                        table_name,
                        json.dumps(columns_info),
                        len(df),
                        json.dumps(likely_keys),
                        json.dumps(encrypted_cols),
                        version
                    ])
                    
                    sheet_info = {
                        'sheet_name': sheet_name,
                        'table_name': table_name,
                        'columns': list(df.columns),
                        'row_count': len(df),
                        'likely_keys': likely_keys,
                        'encrypted_columns': encrypted_cols,
                        'sample_data': df.head(3).to_dict('records')
                    }
                    
                    # =================================================
                    # COLUMN PROFILING - Phase 1 Data Foundation
                    # Profile columns to enable intelligent clarification
                    # =================================================
                    try:
                        profile_result = self.profile_columns(project, table_name)
                        sheet_info['column_profiles'] = profile_result.get('profiles', {})
                        sheet_info['categorical_columns'] = profile_result.get('categorical_columns', [])
                        logger.info(f"[PROFILING] {table_name}: {profile_result.get('columns_profiled', 0)} columns profiled")
                    except Exception as profile_e:
                        logger.warning(f"[PROFILING] Failed for {table_name}: {profile_e}")
                        sheet_info['column_profiles'] = {}
                        sheet_info['categorical_columns'] = []
                    
                    results['sheets'].append(sheet_info)
                    results['total_rows'] += len(df)
                    results['tables_created'].append(table_name)
                    
                    logger.info(f"Created table '{table_name}' with {len(df)} rows, {len(df.columns)} columns")
                    
                except Exception as e:
                    logger.error(f"Error processing sheet '{sheet_name}': {e}")
                    continue
            
            self.conn.commit()
            logger.info(f"Stored {len(results['tables_created'])} tables from {file_name}")
            
            # Detect relationships after loading
            try:
                relationships = self.detect_relationships(project)
                results['relationships'] = relationships
                logger.info(f"Detected {len(relationships)} table relationships")
            except Exception as rel_e:
                logger.warning(f"Relationship detection failed: {rel_e}")
                results['relationships'] = []
            
            # Start background column inference
            try:
                import uuid
                
                job_id = str(uuid.uuid4())[:8]
                tables_info = results.get('sheets', [])
                
                if tables_info:
                    # Create job record
                    self.create_mapping_job(job_id, project, file_name, len(tables_info))
                    results['mapping_job_id'] = job_id
                    
                    # Queue the job instead of starting a new thread
                    queue_inference_job(self, job_id, project, file_name, tables_info)
                    logger.info(f"[MAPPING] Queued inference job {job_id} for {file_name}")
            except Exception as map_e:
                logger.warning(f"[MAPPING] Failed to start inference: {map_e}")
            
        except Exception as e:
            logger.error(f"Error storing Excel file: {e}")
            raise
        
        return results
    
    def store_csv(
        self,
        file_path: str,
        project: str,
        file_name: str
    ) -> Dict[str, Any]:
        """Store CSV file in DuckDB"""
        try:
            df = pd.read_csv(file_path)
            df = df.dropna(how='all').dropna(axis=1, how='all')
            
            # Sanitize column names
            df.columns = [self._sanitize_name(str(c)) for c in df.columns]
            
            # FORCE ALL COLUMNS TO STRING to avoid type inference issues
            for col in df.columns:
                df[col] = df[col].fillna('').astype(str)
                df[col] = df[col].replace({'nan': '', 'None': '', 'NaT': ''})
            
            table_name = self._generate_table_name(project, file_name, 'data')
            
            # Drop existing table
            self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            # Create table
            self.conn.register('temp_df', df)
            self.conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_df")
            self.conn.unregister('temp_df')
            
            # Detect keys
            likely_keys = self._detect_key_columns(df)
            
            # Store metadata
            columns_info = [
                {'name': col, 'type': str(df[col].dtype)}
                for col in df.columns
            ]
            
            self.conn.execute("""
                INSERT INTO _schema_metadata 
                (id, project, file_name, sheet_name, table_name, columns, row_count, likely_keys)
                VALUES (nextval('schema_metadata_seq'), ?, ?, ?, ?, ?, ?, ?)
            """, [
                project, file_name, 'data', table_name,
                json.dumps(columns_info), len(df), json.dumps(likely_keys)
            ])
            
            self.conn.commit()
            
            # Profile columns for CSV
            profile_result = {}
            try:
                profile_result = self.profile_columns(project, table_name)
                logger.info(f"[PROFILING] CSV {table_name}: {profile_result.get('columns_profiled', 0)} columns profiled")
            except Exception as profile_e:
                logger.warning(f"[PROFILING] Failed for CSV {table_name}: {profile_e}")
            
            return {
                'project': project,
                'file_name': file_name,
                'table_name': table_name,
                'columns': list(df.columns),
                'row_count': len(df),
                'likely_keys': likely_keys,
                'column_profiles': profile_result.get('profiles', {}),
                'categorical_columns': profile_result.get('categorical_columns', [])
            }
            
        except Exception as e:
            logger.error(f"Error storing CSV: {e}")
            raise
    
    # =========================================================================
    # COLUMN PROFILING - Phase 1 Data Foundation
    # These methods analyze column data to enable intelligent query generation
    # and data-driven clarification decisions.
    # =========================================================================
    
    def profile_columns(self, project: str, table_name: str) -> Dict[str, Any]:
        """
        Analyze all columns in a table and store detailed profiles.
        
        This is the foundation for intelligent clarification:
        - Know what distinct values exist (e.g., status codes A, T, L)
        - Know value distributions (1500 Active, 200 Terminated)
        - Know numeric ranges (salary $30k - $500k)
        - Know which columns are categorical vs free-text
        
        Args:
            project: Project name
            table_name: DuckDB table name to profile
            
        Returns:
            Dict with profiling results and summary
        """
        logger.info(f"[PROFILING] Starting column profiling for {table_name}")
        
        result = {
            'table_name': table_name,
            'columns_profiled': 0,
            'categorical_columns': [],
            'numeric_columns': [],
            'date_columns': [],
            'profiles': {}
        }
        
        try:
            # Get all data for profiling (we need the full dataset for accurate stats)
            df = self.query_to_dataframe(f"SELECT * FROM {table_name}")
            
            if df.empty:
                logger.warning(f"[PROFILING] Table {table_name} is empty")
                return result
            
            # Decrypt PII columns for profiling (we'll store aggregates, not raw values)
            df = self.encryptor.decrypt_dataframe(df)
            
            for col in df.columns:
                profile = self._profile_single_column(df, col)
                profile['project'] = project
                profile['table_name'] = table_name
                profile['column_name'] = col
                
                # Store in database
                self._store_column_profile(profile)
                
                # Track by type
                result['profiles'][col] = profile
                result['columns_profiled'] += 1
                
                if profile['inferred_type'] == 'categorical':
                    result['categorical_columns'].append({
                        'name': col,
                        'distinct_count': profile['distinct_count'],
                        'values': profile.get('distinct_values', [])
                    })
                elif profile['inferred_type'] == 'numeric':
                    result['numeric_columns'].append({
                        'name': col,
                        'min': profile.get('min_value'),
                        'max': profile.get('max_value'),
                        'mean': profile.get('mean_value')
                    })
                elif profile['inferred_type'] == 'date':
                    result['date_columns'].append({
                        'name': col,
                        'min_date': profile.get('min_date'),
                        'max_date': profile.get('max_date')
                    })
            
            logger.info(f"[PROFILING] Completed {table_name}: {result['columns_profiled']} columns, "
                       f"{len(result['categorical_columns'])} categorical, "
                       f"{len(result['numeric_columns'])} numeric")
            
            return result
            
        except Exception as e:
            logger.error(f"[PROFILING] Failed for {table_name}: {e}")
            result['error'] = str(e)
            return result
    
    def _profile_single_column(self, df: pd.DataFrame, col: str) -> Dict[str, Any]:
        """
        Profile a single column and return statistics.
        """
        series = df[col]
        
        profile = {
            'column_name': col,
            'original_dtype': str(series.dtype),
            'total_count': len(series),
            'null_count': int(series.isna().sum() + (series == '').sum()),
            'distinct_count': 0,
            'inferred_type': 'text',
            'is_likely_key': False,
            'is_categorical': False,
            'distinct_values': None,
            'value_distribution': None,
            'min_value': None,
            'max_value': None,
            'mean_value': None,
            'min_date': None,
            'max_date': None,
            'sample_values': [],
            'filter_category': None,
            'filter_priority': 0
        }
        
        # Get non-null, non-empty values
        non_null = series[series.notna() & (series != '') & (series.astype(str) != 'nan')]
        
        if len(non_null) == 0:
            profile['inferred_type'] = 'empty'
            return profile
        
        # Get distinct values
        distinct_values = non_null.unique()
        profile['distinct_count'] = len(distinct_values)
        
        # Sample values (first 5 unique)
        profile['sample_values'] = [str(v) for v in distinct_values[:5]]
        
        # Check if this is a likely key column (high uniqueness)
        uniqueness_ratio = profile['distinct_count'] / len(non_null) if len(non_null) > 0 else 0
        profile['is_likely_key'] = uniqueness_ratio > 0.95 and profile['distinct_count'] > 10
        
        # Try to infer type and get type-specific stats
        profile = self._infer_column_type(non_null, distinct_values, profile)
        
        # DETECT FILTER CATEGORY
        profile = self._detect_filter_category(col, profile, distinct_values)
        
        return profile
    
    def _detect_filter_category(self, col_name: str, profile: Dict, distinct_values) -> Dict:
        """
        Detect if this column is a common filter dimension.
        
        Categories:
        - status: Employment status (active/terminated)
        - company: Company/entity code
        - organization: Org hierarchy (dept, division, cost center)
        - location: Work location/site
        - pay_type: Hourly/Salary, FLSA status
        - employee_type: Regular/Temp/Contractor
        - job: Job code/family/grade
        """
        col_lower = col_name.lower()
        distinct_count = profile.get('distinct_count', 0)
        inferred_type = profile.get('inferred_type', 'text')
        values_upper = set(str(v).upper() for v in distinct_values) if distinct_values is not None else set()
        
        # STATUS DETECTION
        # Pattern 1: termination_date column
        if 'termination' in col_lower and inferred_type == 'date':
            profile['filter_category'] = 'status'
            profile['filter_priority'] = 100  # Highest - almost always need to clarify
            return profile
        
        # Pattern 2: Status code columns
        if any(p in col_lower for p in ['employment_status', 'emp_status', 'employee_status', 'status_code', 'active_status']):
            if distinct_count <= 10:
                profile['filter_category'] = 'status'
                profile['filter_priority'] = 100
                return profile
        
        # Pattern 3: Values look like status codes
        status_indicators = {'A', 'T', 'I', 'L', 'ACTIVE', 'TERMINATED', 'INACTIVE', 'LEAVE', 'TERM'}
        if distinct_count <= 10 and len(values_upper & status_indicators) >= 2:
            profile['filter_category'] = 'status'
            profile['filter_priority'] = 90
            return profile
        
        # COMPANY DETECTION
        if any(p in col_lower for p in ['company_code', 'company_name', 'entity', 'legal_entity', 'home_company']):
            if 2 <= distinct_count <= 50:
                profile['filter_category'] = 'company'
                profile['filter_priority'] = 80
                return profile
        
        # ORGANIZATION DETECTION
        if any(p in col_lower for p in ['org_level', 'department', 'division', 'cost_center', 'business_unit', 
                                         'org_code', 'dept_code', 'segment']):
            if 2 <= distinct_count <= 200:
                profile['filter_category'] = 'organization'
                profile['filter_priority'] = 70
                return profile
        
        # LOCATION DETECTION
        if any(p in col_lower for p in ['location', 'site', 'work_location', 'work_state', 'work_country',
                                         'location_code', 'facility', 'branch', 'region']):
            if 2 <= distinct_count <= 500:
                profile['filter_category'] = 'location'
                profile['filter_priority'] = 60
                return profile
        
        # PAY TYPE DETECTION
        if any(p in col_lower for p in ['hourly_salary', 'pay_type', 'flsa', 'exempt', 'fullpart_time', 
                                         'full_part', 'ft_pt', 'salary_hourly']):
            if distinct_count <= 5:
                profile['filter_category'] = 'pay_type'
                profile['filter_priority'] = 50
                return profile
        
        # Check for H/S, F/P values
        pay_indicators = {'H', 'S', 'HOURLY', 'SALARY', 'F', 'P', 'FULL', 'PART', 'FT', 'PT',
                          'EXEMPT', 'NON-EXEMPT', 'NONEXEMPT', 'E', 'N'}
        if distinct_count <= 5 and len(values_upper & pay_indicators) >= 1:
            # Check column name hints too
            if any(p in col_lower for p in ['time', 'type', 'class', 'flsa']):
                profile['filter_category'] = 'pay_type'
                profile['filter_priority'] = 45
                return profile
        
        # EMPLOYEE TYPE DETECTION
        if any(p in col_lower for p in ['employee_type', 'worker_type', 'emp_type', 'employment_type',
                                         'worker_category', 'contingent']):
            if distinct_count <= 20:
                profile['filter_category'] = 'employee_type'
                profile['filter_priority'] = 55
                return profile
        
        # Check for REG/TMP/CON values
        emp_type_indicators = {'REG', 'REGULAR', 'TMP', 'TEMP', 'TEMPORARY', 'CON', 'CONTRACTOR', 
                               'CTR', 'INT', 'INTERN', 'CAS', 'CASUAL', 'FTE', 'PTE'}
        if distinct_count <= 15 and len(values_upper & emp_type_indicators) >= 1:
            profile['filter_category'] = 'employee_type'
            profile['filter_priority'] = 50
            return profile
        
        # JOB DETECTION
        if any(p in col_lower for p in ['job_code', 'job_title', 'job_family', 'job_grade', 'position_code',
                                         'occupation', 'job_class', 'pay_grade']):
            if 2 <= distinct_count <= 500:
                profile['filter_category'] = 'job'
                profile['filter_priority'] = 40
                return profile
        
        return profile
    
    def _infer_column_type(self, series: pd.Series, distinct_values, profile: Dict) -> Dict:
        """
        Infer the semantic type of a column and compute type-specific statistics.
        """
        # Try numeric first
        try:
            # Filter out obvious non-numeric
            numeric_series = pd.to_numeric(series.astype(str).str.replace(',', '').str.replace('$', '').str.strip(), errors='coerce')
            numeric_valid = numeric_series.dropna()
            
            if len(numeric_valid) >= len(series) * 0.8:  # 80% numeric
                profile['inferred_type'] = 'numeric'
                profile['min_value'] = float(numeric_valid.min())
                profile['max_value'] = float(numeric_valid.max())
                profile['mean_value'] = float(numeric_valid.mean())
                return profile
        except:
            pass
        
        # Try date
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                date_series = pd.to_datetime(series, errors='coerce')
            date_valid = date_series.dropna()
            
            if len(date_valid) >= len(series) * 0.8:  # 80% valid dates
                profile['inferred_type'] = 'date'
                profile['min_date'] = str(date_valid.min())
                profile['max_date'] = str(date_valid.max())
                return profile
        except:
            pass
        
        # Check for boolean-like
        str_values = set(str(v).upper().strip() for v in distinct_values)
        bool_patterns = [
            {'Y', 'N'}, {'YES', 'NO'}, {'TRUE', 'FALSE'}, {'1', '0'},
            {'T', 'F'}, {'ACTIVE', 'INACTIVE'}, {'Y', 'N', ''}
        ]
        
        str_values_cleaned = str_values - {''}
        for pattern in bool_patterns:
            if str_values == pattern or str_values_cleaned == pattern or str_values_cleaned == pattern - {''}:
                profile['inferred_type'] = 'boolean'
                profile['is_categorical'] = True
                profile['distinct_values'] = sorted([str(v) for v in distinct_values])
                profile['value_distribution'] = series.value_counts().to_dict()
                # Convert keys to strings
                profile['value_distribution'] = {str(k): int(v) for k, v in profile['value_distribution'].items()}
                return profile
        
        # Categorical: distinct count <= 100 and not high cardinality
        if profile['distinct_count'] <= 100:
            profile['inferred_type'] = 'categorical'
            profile['is_categorical'] = True
            profile['distinct_values'] = sorted([str(v) for v in distinct_values if str(v).strip()])
            
            # Get value distribution
            value_counts = series.value_counts()
            profile['value_distribution'] = {str(k): int(v) for k, v in value_counts.items()}
            return profile
        
        # Default to text
        profile['inferred_type'] = 'text'
        return profile
    
    def _store_column_profile(self, profile: Dict):
        """Store or update a column profile in the database."""
        try:
            # Delete existing profile for this column
            self.conn.execute("""
                DELETE FROM _column_profiles 
                WHERE project = ? AND table_name = ? AND column_name = ?
            """, [profile['project'], profile['table_name'], profile['column_name']])
            
            # Insert new profile
            self.conn.execute("""
                INSERT INTO _column_profiles (
                    id, project, table_name, column_name,
                    inferred_type, original_dtype,
                    total_count, null_count, distinct_count,
                    min_value, max_value, mean_value,
                    distinct_values, value_distribution,
                    min_date, max_date,
                    sample_values, is_likely_key, is_categorical,
                    filter_category, filter_priority
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                hash(f"{profile['project']}_{profile['table_name']}_{profile['column_name']}") % 2147483647,
                profile['project'],
                profile['table_name'],
                profile['column_name'],
                profile.get('inferred_type'),
                profile.get('original_dtype'),
                profile.get('total_count'),
                profile.get('null_count'),
                profile.get('distinct_count'),
                profile.get('min_value'),
                profile.get('max_value'),
                profile.get('mean_value'),
                json.dumps(profile.get('distinct_values')) if profile.get('distinct_values') else None,
                json.dumps(profile.get('value_distribution')) if profile.get('value_distribution') else None,
                profile.get('min_date'),
                profile.get('max_date'),
                json.dumps(profile.get('sample_values')) if profile.get('sample_values') else None,
                profile.get('is_likely_key', False),
                profile.get('is_categorical', False),
                profile.get('filter_category'),
                profile.get('filter_priority', 0)
            ])
            self.conn.commit()
            
        except Exception as e:
            logger.warning(f"[PROFILING] Failed to store profile for {profile.get('column_name')}: {e}")
    
    def get_column_profile(self, project: str, table_name: str = None, 
                           column_name: str = None) -> List[Dict]:
        """
        Retrieve column profiles from the database.
        
        Args:
            project: Project name
            table_name: Optional - filter by table
            column_name: Optional - filter by column
            
        Returns:
            List of profile dicts
        """
        try:
            query = "SELECT * FROM _column_profiles WHERE project = ?"
            params = [project]
            
            if table_name:
                query += " AND table_name = ?"
                params.append(table_name)
            
            if column_name:
                query += " AND column_name = ?"
                params.append(column_name)
            
            result = self.conn.execute(query, params).fetchall()
            columns = [desc[0] for desc in self.conn.execute(query, params).description]
            
            profiles = []
            for row in result:
                profile = dict(zip(columns, row))
                # Parse JSON fields
                for json_field in ['distinct_values', 'value_distribution', 'sample_values']:
                    if profile.get(json_field):
                        try:
                            profile[json_field] = json.loads(profile[json_field])
                        except:
                            pass
                profiles.append(profile)
            
            return profiles
            
        except Exception as e:
            logger.warning(f"[PROFILING] Failed to get profiles: {e}")
            return []
    
    def get_categorical_columns(self, project: str, table_name: str = None) -> List[Dict]:
        """
        Get all categorical columns with their distinct values.
        This is the key method for intelligent clarification.
        
        Returns columns where is_categorical = TRUE with their value distributions.
        """
        try:
            query = """
                SELECT table_name, column_name, distinct_count, 
                       distinct_values, value_distribution
                FROM _column_profiles 
                WHERE project = ? AND is_categorical = TRUE
            """
            params = [project]
            
            if table_name:
                query += " AND table_name = ?"
                params.append(table_name)
            
            query += " ORDER BY table_name, column_name"
            
            result = self.conn.execute(query, params).fetchall()
            
            categorical = []
            for row in result:
                table, col, distinct_count, distinct_values, distribution = row
                categorical.append({
                    'table_name': table,
                    'column_name': col,
                    'distinct_count': distinct_count,
                    'distinct_values': json.loads(distinct_values) if distinct_values else [],
                    'value_distribution': json.loads(distribution) if distribution else {}
                })
            
            return categorical
            
        except Exception as e:
            logger.warning(f"[PROFILING] Failed to get categorical columns: {e}")
            return []
    
    def get_filter_candidates(self, project: str) -> Dict[str, List[Dict]]:
        """
        Get all columns identified as filter candidates, grouped by category.
        
        Categories: status, company, organization, location, pay_type, employee_type, job
        
        Returns:
            Dict with category keys: {
                'status': [{'column': 'termination_date', 'table': '...', 'values': [...], ...}],
                'company': [...],
                ...
            }
        """
        try:
            result = self.conn.execute("""
                SELECT 
                    filter_category,
                    table_name,
                    column_name,
                    inferred_type,
                    distinct_count,
                    distinct_values,
                    value_distribution,
                    total_count,
                    null_count,
                    filter_priority
                FROM _column_profiles
                WHERE project = ? AND filter_category IS NOT NULL
                ORDER BY filter_priority DESC, filter_category
            """, [project]).fetchall()
            
            candidates = {}
            for row in result:
                category = row[0]
                if category not in candidates:
                    candidates[category] = []
                
                candidates[category].append({
                    'table': row[1],
                    'column': row[2],
                    'type': row[3],
                    'distinct_count': row[4],
                    'values': json.loads(row[5]) if row[5] else [],
                    'distribution': json.loads(row[6]) if row[6] else {},
                    'total_count': row[7],
                    'null_count': row[8],
                    'priority': row[9]
                })
            
            logger.warning(f"[PROFILING] Found filter candidates: {list(candidates.keys())}")
            return candidates
            
        except Exception as e:
            logger.warning(f"[PROFILING] Failed to get filter candidates: {e}")
            return {}
    
    def get_profile_summary(self, project: str) -> Dict[str, Any]:
        """
        Get a summary of all column profiles for a project.
        Useful for intelligence engine to understand the data landscape.
        """
        try:
            # Count by type
            type_counts = self.conn.execute("""
                SELECT inferred_type, COUNT(*) as cnt
                FROM _column_profiles
                WHERE project = ?
                GROUP BY inferred_type
            """, [project]).fetchall()
            
            # Get categorical columns summary
            categorical = self.get_categorical_columns(project)
            
            # Get tables profiled
            tables = self.conn.execute("""
                SELECT DISTINCT table_name, COUNT(*) as col_count
                FROM _column_profiles
                WHERE project = ?
                GROUP BY table_name
            """, [project]).fetchall()
            
            return {
                'project': project,
                'tables_profiled': len(tables),
                'total_columns': sum(t[1] for t in tables),
                'type_distribution': {t[0]: t[1] for t in type_counts},
                'categorical_columns': len(categorical),
                'categorical_summary': [
                    {
                        'table': c['table_name'],
                        'column': c['column_name'],
                        'values': c['distinct_values'][:10],  # First 10 values
                        'count': c['distinct_count']
                    }
                    for c in categorical[:20]  # First 20 categorical columns
                ],
                'tables': [{'name': t[0], 'columns': t[1]} for t in tables]
            }
            
        except Exception as e:
            logger.warning(f"[PROFILING] Failed to get summary: {e}")
            return {'project': project, 'error': str(e)}
    
    def backfill_profiles(self, project: str = None) -> Dict[str, Any]:
        """
        Backfill column profiles for existing tables.
        Run this after upgrading to add profiles to previously-uploaded data.
        
        Args:
            project: Optional project to limit backfill to
            
        Returns:
            Summary of tables profiled
        """
        logger.info(f"[PROFILING] Starting backfill{' for project ' + project if project else ''}")
        
        result = {
            'tables_profiled': 0,
            'columns_profiled': 0,
            'errors': []
        }
        
        try:
            # Get all tables from metadata
            if project:
                tables = self.conn.execute("""
                    SELECT DISTINCT project, table_name 
                    FROM _schema_metadata 
                    WHERE project = ? AND is_current = TRUE
                """, [project]).fetchall()
            else:
                tables = self.conn.execute("""
                    SELECT DISTINCT project, table_name 
                    FROM _schema_metadata 
                    WHERE is_current = TRUE
                """).fetchall()
            
            logger.info(f"[PROFILING] Found {len(tables)} tables to profile")
            
            for proj, table_name in tables:
                try:
                    profile_result = self.profile_columns(proj, table_name)
                    result['tables_profiled'] += 1
                    result['columns_profiled'] += profile_result.get('columns_profiled', 0)
                    logger.info(f"[PROFILING] Backfilled {table_name}: {profile_result.get('columns_profiled', 0)} columns")
                except Exception as e:
                    error_msg = f"{table_name}: {str(e)}"
                    result['errors'].append(error_msg)
                    logger.warning(f"[PROFILING] Failed to profile {table_name}: {e}")
            
            logger.info(f"[PROFILING] Backfill complete: {result['tables_profiled']} tables, {result['columns_profiled']} columns")
            
        except Exception as e:
            logger.error(f"[PROFILING] Backfill failed: {e}")
            result['error'] = str(e)
        
        return result

    def get_schema_for_project(self, project: str) -> Dict[str, Any]:
        """Get all table schemas for a project (for Claude to use)"""
        try:
            result = self.conn.execute("""
                SELECT file_name, sheet_name, table_name, columns, row_count, likely_keys
                FROM _schema_metadata
                WHERE project = ? AND is_current = TRUE
                ORDER BY file_name, sheet_name
            """, [project]).fetchall()
        except Exception as e:
            # Handle case where is_current column doesn't exist (old schema)
            logger.warning(f"Schema query failed, trying without is_current: {e}")
            result = self.conn.execute("""
                SELECT file_name, sheet_name, table_name, columns, row_count, likely_keys
                FROM _schema_metadata
                WHERE project = ?
                ORDER BY file_name, sheet_name
            """, [project]).fetchall()
        
        schema = {
            'project': project,
            'tables': []
        }
        
        # Get all column profiles for this project (for efficiency)
        all_profiles = {}
        try:
            profiles_list = self.get_column_profile(project)
            for p in profiles_list:
                key = (p['table_name'], p['column_name'])
                all_profiles[key] = p
        except:
            pass
        
        # Get categorical columns summary
        categorical_summary = {}
        try:
            categorical = self.get_categorical_columns(project)
            for c in categorical:
                if c['table_name'] not in categorical_summary:
                    categorical_summary[c['table_name']] = []
                categorical_summary[c['table_name']].append({
                    'column': c['column_name'],
                    'values': c['distinct_values'],
                    'distribution': c['value_distribution']
                })
        except:
            pass
        
        for row in result:
            file_name, sheet_name, table_name, columns, row_count, likely_keys = row
            columns_list = json.loads(columns) if columns else []
            
            # Enhance column info with profile data
            enhanced_columns = []
            for col_info in columns_list:
                col_name = col_info.get('name', col_info) if isinstance(col_info, dict) else col_info
                profile_key = (table_name, col_name)
                
                if profile_key in all_profiles:
                    p = all_profiles[profile_key]
                    enhanced_col = {
                        'name': col_name,
                        'type': col_info.get('type', 'VARCHAR') if isinstance(col_info, dict) else 'VARCHAR',
                        'inferred_type': p.get('inferred_type'),
                        'distinct_count': p.get('distinct_count'),
                        'null_count': p.get('null_count'),
                        'is_categorical': p.get('is_categorical', False),
                        'is_likely_key': p.get('is_likely_key', False)
                    }
                    
                    # Add type-specific info
                    if p.get('inferred_type') == 'categorical':
                        enhanced_col['distinct_values'] = p.get('distinct_values', [])
                        enhanced_col['value_distribution'] = p.get('value_distribution', {})
                    elif p.get('inferred_type') == 'numeric':
                        enhanced_col['min_value'] = p.get('min_value')
                        enhanced_col['max_value'] = p.get('max_value')
                        enhanced_col['mean_value'] = p.get('mean_value')
                    elif p.get('inferred_type') == 'date':
                        enhanced_col['min_date'] = p.get('min_date')
                        enhanced_col['max_date'] = p.get('max_date')
                    
                    enhanced_columns.append(enhanced_col)
                else:
                    # No profile, use basic info
                    enhanced_columns.append(col_info if isinstance(col_info, dict) else {'name': col_info})
            
            table_info = {
                'file': file_name,
                'sheet': sheet_name,
                'table_name': table_name,
                'columns': enhanced_columns,
                'row_count': row_count,
                'likely_keys': json.loads(likely_keys) if likely_keys else []
            }
            
            # Add categorical columns summary for this table
            if table_name in categorical_summary:
                table_info['categorical_columns'] = categorical_summary[table_name]
            
            schema['tables'].append(table_info)
        
        # Add overall profile summary
        try:
            schema['profile_summary'] = self.get_profile_summary(project)
        except:
            pass
        
        return schema
    
    def execute_query(self, sql: str) -> Tuple[List[Dict], List[str]]:
        """
        Execute SQL query and return results.
        Returns (rows as dicts, column names)
        """
        try:
            result = self.conn.execute(sql)
            columns = [desc[0] for desc in result.description]
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            return rows, columns
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise
    
    def query_to_dataframe(self, sql: str) -> pd.DataFrame:
        """Execute query and return as DataFrame (for Excel export)"""
        return self.conn.execute(sql).fetchdf()
    
    def export_to_excel(self, sql: str, output_path: str) -> str:
        """Execute query and export results to Excel"""
        df = self.query_to_dataframe(sql)
        df.to_excel(output_path, index=False)
        return output_path
    
    def export_to_csv(self, sql: str, output_path: str) -> str:
        """Execute query and export results to CSV"""
        df = self.query_to_dataframe(sql)
        df.to_csv(output_path, index=False)
        return output_path
    
    def delete_project_data(self, project: str) -> int:
        """Delete all tables for a project"""
        # Get table names
        tables = self.conn.execute("""
            SELECT table_name FROM _schema_metadata WHERE project = ?
        """, [project]).fetchall()
        
        count = 0
        for (table_name,) in tables:
            try:
                self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                count += 1
            except Exception as e:
                logger.warning(f"Could not drop table {table_name}: {e}")
        
        # Remove metadata
        self.conn.execute("DELETE FROM _schema_metadata WHERE project = ?", [project])
        self.conn.commit()
        
        logger.info(f"Deleted {count} tables for project '{project}'")
        return count
    
    def get_table_sample(self, table_name: str, limit: int = 5, decrypt: bool = True) -> List[Dict]:
        """Get sample rows from a table"""
        try:
            rows, cols = self.execute_query(f"SELECT * FROM {table_name} LIMIT {limit}")
            
            # Decrypt if needed
            if decrypt and rows:
                df = pd.DataFrame(rows)
                df = self.encryptor.decrypt_dataframe(df)
                rows = df.to_dict('records')
            
            return rows
        except:
            return []
    
    def _archive_previous_version(self, project: str, file_name: str, version: int):
        """Archive tables from previous version"""
        tables = self.conn.execute("""
            SELECT table_name, sheet_name FROM _schema_metadata 
            WHERE project = ? AND file_name = ? AND version = ?
        """, [project, file_name, version]).fetchall()
        
        for table_name, sheet_name in tables:
            archive_name = f"{table_name}_v{version}"
            try:
                # Rename table to archive name
                self.conn.execute(f"ALTER TABLE {table_name} RENAME TO {archive_name}")
                logger.info(f"Archived {table_name} → {archive_name}")
            except Exception as e:
                logger.warning(f"Could not archive {table_name}: {e}")
    
    def delete_file(self, project: str, file_name: str, delete_all_versions: bool = True) -> Dict[str, Any]:
        """
        Delete all data for a specific file from a project.
        
        Args:
            project: Project name
            file_name: Name of file to delete
            delete_all_versions: If True, delete archived versions too
            
        Returns:
            Summary of deleted tables
        """
        result = {
            'project': project,
            'file_name': file_name,
            'tables_deleted': [],
            'versions_deleted': []
        }
        
        # Get all tables for this file
        if delete_all_versions:
            tables = self.conn.execute("""
                SELECT table_name, version FROM _schema_metadata 
                WHERE project = ? AND file_name = ?
            """, [project, file_name]).fetchall()
        else:
            tables = self.conn.execute("""
                SELECT table_name, version FROM _schema_metadata 
                WHERE project = ? AND file_name = ? AND is_current = TRUE
            """, [project, file_name]).fetchall()
        
        versions_deleted = set()
        
        for table_name, version in tables:
            try:
                self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                result['tables_deleted'].append(table_name)
                versions_deleted.add(version)
                logger.info(f"Deleted table: {table_name}")
            except Exception as e:
                logger.warning(f"Could not delete table {table_name}: {e}")
        
        # Also try to drop archived tables (naming convention: tablename_v1, _v2, etc.)
        if delete_all_versions:
            for table_name, version in tables:
                for v in range(1, 100):  # Check up to 100 versions
                    archive_name = f"{table_name}_v{v}"
                    try:
                        self.conn.execute(f"DROP TABLE IF EXISTS {archive_name}")
                    except:
                        break
        
        # Delete metadata
        if delete_all_versions:
            self.conn.execute("""
                DELETE FROM _schema_metadata WHERE project = ? AND file_name = ?
            """, [project, file_name])
            self.conn.execute("""
                DELETE FROM _load_versions WHERE project = ? AND file_name = ?
            """, [project, file_name])
        else:
            self.conn.execute("""
                DELETE FROM _schema_metadata WHERE project = ? AND file_name = ? AND is_current = TRUE
            """, [project, file_name])
        
        # ALSO handle PDF-derived tables
        try:
            # Check if _pdf_tables exists
            pdf_table_exists = self.conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = '_pdf_tables'
            """).fetchone()[0] > 0
            
            logger.warning(f"[DELETE] PDF tables exist: {pdf_table_exists}, looking for project={project}, file={file_name}")
            
            if pdf_table_exists:
                # First, see ALL entries in _pdf_tables for debugging
                all_pdf = self.conn.execute("""
                    SELECT table_name, source_file, project, project_id FROM _pdf_tables
                """).fetchall()
                logger.warning(f"[DELETE] All PDF entries: {all_pdf}")
                
                # Find PDF tables matching this file
                pdf_tables = self.conn.execute("""
                    SELECT table_name, source_file FROM _pdf_tables 
                    WHERE (project = ? OR project_id = ?) 
                    AND (source_file = ? OR source_file LIKE ?)
                """, [project, project, file_name, f"%{file_name}%"]).fetchall()
                
                logger.warning(f"[DELETE] Matched PDF tables: {pdf_tables}")
                
                for row in pdf_tables:
                    table_name = row[0]
                    try:
                        self.conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
                        result['tables_deleted'].append(table_name)
                        logger.info(f"Deleted PDF table: {table_name}")
                    except Exception as e:
                        logger.warning(f"Could not delete PDF table {table_name}: {e}")
                
                # Delete from _pdf_tables metadata
                deleted = self.conn.execute("""
                    DELETE FROM _pdf_tables 
                    WHERE (project = ? OR project_id = ?) 
                    AND (source_file = ? OR source_file LIKE ?)
                """, [project, project, file_name, f"%{file_name}%"])
                
                logger.warning(f"[DELETE] Deleted {deleted.rowcount if hasattr(deleted, 'rowcount') else 'unknown'} rows from _pdf_tables")
                
                logger.info(f"Cleaned up PDF metadata for {file_name}")
        except Exception as pdf_e:
            logger.warning(f"Error cleaning up PDF tables: {pdf_e}")
            import traceback
            logger.warning(traceback.format_exc())
        
        self.conn.commit()
        
        result['versions_deleted'] = list(versions_deleted)
        logger.info(f"Deleted {len(result['tables_deleted'])} tables for {file_name}")
        
        return result
    
    def compare_versions(
        self, 
        project: str, 
        file_name: str, 
        sheet_name: str,
        key_column: str,
        version1: int = None,
        version2: int = None
    ) -> Dict[str, Any]:
        """
        Compare two versions of a file to find changes.
        
        Args:
            project: Project name
            file_name: File name
            sheet_name: Sheet to compare
            key_column: Column to use as unique key (e.g., 'employee_id')
            version1: First version (default: previous version)
            version2: Second version (default: current version)
            
        Returns:
            Dict with added, removed, and changed records
        """
        # Get current and previous version numbers
        versions = self.conn.execute("""
            SELECT DISTINCT version FROM _schema_metadata 
            WHERE project = ? AND file_name = ? AND sheet_name = ?
            ORDER BY version DESC
        """, [project, file_name, sheet_name]).fetchall()
        
        if len(versions) < 2:
            return {
                'error': 'Need at least 2 versions to compare',
                'available_versions': [v[0] for v in versions]
            }
        
        v2 = version2 or versions[0][0]  # Latest
        v1 = version1 or versions[1][0]  # Previous
        
        # Get table names
        table1_result = self.conn.execute("""
            SELECT table_name FROM _schema_metadata 
            WHERE project = ? AND file_name = ? AND sheet_name = ? AND version = ?
        """, [project, file_name, sheet_name, v1]).fetchone()
        
        table2_result = self.conn.execute("""
            SELECT table_name FROM _schema_metadata 
            WHERE project = ? AND file_name = ? AND sheet_name = ? AND version = ?
        """, [project, file_name, sheet_name, v2]).fetchone()
        
        if not table1_result or not table2_result:
            # Try archived table names
            base_table = self._generate_table_name(project, file_name, sheet_name)
            table1 = f"{base_table}_v{v1}"
            table2 = base_table  # Current is without version suffix
        else:
            table1 = table1_result[0] if v1 != versions[0][0] else f"{table1_result[0]}_v{v1}"
            table2 = table2_result[0]
        
        result = {
            'project': project,
            'file_name': file_name,
            'sheet_name': sheet_name,
            'version1': v1,
            'version2': v2,
            'key_column': key_column,
            'added': [],
            'removed': [],
            'changed': [],
            'unchanged_count': 0
        }
        
        try:
            # Get data from both versions
            df1 = self.query_to_dataframe(f"SELECT * FROM {table1}")
            df2 = self.query_to_dataframe(f"SELECT * FROM {table2}")
            
            # Decrypt for comparison
            df1 = self.encryptor.decrypt_dataframe(df1)
            df2 = self.encryptor.decrypt_dataframe(df2)
            
            # Ensure key column exists
            if key_column not in df1.columns or key_column not in df2.columns:
                return {'error': f"Key column '{key_column}' not found in both versions"}
            
            # Set key as index
            df1 = df1.set_index(key_column)
            df2 = df2.set_index(key_column)
            
            # Find added (in v2 but not v1)
            added_keys = set(df2.index) - set(df1.index)
            result['added'] = df2.loc[list(added_keys)].reset_index().to_dict('records')
            
            # Find removed (in v1 but not v2)
            removed_keys = set(df1.index) - set(df2.index)
            result['removed'] = df1.loc[list(removed_keys)].reset_index().to_dict('records')
            
            # Find changed (in both but different)
            common_keys = set(df1.index) & set(df2.index)
            changed = []
            unchanged = 0
            
            for key in common_keys:
                row1 = df1.loc[key]
                row2 = df2.loc[key]
                
                # Compare each column
                differences = {}
                for col in df1.columns:
                    if col in df2.columns:
                        val1 = row1[col] if not pd.isna(row1[col]) else None
                        val2 = row2[col] if not pd.isna(row2[col]) else None
                        
                        if str(val1) != str(val2):
                            differences[col] = {'old': val1, 'new': val2}
                
                if differences:
                    changed.append({
                        key_column: key,
                        'changes': differences
                    })
                else:
                    unchanged += 1
            
            result['changed'] = changed
            result['unchanged_count'] = unchanged
            
            # Summary
            result['summary'] = {
                'total_v1': len(df1),
                'total_v2': len(df2),
                'added_count': len(result['added']),
                'removed_count': len(result['removed']),
                'changed_count': len(result['changed']),
                'unchanged_count': unchanged
            }
            
            logger.info(f"Compared {file_name}/{sheet_name}: +{len(result['added'])} -{len(result['removed'])} ~{len(result['changed'])}")
            
        except Exception as e:
            logger.error(f"Comparison error: {e}")
            result['error'] = str(e)
        
        return result
    
    def get_file_versions(self, project: str, file_name: str) -> List[Dict]:
        """Get all versions of a file"""
        versions = self.conn.execute("""
            SELECT DISTINCT version, created_at, row_count
            FROM _schema_metadata 
            WHERE project = ? AND file_name = ?
            ORDER BY version DESC
        """, [project, file_name]).fetchall()
        
        return [
            {'version': v[0], 'created_at': v[1], 'row_count': v[2]}
            for v in versions
        ]
    
    def list_files(self, project: str) -> List[Dict]:
        """List all files in a project with version info"""
        files = self.conn.execute("""
            SELECT DISTINCT file_name, 
                   MAX(version) as latest_version,
                   SUM(row_count) as total_rows,
                   MAX(created_at) as last_updated
            FROM _schema_metadata 
            WHERE project = ? AND is_current = TRUE
            GROUP BY file_name
            ORDER BY file_name
        """, [project]).fetchall()
        
        return [
            {
                'file_name': f[0],
                'latest_version': f[1],
                'total_rows': f[2],
                'last_updated': f[3]
            }
            for f in files
        ]
    
    def reset_database(self) -> Dict[str, Any]:
        """
        Completely reset the database - drop all tables and recreate metadata.
        USE WITH CAUTION - this deletes all data!
        """
        result = {
            'tables_dropped': [],
            'success': False
        }
        
        try:
            # Get all user tables (not metadata)
            tables = self.conn.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'main' 
                AND table_name NOT LIKE '\\_%' ESCAPE '\\'
            """).fetchall()
            
            for (table_name,) in tables:
                try:
                    self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
                    result['tables_dropped'].append(table_name)
                except Exception as e:
                    logger.warning(f"Could not drop {table_name}: {e}")
            
            # Drop metadata tables
            self.conn.execute("DROP TABLE IF EXISTS _schema_metadata")
            self.conn.execute("DROP TABLE IF EXISTS _load_versions")
            self.conn.execute("DROP SEQUENCE IF EXISTS schema_metadata_seq")
            self.conn.execute("DROP SEQUENCE IF EXISTS load_versions_seq")
            self.conn.commit()
            
            # Recreate metadata tables
            self._init_metadata_table()
            
            result['success'] = True
            logger.info(f"Database reset: dropped {len(result['tables_dropped'])} tables")
            
        except Exception as e:
            logger.error(f"Database reset failed: {e}")
            result['error'] = str(e)
        
        return result
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# Singleton instance
_handler: Optional[StructuredDataHandler] = None

def get_structured_handler() -> StructuredDataHandler:
    """Get or create singleton handler"""
    global _handler
    if _handler is None:
        _handler = StructuredDataHandler()
    return _handler


def reset_structured_handler():
    """Reset the singleton handler (forces reconnection)"""
    global _handler
    if _handler:
        _handler.close()
    _handler = None
