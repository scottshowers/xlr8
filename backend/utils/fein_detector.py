"""
Entity Identifier Detection Utilities for Multi-Entity Analysis

Add this to backend/utils/fein_detector.py (new file)
OR add functions to hybrid_analyzer.py

This module handles:
1. Extracting US FEINs and Canada Business Numbers from document text
2. Identifying company names associated with entities
3. Segmenting content by entity for separate analysis
4. Country classification (US vs Canada)

SUPPORTED IDENTIFIERS:
- US FEIN: XX-XXXXXXX (Federal Employer Identification Number)
- Canada BN: XXXXXXXXX RT XXXX (Business Number + Program Account)
"""

import re
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# COUNTRY-SPECIFIC PATTERNS
# =============================================================================

ENTITY_PATTERNS = {
    'us_fein': {
        'pattern': r'\b(\d{2})-(\d{7})\b',
        'format': lambda m: f"{m.group(1)}-{m.group(2)}",
        'country': 'us',
        'type': 'fein',
        'description': 'Federal Employer Identification Number'
    },
    'us_fein_nospace': {
        'pattern': r'\bFEIN[:\s]*(\d{2})[\s-]?(\d{7})\b',
        'format': lambda m: f"{m.group(1)}-{m.group(2)}",
        'country': 'us',
        'type': 'fein',
        'description': 'FEIN with label'
    },
    'canada_bn_spaced': {
        'pattern': r'\b(\d{9})\s+(RT|RC|RP|RZ|RR)\s*(\d{4})\b',
        'format': lambda m: f"{m.group(1)} {m.group(2).upper()} {m.group(3)}",
        'country': 'canada',
        'type': 'bn',
        'description': 'Business Number with program ID (spaced)'
    },
    'canada_bn_concat': {
        'pattern': r'\b(\d{9})(RT|RC|RP|RZ|RR)(\d{4})\b',
        'format': lambda m: f"{m.group(1)} {m.group(2).upper()} {m.group(3)}",
        'country': 'canada',
        'type': 'bn',
        'description': 'Business Number with program ID (concatenated)'
    },
    'canada_bn_base': {
        # Just the 9-digit BN without program code (less specific)
        'pattern': r'\b(?:BN|Business\s*Number)[:\s]*(\d{9})\b',
        'format': lambda m: m.group(1),
        'country': 'canada',
        'type': 'bn_base',
        'description': 'Business Number base (no program)'
    }
}


# =============================================================================
# ENTITY EXTRACTION (US + Canada)
# =============================================================================

def detect_entity_identifiers(text: str) -> Dict[str, List[Dict]]:
    """
    Detect all entity identifiers and classify by country.
    
    Returns:
    {
        'us': [
            {'id': '74-1776312', 'type': 'fein', 'count': 5, 'contexts': [...]}
        ],
        'canada': [
            {'id': '123456789 RT 0001', 'type': 'bn', 'count': 3, 'contexts': [...]}
        ]
    }
    """
    results = {'us': {}, 'canada': {}}  # Use dicts for deduplication
    
    for pattern_name, config in ENTITY_PATTERNS.items():
        pattern = config['pattern']
        country = config['country']
        entity_type = config['type']
        
        for match in re.finditer(pattern, text, re.IGNORECASE):
            # Format the ID using the pattern's format function
            entity_id = config['format'](match)
            
            # Get context (100 chars before/after)
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            context = text[start:end].strip()
            context = re.sub(r'\s+', ' ', context)
            
            if entity_id not in results[country]:
                results[country][entity_id] = {
                    'id': entity_id,
                    'type': entity_type,
                    'country': country,
                    'contexts': [],
                    'count': 0,
                    'positions': []
                }
            
            results[country][entity_id]['count'] += 1
            results[country][entity_id]['positions'].append((match.start(), match.end()))
            
            # Keep up to 5 unique contexts
            if len(results[country][entity_id]['contexts']) < 5:
                existing = results[country][entity_id]['contexts']
                if not any(context in e or e in context for e in existing):
                    results[country][entity_id]['contexts'].append(context)
    
    # Convert dicts to sorted lists
    final = {
        'us': sorted(results['us'].values(), key=lambda x: (-x['count'], x['positions'][0][0] if x['positions'] else 0)),
        'canada': sorted(results['canada'].values(), key=lambda x: (-x['count'], x['positions'][0][0] if x['positions'] else 0))
    }
    
    logger.info(f"[ENTITY] Detected {len(final['us'])} US entities, {len(final['canada'])} Canada entities")
    
    return final


