# Phase 7: Feature Engine

**Status:** FUTURE  
**Total Estimated Hours:** 25-35  
**Dependencies:** Phase 6 (API Connectivity) complete  
**Last Updated:** January 13, 2026

---

## Objective

Build the atomic building blocks (Features) that consultants use to accomplish work. Features are composable, configurable, and can be assembled into Playbooks. Ship with a core library of pre-built features, plus a Feature Builder for power users to create custom features.

---

## Background

### What is a Feature?

A Feature is a discrete unit of work with defined inputs, processing, and outputs. Think of them as LEGO blocks that snap together into workflows.

**Examples:**
- Upload (ingest data)
- Compare (diff two datasets)
- Export (produce deliverable)
- Compliance Check (run rules)
- Crosswalk/Mapping (field alignment)

### Design Principles

1. **Atomic** - Each feature does one thing well
2. **Composable** - Features chain together (output of one → input of another)
3. **Configurable** - Same feature, different parameters
4. **Reusable** - Build once, use in many playbooks

---

## Feature Anatomy

Every feature follows this structure:

```
FEATURE
├── Metadata
│   ├── ID, Name, Description
│   ├── Category (Ingest, Transform, Compare, Analyze, Collaborate, Output)
│   ├── Version
│   └── Author (system or consultant)
│
├── Inputs
│   ├── Data inputs (tables, documents, prior feature outputs)
│   ├── Context inputs (project, customer, user)
│   └── Config inputs (parameters set at design time or runtime)
│
├── Processing
│   ├── Data operations (SQL, transforms)
│   ├── AI operations (summarize, classify, extract)
│   └── External calls (APIs, services)
│
└── Outputs
    ├── Data outputs (tables, documents)
    ├── Artifacts (reports, exports)
    └── Signals (pass/fail, status, route to next step)
```

---

## Component Overview

| # | Component | Hours | Description |
|---|-----------|-------|-------------|
| 7.1 | Feature Schema & Runtime | 4-5 | Define feature anatomy, execution engine |
| 7.2 | Core Feature Library | 10-14 | Pre-built features |
| 7.3 | Feature Builder UI | 6-8 | Low-code + AI assist creation |
| 7.4 | Feature Registry | 3-4 | Store, version, discover features |
| 7.5 | Feature Testing Framework | 2-3 | Validate custom features |

---

## Component 7.1: Feature Schema & Runtime

**Goal:** Define how features work and build the execution engine.

### Feature Schema

```python
# backend/features/schema.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

class FeatureCategory(Enum):
    INGEST = "ingest"
    TRANSFORM = "transform"
    COMPARE = "compare"
    ANALYZE = "analyze"
    COLLABORATE = "collaborate"
    OUTPUT = "output"

class InputType(Enum):
    TABLE = "table"
    DOCUMENT = "document"
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    FEATURE_OUTPUT = "feature_output"  # Output from prior feature

class OutputType(Enum):
    TABLE = "table"
    DOCUMENT = "document"
    ARTIFACT = "artifact"  # PDF, Excel, etc.
    TEXT = "text"
    STATUS = "status"  # Pass/Fail/Warning
    STRUCTURED = "structured"  # JSON blob

@dataclass
class FeatureInput:
    """Definition of a feature input."""
    name: str
    type: InputType
    description: str
    required: bool = True
    default: Any = None
    options: List[str] = field(default_factory=list)  # For SELECT types
    validation: Optional[str] = None  # Validation expression

@dataclass
class FeatureOutput:
    """Definition of a feature output."""
    name: str
    type: OutputType
    description: str

@dataclass
class FeatureDefinition:
    """Complete feature definition."""
    id: str
    name: str
    description: str
    category: FeatureCategory
    version: int = 1
    
    # Authorship
    author: str = "system"
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Inputs/Outputs
    inputs: List[FeatureInput] = field(default_factory=list)
    outputs: List[FeatureOutput] = field(default_factory=list)
    
    # Processing (for custom features)
    processing_type: str = "builtin"  # builtin, sql, python, ai
    processing_config: Dict[str, Any] = field(default_factory=dict)
    
    # UI hints
    icon: str = "box"
    color: str = "#6366f1"
    
    # Feature flags
    active: bool = True
    requires_review: bool = False  # For custom features pending approval

@dataclass
class FeatureExecution:
    """Runtime execution of a feature."""
    feature_id: str
    execution_id: str
    project_id: str
    
    # Input values (resolved at runtime)
    input_values: Dict[str, Any] = field(default_factory=dict)
    
    # Execution state
    status: str = "pending"  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    logs: List[str] = field(default_factory=list)
```

### Feature Runtime Engine

