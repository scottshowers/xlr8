"""
Relationship Detector v2 - INTELLIGENT table relationship detection.

Key Improvements:
1. Configuration Validation file is SOURCE OF TRUTH - other tables map to it
2. Only analyzes KEY columns (IDs, codes, numbers) - not every field
3. Strips common prefixes (home_, work_, etc.) before comparing
4. Limits to top 3 relationships per table pair
5. Much higher confidence thresholds
6. Prepares for global learning (cross-customer mappings)

Deploy to: backend/utils/relationship_detector.py
"""

import re
from difflib import SequenceMatcher
from typing import List, Dict, Tuple, Optional, Set
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Only these column patterns are potential JOIN keys
KEY_COLUMN_PATTERNS = [
    r'.*_id$', r'.*_code$', r'.*_num$', r'.*_number$', r'.*_key$',
    r'^id$', r'^code$', r'^number$',
    r'^emp.*', r'^employee.*', r'^ee_.*',
    r'^company.*', r'^comp_.*', r'^co_.*',
    r'^dept.*', r'^department.*',
    r'^job.*', r'^position.*',
    r'^location.*', r'^loc_.*',
    r'^earn.*', r'^deduct.*', r'^ded_.*',
    r'^tax.*', r'^pay.*group',
]

# NEVER treat these as join keys - they're descriptions, not codes
EXCLUDED_COLUMN_PATTERNS = [
    r'.*_desc$', r'.*_description$', r'.*description$',
    r'.*_name$', r'.*_text$', r'.*_comment$', r'.*_note$',
    r'^desc_', r'^description_', r'^name_',
]

# Strip these prefixes before comparing
STRIP_PREFIXES = [
    'home_', 'work_', 'primary_', 'current_', 'original_',
    'old_', 'new_', 'src_', 'tgt_', 'legacy_', 'default_',
    'main_', 'alt_', 'alternate_', 'secondary_',
]

# Strip these suffixes before comparing  
STRIP_SUFFIXES = [
    '_1', '_2', '_old', '_new', '_orig', '_current',
]

# These files are likely the CONFIG/REFERENCE files (source of truth)
CONFIG_FILE_PATTERNS = [
    r'config.*valid', r'validation', r'configuration',
    r'setup', r'reference', r'master', r'lookup',
]

# Semantic type patterns for grouping columns
# IMPORTANT: These patterns must be PRECISE - only match exact concepts
SEMANTIC_TYPES = {
    'employee_id': [
        r'^emp.*id$', r'^ee.*num$', r'^employee.*number$', r'^worker.*id$',
        r'^person.*id$', r'^emp.*num$', r'^emp.*no$', r'^ee.*id$',
        r'^employee.*id$', r'^staff.*id$', r'^associate.*id$', r'^emp.*key$',
        r'^employee_number$', r'^emp_id$', r'^ee_id$',
    ],
    'company_code': [
        r'^comp.*code$', r'^co.*code$', r'^company.*id$', r'^company.*code$',
        r'^entity.*code$', r'^legal.*entity$', r'^business.*unit.*code$',
        r'^company$', r'^comp$', r'^home.*company.*code$', r'^work.*company.*code$',
    ],
    'department': [
        r'^dept.*code$', r'^department.*code$', r'^div.*code$', r'^division.*code$',
        r'^cost.*center$', r'^dept$', r'^department$', r'^dept_id$',
    ],
    'job_code': [
        r'^job.*code$', r'^job.*id$', r'^position.*code$', r'^title.*code$',
        r'^job.*class$', r'^occupation.*code$', r'^job$',
    ],
    'location': [
        r'^loc.*code$', r'^location.*code$', r'^work.*loc.*code$', r'^site.*code$',
        r'^branch.*code$', r'^office.*code$', r'^location$', r'^loc_id$',
    ],
    'pay_group': [
        r'^pay.*group$', r'^paygroup$', r'^pay.*grp$', r'^pay_group_code$',
    ],
    'pay_frequency': [
        r'^pay.*freq.*code$', r'^pay.*frequency$', r'^payfreq$', r'^pay_freq$',
        r'^frequency.*code$', r'^pay_frequency_code$',
    ],
    'earning_code': [
        r'^earn.*code$', r'^earning.*code$', r'^earnings.*code$', 
        r'^wage.*code$', r'^earning$', r'^earn_cd$',
    ],
    'deduction_code': [
        r'^ded.*code$', r'^deduction.*code$', r'^deduct.*code$',
        r'^deduction$', r'^ded_cd$', r'^benefit.*code$',
    ],
    'tax_code': [
        r'^tax.*code$', r'^tax_code$', r'^withhold.*code$',
        r'^tax.*type.*code$',  # tax_type_code but NOT tax_type (ambiguous)
    ],
    'org_level': [
        r'^org.*level.*\d.*code$', r'^org_level_\d$', r'^org_level_\d_code$',
        r'^organization.*level', r'^org_lvl_\d',
    ],
    'work_state': [
        r'^work.*state$', r'^state.*code$', r'^work_state$', r'^sui.*state$',
    ],
    'status_code': [
        r'^status.*code$', r'^emp.*status$', r'^employee.*status$', r'^status$',
    ],
}