def extract_feins(text: str) -> List[Dict]:
    """
    Extract all unique FEINs from document text (US only, for backward compatibility).
    
    Returns list of:
    {
        'fein': '74-1776312',
        'raw': '74-1776312',
        'contexts': ['...context snippet...'],
        'count': 5,
        'positions': [(start, end), ...]
    }
    """
    entities = detect_entity_identifiers(text)
    
    # Return US entities in legacy format
    return [
        {
            'fein': e['id'],
            'raw': e['id'],
            'contexts': e['contexts'],
            'count': e['count'],
            'positions': e['positions']
        }
        for e in entities.get('us', [])
    ]


def identify_company_names(feins: List[Dict], text: str) -> Dict[str, Dict]:
    """
    Try to match each FEIN to a company name.
    
    Returns:
    {
        '74-1776312': {
            'fein': '74-1776312',
            'company_name': 'Team Industrial Services, Inc.',
            'confidence': 'high',
            'is_primary': True
        }
    }
    """
    results = {}
    
    # Common company suffixes
    suffixes = r'(?:Inc\.?|LLC|L\.?L\.?C\.?|Corp\.?|Corporation|Ltd\.?|Limited|LP|L\.?P\.?|LLP|L\.?L\.?P\.?|Co\.?|Company|PLC|PLLC)'
    
    for i, fein_info in enumerate(feins):
        fein = fein_info['fein']
        fein_escaped = re.escape(fein).replace(r'\-', r'[-\s]?')  # Allow dash or space or nothing
        
        company_name = None
        confidence = 'low'
        
        # Pattern 1: "Company Name, Inc. FEIN: XX-XXXXXXX" or "(XX-XXXXXXX)"
        pattern1 = rf'([A-Z][A-Za-z0-9\s,\.&\'-]+{suffixes})\s*(?:\(|\[)?(?:FEIN|EIN)?[:\s]*{fein_escaped}'
        match = re.search(pattern1, text, re.IGNORECASE)
        if match:
            company_name = match.group(1).strip().rstrip(',.-')
            confidence = 'high'
        
        # Pattern 2: "FEIN XX-XXXXXXX Company Name" or "XX-XXXXXXX - Company Name"
        if not company_name:
            pattern2 = rf'{fein_escaped}\s*(?:\)|\])?(?:\s*[-–:]\s*)?([A-Z][A-Za-z0-9\s,\.&\'-]+{suffixes})'
            match = re.search(pattern2, text, re.IGNORECASE)
            if match:
                company_name = match.group(1).strip().rstrip(',.-')
                confidence = 'high'
        
        # Pattern 3: "Employer: Company Name" near FEIN
        if not company_name:
            for context in fein_info['contexts']:
                pattern3 = rf'(?:Employer|Company|Entity|Legal\s*Name)[:\s]+([A-Z][A-Za-z0-9\s,\.&\'-]+{suffixes})'
                match = re.search(pattern3, context, re.IGNORECASE)
                if match:
                    company_name = match.group(1).strip().rstrip(',.-')
                    confidence = 'medium'
                    break
        
        # Pattern 4: Look for any company-like name in context
        if not company_name:
            for context in fein_info['contexts']:
                pattern4 = rf'([A-Z][A-Za-z0-9\s,\.&\'-]{{5,50}}{suffixes})'
                match = re.search(pattern4, context)
                if match:
                    candidate = match.group(1).strip()
                    # Avoid matching generic text
                    if not any(skip in candidate.lower() for skip in ['page', 'report', 'form', 'date', 'total']):
                        company_name = candidate
                        confidence = 'low'
                        break
        
        # Fallback
        if not company_name:
            company_name = f"Entity {fein}"
            confidence = 'none'
        
        results[fein] = {
            'fein': fein,
            'company_name': company_name,
            'confidence': confidence,
            'is_primary': i == 0,  # First (most frequent) is primary
            'mention_count': fein_info['count']
        }
    
    logger.info(f"[FEIN] Identified entities: {[(v['company_name'], v['confidence']) for v in results.values()]}")
    
    return results


