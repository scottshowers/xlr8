"""
Adaptive PDF Register Parser
Tries multiple libraries and strategies to extract tables from any payroll register PDF
"""

import pandas as pd
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import os

logger = logging.getLogger(__name__)


class AdaptiveRegisterParser:
    """
    Adaptive parser that tries multiple extraction strategies until success.
    Strategies are ordered from most accurate to least accurate.
    """
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.successful_strategy = None
        self.tables = []
        
    def parse(self) -> Tuple[bool, List[pd.DataFrame], str]:
        """
        Try all strategies until one works.
        
        Returns:
            (success, tables, strategy_name)
        """
        strategies = [
            self._try_pdfplumber,
            self._try_tabula,
            self._try_pymupdf4llm,
            self._try_pymupdf_fitz,
            self._try_pypdfium2,
            self._try_ocr
        ]
        
        for strategy in strategies:
            try:
                logger.info(f"Trying strategy: {strategy.__name__}")
                success, tables, strategy_name = strategy()
                
                if success and tables:
                    self.tables = tables
                    self.successful_strategy = strategy_name
                    logger.info(f"✅ SUCCESS with {strategy_name}: {len(tables)} tables extracted")
                    return True, tables, strategy_name
                else:
                    logger.info(f"❌ {strategy_name} failed or found no tables")
                    
            except Exception as e:
                logger.warning(f"Strategy {strategy.__name__} crashed: {e}")
                continue
        
        logger.error("All strategies failed")
        return False, [], "All strategies failed"
    
    def _try_pdfplumber(self) -> Tuple[bool, List[pd.DataFrame], str]:
        """Try pdfplumber with multiple configurations."""
        try:
            import pdfplumber
        except ImportError:
            logger.warning("pdfplumber not installed")
            return False, [], "pdfplumber (not installed)"
        
        tables_found = []
        
        # Strategy 1: Default settings
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    page_tables = page.extract_tables()
                    for table in page_tables:
                        if table:
                            df = pd.DataFrame(table[1:], columns=table[0])
                            if not df.empty:
                                tables_found.append(df)
            
            if tables_found:
                return True, tables_found, "pdfplumber (default)"
        except Exception as e:
            logger.debug(f"pdfplumber default failed: {e}")
        
        # Strategy 2: Explicit table settings
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                table_settings = {
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines"
                }
                for page in pdf.pages:
                    page_tables = page.extract_tables(table_settings)
                    for table in page_tables:
                        if table:
                            df = pd.DataFrame(table[1:], columns=table[0])
                            if not df.empty:
                                tables_found.append(df)
            
            if tables_found:
                return True, tables_found, "pdfplumber (lines strategy)"
        except Exception as e:
            logger.debug(f"pdfplumber lines strategy failed: {e}")
        
        # Strategy 3: Text-based detection
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                table_settings = {
                    "vertical_strategy": "text",
                    "horizontal_strategy": "text"
                }
                for page in pdf.pages:
                    page_tables = page.extract_tables(table_settings)
                    for table in page_tables:
                        if table:
                            df = pd.DataFrame(table[1:], columns=table[0])
                            if not df.empty:
                                tables_found.append(df)
            
            if tables_found:
                return True, tables_found, "pdfplumber (text strategy)"
        except Exception as e:
            logger.debug(f"pdfplumber text strategy failed: {e}")
        
        return False, [], "pdfplumber (all variations failed)"
    
    def _try_tabula(self) -> Tuple[bool, List[pd.DataFrame], str]:
        """Try tabula-py with multiple configurations."""
        try:
            import tabula
        except ImportError:
            logger.warning("tabula-py not installed")
            return False, [], "tabula-py (not installed)"
        
        # Strategy 1: Lattice mode (for bordered tables)
        try:
            tables = tabula.read_pdf(self.pdf_path, pages='all', lattice=True, multiple_tables=True)
            if tables and len(tables) > 0:
                valid_tables = [t for t in tables if not t.empty]
                if valid_tables:
                    return True, valid_tables, "tabula (lattice mode)"
        except Exception as e:
            logger.debug(f"tabula lattice mode failed: {e}")
        
        # Strategy 2: Stream mode (for non-bordered tables)
        try:
            tables = tabula.read_pdf(self.pdf_path, pages='all', stream=True, multiple_tables=True)
            if tables and len(tables) > 0:
                valid_tables = [t for t in tables if not t.empty]
                if valid_tables:
                    return True, valid_tables, "tabula (stream mode)"
        except Exception as e:
            logger.debug(f"tabula stream mode failed: {e}")
        
        # Strategy 3: Guess mode (auto-detect)
        try:
            tables = tabula.read_pdf(self.pdf_path, pages='all', guess=True, multiple_tables=True)
            if tables and len(tables) > 0:
                valid_tables = [t for t in tables if not t.empty]
                if valid_tables:
                    return True, valid_tables, "tabula (guess mode)"
        except Exception as e:
            logger.debug(f"tabula guess mode failed: {e}")
        
        return False, [], "tabula (all variations failed)"
    
    def _try_pymupdf4llm(self) -> Tuple[bool, List[pd.DataFrame], str]:
        """Try pymupdf4llm with multiple configurations."""
        try:
            import pymupdf4llm
        except ImportError:
            logger.warning("pymupdf4llm not installed")
            return False, [], "pymupdf4llm (not installed)"
        
        import re
        
        def parse_markdown_tables(markdown_text: str) -> List[pd.DataFrame]:
            """Parse markdown tables into DataFrames."""
            dataframes = []
            lines = markdown_text.split('\n')
            table_blocks = []
            current_block = []
            in_table = False
            
            for line in lines:
                if re.match(r'\s*\|[\s\-:|]+\|', line):
                    in_table = True
                    if current_block:
                        current_block.append(line)
                elif in_table and '|' in line:
                    current_block.append(line)
                elif in_table and '|' not in line:
                    if current_block:
                        table_blocks.append(current_block)
                        current_block = []
                    in_table = False
                elif not in_table and '|' in line and len(line.strip()) > 3:
                    current_block = [line]
            
            if current_block:
                table_blocks.append(current_block)
            
            for block in table_blocks:
                if len(block) < 2:
                    continue
                
                header_line = block[0]
                headers = [h.strip() for h in header_line.split('|') if h.strip()]
                
                data_lines = [l for l in block[2:] if '|' in l and not re.match(r'\s*\|[\s\-:|]+\|', l)]
                
                rows = []
                for line in data_lines:
                    cells = [c.strip() for c in line.split('|') if c.strip() or c == '']
                    cells = [c if c else '' for c in cells]
                    if len(cells) == len(headers):
                        rows.append(cells)
                
                if rows:
                    df = pd.DataFrame(rows, columns=headers)
                    dataframes.append(df)
            
            return dataframes
        
        # Strategy 1: Standard extraction
        try:
            md_text = pymupdf4llm.to_markdown(
                self.pdf_path,
                page_chunks=False,
                write_images=False,
                show_progress=False
            )
            tables = parse_markdown_tables(md_text)
            if tables:
                return True, tables, "pymupdf4llm (standard)"
        except Exception as e:
            logger.debug(f"pymupdf4llm standard failed: {e}")
        
        # Strategy 2: With page chunks
        try:
            md_text = pymupdf4llm.to_markdown(
                self.pdf_path,
                page_chunks=True,
                write_images=False,
                show_progress=False
            )
            tables = parse_markdown_tables(md_text)
            if tables:
                return True, tables, "pymupdf4llm (page chunks)"
        except Exception as e:
            logger.debug(f"pymupdf4llm page chunks failed: {e}")
        
        return False, [], "pymupdf4llm (all variations failed)"
    
    def _try_pymupdf_fitz(self) -> Tuple[bool, List[pd.DataFrame], str]:
        """Try pymupdf (fitz) with table extraction."""
        try:
            import fitz
        except ImportError:
            logger.warning("pymupdf (fitz) not installed")
            return False, [], "pymupdf (not installed)"
        
        tables_found = []
        
        # Strategy 1: Find tables method (if available)
        try:
            doc = fitz.open(self.pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Try to find tables
                if hasattr(page, 'find_tables'):
                    tables = page.find_tables()
                    if tables:
                        for table in tables:
                            try:
                                table_data = table.extract()
                                if table_data and len(table_data) > 1:
                                    df = pd.DataFrame(table_data[1:], columns=table_data[0])
                                    if not df.empty:
                                        tables_found.append(df)
                            except:
                                continue
            
            doc.close()
            
            if tables_found:
                return True, tables_found, "pymupdf fitz (find_tables)"
        except Exception as e:
            logger.debug(f"pymupdf fitz find_tables failed: {e}")
        
        # Strategy 2: Text extraction with structure
        try:
            doc = fitz.open(self.pdf_path)
            all_text = []
            
            for page in doc:
                text = page.get_text("text")
                all_text.append(text)
            
            doc.close()
            
            # Try to parse structured text into table
            full_text = "\n".join(all_text)
            if full_text.strip():
                # Simple heuristic: if lines have consistent delimiters, try to parse
                lines = full_text.split('\n')
                # Look for consistent pipe or tab delimiters
                # This is basic - could be enhanced
                pass  # Would need more sophisticated parsing here
        except Exception as e:
            logger.debug(f"pymupdf fitz text extraction failed: {e}")
        
        return False, [], "pymupdf (all variations failed)"
    
    def _try_pypdfium2(self) -> Tuple[bool, List[pd.DataFrame], str]:
        """Try pypdfium2 extraction."""
        try:
            import pypdfium2 as pdfium
        except ImportError:
            logger.warning("pypdfium2 not installed")
            return False, [], "pypdfium2 (not installed)"
        
        # pypdfium2 is primarily for rendering, not table extraction
        # Would need additional logic to detect tables from rendered output
        # Skipping for now - better handled by OCR if needed
        
        return False, [], "pypdfium2 (not implemented for tables)"
    
    def _try_ocr(self) -> Tuple[bool, List[pd.DataFrame], str]:
        """Try OCR as last resort for scanned PDFs."""
        try:
            import pytesseract
            from PIL import Image
            import fitz
        except ImportError:
            logger.warning("pytesseract or PIL not installed")
            return False, [], "OCR (dependencies not installed)"
        
        # Convert PDF pages to images and OCR
        # This is expensive and should be last resort
        # Skipping detailed implementation for now
        
        logger.info("OCR would be attempted here (not yet implemented)")
        return False, [], "OCR (not implemented)"
    
    def save_to_excel(self, output_path: str) -> str:
        """Save extracted tables to Excel."""
        if not self.tables:
            raise ValueError("No tables to save")
        
        if len(self.tables) == 1:
            self.tables[0].to_excel(output_path, index=False, engine='openpyxl')
        else:
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                for idx, df in enumerate(self.tables):
                    sheet_name = f"Table_{idx + 1}"
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        return output_path


def extract_register_adaptive(pdf_path: str, output_dir: str) -> Dict[str, Any]:
    """
    Adaptive extraction - tries multiple strategies.
    
    Returns:
        Dict with success, excel_path, table_count, strategy_used
    """
    try:
        parser = AdaptiveRegisterParser(pdf_path)
        success, tables, strategy = parser.parse()
        
        if not success or not tables:
            return {
                'success': False,
                'error': 'No tables found with any extraction method',
                'strategy_tried': strategy
            }
        
        # Generate output path
        pdf_name = Path(pdf_path).stem
        output_path = Path(output_dir) / f"{pdf_name}_parsed.xlsx"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save
        parser.save_to_excel(str(output_path))
        
        # Get table info
        table_info = []
        for idx, df in enumerate(tables):
            table_info.append({
                'table_number': idx + 1,
                'rows': len(df),
                'columns': len(df.columns),
                'headers': list(df.columns)
            })
        
        return {
            'success': True,
            'excel_path': str(output_path),
            'table_count': len(tables),
            'table_info': table_info,
            'strategy_used': strategy
        }
        
    except Exception as e:
        logger.error(f"Adaptive extraction failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }
