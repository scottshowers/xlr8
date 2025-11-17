import streamlit as st
from utils.rag_handler import RAGHandler
from utils.document_processor import DocumentProcessor, render_upload_interface
import logging

logger = logging.getLogger(__name__)


def show():
    """Knowledge page for managing HCMPACT LLM documents."""
    
    st.title("📚 HCMPACT LLM Base")
    st.markdown("Manage your UKG Pro and WFM implementation documents")
    
    # Initialize handlers
    rag = RAGHandler()
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["📤 Upload", "📊 Status", "🗑️ Manage"])
    
    # TAB 1: UPLOAD
    with tab1:
        render_upload_interface()
    
    # TAB 2: STATUS
    with tab2:
        st.subheader("Collection Status")
        
        collections = rag.list_collections()
        
        if not collections:
            st.info("No collections yet. Upload documents to get started.")
        else:
            for collection_name in collections:
                count = rag.get_collection_count(collection_name)
                
                with st.expander(f"📁 {collection_name} ({count:,} chunks)", expanded=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Total Chunks", f"{count:,}")
                    
                    with col2:
                        if st.button(f"🗑️ Delete {collection_name}", key=f"del_{collection_name}"):
                            if rag.delete_collection(collection_name):
                                st.success(f"Deleted {collection_name}")
                                st.rerun()
                            else:
                                st.error("Failed to delete collection")
                    
                    # Test search
                    st.markdown("**Test Search:**")
                    test_query = st.text_input(
                        "Enter search query",
                        key=f"search_{collection_name}",
                        placeholder="e.g., timecard approval"
                    )
                    
                    if test_query:
                        with st.spinner("Searching..."):
                            results = rag.search(collection_name, test_query, n_results=3)
                            
                            if results:
                                st.success(f"Found {len(results)} results")
                                for i, result in enumerate(results, 1):
                                    st.markdown(f"**Result {i}** (distance: {result['distance']:.4f})")
                                    st.markdown(f"*Source:* {result['metadata'].get('source', 'Unknown')}")
                                    st.markdown(f"*Category:* {result['metadata'].get('category', 'General')}")
                                    st.text(result['document'][:200] + "...")
                                    st.divider()
                            else:
                                st.warning("No results found")
    
    # TAB 3: MANAGE
    with tab3:
        st.subheader("Database Management")
        
        st.warning("⚠️ **Danger Zone**")
        
        # Nuclear clear button
        st.markdown("### Clear All Data")
        st.markdown("This will permanently delete ALL collections and documents from the HCMPACT LLM.")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            confirm = st.checkbox("I understand this cannot be undone")
        
        with col2:
            if confirm:
                if st.button("🔥 NUCLEAR CLEAR", type="primary"):
                    with st.spinner("Clearing all data..."):
                        if rag.reset_all():
                            st.success("✅ All data cleared successfully")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("Failed to clear data")
        
        # Statistics
        st.divider()
        st.subheader("Statistics")
        
        collections = rag.list_collections()
        total_chunks = sum(rag.get_collection_count(col) for col in collections)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Collections", len(collections))
        with col2:
            st.metric("Total Chunks", f"{total_chunks:,}")
        
        # Storage info
        st.divider()
        st.subheader("Storage Information")
        st.info("📁 **Persistent Storage:** /data/chromadb")
        st.markdown("""
        - ✅ Data survives Railway deployments
        - ✅ No need to re-upload after redeploy
        - ✅ Backed up by Railway volume
        """)


if __name__ == "__main__":
    show()
