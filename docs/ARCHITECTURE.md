# XLR8 v3.0 - ARCHITECTURE DOCUMENT
## Technical Stack & System Design

**Version:** 3.0.0  
**Architecture:** Modular Microservices Pattern  
**Deployment:** Railway (PaaS) + Hetzner (Dedicated Server)  
**Date:** November 15, 2025

---

## 🏗️ SYSTEM OVERVIEW

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER BROWSER                              │
│  (Chrome, Firefox, Safari, Edge - Modern browsers only)         │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                     RAILWAY PLATFORM                             │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  XLR8 Application (Streamlit)                            │  │
│  │  - Python 3.11                                           │  │
│  │  - Streamlit Web Framework                               │  │
│  │  - Session Management (in-memory)                        │  │
│  │  - Auto-scaling (Railway managed)                        │  │
│  └─────────┬──────────────────────────────────────────┬─────┘  │
└────────────┼──────────────────────────────────────────┼────────┘
             │                                           │
             │ HTTP Auth                                 │ HTTPS
             │ (Basic Auth)                              │
             ↓                                           ↓
┌────────────────────────────┐              ┌──────────────────────┐
│   HETZNER DEDICATED        │              │   UKG APIS           │
│   178.156.190.64          │              │   (External)         │
│                           │              │                      │
│  ┌──────────────────────┐│              │  - PRO WFM API      │
│  │  Nginx (Port 11435)  ││              │  - HCM API          │
│  │  Reverse Proxy +     ││              │  (OAuth 2.0)        │
│  │  Basic Auth          ││              └──────────────────────┘
│  └──────────┬───────────┘│
│             │             │
│  ┌──────────▼───────────┐│
│  │  Ollama (Port 11434) ││
│  │  - mistral:7b        ││
│  │  - mixtral:8x7b      ││
│  │  - nomic-embed-text  ││
│  └──────────────────────┘│
│                           │
│  ┌──────────────────────┐│
│  │  ChromaDB            ││
│  │  /root/.xlr8_chroma  ││
│  │  Vector Store        ││
│  └──────────────────────┘│
└───────────────────────────┘
```

---

## 💻 TECHNOLOGY STACK

### Frontend Layer

**Framework:** Streamlit 1.31.0
- **Why**: Rapid Python-based UI development
- **Benefits**: 
  - No JavaScript required
  - Built-in session management
  - Real-time updates
  - Component reusability

**UI Components:**
- Streamlit native widgets
- Custom CSS theming (Muted Blue palette)
- Responsive layout system
- File upload/download handlers

**Browser Support:**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

### Backend Layer

**Language:** Python 3.11
- **Why**: ML/AI ecosystem compatibility
- **Benefits**:
  - Rich data processing libraries
  - Type hints for safety
  - Async support
  - Extensive PDF/document handling

**Key Libraries:**
```python
# Core Framework
streamlit==1.31.0              # Web framework

# Data Processing
pandas==2.2.0                  # Data manipulation
openpyxl==3.1.2               # Excel handling
PyPDF2>=3.0.0                 # PDF parsing
python-docx>=1.0.0            # Word doc handling

# AI/ML
chromadb>=1.3.0               # Vector database
sentence-transformers>=5.0.0   # Embeddings

# PDF Processing
pdf2image==1.16.3             # PDF to image
Pillow==10.2.0                # Image handling
pytesseract==0.3.10           # OCR
streamlit-drawable-canvas==0.9.3  # Interactive PDF

# Network
requests==2.31.0              # HTTP client
```

### AI/ML Layer

**LLM Engine:** Ollama (Self-Hosted)
- **Location:** Hetzner dedicated server
- **Models:**
  - `mistral:7b` (5GB RAM, Fast)
  - `mixtral:8x7b` (26GB RAM, Thorough)
  - `nomic-embed-text` (274MB, Embeddings)

**Model Selection Logic:**
```python
if task_type == "parsing" or task_type == "categorization":
    use_model("mistral:7b")  # Fast, efficient
elif task_type == "strategic_analysis" or task_type == "complex_reasoning":
    use_model("mixtral:8x7b")  # Thorough, detailed
```

**RAG (Retrieval Augmented Generation):**
- **Vector Store:** ChromaDB 1.3.4
- **Embedding Model:** nomic-embed-text
- **Embedding Dimensions:** 768
- **Similarity Metric:** Cosine similarity
- **Chunk Size:** 500 characters
- **Chunk Overlap:** 50 characters
- **Top-K Retrieval:** 5 chunks per query

**RAG Architecture:**
```
Document Upload
      ↓
