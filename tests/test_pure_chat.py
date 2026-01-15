#!/usr/bin/env python3
"""
Pure Chat Classification Tester
================================

Quick verification that Pure Chat detection works correctly.
Run this to validate the classifier before deploying.

Usage:
    python test_pure_chat.py
"""

# Pure Chat patterns (from engine.py)
PURE_CHAT_PATTERNS = [
    'what is a ', 'what is an ', 'what are ',
    'what does ', 'what do ',
    'how does ', 'how do ',
    'explain ', 'define ', 'describe ',
    'tell me about ', 'what\'s the difference between',
    'what is the purpose of ', 'why would ',
    'when should ', 'when would ',
    'can you explain ', 'help me understand ',
]

# Data indicators (from engine.py)
DATA_INDICATORS = [
    'how many', 'count', 'total', 'sum', 'average',
    'list ', 'show ', 'display ', 'give me ', 'get me ',
    'what are the ', 'what are our ', 'what are my ',
    'do we have', 'do i have', 'does our',
    ' in texas', ' in california', ' in new york', ' in florida',
    'employees in ', 'workers in ', 'people in ',
    'for john', 'for employee', 'for department',
    'our ', 'my ', 'we have', 'our company',
    'table', 'report', 'spreadsheet', 'export',
    'compare our', 'versus our', 'vs our',
]


def is_pure_chat(question: str) -> bool:
    """Check if question is Pure Chat (definitional, no data needed)."""
    q_lower = question.lower()
    
    # Must have definitional pattern
    has_pattern = any(p in q_lower for p in PURE_CHAT_PATTERNS)
    if not has_pattern:
        return False
    
    # Must NOT have data indicator
    has_data = any(d in q_lower for d in DATA_INDICATORS)
    return not has_data


# Test cases
TEST_CASES = [
    # Should be Pure Chat (definitional, no data)
    ("what is a benefit class?", True, "Basic definition"),
    ("how does UKG handle accruals?", True, "System concept"),
    ("explain garnishments", True, "Explain keyword"),
    ("what's the difference between regular and overtime?", True, "Comparison concept"),
    ("define deduction code", True, "Define keyword"),
    ("what is an earning code?", True, "Definition with 'an'"),
    ("how do accrual balances work?", True, "How do question"),
    ("tell me about benefit eligibility", True, "Tell me about"),
    ("when should I use a pay adjustment?", True, "When should"),
    
    # Should NOT be Pure Chat (needs data)
    ("what is the headcount in Texas?", False, "Has 'in texas'"),
    ("how many employees do we have?", False, "Has 'how many'"),
    ("what are our deduction codes?", False, "Has 'our'"),
    ("list all earning codes", False, "Has 'list '"),
    ("show employees in California", False, "Has 'employees in'"),
    ("what is our company code?", False, "Has 'our'"),
    ("how many people work in New York?", False, "Has 'how many' + location"),
    ("give me a report of deductions", False, "Has 'give me' + 'report'"),
    ("what are the benefit classes we have?", False, "Has 'we have'"),
    ("export the employee table", False, "Has 'export' + 'table'"),
    
    # Edge cases - should be Pure Chat
    ("what does FICA mean?", True, "Acronym definition"),
    ("how does the withholding calculation work?", True, "Process explanation"),
    ("explain the difference between gross and net pay", True, "Concept comparison"),
    
    # Edge cases - should NOT be Pure Chat
    ("do we have any terminated employees?", False, "Has 'do we have'"),
    ("what are my pending deductions?", False, "Has 'my '"),
]


def run_tests():
    """Run all test cases and report results."""
    print("=" * 60)
    print("PURE CHAT CLASSIFICATION TESTS")
    print("=" * 60)
    print()
    
    passed = 0
    failed = 0
    
    for question, expected, reason in TEST_CASES:
        result = is_pure_chat(question)
        status = "✅" if result == expected else "❌"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
        
        expected_str = "PURE" if expected else "DATA"
        actual_str = "PURE" if result else "DATA"
        
        print(f"{status} {expected_str:4} | {actual_str:4} | {question[:50]}")
        if result != expected:
            print(f"   ⚠️  Reason: {reason}")
    
    print()
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
