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

# Try to import LLM orchestrator
try:
    from utils.llm_orchestrator import LLMOrchestrator
    LLM_ORCHESTRATOR_AVAILABLE = True
except ImportError:
    try:
        from backend.utils.llm_orchestrator import LLMOrchestrator
        LLM_ORCHESTRATOR_AVAILABLE = True
    except ImportError:
        LLM_ORCHESTRATOR_AVAILABLE = False
        logger.warning("[HYBRID] LLMOrchestrator not available")


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
        # Use same env vars as smart_pdf_analyzer.py
        self.ollama_url = (
            os.getenv("LLM_INFERENCE_URL") or 
            os.getenv("OLLAMA_URL") or 
            os.getenv("RUNPOD_URL") or 
            os.getenv("LLM_ENDPOINT", "")
        )
        if self.ollama_url:
            self.ollama_url = self.ollama_url.rstrip('/')
        
        self.ollama_username = os.getenv("LLM_USERNAME", "")
        self.ollama_password = os.getenv("LLM_PASSWORD", "")
        self.model = os.getenv("OLLAMA_MODEL", os.getenv("LLM_MODEL", "mistral"))
        
        logger.info(f"[HYBRID] LocalLLMClient initialized: url={self.ollama_url}, model={self.model}")
    
    def is_available(self) -> bool:
        """Check if local LLM is configured and reachable"""
        if not self.ollama_url:
            logger.warning("[HYBRID] No LLM URL configured")
            return False
        try:
            url = f"{self.ollama_url}/api/tags"
            auth = None
            if self.ollama_username and self.ollama_password:
                auth = HTTPBasicAuth(self.ollama_username, self.ollama_password)
            resp = requests.get(url, auth=auth, timeout=5)
            logger.info(f"[HYBRID] LLM availability check: {resp.status_code}")
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"[HYBRID] LLM not reachable: {e}")
            return False
    
    def extract(self, text: str, prompt: str, operation: str = "scan", project_id: str = None) -> Tuple[Optional[str], bool]:
        """Call local LLM for extraction"""
        if not self.ollama_url:
            logger.warning("[HYBRID] No LLM URL configured, skipping local extraction")
            return None, False
        
        import time
        start_time = time.time()
        
        try:
            url = f"{self.ollama_url}/api/generate"
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,  # Low temp for extraction
                    "num_predict": 8192  # Increased to avoid truncation with complex docs
                }
            }
            
            logger.info(f"[HYBRID] Calling local LLM at {url} with model {self.model}")
            
            auth = None
            if self.ollama_username and self.ollama_password:
                auth = HTTPBasicAuth(self.ollama_username, self.ollama_password)
            
            response = requests.post(url, json=payload, auth=auth, timeout=120)
            
            if response.status_code != 200:
                logger.warning(f"[HYBRID] Local LLM error: {response.status_code} - {response.text[:200]}")
                return None, False
            
            result = response.json().get("response", "")
            logger.info(f"[HYBRID] Local LLM response: {len(result)} chars")
            
            # Track cost
            duration_ms = int((time.time() - start_time) * 1000)
            try:
                from backend.utils.cost_tracker import log_cost, CostService
                log_cost(
                    service=CostService.RUNPOD,
                    operation=operation,
                    duration_ms=duration_ms,
                    project_id=project_id,
                    metadata={"model": self.model, "prompt_len": len(prompt), "response_len": len(result)}
                )
            except Exception as cost_err:
                logger.debug(f"Cost tracking failed: {cost_err}")
            
            return result, True
            
        except requests.Timeout:
            logger.warning(f"[HYBRID] Local LLM timeout after 120s")
            return None, False
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
        
        # Initialize LLMOrchestrator for Claude calls
        self.orchestrator = None
        if LLM_ORCHESTRATOR_AVAILABLE:
            try:
                self.orchestrator = LLMOrchestrator()
                logger.info("[HYBRID] LLMOrchestrator initialized")
            except Exception as e:
                logger.warning(f"[HYBRID] LLMOrchestrator init failed: {e}")
        
        # Try to import learning system
        try:
            from backend.utils.learning_engine import get_learning_system
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
        Use local LLM to extract AND analyze data like a UKG consultant.
        Returns extracted data with issues and recommendations.
        """
        # First, quick regex extraction
        regex_results = self.extract_with_regex(text)
        
        # Get few-shot examples if learning is available
        examples_context = ""
        if self.learning:
            examples = self.learning.get_few_shot_examples(action_id, limit=2)
            if examples:
                examples_context = "\n\nEXAMPLES OF GOOD ANALYSIS:\n"
                for ex in examples:
                    examples_context += f"Input sample: {ex.get('input_sample', '')[:200]}...\n"
                    examples_context += f"Output: {json.dumps(ex.get('output', {}))}\n\n"
        
        # Build consultant-grade analysis prompt with domain knowledge
        prompt = f"""You are a UKG payroll consultant. Analyze this document and provide SPECIFIC findings.

