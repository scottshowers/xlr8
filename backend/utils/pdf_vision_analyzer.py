"""
PDF Vision Analyzer - Claude Vision-based column structure extraction
======================================================================

Uses Claude Vision to accurately extract column headers from PDF tables.
This approach handles:
- Borderless tables
- Multi-line headers
- Continuation pages with repeated headers
- Complex layouts

FLOW:
1. Render first 2 pages to images
2. Detect and redact PII from images
3. Send redacted images to Claude Vision
4. Get back column structure with high accuracy
5. Apply column structure to all pages

PII PROTECTION:
- OCR detects text locations
- Regex identifies PII patterns
- Black boxes drawn over PII before sending to external API

Author: XLR8 Team
Version: 1.0.0
"""

import os
import re
import io
import base64
import logging
from typing import List, Dict, Tuple, Optional, Any
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

# Try to import required libraries
try:
    from pypdfium2 import PdfDocument
    PYPDFIUM_AVAILABLE = True
except ImportError:
    PYPDFIUM_AVAILABLE = False
    logger.warning("[PDF-VISION] pypdfium2 not available")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("[PDF-VISION] pytesseract not available - PII redaction limited")

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("[PDF-VISION] anthropic SDK not available")


# =============================================================================
# PII PATTERNS FOR REDACTION
# =============================================================================

# =============================================================================
# COMPREHENSIVE PII PATTERNS
# Based on HIPAA, GDPR, CCPA, and financial regulations
# =============================================================================

