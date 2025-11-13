"""
XLR8 by HCMPACT - UKG Pro/WFM Implementation Accelerator
Main Application with Advanced PDF Parsing
"""

import streamlit as st
import json
import io
from datetime import datetime
import pandas as pd
from utils.pdf_parser import AdvancedPDFParser, create_mapping_editor_html

# Page configuration
st.set_page_config(
    page_title="XLR8 by HCMPACT - TEST",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'current_project' not in st.session_state:
    st.session_state.current_project = None
if 'pdf_parser' not in st.session_state:
    st.session_state.pdf_parser = AdvancedPDFParser()
if 'parsed_results' not in st.session_state:
    st.session_state.parsed_results = None
if 'mapping_config' not in st.session_state:
    st.session_state.mapping_config = None

# Custom CSS - Darker Muted Blue Theme
st.markdown("""
<style>
    /* Modern styling with darker muted blues */
    .main {
        padding: 2rem;
        background-color: #e8edf2;
    }
    
    .stButton>button {
        width: 100%;
        border-radius: 6px;
        height: 3rem;
        font-weight: 600;
        transition: all 0.3s;
        background-color: #6d8aa0;
        color: white;
        border: none;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(109, 138, 160, 0.4);
        background-color: #7d96a8;
    }
    
    .success-box {
        background-color: rgba(109, 138, 160, 0.15);
        border-left: 4px solid #6d8aa0;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
        color: #1a2332;
    }
    
    .info-box {
        background-color: rgba(125, 150, 168, 0.15);
        border-left: 4px solid #7d96a8;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
        color: #1a2332;
    }
    
    .warning-box {
        background-color: rgba(140, 166, 190, 0.15);
        border-left: 4px solid #8ca6be;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
        color: #1a2332;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: white;
        border-right: 1px solid #e1e8ed;
    }
    
    section[data-testid="stSidebar"] > div {
        padding-top: 2rem;
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        border-bottom: 2px solid #e1e8ed;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-bottom: 3px solid transparent;
        color: #6c757d;
        font-weight: 600;
        padding: 0.75rem 1.5rem;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(140, 166, 190, 0.05);
        color: #8ca6be;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: transparent;
        border-bottom-color: #8ca6be;
        color: #8ca6be;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #8ca6be;
    }
    
    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Card-like containers */
    .element-container {
        background: white;
        border-radius: 8px;
        padding: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    # Logo Section - Option 4: Minimal Badge with Lightning Bolt
    st.markdown("""
    <div style='text-align: center; padding-bottom: 2rem; border-bottom: 2px solid #d1dce5; margin-bottom: 2rem;'>
        <div style='width: 80px; height: 80px; margin: 0 auto 1rem; background: white; border: 4px solid #6d8aa0; border-radius: 16px; display: flex; align-items: center; justify-content: center; color: #6d8aa0; font-size: 2rem; font-weight: 700; box-shadow: 0 6px 20px rgba(109, 138, 160, 0.25);'>⚡</div>
        <div style='font-size: 1.5rem; font-weight: 700; color: #6d8aa0; margin-bottom: 0.25rem;'>XLR8</div>
        <div style='font-size: 0.85rem; color: #7d96a8; font-weight: 500;'>by HCMPACT</div>
        <div style='display: inline-block; background: rgba(109, 138, 160, 0.15); color: #6d8aa0; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; margin-top: 0.5rem;'>v2.0</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Project selector
    st.markdown("### 📁 Current Project")
    project_name = st.text_input(
        "Project Name",
        value=st.session_state.current_project or "Demo Project",
        key="project_input",
        label_visibility="collapsed"
    )
    
    if st.button("📌 Set Active Project", use_container_width=True):
        st.session_state.current_project = project_name
        st.success(f"✅ Active: {project_name}")
    
    st.markdown("---")
    
    # Foundation Intelligence for Local LLM
    with st.expander("🧠 Foundation Intelligence", expanded=False):
        st.markdown("**Local LLM Knowledge Base**")
        st.markdown("""
        <div style='font-size: 0.85rem; color: #6c757d; margin-bottom: 1rem;'>
        Upload industry knowledge, best practices, and templates that apply across all projects. This content trains your local LLM for UKG implementations.
        </div>
        """, unsafe_allow_html=True)
        
        foundation_files = st.file_uploader(
            "Upload Foundation Files",
            type=['pdf', 'docx', 'txt', 'md', 'xlsx', 'csv'],
            accept_multiple_files=True,
            key="foundation_uploader",
            help="Documents for local LLM: UKG guides, best practices, implementation templates, industry standards"
        )
        
        if foundation_files:
            st.success(f"✅ {len(foundation_files)} file(s) loaded")
            for file in foundation_files:
                st.markdown(f"<div style='font-size: 0.8rem; padding: 0.25rem 0;'>📄 {file.name}</div>", unsafe_allow_html=True)
        else:
            st.info("No foundation files uploaded yet")
        
        st.markdown("""
        <div style='font-size: 0.75rem; color: #6c757d; margin-top: 1rem; line-height: 1.4;'>
        <strong>Examples:</strong><br>
        • UKG Pro configuration guides<br>
        • WFM best practices<br>
        • Pay code templates<br>
        • Accrual policy standards<br>
        • Industry regulations
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Status Section
    st.markdown("### Status")
    st.markdown("""
    <div style='display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0;'>
        <div style='width: 20px; height: 20px; background: #8ca6be; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: white; font-size: 0.75rem;'>✓</div>
        <span style='color: #2c3e50; font-size: 0.9rem;'>Encryption Active</span>
    </div>
    <div style='display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0;'>
        <div style='width: 20px; height: 20px; background: #8ca6be; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: white; font-size: 0.75rem;'>✓</div>
        <span style='color: #2c3e50; font-size: 0.9rem;'>PII Protection On</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Security Expandable
    with st.expander("🔐 Security Details", expanded=False):
        st.markdown("**Active Features**")
        st.markdown("""
        <div style='font-size: 0.85rem; line-height: 1.8;'>
        <div>✓ AES-256 Encryption</div>
        <div>✓ PII Auto-Detection</div>
        <div>✓ Data Anonymization</div>
        <div>✓ Audit Logging</div>
        <div>✓ Secure Storage</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("**Compliance**")
        st.markdown("""
        <div style='font-size: 0.85rem; line-height: 1.8;'>
        <div>✓ GDPR Compliant</div>
        <div>✓ HIPAA Ready</div>
        <div>✓ SOC 2 Type II</div>
        <div>✓ ISO 27001</div>
        </div>
        """, unsafe_allow_html=True)

# Main content
# Minimal header with TEST environment indicator
st.markdown("""
<div style='background: linear-gradient(135deg, #6d8aa0 0%, #7d96a8 100%); padding: 0.75rem 2rem; margin: -2rem -2rem 2rem -2rem; border-bottom: 3px solid #5a7589; box-shadow: 0 2px 8px rgba(0,0,0,0.1);'>
    <div style='display: flex; align-items: center; justify-content: space-between;'>
        <div style='display: flex; align-items: center; gap: 1rem;'>
            <div style='font-size: 1.5rem;'>⚡</div>
            <div>
                <div style='font-size: 1.2rem; font-weight: 700; color: white; letter-spacing: 0.5px;'>XLR8 by HCMPACT</div>
                <div style='font-size: 0.7rem; color: rgba(255,255,255,0.8);'>UKG Implementation Accelerator</div>
            </div>
        </div>
        <div style='background: #ff6b6b; color: white; padding: 0.4rem 1rem; border-radius: 6px; font-weight: 700; font-size: 0.85rem; letter-spacing: 0.5px; box-shadow: 0 2px 6px rgba(255,107,107,0.3);'>
            ⚠️ TEST ENVIRONMENT
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "🏠 Home",
    "📄 Advanced PDF Parser",
    "📊 Data Analysis",
    "⚙️ Admin Panel"
])

with tab1:
    st.markdown("## Welcome to XLR8")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class='info-box'>
            <h4>🚀 Quick Start</h4>
            <p>1. Create or select a project</p>
            <p>2. Upload your PDF pay registers</p>
            <p>3. Configure custom mappings</p>
            <p>4. Export to Excel for UKG import</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class='success-box'>
            <h4>✨ Key Features</h4>
            <p>• Advanced PDF parsing</p>
            <p>• Custom field mappings</p>
            <p>• Offline mapping editor</p>
            <p>• Excel export</p>
        </div>
        """, unsafe_allow_html=True)

with tab2:
    st.markdown("## 📄 Advanced PDF Parser")
    st.markdown("Parse complex pay registers with custom field mappings")
    
    # Step 1: Upload PDF
    st.markdown("### Step 1: Upload PDF")
    uploaded_file = st.file_uploader(
        "Choose a PDF file (Pay Register, Payroll Report, etc.)",
        type=['pdf'],
        key="pdf_uploader"
    )
    
    if uploaded_file:
        st.success(f"✅ Loaded: {uploaded_file.name}")
        
        # Step 2: Parsing Options
        st.markdown("### Step 2: Parsing Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            auto_detect = st.checkbox(
                "🎯 Auto-detect pay register fields",
                value=True,
                help="Automatically identify common payroll fields"
            )
        
        with col2:
            extract_all = st.checkbox(
                "📑 Extract all tables",
                value=True,
                help="Extract all tables or stop after first"
            )
        
        # Step 3: Custom Mapping (Optional)
        st.markdown("### Step 3: Custom Mapping (Optional)")
        
        use_custom_mapping = st.checkbox(
            "📝 Use custom field mapping",
            help="Upload a previously configured mapping JSON file"
        )
        
        custom_mapping_file = None
        custom_mapping = None
        
        if use_custom_mapping:
            custom_mapping_file = st.file_uploader(
                "Upload Mapping Configuration (JSON)",
                type=['json'],
                key="mapping_uploader"
            )
            
            if custom_mapping_file:
                try:
                    mapping_data = json.loads(custom_mapping_file.read())
                    custom_mapping = mapping_data.get('field_mappings', {})
                    st.success(f"✅ Loaded mapping with {len(custom_mapping)} field definitions")
                except Exception as e:
                    st.error(f"Error loading mapping file: {str(e)}")
        
        # Step 4: Parse Button
        st.markdown("### Step 4: Parse PDF")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🚀 Parse PDF", use_container_width=True):
                with st.spinner("Parsing PDF... This may take a moment for large files."):
                    try:
                        pdf_content = uploaded_file.getvalue()
                        
                        # Parse PDF
                        result = st.session_state.pdf_parser.parse_pdf(
                            pdf_content=pdf_content,
                            filename=uploaded_file.name,
                            custom_mapping=custom_mapping if use_custom_mapping else None,
                            extract_all_tables=extract_all
                        )
                        
                        st.session_state.parsed_results = result
                        
                        if result['success']:
                            st.success("✅ PDF parsed successfully!")
                        else:
                            st.error(f"❌ Error: {result['error']}")
                    
                    except Exception as e:
                        st.error(f"Error parsing PDF: {str(e)}")
        
        with col2:
            if st.button("🗺️ Generate Mapping Template", use_container_width=True):
                with st.spinner("Analyzing PDF structure..."):
                    try:
                        pdf_content = uploaded_file.getvalue()
                        
                        # Generate mapping config
                        mapping_result = st.session_state.pdf_parser.generate_mapping_config(
                            pdf_content=pdf_content,
                            filename=uploaded_file.name
                        )
                        
                        if mapping_result['success']:
                            st.session_state.mapping_config = mapping_result['config']
                            st.success("✅ Mapping template generated!")
                        else:
                            st.error(f"Error: {mapping_result['error']}")
                    
                    except Exception as e:
                        st.error(f"Error generating template: {str(e)}")
        
        # Display Results
        if st.session_state.parsed_results and st.session_state.parsed_results['success']:
            st.markdown("---")
            st.markdown("### 📊 Parsing Results")
            
            result = st.session_state.parsed_results
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Pages", result['total_pages'])
            with col2:
                st.metric("Tables Found", result['tables_found'])
            with col3:
                st.metric("Total Records", result['total_records'])
            with col4:
                pay_register_status = "✅ Yes" if result['is_pay_register'] else "❌ No"
                st.metric("Pay Register", pay_register_status)
            
            # Detected Fields
            if result['detected_fields']:
                st.markdown("#### 🎯 Detected Fields")
                for field_name, source_cols in result['detected_fields'].items():
                    st.markdown(f"**{field_name}**: {', '.join(source_cols)}")
            
            # Show extracted tables
            if result['dataframes']:
                st.markdown("#### 📋 Extracted Data")
                
                for i, df in enumerate(result['dataframes'], 1):
                    with st.expander(f"Table {i} ({len(df)} rows, {len(df.columns)} columns)"):
                        st.dataframe(df, use_container_width=True)
            
            # Export Options
            st.markdown("---")
            st.markdown("### 💾 Export Options")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📥 Download as Excel", use_container_width=True):
                    try:
                        # Validate we have data to export
                        if not result['dataframes']:
                            st.error("❌ No data to export. The PDF may not contain any tables.")
                        elif all(df.empty for df in result['dataframes']):
                            st.error("❌ All extracted tables are empty. Try adjusting parsing settings.")
                        else:
                            # Filter out empty dataframes
                            non_empty_dfs = [df for df in result['dataframes'] if not df.empty]
                            
                            if not non_empty_dfs:
                                st.error("❌ No data found in extracted tables.")
                            else:
                                excel_data = st.session_state.pdf_parser.export_to_excel(
                                    dataframes=non_empty_dfs,
                                    filename=uploaded_file.name,
                                    include_summary=True
                                )
                                
                                st.download_button(
                                    label="⬇️ Download Excel File",
                                    data=excel_data,
                                    file_name=f"parsed_{uploaded_file.name.replace('.pdf', '.xlsx')}",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True
                                )
                                st.success(f"✅ Excel file ready! ({len(non_empty_dfs)} table(s) with data)")
                    except Exception as e:
                        st.error(f"❌ Error creating Excel: {str(e)}")
            
            with col2:
                if st.button("📥 Download as CSV", use_container_width=True):
                    try:
                        if not result['dataframes']:
                            st.error("❌ No data to export. The PDF may not contain any tables.")
                        else:
                            # Filter out empty dataframes
                            non_empty_dfs = [df for df in result['dataframes'] if not df.empty]
                            
                            if not non_empty_dfs:
                                st.error("❌ No data found in extracted tables.")
                            else:
                                # Combine all non-empty dataframes
                                combined_df = pd.concat(non_empty_dfs, ignore_index=True)
                                csv_data = combined_df.to_csv(index=False)
                                
                                st.download_button(
                                    label="⬇️ Download CSV File",
                                    data=csv_data,
                                    file_name=f"parsed_{uploaded_file.name.replace('.pdf', '.csv')}",
                                    mime="text/csv",
                                    use_container_width=True
                                )
                                st.success(f"✅ CSV file ready! ({len(combined_df)} rows)")
                    except Exception as e:
                        st.error(f"❌ Error creating CSV: {str(e)}")
        
        # Download Mapping Configuration
        if st.session_state.mapping_config:
            st.markdown("---")
            st.markdown("### 🗺️ Mapping Configuration")
            
            st.markdown("""
            <div class='info-box'>
                <h4>How to use the mapping editor:</h4>
                <p>1. Download the HTML editor and JSON config below</p>
                <p>2. Open the HTML file in your browser</p>
                <p>3. Edit the field mappings as needed</p>
                <p>4. Click "Download Configuration" in the editor</p>
                <p>5. Upload the modified JSON file here for future parses</p>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Download HTML Editor
                html_editor = create_mapping_editor_html(st.session_state.mapping_config)
                st.download_button(
                    label="📝 Download Mapping Editor (HTML)",
                    data=html_editor,
                    file_name=f"mapping_editor_{uploaded_file.name.replace('.pdf', '.html')}",
                    mime="text/html",
                    use_container_width=True
                )
            
            with col2:
                # Download JSON Config
                json_config = json.dumps(st.session_state.mapping_config, indent=2)
                st.download_button(
                    label="📄 Download Config (JSON)",
                    data=json_config,
                    file_name=f"mapping_{uploaded_file.name.replace('.pdf', '.json')}",
                    mime="application/json",
                    use_container_width=True
                )
    
    else:
        st.info("👆 Upload a PDF file to get started")

with tab3:
    st.markdown("## 📊 Data Analysis")
    st.info("Upload additional data sources (Excel, CSV) for cross-reference analysis")
    
    # File uploader for other formats
    data_files = st.file_uploader(
        "Upload Data Files",
        type=['xlsx', 'xls', 'csv'],
        accept_multiple_files=True
    )
    
    if data_files:
        st.success(f"✅ Loaded {len(data_files)} file(s)")
        
        for file in data_files:
            with st.expander(f"📁 {file.name}"):
                try:
                    if file.name.endswith(('.xlsx', '.xls')):
                        df = pd.read_excel(file)
                    else:
                        df = pd.read_csv(file)
                    
                    st.dataframe(df, use_container_width=True)
                    st.markdown(f"**Rows:** {len(df)} | **Columns:** {len(df.columns)}")
                except Exception as e:
                    st.error(f"Error reading file: {str(e)}")

with tab4:
    st.markdown("## ⚙️ Admin Panel")
    st.markdown("""
    <div class='warning-box'>
        <strong>🔧 Development & Testing Tools</strong><br>
        Make changes, test features, and chat with Claude - all without redeploying!
    </div>
    """, unsafe_allow_html=True)
    
    # Create three columns for different admin sections
    admin_col1, admin_col2 = st.columns([2, 1])
    
    with admin_col1:
        # Direct Communication with Claude
        st.markdown("### 💬 Communicate with Claude")
        st.markdown("""
        <div class='info-box' style='font-size: 0.9rem;'>
        <strong>Important:</strong> This panel is for logging issues and requests. Your messages are recorded below 
        so you can copy them to share with Claude in your main conversation for immediate fixes.
        </div>
        """, unsafe_allow_html=True)
        
        # Initialize messages list in session state
        if 'admin_messages' not in st.session_state:
            st.session_state.admin_messages = []
        
        # Message input
        user_message = st.text_area(
            "Describe the issue or request:",
            key="admin_message_input",
            height=120,
            placeholder="Example: 'The PDF parser isn't detecting tables correctly' or 'Can you make the buttons bigger?' or 'Parser not creating any output'"
        )
        
        col_log, col_copy, col_clear = st.columns([2, 2, 1])
        with col_log:
            if st.button("📝 Log Message", use_container_width=True):
                if user_message:
                    # Add message with timestamp
                    st.session_state.admin_messages.append({
                        'timestamp': datetime.now().strftime("%H:%M:%S"),
                        'message': user_message
                    })
                    st.success("✅ Message logged!")
                else:
                    st.warning("Please enter a message")
        
        with col_copy:
            if st.button("📋 Copy All Messages", use_container_width=True):
                if st.session_state.admin_messages:
                    all_messages = "\n\n---\n\n".join([
                        f"[{msg['timestamp']}] {msg['message']}" 
                        for msg in st.session_state.admin_messages
                    ])
                    st.code(all_messages, language=None)
                    st.info("👆 Copy the text above and paste it into your Claude conversation")
                else:
                    st.warning("No messages logged yet")
        
        with col_clear:
            if st.button("🗑️", use_container_width=True):
                st.session_state.admin_messages = []
                st.success("Cleared!")
        
        # Display logged messages
        if st.session_state.admin_messages:
            st.markdown("---")
            st.markdown("**📋 Logged Messages:**")
            
            for i, msg in enumerate(st.session_state.admin_messages):
                st.markdown(f"""
                <div style='background: #e8edf2; color: #1a2332; padding: 0.75rem; border-radius: 6px; margin: 0.5rem 0; border-left: 4px solid #6d8aa0;'>
                    <small style='color: #6c757d;'>{msg['timestamp']}</small><br>
                    {msg['message']}
                </div>
                """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Quick Help
        st.markdown("### 📖 How This Works")
        st.markdown("""
        <div style='font-size: 0.85rem; line-height: 1.6; color: #6c757d;'>
        1. <strong>Describe your issue</strong> above<br>
        2. <strong>Click "Log Message"</strong> to save it<br>
        3. <strong>Click "Copy All Messages"</strong> when ready<br>
        4. <strong>Go to your Claude chat</strong> (where you're talking to me)<br>
        5. <strong>Paste the messages</strong> and I'll fix everything immediately!<br>
        <br>
        <strong>Why this way?</strong> I can't directly access this panel, but I can read your messages 
        in our main conversation and provide instant fixes!
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Quick Actions
        st.markdown("### ⚡ Quick Actions")
        
        action_col1, action_col2, action_col3 = st.columns(3)
        
        with action_col1:
            if st.button("🔄 Restart App", use_container_width=True):
                st.info("To restart: Go to Railway → Click '...' → Restart")
        
        with action_col2:
            if st.button("📋 View Logs", use_container_width=True):
                st.info("Logs: Railway Dashboard → Deployments → View Logs")
        
        with action_col3:
            if st.button("🔍 Test Parse", use_container_width=True):
                st.info("Upload a PDF in the PDF Parser tab to test")
    
    with admin_col2:
        # Color Tester
        st.markdown("### 🎨 Color Tester")
        st.markdown("""
        <div style='font-size: 0.85rem; color: #6c757d; margin-bottom: 1rem;'>
        Test colors before applying them to the app
        </div>
        """, unsafe_allow_html=True)
        
        test_primary = st.color_picker("Primary Color", "#6d8aa0")
        test_bg = st.color_picker("Background", "#e8edf2")
        test_text = st.color_picker("Text Color", "#1a2332")
        
        # Preview
        st.markdown(f"""
        <div style='background: {test_bg}; padding: 1rem; border-radius: 8px; margin-top: 1rem;'>
            <button style='background: {test_primary}; color: white; padding: 0.5rem 1rem; border: none; border-radius: 6px; width: 100%; font-weight: 600;'>
                Sample Button
            </button>
            <p style='color: {test_text}; margin-top: 0.5rem;'>Sample text with your colors</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("📝 Copy Color Values", use_container_width=True):
            st.code(f"""
primaryColor="{test_primary}"
backgroundColor="{test_bg}"
textColor="{test_text}"
            """)
            st.success("Copy these to .streamlit/config.toml")
        
        st.markdown("---")
        
        # Current Config Viewer
        st.markdown("### 📄 Current Config")
        
        config_display = f"""
**Theme Colors:**
- Primary: #6d8aa0
- Background: #e8edf2
- Text: #1a2332

**Environment:** TEST
**Version:** v2.0
**Upload Limit:** 200MB
        """
        
        st.markdown(config_display)
        
        st.markdown("---")
        
        # System Info
        st.markdown("### 📊 System Info")
        
        import platform
        import sys
        
        system_info = f"""
**Python:** {sys.version.split()[0]}
**Platform:** {platform.system()}
**Streamlit:** {st.__version__}

**Session State:**
- Active Project: {st.session_state.current_project or 'None'}
- Logged Messages: {len(st.session_state.get('admin_messages', []))} messages
        """
        
        st.markdown(system_info)
    
    st.markdown("---")
    
    # Documentation Links
    st.markdown("### 📚 Quick Links")
    
    link_col1, link_col2, link_col3 = st.columns(3)
    
    with link_col1:
        st.markdown("""
        **GitHub**
        - Update files here
        - Railway auto-deploys
        """)
    
    with link_col2:
        st.markdown("""
        **Railway**
        - View logs
        - Restart app
        - Check deployments
        """)
    
    with link_col3:
        st.markdown("""
        **This Chat**
        - Report bugs above
        - Request features
        - Get help
        """)
    
    # Tips
    st.markdown("---")
    st.markdown("""
    <div class='info-box'>
    <strong>💡 Pro Tips:</strong><br>
    <ul style='margin-left: 1.5rem; line-height: 1.8;'>
        <li><strong>Test locally first:</strong> Run on your PC before deploying</li>
        <li><strong>Check logs:</strong> Railway logs show all errors</li>
        <li><strong>Small changes:</strong> Test colors here before changing config</li>
        <li><strong>Big changes:</strong> Chat with Claude in main conversation for new features</li>
        <li><strong>Emergency:</strong> Railway → Rollback to previous deployment</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6c757d; padding: 1rem;">
    <small>⚡ XLR8 by HCMPACT v2.0 | Advanced PDF Parser | All data remains secure and private</small>
</div>
""", unsafe_allow_html=True)
