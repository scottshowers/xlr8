# XLR8 Ways of Working

**Last Updated:** January 11, 2026  
**Purpose:** Principles and non-negotiables for building XLR8

---

## Core Philosophy

**We are building an exit-ready asset, not a prototype.**

Every decision, every line of code, every architecture choice is made with the understanding that this system will be reviewed by technical due diligence teams evaluating a $15-25M acquisition.

---

## Non-Negotiables

### 1. No Shortcuts
- Do it right or don't do it
- Technical debt is exit debt
- "Quick fix" means "permanent fix done quickly"

### 2. Full File Replacements Only
- Scott is not a developer
- No patches, no diffs, no "add this at line X"
- Every code change = complete working file

### 3. LLM for Synthesis, Not Generation
- SQL generation: **Deterministic lookup** (TermIndex + SQLAssembler)
- Data retrieval: **Direct queries** (DuckDB, ChromaDB)
- LLM role: **Synthesis and explanation only**
- Why: Hallucinations kill trust, non-determinism kills debugging

### 4. Local First, Cloud Fallback
- Primary: Local LLMs via Ollama (DeepSeek for SQL, Mistral for synthesis)
- Fallback: Claude API for true edge cases only
- Why: Cost control, speed, independence

### 5. Domain Agnostic Architecture
- XLR8 is NOT a UKG tool - it's a universal SaaS analysis platform
- Standards uploaded, not hardcoded
- Domain knowledge via Learning layer, not code
- Any HCM vendor, any implementation type

### 6. Five Truths Framework
All analysis triangulates across:
1. **Reality** - What IS (customer data in DuckDB)
2. **Intent** - What they WANT (parsed from SOW/requirements)
3. **Configuration** - What's SET UP (customer settings)
4. **Reference** - What's RECOMMENDED (vendor best practices)
5. **Regulatory** - What's REQUIRED (compliance rules)

### 7. Document Everything
- Code has clear docstrings
- Architecture decisions are recorded
- Session work updates documentation
- Future Claude instances can understand the system

---

## Development Principles

### Code Quality
- Remove dead code immediately
- Consolidate duplicates on discovery
- Functions do one thing
- Names describe purpose
- Comments explain why, not what

### Testing Approach
- Test pages for interactive validation (like today's Intelligence Test Page)
- Curl/API tests for quick checks
- Real data tests over mocked data
- If it works in test page, it works in production

### Error Handling
- Fail loudly in development
- Fail gracefully in production
- Log everything at WARNING level (INFO doesn't show)
- Errors include context for debugging

### Database Conventions
- DuckDB for structured/tabular data (Reality truth)
- ChromaDB for vector/document data (Reference, Regulatory, Compliance truths)
- Supabase for application state and user data
- Project names normalized to lowercase
- Table names preserved as uploaded

---

## Communication Principles

### Session Start
1. Claude reads WAYS_OF_WORKING.md
2. Claude reads ARCHITECTURE.md
3. Claude reads ROADMAP.md
4. Claude reads active PHASE_XX.md
5. Scott states current focus

### During Work
- Scott describes what, Claude determines how
- Claude explains approach before coding
- Scott approves direction before implementation
- No silent assumptions

### Session End
- Update affected documentation
- Commit with clear messages
- Note any open items
- Update phase status

### When Stuck
- State the problem clearly
- Show what was tried
- Ask specific questions
- Don't spin - escalate

---

## File Organization

```
/xlr8-main
├── ARCHITECTURE.md          # Current system state
├── WAYS_OF_WORKING.md       # This file
├── ROADMAP.md               # Phase overview
├── /doc
│   ├── PHASE_01_SQL.md      # SQL evolutions detail
│   ├── PHASE_02_VECTOR.md   # Vector retrieval detail
│   ├── PHASE_03_SYNTHESIS.md
│   ├── PHASE_04_PRESENTATION.md
│   └── PHASE_05_API.md
├── /backend                  # FastAPI on Railway
├── /frontend                 # React on Vercel
└── /mnt/skills              # Claude skills
```

---

## Decision Framework

When facing a technical decision:

1. **Does it move us toward exit?** If no, don't do it.
2. **Is it deterministic where possible?** Prefer lookup over generation.
3. **Is it maintainable?** Someone else will read this code.
4. **Is it documented?** If it's not written down, it doesn't exist.
5. **Does it follow Five Truths?** Data decisions map to truths.

---

## Frontend Development Principles

### Pipeline Safety First
**NEVER touch backend during UX work:**
- ❌ `/backend/routers/` - API endpoints  
- ❌ `/backend/services/` - Intelligence services  
- ❌ `/backend/utils/` - Detection, analysis, LLM  
- ❌ `/backend/models/` - Data models  
- ❌ `playbooks/` - Playbook definitions  
- ❌ Database schema

**Why:** The backend pipeline is battle-tested and exit-ready. Breaking it delays acquisition.

### Design System Consistency
**Every component uses:**
- CSS custom properties (no magic numbers)
- Sora font for headings, Manrope for body
- 8px spacing system (4/8/16/24/32/48)
- Grass green (#83b16d) as primary brand color
- Consistent hover states (translateY + shadow)

**Why:** Professional appearance = higher valuation.

### Component Reusability
**Build once, use everywhere:**
- Button (primary/secondary/danger variants)
- Card (white background, 16px radius, hover lift)
- Badge (critical/warning/info colors)
- PageHeader (title + subtitle + actions)

**Why:** Faster development, consistent UX, easier maintenance.

### File Creation Strategy
**For new files:**
- Short (<100 lines): Create complete in one call
- Long (>100 lines): Build iteratively section by section

**For existing files:**
- Use str_replace for targeted edits
- Never replace entire file unless <200 lines
- Backup before major changes

**Why:** Avoid compaction issues, preserve git history.

### Page-by-Page Implementation
**Build one page at a time:**
1. Create component file
2. Test in isolation
3. Integrate with routing
4. Verify existing features still work
5. Document completion before moving to next page

**Why:** Incremental progress, easier debugging, avoids overwhelming context window.

---

## What Success Looks Like

### Engine Success
- Any reasonable HCM question returns accurate, useful answer
- 95% of queries use deterministic SQL generation
- Responses include data + context + recommendations
- Sub-second query execution

### Exit Success
- Clean codebase with clear architecture
- Documented decisions and rationale
- Test coverage on critical paths
- Metrics showing system performance
- No embarrassing code in due diligence

### Daily Success
- Work committed and documented
- Documentation reflects reality
- No orphaned experiments
- Clear status on active phase

---

## Anti-Patterns to Avoid

| Don't | Do Instead |
|-------|------------|
| Stub things out "for later" | Build it complete or don't build it |
| Use LLM to generate SQL | Use TermIndex + SQLAssembler |
| Hardcode domain knowledge | Upload standards, use Learning layer |
| Fix symptoms | Fix root causes |
| Leave dead code | Delete immediately |
| Assume context persists | Document in repo |
| Build features before foundation | Foundation → plumbing → features |

---

## Version History

| Date | Change |
|------|--------|
| 2026-01-15 | Added Frontend Development principles - design system, component reusability, page-by-page strategy |
| 2026-01-11 | Initial version - extracted from evolved practices |
