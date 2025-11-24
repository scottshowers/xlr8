"""
Enhanced Chunking System for XLR8
==================================

IMPROVEMENTS:
1. Smart Chunking - Sentence/paragraph boundary awareness
2. Adaptive Sizing - Content-aware chunk sizes
3. Enhanced Metadata - Position tracking, relationships, types
4. File Type Optimization - PDF/Excel/Word specialization

Author: XLR8 Team
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ChunkType(Enum):
    """Types of content chunks"""
    PARAGRAPH = "paragraph"
    HEADER = "header"
    TABLE_ROW = "table_row"
    LIST_ITEM = "list_item"
    CODE_BLOCK = "code_block"
    MIXED = "mixed"


@dataclass
class EnhancedChunk:
    """Enhanced chunk with metadata"""
    text: str
    chunk_index: int
    total_chunks: int
    chunk_type: ChunkType
    start_char: int
    end_char: int
    tokens_estimate: int
    parent_section: Optional[str] = None
    has_header: bool = False
    header_text: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'text': self.text,
            'chunk_index': self.chunk_index,
            'total_chunks': self.total_chunks,
            'chunk_type': self.chunk_type.value,
            'start_char': self.start_char,
            'end_char': self.end_char,
            'tokens_estimate': self.tokens_estimate,
            'parent_section': self.parent_section,
            'has_header': self.has_header,
            'header_text': self.header_text
        }


class EnhancedChunker:
    """
    Advanced document chunker with smart boundaries and adaptive sizing
    """
    
    # File-type specific configurations
    CHUNK_CONFIGS = {
        'xlsx': {'size': 2000, 'overlap': 200, 'method': 'table'},
        'xls': {'size': 2000, 'overlap': 200, 'method': 'table'},
        'csv': {'size': 2000, 'overlap': 200, 'method': 'table'},
        'pdf': {'size': 1000, 'overlap': 150, 'method': 'semantic'},
        'docx': {'size': 1000, 'overlap': 150, 'method': 'semantic'},
        'doc': {'size': 1000, 'overlap': 150, 'method': 'semantic'},
        'txt': {'size': 800, 'overlap': 100, 'method': 'semantic'},
        'md': {'size': 800, 'overlap': 100, 'method': 'semantic'}
    }
    
    def __init__(self):
        """Initialize the enhanced chunker"""
        # Sentence boundary patterns
        self.sentence_endings = re.compile(r'[.!?]+[\s\n]+|[.!?]+$')
        self.paragraph_breaks = re.compile(r'\n\s*\n+')
        
        # Header patterns (markdown, numbered, etc.)
        self.header_patterns = [
            re.compile(r'^#{1,6}\s+.+$', re.MULTILINE),  # Markdown headers
            re.compile(r'^\d+\.\s+[A-Z].+$', re.MULTILINE),  # Numbered headers
            re.compile(r'^[A-Z][A-Z\s]{3,}:?\s*$', re.MULTILINE)  # ALL CAPS headers
        ]
        
        # Table patterns
        self.table_patterns = [
            re.compile(r'\|.+\|'),  # Markdown tables
            re.compile(r'WORKSHEET:'),  # Excel worksheet markers
            re.compile(r'^[\w\s]+\t[\w\s]+\t'),  # Tab-separated
        ]
        
        logger.info("EnhancedChunker initialized")
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count (rough approximation: 1 token ≈ 4 characters)
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        return len(text) // 4
    
    def detect_chunk_type(self, text: str) -> ChunkType:
        """
        Detect the type of content in a chunk
        
        Args:
            text: Text to analyze
            
        Returns:
            ChunkType enum
        """
        text_sample = text[:500]  # Check first 500 chars
        
        # Check for headers
        for pattern in self.header_patterns:
            if pattern.search(text_sample):
                return ChunkType.HEADER
        
        # Check for tables
        for pattern in self.table_patterns:
            if pattern.search(text_sample):
                return ChunkType.TABLE_ROW
        
        # Check for code blocks
        if re.search(r'```|{|}|function\s+\w+|class\s+\w+', text_sample):
            return ChunkType.CODE_BLOCK
        
        # Check for list items
        if re.match(r'^\s*[-•*]\s+', text_sample, re.MULTILINE):
            return ChunkType.LIST_ITEM
        
        # Check if it looks like a paragraph
        if '\n\n' not in text or len(text.split('\n\n')) == 1:
            return ChunkType.PARAGRAPH
        
        return ChunkType.MIXED
    
    def extract_headers(self, text: str) -> List[Tuple[int, str]]:
        """
        Extract headers and their positions from text
        
        Args:
            text: Full document text
            
        Returns:
            List of (position, header_text) tuples
        """
        headers = []
        
        for pattern in self.header_patterns:
            for match in pattern.finditer(text):
                headers.append((match.start(), match.group(0).strip()))
        
        # Sort by position
        headers.sort(key=lambda x: x[0])
        
        logger.debug(f"Extracted {len(headers)} headers from document")
        return headers
    
    def find_sentence_boundary(self, text: str, target_pos: int, direction: str = 'forward') -> int:
        """
        Find the nearest sentence boundary from a target position
        
        Args:
            text: Text to search
            target_pos: Starting position
            direction: 'forward' or 'backward'
            
        Returns:
            Position of nearest sentence boundary
        """
        if direction == 'forward':
            # Search forward for sentence ending
            search_text = text[target_pos:target_pos + 200]  # Look ahead 200 chars
            match = self.sentence_endings.search(search_text)
            if match:
                return target_pos + match.end()
            return min(target_pos + 200, len(text))
        
        else:  # backward
            # Search backward for sentence ending
            search_start = max(0, target_pos - 200)
            search_text = text[search_start:target_pos]
            matches = list(self.sentence_endings.finditer(search_text))
            if matches:
                return search_start + matches[-1].end()
            return max(0, target_pos - 200)
    
    def find_paragraph_boundary(self, text: str, target_pos: int) -> int:
        """
        Find the nearest paragraph boundary from a target position
        
        Args:
            text: Text to search
            target_pos: Starting position
            
        Returns:
            Position of nearest paragraph boundary
        """
        # Look for double newlines nearby
        search_start = max(0, target_pos - 100)
        search_end = min(len(text), target_pos + 100)
        search_text = text[search_start:search_end]
        
        match = self.paragraph_breaks.search(search_text)
        if match:
            return search_start + match.end()
        
        # Fall back to sentence boundary
        return self.find_sentence_boundary(text, target_pos, 'forward')
    
    def chunk_table_content(self, text: str, chunk_size: int, overlap: int) -> List[EnhancedChunk]:
        """
        Specialized chunking for table/Excel content with MULTI-SHEET support
        
        MULTI-SHEET FEATURES:
        - Detects all WORKSHEET: markers
        - Extracts sheet-specific headers
        - Tracks which sheet each chunk belongs to
        - Applies correct header per sheet
        
        Args:
            text: Table text
            chunk_size: Target chunk size
            overlap: Overlap size
            
        Returns:
            List of EnhancedChunk objects
        """
        chunks = []
        
        # Detect all worksheets and their positions
        worksheets = []
        worksheet_pattern = re.compile(r'WORKSHEET:\s*(.+?)\s*\n={20,}', re.IGNORECASE)
        
        for match in worksheet_pattern.finditer(text):
            sheet_name = match.group(1).strip()
            sheet_start = match.start()
            worksheets.append({
                'name': sheet_name,
                'start_pos': sheet_start,
                'header': None
            })
        
        # If no worksheets found, treat as single sheet
        if not worksheets:
            worksheets = [{'name': 'Sheet1', 'start_pos': 0, 'header': None}]
            logger.info("No WORKSHEET markers found, treating as single sheet")
        else:
            logger.info(f"Detected {len(worksheets)} worksheets: {[w['name'] for w in worksheets]}")
        
        # Add end positions to worksheets
        for i, sheet in enumerate(worksheets):
            if i + 1 < len(worksheets):
                sheet['end_pos'] = worksheets[i + 1]['start_pos']
            else:
                sheet['end_pos'] = len(text)
        
        # Extract header for each worksheet
        lines = text.split('\n')
        for sheet in worksheets:
            # Find the worksheet marker line
            sheet_text_start = sheet['start_pos']
            sheet_text = text[sheet_text_start:sheet['end_pos']]
            sheet_lines = sheet_text.split('\n')
            
            # Look for header (skip worksheet name and separator lines)
            for i, line in enumerate(sheet_lines):
                if 'WORKSHEET:' in line:
                    # Skip separator line, grab the next non-empty line as header
                    for j in range(i + 1, min(i + 4, len(sheet_lines))):
                        potential_header = sheet_lines[j].strip()
                        # Check if it looks like a header (has | or \t separators)
                        if potential_header and len(potential_header) < 500:
                            if '|' in potential_header or '\t' in potential_header:
                                sheet['header'] = potential_header
                                logger.info(f"Extracted header for '{sheet['name']}': {potential_header[:50]}...")
                                break
                    break
            
            if not sheet['header']:
                logger.warning(f"No header found for worksheet '{sheet['name']}'")
        
        # Process each worksheet separately
        chunk_index = 0
        
        for sheet_idx, sheet in enumerate(worksheets):
            sheet_name = sheet['name']
            sheet_header = sheet['header']
            sheet_start = sheet['start_pos']
            sheet_end = sheet['end_pos']
            
            # Get text for this sheet
            sheet_text = text[sheet_start:sheet_end]
            sheet_lines = sheet_text.split('\n')
            
            # Skip worksheet header lines (WORKSHEET: and separator)
            content_start_line = 0
            for i, line in enumerate(sheet_lines):
                if 'WORKSHEET:' in line:
                    # Skip next 2-3 lines (separator and header)
                    content_start_line = i + 3 if sheet_header else i + 2
                    break
            
            sheet_lines = sheet_lines[content_start_line:]
            
            # Chunk this sheet's content
            current_chunk = []
            current_size = 0
            sheet_chunk_index = 0
            
            logger.info(f"Processing sheet '{sheet_name}': {len(sheet_lines)} lines")
            
            for line in sheet_lines:
                # Skip empty lines at start
                if not current_chunk and not line.strip():
                    continue
                
                line_size = len(line) + 1  # +1 for newline
                
                # If adding this line exceeds chunk size and we have content, save chunk
                if current_size + line_size > chunk_size and current_chunk:
                    chunk_text = '\n'.join(current_chunk)
                    
                    # Add header to non-first chunks of this sheet
                    if sheet_header and sheet_chunk_index > 0:
                        chunk_text = f"[HEADER] {sheet_header}\n{chunk_text}"
                    
                    # Add sheet context to first chunk
                    if sheet_chunk_index == 0 and len(worksheets) > 1:
                        chunk_text = f"[SHEET: {sheet_name}]\n{chunk_text}"
                    
                    chunks.append(EnhancedChunk(
                        text=chunk_text,
                        chunk_index=chunk_index,
                        total_chunks=0,  # Will update later
                        chunk_type=ChunkType.TABLE_ROW,
                        start_char=sheet_start,  # Approximate
                        end_char=sheet_start + len(chunk_text),  # Approximate
                        tokens_estimate=self.estimate_tokens(chunk_text),
                        parent_section=sheet_name,  # Sheet name as parent section
                        has_header=sheet_header is not None,
                        header_text=sheet_header
                    ))
                    
                    # Keep overlap (last few lines)
                    overlap_lines = max(1, int(overlap / 50))  # Rough estimate: 50 chars per line
                    current_chunk = current_chunk[-overlap_lines:]
                    current_size = sum(len(l) + 1 for l in current_chunk)
                    chunk_index += 1
                    sheet_chunk_index += 1
                
                current_chunk.append(line)
                current_size += line_size
            
            # Add final chunk for this sheet
            if current_chunk:
                chunk_text = '\n'.join(current_chunk)
                
                if sheet_header and sheet_chunk_index > 0:
                    chunk_text = f"[HEADER] {sheet_header}\n{chunk_text}"
                
                if sheet_chunk_index == 0 and len(worksheets) > 1:
                    chunk_text = f"[SHEET: {sheet_name}]\n{chunk_text}"
                
                chunks.append(EnhancedChunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    total_chunks=0,
                    chunk_type=ChunkType.TABLE_ROW,
                    start_char=sheet_start,
                    end_char=sheet_end,
                    tokens_estimate=self.estimate_tokens(chunk_text),
                    parent_section=sheet_name,
                    has_header=sheet_header is not None,
                    header_text=sheet_header
                ))
                
                chunk_index += 1
                sheet_chunk_index += 1
            
            logger.info(f"Sheet '{sheet_name}': Created {sheet_chunk_index} chunks")
        
        # Update total_chunks for all
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total
        
        logger.info(f"Multi-sheet processing complete: {len(chunks)} total chunks across {len(worksheets)} sheets")
        return chunks
    
    def chunk_semantic_content(self, text: str, chunk_size: int, overlap: int) -> List[EnhancedChunk]:
        """
        Semantic chunking with sentence/paragraph boundary awareness
        
        Args:
            text: Document text
            chunk_size: Target chunk size
            overlap: Overlap size
            
        Returns:
            List of EnhancedChunk objects
        """
        chunks = []
        
        # Extract headers for context
        headers = self.extract_headers(text)
        
        # Clean text
        text = re.sub(r'\s+', ' ', text).strip()
        text_len = len(text)
        
        position = 0
        chunk_index = 0
        
        while position < text_len:
            # Determine target end position
            target_end = min(position + chunk_size, text_len)
            
            # Find smart boundary
            if target_end < text_len:
                # Try paragraph boundary first
                actual_end = self.find_paragraph_boundary(text, target_end)
                
                # If paragraph boundary is too far, use sentence boundary
                if actual_end - position > chunk_size * 1.3:  # 30% tolerance
                    actual_end = self.find_sentence_boundary(text, target_end, 'forward')
            else:
                actual_end = text_len
            
            # Extract chunk
            chunk_text = text[position:actual_end].strip()
            
            if chunk_text:
                # Find parent section (nearest header before this chunk)
                parent_section = None
                for header_pos, header_text in headers:
                    if header_pos <= position:
                        parent_section = header_text
                    else:
                        break
                
                # Detect chunk type
                chunk_type = self.detect_chunk_type(chunk_text)
                
                chunks.append(EnhancedChunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    total_chunks=0,  # Will update later
                    chunk_type=chunk_type,
                    start_char=position,
                    end_char=actual_end,
                    tokens_estimate=self.estimate_tokens(chunk_text),
                    parent_section=parent_section
                ))
                
                chunk_index += 1
            
            # Move to next position with overlap
            if actual_end < text_len:
                # Find overlap boundary (go back to sentence)
                overlap_pos = max(position, actual_end - overlap)
                position = self.find_sentence_boundary(text, overlap_pos, 'backward')
            else:
                position = text_len
        
        # Update total_chunks for all
        total = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total
        
        logger.info(f"Created {len(chunks)} semantic chunks")
        return chunks
    
    def chunk_text(
        self, 
        text: str, 
        file_type: str = 'txt',
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Main chunking method - routes to appropriate strategy
        
        Args:
            text: Text to chunk
            file_type: File type extension (xlsx, pdf, txt, etc.)
            metadata: Optional additional metadata to include
            
        Returns:
            List of chunk dictionaries with enhanced metadata
        """
        logger.info(f"Starting enhanced chunking: {len(text)} chars, file_type: {file_type}")
        
        # Get configuration for this file type
        config = self.CHUNK_CONFIGS.get(file_type, self.CHUNK_CONFIGS['txt'])
        chunk_size = config['size']
        overlap = config['overlap']
        method = config['method']
        
        logger.info(f"Using {method} method: chunk_size={chunk_size}, overlap={overlap}")
        
        # Route to appropriate chunking method
        try:
            if method == 'table':
                enhanced_chunks = self.chunk_table_content(text, chunk_size, overlap)
            else:  # semantic
                enhanced_chunks = self.chunk_semantic_content(text, chunk_size, overlap)
            
            logger.info(f"Created {len(enhanced_chunks)} EnhancedChunk objects")
        except Exception as e:
            logger.error(f"Error in chunking method: {e}", exc_info=True)
            raise
        
        # Convert to dictionaries with metadata
        result = []
        for i, chunk in enumerate(enhanced_chunks):
            try:
                # Ensure chunk is EnhancedChunk object
                if not isinstance(chunk, EnhancedChunk):
                    logger.error(f"Chunk {i} is not EnhancedChunk: {type(chunk)}")
                    continue
                
                chunk_dict = chunk.to_dict()
                
                # Ensure chunk_dict is actually a dict
                if not isinstance(chunk_dict, dict):
                    logger.error(f"chunk.to_dict() returned non-dict: {type(chunk_dict)}")
                    continue
                
                # Add any additional metadata
                if metadata and isinstance(metadata, dict):
                    chunk_dict.update(metadata)
                
                # Add convenience fields
                chunk_dict['position'] = f"{chunk.chunk_index + 1}/{chunk.total_chunks}"
                chunk_dict['size_category'] = 'small' if len(chunk.text) < 500 else 'medium' if len(chunk.text) < 1000 else 'large'
                
                result.append(chunk_dict)
            except Exception as e:
                logger.error(f"Error processing chunk {i}: {e}", exc_info=True)
                # Skip this chunk but continue
                continue
        
        if not result:
            raise ValueError(f"No valid chunks created from {len(enhanced_chunks)} chunk objects")
        
        logger.info(f"Enhanced chunking complete: {len(result)} chunks created")
        logger.info(f"Chunk types: {set(c.get('chunk_type', 'unknown') for c in result)}")
        logger.info(f"Avg chunk size: {sum(len(c.get('text', '')) for c in result) / len(result):.0f} chars")
        
        return result


# Convenience function for backward compatibility
def chunk_text_simple(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """
    Simple chunking for backward compatibility
    
    Args:
        text: Text to chunk
        chunk_size: Chunk size in characters
        overlap: Overlap in characters
        
    Returns:
        List of text chunks (strings only)
    """
    chunker = EnhancedChunker()
    chunks = chunker.chunk_text(text, 'txt')
    return [c['text'] for c in chunks]
