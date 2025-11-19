"""
Enhanced Intelligent Parser Orchestrator
Handles complex multi-section PDFs with iterative parsing
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import importlib
import sys
from datetime import datetime

logger = logging.getLogger(__name__)


class IntelligentParserOrchestrator:
    """
    Orchestrates 3-stage parsing with support for complex multi-section documents.
    
    Stage 1: Custom parsers (saved from previous successes)
    Stage 2: Built-in specialized parsers (Dayforce, ADP, etc.)
    Stage 3: Adaptive parsers (general purpose)
    Stage 4: Generated parsers (analyze and create new parser)
    """
    
    def __init__(self):
        self.custom_parsers_dir = Path('/data/custom_parsers')
        self.custom_parsers_dir.mkdir(parents=True, exist_ok=True)
        
        self.parsed_output_dir = Path('/data/parsed_registers')
        self.parsed_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Built-in specialized parsers
        self.specialized_parsers = {
            'dayforce': 'utils.parsers.dayforce_parser_enhanced',
            'adp': None,  # Future
            'paychex': None,  # Future
        }
    
    def parse(self, pdf_path: str, document_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Intelligently parse PDF using 4-stage approach.
        
        Args:
            pdf_path: Path to PDF file
            document_type: Optional hint ('dayforce', 'adp', etc.)
            
        Returns:
            Dict with status, output_path, accuracy, stage_used, etc.
        """
        logger.info(f"Starting intelligent parse of: {pdf_path}")
        
        result = {
            'status': 'pending',
            'pdf_path': pdf_path,
            'stages_attempted': [],
            'stage_used': None,
            'output_path': None,
            'accuracy': 0,
            'employee_count': 0,
            'errors': []
        }
        
        try:
            # Stage 1: Try custom parsers (if any exist)
            stage1_result = self._try_custom_parsers(pdf_path)
            result['stages_attempted'].append({
                'stage': 1,
                'name': 'Custom Parsers',
                'attempted': stage1_result['attempted'],
                'success': stage1_result['success'],
                'accuracy': stage1_result.get('accuracy', 0)
            })
            
            if stage1_result['success'] and stage1_result.get('accuracy', 0) >= 70:
                logger.info(f"Stage 1 success with {stage1_result['accuracy']}% accuracy")
                result.update(stage1_result)
                result['stage_used'] = 1
                return result
            
            # Stage 2: Try specialized parsers (Dayforce, ADP, etc.)
            stage2_result = self._try_specialized_parsers(pdf_path, document_type)
            result['stages_attempted'].append({
                'stage': 2,
                'name': 'Specialized Parsers',
                'attempted': stage2_result['attempted'],
                'success': stage2_result['success'],
                'accuracy': stage2_result.get('accuracy', 0)
            })
            
            if stage2_result['success'] and stage2_result.get('accuracy', 0) >= 70:
                logger.info(f"Stage 2 success with {stage2_result['accuracy']}% accuracy")
                result.update(stage2_result)
                result['stage_used'] = 2
                
                # Offer to save as custom parser
                if stage2_result.get('accuracy', 0) >= 80:
                    result['save_recommended'] = True
                    result['save_reason'] = 'High accuracy specialized parser'
                
                return result
            
            # Stage 3: Try adaptive parsers (general purpose)
            stage3_result = self._try_adaptive_parsers(pdf_path)
            result['stages_attempted'].append({
                'stage': 3,
                'name': 'Adaptive Parsers',
                'attempted': stage3_result['attempted'],
                'success': stage3_result['success'],
                'accuracy': stage3_result.get('accuracy', 0)
            })
            
            if stage3_result['success'] and stage3_result.get('accuracy', 0) >= 60:
                logger.info(f"Stage 3 success with {stage3_result['accuracy']}% accuracy")
                result.update(stage3_result)
                result['stage_used'] = 3
                return result
            
            # Stage 4: Generate custom parser (analyze structure and create)
            stage4_result = self._generate_custom_parser(pdf_path)
            result['stages_attempted'].append({
                'stage': 4,
                'name': 'Generated Parser',
                'attempted': stage4_result['attempted'],
                'success': stage4_result['success'],
                'accuracy': stage4_result.get('accuracy', 0)
            })
            
            if stage4_result['success']:
                logger.info(f"Stage 4 success with {stage4_result['accuracy']}% accuracy")
                result.update(stage4_result)
                result['stage_used'] = 4
                
                # Auto-save if accuracy is high
                if stage4_result.get('accuracy', 0) >= 70:
                    result['save_recommended'] = True
                    result['save_reason'] = 'Generated parser achieved good accuracy'
                
                return result
            
            # All stages failed
            result['status'] = 'error'
            result['message'] = 'All parsing stages failed'
            return result
            
        except Exception as e:
            logger.error(f"Orchestrator error: {str(e)}", exc_info=True)
            result['status'] = 'error'
            result['message'] = str(e)
            result['errors'].append(str(e))
            return result
    
    def _try_custom_parsers(self, pdf_path: str) -> Dict[str, Any]:
        """
        Stage 1: Try all saved custom parsers.
        """
        result = {
            'attempted': False,
            'success': False,
            'parser_name': None
        }
        
        # Get list of custom parsers
        parser_files = list(self.custom_parsers_dir.glob('*.py'))
        
        if not parser_files:
            logger.info("No custom parsers available")
            return result
        
        result['attempted'] = True
        
        # Try each parser
        for parser_file in parser_files:
            try:
                logger.info(f"Trying custom parser: {parser_file.stem}")
                
                # Load parser module
                spec = importlib.util.spec_from_file_location(
                    parser_file.stem,
                    parser_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Execute parser
                if hasattr(module, 'parse'):
                    parse_result = module.parse(pdf_path, str(self.parsed_output_dir))
                    
                    if parse_result.get('status') == 'success':
                        result.update(parse_result)
                        result['success'] = True
                        result['parser_name'] = parser_file.stem
                        return result
                
            except Exception as e:
                logger.warning(f"Custom parser {parser_file.stem} failed: {str(e)}")
                continue
        
        return result
    
    def _try_specialized_parsers(self, pdf_path: str, document_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Stage 2: Try built-in specialized parsers.
        """
        result = {
            'attempted': False,
            'success': False,
            'parser_name': None
        }
        
        # If document type is specified, try that parser first
        if document_type and document_type.lower() in self.specialized_parsers:
            parser_module_name = self.specialized_parsers[document_type.lower()]
            
            if parser_module_name:
                result['attempted'] = True
                try:
                    logger.info(f"Trying specialized parser: {document_type}")
                    module = importlib.import_module(parser_module_name)
                    
                    if hasattr(module, 'parse_dayforce_register'):
                        parse_result = module.parse_dayforce_register(
                            pdf_path,
                            str(self.parsed_output_dir)
                        )
                    elif hasattr(module, 'parse'):
                        parse_result = module.parse(pdf_path, str(self.parsed_output_dir))
                    else:
                        raise AttributeError("Parser module missing parse function")
                    
                    if parse_result.get('status') == 'success':
                        result.update(parse_result)
                        result['success'] = True
                        result['parser_name'] = document_type
                        return result
                        
                except Exception as e:
                    logger.warning(f"Specialized parser {document_type} failed: {str(e)}")
        
        # Try all available specialized parsers
        for parser_name, module_name in self.specialized_parsers.items():
            if not module_name or (document_type and parser_name == document_type.lower()):
                continue  # Skip None or already tried
            
            result['attempted'] = True
            
            try:
                logger.info(f"Trying specialized parser: {parser_name}")
                module = importlib.import_module(module_name)
                
                # Call appropriate parse function
                if hasattr(module, f'parse_{parser_name}_register'):
                    parse_func = getattr(module, f'parse_{parser_name}_register')
                    parse_result = parse_func(pdf_path, str(self.parsed_output_dir))
                elif hasattr(module, 'parse'):
                    parse_result = module.parse(pdf_path, str(self.parsed_output_dir))
                else:
                    continue
                
                if parse_result.get('status') == 'success':
                    result.update(parse_result)
                    result['success'] = True
                    result['parser_name'] = parser_name
                    return result
                    
            except Exception as e:
                logger.warning(f"Specialized parser {parser_name} failed: {str(e)}")
                continue
        
        return result
    
    def _try_adaptive_parsers(self, pdf_path: str) -> Dict[str, Any]:
        """
        Stage 3: Try adaptive general-purpose parsers.
        """
        result = {
            'attempted': True,
            'success': False,
            'parser_name': None
        }
        
        try:
            # Try adaptive register parser (from utils.pdf_parsers)
            from utils.pdf_parsers import extract_register_adaptive
            
            logger.info("Trying adaptive register parser")
            parse_result = extract_register_adaptive(pdf_path, str(self.parsed_output_dir))
            
            if parse_result.get('status') == 'success':
                result.update(parse_result)
                result['success'] = True
                result['parser_name'] = 'adaptive_register'
                return result
            
        except Exception as e:
            logger.warning(f"Adaptive register parser failed: {str(e)}")
        
        try:
            # Try adaptive payroll parser
            from utils.pdf_parsers import extract_payroll_register
            
            logger.info("Trying adaptive payroll parser")
            parse_result = extract_payroll_register(pdf_path, str(self.parsed_output_dir))
            
            if parse_result.get('status') == 'success':
                result.update(parse_result)
                result['success'] = True
                result['parser_name'] = 'adaptive_payroll'
                return result
                
        except Exception as e:
            logger.warning(f"Adaptive payroll parser failed: {str(e)}")
        
        return result
    
    def _generate_custom_parser(self, pdf_path: str) -> Dict[str, Any]:
        """
        Stage 4: Analyze PDF structure and generate custom parser.
        """
        result = {
            'attempted': True,
            'success': False,
            'parser_name': None
        }
        
        try:
            # Analyze PDF structure
            from utils.parsers.pdf_structure_analyzer import PDFStructureAnalyzer
            
            logger.info("Analyzing PDF structure")
            analyzer = PDFStructureAnalyzer(pdf_path)
            structure = analyzer.analyze()
            
            if not structure.get('format_type'):
                raise ValueError("Could not detect PDF format")
            
            # Generate parser code
            from utils.parsers.parser_code_generator import ParserCodeGenerator
            
            logger.info(f"Generating parser for format: {structure['format_type']}")
            generator = ParserCodeGenerator()
            parser_code = generator.generate(structure)
            
            if not parser_code:
                raise ValueError("Could not generate parser code")
            
            # Save and execute generated parser
            temp_parser_path = self.custom_parsers_dir / f"temp_generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
            temp_parser_path.write_text(parser_code)
            
            # Execute generated parser
            spec = importlib.util.spec_from_file_location(
                temp_parser_path.stem,
                temp_parser_path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, 'parse'):
                parse_result = module.parse(pdf_path, str(self.parsed_output_dir))
                
                if parse_result.get('status') == 'success':
                    result.update(parse_result)
                    result['success'] = True
                    result['parser_name'] = 'generated'
                    result['parser_code'] = parser_code
                    result['temp_parser_path'] = str(temp_parser_path)
                    return result
            
            # Clean up temp file if failed
            if temp_parser_path.exists():
                temp_parser_path.unlink()
            
        except Exception as e:
            logger.error(f"Parser generation failed: {str(e)}", exc_info=True)
            result['errors'] = [str(e)]
        
        return result
    
    def save_parser(self, parser_name: str, parser_code: str, metadata: Optional[Dict] = None) -> bool:
        """
        Save a successful parser for future reuse.
        
        Args:
            parser_name: Name for the saved parser
            parser_code: Python code for the parser
            metadata: Optional metadata (accuracy, date, etc.)
            
        Returns:
            True if saved successfully
        """
        try:
            # Clean parser name
            safe_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in parser_name)
            parser_path = self.custom_parsers_dir / f"{safe_name}.py"
            
            # Add metadata as comments
            full_code = f'''"""
Custom Parser: {parser_name}
Generated: {datetime.now().isoformat()}
Metadata: {metadata if metadata else 'None'}
"""

{parser_code}
'''
            
            parser_path.write_text(full_code)
            logger.info(f"Saved custom parser: {safe_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save parser: {str(e)}")
            return False
    
    def list_custom_parsers(self) -> List[Dict[str, Any]]:
        """
        List all saved custom parsers.
        """
        parsers = []
        
        for parser_file in self.custom_parsers_dir.glob('*.py'):
            if parser_file.stem.startswith('temp_'):
                continue  # Skip temp files
            
            stat = parser_file.stat()
            parsers.append({
                'name': parser_file.stem,
                'path': str(parser_file),
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime)
            })
        
        return sorted(parsers, key=lambda x: x['modified'], reverse=True)
    
    def delete_parser(self, parser_name: str) -> bool:
        """
        Delete a custom parser.
        """
        try:
            parser_path = self.custom_parsers_dir / f"{parser_name}.py"
            
            if parser_path.exists():
                parser_path.unlink()
                logger.info(f"Deleted parser: {parser_name}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete parser: {str(e)}")
            return False


def parse_pdf_intelligent(pdf_path: str, document_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function for intelligent PDF parsing.
    
    Args:
        pdf_path: Path to PDF file
        document_type: Optional document type hint ('dayforce', 'adp', etc.)
        
    Returns:
        Dict with parse results
    """
    orchestrator = IntelligentParserOrchestrator()
    return orchestrator.parse(pdf_path, document_type)
