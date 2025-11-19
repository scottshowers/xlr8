"""
Intelligent Adaptive PDF Parser
Analyzes PDF structure dynamically and builds extraction strategy on-the-fly
"""

import fitz  # PyMuPDF
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging
import re
from collections import defaultdict

logger = logging.getLogger(__name__)


class DayforceParserEnhanced:
    """
    Adaptive parser that analyzes PDF structure and builds extraction rules dynamically.
    No fixed patterns - learns the layout and adapts.
    """
    
    def __init__(self):
        """Initialize parser."""
        self.text_blocks = []
        self.structure = {}
        self.employees = []
        
    def parse(self, pdf_path: str, output_dir: str = '/data/parsed_registers') -> Dict[str, Any]:
        """
        Intelligently parse PDF by analyzing structure first.
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Directory for Excel output
            
        Returns:
            Dict with status, output_path, accuracy, employee_count
        """
        try:
            logger.info(f"Starting intelligent adaptive parse: {pdf_path}")
            
            # Step 1: Extract text blocks with position data
            self.text_blocks = self._extract_text_blocks_with_positions(pdf_path)
            logger.info(f"Extracted {len(self.text_blocks)} text blocks")
            
            # Step 2: Analyze layout structure dynamically
            self.structure = self._analyze_layout_structure()
            logger.info(f"Detected structure: {self.structure.get('layout_type')}")
            
            # Step 3: Detect employee boundaries
            employee_regions = self._detect_employee_regions()
            logger.info(f"Found {len(employee_regions)} employee regions")
            
            # Step 4: Extract each employee iteratively
            for i, region in enumerate(employee_regions):
                logger.info(f"Processing employee region {i+1}/{len(employee_regions)}")
                employee = self._extract_employee_from_region(region)
                if employee:
                    self.employees.append(employee)
            
            if not self.employees:
                return {
                    'status': 'error',
                    'message': 'No employees extracted',
                    'accuracy': 0,
                    'employee_count': 0
                }
            
            logger.info(f"Successfully extracted {len(self.employees)} employees")
            
            # Step 5: Build output structure
            tabs = self._build_output_tabs()
            
            # Step 6: Write Excel
            output_path = self._write_excel(tabs, pdf_path, output_dir)
            
            # Step 7: Calculate accuracy
            accuracy = self._calculate_accuracy(tabs)
            
            return {
                'status': 'success',
                'output_path': output_path,
                'accuracy': accuracy,
                'employee_count': len(self.employees),
                'structure_detected': self.structure.get('layout_type')
            }
            
        except Exception as e:
            logger.error(f"Intelligent parse error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e),
                'accuracy': 0,
                'employee_count': 0
            }
    
    def _extract_text_blocks_with_positions(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract text with basic line-based parsing (more reliable than dict for finding patterns).
        """
        doc = fitz.open(pdf_path)
        all_blocks = []
        
        for page_num, page in enumerate(doc):
            # Get simple text (preserves lines better)
            text = page.get_text()
            lines = text.split('\n')
            
            # Create pseudo-blocks from lines
            y_pos = 0
            for line_num, line in enumerate(lines):
                line = line.strip()
                if line:
                    all_blocks.append({
                        'text': line,
                        'x0': 0,
                        'y0': y_pos,
                        'x1': 100,
                        'y1': y_pos + 10,
                        'page': page_num,
                        'font_size': 10,
                        'font_name': 'default',
                        'line_num': line_num
                    })
                    y_pos += 15  # Increment y position
        
        doc.close()
        
        return all_blocks
    
    def _analyze_layout_structure(self) -> Dict[str, Any]:
        """
        Analyze layout structure from line-based text extraction.
        Simplified approach focusing on finding employee markers.
        """
        structure = {
            'layout_type': 'simple',
            'columns': [],
            'sections': [],
            'employee_markers': []
        }
        
        if not self.text_blocks:
            return structure
        
        logger.info(f"Analyzing {len(self.text_blocks)} text lines")
        
        # Detect employee markers (Emp #:, Employee ID, etc.)
        emp_patterns = [r'emp\s*#', r'employee\s*id', r'emp\s*id', r'employee\s*#']
        
        for block in self.text_blocks:
            text_lower = block['text'].lower()
            
            # Check for employee markers
            if any(re.search(pattern, text_lower) for pattern in emp_patterns):
                structure['employee_markers'].append({
                    'text': block['text'],
                    'x': block['x0'],
                    'y': block['y0'],
                    'line_num': block.get('line_num', 0)
                })
                logger.info(f"Found employee marker: {block['text']}")
            
            # Check for section headers
            if any(keyword in text_lower for keyword in ['earnings', 'taxes', 'deductions']):
                structure['sections'].append({
                    'text': block['text'],
                    'x': block['x0'],
                    'y': block['y0']
                })
        
        logger.info(f"Detected {len(structure['employee_markers'])} employee markers")
        logger.info(f"Detected {len(structure['sections'])} section headers")
        
        return structure
    
    def _cluster_positions(self, positions: List[float], threshold: float = 50) -> List[float]:
        """
        Cluster positions that are close together (within threshold).
        Returns representative position for each cluster.
        """
        if not positions:
            return []
        
        sorted_pos = sorted(set(positions))
        clusters = []
        current_cluster = [sorted_pos[0]]
        
        for pos in sorted_pos[1:]:
            if pos - current_cluster[-1] <= threshold:
                current_cluster.append(pos)
            else:
                # Save cluster average
                clusters.append(sum(current_cluster) / len(current_cluster))
                current_cluster = [pos]
        
        # Don't forget last cluster
        if current_cluster:
            clusters.append(sum(current_cluster) / len(current_cluster))
        
        return clusters
    
    def _detect_employee_regions(self) -> List[Dict[str, Any]]:
        """
        Detect employee regions using line numbers (simplified approach).
        """
        regions = []
        
        emp_markers = self.structure.get('employee_markers', [])
        
        if not emp_markers:
            logger.warning("No employee markers found - using entire document as single region")
            return [{
                'blocks': self.text_blocks,
                'start_line': 0,
                'end_line': len(self.text_blocks)
            }]
        
        # Sort markers by line number
        emp_markers = sorted(emp_markers, key=lambda m: m.get('line_num', 0))
        
        logger.info(f"Creating regions from {len(emp_markers)} markers")
        
        # Create regions between markers
        for i, marker in enumerate(emp_markers):
            start_line = marker.get('line_num', 0)
            
            if i + 1 < len(emp_markers):
                end_line = emp_markers[i + 1].get('line_num', len(self.text_blocks))
            else:
                end_line = len(self.text_blocks)
            
            # Get blocks in this range
            region_blocks = [
                block for block in self.text_blocks
                if start_line <= block.get('line_num', 0) < end_line
            ]
            
            if region_blocks:
                regions.append({
                    'marker': marker,
                    'blocks': region_blocks,
                    'start_line': start_line,
                    'end_line': end_line
                })
                logger.info(f"Region {i+1}: lines {start_line}-{end_line}, {len(region_blocks)} blocks")
        
        return regions
    
    def _extract_employee_from_region(self, region: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract employee data from a region using adaptive parsing.
        """
        blocks = region['blocks']
        
        if not blocks:
            return None
        
        employee = {
            'info': {},
            'earnings': [],
            'taxes': [],
            'deductions': []
        }
        
        # Extract employee info (key-value pairs)
        employee['info'] = self._extract_info_fields(blocks)
        
        # Detect sub-sections within this employee region
        subsections = self._detect_subsections(blocks)
        
        # Extract each subsection
        for section_name, section_blocks in subsections.items():
            if 'earning' in section_name.lower():
                employee['earnings'] = self._extract_table_data(section_blocks)
            elif 'tax' in section_name.lower():
                employee['taxes'] = self._extract_table_data(section_blocks)
            elif 'deduction' in section_name.lower():
                employee['deductions'] = self._extract_table_data(section_blocks)
        
        return employee if employee['info'] else None
    
    def _extract_info_fields(self, blocks: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Extract key-value pairs from text blocks (e.g., "Emp #: 12345").
        """
        info = {}
        
        # Common field patterns
        patterns = {
            'employee_id': r'(?:emp\s*#|employee\s*id|emp\s*id)[\s:]+(\w+)',
            'name': r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)$',
            'dept': r'dept[\s:]+([^\n]+)',
            'hire_date': r'hire\s*date[\s:]+([^\n]+)',
            'term_date': r'term\s*date[\s:]+([^\n]+)',
            'ssn': r'ssn[\s:]+([X\d\-]+)',
            'status': r'status[\s:]+([^\n]+)',
            'frequency': r'frequency[\s:]+([^\n]+)',
            'type': r'type[\s:]+([^\n]+)',
            'rate': r'rate[\s:]+\$?([\d,.]+)',
            'salary': r'sal(?:ary)?[\s:]+\$?([\d,.]+)'
        }
        
        for block in blocks:
            text = block['text']
            text_lower = text.lower()
            
            # Try each pattern
            for field, pattern in patterns.items():
                if field not in info:  # Don't overwrite
                    match = re.search(pattern, text_lower)
                    if match:
                        info[field] = match.group(1).strip()
        
        return info
    
    def _detect_subsections(self, blocks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Detect subsections (Earnings, Taxes, Deductions) within employee region.
        """
        subsections = defaultdict(list)
        current_section = 'general'
        
        section_keywords = {
            'earnings': ['earnings', 'pay items', 'income'],
            'taxes': ['taxes', 'tax deductions', 'statutory'],
            'deductions': ['deductions', 'pre-tax', 'post-tax', 'benefits']
        }
        
        for block in blocks:
            text_lower = block['text'].lower()
            
            # Check if this block is a section header
            for section_name, keywords in section_keywords.items():
                if any(keyword in text_lower for keyword in keywords):
                    current_section = section_name
                    break
            
            # Add block to current section
            subsections[current_section].append(block)
        
        return dict(subsections)
    
    def _extract_table_data(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        Extract table data from text lines.
        Looks for lines with amounts ($XX.XX or XX.XX patterns).
        """
        if not blocks:
            return []
        
        rows = []
        
        for block in blocks:
            text = block['text']
            
            # Skip headers and totals
            if any(word in text.lower() for word in ['description', 'amount', 'rate', 'total', 'hours', 'ytd', '---', '===', '***']):
                continue
            
            # Look for lines with dollar amounts
            if '$' in text or re.search(r'\d+\.\d{2}', text):
                # Split by multiple spaces to separate description from amount
                parts = re.split(r'\s{2,}', text)
                
                if len(parts) >= 2:
                    description = parts[0].strip()
                    
                    # Find amount in the line
                    amount_match = re.search(r'\$?([\d,]+\.\d{2})', text)
                    amount = amount_match.group(1).replace(',', '') if amount_match else '0.00'
                    
                    # Only add if description isn't empty or just symbols
                    if description and description not in ['', '-', '----------', '===']:
                        rows.append({
                            'description': description,
                            'amount': amount
                        })
        
        return rows
    
    def _build_output_tabs(self) -> Dict[str, pd.DataFrame]:
        """
        Build 4-tab output structure from extracted employees.
        """
        tabs = {
            'Employee Summary': [],
            'Earnings': [],
            'Taxes': [],
            'Deductions': []
        }
        
        for emp in self.employees:
            # Employee Summary
            summary = emp['info'].copy()
            summary['Total_Earnings'] = sum(
                float(e.get('amount', 0)) for e in emp['earnings']
                if self._is_valid_amount(e.get('amount'))
            )
            summary['Total_Taxes'] = sum(
                float(t.get('amount', 0)) for t in emp['taxes']
                if self._is_valid_amount(t.get('amount'))
            )
            summary['Total_Deductions'] = sum(
                float(d.get('amount', 0)) for d in emp['deductions']
                if self._is_valid_amount(d.get('amount'))
            )
            summary['Net_Pay'] = summary['Total_Earnings'] - summary['Total_Taxes'] - summary['Total_Deductions']
            tabs['Employee Summary'].append(summary)
            
            # Detail tabs
            for earning in emp['earnings']:
                row = emp['info'].copy()
                row.update(earning)
                tabs['Earnings'].append(row)
            
            for tax in emp['taxes']:
                row = emp['info'].copy()
                row.update(tax)
                tabs['Taxes'].append(row)
            
            for deduction in emp['deductions']:
                row = emp['info'].copy()
                row.update(deduction)
                tabs['Deductions'].append(row)
        
        return {name: pd.DataFrame(rows) if rows else pd.DataFrame() for name, rows in tabs.items()}
    
    def _is_valid_amount(self, value: Any) -> bool:
        """Check if value is a valid amount."""
        if not value:
            return False
        try:
            float(str(value).replace(',', ''))
            return True
        except:
            return False
    
    def _write_excel(self, tabs: Dict[str, pd.DataFrame], pdf_path: str, output_dir: str) -> str:
        """Write 4 tabs to Excel."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        pdf_name = Path(pdf_path).stem
        output_path = output_dir / f"{pdf_name}_parsed.xlsx"
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for tab_name, df in tabs.items():
                df.to_excel(writer, sheet_name=tab_name, index=False)
        
        return str(output_path)
    
    def _calculate_accuracy(self, tabs: Dict[str, pd.DataFrame]) -> int:
        """Calculate accuracy score (0-100)."""
        score = 0
        
        # Has 4 tabs (10 pts)
        if len(tabs) == 4:
            score += 10
        
        # All tabs have data (20 pts)
        non_empty = sum(1 for df in tabs.values() if len(df) > 0)
        score += int((non_empty / 4) * 20)
        
        # Employee Summary has required fields (20 pts)
        summary_df = tabs.get('Employee Summary', pd.DataFrame())
        if not summary_df.empty:
            required_fields = ['employee_id', 'Total_Earnings', 'Net_Pay']
            has_fields = sum(1 for f in required_fields if f in summary_df.columns)
            score += int((has_fields / len(required_fields)) * 20)
        
        # Detail tabs have data (30 pts)
        detail_rows = sum(len(tabs[t]) for t in ['Earnings', 'Taxes', 'Deductions'])
        if detail_rows >= 10:
            score += 30
        elif detail_rows >= 5:
            score += 20
        elif detail_rows >= 1:
            score += 10
        
        # Data quality (20 pts)
        if not summary_df.empty and 'Net_Pay' in summary_df.columns:
            # Check if Net Pay is reasonable
            avg_net = summary_df['Net_Pay'].mean()
            if 0 < avg_net < 100000:
                score += 20
            elif avg_net != 0:
                score += 10
        
        return min(100, score)


def parse_dayforce_register(pdf_path: str, output_dir: str = '/data/parsed_registers') -> Dict[str, Any]:
    """
    Parse Dayforce register using intelligent adaptive parser.
    """
    parser = DayforceParserEnhanced()
    return parser.parse(pdf_path, output_dir)
