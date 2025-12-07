"""
Professional Error Handler Utility
Converts raw errors into friendly, helpful messages with recovery steps
"""

import streamlit as st
from typing import Optional, Dict, Any
import traceback


class ErrorHandler:
    """Professional error handling with user-friendly messages and recovery steps"""
    
    @staticmethod
    def handle_llm_error(error: Exception, context: str = "operation") -> None:
        """Handle LLM connection errors with helpful guidance"""
        
        error_msg = str(error).lower()
        
        if "connection" in error_msg or "timeout" in error_msg:
            st.error("😕 Can't Reach AI Server")
            
            with st.expander("ℹ️ What happened & how to fix it"):
                st.markdown("""
                **What happened:**
                The app couldn't connect to your AI server. This usually means:
                - The server is temporarily down
                - Network connection was lost  
                - Firewall is blocking the connection
                
                **What you can do:**
                1. Go to **Setup → Connections** to check server status
                2. Wait 30 seconds and try again
                3. Verify the server is running at: `http://178.156.190.64:11435`
                4. If problem persists, check Railway logs
                
                **Need help?** Contact your system administrator or check server logs.
                """)
                
                if st.button("🔌 Go to Connections", type="primary"):
                    st.session_state.navigate_to = "connections"
                    st.rerun()
        
        elif "unauthorized" in error_msg or "401" in error_msg:
            st.error("🔐 Authentication Failed")
            
            with st.expander("ℹ️ What happened & how to fix it"):
                st.markdown("""
                **What happened:**
                The AI server rejected the authentication credentials.
                
                **What you can do:**
                1. Check that username and password are correct in `config.py`
                2. Verify LLM server authentication settings
                3. Restart the application after config changes
                
                **Technical details:**
                - Username: `xlr8`
                - Server expects HTTP Basic Auth
                """)
        
        elif "model" in error_msg:
            st.error("🤖 AI Model Not Available")
            
            with st.expander("ℹ️ What happened & how to fix it"):
                st.markdown("""
                **What happened:**
                The requested AI model isn't available on the server.
                
                **What you can do:**
                1. Go to **Setup → Connections** 
                2. Try selecting a different model
                3. Verify model is installed: `ollama list`
                4. Pull model if needed: `ollama pull deepseek-r1:7b`
                
                **Available models should include:**
                - mistral:7b (fast)
                - deepseek-r1:7b (reasoning)
                """)
        
        else:
            # Generic LLM error
            st.error(f"⚠️ AI Error During {context}")
            
            with st.expander("ℹ️ Error details & troubleshooting"):
                st.markdown(f"""
                **What happened:**
                An unexpected error occurred while communicating with the AI.
                
                **Error message:**
                ```
                {str(error)}
                ```
                
                **What you can do:**
                1. Try your request again (might be temporary)
                2. Simplify your request and retry
                3. Check **Setup → Connections** for server status
                4. Review Railway logs for detailed errors
                """)
    
    @staticmethod
    def handle_rag_error(error: Exception) -> None:
        """Handle RAG/knowledge base errors"""
        
        error_msg = str(error).lower()
        
        if "no documents" in error_msg or "empty" in error_msg or "'nonetype'" in error_msg:
            st.warning("📚 Knowledge Base Is Empty")
            
            with st.expander("ℹ️ What happened & how to fix it"):
                st.markdown("""
                **What happened:**
                The AI tried to search for relevant information, but no documents 
                have been uploaded to your knowledge base yet.
                
                **What you can do:**
                1. Go to **Setup → HCMPACT LLM Seeding**
                2. Upload UKG documentation (PDFs, Word docs, etc.)
                3. Wait for indexing to complete
                4. Come back and try your question again
                
                **Recommended first uploads:**
                - UKG Pro configuration guides
                - UKG WFM documentation
                - Your company's implementation standards
                - Industry best practices documents
                """)
                
                if st.button("📚 Go to Knowledge Base", type="primary"):
                    st.session_state.navigate_to = "knowledge"
                    st.rerun()
        
        elif "chromadb" in error_msg or "vector" in error_msg:
            st.error("🗄️ Knowledge Base Error")
            
            with st.expander("ℹ️ What happened & how to fix it"):
                st.markdown("""
                **What happened:**
                There was a problem accessing the knowledge base (vector database).
                
                **What you can do:**
                1. Try refreshing the page
                2. Check if ChromaDB is running properly
                3. Verify disk space is available
                4. If problem persists, check server logs
                
                **Technical details:**
                - Vector database: ChromaDB
                - Location: `/root/.xlr8_chroma`
                """)
        
        else:
            st.error("🔍 Search Error")
            
            with st.expander("ℹ️ Error details"):
                st.markdown(f"""
                **What happened:**
                An error occurred while searching the knowledge base.
                
                **Error message:**
                ```
                {str(error)}
                ```
                
                **What you can do:**
                1. Try searching with different keywords
                2. Check if documents are properly uploaded
                3. Refresh the page and try again
                """)
    
    @staticmethod
    def handle_file_error(error: Exception, filename: str = "document") -> None:
        """Handle file upload/parsing errors"""
        
        error_msg = str(error).lower()
        
        if "size" in error_msg or "large" in error_msg:
            st.error("📦 File Too Large")
            
            with st.expander("ℹ️ What happened & how to fix it"):
                st.markdown("""
                **What happened:**
                The file exceeds the maximum upload size.
                
                **What you can do:**
                1. Try compressing the PDF (reduce image quality)
                2. Split large documents into smaller parts
                3. Remove unnecessary pages
                4. Contact admin to increase upload limit
                
                **Current limit:** 200MB
                """)
        
        elif "corrupt" in error_msg or "invalid" in error_msg or "read" in error_msg:
            st.error("📄 Document Can't Be Read")
            
            with st.expander("ℹ️ What happened & how to fix it"):
                st.markdown(f"""
                **What happened:**
                The file `{filename}` appears to be corrupted or in an unsupported format.
                
                **What you can do:**
                1. Try opening the file on your computer to verify it works
                2. Re-save as PDF from the original application
                3. Make sure the file isn't password protected
                4. Try converting to a different format
                5. Try a different document
                
                **Supported formats:**
                - PDF (.pdf)
                - Excel (.xlsx, .xls, .csv)
                - Word (.docx, .doc)
                
                **Maximum size:** 200MB
                """)
        
        elif "password" in error_msg or "encrypted" in error_msg:
            st.error("🔒 Document Is Protected")
            
            with st.expander("ℹ️ What happened & how to fix it"):
                st.markdown("""
                **What happened:**
                The document is password protected or encrypted.
                
                **What you can do:**
                1. Open the document and remove password protection
                2. Save a copy without encryption
                3. Use the unprotected version for upload
                
                **How to remove password:**
                - **PDF:** Open → File → Properties → Security → Remove
                - **Excel:** File → Info → Protect Workbook → Remove password
                """)
        
        else:
            st.error(f"❌ Error Processing {filename}")
            
            with st.expander("ℹ️ Error details & troubleshooting"):
                st.markdown(f"""
                **What happened:**
                An unexpected error occurred while processing the file.
                
                **Error message:**
                ```
                {str(error)}
                ```
                
                **What you can do:**
                1. Verify the file isn't corrupted
                2. Try a different file format
                3. Check file size is under 200MB
                4. Try uploading a different document
                5. Contact support if problem persists
                """)
    
    @staticmethod
    def handle_supabase_error(error: Exception, operation: str = "save") -> None:
        """Handle Supabase/database errors"""
        
        st.warning("💾 Database Connection Issue")
        
        with st.expander("ℹ️ What happened & how to fix it"):
            st.markdown(f"""
            **What happened:**
            Couldn't {operation} to the database. Don't worry - your work is still 
            safe in this browser session!
            
            **Your data is NOT lost!**
            Everything you've done is saved in browser memory and will work 
            until you close the tab or refresh.
            
            **What you can do:**
            1. **Continue working** (data saved locally)
            2. **Download any important results** right now
            3. Check **Setup → Connections** for database status
            4. Try refreshing in a few minutes
            5. If urgent, take screenshots of results
            
            **Technical details:**
            - Database: Supabase PostgreSQL
            - Operation: {operation}
            - Data is in session state (browser memory)
            - Will persist until page refresh
            """)
            
            if st.button("📊 View Connection Status", type="primary"):
                st.session_state.navigate_to = "connections"
                st.rerun()
    
    @staticmethod
    def handle_generic_error(error: Exception, context: str = "operation", show_trace: bool = False) -> None:
        """Handle any other errors with helpful fallback"""
        
        st.error(f"⚠️ Unexpected Error During {context}")
        
        with st.expander("ℹ️ Error details & what to try"):
            st.markdown(f"""
            **What happened:**
            An unexpected error occurred. This might be temporary.
            
            **Error type:**
            `{type(error).__name__}`
            
            **Error message:**
            ```
            {str(error)}
            ```
            
            **What you can do:**
            1. **Try again** - might be temporary
            2. **Refresh the page** (Ctrl+R or F5)
            3. **Check your internet connection**
            4. **Review Railway logs** for detailed errors
            5. **Contact support** if problem persists
            
            **Helpful info for support:**
            - Time: Check your local time
            - Page: Note which page you're on
            - Action: What you were trying to do
            """)
            
            if show_trace:
                st.markdown("**Full stack trace:**")
                st.code(traceback.format_exc())
    
    @staticmethod
    def show_success(message: str, details: Optional[str] = None, autoclose: int = 3) -> None:
        """Show success message (for consistency)"""
        st.success(f"✅ {message}")
        if details:
            with st.expander("ℹ️ Details"):
                st.markdown(details)
    
    @staticmethod
    def show_info(message: str, details: Optional[str] = None) -> None:
        """Show info message (for consistency)"""
        st.info(f"💡 {message}")
        if details:
            with st.expander("ℹ️ More info"):
                st.markdown(details)


# Convenience functions for common patterns
def safe_operation(func, *args, error_handler=None, context="operation", **kwargs):
    """
    Wrap any operation with automatic error handling
    
    Usage:
        result = safe_operation(
            parse_document, 
            uploaded_file,
            error_handler=ErrorHandler.handle_file_error,
            context="document parsing"
        )
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if error_handler:
            error_handler(e)
        else:
            ErrorHandler.handle_generic_error(e, context=context)
        return None


# Example usage in pages:
"""
# In chat page:
try:
    response = call_llm(prompt)
except Exception as e:
    ErrorHandler.handle_llm_error(e, context="chat response")

# In analysis page:
try:
    parsed = parse_document(file)
except Exception as e:
    ErrorHandler.handle_file_error(e, filename=file.name)

# In knowledge base:
try:
    rag_handler.search(query)
except Exception as e:
    ErrorHandler.handle_rag_error(e)

# Or use safe_operation wrapper:
result = safe_operation(
    rag_handler.add_document,
    name="doc.pdf",
    content=content,
    error_handler=ErrorHandler.handle_rag_error,
    context="adding document to knowledge base"
)
"""