PII_PATTERNS = {
    # -------------------------------------------------------------------------
    # GOVERNMENT IDENTIFIERS
    # -------------------------------------------------------------------------
    'ssn': [
        r'\b\d{3}-\d{2}-\d{4}\b',              # 123-45-6789
        r'\b\d{3}\s\d{2}\s\d{4}\b',            # 123 45 6789  
        r'\b\d{9}\b',                           # 123456789 (9 digits standalone)
    ],
    'ein_fein': [
        r'\b\d{2}-\d{7}\b',                     # 12-3456789 (Employer ID)
    ],
    'itin': [
        r'\b9\d{2}-[7-9]\d-\d{4}\b',           # 9XX-7X-XXXX (Individual Taxpayer ID)
    ],
    'drivers_license': [
        r'\b[A-Z]\d{7,8}\b',                   # Various state formats
        r'\b[A-Z]{1,2}\d{6,7}\b',
        r'\b\d{7,9}\b',                        # Some states use numbers only
    ],
    'passport': [
        r'\b[A-Z]{1,2}\d{6,9}\b',              # US passport format
    ],
    'military_id': [
        r'\b\d{10}\b',                          # DoD ID number (10 digits)
    ],
    
    # -------------------------------------------------------------------------
    # FINANCIAL IDENTIFIERS
    # -------------------------------------------------------------------------
    'bank_account': [
        r'\b\d{10,17}\b',                       # Account numbers (10-17 digits)
    ],
    'routing_number': [
        r'\b[0-3]\d{8}\b',                      # ABA routing (starts 0-3, 9 digits)
    ],
    'credit_card': [
        r'\b4\d{3}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',     # Visa
        r'\b5[1-5]\d{2}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', # Mastercard
        r'\b3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}\b',            # Amex
        r'\b6(?:011|5\d{2})[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', # Discover
    ],
    'debit_card': [
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',      # Generic 16-digit
    ],
    
    # -------------------------------------------------------------------------
    # CONTACT INFORMATION
    # -------------------------------------------------------------------------
    'phone': [
        r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',   # 123-456-7890
        r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}\b',     # (123) 456-7890
        r'\+1[-.\s]?\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b',  # +1-123-456-7890
    ],
    'email': [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    ],
    'address': [
        r'\b\d{1,5}\s+[\w\s]+(?:street|st|avenue|ave|road|rd|drive|dr|lane|ln|way|court|ct|boulevard|blvd|circle|cir|place|pl)\.?\b',
    ],
    'zip_code': [
        r'\b\d{5}(?:-\d{4})?\b',                # 12345 or 12345-6789
    ],
    
    # -------------------------------------------------------------------------
    # DATES (can identify individuals in context)
    # -------------------------------------------------------------------------
    'dob': [
        r'\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b',  # MM/DD/YYYY
        r'\b(?:19|20)\d{2}[/-](?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])\b',  # YYYY/MM/DD
        r'\b(?:0?[1-9]|[12]\d|3[01])[/-](?:0?[1-9]|1[0-2])[/-](?:19|20)\d{2}\b',  # DD/MM/YYYY
    ],
    
    # -------------------------------------------------------------------------
    # HEALTHCARE IDENTIFIERS (HIPAA)
    # -------------------------------------------------------------------------
    'medical_record': [
        r'\b(?:MRN|MR#?|Medical Record)[:\s#]*\d{6,12}\b',
    ],
    'health_plan_id': [
        r'\b[A-Z]{3}\d{9}\b',                   # Health plan beneficiary number
    ],
    'npi': [
        r'\b\d{10}\b',                           # National Provider Identifier
    ],
    'dea_number': [
        r'\b[A-Z]{2}\d{7}\b',                   # DEA registration number
    ],
    
    # -------------------------------------------------------------------------
    # VEHICLE IDENTIFIERS
    # -------------------------------------------------------------------------
    'vin': [
        r'\b[A-HJ-NPR-Z0-9]{17}\b',             # Vehicle Identification Number
    ],
    'license_plate': [
        r'\b[A-Z0-9]{5,8}\b',                   # Various state formats
    ],
    
    # -------------------------------------------------------------------------
    # DIGITAL IDENTIFIERS
    # -------------------------------------------------------------------------
    'ip_address': [
        r'\b(?:\d{1,3}\.){3}\d{1,3}\b',         # IPv4
    ],
    'mac_address': [
        r'\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b',  # MAC address
    ],
    
    # -------------------------------------------------------------------------
    # BIOMETRIC IDENTIFIERS (text references)
    # -------------------------------------------------------------------------
    'biometric': [
        r'\b(?:fingerprint|retina|iris|voice\s*print|facial\s*recognition)[:\s]+[A-Za-z0-9]+\b',
    ],
    
    # -------------------------------------------------------------------------
    # EMPLOYEE/HR IDENTIFIERS  
    # -------------------------------------------------------------------------
    'employee_id': [
        r'\b(?:EMP|EE|Employee)[#:\s-]*\d{4,10}\b',
    ],
    'payroll_id': [
        r'\b(?:Payroll|PR)[#:\s-]*\d{4,10}\b',
    ],
    
    # -------------------------------------------------------------------------
    # AUTHENTICATION DATA
    # -------------------------------------------------------------------------
    'password': [
        r'\b(?:password|pwd|pass)[:\s=]+\S+\b',
    ],
    'pin': [
        r'\b(?:PIN|pin)[:\s=]+\d{4,6}\b',
    ],
    'security_answer': [
        r'\b(?:mother\'?s?\s*maiden|security\s*(?:question|answer))[:\s]+\S+\b',
    ],
}


# =============================================================================
# PDF TO IMAGE CONVERSION
# =============================================================================

def render_pdf_pages_to_images(
    file_path: str,
    pages: List[int] = [0, 1],
    dpi: int = 150
) -> List[Image.Image]:
    """
    Render specified PDF pages to PIL Images.
    
    Args:
        file_path: Path to PDF file
        pages: List of page indices (0-based)
        dpi: Resolution for rendering (higher = better quality but larger)
        
    Returns:
        List of PIL Image objects
    """
    if not PYPDFIUM_AVAILABLE:
        logger.error("[PDF-VISION] pypdfium2 required for image rendering")
        return []
    
    images = []
    
    try:
        pdf = PdfDocument(file_path)
        num_pages = len(pdf)
        
        for page_idx in pages:
            if page_idx >= num_pages:
                logger.warning(f"[PDF-VISION] Page {page_idx} doesn't exist (only {num_pages} pages)")
                continue
            
            page = pdf[page_idx]
            
            # Render at specified DPI
            # Scale factor: DPI / 72 (PDF default is 72 DPI)
            scale = dpi / 72
            bitmap = page.render(scale=scale)
            
            # Convert to PIL Image
            pil_image = bitmap.to_pil()
            images.append(pil_image)
            
            logger.info(f"[PDF-VISION] Rendered page {page_idx + 1}: {pil_image.size}")
        
        pdf.close()
        
    except Exception as e:
        logger.error(f"[PDF-VISION] Failed to render PDF: {e}")
    
    return images


