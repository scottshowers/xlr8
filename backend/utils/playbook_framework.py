"""
PLAYBOOK FRAMEWORK - Universal Playbook Engine for XLR8
========================================================

The reusable core that powers ALL playbooks. Domain-agnostic by design.

ARCHITECTURE:
-------------
┌─────────────────────────────────────────────────────────────┐
│                    PlaybookFramework                         │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ PlaybookDef │  │ ScanEngine  │  │ IntelligenceHook    │  │
│  │ (config)    │  │ (search)    │  │ (findings)          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Progress    │  │ Inheritance │  │ LearningHook        │  │
│  │ (tracking)  │  │ (parent→)   │  │ (feedback)          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Conflict    │  │ Export      │  │ AI Extraction       │  │
│  │ Detection   │  │ Engine      │  │ (findings)          │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘

USAGE:
------
1. Define your playbook using PlaybookDefinition
2. Register it with PlaybookRegistry
3. Framework handles: scanning, progress, export, learning

Author: XLR8 Team
Version: 1.1.0 - P3.6 P4 Learning Integration (Supabase)
Date: December 2025
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum
import logging
import json
import re
import os

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class ActionType(Enum):
    """Type of playbook action."""
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


class ActionStatus(Enum):
    """Status of a playbook action."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETE = "complete"
    NOT_APPLICABLE = "not_applicable"


class RiskLevel(Enum):
    """Risk level for findings."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ActionDefinition:
    """
    Definition of a single playbook action.
    
    This is the blueprint - what the action IS, not its current state.
    """
    action_id: str
    description: str
    action_type: ActionType = ActionType.RECOMMENDED
    reports_needed: List[str] = field(default_factory=list)
    due_date: Optional[str] = None
    quarter_end: bool = False
    keywords: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    guidance: Optional[str] = None
    consultative_prompt: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "action_id": self.action_id,
            "description": self.description,
            "action_type": self.action_type.value,
            "reports_needed": self.reports_needed,
            "due_date": self.due_date,
            "quarter_end": self.quarter_end,
            "keywords": self.keywords,
            "categories": self.categories,
            "guidance": self.guidance,
        }


@dataclass
class StepDefinition:
    """
    Definition of a playbook step containing multiple actions.
    """
    step_number: str
    step_name: str
    phase: str
    actions: List[ActionDefinition] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "step_number": self.step_number,
            "step_name": self.step_name,
            "phase": self.phase,
            "actions": [a.to_dict() for a in self.actions]
        }


@dataclass
class PlaybookDefinition:
    """
    Complete definition of a playbook.
    
    This is the configuration that makes a playbook unique:
    - Structure (steps, actions)
    - Domain-specific prompts
    - Custom export configuration
    """
    playbook_id: str
    name: str
    description: str
    version: str = "1.0.0"
    steps: List[StepDefinition] = field(default_factory=list)
    
    # Domain-specific configuration
    consultative_prompts: Dict[str, str] = field(default_factory=dict)
    dependent_guidance: Dict[str, str] = field(default_factory=dict)
    action_keywords: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)
    
    # Export configuration
    export_tabs: List[Dict[str, Any]] = field(default_factory=list)
    
    # Custom handlers (optional)
    custom_scan_handler: Optional[Callable] = None
    custom_export_handler: Optional[Callable] = None
    
    def get_action(self, action_id: str) -> Optional[ActionDefinition]:
        """Get action definition by ID."""
        for step in self.steps:
            for action in step.actions:
                if action.action_id == action_id:
                    return action
        return None
    
    def get_step_for_action(self, action_id: str) -> Optional[StepDefinition]:
        """Get the step containing an action."""
        for step in self.steps:
            for action in step.actions:
                if action.action_id == action_id:
                    return step
        return None
    
    def to_dict(self) -> Dict:
        return {
            "playbook_id": self.playbook_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "steps": [s.to_dict() for s in self.steps]
        }


@dataclass
class ActionProgress:
    """
    Current state of a playbook action for a specific project.
    
    This is the runtime state - what's happening NOW.
    """
    action_id: str
    status: ActionStatus = ActionStatus.NOT_STARTED
    findings: Optional[Dict[str, Any]] = None
    documents_found: List[str] = field(default_factory=list)
    inherited_from: Optional[List[str]] = None
    last_scan: Optional[str] = None
    notes: Optional[str] = None
    review_flag: Optional[str] = None
    is_dependent: bool = False
    intelligence_context: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict:
        return {
            "status": self.status.value,
            "findings": self.findings,
            "documents_found": self.documents_found,
            "inherited_from": self.inherited_from,
            "last_scan": self.last_scan,
            "notes": self.notes,
            "review_flag": self.review_flag,
            "is_dependent": self.is_dependent,
            "intelligence_context": self.intelligence_context,
        }
    
    @classmethod
    def from_dict(cls, action_id: str, data: Dict) -> 'ActionProgress':
        status_str = data.get("status", "not_started")
        try:
            status = ActionStatus(status_str)
        except ValueError:
            status = ActionStatus.NOT_STARTED
            
        return cls(
            action_id=action_id,
            status=status,
            findings=data.get("findings"),
            documents_found=data.get("documents_found", []),
            inherited_from=data.get("inherited_from"),
            last_scan=data.get("last_scan"),
            notes=data.get("notes"),
            review_flag=data.get("review_flag"),
            is_dependent=data.get("is_dependent", False),
            intelligence_context=data.get("intelligence_context"),
        )


@dataclass
class ScanResult:
    """Result of scanning for an action."""
    found: bool
    documents: List[Dict[str, Any]]
    findings: Optional[Dict[str, Any]]
    suggested_status: ActionStatus
    inherited_from: Optional[List[str]] = None
    conflicts: Optional[List[Dict[str, Any]]] = None
    intelligence: Optional[Dict[str, Any]] = None
    is_dependent: bool = False
    
    def to_dict(self) -> Dict:
        return {
            "found": self.found,
            "documents": self.documents,
            "findings": self.findings,
            "suggested_status": self.suggested_status.value,
            "inherited_from": self.inherited_from,
            "conflicts": self.conflicts,
            "intelligence": self.intelligence,
            "is_dependent": self.is_dependent,
        }


# =============================================================================
# PLAYBOOK REGISTRY - Central registry for all playbooks
# =============================================================================

class PlaybookRegistry:
    """
    Central registry for all playbook definitions.
    
    Playbooks register themselves here on startup.
    """
    _instance = None
    _playbooks: Dict[str, PlaybookDefinition] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._playbooks = {}
        return cls._instance
    
    def register(self, playbook: PlaybookDefinition) -> None:
        """Register a playbook definition."""
        self._playbooks[playbook.playbook_id] = playbook
        logger.info(f"[REGISTRY] Registered playbook: {playbook.playbook_id} ({playbook.name})")
    
    def get(self, playbook_id: str) -> Optional[PlaybookDefinition]:
        """Get a playbook by ID."""
        return self._playbooks.get(playbook_id)
    
    def list_all(self) -> List[str]:
        """List all registered playbook IDs."""
        return list(self._playbooks.keys())
    
    def get_all(self) -> Dict[str, PlaybookDefinition]:
        """Get all registered playbooks."""
        return self._playbooks.copy()


# Global registry instance
PLAYBOOK_REGISTRY = PlaybookRegistry()


# =============================================================================
# PROGRESS MANAGER - Handles save/load of progress state
# =============================================================================

class ProgressManager:
    """
    Manages playbook progress persistence.
    
    Stores progress per project per playbook.
    """
    
    def __init__(self, storage_path: str = "/data/playbook_progress.json"):
        self.storage_path = storage_path
        self._cache: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._load()
    
    def _load(self) -> None:
        """Load progress from disk."""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    self._cache = json.load(f)
                logger.info(f"[PROGRESS] Loaded progress from {self.storage_path}")
        except Exception as e:
            logger.warning(f"[PROGRESS] Could not load progress: {e}")
            self._cache = {}
    
    def _save(self) -> None:
        """Save progress to disk."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump(self._cache, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"[PROGRESS] Could not save progress: {e}")
    
    def get_project_progress(
        self, 
        playbook_id: str, 
        project_id: str
    ) -> Dict[str, ActionProgress]:
        """Get all action progress for a project."""
        key = f"{playbook_id}:{project_id}"
        raw = self._cache.get(key, {})
        return {
            action_id: ActionProgress.from_dict(action_id, data)
            for action_id, data in raw.items()
        }
    
    def get_action_progress(
        self, 
        playbook_id: str, 
        project_id: str, 
        action_id: str
    ) -> ActionProgress:
        """Get progress for a specific action."""
        key = f"{playbook_id}:{project_id}"
        raw = self._cache.get(key, {}).get(action_id, {})
        return ActionProgress.from_dict(action_id, raw)
    
    def update_action_progress(
        self, 
        playbook_id: str, 
        project_id: str, 
        progress: ActionProgress
    ) -> None:
        """Update progress for a specific action."""
        key = f"{playbook_id}:{project_id}"
        if key not in self._cache:
            self._cache[key] = {}
        self._cache[key][progress.action_id] = progress.to_dict()
        self._save()
    
    def bulk_update(
        self, 
        playbook_id: str, 
        project_id: str, 
        progress_dict: Dict[str, ActionProgress]
    ) -> None:
        """Bulk update progress for multiple actions."""
        key = f"{playbook_id}:{project_id}"
        if key not in self._cache:
            self._cache[key] = {}
        for action_id, progress in progress_dict.items():
            self._cache[key][action_id] = progress.to_dict()
        self._save()
    
    def get_raw_progress(self, playbook_id: str, project_id: str) -> Dict:
        """Get raw progress dict (for export compatibility)."""
        key = f"{playbook_id}:{project_id}"
        return self._cache.get(key, {})


