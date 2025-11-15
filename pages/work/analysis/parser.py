"""
Document Parser Module
Extracts text and data from uploaded documents

Owner: Person B - Parser Team
Dependencies: utils/parsers, PyPDF2, openpyxl
Testing: Can run standalone with sample files
"""

import streamlit as st
from typing import Dict, Any, Optional
from utils.parsers.pdf_parser import extract_pdf_text
from utils.parsers.excel_parser import extract_excel_data


def parse_document(uploaded_file) -> Optional[Dict[str, Any]]:
    """
    Parse uploaded document and extract content
    
    Args:
        uploaded_file: Streamlit UploadedFile object
    
    Returns:
        Dictionary with parsed data:
        {
            'text': str,
            'tables': List[DataFrame],
            'metadata': dict
        }
    
    Example Usage:
        parsed = parse_document(file)
        text = parsed['text']
    """
    
    try:
        file_type = uploaded_file.name.split('.')[-1].lower()
        
        if file_type == 'pdf':
            return _parse_pdf(uploaded_file)
        elif file_type in ['xlsx', 'xls', 'csv']:
            return _parse_excel(uploaded_file)
        elif file_type in ['docx', 'doc']:
            return _parse_word(uploaded_file)
        else:
            st.error(f"Unsupported file type: {file_type}")
            return None
            
    except Exception as e:
        st.error(f"Error parsing document: {str(e)}")
        return None


def _parse_pdf(uploaded_file) -> Dict[str, Any]:
    """Parse PDF document"""
    text = extract_pdf_text(uploaded_file)
    
    return {
        'text': text,
        'tables': [],  # TODO: Implement table extraction
        'metadata': {
            'type': 'pdf',
            'filename': uploaded_file.name
        }
    }


def _parse_excel(uploaded_file) -> Dict[str, Any]:
    """Parse Excel document"""
    data = extract_excel_data(uploaded_file)
    
    # Convert tables to text for AI analysis
    text_content = f"Excel file: {uploaded_file.name}\n\n"
    for table_name, df in data.items():
        text_content += f"Sheet: {table_name}\n{df.to_string()}\n\n"
    
    return {
        'text': text_content,
        'tables': list(data.values()),
        'metadata': {
            'type': 'excel',
            'filename': uploaded_file.name,
            'sheets': list(data.keys())
        }
    }


def _parse_word(uploaded_file) -> Dict[str, Any]:
    """Parse Word document"""
    # TODO: Implement Word parsing
    return {
        'text': f"[Word document: {uploaded_file.name}]",
        'tables': [],
        'metadata': {
            'type': 'word',
            'filename': uploaded_file.name
        }
    }


# Standalone testing
if __name__ == "__main__":
    st.title("Parser Module - Standalone Test")
    st.write("Upload a test file to verify parsing")
    
    test_file = st.file_uploader("Test file", type=['pdf', 'xlsx', 'csv'])
    
    if test_file:
        with st.spinner("Parsing..."):
            result = parse_document(test_file)
        
        if result:
            st.success("✅ Parse successful!")
            st.json(result['metadata'])
            st.text_area("Extracted Text Preview", result['text'][:500])
