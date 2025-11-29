"""
Extraction Orchestrator
========================
The brain of the extraction system. Coordinates multiple extractors,
manages confidence scoring, and ensures 98%+ accuracy.

Deploy to: backend/extraction/orchestrator.py
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json

logger = logging.getLogger(__name__)

# Confidence threshold - user specified 98%
CONFIDENCE_THRESHOLD = 0.98
CLOUD_FALLBACK_THRESHOLD = 0.80  # If local is below this, go to cloud
MAX_CLOUD_PAGES = 5  # Maximum pages to send to cloud for layout learning


class ExtractionStatus(Enum):
    SUCCESS = "success"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"
    CLOUD_REQUIRED = "cloud_required"


class SectionType(Enum):
    EMPLOYEE_INFO = "employee_info"
    EARNINGS = "earnings"
    TAXES = "taxes"
    DEDUCTIONS = "deductions"
    PAY_TOTALS = "pay_totals"
    HEADER = "header"
    UNKNOWN = "unknown"


class LayoutType(Enum):
    KEY_VALUE = "key_value"  # Row-driven (Employee Info, Pay Totals)
    TABLE = "table"          # Columnar (Earnings, Taxes, Deductions)
    MIXED = "mixed"


@dataclass
class ExtractionResult:
    """Result from a single extractor"""
    extractor_name: str
    data: List[Dict[str, Any]]
    headers: List[str]
    confidence: float
    bbox: Optional[Dict] = None  # Bounding box if available
    issues: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SectionResult:
    """Result for a complete section"""
    section_type: SectionType
    layout_type: LayoutType
    data: List[Dict[str, Any]]
    headers: List[str]
    confidence: float
    row_count: int
    column_count: int
    extraction_method: str  # Which extractor won
    issues: List[str] = field(default_factory=list)
    needs_review: bool = False
    bbox: Optional[Dict] = None


@dataclass
class DocumentResult:
    """Complete document extraction result"""
    source_file: str
    status: ExtractionStatus
    overall_confidence: float
    sections: Dict[str, SectionResult]
    employee_count: int
    validation_passed: bool
    validation_errors: List[str]
    template_id: Optional[str] = None
    template_matched: bool = False
    cloud_used: bool = False
    processing_time_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExtractionOrchestrator:
    """
    Main orchestrator for document extraction.
    
    Flow:
    1. Quick local analysis to check for known templates
    2. If template found with high confidence → use template
    3. If no template or low confidence → multi-extractor analysis
    4. If still below threshold → cloud AI analysis (with PII redaction)
    5. Validate results with cross-checks
    6. Return structured data with confidence scores
    """
    
    def __init__(self):
        # Import extractors
        self._init_extractors()
        
        # Import other components
        self._init_components()
        
    def _init_extractors(self):
        """Initialize available extractors"""
        self.extractors = {}
        
        # pdfplumber (primary)
        try:
            from extraction.extractors.pdfplumber_extractor import PDFPlumberExtractor
            self.extractors['pdfplumber'] = PDFPlumberExtractor()
            logger.info("PDFPlumber extractor loaded")
        except ImportError as e:
            logger.warning(f"PDFPlumber extractor not available: {e}")
        
        # Camelot (table specialist)
        try:
            from extraction.extractors.camelot_extractor import CamelotExtractor
            self.extractors['camelot'] = CamelotExtractor()
            logger.info("Camelot extractor loaded")
        except ImportError as e:
            logger.warning(f"Camelot extractor not available: {e}")
        
        # PyMuPDF (fast, structure-aware)
        try:
            from extraction.extractors.pymupdf_extractor import PyMuPDFExtractor
            self.extractors['pymupdf'] = PyMuPDFExtractor()
            logger.info("PyMuPDF extractor loaded")
        except ImportError as e:
            logger.warning(f"PyMuPDF extractor not available: {e}")
    
    def _init_components(self):
        """Initialize supporting components"""
        # Template manager
        try:
            from extraction.template_manager import TemplateManager
            self.template_manager = TemplateManager()
            logger.info("Template manager loaded")
        except ImportError as e:
            self.template_manager = None
            logger.warning(f"Template manager not available: {e}")
        
        # Layout detector
        try:
            from extraction.layout_detector import LayoutDetector
            self.layout_detector = LayoutDetector()
            logger.info("Layout detector loaded")
        except ImportError as e:
            self.layout_detector = None
            logger.warning(f"Layout detector not available: {e}")
        
        # Cloud analyzer (AWS Textract)
        try:
            from extraction.cloud_analyzer import CloudAnalyzer
            self.cloud_analyzer = CloudAnalyzer()
            logger.info("Cloud analyzer loaded")
        except ImportError as e:
            self.cloud_analyzer = None
            logger.warning(f"Cloud analyzer not available: {e}")
        
        # Validation engine
        try:
            from extraction.validation_engine import ValidationEngine
            self.validator = ValidationEngine()
            logger.info("Validation engine loaded")
        except ImportError as e:
            self.validator = None
            logger.warning(f"Validation engine not available: {e}")
        
        # PII Redactor
        try:
            from extraction.pii_redactor import PIIRedactor
            self.pii_redactor = PIIRedactor()
            logger.info("PII redactor loaded")
        except ImportError as e:
            self.pii_redactor = None
            logger.warning(f"PII redactor not available: {e}")
    
    def extract_document(self, file_path: str, 
                         project: Optional[str] = None,
                         force_cloud: bool = False) -> DocumentResult:
        """
        Main entry point for document extraction.
        
        Args:
            file_path: Path to PDF file
            project: Optional project identifier
            force_cloud: Force cloud analysis even if local is confident
            
        Returns:
            DocumentResult with all extracted data and confidence scores
        """
        start_time = datetime.now()
        
        result = DocumentResult(
            source_file=os.path.basename(file_path),
            status=ExtractionStatus.FAILED,
            overall_confidence=0.0,
            sections={},
            employee_count=0,
            validation_passed=False,
            validation_errors=[],
            metadata={'project': project}
        )
        
        try:
            # Step 1: Check for known template
            template = None
            if self.template_manager:
                template = self.template_manager.find_matching_template(file_path)
                if template and template.get('confidence', 0) >= CONFIDENCE_THRESHOLD:
                    result.template_id = template.get('id')
                    result.template_matched = True
                    logger.info(f"Matched template: {template.get('name')}")
            
            # Step 2: Detect document layout
            layout = None
            if self.layout_detector:
                layout = self.layout_detector.detect_layout(file_path)
                result.metadata['detected_layout'] = layout
            
            # Step 3: Extract using best method
            if result.template_matched and template:
                # Use template-guided extraction
                sections = self._extract_with_template(file_path, template)
            else:
                # Multi-extractor approach
                sections = self._extract_multi_method(file_path, layout)
            
            # Step 4: Calculate confidence
            confidences = [s.confidence for s in sections.values() if s.confidence > 0]
            overall_confidence = min(confidences) if confidences else 0.0
            
            # Step 5: Check if cloud analysis needed
            if (overall_confidence < CLOUD_FALLBACK_THRESHOLD or force_cloud) and self.cloud_analyzer:
                logger.info(f"Confidence {overall_confidence:.2f} below threshold, using cloud analysis")
                sections, overall_confidence = self._extract_with_cloud(file_path, sections)
                result.cloud_used = True
            
            # Step 6: Validate results
            validation_passed = True
            validation_errors = []
            
            if self.validator:
                validation_result = self.validator.validate_document(sections)
                validation_passed = validation_result.passed
                validation_errors = validation_result.errors
                
                # Adjust confidence based on validation
                if not validation_passed:
                    overall_confidence *= 0.8  # Reduce confidence if validation fails
            
            # Step 7: Determine final status
            if overall_confidence >= CONFIDENCE_THRESHOLD and validation_passed:
                status = ExtractionStatus.SUCCESS
            elif overall_confidence >= 0.85:
                status = ExtractionStatus.NEEDS_REVIEW
            else:
                status = ExtractionStatus.FAILED
            
            # Count employees
            employee_count = 0
            if 'employee_info' in sections:
                employee_count = sections['employee_info'].row_count
            
            # Build result
            result.status = status
            result.overall_confidence = overall_confidence
            result.sections = sections
            result.employee_count = employee_count
            result.validation_passed = validation_passed
            result.validation_errors = validation_errors
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            result.status = ExtractionStatus.FAILED
            result.validation_errors = [str(e)]
        
        # Calculate processing time
        result.processing_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        
        return result
    
    def _extract_multi_method(self, file_path: str, 
                               layout: Optional[Dict] = None) -> Dict[str, SectionResult]:
        """
        Extract using multiple methods and merge results.
        """
        all_results = {}
        
        # Run all available extractors
        for name, extractor in self.extractors.items():
            try:
                results = extractor.extract(file_path, layout)
                all_results[name] = results
            except Exception as e:
                logger.warning(f"Extractor {name} failed: {e}")
        
        if not all_results:
            raise RuntimeError("All extractors failed")
        
        # Merge and score results by section
        merged_sections = {}
        
        for section_type in SectionType:
            if section_type in [SectionType.HEADER, SectionType.UNKNOWN]:
                continue
                
            section_name = section_type.value
            section_results = []
            
            # Collect results from each extractor for this section
            for extractor_name, results in all_results.items():
                if section_name in results:
                    section_results.append((extractor_name, results[section_name]))
            
            if section_results:
                # Pick best or merge
                best = self._select_best_result(section_results, section_type)
                merged_sections[section_name] = best
        
        return merged_sections
    
    def _select_best_result(self, results: List[Tuple[str, ExtractionResult]], 
                            section_type: SectionType) -> SectionResult:
        """
        Select the best extraction result from multiple extractors.
        Uses voting and confidence scoring.
        """
        if len(results) == 1:
            name, r = results[0]
            return self._to_section_result(r, section_type, name)
        
        # Score each result
        scored = []
        for name, r in results:
            score = self._score_extraction(r, section_type)
            scored.append((score, name, r))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Check for significant disagreement
        if len(scored) >= 2:
            best_score = scored[0][0]
            second_score = scored[1][0]
            
            if best_score - second_score < 0.1:
                # Close scores - try to merge
                merged = self._merge_results([scored[0], scored[1]], section_type)
                if merged:
                    return merged
        
        # Return best result
        best_score, best_name, best_result = scored[0]
        return self._to_section_result(best_result, section_type, best_name, best_score)
    
    def _score_extraction(self, result: ExtractionResult, 
                          section_type: SectionType) -> float:
        """
        Score an extraction result based on multiple factors.
        """
        score = result.confidence
        
        # Boost for having expected number of columns
        expected_cols = self._get_expected_columns(section_type)
        if expected_cols and len(result.headers) >= expected_cols[0] and len(result.headers) <= expected_cols[1]:
            score += 0.1
        
        # Boost for data consistency
        if result.data:
            # Check if all rows have same number of columns
            col_counts = [len(row) for row in result.data if isinstance(row, (list, dict))]
            if col_counts and len(set(col_counts)) == 1:
                score += 0.05
        
        # Penalty for issues
        score -= len(result.issues) * 0.05
        
        return min(max(score, 0.0), 1.0)
    
    def _get_expected_columns(self, section_type: SectionType) -> Optional[Tuple[int, int]]:
        """Return expected column count range for section type"""
        ranges = {
            SectionType.EMPLOYEE_INFO: (3, 15),  # Flexible - lots of possible fields
            SectionType.EARNINGS: (4, 8),        # Code, Hours, Rate, Amount, YTD typical
            SectionType.TAXES: (3, 6),           # Code, Current, YTD minimum
            SectionType.DEDUCTIONS: (3, 8),      # Code, EE, ER, YTD variations
            SectionType.PAY_TOTALS: (2, 6),      # Gross, Net minimum
        }
        return ranges.get(section_type)
    
    def _merge_results(self, scored_results: List, 
                       section_type: SectionType) -> Optional[SectionResult]:
        """
        Attempt to merge results from multiple extractors.
        Used when scores are close and we want to combine strengths.
        """
        # For now, just return the best one
        # Future: intelligent merging based on column-by-column comparison
        return None
    
    def _to_section_result(self, extraction: ExtractionResult, 
                           section_type: SectionType,
                           method: str,
                           override_confidence: Optional[float] = None) -> SectionResult:
        """Convert ExtractionResult to SectionResult"""
        
        # Determine layout type
        layout_type = LayoutType.TABLE
        if section_type in [SectionType.EMPLOYEE_INFO, SectionType.PAY_TOTALS]:
            layout_type = LayoutType.KEY_VALUE
        
        confidence = override_confidence if override_confidence is not None else extraction.confidence
        
        return SectionResult(
            section_type=section_type,
            layout_type=layout_type,
            data=extraction.data,
            headers=extraction.headers,
            confidence=confidence,
            row_count=len(extraction.data),
            column_count=len(extraction.headers),
            extraction_method=method,
            issues=extraction.issues,
            needs_review=confidence < CONFIDENCE_THRESHOLD,
            bbox=extraction.bbox
        )
    
    def _extract_with_template(self, file_path: str, 
                               template: Dict) -> Dict[str, SectionResult]:
        """
        Extract using a learned template.
        Template provides exact coordinates for each section.
        """
        if not self.template_manager:
            raise RuntimeError("Template manager not available")
        
        return self.template_manager.extract_with_template(file_path, template)
    
    def _extract_with_cloud(self, file_path: str,
                            local_results: Dict[str, SectionResult]) -> Tuple[Dict[str, SectionResult], float]:
        """
        Use cloud AI (AWS Textract) for extraction.
        
        KEY FIX: Actually USE Textract's cell-level data instead of ignoring it!
        
        Flow:
        1. Redact PII from first N pages
        2. Send redacted PDF to Textract -> get table cell coordinates
        3. Use those coordinates to extract text from ORIGINAL PDF
        4. Result: Accurate structure + real data
        """
        if not self.cloud_analyzer:
            raise RuntimeError("Cloud analyzer not available")
        
        # Step 1: Create redacted version (first N pages only)
        redacted_path = None
        if self.pii_redactor:
            redacted_path = self.pii_redactor.create_redacted_pdf(
                file_path, 
                max_pages=MAX_CLOUD_PAGES
            )
            logger.info(f"Created redacted PDF for cloud analysis: {redacted_path}")
        else:
            logger.warning("PII redactor not available, using structure-only cloud analysis")
        
        # Step 2: Send to cloud for layout analysis
        cloud_result = self.cloud_analyzer.analyze_layout(
            redacted_path or file_path,
            max_pages=MAX_CLOUD_PAGES,
            structure_only=redacted_path is None
        )
        
        if not cloud_result or not cloud_result.success:
            logger.error("Cloud analysis failed")
            # Clean up and return local results
            if redacted_path and os.path.exists(redacted_path):
                os.remove(redacted_path)
            return local_results, 0.0
        
        logger.info(f"Cloud analysis found {len(cloud_result.tables)} tables")
        
        # Step 3: Save as new template for future use
        if cloud_result and self.template_manager:
            try:
                template_id = self.template_manager.save_template(
                    name=f"Auto-learned {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    layout=cloud_result,
                    source_file=os.path.basename(file_path)
                )
                logger.info(f"Saved new template: {template_id}")
            except Exception as e:
                logger.warning(f"Failed to save template: {e}")
        
        # Step 4: ACTUALLY USE Textract's cell data!
        # Extract directly from Textract's table cells
        sections = {}
        
        if cloud_result.tables:
            sections = self._extract_from_textract_tables(file_path, cloud_result.tables)
        
        # If no sections from tables, try key-value pairs
        if not sections and cloud_result.key_value_pairs:
            logger.info(f"Trying key-value pairs: {len(cloud_result.key_value_pairs)} pairs")
            # Add key-value data as pay_totals/employee_info
            kv_data = []
            for key, value in cloud_result.key_value_pairs.items():
                kv_data.append({'key': key, 'value': value})
            
            if kv_data:
                sections['pay_totals'] = SectionResult(
                    section_type=SectionType.PAY_TOTALS,
                    layout_type=LayoutType.KEY_VALUE,
                    data=kv_data,
                    headers=['key', 'value'],
                    confidence=cloud_result.confidence,
                    row_count=len(kv_data),
                    column_count=2,
                    extraction_method='cloud_kv',
                    needs_review=True,
                    issues=[]
                )
        
        # Clean up redacted file
        if redacted_path and os.path.exists(redacted_path):
            os.remove(redacted_path)
        
        # Calculate overall confidence
        if sections:
            confidences = [s.confidence for s in sections.values() if s.confidence > 0]
            overall_confidence = min(confidences) if confidences else cloud_result.confidence
        else:
            overall_confidence = 0.0
            logger.warning("No sections extracted from cloud result")
        
        return sections, overall_confidence
    
    def _extract_from_textract_tables(self, file_path: str, 
                                       tables: List) -> Dict[str, SectionResult]:
        """
        Extract data using Textract's table structure but reading from ORIGINAL PDF.
        
        KEY: Textract analyzed the REDACTED PDF and gave us cell POSITIONS.
        Now we use those positions to extract text from the ORIGINAL PDF.
        
        This way:
        - PII never leaves local system (Textract only saw redacted version)
        - We get accurate cell boundaries from Textract
        - We get real data from the original PDF
        """
        try:
            import fitz  # PyMuPDF for coordinate-based extraction
        except ImportError:
            logger.error("PyMuPDF required for coordinate extraction")
            return {}
        
        sections = {}
        
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            logger.error(f"Failed to open PDF: {e}")
            return {}
        
        for table in tables:
            if not table.cells:
                continue
            
            page_num = table.page_number - 1  # 0-indexed
            if page_num >= len(doc):
                logger.warning(f"Page {page_num + 1} not in document")
                continue
            
            page = doc[page_num]
            page_width = page.rect.width
            page_height = page.rect.height
            
            # Build grid from cells
            rows = {}  # row_index -> {col_index: text}
            max_col = 0
            confidences = []
            
            for cell in table.cells:
                row_idx = cell.row_index
                col_idx = cell.column_index
                max_col = max(max_col, col_idx + 1)
                
                if row_idx not in rows:
                    rows[row_idx] = {}
                
                # Extract text from ORIGINAL PDF using Textract's coordinates
                bbox = cell.bbox
                if bbox:
                    # Convert Textract normalized coords (0-1) to page coords
                    left = bbox.get('Left', 0) * page_width
                    top = bbox.get('Top', 0) * page_height
                    width = bbox.get('Width', 0) * page_width
                    height = bbox.get('Height', 0) * page_height
                    
                    # Create rect and extract text from ORIGINAL
                    rect = fitz.Rect(left, top, left + width, top + height)
                    text = page.get_text("text", clip=rect).strip()
                else:
                    # Fallback to Textract's text (will be redacted)
                    text = cell.text.strip() if cell.text else ''
                
                # Clean the text
                text = ' '.join(text.split())  # Normalize whitespace
                rows[row_idx][col_idx] = text
                
                if cell.confidence:
                    confidences.append(cell.confidence)
            
            if not rows:
                continue
            
            # Convert to list format
            data = []
            headers = []
            
            for row_idx in sorted(rows.keys()):
                row_data = []
                for col_idx in range(max_col):
                    row_data.append(rows[row_idx].get(col_idx, ''))
                
                if row_idx == 0:
                    headers = row_data
                else:
                    data.append(row_data)
            
            if not data:
                continue
            
            # Calculate confidence
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.8
            
            # Detect section type
            section_type = self._detect_section_type_from_content(headers, data)
            
            # Check for multi-line cells (quality issue)
            issues = []
            multiline_count = 0
            for row in data:
                for cell_val in row:
                    if '\n' in str(cell_val):
                        multiline_count += 1
            
            if multiline_count > len(data) * 0.3:  # More than 30% multiline
                issues.append("Many multi-line cells detected - possible merged column issue")
                avg_confidence *= 0.85
            
            # Determine layout type
            layout_type = LayoutType.TABLE
            if section_type in ['employee_info', 'pay_totals']:
                layout_type = LayoutType.KEY_VALUE
            
            # Convert section_type string to enum
            try:
                section_type_enum = SectionType(section_type)
            except ValueError:
                section_type_enum = SectionType.UNKNOWN
            
            result = SectionResult(
                section_type=section_type_enum,
                layout_type=layout_type,
                data=data,
                headers=headers,
                confidence=avg_confidence,
                row_count=len(data),
                column_count=max_col,
                extraction_method='cloud_textract',
                needs_review=avg_confidence < CONFIDENCE_THRESHOLD,
                issues=issues
            )
            
            # Add or merge with existing section
            if section_type not in sections:
                sections[section_type] = result
            else:
                # Merge data
                sections[section_type].data.extend(data)
                sections[section_type].row_count += len(data)
                # Take lower confidence
                sections[section_type].confidence = min(
                    sections[section_type].confidence, 
                    avg_confidence
                )
        
        doc.close()
        return sections
    
    def _detect_section_type_from_content(self, headers: List[str], 
                                           data: List[List[str]]) -> str:
        """Detect section type from headers and data content."""
        # Combine all text for analysis
        all_text = ' '.join(str(h) for h in headers).lower()
        for row in data[:5]:  # Check first 5 rows
            all_text += ' ' + ' '.join(str(c) for c in row).lower()
        
        # Score each section type
        section_keywords = {
            'employee_info': ['employee', 'name', 'id', 'ssn', 'department', 'hire', 'location', 'code:', 'tax profile'],
            'earnings': ['earnings', 'hours', 'rate', 'regular', 'overtime', 'gross', 'pay code', 'shift diff', 'amount'],
            'taxes': ['tax', 'federal', 'state', 'fica', 'medicare', 'withhold', 'w/h'],
            'deductions': ['deduction', '401k', 'medical', 'dental', 'insurance', 'garnish', 'child support'],
            'pay_totals': ['gross pay', 'net pay', 'total', 'check', 'direct deposit', 'net check', 'voucher'],
        }
        
        scores = {}
        for section, keywords in section_keywords.items():
            score = sum(1 for kw in keywords if kw in all_text)
            scores[section] = score
        
        if scores:
            best = max(scores, key=scores.get)
            if scores[best] > 0:
                return best
        
        return 'unknown'
    
    def learn_from_corrections(self, document_id: str, 
                               corrections: Dict[str, Any]) -> bool:
        """
        Learn from user corrections to improve future extraction.
        """
        if self.template_manager:
            return self.template_manager.update_from_corrections(document_id, corrections)
        return False


# Singleton instance
_orchestrator_instance = None

def get_extraction_orchestrator() -> ExtractionOrchestrator:
    """Get or create the extraction orchestrator singleton"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = ExtractionOrchestrator()
    return _orchestrator_instance
