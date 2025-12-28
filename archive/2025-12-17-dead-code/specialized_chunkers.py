"""
Specialized Chunkers - Universal Document Intelligence System
==============================================================

Phase 2: Type-specific chunking strategies

Each chunker knows how to handle its document type optimally.

Author: XLR8 Team
"""

from typing import List, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)


class ChunkResult:
    """Standardized chunk output"""
    
    def __init__(self, text: str, metadata: Dict[str, Any]):
        self.text = text
        self.metadata = metadata
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'text': self.text,
            **self.metadata
        }


class TableChunker:
    """
    Adaptive table chunker for tabular data
    
    Handles: Excel, CSV, TSV, data tables
    """
    
    def chunk(self, text: str, strategy: Dict, filename: str) -> List[ChunkResult]:
        """
        Chunk tabular data adaptively based on row count
        
        Strategy includes: rows_per_chunk, preserve_headers, multi_sheet
        """
        chunks = []
        
        # Handle multi-sheet documents
        if strategy.get('multi_sheet'):
            sheets = self._split_by_sheets(text)
            
            for sheet_info in sheets:
                sheet_chunks = self._chunk_sheet(
                    sheet_info['text'],
                    sheet_info['name'],
                    sheet_info.get('header'),
                    strategy
                )
                chunks.extend(sheet_chunks)
        else:
            # Single table
            chunks = self._chunk_sheet(text, filename, None, strategy)
        
        logger.info(f"[TABLE] Created {len(chunks)} chunks")
        return chunks
    
    def _split_by_sheets(self, text: str) -> List[Dict]:
        """Split multi-sheet text into individual sheets"""
        sheets = []
        sheet_pattern = re.compile(r'\[SHEET:\s*(.+?)\]', re.I)
        
        matches = list(sheet_pattern.finditer(text))
        
        for i, match in enumerate(matches):
            name = match.group(1).strip()
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            
            sheet_text = text[start:end]
            
            # Extract header
            header = None
            for line in sheet_text.split('\n'):
                if line.strip().startswith('Columns:'):
                    header = line.strip()
                    break
            
            sheets.append({'name': name, 'text': sheet_text, 'header': header})
        
        return sheets
    
    def _chunk_sheet(
        self, 
        text: str, 
        sheet_name: str, 
        header: str,
        strategy: Dict
    ) -> List[ChunkResult]:
        """Chunk a single sheet/table"""
        lines = text.split('\n')
        rows_per_chunk = strategy['rows_per_chunk']
        
        # Analyze data rows
        data_rows = []
        for line in lines:
            is_data = (
                line.strip() and
                not line.startswith('[') and
                not line.startswith('Columns:') and
                not line.startswith('---') and
                (':' in line or '|' in line)
            )
            if is_data:
                data_rows.append(line)
        
        logger.info(f"  Sheet '{sheet_name}': {len(data_rows)} data rows → {rows_per_chunk} rows/chunk")
        
        # Chunk the data rows
        chunks = []
        for i in range(0, len(data_rows), rows_per_chunk):
            chunk_rows = data_rows[i:i + rows_per_chunk]
            
            # Build chunk text
            chunk_parts = []
            
            # Always include sheet name for searchability
            if sheet_name:
                chunk_parts.append(f"[SHEET: {sheet_name}]")
            
            # Include header for context
            if header and strategy.get('preserve_headers'):
                chunk_parts.append(header)
            
            # Add data rows
            chunk_parts.extend(chunk_rows)
            
            chunk_text = '\n'.join(chunk_parts)
            
            chunks.append(ChunkResult(
                text=chunk_text,
                metadata={
                    'parent_section': sheet_name,
                    'chunk_type': 'table',
                    'has_header': header is not None,
                    'row_start': i,
                    'row_end': min(i + rows_per_chunk, len(data_rows))
                }
            ))
        
        return chunks


