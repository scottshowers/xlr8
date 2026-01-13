# Phase 8: Playbook Engine

**Status:** FUTURE  
**Total Estimated Hours:** 30-40  
**Dependencies:** Phase 7 (Feature Engine) complete  
**Last Updated:** January 13, 2026

---

## Objective

Build the workflow assembly and execution engine that lets consultants:
1. Use pre-built HCMPACT playbooks (methodology baked in)
2. Customize existing playbooks
3. Create new playbooks from scratch

Ship with HCMPACT methodology as the default - quality gates, step guidance, and deliverable standards that encode "the right way" to do implementation consulting.

---

## The Core Problem Being Solved

> "I have failed in teaching that over the years, so I am trying to build it in."

Consultants often:
- Skip steps
- Don't check their work  
- Don't know what good looks like
- Waste time on wrong things
- Ship garbage
- Don't ask the right questions

**Solution:** Build a system where bad work is harder than good work.

---

## Background

### What is a Playbook?

A Playbook is an assembled workflow of Features with:
- **Steps** - Ordered sequence of work
- **Guidance** - What to do and why at each step
- **Suggested Features** - Recommended tools for the step
- **Quality Gates** - Must pass before proceeding
- **Deliverables** - What gets produced

### Hierarchy

```
PLAYBOOK
├── Step 1
│   ├── Guidance (what to do, why it matters)
│   ├── Suggested Features (with pre-configured settings)
│   ├── Quality Gates (auto-checks + manual confirmation)
│   └── Deliverable Definition
├── Step 2
│   └── ...
└── Final Deliverables
```

---

## Component Overview

| # | Component | Hours | Description |
|---|-----------|-------|-------------|
| 8.1 | Playbook Schema | 3-4 | Define playbook structure |
| 8.2 | Playbook Runtime | 5-6 | Execute playbooks, track progress |
| 8.3 | Quality Gate System | 5-6 | Auto-checks, manual confirmations, blocks |
| 8.4 | Playbook Builder UI | 6-8 | Create/edit playbooks |
| 8.5 | HCMPACT Methodology Library | 6-8 | Your playbooks, your way |
| 8.6 | Guidance System | 4-5 | Step-by-step coaching |

---

## Component 8.1: Playbook Schema

**Goal:** Define the structure of a playbook.

### Schema Definition

```python
# backend/playbooks/schema.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

class PlaybookDifficulty(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class GateSeverity(Enum):
    BLOCKER = "blocker"      # Cannot proceed
    WARNING = "warning"      # Can proceed with acknowledgment
    INFO = "info"            # Just informational

class DeliverableStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    EXPORTED = "exported"

@dataclass
class AutoCheck:
    """Automated quality check."""
    id: str
    description: str
    check_type: str  # "exists", "count", "contains", "custom"
    check_config: Dict[str, Any]
    severity: GateSeverity = GateSeverity.BLOCKER
    
    # Examples:
    # check_type: "exists", check_config: {"output": "uploaded_files"}
    # check_type: "count", check_config: {"output": "data.rows", "min": 1}
    # check_type: "contains", check_config: {"output": "doc.text", "keywords": ["year-end"]}

@dataclass
class ManualConfirmation:
    """Manual confirmation checkbox."""
    id: str
    label: str
    description: Optional[str] = None
    severity: GateSeverity = GateSeverity.BLOCKER

@dataclass
class QualityGate:
    """Quality gate for a step."""
    auto_checks: List[AutoCheck] = field(default_factory=list)
    manual_confirmations: List[ManualConfirmation] = field(default_factory=list)
    requires_review: bool = False  # Requires manager/peer review
    reviewer_role: Optional[str] = None  # "manager", "peer", "client"

@dataclass
class DeliverableRequirement:
    """A requirement for a deliverable."""
    description: str
    check_type: str = "manual"  # "manual", "auto"
    check_config: Optional[Dict[str, Any]] = None

@dataclass
class Deliverable:
    """Definition of a step deliverable."""
    name: str
    description: str
    requirements: List[DeliverableRequirement] = field(default_factory=list)
    template_id: Optional[str] = None  # Export template to use

@dataclass
class SuggestedFeature:
    """A feature suggestion for a step."""
    feature_id: str
    reason: str
    pre_configured: Dict[str, Any] = field(default_factory=dict)  # Pre-filled config
    required: bool = False  # Must use this feature

@dataclass
class PlaybookStep:
    """A single step in a playbook."""
    id: str
    name: str
    order: int
    
    # Guidance
    guidance: str  # What to do and why
    tips: List[str] = field(default_factory=list)  # Pro tips
    common_mistakes: List[str] = field(default_factory=list)  # What to avoid
    
    # Features
    suggested_features: List[SuggestedFeature] = field(default_factory=list)
    allow_other_features: bool = True  # Can use non-suggested features
    
    # Quality
    quality_gate: Optional[QualityGate] = None
    
    # Deliverable
    deliverable: Optional[Deliverable] = None
    
    # Branching (optional)
    next_step_default: Optional[str] = None  # Next step ID
    conditional_next: List[Dict[str, Any]] = field(default_factory=list)  # Conditional routing

@dataclass
class FinalDeliverable:
    """A final deliverable of the playbook."""
    name: str
    description: str
    format: str  # pdf, xlsx, docx
    template_id: Optional[str] = None
    assembled_from: List[str] = field(default_factory=list)  # Step IDs to pull from

@dataclass
class PlaybookDefinition:
    """Complete playbook definition."""
    id: str
    name: str
    description: str
    
    # Metadata
    author: str = "HCMPACT"
    version: int = 1
    difficulty: PlaybookDifficulty = PlaybookDifficulty.INTERMEDIATE
    typical_duration: str = ""  # "3-5 days", "1 week"
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Purpose & context
    purpose: str = ""  # Why this playbook exists
    when_to_use: str = ""  # When to choose this playbook
    prerequisites: List[str] = field(default_factory=list)  # What's needed first
    
    # Steps
    steps: List[PlaybookStep] = field(default_factory=list)
    
    # Final deliverables
    final_deliverables: List[FinalDeliverable] = field(default_factory=list)
    
    # Success criteria
    success_criteria: str = ""  # What "done" looks like
    
    # Categorization
    category: str = ""  # "Year-End", "Implementation", "Audit"
    tags: List[str] = field(default_factory=list)
    
    # Status
    active: bool = True
    is_template: bool = True  # Template that gets instantiated

@dataclass
class PlaybookInstance:
    """A running instance of a playbook for a project."""
    id: str
    playbook_id: str
    project_id: str
    
    # Progress
    current_step_id: str
    step_statuses: Dict[str, str] = field(default_factory=dict)  # step_id -> status
    gate_results: Dict[str, Dict] = field(default_factory=dict)  # step_id -> gate results
    
    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    # People
    started_by: str = ""
    assigned_to: Optional[str] = None
    
    # Deliverables
    deliverable_statuses: Dict[str, DeliverableStatus] = field(default_factory=dict)
    
    # Overall status
    status: str = "in_progress"  # in_progress, blocked, completed, abandoned
```

---

## Component 8.2: Playbook Runtime

**Goal:** Execute playbooks and track progress.

### Runtime Engine

```python
# backend/playbooks/runtime.py
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
from .schema import (
    PlaybookDefinition, PlaybookInstance, PlaybookStep,
    GateSeverity, DeliverableStatus
)
from ..features.engine import FeatureEngine

logger = logging.getLogger(__name__)

class PlaybookRuntime:
    """Execute and track playbook progress."""
    
    def __init__(self):
        self.feature_engine = FeatureEngine()
    
    async def start_playbook(
        self,
        playbook: PlaybookDefinition,
        project_id: str,
        user_id: str,
    ) -> PlaybookInstance:
        """Start a new playbook instance."""
        instance = PlaybookInstance(
            id=self._generate_instance_id(),
            playbook_id=playbook.id,
            project_id=project_id,
            current_step_id=playbook.steps[0].id,
            step_statuses={step.id: "not_started" for step in playbook.steps},
            started_by=user_id,
        )
        
        # Mark first step as active
        instance.step_statuses[playbook.steps[0].id] = "active"
        
        # Save instance
        await self._save_instance(instance)
        
        return instance
    
    async def get_current_step(
        self,
        instance: PlaybookInstance,
        playbook: PlaybookDefinition,
    ) -> Dict[str, Any]:
        """Get current step with all context."""
        step = self._get_step(playbook, instance.current_step_id)
        
        # Get feature suggestions with availability
        suggested_features = []
        for sf in step.suggested_features:
            feature = self.feature_engine.registry.get(sf.feature_id)
            suggested_features.append({
                "feature": feature,
                "reason": sf.reason,
                "pre_configured": sf.pre_configured,
                "required": sf.required,
            })
        
        # Get gate status
        gate_status = instance.gate_results.get(step.id, {})
        
        return {
            "step": step,
            "suggested_features": suggested_features,
            "gate_status": gate_status,
            "can_proceed": self._can_proceed(step, gate_status),
            "progress": self._calculate_progress(instance, playbook),
        }
    
    async def execute_feature(
        self,
        instance: PlaybookInstance,
        playbook: PlaybookDefinition,
        feature_id: str,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a feature within playbook context."""
        step = self._get_step(playbook, instance.current_step_id)
        
        # Check if feature is allowed
        if not step.allow_other_features:
            allowed_ids = [sf.feature_id for sf in step.suggested_features]
            if feature_id not in allowed_ids:
                raise ValueError(f"Feature {feature_id} not allowed in this step")
        
        # Execute feature
        execution = await self.feature_engine.execute(
            feature_id=feature_id,
            project_id=instance.project_id,
            inputs=inputs,
            context={
                "playbook_id": playbook.id,
                "step_id": step.id,
                "instance_id": instance.id,
            },
        )
        
        # Update gate results if feature completed successfully
        if execution.status == "completed":
            await self._update_gate_results(instance, step, execution)
        
        return {
            "execution": execution,
            "gate_status": instance.gate_results.get(step.id, {}),
            "can_proceed": self._can_proceed(step, instance.gate_results.get(step.id, {})),
        }
    
    async def confirm_manual_check(
        self,
        instance: PlaybookInstance,
        playbook: PlaybookDefinition,
        check_id: str,
        confirmed: bool,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Confirm a manual quality check."""
        step = self._get_step(playbook, instance.current_step_id)
        
        if step.id not in instance.gate_results:
            instance.gate_results[step.id] = {"auto": {}, "manual": {}}
        
        instance.gate_results[step.id]["manual"][check_id] = {
            "confirmed": confirmed,
            "notes": notes,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        await self._save_instance(instance)
        
        return {
            "gate_status": instance.gate_results[step.id],
            "can_proceed": self._can_proceed(step, instance.gate_results[step.id]),
        }
    
    async def proceed_to_next_step(
        self,
        instance: PlaybookInstance,
        playbook: PlaybookDefinition,
    ) -> Dict[str, Any]:
        """Move to the next step if gates pass."""
        current_step = self._get_step(playbook, instance.current_step_id)
        gate_status = instance.gate_results.get(current_step.id, {})
        
        # Check if we can proceed
        can_proceed, blockers = self._can_proceed_detailed(current_step, gate_status)
        
        if not can_proceed:
            return {
                "success": False,
                "blockers": blockers,
                "message": "Cannot proceed - quality gates not satisfied",
            }
        
        # Determine next step
        next_step_id = self._determine_next_step(current_step, instance, playbook)
        
        if next_step_id is None:
            # Playbook complete
            instance.status = "completed"
            instance.completed_at = datetime.utcnow()
            await self._save_instance(instance)
            
            return {
                "success": True,
                "completed": True,
                "message": "Playbook completed!",
            }
        
        # Move to next step
        instance.step_statuses[current_step.id] = "completed"
        instance.step_statuses[next_step_id] = "active"
        instance.current_step_id = next_step_id
        
        await self._save_instance(instance)
        
        return {
            "success": True,
            "completed": False,
            "next_step_id": next_step_id,
            "message": f"Moved to step: {self._get_step(playbook, next_step_id).name}",
        }
    
    def _can_proceed(self, step: PlaybookStep, gate_status: Dict) -> bool:
        """Check if step gates are satisfied."""
        can_proceed, _ = self._can_proceed_detailed(step, gate_status)
        return can_proceed
    
    def _can_proceed_detailed(self, step: PlaybookStep, gate_status: Dict) -> tuple:
        """Check gates with detailed blockers."""
        if not step.quality_gate:
            return True, []
        
        blockers = []
        
        # Check auto gates
        for check in step.quality_gate.auto_checks:
            if check.severity == GateSeverity.BLOCKER:
                result = gate_status.get("auto", {}).get(check.id)
                if not result or not result.get("passed"):
                    blockers.append({
                        "type": "auto",
                        "id": check.id,
                        "description": check.description,
                    })
        
        # Check manual confirmations
        for conf in step.quality_gate.manual_confirmations:
            if conf.severity == GateSeverity.BLOCKER:
                result = gate_status.get("manual", {}).get(conf.id)
                if not result or not result.get("confirmed"):
                    blockers.append({
                        "type": "manual",
                        "id": conf.id,
                        "label": conf.label,
                    })
        
        # Check review requirement
        if step.quality_gate.requires_review:
            review = gate_status.get("review")
            if not review or not review.get("approved"):
                blockers.append({
                    "type": "review",
                    "description": f"Requires {step.quality_gate.reviewer_role or 'peer'} review",
                })
        
        return len(blockers) == 0, blockers
    
    async def _update_gate_results(
        self,
        instance: PlaybookInstance,
        step: PlaybookStep,
        execution,
    ):
        """Update gate results based on feature execution."""
        if step.id not in instance.gate_results:
            instance.gate_results[step.id] = {"auto": {}, "manual": {}}
        
        if not step.quality_gate:
            return
        
        # Run auto checks against execution outputs
        for check in step.quality_gate.auto_checks:
            passed = self._evaluate_auto_check(check, execution)
            instance.gate_results[step.id]["auto"][check.id] = {
                "passed": passed,
                "timestamp": datetime.utcnow().isoformat(),
            }
        
        await self._save_instance(instance)
    
    def _evaluate_auto_check(self, check, execution) -> bool:
        """Evaluate an auto check against execution results."""
        config = check.check_config
        outputs = execution.outputs
        
        if check.check_type == "exists":
            key = config.get("output")
            return key in outputs and outputs[key] is not None
        
        elif check.check_type == "count":
            key = config.get("output")
            min_count = config.get("min", 1)
            value = outputs.get(key, [])
            if isinstance(value, list):
                return len(value) >= min_count
            return False
        
        elif check.check_type == "contains":
            key = config.get("output")
            keywords = config.get("keywords", [])
            value = str(outputs.get(key, "")).lower()
            return any(kw.lower() in value for kw in keywords)
        
        return False
    
    def _get_step(self, playbook: PlaybookDefinition, step_id: str) -> PlaybookStep:
        """Get step by ID."""
        for step in playbook.steps:
            if step.id == step_id:
                return step
        raise ValueError(f"Step not found: {step_id}")
    
    def _determine_next_step(
        self,
        current_step: PlaybookStep,
        instance: PlaybookInstance,
        playbook: PlaybookDefinition,
    ) -> Optional[str]:
        """Determine the next step (supports conditional branching)."""
        # Check conditional routing first
        for condition in current_step.conditional_next:
            if self._evaluate_condition(condition, instance):
                return condition.get("next_step_id")
        
        # Default next step
        if current_step.next_step_default:
            return current_step.next_step_default
        
        # Find next by order
        current_order = current_step.order
        for step in sorted(playbook.steps, key=lambda s: s.order):
            if step.order > current_order:
                return step.id
        
        # No more steps
        return None
    
    def _calculate_progress(
        self,
        instance: PlaybookInstance,
        playbook: PlaybookDefinition,
    ) -> Dict[str, Any]:
        """Calculate playbook progress."""
        total_steps = len(playbook.steps)
        completed_steps = sum(
            1 for status in instance.step_statuses.values()
            if status == "completed"
        )
        
        return {
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "percentage": int((completed_steps / total_steps) * 100) if total_steps > 0 else 0,
            "current_step": instance.current_step_id,
        }
```

---

## Component 8.3: Quality Gate System

**Goal:** Enforce quality through auto-checks, manual confirmations, and review gates.

### Gate Evaluation Engine

```python
# backend/playbooks/gates.py
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
from .schema import QualityGate, AutoCheck, ManualConfirmation, GateSeverity

@dataclass
class GateEvaluation:
    """Result of evaluating a quality gate."""
    passed: bool
    blockers: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    info: List[Dict[str, Any]]

class GateEvaluator:
    """Evaluate quality gates."""
    
    def evaluate(
        self,
        gate: QualityGate,
        gate_status: Dict[str, Any],
    ) -> GateEvaluation:
        """Evaluate a quality gate."""
        blockers = []
        warnings = []
        info = []
        
        # Evaluate auto checks
        for check in gate.auto_checks:
            result = gate_status.get("auto", {}).get(check.id, {})
            passed = result.get("passed", False)
            
            if not passed:
                item = {
                    "type": "auto",
                    "id": check.id,
                    "description": check.description,
                }
                
                if check.severity == GateSeverity.BLOCKER:
                    blockers.append(item)
                elif check.severity == GateSeverity.WARNING:
                    warnings.append(item)
                else:
                    info.append(item)
        
        # Evaluate manual confirmations
        for conf in gate.manual_confirmations:
            result = gate_status.get("manual", {}).get(conf.id, {})
            confirmed = result.get("confirmed", False)
            
            if not confirmed:
                item = {
                    "type": "manual",
                    "id": conf.id,
                    "label": conf.label,
                    "description": conf.description,
                }
                
                if conf.severity == GateSeverity.BLOCKER:
                    blockers.append(item)
                elif conf.severity == GateSeverity.WARNING:
                    warnings.append(item)
                else:
                    info.append(item)
        
        # Evaluate review requirement
        if gate.requires_review:
            review = gate_status.get("review", {})
            if not review.get("approved"):
                blockers.append({
                    "type": "review",
                    "role": gate.reviewer_role or "peer",
                    "description": f"Requires {gate.reviewer_role or 'peer'} review and approval",
                })
        
        return GateEvaluation(
            passed=len(blockers) == 0,
            blockers=blockers,
            warnings=warnings,
            info=info,
        )


class StandardGates:
    """Library of standard quality gate checks."""
    
    @staticmethod
    def data_uploaded() -> AutoCheck:
        return AutoCheck(
            id="data_uploaded",
            description="At least one file uploaded",
            check_type="count",
            check_config={"output": "uploaded_files", "min": 1},
            severity=GateSeverity.BLOCKER,
        )
    
    @staticmethod
    def rows_exist() -> AutoCheck:
        return AutoCheck(
            id="rows_exist",
            description="Data contains at least one row",
            check_type="count",
            check_config={"output": "data.rows", "min": 1},
            severity=GateSeverity.BLOCKER,
        )
    
    @staticmethod
    def no_critical_gaps() -> AutoCheck:
        return AutoCheck(
            id="no_critical_gaps",
            description="No critical gaps identified",
            check_type="count",
            check_config={"output": "critical_gaps", "max": 0},
            severity=GateSeverity.WARNING,
        )
    
    @staticmethod
    def doc_contains_keyword(keyword: str) -> AutoCheck:
        return AutoCheck(
            id=f"doc_contains_{keyword.lower().replace(' ', '_')}",
            description=f"Document contains '{keyword}'",
            check_type="contains",
            check_config={"output": "doc.text", "keywords": [keyword]},
            severity=GateSeverity.WARNING,
        )
    
    @staticmethod
    def ready_to_ship() -> ManualConfirmation:
        return ManualConfirmation(
            id="ready_to_ship",
            label="I would put my name on this deliverable",
            description="Confirm this meets your professional standards",
            severity=GateSeverity.BLOCKER,
        )
    
    @staticmethod
    def data_complete() -> ManualConfirmation:
        return ManualConfirmation(
            id="data_complete",
            label="I have all required data",
            description="Confirm no critical data is missing",
            severity=GateSeverity.BLOCKER,
        )
    
    @staticmethod
    def reviewed_output() -> ManualConfirmation:
        return ManualConfirmation(
            id="reviewed_output",
            label="I have reviewed the output for accuracy",
            severity=GateSeverity.BLOCKER,
        )
```

### Gate UI Component

```jsx
// components/QualityGate.jsx
import { CheckCircle, XCircle, AlertTriangle, Info, Lock } from 'lucide-react';

const QualityGate = ({ gate, gateStatus, onConfirm, canProceed }) => {
  const evaluation = evaluateGate(gate, gateStatus);
  
  return (
    <div className={`quality-gate ${canProceed ? 'passed' : 'blocked'}`}>
      <div className="gate-header">
        {canProceed ? (
          <CheckCircle className="icon success" />
        ) : (
          <Lock className="icon blocked" />
        )}
        <h3>Quality Gate</h3>
        <span className="status">
          {canProceed ? 'Ready to proceed' : 'Complete all requirements'}
        </span>
      </div>
      
      {/* Blockers */}
      {evaluation.blockers.length > 0 && (
        <div className="gate-section blockers">
          <h4><XCircle size={16} /> Required</h4>
          {evaluation.blockers.map(item => (
            <GateItem
              key={item.id}
              item={item}
              status={getItemStatus(item, gateStatus)}
              onConfirm={item.type === 'manual' ? () => onConfirm(item.id) : null}
            />
          ))}
        </div>
      )}
      
      {/* Warnings */}
      {evaluation.warnings.length > 0 && (
        <div className="gate-section warnings">
          <h4><AlertTriangle size={16} /> Recommended</h4>
          {evaluation.warnings.map(item => (
            <GateItem
              key={item.id}
              item={item}
              status={getItemStatus(item, gateStatus)}
              onConfirm={item.type === 'manual' ? () => onConfirm(item.id) : null}
            />
          ))}
        </div>
      )}
      
      {/* All passed */}
      {evaluation.blockers.length === 0 && evaluation.warnings.length === 0 && (
        <div className="gate-success">
          <CheckCircle size={24} />
          <p>All quality checks passed!</p>
        </div>
      )}
    </div>
  );
};

const GateItem = ({ item, status, onConfirm }) => {
  const isPassed = status === 'passed' || status === 'confirmed';
  
  return (
    <div className={`gate-item ${isPassed ? 'passed' : 'pending'}`}>
      {item.type === 'auto' ? (
        // Auto check - just show status
        <>
          {isPassed ? <CheckCircle size={16} /> : <XCircle size={16} />}
          <span>{item.description}</span>
        </>
      ) : item.type === 'manual' ? (
        // Manual confirmation - checkbox
        <label className="manual-confirm">
          <input
            type="checkbox"
            checked={isPassed}
            onChange={() => onConfirm(!isPassed)}
          />
          <span>{item.label}</span>
          {item.description && <small>{item.description}</small>}
        </label>
      ) : (
        // Review requirement
        <>
          {isPassed ? <CheckCircle size={16} /> : <Lock size={16} />}
          <span>{item.description}</span>
          {!isPassed && <button className="request-review">Request Review</button>}
        </>
      )}
    </div>
  );
};
```

---

## Component 8.4: Playbook Builder UI

**Goal:** Create and edit playbooks visually.

### Playbook Builder Page

```jsx
// pages/PlaybookBuilder.jsx
import { useState, useEffect } from 'react';
import { Plus, GripVertical, Trash2, Settings, Copy } from 'lucide-react';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';

const PlaybookBuilder = ({ playbookId }) => {
  const [playbook, setPlaybook] = useState(null);
  const [selectedStep, setSelectedStep] = useState(null);
  const [dirty, setDirty] = useState(false);
  
  useEffect(() => {
    if (playbookId) {
      loadPlaybook(playbookId);
    } else {
      // New playbook
      setPlaybook(createEmptyPlaybook());
    }
  }, [playbookId]);
  
  const handleDragEnd = (result) => {
    if (!result.destination) return;
    
    const steps = Array.from(playbook.steps);
    const [removed] = steps.splice(result.source.index, 1);
    steps.splice(result.destination.index, 0, removed);
    
    // Update order numbers
    steps.forEach((step, i) => step.order = i + 1);
    
    setPlaybook({ ...playbook, steps });
    setDirty(true);
  };
  
  return (
    <div className="playbook-builder">
      <header>
        <div className="playbook-title">
          <input
            type="text"
            value={playbook?.name || ''}
            onChange={e => {
              setPlaybook({ ...playbook, name: e.target.value });
              setDirty(true);
            }}
            placeholder="Playbook Name"
            className="title-input"
          />
        </div>
        <div className="actions">
          {dirty && <span className="unsaved">Unsaved changes</span>}
          <button onClick={handleSave} disabled={!dirty}>Save</button>
          <button onClick={handlePreview}>Preview</button>
        </div>
      </header>
      
      <div className="builder-layout">
        {/* Left panel - Step list */}
        <div className="steps-panel">
          <div className="panel-header">
            <h3>Steps</h3>
            <button onClick={addStep}><Plus size={16} /> Add Step</button>
          </div>
          
          <DragDropContext onDragEnd={handleDragEnd}>
            <Droppable droppableId="steps">
              {(provided) => (
                <div
                  className="steps-list"
                  ref={provided.innerRef}
                  {...provided.droppableProps}
                >
                  {playbook?.steps.map((step, index) => (
                    <Draggable key={step.id} draggableId={step.id} index={index}>
                      {(provided, snapshot) => (
                        <div
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          className={`step-item ${selectedStep?.id === step.id ? 'selected' : ''} ${snapshot.isDragging ? 'dragging' : ''}`}
                          onClick={() => setSelectedStep(step)}
                        >
                          <span {...provided.dragHandleProps}>
                            <GripVertical size={16} />
                          </span>
                          <span className="step-number">{index + 1}</span>
                          <span className="step-name">{step.name || 'Untitled Step'}</span>
                          <button
                            className="delete-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteStep(step.id);
                            }}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      )}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                </div>
              )}
            </Droppable>
          </DragDropContext>
        </div>
        
        {/* Right panel - Step editor */}
        <div className="step-editor">
          {selectedStep ? (
            <StepEditor
              step={selectedStep}
              onChange={(updated) => {
                setPlaybook({
                  ...playbook,
                  steps: playbook.steps.map(s =>
                    s.id === updated.id ? updated : s
                  ),
                });
                setSelectedStep(updated);
                setDirty(true);
              }}
            />
          ) : (
            <div className="no-selection">
              <p>Select a step to edit or add a new step</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const StepEditor = ({ step, onChange }) => {
  const [activeTab, setActiveTab] = useState('guidance');
  
  return (
    <div className="step-editor-content">
      <input
        type="text"
        value={step.name}
        onChange={e => onChange({ ...step, name: e.target.value })}
        placeholder="Step Name"
        className="step-name-input"
      />
      
      <div className="editor-tabs">
        <button
          className={activeTab === 'guidance' ? 'active' : ''}
          onClick={() => setActiveTab('guidance')}
        >
          Guidance
        </button>
        <button
          className={activeTab === 'features' ? 'active' : ''}
          onClick={() => setActiveTab('features')}
        >
          Features
        </button>
        <button
          className={activeTab === 'quality' ? 'active' : ''}
          onClick={() => setActiveTab('quality')}
        >
          Quality Gate
        </button>
        <button
          className={activeTab === 'deliverable' ? 'active' : ''}
          onClick={() => setActiveTab('deliverable')}
        >
          Deliverable
        </button>
      </div>
      
      <div className="tab-content">
        {activeTab === 'guidance' && (
          <GuidanceEditor step={step} onChange={onChange} />
        )}
        {activeTab === 'features' && (
          <FeaturesEditor step={step} onChange={onChange} />
        )}
        {activeTab === 'quality' && (
          <QualityGateEditor step={step} onChange={onChange} />
        )}
        {activeTab === 'deliverable' && (
          <DeliverableEditor step={step} onChange={onChange} />
        )}
      </div>
    </div>
  );
};
```

---

## Component 8.5: HCMPACT Methodology Library

**Goal:** Ship with Scott's playbooks as the defaults.

### Year-End Readiness Playbook

```python
# backend/playbooks/library/year_end_readiness.py
from ..schema import (
    PlaybookDefinition, PlaybookStep, PlaybookDifficulty,
    SuggestedFeature, QualityGate, AutoCheck, ManualConfirmation,
    Deliverable, DeliverableRequirement, FinalDeliverable, GateSeverity
)

YEAR_END_READINESS = PlaybookDefinition(
    id="year_end_readiness",
    name="Year-End Readiness Assessment",
    description="Assess customer's readiness for year-end processing. Identify gaps before they become December emergencies.",
    
    author="HCMPACT",
    version=1,
    difficulty=PlaybookDifficulty.INTERMEDIATE,
    typical_duration="3-5 days",
    
    purpose="""
    Year-end is when shortcuts come home to roost. This playbook ensures you:
    - Know what the vendor requires this year (it changes)
    - Know what the customer has configured
    - Find the gaps before December
    - Give them a prioritized fix list
    """,
    
    when_to_use="Q4 for any customer with complex payroll, tax, or benefits processing",
    
    prerequisites=[
        "Access to customer instance",
        "Customer contact who can answer config questions",
        "Vendor year-end documentation (or ability to get it)",
    ],
    
    category="Year-End",
    tags=["year-end", "readiness", "gap-analysis", "payroll", "tax"],
    
    steps=[
        PlaybookStep(
            id="gather_vendor_docs",
            name="Gather Vendor Documentation",
            order=1,
            
            guidance="""
            You need the vendor's current year-end checklist and any updates published 
            in the last 90 days. Don't skip this - vendors change requirements every year.
            
            Look for:
            - Year-end processing guide
            - Tax updates bulletin
            - W-2/1099 requirements
            - Benefits year-end requirements
            - Any "what's new" or "what's changed" documents
            """,
            
            tips=[
                "Check the vendor's support portal, not just Google",
                "Look for documents dated within the last 90 days",
                "If there's a 'year-end' or 'YE' tag/category, start there",
            ],
            
            common_mistakes=[
                "Using last year's documentation - requirements change",
                "Missing supplemental bulletins that modify the main guide",
                "Skipping this step because 'we know what to do'",
            ],
            
            suggested_features=[
                SuggestedFeature(
                    feature_id="upload",
                    reason="Upload vendor documentation you've downloaded",
                    pre_configured={"doc_type": "vendor_reference"},
                ),
                SuggestedFeature(
                    feature_id="api_pull",
                    reason="Pull latest docs from vendor API (if connected)",
                    pre_configured={"source": "vendor_docs", "filter": "year_end"},
                ),
            ],
            
            quality_gate=QualityGate(
                auto_checks=[
                    AutoCheck(
                        id="docs_uploaded",
                        description="At least 1 document uploaded",
                        check_type="count",
                        check_config={"output": "uploaded_files", "min": 1},
                        severity=GateSeverity.BLOCKER,
                    ),
                    AutoCheck(
                        id="ye_keyword",
                        description="Document contains year-end related content",
                        check_type="contains",
                        check_config={"output": "doc.text", "keywords": ["year-end", "year end", "YE", "W-2", "1099"]},
                        severity=GateSeverity.WARNING,
                    ),
                ],
                manual_confirmations=[
                    ManualConfirmation(
                        id="all_vendor_docs",
                        label="I have all vendor year-end documentation",
                        description="Including any supplements or bulletins from the last 90 days",
                        severity=GateSeverity.BLOCKER,
                    ),
                ],
            ),
            
            deliverable=Deliverable(
                name="Vendor Year-End Package",
                description="Complete set of vendor year-end documentation",
                requirements=[
                    DeliverableRequirement(description="Year-end checklist document present"),
                    DeliverableRequirement(description="Dated within current year"),
                    DeliverableRequirement(description="All referenced supplemental docs included"),
                ],
            ),
        ),
        
        PlaybookStep(
            id="collect_customer_config",
            name="Collect Customer Configuration",
            order=2,
            
            guidance="""
            Pull their current config - pay rules, deduction setup, tax jurisdictions. 
            Compare against what they had last year if available.
            
            Look for things they ADDED but didn't tell you about. Customers make changes
            mid-year and forget. Those changes might break year-end.
            """,
            
            tips=[
                "Pull config dated within the last 30 days - stale config = wrong analysis",
                "If they have a test vs prod instance, make sure you're looking at PROD",
                "Export tax jurisdictions separately - they're often the source of problems",
            ],
            
            common_mistakes=[
                "Using a config export from 6 months ago",
                "Missing jurisdiction-specific configurations",
                "Not checking for mid-year additions",
            ],
            
            suggested_features=[
                SuggestedFeature(
                    feature_id="api_pull",
                    reason="Pull current configuration from customer instance",
                    pre_configured={"source": "customer_instance"},
                    required=True,
                ),
                SuggestedFeature(
                    feature_id="upload",
                    reason="Upload manual config exports if API not available",
                    pre_configured={"doc_type": "customer_config"},
                ),
                SuggestedFeature(
                    feature_id="compare",
                    reason="Compare current config to prior year if available",
                    pre_configured={"compare_type": "year_over_year"},
                ),
            ],
            
            quality_gate=QualityGate(
                auto_checks=[
                    AutoCheck(
                        id="config_loaded",
                        description="Configuration tables loaded",
                        check_type="exists",
                        check_config={"output": "data.tables"},
                        severity=GateSeverity.BLOCKER,
                    ),
                    AutoCheck(
                        id="pay_rules_exist",
                        description="Pay rule configuration present",
                        check_type="count",
                        check_config={"output": "data.pay_rules", "min": 1},
                        severity=GateSeverity.BLOCKER,
                    ),
                ],
                manual_confirmations=[
                    ManualConfirmation(
                        id="config_current",
                        label="Configuration is current (within last 30 days)",
                        severity=GateSeverity.BLOCKER,
                    ),
                    ManualConfirmation(
                        id="config_complete",
                        label="I have all relevant configuration areas",
                        description="Pay rules, deductions, tax setup, benefits",
                        severity=GateSeverity.BLOCKER,
                    ),
                ],
            ),
            
            deliverable=Deliverable(
                name="Current Configuration Export",
                description="Complete current state of customer configuration",
                requirements=[
                    DeliverableRequirement(description="Pay rule configuration"),
                    DeliverableRequirement(description="Deduction setup"),
                    DeliverableRequirement(description="Tax jurisdiction list"),
                    DeliverableRequirement(description="Dated within last 30 days"),
                ],
            ),
        ),
        
        PlaybookStep(
            id="gap_analysis",
            name="Gap Analysis",
            order=3,
            
            guidance="""
            This is where you earn your money. Compare what the vendor requires against 
            what the customer has configured.
            
            Every gap is a potential December fire drill. Prioritize by:
            - Impact: What breaks if this isn't fixed?
            - Effort: How hard is the fix?
            - Timeline: When does it need to be done by?
            
            Don't just list problems - give them actionable fixes.
            """,
            
            tips=[
                "Critical gaps = can't process year-end. These go first.",
                "High gaps = will cause rework or adjustments. Fix if time permits.",
                "Don't bury the lead - worst gaps at the top",
                "Every gap needs a recommendation, not just a problem statement",
            ],
            
            common_mistakes=[
                "Listing gaps without severity ratings",
                "Identifying problems without solutions",
                "Missing interdependencies (Gap A requires Gap B fixed first)",
                "Leaving items as 'Unknown' - you have to make a call",
            ],
            
            suggested_features=[
                SuggestedFeature(
                    feature_id="compare",
                    reason="Compare vendor requirements to customer config",
                    pre_configured={
                        "source": "step:gather_vendor_docs:output",
                        "target": "step:collect_customer_config:output",
                    },
                    required=True,
                ),
                SuggestedFeature(
                    feature_id="compliance_check",
                    reason="Run year-end compliance rules",
                    pre_configured={"ruleset": "year_end_requirements"},
                ),
                SuggestedFeature(
                    feature_id="query",
                    reason="Ask specific questions about configuration",
                ),
            ],
            
            quality_gate=QualityGate(
                auto_checks=[
                    AutoCheck(
                        id="all_requirements_mapped",
                        description="All vendor requirements have a status",
                        check_type="custom",
                        check_config={"check": "no_unmapped_requirements"},
                        severity=GateSeverity.BLOCKER,
                    ),
                    AutoCheck(
                        id="no_unknown_status",
                        description="No 'Unknown' or 'Not Assessed' items",
                        check_type="count",
                        check_config={"output": "unknown_items", "max": 0},
                        severity=GateSeverity.BLOCKER,
                    ),
                    AutoCheck(
                        id="critical_gaps_have_remediation",
                        description="All critical gaps have remediation steps",
                        check_type="custom",
                        check_config={"check": "critical_gaps_actionable"},
                        severity=GateSeverity.BLOCKER,
                    ),
                ],
                manual_confirmations=[
                    ManualConfirmation(
                        id="reviewed_all_gaps",
                        label="I've reviewed all gaps and recommendations are actionable",
                        description="Not just identified problems - provided solutions",
                        severity=GateSeverity.BLOCKER,
                    ),
                    ManualConfirmation(
                        id="prioritization_correct",
                        label="Gap priorities accurately reflect business impact",
                        severity=GateSeverity.BLOCKER,
                    ),
                ],
            ),
            
            deliverable=Deliverable(
                name="Gap Analysis Report",
                description="Complete gap analysis with prioritized findings",
                requirements=[
                    DeliverableRequirement(description="Every vendor requirement mapped to customer status"),
                    DeliverableRequirement(description="Gaps categorized by severity (Critical/High/Medium/Low)"),
                    DeliverableRequirement(description="Each gap has remediation recommendation"),
                    DeliverableRequirement(description="No 'Unknown' statuses - everything assessed"),
                ],
            ),
        ),
        
        PlaybookStep(
            id="deliverable_assembly",
            name="Deliverable Assembly",
            order=4,
            
            guidance="""
            Package this for the customer. Executive summary on page 1 - they won't 
            read past it.
            
            Structure:
            1. Executive summary (1 page MAX) - Bottom line up front
            2. Gap summary table with RAG status - Visual overview
            3. Detailed findings with evidence - For the team that has to fix things
            4. Prioritized remediation roadmap - What to do and when
            
            Make it look like it cost what we charged.
            """,
            
            tips=[
                "Executive summary = 'You have X critical gaps. Here's what to do.'",
                "Use RAG colors (Red/Amber/Green) - executives understand this instantly",
                "Don't dump raw data - curate and contextualize",
                "Include timeline: 'This needs to be done by [date] or you risk [consequence]'",
            ],
            
            common_mistakes=[
                "No executive summary - jumping straight to details",
                "Data dumps instead of insights",
                "Missing 'so what' - problems without context",
                "Ugly formatting that undermines credibility",
            ],
            
            suggested_features=[
                SuggestedFeature(
                    feature_id="generate_report",
                    reason="Assemble findings into structured report",
                    pre_configured={
                        "template": "year_end_assessment",
                        "sections": ["executive_summary", "gap_table", "details", "roadmap"],
                    },
                    required=True,
                ),
                SuggestedFeature(
                    feature_id="export",
                    reason="Export final deliverables",
                    pre_configured={
                        "format": "pdf",
                        "branding": "customer",
                    },
                ),
            ],
            
            quality_gate=QualityGate(
                auto_checks=[
                    AutoCheck(
                        id="report_generated",
                        description="Report generated successfully",
                        check_type="exists",
                        check_config={"output": "report"},
                        severity=GateSeverity.BLOCKER,
                    ),
                    AutoCheck(
                        id="exec_summary_length",
                        description="Executive summary is concise (< 500 words)",
                        check_type="custom",
                        check_config={"check": "exec_summary_word_count", "max": 500},
                        severity=GateSeverity.WARNING,
                    ),
                ],
                manual_confirmations=[
                    ManualConfirmation(
                        id="would_put_name_on_it",
                        label="I would put my name on this deliverable",
                        description="It meets my professional standards",
                        severity=GateSeverity.BLOCKER,
                    ),
                    ManualConfirmation(
                        id="client_ready",
                        label="This is ready for client presentation",
                        description="Formatting is professional, content is clear",
                        severity=GateSeverity.BLOCKER,
                    ),
                ],
                requires_review=False,  # Could set to True for junior consultants
            ),
            
            deliverable=Deliverable(
                name="Year-End Readiness Report",
                description="Client-ready assessment report",
                requirements=[
                    DeliverableRequirement(description="Executive summary (1 page max)"),
                    DeliverableRequirement(description="Gap summary table with RAG status"),
                    DeliverableRequirement(description="Detailed findings with evidence"),
                    DeliverableRequirement(description="Prioritized remediation roadmap"),
                    DeliverableRequirement(description="Professional formatting"),
                ],
                template_id="year_end_assessment",
            ),
        ),
    ],
    
    final_deliverables=[
        FinalDeliverable(
            name="Year-End Readiness Report",
            description="Executive report with gap analysis and recommendations",
            format="pdf",
            template_id="year_end_assessment",
            assembled_from=["gap_analysis", "deliverable_assembly"],
        ),
        FinalDeliverable(
            name="Gap Detail Workbook",
            description="Detailed gap data for remediation tracking",
            format="xlsx",
            template_id="gap_workbook",
            assembled_from=["gap_analysis"],
        ),
        FinalDeliverable(
            name="Remediation Tracker",
            description="Actionable task list for customer team",
            format="xlsx",
            template_id="remediation_tracker",
            assembled_from=["gap_analysis"],
        ),
    ],
    
    success_criteria="""
    Customer knows exactly what they need to fix before year-end, in priority order, 
    with clear steps. No surprises in December. They can hand the remediation tracker 
    to their team and say 'do this.'
    """,
)
```

### Playbook Library Index

```python
# backend/playbooks/library/__init__.py
from .year_end_readiness import YEAR_END_READINESS

# HCMPACT Methodology Library
HCMPACT_PLAYBOOKS = [
    YEAR_END_READINESS,
    # Future:
    # IMPLEMENTATION_KICKOFF,
    # GO_LIVE_CHECKLIST,
    # QUARTERLY_HEALTH_CHECK,
    # BENEFITS_OPEN_ENROLLMENT,
    # TAX_UPDATE_ASSESSMENT,
    # DATA_MIGRATION_VALIDATION,
]

def get_playbook(playbook_id: str):
    """Get a playbook by ID."""
    for playbook in HCMPACT_PLAYBOOKS:
        if playbook.id == playbook_id:
            return playbook
    return None

def list_playbooks(category: str = None):
    """List available playbooks."""
    playbooks = HCMPACT_PLAYBOOKS
    if category:
        playbooks = [p for p in playbooks if p.category == category]
    return playbooks
```

---

## Component 8.6: Guidance System

**Goal:** Step-by-step coaching that teaches while guiding.

### Guidance Display

```jsx
// components/StepGuidance.jsx
import { useState } from 'react';
import { Lightbulb, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';

const StepGuidance = ({ step }) => {
  const [showTips, setShowTips] = useState(false);
  const [showMistakes, setShowMistakes] = useState(false);
  
  return (
    <div className="step-guidance">
      {/* Main guidance - always visible */}
      <div className="guidance-main">
        <h3>{step.name}</h3>
        <div className="guidance-text">
          {step.guidance.split('\n\n').map((para, i) => (
            <p key={i}>{para}</p>
          ))}
        </div>
      </div>
      
      {/* Tips - collapsible */}
      {step.tips?.length > 0 && (
        <div className="guidance-section tips">
          <button
            className="section-toggle"
            onClick={() => setShowTips(!showTips)}
          >
            <Lightbulb size={16} />
            <span>Pro Tips ({step.tips.length})</span>
            {showTips ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          
          {showTips && (
            <ul className="tips-list">
              {step.tips.map((tip, i) => (
                <li key={i}>{tip}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      
      {/* Common mistakes - collapsible */}
      {step.common_mistakes?.length > 0 && (
        <div className="guidance-section mistakes">
          <button
            className="section-toggle"
            onClick={() => setShowMistakes(!showMistakes)}
          >
            <AlertTriangle size={16} />
            <span>Common Mistakes ({step.common_mistakes.length})</span>
            {showMistakes ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
          
          {showMistakes && (
            <ul className="mistakes-list">
              {step.common_mistakes.map((mistake, i) => (
                <li key={i}>{mistake}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
};
```

---

## Playbook Execution UI

### Full Execution Screen

```jsx
// pages/PlaybookExecution.jsx
import { useState, useEffect } from 'react';
import { StepGuidance } from '../components/StepGuidance';
import { QualityGate } from '../components/QualityGate';
import { FeaturePanel } from '../components/FeaturePanel';

const PlaybookExecution = ({ instanceId }) => {
  const [instance, setInstance] = useState(null);
  const [playbook, setPlaybook] = useState(null);
  const [currentStep, setCurrentStep] = useState(null);
  
  useEffect(() => {
    loadPlaybookInstance(instanceId);
  }, [instanceId]);
  
  const handleFeatureComplete = async (execution) => {
    // Refresh gate status after feature completes
    const updated = await refreshInstance(instanceId);
    setInstance(updated);
  };
  
  const handleProceed = async () => {
    const result = await proceedToNextStep(instanceId);
    if (result.success) {
      if (result.completed) {
        // Show completion screen
        showCompletionModal();
      } else {
        // Load next step
        setInstance(await refreshInstance(instanceId));
      }
    } else {
      // Show blockers
      showBlockersModal(result.blockers);
    }
  };
  
  if (!currentStep) return <Loading />;
  
  return (
    <div className="playbook-execution">
      {/* Header with progress */}
      <header className="execution-header">
        <div className="playbook-info">
          <h1>{playbook.name}</h1>
          <ProgressBar progress={currentStep.progress} />
        </div>
        <div className="step-nav">
          <StepBreadcrumb
            steps={playbook.steps}
            currentId={instance.current_step_id}
            statuses={instance.step_statuses}
          />
        </div>
      </header>
      
      <div className="execution-layout">
        {/* Left: Guidance + Quality Gate */}
        <div className="guidance-panel">
          <StepGuidance step={currentStep.step} />
          
          <QualityGate
            gate={currentStep.step.quality_gate}
            gateStatus={instance.gate_results[currentStep.step.id]}
            onConfirm={handleManualConfirm}
            canProceed={currentStep.can_proceed}
          />
          
          <div className="step-actions">
            <button
              className="primary proceed-btn"
              onClick={handleProceed}
              disabled={!currentStep.can_proceed}
            >
              {currentStep.can_proceed ? 'Proceed to Next Step →' : 'Complete Requirements to Proceed'}
            </button>
          </div>
        </div>
        
        {/* Right: Feature workspace */}
        <div className="feature-panel">
          <h3>Tools for this Step</h3>
          
          {/* Suggested features */}
          <div className="suggested-features">
            {currentStep.suggested_features.map(sf => (
              <FeatureCard
                key={sf.feature.id}
                feature={sf.feature}
                reason={sf.reason}
                preConfigured={sf.pre_configured}
                required={sf.required}
                onLaunch={() => launchFeature(sf.feature.id, sf.pre_configured)}
              />
            ))}
          </div>
          
          {/* Other features (if allowed) */}
          {currentStep.step.allow_other_features && (
            <div className="other-features">
              <button onClick={() => setShowAllFeatures(true)}>
                + Use Other Feature
              </button>
            </div>
          )}
          
          {/* Active feature workspace */}
          {activeFeature && (
            <FeatureWorkspace
              feature={activeFeature}
              onComplete={handleFeatureComplete}
              onCancel={() => setActiveFeature(null)}
            />
          )}
        </div>
      </div>
    </div>
  );
};
```

---

## Success Criteria

### Phase Complete When:
1. Can execute HCMPACT playbooks end-to-end
2. Quality gates block progress until satisfied
3. Guidance displays at each step
4. Features execute within playbook context
5. Final deliverables can be assembled and exported
6. At least 1 complete HCMPACT playbook (Year-End Readiness) working

### Quality Gates:
- Consultants cannot skip steps
- Quality gates require confirmation before proceeding
- All playbook executions are tracked/auditable
- Custom playbooks can be created from scratch

---

## Future HCMPACT Playbooks to Build

| Playbook | Category | Difficulty | Duration |
|----------|----------|------------|----------|
| Year-End Readiness | Year-End | Intermediate | 3-5 days |
| Implementation Kickoff | Implementation | Beginner | 1-2 days |
| Go-Live Checklist | Implementation | Intermediate | 2-3 days |
| Quarterly Health Check | Maintenance | Beginner | 1-2 days |
| Benefits Open Enrollment | Benefits | Advanced | 1-2 weeks |
| Tax Update Assessment | Tax | Intermediate | 2-3 days |
| Data Migration Validation | Implementation | Advanced | 1 week |
| Audit Preparation | Compliance | Intermediate | 3-5 days |

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-13 | Initial phase doc created |