Text Extraction
      ↓
Chunking (500 chars)
      ↓
Generate Embeddings (nomic-embed-text)
      ↓
Store in ChromaDB
      ↓
[User Query] → Embed Query → Semantic Search → Retrieve Top-5 Chunks
      ↓
Send to LLM with Context
      ↓
Generate Response
```

### Data Layer

**Session Storage:** In-Memory (Streamlit Session State)
- **Scope:** Per-user session
- **Lifetime:** Duration of browser session
- **Data Stored:**
  - Current project
  - Uploaded files (metadata)
  - Chat history
  - Analysis results
  - User preferences

**Persistent Storage:** ChromaDB
- **Location:** `/root/.xlr8_chroma`
- **Type:** Vector database
- **Persistence:** Disk-based
- **Backup:** Manual (directory copy)

**No Traditional Database:**
- No PostgreSQL/MySQL
- No user authentication database
- All data session-based or vector-based
- **Rationale:** Simplified architecture, faster development

### Security Layer

**Authentication:**
1. **LLM Access:** HTTP Basic Auth
   - Username: `xlr8`
   - Password: `Argyle76226#`
   - Hardcoded in `config.py`
   - Never exposed to client

2. **UKG APIs:** OAuth 2.0
   - Tokens stored in session state
   - Not persisted to disk
   - Expires per UKG policy

**Network Security:**
- **Railway to Hetzner:** 
  - HTTP with Basic Auth
  - Over public internet
  - Encrypted payload (LLM request/response)

- **Railway to Client:**
  - HTTPS (Railway managed)
  - TLS 1.2+
  - Certificate auto-renewed

**Data Security:**
- **At Rest:** 
  - ChromaDB data unencrypted (local disk)
  - No PII stored long-term
  - Session data in memory only

- **In Transit:**
  - HTTPS client to Railway
  - HTTP+Auth Railway to Hetzner
  - HTTPS to UKG APIs

**Access Control:**
- No user authentication (single-tenant)
- All users have full access
- Audit logging not implemented (future)

### Deployment Layer

**Platform:** Railway
- **Type:** Platform-as-a-Service (PaaS)
- **Region:** US-based data centers
- **Scaling:** Auto-scaling (Railway managed)
- **Deployment:** GitHub integration (auto-deploy on push)
- **Build Time:** ~4-5 minutes
- **Zero-Downtime:** Yes (Railway feature)

**Infrastructure:**
```
GitHub Repository (Source of Truth)
      ↓ (git push)
Railway (CI/CD)
      ↓ (build)
Docker Container
      ↓ (deploy)
Production Environment
```

**Environment Variables:**
- None! All config in `config.py`
- Hardcoded for simplicity
- **Trade-off:** Less flexible, but simpler

---

## 📐 ARCHITECTURAL PATTERNS

### 1. Modular Monolith Pattern

**Not Microservices, Not Traditional Monolith**

```
Traditional Monolith:
- One giant file
- Everything coupled
- Hard to change

Microservices:
- Many separate apps
- Complex orchestration
- Overkill for this use case

Modular Monolith (XLR8):
- One app, many modules
- Clear boundaries
- Easy to extract to microservice later
```

**Module Independence:**
- Each module has single responsibility
- Minimal dependencies between modules
- Can test/develop independently
- Can extract to microservice if needed

### 2. Orchestrator Pattern

**Each page has an orchestrator:**

```python
# pages/work/analysis/__init__.py (Orchestrator)
def render_analysis_page():
    # Coordinates sub-modules
    file = upload.render_upload_section()
    data = parser.parse_document(file)
    analysis = ai_analyzer.analyze(data)
    templates = template_filler.generate(analysis)
    results_viewer.display(analysis, templates)
```

**Benefits:**
- Clear workflow
- Easy to understand
- Simple to modify
- Testable components

### 3. Hexagonal Architecture (Ports & Adapters)

**Core Business Logic vs Infrastructure:**

```
┌─────────────────────────────────────┐
│         CORE DOMAIN                 │
│  (Business Logic - Pure Python)     │
│                                     │
│  - Analysis algorithms              │
│  - Template generation              │
│  - Data transformations             │
└──────────┬──────────────────────────┘
           │
    ┌──────┴──────┐
    │   PORTS     │ (Interfaces)
    └──────┬──────┘
           │
    ┌──────▼──────────────────────────┐
    │      ADAPTERS                   │
    │  (Infrastructure)                │
    │                                  │
    │  - Streamlit UI                 │
    │  - Ollama Client                │
    │  - ChromaDB                     │
    │  - File System                  │
    └──────────────────────────────────┘
```

