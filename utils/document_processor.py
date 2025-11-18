import os
import streamlit as st
from typing import List, Dict, Any
import PyPDF2
import docx
import logging
from utils.rag_handler import RAGHandler

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Handles document upload and processing with proper metadata."""
    
    def __init__(self):
        try:
            self.rag_handler = RAGHandler()
            self.supported_extensions = ['.pdf', '.docx', '.txt', '.md']
            logger.info("DocumentProcessor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DocumentProcessor: {e}")
            self.rag_handler = None
            self.supported_extensions = ['.pdf', '.docx', '.txt', '.md']
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
    
    def extract_text_from_txt(self, file) -> str:
        """Extract text from TXT file."""
        try:
            # Read and decode text file
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
        """
        Extract text from uploaded file based on extension.
        
        Args:
            file: Uploaded file object
            filename: Name of the file
            
        Returns:
            Extracted text content
        """
        _, ext = os.path.splitext(filename.lower())
        
        if ext == '.pdf':
            return self.extract_text_from_pdf(file)
        elif ext == '.docx':
            return self.extract_text_from_docx(file)
        elif ext in ['.txt', '.md']:
            return self.extract_text_from_txt(file)
        else:
            logger.warning(f"Unsupported file type: {ext}")
            return ""
    
    def clean_text(self, text: str) -> str:
        """
        Clean text by removing non-ASCII characters and extra whitespace.
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text
        """
        # Remove non-ASCII characters
        text = text.encode('ascii', 'ignore').decode('ascii')
        
        # Remove extra whitespace
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
        """
        Process a document and add it to ChromaDB.
        
        Args:
            file: Uploaded file object
            filename: Name of the file
            collection_name: ChromaDB collection name
            category: Document category (e.g., "UKG Pro", "WFM", "Implementation")
            
        Returns:
            Dictionary with processing results
        """
        progress_container = st.empty()
        
        try:
            # Extract text
            progress_container.info(f"📄 Extracting text from {filename}...")
            logger.info(f"Processing document: {filename}")
            text = self.extract_text(file, filename)
            
            if not text:
                progress_container.error(f"❌ No text extracted from {filename}")
                return {
                    'success': False,
                    'filename': filename,
                    'error': 'No text extracted from document'
                }
            
            progress_container.info(f"✅ Extracted {len(text)} characters")
            
            # Clean text
            text = self.clean_text(text)
            progress_container.info(f"🧹 Cleaned text: {len(text)} characters")
            
            # Prepare metadata with ACTUAL FILENAME
            metadata = {
                'source': filename,
                'category': category,
                'file_size': len(text),
                'type': os.path.splitext(filename)[1].lower()
            }
            
            # Test embedding first
            progress_container.info(f"🧪 Testing Ollama connection...")
            test_embedding = self.rag_handler.get_embedding("test")
            if test_embedding is None:
                progress_container.error("❌ Cannot connect to Ollama embedding service!")
                progress_container.error(f"Endpoint: {self.rag_handler.ollama_base_url}")
                return {
                    'success': False,
                    'filename': filename,
                    'error': 'Ollama embedding service unavailable'
                }
            progress_container.success("✅ Ollama connection successful")
            
            # Calculate expected chunks
            expected_chunks = max(1, len(text) // 800)
            progress_container.info(f"📦 Will create ~{expected_chunks} chunks, processing now...")
            
            # Process with progress updates
            collection = self.rag_handler.client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            chunks = self.rag_handler.chunk_text(text)
            progress_container.info(f"📦 Created {len(chunks)} chunks, embedding now...")
            
            successful = 0
            failed = 0
            
            for i, chunk in enumerate(chunks):
                progress_container.info(f"🔄 Processing chunk {i+1}/{len(chunks)}...")
                
                embedding = self.rag_handler.get_embedding(chunk)
                if embedding is None:
                    failed += 1
                    progress_container.warning(f"⚠️ Chunk {i+1} failed, continuing...")
                    continue
                
                doc_id = f"{filename}_{i}"
                collection.add(
                    embeddings=[embedding],
                    documents=[chunk],
                    metadatas=[{**metadata, "chunk_index": i}],
                    ids=[doc_id]
                )
                successful += 1
            
            if successful > 0:
                progress_container.success(f"✅ Successfully processed {filename} ({successful}/{len(chunks)} chunks)")
                return {
                    'success': True,
                    'filename': filename,
                    'chunks': successful,
                    'category': category
                }
            else:
                progress_container.error(f"❌ All chunks failed for {filename}")
                return {
                    'success': False,
                    'filename': filename,
                    'error': 'All chunks failed to process'
                }
                
        except Exception as e:
            progress_container.error(f"❌ Error: {str(e)}")
            logger.error(f"Error processing document {filename}: {str(e)}")
            return {
                'success': False,
                'filename': filename,
                'error': str(e)
            }
    
    def process_multiple_documents(
        self, 
        files: List[Any], 
        collection_name: str = "hcmpact_docs",
        category: str = "General"
    ) -> List[Dict[str, Any]]:
        """
        Process multiple documents.
        
        Args:
            files: List of uploaded file objects
            collection_name: ChromaDB collection name
            category: Document category
            
        Returns:
            List of processing results
        """
        results = []
        
        with st.spinner(f"Processing {len(files)} documents..."):
            for file in files:
                # Reset file pointer
                file.seek(0)
                
                # Process document
                result = self.process_document(
                    file=file,
                    filename=file.name,
                    collection_name=collection_name,
                    category=category
                )
                results.append(result)
        
        return results
    
    def get_upload_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics from upload results.
        
        Args:
            results: List of processing results
            
        Returns:
            Statistics dictionary
        """
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
    st.subheader("Upload Documents to HCMPACT LLM")
    
    # Category selection
    category = st.selectbox(
        "Document Category",
        ["UKG Pro", "WFM", "Implementation Guide", "Best Practices", "Configuration", "General"],
        help="Select the category for better organization"
    )
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Choose files",
        type=['pdf', 'docx', 'txt', 'md'],
        accept_multiple_files=True,
        help="Supported formats: PDF, DOCX, TXT, MD"
    )
    
    if uploaded_files:
        st.info(f"{len(uploaded_files)} file(s) selected")
        
        # Display file list
        with st.expander("📄 Selected Files"):
            for file in uploaded_files:
                st.write(f"- {file.name} ({file.size:,} bytes)")
        
        if st.button("🚀 Process Documents", type="primary"):
            processor = DocumentProcessor()
            
            # Process documents
            results = processor.process_multiple_documents(
                files=uploaded_files,
                collection_name="hcmpact_docs",
                category=category
            )
            
            # Get statistics
            stats = processor.get_upload_stats(results)
            
            # Display results
            if stats['successful'] > 0:
                st.success(f"✅ Successfully processed {stats['successful']}/{stats['total']} documents")
                st.info(f"📦 Created {stats['total_chunks']} chunks in ChromaDB")
                
                # Show successful files
                with st.expander("✅ Successful Uploads"):
                    for result in results:
                        if result.get('success'):
                            st.write(f"- **{result['filename']}** ({result.get('chunks', 0)} chunks)")
            
            if stats['failed'] > 0:
                st.error(f"❌ Failed to process {stats['failed']} documents")
                with st.expander("❌ Failed Uploads"):
                    for result in results:
                        if not result.get('success'):
                            st.write(f"- **{result['filename']}**: {result.get('error', 'Unknown error')}")
            
            # Show collection info
            rag = RAGHandler()
            count = rag.get_collection_count("hcmpact_docs")
            st.metric("Total Chunks in HCMPACT LLM", count)
