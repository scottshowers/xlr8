"""
Cloud Analyzer - AWS Textract Integration
==========================================
Uses AWS Textract for layout detection when local extraction
has low confidence. Only sends redacted pages for structure analysis.

Deploy to: backend/extraction/cloud_analyzer.py

Required environment variables:
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- AWS_REGION (default: us-east-1)
"""

import os
import io
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Try to import boto3 for AWS
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False
    logger.warning("boto3 not installed - cloud analysis unavailable")

# Try to import PDF libraries
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


@dataclass
class TableCell:
    """Represents a cell in a detected table"""
    text: str
    row_index: int
    column_index: int
    confidence: float
    bbox: Dict[str, float]  # {left, top, width, height}
    is_header: bool = False


@dataclass
class DetectedTable:
    """Represents a table detected by Textract"""
    table_index: int
    page_number: int
    cells: List[TableCell]
    row_count: int
    column_count: int
    confidence: float
    bbox: Dict[str, float]


@dataclass
class LayoutBlock:
    """Represents a detected layout block"""
    block_type: str  # TABLE, KEY_VALUE_SET, LINE, etc.
    text: str
    confidence: float
    bbox: Dict[str, float]
    page_number: int
    relationships: List[str] = field(default_factory=list)


@dataclass
class CloudAnalysisResult:
    """Result from cloud analysis"""
    success: bool
    tables: List[DetectedTable]
    key_value_pairs: Dict[str, str]
    layout_blocks: List[LayoutBlock]
    page_count: int
    confidence: float
    errors: List[str] = field(default_factory=list)
    raw_response: Optional[Dict] = None


