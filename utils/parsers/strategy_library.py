"""
Strategy Library - Different extraction approaches for different vendors/formats
"""

import logging
from typing import Dict, List, Any
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


class ExtractionStrategy:
    """Base class for extraction strategies."""
    
    def __init__(self):
        self.name = "base_strategy"
        self.description = "Base extraction strategy"
    
    def can_handle(self, pdf_path: str, vendor: str = None) -> bool:
        """Check if this strategy can handle the PDF."""
        return False
    
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract data from PDF.
        
        Returns:
            {
                'employees': [...],
                'earnings': [...],
                'taxes': [...],
                'deductions': [...]
            }
        """
        raise NotImplementedError


class TableBasedStrategy(ExtractionStrategy):
    """Table-based extraction (works for Dayforce, Workday)."""
    
    def __init__(self):
        super().__init__()
        self.name = "table_based"
        self.description = "Table extraction with column separation"
    
    def can_handle(self, pdf_path: str, vendor: str = None) -> bool:
        """Check if PDF has extractable tables."""
        if not PDFPLUMBER_AVAILABLE:
            return False
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                tables = pdf.pages[0].extract_tables()
                return len(tables) > 0 and len(tables[0]) > 3
        except:
            return False
    
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """Extract using table method (delegates to existing V2 parser)."""
        from .intelligent_parser_orchestrator_v2 import IntelligentParserOrchestratorV2
        
        parser = IntelligentParserOrchestratorV2()
        result = parser.parse(pdf_path, '/tmp')
        
        if result.get('success'):
            # Extract structured data from result
            # V2 parser returns excel_path, we need to read it back
            # For now, return empty structure - V3 will handle this properly
            return {
                'employees': [],
                'earnings': [],
                'taxes': [],
                'deductions': [],
                '_result': result
            }
        
        return {'employees': [], 'earnings': [], 'taxes': [], 'deductions': []}


class TextBasedStrategy(ExtractionStrategy):
    """Text-based extraction with keyword filtering (works for ADP, Paychex)."""
    
    def __init__(self):
        super().__init__()
        self.name = "text_based"
        self.description = "Text extraction with keyword filtering"
    
    def can_handle(self, pdf_path: str, vendor: str = None) -> bool:
        """Always can try text extraction."""
        return PDFPLUMBER_AVAILABLE
    
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """Extract using text + keywords (simplified V2 logic)."""
        import re
        
        with pdfplumber.open(pdf_path) as pdf:
            full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        
        # Simple keyword-based extraction
        employees = self._extract_employees(full_text)
        earnings = self._extract_by_keywords(full_text, ['regular', 'overtime', 'bonus', 'vacation'], employees)
        taxes = self._extract_by_keywords(full_text, ['fed', 'fica', 'tax', 'w/h'], employees)
        deductions = self._extract_by_keywords(full_text, ['medical', '401k', 'insurance', 'dental'], employees)
        
        return {
            'employees': employees,
            'earnings': earnings,
            'taxes': taxes,
            'deductions': deductions
        }
    
    def _extract_employees(self, text: str) -> List[Dict]:
        """Extract employee info from text."""
        employees = []
        
        # Look for employee ID patterns
        for match in re.finditer(r'(?:emp|employee)\s*#?\s*:?\s*(\d{4,6})', text, re.IGNORECASE):
            emp_id = match.group(1)
            
            # Look for name nearby
            context_start = max(0, match.start() - 200)
            context_end = min(len(text), match.end() + 200)
            context = text[context_start:context_end]
            
            name_match = re.search(r'([A-Z][a-z]+\s+[A-Z][a-z]+)', context)
            name = name_match.group(1) if name_match else f"Employee {emp_id}"
            
            employees.append({
                'employee_id': emp_id,
                'employee_name': name,
                'department': ''
            })
        
        # Deduplicate
        seen = set()
        unique = []
        for emp in employees:
            if emp['employee_id'] not in seen:
                seen.add(emp['employee_id'])
                unique.append(emp)
        
        return unique if unique else [{'employee_id': 'Unknown', 'employee_name': 'Unknown', 'department': ''}]
    
    def _extract_by_keywords(self, text: str, keywords: List[str], employees: List[Dict]) -> List[Dict]:
        """Extract line items by keywords."""
        items = []
        
        for line in text.split('\n'):
            line = line.strip()
            if len(line) < 10:
                continue
            
            # Check if line has any keyword
            has_keyword = any(kw in line.lower() for kw in keywords)
            if not has_keyword:
                continue
            
            # Extract amounts
            amounts = [float(a.replace(',', '')) for a in re.findall(r'\$?([\d,]+\.\d{2})', line)]
            
            if amounts:
                # Get description (text before first amount)
                desc_match = re.match(r'^([A-Za-z\s\-/]+)', line)
                desc = desc_match.group(1).strip() if desc_match else line[:30]
                
                # Assign to first employee (simple approach)
                emp = employees[0] if employees else {'employee_id': '', 'employee_name': ''}
                
                items.append({
                    'employee_id': emp['employee_id'],
                    'employee_name': emp['employee_name'],
                    'description': desc,
                    'amount': amounts[0] if amounts else 0,
                    'hours': 0,
                    'rate': 0
                })
        
        return items


class HybridStrategy(ExtractionStrategy):
    """Hybrid: Try table first, fall back to text."""
    
    def __init__(self):
        super().__init__()
        self.name = "hybrid"
        self.description = "Table + text fallback"
        self.table_strategy = TableBasedStrategy()
        self.text_strategy = TextBasedStrategy()
    
    def can_handle(self, pdf_path: str, vendor: str = None) -> bool:
        """Always can try."""
        return PDFPLUMBER_AVAILABLE
    
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """Try table first, fall back to text."""
        if self.table_strategy.can_handle(pdf_path):
            result = self.table_strategy.extract(pdf_path)
            if result.get('employees'):
                return result
        
        return self.text_strategy.extract(pdf_path)


class LegacyV1Strategy(ExtractionStrategy):
    """Use existing V1 parser."""
    
    def __init__(self):
        super().__init__()
        self.name = "legacy_v1"
        self.description = "Original V1 multi-stage parser"
    
    def can_handle(self, pdf_path: str, vendor: str = None) -> bool:
        """Always can try."""
        return True
    
    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """Use V1 parser."""
        from .intelligent_parser_orchestrator import IntelligentParserOrchestrator
        
        parser = IntelligentParserOrchestrator()
        result = parser.parse(pdf_path, '/tmp')
        
        # V1 returns different format - need to adapt
        return {
            'employees': [],
            'earnings': [],
            'taxes': [],
            'deductions': [],
            '_result': result
        }


class StrategyLibrary:
    """Library of all available extraction strategies."""
    
    def __init__(self):
        self.strategies = [
            TableBasedStrategy(),
            TextBasedStrategy(),
            HybridStrategy(),
            LegacyV1Strategy()
        ]
    
    def get_strategies_for_vendor(self, vendor: str) -> List[ExtractionStrategy]:
        """Get recommended strategies for a vendor, in priority order."""
        
        strategy_map = {
            'dayforce': ['table_based', 'hybrid', 'text_based'],
            'adp': ['text_based', 'hybrid', 'table_based'],
            'paychex': ['text_based', 'hybrid'],
            'quickbooks': ['hybrid', 'text_based'],
            'gusto': ['text_based', 'hybrid'],
            'workday': ['table_based', 'hybrid'],
            'ukg': ['hybrid', 'table_based', 'text_based'],
            'unknown': ['table_based', 'text_based', 'hybrid', 'legacy_v1']
        }
        
        strategy_names = strategy_map.get(vendor, strategy_map['unknown'])
        
        # Return strategy objects in order
        ordered_strategies = []
        for name in strategy_names:
            for strategy in self.strategies:
                if strategy.name == name:
                    ordered_strategies.append(strategy)
                    break
        
        return ordered_strategies
    
    def get_all_strategies(self) -> List[ExtractionStrategy]:
        """Get all strategies."""
        return self.strategies
