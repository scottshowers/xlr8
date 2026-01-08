"""
XLR8 Intelligence Engine - Synthesizer
=======================================
VERSION: 4.0.0 - Hybrid Approach (Template + LLM Overlay)

Synthesizes responses from all Five Truths into consultative answers.

This is where the magic happens - combining Reality, Intent, Configuration,
Reference, and Regulatory data into actionable insights like a senior consultant.

v4.0 HYBRID STRATEGY:
- Template generates DATA LISTING (accurate, no hallucination)
- LLM adds CONSULTANT OVERLAY (gap analysis, risks, proactive offers)
- Best of both worlds: accurate data + expert insight

Deploy to: backend/utils/intelligence/synthesizer.py
"""

import logging
from typing import Dict, List, Optional, Any

from .types import (
    Truth, Conflict, Insight, SynthesizedAnswer, IntelligenceMode
)

logger = logging.getLogger(__name__)

# Import response patterns for consultant thinking
PATTERNS_AVAILABLE = False
detect_question_type = None
generate_thinking_prompt = None
try:
    from backend.utils.response_patterns import (
        detect_question_type,
        generate_thinking_prompt,
        ResponsePattern
    )
    PATTERNS_AVAILABLE = True
    logger.info("[SYNTHESIZER] Response patterns loaded")
except ImportError:
    try:
        from utils.response_patterns import (
            detect_question_type,
            generate_thinking_prompt,
            ResponsePattern
        )
        PATTERNS_AVAILABLE = True
        logger.info("[SYNTHESIZER] Response patterns loaded (alt path)")
    except ImportError:
        logger.warning("[SYNTHESIZER] Response patterns not available")

# Log version on import
logger.warning("[SYNTHESIZER] Module loaded - VERSION 4.0.0 (Hybrid Approach)")


