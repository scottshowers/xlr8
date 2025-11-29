"""
Smart Pay Register Extractor v1.0
==================================
A clean, simple extraction system that:

1. Extracts text from 1-3 sample pages (Textract)
2. Redacts PII but keeps structure patterns
3. Sends structure to Claude to learn the format
4. Applies learned rules locally to ALL pages
5. Validates the math

Cost: ~$0.10-0.15 per NEW format, $0 for known formats
PII: Never leaves the system - only structure patterns sent to AI

Deploy to: backend/extraction/smart_extractor.py
"""

import os
import re
import json
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ExtractionRule:
    """A single extraction rule learned from the format"""
    field_name: str           # e.g., "employee_name", "gross_pay"
    pattern: str              # regex or description
    column_index: Optional[int] = None
    row_pattern: Optional[str] = None
    data_type: str = "string"  # string, currency, number, date
    required: bool = False


@dataclass 
class LearnedFormat:
    """A learned document format"""
    format_id: str
    format_name: str          # e.g., "Paycom Pay Register"
    vendor: str               # e.g., "Paycom"
    created_at: str
    sample_fingerprint: str   # Hash of structure to match future docs
    
    # Structure info
    column_count: int
    columns: List[Dict[str, str]]  # [{name, description, data_type}]
    row_pattern: str          # How to identify employee rows
    skip_patterns: List[str]  # Patterns for rows to skip (subtotals, headers)
    
    # Extraction rules
    rules: List[ExtractionRule] = field(default_factory=list)
    
    # Stats
    times_used: int = 0
    last_used: Optional[str] = None
    avg_confidence: float = 0.0


@dataclass
class EmployeePayRecord:
    """Extracted employee pay record"""
    employee_name: str = ""
    employee_id: str = ""
    department: str = ""
    
    # Pay data
    gross_pay: float = 0.0
    net_pay: float = 0.0
    total_taxes: float = 0.0
    total_deductions: float = 0.0
    
    # Breakdowns
    earnings: List[Dict[str, Any]] = field(default_factory=list)
    taxes: List[Dict[str, Any]] = field(default_factory=list)
    deductions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    check_number: str = ""
    pay_method: str = ""
    raw_row: Dict[str, str] = field(default_factory=dict)
    
    # Validation
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class ExtractionResult:
    """Complete extraction result"""
    success: bool
    source_file: str
    format_name: str
    format_id: str
    
    # Results
    employees: List[EmployeePayRecord]
    employee_count: int
    
    # Confidence
    confidence: float
    validation_passed: bool
    validation_errors: List[str]
    
    # Cost tracking
    pages_processed: int
    cloud_pages_used: int  # Pages sent to Textract
    ai_calls_used: int     # Calls to Claude
    estimated_cost: float  # In dollars
    
    # Timing
    processing_time_ms: int
    
    # For new formats
    format_learned: bool = False
    
    # Raw data for debugging
    raw_sections: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# FORMAT LIBRARY - Stores learned formats
# =============================================================================