```python
# backend/features/engine.py
from typing import Dict, Any, Optional
import logging
from .schema import FeatureDefinition, FeatureExecution, OutputType
from .registry import FeatureRegistry

logger = logging.getLogger(__name__)

class FeatureEngine:
    """Execute features."""
    
    def __init__(self):
        self.registry = FeatureRegistry()
        self.executors = {}  # feature_id -> executor function
        self._register_builtin_executors()
    
    def _register_builtin_executors(self):
        """Register built-in feature executors."""
        from .library import (
            upload_executor,
            compare_executor,
            export_executor,
            compliance_check_executor,
            crosswalk_executor,
            query_executor,
            summarize_executor,
            snapshot_executor,
            assign_executor,
            generate_report_executor,
        )
        
        self.executors = {
            "upload": upload_executor,
            "compare": compare_executor,
            "export": export_executor,
            "compliance_check": compliance_check_executor,
            "crosswalk": crosswalk_executor,
            "query": query_executor,
            "summarize": summarize_executor,
            "snapshot": snapshot_executor,
            "assign": assign_executor,
            "generate_report": generate_report_executor,
        }
    
    async def execute(
        self,
        feature_id: str,
        project_id: str,
        inputs: Dict[str, Any],
        context: Dict[str, Any] = None,
    ) -> FeatureExecution:
        """
        Execute a feature.
        
        Args:
            feature_id: ID of feature to execute
            project_id: Project context
            inputs: Input values
            context: Additional context (user, prior outputs, etc.)
        
        Returns:
            FeatureExecution with results
        """
        # Get feature definition
        feature = self.registry.get(feature_id)
        if not feature:
            raise ValueError(f"Feature not found: {feature_id}")
        
        # Create execution record
        execution = FeatureExecution(
            feature_id=feature_id,
            execution_id=self._generate_execution_id(),
            project_id=project_id,
            input_values=inputs,
            status="running",
            started_at=datetime.utcnow(),
        )
        
        try:
            # Validate inputs
            self._validate_inputs(feature, inputs)
            
            # Get executor
            if feature.processing_type == "builtin":
                executor = self.executors.get(feature_id)
                if not executor:
                    raise ValueError(f"No executor for builtin feature: {feature_id}")
                
                # Execute
                outputs = await executor(inputs, context or {})
                
            elif feature.processing_type == "sql":
                outputs = await self._execute_sql_feature(feature, inputs, context)
                
            elif feature.processing_type == "ai":
                outputs = await self._execute_ai_feature(feature, inputs, context)
                
            elif feature.processing_type == "python":
                outputs = await self._execute_python_feature(feature, inputs, context)
                
            else:
                raise ValueError(f"Unknown processing type: {feature.processing_type}")
            
            # Success
            execution.status = "completed"
            execution.outputs = outputs
            execution.completed_at = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Feature execution failed: {e}")
            execution.status = "failed"
            execution.error = str(e)
            execution.completed_at = datetime.utcnow()
        
        # Store execution record
        await self._store_execution(execution)
        
        return execution
    
    def _validate_inputs(self, feature: FeatureDefinition, inputs: Dict[str, Any]):
        """Validate inputs against feature definition."""
        for input_def in feature.inputs:
            if input_def.required and input_def.name not in inputs:
                raise ValueError(f"Missing required input: {input_def.name}")
            
            if input_def.name in inputs and input_def.validation:
                # Run validation expression
                value = inputs[input_def.name]
                if not self._eval_validation(input_def.validation, value):
                    raise ValueError(f"Validation failed for {input_def.name}")
    
    async def _execute_sql_feature(
        self,
        feature: FeatureDefinition,
        inputs: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a SQL-based custom feature."""
        sql_template = feature.processing_config.get("sql_template", "")
        
        # Substitute input values into SQL
        sql = sql_template.format(**inputs)
        
        # Execute via DuckDB
        from ..db import execute_query
        results = await execute_query(context["project_id"], sql)
        
        return {"results": results}
    
    async def _execute_ai_feature(
        self,
        feature: FeatureDefinition,
        inputs: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute an AI-based custom feature."""
        prompt_template = feature.processing_config.get("prompt_template", "")
        output_type = feature.processing_config.get("output_type", "text")
        
        # Build prompt
        prompt = prompt_template.format(**inputs)
        
        # Call LLM
        from ..intelligence.synthesizer import Synthesizer
        synth = Synthesizer()
        
        if output_type == "structured":
            result = await synth.generate_structured(prompt)
        else:
            result = await synth.generate_text(prompt)
        
        return {"result": result}
    
    async def _execute_python_feature(
        self,
        feature: FeatureDefinition,
        inputs: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a Python-based custom feature (sandboxed)."""
        code = feature.processing_config.get("code", "")
        
        # Execute in sandbox
        # TODO: Implement sandboxed execution
        raise NotImplementedError("Python features not yet implemented")
```

---

## Component 7.2: Core Feature Library

**Goal:** Ship with 10-12 pre-built features covering common needs.

### Feature Categories & Library