class CodeChunker:
    """
    Code-aware chunker that respects function/class boundaries
    
    Handles: Python, JavaScript, Java, C++, etc.
    """
    
    def chunk(self, text: str, strategy: Dict, filename: str) -> List[ChunkResult]:
        """
        Chunk code by function/class boundaries
        
        Strategy includes: chunk_on, max_lines, preserve_imports
        """
        lines = text.split('\n')
        chunks = []
        
        # Track imports
        imports = []
        if strategy.get('preserve_imports'):
            for line in lines[:50]:  # Imports usually at top
                if re.match(r'^(import|from|#include|using|package)', line.strip()):
                    imports.append(line)
        
        # Find function/class boundaries
        boundaries = self._find_boundaries(lines, strategy['chunk_on'])
        
        # Chunk between boundaries
        for i in range(len(boundaries)):
            start = boundaries[i]
            end = boundaries[i + 1] if i + 1 < len(boundaries) else len(lines)
            
            # Limit chunk size
            if end - start > strategy.get('max_lines', 100):
                end = start + strategy['max_lines']
            
            chunk_lines = lines[start:end]
            
            # Include imports at top
            if imports and i == 0:
                chunk_text = '\n'.join(imports + [''] + chunk_lines)
            else:
                chunk_text = '\n'.join(chunk_lines)
            
            # Extract function/class name for metadata
            func_name = self._extract_name(lines[start])
            
            chunks.append(ChunkResult(
                text=chunk_text,
                metadata={
                    'parent_section': func_name or filename,
                    'chunk_type': 'code',
                    'has_imports': len(imports) > 0,
                    'line_start': start,
                    'line_end': end
                }
            ))
        
        logger.info(f"[CODE] Created {len(chunks)} chunks ({len(boundaries)} functions/classes)")
        return chunks
    
    def _find_boundaries(self, lines: List[str], patterns: List[str]) -> List[int]:
        """Find function/class definition lines"""
        boundaries = []
        pattern = re.compile(r'^(' + '|'.join(patterns) + r')\s+')
        
        for i, line in enumerate(lines):
            if pattern.match(line.strip()):
                boundaries.append(i)
        
        return boundaries if boundaries else [0]
    
    def _extract_name(self, line: str) -> str:
        """Extract function/class name from definition line"""
        match = re.search(r'(def|class|function)\s+(\w+)', line)
        return match.group(2) if match else None


class HierarchicalChunker:
    """
    Section-based chunker for hierarchical documents
    
    Handles: Documentation, books, reports with sections
    """
    
    def chunk(self, text: str, strategy: Dict, filename: str) -> List[ChunkResult]:
        """
        Chunk by section hierarchy
        
        Strategy includes: chunk_size, overlap, preserve_hierarchy
        """
        chunks = []
        
        # Find all section headers
        sections = self._find_sections(text)
        
        if not sections:
            # No sections found, fall back to size-based
            return self._chunk_by_size(text, strategy, filename)
        
        # Chunk between sections
        for i, (level, title, start_pos) in enumerate(sections):
            end_pos = sections[i + 1][2] if i + 1 < len(sections) else len(text)
            
            section_text = text[start_pos:end_pos]
            
            # If section too large, sub-chunk it
            if len(section_text) > strategy['chunk_size'] * 2:
                sub_chunks = self._chunk_by_size(section_text, strategy, title)
                chunks.extend(sub_chunks)
            else:
                # Include parent context if requested
                context = f"[SECTION: {title}]\n" if strategy.get('include_parent_sections') else ""
                
                chunks.append(ChunkResult(
                    text=context + section_text,
                    metadata={
                        'parent_section': title,
                        'chunk_type': 'section',
                        'hierarchy_level': level
                    }
                ))
        
        logger.info(f"[HIERARCHICAL] Created {len(chunks)} chunks ({len(sections)} sections)")
        return chunks
    
    def _find_sections(self, text: str) -> List[tuple]:
        """Find section headers with hierarchy level"""
        sections = []
        
        # Markdown headers
        for match in re.finditer(r'^(#{1,6})\s+(.+)$', text, re.M):
            level = len(match.group(1))
            title = match.group(2).strip()
            sections.append((level, title, match.start()))
        
        # ALL CAPS headers
        for match in re.finditer(r'^([A-Z][A-Z\s]{4,}):?\s*$', text, re.M):
            title = match.group(1).strip()
            sections.append((1, title, match.start()))
        
        # Numbered sections
        for match in re.finditer(r'^(\d+\.\s+[A-Z].+)$', text, re.M):
            title = match.group(1).strip()
            sections.append((2, title, match.start()))
        
        return sorted(sections, key=lambda x: x[2])  # Sort by position
    
    def _chunk_by_size(self, text: str, strategy: Dict, section_name: str) -> List[ChunkResult]:
        """Fallback size-based chunking"""
        chunk_size = strategy['chunk_size']
        overlap = strategy.get('overlap', 0)
        chunks = []
        
        pos = 0
        while pos < len(text):
            end = min(pos + chunk_size, len(text))
            chunk_text = text[pos:end]
            
            chunks.append(ChunkResult(
                text=chunk_text,
                metadata={
                    'parent_section': section_name,
                    'chunk_type': 'content'
                }
            ))
            
            pos = end - overlap if end < len(text) else len(text)
        
        return chunks


