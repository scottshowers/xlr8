# XLR8 Dependency Security Audit Report

**Date:** January 15, 2026
**Auditor:** Claude Code (Automated Analysis)
**Scope:** Python (requirements.txt) and Node.js (package.json) dependencies

---

## Executive Summary

This comprehensive audit identified **14 security vulnerabilities** across Python and Node.js dependencies:
- **4 Critical/High severity** requiring immediate action
- **7 Medium severity** requiring prompt attention
- **3 Low severity** for awareness

Additionally, the project has **significantly outdated packages** and **redundant PDF processing libraries** that increase attack surface and bloat.

**Risk Level: HIGH** - Immediate remediation recommended.

---

## Security Vulnerabilities

### CRITICAL / HIGH Severity (Immediate Action Required)

| Package | CVE | CVSS | Issue | Affected Version | Fix |
|---------|-----|------|-------|------------------|-----|
| **axios** (npm) | CVE-2025-27152 | HIGH | SSRF & credential leakage via absolute URLs | <1.8.2 | Update to `>=1.8.2` |
| **axios** (npm) | CVE-2025-58754 | HIGH | DoS via data: URL causing unbounded memory allocation | <1.12.0 | Update to `>=1.12.0` |
| **xlsx** (npm) | CVE-2023-30533 | 7.8 | Prototype Pollution when reading crafted files | <=0.18.5 on npm | Replace with `exceljs` |
| **xlsx** (npm) | CVE-2024-22363 | 7.5 | ReDoS vulnerability | <=0.20.1 | Replace with `exceljs` |
| **vite** (npm) | CVE-2025-30208 | 7.5 | Arbitrary file read via query strings | <5.4.15 | Update to `>=5.4.18` |
| **vite** (npm) | CVE-2025-31486 | 7.5 | Arbitrary file read via URL manipulation | <5.4.15 | Update to `>=5.4.18` |
| **vite** (npm) | CVE-2025-32395 | 6.0 | Information exposure via `#` in request-targets | <5.4.18 | Update to `>=5.4.18` |
| **python-multipart** | CVE-2024-53981 | 7.5 | DoS via boundary parsing (stalls event loop) | <0.0.18 | Update to `>=0.0.18` |
| **python-multipart** | CVE-2024-24762 | 7.5 | ReDoS via Content-Type header | <0.0.7 | Update to `>=0.0.18` |
| **cryptography** | CVE-2024-12797 | HIGH | Vulnerable OpenSSL in wheels | <44.0.1 | Update to `>=44.0.1` |
| **cryptography** | CVE-2024-6119 | HIGH | OpenSSL type confusion | <43.0.1 | Update to `>=44.0.1` |
| **PyPDF2** | CVE-2023-36464 | HIGH | Infinite loop DoS | All versions | **DEPRECATED** - Use `pypdf>=6.4.0` |
| **duckdb** | CVE-2024-41672 | MEDIUM | Information exposure via sniff_csv | <1.1.0 | Update to `>=1.1.0` |

### MEDIUM Severity

| Package | CVE | CVSS | Issue | Affected Version | Fix |
|---------|-----|------|-------|------------------|-----|
| **requests** | CVE-2024-35195 | 5.6 | SSL cert verification bypass in sessions | <2.32.2 | Update to `>=2.32.5` |
| **requests** | CVE-2024-47081 | 5.3 | .netrc credential leakage to third parties | <2.32.4 | Update to `>=2.32.5` |
| **Pillow** | CVE-2025-48379 | MEDIUM | Heap buffer overflow in DDS encoding | 11.2.0-11.2.x | Update to `>=11.3.0` |
| **Pillow** | CVE-2023-50447 | MEDIUM | Arbitrary code execution via ImageMath.eval | <10.2.0 | Current version OK |
| **fastapi** | CVE-2024-24762 | 7.5 | ReDoS via python-multipart dependency | <0.109.1 | Update to `>=0.109.1` |
| **@supabase/auth-js** | CVE-2025-48370 | MEDIUM | Directory traversal in user functions | <2.70.0 | Update supabase-js |
| **postcss** | CVE-2023-44270 | MEDIUM | Improper input validation in CSS parsing | <8.4.31 | Update to `>=8.4.31` |

