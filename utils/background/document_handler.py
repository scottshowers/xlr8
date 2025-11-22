"""
Document Upload Handler
Processes document uploads in background with progress reporting
"""

import logging
import io
from pathlib import Path
from typing import Dict, Any, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


def process_document_upload(input_data: Dict[str, Any], progress_callback: Callable) -> Dict[str, Any]:
    """
    Handler for document upload jobs
    
    Args:
        input_data: {
            'file_bytes': bytes,
            'filename': str,
            'file_ext': str,
            'selected_project': str or None
        }
        progress_callback: Function(current, total, message)
        
    Returns:
        {
            'success': bool,
            'filename': str,
            'chunks_added': int,
            'sheets_processed': list (for Excel)
        }
    """
    try:
        from utils.rag_handler import RAGHandler
        import os
        
        file_bytes = input_data['file_bytes']
        filename = input_data['filename']
        file_ext = input_data['file_ext']
        selected_project = input_data.get('selected_project')
        
        # Recreate RAGHandler (can't pass objects through Supabase)
        rag_handler = RAGHandler(
            llm_endpoint=os.getenv('LLM_ENDPOINT', 'http://178.156.190.64:11435')
        )
        
        logger.info(f"[UPLOAD] Processing {filename} ({file_ext})")
        progress_callback(0, 100, f"Starting {filename}...")
        
        # Extract text based on file type
        if file_ext in ['.txt', '.md']:
            text_content = file_bytes.decode('utf-8', errors='ignore')
            progress_callback(20, 100, "Text extracted, chunking...")
            
            # Process single document
            result = _process_single_document(
                text_content, filename, file_ext, selected_project, rag_handler, progress_callback
            )
            
            return result
        
        elif file_ext == '.pdf':
            import pdfplumber
            progress_callback(10, 100, "Extracting PDF text...")
            
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                text_content = "\n\n".join([page.extract_text() or "" for page in pdf.pages])
            
            progress_callback(30, 100, "PDF extracted, chunking...")
            
            result = _process_single_document(
                text_content, filename, file_ext, selected_project, rag_handler, progress_callback
            )
            
            return result
        
        elif file_ext == '.docx':
            from docx import Document
            progress_callback(10, 100, "Extracting DOCX text...")
            
            doc = Document(io.BytesIO(file_bytes))
            text_content = "\n\n".join([para.text for para in doc.paragraphs])
            
            progress_callback(30, 100, "DOCX extracted, chunking...")
            
            result = _process_single_document(
                text_content, filename, file_ext, selected_project, rag_handler, progress_callback
            )
            
            return result
        
        elif file_ext in ['.xlsx', '.xls', '.csv']:
            import pandas as pd
            from utils.functional_areas import get_functional_area
            
            progress_callback(5, 100, "Reading Excel file...")
            
            if file_ext == '.csv':
                df = pd.read_csv(io.BytesIO(file_bytes))
                sheets_to_process = [{
                    'sheet_name': 'Sheet1',
                    'functional_area': 'General',
                    'df': df
                }]
            else:
                # Read all sheets
                all_sheets = pd.read_excel(io.BytesIO(file_bytes), sheet_name=None)
                sheets_to_process = []
                
                for sheet_name, df in all_sheets.items():
                    functional_area = get_functional_area(sheet_name)
                    sheets_to_process.append({
                        'sheet_name': sheet_name,
                        'functional_area': functional_area,
                        'df': df
                    })
            
            progress_callback(10, 100, f"Found {len(sheets_to_process)} sheet(s), processing...")
            
            # Process each sheet
            total_chunks = 0
            sheets_processed = []
            
            for idx, sheet_info in enumerate(sheets_to_process):
                sheet_pct_start = 10 + (idx / len(sheets_to_process)) * 80
                sheet_pct_end = 10 + ((idx + 1) / len(sheets_to_process)) * 80
                
                progress_callback(
                    int(sheet_pct_start),
                    100,
                    f"Processing sheet {idx+1}/{len(sheets_to_process)}: {sheet_info['sheet_name']}..."
                )
                
                # Convert sheet to text
                sheet_header = f"\n{'='*80}\nWORKSHEET: {sheet_info['sheet_name']}\n{'='*80}\n"
                sheet_content = sheet_info['df'].to_string()
                sheet_text = sheet_header + sheet_content
                
                # Prepare metadata
                sheet_metadata = {
                    'source': filename,
                    'file_type': file_ext.replace('.', ''),
                    'uploaded_at': datetime.now().isoformat(),
                    'sheet_name': sheet_info['sheet_name'],
                    'functional_area': sheet_info['functional_area']
                }
                
                if selected_project:
                    sheet_metadata['project_id'] = selected_project
                
                # Sheet progress callback
                def sheet_progress(current, total, msg):
                    overall_pct = int(sheet_pct_start + (current / total) * (sheet_pct_end - sheet_pct_start))
                    progress_callback(overall_pct, 100, f"Sheet {idx+1}/{len(sheets_to_process)}: {msg}")
                
                # Add to ChromaDB with progress
                success = rag_handler.add_document(
                    collection_name='hcmpact_knowledge',
                    text=sheet_text,
                    metadata=sheet_metadata,
                    progress_callback=sheet_progress
                )
                
                if success:
                    sheets_processed.append(sheet_info['sheet_name'])
                    # Count chunks (rough estimate)
                    chunks = len(sheet_text) // 2000
                    total_chunks += chunks
            
            # Save file to disk
            progress_callback(95, 100, "Saving file...")
            upload_dir = Path('/data/uploads')
            upload_dir.mkdir(parents=True, exist_ok=True)
            upload_path = upload_dir / filename
            upload_path.write_bytes(file_bytes)
            
            progress_callback(100, 100, f"Complete! Processed {len(sheets_processed)} sheets")
            
            return {
                'success': True,
                'filename': filename,
                'chunks_added': total_chunks,
                'sheets_processed': sheets_processed
            }
        
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
    
    except Exception as e:
        logger.error(f"Error processing document: {e}", exc_info=True)
        progress_callback(0, 100, f"ERROR: {str(e)}")
        return {
            'success': False,
            'filename': filename,
            'error': str(e)
        }


