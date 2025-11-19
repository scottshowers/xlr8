import streamlit as st
from utils.rag_handler import RAGHandler
from utils.document_processor import DocumentProcessor, render_upload_interface
from utils.pdf_parsers import extract_register_adaptive, extract_payroll_register
from utils.column_editor import render_column_editor
from pathlib import Path
import os
import logging

# ADDED: Import intelligent parser UI
from utils.parsers.intelligent_parser_ui import render_intelligent_parser_ui

logger = logging.getLogger(__name__)


def render_knowledge_page():
    """Knowledge page for managing HCMPACT LLM documents."""
    
    st.title("📚 HCMPACT LLM Base")
    st.markdown("Manage your UKG Pro and WFM implementation documents")
    
    # Initialize handlers
    rag = RAGHandler()
    
    # MODIFIED: Changed from 4 tabs to 5 tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📤 Upload", 
        "📊 Status", 
        "🗑️ Manage", 
        "📋 Parse Registers",
        "🧠 Intelligent Parser"  # NEW TAB
    ])
    
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
        st.info("💾 **Persistent Storage:** /data/chromadb")
        st.markdown("""
        - ✅ Data survives Railway deployments
        - ✅ No need to re-upload after redeploy
        - ✅ Backed up by Railway volume
        """)
    
    # TAB 4: PARSE REGISTERS
    with tab4:
        st.subheader("📋 Parse Payroll Registers to Excel")
        
        st.markdown("""
        Extract tables from payroll register PDFs into Excel format for structured analysis.
        Works with registers from any HCM/Payroll vendor.
        """)
        
        # Get list of uploaded PDFs
        upload_dir = "/data/uploads"
        parsed_dir = "/data/parsed_registers"
        
        # Ensure directories exist
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(parsed_dir, exist_ok=True)
        
        if os.path.exists(upload_dir):
            pdf_files = [f for f in os.listdir(upload_dir) if f.lower().endswith('.pdf')]
            
            if pdf_files:
                st.markdown("### Select PDF to Parse")
                
                selected_pdf = st.selectbox(
                    "Choose a PDF register:",
                    pdf_files,
                    help="Select which PDF to extract tables from"
                )
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    if st.button("📊 Parse to Excel", type="primary", key="parse_register"):
                        pdf_path = os.path.join(upload_dir, selected_pdf)
                        
                        with st.spinner(f"Extracting tables from {selected_pdf}..."):
                            try:
                                # Try payroll-specific parser first
                                st.info("📄 Trying payroll register parser...")
                                result = extract_payroll_register(
                                    pdf_path=pdf_path,
                                    output_dir=parsed_dir
                                )
                                
                                # If payroll parser fails, fall back to general parser
                                if not result['success']:
                                    st.info("📄 Trying general table parser...")
                                    result = extract_register_adaptive(
                                        pdf_path=pdf_path,
                                        output_dir=parsed_dir
                                    )
                                
                                if result['success']:
                                    excel_path = result['excel_path']
                                    table_count = result['table_count']
                                    
                                    # Get strategy and accuracy
                                    metadata = result.get('metadata', {})
                                    strategy_used = metadata.get('parsing_strategy', result.get('strategy_used', 'Unknown'))
                                    accuracy = metadata.get('accuracy', None)
                                    
                                    st.success(f"✅ Successfully extracted {table_count} table(s)!")
                                    
                                    # Show parsing info
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.info(f"🔧 **Strategy:** {strategy_used}")
                                    with col2:
                                        if accuracy is not None:
                                            st.metric("Accuracy", f"{accuracy:.1f}%")
                                    
                                    # Show metadata if available
                                    if 'columns_found' in metadata:
                                        with st.expander("📊 Columns Discovered"):
                                            for tab, cols in metadata['columns_found'].items():
                                                if cols:
                                                    st.markdown(f"**{tab}:** {', '.join(cols)}")
                                    
                                    # Show table details
                                    with st.expander("📋 Table Details", expanded=True):
                                        for info in result['table_info']:
                                            sheet_name = info.get('sheet_name', f"Table {info.get('table_number', '?')}")
                                            # Handle None values in headers
                                            headers = [str(h) if h is not None else 'Unnamed' for h in info.get('headers', [])]
                                            st.markdown(f"""
**{sheet_name}:**
- **Rows:** {info['rows']:,}
- **Columns:** {info['columns']}
- **Headers:** {', '.join(headers[:5])}{'...' if len(headers) > 5 else ''}
""")
                                    
                                    # Download button
                                    st.markdown("### 📥 Download Excel")
                                    with open(excel_path, "rb") as f:
                                        st.download_button(
                                            label=f"💾 Download {Path(excel_path).name}",
                                            data=f.read(),
                                            file_name=Path(excel_path).name,
                                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                            key="download_parsed_register"
                                        )
                                    
                                    st.info(f"💾 Excel file saved to: `{parsed_dir}/{Path(excel_path).name}`")
                                    
                                    # Column Editor
                                    if st.checkbox("✏️ Edit Column Names", key="edit_columns_checkbox"):
                                        render_column_editor(excel_path, result['table_info'])
                                
                                else:
                                    st.error(f"❌ Extraction failed: {result.get('error', 'Unknown error')}")
                                    st.info("**Possible issues:**\n- PDF doesn't contain tables\n- PDF is scanned image (not text)\n- Complex table formatting")
                            
                            except Exception as e:
                                st.error(f"❌ Error parsing register: {e}")
                                logger.error(f"Register parsing error: {e}", exc_info=True)
                
                # Show previously parsed files
                st.markdown("---")
                st.markdown("### 📂 Previously Parsed Registers")
                
                if os.path.exists(parsed_dir):
                    excel_files = [f for f in os.listdir(parsed_dir) if f.lower().endswith('.xlsx')]
                    
                    if excel_files:
                        st.success(f"Found {len(excel_files)} parsed register(s)")
                        
                        for excel_file in sorted(excel_files):
                            excel_path = os.path.join(parsed_dir, excel_file)
                            file_size = os.path.getsize(excel_path) / 1024  # KB
                            
                            col1, col2, col3 = st.columns([3, 1, 1])
                            
                            with col1:
                                st.markdown(f"📊 **{excel_file}**")
                                st.caption(f"Size: {file_size:.1f} KB")
                            
                            with col2:
                                with open(excel_path, "rb") as f:
                                    st.download_button(
                                        label="📥",
                                        data=f.read(),
                                        file_name=excel_file,
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        key=f"dl_{excel_file}"
                                    )
                            
                            with col3:
                                if st.button("🗑️", key=f"del_{excel_file}"):
                                    try:
                                        os.remove(excel_path)
                                        st.success("Deleted")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Delete failed: {e}")
                    else:
                        st.info("No parsed registers yet. Parse a PDF above to get started.")
            else:
                st.info("📤 No PDFs uploaded yet. Upload documents in the **Upload** tab first.")
        
        # Info section
        st.markdown("---")
        st.markdown("### ℹ️ About Register Parsing")
        
        with st.expander("How it works"):
            st.markdown("""
**Parsing Process:**
1. Select a payroll register PDF from uploaded documents
2. Click "Parse to Excel" 
3. System extracts all tables from the PDF
4. Tables are converted to Excel format with original structure preserved
5. Download Excel immediately or access later

**Supported Formats:**
- ✅ Tabular payroll registers (any vendor)
- ✅ Benefit enrollment reports
- ✅ Employee data exports
- ✅ Any PDF with structured tables

**Not Supported:**
- ❌ Scanned PDFs (image-only)
- ❌ PDFs without clear table structure
- ❌ Highly complex formatting

**Storage:**
- Parsed Excel files are saved to `/data/parsed_registers/`
- Files persist across deployments
- Available for download anytime
""")
    
    # TAB 5: INTELLIGENT PARSER (NEW!)
    with tab5:
        render_intelligent_parser_ui(
            upload_dir="/data/uploads",
            output_dir="/data/parsed_registers"
        )


if __name__ == "__main__":
    render_knowledge_page()