| Category | Feature | Description | Priority |
|----------|---------|-------------|----------|
| **Ingest** | Upload | Upload files (CSV, Excel, PDF, docs) | P0 (exists) |
| **Ingest** | API_Pull | Pull data from connected APIs | P1 |
| **Ingest** | Manual_Entry | Form-based data entry | P2 |
| **Transform** | Crosswalk | Map fields between source/target | P0 |
| **Transform** | Clean | Data cleaning rules | P1 |
| **Transform** | Filter | Filter dataset by criteria | P1 |
| **Compare** | Diff | Compare two datasets, show changes | P0 |
| **Compare** | Compliance_Check | Run rules, flag violations | P0 |
| **Compare** | Benchmark | Compare against standards | P2 |
| **Analyze** | Query | Ask questions, get answers | P0 (exists) |
| **Analyze** | Summarize | AI summary of data/docs | P1 |
| **Collaborate** | Assign | Route to person for action | P1 |
| **Collaborate** | Snapshot | Save point-in-time state | P1 |
| **Output** | Export | Export to PDF/Excel/etc. | P0 (building) |
| **Output** | Generate_Report | Assemble multi-section report | P0 |

### Core Feature Definitions

```python
# backend/features/library/definitions.py
from ..schema import (
    FeatureDefinition, FeatureInput, FeatureOutput,
    FeatureCategory, InputType, OutputType
)

CORE_FEATURES = [
    # ============ INGEST ============
    FeatureDefinition(
        id="upload",
        name="Upload",
        description="Upload files to the project (CSV, Excel, PDF, documents)",
        category=FeatureCategory.INGEST,
        icon="upload",
        color="#10b981",
        inputs=[
            FeatureInput(
                name="files",
                type=InputType.DOCUMENT,
                description="Files to upload",
                required=True,
            ),
            FeatureInput(
                name="doc_type",
                type=InputType.SELECT,
                description="Document classification",
                required=False,
                options=["customer_config", "vendor_reference", "regulatory", "other"],
            ),
        ],
        outputs=[
            FeatureOutput(
                name="uploaded_files",
                type=OutputType.TABLE,
                description="List of uploaded files with metadata",
            ),
            FeatureOutput(
                name="status",
                type=OutputType.STATUS,
                description="Upload success/failure status",
            ),
        ],
    ),
    
    FeatureDefinition(
        id="api_pull",
        name="API Pull",
        description="Pull data from connected customer instance or vendor API",
        category=FeatureCategory.INGEST,
        icon="download-cloud",
        color="#10b981",
        inputs=[
            FeatureInput(
                name="source",
                type=InputType.SELECT,
                description="API source to pull from",
                required=True,
                options=["customer_instance", "ukg_docs", "workday_docs"],
            ),
            FeatureInput(
                name="endpoint",
                type=InputType.TEXT,
                description="Specific endpoint or data type",
                required=False,
            ),
            FeatureInput(
                name="filters",
                type=InputType.TEXT,
                description="Filter criteria (JSON)",
                required=False,
            ),
        ],
        outputs=[
            FeatureOutput(
                name="data",
                type=OutputType.TABLE,
                description="Pulled data",
            ),
            FeatureOutput(
                name="metadata",
                type=OutputType.STRUCTURED,
                description="Pull metadata (timestamp, record count, etc.)",
            ),
        ],
    ),
    
    # ============ TRANSFORM ============
    FeatureDefinition(
        id="crosswalk",
        name="Crosswalk / Field Mapping",
        description="Map fields from source to target schema",
        category=FeatureCategory.TRANSFORM,
        icon="git-merge",
        color="#f59e0b",
        inputs=[
            FeatureInput(
                name="source_table",
                type=InputType.TABLE,
                description="Source data table",
                required=True,
            ),
            FeatureInput(
                name="target_schema",
                type=InputType.DOCUMENT,
                description="Target schema definition",
                required=True,
            ),
            FeatureInput(
                name="auto_map",
                type=InputType.BOOLEAN,
                description="Attempt automatic field matching",
                required=False,
                default=True,
            ),
        ],
        outputs=[
            FeatureOutput(
                name="mapping",
                type=OutputType.STRUCTURED,
                description="Field mapping (source → target)",
            ),
            FeatureOutput(
                name="unmapped_source",
                type=OutputType.TABLE,
                description="Source fields with no target match",
            ),
            FeatureOutput(
                name="unmapped_target",
                type=OutputType.TABLE,
                description="Target fields with no source match",
            ),
        ],
    ),
    
    FeatureDefinition(
        id="filter",
        name="Filter",
        description="Filter dataset by criteria",
        category=FeatureCategory.TRANSFORM,
        icon="filter",
        color="#f59e0b",
        inputs=[
            FeatureInput(
                name="source_table",
                type=InputType.TABLE,
                description="Table to filter",
                required=True,
            ),
            FeatureInput(
                name="criteria",
                type=InputType.TEXT,
                description="Filter criteria (natural language or SQL WHERE)",
                required=True,
            ),
        ],
        outputs=[
            FeatureOutput(
                name="filtered_data",
                type=OutputType.TABLE,
                description="Filtered results",
            ),
            FeatureOutput(
                name="excluded_count",
                type=OutputType.TEXT,
                description="Number of records excluded",
            ),
        ],
    ),
    
    # ============ COMPARE ============
    FeatureDefinition(
        id="compare",
        name="Compare / Diff",
        description="Compare two datasets and identify differences",
        category=FeatureCategory.COMPARE,
        icon="git-compare",
        color="#8b5cf6",
        inputs=[
            FeatureInput(
                name="source",
                type=InputType.TABLE,
                description="Source dataset (baseline)",
                required=True,
            ),
            FeatureInput(
                name="target",
                type=InputType.TABLE,
                description="Target dataset (to compare)",
                required=True,
            ),
            FeatureInput(
                name="key_columns",
                type=InputType.MULTI_SELECT,
                description="Columns to match records on",
                required=True,
            ),
            FeatureInput(
                name="compare_columns",
                type=InputType.MULTI_SELECT,
                description="Columns to compare (empty = all)",
                required=False,
            ),
        ],
        outputs=[
            FeatureOutput(
                name="added",
                type=OutputType.TABLE,
                description="Records in target but not source",
            ),
            FeatureOutput(
                name="removed",
                type=OutputType.TABLE,
                description="Records in source but not target",
            ),
            FeatureOutput(
                name="changed",
                type=OutputType.TABLE,
                description="Records with value differences",
            ),
            FeatureOutput(
                name="unchanged",
                type=OutputType.TABLE,
                description="Records with no differences",
            ),
            FeatureOutput(
                name="summary",
                type=OutputType.STRUCTURED,
                description="Diff summary statistics",
            ),
        ],
    ),
    
    FeatureDefinition(
        id="compliance_check",
        name="Compliance Check",
        description="Run rules against data, flag violations",
        category=FeatureCategory.COMPARE,
        icon="shield-check",
        color="#8b5cf6",
        inputs=[
            FeatureInput(
                name="data",
                type=InputType.TABLE,
                description="Data to check",
                required=True,
            ),
            FeatureInput(
                name="ruleset",
                type=InputType.SELECT,
                description="Compliance ruleset to apply",
                required=True,
                options=["year_end_requirements", "payroll_compliance", "benefits_eligibility", "custom"],
            ),
            FeatureInput(
                name="custom_rules",
                type=InputType.TEXT,
                description="Custom rules (if ruleset=custom)",
                required=False,
            ),
        ],
        outputs=[
            FeatureOutput(
                name="violations",
                type=OutputType.TABLE,
                description="Records failing compliance checks",
            ),
            FeatureOutput(
                name="passed",
                type=OutputType.TABLE,
                description="Records passing all checks",
            ),
            FeatureOutput(
                name="summary",
                type=OutputType.STRUCTURED,
                description="Compliance summary by rule",
            ),
            FeatureOutput(
                name="status",
                type=OutputType.STATUS,
                description="Overall pass/fail/warning status",
            ),
        ],
    ),
    
    # ============ ANALYZE ============
    FeatureDefinition(
        id="query",
        name="Query",
        description="Ask questions about your data in natural language",
        category=FeatureCategory.ANALYZE,
        icon="message-circle",
        color="#06b6d4",
        inputs=[
            FeatureInput(
                name="question",
                type=InputType.TEXT,
                description="Question to ask",
                required=True,
            ),
            FeatureInput(
                name="scope",
                type=InputType.MULTI_SELECT,
                description="Tables/docs to include in scope",
                required=False,
            ),
        ],
        outputs=[
            FeatureOutput(
                name="answer",
                type=OutputType.TEXT,
                description="Natural language answer",
            ),
            FeatureOutput(
                name="data",
                type=OutputType.TABLE,
                description="Supporting data",
            ),
            FeatureOutput(
                name="citations",
                type=OutputType.STRUCTURED,
                description="Source citations",
            ),
        ],
    ),
    
    FeatureDefinition(
        id="summarize",
        name="Summarize",
        description="AI-generated summary of data or documents",
        category=FeatureCategory.ANALYZE,
        icon="file-text",
        color="#06b6d4",
        inputs=[
            FeatureInput(
                name="source",
                type=InputType.DOCUMENT,
                description="Document or data to summarize",
                required=True,
            ),
            FeatureInput(
                name="focus",
                type=InputType.TEXT,
                description="Specific focus areas (optional)",
                required=False,
            ),
            FeatureInput(
                name="length",
                type=InputType.SELECT,
                description="Summary length",
                required=False,
                default="medium",
                options=["brief", "medium", "detailed"],
            ),
        ],
        outputs=[
            FeatureOutput(
                name="summary",
                type=OutputType.TEXT,
                description="Generated summary",
            ),
            FeatureOutput(
                name="key_points",
                type=OutputType.STRUCTURED,
                description="Extracted key points",
            ),
        ],
    ),
    
    # ============ COLLABORATE ============
    FeatureDefinition(
        id="assign",
        name="Assign / Route",
        description="Assign work to a team member for action",
        category=FeatureCategory.COLLABORATE,
        icon="user-plus",
        color="#ec4899",
        inputs=[
            FeatureInput(
                name="assignee",
                type=InputType.SELECT,
                description="Person to assign to",
                required=True,
                options=[],  # Populated dynamically from team
            ),
            FeatureInput(
                name="task_description",
                type=InputType.TEXT,
                description="What needs to be done",
                required=True,
            ),
            FeatureInput(
                name="due_date",
                type=InputType.DATE,
                description="Due date",
                required=False,
            ),
            FeatureInput(
                name="attachments",
                type=InputType.FEATURE_OUTPUT,
                description="Outputs from prior features to include",
                required=False,
            ),
        ],
        outputs=[
            FeatureOutput(
                name="assignment",
                type=OutputType.STRUCTURED,
                description="Assignment record",
            ),
            FeatureOutput(
                name="status",
                type=OutputType.STATUS,
                description="Assignment status",
            ),
        ],
    ),
    
    FeatureDefinition(
        id="snapshot",
        name="Snapshot",
        description="Save point-in-time state for audit trail",
        category=FeatureCategory.COLLABORATE,
        icon="camera",
        color="#ec4899",
        inputs=[
            FeatureInput(
                name="name",
                type=InputType.TEXT,
                description="Snapshot name",
                required=True,
            ),
            FeatureInput(
                name="description",
                type=InputType.TEXT,
                description="What this snapshot captures",
                required=False,
            ),
            FeatureInput(
                name="include_data",
                type=InputType.BOOLEAN,
                description="Include full data copies",
                required=False,
                default=True,
            ),
        ],
        outputs=[
            FeatureOutput(
                name="snapshot_id",
                type=OutputType.TEXT,
                description="Snapshot identifier",
            ),
            FeatureOutput(
                name="snapshot_metadata",
                type=OutputType.STRUCTURED,
                description="Snapshot details",
            ),
        ],
    ),
    
    # ============ OUTPUT ============
    FeatureDefinition(
        id="export",
        name="Export",
        description="Export data or reports to file",
        category=FeatureCategory.OUTPUT,
        icon="download",
        color="#ef4444",
        inputs=[
            FeatureInput(
                name="source",
                type=InputType.FEATURE_OUTPUT,
                description="Data or content to export",
                required=True,
            ),
            FeatureInput(
                name="format",
                type=InputType.SELECT,
                description="Output format",
                required=True,
                options=["pdf", "xlsx", "csv", "docx"],
            ),
            FeatureInput(
                name="template",
                type=InputType.SELECT,
                description="Export template (optional)",
                required=False,
                options=[],  # Populated from template registry
            ),
            FeatureInput(
                name="branding",
                type=InputType.SELECT,
                description="Branding to apply",
                required=False,
                options=["hcmpact", "customer", "none"],
            ),
        ],
        outputs=[
            FeatureOutput(
                name="file",
                type=OutputType.ARTIFACT,
                description="Exported file",
            ),
            FeatureOutput(
                name="download_url",
                type=OutputType.TEXT,
                description="Download URL",
            ),
        ],
    ),
    
    FeatureDefinition(
        id="generate_report",
        name="Generate Report",
        description="Assemble multiple analyses into a structured report",
        category=FeatureCategory.OUTPUT,
        icon="file-plus",
        color="#ef4444",
        inputs=[
            FeatureInput(
                name="template",
                type=InputType.SELECT,
                description="Report template",
                required=True,
                options=["gap_analysis", "executive_brief", "compliance_report", "custom"],
            ),
            FeatureInput(
                name="sections",
                type=InputType.FEATURE_OUTPUT,
                description="Feature outputs to include as sections",
                required=True,
            ),
            FeatureInput(
                name="executive_summary",
                type=InputType.BOOLEAN,
                description="Auto-generate executive summary",
                required=False,
                default=True,
            ),
        ],
        outputs=[
            FeatureOutput(
                name="report",
                type=OutputType.DOCUMENT,
                description="Generated report",
            ),
            FeatureOutput(
                name="sections",
                type=OutputType.STRUCTURED,
                description="Report section metadata",
            ),
        ],
    ),
]
```