# =============================================================================
# PII DETECTION AND REDACTION
# =============================================================================

def detect_pii_regions_with_ocr(image: Image.Image) -> List[Dict[str, Any]]:
    """
    Use OCR to find text in image, then identify PII patterns.
    
    Returns list of regions containing PII with bounding boxes.
    """
    if not TESSERACT_AVAILABLE:
        logger.warning("[PDF-VISION] Tesseract not available - using pattern-only detection")
        return []
    
    pii_regions = []
    
    try:
        # Get OCR data with bounding boxes
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        n_boxes = len(ocr_data['text'])
        
        for i in range(n_boxes):
            text = ocr_data['text'][i].strip()
            
            if not text:
                continue
            
            # Check against all PII patterns
            for pii_type, patterns in PII_PATTERNS.items():
                for pattern in patterns:
                    if re.search(pattern, text, re.IGNORECASE):
                        # Found PII - record the bounding box
                        x = ocr_data['left'][i]
                        y = ocr_data['top'][i]
                        w = ocr_data['width'][i]
                        h = ocr_data['height'][i]
                        
                        pii_regions.append({
                            'type': pii_type,
                            'text': text[:20] + '...' if len(text) > 20 else text,
                            'bbox': (x, y, x + w, y + h),
                            'confidence': ocr_data['conf'][i]
                        })
                        break
        
        if pii_regions:
            logger.warning(f"[PDF-VISION] Found {len(pii_regions)} PII regions to redact")
        
    except Exception as e:
        logger.error(f"[PDF-VISION] OCR PII detection failed: {e}")
    
    return pii_regions


def redact_image(image: Image.Image, regions: List[Dict[str, Any]] = None) -> Image.Image:
    """
    Redact PII from image by drawing black boxes over sensitive regions.
    
    If regions not provided, will detect using OCR.
    If OCR not available, uses conservative approach: blacks out bottom 80% of image
    (keeps headers visible but hides all data rows).
    
    Args:
        image: PIL Image to redact
        regions: Optional list of PII regions with bboxes
        
    Returns:
        Redacted copy of image
    """
    # Create a copy to avoid modifying original
    redacted = image.copy()
    draw = ImageDraw.Draw(redacted)
    
    # If no regions provided, try to detect
    if regions is None:
        if TESSERACT_AVAILABLE:
            regions = detect_pii_regions_with_ocr(image)
        else:
            # CONSERVATIVE FALLBACK: No OCR available
            # Black out bottom 80% of image (data rows)
            # Keep top 20% visible (headers)
            width, height = image.size
            header_height = int(height * 0.20)  # Keep top 20% for headers
            
            draw.rectangle(
                [0, header_height, width, height],
                fill='black'
            )
            
            # Add text explaining redaction
            try:
                draw.text(
                    (10, header_height + 10),
                    "[DATA ROWS REDACTED FOR PII PROTECTION]",
                    fill='white'
                )
            except Exception:
                pass
            
            logger.warning(f"[PDF-VISION] OCR unavailable - used conservative redaction (kept top 20%)")
            return redacted
    
    # Draw black rectangles over PII regions
    redaction_count = 0
    for region in regions:
        bbox = region.get('bbox')
        if bbox:
            # Add small padding
            x1, y1, x2, y2 = bbox
            padding = 2
            draw.rectangle(
                [x1 - padding, y1 - padding, x2 + padding, y2 + padding],
                fill='black'
            )
            redaction_count += 1
    
    if redaction_count > 0:
        logger.warning(f"[PDF-VISION] Redacted {redaction_count} PII regions")
    
    return redacted


def image_to_base64(image: Image.Image, format: str = 'PNG') -> str:
    """Convert PIL Image to base64 string for API transmission."""
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    return base64.standard_b64encode(buffer.getvalue()).decode('utf-8')


# =============================================================================
# CLAUDE VISION COLUMN EXTRACTION
# =============================================================================

