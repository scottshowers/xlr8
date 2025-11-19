"""
Complete Knowledge Management Page
Restores ALL original functionality + adds Intelligent Parser
"""

import streamlit as st
from pathlib import Path
import pandas as pd
from datetime import datetime
import os

# Import RAG handler
try:
    from utils.rag_handler import RAGHandler
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

# Import intelligent parser components
try:
    from utils.parsers.intelligent_parser_orchestrator import IntelligentParserOrchestrator
    from utils.parsers.intelligent_parser_ui import render_intelligent_parser
    INTELLIGENT_PARSER_AVAILABLE = True
except ImportError:
    INTELLIGENT_PARSER_AVAILABLE = False


def render_knowledge_page():
    """Render complete knowledge management page"""
    
    st.title("Knowledge Management")
    
    # Create tabs for different functionality
    tabs = st.tabs([
        "Document Upload",
        "Collection Status",
        "Test Search",
        "Intelligent Parser"
    ])
    
    # Tab 1: Document Upload
    with tabs[0]:
        render_document_upload()
    
    # Tab 2: Collection Status
    with tabs[1]:
        render_collection_status()
    
    # Tab 3: Test Search
    with tabs[2]:
        render_test_search()
    
    # Tab 4: Intelligent Parser
    with tabs[3]:
        render_intelligent_parser_tab()


def render_document_upload():
    """Document upload interface with progress tracking"""
    
    st.header("Upload Documents")
    
    if not RAG_AVAILABLE:
        st.error("RAG system not available")
        return
    
    st.markdown("""
    Upload documents to the knowledge base. The system will:
    - Extract text from PDFs, Word docs, and text files
    - Split into optimized chunks
    - Generate embeddings
    - Store in ChromaDB for retrieval
    """)
    
    # Category selection
    categories = [
        "UKG Pro", "WFM", "Implementation Guide", "Best Practices",
        "Configuration", "Training", "Technical", "General"
    ]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        category = st.selectbox(
            "Document Category",
            categories,
            help="Select category for better organization"
        )
    
    with col2:
        collection_name = st.text_input(
            "Collection Name",
            value="hcmpact_docs",
            help="ChromaDB collection to store documents"
        )
    
    # File upload
    uploaded_files = st.file_uploader(
        "Choose files",
        type=['pdf', 'docx', 'txt', 'md'],
        accept_multiple_files=True,
        help="Supported formats: PDF, Word, Text, Markdown"
    )
    
    if uploaded_files:
        st.info(f"{len(uploaded_files)} file(s) selected")
        
        # Show selected files
        with st.expander("Selected Files"):
            for file in uploaded_files:
                st.write(f"- {file.name} ({file.size:,} bytes)")
        
        # Process button
        if st.button("Process Documents", type="primary"):
            process_documents(uploaded_files, collection_name, category)


def process_documents(files, collection_name, category):
    """Process uploaded documents with progress tracking"""
    
    try:
        from utils.rag_handler import RAGHandler
        
        rag = RAGHandler()
        results = []
        
        # Progress tracking
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, file in enumerate(files):
            # Update progress
            progress = idx / len(files)
            progress_bar.progress(progress)
            status_text.info(f"Processing {file.name}...")
            
            try:
                # Reset file pointer
                file.seek(0)
                
                # Extract text
                text = extract_text_from_file(file)
                
                if not text:
                    results.append({
                        'filename': file.name,
                        'success': False,
                        'error': 'No text extracted'
                    })
                    continue
                
                # Add to RAG
                success = rag.add_document(
                    collection_name=collection_name,
                    text=text,
                    metadata={
                        'source': file.name,
                        'category': category,
                        'upload_date': datetime.now().isoformat()
                    }
                )
                
                results.append({
                    'filename': file.name,
                    'success': success,
                    'text_length': len(text)
                })
                
            except Exception as e:
                results.append({
                    'filename': file.name,
                    'success': False,
                    'error': str(e)
                })
        
        # Complete
        progress_bar.progress(1.0)
        status_text.empty()
        
        # Display results
        display_upload_results(results)
        
    except Exception as e:
        st.error(f"Upload failed: {str(e)}")


def extract_text_from_file(file):
    """Extract text from uploaded file"""
    
    file_type = file.name.split('.')[-1].lower()
    
    try:
        if file_type == 'pdf':
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n\n"
            return text.strip()
        
        elif file_type == 'docx':
            from docx import Document
            doc = Document(file)
            text = "\n\n".join([para.text for para in doc.paragraphs if para.text.strip()])
            return text
        
        elif file_type in ['txt', 'md']:
            text = file.read().decode('utf-8')
            return text
        
        else:
            return None
            
    except Exception as e:
        st.error(f"Error extracting text: {str(e)}")
        return None


