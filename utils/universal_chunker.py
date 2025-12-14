"""
Universal Chunker - Universal Document Intelligence System
===========================================================

Phase 3: Orchestration layer that ties everything together

This is the main entry point - analyzes ANY document and routes to
the appropriate specialized chunker.

Author: XLR8 Team
"""

from typing import List, Dict, Any
import logging

# Import our system components
from utils.document_analyzer import DocumentAnalyzer, DocumentStructure
from utils.specialized_chunkers import (
    TableChunker,
    CodeChunker,
    HierarchicalChunker,
    HybridChunker,
    SemanticChunker,
    ChunkResult
)

logger = logging.getLogger(__name__)


class UniversalChunker:
    """
    Universal document chunker that handles ANY document type intelligently
    
    Workflow:
    1. Analyze document (detect structure, patterns, density)
    2. Route to appropriate specialized chunker
    3. Return standardized chunks with metadata
    """
    
    def __init__(self):
        # Initialize analyzer
        self.analyzer = DocumentAnalyzer()
        
        # Initialize specialized chunkers
        self.table_chunker = TableChunker()
        self.code_chunker = CodeChunker()
        self.hierarchical_chunker = HierarchicalChunker()
        self.hybrid_chunker = HybridChunker()
        self.semantic_chunker = SemanticChunker()
        
        logger.info("✅ Universal Chunker initialized with all specialized chunkers")
    
    def chunk_document(
        self,
        text: str,
        filename: str,
        file_type: str,
        additional_metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Main entry point: Analyze and chunk ANY document
        
        Args:
            text: Full document text
            filename: Original filename
            file_type: Extension (xlsx, pdf, py, etc)
            additional_metadata: Extra metadata to include (project, functional_area, etc)
        
        Returns:
            List of chunk dicts with text and enriched metadata
        """
        logger.info("="*80)
        logger.info(f"UNIVERSAL CHUNKER: Processing {filename}")
        
        # PHASE 1: ANALYZE
        analysis = self.analyzer.analyze(text, filename, file_type)
        
        # PHASE 2: ROUTE TO SPECIALIZED CHUNKER
        strategy = analysis.recommended_strategy
        structure = analysis.structure
        
        logger.info(f"Routing to {strategy['name']} chunker...")
        
        if structure == DocumentStructure.TABULAR:
            chunks = self.table_chunker.chunk(text, strategy, filename)
        elif structure == DocumentStructure.CODE_BASED:
            chunks = self.code_chunker.chunk(text, strategy, filename)
        elif structure == DocumentStructure.HIERARCHICAL:
            chunks = self.hierarchical_chunker.chunk(text, strategy, filename)
        elif structure == DocumentStructure.MIXED:
            chunks = self.hybrid_chunker.chunk(text, strategy, filename)
        else:  # LINEAR
            chunks = self.semantic_chunker.chunk(text, strategy, filename)
        
        # PHASE 3: ENRICH METADATA
        enriched_chunks = []
        for i, chunk in enumerate(chunks):
            chunk_dict = {
                'text': chunk.text,
                'metadata': {
                    # Core metadata
                    'filename': filename,
                    'file_type': file_type,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    
                    # Analysis metadata
                    'structure': analysis.structure.value,
                    'strategy': strategy['name'],
                    
                    # Chunk-specific metadata
                    **chunk.metadata,
                    
                    # Additional metadata (project, functional_area, etc)
                    **(additional_metadata or {})
                }
            }
            enriched_chunks.append(chunk_dict)
        
        # Log summary
        self._log_summary(filename, analysis, len(chunks))
        
        return enriched_chunks
    
    def chunk_document_simple(
        self,
        text: str,
        filename: str,
        file_type: str
    ) -> List[str]:
        """
        Simplified version that returns just text strings
        
        For backward compatibility with existing code
        """
        chunk_dicts = self.chunk_document(text, filename, file_type)
        return [c['text'] for c in chunk_dicts]
    
    def _log_summary(self, filename: str, analysis: Any, chunk_count: int):
        """Log comprehensive summary"""
        logger.info("="*80)
        logger.info("CHUNKING COMPLETE:")
        logger.info(f"  Document: {filename}")
        logger.info(f"  Structure: {analysis.structure.value}")
        logger.info(f"  Strategy: {analysis.recommended_strategy['name']}")
        logger.info(f"  Patterns: {', '.join(analysis.patterns) if analysis.patterns else 'none'}")
        logger.info(f"  Chunks Created: {chunk_count}")
        logger.info("="*80)


# Main integration functions for RAG handler

def chunk_intelligently(
    text: str,
    filename: str,
    file_type: str,
    metadata: Dict[str, Any] = None
) -> List[Dict[str, Any]]:
    """
    Universal intelligent chunking - full metadata version
    
    This is the main function that RAG handler should call.
    
    Args:
        text: Document text
        filename: Original filename
        file_type: File extension
        metadata: Additional metadata (project, functional_area, etc)
    
    Returns:
        List of chunk dicts with text and metadata
    """
    chunker = UniversalChunker()
    return chunker.chunk_document(text, filename, file_type, metadata)


def chunk_intelligently_simple(
    text: str,
    filename: str,
    file_type: str
) -> List[str]:
    """
    Universal intelligent chunking - simple version
    
    For backward compatibility, returns just text strings
    """
    chunker = UniversalChunker()
    return chunker.chunk_document_simple(text, filename, file_type)


# Quick test function
def test_chunker():
    """Test chunker with sample documents"""
    
    # Test 1: Excel-like table
    excel_sample = """[SHEET: Earnings]
Columns: Code | Description | Type
Country Code: USA | Earnings Code: REG | Description: Regular Pay
Country Code: USA | Earnings Code: OT | Description: Overtime
Country Code: USA | Earnings Code: BONUS | Description: Bonus Pay
"""
    
    print("Testing Excel-like document...")
    chunks = chunk_intelligently_simple(excel_sample, "test.xlsx", "xlsx")
    print(f"  Created {len(chunks)} chunks\n")
    
    # Test 2: Code
    code_sample = """import sys

def calculate_total(items):
    return sum(items)

class DataProcessor:
    def process(self, data):
        return data.upper()
"""
    
    print("Testing Python code...")
    chunks = chunk_intelligently_simple(code_sample, "test.py", "py")
    print(f"  Created {len(chunks)} chunks\n")
    
    # Test 3: Hierarchical
    doc_sample = """# Introduction

This is the introduction section.

## Background

More detail about background.

# Main Content

The main content goes here.
"""
    
    print("Testing hierarchical document...")
    chunks = chunk_intelligently_simple(doc_sample, "test.md", "md")
    print(f"  Created {len(chunks)} chunks\n")
    
    print("✅ All tests passed!")


if __name__ == "__main__":
    # Run tests if executed directly
    test_chunker()