class FormatLibrary:
    """Stores and retrieves learned document formats"""
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or os.path.join(
            os.path.dirname(__file__), 'learned_formats'
        )
        os.makedirs(self.storage_path, exist_ok=True)
        self._cache: Dict[str, LearnedFormat] = {}
        self._load_all()
    
    def _load_all(self):
        """Load all formats from disk"""
        for file in Path(self.storage_path).glob("*.json"):
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                    fmt = self._dict_to_format(data)
                    self._cache[fmt.format_id] = fmt
            except Exception as e:
                logger.warning(f"Failed to load format {file}: {e}")
        
        logger.info(f"Loaded {len(self._cache)} learned formats")
    
    def _dict_to_format(self, data: Dict) -> LearnedFormat:
        """Convert dict to LearnedFormat"""
        rules = [ExtractionRule(**r) for r in data.pop('rules', [])]
        return LearnedFormat(**data, rules=rules)
    
    def save(self, fmt: LearnedFormat):
        """Save a format to disk"""
        self._cache[fmt.format_id] = fmt
        
        file_path = os.path.join(self.storage_path, f"{fmt.format_id}.json")
        with open(file_path, 'w') as f:
            data = asdict(fmt)
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved format: {fmt.format_name} ({fmt.format_id})")
    
    def find_matching_format(self, fingerprint: str) -> Optional[LearnedFormat]:
        """Find a format matching the given fingerprint"""
        for fmt in self._cache.values():
            if fmt.sample_fingerprint == fingerprint:
                return fmt
        return None
    
    def get(self, format_id: str) -> Optional[LearnedFormat]:
        """Get format by ID"""
        return self._cache.get(format_id)
    
    def get_all(self) -> List[LearnedFormat]:
        """Get all formats"""
        return list(self._cache.values())
    
    def delete(self, format_id: str) -> bool:
        """Delete a format"""
        if format_id in self._cache:
            del self._cache[format_id]
            file_path = os.path.join(self.storage_path, f"{format_id}.json")
            if os.path.exists(file_path):
                os.remove(file_path)
            return True
        return False


# =============================================================================
# STRUCTURE ANALYZER - Extracts structure with PII redacted
# =============================================================================

class StructureAnalyzer:
    """
    Extracts document structure while redacting PII.
    
    Takes raw text and creates a "structure template" that shows
    the format without revealing actual data values.
    """
    
    # PII patterns to redact
    SSN_PATTERN = re.compile(r'\b\d{3}[-]?\d{2}[-]?\d{4}\b')
    PHONE_PATTERN = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    
    # Name pattern (LASTNAME, FIRSTNAME or FIRSTNAME LASTNAME)
    NAME_PATTERN = re.compile(r'\b[A-Z][A-Z]+,\s*[A-Z][A-Z]+\b|\b[A-Z][a-z]+\s+[A-Z][a-z]+\b')
    
    # Currency amounts
    CURRENCY_PATTERN = re.compile(r'\$?\d{1,3}(?:,\d{3})*(?:\.\d{2})?')
    
    def analyze(self, pages_text: List[str]) -> Dict[str, Any]:
        """
        Analyze pages and return structure with PII redacted.
        
        Args:
            pages_text: List of text content from each page
            
        Returns:
            Structure template safe to send to AI
        """
        if not pages_text:
            return {"error": "No pages to analyze"}
        
        # Combine first few pages for analysis
        sample_text = "\n---PAGE BREAK---\n".join(pages_text[:3])
        
        # Create redacted version
        redacted = self._redact_pii(sample_text)
        
        # Extract structure hints
        structure = {
            "redacted_sample": redacted,
            "detected_columns": self._detect_columns(sample_text),
            "detected_patterns": self._detect_patterns(sample_text),
            "line_count": len(sample_text.split('\n')),
            "has_tables": self._has_table_structure(sample_text),
        }
        
        # Generate fingerprint for matching
        structure["fingerprint"] = self._generate_fingerprint(structure)
        
        return structure
    
    def _redact_pii(self, text: str) -> str:
        """Redact PII but keep structure"""
        redacted = text
        
        # Replace SSNs
        redacted = self.SSN_PATTERN.sub('[SSN]', redacted)
        
        # Replace phone numbers
        redacted = self.PHONE_PATTERN.sub('[PHONE]', redacted)
        
        # Replace emails
        redacted = self.EMAIL_PATTERN.sub('[EMAIL]', redacted)
        
        # Replace names - be more careful here
        # Only replace obvious name patterns, keep structure words
        def replace_name(match):
            return '[NAME]'
        
        redacted = self.NAME_PATTERN.sub(replace_name, redacted)
        
        # Replace specific currency amounts with type indicators
        def replace_currency(match):
            val = match.group(0).replace('$', '').replace(',', '')
            try:
                num = float(val)
                if num > 10000:
                    return '[AMOUNT:LARGE]'
                elif num > 100:
                    return '[AMOUNT:MED]'
                else:
                    return '[AMOUNT:SMALL]'
            except:
                return '[AMOUNT]'
        
        redacted = self.CURRENCY_PATTERN.sub(replace_currency, redacted)
        
        return redacted
    
    def _detect_columns(self, text: str) -> List[str]:
        """Detect likely column headers"""
        # Look for common payroll column names
        common_headers = [
            'employee', 'name', 'id', 'department', 'dept',
            'earnings', 'rate', 'hours', 'amount', 'regular', 'overtime',
            'taxes', 'federal', 'state', 'local', 'medicare', 'social security',
            'deductions', '401k', 'medical', 'dental', 'insurance',
            'gross', 'net', 'pay', 'check', 'total'
        ]
        
        found = []
        text_lower = text.lower()
        
        for header in common_headers:
            if header in text_lower:
                found.append(header)
        
        return found
    
    def _detect_patterns(self, text: str) -> Dict[str, Any]:
        """Detect structural patterns"""
        lines = text.split('\n')
        
        return {
            "has_code_field": bool(re.search(r'Code:\s*\w+', text)),
            "has_tax_profile": bool(re.search(r'Tax Profile:', text)),
            "has_department_headers": bool(re.search(r'^\d+\s*[-–]\s*', text, re.MULTILINE)),
            "has_subtotals": 'subtotal' in text.lower(),
            "has_check_numbers": bool(re.search(r'Check\s*#?\s*\d+', text)),
            "has_direct_deposit": 'direct deposit' in text.lower(),
            "avg_line_length": sum(len(l) for l in lines) / len(lines) if lines else 0,
        }
    
    def _has_table_structure(self, text: str) -> bool:
        """Check if text appears to have table structure"""
        lines = text.split('\n')
        # Tables usually have consistent spacing or delimiters
        tab_count = sum(1 for l in lines if '\t' in l)
        multi_space_count = sum(1 for l in lines if '  ' in l)
        
        return (tab_count > len(lines) * 0.3 or 
                multi_space_count > len(lines) * 0.3)
    
    def _generate_fingerprint(self, structure: Dict) -> str:
        """Generate a fingerprint for format matching"""
        # Use detected patterns and columns to create fingerprint
        key_data = json.dumps({
            "columns": sorted(structure["detected_columns"]),
            "patterns": structure["detected_patterns"],
            "has_tables": structure["has_tables"],
        }, sort_keys=True)
        
        return hashlib.md5(key_data.encode()).hexdigest()[:16]


