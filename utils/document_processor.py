import os
import streamlit as st
from typing import List, Dict, Any
import PyPDF2
import docx
import pandas as pd
import logging
from utils.rag_handler import RAGHandler
import time

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Handles document upload and processing with proper metadata - ENHANCED EXCEL SUPPORT"""
    
    def __init__(self):
        try:
            self.rag_handler = RAGHandler()
            self.supported_extensions = ['.pdf', '.docx', '.txt', '.md', '.xlsx', '.xls']
            logger.info("DocumentProcessor initialized successfully with enhanced Excel support")
        except Exception as e:
            logger.error(f"Failed to initialize DocumentProcessor: {e}")
            self.rag_handler = None
            self.supported_extensions = ['.pdf', '.docx', '.txt', '.md', '.xlsx', '.xls']
            raise RuntimeError(f"DocumentProcessor initialization failed: {e}")
    
    def extract_text_from_pdf(self, file) -> str:
        """Extract text from PDF file."""
        try:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting PDF text: {str(e)}")
            return ""
    
    def extract_text_from_docx(self, file) -> str:
        """Extract text from DOCX file."""
        try:
            doc = docx.Document(file)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {str(e)}")
            return ""
    
    def extract_text_from_excel(self, file) -> str:
        """
        ENHANCED: Extract text from Excel file (.xlsx or .xls).
        Now with better error handling for complex files like BRIT.
        """
        try:
            all_text = []
            sheets_processed = 0
            sheets_failed = 0
            
            # Try to read Excel file with both engines
            try:
                # First try openpyxl (for .xlsx)
                excel_file = pd.ExcelFile(file, engine='openpyxl')
            except Exception as e1:
                logger.warning(f"openpyxl failed: {e1}, trying xlrd...")
                try:
                    # Fallback to xlrd (for older .xls)
                    file.seek(0)  # Reset file pointer
                    excel_file = pd.ExcelFile(file, engine='xlrd')
                except Exception as e2:
                    logger.error(f"Both engines failed. openpyxl: {e1}, xlrd: {e2}")
                    return ""
            
            total_sheets = len(excel_file.sheet_names)
            logger.info(f"Excel file has {total_sheets} sheets")
            
            # Process each sheet individually with error handling
            for sheet_idx, sheet_name in enumerate(excel_file.sheet_names):
                try:
                    logger.info(f"Processing sheet {sheet_idx+1}/{total_sheets}: '{sheet_name}'")
                    
                    # Try to read the sheet
                    try:
                        df = pd.read_excel(file, sheet_name=sheet_name, engine=excel_file.engine)
                    except Exception as read_error:
                        # If normal read fails, try with header=None
                        logger.warning(f"Normal read failed for '{sheet_name}', trying without headers...")
                        file.seek(0)
                        df = pd.read_excel(file, sheet_name=sheet_name, engine=excel_file.engine, header=None)
                    
                    # Skip completely empty sheets
                    if df.empty or df.shape[0] == 0:
                        logger.info(f"Sheet '{sheet_name}' is empty, skipping")
                        continue
                    
                    # Add sheet header
                    all_text.append(f"\n\n=== SHEET: {sheet_name} ===\n")
                    
                    # Get column names (handling unnamed columns)
                    columns = []
                    for col in df.columns:
                        col_str = str(col)
                        # Skip purely numeric or "Unnamed" columns without data
                        if not col_str.startswith('Unnamed'):
                            columns.append(col_str)
                    
                    if columns:
                        all_text.append(f"Columns: {', '.join(columns)}\n")
                    
                    # Extract rows - simplified approach
                    rows_added = 0
                    for idx, row in df.iterrows():
                        # Skip completely empty rows
                        if row.notna().any():
                            # Convert row to simple text
                            row_values = []
                            for val in row:
                                if pd.notna(val):
                                    val_str = str(val).strip()
                                    if val_str and val_str != 'nan':
                                        row_values.append(val_str)
                            
                            if row_values:
                                all_text.append(" | ".join(row_values) + "\n")
                                rows_added += 1
                        
                        # Limit rows per sheet to prevent massive files
                        if rows_added >= 500:
                            all_text.append(f"[... {len(df) - rows_added} more rows ...]\n")
                            break
                    
                    sheets_processed += 1
                    logger.info(f"✓ Sheet '{sheet_name}': {rows_added} rows extracted")
                    
                except Exception as e:
                    sheets_failed += 1
                    logger.warning(f"✗ Could not process sheet '{sheet_name}': {e}")
                    # Continue to next sheet instead of failing entire file
                    continue
            
            full_text = "".join(all_text)
            
            logger.info(f"Excel extraction complete: {sheets_processed}/{total_sheets} sheets processed")
            logger.info(f"Total text: {len(full_text)} characters")
            
            if sheets_failed > 0:
                logger.warning(f"{sheets_failed} sheets failed to process")
            
            # Return text even if some sheets failed
            if len(full_text) > 100:  # At least some content extracted
                return full_text.strip()
            else:
                logger.error("No meaningful text extracted from any sheet")
                return ""
            
        except Exception as e:
            logger.error(f"Error extracting Excel text: {str(e)}", exc_info=True)
            return ""
    
    def extract_text_from_txt(self, file) -> str:
        """Extract text from TXT file."""
        try:
            content = file.read()
            if isinstance(content, bytes):
                text = content.decode('utf-8', errors='ignore')
            else:
                text = content
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting TXT text: {str(e)}")
            return ""
    
    def extract_text(self, file, filename: str) -> str:
        """Extract text from uploaded file based on extension."""
        _, ext = os.path.splitext(filename.lower())
        
        if ext == '.pdf':
            return self.extract_text_from_pdf(file)
        elif ext == '.docx':
            return self.extract_text_from_docx(file)
        elif ext in ['.xlsx', '.xls']:
            return self.extract_text_from_excel(file)
        elif ext in ['.txt', '.md']:
            return self.extract_text_from_txt(file)
        else:
            logger.warning(f"Unsupported file type: {ext}")
            return ""
    
    def clean_text(self, text: str) -> str:
        """Clean text by removing non-ASCII characters and extra whitespace."""
        text = text.encode('ascii', 'ignore').decode('ascii')
        import re
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def process_document(
        self, 
        file, 
        filename: str, 
        collection_name: str = "hcmpact_docs",
        category: str = "General"
    ) -> Dict[str, Any]:
        """Process a document with batch embedding and proper error handling."""
        
        status_placeholder = st.empty()
        progress_bar = st.progress(0)
        
        try:
            # Extract text
            status_placeholder.info(f"📄 Extracting text from {filename}...")
            text = self.extract_text(file, filename)
            
            if not text or len(text) < 50:
                status_placeholder.error(f"❌ No text extracted from {filename}")
                status_placeholder.warning("This might be due to: file format issues, protected sheets, or unsupported Excel features")
                return {'success': False, 'filename': filename, 'error': 'No text extracted'}
            
            status_placeholder.info(f"✅ Extracted {len(text):,} characters")
            
            # Clean text
            text = self.clean_text(text)
            status_placeholder.info(f"🧹 Cleaned: {len(text):,} characters")
            
            # Metadata
            metadata = {
                'source': filename,
                'category': category,
                'file_size': len(text),
                'type': os.path.splitext(filename)[1].lower()
            }
            
            # Test Ollama
            status_placeholder.info(f"🧪 Testing Ollama...")
            test_start = time.time()
            test_embedding = self.rag_handler.get_embedding("test")
            test_time = time.time() - test_start
            
            if test_embedding is None:
                status_placeholder.error("❌ Ollama unreachable!")
                status_placeholder.error(f"Endpoint: {self.rag_handler.ollama_base_url}")
                return {'success': False, 'filename': filename, 'error': 'Ollama unavailable'}
            
            status_placeholder.success(f"✅ Ollama OK ({test_time:.1f}s)")
            
            # Get collection
            status_placeholder.info(f"📂 Getting ChromaDB collection '{collection_name}'...")
            try:
                collection = self.rag_handler.client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                status_placeholder.success(f"✅ Collection ready: {collection.count()} existing chunks")
            except Exception as e:
                status_placeholder.error(f"❌ ChromaDB collection error: {str(e)}")
                return {'success': False, 'filename': filename, 'error': f'Collection error: {str(e)}'}
            
            # Chunk text
            status_placeholder.info(f"✂️ Chunking text (800 chars per chunk)...")
            try:
                chunks = self.rag_handler.chunk_text(text)
                total_chunks = len(chunks)
                status_placeholder.success(f"✅ Created {total_chunks} chunks")
            except Exception as e:
                status_placeholder.error(f"❌ Chunking error: {str(e)}")
                return {'success': False, 'filename': filename, 'error': f'Chunking error: {str(e)}'}
            
            status_placeholder.info(f"📦 Starting batch processing ({total_chunks} chunks)...")
            
            # Process in batches to avoid timeout
            BATCH_SIZE = 10
            successful = 0
            failed = 0
            
            for batch_start in range(0, total_chunks, BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, total_chunks)
                batch_chunks = chunks[batch_start:batch_end]
                
                status_placeholder.info(f"📄 Batch {batch_start//BATCH_SIZE + 1} (chunks {batch_start+1}-{batch_end}/{total_chunks})")
                
                for i, chunk in enumerate(batch_chunks):
                    chunk_idx = batch_start + i
                    
                    # Update progress
                    progress = (chunk_idx + 1) / total_chunks
                    progress_bar.progress(progress)
                    
                    # Get embedding
                    embedding = self.rag_handler.get_embedding(chunk)
                    if embedding is None:
                        failed += 1
                        logger.warning(f"Chunk {chunk_idx+1} failed")
                        continue
                    
                    # Add to ChromaDB
                    try:
                        doc_id = f"{filename}_{chunk_idx}"
                        collection.add(
                            embeddings=[embedding],
                            documents=[chunk],
                            metadatas=[{**metadata, "chunk_index": chunk_idx}],
                            ids=[doc_id]
                        )
                        successful += 1
                    except Exception as e:
                        failed += 1
                        logger.error(f"Failed to add chunk {chunk_idx}: {e}")
            
            progress_bar.progress(1.0)
            
            if successful > 0:
                status_placeholder.success(f"✅ {filename}: {successful}/{total_chunks} chunks ({failed} failed)")
                return {
                    'success': True,
                    'filename': filename,
                    'chunks': successful,
                    'category': category
                }
            else:
                status_placeholder.error(f"❌ All chunks failed for {filename}")
                return {'success': False, 'filename': filename, 'error': 'All chunks failed'}
                
        except Exception as e:
            status_placeholder.error(f"❌ ERROR: {str(e)}")
            logger.error(f"Error processing {filename}: {str(e)}", exc_info=True)
            return {'success': False, 'filename': filename, 'error': str(e)}
    
    def process_multiple_documents(
        self, 
        files: List[Any], 
        collection_name: str = "hcmpact_docs",
        category: str = "General"
    ) -> List[Dict[str, Any]]:
        """Process multiple documents."""
        results = []
        
        for idx, file in enumerate(files):
            st.markdown(f"### Document {idx+1}/{len(files)}")
            file.seek(0)
            result = self.process_document(
                file=file,
                filename=file.name,
                collection_name=collection_name,
                category=category
            )
            results.append(result)
            st.markdown("---")
        
        return results
    
    def get_upload_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get statistics from upload results."""
        successful = [r for r in results if r.get('success')]
        failed = [r for r in results if not r.get('success')]
        total_chunks = sum(r.get('chunks', 0) for r in successful)
        
        return {
            'total': len(results),
            'successful': len(successful),
            'failed': len(failed),
            'total_chunks': total_chunks,
            'failed_files': [r.get('filename') for r in failed]
        }