# =============================================================================
# CONTENT SEGMENTATION
# =============================================================================

def segment_content_by_fein(text: str, feins: List[str]) -> Dict[str, str]:
    """
    Attempt to segment document content by FEIN.
    
    Returns:
    {
        '74-1776312': 'Content related to this FEIN...',
        '12-3456789': 'Content related to this FEIN...',
        '_global': 'Content that applies to all or is ambiguous...',
        '_header': 'Content before first FEIN mention...'
    }
    
    Note: This is best-effort. Some documents intermix FEIN data.
    In those cases, we return '_mixed' and let the LLM sort it out.
    """
    if len(feins) <= 1:
        return {'_all': text}
    
    # Find all FEIN positions
    fein_positions = []
    for fein in feins:
        fein_escaped = re.escape(fein)
        for match in re.finditer(fein_escaped, text):
            fein_positions.append((match.start(), match.end(), fein))
    
    fein_positions.sort(key=lambda x: x[0])
    
    # Check if FEINs are cleanly separated or intermixed
    if len(fein_positions) > 0:
        # Check pattern: do FEINs alternate or cluster?
        fein_sequence = [p[2] for p in fein_positions]
        
        # Count transitions between different FEINs
        transitions = sum(1 for i in range(1, len(fein_sequence)) if fein_sequence[i] != fein_sequence[i-1])
        
        if transitions > len(feins) * 2:
            # Too many transitions = intermixed, can't cleanly segment
            logger.info(f"[FEIN] Content is intermixed ({transitions} transitions), returning as mixed")
            return {'_mixed': text}
    
    # Try to segment by FEIN sections
    segments = {fein: [] for fein in feins}
    segments['_global'] = []
    segments['_header'] = []
    
    lines = text.split('\n')
    current_fein = '_header'
    
    for line in lines:
        # Check which FEINs appear in this line
        mentioned = [f for f in feins if f in line]
        
        if len(mentioned) == 1:
            current_fein = mentioned[0]
        elif len(mentioned) > 1:
            # Multiple FEINs in one line = global/comparison
            segments['_global'].append(line)
            continue
        
        if current_fein in feins:
            segments[current_fein].append(line)
        elif current_fein == '_header':
            segments['_header'].append(line)
        else:
            segments['_global'].append(line)
    
    # Join lines back
    result = {}
    for key, lines in segments.items():
        content = '\n'.join(lines).strip()
        if content:
            result[key] = content
    
    logger.info(f"[FEIN] Segmented content: {[(k, len(v)) for k, v in result.items()]}")
    
    return result


# =============================================================================
# ANALYSIS DECISION
# =============================================================================

def get_analysis_mode(feins: List[Dict]) -> Tuple[str, Dict]:
    """
    Determine how to analyze based on FEIN count.
    
    Returns:
        (mode, metadata)
        
    Modes:
    - 'single': One FEIN, standard analysis
    - 'multi': Multiple FEINs, segmented analysis
    - 'none': No FEINs found, generic analysis
    """
    if not feins:
        return 'none', {'fein_count': 0}
    
    if len(feins) == 1:
        return 'single', {
            'fein_count': 1,
            'primary_fein': feins[0]['fein']
        }
    
    return 'multi', {
        'fein_count': len(feins),
        'feins': [f['fein'] for f in feins],
        'primary_fein': feins[0]['fein']  # Most mentioned = primary
    }


# =============================================================================
# MULTI-FEIN PROMPT BUILDER
# =============================================================================

