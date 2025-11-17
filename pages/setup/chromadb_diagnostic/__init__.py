"""
ChromaDB Diagnostic Tool for XLR8

Checks:
- Is ChromaDB initialized?
- How many documents are indexed?
- Can we search and find results?
- What are the chunk sizes?
- What are the search parameters?

Author: HCMPACT
Version: 1.0
"""

import streamlit as st
from typing import Dict, Any, List


def render_chromadb_diagnostic():
    """Diagnostic page for ChromaDB"""
    
    st.title("🔍 ChromaDB Diagnostic Tool")
    
    st.markdown("""
    This tool helps diagnose why ChromaDB isn't finding your documents.
    """)
    
    # Check if RAG handler exists
    st.markdown("## 1. RAG Handler Status")
    
    rag_handler = st.session_state.get('rag_handler')
    
    if not rag_handler:
        st.error("❌ RAG Handler NOT initialized!")
        st.markdown("""
        **Fix:** Go to Knowledge tab and upload documents to initialize ChromaDB.
        """)
        return
    else:
        st.success("✅ RAG Handler initialized")
    
    # Check ChromaDB collection
    st.markdown("## 2. ChromaDB Collection Status")
    
    try:
        # Try to access the collection
        if hasattr(rag_handler, 'collection'):
            collection = rag_handler.collection
            count = collection.count()
            
            st.success(f"✅ ChromaDB Collection exists: **{count} documents indexed**")
            
            if count == 0:
                st.warning("⚠️ Collection is empty! No documents indexed yet.")
                st.markdown("**Fix:** Upload documents in Knowledge tab")
            
        else:
            st.error("❌ RAG handler has no 'collection' attribute")
            st.code(f"RAG handler type: {type(rag_handler)}")
            st.code(f"RAG handler attributes: {dir(rag_handler)}")
            
    except Exception as e:
        st.error(f"❌ Error accessing collection: {e}")
    
    # Test search functionality
    st.markdown("## 3. Search Test")
    
    test_query = st.text_input(
        "Test Query",
        value="earnings configuration",
        help="Enter a query to test if ChromaDB can find relevant documents"
    )
    
    num_results = st.slider("Number of results", 1, 20, 10)
    
    if st.button("🔍 Test Search", type="primary"):
        if not test_query:
            st.warning("Enter a test query first")
        else:
            _test_search(rag_handler, test_query, num_results)
    
    # Show collection details
    st.markdown("## 4. Collection Details")
    
    if st.button("📊 Show Collection Metadata"):
        _show_collection_details(rag_handler)
    
    # Check search parameters
    st.markdown("## 5. Search Parameters")
    
    if hasattr(rag_handler, 'search'):
        st.info("✅ RAG handler has 'search' method")
        
        # Show search method signature
        import inspect
        sig = inspect.signature(rag_handler.search)
        st.code(f"search{sig}")
    else:
        st.error("❌ RAG handler has no 'search' method")
        st.markdown("Available methods:")
        methods = [m for m in dir(rag_handler) if not m.startswith('_')]
        st.code('\n'.join(methods))


def _test_search(rag_handler, query: str, n_results: int):
    """Test ChromaDB search"""
    
    st.markdown("### Search Results")
    
    try:
        with st.spinner(f"Searching for: '{query}'..."):
            # Try to search
            results = rag_handler.search(
                query_text=query,
                n_results=n_results
            )
        
        if not results or len(results) == 0:
            st.error(f"❌ Found 0 results for '{query}'")
            st.markdown("""
            **Possible causes:**
            1. No documents contain this content
            2. Search threshold too strict
            3. Documents not properly indexed
            4. Wrong search method/parameters
            """)
        else:
            st.success(f"✅ Found {len(results)} results")
            
            for i, result in enumerate(results, 1):
                with st.expander(f"Result {i}: {result.get('document', 'Unknown')}", expanded=(i<=3)):
                    st.markdown(f"**Document:** {result.get('document', 'N/A')}")
                    st.markdown(f"**Category:** {result.get('category', 'N/A')}")
                    
                    if 'distance' in result:
                        similarity = 1.0 - result['distance']
                        st.markdown(f"**Similarity:** {similarity:.2%} (distance: {result['distance']:.4f})")
                    
                    if 'content' in result:
                        content = result['content']
                        st.markdown("**Content Preview:**")
                        st.text(content[:500] + "..." if len(content) > 500 else content)
                    
                    if 'metadata' in result:
                        st.markdown("**Metadata:**")
                        st.json(result['metadata'])
    
    except Exception as e:
        st.error(f"❌ Search failed: {e}")
        st.exception(e)


def _show_collection_details(rag_handler):
    """Show detailed collection information"""
    
    st.markdown("### Collection Metadata")
    
    try:
        collection = rag_handler.collection
        
        # Basic info
        st.markdown(f"**Name:** {collection.name}")
        st.markdown(f"**Count:** {collection.count()} documents")
        
        # Try to peek at some data
        if collection.count() > 0:
            st.markdown("### Sample Data (first 5 items)")
            
            try:
                sample = collection.peek(limit=5)
                
                st.markdown("**IDs:**")
                st.code(sample.get('ids', []))
                
                st.markdown("**Documents (first 200 chars each):**")
                docs = sample.get('documents', [])
                for i, doc in enumerate(docs, 1):
                    st.text(f"{i}. {doc[:200]}...")
                
                if 'metadatas' in sample:
                    st.markdown("**Metadatas:**")
                    st.json(sample.get('metadatas', []))
                
                if 'distances' in sample:
                    st.markdown("**Distances:**")
                    st.code(sample.get('distances', []))
                    
            except Exception as e:
                st.warning(f"Could not peek at data: {e}")
        
        # Try to get collection metadata
        try:
            metadata = collection.metadata
            if metadata:
                st.markdown("### Collection Metadata")
                st.json(metadata)
        except:
            pass
            
    except Exception as e:
        st.error(f"Error getting collection details: {e}")
        st.exception(e)


# For use in sidebar or as standalone page
if __name__ == "__main__":
    render_chromadb_diagnostic()