COLUMN_EXTRACTION_PROMPT = """You are analyzing a PDF table to extract the column headers.

Look at this image of a PDF page containing a table. Identify ALL column headers in the table.

IMPORTANT:
- Focus on the actual column headers, not page titles or metadata
- If headers span multiple lines, combine them into one name
- Use snake_case for column names (lowercase, underscores)
- Be precise - these will be used as database column names
- Include ALL columns you can see, in left-to-right order
- If a column has no clear header, use a descriptive name based on the data

Respond with ONLY a JSON object in this exact format:
{
  "columns": ["column_name_1", "column_name_2", "column_name_3", ...],
  "table_description": "Brief description of what this table contains",
  "confidence": 0.95
}

Do NOT include any other text, explanation, or markdown - just the JSON object."""


TABLE_EXTRACTION_PROMPT = """You are extracting tabular data from a PDF page.

Look at this image and extract ALL rows of data from the table. 

COLUMN HEADERS (use these exact names):
{columns}

INSTRUCTIONS:
- Extract EVERY row of data you can see
- Use the column names provided above
- If a cell is empty, use empty string ""
- If a cell spans multiple lines, combine into one value
- Skip page headers, footers, and navigation text (like "Page X of Y")
- Skip repeated header rows
- Return data as a JSON array of objects

Respond with ONLY a JSON array in this format:
[
  {{"column_1": "value", "column_2": "value", ...}},
  {{"column_1": "value", "column_2": "value", ...}}
]

Do NOT include any other text, explanation, or markdown - just the JSON array."""


# Full table extraction prompt - extracts ALL data
TABLE_EXTRACTION_PROMPT = """Extract ALL tabular data from this PDF page image.

TASK: Convert the table in this image to structured JSON data.

RULES:
1. Extract EVERY row of data you can see
2. Use consistent column names across all rows (snake_case, lowercase)
3. Preserve the exact values - don't summarize or modify data
4. Skip page headers, footers, and non-table text
5. If a cell is empty, use empty string ""
6. If a row continues from previous page, include it

OUTPUT FORMAT - respond with ONLY this JSON structure:
{
  "columns": ["col_1", "col_2", "col_3"],
  "rows": [
    {"col_1": "value", "col_2": "value", "col_3": "value"},
    {"col_1": "value", "col_2": "value", "col_3": "value"}
  ],
  "page_notes": "any relevant notes about this page"
}

CRITICAL: Output ONLY valid JSON. No markdown, no explanation, no ```."""


