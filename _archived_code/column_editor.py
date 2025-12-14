"""
Column Editor Component
Allows user to rename, delete, and reorder columns after parsing
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


def render_column_editor(excel_path: str, table_info: List[Dict]) -> bool:
    """
    Render column editor UI for parsed Excel file.
    
    Args:
        excel_path: Path to parsed Excel file
        table_info: List of table metadata
        
    Returns:
        True if changes were saved
    """
    
    st.markdown("---")
    st.markdown("### ✏️ Edit Columns")
    st.info("Review and correct column names, delete unwanted columns, or reorder them.")
    
    # Load Excel file
    try:
        sheets = pd.read_excel(excel_path, sheet_name=None, engine='openpyxl')
    except Exception as e:
        st.error(f"Error loading Excel: {e}")
        return False
    
    # Initialize session state for edits
    if 'column_edits' not in st.session_state:
        st.session_state.column_edits = {}
        for sheet_name, df in sheets.items():
            st.session_state.column_edits[sheet_name] = {
                'renames': {},  # {old_name: new_name}
                'deletes': [],  # [col_name]
                'order': list(df.columns)  # [col_name, ...]
            }
    
    # Create tabs for each sheet
    sheet_tabs = st.tabs([f"📋 {name}" for name in sheets.keys()])
    
    changes_made = False
    
    for idx, (sheet_name, df) in enumerate(sheets.items()):
        with sheet_tabs[idx]:
            st.markdown(f"**{sheet_name}** - {len(df)} rows")
            
            # Get current column state
            edits = st.session_state.column_edits[sheet_name]
            current_cols = [col for col in edits['order'] if col not in edits['deletes']]
            
            # Column editor table
            st.markdown("#### Column Mapping")
            
            col_data = []
            for col in current_cols:
                new_name = edits['renames'].get(col, col)
                col_data.append({
                    'Original': col,
                    'New Name': new_name,
                    'Sample Data': ', '.join(str(df[col].iloc[i]) for i in range(min(2, len(df))) if pd.notna(df[col].iloc[i]))[:50] + '...'
                })
            
            if col_data:
                # Show editable table
                for i, row in enumerate(col_data):
                    col1, col2, col3, col4 = st.columns([2, 2, 3, 1])
                    
                    with col1:
                        st.text_input(
                            "Original",
                            value=row['Original'],
                            disabled=True,
                            key=f"orig_{sheet_name}_{i}",
                            label_visibility="collapsed"
                        )
                    
                    with col2:
                        new_name = st.text_input(
                            "New Name",
                            value=row['New Name'],
                            key=f"new_{sheet_name}_{i}",
                            label_visibility="collapsed"
                        )
                        
                        # Track rename
                        if new_name != row['Original']:
                            edits['renames'][row['Original']] = new_name
                            changes_made = True
                        elif row['Original'] in edits['renames']:
                            del edits['renames'][row['Original']]
                    
                    with col3:
                        st.caption(row['Sample Data'])
                    
                    with col4:
                        if st.button("🗑️", key=f"del_{sheet_name}_{i}", help="Delete column"):
                            edits['deletes'].append(row['Original'])
                            changes_made = True
                            st.rerun()
                
                # Reorder buttons
                st.markdown("#### Reorder Columns")
                col1, col2 = st.columns(2)
                
                with col1:
                    if len(current_cols) > 1:
                        move_col = st.selectbox(
                            "Move column:",
                            current_cols,
                            key=f"move_col_{sheet_name}"
                        )
                with col2:
                    if len(current_cols) > 1:
                        move_dir = st.selectbox(
                            "Direction:",
                            ["← Left", "→ Right"],
                            key=f"move_dir_{sheet_name}"
                        )
                        
                        if st.button("Move", key=f"move_btn_{sheet_name}"):
                            idx = edits['order'].index(move_col)
                            if move_dir == "← Left" and idx > 0:
                                edits['order'][idx], edits['order'][idx-1] = edits['order'][idx-1], edits['order'][idx]
                                changes_made = True
                                st.rerun()
                            elif move_dir == "→ Right" and idx < len(edits['order']) - 1:
                                edits['order'][idx], edits['order'][idx+1] = edits['order'][idx+1], edits['order'][idx]
                                changes_made = True
                                st.rerun()
                
                # Restore deleted columns
                if edits['deletes']:
                    st.markdown("#### Deleted Columns")
                    for col in edits['deletes']:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.caption(f"❌ {col}")
                        with col2:
                            if st.button("Restore", key=f"restore_{sheet_name}_{col}"):
                                edits['deletes'].remove(col)
                                st.rerun()
                
                # Preview
                st.markdown("#### Preview")
                preview_df = df.copy()
                
                # Apply deletes
                preview_df = preview_df[[col for col in preview_df.columns if col not in edits['deletes']]]
                
                # Apply renames
                rename_map = {old: new for old, new in edits['renames'].items() if old in preview_df.columns}
                if rename_map:
                    preview_df = preview_df.rename(columns=rename_map)
                
                # Apply reorder
                final_order = [edits['renames'].get(col, col) for col in edits['order'] if col not in edits['deletes']]
                final_order = [col for col in final_order if col in preview_df.columns]
                preview_df = preview_df[final_order]
                
                st.dataframe(preview_df.head(3), use_container_width=True)
    
    # Save button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        if st.button("💾 Save Corrected Version", type="primary", disabled=not changes_made):
            success = _apply_edits_and_save(excel_path, sheets, st.session_state.column_edits)
            if success:
                st.success("✅ Saved corrected version!")
                # Clear edits
                st.session_state.column_edits = {}
                return True
            else:
                st.error("❌ Failed to save")
                return False
    
    with col2:
        if st.button("🔄 Reset Changes"):
            st.session_state.column_edits = {}
            st.rerun()
    
    return False


def _apply_edits_and_save(excel_path: str, sheets: Dict[str, pd.DataFrame], edits: Dict) -> bool:
    """Apply edits to DataFrames and save to Excel."""
    try:
        corrected_sheets = {}
        
        for sheet_name, df in sheets.items():
            sheet_edits = edits.get(sheet_name, {})
            
            # Apply deletes
            df_edited = df[[col for col in df.columns if col not in sheet_edits.get('deletes', [])]]
            
            # Apply renames
            rename_map = {old: new for old, new in sheet_edits.get('renames', {}).items() if old in df_edited.columns}
            if rename_map:
                df_edited = df_edited.rename(columns=rename_map)
            
            # Apply reorder
            order = sheet_edits.get('order', list(df.columns))
            final_order = [sheet_edits.get('renames', {}).get(col, col) for col in order if col not in sheet_edits.get('deletes', [])]
            final_order = [col for col in final_order if col in df_edited.columns]
            df_edited = df_edited[final_order]
            
            corrected_sheets[sheet_name] = df_edited
        
        # Save to same path (overwrites original)
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            for sheet_name, df in corrected_sheets.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        logger.info(f"Saved corrected Excel to {excel_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving corrected Excel: {e}")
        return False
