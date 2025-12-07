"""
Vacuum Extractor Patch
======================
Deploy to: backend/utils/vacuum_extractor_patch.py

This adds the update_extract_data method needed for column splitting.
Import this at the end of your vacuum_extractor.py file, or add 
the method directly to your VacuumExtractor class.

OPTION 1: Add to bottom of vacuum_extractor.py:
    from vacuum_extractor_patch import patch_vacuum_extractor
    patch_vacuum_extractor(VacuumExtractor)

OPTION 2: Copy the method below directly into VacuumExtractor class
"""

def update_extract_data(self, extract_id: int, raw_data=None, raw_headers=None, 
                        column_count=None, metadata=None) -> bool:
    """
    Update an extract's data after column splitting or other modifications.
    
    Args:
        extract_id: The extract ID to update
        raw_data: New data rows (list of lists)
        raw_headers: New column headers
        column_count: New column count
        metadata: Additional metadata dict to merge
        
    Returns:
        bool: True if successful
    """
    try:
        # Build update dict
        updates = {}
        if raw_data is not None:
            updates['raw_data'] = raw_data
            updates['row_count'] = len(raw_data)
        if raw_headers is not None:
            updates['raw_headers'] = raw_headers
        if column_count is not None:
            updates['column_count'] = column_count
            
        if not updates:
            return True  # Nothing to update
            
        # If using Supabase
        if hasattr(self, 'supabase') and self.supabase:
            result = self.supabase.table('vacuum_extracts').update(updates).eq('id', extract_id).execute()
            return bool(result.data)
            
        # If using DuckDB
        if hasattr(self, 'conn') and self.conn:
            import json
            set_clauses = []
            params = []
            
            if 'raw_data' in updates:
                set_clauses.append('raw_data = ?')
                params.append(json.dumps(updates['raw_data']))
            if 'raw_headers' in updates:
                set_clauses.append('raw_headers = ?')
                params.append(json.dumps(updates['raw_headers']))
            if 'row_count' in updates:
                set_clauses.append('row_count = ?')
                params.append(updates['row_count'])
            if 'column_count' in updates:
                set_clauses.append('column_count = ?')
                params.append(updates['column_count'])
                
            if set_clauses:
                params.append(extract_id)
                sql = f"UPDATE vacuum_extracts SET {', '.join(set_clauses)} WHERE id = ?"
                self.conn.execute(sql, params)
                return True
                
        return False
        
    except Exception as e:
        import logging
        logging.error(f"Error updating extract data: {e}")
        return False


def patch_vacuum_extractor(cls):
    """Patch the VacuumExtractor class with the update_extract_data method"""
    if not hasattr(cls, 'update_extract_data'):
        cls.update_extract_data = update_extract_data
    return cls


# For direct import
__all__ = ['update_extract_data', 'patch_vacuum_extractor']