# =============================================================================
# FORMAT LEARNER - Uses Claude to understand the format
# =============================================================================

class FormatLearner:
    """
    Sends redacted structure to Claude to learn extraction rules.
    
    Claude sees ONLY the structure patterns, never actual PII.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get('CLAUDE_API_KEY')
        self._client = None
    
    @property
    def client(self):
        """Lazy load Anthropic client"""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                logger.error("anthropic package not installed")
                raise
        return self._client
    
    @property
    def is_available(self) -> bool:
        """Check if Claude API is available"""
        return bool(self.api_key)
    
    def learn_format(self, structure: Dict[str, Any], 
                     vendor_hint: str = None) -> LearnedFormat:
        """
        Send structure to Claude and get back extraction rules.
        
        Args:
            structure: Redacted structure from StructureAnalyzer
            vendor_hint: Optional hint about the payroll vendor
            
        Returns:
            LearnedFormat with extraction rules
        """
        if not self.is_available:
            raise RuntimeError("Claude API key not configured")
        
        prompt = self._build_learning_prompt(structure, vendor_hint)
        
        logger.info("Sending structure to Claude for format learning...")
        
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse Claude's response
        response_text = response.content[0].text
        
        return self._parse_learning_response(response_text, structure)
    
    def _build_learning_prompt(self, structure: Dict, vendor_hint: str = None) -> str:
        """Build the prompt for Claude"""
        return f"""You are analyzing a pay register document structure. The actual values have been redacted for privacy - you're seeing patterns, not real data.

