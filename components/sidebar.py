import streamlit as st
from utils.rag_handler import RAGHandler
import logging

logger = logging.getLogger(__name__)


def _get_chromadb_stats():
    """Get ChromaDB statistics safely."""
    try:
        rag = RAGHandler()
        collections = rag.list_collections()
        
        total_docs = 0
        customer_docs = 0
        global_docs = 0
        
        for collection_name in collections:
            try:
                count = rag.get_collection_count(collection_name)
                total_docs += count
                
                # Try to differentiate customer vs global
                # Global docs typically in 'hcmpact_knowledge' collection
                if 'knowledge' in collection_name.lower():
                    global_docs += count
                else:
                    customer_docs += count
                    
            except Exception as e:
                logger.error(f"Error counting {collection_name}: {e}")
                
        return {
            'total': total_docs,
            'customer': customer_docs,
            'global': global_docs
        }
    except Exception as e:
        logger.error(f"ChromaDB stats error: {e}")
        return {'total': 0, 'customer': 0, 'global': 0}


def _get_project_count():
    """Get number of active projects."""
    try:
        # Check if using Supabase
        if hasattr(st.session_state, 'use_supabase') and st.session_state.use_supabase:
            try:
                from utils.database.storage_adapter import ProjectStorage
                projects = ProjectStorage.list_all()
                return len(projects) if projects else 0
            except:
                pass
        
        # Fallback to session state
        projects = st.session_state.get('projects', {})
        if isinstance(projects, dict):
            return len(projects)
        elif isinstance(projects, list):
            return len(projects)
        return 0
    except Exception as e:
        logger.error(f"Project count error: {e}")
        return 0


def _render_statistics():
    """Render statistics section."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Statistics")
    
    # Get stats
    chromadb_stats = _get_chromadb_stats()
    project_count = _get_project_count()
    
    # Display in compact format
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        st.metric("Projects", project_count)
        st.metric("Customer Docs", chromadb_stats['customer'])
    
    with col2:
        st.metric("LLM Docs", chromadb_stats['total'])
        st.metric("Global Docs", chromadb_stats['global'])


def _render_security_features():
    """Render security features section."""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔒 Security Features")
    
    # Security features with icons
    security_features = [
        ("🔐", "End-to-End Encryption"),
        ("🏠", "Local LLM Processing"),
        ("🚫", "No Data Sharing"),
        ("🔑", "Secure API Auth"),
        ("📝", "Audit Logging"),
        ("🗑️", "Auto Data Cleanup"),
        ("✅", "GDPR Compliant"),
        ("🛡️", "PII Protection")
    ]
    
    # Display in compact two-column format
    for i in range(0, len(security_features), 2):
        col1, col2 = st.sidebar.columns(2)
        
        # First feature
        icon1, text1 = security_features[i]
        with col1:
            st.markdown(f"""
            <div style='font-size: 0.75rem; padding: 0.25rem 0;'>
                {icon1} {text1}
            </div>
            """, unsafe_allow_html=True)
        
        # Second feature (if exists)
        if i + 1 < len(security_features):
            icon2, text2 = security_features[i + 1]
            with col2:
                st.markdown(f"""
                <div style='font-size: 0.75rem; padding: 0.25rem 0;'>
                    {icon2} {text2}
                </div>
                """, unsafe_allow_html=True)


def render_chromadb_diagnostic():
    """Render ChromaDB diagnostic section - advanced expandable."""
    
    try:
        st.sidebar.markdown("---")
        
        with st.sidebar.expander("🔍 ChromaDB Diagnostic"):
            try:
                rag = RAGHandler()
                collections = rag.list_collections()
                
                if not collections:
                    st.info("No collections yet")
                    return
                
                # Show detailed collection stats
                st.markdown("**Collections:**")
                for collection_name in collections:
                    try:
                        count = rag.get_collection_count(collection_name)
                        st.text(f"• {collection_name}: {count:,} chunks")
                    except Exception as e:
                        st.text(f"• {collection_name}: Error")
                
                # Search test
                st.markdown("---")
                st.markdown("**Test Search:**")
                test_query = st.text_input("Query", key="sidebar_search", placeholder="Test...")
                
                if test_query:
                    try:
                        results = rag.search("hcmpact_docs", test_query, n_results=3)
                        
                        if results:
                            st.success(f"✅ {len(results)} results")
                            for i, result in enumerate(results[:2], 1):
                                distance = result.get('distance', 0)
                                source = result.get('metadata', {}).get('source', 'Unknown')
                                st.caption(f"{i}. {source[:25]}... (dist: {distance:.3f})")
                        else:
                            st.warning("No results found")
                    except Exception as e:
                        st.error(f"Search error: {str(e)[:40]}")
            
            except Exception as e:
                st.error(f"Init error: {str(e)[:40]}")
    
    except Exception as e:
        logger.error(f"Diagnostic error: {e}")


def render_sidebar():
    """Main sidebar rendering function."""
    
    try:
        # App title/logo
        st.sidebar.title("⚡ XLR8")
        st.sidebar.caption("UKG Implementation Assistant")
        
        # Statistics section
        _render_statistics()
        
        # ChromaDB diagnostic (expandable)
        render_chromadb_diagnostic()
        
        # Security features section
        _render_security_features()
        
        # Footer
        st.sidebar.markdown("---")
        st.sidebar.caption("Powered by Claude + Ollama")
        
    except Exception as e:
        st.sidebar.error("Sidebar error")
        logger.error(f"Sidebar rendering error: {e}", exc_info=True)