### LOW Severity / Informational

| Package | Issue | Notes |
|---------|-------|-------|
| **pandas** | CVE-2024-9880 | Arbitrary code execution via `query()` - sanitize user inputs |
| **boto3/urllib3** | CVE-2025-50181 | Transitive dependency issue - botocore pins old urllib3 |
| **chromadb** | No direct CVEs | Integration vulnerabilities exist in tools using ChromaDB |

---

## Outdated Packages Analysis

### Python Dependencies (requirements.txt)

| Package | Current | Latest | Gap | Priority |
|---------|---------|--------|-----|----------|
| `fastapi` | 0.108.0 | 0.115.x | 7 minor | **HIGH** (CVE-2024-24762) |
| `uvicorn[standard]` | 0.25.0 | 0.34.x | 9 minor | Medium |
| `python-multipart` | 0.0.6 | 0.0.20 | 14 patches | **CRITICAL** (CVEs) |
| `requests` | 2.31.0 | 2.32.5 | 1 minor | **HIGH** (CVEs) |
| `Pillow` | 10.2.0 | 11.3.0 | 1 major | **HIGH** (CVE) |
| `cryptography` | >=41.0.0 | 44.0.1 | 3 major | **CRITICAL** (CVEs) |
| `pandas` | 2.2.0 | 2.2.3 | 3 patches | Low |
| `duckdb` | >=0.9.0 | 1.3.4 | 1 major | **HIGH** (CVE) |
| `websockets` | 13.0 | 15.0 | 2 major | Low |
| `anthropic` | >=0.40.0 | 0.75.0 | 35 minor | Medium |
| `chromadb` | >=0.4.0 | 1.4.0 | 1 major | Medium |
| `PyMuPDF` | >=1.23.0 | 1.26.7 | 3 minor | Low |
| `PyPDF2` | >=3.0.0 | **DEPRECATED** | N/A | **CRITICAL** |

### Node.js Dependencies (frontend/package.json)

| Package | Current | Latest | Priority |
|---------|---------|--------|----------|
| `axios` | ^1.6.2 | 1.12.0 | **CRITICAL** (CVEs) |
| `vite` | ^5.0.8 | 5.4.18 / 6.2.6 | **CRITICAL** (CVEs) |
| `xlsx` | ^0.18.5 | **UNMAINTAINED** | **CRITICAL** - Replace |
| `@supabase/supabase-js` | ^2.39.0 | 2.49.x | **HIGH** (auth-js CVE) |
| `postcss` | ^8.4.32 | 8.5.x | Medium |
| `tailwindcss` | ^3.3.6 | 3.4.x | Low |
| `lucide-react` | ^0.263.1 | 0.470.x | Low |
| `react` | ^18.2.0 | 18.3.1 | Low |
| `react-router-dom` | ^6.20.0 | 6.30.x | Low |

---

## Redundancy & Bloat Analysis

### PDF Processing Libraries (7 libraries - HIGH REDUNDANCY)

The project includes **7 different PDF processing libraries**, creating:
- Increased attack surface (more code = more potential vulnerabilities)
- Docker image bloat (~300-500MB of redundant dependencies)
- Dependency conflict risks
- Maintenance burden

| Library | Size Impact | Recommendation | Justification |
|---------|-------------|----------------|---------------|
| `PyMuPDF` | ~50MB | **KEEP** | Fast, comprehensive PDF/image handling |
| `pymupdf4llm` | ~1MB | **KEEP** | LLM-optimized text extraction |
| `pdfplumber` | ~10MB | **KEEP** | Excellent table extraction |
| `PyPDF2` | ~5MB | **REMOVE** | Deprecated, has CVEs, replaced by pypdf |
| `pdf2image` | ~5MB | **EVALUATE** | PyMuPDF can render to images |
| `pypdfium2` | ~30MB | **EVALUATE** | Overlaps with PyMuPDF capabilities |
| `camelot-py[cv]` | ~200MB | **EVALUATE** | Brings OpenCV, heavy for table extraction |
| `tabula-py` | ~50MB | **EVALUATE** | Requires Java runtime, overlaps with camelot |

