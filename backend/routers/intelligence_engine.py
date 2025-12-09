"""
XLR8 INTELLIGENCE ENGINE
=========================

This is not a chatbot. This is a REASONING SYSTEM that:

1. SYNTHESIZES - Combines customer data + documents + global knowledge
2. CONTRASTS - Shows what data says vs docs vs best practice  
3. CATCHES - Surfaces conflicts and anomalies automatically
4. CONFIGURES - Generates ready-to-use UKG templates
5. GUIDES - Leads consultants through complex workflows
6. LEARNS - Gets smarter from every interaction

THE CORE INSIGHT:
-----------------
Consultants don't need another search box.
They need a system that THINKS WITH THEM.

"Show me employees" is a search.
"Help me configure earnings for this customer" is intelligence.

This engine makes the latter possible.

Deploy to: backend/utils/intelligence_engine.py

Author: XLR8 Team
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# CORE CONCEPT: THE THREE TRUTHS
# =============================================================================
#
# Every answer involves THREE sources of truth:
#
# 1. REALITY (Customer Data)
#    - DuckDB structured data
#    - What actually IS in their system
#    - Employee counts, earning codes, deduction setups
#
# 2. INTENT (Customer Documents)  
#    - Policy documents, requirements, specs
#    - What they SAY they want or do
#    - May conflict with reality
#
# 3. BEST PRACTICE (Global Knowledge)
#    - UKG documentation, implementation guides
#    - How things SHOULD be done
#    - Industry standards and recommendations
#
# The magic happens when we COMPARE these three.
# =============================================================================


@dataclass
class Truth:
    """A piece of information from one source of truth."""
    source_type: str  # 'reality', 'intent', 'best_practice'
    source_name: str  # File name, document name, etc.
    content: Any      # The actual data/text
    confidence: float # How confident we are (0-1)
    location: str     # Where to find this (page, row, etc.)


@dataclass  
class Conflict:
    """A detected conflict between sources of truth."""
    description: str
    reality: Optional[Truth]
    intent: Optional[Truth]
    best_practice: Optional[Truth]
    severity: str  # 'high', 'medium', 'low'
    recommendation: str


@dataclass
class Insight:
    """A proactive insight discovered while processing."""
    type: str  # 'anomaly', 'missing', 'conflict', 'recommendation'
    title: str
    description: str
    data: Any
    severity: str
    action_required: bool


@dataclass
class SynthesizedAnswer:
    """A complete answer synthesized from all sources."""
    question: str
    
    # The synthesized answer
    answer: str
    confidence: float
    
    # What each source contributed
    from_reality: List[Truth]      # What the DATA shows
    from_intent: List[Truth]       # What DOCUMENTS say
    from_best_practice: List[Truth] # What SHOULD be done
    
    # Conflicts detected
    conflicts: List[Conflict]
    
    # Proactive insights
    insights: List[Insight]
    
    # For template population
    structured_output: Optional[Dict]
    
    # Reasoning chain
    reasoning: List[str]


# =============================================================================
# INTELLIGENCE MODES - What kind of help does the consultant need?
# =============================================================================

class IntelligenceMode(Enum):
    """Different modes of intelligence the engine can provide."""
    
    # Basic query modes
    SEARCH = "search"              # Just find data
    ANALYZE = "analyze"            # Find and interpret data
    
    # Synthesis modes (the good stuff)
    COMPARE = "compare"            # Compare data vs docs vs best practice
    VALIDATE = "validate"          # Check for issues and conflicts
    CONFIGURE = "configure"        # Generate UKG configuration
    
    # Guided modes
    INTERVIEW = "interview"        # Ask clarifying questions
    WORKFLOW = "workflow"          # Multi-step guided process
    
    # Output modes
    POPULATE = "populate"          # Fill in a template
    REPORT = "report"              # Generate a report


# =============================================================================
# THE INTELLIGENCE ENGINE
# =============================================================================

class IntelligenceEngine:
    """
    The brain of XLR8.
    
    This is not a search engine. This is a reasoning system that:
    - Understands context from multiple sources
    - Synthesizes information into coherent answers
    - Catches conflicts and anomalies
    - Generates actionable outputs
    
    Usage:
        engine = IntelligenceEngine(project_name)
        engine.load_context(structured_handler, rag_handler)
        answer = engine.ask("How should I configure overtime earnings?")
    """
    
    def __init__(self, project_name: str):
        self.project = project_name
        self.structured_handler = None
        self.rag_handler = None
        self.schema = {}
        self.relationships = []
        
        # Session state
        self.conversation_history = []
        self.confirmed_facts = {}  # Things the consultant has confirmed
        self.pending_questions = []  # Questions we need to ask
        
        # Cached insights (don't recalculate every query)
        self._cached_insights = None
        self._insight_cache_time = None
    
    def load_context(
        self, 
        structured_handler=None, 
        rag_handler=None,
        schema: Dict = None,
        relationships: List[Dict] = None
    ):
        """Load data context for this project."""
        self.structured_handler = structured_handler
        self.rag_handler = rag_handler
        self.schema = schema or {}
        self.relationships = relationships or []
    
    # =========================================================================
    # MAIN ENTRY POINT
    # =========================================================================
    
    def ask(
        self, 
        question: str,
        mode: IntelligenceMode = None,
        context: Dict = None
    ) -> SynthesizedAnswer:
        """
        Ask the intelligence engine a question.
        
        This is the main entry point. It:
        1. Analyzes the question to determine what's needed
        2. Gathers relevant information from all sources
        3. Synthesizes an answer
        4. Detects conflicts and insights
        5. Returns a complete, reasoned answer
        
        Args:
            question: The consultant's question
            mode: Force a specific intelligence mode (optional)
            context: Additional context (filters, constraints, etc.)
        
        Returns:
            SynthesizedAnswer with full reasoning and sources
        """
        logger.info(f"[INTELLIGENCE] Question: {question[:100]}...")
        
        # Step 1: Understand the question
        analysis = self._analyze_question(question)
        mode = mode or analysis['mode']
        
        logger.info(f"[INTELLIGENCE] Mode: {mode.value}, Confidence: {analysis['confidence']}")
        
        # Step 2: Check if we need clarification first
        if analysis['needs_clarification']:
            return self._request_clarification(question, analysis)
        
        # Step 3: Gather the three truths
        reality = self._gather_reality(question, analysis)
        intent = self._gather_intent(question, analysis)
        best_practice = self._gather_best_practice(question, analysis)
        
        logger.info(f"[INTELLIGENCE] Gathered: {len(reality)} reality, {len(intent)} intent, {len(best_practice)} best practice")
        
        # Step 4: Detect conflicts
        conflicts = self._detect_conflicts(reality, intent, best_practice)
        
        # Step 5: Run proactive checks
        insights = self._run_proactive_checks(analysis)
        
        # Step 6: Synthesize the answer
        answer = self._synthesize_answer(
            question=question,
            mode=mode,
            reality=reality,
            intent=intent,
            best_practice=best_practice,
            conflicts=conflicts,
            insights=insights,
            context=context
        )
        
        # Step 7: Store in conversation history
        self.conversation_history.append({
            'question': question,
            'answer_preview': answer.answer[:200] if answer.answer else '',
            'mode': mode.value,
            'timestamp': datetime.now().isoformat()
        })
        
        return answer
    
    # =========================================================================
    # QUESTION ANALYSIS
    # =========================================================================
    
    def _analyze_question(self, question: str) -> Dict:
        """
        Analyze what the question is really asking for.
        
        Returns:
            Dict with mode, entities, domains, confidence, needs_clarification
        """
        q_lower = question.lower()
        
        # Detect intelligence mode
        mode = self._detect_mode(q_lower)
        
        # Extract entities (employee IDs, codes, etc.)
        entities = self._extract_entities(question)
        
        # Detect domains (employees, earnings, taxes, etc.)
        domains = self._detect_domains(q_lower)
        
        # Check if we need clarification
        needs_clarification = self._needs_clarification(mode, entities, domains, q_lower)
        
        # Calculate confidence
        confidence = 0.7
        if entities:
            confidence += 0.1
        if len(domains) == 1:
            confidence += 0.1
        if mode != IntelligenceMode.SEARCH:
            confidence += 0.05
        
        return {
            'mode': mode,
            'entities': entities,
            'domains': domains,
            'needs_clarification': needs_clarification,
            'clarification_questions': self._get_clarification_questions(mode, domains) if needs_clarification else [],
            'confidence': min(confidence, 0.95)
        }
    
    def _detect_mode(self, q_lower: str) -> IntelligenceMode:
        """Detect the appropriate intelligence mode."""
        
        # Configuration requests
        if any(w in q_lower for w in ['configure', 'set up', 'setup', 'create', 'build']):
            if any(w in q_lower for w in ['rule', 'business rule', 'earning', 'deduction']):
                return IntelligenceMode.CONFIGURE
        
        # Validation requests  
        if any(w in q_lower for w in ['validate', 'check', 'verify', 'issues', 'problems', 'errors']):
            return IntelligenceMode.VALIDATE
        
        # Comparison requests
        if any(w in q_lower for w in ['compare', 'difference', 'versus', 'vs', 'match']):
            return IntelligenceMode.COMPARE
        
        # Template population
        if any(w in q_lower for w in ['fill in', 'populate', 'template', 'generate']):
            return IntelligenceMode.POPULATE
        
        # Report generation
        if any(w in q_lower for w in ['report', 'summary', 'overview', 'status']):
            return IntelligenceMode.REPORT
        
        # Analysis requests
        if any(w in q_lower for w in ['analyze', 'analysis', 'pattern', 'trend', 'insight']):
            return IntelligenceMode.ANALYZE
        
        # Guided workflow triggers
        if any(w in q_lower for w in ['help me', 'walk me through', 'guide', 'step by step']):
            return IntelligenceMode.WORKFLOW
        
        # Default to search for simple queries
        return IntelligenceMode.SEARCH
    
    def _extract_entities(self, question: str) -> Dict[str, Any]:
        """Extract specific entities from the question."""
        entities = {}
        
        # Employee references
        emp_match = re.search(r'employee\s*(?:#|id|number|num)?\s*(\d+)', question, re.I)
        if emp_match:
            entities['employee_id'] = emp_match.group(1)
        
        # Company codes
        company_match = re.search(r'company\s*(?:code)?\s*([A-Z0-9]{2,10})', question, re.I)
        if company_match:
            entities['company_code'] = company_match.group(1)
        
        # Earning/deduction codes
        code_match = re.search(r'(?:earning|deduction|code)\s*([A-Z0-9]{1,10})', question, re.I)
        if code_match:
            entities['code'] = code_match.group(1)
        
        # Status filters
        if 'active' in question.lower():
            entities['status'] = 'active'
        elif 'terminated' in question.lower() or 'termed' in question.lower():
            entities['status'] = 'terminated'
        
        return entities
    
    def _detect_domains(self, q_lower: str) -> List[str]:
        """Detect which data domains are relevant."""
        domains = []
        
        domain_patterns = {
            'employees': r'\b(employee|worker|staff|people|person)\b',
            'earnings': r'\b(earning|pay|salary|wage|compensation|overtime|ot)\b',
            'deductions': r'\b(deduction|benefit|401k|insurance|health|dental|vision)\b',
            'taxes': r'\b(tax|withhold|federal|state|local|w-?4|fit|sit|lit)\b',
            'direct_deposit': r'\b(direct\s*deposit|bank|routing|ach)\b',
            'time': r'\b(time|hours|schedule|attendance|pto|vacation|sick)\b',
            'jobs': r'\b(job|position|title|department|location)\b',
        }
        
        for domain, pattern in domain_patterns.items():
            if re.search(pattern, q_lower):
                domains.append(domain)
        
        return domains if domains else ['general']
    
    def _needs_clarification(
        self, 
        mode: IntelligenceMode, 
        entities: Dict, 
        domains: List[str],
        q_lower: str
    ) -> bool:
        """Determine if we need to ask clarifying questions."""
        
        # Configuration always needs details
        if mode == IntelligenceMode.CONFIGURE:
            return True
        
        # Validation with no specific domain
        if mode == IntelligenceMode.VALIDATE and domains == ['general']:
            return True
        
        # Employee lists without status filter
        if 'employees' in domains and 'status' not in entities:
            # Unless they said "all employees"
            if 'all' not in q_lower:
                return True
        
        return False
    
    def _get_clarification_questions(self, mode: IntelligenceMode, domains: List[str]) -> List[Dict]:
        """Get clarification questions for the given mode/domains."""
        questions = []
        
        if 'employees' in domains:
            questions.append({
                'id': 'employee_status',
                'question': 'Which employees should I include?',
                'type': 'radio',
                'options': [
                    {'id': 'active', 'label': 'Active only', 'default': True},
                    {'id': 'termed', 'label': 'Terminated only'},
                    {'id': 'all', 'label': 'All employees'},
                ]
            })
        
        if mode == IntelligenceMode.CONFIGURE:
            questions.append({
                'id': 'config_type',
                'question': 'What are you trying to configure?',
                'type': 'radio',
                'options': [
                    {'id': 'earning', 'label': 'Earning code/calculation'},
                    {'id': 'deduction', 'label': 'Deduction setup'},
                    {'id': 'tax', 'label': 'Tax configuration'},
                    {'id': 'accrual', 'label': 'Accrual/PTO rule'},
                    {'id': 'other', 'label': 'Something else'},
                ]
            })
            questions.append({
                'id': 'output_format',
                'question': 'How should I format the output?',
                'type': 'radio',
                'options': [
                    {'id': 'ukg_spec', 'label': 'UKG Configuration Spec', 'default': True},
                    {'id': 'business_rule', 'label': 'Business Rule Template'},
                    {'id': 'plain', 'label': 'Plain English Explanation'},
                ]
            })
        
        if mode == IntelligenceMode.VALIDATE:
            questions.append({
                'id': 'validate_scope',
                'question': 'What should I validate?',
                'type': 'checkbox',
                'options': [
                    {'id': 'tax_setup', 'label': 'Tax setup (FIT/SIT/LIT)', 'default': True},
                    {'id': 'direct_deposit', 'label': 'Direct deposit'},
                    {'id': 'deductions', 'label': 'Deduction setup'},
                    {'id': 'demographics', 'label': 'Demographics/addresses'},
                    {'id': 'all', 'label': 'Everything'},
                ]
            })
        
        return questions
    
    def _request_clarification(self, question: str, analysis: Dict) -> SynthesizedAnswer:
        """Return a response that asks for clarification."""
        return SynthesizedAnswer(
            question=question,
            answer=None,
            confidence=0.0,
            from_reality=[],
            from_intent=[],
            from_best_practice=[],
            conflicts=[],
            insights=[],
            structured_output={
                'type': 'clarification_needed',
                'questions': analysis['clarification_questions'],
                'original_question': question,
                'detected_mode': analysis['mode'].value,
                'detected_domains': analysis['domains']
            },
            reasoning=['Need more information to provide accurate answer']
        )
    
    # =========================================================================
    # GATHERING THE THREE TRUTHS
    # =========================================================================
    
    def _gather_reality(self, question: str, analysis: Dict) -> List[Truth]:
        """
        Gather REALITY - what the customer's DATA actually shows.
        
        This queries DuckDB for structured data.
        """
        if not self.structured_handler:
            return []
        
        truths = []
        domains = analysis['domains']
        entities = analysis['entities']
        
        try:
            # Get relevant tables
            tables = self.schema.get('tables', [])
            
            for table in tables:
                table_name = table.get('table_name', '')
                columns = table.get('columns', [])
                
                # Filter to relevant tables based on domain
                relevant = False
                if 'employees' in domains and any(c in table_name.lower() for c in ['personal', 'employee', 'demographic']):
                    relevant = True
                if 'earnings' in domains and 'earning' in table_name.lower():
                    relevant = True
                if 'deductions' in domains and 'deduction' in table_name.lower():
                    relevant = True
                if 'taxes' in domains and any(c in table_name.lower() for c in ['tax', 'fit', 'sit', 'lit']):
                    relevant = True
                if 'direct_deposit' in domains and 'deposit' in table_name.lower():
                    relevant = True
                
                if not relevant and domains != ['general']:
                    continue
                
                # Query the table
                try:
                    # Build WHERE clause from entities
                    where_parts = []
                    if 'employee_id' in entities:
                        for col in columns:
                            if 'employee' in col.lower() and ('id' in col.lower() or 'num' in col.lower()):
                                where_parts.append(f'"{col}" = \'{entities["employee_id"]}\'')
                                break
                    if 'status' in entities:
                        for col in columns:
                            if 'status' in col.lower():
                                status_val = 'A' if entities['status'] == 'active' else 'T'
                                where_parts.append(f'"{col}" ILIKE \'%{status_val}%\'')
                                break
                    
                    where_clause = ' AND '.join(where_parts) if where_parts else '1=1'
                    sql = f'SELECT * FROM "{table_name}" WHERE {where_clause} LIMIT 100'
                    
                    rows, cols = self.structured_handler.execute_query(sql)
                    
                    if rows:
                        truths.append(Truth(
                            source_type='reality',
                            source_name=table_name,
                            content={
                                'columns': cols,
                                'rows': rows,
                                'total': len(rows),
                                'table': table_name
                            },
                            confidence=0.95,
                            location=f"Table: {table_name}"
                        ))
                        
                except Exception as e:
                    logger.debug(f"Query failed for {table_name}: {e}")
        
        except Exception as e:
            logger.error(f"Error gathering reality: {e}")
        
        return truths
    
    def _gather_intent(self, question: str, analysis: Dict) -> List[Truth]:
        """
        Gather INTENT - what customer's DOCUMENTS say they want/do.
        
        This searches project-specific documents in ChromaDB.
        """
        if not self.rag_handler:
            return []
        
        truths = []
        
        try:
            collection = self.rag_handler.client.get_or_create_collection(name="documents")
            
            # Search project documents only
            results = collection.query(
                query_texts=[question],
                n_results=10,
                where={"project": self.project} if self.project else None
            )
            
            if results and results.get('documents') and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                    distance = results['distances'][0][i] if results.get('distances') else 1.0
                    
                    # Skip global docs - those go in best_practice
                    if metadata.get('project', '').lower() in ['global', '__global__', 'global/universal']:
                        continue
                    
                    truths.append(Truth(
                        source_type='intent',
                        source_name=metadata.get('filename', 'Document'),
                        content=doc,
                        confidence=max(0.3, 1.0 - distance),
                        location=f"Page {metadata.get('page', '?')}"
                    ))
        
        except Exception as e:
            logger.error(f"Error gathering intent: {e}")
        
        return truths
    
    def _gather_best_practice(self, question: str, analysis: Dict) -> List[Truth]:
        """
        Gather BEST PRACTICE - what UKG docs say SHOULD be done.
        
        This searches global knowledge in ChromaDB.
        """
        if not self.rag_handler:
            return []
        
        truths = []
        
        try:
            collection = self.rag_handler.client.get_or_create_collection(name="documents")
            
            # Search global documents
            results = collection.query(
                query_texts=[question],
                n_results=10,
                where={"project": {"$in": ["global", "__global__", "Global/Universal"]}}
            )
            
            if results and results.get('documents') and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                    distance = results['distances'][0][i] if results.get('distances') else 1.0
                    
                    truths.append(Truth(
                        source_type='best_practice',
                        source_name=metadata.get('filename', 'UKG Documentation'),
                        content=doc,
                        confidence=max(0.3, 1.0 - distance),
                        location=f"Page {metadata.get('page', '?')}"
                    ))
        
        except Exception as e:
            logger.error(f"Error gathering best practice: {e}")
        
        return truths
    
    # =========================================================================
    # CONFLICT DETECTION
    # =========================================================================
    
    def _detect_conflicts(
        self, 
        reality: List[Truth], 
        intent: List[Truth], 
        best_practice: List[Truth]
    ) -> List[Conflict]:
        """
        Detect conflicts between the three truths.
        
        This is where the magic happens. We look for:
        - Data says X but documents say Y
        - Customer does X but best practice says Y
        - Documents promise X but data shows Y
        """
        conflicts = []
        
        # Example conflict patterns to check:
        # (In production, this would be much more sophisticated)
        
        # Check: Active employee counts
        # Reality: COUNT(*) WHERE status = 'A'
        # Intent: "We have approximately X employees"
        # Best Practice: (not applicable)
        
        # Check: Earning code configurations
        # Reality: What codes exist in data
        # Intent: What codes are documented
        # Best Practice: Standard UKG earning codes
        
        # For now, return empty - this needs domain-specific logic
        # TODO: Implement specific conflict detection rules
        
        return conflicts
    
    # =========================================================================
    # PROACTIVE CHECKS
    # =========================================================================
    
    def _run_proactive_checks(self, analysis: Dict) -> List[Insight]:
        """
        Run proactive checks while answering.
        
        This surfaces issues even if the user didn't ask about them.
        """
        insights = []
        domains = analysis['domains']
        
        if not self.structured_handler:
            return insights
        
        try:
            tables = self.schema.get('tables', [])
            
            # Employee checks
            if 'employees' in domains or domains == ['general']:
                for table in tables:
                    table_name = table.get('table_name', '')
                    
                    if any(c in table_name.lower() for c in ['personal', 'employee']):
                        # Check for missing SSN
                        try:
                            sql = f'''
                                SELECT COUNT(*) as cnt 
                                FROM "{table_name}" 
                                WHERE ssn_formatted IS NULL OR ssn_formatted = ''
                            '''
                            result = self.structured_handler.conn.execute(sql).fetchone()
                            if result and result[0] > 0:
                                insights.append(Insight(
                                    type='anomaly',
                                    title='Missing SSN',
                                    description=f'{result[0]} employees missing SSN',
                                    data={'count': result[0], 'table': table_name},
                                    severity='high',
                                    action_required=True
                                ))
                        except:
                            pass
                        
                        # Check for future hire dates
                        try:
                            sql = f'''
                                SELECT COUNT(*) as cnt 
                                FROM "{table_name}" 
                                WHERE original_hire_date > CURRENT_DATE
                            '''
                            result = self.structured_handler.conn.execute(sql).fetchone()
                            if result and result[0] > 0:
                                insights.append(Insight(
                                    type='anomaly',
                                    title='Future Hire Dates',
                                    description=f'{result[0]} employees have hire date in the future',
                                    data={'count': result[0], 'table': table_name},
                                    severity='medium',
                                    action_required=True
                                ))
                        except:
                            pass
                        
                        break  # Only check first relevant table
            
            # Earnings checks
            if 'earnings' in domains:
                for table in tables:
                    table_name = table.get('table_name', '')
                    
                    if 'earning' in table_name.lower():
                        # Check for zero amounts
                        try:
                            sql = f'''
                                SELECT COUNT(*) as cnt 
                                FROM "{table_name}" 
                                WHERE (amount IS NULL OR amount = 0)
                            '''
                            result = self.structured_handler.conn.execute(sql).fetchone()
                            if result and result[0] > 10:  # Allow some
                                insights.append(Insight(
                                    type='anomaly',
                                    title='Zero Earning Amounts',
                                    description=f'{result[0]} earning records with zero/null amount',
                                    data={'count': result[0], 'table': table_name},
                                    severity='medium',
                                    action_required=True
                                ))
                        except:
                            pass
                        
                        break
        
        except Exception as e:
            logger.error(f"Error in proactive checks: {e}")
        
        return insights
    
    # =========================================================================
    # ANSWER SYNTHESIS
    # =========================================================================
    
    def _synthesize_answer(
        self,
        question: str,
        mode: IntelligenceMode,
        reality: List[Truth],
        intent: List[Truth],
        best_practice: List[Truth],
        conflicts: List[Conflict],
        insights: List[Insight],
        context: Dict = None
    ) -> SynthesizedAnswer:
        """
        Synthesize a complete answer from all sources.
        
        This is where we combine everything into a coherent response.
        """
        reasoning = []
        
        # Build context for LLM
        context_parts = []
        
        # Add reality (customer data)
        if reality:
            context_parts.append("=== CUSTOMER DATA (What IS) ===")
            for truth in reality[:3]:
                if isinstance(truth.content, dict) and 'rows' in truth.content:
                    rows = truth.content['rows']
                    cols = truth.content['columns']
                    context_parts.append(f"\nSource: {truth.source_name}")
                    context_parts.append(f"Columns: {', '.join(cols[:10])}")
                    context_parts.append(f"Sample data ({len(rows)} rows):")
                    for row in rows[:10]:
                        row_str = " | ".join(f"{k}: {v}" for k, v in list(row.items())[:8])
                        context_parts.append(f"  {row_str}")
            reasoning.append(f"Found {len(reality)} relevant data sources")
        
        # Add intent (customer documents)
        if intent:
            context_parts.append("\n=== CUSTOMER DOCUMENTS (What they SAY) ===")
            for truth in intent[:3]:
                context_parts.append(f"\nSource: {truth.source_name} ({truth.location})")
                context_parts.append(str(truth.content)[:1000])
            reasoning.append(f"Found {len(intent)} relevant customer documents")
        
        # Add best practice (UKG knowledge)
        if best_practice:
            context_parts.append("\n=== UKG BEST PRACTICE (What SHOULD be) ===")
            for truth in best_practice[:3]:
                context_parts.append(f"\nSource: {truth.source_name}")
                context_parts.append(str(truth.content)[:1000])
            reasoning.append(f"Found {len(best_practice)} relevant UKG best practice documents")
        
        # Add conflicts
        if conflicts:
            context_parts.append("\n=== CONFLICTS DETECTED ===")
            for conflict in conflicts:
                context_parts.append(f"⚠️ {conflict.description}")
                context_parts.append(f"   Recommendation: {conflict.recommendation}")
        
        # Add insights
        if insights:
            context_parts.append("\n=== PROACTIVE INSIGHTS ===")
            for insight in insights:
                context_parts.append(f"{'🔴' if insight.severity == 'high' else '🟡'} {insight.title}: {insight.description}")
        
        combined_context = '\n'.join(context_parts)
        
        # Determine output structure based on mode
        structured_output = None
        
        if mode == IntelligenceMode.CONFIGURE:
            structured_output = {
                'type': 'configuration',
                'template': 'business_rule',
                'fields': {
                    'rule_name': '',
                    'effective_date': '',
                    'conditions': [],
                    'calculations': [],
                    'exceptions': [],
                    'ukg_config_steps': []
                }
            }
        elif mode == IntelligenceMode.VALIDATE:
            structured_output = {
                'type': 'validation_report',
                'issues_found': len(insights),
                'issues': [
                    {
                        'severity': i.severity,
                        'title': i.title,
                        'description': i.description,
                        'count': i.data.get('count') if isinstance(i.data, dict) else None
                    }
                    for i in insights
                ],
                'recommendations': []
            }
        elif mode == IntelligenceMode.COMPARE:
            structured_output = {
                'type': 'comparison',
                'reality_summary': f"{len(reality)} data sources",
                'intent_summary': f"{len(intent)} documents",
                'best_practice_summary': f"{len(best_practice)} UKG references",
                'conflicts': len(conflicts),
                'comparison_table': []
            }
        
        # Calculate confidence
        confidence = 0.5
        if reality:
            confidence += 0.2
        if intent:
            confidence += 0.15
        if best_practice:
            confidence += 0.1
        confidence = min(confidence, 0.95)
        
        return SynthesizedAnswer(
            question=question,
            answer=combined_context,  # The actual answer will be generated by Claude using this context
            confidence=confidence,
            from_reality=reality,
            from_intent=intent,
            from_best_practice=best_practice,
            conflicts=conflicts,
            insights=insights,
            structured_output=structured_output,
            reasoning=reasoning
        )


# =============================================================================
# OUTPUT TEMPLATES - Ready-to-use configuration formats
# =============================================================================

BUSINESS_RULE_TEMPLATE = """
================================================================================
BUSINESS RULE SPECIFICATION
================================================================================