---

## Component 7.3: Feature Builder UI

**Goal:** Low-code + AI-assisted custom feature creation.

### Feature Builder Interface

```jsx
// pages/FeatureBuilder.jsx
import { useState } from 'react';
import { Wand2, Code, Database, MessageSquare } from 'lucide-react';

const FeatureBuilder = () => {
  const [step, setStep] = useState(1);
  const [feature, setFeature] = useState({
    name: '',
    description: '',
    category: 'analyze',
    inputs: [],
    outputs: [],
    processing_type: 'ai',
    processing_config: {},
  });
  
  return (
    <div className="feature-builder">
      <header>
        <h1>Create Custom Feature</h1>
        <StepIndicator current={step} total={4} />
      </header>
      
      {step === 1 && (
        <BasicInfoStep feature={feature} onChange={setFeature} onNext={() => setStep(2)} />
      )}
      
      {step === 2 && (
        <InputsStep feature={feature} onChange={setFeature} onNext={() => setStep(3)} onBack={() => setStep(1)} />
      )}
      
      {step === 3 && (
        <ProcessingStep feature={feature} onChange={setFeature} onNext={() => setStep(4)} onBack={() => setStep(2)} />
      )}
      
      {step === 4 && (
        <OutputsStep feature={feature} onChange={setFeature} onSubmit={handleSubmit} onBack={() => setStep(3)} />
      )}
    </div>
  );
};

const ProcessingStep = ({ feature, onChange, onNext, onBack }) => {
  const [aiPrompt, setAiPrompt] = useState('');
  const [generating, setGenerating] = useState(false);
  
  const handleAIGenerate = async () => {
    setGenerating(true);
    try {
      // Send description to AI to generate processing logic
      const response = await fetch('/api/features/ai-generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: feature.name,
          description: feature.description,
          inputs: feature.inputs,
          prompt: aiPrompt,
        }),
      });
      
      const result = await response.json();
      
      onChange({
        ...feature,
        processing_type: result.type,
        processing_config: result.config,
        outputs: result.suggested_outputs || feature.outputs,
      });
      
    } finally {
      setGenerating(false);
    }
  };
  
  return (
    <div className="step processing-step">
      <h2>Define Processing Logic</h2>
      <p>How should this feature process inputs to produce outputs?</p>
      
      <div className="processing-options">
        <ProcessingOption
          icon={<Wand2 />}
          title="AI-Assisted"
          description="Describe what you want in plain English"
          selected={feature.processing_type === 'ai'}
          onClick={() => onChange({ ...feature, processing_type: 'ai' })}
        />
        
        <ProcessingOption
          icon={<Database />}
          title="SQL Query"
          description="Write a SQL template with input placeholders"
          selected={feature.processing_type === 'sql'}
          onClick={() => onChange({ ...feature, processing_type: 'sql' })}
        />
        
        <ProcessingOption
          icon={<Code />}
          title="Python Code"
          description="Write custom Python logic (advanced)"
          selected={feature.processing_type === 'python'}
          onClick={() => onChange({ ...feature, processing_type: 'python' })}
        />
      </div>
      
      {feature.processing_type === 'ai' && (
        <div className="ai-builder">
          <label>Describe what this feature should do:</label>
          <textarea
            value={aiPrompt}
            onChange={e => setAiPrompt(e.target.value)}
            placeholder="For each employee, check if their hours worked is greater than the minimum hours threshold. Flag employees who don't meet the threshold along with the reason..."
            rows={6}
          />
          
          <button 
            className="primary"
            onClick={handleAIGenerate}
            disabled={!aiPrompt || generating}
          >
            {generating ? 'Generating...' : '✨ Generate Logic'}
          </button>
          
          {feature.processing_config.generated && (
            <div className="generated-preview">
              <h4>Generated Logic</h4>
              <pre>{JSON.stringify(feature.processing_config, null, 2)}</pre>
              <p className="hint">You can edit this or regenerate</p>
            </div>
          )}
        </div>
      )}
      
      {feature.processing_type === 'sql' && (
        <div className="sql-builder">
          <label>SQL Template (use {`{input_name}`} for placeholders):</label>
          <textarea
            value={feature.processing_config.sql_template || ''}
            onChange={e => onChange({
              ...feature,
              processing_config: { ...feature.processing_config, sql_template: e.target.value }
            })}
            placeholder={`SELECT * FROM {source_table}\nWHERE hours_worked < {min_hours}`}
            rows={10}
            className="code"
          />
        </div>
      )}
      
      {feature.processing_type === 'python' && (
        <div className="python-builder">
          <label>Python Code:</label>
          <textarea
            value={feature.processing_config.code || ''}
            onChange={e => onChange({
              ...feature,
              processing_config: { ...feature.processing_config, code: e.target.value }
            })}
            placeholder={`def process(inputs, context):\n    # Your logic here\n    return {"result": ...}`}
            rows={15}
            className="code"
          />
          <p className="warning">⚠️ Custom Python features require admin approval</p>
        </div>
      )}
      
      <div className="step-actions">
        <button onClick={onBack}>Back</button>
        <button className="primary" onClick={onNext}>Next: Define Outputs</button>
      </div>
    </div>
  );
};
```

### AI Feature Generation Backend

```python
# backend/features/ai_generator.py
from typing import Dict, Any, List
import json