**Recommendation:** Keep PyMuPDF, pymupdf4llm, pdfplumber. Remove PyPDF2. Evaluate others based on actual usage.

### Potential Image Size Reduction

| Action | Estimated Savings |
|--------|-------------------|
| Remove PyPDF2 | ~5MB |
| Remove camelot-py + OpenCV deps | ~200MB |
| Remove tabula-py + Java | ~150MB |
| Remove pypdfium2 | ~30MB |
| **Total Potential** | **~385MB** |

---

## Recommended Secure Dependencies

### requirements-secure.txt

```txt
# Core Framework
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
websockets>=15.0
python-multipart>=0.0.20  # CRITICAL: CVE-2024-24762, CVE-2024-53981

# AI/ML
anthropic>=0.75.0
chromadb>=1.4.0
nltk==3.8.1

# Cloud & Auth
supabase>=2.10.0
boto3>=1.35.0
cryptography>=44.0.1  # CRITICAL: CVE-2024-12797, CVE-2024-6119

# Data Processing
duckdb>=1.1.0  # HIGH: CVE-2024-41672
pandas>=2.2.3
numpy>=1.26.0

# PDF Processing (Consolidated)
PyMuPDF>=1.26.0
pymupdf4llm>=0.0.17
pdfplumber>=0.11.0
pypdf>=6.4.0  # Replaces deprecated PyPDF2
Pillow>=11.3.0  # HIGH: CVE-2025-48379
pytesseract>=0.3.13
pdf2image>=1.17.0

# Office Documents
python-docx>=1.1.0
openpyxl>=3.1.5
xlrd>=2.0.1

# HTTP & Utilities
requests>=2.32.5  # HIGH: CVE-2024-35195, CVE-2024-47081
python-dotenv>=1.0.1

# Optional - evaluate need before including:
# camelot-py[cv]>=0.11.0  # Heavy OpenCV dependency
# tabula-py>=2.9.0  # Requires Java runtime
# pypdfium2>=4.30.0  # Overlaps with PyMuPDF
```

### package.json (Updated)

```json
{
  "name": "xlr8-frontend",
  "version": "2.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "node write-env.js && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@supabase/supabase-js": "^2.49.0",
    "axios": "^1.12.0",
    "exceljs": "^4.4.0",
    "lucide-react": "^0.470.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-joyride": "^2.9.2",
    "react-router-dom": "^6.30.0",
    "recharts": "^2.15.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.4",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.5.0",
    "tailwindcss": "^3.4.17",
    "vite": "^5.4.18"
  }
}
```

---

## Migration Guide

### 1. Replace xlsx with exceljs (CRITICAL)

The npm `xlsx` package is unmaintained and has unpatched vulnerabilities.

```javascript
// BEFORE (xlsx - vulnerable)
import * as XLSX from 'xlsx';
const workbook = XLSX.read(buffer, { type: 'buffer' });
const sheet = workbook.Sheets[workbook.SheetNames[0]];
const data = XLSX.utils.sheet_to_json(sheet);

// AFTER (exceljs - maintained)
import ExcelJS from 'exceljs';
const workbook = new ExcelJS.Workbook();
await workbook.xlsx.load(buffer);
const sheet = workbook.worksheets[0];
const data = [];
const headers = [];
sheet.eachRow((row, rowNumber) => {
  if (rowNumber === 1) {
    headers.push(...row.values.slice(1));
  } else {
    const obj = {};
    row.values.slice(1).forEach((val, i) => {
      obj[headers[i]] = val;
    });
    data.push(obj);
  }
});
```

### 2. Replace PyPDF2 with pypdf (CRITICAL)

```python
# BEFORE (PyPDF2 - deprecated)
from PyPDF2 import PdfReader, PdfWriter

# AFTER (pypdf - maintained)
from pypdf import PdfReader, PdfWriter
# API is largely compatible - same method names
```

### 3. Update python-multipart (CRITICAL)

```bash
pip install "python-multipart>=0.0.20"
```

No code changes required - this is a drop-in security update.

### 4. Secure pandas query() usage

```python
# UNSAFE - allows code injection
df.query(user_input)

# SAFER - use parameterized queries
value = sanitize(user_input)
df.query("column == @value")

# SAFEST - avoid query() with user input entirely
df[df['column'] == sanitized_value]
```

