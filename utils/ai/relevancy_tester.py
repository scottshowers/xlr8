"""
Relevancy Testing Framework - Day 1
Test suite to measure improvements in answer quality and relevancy
"""

import json
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class RelevancyTester:
    """Test framework to measure answer quality."""
    
    def __init__(self, questions_path: str = "data/questions_database.json"):
        self.questions_path = Path(questions_path)
        self.test_results = []
    
    def load_test_questions(self, sample_size: int = 10) -> List[Dict[str, Any]]:
        """
        Load a sample of questions for testing.
        
        Focus on questions likely to have answers in customer docs:
        - Company Structure questions
        - Payroll Policy questions
        - Benefits questions
        """
        
        with open(self.questions_path, 'r') as f:
            data = json.load(f)
        
        questions = data.get('questions', [])
        
        # Priority categories for testing
        priority_categories = [
            'Company Structure',
            'Payroll Policy',
            'Benefits',
            'Time and Attendance'
        ]
        
        # Get questions from priority categories
        test_questions = []
        for category in priority_categories:
            category_questions = [q for q in questions if q.get('category') == category]
            test_questions.extend(category_questions[:3])  # 3 per category
        
        # If we need more, add required questions
        if len(test_questions) < sample_size:
            required = [q for q in questions if q.get('required') and q not in test_questions]
            test_questions.extend(required[:sample_size - len(test_questions)])
        
        return test_questions[:sample_size]
    
    def evaluate_answer(self, question: Dict[str, Any], answer: str, confidence: float, sources: List[str]) -> Dict[str, Any]:
        """
        Evaluate answer quality on multiple dimensions.
        
        Returns score dict with:
        - relevancy: Is answer relevant to question? (0-10)
        - completeness: Does it fully answer the question? (0-10)
        - specificity: Specific details vs vague? (0-10)
        - source_quality: Are sources appropriate? (0-10)
        """
        
        scores = {
            'question_id': question['id'],
            'question': question['question'],
            'category': question['category'],
            'answer_length': len(answer),
            'confidence': confidence,
            'num_sources': len(sources),
            'sources': sources
        }
        
        # Auto-checks
        scores['has_specific_values'] = self._has_specific_values(answer)
        scores['mentions_ukg_terms'] = self._mentions_ukg_terms(answer)
        scores['says_no_info'] = 'no information' in answer.lower() or 'not contain' in answer.lower()
        scores['answer_too_short'] = len(answer) < 50
        scores['answer_looks_good'] = (
            len(answer) > 100 and 
            confidence > 0.7 and 
            len(sources) > 0 and
            not scores['says_no_info']
        )
        
        return scores
    
    def _has_specific_values(self, answer: str) -> bool:
        """Check if answer contains specific values (numbers, names, dates)."""
        import re
        
        # Look for patterns indicating specificity
        patterns = [
            r'\d+',  # Numbers
            r'[A-Z][a-z]+ [A-Z][a-z]+',  # Proper names
            r'\d{2}/\d{2}/\d{4}',  # Dates
            r'\$[\d,]+',  # Money
            r'\d+%',  # Percentages
        ]
        
        for pattern in patterns:
            if re.search(pattern, answer):
                return True
        return False
    
    def _mentions_ukg_terms(self, answer: str) -> bool:
        """Check if answer uses UKG terminology."""
        ukg_terms = [
            'component company',
            'pay group',
            'pay class',
            'fein',
            'accrual',
            'timecard',
            'benefit plan',
            'eligibility',
            'pay frequency'
        ]
        
        answer_lower = answer.lower()
        return any(term in answer_lower for term in ukg_terms)
    
    def run_test_suite(self, analyze_function, rag_handler) -> Dict[str, Any]:
        """
        Run full test suite and return results.
        
        Args:
            analyze_function: Function that takes (question, rag_handler) and returns result
            rag_handler: RAG handler instance
        """
        
        test_questions = self.load_test_questions(10)
        results = []
        
        print(f"\n{'='*80}")
        print(f"RUNNING RELEVANCY TEST SUITE - {len(test_questions)} questions")
        print(f"{'='*80}\n")
        
        for i, question in enumerate(test_questions, 1):
            print(f"Testing {i}/{len(test_questions)}: {question['id']} - {question['question'][:60]}...")
            
            try:
                result = analyze_function(question, rag_handler)
                
                eval_result = self.evaluate_answer(
                    question=question,
                    answer=result.get('answer', ''),
                    confidence=result.get('confidence', 0),
                    sources=result.get('sources', [])
                )
                
                results.append(eval_result)
                
                # Quick feedback
                if eval_result['answer_looks_good']:
                    print(f"  ✅ Looks good! (conf: {eval_result['confidence']*100:.0f}%)")
                elif eval_result['says_no_info']:
                    print(f"  ⚠️  No info found")
                else:
                    print(f"  ⚠️  Needs review (conf: {eval_result['confidence']*100:.0f}%)")
                
            except Exception as e:
                print(f"  ❌ Error: {e}")
                results.append({
                    'question_id': question['id'],
                    'error': str(e)
                })
        
        # Calculate summary stats
        summary = self._calculate_summary(results)
        
        print(f"\n{'='*80}")
        print("TEST RESULTS SUMMARY")
        print(f"{'='*80}")
        print(f"Total Questions: {summary['total']}")
        print(f"Looks Good: {summary['looks_good']} ({summary['looks_good_pct']:.0f}%)")
        print(f"No Info Found: {summary['no_info']} ({summary['no_info_pct']:.0f}%)")
        print(f"Needs Review: {summary['needs_review']} ({summary['needs_review_pct']:.0f}%)")
        print(f"")
        print(f"Avg Confidence: {summary['avg_confidence']*100:.0f}%")
        print(f"Avg Answer Length: {summary['avg_length']:.0f} chars")
        print(f"Using UKG Terms: {summary['ukg_terms_pct']:.0f}%")
        print(f"Has Specific Values: {summary['specific_values_pct']:.0f}%")
        print(f"{'='*80}\n")
        
        return {
            'results': results,
            'summary': summary
        }
    
    def _calculate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics."""
        
        valid_results = [r for r in results if 'error' not in r]
        
        if not valid_results:
            return {'error': 'No valid results'}
        
        total = len(valid_results)
        looks_good = sum(1 for r in valid_results if r.get('answer_looks_good'))
        no_info = sum(1 for r in valid_results if r.get('says_no_info'))
        needs_review = total - looks_good - no_info
        
        return {
            'total': total,
            'looks_good': looks_good,
            'looks_good_pct': (looks_good / total * 100) if total > 0 else 0,
            'no_info': no_info,
            'no_info_pct': (no_info / total * 100) if total > 0 else 0,
            'needs_review': needs_review,
            'needs_review_pct': (needs_review / total * 100) if total > 0 else 0,
            'avg_confidence': sum(r.get('confidence', 0) for r in valid_results) / total,
            'avg_length': sum(r.get('answer_length', 0) for r in valid_results) / total,
            'ukg_terms_pct': sum(1 for r in valid_results if r.get('mentions_ukg_terms')) / total * 100,
            'specific_values_pct': sum(1 for r in valid_results if r.get('has_specific_values')) / total * 100
        }
    
    def compare_before_after(self, before_results: Dict, after_results: Dict):
        """Compare test results before and after optimization."""
        
        print(f"\n{'='*80}")
        print("BEFORE vs AFTER COMPARISON")
        print(f"{'='*80}\n")
        
        before = before_results['summary']
        after = after_results['summary']
        
        metrics = [
            ('Looks Good %', 'looks_good_pct'),
            ('Avg Confidence %', 'avg_confidence', 100),
            ('UKG Terms %', 'ukg_terms_pct'),
            ('Specific Values %', 'specific_values_pct'),
        ]
        
        for label, key, *multiplier in metrics:
            mult = multiplier[0] if multiplier else 1
            before_val = before.get(key, 0) * mult
            after_val = after.get(key, 0) * mult
            delta = after_val - before_val
            delta_pct = (delta / before_val * 100) if before_val > 0 else 0
            
            arrow = "📈" if delta > 0 else "📉" if delta < 0 else "➡️"
            
            print(f"{label:20} {before_val:6.1f} → {after_val:6.1f}  {arrow} {delta:+.1f} ({delta_pct:+.0f}%)")
        
        print(f"{'='*80}\n")


# Helper function to run quick test
def quick_test(analyze_function, rag_handler, num_questions: int = 5):
    """Run a quick test with specified number of questions."""
    tester = RelevancyTester()
    test_questions = tester.load_test_questions(num_questions)
    
    results = []
    for question in test_questions:
        result = analyze_function(question, rag_handler)
        eval_result = tester.evaluate_answer(
            question,
            result.get('answer', ''),
            result.get('confidence', 0),
            result.get('sources', [])
        )
        results.append(eval_result)
    
    summary = tester._calculate_summary(results)
    return {'results': results, 'summary': summary}