class FeatureAIGenerator:
    """Generate feature processing logic from natural language."""
    
    async def generate(
        self,
        name: str,
        description: str,
        inputs: List[Dict],
        prompt: str,
    ) -> Dict[str, Any]:
        """
        Generate feature processing config from description.
        
        Returns processing_type and processing_config.
        """
        # Build context for LLM
        input_descriptions = "\n".join([
            f"- {inp['name']} ({inp['type']}): {inp.get('description', '')}"
            for inp in inputs
        ])
        
        system_prompt = """You are a feature builder assistant. Given a feature description and inputs,
        generate the appropriate processing logic.
        
        You can generate one of these types:
        1. "sql" - A SQL template with {input_name} placeholders
        2. "ai" - A prompt template for LLM processing
        
        Respond with JSON:
        {
            "type": "sql" | "ai",
            "config": {
                // For SQL:
                "sql_template": "SELECT ... FROM {table} WHERE ..."
                
                // For AI:
                "prompt_template": "Analyze the following data...",
                "output_type": "text" | "structured"
            },
            "suggested_outputs": [
                {"name": "...", "type": "...", "description": "..."}
            ]
        }
        """
        
        user_prompt = f"""Feature: {name}
        Description: {description}
        
        Available Inputs:
        {input_descriptions}
        
        User's description of what it should do:
        {prompt}
        
        Generate the processing logic:"""
        
        # Call LLM
        from ..intelligence.synthesizer import Synthesizer
        synth = Synthesizer()
        
        response = await synth.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        
        return json.loads(response)
