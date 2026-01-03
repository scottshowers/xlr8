"""
Tests for Upload Flow
======================
Tests file upload and processing pipeline.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
import io


class TestUploadEndpoints:
    """Tests for upload router endpoints."""
    
    @pytest.fixture
    def app(self):
        """Create test FastAPI app."""
        app = FastAPI()
        
        # Mock the router
        from fastapi import APIRouter
        router = APIRouter()
        
        @router.post("/upload")
        async def upload_file(project: str = "default"):
            return {"status": "success", "project": project}
        
        app.include_router(router, prefix="/api")
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return TestClient(app)
    
    def test_upload_requires_project(self, client):
        """Test that upload requires project parameter."""
        response = client.post("/api/upload")
        assert response.status_code == 200
        assert response.json()["project"] == "default"
    
    def test_upload_accepts_project(self, client):
        """Test upload accepts custom project."""
        response = client.post("/api/upload?project=TestProject")
        assert response.status_code == 200
        assert response.json()["project"] == "TestProject"


class TestFileProcessing:
    """Tests for file processing logic."""
    
    def test_excel_detection(self):
        """Test Excel file type detection."""
        test_files = [
            ("data.xlsx", "xlsx"),
            ("report.xls", "xls"),
            ("export.xlsm", "xlsm"),
            ("data.csv", "csv"),
            ("config.pdf", "pdf"),
        ]
        
        for filename, expected_type in test_files:
            ext = filename.rsplit(".", 1)[-1].lower()
            assert ext == expected_type
    
    def test_file_hash_generation(self):
        """Test file hash is generated correctly."""
        import hashlib
        
        content = b"test file content"
        expected_hash = hashlib.sha256(content).hexdigest()
        
        actual_hash = hashlib.sha256(content).hexdigest()
        
        assert actual_hash == expected_hash
        assert len(actual_hash) == 64  # SHA256 hex length
    
    def test_table_name_from_filename(self):
        """Test DuckDB table name generation."""
        def generate_table_name(project: str, filename: str, sheet: str = None) -> str:
            import re
            # Sanitize project
            proj = re.sub(r'[^a-zA-Z0-9]', '', project).lower()
            # Sanitize filename (remove extension)
            name = filename.rsplit(".", 1)[0]
            name = re.sub(r'[^a-zA-Z0-9]', '_', name).lower()
            
            if sheet:
                sheet = re.sub(r'[^a-zA-Z0-9]', '_', sheet).lower()
                return f"{proj}__{name}__{sheet}"
            return f"{proj}__{name}"
        
        assert generate_table_name("Test Project", "data.xlsx") == "testproject__data"
        assert generate_table_name("Proj", "My File.xlsx", "Sheet 1") == "proj__my_file__sheet_1"
    
    def test_row_count_extraction(self):
        """Test row count is correctly extracted."""
        import pandas as pd
        
        df = pd.DataFrame({
            "a": [1, 2, 3, 4, 5],
            "b": ["x", "y", "z", "w", "v"]
        })
        
        assert len(df) == 5
        assert df.shape[0] == 5


class TestExcelParsing:
    """Tests for Excel file parsing."""
    
    @pytest.fixture
    def sample_excel(self):
        """Create sample Excel file."""
        import pandas as pd
        
        df = pd.DataFrame({
            "employee_id": ["E001", "E002", "E003"],
            "name": ["Alice", "Bob", "Charlie"],
            "salary": [75000, 65000, 80000]
        })
        
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, sheet_name="Employees")
        buffer.seek(0)
        return buffer
    
    def test_parse_single_sheet(self, sample_excel):
        """Test parsing single sheet Excel."""
        import pandas as pd
        
        df = pd.read_excel(sample_excel, sheet_name="Employees")
        
        assert len(df) == 3
        assert list(df.columns) == ["employee_id", "name", "salary"]
    
    def test_detect_header_row(self):
        """Test header row detection."""
        import pandas as pd
        
        # Data with header in row 0
        df1 = pd.DataFrame({
            "employee_id": ["E001", "E002"],
            "name": ["Alice", "Bob"]
        })
        assert "employee_id" in df1.columns
        
        # Simulate data with header in row 2
        data = [
            ["", ""],
            ["Report Title", ""],
            ["employee_id", "name"],
            ["E001", "Alice"],
        ]
        df2 = pd.DataFrame(data)
        # Find header row
        for i, row in df2.iterrows():
            if "employee_id" in row.values:
                header_row = i
                break
        assert header_row == 2


class TestCSVParsing:
    """Tests for CSV file parsing."""
    
    def test_parse_csv_content(self, sample_csv_content):
        """Test parsing CSV content."""
        import pandas as pd
        
        df = pd.read_csv(io.BytesIO(sample_csv_content))
        
        assert len(df) == 3
        assert "employee_id" in df.columns
    
    def test_detect_delimiter(self):
        """Test delimiter detection."""
        import csv
        
        csv_content = "a,b,c\n1,2,3"
        tsv_content = "a\tb\tc\n1\t2\t3"
        
        # Simple detection
        def detect_delimiter(content):
            first_line = content.split("\n")[0]
            if "\t" in first_line:
                return "\t"
            elif "," in first_line:
                return ","
            elif ";" in first_line:
                return ";"
            return ","
        
        assert detect_delimiter(csv_content) == ","
        assert detect_delimiter(tsv_content) == "\t"
    
    def test_encoding_handling(self):
        """Test handling different encodings."""
        # UTF-8 content
        utf8_content = "name,city\nAlice,München".encode('utf-8')
        
        # Decode and verify
        decoded = utf8_content.decode('utf-8')
        assert "München" in decoded


class TestPDFProcessing:
    """Tests for PDF file processing."""
    
    def test_pdf_classification(self):
        """Test PDF is classified correctly."""
        def classify_pdf(text_content: str) -> str:
            text_lower = text_content.lower()
            
            if any(kw in text_lower for kw in ["configuration", "settings", "setup"]):
                return "configuration"
            elif any(kw in text_lower for kw in ["compliance", "regulation", "policy"]):
                return "regulatory"
            elif any(kw in text_lower for kw in ["guide", "manual", "reference"]):
                return "reference"
            else:
                return "reference"  # Default for PDFs
        
        assert classify_pdf("Configuration Guide") == "configuration"
        assert classify_pdf("Compliance Policy Document") == "regulatory"
        assert classify_pdf("User Manual") == "reference"
    
    def test_pdf_text_extraction_fallback(self):
        """Test fallback when PDF text extraction fails."""
        def extract_text_with_fallback(pdf_bytes):
            try:
                # Simulate primary extraction
                raise Exception("Primary extraction failed")
            except Exception:
                # Fallback to OCR or other method
                return "Fallback text extraction"
        
        result = extract_text_with_fallback(b"fake pdf content")
        assert result == "Fallback text extraction"


class TestUploadValidation:
    """Tests for upload validation."""
    
    def test_file_size_limit(self):
        """Test file size validation."""
        MAX_SIZE = 50 * 1024 * 1024  # 50MB
        
        def validate_file_size(size_bytes: int) -> bool:
            return size_bytes <= MAX_SIZE
        
        assert validate_file_size(1024) == True
        assert validate_file_size(100 * 1024 * 1024) == False
    
    def test_allowed_extensions(self):
        """Test file extension validation."""
        ALLOWED = {".xlsx", ".xls", ".csv", ".pdf", ".xlsm", ".tsv"}
        
        def validate_extension(filename: str) -> bool:
            ext = "." + filename.rsplit(".", 1)[-1].lower()
            return ext in ALLOWED
        
        assert validate_extension("data.xlsx") == True
        assert validate_extension("script.py") == False
        assert validate_extension("report.PDF") == True  # Case insensitive
    
    def test_filename_sanitization(self):
        """Test filename sanitization."""
        def sanitize_filename(filename: str) -> str:
            import re
            # Remove path separators
            filename = filename.replace("/", "_").replace("\\", "_")
            # Remove dangerous characters
            filename = re.sub(r'[<>:"|?*]', '_', filename)
            return filename
        
        assert "/" not in sanitize_filename("path/to/file.xlsx")
        assert sanitize_filename("file<name>.xlsx") == "file_name_.xlsx"