def build_multi_fein_prompt(
    entities: Dict[str, Dict],
    action: Dict,
    content: str,
    inherited_context: str = ""
) -> str:
    """
    Build analysis prompt for multi-FEIN documents.
    
    This prompt instructs the LLM to:
    1. Analyze each entity separately
    2. NOT flag inter-entity differences as conflicts
    3. Identify truly global issues
    """
    
    entity_list = "\n".join([
        f"  - {info['fein']}: {info['company_name']} {'(PRIMARY)' if info.get('is_primary') else ''}"
        for fein, info in entities.items()
    ])
    
    fein_list = list(entities.keys())
    
    prompt = f"""You are a senior UKG implementation consultant analyzing documents for a customer with MULTIPLE LEGAL ENTITIES.

═══════════════════════════════════════════════════════════════
CRITICAL: This customer has {len(entities)} separate legal entities (FEINs)
═══════════════════════════════════════════════════════════════

ENTITIES DETECTED:
{entity_list}

IMPORTANT RULES:
1. Analyze EACH entity SEPARATELY
2. DO NOT flag differences BETWEEN entities as conflicts - they are DIFFERENT COMPANIES
3. Each entity may have different tax rates, registrations, and configurations - this is NORMAL
4. Only flag as "global_issues" things that truly span entities (missing shared tax groups, etc.)

ACTION: {action.get('action_id')} - {action.get('description', '')}
{f'INHERITED CONTEXT: {inherited_context}' if inherited_context else ''}

<document>
{content[:20000]}
</document>

Analyze and return JSON with findings PER ENTITY:

{{
    "is_multi_fein": true,
    "fein_count": {len(entities)},
    "entities": {{
        "{fein_list[0]}": {{
            "company_name": "Full legal name",
            "is_primary": true,
            "key_values": {{"SUI Rate": "X%", "Active States": "TX, CA", ...}},
            "issues": ["SPECIFIC issue for THIS entity only"],
            "recommendations": ["SPECIFIC recommendation for THIS entity"],
            "risk_level": "low|medium|high",
            "data_quality": "good|fair|poor"
        }},
        "{fein_list[1] if len(fein_list) > 1 else 'XX-XXXXXXX'}": {{
            "company_name": "...",
            "is_primary": false,
            ...
        }}
    }},
    "global_issues": [
        "Issues that span ALL entities or are company-wide policy issues"
    ],
    "global_recommendations": [
        "Recommendations that apply across all entities"
    ],
    "cross_entity_notes": "Any observations about relationships between entities (optional)",
    "summary": "2-3 sentence summary covering ALL entities",
    "complete": true/false
}}

REMEMBER:
- Entity A having SUI 2.7% while Entity B has SUI 5.1% is NOT a conflict
- Analyze each entity against UKG standards individually
- Be SPECIFIC with values and sources
- Include source filenames when citing data

Return ONLY valid JSON."""

    return prompt


# =============================================================================
# RESULT MERGER
# =============================================================================

def merge_multi_fein_results(
    entity_results: Dict[str, Dict],
    global_issues: List[str] = None,
    global_recommendations: List[str] = None
) -> Dict:
    """
    Merge individual entity analysis results into unified response.
    
    Used when we analyze each entity separately and need to combine.
    """
    
    # Determine overall risk level (highest among entities)
    risk_levels = {'low': 1, 'medium': 2, 'high': 3}
    max_risk = 'low'
    for fein, result in entity_results.items():
        entity_risk = result.get('risk_level', 'low')
        if risk_levels.get(entity_risk, 0) > risk_levels.get(max_risk, 0):
            max_risk = entity_risk
    
    # Count total issues
    total_issues = sum(len(r.get('issues', [])) for r in entity_results.values())
    total_issues += len(global_issues or [])
    
    # Build summary
    entity_summaries = []
    for fein, result in entity_results.items():
        name = result.get('company_name', fein)
        risk = result.get('risk_level', 'unknown')
        issue_count = len(result.get('issues', []))
        entity_summaries.append(f"{name} ({risk.upper()} risk, {issue_count} issues)")
    
    summary = f"Analyzed {len(entity_results)} entities. " + "; ".join(entity_summaries) + "."
    
    return {
        'is_multi_fein': True,
        'fein_count': len(entity_results),
        'entities': entity_results,
        'global_issues': global_issues or [],
        'global_recommendations': global_recommendations or [],
        'summary': summary,
        'risk_level': max_risk,
        'complete': total_issues == 0,
        '_analyzed_by': 'multi_fein'
    }
