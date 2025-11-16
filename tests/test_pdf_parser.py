"""
PDF Parser Module Test Template

This file allows you to test your PDF parser implementation independently
without running the entire XLR8 application.

HOW TO USE:
1. Copy this file to your module directory
2. Implement your parser following the PDFParserInterface
3. Run this file: streamlit run test_pdf_parser.py
4. Upload test PDFs and verify results
5. When satisfied, integrate into main app with feature flag
"""

import streamlit as st
import sys
from pathlib import Path
from io import BytesIO
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the interface
from interfaces.pdf_parser_interface import PDFParserInterface, PayrollParserInterface


# ============================================
# IMPORT YOUR PARSER HERE
# ============================================
# Example:
# from utils.parsers.improved_pdf_parser import ImprovedPDFParser
# parser = ImprovedPDFParser()

# For testing, use the original parser:
from utils.parsers.pdf_parser import EnhancedPayrollParser
parser = EnhancedPayrollParser()


def main():
    """Main test interface"""
    
    st.set_page_config(
        page_title="PDF Parser Test",
        page_icon="📄",
        layout="wide"
    )
    
    st.title("📄 PDF Parser Module Test")
    
    st.markdown("""
    ### Test Your PDF Parser Implementation
    
    This standalone test allows you to:
    1. Upload test PDFs
    2. View parsing results
    3. Validate against interface contract
    4. Compare with original parser
    5. Export test results
    
    **Before integration:** Ensure all tests pass here!
    """)
    
    # Sidebar with parser info
    with st.sidebar:
        st.markdown("### Parser Information")
        
        try:
            info = parser.get_parser_info()
            st.success(f"**{info['name']}** v{info['version']}")
            st.write(f"**Engine:** {info['engine']}")
            st.write(f"**Capabilities:** {', '.join(info['capabilities'])}")
        except Exception as e:
            st.error(f"Failed to get parser info: {e}")
        
        st.markdown("---")
        st.markdown("### Test Options")
        
        test_validation = st.checkbox("Test validation", value=True)
        test_tables = st.checkbox("Test table extraction", value=True)
        test_text = st.checkbox("Test text extraction", value=True)
        compare_parsers = st.checkbox("Compare with original", value=False)
    
    # Main test area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### 📤 Upload Test PDF")
        
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            help="Upload a test PDF to validate your parser"
        )
        
        if uploaded_file:
            st.success(f"Uploaded: {uploaded_file.name}")
            st.write(f"Size: {uploaded_file.size / 1024:.2f} KB")
    
    with col2:
        st.markdown("### 📊 Test Results")
        
        if uploaded_file:
            # Create BytesIO object
            file_bytes = BytesIO(uploaded_file.getvalue())
            
            # Run tests
            with st.spinner("Running tests..."):
                results = run_all_tests(
                    parser=parser,
                    file=file_bytes,
                    filename=uploaded_file.name,
                    test_validation=test_validation,
                    test_tables=test_tables,
                    test_text=test_text
                )
            
            # Display results
            display_test_results(results)
    
    # Test suite section
    st.markdown("---")
    st.markdown("### 🧪 Test Suite")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Run Interface Compliance Test"):
            run_interface_compliance_test(parser)
    
    with col2:
        if st.button("Run Performance Test"):
            if uploaded_file:
                run_performance_test(parser, BytesIO(uploaded_file.getvalue()), uploaded_file.name)
            else:
                st.warning("Upload a file first!")
    
    with col3:
        if st.button("Export Test Report"):
            if uploaded_file:
                export_test_report(results if 'results' in locals() else None)
            else:
                st.warning("Run tests first!")


def run_all_tests(parser, file, filename, test_validation, test_tables, test_text):
    """Run all selected tests"""
    
    results = {
        'timestamp': pd.Timestamp.now(),
        'filename': filename,
        'tests_run': [],
        'tests_passed': [],
        'tests_failed': [],
        'errors': []
    }
    
    # Test 1: Validation
    if test_validation:
        results['tests_run'].append('validation')
        try:
            file.seek(0)  # Reset file pointer
            validation = parser.validate_structure(file)
            
            if validation['is_valid']:
                results['tests_passed'].append('validation')
                results['validation'] = validation
            else:
                results['tests_failed'].append('validation')
                results['errors'].append(f"Validation failed: {validation.get('warnings', [])}")
        
        except Exception as e:
            results['tests_failed'].append('validation')
            results['errors'].append(f"Validation error: {str(e)}")
    
    # Test 2: Full Parse
    results['tests_run'].append('full_parse')
    try:
        file.seek(0)
        parse_result = parser.parse(file, filename)
        
        if parse_result['success']:
            results['tests_passed'].append('full_parse')
            results['parse_result'] = parse_result
        else:
            results['tests_failed'].append('full_parse')
            results['errors'].extend(parse_result.get('errors', []))
    
    except Exception as e:
        results['tests_failed'].append('full_parse')
        results['errors'].append(f"Parse error: {str(e)}")
    
    # Test 3: Table Extraction
    if test_tables:
        results['tests_run'].append('tables')
        try:
            file.seek(0)
            tables = parser.extract_tables(file)
            
            if tables:
                results['tests_passed'].append('tables')
                results['tables'] = tables
            else:
                results['tests_failed'].append('tables')
                results['errors'].append("No tables extracted")
        
        except Exception as e:
            results['tests_failed'].append('tables')
            results['errors'].append(f"Table extraction error: {str(e)}")
    
    # Test 4: Text Extraction
    if test_text:
        results['tests_run'].append('text')
        try:
            file.seek(0)
            text = parser.extract_text(file)
            
            if text and len(text) > 0:
                results['tests_passed'].append('text')
                results['text'] = text
            else:
                results['tests_failed'].append('text')
                results['errors'].append("No text extracted")
        
        except Exception as e:
            results['tests_failed'].append('text')
            results['errors'].append(f"Text extraction error: {str(e)}")
    
    return results


