# Phase 4B: Export Template Repo

**Status:** NOT STARTED  
**Total Estimated Hours:** 10-15  
**Dependencies:** Phase 4A (E2E Flow) substantially complete  
**Last Updated:** January 13, 2026

---

## Objective

Build a Carbone-based export infrastructure that transforms XLR8 analysis into professional, branded deliverables. Templates are versioned, customer-assignable, and support multiple output formats.

---

## Background

### Why Carbone?

| Option | Pros | Cons |
|--------|------|------|
| **Carbone** | Any format (docx, xlsx, pptx, pdf), uses LibreOffice, template-driven | Node.js, heavier runtime |
| python-docx-template | Pure Python, simple | docx only, separate PDF conversion |
| ReportLab | PDF native | Complex API, no Word/Excel |
| WeasyPrint | HTML → PDF | No native Word/Excel |

**Decision:** Carbone gives us the most flexibility for professional deliverables across formats.

### Target State

```
/data/export_library/
├── templates/
│   ├── global/                    # Available to all customers
│   │   ├── gap_analysis_v1.docx
│   │   ├── data_summary_v1.xlsx
│   │   └── executive_brief_v1.pptx
│   └── customer/                  # Customer-specific branding
│       ├── acme_corp/
│       │   └── branded_report_v1.docx
│       └── globex/
│           └── quarterly_review_v1.docx
├── rendered/                      # Temp output directory
└── metadata.json                  # Template registry
```

---

## Component Overview

| # | Component | Hours | Description |
|---|-----------|-------|-------------|
| 4B.1 | Template Storage Structure | 2-3 | Directory layout, versioning, metadata |
| 4B.2 | Carbone Integration | 3-4 | Node service, rendering pipeline |
| 4B.3 | Variable Mapping | 2-3 | SynthesizedAnswer → template placeholders |
| 4B.4 | Template Admin UI | 3-4 | Upload, preview, assign to customer |
| 4B.5 | Multi-Format Output | 1-2 | docx → PDF conversion, xlsx, pptx |

---

## Component 4B.1: Template Storage Structure

**Goal:** Organized, versioned template library with metadata.

### Directory Structure

```
/data/export_library/
├── templates/
│   ├── global/
│   │   ├── gap_analysis/
│   │   │   ├── v1/
│   │   │   │   ├── template.docx
│   │   │   │   └── preview.png
│   │   │   └── v2/
│   │   │       ├── template.docx
│   │   │       └── preview.png
│   │   ├── data_summary/
│   │   │   └── v1/
│   │   │       ├── template.xlsx
│   │   │       └── preview.png
│   │   └── executive_brief/
│   │       └── v1/
│   │           ├── template.pptx
│   │           └── preview.png
│   └── customer/
│       └── {customer_id}/
│           └── {template_name}/
│               └── v1/
│                   ├── template.docx
│                   └── preview.png
├── rendered/                      # Temporary outputs (auto-cleaned)
└── registry.json                  # Template metadata
```

### Registry Schema

```json
{
  "templates": [
    {
      "id": "gap_analysis_v2",
      "name": "Gap Analysis Report",
      "description": "Comprehensive gap analysis with recommendations",
      "scope": "global",
      "customer_id": null,
      "format": "docx",
      "version": 2,
      "path": "global/gap_analysis/v2/template.docx",
      "preview_path": "global/gap_analysis/v2/preview.png",
      "variables": ["project_name", "customer_name", "gaps", "recommendations", "data_tables"],
      "created_at": "2026-01-13T10:00:00Z",
      "created_by": "admin",
      "active": true
    }
  ],
  "customer_assignments": [
    {
      "customer_id": "acme_corp",
      "template_id": "gap_analysis_v2",
      "override_template_id": "acme_branded_v1"
    }
  ]
}
```

### Template Versioning Rules

```python
class TemplateVersioning:
    """
    Versioning rules:
    - New upload of same template → increment version
    - Never delete old versions (archive)
    - Customer can pin to specific version
    - Default: latest active version
    """
    
    def get_template(self, template_id: str, customer_id: str = None, version: int = None) -> Path:
        """
        Resolution order:
        1. Customer override (if exists)
        2. Specific version (if requested)
        3. Latest active version
        """
        # Check for customer override
        if customer_id:
            override = self._get_customer_override(customer_id, template_id)
            if override:
                return override.path
        
        # Get specific or latest version
        template = self._get_template(template_id, version)
        return template.path
```

---

## Component 4B.2: Carbone Integration

**Goal:** Reliable document rendering service.

### Carbone Service (Node.js)

```javascript
// services/carbone-service/index.js
const carbone = require('carbone');
const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs').promises;

const app = express();
app.use(express.json({ limit: '50mb' }));

const TEMPLATE_DIR = process.env.TEMPLATE_DIR || '/data/export_library/templates';
const RENDER_DIR = process.env.RENDER_DIR || '/data/export_library/rendered';

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'carbone' });
});

// Render document
app.post('/render', async (req, res) => {
  const { template_path, data, output_format } = req.body;
  
  try {
    const templateFullPath = path.join(TEMPLATE_DIR, template_path);
    
    // Verify template exists
    await fs.access(templateFullPath);
    
    // Generate unique output filename
    const outputName = `${Date.now()}_${path.basename(template_path, path.extname(template_path))}.${output_format || 'pdf'}`;
    const outputPath = path.join(RENDER_DIR, outputName);
    
    // Render with Carbone
    const options = {
      convertTo: output_format || 'pdf',
    };
    
    carbone.render(templateFullPath, data, options, async (err, result) => {
      if (err) {
        console.error('Carbone render error:', err);
        return res.status(500).json({ error: 'Render failed', details: err.message });
      }
      
      // Write output file
      await fs.writeFile(outputPath, result);
      
      // Return download URL
      res.json({
        success: true,
        output_path: outputName,
        download_url: `/download/${outputName}`,
      });
    });
    
  } catch (err) {
    console.error('Render error:', err);
    res.status(500).json({ error: err.message });
  }
});

// Download rendered file
app.get('/download/:filename', async (req, res) => {
  const filePath = path.join(RENDER_DIR, req.params.filename);
  
  try {
    await fs.access(filePath);
    res.download(filePath, async () => {
      // Clean up after download (optional - could use cron instead)
      // await fs.unlink(filePath);
    });
  } catch (err) {
    res.status(404).json({ error: 'File not found' });
  }
});

// List available templates
app.get('/templates', async (req, res) => {
  try {
    const registry = JSON.parse(
      await fs.readFile(path.join(TEMPLATE_DIR, '../registry.json'), 'utf8')
    );
    res.json(registry.templates.filter(t => t.active));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`Carbone service running on port ${PORT}`);
});
```

### Dockerfile for Carbone Service

```dockerfile
FROM node:18-slim

# Install LibreOffice for format conversion
RUN apt-get update && apt-get install -y \
    libreoffice-writer \
    libreoffice-calc \
    libreoffice-impress \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

ENV TEMPLATE_DIR=/data/export_library/templates
ENV RENDER_DIR=/data/export_library/rendered

EXPOSE 3001

CMD ["node", "index.js"]
```

### Python Client

```python
# backend/utils/export/carbone_client.py
import httpx
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class CarboneClient:
    """Client for Carbone rendering service."""
    
    def __init__(self, base_url: str = "http://localhost:3001"):
        self.base_url = base_url
        self.timeout = 60.0  # Document rendering can be slow
    
    async def health_check(self) -> bool:
        """Check if Carbone service is running."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/health", timeout=5.0)
                return resp.status_code == 200
        except Exception as e:
            logger.error(f"Carbone health check failed: {e}")
            return False
    
    async def render(
        self,
        template_path: str,
        data: Dict[str, Any],
        output_format: str = "pdf"
    ) -> Optional[bytes]:
        """
        Render a template with data.
        
        Args:
            template_path: Relative path within templates directory
            data: Dictionary of template variables
            output_format: pdf, docx, xlsx, etc.
        
        Returns:
            Rendered document bytes or None on error
        """
        try:
            async with httpx.AsyncClient() as client:
                # Request render
                resp = await client.post(
                    f"{self.base_url}/render",
                    json={
                        "template_path": template_path,
                        "data": data,
                        "output_format": output_format,
                    },
                    timeout=self.timeout
                )
                
                if resp.status_code != 200:
                    logger.error(f"Render failed: {resp.text}")
                    return None
                
                result = resp.json()
                
                # Download the rendered file
                download_resp = await client.get(
                    f"{self.base_url}{result['download_url']}",
                    timeout=self.timeout
                )
                
                if download_resp.status_code == 200:
                    return download_resp.content
                
                logger.error(f"Download failed: {download_resp.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Carbone render error: {e}")
            return None
    
    async def list_templates(self) -> list:
        """Get list of available templates."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/templates", timeout=10.0)
                if resp.status_code == 200:
                    return resp.json()
                return []
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return []
```

---

## Component 4B.3: Variable Mapping

**Goal:** Transform SynthesizedAnswer into template-ready data.

### Variable Mapper

```python
# backend/utils/export/variable_mapper.py
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from datetime import datetime

@dataclass
class ExportContext:
    """Context for export rendering."""
    project_name: str
    customer_name: str
    generated_at: datetime
    query: str
    
@dataclass
class TemplateData:
    """Mapped data ready for template."""
    data: Dict[str, Any]
    

class VariableMapper:
    """Map SynthesizedAnswer to template variables."""
    
    def map_gap_analysis(
        self,
        synthesis: 'SynthesizedAnswer',
        context: ExportContext
    ) -> TemplateData:
        """
        Map synthesis result to gap analysis template variables.
        
        Template expects:
        - {project_name}
        - {customer_name}
        - {generated_date}
        - {executive_summary}
        - {gaps[i].title}
        - {gaps[i].severity}
        - {gaps[i].description}
        - {gaps[i].recommendation}
        - {recommendations[i].text}
        - {data_tables[i].name}
        - {data_tables[i].rows[j].col1}
        """
        return TemplateData(data={
            "project_name": context.project_name,
            "customer_name": context.customer_name,
            "generated_date": context.generated_at.strftime("%B %d, %Y"),
            "query": context.query,
            "executive_summary": synthesis.response[:500] if synthesis.response else "",
            
            # Gap list - Carbone iterates with {d.gaps[i].field}
            "gaps": [
                {
                    "title": gap.get("title", ""),
                    "severity": gap.get("severity", "MEDIUM"),
                    "severity_color": self._severity_color(gap.get("severity")),
                    "description": gap.get("description", ""),
                    "recommendation": gap.get("recommendation", ""),
                    "affected_records": gap.get("affected_count", 0),
                }
                for gap in (synthesis.gaps or [])
            ],
            
            # Recommendations
            "recommendations": [
                {"text": r, "priority": i + 1}
                for i, r in enumerate(synthesis.recommendations or [])
            ],
            
            # Data tables - for embedding query results
            "data_tables": self._format_data_tables(synthesis.sql_results),
            
            # Citations
            "citations": [
                {
                    "source": c.get("source_document", ""),
                    "page": c.get("page_number", ""),
                    "excerpt": c.get("excerpt", "")[:200],
                }
                for c in (synthesis.citations or [])
            ],
            
            # Metadata
            "total_gaps": len(synthesis.gaps or []),
            "critical_gaps": len([g for g in (synthesis.gaps or []) if g.get("severity") == "CRITICAL"]),
            "data_source_count": len(synthesis.sql_results.tables_used) if synthesis.sql_results else 0,
        })
    
    def map_data_summary(
        self,
        synthesis: 'SynthesizedAnswer',
        context: ExportContext
    ) -> TemplateData:
        """Map to data summary Excel template."""
        return TemplateData(data={
            "project_name": context.project_name,
            "customer_name": context.customer_name,
            "generated_date": context.generated_at.strftime("%Y-%m-%d"),
            "query": context.query,
            
            # For Excel, flat row data works best
            "rows": synthesis.sql_results.data if synthesis.sql_results else [],
            "columns": synthesis.sql_results.columns if synthesis.sql_results else [],
            "row_count": synthesis.sql_results.row_count if synthesis.sql_results else 0,
            
            # Summary stats
            "summary": synthesis.response[:1000] if synthesis.response else "",
        })
    
    def map_executive_brief(
        self,
        synthesis: 'SynthesizedAnswer',
        context: ExportContext
    ) -> TemplateData:
        """Map to executive brief PowerPoint template."""
        return TemplateData(data={
            "project_name": context.project_name,
            "customer_name": context.customer_name,
            "generated_date": context.generated_at.strftime("%B %Y"),
            
            # Slide content
            "title": f"Analysis: {context.query[:50]}",
            "key_finding": synthesis.response[:300] if synthesis.response else "",
            "metrics": self._extract_metrics(synthesis),
            "top_gaps": (synthesis.gaps or [])[:3],
            "next_steps": (synthesis.recommendations or [])[:3],
        })
    
    def _severity_color(self, severity: str) -> str:
        """Return hex color for severity level."""
        return {
            "CRITICAL": "#dc2626",  # Red
            "HIGH": "#ea580c",      # Orange
            "MEDIUM": "#ca8a04",    # Yellow
            "LOW": "#16a34a",       # Green
        }.get(severity, "#6b7280")  # Gray default
    
    def _format_data_tables(self, sql_results) -> List[Dict]:
        """Format SQL results for template embedding."""
        if not sql_results or not sql_results.data:
            return []
        
        return [{
            "name": "Query Results",
            "columns": sql_results.columns,
            "rows": sql_results.data[:50],  # Limit for template
            "total_rows": sql_results.row_count,
            "truncated": sql_results.row_count > 50,
        }]
    
    def _extract_metrics(self, synthesis: 'SynthesizedAnswer') -> List[Dict]:
        """Extract key metrics for dashboard display."""
        metrics = []
        
        if synthesis.sql_results:
            metrics.append({
                "label": "Records Analyzed",
                "value": f"{synthesis.sql_results.row_count:,}",
            })
        
        if synthesis.gaps:
            metrics.append({
                "label": "Gaps Found",
                "value": str(len(synthesis.gaps)),
            })
        
        if synthesis.citations:
            metrics.append({
                "label": "Sources Referenced",
                "value": str(len(synthesis.citations)),
            })
        
        return metrics
```

