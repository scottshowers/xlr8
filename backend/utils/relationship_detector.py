"""
Relationship Detector - Auto-detect table relationships using rules + local LLM.

Deploy to: backend/utils/relationship_detector.py

Features:
- Rule-based exact/normalized matching (free, instant)
- Fuzzy matching with Levenshtein + token overlap (free, instant)
- Semantic type detection from column name patterns (free, instant)
- Local LLM for ambiguous pairs (free, ~2-5 sec)
- Confidence scores for all matches
- needs_review flag for uncertain matches
"""

import re
from difflib import SequenceMatcher
from typing import List, Dict, Tuple, Optional
import json
import logging

logger = logging.getLogger(__name__)

# Common patterns that indicate column purpose
SEMANTIC_PATTERNS = {
    'employee_id': [
        r'^emp.*id$', r'^ee.*num', r'^employee.*number', r'^worker.*id', 
        r'^person.*id', r'^emp.*num', r'^emp.*no$', r'^ee.*id$',
        r'^employee.*id$', r'^staff.*id', r'^associate.*id'
    ],
    'company_code': [
        r'^comp.*code', r'^co.*code', r'^company.*id', r'^org.*code',
        r'^entity.*code', r'^legal.*entity', r'^business.*unit'
    ],
    'department': [
        r'dept', r'department', r'^div.*code', r'division', r'cost.*center',
        r'home.*dept', r'work.*dept'
    ],
    'job_code': [
        r'^job.*code', r'^job.*id', r'^position.*code', r'^title.*code',
        r'^job.*class', r'^occupation'
    ],
    'location': [
        r'^loc.*code', r'^location', r'^work.*loc', r'^site.*code',
        r'^branch.*code', r'^office.*code'
    ],
    'date': [
        r'.*_date$', r'.*_dt$', r'^date_.*', r'.*_on$', r'.*_when$',
        r'^eff.*date', r'^effective', r'^start.*date', r'^end.*date',
        r'^hire.*date', r'^term.*date', r'^birth.*date', r'^check.*date'
    ],
    'amount': [
        r'.*_amt$', r'.*_amount$', r'.*_pay$', r'^gross.*', r'^net.*', 
        r'^total.*', r'.*_sum$', r'^salary', r'^wage', r'^bonus'
    ],
    'code': [
        r'.*_code$', r'.*_cd$', r'.*_type$', r'.*_key$'
    ],
    'rate': [
        r'.*_rate$', r'.*_rt$', r'^hourly.*', r'^annual.*', r'^pay.*rate',
        r'^comp.*rate'
    ],
    'hours': [
        r'.*_hrs$', r'.*_hours$', r'^hours.*', r'^hrs_.*', r'^worked.*hrs'
    ],
    'status': [
        r'.*_status$', r'.*_stat$', r'^active.*', r'^status.*', 
        r'^emp.*status', r'^employment.*status'
    ],
    'name': [
        r'.*_name$', r'^first.*', r'^last.*', r'^full.*name', 
        r'^fname', r'^lname', r'^middle.*'
    ],
    'ssn': [
        r'^ssn', r'^social.*sec', r'^ss_num', r'^tax.*id'
    ],
    'email': [
        r'^email', r'^e_mail', r'.*_email$'
    ],
    'phone': [
        r'^phone', r'^tel', r'^mobile', r'^cell', r'.*_phone$'
    ],
    'address': [
        r'^address', r'^street', r'^city', r'^state', r'^zip', r'^postal'
    ],
    'earning_code': [
        r'^earn.*code', r'^earning.*type', r'^pay.*code', r'^wage.*type'
    ],
    'deduction_code': [
        r'^ded.*code', r'^deduction.*type', r'^deduct.*code'
    ],
    'tax_code': [
        r'^tax.*code', r'^tax.*type', r'^withhold'
    ],
}

# Key fields that should be used for relationships (JOINs)
KEY_SEMANTIC_TYPES = [
    'employee_id', 'company_code', 'department', 'job_code', 
    'location', 'earning_code', 'deduction_code', 'tax_code'
]


def normalize_column_name(name: str) -> str:
    """Normalize column name for comparison."""
    if not name:
        return ''
    # Lowercase, remove special chars, normalize separators
    normalized = name.lower()
    normalized = re.sub(r'[^a-z0-9]', '_', normalized)
    normalized = re.sub(r'_+', '_', normalized)
    normalized = normalized.strip('_')
    return normalized