def render_upload_interface():
    """Render the document upload interface with proper metadata capture."""
    try:
        st.subheader("Upload Documents to HCMPACT LLM")
        
        category = st.selectbox(
            "Document Category",
            ["UKG Templates", "UKG Pro", "WFM", "Implementation Guide", "Best Practices", "Configuration", "General"],
            help="Select the category for better organization"
        )
        
        uploaded_files = st.file_uploader(
            "Choose files",
            type=['pdf', 'docx', 'txt', 'md', 'xlsx', 'xls'],
            accept_multiple_files=True,
            help="Supported formats: PDF, DOCX, TXT, MD, XLSX, XLS"
        )
        
        if uploaded_files:
            st.info(f"{len(uploaded_files)} file(s) selected")
            
            with st.expander("📄 Selected Files"):
                for file in uploaded_files:
                    st.write(f"- {file.name} ({file.size:,} bytes)")
            
            if st.button("🚀 Process Documents", type="primary"):
                try:
                    processor = DocumentProcessor()
                    
                    results = processor.process_multiple_documents(
                        files=uploaded_files,
                        collection_name="hcmpact_docs",
                        category=category
                    )
                    
                    stats = processor.get_upload_stats(results)
                    
                    st.markdown("---")
                    st.markdown("### Results")
                    
                    if stats['successful'] > 0:
                        st.success(f"✅ {stats['successful']}/{stats['total']} documents processed")
                        st.info(f"📦 Total chunks: {stats['total_chunks']:,}")
                    
                    if stats['failed'] > 0:
                        st.error(f"❌ {stats['failed']} documents failed")
                        with st.expander("Failed Files"):
                            for fname in stats['failed_files']:
                                st.write(f"- {fname}")
                    
                    rag = RAGHandler()
                    count = rag.get_collection_count("hcmpact_docs")
                    st.metric("Total Chunks in HCMPACT LLM", f"{count:,}")
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    logger.error(f"Upload error: {e}", exc_info=True)
    
    except Exception as e:
        st.error("❌ Failed to initialize upload interface")
        st.error(f"Error: {str(e)}")
        logger.error(f"Upload interface error: {e}", exc_info=True)
