"""
Template Manager
=================
Saves, matches, and applies document templates.
Templates store the learned structure of vendor pay register formats.

Deploy to: backend/extraction/template_manager.py
"""

import os
import json
import logging
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Try to import Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

# Try PDF libraries for fingerprinting
try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


@dataclass
class SectionTemplate:
    """Template for a document section"""
    section_type: str  # employee_info, earnings, taxes, etc.
    layout_type: str   # table, key_value
    bbox: Optional[Dict[str, float]] = None  # Bounding box {left, top, width, height}
    page: int = 1
    columns: List[Dict] = None  # Column definitions with positions
    header_row: int = 0
    expected_headers: List[str] = None
    
    def __post_init__(self):
        if self.columns is None:
            self.columns = []
        if self.expected_headers is None:
            self.expected_headers = []


@dataclass
class DocumentTemplate:
    """Complete template for a document type"""
    id: str
    name: str
    vendor: str
    version: str
    created_at: str
    updated_at: str
    confidence: float
    source_file: str
    fingerprint: str  # Hash of structural elements for matching
    sections: List[SectionTemplate]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TemplateManager:
    """
    Manages document templates for extraction.
    
    Features:
    - Template matching based on document fingerprint
    - Template versioning and updates
    - Learning from user corrections
    - Supabase storage with local fallback
    """
    
    def __init__(self):
        self.supabase: Optional[Client] = None
        self.local_templates: Dict[str, DocumentTemplate] = {}
        self._init_storage()
    
    def _init_storage(self):
        """Initialize storage backend"""
        if SUPABASE_AVAILABLE:
            url = os.environ.get('SUPABASE_URL')
            key = os.environ.get('SUPABASE_SERVICE_KEY') or os.environ.get('SUPABASE_KEY')
            
            if url and key:
                try:
                    self.supabase = create_client(url, key)
                    self._ensure_table_exists()
                    logger.info("Template manager using Supabase storage")
                except Exception as e:
                    logger.warning(f"Supabase init failed: {e}, using local storage")
        
        if not self.supabase:
            logger.info("Template manager using local storage")
    
    def _ensure_table_exists(self):
        """Ensure the templates table exists"""
        # Table creation is done via SQL migration, not here
        pass
    
    def find_matching_template(self, file_path: str) -> Optional[Dict]:
        """
        Find a template that matches the given document.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Matching template dict with confidence score, or None
        """
        # Generate fingerprint for this document
        fingerprint = self._generate_fingerprint(file_path)
        
        if not fingerprint:
            return None
        
        # Search for matching templates
        templates = self._get_all_templates()
        
        best_match = None
        best_score = 0.0
        
        for template in templates:
            score = self._compare_fingerprints(fingerprint, template.get('fingerprint', ''))
            
            if score > best_score and score >= 0.80:  # 80% match threshold
                best_score = score
                best_match = template
        
        if best_match:
            best_match['confidence'] = best_score
            logger.info(f"Found matching template: {best_match.get('name')} (score: {best_score:.2f})")
        
        return best_match
    
    def _generate_fingerprint(self, file_path: str) -> Optional[str]:
        """
        Generate a structural fingerprint for a document.
        Based on text positions, not content.
        """
        try:
            fingerprint_parts = []
            
            if PYMUPDF_AVAILABLE:
                doc = fitz.open(file_path)
                
                # Analyze first 3 pages
                for page_num in range(min(3, len(doc))):
                    page = doc[page_num]
                    
                    # Get text blocks
                    blocks = page.get_text("dict")["blocks"]
                    
                    for block in blocks:
                        if block.get("type") == 0:  # Text block
                            bbox = block.get("bbox", [0, 0, 0, 0])
                            # Normalize to percentages (0-100)
                            page_width = page.rect.width
                            page_height = page.rect.height
                            
                            norm_bbox = [
                                int(bbox[0] / page_width * 100),
                                int(bbox[1] / page_height * 100),
                                int(bbox[2] / page_width * 100),
                                int(bbox[3] / page_height * 100),
                            ]
                            fingerprint_parts.append(f"T{norm_bbox}")
                    
                    # Get tables
                    tables = page.find_tables()
                    for table in tables:
                        bbox = table.bbox
                        norm_bbox = [
                            int(bbox[0] / page_width * 100),
                            int(bbox[1] / page_height * 100),
                            int(bbox[2] / page_width * 100),
                            int(bbox[3] / page_height * 100),
                        ]
                        fingerprint_parts.append(f"TBL{norm_bbox}c{table.col_count}")
                
                doc.close()
            
            elif PDFPLUMBER_AVAILABLE:
                with pdfplumber.open(file_path) as pdf:
                    for page_num in range(min(3, len(pdf.pages))):
                        page = pdf.pages[page_num]
                        
                        # Get tables
                        tables = page.find_tables()
                        for i, table in enumerate(tables):
                            bbox = table.bbox
                            fingerprint_parts.append(f"TBL{i}:{len(table.cells)}")
            
            if not fingerprint_parts:
                return None
            
            # Create hash
            fingerprint_str = '|'.join(fingerprint_parts)
            return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:32]
            
        except Exception as e:
            logger.warning(f"Error generating fingerprint: {e}")
            return None
    
    def _compare_fingerprints(self, fp1: str, fp2: str) -> float:
        """
        Compare two fingerprints and return similarity score.
        Simple comparison - could be enhanced with fuzzy matching.
        """
        if not fp1 or not fp2:
            return 0.0
        
        if fp1 == fp2:
            return 1.0
        
        # Character-level similarity
        matches = sum(1 for a, b in zip(fp1, fp2) if a == b)
        return matches / max(len(fp1), len(fp2))
    
    def _get_all_templates(self) -> List[Dict]:
        """Get all saved templates"""
        templates = []
        
        if self.supabase:
            try:
                result = self.supabase.table('extraction_templates').select('*').execute()
                templates = result.data or []
            except Exception as e:
                logger.warning(f"Error fetching templates from Supabase: {e}")
        
        # Also include local templates
        templates.extend([asdict(t) for t in self.local_templates.values()])
        
        return templates
    
    def save_template(self, name: str, layout: Dict, 
                      source_file: str,
                      vendor: str = 'unknown') -> Optional[str]:
        """
        Save a new template.
        
        Args:
            name: Template name
            layout: Layout structure from cloud analysis
            source_file: Original file this was learned from
            vendor: Vendor name if known
            
        Returns:
            Template ID if successful
        """
        template_id = hashlib.sha256(
            f"{name}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        # Handle both dict and CloudAnalysisResult dataclass
        if hasattr(layout, 'confidence'):
            # It's a CloudAnalysisResult dataclass
            confidence = layout.confidence
            fingerprint = getattr(layout, 'fingerprint', '')
            
            # Convert tables to section definitions
            sections = []
            for table in getattr(layout, 'tables', []):
                sections.append({
                    'section_type': 'unknown',
                    'layout_type': 'table',
                    'page': table.page_number,
                    'bbox': table.bbox,
                    'row_count': table.row_count,
                    'column_count': table.column_count,
                    'expected_headers': [c.text for c in table.cells if c.is_header][:20]
                })
            
            metadata = {
                'page_count': getattr(layout, 'page_count', 1),
                'source': 'cloud_analysis'
            }
        else:
            # It's a dict
            confidence = layout.get('confidence', 0.9)
            fingerprint = layout.get('fingerprint', '')
            sections = layout.get('sections', [])
            metadata = layout.get('metadata', {})
        
        template_data = {
            'id': template_id,
            'name': name,
            'vendor': vendor,
            'version': '1.0',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'confidence': confidence,
            'source_file': source_file,
            'fingerprint': fingerprint,
            'sections': sections,
            'metadata': metadata
        }
        
        if self.supabase:
            try:
                self.supabase.table('extraction_templates').insert(template_data).execute()
                logger.info(f"Saved template to Supabase: {template_id}")
                return template_id
            except Exception as e:
                logger.warning(f"Error saving to Supabase: {e}")
        
        # Fallback to local storage
        self.local_templates[template_id] = DocumentTemplate(**template_data)
        logger.info(f"Saved template locally: {template_id}")
        
        return template_id
    
    def extract_with_template(self, file_path: str, 
                              template: Dict) -> Dict[str, Any]:
        """
        Extract data using a saved template.
        Template provides exact coordinates for each section.
        """
        results = {}
        sections = template.get('sections', [])
        
        if not sections:
            logger.warning("Template has no sections defined")
            return results
        
        try:
            if PYMUPDF_AVAILABLE:
                doc = fitz.open(file_path)
                
                for section in sections:
                    section_type = section.get('section_type', 'unknown')
                    bbox = section.get('bbox')
                    page_num = section.get('page', 1) - 1
                    
                    if page_num >= len(doc):
                        continue
                    
                    page = doc[page_num]
                    
                    # Extract text from bounding box
                    if bbox:
                        rect = fitz.Rect(
                            bbox['left'] * page.rect.width,
                            bbox['top'] * page.rect.height,
                            (bbox['left'] + bbox['width']) * page.rect.width,
                            (bbox['top'] + bbox['height']) * page.rect.height
                        )
                        text = page.get_text("text", clip=rect)
                        
                        # Parse based on layout type
                        layout_type = section.get('layout_type', 'table')
                        
                        if layout_type == 'table':
                            data, headers = self._parse_table_text(text, section)
                        else:
                            data, headers = self._parse_key_value_text(text)
                        
                        results[section_type] = {
                            'data': data,
                            'headers': headers,
                            'confidence': 0.9,
                            'extractor_name': 'template'
                        }
                
                doc.close()
                
        except Exception as e:
            logger.error(f"Template extraction failed: {e}")
        
        return results
    
    def _parse_table_text(self, text: str, 
                          section: Dict) -> tuple:
        """Parse table text using column positions from template"""
        lines = text.strip().split('\n')
        
        if not lines:
            return [], []
        
        # Use expected headers if available
        expected_headers = section.get('expected_headers', [])
        columns = section.get('columns', [])
        
        # First line as headers (or use expected)
        headers = expected_headers if expected_headers else lines[0].split()
        
        # Parse data rows
        data = []
        for line in lines[1:]:
            if not line.strip():
                continue
            
            # Split by whitespace (simple approach)
            # Could be enhanced using column positions
            values = line.split()
            if values:
                data.append(values)
        
        return data, headers
    
    def _parse_key_value_text(self, text: str) -> tuple:
        """Parse key-value text"""
        pairs = []
        
        for line in text.strip().split('\n'):
            if ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    pairs.append({
                        'key': parts[0].strip(),
                        'value': parts[1].strip()
                    })
        
        return pairs, ['key', 'value']
    
    def update_from_corrections(self, document_id: str, 
                                corrections: Dict) -> bool:
        """
        Update template based on user corrections.
        This is how the system learns and improves.
        """
        try:
            # Find the template used for this document
            # Apply corrections to improve matching
            
            # For now, just log the corrections
            logger.info(f"Received corrections for document {document_id}: {corrections}")
            
            # TODO: Implement template improvement logic
            # - Adjust column positions based on corrections
            # - Update expected headers
            # - Refine bounding boxes
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating from corrections: {e}")
            return False
    
    def get_template_by_id(self, template_id: str) -> Optional[Dict]:
        """Get a specific template by ID"""
        if self.supabase:
            try:
                result = self.supabase.table('extraction_templates').select('*').eq(
                    'id', template_id
                ).single().execute()
                return result.data
            except Exception as e:
                logger.warning(f"Error fetching template: {e}")
        
        # Check local
        template = self.local_templates.get(template_id)
        return asdict(template) if template else None
    
    def delete_template(self, template_id: str) -> bool:
        """Delete a template"""
        if self.supabase:
            try:
                self.supabase.table('extraction_templates').delete().eq(
                    'id', template_id
                ).execute()
                return True
            except Exception as e:
                logger.warning(f"Error deleting template: {e}")
        
        if template_id in self.local_templates:
            del self.local_templates[template_id]
            return True
        
        return False


# Singleton
_template_manager_instance = None

def get_template_manager() -> TemplateManager:
    """Get or create template manager singleton"""
    global _template_manager_instance
    if _template_manager_instance is None:
        _template_manager_instance = TemplateManager()
    return _template_manager_instance