```

---

## Component 7.4: Feature Registry

**Goal:** Store, version, and discover features.

### Registry Storage

```python
# backend/features/registry.py
from typing import List, Optional, Dict
from datetime import datetime
import json
from pathlib import Path
from .schema import FeatureDefinition

class FeatureRegistry:
    """Store and retrieve feature definitions."""
    
    def __init__(self, storage_path: str = "/data/features"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, FeatureDefinition] = {}
        self._load_builtin_features()
    
    def _load_builtin_features(self):
        """Load built-in feature definitions."""
        from .library.definitions import CORE_FEATURES
        for feature in CORE_FEATURES:
            self._cache[feature.id] = feature
    
    def get(self, feature_id: str) -> Optional[FeatureDefinition]:
        """Get a feature by ID."""
        # Check cache first
        if feature_id in self._cache:
            return self._cache[feature_id]
        
        # Check storage
        feature_path = self.storage_path / f"{feature_id}.json"
        if feature_path.exists():
            data = json.loads(feature_path.read_text())
            feature = self._dict_to_feature(data)
            self._cache[feature_id] = feature
            return feature
        
        return None
    
    def list(
        self,
        category: str = None,
        author: str = None,
        active_only: bool = True,
    ) -> List[FeatureDefinition]:
        """List features with optional filters."""
        # Ensure all custom features are loaded
        self._load_custom_features()
        
        features = list(self._cache.values())
        
        if category:
            features = [f for f in features if f.category.value == category]
        
        if author:
            features = [f for f in features if f.author == author]
        
        if active_only:
            features = [f for f in features if f.active]
        
        return features
    
    def save(self, feature: FeatureDefinition) -> str:
        """Save a custom feature."""
        # Generate ID if needed
        if not feature.id:
            feature.id = self._generate_id(feature.name)
        
        # Check for version conflict
        existing = self.get(feature.id)
        if existing:
            feature.version = existing.version + 1
        
        # Save to storage
        feature_path = self.storage_path / f"{feature.id}.json"
        feature_path.write_text(json.dumps(self._feature_to_dict(feature), indent=2))
        
        # Update cache
        self._cache[feature.id] = feature
        
        return feature.id
    
    def _load_custom_features(self):
        """Load all custom features from storage."""
        for path in self.storage_path.glob("*.json"):
            feature_id = path.stem
            if feature_id not in self._cache:
                data = json.loads(path.read_text())
                self._cache[feature_id] = self._dict_to_feature(data)
    
    def _generate_id(self, name: str) -> str:
        """Generate feature ID from name."""
        base_id = name.lower().replace(" ", "_")
        # Ensure uniqueness
        if base_id not in self._cache:
            return base_id
        
        counter = 1
        while f"{base_id}_{counter}" in self._cache:
            counter += 1
        return f"{base_id}_{counter}"
    
    def _feature_to_dict(self, feature: FeatureDefinition) -> dict:
        """Convert feature to serializable dict."""
        return {
            "id": feature.id,
            "name": feature.name,
            "description": feature.description,
            "category": feature.category.value,
            "version": feature.version,
            "author": feature.author,
            "created_at": feature.created_at.isoformat(),
            "inputs": [
                {
                    "name": i.name,
                    "type": i.type.value,
                    "description": i.description,
                    "required": i.required,
                    "default": i.default,
                    "options": i.options,
                }
                for i in feature.inputs
            ],
            "outputs": [
                {
                    "name": o.name,
                    "type": o.type.value,
                    "description": o.description,
                }
                for o in feature.outputs
            ],
            "processing_type": feature.processing_type,
            "processing_config": feature.processing_config,
            "icon": feature.icon,
            "color": feature.color,
            "active": feature.active,
            "requires_review": feature.requires_review,
        }
    
    def _dict_to_feature(self, data: dict) -> FeatureDefinition:
        """Convert dict to FeatureDefinition."""
        from .schema import FeatureInput, FeatureOutput, FeatureCategory, InputType, OutputType
        
        return FeatureDefinition(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            category=FeatureCategory(data["category"]),
            version=data.get("version", 1),
            author=data.get("author", "system"),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            inputs=[
                FeatureInput(
                    name=i["name"],
                    type=InputType(i["type"]),
                    description=i["description"],
                    required=i.get("required", True),
                    default=i.get("default"),
                    options=i.get("options", []),
                )
                for i in data.get("inputs", [])
            ],
            outputs=[
                FeatureOutput(
                    name=o["name"],
                    type=OutputType(o["type"]),
                    description=o["description"],
                )
                for o in data.get("outputs", [])
            ],
            processing_type=data.get("processing_type", "builtin"),
            processing_config=data.get("processing_config", {}),
            icon=data.get("icon", "box"),
            color=data.get("color", "#6366f1"),
            active=data.get("active", True),
            requires_review=data.get("requires_review", False),
        )