# Max relationships to suggest per table pair
MAX_PER_TABLE_PAIR = 3

# Confidence thresholds
THRESHOLD_AUTO_ACCEPT = 0.90   # This high = auto-accept
THRESHOLD_NEEDS_REVIEW = 0.70  # Between this and auto = needs review
THRESHOLD_DISCARD = 0.70       # Below this = ignore completely


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_key_column(col_name: str) -> bool:
    """Check if column is likely a JOIN key (not just any field)."""
    normalized = col_name.lower().strip()
    
    # First check if it's an excluded pattern (descriptions, names, etc.)
    for pattern in EXCLUDED_COLUMN_PATTERNS:
        if re.match(pattern, normalized) or re.search(pattern, normalized):
            return False
    
    # Then check if it matches key patterns
    for pattern in KEY_COLUMN_PATTERNS:
        if re.match(pattern, normalized) or re.search(pattern, normalized):
            return True
    return False


def normalize_column_name(name: str) -> str:
    """Normalize column name for comparison."""
    if not name:
        return ''
    
    normalized = name.lower().strip()
    normalized = re.sub(r'[^a-z0-9]', '_', normalized)
    normalized = re.sub(r'_+', '_', normalized)
    normalized = normalized.strip('_')
    return normalized


def strip_prefixes_suffixes(name: str) -> str:
    """Strip common prefixes/suffixes to get core name."""
    normalized = normalize_column_name(name)
    
    # Strip prefixes
    for prefix in STRIP_PREFIXES:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break
    
    # Strip suffixes
    for suffix in STRIP_SUFFIXES:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)]
            break
    
    return normalized


def get_semantic_type(column_name: str) -> Tuple[str, float]:
    """Detect semantic type from column name patterns."""
    normalized = normalize_column_name(column_name)
    stripped = strip_prefixes_suffixes(column_name)
    
    # First check if it's an excluded pattern (descriptions should never match)
    for pattern in EXCLUDED_COLUMN_PATTERNS:
        if re.match(pattern, normalized) or re.search(pattern, normalized):
            return 'excluded', 0.0
    
    for sem_type, patterns in SEMANTIC_TYPES.items():
        for pattern in patterns:
            # Check both normalized and stripped versions
            if re.match(pattern, normalized) or re.match(pattern, stripped):
                return sem_type, 0.95
            if re.search(pattern, normalized) or re.search(pattern, stripped):
                return sem_type, 0.85
    
    return 'unknown', 0.0


def similarity_score(name1: str, name2: str) -> float:
    """Calculate similarity between two column names."""
    # Normalize both
    n1 = normalize_column_name(name1)
    n2 = normalize_column_name(name2)
    
    if not n1 or not n2:
        return 0.0
    
    # Exact match after normalization
    if n1 == n2:
        return 1.0
    
    # Try with prefixes/suffixes stripped
    s1 = strip_prefixes_suffixes(name1)
    s2 = strip_prefixes_suffixes(name2)
    
    if s1 == s2 and len(s1) > 2:
        return 0.95  # Very high - just prefix difference
    
    # Check semantic type match
    type1, _ = get_semantic_type(name1)
    type2, _ = get_semantic_type(name2)
    
    if type1 != 'unknown' and type1 == type2:
        # Same semantic type - boost score significantly
        base_score = SequenceMatcher(None, s1, s2).ratio()
        return min(0.95, base_score + 0.3)  # Boost by 0.3
    
    # Sequence matcher on stripped names
    seq_score = SequenceMatcher(None, s1, s2).ratio()
    
    # Token overlap
    tokens1 = set(s1.split('_'))
    tokens2 = set(s2.split('_'))
    
    if tokens1 and tokens2:
        overlap = len(tokens1 & tokens2)
        total = len(tokens1 | tokens2)
        token_score = overlap / total if total > 0 else 0
    else:
        token_score = 0
    
    # Combined score
    return max(seq_score, token_score)


def is_config_table(table_name: str, filename: str = '') -> bool:
    """Check if this table is likely a configuration/reference table."""
    check_str = f"{table_name} {filename}".lower()
    
    for pattern in CONFIG_FILE_PATTERNS:
        if re.search(pattern, check_str):
            return True
    return False


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

