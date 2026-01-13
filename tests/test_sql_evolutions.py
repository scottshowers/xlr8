#!/usr/bin/env python3
"""
SQL Evolutions Regression Test Suite
=====================================
Tests all 10 SQL evolutions to ensure nothing broke.

Usage:
    python test_sql_evolutions.py --project <project_id>
    python test_sql_evolutions.py --project <project_id> --base-url https://your-api.com
    
Requirements:
    - Project must have employee-like data with columns:
      state, salary, hire_date, department, supervisor_id, employee_number, name
    - Adjust test queries below if your schema differs
"""

import asyncio
import argparse
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Add parent to path for imports
sys.path.insert(0, '/home/claude/xlr8-main/backend')

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class TestStatus(Enum):
    PASS = "✅ PASS"
    FAIL = "❌ FAIL"
    SKIP = "⏭️ SKIP"
    WARN = "⚠️ WARN"


@dataclass
class TestResult:
    evolution: int
    name: str
    query: str
    status: TestStatus
    details: str
    sql_generated: Optional[str] = None
    used_deterministic: Optional[bool] = None
    error: Optional[str] = None


@dataclass
class TestCase:
    evolution: int
    name: str
    query: str
    expected_sql_patterns: List[str]  # Patterns that SHOULD appear in SQL
    forbidden_patterns: List[str] = None  # Patterns that should NOT appear
    require_deterministic: bool = True


# =============================================================================
# TEST CASES - Adjust queries to match your schema
# =============================================================================

TEST_CASES = [
    # Evolution 1: Categorical Lookups
    TestCase(
        evolution=1,
        name="Categorical Lookup",
        query="employees in California",
        expected_sql_patterns=["WHERE", "california", "="],
    ),
    TestCase(
        evolution=1,
        name="Categorical Lookup (alternate)",
        query="show me active employees",
        expected_sql_patterns=["WHERE", "active"],
    ),
    
    # Evolution 2: Multi-Table JOINs
    TestCase(
        evolution=2,
        name="Multi-Table JOIN",
        query="employees with their department names",
        expected_sql_patterns=["JOIN"],
    ),
    
    # Evolution 3: Numeric Comparisons
    TestCase(
        evolution=3,
        name="Numeric Greater Than",
        query="employees with salary greater than 50000",
        expected_sql_patterns=["WHERE", "salary", ">", "50000"],
    ),
    TestCase(
        evolution=3,
        name="Numeric Less Than",
        query="employees making less than 40000",
        expected_sql_patterns=["WHERE", "salary", "<", "40000"],
    ),
    TestCase(
        evolution=3,
        name="Numeric Between",
        query="employees with salary between 50000 and 100000",
        expected_sql_patterns=["WHERE", "salary", "BETWEEN"],
    ),
    
    # Evolution 4: Date/Time Filters
    TestCase(
        evolution=4,
        name="Date After",
        query="employees hired after January 2024",
        expected_sql_patterns=["WHERE", "hire", "2024"],
    ),
    TestCase(
        evolution=4,
        name="Date Before",
        query="employees hired before 2020",
        expected_sql_patterns=["WHERE", "hire", "2020"],
    ),
    
    # Evolution 5: OR Logic
    TestCase(
        evolution=5,
        name="OR with IN clause",
        query="employees in California or Texas",
        expected_sql_patterns=["WHERE"],
        # Should have either OR or IN
    ),
    TestCase(
        evolution=5,
        name="Multiple OR conditions",
        query="employees in CA or TX or NY",
        expected_sql_patterns=["WHERE"],
    ),
    
    # Evolution 6: Negation
    TestCase(
        evolution=6,
        name="Negation - NOT",
        query="employees not in California",
        expected_sql_patterns=["WHERE"],
        # Should have != or NOT or <> 
    ),
    TestCase(
        evolution=6,
        name="Negation - Exclude",
        query="employees excluding Texas",
        expected_sql_patterns=["WHERE"],
    ),
    
    # Evolution 7: Aggregations
    TestCase(
        evolution=7,
        name="SUM Aggregation",
        query="total salary by department",
        expected_sql_patterns=["SUM", "salary", "GROUP BY"],
    ),
    TestCase(
        evolution=7,
        name="COUNT Aggregation",
        query="how many employees are there",
        expected_sql_patterns=["COUNT"],
    ),
    TestCase(
        evolution=7,
        name="AVG Aggregation",
        query="average salary",
        expected_sql_patterns=["AVG", "salary"],
    ),
    
    # Evolution 8: Group By
    TestCase(
        evolution=8,
        name="Group By Single Column",
        query="count employees by state",
        expected_sql_patterns=["COUNT", "GROUP BY", "state"],
    ),
    TestCase(
        evolution=8,
        name="Group By with Aggregation",
        query="average salary by department",
        expected_sql_patterns=["AVG", "GROUP BY", "department"],
    ),
    
    # Evolution 9: Superlatives
    TestCase(
        evolution=9,
        name="Superlative - Highest",
        query="highest paid employee",
        expected_sql_patterns=["ORDER BY", "salary", "DESC", "LIMIT"],
    ),
    TestCase(
        evolution=9,
        name="Superlative - Lowest",
        query="lowest salary",
        expected_sql_patterns=["ORDER BY", "salary", "ASC", "LIMIT"],
    ),
    TestCase(
        evolution=9,
        name="Superlative - Top N",
        query="top 5 highest salaries",
        expected_sql_patterns=["ORDER BY", "DESC", "LIMIT"],
    ),
    
    # Evolution 10: Multi-Hop Relationships
    TestCase(
        evolution=10,
        name="Multi-Hop - Manager's Attribute",
        query="show me each employee's manager department",
        expected_sql_patterns=["JOIN"],  # Self-join
    ),
    TestCase(
        evolution=10,
        name="Multi-Hop - Supervisor Name",
        query="employees with their supervisor name",
        expected_sql_patterns=["JOIN"],
    ),
    TestCase(
        evolution=10,
        name="Multi-Hop - Named Possessive",
        query="who is on John's team",
        expected_sql_patterns=["JOIN", "WHERE", "John"],
    ),
]


