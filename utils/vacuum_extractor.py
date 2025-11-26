"""
Vacuum Extractor - Extract EVERYTHING from files
=================================================

Philosophy: Parse now, understand later, learn forever.

This is a SEPARATE feature from normal uploads. Used for:
- Complex PDFs from various payroll vendors
- Files with multiple tables per page
- Files where structure is unknown

Extracts ALL tables and data without interpretation.
Users explore and map columns later.

Author: XLR8 Team
"""

import os
import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import hashlib

# PDF extraction
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

# Excel extraction
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# OCR for scanned PDFs
try:
    import pytesseract
    from pdf2image import convert_from_path
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# DuckDB for storage
try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False

logger = logging.getLogger(__name__)

# Database path
VACUUM_DB_PATH = "/data/vacuum_extracts.duckdb"


class VacuumExtractor:
    """
    Extracts EVERYTHING from files without interpretation.
    
    Supported formats:
    - PDF (native tables via pdfplumber)
    - PDF (scanned via OCR - if available)
    - Excel (.xlsx, .xls)
    - CSV
    
    All data stored in raw form for later exploration and mapping.
    """
    
    def __init__(self, db_path: str = VACUUM_DB_PATH):
        """Initialize vacuum extractor with DuckDB storage"""
        if not DUCKDB_AVAILABLE:
            raise ImportError("DuckDB required for vacuum extractor")
        
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        self._init_tables()
        logger.info(f"VacuumExtractor initialized with {db_path}")
    
    def _init_tables(self):
        """Create database tables for raw extracts and mappings"""
        
        # Raw extracts - everything we find
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS extract_seq START 1
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS raw_extracts (
                id INTEGER DEFAULT nextval('extract_seq'),
                source_file VARCHAR NOT NULL,
                project VARCHAR,
                file_type VARCHAR,
                page_num INTEGER,
                table_index INTEGER,
                raw_headers JSON,
                raw_data JSON,
                row_count INTEGER,
                column_count INTEGER,
                extraction_method VARCHAR,
                confidence FLOAT,
                extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status VARCHAR DEFAULT 'raw',
                mapped_to VARCHAR,
                notes VARCHAR
            )
        """)
        
        # Column mappings - learned over time
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS mapping_seq START 1
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS column_mappings (
                id INTEGER DEFAULT nextval('mapping_seq'),
                source_pattern VARCHAR NOT NULL,
                target_field VARCHAR NOT NULL,
                confidence FLOAT DEFAULT 1.0,
                times_used INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Vendor templates - for auto-detection
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS template_seq START 1
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS vendor_templates (
                id INTEGER DEFAULT nextval('template_seq'),
                vendor_name VARCHAR,
                report_type VARCHAR,
                header_signature JSON,
                column_map JSON,
                times_matched INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_matched TIMESTAMP
            )
        """)
        
        self.conn.commit()
        logger.info("Vacuum database tables initialized")
    
    def vacuum_file(self, file_path: str, project: str = None) -> Dict[str, Any]:
        """
        Main entry point - extract EVERYTHING from a file.
        
        Returns summary of what was found.
        """
        file_name = os.path.basename(file_path)
        file_ext = file_name.split('.')[-1].lower()
        
        result = {
            'source_file': file_name,
            'project': project,
            'file_type': file_ext,
            'tables_found': 0,
            'total_rows': 0,
            'extracts': [],
            'errors': []
        }
        
        try:
            if file_ext == 'pdf':
                extracts = self._vacuum_pdf(file_path, file_name, project)
            elif file_ext in ['xlsx', 'xls']:
                extracts = self._vacuum_excel(file_path, file_name, project)
            elif file_ext == 'csv':
                extracts = self._vacuum_csv(file_path, file_name, project)
            else:
                result['errors'].append(f"Unsupported file type: {file_ext}")
                return result
            
            result['extracts'] = extracts
            result['tables_found'] = len(extracts)
            result['total_rows'] = sum(e.get('row_count', 0) for e in extracts)
            
            logger.info(f"Vacuumed {file_name}: {result['tables_found']} tables, {result['total_rows']} rows")
            
        except Exception as e:
            logger.error(f"Vacuum extraction error: {e}", exc_info=True)
            result['errors'].append(str(e))
        
        return result
    
    def _vacuum_pdf(self, file_path: str, file_name: str, project: str) -> List[Dict]:
        """Extract all tables from PDF"""
        if not PDFPLUMBER_AVAILABLE:
            raise ImportError("pdfplumber required for PDF extraction")
        
        extracts = []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    # Extract all tables on this page
                    tables = page.extract_tables()
                    
                    for table_idx, table in enumerate(tables):
                        if not table or len(table) < 2:
                            continue
                        
                        # First row as headers (might be wrong - user can fix)
                        headers = [str(h) if h else f'col_{i}' for i, h in enumerate(table[0])]
                        data = table[1:]
                        
                        # Clean up data
                        cleaned_data = []
                        for row in data:
                            cleaned_row = [str(cell) if cell else '' for cell in row]
                            # Skip completely empty rows
                            if any(cell.strip() for cell in cleaned_row):
                                cleaned_data.append(cleaned_row)
                        
                        if not cleaned_data:
                            continue
                        
                        # Calculate confidence based on header quality
                        confidence = self._calculate_confidence(headers, cleaned_data)
                        
                        # Store in database
                        extract_id = self._store_extract(
                            source_file=file_name,
                            project=project,
                            file_type='pdf',
                            page_num=page_num,
                            table_index=table_idx,
                            headers=headers,
                            data=cleaned_data,
                            method='pdfplumber',
                            confidence=confidence
                        )
                        
                        extracts.append({
                            'id': extract_id,
                            'page': page_num,
                            'table_index': table_idx,
                            'headers': headers,
                            'row_count': len(cleaned_data),
                            'column_count': len(headers),
                            'confidence': confidence,
                            'preview': cleaned_data[:3]
                        })
                        
                except Exception as e:
                    logger.warning(f"Error extracting page {page_num}: {e}")
                    continue
        
        # Try to detect and merge multi-page tables
        extracts = self._merge_continuation_tables(extracts)
        
        return extracts
    
    def _vacuum_excel(self, file_path: str, file_name: str, project: str) -> List[Dict]:
        """Extract all sheets from Excel"""
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas required for Excel extraction")
        
        extracts = []
        
        excel_file = pd.ExcelFile(file_path)
        
        for sheet_idx, sheet_name in enumerate(excel_file.sheet_names):
            try:
                # Try different header rows
                best_df = None
                best_header_row = 0
                min_unnamed = float('inf')
                
                for header_row in range(10):
                    try:
                        df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row, nrows=100)
                        unnamed = sum(1 for c in df.columns if str(c).startswith('Unnamed'))
                        if unnamed < min_unnamed and len(df.columns) >= 2:
                            min_unnamed = unnamed
                            best_df = df
                            best_header_row = header_row
                            if unnamed == 0:
                                break
                    except:
                        continue
                
                if best_df is None:
                    continue
                
                # Read full data with best header row
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=best_header_row)
                df = df.dropna(how='all').dropna(axis=1, how='all')
                
                if df.empty:
                    continue
                
                headers = [str(c) for c in df.columns]
                
                # Convert to list of lists
                data = df.fillna('').astype(str).values.tolist()
                
                confidence = self._calculate_confidence(headers, data)
                
                extract_id = self._store_extract(
                    source_file=file_name,
                    project=project,
                    file_type='excel',
                    page_num=sheet_idx,
                    table_index=0,
                    headers=headers,
                    data=data,
                    method='pandas',
                    confidence=confidence,
                    notes=f"Sheet: {sheet_name}, Header row: {best_header_row}"
                )
                
                extracts.append({
                    'id': extract_id,
                    'page': sheet_idx,
                    'sheet_name': sheet_name,
                    'table_index': 0,
                    'headers': headers,
                    'row_count': len(data),
                    'column_count': len(headers),
                    'confidence': confidence,
                    'preview': data[:3]
                })
                
            except Exception as e:
                logger.warning(f"Error extracting sheet {sheet_name}: {e}")
                continue
        
        return extracts
    
    def _vacuum_csv(self, file_path: str, file_name: str, project: str) -> List[Dict]:
        """Extract data from CSV"""
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas required for CSV extraction")
        
        extracts = []
        
        try:
            df = pd.read_csv(file_path)
            df = df.dropna(how='all').dropna(axis=1, how='all')
            
            if df.empty:
                return extracts
            
            headers = [str(c) for c in df.columns]
            data = df.fillna('').astype(str).values.tolist()
            
            confidence = self._calculate_confidence(headers, data)
            
            extract_id = self._store_extract(
                source_file=file_name,
                project=project,
                file_type='csv',
                page_num=0,
                table_index=0,
                headers=headers,
                data=data,
                method='pandas',
                confidence=confidence
            )
            
            extracts.append({
                'id': extract_id,
                'page': 0,
                'table_index': 0,
                'headers': headers,
                'row_count': len(data),
                'column_count': len(headers),
                'confidence': confidence,
                'preview': data[:3]
            })
            
        except Exception as e:
            logger.error(f"CSV extraction error: {e}")
        
        return extracts
    
    def _calculate_confidence(self, headers: List[str], data: List[List]) -> float:
        """Calculate confidence score based on header quality"""
        score = 1.0
        
        # Penalize unnamed columns
        unnamed = sum(1 for h in headers if 'unnamed' in h.lower() or h.startswith('col_'))
        score -= (unnamed / len(headers)) * 0.3
        
        # Penalize very short headers
        short = sum(1 for h in headers if len(h) < 2)
        score -= (short / len(headers)) * 0.2
        
        # Penalize if headers look like data (all numeric)
        numeric = sum(1 for h in headers if h.replace('.', '').replace('-', '').isdigit())
        score -= (numeric / len(headers)) * 0.3
        
        # Bonus for recognizable HR/payroll terms
        hr_terms = ['employee', 'emp', 'name', 'id', 'date', 'amount', 'hours', 'rate', 'dept', 'code']
        matches = sum(1 for h in headers if any(term in h.lower() for term in hr_terms))
        score += (matches / len(headers)) * 0.2
        
        return max(0.0, min(1.0, score))
    
    def _merge_continuation_tables(self, extracts: List[Dict]) -> List[Dict]:
        """Detect and flag tables that continue across pages"""
        if len(extracts) < 2:
            return extracts
        
        # Group by similar headers
        for i in range(len(extracts) - 1):
            current = extracts[i]
            next_table = extracts[i + 1]
            
            # Check if headers match (likely continuation)
            if current['headers'] == next_table['headers']:
                if next_table['page'] == current['page'] + 1:
                    # Mark as continuation
                    if 'continuation_of' not in next_table:
                        next_table['continuation_of'] = current['id']
                        current['continues_to'] = next_table['id']
        
        return extracts
    
    def _store_extract(
        self,
        source_file: str,
        project: str,
        file_type: str,
        page_num: int,
        table_index: int,
        headers: List[str],
        data: List[List],
        method: str,
        confidence: float,
        notes: str = None
    ) -> int:
        """Store extracted data in database"""
        
        self.conn.execute("""
            INSERT INTO raw_extracts 
            (source_file, project, file_type, page_num, table_index, 
             raw_headers, raw_data, row_count, column_count, 
             extraction_method, confidence, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            source_file, project, file_type, page_num, table_index,
            json.dumps(headers), json.dumps(data), len(data), len(headers),
            method, confidence, notes
        ])
        
        self.conn.commit()
        
        # Get the ID of inserted row
        result = self.conn.execute("""
            SELECT MAX(id) FROM raw_extracts WHERE source_file = ?
        """, [source_file]).fetchone()
        
        return result[0] if result else 0
    
    def get_extracts(self, project: str = None, source_file: str = None) -> List[Dict]:
        """Get all extracts, optionally filtered"""
        query = "SELECT * FROM raw_extracts WHERE 1=1"
        params = []
        
        if project:
            query += " AND project = ?"
            params.append(project)
        
        if source_file:
            query += " AND source_file = ?"
            params.append(source_file)
        
        query += " ORDER BY source_file, page_num, table_index"
        
        result = self.conn.execute(query, params).fetchall()
        columns = [desc[0] for desc in self.conn.description]
        
        extracts = []
        for row in result:
            extract = dict(zip(columns, row))
            # Parse JSON fields
            if extract.get('raw_headers'):
                extract['raw_headers'] = json.loads(extract['raw_headers'])
            if extract.get('raw_data'):
                extract['raw_data'] = json.loads(extract['raw_data'])
            extracts.append(extract)
        
        return extracts
    
    def get_extract_by_id(self, extract_id: int) -> Optional[Dict]:
        """Get single extract by ID"""
        result = self.conn.execute("""
            SELECT * FROM raw_extracts WHERE id = ?
        """, [extract_id]).fetchone()
        
        if not result:
            return None
        
        columns = [desc[0] for desc in self.conn.description]
        extract = dict(zip(columns, result))
        
        if extract.get('raw_headers'):
            extract['raw_headers'] = json.loads(extract['raw_headers'])
        if extract.get('raw_data'):
            extract['raw_data'] = json.loads(extract['raw_data'])
        
        return extract
    
    def get_files_summary(self, project: str = None) -> List[Dict]:
        """Get summary of all vacuumed files"""
        query = """
            SELECT 
                source_file,
                project,
                file_type,
                COUNT(*) as table_count,
                SUM(row_count) as total_rows,
                MIN(extracted_at) as first_extracted,
                AVG(confidence) as avg_confidence
            FROM raw_extracts
        """
        
        if project:
            query += " WHERE project = ?"
            params = [project]
        else:
            params = []
        
        query += " GROUP BY source_file, project, file_type ORDER BY first_extracted DESC"
        
        result = self.conn.execute(query, params).fetchall()
        
        return [
            {
                'source_file': row[0],
                'project': row[1],
                'file_type': row[2],
                'table_count': row[3],
                'total_rows': row[4],
                'first_extracted': row[5],
                'avg_confidence': round(row[6], 2) if row[6] else 0
            }
            for row in result
        ]
    
    def delete_file_extracts(self, source_file: str, project: str = None) -> int:
        """Delete all extracts for a file"""
        if project:
            result = self.conn.execute("""
                DELETE FROM raw_extracts WHERE source_file = ? AND project = ?
            """, [source_file, project])
        else:
            result = self.conn.execute("""
                DELETE FROM raw_extracts WHERE source_file = ?
            """, [source_file])
        
        self.conn.commit()
        return result.rowcount
    
    def delete_all_extracts(self) -> int:
        """Delete all extracts (reset)"""
        result = self.conn.execute("DELETE FROM raw_extracts")
        self.conn.commit()
        return result.rowcount
    
    def apply_mapping(self, extract_id: int, column_map: Dict[str, str], target_table: str) -> bool:
        """
        Apply column mapping and create structured table.
        
        column_map: {"original_col": "target_col", ...}
        target_table: Name for the new structured table
        """
        extract = self.get_extract_by_id(extract_id)
        if not extract:
            return False
        
        headers = extract['raw_headers']
        data = extract['raw_data']
        
        # Create new headers based on mapping
        new_headers = []
        col_indices = []
        for i, h in enumerate(headers):
            if h in column_map:
                new_headers.append(column_map[h])
                col_indices.append(i)
        
        if not new_headers:
            return False
        
        # Extract mapped columns
        mapped_data = []
        for row in data:
            mapped_row = [row[i] if i < len(row) else '' for i in col_indices]
            mapped_data.append(mapped_row)
        
        # Create DataFrame and store in DuckDB
        import pandas as pd
        df = pd.DataFrame(mapped_data, columns=new_headers)
        
        # Sanitize table name
        safe_table = re.sub(r'[^\w]', '_', target_table.lower())
        
        self.conn.execute(f"DROP TABLE IF EXISTS {safe_table}")
        self.conn.register('temp_df', df)
        self.conn.execute(f"CREATE TABLE {safe_table} AS SELECT * FROM temp_df")
        self.conn.unregister('temp_df')
        
        # Update extract status
        self.conn.execute("""
            UPDATE raw_extracts SET status = 'mapped', mapped_to = ? WHERE id = ?
        """, [safe_table, extract_id])
        
        # Store the mapping for learning
        for orig, target in column_map.items():
            self._learn_mapping(orig, target)
        
        self.conn.commit()
        logger.info(f"Created table {safe_table} from extract {extract_id}")
        
        return True
    
    def _learn_mapping(self, source: str, target: str):
        """Store column mapping for future suggestions"""
        # Check if mapping exists
        existing = self.conn.execute("""
            SELECT id, times_used FROM column_mappings 
            WHERE LOWER(source_pattern) = LOWER(?) AND target_field = ?
        """, [source, target]).fetchone()
        
        if existing:
            self.conn.execute("""
                UPDATE column_mappings 
                SET times_used = times_used + 1, last_used = CURRENT_TIMESTAMP
                WHERE id = ?
            """, [existing[0]])
        else:
            self.conn.execute("""
                INSERT INTO column_mappings (source_pattern, target_field)
                VALUES (?, ?)
            """, [source, target])
    
    def suggest_mappings(self, headers: List[str]) -> Dict[str, str]:
        """Suggest column mappings based on learned patterns"""
        suggestions = {}
        
        for header in headers:
            # Check exact match first
            result = self.conn.execute("""
                SELECT target_field, confidence, times_used
                FROM column_mappings
                WHERE LOWER(source_pattern) = LOWER(?)
                ORDER BY times_used DESC, confidence DESC
                LIMIT 1
            """, [header]).fetchone()
            
            if result:
                suggestions[header] = {
                    'target': result[0],
                    'confidence': result[1],
                    'times_used': result[2]
                }
        
        return suggestions
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# Singleton instance
_vacuum_extractor: Optional[VacuumExtractor] = None

def get_vacuum_extractor() -> VacuumExtractor:
    """Get or create singleton extractor"""
    global _vacuum_extractor
    if _vacuum_extractor is None:
        _vacuum_extractor = VacuumExtractor()
    return _vacuum_extractor