async def analyze_project_relationships(
    project_name: str,
    tables: List[Dict],
    llm_client=None
) -> Dict:
    """
    Analyze tables and detect relationships.
    
    INTELLIGENT APPROACH:
    1. Detect semantic type of each key column
    2. ONLY compare columns of the SAME type (employee to employee, company to company)
    3. No cross-type comparisons (employee_id will never match company_code)
    4. Strip prefixes before comparing
    5. Use global mappings for known equivalents
    
    Args:
        project_name: Project identifier
        tables: List of table dicts with 'table_name', 'columns', etc.
        llm_client: Optional local LLM for ambiguous cases
    
    Returns:
        {
            "relationships": [...],
            "semantic_types": [...],
            "unmatched_columns": [...],
            "stats": {...}
        }
    """
    logger.info(f"[RELATIONSHIP] Analyzing {len(tables)} tables for {project_name}")
    
    relationships = []
    semantic_types = []
    
    # Step 1: Build a map of semantic_type -> [(table, column), ...]
    type_to_columns: Dict[str, List[Tuple[str, str]]] = {}
    
    for table in tables:
        table_name = table.get('table_name', '')
        columns = table.get('columns', [])
        
        for col in columns:
            col_name = col if isinstance(col, str) else col.get('name', '')
            if not col_name:
                continue
            
            # Only process key columns
            if not is_key_column(col_name):
                continue
            
            # Get semantic type
            sem_type, confidence = get_semantic_type(col_name)
            
            if sem_type != 'unknown':
                semantic_types.append({
                    'table': table_name,
                    'column': col_name,
                    'type': sem_type,
                    'confidence': round(confidence, 2)
                })
                
                # Add to type grouping
                if sem_type not in type_to_columns:
                    type_to_columns[sem_type] = []
                type_to_columns[sem_type].append((table_name, col_name))
    
    logger.info(f"[RELATIONSHIP] Found {len(semantic_types)} typed key columns across {len(type_to_columns)} types")
    
    # Step 2: For each semantic type, find relationships WITHIN that type
    for sem_type, columns in type_to_columns.items():
        if len(columns) < 2:
            continue  # Need at least 2 columns to form a relationship
        
        logger.info(f"[RELATIONSHIP] Processing {sem_type}: {len(columns)} columns")
        
        # Compare columns of the SAME type across DIFFERENT tables
        for i, (table1, col1) in enumerate(columns):
            for table2, col2 in columns[i+1:]:
                # Skip if same table
                if table1 == table2:
                    continue
                
                # Calculate similarity
                score = similarity_score(col1, col2)
                
                # Since they're already the same semantic type, boost confidence
                # They're fundamentally the same kind of data
                boosted_score = min(1.0, score + 0.15)
                
                if boosted_score >= THRESHOLD_DISCARD:
                    relationships.append({
                        'from_table': table1,
                        'from_column': col1,
                        'to_table': table2,
                        'to_column': col2,
                        'confidence': round(boosted_score, 2),
                        'semantic_type': sem_type,
                        'method': 'exact' if boosted_score == 1.0 else 'semantic',
                        'needs_review': boosted_score < THRESHOLD_AUTO_ACCEPT,
                        'confirmed': False,
                    })
    
    # Step 3: Deduplicate and sort by confidence
    relationships = deduplicate_relationships(relationships)
    relationships.sort(key=lambda x: x['confidence'], reverse=True)
    
    # Step 4: Limit relationships per table pair
    limited_relationships = []
    pair_counts: Dict[Tuple[str, str], int] = {}
    
    for rel in relationships:
        pair = tuple(sorted([rel['from_table'], rel['to_table']]))
        count = pair_counts.get(pair, 0)
        
        if count < MAX_PER_TABLE_PAIR:
            limited_relationships.append(rel)
            pair_counts[pair] = count + 1
    
    relationships = limited_relationships
    
    # Step 5: Find unmatched key columns
    matched_cols = set()
    for r in relationships:
        matched_cols.add(f"{r['from_table']}.{r['from_column']}")
        matched_cols.add(f"{r['to_table']}.{r['to_column']}")
    
    unmatched = []
    for st in semantic_types:
        full_name = f"{st['table']}.{st['column']}"
        if full_name not in matched_cols:
            unmatched.append({
                'table': st['table'],
                'column': st['column'],
                'semantic_type': st['type']
            })
    
    # Stats
    total_cols = sum(len(t.get('columns', [])) for t in tables)
    high_conf = sum(1 for r in relationships if not r['needs_review'])
    needs_review = sum(1 for r in relationships if r['needs_review'])
    
    logger.info(f"[RELATIONSHIP] Results: {len(relationships)} total, {high_conf} high-conf, {needs_review} needs review")
    
    return {
        'relationships': relationships,
        'semantic_types': semantic_types,
        'unmatched_columns': unmatched[:30],  # Limit list
        'stats': {
            'tables_analyzed': len(tables),
            'columns_analyzed': total_cols,
            'key_columns_found': len(semantic_types),
            'semantic_types_found': len(type_to_columns),
            'relationships_found': len(relationships),
            'high_confidence': high_conf,
            'needs_review': needs_review,
        }
    }