def extract_columns_with_vision(
    images: List[Image.Image],
    redact_pii: bool = True
) -> Dict[str, Any]:
    """
    Use Claude Vision to extract column structure from PDF images.
    
    Args:
        images: List of PIL Images (first 2 pages recommended)
        redact_pii: Whether to redact PII before sending (default True)
        
    Returns:
        Dict with columns list and metadata
    """
    if not ANTHROPIC_AVAILABLE:
        logger.error("[PDF-VISION] Anthropic SDK required for vision analysis")
        return {'columns': [], 'error': 'Anthropic SDK not available'}
    
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        logger.error("[PDF-VISION] ANTHROPIC_API_KEY not configured")
        return {'columns': [], 'error': 'API key not configured'}
    
    if not images:
        return {'columns': [], 'error': 'No images provided'}
    
    try:
        # Prepare images - redact PII if requested
        image_contents = []
        
        for idx, img in enumerate(images):
            if redact_pii:
                img = redact_image(img)
            
            # Convert to base64
            b64_data = image_to_base64(img, format='PNG')
            
            image_contents.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": b64_data
                }
            })
            
            logger.info(f"[PDF-VISION] Prepared page {idx + 1} for vision analysis")
        
        # Add the text prompt
        image_contents.append({
            "type": "text",
            "text": COLUMN_EXTRACTION_PROMPT
        })
        
        # Call Claude Vision API
        client = anthropic.Anthropic(api_key=api_key)
        
        logger.warning("[PDF-VISION] Calling Claude Vision API...")
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": image_contents
            }]
        )
        
        # Parse response
        response_text = response.content[0].text.strip()
        logger.info(f"[PDF-VISION] Raw response: {response_text[:500]}")
        
        # Parse JSON response
        try:
            # Clean up response if needed
            if response_text.startswith('```'):
                response_text = re.sub(r'^```json?\s*', '', response_text)
                response_text = re.sub(r'\s*```$', '', response_text)
            
            result = json.loads(response_text)
            
            columns = result.get('columns', [])
            description = result.get('table_description', '')
            confidence = result.get('confidence', 0.0)
            
            logger.warning(f"[PDF-VISION] Extracted {len(columns)} columns with {confidence:.0%} confidence")
            logger.warning(f"[PDF-VISION] Columns: {columns[:10]}{'...' if len(columns) > 10 else ''}")
            
            return {
                'columns': columns,
                'table_description': description,
                'confidence': confidence,
                'method': 'claude_vision',
                'success': True
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"[PDF-VISION] Failed to parse JSON response: {e}")
            logger.error(f"[PDF-VISION] Response was: {response_text[:500]}")
            return {
                'columns': [],
                'error': f'JSON parse error: {e}',
                'raw_response': response_text[:500]
            }
        
    except anthropic.APIError as e:
        logger.error(f"[PDF-VISION] Claude API error: {e}")
        return {'columns': [], 'error': f'API error: {e}'}
        
    except Exception as e:
        logger.error(f"[PDF-VISION] Vision analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {'columns': [], 'error': str(e)}


# Need json import
import json


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def get_pdf_table_structure(
    file_path: str,
    pages_to_analyze: List[int] = [0, 1],
    dpi: int = 150,
    redact_pii: bool = True
) -> Dict[str, Any]:
    """
    Extract table column structure from PDF using Claude Vision.
    
    This is the main entry point for vision-based PDF analysis.
    
    Args:
        file_path: Path to PDF file
        pages_to_analyze: Which pages to send to vision (default: first 2)
        dpi: Image resolution (default: 150)
        redact_pii: Whether to redact PII before sending (default: True)
        
    Returns:
        Dict containing:
        - columns: List of column names
        - table_description: Description of table contents
        - confidence: Extraction confidence (0-1)
        - success: Whether extraction succeeded
        - error: Error message if failed
    """
    logger.warning(f"[PDF-VISION] Analyzing {file_path}")
    
    # Step 1: Render pages to images
    images = render_pdf_pages_to_images(file_path, pages=pages_to_analyze, dpi=dpi)
    
    if not images:
        return {
            'columns': [],
            'success': False,
            'error': 'Failed to render PDF pages to images'
        }
    
    logger.warning(f"[PDF-VISION] Rendered {len(images)} pages")
    
    # Step 2: Extract columns using Claude Vision
    result = extract_columns_with_vision(images, redact_pii=redact_pii)
    
    return result


# =============================================================================
# FULL TABLE EXTRACTION - Vision for structure, text for data
# =============================================================================

def extract_table_data_from_text(
    text: str,
    columns: List[str],
    page_num: int = 0
) -> List[Dict[str, str]]:
    """
    Extract table rows from text using known column structure.
    
    This is the FAST path - no Vision API calls needed.
    Used for pages 3+ after Vision has identified columns from pages 1-2.
    
    Args:
        text: Raw text from PDF page
        columns: Known column names from Vision analysis
        page_num: For logging
        
    Returns:
        List of row dicts
    """
    rows = []
    
    if not text or not columns:
        return rows
    
    # Split into lines and look for data patterns
    lines = text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Skip obvious headers/footers
        if any(skip in line.lower() for skip in ['page ', 'continued', 'select:', 'last page']):
            continue
        
        # Split line into values - try multiple delimiters
        values = None
        for delimiter in ['\t', '  ', ' | ', '|']:
            parts = [p.strip() for p in line.split(delimiter) if p.strip()]
            if len(parts) >= len(columns) * 0.5:  # At least half the columns
                values = parts
                break
        
        if not values:
            # Try whitespace splitting with column count hint
            parts = line.split()
            if len(parts) >= 2:
                values = parts
        
        if values:
            row = {}
            for i, col in enumerate(columns):
                if i < len(values):
                    row[col] = values[i]
                else:
                    row[col] = ''
            
            # Only add if we got meaningful data
            if any(v for v in row.values()):
                rows.append(row)
    
    if rows:
        logger.info(f"[PDF-VISION] Page {page_num}: extracted {len(rows)} rows from text")
    
    return rows


def extract_tables_smart(
    file_path: str,
    dpi: int = 150,
    redact_pii: bool = True,
    status_callback = None
) -> Dict[str, Any]:
    """
    Smart PDF table extraction - Vision for structure, text for data.
    
    COST-EFFICIENT APPROACH:
    1. Render pages 1-2 to images
    2. Send to Vision to get column structure (~$0.04)
    3. Use pdfplumber text extraction for ALL pages
    4. Parse text using known column structure (free)
    
    Args:
        file_path: Path to PDF file
        dpi: Image resolution for Vision pages
        redact_pii: Always redact PII before sending to Claude
        status_callback: Optional callback for progress updates
        
    Returns:
        Dict with:
        - rows: List[Dict] - all extracted data
        - columns: List[str] - column names
        - page_count: int - pages processed
        - success: bool
        - error: str if failed
    """
    if not ANTHROPIC_AVAILABLE:
        return {
            'rows': [],
            'columns': [],
            'success': False,
            'error': 'Anthropic SDK not available'
        }
    
    if not PYPDFIUM_AVAILABLE:
        return {
            'rows': [],
            'columns': [],
            'success': False,
            'error': 'pypdfium2 not available for PDF rendering'
        }
    
    def update_status(msg):
        if status_callback:
            status_callback(msg)
        logger.warning(f"[PDF-VISION] {msg}")
    
    all_rows = []
    columns = []
    
    try:
        # Step 1: Get column structure from pages 1-2 using Vision
        update_status("Analyzing table structure with Vision AI (pages 1-2)...")
        
        structure_result = get_pdf_table_structure(
            file_path=file_path,
            pages_to_analyze=[0, 1],  # First 2 pages only
            dpi=dpi,
            redact_pii=redact_pii
        )
        
        if not structure_result.get('success') or not structure_result.get('columns'):
            return {
                'rows': [],
                'columns': [],
                'success': False,
                'error': structure_result.get('error', 'Vision could not detect table structure')
            }
        
        columns = structure_result['columns']
        confidence = structure_result.get('confidence', 0)
        description = structure_result.get('table_description', '')
        
        update_status(f"✓ Detected {len(columns)} columns ({confidence:.0%} confidence)")
        logger.warning(f"[PDF-VISION] Columns: {columns}")
        
        # Step 2: Extract text from ALL pages using pdfplumber (fast, free)
        update_status("Extracting data from all pages...")
        
        try:
            import pdfplumber
            
            with pdfplumber.open(file_path) as pdf:
                total_pages = len(pdf.pages)
                
                for page_idx, page in enumerate(pdf.pages):
                    try:
                        # Extract text from page
                        page_text = page.extract_text() or ''
                        
                        # Also try to get tables directly if pdfplumber can see them
                        tables = page.extract_tables()
                        
                        if tables:
                            # pdfplumber found tables - use those
                            for table in tables:
                                if not table or len(table) < 1:
                                    continue
                                
                                for row_data in table:
                                    if not row_data or not any(row_data):
                                        continue
                                    
                                    # Skip header-like rows
                                    row_text = ' '.join(str(c) for c in row_data if c)
                                    if 'Page' in row_text and 'of' in row_text:
                                        continue
                                    
                                    # Map to columns
                                    row = {}
                                    for i, col in enumerate(columns):
                                        if i < len(row_data) and row_data[i]:
                                            row[col] = str(row_data[i]).strip()
                                        else:
                                            row[col] = ''
                                    
                                    if any(v for v in row.values()):
                                        all_rows.append(row)
                        else:
                            # No tables found - parse text
                            page_rows = extract_table_data_from_text(
                                text=page_text,
                                columns=columns,
                                page_num=page_idx + 1
                            )
                            all_rows.extend(page_rows)
                        
                        # Progress update every 5 pages
                        if (page_idx + 1) % 5 == 0:
                            update_status(f"Processed {page_idx + 1}/{total_pages} pages, {len(all_rows)} rows")
                            
                    except Exception as page_error:
                        logger.warning(f"[PDF-VISION] Page {page_idx + 1} error: {page_error}")
                        continue
                
        except ImportError:
            return {
                'rows': [],
                'columns': columns,
                'success': False,
                'error': 'pdfplumber not available for text extraction'
            }
        
        update_status(f"✓ Complete: {len(all_rows)} rows from {total_pages} pages")
        
        return {
            'rows': all_rows,
            'columns': columns,
            'page_count': total_pages,
            'table_description': description,
            'confidence': confidence,
            'success': True
        }
        
    except Exception as e:
        logger.error(f"[PDF-VISION] Smart extraction failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'rows': all_rows,
            'columns': columns,
            'success': False,
            'error': str(e)
        }


# =============================================================================
# DOCUMENT STRUCTURE LEARNING
# =============================================================================

def get_document_fingerprint(text: str) -> str:
    """
    Generate a fingerprint for document type identification.
    
    Used to recognize similar documents and reuse learned structure.
    """
    import hashlib
    
    # Extract key identifiers from first 2000 chars
    sample = text[:2000].lower()
    
    # Look for document type indicators
    indicators = []
    
    # Common report titles
    title_patterns = [
        r'tax\s+verification',
        r'payroll\s+register',
        r'earnings\s+statement',
        r'benefits\s+summary',
        r'employee\s+roster',
        r'deduction\s+report',
        r'w-2\s+',
        r'1099\s+',
    ]
    
    for pattern in title_patterns:
        if re.search(pattern, sample):
            indicators.append(pattern.replace(r'\s+', '_'))
    
    # Look for column header patterns
    header_patterns = [
        r'tax\s+code',
        r'contribution\s+rate',
        r'effective\s+date',
        r'employee\s+id',
        r'gross\s+pay',
        r'net\s+pay',
        r'deduction',
        r'jurisdiction',
    ]
    
    for pattern in header_patterns:
        if re.search(pattern, sample):
            indicators.append(f"col:{pattern.replace(r's+', '_')}")
    
    # Create fingerprint from indicators
    if indicators:
        fingerprint = '|'.join(sorted(indicators))
        return hashlib.md5(fingerprint.encode()).hexdigest()[:16]
    
    # Fallback: hash first line (usually title)
    first_line = sample.split('\n')[0].strip()
    return hashlib.md5(first_line.encode()).hexdigest()[:16]


def store_learned_structure(
    fingerprint: str,
    columns: List[str],
    document_type: str = None,
    description: str = None
) -> bool:
    """
    Store learned document structure for future reuse.
    
    Saves to ChromaDB for semantic matching.
    """
    # TODO: Implement ChromaDB storage
    # For now, we'll use a simple file-based cache
    
    import json
    import os
    
    cache_dir = '/tmp/xlr8_doc_structures'
    os.makedirs(cache_dir, exist_ok=True)
    
    cache_file = os.path.join(cache_dir, f"{fingerprint}.json")
    
    try:
        data = {
            'fingerprint': fingerprint,
            'columns': columns,
            'document_type': document_type,
            'description': description,
            'created_at': datetime.now().isoformat()
        }
        
        with open(cache_file, 'w') as f:
            json.dump(data, f)
        
        logger.info(f"[PDF-VISION] Stored structure for fingerprint {fingerprint}")
        return True
        
    except Exception as e:
        logger.warning(f"[PDF-VISION] Failed to store structure: {e}")
        return False


def get_learned_structure(fingerprint: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve previously learned document structure.
    
    Returns None if not found.
    """
    import json
    import os
    
    cache_dir = '/tmp/xlr8_doc_structures'
    cache_file = os.path.join(cache_dir, f"{fingerprint}.json")
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, 'r') as f:
            data = json.load(f)
        
        logger.info(f"[PDF-VISION] Found cached structure for fingerprint {fingerprint}")
        return data
        
    except Exception as e:
        logger.warning(f"[PDF-VISION] Failed to load structure: {e}")
        return None


# Need datetime for cache timestamps
from datetime import datetime


# =============================================================================
# MAIN ENTRY POINT WITH LEARNING
# =============================================================================

def extract_all_tables_with_vision(
    file_path: str,
    dpi: int = 150,
    redact_pii: bool = True,
    max_pages: int = None,
    status_callback = None,
    use_learning: bool = True
) -> Dict[str, Any]:
    """
    Extract ALL table data from a PDF - smart approach with learning.
    
    FLOW:
    1. Extract sample text from PDF
    2. Generate document fingerprint
    3. Check if we've seen this document type before
       - YES: Use cached columns (FREE!)
       - NO: Send pages 1-2 to Vision (~$0.04)
    4. Extract all pages using text parsing with known columns
    5. Cache the structure for next time
    
    Args:
        file_path: Path to PDF file
        dpi: Image resolution for Vision pages (if needed)
        redact_pii: Always redact PII before sending to Claude
        max_pages: Optional limit on pages to process
        status_callback: Optional callback for progress updates
        use_learning: Whether to use/store learned structures (default True)
        
    Returns:
        Dict with:
        - rows: List[Dict] - all extracted data
        - columns: List[str] - column names  
        - page_count: int - pages processed
        - from_cache: bool - whether structure was cached
        - success: bool
        - error: str if failed
    """
    def update_status(msg):
        if status_callback:
            status_callback(msg)
        logger.warning(f"[PDF-VISION] {msg}")
    
    # Step 1: Try to use cached structure
    if use_learning:
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                # Get text from first 2 pages for fingerprinting
                sample_text = ''
                for i, page in enumerate(pdf.pages[:2]):
                    sample_text += (page.extract_text() or '') + '\n'
                
            if sample_text:
                fingerprint = get_document_fingerprint(sample_text)
                cached = get_learned_structure(fingerprint)
                
                if cached and cached.get('columns'):
                    update_status(f"✓ Using cached structure (fingerprint: {fingerprint[:8]}...)")
                    
                    # Fast path: use cached columns, extract all pages
                    columns = cached['columns']
                    all_rows = []
                    
                    with pdfplumber.open(file_path) as pdf:
                        total_pages = len(pdf.pages)
                        if max_pages:
                            total_pages = min(total_pages, max_pages)
                        
                        for page_idx in range(total_pages):
                            page = pdf.pages[page_idx]
                            
                            # Try tables first
                            tables = page.extract_tables()
                            if tables:
                                for table in tables:
                                    for row_data in (table or []):
                                        if not row_data or not any(row_data):
                                            continue
                                        row = {}
                                        for i, col in enumerate(columns):
                                            if i < len(row_data) and row_data[i]:
                                                row[col] = str(row_data[i]).strip()
                                            else:
                                                row[col] = ''
                                        if any(v for v in row.values()):
                                            all_rows.append(row)
                            else:
                                # Parse text
                                page_text = page.extract_text() or ''
                                page_rows = extract_table_data_from_text(page_text, columns, page_idx + 1)
                                all_rows.extend(page_rows)
                    
                    update_status(f"✓ Extracted {len(all_rows)} rows using cached structure")
                    
                    return {
                        'rows': all_rows,
                        'columns': columns,
                        'page_count': total_pages,
                        'from_cache': True,
                        'fingerprint': fingerprint,
                        'success': True
                    }
                    
        except Exception as e:
            logger.warning(f"[PDF-VISION] Cache lookup failed: {e}")
    
    # Step 2: No cache hit - use Vision for structure detection
    update_status("New document type - analyzing with Vision AI...")
    
    result = extract_tables_smart(
        file_path=file_path,
        dpi=dpi,
        redact_pii=redact_pii,
        status_callback=status_callback
    )
    
    # Step 3: Cache the structure for next time
    if use_learning and result.get('success') and result.get('columns'):
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                sample_text = ''
                for page in pdf.pages[:2]:
                    sample_text += (page.extract_text() or '') + '\n'
            
            if sample_text:
                fingerprint = get_document_fingerprint(sample_text)
                store_learned_structure(
                    fingerprint=fingerprint,
                    columns=result['columns'],
                    description=result.get('table_description', '')
                )
                result['fingerprint'] = fingerprint
                update_status(f"✓ Cached structure for future use (fingerprint: {fingerprint[:8]}...)")
                
        except Exception as e:
            logger.warning(f"[PDF-VISION] Failed to cache structure: {e}")
    
    result['from_cache'] = False
    return result