---

## Component 4B.4: Template Admin UI

**Goal:** Upload, preview, and assign templates to customers.

### Template Management Page

```jsx
// pages/TemplateManagement.jsx
import { useState, useEffect } from 'react';
import { Upload, Eye, Trash2, Users } from 'lucide-react';

const TemplateManagement = () => {
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  
  useEffect(() => {
    loadTemplates();
  }, []);
  
  const loadTemplates = async () => {
    const resp = await fetch('/api/templates');
    setTemplates(await resp.json());
  };
  
  return (
    <div className="template-management">
      <header className="page-header">
        <h1>Export Templates</h1>
        <button className="primary" onClick={() => setUploadModalOpen(true)}>
          <Upload size={16} /> Upload Template
        </button>
      </header>
      
      <div className="template-grid">
        {templates.map(template => (
          <TemplateCard
            key={template.id}
            template={template}
            onPreview={() => setSelectedTemplate(template)}
            onAssign={() => openAssignModal(template)}
          />
        ))}
      </div>
      
      {uploadModalOpen && (
        <UploadTemplateModal
          onClose={() => setUploadModalOpen(false)}
          onSuccess={() => {
            setUploadModalOpen(false);
            loadTemplates();
          }}
        />
      )}
      
      {selectedTemplate && (
        <TemplatePreviewModal
          template={selectedTemplate}
          onClose={() => setSelectedTemplate(null)}
        />
      )}
    </div>
  );
};

const TemplateCard = ({ template, onPreview, onAssign }) => (
  <div className="template-card">
    <div className="template-preview">
      {template.preview_path ? (
        <img src={`/api/templates/preview/${template.id}`} alt={template.name} />
      ) : (
        <div className="no-preview">No preview</div>
      )}
    </div>
    
    <div className="template-info">
      <h3>{template.name}</h3>
      <p>{template.description}</p>
      <div className="template-meta">
        <span className="format">{template.format.toUpperCase()}</span>
        <span className="version">v{template.version}</span>
        <span className="scope">{template.scope}</span>
      </div>
    </div>
    
    <div className="template-actions">
      <button onClick={onPreview} title="Preview">
        <Eye size={16} />
      </button>
      <button onClick={onAssign} title="Assign to Customer">
        <Users size={16} />
      </button>
    </div>
  </div>
);

const UploadTemplateModal = ({ onClose, onSuccess }) => {
  const [file, setFile] = useState(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [scope, setScope] = useState('global');
  const [uploading, setUploading] = useState(false);
  
  const handleUpload = async () => {
    if (!file || !name) return;
    
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', name);
    formData.append('description', description);
    formData.append('scope', scope);
    
    try {
      const resp = await fetch('/api/templates/upload', {
        method: 'POST',
        body: formData,
      });
      
      if (resp.ok) {
        onSuccess();
      } else {
        alert('Upload failed');
      }
    } finally {
      setUploading(false);
    }
  };
  
  return (
    <div className="modal-overlay">
      <div className="modal">
        <h2>Upload Template</h2>
        
        <div className="form-group">
          <label>Template File</label>
          <input
            type="file"
            accept=".docx,.xlsx,.pptx"
            onChange={e => setFile(e.target.files[0])}
          />
          <small>Supported: .docx, .xlsx, .pptx</small>
        </div>
        
        <div className="form-group">
          <label>Name</label>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="Gap Analysis Report"
          />
        </div>
        
        <div className="form-group">
          <label>Description</label>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="Comprehensive gap analysis with recommendations"
          />
        </div>
        
        <div className="form-group">
          <label>Scope</label>
          <select value={scope} onChange={e => setScope(e.target.value)}>
            <option value="global">Global (all customers)</option>
            <option value="customer">Customer-specific</option>
          </select>
        </div>
        
        <div className="modal-actions">
          <button onClick={onClose}>Cancel</button>
          <button
            className="primary"
            onClick={handleUpload}
            disabled={!file || !name || uploading}
          >
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </div>
      </div>
    </div>
  );
};
```

### Backend API Endpoints

```python
# backend/routers/templates.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
import shutil
import json
from datetime import datetime

router = APIRouter(prefix="/api/templates", tags=["templates"])

TEMPLATE_DIR = Path("/data/export_library/templates")
REGISTRY_PATH = TEMPLATE_DIR.parent / "registry.json"

@router.get("")
async def list_templates():
    """List all active templates."""
    registry = _load_registry()
    return [t for t in registry["templates"] if t.get("active", True)]

@router.post("/upload")
async def upload_template(
    file: UploadFile = File(...),
    name: str = Form(...),
    description: str = Form(""),
    scope: str = Form("global"),
):
    """Upload a new template."""
    # Validate file type
    ext = Path(file.filename).suffix.lower()
    if ext not in [".docx", ".xlsx", ".pptx"]:
        raise HTTPException(400, "Unsupported file type")
    
    # Generate template ID and version
    template_id = name.lower().replace(" ", "_")
    registry = _load_registry()
    
    # Find existing versions
    existing = [t for t in registry["templates"] if t["id"].startswith(template_id)]
    version = len(existing) + 1
    
    # Create directory
    template_dir = TEMPLATE_DIR / scope / template_id / f"v{version}"
    template_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file
    template_path = template_dir / f"template{ext}"
    with open(template_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    # Add to registry
    template_entry = {
        "id": f"{template_id}_v{version}",
        "name": name,
        "description": description,
        "scope": scope,
        "format": ext[1:],  # Remove dot
        "version": version,
        "path": str(template_path.relative_to(TEMPLATE_DIR)),
        "variables": [],  # TODO: Extract from template
        "created_at": datetime.utcnow().isoformat(),
        "active": True,
    }
    
    registry["templates"].append(template_entry)
    _save_registry(registry)
    
    return template_entry

@router.post("/render/{template_id}")
async def render_template(template_id: str, data: dict):
    """Render a template with provided data."""
    from ..utils.export.carbone_client import CarboneClient
    
    registry = _load_registry()
    template = next((t for t in registry["templates"] if t["id"] == template_id), None)
    
    if not template:
        raise HTTPException(404, "Template not found")
    
    client = CarboneClient()
    result = await client.render(
        template_path=template["path"],
        data=data,
        output_format="pdf"
    )
    
    if not result:
        raise HTTPException(500, "Render failed")
    
    return Response(
        content=result,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={template_id}.pdf"}
    )

def _load_registry() -> dict:
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text())
    return {"templates": [], "customer_assignments": []}

def _save_registry(registry: dict):
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2))
```