class Synthesizer:
    """
    Synthesizes responses from Five Truths into consultative answers.
    
    v4.0 HYBRID STRATEGY:
    1. Template generates accurate data listing (no LLM hallucination)
    2. LLM adds consultant overlay (analysis, gaps, risks, proactive offers)
    
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
                 filter_candidates: Dict = None, schema: Dict = None,
                 structured_handler=None):
        """
        Initialize the synthesizer.
        
        Args:
            llm_synthesizer: ConsultativeSynthesizer instance for LLM synthesis
            confirmed_facts: Dict of confirmed filter facts (status=active, etc.)
            filter_candidates: Dict of filter category → candidates
            schema: Schema metadata for suggestions
            structured_handler: DuckDB handler for running queries (v4.4)
        """
        self.llm_synthesizer = llm_synthesizer
        self.confirmed_facts = confirmed_facts or {}
        self.filter_candidates = filter_candidates or {}
        self.schema = schema or {}
        self.structured_handler = structured_handler  # v4.4: For hub usage analysis
        
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
        
        # v4.2: Store context_graph for entity context
        self._context_graph: Dict = None
        
        # v4.4: Store project for usage queries
        self._project: str = None
    
    def _get_entity_context(self, table_name: str, columns: List[str]) -> str:
        """
        v4.2: Build rich entity context from available metadata.
        
        This is what makes the LLM smart - understanding:
        - What TYPE of entity this is (earnings, deductions, etc.)
        - What columns are EXPECTED vs what's present
        - Column semantics (which column is the code, which is description)
        - What's NORMAL for this entity type
        
        Returns context string for LLM prompt.
        """
        context_parts = []
        
        # Find table in schema
        table_info = None
        for t in self.schema.get('tables', []):
            if t.get('table_name', '').lower() == table_name.lower():
                table_info = t
                break
        
        if not table_info:
            return ""
        
        # 1. Entity type and display name
        display_name = table_info.get('display_name', '')
        truth_type = table_info.get('truth_type', 'unknown')
        
        if display_name:
            context_parts.append(f"Entity: {display_name}")
        context_parts.append(f"Data type: {truth_type.upper() if truth_type else 'Configuration'} table")
        
        # 2. Infer entity type from table name
        table_lower = table_name.lower()
        entity_semantics = self._infer_entity_semantics(table_lower, columns)
        if entity_semantics:
            context_parts.append(f"\n{entity_semantics}")
        
        # 3. Column profiles - what columns mean
        column_profiles = table_info.get('column_profiles', {})
        if column_profiles:
            context_parts.append("\nColumn semantics:")
            for col_name, profile in list(column_profiles.items())[:10]:
                col_type = profile.get('inferred_type', 'unknown')
                distinct = profile.get('distinct_count', '?')
                is_cat = profile.get('is_categorical', False)
                filter_cat = profile.get('filter_category', '')
                
                desc = f"  • {col_name}: {col_type}"
                if is_cat:
                    desc += f" (categorical, {distinct} values)"
                if filter_cat:
                    desc += f" [filter: {filter_cat}]"
                context_parts.append(desc)
        
        # 4. Context graph - hub/spoke role
        if self._context_graph:
            hubs = self._context_graph.get('hubs', [])
            for hub in hubs:
                if hub.get('table', '').lower() == table_lower:
                    sem_type = hub.get('semantic_type', '')
                    has_spokes = hub.get('has_reality_spokes', False)
                    context_parts.append(f"\nData model role: This is the MASTER {sem_type} table (hub)")
                    if has_spokes:
                        context_parts.append("  → Has transactional data referencing these codes")
                    break
        
        return "\n".join(context_parts)
    
    def _infer_entity_semantics(self, table_name: str, columns: List[str]) -> str:
        """
        Infer what this entity IS and what columns MEAN based on domain knowledge.
        
        This encodes consultant knowledge about HCM data structures.
        """
        cols_lower = [c.lower() for c in columns]
        
        # Earnings tables
        if 'earning' in table_name:
            semantics = ["EARNINGS TABLE - defines pay codes employees can receive"]
            semantics.append("Key columns typically include:")
            semantics.append("  • earnings_code/earning_code: Unique identifier for the earning type")
            semantics.append("  • description/earning: Display name for the earning")
            semantics.append("  • regular_pay: FLAG (boolean) - only ONE earning per group can be marked as regular pay. NULLs are normal.")
            semantics.append("  • earnings_group: Logical grouping of related earnings")
            if 'waiting_period' in cols_lower:
                semantics.append("  • waiting_period: Days before earning takes effect")
            if 'auto_add' in cols_lower:
                semantics.append("  • auto_add: Whether earning is automatically assigned to new hires")
            return "\n".join(semantics)
        
        # Deductions tables
        if 'deduction' in table_name or 'benefit' in table_name:
            semantics = ["DEDUCTIONS/BENEFITS TABLE - defines withholdings from employee pay"]
            semantics.append("Key columns typically include:")
            semantics.append("  • deduction_code: Unique identifier")
            semantics.append("  • plan_type: Category (medical, dental, 401k, etc.)")
            semantics.append("  • employee_contribution: Amount/rate deducted from employee")
            semantics.append("  • employer_contribution: Amount/rate paid by employer")
            return "\n".join(semantics)
        
        # Tax tables
        if 'tax' in table_name or 'fit' in table_name or 'sit' in table_name:
            semantics = ["TAX TABLE - tax jurisdiction and withholding configuration"]
            semantics.append("Common tax types: FIT (Federal), SIT (State), LIT (Local)")
            return "\n".join(semantics)
        
        # Workers comp
        if 'worker' in table_name and 'comp' in table_name:
            semantics = ["WORKERS COMPENSATION TABLE - WC class codes and rates"]
            semantics.append("Key columns:")
            semantics.append("  • wc_code/class_code: State-assigned classification code")
            semantics.append("  • employer_rate: Rate paid by employer per $100 of payroll")
            semantics.append("  • employee_rate: Rate (if any) deducted from employee - often 0")
            return "\n".join(semantics)
        
        # Locations
        if 'location' in table_name:
            semantics = ["LOCATIONS TABLE - work locations and addresses"]
            return "\n".join(semantics)
        
        # Jobs/positions  
        if 'job' in table_name or 'position' in table_name:
            semantics = ["JOBS TABLE - job codes and position definitions"]
            return "\n".join(semantics)
        
        return ""
    
    def _get_domain_rules(self, table_name: str) -> str:
        """
        v4.3: Generate domain-specific rules to prevent LLM hallucination.
        
        These rules are added directly to the prompt to stop the LLM from
        flagging normal configuration as problems.
        """
        table_lower = table_name.lower()
        
        if 'earning' in table_lower:
            return """
