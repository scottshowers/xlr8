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
    """Handles document upload and processing with proper metadata - NOW WITH EXCEL SUPPORT!"""
    
    def __init__(self):
        try:
            self.rag_handler = RAGHandler()
            # UPDATED: Added Excel support for UKG templates
            self.supported_extensions = ['.pdf', '.docx', '.txt', '.md', '.xlsx', '.xls']
            logger.info("DocumentProcessor initialized successfully with Excel support")
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
        Extract text from Excel file (.xlsx or .xls).
        Reads ALL sheets and converts to text format.
        
        Critical for UKG templates like:
        - Analysis_Workbook.xlsx
        - BRIT_Master.xlsx
        - Data conversion templates
        """
        try:
            # Read all sheets
            excel_file = pd.ExcelFile(file)
            all_text = []
            
            logger.info(f"Excel file has {len(excel_file.sheet_names)} sheets")
            
            for sheet_name in excel_file.sheet_names:
                try:
                    # Read sheet
                    df = pd.read_excel(file, sheet_name=sheet_name)
                    
                    # Add sheet header
                    all_text.append(f"\n\n=== SHEET: {sheet_name} ===\n")
                    
                    # Convert dataframe to text
                    # Include column names and all cell values
                    all_text.append(f"Columns: {', '.join([str(col) for col in df.columns])}\n")
                    
                    # Convert each row to text
                    for idx, row in df.iterrows():
                        # Skip completely empty rows
                        if row.notna().any():
                            row_text = " | ".join([
                                f"{col}: {val}" 
                                for col, val in zip(df.columns, row) 
                                if pd.notna(val) and str(val).strip()
                            ])
                            if row_text:
                                all_text.append(row_text + "\n")
                    
                    logger.info(f"Extracted {len(df)} rows from sheet '{sheet_name}'")
                    
                except Exception as e:
                    logger.warning(f"Could not read sheet '{sheet_name}': {e}")
                    continue
            
            full_text = "".join(all_text)
            logger.info(f"Excel extraction complete: {len(full_text)} characters")
            return full_text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting Excel text: {str(e)}")
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
            
            if not text:
                status_placeholder.error(f"❌ No text extracted from {filename}")
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
        
        # UPDATED: Added Excel file types for UKG templates
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