---

## Component 4B.5: Multi-Format Output

**Goal:** Support docx, PDF, xlsx, pptx from same templates.

### Format Conversion Matrix

| Template Type | Direct Output | Convertible To |
|---------------|---------------|----------------|
| .docx | docx | PDF |
| .xlsx | xlsx | PDF, CSV |
| .pptx | pptx | PDF |

### Export Endpoint

```python
@router.post("/export")
async def export_analysis(
    synthesis_id: str,
    template_id: str,
    output_format: str = "pdf",
    customer_id: str = None,
):
    """
    Export a synthesis result using specified template.
    
    Args:
        synthesis_id: ID of stored synthesis result
        template_id: Template to use
        output_format: pdf, docx, xlsx
        customer_id: Optional customer for branded template
    """
    # Load synthesis result
    synthesis = await get_synthesis(synthesis_id)
    if not synthesis:
        raise HTTPException(404, "Synthesis not found")
    
    # Get template (with customer override if applicable)
    template = template_service.get_template(
        template_id, 
        customer_id=customer_id
    )
    
    # Map variables
    mapper = VariableMapper()
    template_data = mapper.map_for_template(synthesis, template.type)
    
    # Render
    client = CarboneClient()
    result = await client.render(
        template_path=template.path,
        data=template_data.data,
        output_format=output_format
    )
    
    # Return file
    content_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    
    return Response(
        content=result,
        media_type=content_types.get(output_format, "application/octet-stream"),
        headers={
            "Content-Disposition": f"attachment; filename=export.{output_format}"
        }
    )
```

---

## Testing Strategy

### Template Rendering
- [ ] docx template renders with all variables
- [ ] xlsx template handles row iteration
- [ ] pptx template populates slides
- [ ] PDF conversion produces readable output

### Variable Mapping
- [ ] All SynthesizedAnswer fields map correctly
- [ ] Empty/null fields don't break templates
- [ ] Large datasets truncate gracefully

### Admin UI
- [ ] Upload new template
- [ ] Preview existing template
- [ ] Assign to customer
- [ ] Version increment works

---

## Success Criteria

### Phase Complete When:
1. Can upload docx/xlsx/pptx templates via Admin UI
2. Templates render with real synthesis data
3. PDF export produces professional output
4. Customer-specific branding works
5. Version history maintained

### Quality Gates:
- Rendered documents open correctly in target apps
- No broken template variables
- Export completes in <10 seconds
- Templates versioned (no overwrites)

---

## Starter Templates to Create

| Template | Format | Purpose |
|----------|--------|---------|
| Gap Analysis Report | docx | Detailed gap findings with recommendations |
| Data Summary | xlsx | Query results with summary stats |
| Executive Brief | pptx | 3-5 slide overview for leadership |
| Compliance Check | docx | Regulatory compliance status |

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-13 | Initial phase doc created |
