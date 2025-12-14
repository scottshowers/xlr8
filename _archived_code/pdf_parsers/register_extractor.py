"""
Payroll Register PDF Extractor
Extracts tables from payroll register PDFs to Excel with zero transformations
"""

import pymupdf4llm
import pandas as pd
import re
from typing import List, Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PayrollPDFExtractor:
    """Extract payroll data from PDF using pymupdf4llm with zero transformations."""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.raw_markdown = None
        self.tables = []
        
    def extract_to_markdown(self) -> str:
        """Extract PDF content to markdown format."""
        self.raw_markdown = pymupdf4llm.to_markdown(self.pdf_path)
        return self.raw_markdown
    
    def extract_tables(self) -> List[pd.DataFrame]:
        """
        Extract all tables from the PDF.
        Returns list of DataFrames, one per table found.
        """
        try:
            # Extract with table detection
            md_text = pymupdf4llm.to_markdown(
                self.pdf_path,
                page_chunks=False,
                write_images=False,
                show_progress=False
            )
            
            # Parse markdown tables
            tables = self._parse_markdown_tables(md_text)
            self.tables = tables
            
            logger.info(f"Extracted {len(tables)} tables from {self.pdf_path}")
            return tables
            
        except Exception as e:
            logger.error(f"Error extracting tables: {e}")
            return []
    
    def _parse_markdown_tables(self, markdown_text: str) -> List[pd.DataFrame]:
        """Parse markdown tables into pandas DataFrames."""
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
            df = self._block_to_dataframe(block)
            if df is not None and not df.empty:
                dataframes.append(df)
        
        return dataframes
    
    def _block_to_dataframe(self, lines: List[str]) -> pd.DataFrame:
        """Convert markdown table block to DataFrame."""
        if len(lines) < 2:
            return None
        
        header_line = lines[0]
        headers = [h.strip() for h in header_line.split('|') if h.strip()]
        
        data_lines = [l for l in lines[2:] if '|' in l and not re.match(r'\s*\|[\s\-:|]+\|', l)]
        
        rows = []
        for line in data_lines:
            cells = [c.strip() for c in line.split('|') if c.strip() or c == '']
            cells = [c if c else '' for c in cells]
            if len(cells) == len(headers):
                rows.append(cells)
        
        if not rows:
            return None
        
        df = pd.DataFrame(rows, columns=headers)
        return df
    
    def save_to_excel(self, output_path: str, table_index: int = 0) -> str:
        """Save extracted table to Excel with NO modifications."""
        if not self.tables:
            self.extract_tables()
        
        if table_index >= len(self.tables):
            raise IndexError(f"Table index {table_index} not found. Only {len(self.tables)} tables extracted.")
        
        df = self.tables[table_index]
        df.to_excel(output_path, index=False, engine='openpyxl')
        
        logger.info(f"Saved {len(df)} rows, {len(df.columns)} columns to {output_path}")
        return output_path
    
    def save_all_tables(self, output_path: str) -> str:
        """Save all tables to separate sheets in one Excel file."""
        if not self.tables:
            self.extract_tables()
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for idx, df in enumerate(self.tables):
                sheet_name = f"Table_{idx + 1}"
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                logger.info(f"Sheet '{sheet_name}': {len(df)} rows, {len(df.columns)} columns")
        
        logger.info(f"Saved {len(self.tables)} tables to {output_path}")
        return output_path
    
    def get_table_info(self) -> List[Dict[str, Any]]:
        """Get information about extracted tables."""
        if not self.tables:
            self.extract_tables()
        
        info = []
        for idx, df in enumerate(self.tables):
            info.append({
                'table_number': idx + 1,
                'rows': len(df),
                'columns': len(df.columns),
                'headers': list(df.columns)
            })
        return info


def extract_register_to_excel(pdf_path: str, output_dir: str) -> Dict[str, Any]:
    """
    Extract payroll register PDF and save to Excel.
    
    Args:
        pdf_path: Path to PDF file
        output_dir: Directory to save Excel file
        
    Returns:
        Dict with status, excel_path, and table info
    """
    try:
        extractor = PayrollPDFExtractor(pdf_path)
        tables = extractor.extract_tables()
        
        if not tables:
            return {
                'success': False,
                'error': 'No tables found in PDF'
            }
        
        # Generate output path
        pdf_name = Path(pdf_path).stem
        output_path = Path(output_dir) / f"{pdf_name}_parsed.xlsx"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save
        if len(tables) == 1:
            extractor.save_to_excel(str(output_path))
        else:
            extractor.save_all_tables(str(output_path))
        
        return {
            'success': True,
            'excel_path': str(output_path),
            'table_count': len(tables),
            'table_info': extractor.get_table_info()
        }
        
    except Exception as e:
        logger.error(f"Register extraction failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }
