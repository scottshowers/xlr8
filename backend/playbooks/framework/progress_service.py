"""
PLAYBOOK FRAMEWORK - Progress Service
======================================

Handles tracking and persisting playbook instance progress.

Responsibilities:
- Create/load playbook instances
- Update step status
- Track findings
- Handle review decisions (acknowledge, suppress)
- Calculate completion metrics

Author: XLR8 Team
Created: January 18, 2026
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from .definitions import (
    PlaybookDefinition, PlaybookInstance, StepProgress, Finding,
    StepStatus, FindingStatus, FindingSeverity,
    create_playbook_instance, create_step_progress
)

logger = logging.getLogger(__name__)


class ProgressService:
    """
    Service for managing playbook instance progress.
    
    Provides:
    - Instance creation and loading
    - Step status updates
    - Finding management
    - Review workflow (acknowledge/suppress)
    - Progress metrics
    """
    
    def __init__(self, supabase_client=None):
        """
        Initialize progress service.
        
        Args:
            supabase_client: Optional Supabase client for persistence.
                           If None, uses in-memory storage.
        """
        self.supabase = supabase_client
        self._instances: Dict[str, PlaybookInstance] = {}  # In-memory cache
    
    # =========================================================================
    # INSTANCE MANAGEMENT
    # =========================================================================
    
    def create_instance(
        self,
        playbook: PlaybookDefinition,
        project_id: str,
        instance_id: Optional[str] = None
    ) -> PlaybookInstance:
        """Create a new playbook instance."""
        instance = create_playbook_instance(playbook, project_id, instance_id)
        self._instances[instance.id] = instance
        
        # Persist if we have Supabase
        if self.supabase:
            self._persist_instance(instance)
        
        logger.info(f"[PROGRESS] Created instance {instance.id} for playbook {playbook.id}")
        return instance
    
    def get_instance(self, instance_id: str) -> Optional[PlaybookInstance]:
        """Get a playbook instance by ID."""
        # Check cache first
        if instance_id in self._instances:
            return self._instances[instance_id]
        
        # Try loading from Supabase
        if self.supabase:
            instance = self._load_instance(instance_id)
            if instance:
                self._instances[instance_id] = instance
                return instance
        
        return None
    
    def get_instance_for_project(
        self, 
        playbook_id: str, 
        project_id: str
    ) -> Optional[PlaybookInstance]:
        """Get the playbook instance for a specific project."""
        # Check cache
        for instance in self._instances.values():
            if instance.playbook_id == playbook_id and instance.project_id == project_id:
                return instance
        
        # Try loading from Supabase
        if self.supabase:
            instance = self._load_instance_for_project(playbook_id, project_id)
            if instance:
                self._instances[instance.id] = instance
                return instance
        
        return None
    
    def get_or_create_instance(
        self,
        playbook: PlaybookDefinition,
        project_id: str
    ) -> PlaybookInstance:
        """Get existing instance or create new one."""
        existing = self.get_instance_for_project(playbook.id, project_id)
        if existing:
            return existing
        return self.create_instance(playbook, project_id)
    
    # =========================================================================
    # STEP STATUS
    # =========================================================================
    
    def update_step_status(
        self,
        instance_id: str,
        step_id: str,
        status: StepStatus,
        notes: Optional[str] = None,
        ai_context: Optional[str] = None
    ) -> bool:
        """Update the status of a step."""
        instance = self.get_instance(instance_id)
        if not instance:
            logger.warning(f"[PROGRESS] Instance {instance_id} not found")
            return False
        
        if step_id not in instance.progress:
            logger.warning(f"[PROGRESS] Step {step_id} not found in instance")
            return False
        
        progress = instance.progress[step_id]
        old_status = progress.status
        progress.status = status
        
        if notes is not None:
            progress.notes = notes
        if ai_context is not None:
            progress.ai_context = ai_context
        
        # Update timestamps
        if status == StepStatus.IN_PROGRESS and not progress.started_at:
            progress.started_at = datetime.now()
        elif status == StepStatus.COMPLETE:
            progress.completed_at = datetime.now()
        
        # Recalculate instance metrics
        self._recalculate_metrics(instance)
        
        instance.updated_at = datetime.now()
        
        # Persist
        if self.supabase:
            self._persist_instance(instance)
        
        logger.info(f"[PROGRESS] Step {step_id}: {old_status.value} -> {status.value}")
        return True
    
    def update_step_files(
        self,
        instance_id: str,
        step_id: str,
        matched_files: List[str],
        missing_data: List[str]
    ) -> bool:
        """Update the matched/missing files for a step."""
        instance = self.get_instance(instance_id)
        if not instance or step_id not in instance.progress:
            return False
        
        progress = instance.progress[step_id]
        progress.matched_files = matched_files
        progress.missing_data = missing_data
        
        # Auto-update status based on data availability
        if missing_data and progress.status == StepStatus.NOT_STARTED:
            progress.status = StepStatus.BLOCKED
        elif not missing_data and progress.status == StepStatus.BLOCKED:
            progress.status = StepStatus.NOT_STARTED  # Unblock
        
        instance.updated_at = datetime.now()
        self._recalculate_metrics(instance)
        
        if self.supabase:
            self._persist_instance(instance)
        
        return True
    
    # =========================================================================
    # FINDINGS MANAGEMENT
    # =========================================================================
    
    def add_findings(
        self,
        instance_id: str,
        step_id: str,
        findings: List[Finding]
    ) -> bool:
        """Add findings to a step."""
        instance = self.get_instance(instance_id)
        if not instance or step_id not in instance.progress:
            return False
        
        progress = instance.progress[step_id]
        progress.findings.extend(findings)
        
        # Update finding counts
        for finding in findings:
            severity = finding.severity.value
            progress.finding_counts[severity] = progress.finding_counts.get(severity, 0) + 1
        
        instance.updated_at = datetime.now()
        
        if self.supabase:
            self._persist_instance(instance)
        
        logger.info(f"[PROGRESS] Added {len(findings)} findings to step {step_id}")
        return True
    
    def clear_findings(
        self,
        instance_id: str,
        step_id: str
    ) -> bool:
        """Clear all findings for a step (for re-analysis)."""
        instance = self.get_instance(instance_id)
        if not instance or step_id not in instance.progress:
            return False
        
        progress = instance.progress[step_id]
        progress.findings = []
        progress.finding_counts = {}
        
        instance.updated_at = datetime.now()
        
        if self.supabase:
            self._persist_instance(instance)
        
        return True
    
    def update_finding_status(
        self,
        instance_id: str,
        step_id: str,
        finding_id: str,
        status: FindingStatus,
        review_note: Optional[str] = None,
        reviewed_by: Optional[str] = None
    ) -> bool:
        """Update the status of a finding (acknowledge, suppress, etc.)."""
        instance = self.get_instance(instance_id)
        if not instance or step_id not in instance.progress:
            return False
        
        progress = instance.progress[step_id]
        
        for finding in progress.findings:
            if finding.id == finding_id:
                finding.status = status
                finding.review_note = review_note
                finding.reviewed_by = reviewed_by
                finding.reviewed_at = datetime.now()
                
                instance.updated_at = datetime.now()
                
                if self.supabase:
                    self._persist_instance(instance)
                
                logger.info(f"[PROGRESS] Finding {finding_id}: status -> {status.value}")
                return True
        
        return False
    
    def acknowledge_finding(
        self,
        instance_id: str,
        step_id: str,
        finding_id: str,
        note: Optional[str] = None
    ) -> bool:
        """Mark a finding as acknowledged."""
        return self.update_finding_status(
            instance_id, step_id, finding_id,
            FindingStatus.ACKNOWLEDGED, note
        )
    
    def suppress_finding(
        self,
        instance_id: str,
        step_id: str,
        finding_id: str,
        reason: Optional[str] = None
    ) -> bool:
        """Suppress a finding (hide it)."""
        return self.update_finding_status(
            instance_id, step_id, finding_id,
            FindingStatus.SUPPRESSED, reason
        )
    
    # =========================================================================
    # METRICS
    # =========================================================================
    
    def _recalculate_metrics(self, instance: PlaybookInstance) -> None:
        """Recalculate instance-level metrics."""
        completed = 0
        blocked = 0
        
        for progress in instance.progress.values():
            if progress.status == StepStatus.COMPLETE:
                completed += 1
            elif progress.status == StepStatus.BLOCKED:
                blocked += 1
        
        instance.completed_steps = completed
        instance.blocked_steps = blocked
        
        # Check if fully complete
        if completed == instance.total_steps:
            instance.completed_at = datetime.now()
    
    def get_progress_summary(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of progress for an instance."""
        instance = self.get_instance(instance_id)
        if not instance:
            return None
        
        # Count findings by severity across all steps
        total_findings = 0
        findings_by_severity = {}
        active_findings = 0
        
        for progress in instance.progress.values():
            for finding in progress.findings:
                total_findings += 1
                severity = finding.severity.value
                findings_by_severity[severity] = findings_by_severity.get(severity, 0) + 1
                if finding.status == FindingStatus.ACTIVE:
                    active_findings += 1
        
        return {
            'instance_id': instance.id,
            'playbook_id': instance.playbook_id,
            'project_id': instance.project_id,
            'total_steps': instance.total_steps,
            'completed_steps': instance.completed_steps,
            'blocked_steps': instance.blocked_steps,
            'completion_pct': (instance.completed_steps / instance.total_steps * 100) if instance.total_steps > 0 else 0,
            'total_findings': total_findings,
            'active_findings': active_findings,
            'findings_by_severity': findings_by_severity,
            'using_expert_path': instance.using_expert_path,
            'created_at': instance.created_at.isoformat() if instance.created_at else None,
            'updated_at': instance.updated_at.isoformat() if instance.updated_at else None,
        }
    
    def get_step_progress(
        self, 
        instance_id: str, 
        step_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get progress details for a specific step."""
        instance = self.get_instance(instance_id)
        if not instance or step_id not in instance.progress:
            return None
        
        progress = instance.progress[step_id]
        
        # Separate findings by status
        active_findings = [f for f in progress.findings if f.status == FindingStatus.ACTIVE]
        acknowledged_findings = [f for f in progress.findings if f.status == FindingStatus.ACKNOWLEDGED]
        suppressed_findings = [f for f in progress.findings if f.status == FindingStatus.SUPPRESSED]
        
        return {
            'step_id': step_id,
            'status': progress.status.value,
            'matched_files': progress.matched_files,
            'missing_data': progress.missing_data,
            'is_blocked': len(progress.missing_data) > 0,
            'findings_total': len(progress.findings),
            'findings_active': len(active_findings),
            'findings_acknowledged': len(acknowledged_findings),
            'findings_suppressed': len(suppressed_findings),
            'finding_counts': progress.finding_counts,
            'notes': progress.notes,
            'ai_context': progress.ai_context,
            'started_at': progress.started_at.isoformat() if progress.started_at else None,
            'completed_at': progress.completed_at.isoformat() if progress.completed_at else None,
        }
    
    # =========================================================================
    # PERSISTENCE (Supabase)
    # =========================================================================
    
    def _persist_instance(self, instance: PlaybookInstance) -> None:
        """Save instance to Supabase."""
        if not self.supabase:
            return
        
        try:
            data = {
                'id': instance.id,
                'playbook_id': instance.playbook_id,
                'project_id': instance.project_id,
                'progress': self._serialize_progress(instance.progress),
                'total_steps': instance.total_steps,
                'completed_steps': instance.completed_steps,
                'blocked_steps': instance.blocked_steps,
                'using_expert_path': instance.using_expert_path,
                'vendor_path_mapping': json.dumps(instance.vendor_path_mapping) if instance.vendor_path_mapping else None,
                'updated_at': datetime.now().isoformat()
            }
            
            self.supabase.table('playbook_instances').upsert(data).execute()
            
        except Exception as e:
            logger.error(f"[PROGRESS] Failed to persist instance: {e}")
    
    def _load_instance(self, instance_id: str) -> Optional[PlaybookInstance]:
        """Load instance from Supabase."""
        if not self.supabase:
            return None
        
        try:
            result = self.supabase.table('playbook_instances').select('*').eq('id', instance_id).single().execute()
            if result.data:
                return self._deserialize_instance(result.data)
        except Exception as e:
            logger.error(f"[PROGRESS] Failed to load instance: {e}")
        
        return None
    
    def _load_instance_for_project(
        self, 
        playbook_id: str, 
        project_id: str
    ) -> Optional[PlaybookInstance]:
        """Load instance for a specific project."""
        if not self.supabase:
            return None
        
        try:
            result = self.supabase.table('playbook_instances').select('*')\
                .eq('playbook_id', playbook_id)\
                .eq('project_id', project_id)\
                .order('updated_at', desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                return self._deserialize_instance(result.data[0])
        except Exception as e:
            logger.error(f"[PROGRESS] Failed to load instance for project: {e}")
        
        return None
    
    def _serialize_progress(self, progress: Dict[str, StepProgress]) -> str:
        """Serialize progress dict to JSON."""
        data = {}
        for step_id, sp in progress.items():
            data[step_id] = {
                'status': sp.status.value,
                'matched_files': sp.matched_files,
                'missing_data': sp.missing_data,
                'finding_counts': sp.finding_counts,
                'notes': sp.notes,
                'ai_context': sp.ai_context,
                'started_at': sp.started_at.isoformat() if sp.started_at else None,
                'completed_at': sp.completed_at.isoformat() if sp.completed_at else None,
                # Findings serialized separately for size
                'findings_count': len(sp.findings)
            }
        return json.dumps(data)
    
    def _deserialize_instance(self, data: Dict) -> PlaybookInstance:
        """Deserialize instance from database row."""
        instance = PlaybookInstance(
            id=data['id'],
            playbook_id=data['playbook_id'],
            project_id=data['project_id'],
            total_steps=data.get('total_steps', 0),
            completed_steps=data.get('completed_steps', 0),
            blocked_steps=data.get('blocked_steps', 0),
            using_expert_path=data.get('using_expert_path', False),
        )
        
        # Deserialize progress
        if data.get('progress'):
            progress_data = json.loads(data['progress']) if isinstance(data['progress'], str) else data['progress']
            for step_id, sp_data in progress_data.items():
                instance.progress[step_id] = StepProgress(
                    step_id=step_id,
                    status=StepStatus(sp_data.get('status', 'not_started')),
                    matched_files=sp_data.get('matched_files', []),
                    missing_data=sp_data.get('missing_data', []),
                    finding_counts=sp_data.get('finding_counts', {}),
                    notes=sp_data.get('notes'),
                    ai_context=sp_data.get('ai_context'),
                )
        
        return instance


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_progress_service = None

def get_progress_service(supabase_client=None) -> ProgressService:
    """Get the singleton progress service instance."""
    global _progress_service
    if _progress_service is None:
        _progress_service = ProgressService(supabase_client)
    return _progress_service
