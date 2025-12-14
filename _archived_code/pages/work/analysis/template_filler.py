"""
Template Generation Module
Uses ACTUAL UKG Excel export from secure_pdf_parser
"""

import streamlit as st
from typing import Dict, Any, List
from io import BytesIO
from utils.secure_pdf_parser import process_parsed_pdf_for_ukg
import pandas as pd


def generate_templates(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate UKG templates from analysis results
    Uses ACTUAL working process_parsed_pdf_for_ukg function
    
    Args:
        analysis: Analysis results dictionary
    
    Returns:
        List of template dictionaries with download info
    """
    
    templates = []
    
    # Check if we have parsed PDF data in session state
    if 'parsed_results' in st.session_state and st.session_state.parsed_results:
        parsed_result = st.session_state.parsed_results
        
        # Generate UKG Excel using ACTUAL working function
        try:
            excel_buffer = process_parsed_pdf_for_ukg(
                parsed_result_or_tables=parsed_result,
                filename=parsed_result.get('filename', 'document.pdf')
            )
            
            if excel_buffer:
                templates.append({
                    'name': 'UKG-Ready Template',
                    'type': 'excel',
                    'content': excel_buffer.getvalue(),
                    'filename': 'UKG_Template.xlsx',
                    'description': 'UKG-formatted Excel with 5 tabs: Employee Info, Earnings, Deductions, Taxes, Check Info'
                })
        
        except Exception as e:
            st.error(f"Error generating UKG template: {str(e)}")
    
    # If no parsed PDF, try to generate from analysis text
    if not templates and analysis.get('success'):
        # Generate summary template
        summary_template = _generate_analysis_summary(analysis)
        if summary_template:
            templates.append(summary_template)
    
    return templates


def _generate_analysis_summary(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Excel summary of analysis results"""
    
    try:
        # Create summary DataFrame
        summary_data = {
            'Section': [],
            'Content': []
        }
        
        summary_data['Section'].append('Analysis Type')
        summary_data['Content'].append(analysis.get('depth', 'Standard'))
        
        if analysis.get('findings'):
            for i, finding in enumerate(analysis['findings'], 1):
                summary_data['Section'].append(f'Finding {i}')
                summary_data['Content'].append(finding)
        
        if analysis.get('recommendations'):
            for i, rec in enumerate(analysis['recommendations'], 1):
                summary_data['Section'].append(f'Recommendation {i}')
                summary_data['Content'].append(rec)
        
        df = pd.DataFrame(summary_data)
        
        # Convert to Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Analysis Summary', index=False)
        
        output.seek(0)
        
        return {
            'name': 'Analysis Summary',
            'type': 'excel',
            'content': output.getvalue(),
            'filename': 'Analysis_Summary.xlsx',
            'description': 'Summary of AI analysis findings and recommendations'
        }
    
    except Exception as e:
        st.error(f"Error generating summary: {str(e)}")
        return None


def generate_pay_codes_template(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate pay codes template from parsed data"""
    
    try:
        # Extract earnings-related data
        tables = parsed_data.get('tables', [])
        pay_codes = []
        
        for table_info in tables:
            df = table_info.get('data')
            if df is not None:
                # Look for columns that might contain pay codes
                for col in df.columns:
                    col_lower = str(col).lower()
                    if any(term in col_lower for term in ['pay', 'earn', 'code', 'rate']):
                        # This might be pay code data
                        for val in df[col].dropna().unique():
                            pay_codes.append({'Field': col, 'Value': val})
        
        if pay_codes:
            df = pd.DataFrame(pay_codes)
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Pay Codes', index=False)
            
            output.seek(0)
            
            return {
                'name': 'Pay Codes Template',
                'type': 'excel',
                'content': output.getvalue(),
                'filename': 'Pay_Codes_Template.xlsx',
                'description': 'Extracted pay code information'
            }
    
    except Exception as e:
        st.warning(f"Could not generate pay codes template: {str(e)}")
    
    return None


def generate_deductions_template(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate deductions template from parsed data"""
    
    try:
        tables = parsed_data.get('tables', [])
        deductions = []
        
        for table_info in tables:
            df = table_info.get('data')
            if df is not None:
                # Look for deduction columns
                for col in df.columns:
                    col_lower = str(col).lower()
                    if any(term in col_lower for term in ['deduct', 'withhold', 'tax', 'benefit']):
                        for val in df[col].dropna().unique():
                            deductions.append({'Field': col, 'Value': val})
        
        if deductions:
            df = pd.DataFrame(deductions)
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Deductions', index=False)
            
            output.seek(0)
            
            return {
                'name': 'Deductions Template',
                'type': 'excel',
                'content': output.getvalue(),
                'filename': 'Deductions_Template.xlsx',
                'description': 'Extracted deduction information'
            }
    
    except Exception as e:
        st.warning(f"Could not generate deductions template: {str(e)}")
    
    return None


# Standalone testing
if __name__ == "__main__":
    st.title("Template Generator - Using ACTUAL UKG Export")
    
    st.write("This module uses the working process_parsed_pdf_for_ukg function")
    
    if st.button("Test with sample data"):
        # Create sample analysis
        sample_analysis = {
            'success': True,
            'depth': 'Standard Analysis',
            'findings': [
                'Employee data found in table 1',
                'Pay codes identified: REG, OT, BONUS',
                'Deductions: FED, STATE, 401K'
            ],
            'recommendations': [
                'Map employee IDs to UKG Person Number',
                'Configure pay codes in UKG',
                'Set up deduction rules'
            ]
        }
        
        templates = generate_templates(sample_analysis)
        
        if templates:
            st.success(f"Generated {len(templates)} templates")
            for template in templates:
                st.write(f"- {template['name']}: {template['description']}")
        else:
            st.info("No templates generated (need parsed PDF data in session state)")