# Global progress manager
PROGRESS_MANAGER = ProgressManager()


# =============================================================================
# INTELLIGENCE HOOK - Integration with Intelligence Engine
# =============================================================================

class IntelligenceHook:
    """
    Hook into the Project Intelligence Service.
    
    Provides pre-computed findings, tasks, and lookups.
    """
    
    @staticmethod
    def is_available() -> bool:
        """Check if intelligence service is available."""
        try:
            from backend.utils.project_intelligence import get_project_intelligence
            return True
        except ImportError:
            try:
                from utils.project_intelligence import get_project_intelligence
                return True
            except ImportError:
                return False
    
    @staticmethod
    def get_context(
        project_id: str, 
        action_id: str, 
        action_keywords: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Get intelligence context for an action.
        
        Returns:
            {
                'available': bool,
                'findings': List[Dict],
                'tasks': List[Dict],
                'lookups': List[Dict],
                'summary': Dict
            }
        """
        result = {
            'available': False,
            'findings': [],
            'tasks': [],
            'lookups': [],
            'summary': {}
        }
        
        if not IntelligenceHook.is_available():
            return result
        
        try:
            # Import intelligence service
            try:
                from backend.utils.project_intelligence import get_project_intelligence
            except ImportError:
                from utils.project_intelligence import get_project_intelligence
            
            try:
                from utils.structured_data_handler import get_structured_handler
            except ImportError:
                from backend.utils.structured_data_handler import get_structured_handler
            
            handler = get_structured_handler()
            service = get_project_intelligence(project_id, handler)
            
            if not service or not service.analyzed_at:
                logger.debug(f"[INTELLIGENCE] Project {project_id[:8]} not analyzed yet")
                return result
            
            result['available'] = True
            
            # Summary stats
            result['summary'] = {
                'total_tables': service.total_tables,
                'total_rows': service.total_rows,
                'total_findings': len(service.findings),
                'analyzed_at': service.analyzed_at.isoformat() if service.analyzed_at else None
            }
            
            keywords = action_keywords.get('keywords', [])
            categories = action_keywords.get('categories', [])
            
            # Filter relevant findings
            for finding in service.findings:
                finding_dict = finding.to_dict() if hasattr(finding, 'to_dict') else finding
                if IntelligenceHook._is_finding_relevant(finding_dict, keywords, categories):
                    result['findings'].append({
                        'id': finding_dict.get('id'),
                        'title': finding_dict.get('title'),
                        'description': finding_dict.get('description'),
                        'severity': finding_dict.get('severity', {}).get('value') if isinstance(finding_dict.get('severity'), dict) else str(finding_dict.get('severity', '')),
                        'category': finding_dict.get('category'),
                        'table': finding_dict.get('table'),
                        'column': finding_dict.get('column'),
                        'source': 'intelligence_engine'
                    })
            
            # Filter relevant tasks
            for task in service.tasks:
                task_dict = task.to_dict() if hasattr(task, 'to_dict') else task
                if IntelligenceHook._is_task_relevant(task_dict, keywords):
                    result['tasks'].append({
                        'id': task_dict.get('id'),
                        'title': task_dict.get('title'),
                        'shortcut': task_dict.get('shortcut'),
                        'status': task_dict.get('status', {}).get('value') if isinstance(task_dict.get('status'), dict) else str(task_dict.get('status', '')),
                        'source': 'intelligence_engine'
                    })
            
            # Include lookups
            for lookup in service.lookups[:10]:
                lookup_dict = lookup.to_dict() if hasattr(lookup, 'to_dict') else lookup
                result['lookups'].append({
                    'table': lookup_dict.get('table'),
                    'lookup_type': lookup_dict.get('lookup_type'),
                    'entry_count': lookup_dict.get('entry_count', 0)
                })
            
            logger.info(f"[INTELLIGENCE] Action {action_id}: {len(result['findings'])} findings, {len(result['tasks'])} tasks")
            return result
            
        except Exception as e:
            logger.warning(f"[INTELLIGENCE] Failed to get context: {e}")
            return result
    
    @staticmethod
    def _is_finding_relevant(finding: Dict, keywords: List[str], categories: List[str]) -> bool:
        """Check if a finding is relevant based on keywords."""
        finding_category = finding.get('category', '')
        if isinstance(finding_category, dict):
            finding_category = finding_category.get('value', '')
        
        category_match = any(cat.lower() in str(finding_category).lower() for cat in categories)
        
        text_to_check = ' '.join([
            str(finding.get('title', '')),
            str(finding.get('description', '')),
            str(finding.get('table', '')),
            str(finding.get('column', ''))
        ]).lower()
        
        keyword_match = any(kw.lower() in text_to_check for kw in keywords)
        return category_match or keyword_match
    
    @staticmethod
    def _is_task_relevant(task: Dict, keywords: List[str]) -> bool:
        """Check if a task is relevant based on keywords."""
        text_to_check = ' '.join([
            str(task.get('title', '')),
            str(task.get('shortcut', ''))
        ]).lower()
        return any(kw.lower() in text_to_check for kw in keywords)


# =============================================================================
# LEARNING HOOK - Integration with Learning Engine (P4 preparation)
# =============================================================================

class LearningHook:
    """
    Hook into the Learning Module (Supabase-backed).
    
    Provides feedback recording and pattern retrieval.
    This is a HOOK - actual implementation is in learning.py (Supabase).
    
    P3.6 P4: Rewired to use learning.py instead of learning_engine.py
    so that feedback shows in the Admin UI.
    """
    
    @staticmethod
    def is_available() -> bool:
        """Check if learning module is available."""
        try:
            from backend.utils.learning import get_learning_module
            module = get_learning_module()
            return module.supabase is not None
        except ImportError:
            try:
                from utils.learning import get_learning_module
                module = get_learning_module()
                return module.supabase is not None
            except ImportError:
                return False
    
    @staticmethod
    def record_feedback(
        project_id: str,
        playbook_id: str,
        action_id: str,
        finding_text: str,
        feedback: str,  # 'keep', 'discard', 'modify'
        reason: Optional[str] = None
    ) -> bool:
        """
        Record user feedback on a finding.
        
        This trains the system to make better recommendations.
        Stores in Supabase so it shows in Admin UI.
        """
        if not LearningHook.is_available():
            logger.warning("[LEARNING] Learning module not available")
            return False
        
        try:
            try:
                from backend.utils.learning import get_learning_module
            except ImportError:
                from utils.learning import get_learning_module
            
            learning = get_learning_module()
            success = learning.record_playbook_feedback(
                project_id=project_id,
                playbook_id=playbook_id,
                action_id=action_id,
                finding_text=finding_text,
                feedback=feedback,
                reason=reason
            )
            
            if success:
                logger.info(f"[LEARNING] Recorded feedback: {feedback} for {action_id}")
            return success
            
        except Exception as e:
            logger.warning(f"[LEARNING] Failed to record feedback: {e}")
            return False
    
    @staticmethod
    def get_learned_patterns(project_id: str, playbook_id: str) -> Dict[str, Any]:
        """
        Get learned patterns for a project/playbook.
        
        Returns patterns that should influence findings.
        Reads from Supabase.
        """
        if not LearningHook.is_available():
            return {'suppressions': [], 'preferences': {}}
        
        try:
            try:
                from backend.utils.learning import get_learning_module
            except ImportError:
                from utils.learning import get_learning_module
            
            learning = get_learning_module()
            return learning.get_playbook_patterns(project_id, playbook_id)
            
        except Exception as e:
            logger.warning(f"[LEARNING] Failed to get patterns: {e}")
            return {'suppressions': [], 'preferences': {}}
    
    @staticmethod
    def _normalize_for_matching(text: str) -> str:
        """Normalize text for suppression matching (same as learning.py)."""
        import re
        # Replace numbers with N, lowercase, truncate
        normalized = re.sub(r'\d+', 'N', text.lower())
        normalized = ' '.join(normalized.split())  # Clean whitespace
        return normalized[:100]
    
    @staticmethod
    def apply_learned_suppressions(
        findings: Dict[str, Any],
        patterns: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply learned suppressions to findings.
        
        Removes or marks findings that user has previously discarded.
        
        IMPORTANT: Both the finding and the suppression pattern are normalized
        (numbers replaced with 'N', lowercased) before comparison.
        """
        if not findings or not patterns.get('suppressions'):
            return findings
        
        suppressions = patterns['suppressions']
        
        def should_suppress(text: str) -> bool:
            """Check if text matches any suppression pattern."""
            normalized_text = LearningHook._normalize_for_matching(text)
            for supp in suppressions:
                # Normalize suppression too (in case it wasn't already)
                normalized_supp = LearningHook._normalize_for_matching(supp)
                if normalized_supp in normalized_text or normalized_text in normalized_supp:
                    logger.debug(f"[LEARNING] Match: '{normalized_supp}' <-> '{normalized_text}'")
                    return True
            return False
        
        # Filter issues
        if findings.get('issues'):
            original_count = len(findings['issues'])
            findings['issues'] = [
                issue for issue in findings['issues']
                if not should_suppress(issue)
            ]
            suppressed = original_count - len(findings['issues'])
            if suppressed > 0:
                logger.info(f"[LEARNING] Suppressed {suppressed} issues based on learned patterns")
        
        # Filter recommendations
        if findings.get('recommendations'):
            original_count = len(findings['recommendations'])
            findings['recommendations'] = [
                rec for rec in findings['recommendations']
                if not should_suppress(rec)
            ]
            suppressed = original_count - len(findings['recommendations'])
            if suppressed > 0:
                logger.info(f"[LEARNING] Suppressed {suppressed} recommendations based on learned patterns")
        
        return findings


# =============================================================================
# DOCUMENT SCANNER - Search ChromaDB and DuckDB for documents
# =============================================================================

class DocumentScanner:
    """
    Scans for documents relevant to a playbook action.
    
    Sources:
    - ChromaDB (vector chunks from PDFs, docs)
    - DuckDB (structured data from Excel, CSV)
    """
    
    @staticmethod
    def get_project_files(project_id: str) -> set:
        """Get all files associated with a project."""
        project_files = set()
        
        # Look up project name from UUID for better matching
        project_name = None
        try:
            from backend.utils.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            if supabase:
                result = supabase.table('projects').select('name').eq('id', project_id).execute()
                if result.data:
                    project_name = result.data[0].get('name')
                    logger.debug(f"[SCAN] Resolved project: {project_id[:8]} -> {project_name}")
        except Exception as e:
            logger.debug(f"[SCAN] Project name lookup failed: {e}")
        
        # Source 1: ChromaDB
        try:
            from utils.rag_handler import RAGHandler
            rag = RAGHandler()
            collection = rag.client.get_or_create_collection(name="documents")
            all_results = collection.get(include=["metadatas"], limit=1000)
            
            for metadata in all_results.get("metadatas", []):
                doc_project = metadata.get("project_id") or metadata.get("project", "")
                doc_project_name = metadata.get("project") or ""
                
                is_global = doc_project_name.lower() in ('global', '__global__', 'global/universal')
                is_this_project = (
                    doc_project == project_id or 
                    doc_project == project_id[:8] or
                    (project_name and doc_project_name.lower() == project_name.lower())
                )
                
                if is_global or is_this_project:
                    filename = metadata.get("source", metadata.get("filename", ""))
                    if filename:
                        project_files.add(filename)
                        
        except Exception as e:
            logger.debug(f"[SCAN] ChromaDB query failed: {e}")
        
        # Source 2: DuckDB _pdf_tables
        try:
            from backend.utils.playbook_parser import get_duckdb_connection
            conn = get_duckdb_connection()
            if conn:
                table_check = conn.execute("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = '_pdf_tables'
                """).fetchone()
                
                if table_check and table_check[0] > 0:
                    # Check if project_id column exists
                    cols = conn.execute("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name = '_pdf_tables'
                    """).fetchall()
                    col_names = [c[0] for c in cols]
                    has_project_id = 'project_id' in col_names
                    
                    if has_project_id:
                        result = conn.execute("""
                            SELECT DISTINCT source_file, project, project_id
                            FROM _pdf_tables
                            WHERE source_file IS NOT NULL
                        """).fetchall()
                    else:
                        result = conn.execute("""
                            SELECT DISTINCT source_file, project, NULL as project_id
                            FROM _pdf_tables
                            WHERE source_file IS NOT NULL
                        """).fetchall()
                    
                    logger.warning(f"[SCAN] _pdf_tables has {len(result)} distinct files, looking for project {project_id[:8]}")
                    
                    for row in result:
                        source_file, proj, proj_id = row
                        logger.warning(f"[SCAN] _pdf_tables row: file={source_file}, proj={proj}, proj_id={proj_id}")
                        is_global = proj and proj.lower() in ('global', '__global__', 'global/universal')
                        # Match on project_id (UUID) OR project name OR partial UUID in name
                        is_this_project = (
                            (proj_id and proj_id == project_id) or
                            (proj_id and project_id[:8].lower() in (proj_id or '').lower()) or
                            (proj and project_id[:8].lower() in proj.lower()) or
                            (project_name and proj and proj.lower() == project_name.lower())
                        )
                        
                        if is_global or is_this_project:
                            if source_file:
                                project_files.add(source_file)
                                logger.warning(f"[SCAN] ✓ Matched: {source_file}")
                
                conn.close()
        except Exception as e:
            logger.debug(f"[SCAN] DuckDB _pdf_tables query failed: {e}")
        
        # Source 3: DuckDB _schema_metadata (Excel files)
        try:
            from backend.utils.playbook_parser import get_duckdb_connection
            conn = get_duckdb_connection()
            if conn:
                # Check if project_id column exists
                cols = conn.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = '_schema_metadata'
                """).fetchall()
                col_names = [c[0] for c in cols]
                has_project_id = 'project_id' in col_names
                
                if has_project_id:
                    result = conn.execute("""
                        SELECT DISTINCT file_name, project, project_id
                        FROM _schema_metadata
                        WHERE file_name IS NOT NULL
                    """).fetchall()
                else:
                    result = conn.execute("""
                        SELECT DISTINCT file_name, project, NULL as project_id
                        FROM _schema_metadata
                        WHERE file_name IS NOT NULL
                    """).fetchall()
                
                for row in result:
                    source_file, proj, proj_id = row
                    is_global = proj and proj.lower() in ('global', '__global__', 'global/universal')
                    # Match on project_id (UUID) OR project name OR partial UUID in name
                    is_this_project = (
                        (proj_id and proj_id == project_id) or
                        (proj_id and project_id[:8].lower() in (proj_id or '').lower()) or
                        (proj and project_id[:8].lower() in proj.lower()) or
                        (project_name and proj and proj.lower() == project_name.lower())
                    )
                    
                    if is_global or is_this_project:
                        if source_file:
                            project_files.add(source_file)
                
                conn.close()
        except Exception as e:
            logger.debug(f"[SCAN] DuckDB _schema_metadata query failed: {e}")
        
        return project_files
    
    @staticmethod
    def search_by_filename(
        project_files: set,
        reports_needed: List[str]
    ) -> List[Dict[str, Any]]:
        """Match files by filename to required reports."""
        found_docs = []
        seen_files = set()
        
        for report_name in reports_needed:
            report_keywords = report_name.lower().split()
            for filename in project_files:
                filename_lower = filename.lower()
                matches = sum(1 for kw in report_keywords if kw in filename_lower)
                if matches >= len(report_keywords) - 1:  # Allow 1 word missing
                    if filename not in seen_files:
                        seen_files.add(filename)
                        found_docs.append({
                            "filename": filename,
                            "snippet": f"Matched report: {report_name}",
                            "query": report_name,
                            "match_type": "filename"
                        })
        
        return found_docs
    
    @staticmethod
    def search_semantic(
        project_id: str,
        reports_needed: List[str],
        action_description: str
    ) -> List[Dict[str, Any]]:
        """Semantic search using RAG."""
        results = []
        
        try:
            from utils.rag_handler import RAGHandler
            rag = RAGHandler()
            
            # Primary search: combined reports
            if reports_needed:
                primary_query = " ".join(reports_needed[:5])
                try:
                    search_results = rag.search(
                        collection_name="documents",
                        query=primary_query,
                        n_results=40,
                        project_id=project_id
                    )
                    if search_results:
                        results.extend(search_results)
                except Exception:
                    pass
            
            # Secondary search: action description
            if action_description and len(action_description) > 20:
                try:
                    search_results = rag.search(
                        collection_name="documents",
                        query=action_description[:100],
                        n_results=20,
                        project_id=project_id
                    )
                    if search_results:
                        results.extend(search_results)
                except Exception:
                    pass
                    
        except Exception as e:
            logger.debug(f"[SCAN] Semantic search failed: {e}")
        
        return results
    
    @staticmethod
    def get_structured_data(
        project_files: set
    ) -> List[str]:
        """Get structured data from DuckDB tables."""
        content = []
        
        try:
            from backend.utils.playbook_parser import get_duckdb_connection
            conn = get_duckdb_connection()
            if not conn:
                return content
            
            # Use _schema_metadata (where all tables including PDFs are tracked)
            table_check = conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = '_schema_metadata'
            """).fetchone()
            
            if not table_check or table_check[0] == 0:
                logger.warning(f"[SCAN] _schema_metadata table not found")
                conn.close()
                return content
            
            # Get all tables from _schema_metadata
            all_tables = conn.execute("""
                SELECT table_name, columns, file_name
                FROM _schema_metadata
                WHERE is_current = TRUE
            """).fetchall()
            
            logger.warning(f"[SCAN] _schema_metadata has {len(all_tables)} current tables")
            
            seen_tables = set()
            
            for filename in project_files:
                if not filename:
                    continue
                
                filename_norm = filename.lower().replace("'", "").replace("'", "").replace(".pdf", "").replace(".xlsx", "").replace(".csv", "")
                
                for table_name, columns_json, source_file in all_tables:
                    if not source_file or table_name in seen_tables:
                        continue
                    source_norm = source_file.lower().replace("'", "").replace("'", "").replace(".pdf", "").replace(".xlsx", "").replace(".csv", "")
                    
                    if filename_norm in source_norm or source_norm in filename_norm:
                        seen_tables.add(table_name)
                        logger.warning(f"[SCAN] Matched table '{table_name}' for file '{filename}'")
                        try:
                            data = conn.execute(f'SELECT * FROM "{table_name}"').fetchall()
                            # Parse columns from JSON
                            if columns_json:
                                try:
                                    columns_data = json.loads(columns_json)
                                    # Handle both formats: list of strings or list of dicts
                                    if columns_data and isinstance(columns_data[0], dict):
                                        columns = [c.get('name', f'col_{i}') for i, c in enumerate(columns_data)]
                                    else:
                                        columns = columns_data
                                except:
                                    columns = []
                            else:
                                columns = []
                            
                            if data:
                                # If no columns from metadata, get from table
                                if not columns:
                                    col_info = conn.execute(f'SELECT column_name FROM information_schema.columns WHERE table_name = ?', [table_name]).fetchall()
                                    columns = [c[0] for c in col_info]
                                
                                content_lines = [f"[FILE: {filename}] [TABLE: {table_name}] [{len(data)} rows]"]
                                content_lines.append("|".join(columns))
                                
                                for row in data[:500]:  # Limit to first 500 rows
                                    row_vals = [str(row[i]) if i < len(row) and row[i] else "" for i in range(len(columns))]
                                    content_lines.append("|".join(row_vals))
                                
                                content.append("\n".join(content_lines))
                                logger.warning(f"[SCAN] Added {len(data)} rows from '{table_name}'")
                        except Exception as e:
                            logger.warning(f"[SCAN] Failed to read table '{table_name}': {e}")
            
            conn.close()
            
        except Exception as e:
            logger.warning(f"[SCAN] Structured data query failed: {e}")
        
        return content


