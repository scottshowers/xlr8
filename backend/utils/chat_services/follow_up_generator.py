"""
Follow-Up Generator
===================

Guide the conversation like a real consultant.

After answering a question, suggest relevant follow-up questions
to help the user dig deeper into their data.

Usage:
    generator = FollowUpGenerator(schema)
    suggestions = generator.generate(
        query_type='count',
        question='How many employees?',
        result={'count': 847}
    )
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class FollowUpGenerator:
    """
    Suggested Follow-Up Generator - Guide the conversation like a consultant.
    
    After answering a question, suggest relevant follow-up questions
    to help the user dig deeper into their data.
    """
    
    # Follow-up templates based on query type
    FOLLOW_UP_TEMPLATES = {
        'count': [
            "Break this down by {dimension}",
            "How has this changed over the last {time_period}?",
            "Which {entity} has the most?",
            "Compare this to {benchmark}",
        ],
        'list': [
            "Filter this to show only {filter_value}",
            "Sort by {sort_column}",
            "Show me more details about {entity}",
            "Export this to Excel",
        ],
        'sum': [
            "What's the average instead?",
            "Break this down by {dimension}",
            "Show the top 10 contributors",
            "How does this compare to budget?",
        ],
        'analysis': [
            "What's driving this trend?",
            "Are there any outliers?",
            "How does this compare to industry benchmarks?",
            "What actions should we take based on this?",
        ],
        'general': [
            "Tell me more about {entity}",
            "What else should I know about this?",
            "Are there any related issues?",
            "Show me the underlying data",
        ]
    }
    
    # Common dimensions for breakdowns
    COMMON_DIMENSIONS = [
        'department', 'location', 'company', 'pay_group', 
        'job_title', 'employment_type', 'hire_year'
    ]
    
    def __init__(self, schema: Dict = None):
        self.schema = schema or {}
        self.available_columns = self._extract_columns()
    
    def _extract_columns(self) -> List[str]:
        """Extract all available column names from schema."""
        columns = []
        for table in self.schema.get('tables', []):
            columns.extend(table.get('columns', []))
        return list(set(columns))
    
    def generate(
        self, 
        query_type: str, 
        question: str, 
        result: Dict,
        context: Dict = None
    ) -> List[str]:
        """
        Generate suggested follow-up questions.
        
        Args:
            query_type: Type of query (count, list, sum, analysis, general)
            question: Original question asked
            result: Query result
            context: Additional context
            
        Returns:
            List of suggested follow-up questions
        """
        suggestions = []
        context = context or {}
        
        # Get templates for this query type
        templates = self.FOLLOW_UP_TEMPLATES.get(query_type, self.FOLLOW_UP_TEMPLATES['general'])
        
        # Find relevant dimensions from schema
        available_dimensions = []
        for dim in self.COMMON_DIMENSIONS:
            if any(dim in col.lower() for col in self.available_columns):
                available_dimensions.append(dim.replace('_', ' ').title())
        
        # Generate suggestions
        for template in templates[:4]:  # Max 4 suggestions
            suggestion = template
            
            # Fill in placeholders
            if '{dimension}' in suggestion and available_dimensions:
                suggestion = suggestion.replace('{dimension}', available_dimensions[0])
            elif '{dimension}' in suggestion:
                suggestion = suggestion.replace('{dimension}', 'department')
            
            if '{time_period}' in suggestion:
                suggestion = suggestion.replace('{time_period}', '12 months')
            
            if '{entity}' in suggestion:
                # Try to extract entity from question
                entity = self._extract_entity(question)
                suggestion = suggestion.replace('{entity}', entity)
            
            if '{filter_value}' in suggestion:
                suggestion = suggestion.replace('{filter_value}', 'active employees')
            
            if '{sort_column}' in suggestion:
                suggestion = suggestion.replace('{sort_column}', 'hire date')
            
            if '{benchmark}' in suggestion:
                suggestion = suggestion.replace('{benchmark}', 'last year')
            
            suggestions.append(suggestion)
        
        # Add context-specific suggestions
        if query_type == 'count' and result.get('count', 0) > 100:
            suggestions.append("Show me the top 10 by count")
        
        if 'employee' in question.lower():
            if 'terminated' not in question.lower():
                suggestions.append("Include terminated employees")
            if 'active' not in question.lower():
                suggestions.append("Filter to active employees only")
        
        return suggestions[:5]  # Return max 5 suggestions
    
    def _extract_entity(self, question: str) -> str:
        """Extract the main entity from a question."""
        # Simple extraction - look for common nouns
        entities = ['employees', 'departments', 'locations', 'companies', 'earnings', 'deductions']
        
        question_lower = question.lower()
        for entity in entities:
            if entity in question_lower:
                return entity
        
        return 'this'