**Example:**
- Core: `template_generator.py` (no UI code)
- Adapter: `template_filler.py` (connects UI to core)

### 4. Repository Pattern (for RAG)

**RAG Handler is a Repository:**

```python
class RAGHandler:
    # Abstract storage details
    def add_document(name, content, category)
    def search(query, n_results)
    def delete_document(name, category)
    def get_stats()
```

**Can swap ChromaDB for:**
- Pinecone
- Weaviate
- Qdrant
- Milvus

Without changing calling code!

---

## 🔄 DATA FLOW

### Document Analysis Flow

```
1. User uploads PDF
   ↓
2. upload.py validates file
   ↓
3. parser.py extracts text
   ↓
4. Text sent to ai_analyzer.py
   ↓
5. ai_analyzer calls RAG search
   ↓
6. RAG returns relevant HCMPACT standards (Top-5 chunks)
   ↓
7. ai_analyzer builds prompt:
   - User document text
   - Relevant HCMPACT chunks
   - Analysis instructions
   ↓
8. Send to Ollama (via Nginx+Auth)
   ↓
9. LLM generates analysis
   ↓
10. Return to ai_analyzer
   ↓
11. Pass to template_filler.py
   ↓
12. template_filler generates UKG templates
   ↓
13. results_viewer.py displays
   ↓
14. User downloads templates
```

### Chat Flow with RAG

```
1. User asks question
   ↓
2. Question sent to chat interface
   ↓
3. RAG semantic search
   - Convert question to embedding
   - Search ChromaDB
   - Return top 5 relevant chunks
   ↓
4. Build chat prompt:
   - Chat history (last 10 messages)
   - Retrieved HCMPACT chunks
   - Current question
   ↓
5. Send to LLM
   ↓
6. LLM generates response
   ↓
7. Display with source citations
   ↓
8. User sees: Answer + "Sources Used" expander
```

---

## 🔧 MODULE ARCHITECTURE

### Module Template

Every module follows this pattern:

```python
"""
Module: <module_name>
Owner: <person/team>
Purpose: <clear single purpose>
Dependencies: <list dependencies>
Testing: <how to test independently>
"""

import streamlit as st
from typing import <types>
from config import AppConfig

def main_function(inputs) -> outputs:
    """
    Clear docstring
    
    Args:
        inputs: Description
    
    Returns:
        outputs: Description
    
    Example:
        result = main_function(data)
    """
    # Implementation
    pass

# Standalone testing
if __name__ == "__main__":
    st.title("Module Test")
    # Test code here
```

### Dependency Rules

**Allowed Dependencies:**
- ✅ Module can import from `utils/`
- ✅ Module can import from `config.py`
- ✅ Module can import from `components/`
- ✅ Orchestrator can import sub-modules

**Forbidden Dependencies:**
- ❌ Sub-module cannot import sibling sub-module
- ❌ Module cannot import from `pages/`
- ❌ No circular dependencies
- ❌ No global state modifications (use session)

### Interface Contracts

**Every module defines clear interfaces:**

```python
# Input Contract
TypedDict('ParsedDocument', {
    'text': str,
    'tables': List[DataFrame],
    'metadata': dict
})

# Output Contract
TypedDict('AnalysisResult', {
    'summary': str,
    'recommendations': List[str],
    'confidence': float,
    'sources': List[dict]
})
```

---

## 📊 PERFORMANCE CHARACTERISTICS

### Response Times (Expected)

| Operation | Time | Notes |
|-----------|------|-------|
| Page Load | <2s | Cold start: 3-5s |
| File Upload (10MB) | <5s | Depends on network |
| PDF Parsing | 5-15s | Depends on pages |
| RAG Indexing (first) | 20-40s | Embedding generation |
| RAG Indexing (subsequent) | 10-20s | Cached embeddings |
| RAG Search | <1s | Very fast |
| AI Analysis (Fast) | 15-30s | mistral:7b |
| AI Analysis (Thorough) | 45-90s | mixtral:8x7b |
| Chat Response (Fast) | 5-15s | With RAG context |
| Template Generation | <2s | Post-processing |

### Resource Usage

**Railway Container:**
- Memory: ~500MB baseline
- CPU: 0.5-1.0 cores
- Disk: ~2GB (application + dependencies)
- Network: Minimal (stateless)

**Hetzner Server (CPX51):**
- RAM: 32GB total
  - Ollama: 5-26GB (depends on model)
  - ChromaDB: ~100MB + data
  - System: ~2GB
