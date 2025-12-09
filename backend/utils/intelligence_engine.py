"""
XLR8 INTELLIGENCE ENGINE
=========================

Deploy to: backend/utils/intelligence_engine.py
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
# DATA CLASSES
# =============================================================================

@dataclass
class Truth:
    """A piece of information from one source of truth."""
    source_type: str  # 'reality', 'intent', 'best_practice'
    source_name: str
    content: Any
    confidence: float
    location: str


@dataclass  
class Conflict:
    """A detected conflict between sources of truth."""
    description: str
    reality: Optional[Truth] = None
    intent: Optional[Truth] = None
    best_practice: Optional[Truth] = None
    severity: str = "medium"
    recommendation: str = ""


@dataclass
class Insight:
    """A proactive insight discovered while processing."""
    type: str
    title: str
    description: str
    data: Any
    severity: str
    action_required: bool = False


@dataclass
class SynthesizedAnswer:
    """A complete answer synthesized from all sources."""
    question: str
    answer: str
    confidence: float
    from_reality: List[Truth] = field(default_factory=list)
    from_intent: List[Truth] = field(default_factory=list)
    from_best_practice: List[Truth] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    insights: List[Insight] = field(default_factory=list)
    structured_output: Optional[Dict] = None
    reasoning: List[str] = field(default_factory=list)


class IntelligenceMode(Enum):
    SEARCH = "search"
    ANALYZE = "analyze"
    COMPARE = "compare"
    VALIDATE = "validate"
    CONFIGURE = "configure"
    INTERVIEW = "interview"
    WORKFLOW = "workflow"
    POPULATE = "populate"
    REPORT = "report"


# =============================================================================
# SEMANTIC PATTERNS
# =============================================================================

SEMANTIC_TYPES = {
    'employee_id': [
        r'^emp.*id', r'^ee.*num', r'^employee.*number', r'^worker.*id',
        r'^person.*id', r'^emp.*num', r'^emp.*no$', r'^ee.*id',
        r'^employee.*id', r'^staff.*id', r'^associate.*id', r'^emp.*key',
    ],
    'company_code': [
        r'^comp.*code', r'^co.*code', r'^company.*id', r'^org.*code',
        r'^entity.*code', r'^legal.*entity', r'^business.*unit',
        r'^company$', r'^comp$',
    ],
    'department': [
        r'dept.*code', r'department.*code', r'^div.*code', r'division.*code',
        r'cost.*center', r'^dept$', r'^department$',
    ],
    'job_code': [
        r'^job.*code', r'^job.*id', r'^position.*code', r'^title.*code',
        r'^job.*class', r'^occupation', r'^job$',
    ],
    'location': [
        r'^loc.*code', r'^location.*code', r'^work.*loc', r'^site.*code',
        r'^branch.*code', r'^office.*code', r'^location$',
    ],
    'earning_code': [
        r'^earn.*code', r'^earning.*type', r'^pay.*code', r'^wage.*type',
        r'^earning$', r'^earn_cd',
    ],
    'deduction_code': [
        r'^ded.*code', r'^deduction.*type', r'^deduct.*code',
        r'^deduction$', r'^ded_cd', r'^benefit.*code',
    ],
}


# =============================================================================
# INTELLIGENCE ENGINE
# =============================================================================

class IntelligenceEngine:
    """The brain of XLR8."""
    
    def __init__(self, project_name: str):
        self.project = project_name
        self.structured_handler = None
        self.rag_handler = None
        self.schema = {}
        self.relationships = []
        self.conversation_history = []
        self.confirmed_facts = {}
        self.pending_questions = []
    
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
    
    def ask(
        self, 
        question: str,
        mode: IntelligenceMode = None,
        context: Dict = None
    ) -> SynthesizedAnswer:
        """Main entry point - ask the engine a question."""
        logger.info(f"[INTELLIGENCE] Question: {question[:100]}...")
        
        # Analyze the question
        analysis = self._analyze_question(question)
        mode = mode or analysis['mode']
        
        # Check if clarification needed
        if analysis['needs_clarification']:
            return self._request_clarification(question, analysis)
        
        logger.info(f"[INTELLIGENCE] Gathering truths - no clarification needed")
        
        # Gather the three truths
        reality = self._gather_reality(question, analysis)
        logger.info(f"[INTELLIGENCE] Reality gathered: {len(reality)} truths")
        
        intent = self._gather_intent(question, analysis)
        best_practice = self._gather_best_practice(question, analysis)
        
        # Detect conflicts
        conflicts = self._detect_conflicts(reality, intent, best_practice)
        
        # Run proactive checks
        insights = self._run_proactive_checks(analysis)
        
        # Synthesize answer
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
        
        # Store in history
        self.conversation_history.append({
            'question': question,
            'answer_preview': answer.answer[:200] if answer.answer else '',
            'mode': mode.value if mode else 'search',
            'timestamp': datetime.now().isoformat()
        })
        
        return answer
    
    def _analyze_question(self, question: str) -> Dict:
        """Analyze what the question is asking for."""
        q_lower = question.lower()
        
        mode = self._detect_mode(q_lower)
        entities = self._extract_entities(question)
        domains = self._detect_domains(q_lower)
        needs_clarification = self._needs_clarification(mode, entities, domains, q_lower)
        
        confidence = 0.7
        if entities:
            confidence += 0.1
        if len(domains) == 1:
            confidence += 0.1
        
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
        if any(w in q_lower for w in ['configure', 'set up', 'setup', 'create', 'build']):
            if any(w in q_lower for w in ['rule', 'business rule', 'earning', 'deduction']):
                return IntelligenceMode.CONFIGURE
        
        if any(w in q_lower for w in ['validate', 'check', 'verify', 'issues', 'problems', 'errors']):
            return IntelligenceMode.VALIDATE
        
        if any(w in q_lower for w in ['compare', 'difference', 'versus', 'vs', 'match']):
            return IntelligenceMode.COMPARE
        
        if any(w in q_lower for w in ['fill in', 'populate', 'template', 'generate']):
            return IntelligenceMode.POPULATE
        
        if any(w in q_lower for w in ['report', 'summary', 'overview', 'status']):
            return IntelligenceMode.REPORT
        
        if any(w in q_lower for w in ['analyze', 'analysis', 'pattern', 'trend', 'insight']):
            return IntelligenceMode.ANALYZE
        
        if any(w in q_lower for w in ['help me', 'walk me through', 'guide', 'step by step']):
            return IntelligenceMode.WORKFLOW
        
        return IntelligenceMode.SEARCH
    
    def _extract_entities(self, question: str) -> Dict[str, Any]:
        """Extract specific entities from the question."""
        entities = {}
        
        emp_match = re.search(r'employee\s*(?:#|id|number|num)?\s*(\d+)', question, re.I)
        if emp_match:
            entities['employee_id'] = emp_match.group(1)
        
        company_match = re.search(r'company\s*(?:code)?\s*([A-Z0-9]{2,10})', question, re.I)
        if company_match:
            entities['company_code'] = company_match.group(1)
        
        if 'active' in question.lower():
            entities['status'] = 'active'
        elif 'terminated' in question.lower() or 'termed' in question.lower():
            entities['status'] = 'terminated'
        
        return entities
    
    def _detect_domains(self, q_lower: str) -> List[str]:
        """Detect which data domains are relevant."""
        domains = []
        
        domain_patterns = {
            'employees': r'\b(employee|worker|staff|people|person|pt|ft|part.?time|full.?time)\b',
            'earnings': r'\b(earning|pay|salary|wage|compensation|overtime|ot|hour|rate|hourly)\b',
            'deductions': r'\b(deduction|benefit|401k|insurance|health|dental)\b',
            'taxes': r'\b(tax|withhold|federal|state|local|w-?4|fit|sit)\b',
            'jobs': r'\b(job|position|title|department|location)\b',
        }
        
        for domain, pattern in domain_patterns.items():
            if re.search(pattern, q_lower):
                domains.append(domain)
        
        return domains if domains else ['general']
    
    def _generate_sql_for_question(self, question: str, analysis: Dict) -> Optional[Dict]:
        """Generate SQL query based on the question - SMART schema scanning."""
        logger.info(f"[SQL-GEN] Starting - handler: {self.structured_handler is not None}, schema: {self.schema is not None}")
        
        if not self.structured_handler:
            logger.warning("[SQL-GEN] No structured handler")
            return None
        
        if not self.schema:
            logger.warning("[SQL-GEN] No schema")
            return None
        
        q_lower = question.lower()
        tables = self.schema.get('tables', [])
        
        if not tables:
            logger.warning("[SQL-GEN] Schema has no tables")
            return None
        
        logger.info(f"[SQL-GEN] Scanning {len(tables)} tables: {[t.get('table_name') for t in tables[:5]]}...")
        
        # Detect query type
        query_type = 'list'
        if any(w in q_lower for w in ['how many', 'count', 'number of', 'total number']):
            query_type = 'count'
        elif any(w in q_lower for w in ['total', 'sum of']):
            query_type = 'sum'
        elif any(w in q_lower for w in ['average', 'avg', 'mean']):
            query_type = 'average'
        
        # SMART: Scan ALL tables and columns to find relevant ones
        best_table = None
        best_score = 0
        pt_col = None
        rate_col = None
        
        # Keywords that indicate PT/FT columns
        pt_keywords = ['fullpart', 'full_part', 'ft_pt', 'ptft', 'part_time', 'parttime', 
                       'emp_type', 'employee_type', 'work_status', 'schedule_type', 'fte']
        
        # Keywords that indicate rate/pay columns
        rate_keywords = ['hourly', 'hour_rate', 'hrly', 'pay_rate', 'rate', 'wage', 
                         'salary', 'compensation', 'annual', 'pay', 'amount']
        
        for table in tables:
            table_name = table.get('table_name', '')
            columns = table.get('columns', [])
            
            # Get column names
            col_names = []
            for c in columns:
                if isinstance(c, str):
                    col_names.append(c.lower())
                elif isinstance(c, dict):
                    col_names.append(c.get('name', '').lower())
            
            logger.debug(f"[INTELLIGENCE] Table {table_name} has columns: {col_names[:10]}...")
            
            # Score this table
            table_score = 0
            found_pt = None
            found_rate = None
            
            for col in col_names:
                # Check for PT/FT column
                for kw in pt_keywords:
                    if kw in col:
                        found_pt = col
                        table_score += 10
                        break
                
                # Check for rate/pay column
                for kw in rate_keywords:
                    if kw in col and 'date' not in col and 'code' not in col:
                        found_rate = col
                        table_score += 10
                        break
                
                # Bonus for employee-related tables
                if any(x in table_name.lower() for x in ['employee', 'personal', 'worker', 'staff']):
                    table_score += 5
            
            if table_score > best_score:
                best_score = table_score
                best_table = table_name
                pt_col = found_pt
                rate_col = found_rate
        
        if not best_table:
            logger.warning("[INTELLIGENCE] Could not find suitable table")
            return None
        
        logger.info(f"[INTELLIGENCE] Best table: {best_table} (score: {best_score})")
        logger.info(f"[INTELLIGENCE] PT column: {pt_col}, Rate column: {rate_col}")
        
        # If we didn't find the specific columns, try to get table info directly
        if not pt_col and not rate_col:
            # Query the table to see what columns exist
            try:
                check_sql = f'SELECT * FROM "{best_table}" LIMIT 1'
                rows, cols = self.structured_handler.execute_query(check_sql)
                logger.info(f"[INTELLIGENCE] Direct column check: {cols}")
                
                # Search in actual returned columns
                for col in cols:
                    col_lower = col.lower()
                    if not pt_col:
                        for kw in pt_keywords:
                            if kw in col_lower:
                                pt_col = col
                                break
                    if not rate_col:
                        for kw in rate_keywords:
                            if kw in col_lower and 'date' not in col_lower and 'code' not in col_lower:
                                rate_col = col
                                break
            except Exception as e:
                logger.warning(f"[INTELLIGENCE] Column check failed: {e}")
        
        # Build WHERE conditions
        where_conditions = []
        
        # PT/FT filter
        if 'pt' in q_lower or 'part-time' in q_lower or 'part time' in q_lower:
            if pt_col:
                where_conditions.append(f'LOWER(CAST("{pt_col}" AS VARCHAR)) IN (\'p\', \'pt\', \'part-time\', \'part time\', \'parttime\', \'part\')')
            else:
                logger.warning("[INTELLIGENCE] No PT/FT column found for filtering")
        elif 'ft' in q_lower or 'full-time' in q_lower or 'full time' in q_lower:
            if pt_col:
                where_conditions.append(f'LOWER(CAST("{pt_col}" AS VARCHAR)) IN (\'f\', \'ft\', \'full-time\', \'full time\', \'fulltime\', \'full\')')
        
        # Numeric conditions (more than, less than)
        money_match = re.search(r'(?:more than|over|greater than|above|>|make\s+)\s*\$?(\d+(?:\.\d+)?)', q_lower)
        if money_match and rate_col:
            amount = money_match.group(1)
            where_conditions.append(f'TRY_CAST("{rate_col}" AS DOUBLE) > {amount}')
            logger.info(f"[INTELLIGENCE] Adding rate filter: > {amount}")
        
        money_match_less = re.search(r'(?:less than|under|below|<)\s*\$?(\d+(?:\.\d+)?)', q_lower)
        if money_match_less and rate_col:
            amount = money_match_less.group(1)
            where_conditions.append(f'TRY_CAST("{rate_col}" AS DOUBLE) < {amount}')
        
        # Build SQL
        where_clause = ' AND '.join(where_conditions) if where_conditions else '1=1'
        
        if query_type == 'count':
            sql = f'SELECT COUNT(*) as count FROM "{best_table}" WHERE {where_clause}'
        elif query_type == 'sum' and rate_col:
            sql = f'SELECT SUM(TRY_CAST("{rate_col}" AS DOUBLE)) as total FROM "{best_table}" WHERE {where_clause}'
        elif query_type == 'average' and rate_col:
            sql = f'SELECT AVG(TRY_CAST("{rate_col}" AS DOUBLE)) as average FROM "{best_table}" WHERE {where_clause}'
        else:
            sql = f'SELECT * FROM "{best_table}" WHERE {where_clause} LIMIT 100'
        
        logger.info(f"[INTELLIGENCE] Generated SQL: {sql}")
        
        return {
            'sql': sql,
            'table': best_table,
            'columns': [c for c in [pt_col, rate_col] if c],
            'query_type': query_type,
            'conditions': where_conditions
        }
    
    def _needs_clarification(self, mode, entities, domains, q_lower) -> bool:
        """Determine if we need to ask clarifying questions."""
        # Skip clarification for simple data queries with clear filters
        if any(w in q_lower for w in ['how many', 'count', 'list', 'show me', 'what is', 'total']):
            # If they specified PT/FT, don't ask about employee status
            if any(w in q_lower for w in ['pt ', 'ft ', 'part-time', 'part time', 'full-time', 'full time']):
                return False
            # If they specified active/terminated, don't ask
            if any(w in q_lower for w in ['active', 'terminated', 'termed', 'all employees']):
                return False
        
        if mode == IntelligenceMode.CONFIGURE:
            return True
        
        if mode == IntelligenceMode.VALIDATE and domains == ['general']:
            return True
        
        # Don't ask for employee status clarification on simple queries
        # Only ask for complex configuration scenarios
        
        return False
    
    def _get_clarification_questions(self, mode, domains) -> List[Dict]:
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
                    {'id': 'other', 'label': 'Something else'},
                ]
            })
        
        return questions
    
    def _request_clarification(self, question: str, analysis: Dict) -> SynthesizedAnswer:
        """Return a response that asks for clarification."""
        return SynthesizedAnswer(
            question=question,
            answer="",
            confidence=0.0,
            structured_output={
                'type': 'clarification_needed',
                'questions': analysis['clarification_questions'],
                'original_question': question,
                'detected_mode': analysis['mode'].value,
                'detected_domains': analysis['domains']
            },
            reasoning=['Need more information to provide accurate answer']
        )
    
    def _gather_reality(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather REALITY - what the customer's DATA shows."""
        logger.info(f"[REALITY] Starting - handler: {self.structured_handler is not None}, schema tables: {len(self.schema.get('tables', [])) if self.schema else 0}")
        
        if not self.structured_handler:
            logger.warning("[REALITY] No structured handler - returning empty")
            return []
        
        if not self.schema or not self.schema.get('tables'):
            logger.warning("[REALITY] No schema tables - returning empty")
            return []
        
        truths = []
        domains = analysis['domains']
        entities = analysis['entities']
        
        try:
            # FIRST: Try to generate and execute targeted SQL
            sql_info = self._generate_sql_for_question(question, analysis)
            if sql_info:
                try:
                    sql = sql_info['sql']
                    logger.info(f"[INTELLIGENCE] Generated SQL: {sql}")
                    rows, cols = self.structured_handler.execute_query(sql)
                    
                    if rows:
                        truths.append(Truth(
                            source_type='reality',
                            source_name=f"SQL Query: {sql_info['table']}",
                            content={
                                'sql': sql,
                                'columns': cols,
                                'rows': rows,
                                'total': len(rows),
                                'query_type': sql_info['query_type'],
                                'table': sql_info['table'],
                                'is_targeted_query': True
                            },
                            confidence=0.98,
                            location=f"Query: {sql}"
                        ))
                        logger.info(f"[INTELLIGENCE] SQL returned {len(rows)} rows")
                        # If we got a targeted result, prioritize it
                        return truths
                except Exception as sql_e:
                    logger.warning(f"[INTELLIGENCE] SQL query failed: {sql_e}")
            
            # FALLBACK: Sample data from relevant tables
            tables = self.schema.get('tables', [])
            
            for table in tables:
                table_name = table.get('table_name', '')
                columns = table.get('columns', [])
                
                # Filter to relevant tables
                relevant = False
                if 'employees' in domains and any(c in table_name.lower() for c in ['personal', 'employee', 'demographic']):
                    relevant = True
                if 'earnings' in domains and any(c in table_name.lower() for c in ['earning', 'pay', 'rate', 'salary', 'compensation']):
                    relevant = True
                if 'deductions' in domains and 'deduction' in table_name.lower():
                    relevant = True
                
                if not relevant and domains != ['general']:
                    continue
                
                try:
                    sql = f'SELECT * FROM "{table_name}" LIMIT 100'
                    rows, cols = self.structured_handler.execute_query(sql)
                    
                    if rows:
                        truths.append(Truth(
                            source_type='reality',
                            source_name=table_name,
                            content={
                                'columns': cols,
                                'rows': rows,
                                'total': len(rows),
                                'table': table_name,
                                'is_targeted_query': False
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
        """Gather INTENT - what customer's DOCUMENTS say."""
        if not self.rag_handler:
            return []
        
        truths = []
        
        try:
            # Try to find the right collection name
            collection_name = self._get_document_collection_name()
            if not collection_name:
                logger.warning("No document collection found")
                return []
            
            # Use rag_handler.search() which properly handles embeddings
            # Filter by project to get customer-specific docs (excludes Global/Universal)
            results = self.rag_handler.search(
                collection_name=collection_name,
                query=question,
                n_results=10,
                project_id=self.project if self.project else None
            )
            
            for result in results:
                metadata = result.get('metadata', {})
                distance = result.get('distance', 1.0)
                doc = result.get('document', '')
                
                # Skip global docs - we want customer-specific intent
                project_id = metadata.get('project_id', '').lower()
                if project_id in ['global', '__global__', 'global/universal']:
                    continue
                
                truths.append(Truth(
                    source_type='intent',
                    source_name=metadata.get('filename', 'Document'),
                    content=doc,
                    confidence=max(0.3, 1.0 - distance) if distance else 0.7,
                    location=f"Page {metadata.get('page', '?')}"
                ))
        
        except Exception as e:
            logger.error(f"Error gathering intent: {e}")
        
        return truths
    
    def _get_document_collection_name(self) -> Optional[str]:
        """Find the document collection name from available collections."""
        if not self.rag_handler:
            return None
        
        # Cache the result
        if hasattr(self, '_doc_collection_name'):
            return self._doc_collection_name
        
        try:
            collections = self.rag_handler.list_collections()
            
            # Priority order for document collections
            preferred = ['hcmpact_docs', 'documents', 'hcm_docs', 'xlr8_docs']
            
            for name in preferred:
                if name in collections:
                    self._doc_collection_name = name
                    logger.info(f"Using document collection: {name}")
                    return name
            
            # Fall back to any collection that might have docs
            for name in collections:
                if 'doc' in name.lower() or 'hcm' in name.lower():
                    self._doc_collection_name = name
                    logger.info(f"Using document collection (fallback): {name}")
                    return name
            
            # Last resort - use first collection if any
            if collections:
                self._doc_collection_name = collections[0]
                logger.warning(f"Using first available collection: {collections[0]}")
                return collections[0]
                
        except Exception as e:
            logger.error(f"Error finding document collection: {e}")
        
        return None
    
    def _gather_best_practice(self, question: str, analysis: Dict) -> List[Truth]:
        """Gather BEST PRACTICE - what UKG docs say SHOULD be done."""
        if not self.rag_handler:
            return []
        
        truths = []
        
        try:
            # Try to find the right collection name
            collection_name = self._get_document_collection_name()
            if not collection_name:
                logger.warning("No document collection found for best practices")
                return []
            
            # Use rag_handler.search() with Global/Universal to get only UKG best practices
            results = self.rag_handler.search(
                collection_name=collection_name,
                query=question,
                n_results=10,
                project_id="Global/Universal"  # Only get global/UKG docs
            )
            
            for result in results:
                metadata = result.get('metadata', {})
                distance = result.get('distance', 1.0)
                doc = result.get('document', '')
                
                truths.append(Truth(
                    source_type='best_practice',
                    source_name=metadata.get('filename', 'UKG Documentation'),
                    content=doc,
                    confidence=max(0.3, 1.0 - distance) if distance else 0.7,
                    location=f"Page {metadata.get('page', '?')}"
                ))
        
        except Exception as e:
            logger.error(f"Error gathering best practice: {e}")
        
        return truths
    
    def _detect_conflicts(self, reality, intent, best_practice) -> List[Conflict]:
        """Detect conflicts between the three truths."""
        # Placeholder - return empty for now
        return []
    
    def _run_proactive_checks(self, analysis: Dict) -> List[Insight]:
        """Run proactive checks while answering."""
        insights = []
        domains = analysis['domains']
        
        if not self.structured_handler:
            return insights
        
        try:
            tables = self.schema.get('tables', [])
            
            if 'employees' in domains or domains == ['general']:
                for table in tables:
                    table_name = table.get('table_name', '')
                    
                    if any(c in table_name.lower() for c in ['personal', 'employee']):
                        try:
                            sql = f'SELECT COUNT(*) as cnt FROM "{table_name}" WHERE ssn IS NULL OR ssn = \'\''
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
                        break
        
        except Exception as e:
            logger.error(f"Error in proactive checks: {e}")
        
        return insights
    
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
        """Synthesize a complete answer from all sources."""
        reasoning = []
        context_parts = []
        
        if reality:
            context_parts.append("=== CUSTOMER DATA ===")
            for truth in reality[:3]:
                if isinstance(truth.content, dict) and 'rows' in truth.content:
                    rows = truth.content['rows']
                    cols = truth.content['columns']
                    context_parts.append(f"\nSource: {truth.source_name}")
                    context_parts.append(f"Columns: {', '.join(cols[:10])}")
                    context_parts.append(f"Sample data ({len(rows)} rows):")
                    for row in rows[:5]:
                        row_str = " | ".join(f"{k}: {v}" for k, v in list(row.items())[:6])
                        context_parts.append(f"  {row_str}")
            reasoning.append(f"Found {len(reality)} relevant data sources")
        
        if intent:
            context_parts.append("\n=== CUSTOMER DOCUMENTS ===")
            for truth in intent[:3]:
                context_parts.append(f"\nSource: {truth.source_name} ({truth.location})")
                context_parts.append(str(truth.content)[:500])
            reasoning.append(f"Found {len(intent)} relevant customer documents")
        
        if best_practice:
            context_parts.append("\n=== UKG BEST PRACTICE ===")
            for truth in best_practice[:3]:
                context_parts.append(f"\nSource: {truth.source_name}")
                context_parts.append(str(truth.content)[:500])
            reasoning.append(f"Found {len(best_practice)} UKG best practice documents")
        
        if insights:
            context_parts.append("\n=== PROACTIVE INSIGHTS ===")
            for insight in insights:
                icon = '🔴' if insight.severity == 'high' else '🟡'
                context_parts.append(f"{icon} {insight.title}: {insight.description}")
        
        combined_context = '\n'.join(context_parts)
        
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
            answer=combined_context,
            confidence=confidence,
            from_reality=reality,
            from_intent=intent,
            from_best_practice=best_practice,
            conflicts=conflicts,
            insights=insights,
            structured_output=None,
            reasoning=reasoning
        )
