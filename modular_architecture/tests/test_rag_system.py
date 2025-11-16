"""
RAG System Module Test Template

Test your RAG implementation independently before integration.

HOW TO USE:
1. Run: streamlit run test_rag_system.py
2. Add test documents
3. Test search functionality
4. Verify interface compliance
5. Integrate with feature flag when ready
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
import time

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from interfaces.rag_interface import RAGInterface, SearchMethod


# ============================================
# IMPORT YOUR RAG HANDLER HERE
# ============================================
# Example:
# from utils.rag.advanced_handler import AdvancedRAGHandler
# rag = AdvancedRAGHandler()

# For testing, use original:
from utils.rag.handler import RAGHandler
rag = RAGHandler()


def main():
    st.set_page_config(
        page_title="RAG System Test",
        page_icon="🧠",
        layout="wide"
    )
    
    st.title("🧠 RAG System Module Test")
    
    # Initialize session state
    if 'test_docs' not in st.session_state:
        st.session_state.test_docs = []
    
    # Sidebar - System Info
    with st.sidebar:
        st.markdown("### System Information")
        
        try:
            info = rag.get_system_info()
            st.success(f"**{info['name']}** v{info['version']}")
            st.write(f"**Vector DB:** {info['vector_db']}")
            st.write(f"**Embedding:** {info['embedding_model']}")
            st.write(f"**Chunk Size:** {info['chunk_size']}")
        except Exception as e:
            st.error(f"Failed to get system info: {e}")
        
        st.markdown("---")
        st.markdown("### Statistics")
        
        try:
            stats = rag.get_stats()
            st.metric("Total Documents", stats['total_documents'])
            st.metric("Total Chunks", stats['total_chunks'])
            st.metric("Storage (MB)", f"{stats['storage_size_mb']:.2f}")
        except Exception as e:
            st.error(f"Stats error: {e}")
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📤 Add Documents",
        "🔍 Test Search",
        "✅ Interface Test",
        "⚡ Performance Test"
    ])
    
    # TAB 1: Add Documents
    with tab1:
        test_add_documents()
    
    # TAB 2: Test Search
    with tab2:
        test_search_functionality()
    
    # TAB 3: Interface Compliance
    with tab3:
        test_interface_compliance(rag)
    
    # TAB 4: Performance
    with tab4:
        test_performance()


def test_add_documents():
    """Test document addition"""
    
    st.markdown("### Add Test Documents")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        doc_name = st.text_input("Document Name", "test_doc_1.txt")
        category = st.selectbox("Category", ["Test", "UKG_Standards", "Client_Docs"])
        content = st.text_area(
            "Document Content",
            "This is a test document about UKG earnings configuration...",
            height=200
        )
    
    with col2:
        st.markdown("**Metadata (Optional)**")
        meta_author = st.text_input("Author", "Test User")
        meta_date = st.date_input("Date")
        
        metadata = {
            'author': meta_author,
            'date': str(meta_date)
        }
    
    if st.button("➕ Add Document", type="primary"):
        with st.spinner("Adding document..."):
            try:
                result = rag.add_document(
                    content=content,
                    doc_name=doc_name,
                    category=category,
                    metadata=metadata
                )
                
                if result['success']:
                    st.success(f"✅ Added: {doc_name}")
                    st.json(result)
                    st.session_state.test_docs.append(doc_name)
                else:
                    st.error(f"❌ Failed: {result['errors']}")
            
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    # Show added documents
    if st.session_state.test_docs:
        st.markdown("---")
        st.markdown("### Added Test Documents")
        
        for i, doc in enumerate(st.session_state.test_docs):
            col1, col2 = st.columns([4, 1])
            col1.write(f"{i+1}. {doc}")
            if col2.button("🗑️", key=f"del_{i}"):
                st.session_state.test_docs.pop(i)
                st.rerun()


def test_search_functionality():
    """Test search capabilities"""
    
    st.markdown("### Test Search")
    
    # Search options
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        query = st.text_input("Search Query", "How to configure earnings?")
    
    with col2:
        method = st.selectbox(
            "Search Method",
            [m.value for m in SearchMethod]
        )
    
    with col3:
        n_results = st.number_input("Results", min_value=1, max_value=20, value=5)
    
    if st.button("🔍 Search", type="primary"):
        with st.spinner("Searching..."):
            try:
                start_time = time.time()
                
                results = rag.search(
                    query=query,
                    method=SearchMethod(method),
                    n_results=n_results
                )
                
                search_time = time.time() - start_time
                
                st.success(f"Found {len(results)} results in {search_time:.3f}s")
                
                # Display results
                for i, result in enumerate(results, 1):
                    with st.expander(f"Result {i} - {result['doc_name']} (Score: {result['score']:.3f})"):
                        st.write(f"**Category:** {result['category']}")
                        st.write(f"**Score:** {result['score']:.4f}")
                        st.markdown("**Text:**")
                        st.text(result['text'][:500] + "..." if len(result['text']) > 500 else result['text'])
                        
                        if result.get('metadata'):
                            st.json(result['metadata'])
            
            except Exception as e:
                st.error(f"Search error: {str(e)}")


def test_interface_compliance(rag):
    """Test interface compliance"""
    
    st.markdown("### Interface Compliance Check")
    
    required_methods = [
        'add_document',
        'search',
        'delete_document',
        'get_stats',
        'list_documents',
        'clear_category',
        'get_system_info'
    ]
    
    results = {}
    
    for method in required_methods:
        has_method = hasattr(rag, method)
        results[method] = has_method
        
        col1, col2 = st.columns([3, 1])
        col1.write(f"**{method}**")
        if has_method:
            col2.success("✅")
        else:
            col2.error("❌")
    
    compliance_rate = (sum(results.values()) / len(results)) * 100
    
    st.markdown("---")
    if compliance_rate == 100:
        st.success(f"✅ Fully compliant with RAGInterface ({compliance_rate:.0f}%)")
    else:
        st.error(f"❌ Interface compliance: {compliance_rate:.0f}%")
    
    # Test return value formats
    st.markdown("### Return Value Format Test")
    
    if st.button("Test Return Formats"):
        with st.spinner("Testing..."):
            format_results = {}
            
            # Test get_stats return format
            try:
                stats = rag.get_stats()
                required_keys = ['total_documents', 'total_chunks', 'categories', 'storage_size_mb']
                has_all_keys = all(key in stats for key in required_keys)
                format_results['get_stats'] = has_all_keys
            except:
                format_results['get_stats'] = False
            
            # Test get_system_info return format
            try:
                info = rag.get_system_info()
                required_keys = ['name', 'version', 'vector_db', 'embedding_model']
                has_all_keys = all(key in info for key in required_keys)
                format_results['get_system_info'] = has_all_keys
            except:
                format_results['get_system_info'] = False
            
            # Display results
            for method, passed in format_results.items():
                if passed:
                    st.success(f"✅ {method} - Correct format")
                else:
                    st.error(f"❌ {method} - Incorrect format")


def test_performance():
    """Test RAG system performance"""
    
    st.markdown("### Performance Benchmarks")
    
    # Test parameters
    col1, col2 = st.columns(2)
    
    with col1:
        num_test_docs = st.number_input("Number of test documents", 1, 100, 10)
        doc_size = st.number_input("Document size (chars)", 100, 10000, 1000)
    
    with col2:
        num_queries = st.number_input("Number of test queries", 1, 50, 10)
    
    if st.button("🚀 Run Performance Test"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = {
            'add_times': [],
            'search_times': [],
            'total_time': 0
        }
        
        start_total = time.time()
        
        # Test 1: Add Documents
        status_text.text("Testing document addition...")
        for i in range(num_test_docs):
            content = "Test content " * (doc_size // 13)
            
            start = time.time()
            try:
                rag.add_document(
                    content=content,
                    doc_name=f"perf_test_{i}",
                    category="Performance_Test"
                )
                results['add_times'].append(time.time() - start)
            except:
                pass
            
            progress_bar.progress((i + 1) / (num_test_docs + num_queries))
        
        # Test 2: Search
        status_text.text("Testing search performance...")
        for i in range(num_queries):
            start = time.time()
            try:
                rag.search(
                    query=f"test query {i}",
                    n_results=5
                )
                results['search_times'].append(time.time() - start)
            except:
                pass
            
            progress_bar.progress((num_test_docs + i + 1) / (num_test_docs + num_queries))
        
        results['total_time'] = time.time() - start_total
        
        # Display results
        status_text.text("Complete!")
        progress_bar.progress(1.0)
        
        col1, col2, col3 = st.columns(3)
        
        col1.metric(
            "Avg Add Time",
            f"{sum(results['add_times']) / len(results['add_times']):.3f}s"
        )
        col2.metric(
            "Avg Search Time",
            f"{sum(results['search_times']) / len(results['search_times']):.3f}s"
        )
        col3.metric(
            "Total Time",
            f"{results['total_time']:.2f}s"
        )
        
        # Performance rating
        avg_search = sum(results['search_times']) / len(results['search_times'])
        
        if avg_search < 0.5:
            st.success("⚡ Excellent search performance!")
        elif avg_search < 1.5:
            st.info("👍 Good search performance")
        else:
            st.warning("⚠️ Consider optimization")
        
        # Cleanup
        if st.button("🗑️ Cleanup Test Documents"):
            try:
                rag.clear_category("Performance_Test")
                st.success("Cleaned up test documents")
            except:
                st.error("Cleanup failed")


if __name__ == "__main__":
    main()
