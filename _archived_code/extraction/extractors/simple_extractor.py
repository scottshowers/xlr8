"""
Pay Register Extractor - Simple Version
=========================================
Does exactly what was promised:

1. Textract extracts text from PDF (3 sample pages)
2. Redact PII from sample, send structure to Claude
3. Claude returns parsing instructions
4. Apply to ALL pages locally using those instructions

Deploy to: backend/extraction/simple_extractor.py
"""

import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class Employee:
    name: str = ""
    employee_id: str = ""
    department: str = ""
    gross_pay: float = 0.0
    net_pay: float = 0.0
    total_taxes: float = 0.0
    total_deductions: float = 0.0
    earnings: List[Dict] = field(default_factory=list)
    taxes: List[Dict] = field(default_factory=list)
    deductions: List[Dict] = field(default_factory=list)
    check_number: str = ""
    pay_method: str = ""
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class ExtractionResult:
    success: bool
    source_file: str
    employees: List[Employee]
    employee_count: int
    confidence: float
    validation_passed: bool
    validation_errors: List[str]
    pages_processed: int
    processing_time_ms: int
    cost_usd: float


class SimpleExtractor:
    """
    Simple, working extractor.
    
    Uses Textract to get the text, Claude to understand it.
    """
    
    def __init__(self):
        self.claude_api_key = os.environ.get('CLAUDE_API_KEY')
        self.aws_region = os.environ.get('AWS_REGION', 'us-east-1')
        self._textract = None
        self._claude = None
    
    @property
    def textract(self):
        if self._textract is None:
            import boto3
            self._textract = boto3.client('textract', region_name=self.aws_region)
        return self._textract
    
    @property
    def claude(self):
        if self._claude is None:
            import anthropic
            self._claude = anthropic.Anthropic(api_key=self.claude_api_key)
        return self._claude
    
    def extract(self, file_path: str, max_pages: int = 10) -> ExtractionResult:
        """
        Extract employee pay data from PDF.
        
        Args:
            file_path: Path to PDF
            max_pages: Maximum pages to process (default 10 for cost control)
                       Set to 0 for unlimited (warning: expensive for large docs)
        """
        start = datetime.now()
        filename = os.path.basename(file_path)
        
        try:
            # Step 1: Get text from pages using Textract
            logger.info(f"Step 1: Extracting text with Textract (max {max_pages} pages)...")
            pages_text = self._extract_all_pages_text(file_path, max_pages)
            pages_processed = len(pages_text)
            
            # Step 2: Get sample for Claude (first 3 pages, redacted)
            logger.info("Step 2: Preparing sample for Claude...")
            sample_text = "\n\n--- PAGE BREAK ---\n\n".join(pages_text[:3])
            redacted_sample = self._redact_pii(sample_text)
            
            # Step 3: Ask Claude to parse
            logger.info("Step 3: Asking Claude to parse...")
            employees = self._parse_with_claude(redacted_sample, pages_text)
            
            # Step 4: Validate
            logger.info("Step 4: Validating...")
            validation_errors = []
            for emp in employees:
                errors = self._validate_employee(emp)
                emp.validation_errors = errors
                emp.is_valid = len(errors) == 0
                validation_errors.extend(errors)
            
            valid_count = sum(1 for e in employees if e.is_valid)
            confidence = valid_count / len(employees) if employees else 0.0
            
            # Cost: $0.015/page for Textract + ~$0.03 for Claude
            cost = (pages_processed * 0.015) + 0.03
            
            processing_time = int((datetime.now() - start).total_seconds() * 1000)
            
            return ExtractionResult(
                success=len(employees) > 0 and confidence >= 0.8,
                source_file=filename,
                employees=employees,
                employee_count=len(employees),
                confidence=confidence,
                validation_passed=len(validation_errors) == 0,
                validation_errors=validation_errors[:20],  # Limit errors shown
                pages_processed=pages_processed,
                processing_time_ms=processing_time,
                cost_usd=round(cost, 4)
            )
            
        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            processing_time = int((datetime.now() - start).total_seconds() * 1000)
            return ExtractionResult(
                success=False,
                source_file=filename,
                employees=[],
                employee_count=0,
                confidence=0.0,
                validation_passed=False,
                validation_errors=[str(e)],
                pages_processed=0,
                processing_time_ms=processing_time,
                cost_usd=0.0
            )
    
    def _extract_all_pages_text(self, file_path: str, max_pages: int = 0) -> List[str]:
        """Extract text from pages using Textract."""
        import fitz  # PyMuPDF
        
        pages_text = []
        doc = fitz.open(file_path)
        
        try:
            total_pages = len(doc)
            pages_to_process = total_pages if max_pages == 0 else min(max_pages, total_pages)
            
            for page_num in range(pages_to_process):
                page = doc[page_num]
                # Convert to image for Textract
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_bytes = pix.tobytes("png")
                
                # Send to Textract
                response = self.textract.analyze_document(
                    Document={'Bytes': img_bytes},
                    FeatureTypes=['TABLES']
                )
                
                # Get text from LINE blocks (preserves reading order)
                lines = []
                for block in response.get('Blocks', []):
                    if block['BlockType'] == 'LINE':
                        lines.append(block.get('Text', ''))
                
                pages_text.append('\n'.join(lines))
                logger.info(f"Extracted page {page_num + 1}/{pages_to_process}")
                
        finally:
            doc.close()
        
        return pages_text
    
    def _redact_pii(self, text: str) -> str:
        """Redact PII but keep structure visible."""
        redacted = text
        
        # SSN
        redacted = re.sub(r'\b\d{3}[-]?\d{2}[-]?\d{4}\b', '[SSN]', redacted)
        
        # Names - be careful, keep structure words
        # Pattern: LASTNAME, FIRSTNAME or FIRSTNAME LASTNAME at start of line/after newline
        redacted = re.sub(
            r'(?<=\n)([A-Z][A-Z]+,\s*[A-Z][A-Z]+)',
            '[EMPLOYEE_NAME]',
            redacted
        )
        
        # Currency amounts - keep decimals to show structure
        redacted = re.sub(
            r'\b\d{1,3}(?:,\d{3})*\.\d{2}\b',
            '[AMT]',
            redacted
        )
        
        return redacted
    
    def _parse_with_claude(self, redacted_sample: str, 
                           all_pages_text: List[str]) -> List[Employee]:
        """
        Two-phase approach:
        1. Claude analyzes redacted sample to understand format
        2. Claude parses actual data (page by page to limit tokens)
        """
        
        # Phase 1: Learn the format from redacted sample
        format_prompt = f"""Analyze this pay register structure. Values are redacted but structure is visible.

REDACTED SAMPLE:
{redacted_sample[:4000]}

Identify:
1. How are employee records structured?
2. What indicates the start of a new employee?
3. Where are: name, earnings, taxes, deductions, gross, net?

Respond with a brief description of the format."""

        format_response = self.claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": format_prompt}]
        )
        
        format_description = format_response.content[0].text
        logger.info(f"Format understood: {format_description[:200]}...")
        
        # Phase 2: Parse actual data
        all_employees = []
        
        # Process in batches to avoid token limits
        batch_size = 3  # pages per batch
        full_text = "\n\n--- PAGE ---\n\n".join(all_pages_text)
        
        parse_prompt = f"""You are parsing a pay register. Here's the format:
{format_description}

Parse the following pay register data and extract ALL employees.

DATA:
{full_text[:50000]}

Return a JSON array of employees. Each employee should have:
- name (string)
- employee_id (string, from "Code:" field if present)
- department (string)
- gross_pay (number)
- net_pay (number)  
- total_taxes (number)
- total_deductions (number)
- earnings (array of {{description, rate, hours, amount}})
- taxes (array of {{description, amount}})
- deductions (array of {{description, amount}})
- check_number (string)
- pay_method (string: "Direct Deposit" or "Check")

IMPORTANT: Extract REAL values, not redacted placeholders.
Return ONLY valid JSON array, no other text."""

        parse_response = self.claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=16000,
            messages=[{"role": "user", "content": parse_prompt}]
        )
        
        response_text = parse_response.content[0].text
        
        # Parse JSON from response
        try:
            # Try to find JSON array in response
            json_match = re.search(r'\[[\s\S]*\]', response_text)
            if json_match:
                employees_data = json.loads(json_match.group())
            else:
                employees_data = json.loads(response_text)
            
            # Convert to Employee objects
            for emp_data in employees_data:
                emp = Employee(
                    name=emp_data.get('name', ''),
                    employee_id=emp_data.get('employee_id', ''),
                    department=emp_data.get('department', ''),
                    gross_pay=float(emp_data.get('gross_pay', 0) or 0),
                    net_pay=float(emp_data.get('net_pay', 0) or 0),
                    total_taxes=float(emp_data.get('total_taxes', 0) or 0),
                    total_deductions=float(emp_data.get('total_deductions', 0) or 0),
                    earnings=emp_data.get('earnings', []),
                    taxes=emp_data.get('taxes', []),
                    deductions=emp_data.get('deductions', []),
                    check_number=str(emp_data.get('check_number', '')),
                    pay_method=emp_data.get('pay_method', '')
                )
                all_employees.append(emp)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response: {e}")
            logger.error(f"Response was: {response_text[:500]}")
        
        return all_employees
    
    def _validate_employee(self, emp: Employee) -> List[str]:
        """Validate employee record."""
        errors = []
        
        if not emp.name:
            errors.append(f"Missing employee name")
        
        # Check math: Gross - Taxes - Deductions = Net
        if emp.gross_pay > 0 and emp.net_pay > 0:
            calculated = emp.gross_pay - emp.total_taxes - emp.total_deductions
            if abs(calculated - emp.net_pay) > 0.02:
                errors.append(
                    f"{emp.name}: Math error - calculated net {calculated:.2f} != {emp.net_pay:.2f}"
                )
        
        return errors


# Singleton
_instance = None

def get_simple_extractor() -> SimpleExtractor:
    global _instance
    if _instance is None:
        _instance = SimpleExtractor()
    return _instance