# =============================================================================
# TEST RUNNER
# =============================================================================

class SQLEvolutionTester:
    """Run SQL evolution regression tests."""
    
    def __init__(self, project_id: str, base_url: str = None):
        self.project_id = project_id
        self.base_url = base_url or "http://localhost:8000"
        self.results: List[TestResult] = []
    
    async def run_all_tests(self) -> List[TestResult]:
        """Run all test cases."""
        print("\n" + "=" * 60)
        print("XLR8 SQL EVOLUTIONS REGRESSION TEST")
        print("=" * 60)
        print(f"Project: {self.project_id}")
        print(f"API: {self.base_url}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60 + "\n")
        
        for test_case in TEST_CASES:
            result = await self.run_single_test(test_case)
            self.results.append(result)
            self._print_result(result)
        
        self._print_summary()
        return self.results
    
    async def run_single_test(self, test: TestCase) -> TestResult:
        """Run a single test case."""
        try:
            # Call the query endpoint
            response = await self._call_query_api(test.query)
            
            if response is None:
                return TestResult(
                    evolution=test.evolution,
                    name=test.name,
                    query=test.query,
                    status=TestStatus.FAIL,
                    details="API call failed",
                    error="No response from API"
                )
            
            # Extract SQL and path info
            sql = self._extract_sql(response)
            used_deterministic = self._check_deterministic(response)
            
            # Validate results
            status, details = self._validate_result(test, sql, used_deterministic)
            
            return TestResult(
                evolution=test.evolution,
                name=test.name,
                query=test.query,
                status=status,
                details=details,
                sql_generated=sql,
                used_deterministic=used_deterministic,
            )
            
        except Exception as e:
            return TestResult(
                evolution=test.evolution,
                name=test.name,
                query=test.query,
                status=TestStatus.FAIL,
                details=f"Exception: {str(e)}",
                error=str(e)
            )
    
    async def _call_query_api(self, query: str) -> Optional[Dict]:
        """Call the query API endpoint."""
        if HAS_HTTPX:
            async with httpx.AsyncClient(timeout=60.0) as client:
                try:
                    response = await client.post(
                        f"{self.base_url}/api/query",
                        json={
                            "project_id": self.project_id,
                            "query": query,
                        }
                    )
                    if response.status_code == 200:
                        return response.json()
                    else:
                        print(f"    API returned {response.status_code}: {response.text[:200]}")
                        return None
                except Exception as e:
                    print(f"    API error: {e}")
                    return None
        else:
            # Fallback: try direct engine call
            return await self._call_engine_direct(query)
    
    async def _call_engine_direct(self, query: str) -> Optional[Dict]:
        """Call engine directly if httpx not available."""
        try:
            from utils.intelligence.engine import IntelligenceEngine
            
            engine = IntelligenceEngine()
            result = await engine.query(
                project_id=self.project_id,
                query=query
            )
            
            # Convert to dict-like structure
            return {
                "sql": getattr(result, 'sql', None) or getattr(result, 'generated_sql', None),
                "path": getattr(result, 'path', None) or getattr(result, 'resolution_path', None),
                "data": getattr(result, 'data', None),
                "response": getattr(result, 'response', None),
            }
        except Exception as e:
            print(f"    Direct engine error: {e}")
            return None
    
    def _extract_sql(self, response: Dict) -> Optional[str]:
        """Extract SQL from response."""
        # Try various keys where SQL might be
        for key in ['sql', 'generated_sql', 'query_sql', 'sql_query']:
            if key in response and response[key]:
                return response[key]
        
        # Check nested structures
        if 'sql_results' in response and response['sql_results']:
            sql_results = response['sql_results']
            if isinstance(sql_results, dict) and 'sql' in sql_results:
                return sql_results['sql']
        
        return None
    
    def _check_deterministic(self, response: Dict) -> Optional[bool]:
        """Check if deterministic path was used."""
        # Look for path indicators
        path = response.get('path') or response.get('resolution_path', '')
        
        if isinstance(path, str):
            path_lower = path.lower()
            if 'deterministic' in path_lower:
                return True
            if 'llm' in path_lower or 'fallback' in path_lower:
                return False
        
        # Check for explicit flag
        if 'used_deterministic' in response:
            return response['used_deterministic']
        
        return None
    
    def _validate_result(
        self,
        test: TestCase,
        sql: Optional[str],
        used_deterministic: Optional[bool]
    ) -> Tuple[TestStatus, str]:
        """Validate test result against expectations."""
        issues = []
        
        # Check if we got SQL
        if not sql:
            return TestStatus.FAIL, "No SQL generated"
        
        sql_upper = sql.upper()
        
        # Check expected patterns
        missing_patterns = []
        for pattern in test.expected_sql_patterns:
            if pattern.upper() not in sql_upper:
                missing_patterns.append(pattern)
        
        if missing_patterns:
            issues.append(f"Missing patterns: {missing_patterns}")
        
        # Check forbidden patterns
        if test.forbidden_patterns:
            found_forbidden = []
            for pattern in test.forbidden_patterns:
                if pattern.upper() in sql_upper:
                    found_forbidden.append(pattern)
            if found_forbidden:
                issues.append(f"Found forbidden: {found_forbidden}")
        
        # Check deterministic path
        if test.require_deterministic and used_deterministic is False:
            issues.append("Used LLM fallback instead of deterministic")
        
        # Determine status
        if not issues:
            return TestStatus.PASS, "All checks passed"
        elif len(issues) == 1 and "LLM fallback" in issues[0]:
            return TestStatus.WARN, issues[0]
        else:
            return TestStatus.FAIL, "; ".join(issues)
    
    def _print_result(self, result: TestResult):
        """Print a single test result."""
        print(f"Evo {result.evolution}: {result.name}")
        print(f"  Query: \"{result.query}\"")
        print(f"  Status: {result.status.value}")
        print(f"  Details: {result.details}")
        if result.sql_generated:
            # Truncate long SQL
            sql_preview = result.sql_generated[:100]
            if len(result.sql_generated) > 100:
                sql_preview += "..."
            print(f"  SQL: {sql_preview}")
        print()
    
    def _print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        
        # Count by status
        by_status = {}
        for result in self.results:
            status = result.status.name
            by_status[status] = by_status.get(status, 0) + 1
        
        for status, count in by_status.items():
            print(f"  {status}: {count}")
        
        # Count by evolution
        print("\nBy Evolution:")
        by_evo = {}
        for result in self.results:
            evo = result.evolution
            if evo not in by_evo:
                by_evo[evo] = {"pass": 0, "fail": 0, "warn": 0}
            if result.status == TestStatus.PASS:
                by_evo[evo]["pass"] += 1
            elif result.status == TestStatus.FAIL:
                by_evo[evo]["fail"] += 1
            else:
                by_evo[evo]["warn"] += 1
        
        for evo in sorted(by_evo.keys()):
            counts = by_evo[evo]
            status_str = "✅" if counts["fail"] == 0 else "❌"
            print(f"  Evo {evo}: {status_str} ({counts['pass']} pass, {counts['fail']} fail, {counts['warn']} warn)")
        
        # Overall
        total = len(self.results)
        passed = by_status.get("PASS", 0)
        failed = by_status.get("FAIL", 0)
        
        print(f"\nTotal: {passed}/{total} passed ({100*passed//total}%)")
        
        if failed == 0:
            print("\n🎉 ALL TESTS PASSED!")
        else:
            print(f"\n⚠️  {failed} test(s) failed - review above for details")
        
        print("=" * 60)


# =============================================================================
# QUICK LOCAL TEST (no API needed)
# =============================================================================

async def run_local_syntax_check():
    """Quick syntax check of the intelligence modules."""
    print("\n" + "=" * 60)
    print("LOCAL SYNTAX CHECK")
    print("=" * 60)
    
    modules_to_check = [
        ("relationship_resolver", "utils.intelligence.relationship_resolver"),
        ("sql_assembler", "utils.intelligence.sql_assembler"),
        ("term_index", "utils.intelligence.term_index"),
        ("engine", "utils.intelligence.engine"),
        ("semantic_vocabulary", "utils.semantic_vocabulary"),
    ]
    
    all_passed = True
    
    for name, module_path in modules_to_check:
        try:
            __import__(module_path, fromlist=[''])
            print(f"  ✅ {name}")
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            all_passed = False
    
    if all_passed:
        print("\n✅ All modules import successfully")
    else:
        print("\n❌ Some modules failed to import")
    
    return all_passed


# =============================================================================
# MAIN
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description="SQL Evolutions Regression Test")
    parser.add_argument("--project", "-p", help="Project ID to test against")
    parser.add_argument("--base-url", "-u", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--syntax-only", "-s", action="store_true", help="Only run syntax/import checks")
    parser.add_argument("--evolution", "-e", type=int, help="Only test specific evolution (1-10)")
    
    args = parser.parse_args()
    
    # Always run syntax check first
    syntax_ok = await run_local_syntax_check()
    
    if args.syntax_only:
        sys.exit(0 if syntax_ok else 1)
    
    if not args.project:
        print("\n⚠️  No project specified. Use --project <id> to run full tests.")
        print("   Run with --syntax-only to just check module imports.")
        sys.exit(0)
    
    # Filter test cases if specific evolution requested
    global TEST_CASES
    if args.evolution:
        TEST_CASES = [t for t in TEST_CASES if t.evolution == args.evolution]
        print(f"\nFiltered to Evolution {args.evolution} tests only")
    
    # Run full tests
    tester = SQLEvolutionTester(
        project_id=args.project,
        base_url=args.base_url
    )
    
    results = await tester.run_all_tests()
    
    # Exit with error code if any failures
    failures = sum(1 for r in results if r.status == TestStatus.FAIL)
    sys.exit(1 if failures > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())