def get_column_tokens(name: str) -> set:
    """Extract meaningful tokens from column name."""
    normalized = normalize_column_name(name)
    tokens = set(normalized.split('_'))
    # Remove common noise tokens
    noise = {'id', 'num', 'no', 'code', 'cd', 'key', 'the', 'a', 'an'}
    return tokens - noise


def get_semantic_type(column_name: str) -> Tuple[str, float]:
    """Detect semantic type from column name patterns."""
    normalized = normalize_column_name(column_name)
    
    for sem_type, patterns in SEMANTIC_PATTERNS.items():
        for pattern in patterns:
            if re.match(pattern, normalized) or re.search(pattern, normalized):
                # Higher confidence for exact pattern match at start
                confidence = 0.95 if re.match(pattern, normalized) else 0.85
                return sem_type, confidence
    
    return 'unknown', 0.0


def similarity_score(name1: str, name2: str) -> float:
    """Calculate similarity between two column names."""
    n1 = normalize_column_name(name1)
    n2 = normalize_column_name(name2)
    
    if not n1 or not n2:
        return 0.0
    
    # Exact match after normalization
    if n1 == n2:
        return 1.0
    
    # Sequence matcher (handles insertions/deletions)
    seq_score = SequenceMatcher(None, n1, n2).ratio()
    
    # Token overlap (handles word reordering)
    tokens1 = get_column_tokens(name1)
    tokens2 = get_column_tokens(name2)
    
    if tokens1 and tokens2:
        intersection = tokens1 & tokens2
        union = tokens1 | tokens2
        # Jaccard similarity
        token_score = len(intersection) / len(union) if union else 0
        # Bonus for having the important tokens match
        important_tokens = {'emp', 'employee', 'dept', 'department', 'company', 'job', 'loc'}
        important_match = bool(intersection & important_tokens)
        if important_match:
            token_score = min(1.0, token_score + 0.2)
    else:
        token_score = 0
    
    # Combined score - take the best
    return max(seq_score, token_score)