EARNINGS-SPECIFIC RULES (CRITICAL - DO NOT VIOLATE):
• regular_pay NULL/empty is CORRECT - only 1 earning per group should have this set
• waiting_period = 0 is VALID - means no waiting period required  
• auto_add empty is VALID - means manual assignment
• Different codes with similar names (HSA2E vs HSAER) often serve different purposes
• DO NOT report these as "findings" or "issues" - they are NORMAL"""
        
        if 'deduction' in table_lower or 'benefit' in table_lower:
            return """
DEDUCTIONS-SPECIFIC RULES (CRITICAL - DO NOT VIOLATE):
• Empty contribution fields may be valid (employer-only or employee-only plans)
• Multiple plans with similar names often serve different employee groups
• DO NOT report empty optional fields as problems"""
        
        if 'tax' in table_lower:
            return """
TAX-SPECIFIC RULES (CRITICAL - DO NOT VIOLATE):
• Tax configurations vary by jurisdiction - empty fields may be valid
• Not all tax types apply to all employees"""
        
        return ""
    
    def _get_hub_usage_analysis(self, table_name: str, code_column: str, 
                                 result_rows: List[Dict]) -> Optional[str]:
        """
        v4.4: Analyze hub usage by querying spoke (Reality) tables.
        
        For a hub table like earnings_earnings, this finds employee-level
        spoke tables and counts how many employees have each code assigned.
        
        Returns formatted usage analysis or None if no spoke data.
        """
        if not self.structured_handler or not self._context_graph or not self._project:
            logger.debug("[SYNTHESIZE] Cannot run hub usage analysis - missing handler/graph/project")
            return None
        
        # Find this table's semantic type in the hub list
        hub_info = None
        for hub in self._context_graph.get('hubs', []):
            if hub.get('table', '').lower() == table_name.lower():
                hub_info = hub
                break
        
        if not hub_info:
            logger.debug(f"[SYNTHESIZE] Table {table_name} is not a hub")
            return None
        
        semantic_type = hub_info.get('semantic_type', '')
        logger.warning(f"[SYNTHESIZE] Hub usage analysis for {semantic_type} in {table_name}")
        
        # Find Reality spoke tables that reference this hub
        reality_spokes = []
        for rel in self._context_graph.get('relationships', []):
            if (rel.get('hub_table', '').lower() == table_name.lower() and 
                rel.get('truth_type') == 'reality'):
                reality_spokes.append(rel)
        
        if not reality_spokes:
            logger.debug(f"[SYNTHESIZE] No Reality spokes found for hub {table_name}")
            return None
        
        logger.warning(f"[SYNTHESIZE] Found {len(reality_spokes)} Reality spokes")
        
        # Build usage counts from the first spoke table
        # (typically the employee-level assignment table)
        spoke = reality_spokes[0]
        spoke_table = spoke.get('spoke_table', '')
        spoke_column = spoke.get('spoke_column', '')
        
        if not spoke_table or not spoke_column:
            return None
        
        try:
            # Count occurrences in spoke table
            count_sql = f'''
                SELECT "{spoke_column}" as code, COUNT(*) as employee_count
                FROM "{spoke_table}"
                WHERE "{spoke_column}" IS NOT NULL
                GROUP BY "{spoke_column}"
                ORDER BY employee_count DESC
            '''
            
            count_result = self.structured_handler.conn.execute(count_sql).fetchall()
            
            # Build lookup: code -> count
            usage_counts = {row[0]: row[1] for row in count_result}
            
            # Get total employees with any assignment
            total_with = sum(usage_counts.values())
            
            # Get unique employee count (assuming there's an employee_id-like column)
            unique_sql = f'SELECT COUNT(DISTINCT "{spoke_column}") FROM "{spoke_table}"'
            # This gives unique codes used, not unique employees
            
            # Format the analysis
            analysis_parts = []
            analysis_parts.append("\n📊 **Usage Analysis** (from employee data):")
            
            # Codes in use
            used_codes = []
            unused_codes = []
            
            # Extract code column from result_rows
            hub_codes = set()
            for row in result_rows:
                # Try to find the code value
                for key in row.keys():
                    if 'code' in key.lower():
                        hub_codes.add(row[key])
                        break
            
            for code in hub_codes:
                count = usage_counts.get(code, 0)
                if count > 0:
                    used_codes.append((code, count))
                else:
                    unused_codes.append(code)
            
            # Sort by count descending
            used_codes.sort(key=lambda x: x[1], reverse=True)
            
            if used_codes:
                analysis_parts.append(f"• **{len(used_codes)} codes in active use:**")
                for code, count in used_codes[:5]:  # Top 5
                    analysis_parts.append(f"  - `{code}`: {count} employees")
                if len(used_codes) > 5:
                    analysis_parts.append(f"  - *...and {len(used_codes) - 5} more*")
            
            if unused_codes:
                analysis_parts.append(f"• **{len(unused_codes)} codes configured but UNUSED:**")
                for code in unused_codes[:5]:
                    analysis_parts.append(f"  - `{code}` (0 employees)")
                if len(unused_codes) > 5:
                    analysis_parts.append(f"  - *...and {len(unused_codes) - 5} more*")
            
            if not used_codes and not unused_codes:
                analysis_parts.append("• No usage data available")
            
            logger.warning(f"[SYNTHESIZE] Usage analysis: {len(used_codes)} used, {len(unused_codes)} unused")
            return "\n".join(analysis_parts)
            
        except Exception as e:
            logger.warning(f"[SYNTHESIZE] Hub usage analysis failed: {e}")
            return None
    
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
        self._project = self._context.get('project', None)  # v4.4: For usage analysis
        
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
            'structured_output': None,
            'table_name': None  # v4.2: Track source table
        }
        
        if not reality:
            return info
        
        for truth in reality[:3]:
            if isinstance(truth.content, dict) and 'rows' in truth.content:
                rows = truth.content['rows']
                cols = truth.content['columns']
                query_type = truth.content.get('query_type', 'list')
                table_name = truth.content.get('table', '')  # v4.2
                
                info['query_type'] = query_type
                info['result_columns'] = cols
                info['table_name'] = table_name  # v4.2
                
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
        
        v4.0 HYBRID STRATEGY:
        1. Template generates DATA LISTING (accurate, no hallucination)
        2. LLM adds CONSULTANT OVERLAY (analysis, gaps, risks, proactive offers)
        
        This ensures data accuracy while delivering consultant-level insight.
        """
        q_lower = question.lower()
        
        logger.warning(f"[SYNTHESIZE] _generate_response called, question: {question[:50]}")
        
        # =====================================================================
        # STEP 1: Generate Template Response (accurate data listing)
        # =====================================================================
        template_response = self._generate_template_response(
            question, data_info, doc_context, reflib_context,
            insights, conflicts, compliance_check
        )
        
        result_rows = data_info.get('result_rows', [])
        table_name = data_info.get('table_name', '')
        result_columns = data_info.get('result_columns', [])
        
        # =====================================================================
        # STEP 1.5: Add Hub Usage Analysis (if this is a hub table)
        # v4.4: Show how config codes are used in employee data
        # =====================================================================
        if result_rows and table_name:
            # Find code column
            code_col = None
            for col in result_columns:
                if 'code' in col.lower():
                    code_col = col
                    break
            
            if code_col:
                usage_analysis = self._get_hub_usage_analysis(table_name, code_col, result_rows)
                if usage_analysis:
                    # Insert usage analysis after template response
                    template_response = template_response + "\n" + usage_analysis
                    logger.warning(f"[SYNTHESIZE] Added hub usage analysis")
        
        # =====================================================================
        # STEP 2: Add Consultant Overlay via LLM
        # LLM enhances with analysis but CANNOT modify the data
        # =====================================================================
        if self.llm_synthesizer and result_rows:
            try:
                logger.warning(f"[SYNTHESIZE] v4.0 Hybrid: Adding consultant overlay...")
                logger.warning(f"[SYNTHESIZE] data_info keys: {list(data_info.keys())}")
                logger.warning(f"[SYNTHESIZE] data_info table_name: '{data_info.get('table_name', 'MISSING')}'")
                
                enhanced_response = self._add_consultant_overlay(
                    question=question,
                    template_response=template_response,
                    data_info=data_info,
                    doc_context=doc_context,
                    reflib_context=reflib_context,
                    insights=insights,
                    conflicts=conflicts
                )
                
                if enhanced_response:
                    logger.warning("[SYNTHESIZE] Consultant overlay applied successfully")
                    return enhanced_response
                else:
                    logger.warning("[SYNTHESIZE] Overlay failed, using template only")
                    
            except Exception as e:
                logger.warning(f"[SYNTHESIZE] Consultant overlay error: {e}")
        
        # Fallback to template-only response
        return template_response
    
    def _add_consultant_overlay(
        self,
        question: str,
        template_response: str,
        data_info: Dict,
        doc_context: List[str],
        reflib_context: List[str],
        insights: List[Insight],
        conflicts: List[Conflict]
    ) -> Optional[str]:
        """
        v4.0: Add consultant-level analysis overlay to template response.
        
        Uses Response Patterns to guide the LLM's thinking:
        - Pattern's hunt_for → Gap Analysis targets
        - Pattern's hidden_worry → Risk framing
        - Pattern's proactive_offers → Next steps
        - Pattern's hcmpact_hook → Support path
        
        Returns:
        - Enhanced response with consultant overlay
        - None if overlay fails (caller uses template)
        """
        if not self.llm_synthesizer:
            return None
        
        # =====================================================================
        # v4.0: Detect question type and get response pattern
        # =====================================================================
        pattern = None
        if PATTERNS_AVAILABLE and detect_question_type:
            try:
                pattern = detect_question_type(question)
                logger.warning(f"[SYNTHESIZE] Pattern detected: {pattern.question_type} ({pattern.category.value})")
            except Exception as e:
                logger.warning(f"[SYNTHESIZE] Pattern detection failed: {e}")
        
        # =====================================================================
        # v4.1: Build GROUNDED context - actual data rows for analysis
        # =====================================================================
        context_parts = []
        
        # v4.2: Add entity context FIRST - this tells LLM what this data IS
        table_name = data_info.get('table_name', '')
        result_columns = data_info.get('result_columns', [])
        domain_rules = ""  # v4.3: Domain-specific anti-hallucination rules
        
        logger.warning(f"[SYNTHESIZE] Entity context check: table_name='{table_name}', columns={len(result_columns)}")
        
        if table_name:
            entity_context = self._get_entity_context(table_name, result_columns)
            if entity_context:
                context_parts.append("=== ENTITY CONTEXT (what this data means) ===")
                context_parts.append(entity_context)
                logger.warning(f"[SYNTHESIZE] Added entity context for {table_name}")
            else:
                logger.warning(f"[SYNTHESIZE] No entity context generated for {table_name}")
            
            # v4.3: Generate domain-specific anti-hallucination rules
            domain_rules = self._get_domain_rules(table_name)
            if domain_rules:
                logger.warning(f"[SYNTHESIZE] Added domain rules for {table_name[:30]}")
        else:
            logger.warning("[SYNTHESIZE] No table_name in data_info - cannot add entity context")
        
        # CRITICAL: Include actual data rows so LLM can analyze real values
        result_rows = data_info.get('result_rows', [])
        if result_rows:
            context_parts.append("=== ACTUAL DATA FROM DATABASE ===")
            context_parts.append(f"Columns: {', '.join(result_columns)}")
            context_parts.append(f"Total rows: {len(result_rows)}")
            context_parts.append("Data:")
            for i, row in enumerate(result_rows[:30]):  # Limit to 30 rows
                row_str = " | ".join(f"{k}: {v}" for k, v in row.items())
                context_parts.append(f"  {i+1}. {row_str}")
            if len(result_rows) > 30:
                context_parts.append(f"  ... and {len(result_rows) - 30} more rows")
        
        # Add document context
        if doc_context:
            context_parts.append("\n=== CUSTOMER DOCUMENTS ===")
            for doc in doc_context[:3]:
                context_parts.append(doc[:400])
        
        if reflib_context:
            context_parts.append("\n=== REFERENCE LIBRARY ===")
            for doc in reflib_context[:3]:
                context_parts.append(doc[:400])
        
        # Add insights
        if insights:
            context_parts.append("\n=== SYSTEM DETECTED INSIGHTS ===")
            for insight in insights[:5]:
                context_parts.append(f"• [{insight.severity.upper()}] {insight.title}: {insight.description}")
        
        # Add conflicts
        if conflicts:
            context_parts.append("\n=== DETECTED CONFLICTS ===")
            for conflict in conflicts[:5]:
                context_parts.append(f"• {conflict.description}")
        
        # Add context graph summary if available
        if hasattr(self, '_context_graph') and self._context_graph:
            hubs = self._context_graph.get('hubs', [])
            if hubs:
                context_parts.append(f"\n=== DATA MODEL ===")
                context_parts.append(f"System has {len(hubs)} master data hubs (lookup tables)")
        
        context = "\n".join(context_parts)
        
        # =====================================================================
        # v4.1: Build pattern-guided overlay prompt with STRICT formatting
        # =====================================================================
        if pattern:
            # Use pattern-specific guidance
            hunt_for_list = "\n".join(f"  • {item}" for item in pattern.hunt_for)
            proactive_list = "\n".join(f"• {offer}" for offer in pattern.proactive_offers)
            
            overlay_prompt = f"""You are a senior HCM implementation consultant. Analyze this data and provide insights.

The client asked: "{question}"

UNDERSTAND THE QUESTION:
• Surface question: {pattern.surface_question}
• Real question: {pattern.real_question}  
• Hidden worry: {pattern.hidden_worry}

ACTUAL DATA TO ANALYZE:
{context}
{domain_rules}

HUNT FOR THESE PROBLEMS (only mention if you find CLEAR evidence):
{hunt_for_list}

CRITICAL RULES - READ CAREFULLY:
1. READ THE "ENTITY CONTEXT" SECTION FIRST - it explains what columns mean
2. NULL/empty fields are often CORRECT BY DESIGN - NOT automatic problems
3. Only report something as a "finding" if it's ACTUALLY wrong, not just empty
4. Duplicate codes with same description MAY be valid (different purposes)
5. If configuration looks normal, SAY SO - don't invent problems

OUTPUT FORMAT - Bullets only, no paragraphs:

**🔍 Consultant Analysis**

**What I Found:**
• [Only cite ACTUAL problems with specific evidence]
• [If nothing wrong: "Configuration appears complete with X earnings across Y groups"]

**Recommendations:**
• [Only if there are real issues to address]

**Next Steps:**
{proactive_list}
• {pattern.hcmpact_hook}

REMEMBER: An experienced consultant knows that empty fields are often intentional.
Do NOT flag normal configuration as problems."""

        else:
            # Fallback generic prompt
            overlay_prompt = f"""You are a senior HCM implementation consultant. Analyze this data and provide insights.

The client asked: "{question}"

ACTUAL DATA TO ANALYZE:
{context}
{domain_rules}

CRITICAL RULES:
1. READ THE "ENTITY CONTEXT" SECTION FIRST - it explains what columns mean
2. NULL/empty fields are often CORRECT BY DESIGN - NOT problems
3. Only report ACTUAL issues with specific evidence
4. If configuration looks normal, say so - don't invent problems

OUTPUT FORMAT - Bullets only, no paragraphs:

**🔍 Consultant Analysis**

**What I Found:**
• [Only cite ACTUAL problems with evidence, or say "Configuration looks complete"]

**Recommendations:**
• [Only if there are real issues]

**Next Steps:**
• [Proactive offers based on data type]
• Need help with implementation? HCMPACT can assist.

REMEMBER: Empty fields are often intentional. Don't flag normal config as problems."""

        try:
            # Use the LLM synthesizer's orchestrator directly
            if hasattr(self.llm_synthesizer, '_orchestrator') and self.llm_synthesizer._orchestrator:
                result = self.llm_synthesizer._orchestrator.synthesize_answer(
                    question=f"Add consultant analysis to: {question}",
                    context=context,  # Just the data context, not template
                    expert_prompt=overlay_prompt,
                    use_claude_fallback=False  # Local only for speed
                )
                
                if result.get('success') and result.get('response'):
                    analysis = result['response'].strip()
                    
                    # Validate the analysis is meaningful
                    if len(analysis) > 50 and '**' in analysis:
                        # CONCATENATE: Template data + separator + LLM analysis
                        combined_response = f"{template_response}\n\n---\n\n{analysis}"
                        
                        # Store metadata for later retrieval
                        self._last_consultative_answer = type('ConsultativeAnswer', (), {
                            'question_type': pattern.question_type if pattern else 'hybrid_analysis',
                            'question_category': pattern.category.value if pattern else 'operational',
                            'excel_spec': [],
                            'proactive_offers': list(pattern.proactive_offers) if pattern else [
                                'Run compliance check on this data?',
                                'Compare against vendor standards?',
                                'Export full dataset to Excel?'
                            ],
                            'hcmpact_hook': pattern.hcmpact_hook if pattern else 'Need expert help? HCMPACT consultants are available.',
                            'synthesis_method': f"hybrid_pattern_{pattern.question_type}_{result.get('model_used', 'llm')}" if pattern else f"hybrid_generic_{result.get('model_used', 'llm')}"
                        })()
                        
                        logger.warning(f"[SYNTHESIZE] Overlay success via {result.get('model_used')}, pattern={pattern.question_type if pattern else 'none'}")
                        return combined_response
                    else:
                        logger.warning(f"[SYNTHESIZE] LLM analysis too short or malformed ({len(analysis)} chars), using template only")
                        
        except Exception as e:
            logger.warning(f"[SYNTHESIZE] Overlay LLM error: {e}")
        
        return None
    
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
        
        # Document context sections (for template-only mode)
        # In hybrid mode, LLM overlay adds richer analysis
        if not self.llm_synthesizer:
            self._add_truth_sections(parts, doc_context, reflib_context)
        
        # Compliance findings (always show - critical info)
        if compliance_check:
            if compliance_check.get('findings'):
                parts.append("\n\n🚨 **Compliance Findings:**")
                for finding in compliance_check['findings'][:5]:
                    parts.append(f"- {finding}")
            if compliance_check.get('gaps'):
                parts.append("\n\n⚠️ **Compliance Gaps:**")
                for gap in compliance_check['gaps'][:5]:
                    parts.append(f"- {gap}")
        
        # Insights (for template-only mode - LLM overlay adds richer analysis)
        if not self.llm_synthesizer and insights:
            parts.append("\n\n---\n💡 **Insights:**")
            for insight in insights[:3]:
                icon = '🔴' if insight.severity == 'high' else '🟡' if insight.severity == 'medium' else '💡'
                parts.append(f"\n{icon} **{insight.title}**: {insight.description}")
        
        # Conflicts (for template-only mode - LLM overlay adds richer analysis)
        if not self.llm_synthesizer and conflicts:
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
