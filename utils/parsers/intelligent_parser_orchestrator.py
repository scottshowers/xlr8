"""
Intelligent Parser Orchestrator for XLR8
Orchestrates 3-stage parsing system and calculates accuracy
"""

import logging
from pathlib import Path
from typing import Dict, Optional
import importlib.util
import sys
import time
import pandas as pd
from datetime import datetime

from utils.pdf_parsers import extract_register_adaptive, extract_payroll_register
from utils.parsers.pdf_structure_analyzer import PDFStructureAnalyzer
from utils.parsers.parser_code_generator import ParserCodeGenerator

logger = logging.getLogger(__name__)


class IntelligentParserOrchestrator:
    """
    Orchestrates 3-stage intelligent parsing system:
    1. Custom parsers (saved from previous successful parses)
    2. Adaptive parsers (existing adaptive parsers)
    3. Generated parsers (analyzes PDF, generates code, tests, saves if accuracy >= 70%)
    """
    
    def __init__(self):
        self.analyzer = PDFStructureAnalyzer()
        self.generator = ParserCodeGenerator()
        self.custom_parsers_dir = Path("/data/custom_parsers")
        self.uploads_dir = Path("/data/uploads")
        self.output_dir = Path("/data/parsed_registers")
        
        # Create directories
        self.custom_parsers_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_with_intelligence(
        self,
        pdf_path: str,
        auto_save: bool = True,
        min_accuracy_to_save: int = 70
    ) -> Dict:
        """
        Intelligently parse PDF using 3-stage approach
        
        Args:
            pdf_path: Path to input PDF
            auto_save: Whether to auto-save successful parsers
            min_accuracy_to_save: Minimum accuracy to save parser (0-100)
            
        Returns:
            Dict with parsing results and accuracy metrics
        """
        start_time = time.time()
        pdf_name = Path(pdf_path).stem
        
        logger.info(f"Starting intelligent parsing for: {pdf_path}")
        
        # Stage 1: Try custom parsers
        logger.info("STAGE 1: Trying custom parsers...")
        result = self._try_custom_parsers(pdf_path, pdf_name)
        
        if result['success'] and result.get('accuracy', 0) >= 70:
            result['stage_used'] = 'custom_parser'
            result['execution_time'] = time.time() - start_time
            logger.info(f"Custom parser succeeded with {result['accuracy']}% accuracy")
            return result
        
        # Stage 2: Try adaptive parsers
        logger.info("STAGE 2: Trying adaptive parsers...")
        result = self._try_adaptive_parsers(pdf_path, pdf_name)
        
        if result['success'] and result.get('accuracy', 0) >= 70:
            result['stage_used'] = 'adaptive_parser'
            result['execution_time'] = time.time() - start_time
            logger.info(f"Adaptive parser succeeded with {result['accuracy']}% accuracy")
            return result
        
        # Stage 3: Generate and test new parser
        logger.info("STAGE 3: Generating custom parser...")
        result = self._generate_and_test_parser(
            pdf_path,
            pdf_name,
            auto_save=auto_save,
            min_accuracy=min_accuracy_to_save
        )
        
        result['stage_used'] = 'generated_parser'
        result['execution_time'] = time.time() - start_time
        
        if result['success']:
            logger.info(f"Generated parser succeeded with {result.get('accuracy', 0)}% accuracy")
        else:
            logger.warning("All parsing stages failed")
        
        return result
    
    def _try_custom_parsers(self, pdf_path: str, pdf_name: str) -> Dict:
        """Try all saved custom parsers"""
        
        if not self.custom_parsers_dir.exists():
            return {'success': False, 'error': 'No custom parsers directory'}
        
        parser_files = list(self.custom_parsers_dir.glob("*.py"))
        
        if not parser_files:
            return {'success': False, 'error': 'No custom parsers available'}
        
        # Try each parser
        for parser_file in parser_files:
            try:
                logger.info(f"Trying custom parser: {parser_file.stem}")
                result = self._execute_parser(parser_file, pdf_path, pdf_name)
                
                if result['success']:
                    # Calculate accuracy
                    accuracy = self._calculate_accuracy(result)
                    result['accuracy'] = accuracy['total']
                    result['accuracy_breakdown'] = accuracy
                    result['parser_name'] = parser_file.stem
                    
                    if accuracy['total'] >= 70:
                        logger.info(f"Custom parser {parser_file.stem} succeeded")
                        return result
                        
            except Exception as e:
                logger.warning(f"Custom parser {parser_file.stem} failed: {str(e)}")
                continue
        
        return {'success': False, 'error': 'All custom parsers failed'}
    
    def _try_adaptive_parsers(self, pdf_path: str, pdf_name: str) -> Dict:
        """Try existing adaptive parsers"""
        
        output_path = self.output_dir / f"{pdf_name}_parsed.xlsx"
        
        # Try adaptive register parser first
        try:
            logger.info("Trying adaptive register parser...")
            result = extract_register_adaptive(pdf_path, str(output_path))
            
            if result.get('success'):
                accuracy = self._calculate_accuracy(result)
                result['accuracy'] = accuracy['total']
                result['accuracy_breakdown'] = accuracy
                result['parser_name'] = 'adaptive_register_parser'
                
                if accuracy['total'] >= 70:
                    return result
                    
        except Exception as e:
            logger.warning(f"Adaptive register parser failed: {str(e)}")
        
        # Try payroll register parser
        try:
            logger.info("Trying payroll register parser...")
            result = extract_payroll_register(pdf_path, str(output_path))
            
            if result.get('success'):
                accuracy = self._calculate_accuracy(result)
                result['accuracy'] = accuracy['total']
                result['accuracy_breakdown'] = accuracy
                result['parser_name'] = 'adaptive_payroll_parser'
                
                if accuracy['total'] >= 70:
                    return result
                    
        except Exception as e:
            logger.warning(f"Payroll register parser failed: {str(e)}")
        
        return {'success': False, 'error': 'All adaptive parsers failed'}
    
    def _generate_and_test_parser(
        self,
        pdf_path: str,
        pdf_name: str,
        auto_save: bool = True,
        min_accuracy: int = 70
    ) -> Dict:
        """Generate new parser, test it, and optionally save"""
        
        try:
            # Analyze PDF structure
            logger.info("Analyzing PDF structure...")
            analysis = self.analyzer.analyze_pdf(pdf_path)
            
            if not analysis.get('success'):
                return {
                    'success': False,
                    'error': f"PDF analysis failed: {analysis.get('error')}"
                }
            
            # Generate parsing hints
            hints = self.analyzer.generate_parsing_hints()
            
            # Generate parser code
            logger.info("Generating parser code...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            parser_name = f"{pdf_name}_parser_{timestamp}"
            
            gen_result = self.generator.generate_parser(analysis, hints, parser_name)
            
            if not gen_result.get('success'):
                return {
                    'success': False,
                    'error': f"Parser generation failed: {gen_result.get('error')}"
                }
            
            # Save parser temporarily for testing
            temp_parser_path = self.custom_parsers_dir / f"temp_{parser_name}.py"
            with open(temp_parser_path, 'w') as f:
                f.write(gen_result['code'])
            
            # Test the generated parser
            logger.info("Testing generated parser...")
            result = self._execute_parser(temp_parser_path, pdf_path, pdf_name)
            
            if result['success']:
                # Calculate accuracy
                accuracy = self._calculate_accuracy(result)
                result['accuracy'] = accuracy['total']
                result['accuracy_breakdown'] = accuracy
                result['parser_name'] = parser_name
                
                # Save if meets accuracy threshold
                if auto_save and accuracy['total'] >= min_accuracy:
                    final_parser_path = self.custom_parsers_dir / f"{parser_name}.py"
                    temp_parser_path.rename(final_parser_path)
                    result['was_saved'] = True
                    result['saved_path'] = str(final_parser_path)
                    logger.info(f"Parser saved with {accuracy['total']}% accuracy")
                else:
                    temp_parser_path.unlink()  # Delete temp file
                    result['was_saved'] = False
                    if accuracy['total'] < min_accuracy:
                        logger.info(f"Parser not saved: accuracy {accuracy['total']}% < {min_accuracy}%")
            else:
                # Clean up temp file
                if temp_parser_path.exists():
                    temp_parser_path.unlink()
            
            return result
            
        except Exception as e:
            logger.error(f"Generate and test failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _execute_parser(self, parser_file: Path, pdf_path: str, pdf_name: str) -> Dict:
        """Execute a parser file"""
        
        try:
            output_path = self.output_dir / f"{pdf_name}_parsed.xlsx"
            
            # Load parser module
            spec = importlib.util.spec_from_file_location("custom_parser", parser_file)
            parser_module = importlib.util.module_from_spec(spec)
            sys.modules["custom_parser"] = parser_module
            spec.loader.exec_module(parser_module)
            
            # Execute parse function
            result = parser_module.parse(pdf_path, str(output_path))
            
            return result
            
        except Exception as e:
            logger.error(f"Parser execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_accuracy(self, result: Dict) -> Dict:
        """
        Calculate parsing accuracy (0-100%)
        
        Formula:
        - Basic success: 30 points (parser ran successfully)
        - Table quality: 40 points (rows extracted, columns identified)
        - Text extraction: 20 points (non-empty cells)
        - Data quality: 10 points (proper data types, no corruption)
        
        Total: 100 points
        """
        
        accuracy = {
            'basic_success': 0,
            'table_quality': 0,
            'text_extraction': 0,
            'data_quality': 0,
            'total': 0
        }
        
        # Basic success (30 points)
        if result.get('success'):
            accuracy['basic_success'] = 30
        else:
            return accuracy  # Return 0 if not successful
        
        # Check if output file exists
        output_file = result.get('output_file')
        if not output_file or not Path(output_file).exists():
            accuracy['total'] = accuracy['basic_success']
            return accuracy
        
        try:
            # Load the parsed data
            df = pd.read_excel(output_file)
            
            # Table quality (40 points)
            rows = len(df)
            cols = len(df.columns)
            
            if rows > 0:
                # Points for having data
                accuracy['table_quality'] += 10
                
                # Points based on number of rows (up to 15 points)
                if rows >= 50:
                    accuracy['table_quality'] += 15
                elif rows >= 20:
                    accuracy['table_quality'] += 10
                elif rows >= 5:
                    accuracy['table_quality'] += 5
                
                # Points based on number of columns (up to 15 points)
                if cols >= 10:
                    accuracy['table_quality'] += 15
                elif cols >= 5:
                    accuracy['table_quality'] += 10
                elif cols >= 2:
                    accuracy['table_quality'] += 5
            
            # Text extraction (20 points)
            total_cells = rows * cols
            if total_cells > 0:
                non_empty_cells = df.count().sum()
                fill_rate = non_empty_cells / total_cells
                accuracy['text_extraction'] = int(fill_rate * 20)
            
            # Data quality (10 points)
            quality_score = 0
            
            # Check for proper column names (not all "Unnamed")
            unnamed_cols = sum(1 for col in df.columns if 'Unnamed' in str(col))
            if unnamed_cols < cols * 0.5:
                quality_score += 3
            
            # Check for data variety (not all same value)
            unique_values = sum(df[col].nunique() for col in df.columns)
            if unique_values > cols:
                quality_score += 3
            
            # Check for reasonable data types
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                quality_score += 2
            
            # Check for no excessive NaN
            nan_rate = df.isna().sum().sum() / total_cells if total_cells > 0 else 1
            if nan_rate < 0.5:
                quality_score += 2
            
            accuracy['data_quality'] = quality_score
            
        except Exception as e:
            logger.warning(f"Accuracy calculation error: {str(e)}")
            # Keep basic success points
        
        # Calculate total
        accuracy['total'] = (
            accuracy['basic_success'] +
            accuracy['table_quality'] +
            accuracy['text_extraction'] +
            accuracy['data_quality']
        )
        
        # Ensure within bounds
        accuracy['total'] = max(0, min(100, accuracy['total']))
        
        return accuracy
    
    def list_custom_parsers(self) -> list:
        """List all saved custom parsers"""
        
        if not self.custom_parsers_dir.exists():
            return []
        
        parser_files = list(self.custom_parsers_dir.glob("*.py"))
        
        parsers = []
        for parser_file in parser_files:
            if parser_file.stem.startswith('temp_'):
                continue  # Skip temp files
                
            stat = parser_file.stat()
            parsers.append({
                'name': parser_file.stem,
                'path': str(parser_file),
                'created': datetime.fromtimestamp(stat.st_mtime),
                'size': stat.st_size
            })
        
        return sorted(parsers, key=lambda x: x['created'], reverse=True)
    
    def delete_custom_parser(self, parser_name: str) -> bool:
        """Delete a custom parser"""
        
        parser_path = self.custom_parsers_dir / f"{parser_name}.py"
        
        if parser_path.exists():
            parser_path.unlink()
            logger.info(f"Deleted parser: {parser_name}")
            return True
        
        return False