---

## Action Items by Priority

### P0 - Critical (Fix Immediately)

| # | Action | Package | CVE |
|---|--------|---------|-----|
| 1 | Update axios | `^1.6.2` → `^1.12.0` | CVE-2025-27152, CVE-2025-58754 |
| 2 | Update vite | `^5.0.8` → `^5.4.18` | CVE-2025-30208, CVE-2025-31486 |
| 3 | Replace xlsx | Remove, add exceljs | CVE-2023-30533, CVE-2024-22363 |
| 4 | Update python-multipart | `0.0.6` → `>=0.0.20` | CVE-2024-24762, CVE-2024-53981 |
| 5 | Update cryptography | `>=41.0.0` → `>=44.0.1` | CVE-2024-12797, CVE-2024-6119 |
| 6 | Replace PyPDF2 | Remove, add pypdf | CVE-2023-36464 (deprecated) |

### P1 - High (Fix This Week)

| # | Action | Package | Reason |
|---|--------|---------|--------|
| 7 | Update requests | `2.31.0` → `>=2.32.5` | CVE-2024-35195, CVE-2024-47081 |
| 8 | Update Pillow | `10.2.0` → `>=11.3.0` | CVE-2025-48379 |
| 9 | Update fastapi | `0.108.0` → `>=0.115.0` | ReDoS fix + improvements |
| 10 | Update duckdb | `>=0.9.0` → `>=1.1.0` | CVE-2024-41672 |
| 11 | Update @supabase/supabase-js | `^2.39.0` → `^2.49.0` | CVE-2025-48370 in auth-js |

### P2 - Medium (Fix This Month)

| # | Action | Package | Reason |
|---|--------|---------|--------|
| 12 | Update uvicorn | `0.25.0` → `>=0.34.0` | Performance, bug fixes |
| 13 | Update anthropic | `>=0.40.0` → `>=0.75.0` | New features, fixes |
| 14 | Update chromadb | `>=0.4.0` → `>=1.4.0` | Major improvements |
| 15 | Update postcss | `^8.4.32` → `^8.5.0` | CVE-2023-44270 |
| 16 | Audit PDF library usage | All PDF libs | Reduce redundancy |

### P3 - Low (Maintenance)

| # | Action | Package | Reason |
|---|--------|---------|--------|
| 17 | Update remaining npm packages | Various | Keep current |
| 18 | Remove unused PDF libraries | camelot/tabula/pypdfium2 | Reduce bloat |
| 19 | Pin transitive dependencies | Various | Reproducible builds |

---

## Verification Commands

After applying updates, verify security status:

```bash
# Python
pip install pip-audit
pip-audit

# Node.js
npm audit
npm audit fix

# Check for outdated packages
pip list --outdated
npm outdated
```

---

## Sources

- [axios vulnerabilities | Snyk](https://security.snyk.io/package/npm/axios)
- [vite vulnerabilities | Snyk](https://security.snyk.io/package/npm/vite)
- [xlsx vulnerabilities | Snyk](https://security.snyk.io/package/npm/xlsx)
- [python-multipart CVE-2024-53981](https://www.miggo.io/vulnerability-database/cve/CVE-2024-53981)
- [cryptography vulnerabilities | Snyk](https://security.snyk.io/package/pip/cryptography)
- [requests vulnerabilities | Snyk](https://security.snyk.io/package/pip/requests)
- [Pillow vulnerabilities](https://www.cvedetails.com/product/27460/Python-Pillow.html)
- [PyPDF2 deprecation](https://security.snyk.io/package/pip/PyPDF2)
- [fastapi vulnerabilities | Snyk](https://security.snyk.io/package/pip/fastapi)
- [duckdb CVE-2024-41672](https://security.snyk.io/vuln/SNYK-UNMANAGED-DUCKDBDUCKDB-7558566)
- [Vite CVE-2025-30208 | NSFOCUS](https://nsfocusglobal.com/vite-arbitrary-file-read-vulnerability-cve-2025-30208/)
- [@supabase/auth-js CVE-2025-48370](https://security.snyk.io/vuln/SNYK-JS-SUPABASEAUTHJS-10255365)