def _process_single_document(
    text_content: str,
    filename: str,
    file_ext: str,
    selected_project: str,
    rag_handler,
    progress_callback: Callable
) -> Dict[str, Any]:
    """Helper to process non-Excel documents"""
    
    metadata = {
        'source': filename,
        'file_type': file_ext.replace('.', ''),
        'uploaded_at': datetime.now().isoformat()
    }
    
    if selected_project:
        metadata['project_id'] = selected_project
    
    # Add to ChromaDB with progress
    def doc_progress(current, total, msg):
        # Map 30-100% to the doc processing phase
        overall_pct = 30 + int((current / total) * 65)
        progress_callback(overall_pct, 100, msg)
    
    success = rag_handler.add_document(
        collection_name='hcmpact_knowledge',
        text=text_content,
        metadata=metadata,
        progress_callback=doc_progress
    )
    
    if success:
        # Save file to disk
        progress_callback(95, 100, "Saving file...")
        upload_dir = Path('/data/uploads')
        upload_dir.mkdir(parents=True, exist_ok=True)
        upload_path = upload_dir / filename
        
        # For text files, save as bytes
        if isinstance(text_content, str):
            upload_path.write_text(text_content)
        
        progress_callback(100, 100, "Complete!")
        
        # Rough chunk estimate
        chunks = len(text_content) // 800
        
        return {
            'success': True,
            'filename': filename,
            'chunks_added': chunks
        }
    else:
        return {
            'success': False,
            'filename': filename,
            'error': 'Failed to add document'
        }