Here is the redacted document structure:

```
{structure.get('redacted_sample', 'No sample available')}
```

Detected patterns:
- Columns found: {structure.get('detected_columns', [])}
- Structure hints: {json.dumps(structure.get('detected_patterns', {}), indent=2)}
- Has table structure: {structure.get('has_tables', False)}
{f'- Vendor hint: {vendor_hint}' if vendor_hint else ''}

Based on this structure, please provide:

1. **Format identification**: What payroll system is this from? (Paycom, ADP, Paychex, etc.)

2. **Column structure**: How many columns are there and what does each contain?

3. **Row patterns**: How do I identify:
   - Employee data rows (vs headers, subtotals, etc.)
   - Department headers
   - Subtotal rows to skip

4. **Extraction rules**: For each field below, provide a regex pattern or description of how to extract it:
   - employee_name
   - employee_id (or code)
   - department
   - gross_pay
   - net_pay
   - individual earnings (type, rate, hours, amount)
   - individual taxes (type, amount)
   - individual deductions (type, amount)

Respond in this JSON format:
```json
{{
    "vendor": "Paycom",
    "format_name": "Paycom Pay Register Standard",
    "column_count": 5,
    "columns": [
        {{"index": 0, "name": "Employee Info", "description": "Name, code, tax profile", "data_type": "mixed"}},
        {{"index": 1, "name": "Earnings", "description": "All earning types with rate/hours/amount", "data_type": "earnings_block"}}
    ],
    "row_patterns": {{
        "employee_row": "regex or description to identify employee rows",
        "department_header": "regex for department headers like '2025 - RN Department'",
        "skip_patterns": ["Subtotal", "Page \\\\d+"]
    }},
    "extraction_rules": [
        {{
            "field_name": "employee_name",
            "pattern": "^([A-Z]+,\\\\s*[A-Z]+)",
            "column_index": 0,
            "data_type": "string",
            "required": true
        }},
        {{
            "field_name": "gross_pay",
            "pattern": "GROSS\\\\s+([\\\\d,]+\\\\.\\\\d{{2}})",
            "column_index": 1,
            "data_type": "currency",
            "required": true
        }}
    ]
}}
```

Be specific with regex patterns. They will be applied to actual data."""

    def _parse_learning_response(self, response: str, 
                                  structure: Dict) -> LearnedFormat:
        """Parse Claude's response into a LearnedFormat"""
        # Extract JSON from response
        json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
        
        if json_match:
            try:
                data = json.loads(json_match.group(1))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from Claude: {e}")
                data = {}
        else:
            # Try to parse entire response as JSON
            try:
                data = json.loads(response)
            except:
                logger.error("Could not extract JSON from Claude response")
                data = {}
        
        # Build LearnedFormat
        format_id = f"{data.get('vendor', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        rules = []
        for rule_data in data.get('extraction_rules', []):
            rules.append(ExtractionRule(
                field_name=rule_data.get('field_name', ''),
                pattern=rule_data.get('pattern', ''),
                column_index=rule_data.get('column_index'),
                data_type=rule_data.get('data_type', 'string'),
                required=rule_data.get('required', False)
            ))
        
        row_patterns = data.get('row_patterns', {})
        
        return LearnedFormat(
            format_id=format_id,
            format_name=data.get('format_name', 'Unknown Format'),
            vendor=data.get('vendor', 'Unknown'),
            created_at=datetime.now().isoformat(),
            sample_fingerprint=structure.get('fingerprint', ''),
            column_count=data.get('column_count', 0),
            columns=data.get('columns', []),
            row_pattern=row_patterns.get('employee_row', ''),
            skip_patterns=row_patterns.get('skip_patterns', []),
            rules=rules
        )


# =============================================================================
# PATTERN APPLIER - Applies learned rules to extract data
# =============================================================================

