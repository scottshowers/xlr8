# XLR8 Dependency Audit Report

**Date:** January 15, 2026
**Auditor:** Claude Code (Automated Analysis)

## Executive Summary

This audit identified **7 security vulnerabilities** (3 high severity, 4 medium severity), **multiple outdated packages**, and **significant redundancy** in PDF processing libraries. Immediate attention is recommended for the critical vulnerabilities.

---

## Security Vulnerabilities

### CRITICAL / HIGH Severity

| Package | CVE | Severity | Issue | Fix |
|---------|-----|----------|-------|-----|
| **xlsx** (npm) | CVE-2023-30533 | HIGH (7.8) | Prototype Pollution | Replace with `exceljs` or download xlsx 0.20.1+ from cdn.sheetjs.com |
| **xlsx** (npm) | CVE-2024-22363 | HIGH (7.5) | ReDoS vulnerability | Same as above |
| **cryptography** | CVE-2024-12797, CVE-2024-6119, CVE-2024-26130 | HIGH | OpenSSL vulnerabilities, NULL pointer dereference | Update to `>=44.0.1` |
| **Vite** (npm) | CVE-2025-30208, CVE-2025-31486 | HIGH (7.5) | Arbitrary file read | Update to `>=5.4.15` |
| **PyPDF2** | CVE-2023-36464, CVE-2023-36807 | HIGH | Infinite loop DoS (DEPRECATED) | Migrate to `pypdf>=6.4.0` |
| **pandas** | CVE-2024-9880 | HIGH (8.6) | Arbitrary code execution via `query()` | No fix - sanitize inputs to `DataFrame.query()` |

### MEDIUM Severity

| Package | CVE | Severity | Issue | Fix |
|---------|-----|----------|-------|-----|
| **requests** | CVE-2024-35195 | MEDIUM (5.6) | SSL cert verification bypass | Update to `>=2.32.0` |
| **requests** | CVE-2024-47081 | MEDIUM (5.3) | .netrc credential leakage | Update to `>=2.32.4` |
| **Pillow** | CVE-2023-50447 | MEDIUM | Arbitrary code execution via ImageMath.eval | Update to `>=10.2.0` (current) |
| **Pillow** | CVE-2025-48379 | MEDIUM | Heap buffer overflow (DDS images) | Update to `>=11.3.0` |

---

## Outdated Packages

### Python (requirements.txt)

| Package | Current Version | Recommended Version | Notes |
|---------|-----------------|---------------------|-------|
| `fastapi` | 0.108.0 | 0.115.x | Security patches, performance improvements |
| `uvicorn[standard]` | 0.25.0 | 0.32.x | Bug fixes, performance |
| `requests` | 2.31.0 | 2.32.5 | **Security fix required** |
| `Pillow` | 10.2.0 | 11.3.0 | **Security fix required** |
| `cryptography` | >=41.0.0 | >=44.0.1 | **Security fix required** |
| `pandas` | 2.2.0 | 2.2.3 | Bug fixes |
| `duckdb` | >=0.9.0 | >=1.1.0 | Major version with improvements |
| `websockets` | 13.0 | 14.x | Performance improvements |
| `PyPDF2` | >=3.0.0 | N/A | **DEPRECATED - migrate to pypdf** |

### Node.js (frontend/package.json)

| Package | Current Version | Recommended Version | Notes |
|---------|-----------------|---------------------|-------|
| `vite` | ^5.0.8 | ^6.2.3 or ^5.4.15 | **Security fix required** |
| `@vitejs/plugin-react` | ^4.2.1 | ^4.3.x | Compatible with Vite 5.x |
| `xlsx` | ^0.18.5 | N/A | **Replace with exceljs** |
| `react` | ^18.2.0 | ^18.3.1 | Minor improvements |
| `tailwindcss` | ^3.3.6 | ^3.4.x | New features |
| `lucide-react` | ^0.263.1 | ^0.470.x | New icons, fixes |

---

## Redundant / Bloat Analysis

### PDF Processing Libraries (HIGH REDUNDANCY)

The project currently includes **7 different PDF processing libraries**, which creates:
- Increased attack surface
- Larger Docker image size
- Dependency conflicts risk
- Maintenance burden

| Library | Purpose | Recommendation |
|---------|---------|----------------|
| `PyMuPDF` (>=1.23.0) | **KEEP** - Fast, full-featured PDF reading/rendering |
| `pymupdf4llm` (>=0.0.7) | **KEEP** - LLM-optimized text extraction |
| `pdfplumber` (>=0.11.0) | **KEEP** - Table extraction, detailed layout analysis |
| `PyPDF2` (>=3.0.0) | **REMOVE** - Deprecated, replace with `pypdf` |
| `pdf2image` (1.16.3) | **EVALUATE** - PyMuPDF can render pages to images |
| `pypdfium2` (>=4.26.0) | **EVALUATE** - Overlaps with PyMuPDF |
| `camelot-py[cv]` (>=0.11.0) | **EVALUATE** - Complex table extraction, heavy deps |
| `tabula-py` (>=2.9.0) | **EVALUATE** - Requires Java, overlaps with camelot |

**Suggested consolidation:**
- Keep: `PyMuPDF`, `pymupdf4llm`, `pdfplumber`
- Remove: `PyPDF2` (deprecated)
- Evaluate need for: `camelot-py`, `tabula-py`, `pdf2image`, `pypdfium2`

