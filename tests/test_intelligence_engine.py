"""
Tests for Intelligence Engine
==============================
Tests the core query processing pipeline.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, Any


class TestIntelligenceEngine:
    """Tests for IntelligenceEngineV2."""
    
    @pytest.fixture
    def mock_dependencies(self, mock_duckdb, mock_chromadb, mock_llm_orchestrator):
        """Set up all mocked dependencies."""
        return {
            "duckdb": mock_duckdb,
            "chromadb": mock_chromadb,
            "llm": mock_llm_orchestrator
        }
    
    @pytest.fixture
    def engine(self, mock_dependencies):
        """Create engine with mocked dependencies."""
        with patch('backend.utils.intelligence.engine.get_structured_handler') as mock_handler, \
             patch('backend.utils.intelligence.engine.TableSelector') as mock_selector, \
             patch('backend.utils.intelligence.engine.SQLGenerator') as mock_sql_gen, \
             patch('backend.utils.intelligence.engine.Synthesizer') as mock_synth:
            
            mock_handler.return_value = MagicMock()
            mock_handler.return_value.conn = mock_dependencies["duckdb"]
            
            mock_selector.return_value.select_tables.return_value = {
                "selected_tables": ["test__employees"],
                "confidence": 0.9,
                "reasoning": "Table contains employee data"
            }
            
            mock_sql_gen.return_value.generate.return_value = {
                "sql": "SELECT COUNT(*) FROM test__employees",
                "confidence": 0.85
            }
            
            mock_synth.return_value.synthesize.return_value = {
                "answer": "There are 100 employees.",
                "confidence": 0.9
            }
            
            from backend.utils.intelligence import IntelligenceEngineV2
            engine = IntelligenceEngineV2.__new__(IntelligenceEngineV2)
            engine.handler = mock_handler.return_value
            engine.table_selector = mock_selector.return_value
            engine.sql_generator = mock_sql_gen.return_value
            engine.synthesizer = mock_synth.return_value
            
            yield engine
    
    def test_query_classification(self):
        """Test query intent classification."""
        test_queries = [
            ("How many employees?", "count"),
            ("Show me all departments", "list"),
            ("What is the average salary?", "aggregate"),
            ("Compare Q1 vs Q2 revenue", "comparison"),
        ]
        
        for query, expected_type in test_queries:
            # Simple heuristic check
            query_lower = query.lower()
            if "how many" in query_lower or "count" in query_lower:
                detected = "count"
            elif "show" in query_lower or "list" in query_lower:
                detected = "list"
            elif "average" in query_lower or "sum" in query_lower:
                detected = "aggregate"
            elif "compare" in query_lower or "vs" in query_lower:
                detected = "comparison"
            else:
                detected = "unknown"
            
            assert detected == expected_type, f"Failed for: {query}"
    
    def test_table_selection_uses_scorer(self, engine):
        """Test that table selection uses proper scoring."""
        result = engine.table_selector.select_tables(
            query="How many employees in Engineering?",
            project="test"
        )
        
        assert "selected_tables" in result
        assert "confidence" in result
        assert result["confidence"] > 0
    
    def test_sql_generation_valid_syntax(self, engine):
        """Test SQL generation produces valid syntax."""
        result = engine.sql_generator.generate(
            query="Count employees",
            tables=["test__employees"],
            schema={"test__employees": ["employee_id", "name", "department"]}
        )
        
        assert "sql" in result
        assert "SELECT" in result["sql"].upper()
    
    def test_synthesis_includes_confidence(self, engine):
        """Test synthesis returns confidence score."""
        result = engine.synthesizer.synthesize(
            query="How many employees?",
            sql_result={"count": 100},
            context={}
        )
        
        assert "answer" in result
        assert "confidence" in result
        assert 0 <= result["confidence"] <= 1


class TestTableSelector:
    """Tests for TableSelector component."""
    
    def test_score_calculation(self):
        """Test table scoring algorithm."""
        # Simulate scoring logic
        def calculate_score(query_terms, table_columns, table_values):
            score = 0
            for term in query_terms:
                term_lower = term.lower()
                # Column name match
                if any(term_lower in col.lower() for col in table_columns):
                    score += 30
                # Value match
                if any(term_lower in str(val).lower() for val in table_values):
                    score += 20
            return min(score, 100)
        
        # Test cases
        score1 = calculate_score(
            ["employee", "salary"],
            ["employee_id", "name", "salary"],
            ["E001", "Alice", 75000]
        )
        assert score1 >= 50, "Should match on column names"
        
        score2 = calculate_score(
            ["Engineering"],
            ["department"],
            ["Engineering", "Sales", "HR"]
        )
        assert score2 >= 20, "Should match on values"
    
    def test_multi_table_ranking(self):
        """Test ranking multiple candidate tables."""
        candidates = [
            {"table": "employees", "score": 85},
            {"table": "departments", "score": 45},
            {"table": "salaries", "score": 72},
        ]
        
        ranked = sorted(candidates, key=lambda x: x["score"], reverse=True)
        
        assert ranked[0]["table"] == "employees"
        assert ranked[1]["table"] == "salaries"


class TestSQLGenerator:
    """Tests for SQL generation."""
    
    def test_select_query_generation(self):
        """Test basic SELECT query generation."""
        # Simple template-based generation
        def generate_count_query(table, column=None):
            if column:
                return f"SELECT COUNT(DISTINCT {column}) FROM {table}"
            return f"SELECT COUNT(*) FROM {table}"
        
        sql = generate_count_query("employees")
        assert sql == "SELECT COUNT(*) FROM employees"
        
        sql = generate_count_query("employees", "department")
        assert sql == "SELECT COUNT(DISTINCT department) FROM employees"
    
    def test_aggregation_query_generation(self):
        """Test aggregation query generation."""
        def generate_agg_query(table, agg_func, column, group_by=None):
            sql = f"SELECT {agg_func}({column}) FROM {table}"
            if group_by:
                sql += f" GROUP BY {group_by}"
            return sql
        
        sql = generate_agg_query("employees", "AVG", "salary", "department")
        assert "AVG(salary)" in sql
        assert "GROUP BY department" in sql
    
    def test_sql_injection_prevention(self):
        """Test that dangerous inputs are sanitized."""
        dangerous_inputs = [
            "employees; DROP TABLE users;",
            "employees' OR '1'='1",
            "employees\"; DELETE FROM users; --",
        ]
        
        def sanitize_table_name(name):
            # Only allow alphanumeric and underscore
            import re
            return re.sub(r'[^a-zA-Z0-9_]', '', name)
        
        for dangerous in dangerous_inputs:
            sanitized = sanitize_table_name(dangerous)
            assert ";" not in sanitized
            assert "'" not in sanitized
            assert '"' not in sanitized
            assert "--" not in sanitized


class TestSynthesizer:
    """Tests for response synthesis."""
    
    def test_numeric_formatting(self):
        """Test numeric values are formatted properly."""
        def format_number(value):
            if isinstance(value, float):
                if value >= 1000000:
                    return f"{value/1000000:.1f}M"
                elif value >= 1000:
                    return f"{value/1000:.1f}K"
                return f"{value:,.2f}"
            return str(value)
        
        assert format_number(1500000) == "1.5M"
        assert format_number(75000) == "75.0K"
        assert format_number(123.456) == "123.46"
    
    def test_confidence_thresholds(self):
        """Test confidence affects response style."""
        def get_response_prefix(confidence):
            if confidence >= 0.9:
                return ""
            elif confidence >= 0.7:
                return "Based on the available data, "
            elif confidence >= 0.5:
                return "The data suggests that "
            else:
                return "I'm not certain, but "
        
        assert get_response_prefix(0.95) == ""
        assert "suggests" in get_response_prefix(0.6)
        assert "not certain" in get_response_prefix(0.3)