```

---

## Component 7.5: Feature Testing Framework

**Goal:** Validate custom features before they're used in playbooks.

```python
# backend/features/testing.py
from typing import List, Dict, Any
from dataclasses import dataclass
from .schema import FeatureDefinition, FeatureExecution
from .engine import FeatureEngine

@dataclass
class TestCase:
    """A test case for a feature."""
    name: str
    inputs: Dict[str, Any]
    expected_outputs: Dict[str, Any] = None
    expected_status: str = "completed"

@dataclass
class TestResult:
    """Result of running a test case."""
    test_name: str
    passed: bool
    execution: FeatureExecution
    errors: List[str]

class FeatureTester:
    """Test custom features before deployment."""
    
    def __init__(self):
        self.engine = FeatureEngine()
    
    async def run_tests(
        self,
        feature: FeatureDefinition,
        test_cases: List[TestCase],
        project_id: str = "test_project",
    ) -> List[TestResult]:
        """Run all test cases for a feature."""
        results = []
        
        for test in test_cases:
            result = await self._run_single_test(feature, test, project_id)
            results.append(result)
        
        return results
    
    async def _run_single_test(
        self,
        feature: FeatureDefinition,
        test: TestCase,
        project_id: str,
    ) -> TestResult:
        """Run a single test case."""
        errors = []
        
        # Execute feature
        execution = await self.engine.execute(
            feature_id=feature.id,
            project_id=project_id,
            inputs=test.inputs,
            context={"test_mode": True},
        )
        
        # Check status
        if execution.status != test.expected_status:
            errors.append(f"Expected status '{test.expected_status}', got '{execution.status}'")
        
        # Check outputs if specified
        if test.expected_outputs and execution.status == "completed":
            for key, expected in test.expected_outputs.items():
                actual = execution.outputs.get(key)
                if actual != expected:
                    errors.append(f"Output '{key}': expected {expected}, got {actual}")
        
        return TestResult(
            test_name=test.name,
            passed=len(errors) == 0,
            execution=execution,
            errors=errors,
        )
    
    def generate_test_cases(self, feature: FeatureDefinition) -> List[TestCase]:
        """Auto-generate basic test cases for a feature."""
        cases = []
        
        # Test 1: Missing required inputs
        cases.append(TestCase(
            name="missing_required_inputs",
            inputs={},
            expected_status="failed",
        ))
        
        # Test 2: Valid minimal inputs
        minimal_inputs = {}
        for inp in feature.inputs:
            if inp.required:
                minimal_inputs[inp.name] = self._generate_sample_value(inp)
        
        cases.append(TestCase(
            name="minimal_valid_inputs",
            inputs=minimal_inputs,
            expected_status="completed",
        ))
        
        return cases
    
    def _generate_sample_value(self, input_def) -> Any:
        """Generate a sample value for an input."""
        from .schema import InputType
        
        type_samples = {
            InputType.TEXT: "sample text",
            InputType.NUMBER: 100,
            InputType.DATE: "2026-01-01",
            InputType.BOOLEAN: True,
            InputType.SELECT: input_def.options[0] if input_def.options else "option1",
        }
        
        return type_samples.get(input_def.type, None)
```

---

## Success Criteria

### Phase Complete When:
1. Core feature library (10+ features) implemented and working
2. Feature Builder UI allows creating custom features
3. AI-assisted feature generation produces usable logic
4. Feature registry stores and versions features
5. Basic testing framework validates features

### Quality Gates:
- All core features have unit tests
- Custom features can be created without coding
- AI generation works for common patterns
- Features can chain (output → input)

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-13 | Initial phase doc created |
