"""
Intelligent Parser Orchestrator - 3-Stage Parsing System
Coordinates custom parsers, adaptive parsers, and generated parsers

Author: HCMPACT  
Version: 1.0
"""

import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import importlib.util
import pandas as pd

from pdf_structure_analyzer import PDFStructureAnalyzer
from parser_code_generator import ParserCodeGenerator

logger = logging.getLogger(__name__)


class IntelligentParserOrchestrator:
    """
    3-Stage Intelligent Parsing System:
    
    Stage 1: Custom Parsers - Try saved custom parsers for similar documents
    Stage 2: Adaptive Parsers - Use existing adaptive_register_parser.py and adaptive_payroll_parser.py
    Stage 3: Generated Parsers - Generate and test new custom parser
    
    Reports accuracy (0-100%) and saves successful parsers for future use.
    """
    
    def __init__(self, custom_parsers_dir: str = "/data/custom_parsers"):
        """
        Initialize orchestrator.
        
        Args:
            custom_parsers_dir: Directory to store/load custom parsers
        """
        self.custom_parsers_dir = custom_parsers_dir
        os.makedirs(custom_parsers_dir, exist_ok=True)
        
        self.analyzer = PDFStructureAnalyzer()
        self.generator = ParserCodeGenerator()
        
        # Load adaptive parsers
        self.adaptive_parsers = self._load_adaptive_parsers()
        
        logger.info(f"Intelligent Parser Orchestrator initialized")
        logger.info(f"Custom parsers directory: {custom_parsers_dir}")
        logger.info(f"Loaded {len(self.adaptive_parsers)} adaptive parsers")
    
    def _load_adaptive_parsers(self) -> Dict[str, Any]:
        """Load existing adaptive parsers."""
        
        parsers = {}
        
        try:
            # Try to import adaptive_register_parser
            from utils.pdf_parsers import extract_register_adaptive
            parsers['adaptive_register'] = extract_register_adaptive
            logger.info("âœ… Loaded adaptive_register_parser")
        except ImportError:
            logger.warning("âš ï¸ adaptive_register_parser not available")
        
        try:
            # Try to import adaptive_payroll_parser
            from utils.pdf_parsers import extract_payroll_register
            parsers['adaptive_payroll'] = extract_payroll_register
            logger.info("âœ… Loaded adaptive_payroll_parser")
        except ImportError:
            logger.warning("âš ï¸ adaptive_payroll_parser not available")
        
        return parsers
    
    def parse(self, pdf_path: str, force_regenerate: bool = False) -> Dict[str, Any]:
        """
        Parse PDF using 3-stage intelligent system.
        
        Args:
            pdf_path: Path to PDF file
            force_regenerate: Skip Stage 1 & 2, force Stage 3
            
        Returns:
            {
                'success': bool,
                'stage': int,                    # 1, 2, or 3
                'stage_name': str,               # 'custom', 'adaptive', 'generated'
                'method': str,                   # Specific parser used
                'accuracy': float,               # 0-100
                'tables': List[Dict],            # Extracted tables
                'text': str,                     # Extracted text
                'metadata': Dict,
                'parser_path': str,              # Path to parser used (if Stage 1 or 3)
                'processing_time': float,
                'recommendations': List[str]
            }
        """
        
        logger.info(f"========== Intelligent Parsing: {pdf_path} ==========")
        
        import time
        start_time = time.time()
        
        # Step 0: Analyze PDF structure
        logger.info("Step 0: Analyzing PDF structure...")
        structure_analysis = self.analyzer.analyze(pdf_path)
        
        logger.info(f"  Document type: {structure_analysis['document_type']}")
        logger.info(f"  Recommended strategy: {structure_analysis['recommended_strategy']}")
        logger.info(f"  Complexity: {structure_analysis['complexity']}")
        logger.info(f"  Table density: {structure_analysis['table_density']:.1%}")
        
        result = None
        
        if not force_regenerate:
            # Stage 1: Try custom parsers
            logger.info("Stage 1: Trying custom parsers...")
            result = self._try_custom_parsers(pdf_path, structure_analysis)
            
            if result and result['success'] and result['accuracy'] >= 80:
                logger.info(f"âœ… Stage 1 succeeded with {result['accuracy']:.0f}% accuracy")
                result['stage'] = 1
                result['stage_name'] = 'custom'
                result['processing_time'] = time.time() - start_time
                return result
            
            # Stage 2: Try adaptive parsers
            logger.info("Stage 2: Trying adaptive parsers...")
            result = self._try_adaptive_parsers(pdf_path, structure_analysis)
            
            if result and result['success'] and result['accuracy'] >= 70:
                logger.info(f"âœ… Stage 2 succeeded with {result['accuracy']:.0f}% accuracy")
                result['stage'] = 2
                result['stage_name'] = 'adaptive'
                result['processing_time'] = time.time() - start_time
                return result
        
        # Stage 3: Generate custom parser
        logger.info("Stage 3: Generating custom parser...")
        result = self._generate_and_test_parser(pdf_path, structure_analysis)
        
        if result and result['success']:
            logger.info(f"âœ… Stage 3 succeeded with {result['accuracy']:.0f}% accuracy")
            result['stage'] = 3
            result['stage_name'] = 'generated'
            result['processing_time'] = time.time() - start_time
            
            # Save parser if accuracy is good
            if result['accuracy'] >= 70:
                self._save_parser_for_reuse(result, structure_analysis)
            
            return result
        
        # All stages failed
        logger.error("âŒ All parsing stages failed")
        return {
            'success': False,
            'stage': 0,
            'stage_name': 'none',
            'method': 'failed',
            'accuracy': 0.0,
            'tables': [],
            'text': '',
            'metadata': structure_analysis,
            'processing_time': time.time() - start_time,
            'error': 'All parsing stages failed',
            'recommendations': ['Try manual parsing', 'Check if PDF is corrupted']
        }
    
    def _try_custom_parsers(self, pdf_path: str, structure_analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Stage 1: Try saved custom parsers."""
        
        # Find matching parsers based on document type
        doc_type = structure_analysis['document_type']
        matching_parsers = self._find_matching_parsers(doc_type)
        
        if not matching_parsers:
            logger.info("  No matching custom parsers found")
            return None
        
        logger.info(f"  Found {len(matching_parsers)} matching custom parser(s)")
        
        # Try each matching parser
        for parser_path in matching_parsers:
            try:
                logger.info(f"  Trying: {Path(parser_path).name}")
                
                # Load and execute parser
                result = self._execute_custom_parser(parser_path, pdf_path)
                
                if result and result['success']:
                    # Calculate accuracy
                    accuracy = self._calculate_accuracy(result, structure_analysis)
                    result['accuracy'] = accuracy
                    result['method'] = Path(parser_path).stem
                    result['parser_path'] = parser_path
                    
                    logger.info(f"    Accuracy: {accuracy:.0f}%")
                    
                    if accuracy >= 80:
                        return result
                
            except Exception as e:
                logger.warning(f"    Failed: {e}")
                continue
        
        return None
    
    def _try_adaptive_parsers(self, pdf_path: str, structure_analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Stage 2: Try adaptive parsers."""
        
        if not self.adaptive_parsers:
            logger.info("  No adaptive parsers available")
            return None
        
        doc_type = structure_analysis['document_type']
        
        # Select appropriate adaptive parser
        if 'payroll' in doc_type.lower():
            parser_name = 'adaptive_payroll'
        else:
            parser_name = 'adaptive_register'
        
        if parser_name not in self.adaptive_parsers:
            logger.info(f"  Parser {parser_name} not available, trying other...")
            # Try any available parser
            parser_name = list(self.adaptive_parsers.keys())[0]
        
        try:
            logger.info(f"  Trying: {parser_name}")
            
            parser_func = self.adaptive_parsers[parser_name]
            
            # Call parser
            result = parser_func(pdf_path=pdf_path, output_dir=None)
            
            if result and result.get('success'):
                # Calculate accuracy
                accuracy = self._calculate_accuracy(result, structure_analysis)
                result['accuracy'] = accuracy
                result['method'] = parser_name
                
                logger.info(f"    Accuracy: {accuracy:.0f}%")
                
                return result
            
        except Exception as e:
            logger.warning(f"    Failed: {e}")
        
        return None
    
    def _generate_and_test_parser(self, pdf_path: str, structure_analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Stage 3: Generate and test custom parser."""
        
        try:
            # Generate parser code
            logger.info("  Generating parser code...")
            code = self.generator.generate(structure_analysis, pdf_path)
            
            # Test parser
            logger.info("  Testing generated parser...")
            test_result = self.generator.test_generated_parser(code, pdf_path)
            
            if test_result and test_result.get('success'):
                result = test_result['result']
                
                # Calculate accuracy
                accuracy = self._calculate_accuracy(result, structure_analysis)
                result['accuracy'] = accuracy
                result['method'] = 'generated_custom'
                result['generated_code'] = code
                
                logger.info(f"    Accuracy: {accuracy:.0f}%")
                
                return result
            else:
                logger.warning(f"    Generation failed: {test_result.get('error', 'Unknown error')}")
                return None
            
        except Exception as e:
            logger.error(f"    Error: {e}")
            return None
    
    def _find_matching_parsers(self, doc_type: str) -> List[str]:
        """Find custom parsers that match document type."""
        
        matching = []
        
        if not os.path.exists(self.custom_parsers_dir):
            return matching
        
        # List all .py files in custom parsers directory
        for file_path in Path(self.custom_parsers_dir).glob("*.py"):
            # Check if filename matches document type
            filename = file_path.stem.lower()
            
            if doc_type.lower() in filename or 'custom' in filename:
                matching.append(str(file_path))
        
        return matching
    
    def _execute_custom_parser(self, parser_path: str, pdf_path: str) -> Optional[Dict[str, Any]]:
        """Execute a custom parser."""
        
        try:
            # Load module
            spec = importlib.util.spec_from_file_location("custom_parser", parser_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Get parse function
            if hasattr(module, 'parse_pdf'):
                result = module.parse_pdf(pdf_path)
                return result
            elif hasattr(module, 'CustomParser'):
                parser = module.CustomParser()
                result = parser.parse(pdf_path)
                return result
            else:
                logger.warning(f"No parse function found in {parser_path}")
                return None
                
        except Exception as e:
            logger.error(f"Error executing custom parser: {e}")
            return None
    
    def _calculate_accuracy(self, result: Dict[str, Any], structure_analysis: Dict[str, Any]) -> float:
        """
        Calculate parsing accuracy (0-100).
        
        Factors:
        - Number of tables extracted
        - Text length
        - Data completeness
        - Structure match
        """
        
        accuracy = 0.0
        
        # Base score for success
        if result.get('success'):
            accuracy += 30
        
        # Tables extracted
        tables = result.get('tables', [])
        if tables:
            expected_tables = int(structure_analysis.get('table_density', 0) * 10)
            if expected_tables == 0:
                expected_tables = 1
            
            table_score = min(len(tables) / expected_tables, 1.0) * 40
            accuracy += table_score
        
        # Text extracted
        text = result.get('text', '')
        if text:
            text_score = min(len(text) / 1000, 1.0) * 20
            accuracy += text_score
        
        # Data quality (if tables have data)
        if tables:
            for table in tables:
                if isinstance(table, dict) and 'data' in table:
                    df = table['data']
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        accuracy += 10
                        break
        
        return min(accuracy, 100.0)
    
    def _save_parser_for_reuse(self, result: Dict[str, Any], structure_analysis: Dict[str, Any]):
        """Save successful parser for future reuse."""
        
        if 'generated_code' not in result:
            return
        
        doc_type = structure_analysis['document_type']
        accuracy = result['accuracy']
        
        # Generate filename
        filename = f"custom_{doc_type}_{int(accuracy)}.py"
        output_path = os.path.join(self.custom_parsers_dir, filename)
        
        # Save code
        success = self.generator.save_parser(result['generated_code'], output_path)
        
        if success:
            logger.info(f"âœ… Saved parser for reuse: {filename}")
        else:
            logger.warning("âš ï¸ Failed to save parser")


# Convenience function
def intelligent_parse(pdf_path: str, custom_parsers_dir: str = "/data/custom_parsers") -> Dict[str, Any]:
    """
    Quick intelligent parsing.
    
    Args:
        pdf_path: Path to PDF
        custom_parsers_dir: Directory for custom parsers
        
    Returns:
        Parse result with accuracy
    """
    orchestrator = IntelligentParserOrchestrator(custom_parsers_dir)
    return orchestrator.parse(pdf_path)
