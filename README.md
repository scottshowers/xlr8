# XLR8

**SaaS Implementation Analysis Platform**

XLR8 automates what traditionally required senior consultants—analyzing customer configuration data, comparing it against reference standards, and providing actionable insights.

## What It Does

- **Upload** configuration exports, policy documents, pay registers
- **Analyze** against Five Truths: Reality, Intent, Configuration, Reference, Regulatory
- **Discover** gaps, misconfigurations, and compliance issues
- **Report** with consultative insights, not just data dumps

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React + Vite (Vercel) |
| Backend | FastAPI + Python 3.11 (Railway) |
| Structured Data | DuckDB |
| Semantic Search | ChromaDB |
| Metadata | Supabase (PostgreSQL) |
| LLMs | Ollama (local) + Claude API (fallback) |

## Architecture

```
User → React Frontend → FastAPI Backend → Intelligence Engine
                                              ↓
                              ┌───────────────┼───────────────┐
                              ▼               ▼               ▼
                           DuckDB        ChromaDB        Supabase
                          (Reality)     (Semantic)      (Metadata)
```

See `/docs/ARCHITECTURE.md` for detailed documentation.

## Quick Start

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Environment

Backend requires:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `ANTHROPIC_API_KEY` (optional - for Claude fallback)

## License

Proprietary - HCMPACT LLC

---

*Built by [HCMPACT](https://hcmpact.com)*
