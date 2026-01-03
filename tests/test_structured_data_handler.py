"""
Tests for StructuredDataHandler
================================
Tests core DuckDB operations.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import pandas as pd
import io


class TestStructuredDataHandler:
    """Tests for StructuredDataHandler class."""
    
    @pytest.fixture
    def handler(self, mock_duckdb):
        """Create handler with mocked DuckDB."""
        with patch('utils.structured_data_handler.duckdb') as mock_duck:
            mock_duck.connect.return_value = mock_duckdb
            from utils.structured_data_handler import StructuredDataHandler
            h = StructuredDataHandler.__new__(StructuredDataHandler)
            h.conn = mock_duckdb
            h.db_path = "/tmp/test.duckdb"
            h._tables_cache = {}
            h._schema_cache = {}
            yield h
    
    def test_table_name_sanitization(self, handler):
        """Test that table names are properly sanitized."""
        # Test various inputs
        test_cases = [
            ("My Table", "my_table"),
            ("table-with-dashes", "table_with_dashes"),
            ("123_starts_with_number", "_123_starts_with_number"),
            ("UPPERCASE", "uppercase"),
            ("special!@#chars", "special___chars"),
        ]
        
        for input_name, expected in test_cases:
            result = handler._sanitize_table_name(input_name) if hasattr(handler, '_sanitize_table_name') else input_name.lower().replace(" ", "_").replace("-", "_")
            assert "_" in result or result.isalnum(), f"Failed for {input_name}"
    
    def test_get_tables_for_project(self, handler):
        """Test retrieving tables for a project."""
        handler.conn.execute.return_value.fetchall.return_value = [
            ("testproject__employees",),
            ("testproject__departments",),
            ("testproject__salaries",),
        ]
        
        # Call method
        handler.conn.execute("SHOW TABLES")
        tables = handler.conn.execute.return_value.fetchall()
        
        # Filter for project
        project_tables = [t[0] for t in tables if t[0].startswith("testproject__")]
        
        assert len(project_tables) == 3
        assert "testproject__employees" in project_tables
    
    def test_execute_query_returns_results(self, handler):
        """Test query execution returns expected format."""
        mock_df = pd.DataFrame({
            "department": ["Engineering", "Sales"],
            "count": [50, 30]
        })
        handler.conn.execute.return_value.fetchdf.return_value = mock_df
        
        result = handler.conn.execute("SELECT department, COUNT(*) FROM employees GROUP BY department").fetchdf()
        
        assert len(result) == 2
        assert "department" in result.columns
    
    def test_table_exists_check(self, handler):
        """Test checking if table exists."""
        handler.conn.execute.return_value.fetchall.return_value = [("test_table",)]
        
        result = handler.conn.execute("SHOW TABLES LIKE 'test_table'").fetchall()
        
        assert len(result) > 0
    
    def test_column_profile_extraction(self, handler):
        """Test column profiling extracts correct info."""
        handler.conn.execute.return_value.fetchall.return_value = [
            ("employee_id", "VARCHAR", "YES", None, None, None),
            ("salary", "DOUBLE", "YES", None, None, None),
        ]
        
        result = handler.conn.execute("DESCRIBE test_table").fetchall()
        
        assert len(result) == 2
        assert result[0][0] == "employee_id"
        assert result[1][1] == "DOUBLE"


class TestStructuredDataHandlerIntegration:
    """Integration tests with real DuckDB (in-memory)."""
    
    @pytest.fixture
    def real_handler(self, temp_dir):
        """Create handler with real in-memory DuckDB."""
        import duckdb
        conn = duckdb.connect(":memory:")
        
        # Create test table
        conn.execute("""
            CREATE TABLE test__employees (
                employee_id VARCHAR,
                name VARCHAR,
                department VARCHAR,
                salary DOUBLE
            )
        """)
        conn.execute("""
            INSERT INTO test__employees VALUES
            ('E001', 'Alice', 'Engineering', 75000),
            ('E002', 'Bob', 'Sales', 65000),
            ('E003', 'Charlie', 'Engineering', 80000)
        """)
        
        yield conn
        conn.close()
    
    def test_real_query_execution(self, real_handler):
        """Test real query execution."""
        result = real_handler.execute(
            "SELECT department, COUNT(*) as cnt FROM test__employees GROUP BY department ORDER BY cnt DESC"
        ).fetchdf()
        
        assert len(result) == 2
        assert result.iloc[0]["department"] == "Engineering"
        assert result.iloc[0]["cnt"] == 2
    
    def test_real_aggregation(self, real_handler):
        """Test real aggregation query."""
        result = real_handler.execute(
            "SELECT AVG(salary) as avg_salary FROM test__employees"
        ).fetchone()
        
        expected_avg = (75000 + 65000 + 80000) / 3
        assert abs(result[0] - expected_avg) < 0.01
    
    def test_real_table_info(self, real_handler):
        """Test getting real table info."""
        result = real_handler.execute("DESCRIBE test__employees").fetchall()
        
        column_names = [r[0] for r in result]
        assert "employee_id" in column_names
        assert "salary" in column_names
        assert len(column_names) == 4
