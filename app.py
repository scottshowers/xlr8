"""
XLR8 by HCMPACT - UKG Implementation Accelerator
Integrated Payroll Template System for Multi-Vendor PDF Processing
"""

import streamlit as st
import json
import io
from datetime import datetime
from pathlib import Path
import pandas as pd

# PDF parsing imports
try:
    from pdf2image import convert_from_bytes
    from PIL import Image, ImageDraw, ImageFont
    import pytesseract
    PDF_FEATURES_AVAILABLE = True
except ImportError:
    PDF_FEATURES_AVAILABLE = False

# Page configuration
st.set_page_config(
    page_title="XLR8 by HCMPACT",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'current_project' not in st.session_state:
    st.session_state.current_project = None
if 'projects' not in st.session_state:
    st.session_state.projects = {}
if 'templates' not in st.session_state:
    st.session_state.templates = {}
if 'pdf_images' not in st.session_state:
    st.session_state.pdf_images = []
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = None
if 'temp_columns' not in st.session_state:
    st.session_state.temp_columns = []

# Template directory
TEMPLATE_DIR = Path("templates")
TEMPLATE_DIR.mkdir(exist_ok=True)

def load_templates():
    """Load all saved templates from disk"""
    templates = {}
    for file in TEMPLATE_DIR.glob("*.json"):
        try:
            with open(file, 'r') as f:
                templates[file.stem] = json.load(f)
        except:
            pass
    return templates

def save_template(name, template_data):
    """Save template to disk"""
    filepath = TEMPLATE_DIR / f"{name}.json"
    with open(filepath, 'w') as f:
        json.dump(template_data, f, indent=2)

def extract_text_from_region(image, x1, y1, x2, y2):
    """Extract text from region using OCR"""
    if not PDF_FEATURES_AVAILABLE:
        return "PDF features not available"
    cropped = image.crop((x1, y1, x2, y2))
    text = pytesseract.image_to_string(cropped, config='--psm 6')
    return text.strip()

def apply_template(image, template):
    """Apply template to extract data"""
    extracted = {}
    for column in template['columns']:
        x1, y1, x2, y2 = column['x1'], column['y1'], column['x2'], column['y2']
        text = extract_text_from_region(image, x1, y1, x2, y2)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        category = column['category']
        if category not in extracted:
            extracted[category] = []
        extracted[category].extend(lines)
    return extracted

# Load templates
st.session_state.templates = load_templates()

# Custom CSS
st.markdown("""
<style>
    .main {
        padding: 2rem;
        background-color: #e8edf2;
    }
    .stButton>button {
        width: 100%;
        border-radius: 6px;
        height: 3rem;
        font-weight: 600;
        background-color: #6d8aa0;
        color: white;
        border: none;
        transition: all 0.3s;
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
    }
    .info-box {
        background-color: rgba(125, 150, 168, 0.15);
        border-left: 4px solid #7d96a8;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("""
    <div style='text-align: center; padding-bottom: 2rem; border-bottom: 2px solid #d1dce5; margin-bottom: 2rem;'>
        <div style='width: 80px; height: 80px; margin: 0 auto 1rem; background: white; border: 4px solid #6d8aa0; border-radius: 16px; display: flex; align-items: center; justify-content: center; color: #6d8aa0; font-size: 2rem; font-weight: 700; box-shadow: 0 6px 20px rgba(109, 138, 160, 0.25);'>⚡</div>
        <div style='font-size: 1.5rem; font-weight: 700; color: #6d8aa0;'>XLR8</div>
        <div style='font-size: 0.85rem; color: #7d96a8; font-weight: 500;'>by HCMPACT</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 📁 Projects")
    if st.session_state.projects:
        project_names = list(st.session_state.projects.keys())
        selected = st.selectbox("Select Project", [""] + project_names)
        if selected:
            st.session_state.current_project = selected
            st.markdown(f"<div class='info-box' style='font-size: 0.85rem;'><strong>{selected}</strong></div>", unsafe_allow_html=True)
    else:
        st.info("No projects yet")

# Header
st.markdown("""
<div style='background: linear-gradient(135deg, #6d8aa0 0%, #7d96a8 100%); padding: 0.75rem 2rem; margin: -2rem -2rem 2rem -2rem;'>
    <div style='display: flex; align-items: center; gap: 1rem;'>
        <div style='font-size: 1.5rem;'>⚡</div>
        <div>
            <div style='font-size: 1.2rem; font-weight: 700; color: white;'>XLR8 by HCMPACT</div>
            <div style='font-size: 0.7rem; color: rgba(255,255,255,0.8);'>UKG Implementation Accelerator</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Main tabs
tab1, tab2, tab3 = st.tabs(["🏠 Home", "🎯 Template System", "⚙️ Admin"])

# TAB 1: HOME
with tab1:
    st.markdown("## 🏠 Welcome")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        <div class='info-box'>
            <h4>🚀 Quick Start</h4>
            <p>1. Create a project below</p>
            <p>2. Go to Template System</p>
            <p>3. Create vendor templates</p>
            <p>4. Process PDFs</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class='success-box'>
            <h4>✨ Features</h4>
            <p>• Multi-vendor support</p>
            <p>• Template-based parsing</p>
            <p>• UKG-ready Excel</p>
            <p>• 100% local processing</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("## 📁 Projects")
    
    with st.expander("➕ Create New Project", expanded=not bool(st.session_state.projects)):
        with st.form("create_project"):
            col1, col2 = st.columns(2)
            with col1:
                project_name = st.text_input("Project Name *", placeholder="Acme Corp - UKG Pro")
                customer_id = st.text_input("Customer ID", placeholder="ACME001")
            with col2:
                impl_type = st.multiselect("Type *", ["UKG Pro", "UKG WFM"])
                go_live = st.date_input("Go-Live Date")
            
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("🚀 Create", type="primary")
            
            if submitted:
                if not project_name or not impl_type:
                    st.error("❌ Name and type required")
                elif project_name in st.session_state.projects:
                    st.error("❌ Project exists")
                else:
                    st.session_state.projects[project_name] = {
                        'customer_id': customer_id,
                        'implementation_type': ', '.join(impl_type),
                        'go_live_date': str(go_live),
                        'created_date': datetime.now().strftime('%Y-%m-%d'),
                        'notes': notes
                    }
                    st.session_state.current_project = project_name
                    st.success(f"✅ Created {project_name}")
                    st.balloons()
                    st.rerun()
    
    if st.session_state.projects:
        st.markdown("### 📊 Active Projects")
        for proj_name, proj_data in st.session_state.projects.items():
            is_current = proj_name == st.session_state.current_project
            with st.expander(f"{'📌' if is_current else '📁'} {proj_name}", expanded=is_current):
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"**ID:** {proj_data.get('customer_id', 'N/A')}")
                    st.markdown(f"**Type:** {proj_data.get('implementation_type', 'N/A')}")
                with col2:
                    if st.button("📌 Active", key=f"act_{proj_name}", disabled=is_current):
                        st.session_state.current_project = proj_name
                        st.rerun()
                with col3:
                    if st.button("🗑️ Delete", key=f"del_{proj_name}"):
                        del st.session_state.projects[proj_name]
                        if st.session_state.current_project == proj_name:
                            st.session_state.current_project = None
                        st.rerun()

# TAB 2: TEMPLATE SYSTEM
with tab2:
    st.markdown("## 🎯 Payroll Template System")
    
    if not PDF_FEATURES_AVAILABLE:
        st.error("⚠️ PDF features not available. Install: pdf2image, Pillow, pytesseract, poppler-utils, tesseract-ocr")
    else:
        ttab1, ttab2, ttab3 = st.tabs(["📝 Create", "⚡ Process", "📚 Manage"])
        
        # CREATE TEMPLATE
        with ttab1:
            st.header("Create Template")
            col1, col2 = st.columns([2, 1])
            
            with col1:
                uploaded_file = st.file_uploader("Upload Sample PDF", type=['pdf'], key="template_upload")
            with col2:
                template_name = st.text_input("Template Name", placeholder="Dayforce_Register")
                template_vendor = st.text_input("Vendor", placeholder="Dayforce, ADP")
            
            if uploaded_file and template_name:
                if not st.session_state.pdf_images or st.session_state.get('last_upload') != uploaded_file.name:
                    with st.spinner("Converting PDF..."):
                        pdf_bytes = uploaded_file.read()
                        st.session_state.pdf_images = convert_from_bytes(pdf_bytes, dpi=300, first_page=1, last_page=1)
                        st.session_state.last_upload = uploaded_file.name
                
                image = st.session_state.pdf_images[0]
                img_w, img_h = image.size
                st.success(f"✅ Loaded: {img_w}px × {img_h}px")
                
                st.markdown("---")
                st.image(image, caption="PDF Preview")
                
                st.markdown("---")
                st.markdown("### Add Columns")
                
                with st.form("add_column"):
                    col_inp1, col_inp2 = st.columns(2)
                    with col_inp1:
                        st.markdown("**X Coordinates**")
                        col_x1 = st.number_input("Left X", 0, img_w, 0, 10)
                        col_x2 = st.number_input("Right X", 0, img_w, 200, 10)
                    with col_inp2:
                        st.markdown("**Y Coordinates**")
                        col_y1 = st.number_input("Top Y", 0, img_h, 0, 10)
                        col_y2 = st.number_input("Bottom Y", 0, img_h, img_h, 10)
                    
                    col_name = st.text_input("Column Name", placeholder="Employee Name")
                    col_cat = st.selectbox("Category", ["Employee Info", "Earnings", "Deductions", "Taxes", "Check Info"])
                    
                    if st.form_submit_button("➕ Add Column", type="primary"):
                        if not col_name:
                            st.error("Enter column name")
                        elif col_x2 <= col_x1 or col_y2 <= col_y1:
                            st.error("Invalid coordinates")
                        else:
                            st.session_state.temp_columns.append({
                                'name': col_name, 'x1': col_x1, 'y1': col_y1,
                                'x2': col_x2, 'y2': col_y2, 'category': col_cat
                            })
                            st.success(f"✅ Added {col_name}")
                            st.rerun()
                
                if st.session_state.temp_columns:
                    st.markdown("---")
                    st.markdown("### Template Preview")
                    
                    preview = image.copy()
                    draw = ImageDraw.Draw(preview)
                    colors = {'Employee Info': 'blue', 'Earnings': 'green', 'Deductions': 'orange', 'Taxes': 'red', 'Check Info': 'purple'}
                    
                    for i, col in enumerate(st.session_state.temp_columns):
                        color = colors.get(col['category'], 'black')
                        draw.rectangle([col['x1'], col['y1'], col['x2'], col['y2']], outline=color, width=3)
                        draw.text((col['x1']+5, col['y1']+5), f"{i+1}. {col['name']}", fill=color)
                    
                    st.image(preview, caption="Template Preview")
                    
                    st.markdown("**Columns:**")
                    for i, col in enumerate(st.session_state.temp_columns):
                        cols = st.columns([4, 1])
                        cols[0].markdown(f"**{i+1}. {col['name']}** → {col['category']}")
                        if cols[1].button("🗑️", key=f"del{i}"):
                            st.session_state.temp_columns.pop(i)
                            st.rerun()
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if st.button("💾 Save Template", type="primary"):
                            template_data = {
                                'name': template_name, 'vendor': template_vendor,
                                'created_at': datetime.now().isoformat(),
                                'image_dimensions': {'width': img_w, 'height': img_h},
                                'columns': st.session_state.temp_columns
                            }
                            save_template(template_name, template_data)
                            st.session_state.templates[template_name] = template_data
                            st.success("✅ Template saved!")
                            st.session_state.temp_columns = []
                            st.session_state.pdf_images = []
                            st.balloons()
                    with col2:
                        if st.button("🔄 Clear"):
                            st.session_state.temp_columns = []
                            st.rerun()
        
        # PROCESS PDF
        with ttab2:
            st.header("Process PDF")
            
            if not st.session_state.templates:
                st.warning("⚠️ No templates. Create one first!")
            else:
                col1, col2 = st.columns([2, 1])
                with col1:
                    process_file = st.file_uploader("Upload PDF", type=['pdf'], key="process_upload")
                with col2:
                    selected_template = st.selectbox("Select Template", list(st.session_state.templates.keys()))
                
                if process_file and selected_template:
                    template = st.session_state.templates[selected_template]
                    
                    with st.spinner("Converting..."):
                        pdf_bytes = process_file.read()
                        process_images = convert_from_bytes(pdf_bytes, dpi=300, first_page=1, last_page=3)
                    
                    st.success(f"✅ {len(process_images)} page(s)")
                    
                    if st.button("🚀 Extract Data", type="primary"):
                        with st.spinner("Extracting..."):
                            all_extracted = {}
                            for page_idx, image in enumerate(process_images):
                                page_data = apply_template(image, template)
                                for category, lines in page_data.items():
                                    if category not in all_extracted:
                                        all_extracted[category] = []
                                    all_extracted[category].extend(lines)
                            st.session_state.extracted_data = all_extracted
                            st.success("✅ Complete!")
                        
                        st.markdown("---")
                        st.markdown("### 📊 Extracted Data")
                        
                        for category in ['Employee Info', 'Earnings', 'Deductions', 'Taxes', 'Check Info']:
                            if category in st.session_state.extracted_data:
                                with st.expander(f"{category} ({len(st.session_state.extracted_data[category])} lines)"):
                                    lines = st.session_state.extracted_data[category]
                                    if len(lines) > 1:
                                        df = pd.DataFrame({'Text': lines})
                                        st.dataframe(df)
                                    else:
                                        st.text('\n'.join(lines))
                        
                        st.markdown("---")
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            for category in ['Employee Info', 'Earnings', 'Deductions', 'Taxes', 'Check Info']:
                                if category in st.session_state.extracted_data:
                                    df = pd.DataFrame({'Data': st.session_state.extracted_data[category]})
                                    df.to_excel(writer, sheet_name=category[:31], index=False)
                            
                            metadata = pd.DataFrame({
                                'Property': ['File', 'Template', 'Processed', 'Pages'],
                                'Value': [process_file.name, selected_template, datetime.now().isoformat(), len(process_images)]
                            })
                            metadata.to_excel(writer, sheet_name='Metadata', index=False)
                        
                        output.seek(0)
                        st.download_button(
                            "📥 Download Excel",
                            output,
                            f"UKG_{process_file.name.replace('.pdf', '')}.xlsx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary"
                        )
        
        # MANAGE TEMPLATES
        with ttab3:
            st.header("Manage Templates")
            
            if not st.session_state.templates:
                st.info("📋 No templates yet")
            else:
                st.markdown(f"### 📚 {len(st.session_state.templates)} Template(s)")
                
                for template_name, template_data in st.session_state.templates.items():
                    with st.expander(f"📄 {template_name}"):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**Vendor:** {template_data.get('vendor', 'N/A')}")
                            st.markdown(f"**Created:** {template_data.get('created_at', 'N/A')}")
                            st.markdown(f"**Columns:** {len(template_data.get('columns', []))}")
                        with col2:
                            if st.button("🗑️ Delete", key=f"del_t_{template_name}"):
                                filepath = TEMPLATE_DIR / f"{template_name}.json"
                                if filepath.exists():
                                    filepath.unlink()
                                del st.session_state.templates[template_name]
                                st.success("Deleted")
                                st.rerun()
                        
                        template_json = json.dumps(template_data, indent=2)
                        st.download_button("📤 Export JSON", template_json, f"{template_name}.json", "application/json", key=f"exp_{template_name}")

# TAB 3: ADMIN
with tab3:
    st.markdown("## ⚙️ Admin")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Projects", len(st.session_state.projects))
    with col2:
        st.metric("Templates", len(st.session_state.templates))
    with col3:
        st.metric("PDF", "✅" if PDF_FEATURES_AVAILABLE else "❌")
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Clear Projects"):
            st.session_state.projects = {}
            st.session_state.current_project = None
            st.success("Cleared!")
            st.rerun()
    with col2:
        if st.button("🔄 Clear Templates"):
            st.session_state.templates = {}
            st.session_state.temp_columns = []
            for file in TEMPLATE_DIR.glob("*.json"):
                file.unlink()
            st.success("Cleared!")
            st.rerun()

st.markdown("---")
st.markdown("<div style='text-align: center; color: #6c757d; padding: 2rem;'><strong>XLR8 by HCMPACT v2.0</strong><br>Payroll Template System</div>", unsafe_allow_html=True)
