"""
Hybrid LLM Analyzer for XLR8 Year-End Playbook
===============================================

ARCHITECTURE:
- Learning Engine: Cache, rules, training data collection
- Local LLM (Ollama): Fast extraction, pattern matching, data validation
- Claude: Complex reasoning, consultative analysis, recommendations

LEARNING FLOW:
1. Check cache → if hit, return immediately (FREE)
2. Run rule-based validation (FREE)
3. Try local LLM extraction (FREE)
4. If needed, call Claude → capture output for learning
5. User corrections → feed back into system

Cost Savings: 60-80% reduction in Claude API calls

Author: XLR8 Team
"""

import os
import re
import json
import logging
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# EXTRACTION PATTERNS - What local LLM should find
# =============================================================================

EXTRACTION_PATTERNS = {
    # Tax/Company identifiers
    'fein': r'\b\d{2}-\d{7}\b',
    'state_id': r'\b[A-Z]{2}\s*\d{6,12}\b',
    
    # Rates (percentages)
    'rate_percent': r'\b\d{1,2}\.\d{2,4}\s*%',
    'rate_decimal': r'\b0\.\d{4,6}\b',
    
    # Money amounts
    'wage_base': r'\$[\d,]+(?:\.\d{2})?',
    'amount': r'\$[\d,]+(?:\.\d{2})?',
    
    # Addresses
    'address_line': r'\d+\s+[A-Za-z\s]+(?:St|Street|Ave|Avenue|Blvd|Boulevard|Dr|Drive|Rd|Road|Way|Lane|Ln|Ct|Court|Suite|Ste|#)\s*\d*',
    'zip_code': r'\b\d{5}(?:-\d{4})?\b',
    'state_abbrev': r'\b[A-Z]{2}\b',
    
    # Tax codes
    'tax_code': r'(?:SUI|SIT|SDI|FICA|FUTA|SUTA|FWT|SWT|MWTR|PIT)\b',
    
    # Transmittal codes
    'tcc': r'\b[A-Z0-9]{5,6}\b',  # Transmittal Control Code
}

# Actions that can often be resolved locally without Claude
SIMPLE_EXTRACTION_ACTIONS = [
    '2A',  # Review company/tax code info - just extraction
    '2B',  # Verify tax rates - pattern matching
    '3A',  # W-2 contact info - extraction
    '3B',  # Employer name/address - extraction
    '4A',  # Review YTD - numeric validation
    '6A', '6B', '6C', '6D',  # Tax statement reviews - extraction
]

# Actions that ALWAYS need Claude (complex reasoning)
ALWAYS_CLAUDE_ACTIONS = [
    '1A', '1B', '1C',  # Setup/planning - need recommendations
    '5A', '5B', '5C',  # Reconciliation - complex analysis
    '7A', '7B',        # Filing decisions - need expertise
]


# =============================================================================
# LOCAL LLM CLIENT
# =============================================================================

class LocalLLMClient:
    """Client for Ollama (local LLM)"""
    
    def __init__(self):
        self.ollama_url = os.getenv("LLM_ENDPOINT", "").rstrip('/')
        self.ollama_username = os.getenv("LLM_USERNAME", "")
        self.ollama_password = os.getenv("LLM_PASSWORD", "")
        self.model = os.getenv("OLLAMA_MODEL", "mistral")  # or llama3, deepseek-coder
        
        logger.info(f"LocalLLMClient: {self.ollama_url}, model={self.model}")
    
    def is_available(self) -> bool:
        """Check if local LLM is configured and reachable"""
        if not self.ollama_url:
            return False
        try:
            url = f"{self.ollama_url}/api/tags"
            if self.ollama_username:
                resp = requests.get(url, auth=HTTPBasicAuth(self.ollama_username, self.ollama_password), timeout=5)
            else:
                resp = requests.get(url, timeout=5)
            return resp.status_code == 200
        except:
            return False
    
    def extract(self, text: str, prompt: str) -> Tuple[Optional[str], bool]:
        """Call local LLM for extraction"""
        if not self.ollama_url:
            return None, False
        
        try:
            url = f"{self.ollama_url}/api/generate"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temp for extraction
                    "num_predict": 1024
                }
            }
            
            logger.info(f"[HYBRID] Calling local LLM ({self.model}) for extraction")
            
            if self.ollama_username and self.ollama_password:
                response = requests.post(
                    url, json=payload,
                    auth=HTTPBasicAuth(self.ollama_username, self.ollama_password),
                    timeout=30
                )
            else:
                response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"[HYBRID] Local LLM error: {response.status_code}")
                return None, False
            
            result = response.json().get("response", "")
            logger.info(f"[HYBRID] Local LLM response: {len(result)} chars")
            return result, True
            
        except Exception as e:
            logger.warning(f"[HYBRID] Local LLM failed: {e}")
            return None, False