RULES:
- SUI rates: normal 0.5%-5.4%, above 6% is unusual
- FUTA: should be 0.6%
- WC rates above 10% = high-risk
- FEIN format: XX-XXXXXXX

CRITICAL: Be SPECIFIC. Don't say "there are issues" - LIST THE EXACT ITEMS.

BAD: "Multiple duplicate SUI entries found"
GOOD: "Duplicate SUI entries: KY has 2.7% and 2.5%, MI has 3.1% twice, MN has 2.8% and 2.9%"

BAD: "Some states missing WC coverage"  
GOOD: "States missing WC coverage: TX, FL, GA, NC (these are active payroll states with no WC rates)"

BAD: "Tax rate inconsistencies found"
GOOD: "Rate mismatches: PA SUI is 13.6% in Tax Verification but 13.2% in Master Profile"

{examples_context}

DOCUMENT:
{text[:15000]}

Return JSON with SPECIFIC values and lists:
{{"fein":"actual-fein","company_name":"actual name","tax_rates":{{"STATE":"rate%"}},"wc_rates":{{"code":"rate%"}},"issues_found":["SPECIFIC issue with exact values"],"recommendations":["SPECIFIC action: fix X, Y, Z"],"risk_level":"low/medium/high"}}"""

        result, success = self.local_llm.extract(text, prompt)
        
        if not success or not result:
            return None
        
        # Try to parse JSON from response
        try:
            # Clean up response - handle preamble text before JSON
            result = result.strip()
            
            # Strip JavaScript-style comments that break JSON
            # Remove single-line comments (// ...)
            result = re.sub(r'//[^\n]*', '', result)
            # Remove multi-line comments (/* ... */)
            result = re.sub(r'/\*.*?\*/', '', result, flags=re.DOTALL)
            # Remove trailing commas before } or ]
            result = re.sub(r',\s*([}\]])', r'\1', result)
            
            # Strip JavaScript-style comments (// ... until end of line)
            # This handles local LLMs that add comments like: "address": null, // not provided
            result = re.sub(r'//[^\n]*', '', result)
            
            # Strip multi-line comments /* ... */
            result = re.sub(r'/\*.*?\*/', '', result, flags=re.DOTALL)
            
            # Find JSON object in response (may have preamble text)
            json_start = result.find('{')
            if json_start > 0:
                result = result[json_start:]
            
            # Handle markdown code blocks
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]
                result = result.strip()
            
            # Find matching closing brace
            brace_count = 0
            json_end = -1
            for i, char in enumerate(result):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i + 1
                        break
            
            if json_end > 0:
                result = result[:json_end]
            else:
                # JSON appears truncated - try to repair by closing brackets
                logger.warning(f"[HYBRID] JSON appears truncated (unclosed braces: {brace_count}), attempting repair")
                # Close any open strings first (find last " and add one if odd count)
                quote_count = result.count('"')
                if quote_count % 2 == 1:
                    result += '"'
                # Close brackets/braces
                result += '}' * brace_count
            
            result = result.strip()
            
            extracted = json.loads(result)
            
            # Ensure we have a dict, not a list
            if isinstance(extracted, list):
                extracted = {'items': extracted}
            
            # Merge regex results
            if regex_results and isinstance(extracted, dict):
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
        
        # If parse failed, ALWAYS use Claude - regex extraction is not analysis
        if local_results.get('_local_parse_failed'):
            logger.info(f"[HYBRID] Local parse failed, falling back to Claude for real analysis")
            return True
        
        # Simple extraction actions can skip Claude if local succeeded
        if action_id in SIMPLE_EXTRACTION_ACTIONS:
            return False
        
        # Default: use Claude for safety
        return True
    
    def call_claude(self, text: str, action: Dict, local_results: Optional[Dict] = None, 
                    inherited_findings: List[Dict] = None) -> Optional[Dict]:
        """Call Claude for complex analysis - uses LLMOrchestrator"""
        if not self.orchestrator and not self.claude_api_key:
            logger.error("[HYBRID] No LLM available for Claude calls")
            return None
        
        try:
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
            
            prompt = f"""ACTION: {action.get('action_id')} - {action.get('description', '')}
{f'INHERITED: {inherited_context}' if inherited_context else ''}

{local_context}

<document>
{text[:15000]}
</document>

CRITICAL: Be SPECIFIC with findings. Don't summarize - LIST EXACT ITEMS.

BAD: "Multiple duplicate SUI entries found"
GOOD: "Duplicate SUI entries: KY has 2.7% and 2.5%, MI has 3.1% twice"

BAD: "Some states missing WC coverage"  
GOOD: "States missing WC coverage: TX, FL, GA, NC"