class CloudAnalyzer:
    """
    AWS Textract integration for document analysis.
    
    Features:
    - Table detection with cell-level bounding boxes
    - Key-value pair extraction (for form fields)
    - Layout structure analysis
    - Designed to work with redacted documents (no PII)
    
    Usage:
        analyzer = CloudAnalyzer()
        result = analyzer.analyze_layout(pdf_path, max_pages=3)
    """
    
    def __init__(self):
        self.client = None
        self._init_client()
    
    def _init_client(self):
        """Initialize AWS Textract client"""
        if not BOTO3_AVAILABLE:
            logger.warning("boto3 not available - cloud analyzer disabled")
            return
        
        # Check for credentials
        aws_key = os.environ.get('AWS_ACCESS_KEY_ID')
        aws_secret = os.environ.get('AWS_SECRET_ACCESS_KEY')
        aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        
        if not aws_key or not aws_secret:
            logger.warning("AWS credentials not configured - cloud analyzer disabled")
            return
        
        try:
            self.client = boto3.client(
                'textract',
                aws_access_key_id=aws_key,
                aws_secret_access_key=aws_secret,
                region_name=aws_region
            )
            logger.info(f"AWS Textract client initialized (region: {aws_region})")
        except Exception as e:
            logger.error(f"Failed to initialize AWS client: {e}")
            self.client = None
    
    @property
    def is_available(self) -> bool:
        """Check if cloud analysis is available"""
        return self.client is not None
    
    def analyze_layout(self, pdf_path: str, 
                       max_pages: int = 5,
                       structure_only: bool = False) -> CloudAnalysisResult:
        """
        Analyze document layout using AWS Textract.
        
        Args:
            pdf_path: Path to PDF file (should be redacted for PII protection)
            max_pages: Maximum pages to analyze (cost control)
            structure_only: If True, only extract structure, not text content
            
        Returns:
            CloudAnalysisResult with detected tables, forms, and layout
        """
        if not self.is_available:
            return CloudAnalysisResult(
                success=False,
                tables=[],
                key_value_pairs={},
                layout_blocks=[],
                page_count=0,
                confidence=0.0,
                errors=["Cloud analyzer not available - check AWS credentials"]
            )
        
        try:
            # Read PDF and limit pages
            pdf_bytes = self._prepare_document(pdf_path, max_pages)
            
            if pdf_bytes is None:
                return CloudAnalysisResult(
                    success=False,
                    tables=[],
                    key_value_pairs={},
                    layout_blocks=[],
                    page_count=0,
                    confidence=0.0,
                    errors=["Failed to read PDF document"]
                )
            
            # Call Textract
            response = self._call_textract(pdf_bytes)
            
            if response is None:
                return CloudAnalysisResult(
                    success=False,
                    tables=[],
                    key_value_pairs={},
                    layout_blocks=[],
                    page_count=0,
                    confidence=0.0,
                    errors=["Textract API call failed"]
                )
            
            # Parse response
            result = self._parse_textract_response(response)
            result.raw_response = response if not structure_only else None
            
            return result
            
        except Exception as e:
            logger.error(f"Cloud analysis failed: {e}", exc_info=True)
            return CloudAnalysisResult(
                success=False,
                tables=[],
                key_value_pairs={},
                layout_blocks=[],
                page_count=0,
                confidence=0.0,
                errors=[str(e)]
            )
    
    def _prepare_document(self, pdf_path: str, max_pages: int) -> Optional[bytes]:
        """
        Prepare document for Textract - limit to max_pages.
        """
        try:
            if not PYMUPDF_AVAILABLE:
                # If PyMuPDF not available, just read the whole file
                with open(pdf_path, 'rb') as f:
                    return f.read()
            
            # Use PyMuPDF to extract only first N pages
            doc = fitz.open(pdf_path)
            
            if len(doc) <= max_pages:
                # Entire document fits within limit
                doc.close()
                with open(pdf_path, 'rb') as f:
                    return f.read()
            
            # Create new PDF with only first N pages
            new_doc = fitz.open()
            for page_num in range(min(max_pages, len(doc))):
                new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            
            # Get bytes
            pdf_bytes = new_doc.write()
            
            new_doc.close()
            doc.close()
            
            logger.info(f"Prepared {max_pages} pages for cloud analysis (original: {len(doc)} pages)")
            
            return bytes(pdf_bytes)
            
        except Exception as e:
            logger.error(f"Error preparing document: {e}")
            return None
    
    def _call_textract(self, pdf_bytes: bytes) -> Optional[Dict]:
        """
        Call AWS Textract API.
        AnalyzeDocument only supports single pages, so we convert PDF pages
        to images and analyze each one, then merge results.
        """
        try:
            if not PYMUPDF_AVAILABLE:
                logger.error("PyMuPDF required for Textract multi-page support")
                return None
            
            # Open PDF from bytes
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            all_blocks = []
            page_count = len(doc)
            
            logger.info(f"Analyzing {page_count} pages with Textract...")
            
            for page_num in range(page_count):
                page = doc[page_num]
                
                # Convert page to PNG image (Textract likes this better)
                # Use 150 DPI for good quality without huge size
                mat = fitz.Matrix(150/72, 150/72)  # 150 DPI
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                
                logger.info(f"  Analyzing page {page_num + 1}/{page_count} ({len(img_bytes)} bytes)")
                
                try:
                    response = self.client.analyze_document(
                        Document={'Bytes': img_bytes},
                        FeatureTypes=['TABLES', 'FORMS', 'LAYOUT']
                    )
                    
                    # Add page number to each block and collect
                    for block in response.get('Blocks', []):
                        block['Page'] = page_num + 1
                        all_blocks.append(block)
                        
                except ClientError as e:
                    error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                    error_msg = e.response.get('Error', {}).get('Message', str(e))
                    logger.warning(f"Textract error on page {page_num + 1}: {error_code} - {error_msg}")
                    continue
            
            doc.close()
            
            if not all_blocks:
                logger.error("No blocks extracted from any page")
                return None
            
            # Return merged response
            logger.info(f"Textract complete: {len(all_blocks)} blocks from {page_count} pages")
            return {
                'Blocks': all_blocks,
                'DocumentMetadata': {'Pages': page_count}
            }
                
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_msg = e.response.get('Error', {}).get('Message', str(e))
            logger.error(f"Textract API error ({error_code}): {error_msg}")
            return None
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            return None
        except Exception as e:
            logger.error(f"Textract call failed: {e}", exc_info=True)
            return None
    
    def _parse_textract_response(self, response: Dict) -> CloudAnalysisResult:
        """
        Parse Textract response into structured result.
        """
        blocks = response.get('Blocks', [])
        
        if not blocks:
            return CloudAnalysisResult(
                success=True,
                tables=[],
                key_value_pairs={},
                layout_blocks=[],
                page_count=0,
                confidence=0.0
            )
        
        # Build block lookup
        block_map = {block['Id']: block for block in blocks}
        
        # Extract tables
        tables = self._extract_tables(blocks, block_map)
        
        # Extract key-value pairs
        key_value_pairs = self._extract_key_value_pairs(blocks, block_map)
        
        # Extract layout blocks
        layout_blocks = self._extract_layout_blocks(blocks)
        
        # Count pages
        page_blocks = [b for b in blocks if b.get('BlockType') == 'PAGE']
        page_count = len(page_blocks)
        
        # Calculate overall confidence
        confidences = [b.get('Confidence', 0) for b in blocks if 'Confidence' in b]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return CloudAnalysisResult(
            success=True,
            tables=tables,
            key_value_pairs=key_value_pairs,
            layout_blocks=layout_blocks,
            page_count=page_count,
            confidence=avg_confidence / 100.0  # Textract uses 0-100
        )
    
    def _extract_tables(self, blocks: List[Dict], 
                        block_map: Dict[str, Dict]) -> List[DetectedTable]:
        """Extract table structures from Textract response"""
        tables = []
        
        # Find TABLE blocks
        table_blocks = [b for b in blocks if b.get('BlockType') == 'TABLE']
        
        for table_idx, table_block in enumerate(table_blocks):
            cells = []
            max_row = 0
            max_col = 0
            
            # Get child CELL blocks
            relationships = table_block.get('Relationships', [])
            child_ids = []
            for rel in relationships:
                if rel.get('Type') == 'CHILD':
                    child_ids.extend(rel.get('Ids', []))
            
            for cell_id in child_ids:
                cell_block = block_map.get(cell_id)
                if not cell_block or cell_block.get('BlockType') != 'CELL':
                    continue
                
                row_idx = cell_block.get('RowIndex', 1) - 1  # 0-indexed
                col_idx = cell_block.get('ColumnIndex', 1) - 1
                
                max_row = max(max_row, row_idx + 1)
                max_col = max(max_col, col_idx + 1)
                
                # Get cell text
                cell_text = self._get_block_text(cell_block, block_map)
                
                # Get bounding box
                bbox = cell_block.get('Geometry', {}).get('BoundingBox', {})
                
                cells.append(TableCell(
                    text=cell_text,
                    row_index=row_idx,
                    column_index=col_idx,
                    confidence=cell_block.get('Confidence', 0) / 100.0,
                    bbox=bbox,
                    is_header=row_idx == 0  # Assume first row is header
                ))
            
            # Get table bounding box
            table_bbox = table_block.get('Geometry', {}).get('BoundingBox', {})
            
            tables.append(DetectedTable(
                table_index=table_idx,
                page_number=table_block.get('Page', 1),
                cells=cells,
                row_count=max_row,
                column_count=max_col,
                confidence=table_block.get('Confidence', 0) / 100.0,
                bbox=table_bbox
            ))
        
        return tables
    
    def _extract_key_value_pairs(self, blocks: List[Dict], 
                                  block_map: Dict[str, Dict]) -> Dict[str, str]:
        """Extract key-value pairs from form fields"""
        pairs = {}
        
        # Find KEY_VALUE_SET blocks
        key_blocks = [b for b in blocks 
                     if b.get('BlockType') == 'KEY_VALUE_SET' 
                     and 'KEY' in b.get('EntityTypes', [])]
        
        for key_block in key_blocks:
            # Get key text
            key_text = self._get_block_text(key_block, block_map)
            
            # Find associated value
            relationships = key_block.get('Relationships', [])
            for rel in relationships:
                if rel.get('Type') == 'VALUE':
                    for value_id in rel.get('Ids', []):
                        value_block = block_map.get(value_id)
                        if value_block:
                            value_text = self._get_block_text(value_block, block_map)
                            if key_text and value_text:
                                pairs[key_text.strip()] = value_text.strip()
        
        return pairs
    
    def _extract_layout_blocks(self, blocks: List[Dict]) -> List[LayoutBlock]:
        """Extract general layout blocks"""
        layout_blocks = []
        
        # Get LAYOUT blocks (introduced in newer Textract)
        for block in blocks:
            block_type = block.get('BlockType', '')
            
            # Include relevant block types
            if block_type in ['LAYOUT_TITLE', 'LAYOUT_HEADER', 'LAYOUT_FOOTER',
                             'LAYOUT_SECTION_HEADER', 'LAYOUT_PAGE_NUMBER',
                             'LAYOUT_TABLE', 'LAYOUT_KEY_VALUE', 'LAYOUT_TEXT',
                             'LAYOUT_FIGURE', 'LAYOUT_LIST']:
                
                bbox = block.get('Geometry', {}).get('BoundingBox', {})
                
                layout_blocks.append(LayoutBlock(
                    block_type=block_type,
                    text=block.get('Text', ''),
                    confidence=block.get('Confidence', 0) / 100.0,
                    bbox=bbox,
                    page_number=block.get('Page', 1)
                ))
        
        return layout_blocks
    
    def _get_block_text(self, block: Dict, block_map: Dict[str, Dict]) -> str:
        """Get text content from a block, including child blocks"""
        text_parts = []
        
        # Check for direct text
        if 'Text' in block:
            return block['Text']
        
        # Get text from child blocks
        relationships = block.get('Relationships', [])
        for rel in relationships:
            if rel.get('Type') == 'CHILD':
                for child_id in rel.get('Ids', []):
                    child_block = block_map.get(child_id)
                    if child_block and child_block.get('BlockType') in ['WORD', 'LINE']:
                        text_parts.append(child_block.get('Text', ''))
        
        return ' '.join(text_parts)
    
    def convert_to_template(self, analysis_result: CloudAnalysisResult) -> Dict[str, Any]:
        """
        Convert Textract analysis result to a template format
        that can be saved and used for future extractions.
        """
        template = {
            'version': '1.0',
            'source': 'aws_textract',
            'page_structure': [],
            'sections': [],
            'confidence': analysis_result.confidence
        }
        
        # Build section definitions from detected tables
        for table in analysis_result.tables:
            section = {
                'type': 'table',
                'bbox': table.bbox,
                'page': table.page_number,
                'columns': table.column_count,
                'header_row': 0,  # Assume first row is header
                'column_positions': self._get_column_positions(table)
            }
            template['sections'].append(section)
        
        # Add key-value sections
        if analysis_result.key_value_pairs:
            template['sections'].append({
                'type': 'key_value',
                'fields': list(analysis_result.key_value_pairs.keys())
            })
        
        return template
    
    def _get_column_positions(self, table: DetectedTable) -> List[Dict]:
        """Extract column positions from table cells"""
        columns = {}
        
        for cell in table.cells:
            col_idx = cell.column_index
            if col_idx not in columns:
                columns[col_idx] = {
                    'index': col_idx,
                    'left': cell.bbox.get('Left', 0),
                    'width': cell.bbox.get('Width', 0),
                    'header': ''
                }
            
            # Get header text from first row
            if cell.row_index == 0:
                columns[col_idx]['header'] = cell.text
        
        return list(columns.values())


# Singleton instance
_cloud_analyzer_instance = None

def get_cloud_analyzer() -> CloudAnalyzer:
    """Get or create the cloud analyzer singleton"""
    global _cloud_analyzer_instance
    if _cloud_analyzer_instance is None:
        _cloud_analyzer_instance = CloudAnalyzer()
    return _cloud_analyzer_instance