# =============================================================================
# HYBRID ANALYZER
# =============================================================================

class HybridAnalyzer:
    """
    Hybrid analyzer with learning capabilities.
    
    Priority order:
    1. Cache hit → return immediately
    2. Rule-based validation → add issues
    3. Local LLM extraction → if enough, skip Claude
    4. Claude analysis → capture for learning
    """
    
    def __init__(self):
        self.local_llm = LocalLLMClient()
        self.claude_api_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        
        # Try to import learning system
        try:
            from utils.learning_engine import get_learning_system
            self.learning = get_learning_system()
            logger.info("[HYBRID] Learning system enabled")
        except ImportError:
            self.learning = None
            logger.warning("[HYBRID] Learning system not available")
        
        self.stats = {
            'cache_hits': 0,
            'local_only': 0,
            'claude_calls': 0,
            'local_failures': 0
        }
    
    def extract_with_regex(self, text: str) -> Dict[str, List[str]]:
        """Fast regex-based extraction for common patterns"""
        results = {}
        
        for name, pattern in EXTRACTION_PATTERNS.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Dedupe and limit
                unique = list(set(matches))[:10]
                results[name] = unique
        
        return results
    
    def local_extraction(self, text: str, action_id: str, reports_needed: List[str]) -> Optional[Dict]:
        """
        Try to extract key values using local LLM.
        Returns extracted data or None if extraction fails.
        """
        # First, quick regex extraction
        regex_results = self.extract_with_regex(text)
        
        # Get few-shot examples if learning is available
        examples_context = ""
        if self.learning:
            examples = self.learning.get_few_shot_examples(action_id, limit=2)
            if examples:
                examples_context = "\n\nEXAMPLES OF GOOD EXTRACTIONS:\n"
                for ex in examples:
                    examples_context += f"Input sample: {ex.get('input_sample', '')[:200]}...\n"
                    examples_context += f"Output: {json.dumps(ex.get('output', {}))}\n\n"
        
        # Build focused extraction prompt
        prompt = f"""Extract the following from this document. Return ONLY a JSON object.

LOOK FOR:
- FEIN/EIN (format: XX-XXXXXXX)
- Company name and address
- Tax rates (percentages like X.XX%)
- State tax codes (SUI, SIT, SDI, etc.)
- Wage bases (dollar amounts)
- Any transmittal control codes (TCC)
{examples_context}
DOCUMENT:
{text[:8000]}

Return JSON like:
{{"fein": "XX-XXXXXXX", "company_name": "...", "address": "...", "tax_rates": {{"SUI": "X.XX%"}}, "issues_found": []}}

If data is missing, use null. Return ONLY valid JSON, no explanation."""

        result, success = self.local_llm.extract(text, prompt)
        
        if not success or not result:
            return None
        
        # Try to parse JSON from response
        try:
            # Clean up response
            result = result.strip()
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
            result = result.strip()
            
            extracted = json.loads(result)
            
            # Merge regex results
            if regex_results:
                extracted['_regex'] = regex_results
            
            return extracted
            
        except json.JSONDecodeError:
            logger.warning(f"[HYBRID] Local LLM returned non-JSON: {result[:200]}")
            # Return regex results as fallback
            if regex_results:
                return {'_regex': regex_results, '_local_parse_failed': True}
            return None
    
    def needs_claude(self, action_id: str, local_results: Optional[Dict]) -> bool:
        """
        Determine if we need Claude for this action.
        """
        # Always Claude for complex actions
        if action_id in ALWAYS_CLAUDE_ACTIONS:
            return True
        
        # If local extraction failed, use Claude
        if not local_results:
            return True
        
        # If local found issues, use Claude for analysis
        if local_results.get('issues_found') and len(local_results.get('issues_found', [])) > 0:
            return True
        
        # If parse failed but we have regex results, might be okay
        if local_results.get('_local_parse_failed'):
            # Check if we got the essential data via regex
            regex = local_results.get('_regex', {})
            if regex.get('fein') or regex.get('rate_percent'):
                return False  # We got what we needed
            return True  # Need Claude to interpret
        
        # Simple extraction actions can skip Claude if local succeeded
        if action_id in SIMPLE_EXTRACTION_ACTIONS:
            return False
        
        # Default: use Claude for safety
        return True
    
    def call_claude(self, text: str, action: Dict, local_results: Optional[Dict] = None, 
                    inherited_findings: List[Dict] = None) -> Optional[Dict]:
        """Call Claude for complex analysis"""
        if not self.claude_api_key:
            logger.error("[HYBRID] Claude API key not configured")
            return None
        
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.claude_api_key)
            
            # Build context with local extraction results
            local_context = ""
            if local_results:
                local_context = f"""
PRE-EXTRACTED DATA (verified by local analysis):
{json.dumps(local_results, indent=2)}

Use these values as reference. Focus on ANALYSIS and RECOMMENDATIONS.
"""
            
            inherited_context = ""
            if inherited_findings:
                parts = []
                for inf in inherited_findings:
                    parent_id = inf.get("action_id", "unknown")
                    parent_findings = inf.get("findings", {})
                    parts.append(f"From {parent_id}: {parent_findings.get('summary', 'N/A')}")
                inherited_context = "\n".join(parts)
            
            prompt = f"""You are a senior UKG implementation consultant.

ACTION: {action.get('action_id')} - {action.get('description', '')}
{f'INHERITED: {inherited_context}' if inherited_context else ''}

{local_context}

<document>
{text[:15000]}
</document>

IMPORTANT: Each document chunk is labeled with [FILE: filename]. Include source citations.

Analyze and return JSON:
{{
    "complete": true/false,
    "key_values": {{"label": "value (from filename)"}},
    "issues": ["Issue description (Source: filename)"],
    "recommendations": ["specific actions"],
    "risk_level": "low|medium|high",
    "summary": "2-3 sentence summary",
    "sources_used": ["list of filenames analyzed"]
}}

Include "(Source: filename)" at the end of each issue when you can identify the source.
Return ONLY valid JSON."""

            logger.info(f"[HYBRID] Calling Claude for {action.get('action_id')}")
            self.stats['claude_calls'] += 1
            
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            result_text = response.content[0].text.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
            result_text = result_text.strip()
            
            result = json.loads(result_text)
            
            # LEARNING: Capture this output for future training
            if self.learning:
                quality = 'high' if result.get('complete') else 'medium'
                self.learning.learn_from_claude(text, prompt, result, action.get('action_id'), quality)
            
            return result
            
        except Exception as e:
            logger.error(f"[HYBRID] Claude failed: {e}")
            return None
    
    def build_local_only_result(self, action_id: str, local_results: Dict) -> Dict:
        """Build a findings result using only local extraction"""
        self.stats['local_only'] += 1
        
        # Run rule-based validation if learning is available
        rule_issues = []
        if self.learning:
            rule_issues = self.learning.validate_extraction(local_results)
        
        # Get key values from extraction
        key_values = {}
        regex = local_results.get('_regex', {})
        
        if local_results.get('fein'):
            key_values['FEIN'] = local_results['fein']
        elif regex.get('fein'):
            key_values['FEIN'] = regex['fein'][0]
        
        if local_results.get('company_name'):
            key_values['Company'] = local_results['company_name']
        
        if local_results.get('address'):
            key_values['Address'] = local_results['address']
        
        if local_results.get('tax_rates'):
            for code, rate in local_results.get('tax_rates', {}).items():
                key_values[f'{code} Rate'] = rate
        elif regex.get('rate_percent'):
            key_values['Rates Found'] = ', '.join(regex['rate_percent'][:5])
        
        # Combine local issues with rule-based issues
        all_issues = local_results.get('issues_found', [])
        for ri in rule_issues:
            all_issues.append(f"{ri['field']}: {ri['error']}")
        
        # Filter out suppressed issues
        if self.learning:
            all_issues = [i for i in all_issues if not self.learning.should_suppress_issue(i)]
        
        return {
            'complete': len(all_issues) == 0,
            'key_values': key_values,
            'issues': all_issues,
            'recommendations': [],
            'risk_level': 'low' if len(all_issues) == 0 else 'medium',
            'summary': f'Data extracted successfully via local analysis.',
            '_analyzed_by': 'local'
        }
    
    async def analyze(self, action: Dict, content: List[str], 
                      inherited_findings: List[Dict] = None) -> Optional[Dict]:
        """
        Main hybrid analysis method with learning.
        
        1. Check cache
        2. Try local extraction
        3. If simple + good extraction → return local
        4. Otherwise → Claude with pre-extracted context
        5. Capture output for learning
        """
        action_id = action.get('action_id', '')
        combined_text = "\n\n---\n\n".join(content)
        
        logger.info(f"[HYBRID] Analyzing {action_id}, {len(combined_text)} chars")
        
        # Step 0: Check cache
        if self.learning:
            cached = self.learning.get_cached_analysis(combined_text, action_id)
            if cached:
                self.stats['cache_hits'] += 1
                logger.info(f"[HYBRID] ✓ Cache hit for {action_id}")
                cached['_analyzed_by'] = 'cache'
                return cached
        
        # Step 1: Try local extraction
        local_results = None
        if self.local_llm.is_available():
            local_results = self.local_extraction(
                combined_text, 
                action_id,
                action.get('reports_needed', [])
            )
            if local_results:
                logger.info(f"[HYBRID] Local extraction succeeded: {list(local_results.keys())}")
            else:
                self.stats['local_failures'] += 1
                logger.info(f"[HYBRID] Local extraction failed, will use Claude")
        else:
            logger.info(f"[HYBRID] Local LLM not available, using Claude")
        
        # Step 2: Decide if Claude is needed
        if not self.needs_claude(action_id, local_results):
            logger.info(f"[HYBRID] ✓ Using local-only result for {action_id}")
            return self.build_local_only_result(action_id, local_results)
        
        # Step 3: Call Claude with local context
        logger.info(f"[HYBRID] Calling Claude for {action_id}")
        result = self.call_claude(
            combined_text, 
            action, 
            local_results,
            inherited_findings
        )
        
        if result:
            result['_analyzed_by'] = 'claude' if not local_results else 'hybrid'
        
        return result
    
    def get_stats(self) -> Dict:
        """Get analysis statistics"""
        total = self.stats['cache_hits'] + self.stats['local_only'] + self.stats['claude_calls']
        saved = self.stats['cache_hits'] + self.stats['local_only']
        
        stats = {
            **self.stats,
            'total_analyses': total,
            'claude_reduction': f"{(saved / max(total, 1)) * 100:.1f}%"
        }
        
        # Add learning stats if available
        if self.learning:
            stats['learning'] = self.learning.get_stats()
        
        return stats


# =============================================================================
# SINGLETON & CONVENIENCE
# =============================================================================

_analyzer: Optional[HybridAnalyzer] = None

def get_hybrid_analyzer() -> HybridAnalyzer:
    """Get or create singleton analyzer"""
    global _analyzer
    if _analyzer is None:
        _analyzer = HybridAnalyzer()
    return _analyzer


async def analyze_hybrid(action: Dict, content: List[str], 
                        inherited_findings: List[Dict] = None) -> Optional[Dict]:
    """Convenience function for hybrid analysis"""
    analyzer = get_hybrid_analyzer()
    return await analyzer.analyze(action, content, inherited_findings)