Each document chunk is labeled with [FILE: filename]. Include source citations.

Return JSON:
{{
    "complete": true/false,
    "key_values": {{"label": "value (from filename)"}},
    "issues": ["SPECIFIC issue with exact values (Source: filename)"],
    "recommendations": ["SPECIFIC action: fix X, Y, Z"],
    "risk_level": "low|medium|high",
    "summary": "2-3 sentence summary",
    "sources_used": ["list of filenames analyzed"]
}}

Return ONLY valid JSON."""

            system_prompt = "You are a senior UKG implementation consultant. Analyze documents and provide specific, actionable findings."
            
            logger.info(f"[HYBRID] Calling Claude for {action.get('action_id')}")
            self.stats['claude_calls'] += 1
            
            # Use orchestrator for all LLM calls
            if not self.orchestrator:
                logger.error("[HYBRID] LLMOrchestrator not available")
                return None
            
            # Use generate_json for structured output
            result = self.orchestrator.generate_json(
                prompt=f"{system_prompt}\n\n{prompt}"
            )
            
            if result.get('success') and result.get('json'):
                parsed_result = result['json']
                logger.info(f"[HYBRID] Got response from {result.get('model_used', 'unknown')}")
                
                # LEARNING: Capture this output for future training
                if self.learning:
                    quality = 'high' if parsed_result.get('complete') else 'medium'
                    self.learning.learn_from_claude(text, prompt, parsed_result, action.get('action_id'), quality)
                
                return parsed_result
            elif result.get('response'):
                # Try to parse raw response
                result_text = result['response'].strip()
            else:
                logger.error(f"[HYBRID] LLM call failed: {result.get('error')}")
                return None
            
            result_text = result_text.strip()
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
        """Build a findings result using local LLM analysis."""
        self.stats['local_only'] += 1
        
        # The local LLM now returns issues, recommendations, and risk_level directly
        # Use those if available, otherwise fall back to learned patterns
        
        # Get LLM's direct analysis
        llm_issues = local_results.get('issues_found', [])
        llm_recommendations = local_results.get('recommendations', [])
        llm_risk_level = local_results.get('risk_level', 'low')
        
        # Run additional rule-based validation if learning is available
        rule_issues = []
        if self.learning:
            rule_issues = self.learning.validate_extraction(local_results)
            for ri in rule_issues:
                issue_text = f"{ri['field']}: {ri['error']}"
                if issue_text not in llm_issues:
                    llm_issues.append(issue_text)
        
        # Get key values from extraction
        key_values = {}
        regex = local_results.get('_regex', {})
        
        def format_fein(fein_str):
            """Format FEIN as XX-XXXXXXX"""
            if not fein_str:
                return None
            digits = ''.join(c for c in str(fein_str) if c.isdigit())
            if len(digits) == 9:
                return f"{digits[:2]}-{digits[2:]}"
            elif len(digits) >= 7:
                return f"{digits[:2]}-{digits[2:9]}"
            return fein_str
        
        if local_results.get('fein'):
            key_values['FEIN'] = format_fein(local_results['fein'])
        elif regex.get('fein'):
            key_values['FEIN'] = regex['fein'][0]
        
        if local_results.get('company_name'):
            key_values['Company'] = local_results['company_name']
        
        if local_results.get('address'):
            key_values['Address'] = local_results['address']
        
        if local_results.get('tax_rates'):
            for code, rate in local_results.get('tax_rates', {}).items():
                if isinstance(rate, dict):
                    key_values[f'{code}'] = rate
                else:
                    key_values[f'{code} Rate'] = rate
        elif regex.get('rate_percent'):
            key_values['Rates Found'] = ', '.join(regex['rate_percent'][:5])
        
        # Add WC rates if present
        if local_results.get('wc_rates'):
            key_values['WC Rates'] = local_results['wc_rates']
        
        # Filter out suppressed issues
        if self.learning:
            llm_issues = [i for i in llm_issues if not self.learning.should_suppress_issue(i)]
        
        # Build summary based on what was found
        if llm_issues:
            summary = f"Found {len(llm_issues)} issue(s) requiring attention. "
        else:
            summary = "Analysis complete. "
        
        extracted_items = [k for k in key_values.keys() if key_values[k]]
        if extracted_items:
            summary += f"Extracted: {', '.join(extracted_items[:4])}."
        
        if llm_recommendations:
            summary += f" {len(llm_recommendations)} recommendation(s) for review."
        
        return {
            'complete': len(llm_issues) == 0,
            'key_values': key_values,
            'issues': llm_issues,
            'recommendations': llm_recommendations[:5],
            'risk_level': llm_risk_level,
            'summary': summary,
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
        
        logger.warning(f"[HYBRID] Analyzing {action_id}: {len(combined_text)} total chars, sending {min(15000, len(combined_text))} to LLM")
        
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