def display_upload_results(results):
    """Display upload results"""
    
    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]
    
    if successful:
        st.success(f"Successfully processed {len(successful)}/{len(results)} documents")
        
        with st.expander("Successful Uploads"):
            for result in successful:
                st.write(f"- **{result['filename']}** ({result.get('text_length', 0):,} chars)")
    
    if failed:
        st.error(f"Failed to process {len(failed)} documents")
        
        with st.expander("Failed Uploads"):
            for result in failed:
                st.write(f"- **{result['filename']}**: {result.get('error', 'Unknown error')}")


def render_collection_status():
    """Display collection status and statistics"""
    
    st.header("Collection Status")
    
    if not RAG_AVAILABLE:
        st.error("RAG system not available")
        return
    
    try:
        from utils.rag_handler import RAGHandler
        
        rag = RAGHandler()
        
        # Get collections
        collections = rag.list_collections()
        
        if not collections:
            st.info("No collections found. Upload documents to create collections.")
            return
        
        # Display each collection
        for collection_name in collections:
            with st.expander(f"Collection: {collection_name}", expanded=True):
                try:
                    count = rag.get_collection_count(collection_name)
                    st.metric("Total Chunks", count)
                    
                    # Action buttons
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button(f"Test Search", key=f"test_{collection_name}"):
                            st.session_state[f'test_collection'] = collection_name
                    
                    with col2:
                        if st.button(f"Delete Collection", key=f"delete_{collection_name}"):
                            if rag.delete_collection(collection_name):
                                st.success(f"Deleted {collection_name}")
                                st.rerun()
                            else:
                                st.error("Delete failed")
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        # Overall statistics
        st.markdown("---")
        st.subheader("Overall Statistics")
        
        total_collections = len(collections)
        total_chunks = sum(rag.get_collection_count(c) for c in collections)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Collections", total_collections)
        with col2:
            st.metric("Total Chunks", total_chunks)
        
    except Exception as e:
        st.error(f"Failed to load collections: {str(e)}")


def render_test_search():
    """Test search interface"""
    
    st.header("Test Search")
    
    if not RAG_AVAILABLE:
        st.error("RAG system not available")
        return
    
    st.markdown("""
    Test document retrieval by searching the knowledge base.
    This helps verify documents are properly indexed and searchable.
    """)
    
    try:
        from utils.rag_handler import RAGHandler
        
        rag = RAGHandler()
        collections = rag.list_collections()
        
        if not collections:
            st.warning("No collections available. Upload documents first.")
            return
        
        # Collection selection
        collection = st.selectbox(
            "Select Collection",
            collections,
            help="Choose which collection to search"
        )
        
        # Search query
        query = st.text_input(
            "Search Query",
            placeholder="Enter search terms...",
            help="Enter keywords or questions to search for"
        )
        
        # Number of results
        n_results = st.slider(
            "Number of Results",
            min_value=1,
            max_value=20,
            value=5,
            help="How many results to return"
        )
        
        # Search button
        if st.button("Search", type="primary", disabled=not query):
            with st.spinner("Searching..."):
                results = rag.search(
                    collection_name=collection,
                    query=query,
                    n_results=n_results
                )
                
                if results:
                    st.success(f"Found {len(results)} results")
                    
                    for i, result in enumerate(results, 1):
                        with st.expander(f"Result {i} (Distance: {result.get('distance', 'N/A'):.4f})"):
                            st.markdown(result.get('document', 'No content'))
                            
                            metadata = result.get('metadata', {})
                            if metadata:
                                st.caption(f"Source: {metadata.get('source', 'Unknown')}")
                                st.caption(f"Category: {metadata.get('category', 'Unknown')}")
                else:
                    st.warning("No results found")
        
    except Exception as e:
        st.error(f"Search failed: {str(e)}")


def render_intelligent_parser_tab():
    """Render intelligent parser interface"""
    
    st.header("Intelligent PDF Parser")
    
    if not INTELLIGENT_PARSER_AVAILABLE:
        st.warning("Intelligent parser not available")
        st.info("""
        The intelligent parser requires additional components:
        - pdf_structure_analyzer.py
        - parser_code_generator.py
        - intelligent_parser_orchestrator.py
        - intelligent_parser_ui.py
        
        These files should be in utils/parsers/ directory.
        """)
        return
    
    try:
        # Initialize orchestrator
        orchestrator = IntelligentParserOrchestrator()
        
        # Render the intelligent parser UI
        render_intelligent_parser(orchestrator)
        
    except Exception as e:
        st.error(f"Failed to initialize intelligent parser: {str(e)}")
        st.exception(e)


# For backward compatibility
def render():
    """Legacy render function"""
    render_knowledge_page()
