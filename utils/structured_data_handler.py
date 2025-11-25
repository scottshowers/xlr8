"""
Structured Data Handler - DuckDB Storage for Excel/CSV
=======================================================

Stores tabular data in DuckDB for fast SQL queries.
Each project gets isolated tables. Cross-sheet joins supported.

SECURITY FEATURES:
- Field-level encryption for PII (SSN, DOB, etc.)
- Encryption at rest using Fernet (AES-128)

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
    from cryptography.fernet import Fernet
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False
    logging.warning("cryptography not installed - PII encryption disabled. Run: pip install cryptography")

logger = logging.getLogger(__name__)

# DuckDB storage location
DUCKDB_PATH = "/data/structured_data.duckdb"
ENCRYPTION_KEY_PATH = "/data/.encryption_key"

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


class FieldEncryptor:
    """Handles field-level encryption for PII data"""
    
    def __init__(self, key_path: str = ENCRYPTION_KEY_PATH):
        self.key_path = key_path
        self.fernet = None
        
        if ENCRYPTION_AVAILABLE:
            self._init_encryption()
    
    def _init_encryption(self):
        """Initialize or load encryption key"""
        try:
            if os.path.exists(self.key_path):
                with open(self.key_path, 'rb') as f:
                    key = f.read()
            else:
                # Generate new key
                key = Fernet.generate_key()
                os.makedirs(os.path.dirname(self.key_path), exist_ok=True)
                with open(self.key_path, 'wb') as f:
                    f.write(key)
                os.chmod(self.key_path, 0o600)  # Restrict permissions
                logger.info("Generated new encryption key")
            
            self.fernet = Fernet(key)
            logger.info("Encryption initialized successfully")
        except Exception as e:
            logger.error(f"Encryption initialization failed: {e}")
            self.fernet = None
    
    def is_pii_column(self, column_name: str) -> bool:
        """Check if column likely contains PII"""
        col_lower = column_name.lower()
        for pattern in PII_PATTERNS:
            if re.search(pattern, col_lower):
                return True
        return False
    
    def encrypt(self, value: Any) -> str:
        """Encrypt a value"""
        if not self.fernet or value is None or pd.isna(value):
            return value
        
        try:
            # Convert to string and encrypt
            val_str = str(value)
            encrypted = self.fernet.encrypt(val_str.encode())
            # Prefix with 'ENC:' to identify encrypted values
            return f"ENC:{encrypted.decode()}"
        except Exception as e:
            logger.warning(f"Encryption failed for value: {e}")
            return value
    
    def decrypt(self, value: Any) -> str:
        """Decrypt a value"""
        if not self.fernet or value is None or pd.isna(value):
            return value
        
        try:
            val_str = str(value)
            if not val_str.startswith("ENC:"):
                return value
            
            encrypted_data = val_str[4:].encode()
            decrypted = self.fernet.decrypt(encrypted_data)
            return decrypted.decode()
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
                logger.info(f"Encrypted PII column: {col}")
        
        return df, encrypted_cols
    
    def decrypt_dataframe(self, df: pd.DataFrame, encrypted_cols: List[str] = None) -> pd.DataFrame:
        """Decrypt PII columns in a DataFrame"""
        df = df.copy()
        
        # If no encrypted_cols specified, check all columns for ENC: prefix
        if encrypted_cols is None:
            encrypted_cols = []
            for col in df.columns:
                if df[col].dtype == object:
                    sample = df[col].dropna().head(1)
                    if len(sample) > 0 and str(sample.iloc[0]).startswith("ENC:"):
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
        logger.info(f"StructuredDataHandler initialized with {db_path}")
    
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
        encrypt_pii: bool = True,
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
            
            # If keeping previous version, rename old tables
            if keep_previous_version and version > 1:
                self._archive_previous_version(project, file_name, version - 1)
            
            # Read all sheets
            excel_file = pd.ExcelFile(file_path)
            
            all_encrypted_cols = []
            
            for sheet_name in excel_file.sheet_names:
                try:
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
                                    
                                    for col_idx in range(1, min(20, ws.max_column + 1)):
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
                    
                    results['sheets'].append(sheet_info)
                    results['total_rows'] += len(df)
                    results['tables_created'].append(table_name)
                    
                    logger.info(f"Created table '{table_name}' with {len(df)} rows, {len(df.columns)} columns")
                    
                except Exception as e:
                    logger.error(f"Error processing sheet '{sheet_name}': {e}")
                    continue
            
            self.conn.commit()
            logger.info(f"Stored {len(results['tables_created'])} tables from {file_name}")
            
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
            
            return {
                'project': project,
                'file_name': file_name,
                'table_name': table_name,
                'columns': list(df.columns),
                'row_count': len(df),
                'likely_keys': likely_keys
            }
            
        except Exception as e:
            logger.error(f"Error storing CSV: {e}")
            raise
    
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
        
        for row in result:
            file_name, sheet_name, table_name, columns, row_count, likely_keys = row
            schema['tables'].append({
                'file': file_name,
                'sheet': sheet_name,
                'table_name': table_name,
                'columns': json.loads(columns) if columns else [],
                'row_count': row_count,
                'likely_keys': json.loads(likely_keys) if likely_keys else []
            })
        
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