def display_test_results(results):
    """Display test results"""
    
    total_tests = len(results['tests_run'])
    passed_tests = len(results['tests_passed'])
    failed_tests = len(results['tests_failed'])
    
    # Summary
    st.markdown("#### Test Summary")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Tests", total_tests)
    col2.metric("Passed", passed_tests, delta=None if failed_tests == 0 else "✓")
    col3.metric("Failed", failed_tests, delta=None if failed_tests == 0 else "✗")
    
    # Pass rate
    pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    if pass_rate == 100:
        st.success(f"✅ All tests passed! ({pass_rate:.0f}%)")
    elif pass_rate >= 70:
        st.warning(f"⚠️ Most tests passed ({pass_rate:.0f}%)")
    else:
        st.error(f"❌ Many tests failed ({pass_rate:.0f}%)")
    
    # Detailed results
    with st.expander("📊 Detailed Results", expanded=True):
        
        # Validation results
        if 'validation' in results:
            st.markdown("**Validation Results:**")
            val = results['validation']
            st.json({
                'is_valid': val['is_valid'],
                'page_count': val['page_count'],
                'has_tables': val['has_tables'],
                'has_text': val['has_text'],
                'is_scanned': val['is_scanned'],
                'warnings': val['warnings']
            })
        
        # Parse results
        if 'parse_result' in results:
            st.markdown("**Parse Results:**")
            parse = results['parse_result']
            st.write(f"- Text length: {len(parse.get('text', ''))}")
            st.write(f"- Tables found: {len(parse.get('tables', []))}")
            st.write(f"- Success: {parse.get('success')}")
        
        # Table preview
        if 'tables' in results and results['tables']:
            st.markdown("**Table Preview:**")
            for i, table in enumerate(results['tables'][:2]):  # Show first 2 tables
                st.write(f"Table {i+1} ({table.shape[0]} rows x {table.shape[1]} cols)")
                st.dataframe(table.head(10))
        
        # Text preview
        if 'text' in results:
            st.markdown("**Text Preview:**")
            st.text(results['text'][:500] + "..." if len(results['text']) > 500 else results['text'])
    
    # Errors
    if results['errors']:
        with st.expander("❌ Errors", expanded=True):
            for error in results['errors']:
                st.error(error)


def run_interface_compliance_test(parser):
    """Test if parser implements the interface correctly"""
    
    st.markdown("#### Interface Compliance Test")
    
    required_methods = [
        'parse',
        'extract_tables',
        'extract_text',
        'validate_structure',
        'get_parser_info'
    ]
    
    results = {}
    
    for method in required_methods:
        has_method = hasattr(parser, method)
        results[method] = has_method
        
        if has_method:
            st.success(f"✅ {method}")
        else:
            st.error(f"❌ {method} - MISSING!")
    
    compliance_rate = (sum(results.values()) / len(results)) * 100
    
    if compliance_rate == 100:
        st.success(f"✅ Fully compliant with PDFParserInterface ({compliance_rate:.0f}%)")
    else:
        st.error(f"❌ Interface compliance: {compliance_rate:.0f}%")


def run_performance_test(parser, file, filename):
    """Test parser performance"""
    import time
    
    st.markdown("#### Performance Test")
    
    with st.spinner("Running performance test..."):
        # Test 1: Parse time
        file.seek(0)
        start = time.time()
        result = parser.parse(file, filename)
        parse_time = time.time() - start
        
        # Test 2: Table extraction time
        file.seek(0)
        start = time.time()
        tables = parser.extract_tables(file)
        table_time = time.time() - start
        
        # Test 3: Text extraction time
        file.seek(0)
        start = time.time()
        text = parser.extract_text(file)
        text_time = time.time() - start
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Parse Time", f"{parse_time:.2f}s")
    col2.metric("Table Extract", f"{table_time:.2f}s")
    col3.metric("Text Extract", f"{text_time:.2f}s")
    
    # Performance rating
    total_time = parse_time + table_time + text_time
    
    if total_time < 5:
        st.success("⚡ Excellent performance!")
    elif total_time < 15:
        st.info("👍 Good performance")
    else:
        st.warning("⚠️ Consider optimization")


def export_test_report(results):
    """Export test results to file"""
    
    if not results:
        st.warning("No test results to export!")
        return
    
    import json
    
    # Convert to JSON
    report = {
        'timestamp': results['timestamp'].isoformat(),
        'filename': results['filename'],
        'tests_run': results['tests_run'],
        'tests_passed': results['tests_passed'],
        'tests_failed': results['tests_failed'],
        'errors': results['errors'],
        'pass_rate': len(results['tests_passed']) / len(results['tests_run']) * 100 if results['tests_run'] else 0
    }
    
    report_json = json.dumps(report, indent=2)
    
    st.download_button(
        label="📥 Download Test Report (JSON)",
        data=report_json,
        file_name=f"parser_test_report_{results['timestamp'].strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json"
    )
    
    st.success("Test report ready for download!")


if __name__ == "__main__":
    main()