class RelationshipDetector:
    """Detect relationships between tables in a project."""
    
    def __init__(self, llm_client=None):
        """
        Initialize detector.
        
        Args:
            llm_client: Optional local LLM client with .generate(prompt) method
        """
        self.llm = llm_client
    
    def analyze_project(self, tables: List[Dict]) -> Dict:
        """
        Analyze all tables in a project and detect relationships.
        
        Args:
            tables: List of table dictionaries with structure:
                {
                    "table_name": "payroll_data",
                    "columns": ["Employee_ID", "Dept_Code", ...] or 
                               [{"name": "Employee_ID", "type": "TEXT"}, ...]
                }
        
        Returns:
            {
                "relationships": [...],
                "semantic_types": [...],
                "unmatched_columns": [...]
            }
        """
        relationships = []
        semantic_types = []
        uncertain_pairs = []
        
        logger.info(f"Analyzing {len(tables)} tables for relationships")
        
        # Step 1: Detect semantic types for all columns
        for table in tables:
            table_name = table.get('table_name', table.get('name', 'unknown'))
            columns = table.get('columns', [])
            
            for col in columns:
                col_name = col if isinstance(col, str) else col.get('name', '')
                if not col_name:
                    continue
                    
                sem_type, confidence = get_semantic_type(col_name)
                if sem_type != 'unknown':
                    semantic_types.append({
                        'table': table_name,
                        'column': col_name,
                        'type': sem_type,
                        'confidence': round(confidence, 2)
                    })
        
        logger.info(f"Found {len(semantic_types)} semantic type matches")
        
        # Step 2: Find relationships by comparing columns across tables
        for i, table1 in enumerate(tables):
            table1_name = table1.get('table_name', table1.get('name', 'unknown'))
            cols1 = table1.get('columns', [])
            
            for table2 in tables[i+1:]:
                table2_name = table2.get('table_name', table2.get('name', 'unknown'))
                cols2 = table2.get('columns', [])
                
                for col1 in cols1:
                    col1_name = col1 if isinstance(col1, str) else col1.get('name', '')
                    if not col1_name:
                        continue
                    
                    for col2 in cols2:
                        col2_name = col2 if isinstance(col2, str) else col2.get('name', '')
                        if not col2_name:
                            continue
                        
                        score = similarity_score(col1_name, col2_name)
                        
                        if score >= 0.85:
                            # High confidence - auto-accept
                            relationships.append({
                                'source_table': table1_name,
                                'source_column': col1_name,
                                'target_table': table2_name,
                                'target_column': col2_name,
                                'confidence': round(score, 2),
                                'method': 'exact' if score == 1.0 else 'fuzzy',
                                'needs_review': False,
                                'confirmed': False
                            })
                        elif score >= 0.55:
                            # Medium confidence - queue for LLM review or mark uncertain
                            uncertain_pairs.append({
                                'table1': table1_name,
                                'col1': col1_name,
                                'table2': table2_name,
                                'col2': col2_name,
                                'score': score
                            })
        
        logger.info(f"Found {len(relationships)} high-confidence matches, {len(uncertain_pairs)} uncertain")
        
        # Step 3: Use local LLM to resolve uncertain pairs (if available)
        if uncertain_pairs and self.llm:
            try:
                llm_results = self._llm_analyze_pairs(uncertain_pairs)
                for result in llm_results:
                    relationships.append({
                        'source_table': result['table1'],
                        'source_column': result['col1'],
                        'target_table': result['table2'],
                        'target_column': result['col2'],
                        'confidence': round(result['confidence'], 2),
                        'method': 'llm',
                        'needs_review': result['confidence'] < 0.8,
                        'confirmed': False,
                        'llm_reason': result.get('reason', '')
                    })
                logger.info(f"LLM confirmed {len(llm_results)} additional relationships")
            except Exception as e:
                logger.warning(f"LLM analysis failed: {e}, marking pairs as needs_review")
                for pair in uncertain_pairs:
                    relationships.append({
                        'source_table': pair['table1'],
                        'source_column': pair['col1'],
                        'target_table': pair['table2'],
                        'target_column': pair['col2'],
                        'confidence': round(pair['score'], 2),
                        'method': 'fuzzy',
                        'needs_review': True,
                        'confirmed': False
                    })
        elif uncertain_pairs:
            # No LLM available - mark as needs review
            for pair in uncertain_pairs:
                relationships.append({
                    'source_table': pair['table1'],
                    'source_column': pair['col1'],
                    'target_table': pair['table2'],
                    'target_column': pair['col2'],
                    'confidence': round(pair['score'], 2),
                    'method': 'fuzzy',
                    'needs_review': True,
                    'confirmed': False
                })
        
        # Step 4: Also suggest relationships based on semantic type matches
        relationships = self._add_semantic_relationships(relationships, semantic_types)
        
        # Step 5: Find unmatched key columns (might need manual mapping)
        unmatched = self._find_unmatched_keys(tables, relationships, semantic_types)
        
        # Deduplicate relationships
        relationships = self._deduplicate_relationships(relationships)
        
        return {
            'relationships': relationships,
            'semantic_types': semantic_types,
            'unmatched_columns': unmatched
        }
    
    def _add_semantic_relationships(
        self, 
        relationships: List[Dict], 
        semantic_types: List[Dict]
    ) -> List[Dict]:
        """Add relationships based on matching semantic types."""
        
        # Build set of existing pairs
        existing_pairs = set()
        for r in relationships:
            pair = tuple(sorted([
                f"{r['source_table']}.{r['source_column']}",
                f"{r['target_table']}.{r['target_column']}"
            ]))
            existing_pairs.add(pair)
        
        # Group columns by semantic type
        by_type = {}
        for st in semantic_types:
            key = st['type']
            if key not in by_type:
                by_type[key] = []
            by_type[key].append(st)
        
        # Connect columns with same key semantic type
        for sem_type in KEY_SEMANTIC_TYPES:
            cols = by_type.get(sem_type, [])
            for i, col1 in enumerate(cols):
                for col2 in cols[i+1:]:
                    if col1['table'] != col2['table']:
                        pair = tuple(sorted([
                            f"{col1['table']}.{col1['column']}",
                            f"{col2['table']}.{col2['column']}"
                        ]))
                        
                        if pair not in existing_pairs:
                            confidence = min(col1['confidence'], col2['confidence']) * 0.85
                            relationships.append({
                                'source_table': col1['table'],
                                'source_column': col1['column'],
                                'target_table': col2['table'],
                                'target_column': col2['column'],
                                'confidence': round(confidence, 2),
                                'method': 'semantic',
                                'needs_review': True,
                                'confirmed': False,
                                'semantic_type': sem_type
                            })
                            existing_pairs.add(pair)
        
        return relationships
    
    def _find_unmatched_keys(
        self,
        tables: List[Dict],
        relationships: List[Dict],
        semantic_types: List[Dict]
    ) -> List[Dict]:
        """Find key columns that don't have any relationships."""
        
        # Columns that are in relationships
        matched = set()
        for r in relationships:
            matched.add(f"{r['source_table']}.{r['source_column']}")
            matched.add(f"{r['target_table']}.{r['target_column']}")
        
        # Find key semantic type columns not in relationships
        unmatched = []
        for st in semantic_types:
            if st['type'] in KEY_SEMANTIC_TYPES:
                key = f"{st['table']}.{st['column']}"
                if key not in matched:
                    unmatched.append({
                        'table': st['table'],
                        'column': st['column'],
                        'semantic_type': st['type'],
                        'confidence': st['confidence']
                    })
        
        return unmatched
    
    def _deduplicate_relationships(self, relationships: List[Dict]) -> List[Dict]:
        """Remove duplicate relationships, keeping highest confidence."""
        seen = {}
        for r in relationships:
            # Create canonical key (sorted to handle A->B and B->A)
            pair = tuple(sorted([
                f"{r['source_table']}.{r['source_column']}",
                f"{r['target_table']}.{r['target_column']}"
            ]))
            
            if pair not in seen or r['confidence'] > seen[pair]['confidence']:
                seen[pair] = r
        
        return list(seen.values())
    
    def _llm_analyze_pairs(self, pairs: List[Dict]) -> List[Dict]:
        """Use local LLM to analyze uncertain column pairs."""
        if not pairs or not self.llm:
            return []
        
        # Batch in groups of 15 to keep prompt manageable
        batch_size = 15
        all_results = []
        
        for batch_start in range(0, len(pairs), batch_size):
            batch = pairs[batch_start:batch_start + batch_size]
            
            prompt = """You are analyzing database column names to determine if they refer to the same data.
For each pair, determine if they likely represent the same field (could be JOINed).

Pairs to analyze:
"""
            for i, pair in enumerate(batch):
                prompt += f"{i+1}. '{pair['col1']}' (from {pair['table1']}) vs '{pair['col2']}' (from {pair['table2']})\n"
            
            prompt += """
Return ONLY a JSON array with your assessment. No other text.
Format:
[
  {"pair": 1, "same_data": true, "confidence": 0.85, "reason": "Both appear to be employee identifiers"},
  {"pair": 2, "same_data": false, "confidence": 0.90, "reason": "Different concepts - department vs division level"}
]
"""
            try:
                response = self.llm.generate(prompt, max_tokens=1500)
                
                # Clean response - extract JSON
                response = response.strip()
                if response.startswith('```'):
                    response = re.sub(r'^```\w*\n?', '', response)
                    response = re.sub(r'\n?```$', '', response)
                
                results = json.loads(response)
                
                for r in results:
                    idx = r.get('pair', 0) - 1
                    if 0 <= idx < len(batch) and r.get('same_data'):
                        all_results.append({
                            'table1': batch[idx]['table1'],
                            'col1': batch[idx]['col1'],
                            'table2': batch[idx]['table2'],
                            'col2': batch[idx]['col2'],
                            'confidence': r.get('confidence', 0.7),
                            'reason': r.get('reason', '')
                        })
                        
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LLM response: {e}")
            except Exception as e:
                logger.warning(f"LLM batch analysis failed: {e}")
        
        return all_results


# Convenience function for router
async def analyze_project_relationships(
    project_name: str, 
    tables: List[Dict], 
    llm_client=None
) -> Dict:
    """
    Main entry point for relationship detection.
    
    Args:
        project_name: Project identifier
        tables: List of table schemas
        llm_client: Optional LLM client for ambiguous matches
    
    Returns:
        Analysis results with relationships, semantic types, and stats
    """
    detector = RelationshipDetector(llm_client)
    result = detector.analyze_project(tables)
    
    return {
        'project': project_name,
        'relationships': result['relationships'],
        'semantic_types': result['semantic_types'],
        'unmatched_columns': result['unmatched_columns'],
        'stats': {
            'tables_analyzed': len(tables),
            'columns_analyzed': sum(len(t.get('columns', [])) for t in tables),
            'relationships_found': len(result['relationships']),
            'high_confidence': sum(1 for r in result['relationships'] if r['confidence'] >= 0.85),
            'needs_review': sum(1 for r in result['relationships'] if r.get('needs_review')),
            'semantic_types_detected': len(result['semantic_types']),
            'unmatched_keys': len(result['unmatched_columns'])
        }
    }