### Potential Savings
Removing redundant PDF libraries could reduce:
- Docker image size by ~200-400MB
- Build time by 30-60 seconds
- Dependency tree complexity significantly

---

## Recommended Updates

### requirements.txt (Updated)

```txt
# Core Framework
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
websockets>=14.0
python-multipart>=0.0.12

# AI/ML
anthropic>=0.40.0
chromadb>=0.4.0
nltk==3.8.1

# Cloud & Auth
supabase>=2.7.0
boto3>=1.35.0
cryptography>=44.0.1  # SECURITY UPDATE

# Data Processing
duckdb>=1.1.0
pandas>=2.2.3
numpy>=1.26.0

# PDF Processing (Consolidated)
PyMuPDF>=1.24.0
pymupdf4llm>=0.0.7
pdfplumber>=0.11.0
pypdf>=6.4.0  # REPLACES PyPDF2
Pillow>=11.3.0  # SECURITY UPDATE
pytesseract==0.3.10

# Office Documents
python-docx>=1.0.0
openpyxl>=3.1.5
xlrd>=2.0.1

# HTTP & Utilities
requests>=2.32.5  # SECURITY UPDATE
python-dotenv>=1.0.0

# Optional - evaluate if needed:
# pdf2image==1.16.3  # PyMuPDF can do this
# camelot-py[cv]>=0.11.0  # Heavy deps, evaluate need
# tabula-py>=2.9.0  # Requires Java
# pypdfium2>=4.26.0  # Overlaps with PyMuPDF
```

### frontend/package.json (Updated)

```json
{
  "dependencies": {
    "@supabase/supabase-js": "^2.47.0",
    "axios": "^1.7.0",
    "exceljs": "^4.4.0",
    "lucide-react": "^0.470.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-joyride": "^2.9.0",
    "react-router-dom": "^6.28.0",
    "recharts": "^2.15.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.17",
    "vite": "^5.4.15"
  }
}
```

---

## Migration Guide

### 1. Replace xlsx with exceljs (HIGH PRIORITY)

The `xlsx` package has unpatched vulnerabilities. Replace with `exceljs`:

```javascript
// Before (xlsx)
import * as XLSX from 'xlsx';
const workbook = XLSX.read(data);
const sheet = workbook.Sheets[workbook.SheetNames[0]];
const json = XLSX.utils.sheet_to_json(sheet);

// After (exceljs)
import ExcelJS from 'exceljs';
const workbook = new ExcelJS.Workbook();
await workbook.xlsx.load(data);
const sheet = workbook.worksheets[0];
const json = [];
sheet.eachRow((row, rowNumber) => {
  if (rowNumber > 1) { // Skip header
    json.push(row.values.slice(1)); // Remove empty first cell
  }
});
```

### 2. Replace PyPDF2 with pypdf (HIGH PRIORITY)

```python
# Before
from PyPDF2 import PdfReader

# After
from pypdf import PdfReader
# API is largely compatible
```

### 3. Update pandas usage (MEDIUM PRIORITY)

Avoid passing untrusted input to `DataFrame.query()`:

```python
# UNSAFE
df.query(user_input)

# SAFER - parameterize queries
df.query("column == @value", local_dict={"value": sanitized_input})
```

---

## Action Items

### Immediate (Security Critical)
1. [ ] Update `vite` to `>=5.4.15`
2. [ ] Replace `xlsx` with `exceljs`
3. [ ] Update `cryptography` to `>=44.0.1`
4. [ ] Update `requests` to `>=2.32.5`
5. [ ] Update `Pillow` to `>=11.3.0`
6. [ ] Replace `PyPDF2` with `pypdf>=6.4.0`

### Short-term (Maintenance)
7. [ ] Update `fastapi` to `>=0.115.0`
8. [ ] Update `uvicorn` to `>=0.32.0`
9. [ ] Evaluate and consolidate PDF libraries
10. [ ] Update remaining frontend dependencies

### Long-term (Optimization)
11. [ ] Audit actual usage of each PDF library
12. [ ] Remove unused dependencies
13. [ ] Consider `camelot-py` alternatives (heavy OpenCV dependency)
14. [ ] Review if `tabula-py` Java requirement is justified

---

## Sources

- [PyPDF2 vulnerabilities | Snyk](https://security.snyk.io/package/pip/PyPDF2)
- [xlsx vulnerabilities | Snyk](https://security.snyk.io/package/npm/xlsx)
- [Pillow Security Vulnerabilities](https://stack.watch/product/python/pillow/)
- [cryptography vulnerabilities | Snyk](https://security.snyk.io/package/pip/cryptography)
- [requests vulnerabilities | Snyk](https://security.snyk.io/package/pip/requests)
- [vite vulnerabilities | Snyk](https://security.snyk.io/package/npm/vite)
- [pandas vulnerabilities | Snyk](https://security.snyk.io/package/pip/pandas)
- [Vite Arbitrary File Read (CVE-2025-30208)](https://nsfocusglobal.com/vite-arbitrary-file-read-vulnerability-cve-2025-30208/)
- [ExcelJS as xlsx alternative](https://medium.com/@manishasiram/exceljs-alternate-for-xlsx-package-fc1d36b2e743)