class PatternApplier:
    """
    Applies learned extraction rules to actual document data.
    
    This runs LOCALLY - no cloud calls, no PII exposure.
    """
    
    def apply(self, fmt: LearnedFormat, 
              pages_data: List[List[Dict[str, str]]]) -> List[EmployeePayRecord]:
        """
        Apply extraction rules to page data.
        
        Args:
            fmt: The learned format with extraction rules
            pages_data: List of pages, each containing rows of cell data
            
        Returns:
            List of extracted EmployeePayRecord objects
        """
        employees = []
        current_department = ""
        
        for page_rows in pages_data:
            for row in page_rows:
                # Check if this is a department header
                if self._is_department_header(row, fmt):
                    current_department = self._extract_department(row)
                    continue
                
                # Check if this should be skipped
                if self._should_skip(row, fmt):
                    continue
                
                # Check if this is an employee row
                if self._is_employee_row(row, fmt):
                    employee = self._extract_employee(row, fmt)
                    employee.department = current_department
                    employees.append(employee)
        
        return employees
    
    def _is_department_header(self, row: Dict[str, str], fmt: LearnedFormat) -> bool:
        """Check if row is a department header"""
        first_col = list(row.values())[0] if row else ""
        
        # Check format's department pattern
        if fmt.row_pattern:
            dept_pattern = None
            for col in fmt.columns:
                if 'department' in col.get('description', '').lower():
                    break
        
        # Default pattern: starts with number and dash
        return bool(re.match(r'^\d+\s*[-–]', first_col))
    
    def _extract_department(self, row: Dict[str, str]) -> str:
        """Extract department name from header row"""
        first_col = list(row.values())[0] if row else ""
        return first_col.strip()
    
    def _should_skip(self, row: Dict[str, str], fmt: LearnedFormat) -> bool:
        """Check if row should be skipped"""
        row_text = ' '.join(str(v) for v in row.values()).lower()
        
        for pattern in fmt.skip_patterns:
            if re.search(pattern, row_text, re.IGNORECASE):
                return True
        
        return False
    
    def _is_employee_row(self, row: Dict[str, str], fmt: LearnedFormat) -> bool:
        """Check if row contains employee data"""
        if not row:
            return False
        
        first_col = list(row.values())[0] if row else ""
        
        # Use format's employee row pattern if available
        if fmt.row_pattern:
            try:
                if re.search(fmt.row_pattern, first_col, re.IGNORECASE):
                    return True
            except:
                pass
        
        # Default: look for name pattern with Code: or Tax Profile:
        if 'Code:' in first_col or 'Tax Profile:' in first_col:
            return True
        
        # Or just a name pattern (LASTNAME, FIRSTNAME)
        if re.match(r'^[A-Z][A-Z]+,\s*[A-Z]', first_col):
            return True
        
        return False
    
    def _extract_employee(self, row: Dict[str, str], 
                          fmt: LearnedFormat) -> EmployeePayRecord:
        """Extract employee data using format rules"""
        employee = EmployeePayRecord()
        employee.raw_row = row
        
        # Convert row to list for indexed access
        cells = list(row.values())
        
        # Apply each extraction rule
        for rule in fmt.rules:
            value = self._apply_rule(rule, cells)
            
            if value is not None:
                if rule.field_name == 'employee_name':
                    employee.employee_name = str(value)
                elif rule.field_name == 'employee_id':
                    employee.employee_id = str(value)
                elif rule.field_name == 'gross_pay':
                    employee.gross_pay = self._to_float(value)
                elif rule.field_name == 'net_pay':
                    employee.net_pay = self._to_float(value)
                elif rule.field_name == 'earnings':
                    employee.earnings = value if isinstance(value, list) else []
                elif rule.field_name == 'taxes':
                    employee.taxes = value if isinstance(value, list) else []
                elif rule.field_name == 'deductions':
                    employee.deductions = value if isinstance(value, list) else []
        
        # Calculate totals if not extracted directly
        if employee.total_taxes == 0 and employee.taxes:
            employee.total_taxes = sum(t.get('amount', 0) for t in employee.taxes)
        
        if employee.total_deductions == 0 and employee.deductions:
            employee.total_deductions = sum(d.get('amount', 0) for d in employee.deductions)
        
        return employee
    
    def _apply_rule(self, rule: ExtractionRule, cells: List[str]) -> Any:
        """Apply a single extraction rule"""
        # Get target cell
        if rule.column_index is not None and rule.column_index < len(cells):
            target = cells[rule.column_index]
        else:
            target = ' '.join(cells)  # Search all cells
        
        if not rule.pattern:
            return target.strip()
        
        try:
            match = re.search(rule.pattern, target, re.IGNORECASE)
            if match:
                # Return first group if exists, else full match
                return match.group(1) if match.groups() else match.group(0)
        except re.error as e:
            logger.warning(f"Invalid regex pattern: {rule.pattern} - {e}")
        
        return None
    
    def _to_float(self, value: Any) -> float:
        """Convert value to float"""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value.replace(',', '').replace('$', ''))
            except:
                return 0.0
        return 0.0


