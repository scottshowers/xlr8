"""
File Upload Validator
Sanitizes and validates all uploaded files
"""

import re
from pathlib import Path
from typing import Tuple


class FileValidator:
    """Validate and sanitize uploaded files"""
    
    # Allowed extensions
    ALLOWED_EXTENSIONS = {
        '.pdf', '.xlsx', '.xls', '.docx', '.doc', 
        '.csv', '.txt', '.md'
    }
    
    # Max size in MB
    MAX_SIZE_MB = 200
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize uploaded filename to prevent path traversal
        
        Args:
            filename: Original filename
            
        Returns:
            Safe filename
        """
        # Get just the filename (no path)
        filename = Path(filename).name
        
        # Remove dangerous characters
        filename = re.sub(r'[^\w\s\-.]', '', filename)
        
        # Remove multiple dots (except for extension)
        name_parts = filename.rsplit('.', 1)
        if len(name_parts) == 2:
            name, ext = name_parts
            name = name.replace('.', '_')
            filename = f"{name}.{ext}"
        
        # Limit length
        if len(filename) > 200:
            name, ext = filename.rsplit('.', 1)
            name = name[:190]
            filename = f"{name}.{ext}"
        
        return filename
    
    @staticmethod
    def validate_size(uploaded_file, max_size_mb: int = None) -> Tuple[bool, str]:
        """
        Validate file size
        
        Args:
            uploaded_file: Streamlit UploadedFile
            max_size_mb: Max size in MB (default: from class)
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        max_size = max_size_mb or FileValidator.MAX_SIZE_MB
        
        file_size_mb = uploaded_file.size / (1024 * 1024)
        
        if file_size_mb > max_size:
            return False, f"File too large: {file_size_mb:.1f}MB (max {max_size}MB)"
        
        return True, ""
    
    @staticmethod
    def validate_extension(filename: str) -> Tuple[bool, str]:
        """
        Validate file extension
        
        Args:
            filename: Filename to check
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        ext = Path(filename).suffix.lower()
        
        if ext not in FileValidator.ALLOWED_EXTENSIONS:
            allowed = ', '.join(FileValidator.ALLOWED_EXTENSIONS)
            return False, f"Invalid file type: {ext}. Allowed: {allowed}"
        
        return True, ""
    
    @classmethod
    def validate_upload(cls, uploaded_file, max_size_mb: int = None) -> Tuple[bool, str, str]:
        """
        Complete validation of uploaded file
        
        Args:
            uploaded_file: Streamlit UploadedFile
            max_size_mb: Optional max size override
            
        Returns:
            Tuple of (is_valid, safe_filename, error_message)
        """
        # Sanitize filename
        safe_name = cls.sanitize_filename(uploaded_file.name)
        
        # Validate extension
        valid, error = cls.validate_extension(safe_name)
        if not valid:
            return False, safe_name, error
        
        # Validate size
        valid, error = cls.validate_size(uploaded_file, max_size_mb)
        if not valid:
            return False, safe_name, error
        
        return True, safe_name, ""


# Convenience function
def validate_upload(uploaded_file, max_size_mb: int = None):
    """
    Quick validation function
    
    Usage:
        from utils.file_validator import validate_upload
        
        is_valid, safe_name, error = validate_upload(uploaded_file)
        if not is_valid:
            st.error(error)
            return None
    """
    return FileValidator.validate_upload(uploaded_file, max_size_mb)