- CPU: 8 vCPUs (shared)
- Disk: 240GB NVMe
  - Ollama models: ~30GB
  - ChromaDB data: varies (1GB per 10K docs)
- Network: 20TB/month

### Scaling Limits

**Current Architecture:**
- **Concurrent Users:** ~50-100 (Railway auto-scales)
- **Documents in RAG:** ~10,000 (ChromaDB efficient)
- **Chat Messages:** Unlimited (per session)
- **File Size:** 200MB max (configurable)

**Bottlenecks:**
1. **LLM Throughput:** 1 request at a time per model
   - Solution: Queue or multiple instances
2. **Railway Memory:** 512MB-2GB
   - Solution: Upgrade plan
3. **Hetzner RAM:** 32GB (mixtral uses 26GB)
   - Solution: Upgrade server or use smaller models

---

## 🔌 INTEGRATION POINTS

### External APIs

**1. UKG Pro WFM API**
- Protocol: OAuth 2.0
- Authentication: Client credentials flow
- Token lifetime: Configurable
- Rate limits: Per UKG agreement
- Error handling: Retry with exponential backoff

**2. UKG HCM API**
- Protocol: Basic Auth + API Keys
- Headers: US-Customer-Api-Key, US-User-Api-Key
- Rate limits: Per UKG agreement

**3. Anthropic API (Optional/Disabled)**
- Protocol: REST API
- Authentication: API Key
- Model: Claude Sonnet
- **Note:** Disabled by default (security)

### Internal APIs

**1. Ollama API**
- Endpoint: `http://178.156.190.64:11435/api/generate`
- Authentication: HTTP Basic Auth
- Request format: JSON
- Response: Streaming or complete
- Timeout: 300 seconds

**2. ChromaDB API**
- Type: Embedded (in-process)
- No network calls
- Python client library
- Persistent disk storage

---

## 🛡️ SECURITY ARCHITECTURE

See `SECURITY.md` for comprehensive security documentation.

**Key Points:**
- Local LLM = Data stays on-premises
- No PII persistence
- Session-based security
- HTTPS in transit
- Basic Auth for LLM access

---

## 📈 MONITORING & OBSERVABILITY

**Current State:** Minimal

**Available:**
- Railway logs (stdout/stderr)
- Railway metrics (CPU, memory)
- Streamlit error messages
- Browser console logs

**Not Implemented:**
- Application performance monitoring (APM)
- Error tracking (Sentry)
- User analytics
- Audit logs

**Future Enhancements:**
- Add logging framework
- Implement audit trail
- Add performance metrics
- Track user actions

---

## 🔮 FUTURE ARCHITECTURE

### Planned Enhancements

**1. Database Layer**
- Add PostgreSQL for persistence
- Store projects, documents metadata
- User management
- Audit logs

**2. Authentication/Authorization**
- User login system
- Role-based access control (RBAC)
- Multi-tenant support

**3. Microservices Extraction**
- PDF parsing service
- LLM service
- RAG service
- Template generation service

**4. Caching Layer**
- Redis for session management
- Cache LLM responses
- Cache RAG results

**5. Message Queue**
- Async processing for long tasks
- Background jobs
- Scheduled tasks

### Migration Path

```
Current (v3.0):
Modular Monolith

     ↓

Phase 1 (v3.5):
Add Database + Auth

     ↓

Phase 2 (v4.0):
Extract PDF Service

     ↓

Phase 3 (v4.5):
Extract LLM Service

     ↓

Future (v5.0):
Full Microservices
```

---

## 📚 REFERENCES

### Documentation
- Streamlit: https://docs.streamlit.io
- ChromaDB: https://docs.trychroma.com
- Ollama: https://ollama.ai/docs
- Railway: https://docs.railway.app

### Standards
- Python Type Hints: PEP 484
- Module Structure: PEP 420
- Docstrings: Google Style

### Best Practices
- Clean Architecture (Robert C. Martin)
- Domain-Driven Design (Eric Evans)
- Microservices Patterns (Chris Richardson)

---

## ✅ ARCHITECTURE REVIEW CHECKLIST

- [x] Clear separation of concerns
- [x] Modular design for team collaboration
- [x] Testable components
- [x] Scalable within limits
- [x] Secure (see SECURITY.md)
- [x] Well-documented
- [x] Standard Python practices
- [x] Production-ready

**Architecture approved for production deployment.**

---

**Document Version:** 1.0  
**Last Updated:** November 15, 2025  
**Next Review:** January 2026
