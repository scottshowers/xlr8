import streamlit as st
from utils.rag_handler import RAGHandler
import logging

logger = logging.getLogger(__name__)


def render_chromadb_diagnostic():
    """Render ChromaDB diagnostic in sidebar - safe version that won't crash."""
    
    try:
        st.sidebar.markdown("---")
        st.sidebar.subheader("📊 HCMPACT LLM Status")
        
        # Initialize RAG handler
        try:
            rag = RAGHandler()
        except Exception as e:
            st.sidebar.error(f"⚠️ RAG Init Error: {str(e)[:50]}")
            return
        
        # Get collections
        try:
            collections = rag.list_collections()
            
            if not collections:
                st.sidebar.info("No collections yet")
                return
            
            # Show collection stats
            for collection_name in collections:
                try:
                    count = rag.get_collection_count(collection_name)
                    st.sidebar.metric(collection_name, f"{count:,} chunks")
                except Exception as e:
                    st.sidebar.warning(f"{collection_name}: Error")
                    logger.error(f"Collection count error: {e}")
            
            # Simple search test
            with st.sidebar.expander("🔍 Test Search"):
                test_query = st.text_input("Query", key="sidebar_search")
                
                if test_query:
                    try:
                        results = rag.search("hcmpact_docs", test_query, n_results=3)
                        
                        if results:
                            st.success(f"Found {len(results)} results")
                            for i, result in enumerate(results[:2], 1):
                                distance = result.get('distance', 'N/A')
                                source = result.get('metadata', {}).get('source', 'Unknown')
                                st.text(f"{i}. {source} ({distance:.3f})")
                        else:
                            st.warning("No results")
                    except Exception as e:
                        st.error(f"Search error: {str(e)[:50]}")
        
        except Exception as e:
            st.sidebar.error(f"ChromaDB Error: {str(e)[:50]}")
            logger.error(f"Diagnostic error: {e}", exc_info=True)
    
    except Exception as e:
        st.sidebar.error("Diagnostic unavailable")
        logger.error(f"Sidebar diagnostic crashed: {e}")