Rule Name: {rule_name}
Effective Date: {effective_date}
Created: {created_date}
Status: {status}

--------------------------------------------------------------------------------
DESCRIPTION
--------------------------------------------------------------------------------
{description}

--------------------------------------------------------------------------------
CONDITIONS (When this rule applies)
--------------------------------------------------------------------------------
{conditions}

--------------------------------------------------------------------------------
CALCULATION/LOGIC
--------------------------------------------------------------------------------
{calculation}

--------------------------------------------------------------------------------
EXCEPTIONS
--------------------------------------------------------------------------------
{exceptions}

--------------------------------------------------------------------------------
UKG CONFIGURATION STEPS
--------------------------------------------------------------------------------
{ukg_steps}

--------------------------------------------------------------------------------
SOURCE REFERENCES
--------------------------------------------------------------------------------
{sources}
================================================================================
"""

UKG_CONFIG_TEMPLATE = """
================================================================================
UKG CONFIGURATION SPECIFICATION
================================================================================

Component: {component}
Module: {module}
Version: {version}

--------------------------------------------------------------------------------
SETTINGS
--------------------------------------------------------------------------------
{settings}

--------------------------------------------------------------------------------
DEPENDENCIES
--------------------------------------------------------------------------------
{dependencies}

--------------------------------------------------------------------------------
VALIDATION RULES
--------------------------------------------------------------------------------
{validation}

--------------------------------------------------------------------------------
IMPLEMENTATION NOTES
--------------------------------------------------------------------------------
{notes}
================================================================================
"""


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_engine(
    project_name: str,
    structured_handler=None,
    rag_handler=None,
    schema: Dict = None,
    relationships: List[Dict] = None
) -> IntelligenceEngine:
    """Create and initialize an intelligence engine."""
    engine = IntelligenceEngine(project_name)
    engine.load_context(structured_handler, rag_handler, schema, relationships)
    return engine


def quick_ask(
    question: str,
    project_name: str,
    structured_handler=None,
    rag_handler=None
) -> SynthesizedAnswer:
    """Quick one-off question without persistent engine."""
    engine = create_engine(project_name, structured_handler, rag_handler)
    return engine.ask(question)