# =============================================================================
# FINDINGS EXTRACTOR - AI-powered findings extraction
# =============================================================================

class FindingsExtractor:
    """
    Extracts findings from document content using AI.
    
    Uses consultative prompts for domain-specific analysis.
    """
    
    @staticmethod
    async def extract(
        action: ActionDefinition,
        content: List[str],
        inherited_findings: List[Dict],
        project_id: str,
        consultative_prompt: Optional[str] = None,
        intelligence_findings: Optional[List[Dict]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Extract findings from content using Claude.
        
        Args:
            action: The action definition
            content: Document content to analyze
            inherited_findings: Findings from parent actions
            project_id: Project ID
            consultative_prompt: Domain-specific analysis prompt
            intelligence_findings: Pre-computed findings from intelligence engine
            
        Returns:
            Findings dict with issues, recommendations, etc.
        """
        if not content and not inherited_findings:
            return None
        
        try:
            import anthropic
            import os
            api_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                logger.error("[EXTRACT] No Claude API key found")
                return None
            client = anthropic.Anthropic(api_key=api_key)
        except Exception as e:
            logger.error(f"[EXTRACT] Claude client init failed: {e}")
            return None
        
        # Build content summary
        content_summary = "\n\n---\n\n".join(content[:10]) if content else "No new content"
        
        # Build inherited context
        inherited_text = ""
        if inherited_findings:
            inherited_parts = []
            for inf in inherited_findings:
                if isinstance(inf, dict) and inf.get('findings'):
                    inherited_parts.append(json.dumps(inf['findings'], indent=2))
            if inherited_parts:
                inherited_text = f"\n\nINHERITED FINDINGS:\n{chr(10).join(inherited_parts)}"
        
        # Build intelligence context
        intelligence_text = ""
        if intelligence_findings:
            intel_parts = [f"- {f.get('title', 'Unknown')}: {f.get('description', '')}" for f in intelligence_findings[:10]]
            if intel_parts:
                intelligence_text = f"\n\nPRE-ANALYZED ISSUES FROM INTELLIGENCE ENGINE:\n{chr(10).join(intel_parts)}"
        
        # Build prompt
        base_prompt = f"""Analyze this data for playbook action: {action.action_id}

ACTION: {action.description}

REPORTS NEEDED: {', '.join(action.reports_needed) if action.reports_needed else 'None specified'}

{consultative_prompt or ''}

DOCUMENT CONTENT:
{content_summary}
{inherited_text}
{intelligence_text}

Analyze the content and return JSON:
{{
    "complete": true/false,
    "key_values": {{"field": "value (Source: filename)"}},
    "issues": [],
    "recommendations": [],
    "risk_level": "low|medium|high",
    "summary": "2-3 sentences with specific findings",
    "sources_used": ["filenames"]
}}

Empty arrays are FINE. Don't invent problems. Return ONLY valid JSON."""

        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                temperature=0,
                messages=[{"role": "user", "content": base_prompt}]
            )
            
            text = response.content[0].text.strip()
            
            # Clean markdown
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            
            result = json.loads(text)
            result['_analyzed_by'] = 'claude'
            return result
            
        except Exception as e:
            logger.error(f"[EXTRACT] Failed to extract findings: {e}")
            return None


# =============================================================================
# CONFLICT DETECTOR - Detect inconsistencies between actions
# =============================================================================

class ConflictDetector:
    """
    Detects conflicts between findings from different actions.
    """
    
    @staticmethod
    async def detect(
        project_id: str,
        playbook_id: str,
        action_id: str,
        new_findings: Optional[Dict]
    ) -> List[Dict[str, Any]]:
        """
        Detect conflicts between new findings and existing data.
        
        Returns list of conflict objects.
        """
        if not new_findings or not new_findings.get("key_values"):
            return []
        
        conflicts = []
        progress = PROGRESS_MANAGER.get_raw_progress(playbook_id, project_id)
        new_values = new_findings.get("key_values", {})
        
        critical_fields = ["rate", "amount", "count", "total"]
        
        def normalize_value(value: str) -> str:
            if not value:
                return ""
            val = str(value).strip()
            val = re.sub(r'\s*\(Source:\s*[^)]+\)', '', val)
            try:
                cleaned = val.replace('%', '').replace('$', '').replace(',', '').strip()
                num = float(cleaned)
                return f"{num:.4f}"
            except (ValueError, TypeError):
                return val.lower()
        
        for other_action_id, other_progress in progress.items():
            if other_action_id == action_id:
                continue
            
            other_findings = other_progress.get("findings") if other_progress else None
            if not other_findings or not isinstance(other_findings, dict):
                continue
            other_values = other_findings.get("key_values", {})
            
            for field in critical_fields:
                new_val = None
                other_val = None
                
                for k, v in new_values.items():
                    if field.lower() in k.lower():
                        new_val = normalize_value(str(v))
                        break
                
                for k, v in other_values.items():
                    if field.lower() in k.lower():
                        other_val = normalize_value(str(v))
                        break
                
                if new_val and other_val and new_val != other_val:
                    conflicts.append({
                        "field": field,
                        "action_1": action_id,
                        "action_2": other_action_id,
                        "message": f"Value mismatch: {field} differs between {action_id} and {other_action_id}"
                    })
        
        return conflicts


# =============================================================================
# INHERITANCE MANAGER - Handle parent/child action relationships
# =============================================================================

class InheritanceManager:
    """
    Manages inheritance between parent and child actions.
    """
    
    @staticmethod
    def build_dependencies(playbook: PlaybookDefinition) -> Dict[str, List[str]]:
        """
        Build action dependencies from playbook structure.
        
        Logic: Within each step, actions without reports_needed depend on
        the first action in that step that HAS reports_needed.
        """
        dependencies = {}
        
        for step in playbook.steps:
            actions = step.actions
            
            # Find primary action (first with reports_needed)
            primary_action = None
            for action in actions:
                if action.reports_needed:
                    primary_action = action.action_id
                    break
            
            if not primary_action:
                continue
            
            # Other actions depend on primary
            for action in actions:
                if action.action_id != primary_action and not action.reports_needed:
                    dependencies[action.action_id] = [primary_action]
        
        return dependencies
    
    @staticmethod
    def get_parent_actions(
        action_id: str, 
        dependencies: Dict[str, List[str]]
    ) -> List[str]:
        """Get parent actions for a given action."""
        return dependencies.get(action_id, [])
    
    @staticmethod
    def get_inherited_data(
        playbook_id: str,
        project_id: str,
        action_id: str,
        dependencies: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        Get inherited documents, findings, and content from parent actions.
        """
        result = {
            "documents": [],
            "findings": [],
            "content": []
        }
        
        parent_actions = InheritanceManager.get_parent_actions(action_id, dependencies)
        if not parent_actions:
            return result
        
        for parent_id in parent_actions:
            parent_progress = PROGRESS_MANAGER.get_action_progress(
                playbook_id, project_id, parent_id
            )
            
            if parent_progress.documents_found:
                result["documents"].extend(parent_progress.documents_found)
            
            if parent_progress.findings:
                result["findings"].append({
                    "action_id": parent_id,
                    "findings": parent_progress.findings
                })
                
                # Add summary as context
                if parent_progress.findings.get("summary"):
                    result["content"].append(
                        f"[From {parent_id}]: {parent_progress.findings['summary']}"
                    )
        
        return result


# =============================================================================
# PLAYBOOK ENGINE - The main orchestrator
# =============================================================================

class PlaybookEngine:
    """
    The main playbook engine that orchestrates all operations.
    
    This is what routers interact with.
    """
    
    def __init__(self, playbook: PlaybookDefinition):
        self.playbook = playbook
        self.dependencies = InheritanceManager.build_dependencies(playbook)
    
    def get_structure(self) -> Dict:
        """Get playbook structure for frontend."""
        return self.playbook.to_dict()
    
    def get_progress(self, project_id: str) -> Dict[str, Any]:
        """Get all progress for a project."""
        raw = PROGRESS_MANAGER.get_raw_progress(self.playbook.playbook_id, project_id)
        return raw
    
    async def scan_action(
        self,
        project_id: str,
        action_id: str
    ) -> ScanResult:
        """
        Scan documents for a specific action.
        
        This is the main scan entry point.
        """
        logger.warning(f"[SCAN] ====== START {action_id} in project {project_id[:8]} ======")
        
        # Get action definition
        action = self.playbook.get_action(action_id)
        if not action:
            raise ValueError(f"Action {action_id} not found")
        
        logger.warning(f"[SCAN] Action reports_needed: {action.reports_needed}")
        
        # Get parent actions
        parent_actions = InheritanceManager.get_parent_actions(action_id, self.dependencies)
        
        # Check if this is a dependent action (no reports_needed)
        if not action.reports_needed and parent_actions:
            return await self._handle_dependent_action(project_id, action, parent_actions)
        
        # Get intelligence context
        action_keywords = self.playbook.action_keywords.get(action_id, {
            'keywords': ['data', 'quality', 'missing', 'duplicate', 'error'],
            'categories': ['QUALITY', 'PATTERN']
        })
        intelligence_context = IntelligenceHook.get_context(
            project_id, action_id, action_keywords
        )
        intelligence_findings = intelligence_context.get('findings', [])
        intelligence_tasks = intelligence_context.get('tasks', [])
        
        # Get inherited data
        inherited = InheritanceManager.get_inherited_data(
            self.playbook.playbook_id, project_id, action_id, self.dependencies
        )
        
        # Get project files
        project_files = DocumentScanner.get_project_files(project_id)
        logger.warning(f"[SCAN] Found {len(project_files)} project files: {list(project_files)[:5]}")
        
        # Search by filename
        found_docs = DocumentScanner.search_by_filename(
            project_files, action.reports_needed
        )
        logger.warning(f"[SCAN] Filename search found {len(found_docs)} docs: {[d.get('filename') for d in found_docs]}")
        seen_files = set(d['filename'] for d in found_docs)
        
        # Add inherited docs
        for doc_name in inherited["documents"]:
            if doc_name not in seen_files:
                seen_files.add(doc_name)
                found_docs.append({
                    "filename": doc_name,
                    "snippet": f"Inherited from {', '.join(parent_actions)}",
                    "match_type": "inherited"
                })
        
        # Collect all content
        all_content = list(inherited["content"])
        
        # Add filename matches as content hints
        for doc in found_docs:
            if doc.get('match_type') == 'filename':
                all_content.append(f"[FILE: {doc['filename']}] - matches required report")
        
        # Semantic search
        semantic_results = DocumentScanner.search_semantic(
            project_id, action.reports_needed, action.description
        )
        logger.warning(f"[SCAN] Semantic search returned {len(semantic_results)} results")
        
        seen_content = set()
        for result in semantic_results:
            doc = result.get('document', '')
            if not doc or len(doc) < 50:
                continue
            
            content_hash = hash(doc[:500])
            if content_hash in seen_content:
                continue
            seen_content.add(content_hash)
            
            cleaned = re.sub(r'ENC256:[A-Za-z0-9+/=]+', '[ENCRYPTED]', doc)
            if cleaned.count('[ENCRYPTED]') >= 10:
                continue
            
            metadata = result.get('metadata', {})
            filename = metadata.get('source', metadata.get('filename', 'Unknown'))
            all_content.append(f"[FILE: {filename}]\n{cleaned[:3000]}")
            
            if filename not in seen_files:
                seen_files.add(filename)
                found_docs.append({
                    "filename": filename,
                    "snippet": cleaned[:300],
                    "match_type": "semantic"
                })
        
        # Get structured data (DuckDB) - ONLY for matched files, not all project files
        duckdb_content = DocumentScanner.get_structured_data(seen_files)
        logger.warning(f"[SCAN] DuckDB structured data: {len(duckdb_content)} content blocks for {len(seen_files)} matched files")
        if duckdb_content:
            logger.warning(f"[SCAN] First DuckDB block preview: {duckdb_content[0][:200] if duckdb_content[0] else 'empty'}...")
        
        final_content = duckdb_content + all_content[:20]
        
        # Log which files are represented in final content
        files_in_content = set()
        for block in final_content:
            if block.startswith('[FILE:'):
                file_name = block.split(']')[0].replace('[FILE:', '').strip()
                files_in_content.add(file_name)
        logger.warning(f"[SCAN] Final content: {len(final_content)} blocks from files: {files_in_content}")
        
        # Determine status and extract findings
        findings = None
        suggested_status = ActionStatus.NOT_STARTED
        
        has_data = len(found_docs) > 0 or len(inherited["findings"]) > 0 or len(final_content) > 0
        
        if has_data:
            suggested_status = ActionStatus.IN_PROGRESS
            
            # Get consultative prompt
            consultative_prompt = self.playbook.consultative_prompts.get(action_id)
            
            # Extract findings
            if final_content or inherited["findings"]:
                findings = await FindingsExtractor.extract(
                    action=action,
                    content=final_content,
                    inherited_findings=inherited["findings"],
                    project_id=project_id,
                    consultative_prompt=consultative_prompt,
                    intelligence_findings=intelligence_findings
                )
                
                # Merge intelligence findings
                if findings and intelligence_findings:
                    existing_issues = set(findings.get('issues') or [])
                    for intel_finding in intelligence_findings:
                        issue_text = f"[Intelligence] {intel_finding.get('title', 'Unknown issue')}"
                        if intel_finding.get('severity') in ['critical', 'warning']:
                            if issue_text not in existing_issues:
                                if 'issues' not in findings:
                                    findings['issues'] = []
                                findings['issues'].append(issue_text)
                    
                    # Add intelligence tasks as recommendations
                    existing_recs = set(findings.get('recommendations') or [])
                    for intel_task in intelligence_tasks:
                        if intel_task.get('status') != 'complete':
                            rec_text = f"[Task] {intel_task.get('title', 'Unknown task')}"
                            shortcut = intel_task.get('shortcut')
                            if shortcut:
                                rec_text += f" - {shortcut}"
                            if rec_text not in existing_recs:
                                if 'recommendations' not in findings:
                                    findings['recommendations'] = []
                                findings['recommendations'].append(rec_text)
                
                # Apply learned suppressions
                if findings:
                    patterns = LearningHook.get_learned_patterns(
                        project_id, self.playbook.playbook_id
                    )
                    findings = LearningHook.apply_learned_suppressions(findings, patterns)
        
        # Detect conflicts
        conflicts = await ConflictDetector.detect(
            project_id, self.playbook.playbook_id, action_id, findings
        )
        if conflicts:
            findings = findings or {}
            findings['conflicts'] = conflicts
            if suggested_status == ActionStatus.COMPLETE:
                suggested_status = ActionStatus.IN_PROGRESS
        
        # Update progress
        progress = ActionProgress(
            action_id=action_id,
            status=suggested_status,
            findings=findings,
            documents_found=[d['filename'] for d in found_docs],
            inherited_from=parent_actions if parent_actions else None,
            last_scan=datetime.now().isoformat(),
            intelligence_context={
                'available': intelligence_context['available'],
                'findings_count': len(intelligence_findings),
                'tasks_count': len(intelligence_tasks)
            } if intelligence_context['available'] else None
        )
        PROGRESS_MANAGER.update_action_progress(
            self.playbook.playbook_id, project_id, progress
        )
        
        return ScanResult(
            found=len(found_docs) > 0,
            documents=found_docs,
            findings=findings,
            suggested_status=suggested_status,
            inherited_from=parent_actions if parent_actions else None,
            conflicts=conflicts,
            intelligence={
                'available': intelligence_context['available'],
                'findings': intelligence_findings,
                'tasks': intelligence_tasks,
                'summary': intelligence_context.get('summary', {})
            } if intelligence_context['available'] else None
        )
    
    async def _handle_dependent_action(
        self,
        project_id: str,
        action: ActionDefinition,
        parent_actions: List[str]
    ) -> ScanResult:
        """Handle scan for a dependent action (no reports_needed)."""
        logger.info(f"[DEPENDENT] Handling dependent action {action.action_id}")
        
        # Get parent progress
        all_parents_complete = True
        parent_docs = []
        primary_parent = parent_actions[0] if parent_actions else None
        
        for parent_id in parent_actions:
            parent_progress = PROGRESS_MANAGER.get_action_progress(
                self.playbook.playbook_id, project_id, parent_id
            )
            if parent_progress.documents_found:
                parent_docs.extend(parent_progress.documents_found)
            if parent_progress.status != ActionStatus.COMPLETE:
                all_parents_complete = False
        
        # Get guidance
        guidance = self.playbook.dependent_guidance.get(
            action.action_id,
            f"Review findings from action(s) {', '.join(parent_actions)} and complete the tasks for this action."
        )
        
        # Build findings
        findings = {
            "complete": all_parents_complete,
            "is_dependent": True,
            "parent_actions": parent_actions,
            "guidance": guidance,
            "key_values": {},
            "issues": [],
            "recommendations": [],
            "summary": f"Please see {primary_parent} response for document analysis.",
            "risk_level": "low"
        }
        
        if not all_parents_complete:
            findings["summary"] = f"Waiting on {primary_parent} to complete."
            findings["issues"] = [f"Complete {primary_parent} before proceeding."]
        
        # Determine status
        if all_parents_complete:
            suggested_status = ActionStatus.IN_PROGRESS
        else:
            suggested_status = ActionStatus.BLOCKED
        
        # Update progress
        progress = ActionProgress(
            action_id=action.action_id,
            status=suggested_status,
            findings=findings,
            documents_found=list(set(parent_docs)),
            inherited_from=parent_actions,
            last_scan=datetime.now().isoformat(),
            is_dependent=True
        )
        PROGRESS_MANAGER.update_action_progress(
            self.playbook.playbook_id, project_id, progress
        )
        
        return ScanResult(
            found=len(parent_docs) > 0,
            documents=[
                {"filename": d, "match_type": "inherited", "snippet": f"From {primary_parent}"}
                for d in set(parent_docs)
            ],
            findings=findings,
            suggested_status=suggested_status,
            inherited_from=parent_actions,
            is_dependent=True
        )
    
    def update_status(
        self,
        project_id: str,
        action_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> Dict:
        """Update action status manually."""
        try:
            action_status = ActionStatus(status)
        except ValueError:
            action_status = ActionStatus.NOT_STARTED
        
        progress = PROGRESS_MANAGER.get_action_progress(
            self.playbook.playbook_id, project_id, action_id
        )
        progress.status = action_status
        if notes is not None:
            progress.notes = notes
        
        PROGRESS_MANAGER.update_action_progress(
            self.playbook.playbook_id, project_id, progress
        )
        
        return {"success": True, "status": status}
    
    def record_feedback(
        self,
        project_id: str,
        action_id: str,
        finding_text: str,
        feedback: str,
        reason: Optional[str] = None
    ) -> bool:
        """Record user feedback on a finding."""
        return LearningHook.record_feedback(
            project_id=project_id,
            playbook_id=self.playbook.playbook_id,
            action_id=action_id,
            finding_text=finding_text,
            feedback=feedback,
            reason=reason
        )


# =============================================================================
# FACTORY FUNCTION - Easy playbook engine creation
# =============================================================================

def get_playbook_engine(playbook_id: str) -> Optional[PlaybookEngine]:
    """
    Get a playbook engine for a registered playbook.
    
    Usage:
        engine = get_playbook_engine("year-end")
        result = await engine.scan_action(project_id, "2A")
    """
    playbook = PLAYBOOK_REGISTRY.get(playbook_id)
    if not playbook:
        logger.warning(f"[ENGINE] Playbook not found: {playbook_id}")
        return None
    return PlaybookEngine(playbook)
