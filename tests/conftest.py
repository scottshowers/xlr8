"""
Pytest Configuration and Fixtures
==================================
Shared fixtures for XLR8 test suite.
"""

import pytest
import os
import sys
import tempfile
import json
from unittest.mock import MagicMock, patch
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =============================================================================
# ENVIRONMENT FIXTURES
# =============================================================================

@pytest.fixture(autouse=True)
def mock_environment(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")
    monkeypatch.setenv("LLM_ENDPOINT", "http://localhost:11434")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
    monkeypatch.setenv("CHROMADB_PATH", "/tmp/test_chroma")


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# =============================================================================
# MOCK FIXTURES
# =============================================================================

@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    mock = MagicMock()
    mock.table.return_value.select.return_value.execute.return_value.data = []
    mock.table.return_value.insert.return_value.execute.return_value.data = [{"id": "test-id"}]
    mock.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]
    mock.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    return mock


@pytest.fixture
def mock_duckdb():
    """Mock DuckDB connection."""
    mock = MagicMock()
    mock.execute.return_value.fetchall.return_value = []
    mock.execute.return_value.fetchone.return_value = (0,)
    mock.execute.return_value.fetchdf.return_value = MagicMock()
    return mock


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB client."""
    mock = MagicMock()
    collection = MagicMock()
    collection.query.return_value = {"documents": [[]], "metadatas": [[]], "distances": [[]]}
    collection.add.return_value = None
    collection.count.return_value = 0
    mock.get_or_create_collection.return_value = collection
    return mock


@pytest.fixture
def mock_llm_orchestrator():
    """Mock LLM Orchestrator."""
    mock = MagicMock()
    mock.generate.return_value = "Test LLM response"
    mock.generate_with_fallback.return_value = ("Test response", "local")
    return mock


# =============================================================================
# SAMPLE DATA FIXTURES
# =============================================================================

@pytest.fixture
def sample_project() -> Dict[str, Any]:
    """Sample project data."""
    return {
        "id": "test-project-id",
        "name": "TestProject",
        "description": "Test project for unit tests",
        "is_active": True,
        "created_at": "2025-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_document() -> Dict[str, Any]:
    """Sample document data."""
    return {
        "id": "test-doc-id",
        "project_id": "test-project-id",
        "name": "test_data.xlsx",
        "category": "employee_data",
        "file_type": "xlsx",
        "truth_type": "reality"
    }


@pytest.fixture
def sample_table_schema() -> Dict[str, Any]:
    """Sample DuckDB table schema."""
    return {
        "table_name": "testproject__employees",
        "columns": [
            {"name": "employee_id", "type": "VARCHAR"},
            {"name": "first_name", "type": "VARCHAR"},
            {"name": "last_name", "type": "VARCHAR"},
            {"name": "department", "type": "VARCHAR"},
            {"name": "hire_date", "type": "DATE"},
            {"name": "salary", "type": "DOUBLE"}
        ],
        "row_count": 100
    }


@pytest.fixture
def sample_excel_content():
    """Sample Excel file content as bytes."""
    import io
    try:
        import pandas as pd
        df = pd.DataFrame({
            "employee_id": ["E001", "E002", "E003"],
            "name": ["Alice", "Bob", "Charlie"],
            "department": ["Engineering", "Sales", "HR"],
            "salary": [75000, 65000, 55000]
        })
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False)
        buffer.seek(0)
        return buffer.getvalue()
    except ImportError:
        return b""


@pytest.fixture
def sample_csv_content():
    """Sample CSV content."""
    return b"employee_id,name,department,salary\nE001,Alice,Engineering,75000\nE002,Bob,Sales,65000\nE003,Charlie,HR,55000"


@pytest.fixture
def sample_intelligence_query() -> Dict[str, Any]:
    """Sample intelligence query request."""
    return {
        "query": "How many employees are in each department?",
        "project": "TestProject",
        "session_id": "test-session"
    }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_test_file(temp_dir: str, filename: str, content: bytes) -> str:
    """Create a test file in temp directory."""
    filepath = os.path.join(temp_dir, filename)
    with open(filepath, 'wb') as f:
        f.write(content)
    return filepath