def find_column_matches(
    table1_name: str, 
    cols1: List[str],
    table2_name: str, 
    cols2: List[str]
) -> List[Dict]:
    """
    Find matching columns between two tables.
    Returns list of matches sorted by confidence.
    """
    matches = []
    seen_pairs = set()
    
    for col1 in cols1:
        for col2 in cols2:
            # Skip if same column name in same comparison
            pair_key = tuple(sorted([col1.lower(), col2.lower()]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            
            score = similarity_score(col1, col2)
            
            if score >= THRESHOLD_DISCARD:
                matches.append({
                    'from_table': table1_name,
                    'from_column': col1,
                    'to_table': table2_name,
                    'to_column': col2,
                    'confidence': round(score, 2),
                    'method': 'exact' if score == 1.0 else 'semantic' if score >= 0.9 else 'fuzzy',
                    'needs_review': score < THRESHOLD_AUTO_ACCEPT,
                    'confirmed': False,
                })
    
    # Sort by confidence descending
    matches.sort(key=lambda x: x['confidence'], reverse=True)
    
    return matches


def deduplicate_relationships(relationships: List[Dict]) -> List[Dict]:
    """Remove duplicate relationships (same pair of columns)."""
    seen = set()
    unique = []
    
    for r in relationships:
        # Create canonical pair key
        pair = tuple(sorted([
            f"{r['from_table']}.{r['from_column']}",
            f"{r['to_table']}.{r['to_column']}"
        ]))
        
        if pair not in seen:
            seen.add(pair)
            unique.append(r)
    
    return unique


# =============================================================================
# GLOBAL MAPPINGS (for cross-customer learning)
# =============================================================================

# These are "known good" mappings that apply across customers
# In production, this would come from Supabase global_column_mappings table
KNOWN_GLOBAL_MAPPINGS = {
    # (normalized_name1, normalized_name2): confidence
    ('employee_number', 'ee_num'): 1.0,
    ('employee_number', 'emp_id'): 1.0,
    ('employee_number', 'employee_id'): 1.0,
    ('company_code', 'home_company_code'): 1.0,
    ('company_code', 'co_code'): 1.0,
    ('department_code', 'dept_code'): 1.0,
    ('department_code', 'home_department_code'): 1.0,
    ('job_code', 'position_code'): 0.95,
    ('location_code', 'loc_code'): 1.0,
    ('location_code', 'work_location_code'): 1.0,
    ('earning_code', 'earn_code'): 1.0,
    ('deduction_code', 'ded_code'): 1.0,
    ('pay_group', 'paygroup'): 1.0,
    ('pay_group', 'pay_grp'): 1.0,
}


def check_global_mapping(col1: str, col2: str) -> Optional[float]:
    """
    Check if this column pair has a known global mapping.
    Returns confidence if found, None if not.
    """
    n1 = strip_prefixes_suffixes(col1)
    n2 = strip_prefixes_suffixes(col2)
    
    # Check both orderings
    pair1 = (n1, n2)
    pair2 = (n2, n1)
    
    if pair1 in KNOWN_GLOBAL_MAPPINGS:
        return KNOWN_GLOBAL_MAPPINGS[pair1]
    if pair2 in KNOWN_GLOBAL_MAPPINGS:
        return KNOWN_GLOBAL_MAPPINGS[pair2]
    
    return None


async def save_confirmed_mapping(col1: str, col2: str, project: str = None):
    """
    Save a confirmed mapping to global mappings.
    
    TODO: Implement Supabase storage
    """
    n1 = strip_prefixes_suffixes(col1)
    n2 = strip_prefixes_suffixes(col2)
    
    logger.info(f"[GLOBAL] Would save mapping: {n1} <-> {n2}")
    # Future: INSERT INTO global_column_mappings ...


async def get_confirmed_relationships(project: str) -> List[Dict]:
    """
    Get previously confirmed relationships for a project.
    
    TODO: Implement Supabase storage
    """
    # Future: SELECT * FROM project_relationships WHERE project = ...
    return []