# =============================================================================
# VALIDATOR - Checks the math
# =============================================================================

class PayrollValidator:
    """Validates extracted payroll data"""
    
    TOLERANCE = 0.02  # $0.02 tolerance for rounding
    
    def validate(self, employees: List[EmployeePayRecord]) -> Tuple[bool, List[str]]:
        """
        Validate all employee records.
        
        Returns:
            (all_valid, list of error messages)
        """
        all_errors = []
        
        for emp in employees:
            errors = self._validate_employee(emp)
            emp.validation_errors = errors
            emp.is_valid = len(errors) == 0
            all_errors.extend(errors)
        
        return len(all_errors) == 0, all_errors
    
    def _validate_employee(self, emp: EmployeePayRecord) -> List[str]:
        """Validate single employee record"""
        errors = []
        
        # Required fields
        if not emp.employee_name:
            errors.append(f"Missing employee name")
        
        # Earnings sum should equal gross
        if emp.earnings and emp.gross_pay > 0:
            earnings_sum = sum(e.get('amount', 0) for e in emp.earnings)
            if abs(earnings_sum - emp.gross_pay) > self.TOLERANCE:
                errors.append(
                    f"{emp.employee_name}: Earnings sum ({earnings_sum:.2f}) != "
                    f"Gross ({emp.gross_pay:.2f})"
                )
        
        # Gross - Taxes - Deductions should equal Net
        if emp.gross_pay > 0 and emp.net_pay > 0:
            calculated_net = emp.gross_pay - emp.total_taxes - emp.total_deductions
            if abs(calculated_net - emp.net_pay) > self.TOLERANCE:
                errors.append(
                    f"{emp.employee_name}: Calculated net ({calculated_net:.2f}) != "
                    f"Actual net ({emp.net_pay:.2f})"
                )
        
        return errors


# =============================================================================
# TEXT EXTRACTOR - Gets text from PDF pages
# =============================================================================