class HybridChunker:
    """
    Hybrid chunker for mixed-structure documents (PDFs, complex Word docs)
    
    Handles tables AND sections together
    """
    
    def __init__(self):
        self.table_chunker = TableChunker()
        self.hierarchical_chunker = HierarchicalChunker()
    
    def chunk(self, text: str, strategy: Dict, filename: str) -> List[ChunkResult]:
        """
        Smart hybrid chunking - detect and route to appropriate sub-chunker
        """
        chunks = []
        
        # Split text into segments (tables vs text)
        segments = self._segment_document(text)
        
        for seg_type, seg_text in segments:
            if seg_type == 'table':
                # Use table chunker
                table_chunks = self.table_chunker._chunk_sheet(
                    seg_text,
                    'table-section',
                    None,
                    {'rows_per_chunk': 5, 'preserve_headers': True}
                )
                chunks.extend(table_chunks)
            else:
                # Use hierarchical/semantic chunker
                text_chunks = self.hierarchical_chunker._chunk_by_size(
                    seg_text,
                    strategy,
                    'text-section'
                )
                chunks.extend(text_chunks)
        
        logger.info(f"[HYBRID] Created {len(chunks)} chunks ({len(segments)} segments)")
        return chunks
    
    def _segment_document(self, text: str) -> List[tuple]:
        """Split document into table and text segments"""
        segments = []
        current_type = None
        current_text = []
        
        for line in text.split('\n'):
            # Detect if line is part of table
            is_table_line = bool(re.search(r'\||:.*:|\t.*\t', line))
            
            if is_table_line:
                line_type = 'table'
            else:
                line_type = 'text'
            
            # If type changes, save current segment
            if current_type and current_type != line_type:
                segments.append((current_type, '\n'.join(current_text)))
                current_text = []
            
            current_type = line_type
            current_text.append(line)
        
        # Save final segment
        if current_text:
            segments.append((current_type, '\n'.join(current_text)))
        
        return segments


class SemanticChunker:
    """
    Semantic chunker for linear text (articles, blog posts)
    
    Respects paragraph and sentence boundaries
    """
    
    def chunk(self, text: str, strategy: Dict, filename: str) -> List[ChunkResult]:
        """
        Chunk by paragraphs with sentence boundary awareness
        """
        chunk_size = strategy['chunk_size']
        overlap = strategy.get('overlap', 0)
        chunks = []
        
        # Split into paragraphs
        paragraphs = re.split(r'\n\s*\n+', text)
        
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            # If adding this paragraph exceeds size, save chunk
            if current_size + para_size > chunk_size and current_chunk:
                chunk_text = '\n\n'.join(current_chunk)
                chunks.append(ChunkResult(
                    text=chunk_text,
                    metadata={
                        'parent_section': filename,
                        'chunk_type': 'semantic'
                    }
                ))
                
                # Start new chunk with overlap
                if overlap > 0 and current_chunk:
                    current_chunk = [current_chunk[-1]]  # Keep last paragraph
                    current_size = len(current_chunk[0])
                else:
                    current_chunk = []
                    current_size = 0
            
            current_chunk.append(para)
            current_size += para_size
        
        # Save final chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append(ChunkResult(
                text=chunk_text,
                metadata={
                    'parent_section': filename,
                    'chunk_type': 'semantic'
                }
            ))
        
        logger.info(f"[SEMANTIC] Created {len(chunks)} chunks")
        return chunks
