"""
XLR8 Intelligence Engine - Synthesizer
=======================================
VERSION: 3.0.0 - Consultative-First (LLM primary, template fallback)

Synthesizes responses from all Five Truths into consultative answers.

This is where the magic happens - combining Reality, Intent, Configuration,
Reference, and Regulatory data into actionable insights like a senior consultant.

PRIORITY: LLM Synthesis FIRST → Template FALLBACK only on failure

Deploy to: backend/utils/intelligence/synthesizer.py
"""

import logging
from typing import Dict, List, Optional, Any

from .types import (
    Truth, Conflict, Insight, SynthesizedAnswer, IntelligenceMode
)

logger = logging.getLogger(__name__)

# Log version on import
logger.warning("[SYNTHESIZER] Module loaded - VERSION 3.0.0 (Consultative-First)")


class Synthesizer:
    """
    Synthesizes responses from Five Truths into consultative answers.
    
    PRIORITY: LLM Synthesis FIRST → Template FALLBACK
    
    This is what separates XLR8 from data dumps - the ability to triangulate
    across the Five Truths and provide the "so-what" that consultants charge for.
    
    The Five Truths provide full provenance:
    - REALITY: What the data actually shows (DuckDB)
    - INTENT: What the customer says they want (ChromaDB)
    - CONFIGURATION: How they've configured the system (DuckDB)
    - REFERENCE: Product docs, implementation standards (ChromaDB)
    - REGULATORY: Laws, compliance requirements (ChromaDB)
    """
    
    def __init__(self, llm_synthesizer=None, confirmed_facts: Dict = None,
                 filter_candidates: Dict = None, schema: Dict = None):
        """
        Initialize the synthesizer.
        
        Args:
            llm_synthesizer: ConsultativeSynthesizer instance for LLM synthesis
            confirmed_facts: Dict of confirmed filter facts (status=active, etc.)
            filter_candidates: Dict of filter category → candidates
            schema: Schema metadata for suggestions
        """
        self.llm_synthesizer = llm_synthesizer
        self.confirmed_facts = confirmed_facts or {}
        self.filter_candidates = filter_candidates or {}
        self.schema = schema or {}
        
        # Store last gathered truths for LLM synthesis
        self._last_reality: List[Truth] = []
        self._last_intent: List[Truth] = []
        self._last_configuration: List[Truth] = []
        self._last_reference: List[Truth] = []
        self._last_regulatory: List[Truth] = []
        
        # v3.2: Store last consultative answer for rich metadata access
        self._last_consultative_answer = None
        
        # Track last executed SQL for provenance
        self.last_executed_sql: Optional[str] = None
    
    def synthesize(
        self,
        question: str,
        mode: IntelligenceMode,
        reality: List[Truth],
        intent: List[Truth],
        configuration: List[Truth],
        reference: List[Truth],
        regulatory: List[Truth],
        compliance: List[Truth],
        conflicts: List[Conflict],
        insights: List[Insight],
        compliance_check: Optional[Dict] = None,
        context: Dict = None,
        context_graph: Dict = None  # v3.0: Context Graph for relationship context
    ) -> SynthesizedAnswer:
        """
        Synthesize a consultative answer from all Five Truths.
        
        v3.0: Now accepts context_graph for relationship awareness.
        
        Args:
            question: The user's question
            mode: Intelligence mode (search, analyze, validate, etc.)
            reality: Truths from Reality (DuckDB data)
            intent: Truths from Intent (customer docs)
            configuration: Truths from Configuration (config tables)
            reference: Truths from Reference (product docs)
            regulatory: Truths from Regulatory (laws/compliance)
            compliance: Truths from Compliance checks
            conflicts: Detected conflicts between truths
            insights: Proactive insights discovered
            compliance_check: Results of compliance checking
            context: Additional context
            context_graph: Hub/spoke relationships and coverage info
            
        Returns:
            SynthesizedAnswer with full provenance
        """
        # Store for LLM synthesis
        self._last_reality = reality
        self._last_intent = intent
        self._last_configuration = configuration
        self._last_reference = reference
        self._last_regulatory = regulatory
        self._context_graph = context_graph  # v3.0
        
        # Store context for routing decisions
        self._context = context or {}
        
        reasoning = []
        
        # =====================================================================
        # v3.2: Smart Data Source Selection
        # Priority: DuckDB Reality (if has data rows) > ChromaDB Config docs
        # DuckDB config tables ARE in Reality, not Configuration (ChromaDB)
        # =====================================================================
        is_config = self._context.get('is_config', False)
        is_config_listing = self._is_config_listing_question(question.lower())
        
        # Extract Reality data first to check if it has actual rows
        reality_info = self._extract_data_info(reality) if reality else {'result_rows': []}
        reality_has_data = len(reality_info.get('result_rows', [])) > 0
        
        logger.warning(f"[SYNTHESIZE] Data source selection: is_config={is_config}, "
                      f"is_config_listing={is_config_listing}, "
                      f"reality_rows={len(reality_info.get('result_rows', []))}, "
                      f"config_truths={len(configuration)}")
        
        # Decide primary data source
        # PRIORITY: Reality data (DuckDB) over Configuration docs (ChromaDB)
        if reality_has_data:
            # Reality has actual data rows - use it
            data_info = reality_info
            reasoning.append(f"Found {len(reality)} data results with {len(data_info.get('result_rows', []))} rows")
        elif is_config_listing and configuration:
            # No Reality data, try Configuration docs (ChromaDB)
            logger.warning("[SYNTHESIZE] No Reality data - using Configuration docs")
            data_info = self._extract_data_info(configuration)
            reasoning.append(f"Config listing: Using {len(configuration)} configuration documents")
        else:
            # Default fallback
            data_info = reality_info
            reasoning.append(f"Found {len(reality)} data results (Reality)")
        
        # Extract document context
        doc_context = self._build_doc_context(intent, configuration)
        if intent:
            reasoning.append(f"Found {len(intent)} customer intent documents")
        if configuration:
            reasoning.append(f"Found {len(configuration)} configuration documents")
        
        # Extract reference library context
        reflib_context = self._build_reflib_context(reference, regulatory, compliance)
        if reference:
            reasoning.append(f"Found {len(reference)} reference documents")
        if regulatory:
            reasoning.append(f"Found {len(regulatory)} regulatory documents")
        if compliance:
            reasoning.append(f"Found {len(compliance)} compliance documents")
        
        # v3.2: Add entity gaps as insights
        entity_gaps = self._context.get('entity_gaps', [])
        if entity_gaps:
            reasoning.append(f"Found {len(entity_gaps)} entity gaps (config vs docs)")
            # Convert gaps to Insight objects for synthesis
            from .types import Insight
            for gap in entity_gaps[:5]:  # Limit to top 5 gaps
                gap_type = gap.get('gap_type', 'unknown')
                entity = gap.get('entity_type', 'unknown')
                if gap_type == 'config_only':
                    insights.append(Insight(
                        type='gap_detection',
                        title=f'Configured but not documented: {entity}',
                        description=f'{entity} is configured in the system but not mentioned in any reference documents',
                        severity='medium',
                        action_required=True
                    ))
                elif gap_type == 'docs_only':
                    insights.append(Insight(
                        type='gap_detection',
                        title=f'Documented but not configured: {entity}',
                        description=f'{entity} is mentioned in documents but not found in system configuration',
                        severity='high',
                        action_required=True
                    ))
        
        # Generate the response
        answer_text = self._generate_response(
            question=question,
            data_info=data_info,
            doc_context=doc_context,
            reflib_context=reflib_context,
            insights=insights,
            conflicts=conflicts,
            compliance_check=compliance_check
        )
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            reality, intent, configuration, reference, regulatory, compliance
        )
        
        return SynthesizedAnswer(
            question=question,
            answer=answer_text,
            confidence=confidence,
            from_reality=reality,
            from_intent=intent,
            from_configuration=configuration,
            from_reference=reference,
            from_regulatory=regulatory,
            from_compliance=compliance,
            conflicts=conflicts,
            insights=insights,
            compliance_check=compliance_check,
            structured_output=data_info.get('structured_output'),
            reasoning=reasoning,
            executed_sql=self.last_executed_sql
        )
    
    def get_consultative_metadata(self) -> Optional[Dict]:
        """
        Get rich metadata from last consultative synthesis.
        
        v3.2: Returns the full ConsultativeAnswer fields that were previously
        discarded. Enables excel_spec, proactive_offers, hcmpact_hook.
        
        Returns:
            Dict with: question_type, question_category, excel_spec, 
                      proactive_offers, hcmpact_hook, synthesis_method
            None if no consultative synthesis was performed
        """
        if not self._last_consultative_answer:
            return None
        
        ca = self._last_consultative_answer
        return {
            'question_type': getattr(ca, 'question_type', ''),
            'question_category': getattr(ca, 'question_category', ''),
            'excel_spec': getattr(ca, 'excel_spec', []),
            'proactive_offers': getattr(ca, 'proactive_offers', []),
            'hcmpact_hook': getattr(ca, 'hcmpact_hook', ''),
            'synthesis_method': getattr(ca, 'synthesis_method', ''),
            'recommended_actions': getattr(ca, 'recommended_actions', []),
        }
    
    def _extract_data_info(self, reality: List[Truth]) -> Dict:
        """Extract query results and metadata from reality truths."""
        info = {
            'query_type': 'list',
            'result_value': None,
            'result_rows': [],
            'result_columns': [],
            'data_context': [],
            'structured_output': None
        }
        
        if not reality:
            return info
        
        for truth in reality[:3]:
            if isinstance(truth.content, dict) and 'rows' in truth.content:
                rows = truth.content['rows']
                cols = truth.content['columns']
                query_type = truth.content.get('query_type', 'list')
                
                info['query_type'] = query_type
                info['result_columns'] = cols
                
                if query_type == 'count' and rows:
                    info['result_value'] = list(rows[0].values())[0] if rows[0] else 0
                    info['data_context'].append(f"COUNT RESULT: {info['result_value']}")
                elif query_type in ['sum', 'average'] and rows:
                    info['result_value'] = list(rows[0].values())[0] if rows[0] else 0
                    info['data_context'].append(f"{query_type.upper()} RESULT: {info['result_value']}")
                elif query_type == 'group' and rows:
                    info['result_rows'] = rows[:20]
                    info['data_context'].append(f"Grouped results: {len(rows)} groups")
                else:
                    info['result_rows'] = rows[:20]
                    info['data_context'].append(f"Found {len(rows)} rows with columns: {', '.join(cols[:8])}")
                
                # Build structured output
                info['structured_output'] = {
                    'type': 'data',
                    'sql': truth.content.get('sql'),
                    'rows': info['result_rows'],
                    'columns': info['result_columns'],
                    'total': len(rows)
                }
                break
        
        return info
    
    def _build_doc_context(self, intent: List[Truth], 
                          configuration: List[Truth]) -> List[str]:
        """Build document context from Intent and Configuration truths."""
        context = []
        
        for truth in intent[:2]:
            # Extract useful text from content
            content = truth.content
            if isinstance(content, dict):
                # For structured data, get summary or key info
                text = content.get('text', content.get('summary', ''))
                if not text and 'rows' in content:
                    text = f"{len(content.get('rows', []))} records from {truth.source_name}"
            else:
                text = str(content)
            context.append(f"Customer Intent ({truth.source_name}): {text[:200]}")
        
        for truth in configuration[:2]:
            content = truth.content
            if isinstance(content, dict):
                # For SQL results, summarize the query
                sql = content.get('sql', '')
                rows = content.get('rows', [])
                cols = content.get('columns', [])
                if sql and rows:
                    text = f"Query returned {len(rows)} records with columns: {', '.join(cols[:5])}"
                else:
                    text = content.get('text', content.get('summary', str(content)[:100]))
            else:
                text = str(content)
            context.append(f"Configuration ({truth.source_name}): {text[:200]}")
        
        return context
    
    def _build_reflib_context(self, reference: List[Truth], regulatory: List[Truth],
                             compliance: List[Truth]) -> List[str]:
        """Build reference library context."""
        context = []
        
        for truth in reference[:2]:
            content = truth.content
            if isinstance(content, dict):
                text = content.get('text', content.get('summary', ''))[:200]
            else:
                text = str(content)[:200]
            if text:
                context.append(f"Reference ({truth.source_name}): {text}")
        
        for truth in regulatory[:2]:
            content = truth.content
            if isinstance(content, dict):
                text = content.get('text', content.get('summary', ''))[:200]
            else:
                text = str(content)[:200]
            if text:
                context.append(f"Regulatory ({truth.source_name}): {text}")
        
        for truth in compliance[:2]:
            content = truth.content
            if isinstance(content, dict):
                text = content.get('text', content.get('summary', ''))[:200]
            else:
                text = str(content)[:200]
            if text:
                context.append(f"Compliance ({truth.source_name}): {text}")
        
        return context
    
    def _generate_response(
        self,
        question: str,
        data_info: Dict,
        doc_context: List[str],
        reflib_context: List[str],
        insights: List[Insight],
        conflicts: List[Conflict],
        compliance_check: Optional[Dict]
    ) -> str:
        """
        Generate the response text.
        
        ROUTING STRATEGY (v3.2):
        - INVENTORY/LIST questions → Template (LLM hallucinates data values)
        - ANALYSIS/VALIDATION questions → LLM (actual reasoning needed)
        
        This ensures data accuracy while preserving consultative analysis.
        """
        q_lower = question.lower()
        
        logger.warning(f"[SYNTHESIZE] _generate_response called, question: {question[:50]}")
        
        # =====================================================================
        # v3.2: SMART ROUTING - Template for data listing, LLM for analysis
        # LLM hallucinates when asked to list data values (makes up codes)
        # Template is reliable for "list all X" - just format the actual data
        # =====================================================================
        is_inventory_question = any(trigger in q_lower for trigger in [
            'list all', 'show all', 'what are my', 'what do i have',
            'give me all', 'show me all', "what's configured", 'what is setup',
            'list the', 'show the'
        ])
        
        result_rows = data_info.get('result_rows', [])
        
        # For inventory questions WITH data, use template (no hallucination risk)
        if is_inventory_question and result_rows:
            logger.warning(f"[SYNTHESIZE] Inventory question with {len(result_rows)} rows - using template (no LLM)")
            return self._generate_template_response(
                question, data_info, doc_context, reflib_context,
                insights, conflicts, compliance_check
            )
        
        # =====================================================================
        # For analysis/validation questions, try LLM synthesis
        # =====================================================================
        if self.llm_synthesizer:
            try:
                structured_data = {
                    'rows': data_info.get('result_rows', []),
                    'columns': data_info.get('result_columns', []),
                    'query_type': data_info.get('query_type', 'list'),
                    'sql': self.last_executed_sql or ''
                }
                
                # Handle count/sum/avg values
                if data_info.get('query_type') in ['count', 'sum', 'average']:
                    if data_info.get('result_value') is not None:
                        structured_data['rows'] = [{'result': data_info['result_value']}]
                        structured_data['columns'] = ['result']
                
                logger.warning("[SYNTHESIZE] Attempting LLM consultative synthesis...")
                
                consultative_answer = self.llm_synthesizer.synthesize(
                    question=question,
                    reality=self._last_reality,
                    intent=self._last_intent,
                    configuration=self._last_configuration,
                    reference=self._last_reference,
                    regulatory=self._last_regulatory,
                    conflicts=conflicts,
                    insights=insights,
                    structured_data=structured_data,
                    context_graph=getattr(self, '_context_graph', None)  # v3.0
                )
                
                logger.warning(f"[SYNTHESIZE] LLM synthesis SUCCESS: method={consultative_answer.synthesis_method}")
                
                # v3.2: Store rich answer metadata for caller to use
                self._last_consultative_answer = consultative_answer
                return consultative_answer.answer
                
            except Exception as e:
                logger.warning(f"[SYNTHESIZE] LLM synthesis failed: {e}, falling back to template")
        else:
            logger.warning("[SYNTHESIZE] No LLM synthesizer available, using template")
        
        # =====================================================================
        # FALLBACK: Template-based response (only if LLM fails)
        # =====================================================================
        logger.warning("[SYNTHESIZE] Using template fallback")
        return self._generate_template_response(
            question, data_info, doc_context, reflib_context,
            insights, conflicts, compliance_check
        )
    
    def _generate_template_response(
        self,
        question: str,
        data_info: Dict,
        doc_context: List[str],
        reflib_context: List[str],
        insights: List[Insight],
        conflicts: List[Conflict],
        compliance_check: Optional[Dict]
    ) -> str:
        """Generate template-based response as fallback."""
        parts = []
        
        query_type = data_info.get('query_type', 'list')
        result_value = data_info.get('result_value')
        result_rows = data_info.get('result_rows', [])
        result_columns = data_info.get('result_columns', [])
        
        status_filter = self.confirmed_facts.get('status', '')
        q_lower = question.lower()
        
        # =====================================================================
        # v3.1: Detect config listing - use cleaner format without "Reality" label
        # =====================================================================
        is_config_listing = self._is_config_listing_question(q_lower)
        
        if is_config_listing and result_rows:
            # Config listing gets dedicated clean format
            config_response = self._format_config_listing(q_lower, result_rows, result_columns)
            if config_response:
                parts.append(config_response)
            else:
                # Fallback to simple table
                parts.append(f"Found **{len(result_rows):,}** configured items:\n")
                parts.extend(self._format_table(result_rows[:15], result_columns[:6]))
                if len(result_rows) > 15:
                    parts.append(f"\n*Showing first 15 of {len(result_rows):,} results*")
            
            # For config listings, skip the noisy truth sections - just add relevant reference
            ref_docs = [d for d in reflib_context if 'Reference' in d]
            if ref_docs:
                parts.append("\n\n📚 **Related Documentation:**")
                for doc in ref_docs[:1]:  # Just top 1
                    content = doc.split('): ', 1)[-1] if '): ' in doc else doc
                    # Extract just the first sentence
                    first_sentence = content.split('. ')[0][:150]
                    parts.append(f"- {first_sentence}...")
            
            return "\n".join(parts)
        
        # =====================================================================
        # Standard response format for non-config questions
        # =====================================================================
        
        # REALITY section
        if query_type == 'count' and result_value is not None:
            try:
                count = int(result_value)
                if status_filter == 'active':
                    parts.append(f"📊 **Reality:** You have **{count:,} active employees**.")
                elif status_filter == 'termed':
                    parts.append(f"📊 **Reality:** Your data shows **{count:,} terminated employees**.")
                else:
                    parts.append(f"📊 **Reality:** Found **{count:,}** matching records.")
            except (ValueError, TypeError):
                parts.append(f"📊 **Reality:** Count = **{result_value}**")
        
        elif query_type in ['sum', 'average'] and result_value is not None:
            try:
                val = float(result_value)
                parts.append(f"📊 **Reality:** {query_type.title()} = **{val:,.2f}**")
            except (ValueError, TypeError):
                parts.append(f"📊 **Reality:** {query_type.title()} = **{result_value}**")
        
        elif query_type == 'group' and result_rows:
            parts.append(f"📊 **Reality:** Breakdown by {result_columns[0] if result_columns else 'category'}:\n")
            parts.extend(self._format_table(result_rows[:15], result_columns[:4]))
            if len(result_rows) > 15:
                parts.append(f"\n*Showing top 15 of {len(result_rows):,} groups*")
        
        elif result_rows:
            parts.append(f"📊 **Reality:** Found **{len(result_rows):,}** matching records\n")
            parts.extend(self._format_table(result_rows[:12], result_columns[:6]))
            if len(result_rows) > 12:
                parts.append(f"\n*Showing first 12 of {len(result_rows):,} results*")
        else:
            parts.append("📊 **Reality:** No data found matching your criteria.")
        
        # Document context sections
        self._add_truth_sections(parts, doc_context, reflib_context)
        
        # Compliance findings
        if compliance_check:
            if compliance_check.get('findings'):
                parts.append("\n\n🚨 **Compliance Findings:**")
                for finding in compliance_check['findings'][:5]:
                    parts.append(f"- {finding}")
            if compliance_check.get('gaps'):
                parts.append("\n\n⚠️ **Compliance Gaps:**")
                for gap in compliance_check['gaps'][:5]:
                    parts.append(f"- {gap}")
        
        # Insights
        if insights:
            parts.append("\n\n---\n💡 **Insights:**")
            for insight in insights[:3]:
                icon = '🔴' if insight.severity == 'high' else '🟡' if insight.severity == 'medium' else '💡'
                parts.append(f"\n{icon} **{insight.title}**: {insight.description}")
        
        # Conflicts
        if conflicts:
            parts.append("\n\n---\n⚖️ **Cross-Truth Analysis:**")
            for conflict in conflicts[:5]:
                icon = '🔴' if conflict.severity in ['critical', 'high'] else '🟡' if conflict.severity == 'medium' else '💡'
                parts.append(f"\n{icon} {conflict.description}")
                if conflict.recommendation:
                    parts.append(f"   → *{conflict.recommendation}*")
        
        return "\n".join(parts)
    
    def _is_config_listing_question(self, q_lower: str) -> bool:
        """Detect if this is a configuration listing question."""
        listing_triggers = [
            'what', 'show', 'list', 'display', 'give me',
            'setup', 'configured', 'available', 'currently'
        ]
        config_domains = [
            'earning', 'deduction', 'benefit', 'tax', 'location',
            'job', 'pay group', 'bank', 'pto', 'accrual', 'gl',
            'organization', 'company', 'code'
        ]
        
        has_listing = any(t in q_lower for t in listing_triggers)
        has_domain = any(d in q_lower for d in config_domains)
        
        return has_listing and has_domain
    
    def _format_config_listing(self, q_lower: str, rows: List[Dict], 
                               columns: List[str]) -> Optional[str]:
        """
        Format configuration data consultatively.
        
        Identifies code, description, and category columns,
        then groups and formats like a senior consultant would.
        """
        if not rows or not columns:
            return None
        
        logger.warning(f"[SYNTHESIZE] Config listing columns: {columns[:10]}")
        
        # =====================================================================
        # v3.2: Domain-aware column detection
        # Prioritize domain-specific columns over generic ones
        # =====================================================================
        domain = self._detect_domain(q_lower)
        
        # Domain-specific code column patterns (checked first)
        domain_code_patterns = {
            'deduction': ['deductionbenefit_code', 'deduction_code', 'benefit_code', 'ded_code'],
            'earning': ['earnings_code', 'earning_code', 'earn_code'],
            'tax': ['tax_code', 'tax_id'],
            'location': ['location_code', 'loc_code', 'site_code'],
            'job': ['job_code', 'job_id', 'position_code'],
            'bank': ['bank_code', 'bank_id'],
            'pto': ['pto_code', 'accrual_code'],
            'gl': ['gl_code', 'account_code'],
        }
        
        # Domain-specific description column patterns
        domain_desc_patterns = {
            'deduction': ['deductionbenefit', 'deduction_description', 'benefit_name', 'deductionbenefit_long'],
            'earning': ['earnings', 'earning_description', 'earning_name', 'earnings_long'],
            'tax': ['tax_description', 'tax_name'],
            'location': ['location_description', 'location_name', 'loc_name'],
            'job': ['job_description', 'job_name', 'job_title'],
            'bank': ['bank_name', 'bank_description'],
        }
        
        # Try domain-specific patterns first
        code_col = None
        desc_col = None
        
        if domain in domain_code_patterns:
            code_col = self._find_column(columns, domain_code_patterns[domain])
        if domain in domain_desc_patterns:
            desc_col = self._find_column(columns, domain_desc_patterns[domain])
        
        # Fall back to generic patterns (but exclude country_code, state_code, etc.)
        if not code_col:
            # EXCLUDE geographic codes from being the main code column
            generic_code_patterns = ['code', 'id']
            exclude_patterns = ['country', 'state', 'zip', 'postal', 'address', 'region']
            
            for col in columns:
                col_lower = col.lower()
                # Must contain 'code' or 'id' but NOT be a geographic column
                has_code = any(p in col_lower for p in generic_code_patterns)
                is_geographic = any(p in col_lower for p in exclude_patterns)
                if has_code and not is_geographic:
                    code_col = col
                    break
        
        if not desc_col:
            desc_col = self._find_column(columns, [
                'description', 'name', 'label', 'long_description', 'desc', 'long'
            ])
        
        # If code_col same as desc_col, clear desc_col
        if code_col and desc_col and code_col == desc_col:
            desc_col = None
        
        # Category/type column for grouping
        category_col = self._find_column(columns, [
            'group', 'group_code', 'category', 'type', 'class',
            'deductionbenefit_group', 'deductionbenefit_group_code',
            'earnings_group', 'earning_type', 'calc_type'
        ])
        
        logger.warning(f"[SYNTHESIZE] Detected columns - code: {code_col}, desc: {desc_col}, category: {category_col}")
        
        # If no code column found, try to detect it from data
        if not code_col:
            code_col = self._detect_code_column(rows, columns)
            logger.warning(f"[SYNTHESIZE] Auto-detected code column: {code_col}")
        
        # Determine what we're listing
        domain = self._detect_domain(q_lower)
        domain_label = domain.title() if domain else "Configuration"
        
        # Build consultative response
        parts = []
        total = len(rows)
        
        # Header with count
        parts.append(f"You have **{total}** {domain_label.lower()} codes configured:\n")
        
        # If we have a category column, group by it
        if category_col and code_col:
            grouped = self._group_by_category(rows, category_col, code_col, desc_col)
            
            for category, items in grouped.items():
                cat_display = category if category else "Uncategorized"
                parts.append(f"\n**{cat_display}** ({len(items)})")
                
                # Show up to 8 items per category
                for item in items[:8]:
                    code = item.get('code', '')
                    desc = item.get('desc', '')
                    if desc and desc != code:
                        parts.append(f"- `{code}` - {desc[:50]}")
                    else:
                        parts.append(f"- `{code}`")
                
                if len(items) > 8:
                    parts.append(f"- *...and {len(items) - 8} more*")
        
        elif code_col:
            # No category, just list codes
            codes = []
            for row in rows[:50]:
                code_val = str(row.get(code_col, ''))[:20]
                if code_val and code_val not in codes:
                    codes.append(code_val)
            
            # Show in organized chunks
            parts.append("\n**Configured codes:**")
            for i in range(0, min(len(codes), 30), 10):
                chunk = codes[i:i+10]
                parts.append(f"{', '.join(f'`{c}`' for c in chunk if c)}")
            
            if total > 50:
                parts.append(f"\n*Showing {len(codes)} unique codes from {total} total records*")
        
        else:
            # Can't identify structure, return None to fall back to table
            logger.warning("[SYNTHESIZE] Could not identify code column, falling back to table")
            return None
        
        return "\n".join(parts)
    
    def _detect_code_column(self, rows: List[Dict], columns: List[str]) -> Optional[str]:
        """
        Auto-detect which column contains the actual codes.
        
        Codes are typically:
        - Short strings (2-15 chars)
        - Alphanumeric, often uppercase
        - High cardinality (many unique values)
        """
        if not rows or not columns:
            return None
        
        best_col = None
        best_score = 0
        
        for col in columns:
            # Sample values from this column
            values = [str(row.get(col, '')) for row in rows[:20] if row.get(col)]
            if not values:
                continue
            
            # Score this column
            score = 0
            
            # Prefer columns with "code" in name
            if 'code' in col.lower():
                score += 50
            
            # Check value characteristics
            avg_len = sum(len(v) for v in values) / len(values)
            unique_ratio = len(set(values)) / len(values)
            
            # Codes are usually short (2-15 chars)
            if 2 <= avg_len <= 15:
                score += 30
            elif avg_len > 50:
                score -= 20  # Likely description
            
            # Codes typically have high uniqueness
            if unique_ratio > 0.8:
                score += 20
            
            # Check if values look like codes (alphanumeric, often uppercase)
            uppercase_ratio = sum(1 for v in values if v.isupper() or v.replace('_', '').replace('-', '').isalnum()) / len(values)
            if uppercase_ratio > 0.7:
                score += 20
            
            # Numeric-only columns are usually IDs, not codes
            numeric_ratio = sum(1 for v in values if v.isdigit()) / len(values)
            if numeric_ratio > 0.9:
                score -= 30  # Likely ID column
            
            if score > best_score:
                best_score = score
                best_col = col
        
        return best_col if best_score > 20 else None
    
    def _find_column(self, columns: List[str], patterns: List[str]) -> Optional[str]:
        """Find a column matching any of the patterns."""
        cols_lower = {c.lower(): c for c in columns}
        
        # Exact match first
        for pattern in patterns:
            if pattern in cols_lower:
                return cols_lower[pattern]
        
        # Partial match
        for pattern in patterns:
            for col_lower, col_orig in cols_lower.items():
                if pattern in col_lower:
                    return col_orig
        
        return None
    
    def _detect_domain(self, q_lower: str) -> str:
        """Detect the configuration domain from the question."""
        domains = {
            'earning': ['earning', 'earnings', 'pay code'],
            'deduction': ['deduction', 'deductions', 'benefit plan'],
            'tax': ['tax', 'taxes', 'sui', 'futa'],
            'location': ['location', 'locations', 'site'],
            'job': ['job', 'jobs', 'position'],
            'bank': ['bank', 'banks'],
            'pto': ['pto', 'accrual', 'time off'],
            'gl': ['gl', 'general ledger', 'account'],
        }
        
        for domain, triggers in domains.items():
            if any(t in q_lower for t in triggers):
                return domain
        
        return "configuration"
    
    def _group_by_category(self, rows: List[Dict], category_col: str,
                          code_col: str, desc_col: Optional[str]) -> Dict[str, List[Dict]]:
        """Group rows by category."""
        from collections import defaultdict
        
        grouped = defaultdict(list)
        
        for row in rows:
            category = str(row.get(category_col, 'Other'))[:30]
            code = str(row.get(code_col, ''))
            desc = str(row.get(desc_col, '')) if desc_col else ''
            
            if code:  # Only include if we have a code
                grouped[category].append({
                    'code': code,
                    'desc': desc
                })
        
        # Sort categories by count (most first)
        return dict(sorted(grouped.items(), key=lambda x: -len(x[1])))
    
    def _format_table(self, rows: List[Dict], columns: List[str]) -> List[str]:
        """Format rows as a markdown table."""
        if not rows or not columns:
            return []
        
        parts = []
        header = " | ".join(columns)
        parts.append(f"| {header} |")
        parts.append("|" + "---|" * len(columns))
        
        for row in rows:
            vals = []
            for col in columns:
                v = row.get(col, '')
                if isinstance(v, (int, float)) and col.lower() in ['count', 'count(*)', 'total']:
                    vals.append(f"{int(v):,}")
                else:
                    vals.append(str(v)[:30])
            parts.append(f"| {' | '.join(vals)} |")
        
        return parts
    
    def _add_truth_sections(self, parts: List[str], doc_context: List[str],
                          reflib_context: List[str]):
        """Add sections for each truth type."""
        intent_docs = [d for d in doc_context if 'Customer Intent' in d]
        if intent_docs:
            parts.append("\n\n📋 **Customer Intent:**")
            for doc in intent_docs[:2]:
                content = doc.split('): ', 1)[-1] if '): ' in doc else doc
                parts.append(f"- {content[:300]}")
        
        config_docs = [d for d in doc_context if 'Configuration' in d]
        if config_docs:
            parts.append("\n\n⚙️ **Configuration:**")
            for doc in config_docs[:2]:
                content = doc.split('): ', 1)[-1] if '): ' in doc else doc
                parts.append(f"- {content[:300]}")
        
        ref_docs = [d for d in reflib_context if 'Reference' in d]
        if ref_docs:
            parts.append("\n\n📚 **Reference:**")
            for doc in ref_docs[:2]:
                content = doc.split('): ', 1)[-1] if '): ' in doc else doc
                parts.append(f"- {content[:300]}")
        
        reg_docs = [d for d in reflib_context if 'Regulatory' in d]
        if reg_docs:
            parts.append("\n\n⚖️ **Regulatory:**")
            for doc in reg_docs[:2]:
                content = doc.split('): ', 1)[-1] if '): ' in doc else doc
                parts.append(f"- {content[:300]}")
    
    def _calculate_confidence(self, reality, intent, configuration,
                            reference, regulatory, compliance) -> float:
        """Calculate confidence score based on available truths."""
        confidence = 0.5
        if reality:
            confidence += 0.2
        if intent:
            confidence += 0.1
        if configuration:
            confidence += 0.05
        if reference:
            confidence += 0.05
        if regulatory:
            confidence += 0.05
        if compliance:
            confidence += 0.05
        return min(confidence, 0.95)