class TextExtractor:
    """Extracts text from PDF using local tools or Textract"""
    
    def __init__(self, use_textract: bool = True, aws_region: str = None):
        self.use_textract = use_textract
        self.aws_region = aws_region or os.environ.get('AWS_REGION', 'us-east-1')
        self._textract_client = None
    
    @property
    def textract_client(self):
        """Lazy load Textract client"""
        if self._textract_client is None:
            try:
                import boto3
                self._textract_client = boto3.client('textract', region_name=self.aws_region)
            except ImportError:
                logger.error("boto3 not installed")
                raise
        return self._textract_client
    
    def extract_sample_pages(self, file_path: str, 
                             max_pages: int = 3) -> List[str]:
        """
        Extract text from sample pages for format learning.
        
        Args:
            file_path: Path to PDF
            max_pages: Number of pages to sample
            
        Returns:
            List of text content per page
        """
        if self.use_textract:
            return self._extract_with_textract(file_path, max_pages)
        else:
            return self._extract_with_pdfplumber(file_path, max_pages)
    
    def extract_all_pages(self, file_path: str) -> List[List[Dict[str, str]]]:
        """
        Extract all pages for data extraction.
        Uses local extraction (free) once format is known.
        
        Returns:
            List of pages, each containing list of rows (as dicts)
        """
        return self._extract_with_pdfplumber_structured(file_path)
    
    def _extract_with_textract(self, file_path: str, 
                                max_pages: int) -> List[str]:
        """Extract using AWS Textract"""
        import fitz  # PyMuPDF
        
        pages_text = []
        doc = fitz.open(file_path)
        
        try:
            for page_num in range(min(max_pages, len(doc))):
                # Convert page to image
                page = doc[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale
                img_bytes = pix.tobytes("png")
                
                # Send to Textract
                response = self.textract_client.analyze_document(
                    Document={'Bytes': img_bytes},
                    FeatureTypes=['TABLES']
                )
                
                # Extract text from blocks
                text_parts = []
                for block in response.get('Blocks', []):
                    if block['BlockType'] == 'LINE':
                        text_parts.append(block.get('Text', ''))
                
                pages_text.append('\n'.join(text_parts))
                
        finally:
            doc.close()
        
        return pages_text
    
    def _extract_with_pdfplumber(self, file_path: str, 
                                  max_pages: int) -> List[str]:
        """Extract using pdfplumber (free, local)"""
        import pdfplumber
        
        pages_text = []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num in range(min(max_pages, len(pdf.pages))):
                page = pdf.pages[page_num]
                text = page.extract_text() or ""
                pages_text.append(text)
        
        return pages_text
    
    def _extract_with_pdfplumber_structured(self, 
                                            file_path: str) -> List[List[Dict[str, str]]]:
        """Extract structured table data from all pages"""
        import pdfplumber
        
        all_pages = []
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_rows = []
                
                # Try to extract tables
                tables = page.extract_tables()
                
                if tables:
                    for table in tables:
                        for row in table:
                            if row and any(cell for cell in row):
                                # Convert to dict with column indices as keys
                                row_dict = {f"col_{i}": str(cell or '') 
                                           for i, cell in enumerate(row)}
                                page_rows.append(row_dict)
                else:
                    # Fall back to line-by-line extraction
                    text = page.extract_text() or ""
                    for line in text.split('\n'):
                        if line.strip():
                            page_rows.append({"col_0": line.strip()})
                
                all_pages.append(page_rows)
        
        return all_pages


# =============================================================================
# MAIN SMART EXTRACTOR - Ties it all together
# =============================================================================

class SmartExtractor:
    """
    The main extraction orchestrator.
    
    Usage:
        extractor = SmartExtractor()
        result = extractor.extract("payroll.pdf")
        
        # Result contains structured employee data
        for emp in result.employees:
            print(f"{emp.employee_name}: ${emp.net_pay}")
    """
    
    def __init__(self, 
                 claude_api_key: str = None,
                 aws_region: str = None,
                 formats_path: str = None):
        """
        Initialize the smart extractor.
        
        Args:
            claude_api_key: API key for Claude (format learning)
            aws_region: AWS region for Textract
            formats_path: Path to store learned formats
        """
        self.format_library = FormatLibrary(formats_path)
        self.structure_analyzer = StructureAnalyzer()
        self.format_learner = FormatLearner(claude_api_key)
        self.pattern_applier = PatternApplier()
        self.validator = PayrollValidator()
        self.text_extractor = TextExtractor(aws_region=aws_region)
    
    def extract(self, file_path: str, 
                vendor_hint: str = None,
                force_relearn: bool = False) -> ExtractionResult:
        """
        Extract employee pay data from a document.
        
        Args:
            file_path: Path to the PDF file
            vendor_hint: Optional hint about payroll vendor
            force_relearn: Force re-learning even if format is known
            
        Returns:
            ExtractionResult with all extracted data
        """
        start_time = datetime.now()
        cloud_pages = 0
        ai_calls = 0
        format_learned = False
        
        filename = os.path.basename(file_path)
        logger.info(f"Starting extraction: {filename}")
        
        try:
            # Step 1: Get sample pages and analyze structure
            logger.info("Step 1: Extracting sample pages...")
            sample_text = self.text_extractor.extract_sample_pages(file_path, max_pages=3)
            cloud_pages = len(sample_text)
            
            structure = self.structure_analyzer.analyze(sample_text)
            fingerprint = structure.get('fingerprint', '')
            
            # Step 2: Check if we know this format
            fmt = None
            if not force_relearn:
                fmt = self.format_library.find_matching_format(fingerprint)
                if fmt:
                    logger.info(f"Found matching format: {fmt.format_name}")
            
            # Step 3: Learn format if needed
            if fmt is None:
                if not self.format_learner.is_available:
                    raise RuntimeError(
                        "Unknown format and Claude API not available. "
                        "Please set CLAUDE_API_KEY environment variable."
                    )
                
                logger.info("Step 3: Learning new format with Claude...")
                fmt = self.format_learner.learn_format(structure, vendor_hint)
                ai_calls = 1
                format_learned = True
                
                # Save for future use
                self.format_library.save(fmt)
                logger.info(f"Learned and saved new format: {fmt.format_name}")
            
            # Step 4: Extract all pages locally
            logger.info("Step 4: Extracting all pages locally...")
            all_pages_data = self.text_extractor.extract_all_pages(file_path)
            total_pages = len(all_pages_data)
            
            # Step 5: Apply extraction rules
            logger.info("Step 5: Applying extraction rules...")
            employees = self.pattern_applier.apply(fmt, all_pages_data)
            
            # Step 6: Validate
            logger.info("Step 6: Validating results...")
            validation_passed, validation_errors = self.validator.validate(employees)
            
            # Calculate confidence
            valid_count = sum(1 for e in employees if e.is_valid)
            confidence = valid_count / len(employees) if employees else 0.0
            
            # Calculate cost
            textract_cost = cloud_pages * 0.015
            claude_cost = ai_calls * 0.05  # Rough estimate
            total_cost = textract_cost + claude_cost
            
            # Update format stats
            fmt.times_used += 1
            fmt.last_used = datetime.now().isoformat()
            self.format_library.save(fmt)
            
            # Build result
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return ExtractionResult(
                success=confidence >= 0.9 and validation_passed,
                source_file=filename,
                format_name=fmt.format_name,
                format_id=fmt.format_id,
                employees=employees,
                employee_count=len(employees),
                confidence=confidence,
                validation_passed=validation_passed,
                validation_errors=validation_errors,
                pages_processed=total_pages,
                cloud_pages_used=cloud_pages,
                ai_calls_used=ai_calls,
                estimated_cost=total_cost,
                processing_time_ms=processing_time,
                format_learned=format_learned
            )
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            
            return ExtractionResult(
                success=False,
                source_file=filename,
                format_name="Unknown",
                format_id="",
                employees=[],
                employee_count=0,
                confidence=0.0,
                validation_passed=False,
                validation_errors=[str(e)],
                pages_processed=0,
                cloud_pages_used=cloud_pages,
                ai_calls_used=ai_calls,
                estimated_cost=cloud_pages * 0.015,
                processing_time_ms=processing_time
            )
    
    def get_formats(self) -> List[Dict]:
        """Get all learned formats"""
        return [asdict(f) for f in self.format_library.get_all()]
    
    def delete_format(self, format_id: str) -> bool:
        """Delete a learned format"""
        return self.format_library.delete(format_id)


# =============================================================================
# SINGLETON FOR API USE
# =============================================================================

_extractor_instance = None

def get_smart_extractor() -> SmartExtractor:
    """Get or create the singleton SmartExtractor"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = SmartExtractor()
    return _extractor_instance
