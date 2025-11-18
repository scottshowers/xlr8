import streamlit as st
from utils.rag_handler import RAGHandler
import logging

logger = logging.getLogger(__name__)


def render_chromadb_diagnostic():
    """Render ChromaDB diagnostic section - safe version."""
    
    try:
        st.sidebar.markdown("---")
        st.sidebar.subheader("📊 HCMPACT LLM")
        
        # Initialize RAG handler
        try:
            rag = RAGHandler()
        except Exception as e:
            st.sidebar.error(f"⚠️ Init Error: {str(e)[:30]}")
            return
        
        # Get collections
        try:
            collections = rag.list_collections()
            
            if not collections:
                st.sidebar.info("No data yet")
                return
            
            # Show collection stats
            for collection_name in collections:
                try:
                    count = rag.get_collection_count(collection_name)
                    st.sidebar.metric(collection_name, f"{count:,}")
                except Exception as e:
                    st.sidebar.warning(f"{collection_name}: Error")
            
            # Simple search test
            with st.sidebar.expander("🔍 Test"):
                test_query = st.text_input("Query", key="sidebar_search", placeholder="Test search...")
                
                if test_query:
                    try:
                        results = rag.search("hcmpact_docs", test_query, n_results=3)
                        
                        if results:
                            st.success(f"{len(results)} results")
                            for i, result in enumerate(results[:2], 1):
                                distance = result.get('distance', 0)
                                source = result.get('metadata', {}).get('source', 'Unknown')
                                st.text(f"{i}. {source[:20]}... ({distance:.3f})")
                        else:
                            st.warning("No results")
                    except Exception as e:
                        st.error(f"Error: {str(e)[:30]}")
        
        except Exception as e:
            st.sidebar.error(f"Error: {str(e)[:30]}")
    
    except Exception as e:
        st.sidebar.error("Unavailable")
        logger.error(f"Diagnostic error: {e}")


def render_sidebar():
    """Main sidebar rendering function."""
    
    try:
        # App title/logo
        st.sidebar.title("⚡ XLR8")
        st.sidebar.caption("UKG Implementation Assistant")
        
        # Navigation info (if needed)
        # st.sidebar.markdown("---")
        # st.sidebar.markdown("### Navigation")
        # Add navigation elements here if needed
        
        # ChromaDB diagnostic
        render_chromadb_diagnostic()
        
        # Footer
        st.sidebar.markdown("---")
        st.sidebar.caption("Powered by Claude + Ollama")
        
    except Exception as e:
        st.sidebar.error("Sidebar error")
        logger.error(f"Sidebar rendering error: {e}", exc_info=True)
