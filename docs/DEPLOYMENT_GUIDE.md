# XLR8 v3.0 - DEPLOYMENT GUIDE
## Modular Architecture - Package Deployment

**Version:** 3.0.0  
**Date:** November 15, 2025  
**Architecture:** Hyper-Modular with RAG Integration

---

## 📦 WHAT'S NEW IN V3.0

### Complete Restructure
- **Modular Architecture**: 30+ independent modules
- **Team Collaboration**: Multiple developers can work simultaneously
- **Zero Conflicts**: Each person owns their own files
- **RAG Integration**: Production-grade semantic search
- **Centralized Configuration**: All settings in `config.py`

### Benefits
✅ **Scalable Development**: Add features without touching existing code  
✅ **Easy Testing**: Each module tests independently  
✅ **Clear Ownership**: Every file has an assigned owner  
✅ **No Merge Conflicts**: Parallel development without conflicts  
✅ **Progressive Deployment**: Deploy one module at a time  

---

## 📁 PACKAGE STRUCTURE

```
xlr8/
├── app.py                          # Main router (MINIMAL - 150 lines)
├── config.py                       # All configuration
├── requirements.txt                # Python dependencies
│
├── pages/                          # UI Pages (12 pages)
│   ├── work/
│   │   ├── analysis/              # 📊 Analysis & Templates (PRIORITY)
│   │   │   ├── upload.py          # File upload
│   │   │   ├── parser.py          # Document parsing
│   │   │   ├── ai_analyzer.py    # AI analysis
│   │   │   ├── template_filler.py # Template generation
│   │   │   └── results_viewer.py  # Display results
│   │   ├── chat/                  # 💬 AI Assistant
│   │   └── library/               # 📁 Document Library
│   │
│   ├── setup/
│   │   ├── projects/              # Project management
│   │   ├── knowledge/             # HCMPACT knowledge base
│   │   └── connections/           # API configurations
│   │
│   ├── qa/
│   │   ├── sit/                   # SIT testing
│   │   ├── uat/                   # UAT testing
│   │   └── scenarios/             # Test scenarios
│   │
│   └── admin/
│       ├── users/                 # User management
│       ├── audit/                 # Audit logs
│       └── settings/              # System settings
│
├── utils/                          # Business Logic (NO UI)
│   ├── data/
│   │   └── session.py             # Session state management
│   ├── llm/                       # LLM clients
│   ├── rag/
│   │   └── handler.py             # RAG/vector store
│   ├── parsers/
│   │   └── pdf_parser.py          # PDF parsing
│   └── templates/                 # Template generators
│
├── components/                     # Reusable UI
│   └── sidebar.py                 # Main sidebar
│
└── docs/                          # Documentation
    ├── DEPLOYMENT_GUIDE.md        # This file
    ├── ARCHITECTURE.md            # Tech stack docs
    ├── SECURITY.md                # Security audit
    ├── TEAM_GUIDE.md              # Developer guide
    └── MODULE_OWNERSHIP.md        # Who owns what
```

---

## 🚀 DEPLOYMENT OPTIONS

### Option A: Full Package Replace (Recommended for V3.0)

**When to use**: First time deploying modular structure

**Steps:**

1. **Backup Current Version**
   ```bash
   # In GitHub, create a release/tag for current version
   git tag v2.1-pre-modular
   git push origin v2.1-pre-modular
   ```

2. **Delete Old Structure**
   - In GitHub repo, delete current `app.py`
   - Keep `requirements.txt` and `utils/` folder

3. **Upload New Structure**
   - Upload all files from `xlr8_modular/` package
   - Maintain directory structure exactly as shown above

4. **Verify Structure**
   ```
   Your GitHub repo should look like:
   ├── app.py
   ├── config.py
   ├── requirements.txt
   ├── pages/
   │   ├── work/...
   │   ├── setup/...
   │   ├── qa/...
   │   └── admin/...
   ├── utils/...
   ├── components/...
   └── docs/...
   ```

5. **Commit**
   ```
   Commit message: "v3.0: Modular architecture deployment"
   ```

6. **Railway Auto-Deploys** (~5 minutes)

---

### Option B: Gradual Migration (Safer, Longer)

**When to use**: Want to test before full cutover

**Phase 1: Deploy Skeleton**
1. Add new structure alongside old `app.py`
2. Rename old app: `app_v2_backup.py`
3. Deploy new `app.py`
4. Test basic navigation

**Phase 2: Migrate One Feature**
1. Migrate Analysis module (most important)
2. Test thoroughly
3. Keep old code as backup

**Phase 3: Migrate Remaining**
1. One module per day
2. Test after each
3. Remove backups when stable

---

## 📋 PRE-DEPLOYMENT CHECKLIST

### Required Files
- [ ] `app.py` (main router)
- [ ] `config.py` (configuration)
- [ ] `requirements.txt` (dependencies)
- [ ] `utils/data/session.py` (session manager)
- [ ] `utils/rag/handler.py` (RAG system)
- [ ] `components/sidebar.py` (sidebar)
- [ ] All page `__init__.py` files

### Required on Server (Hetzner)
- [ ] ChromaDB installed
- [ ] Ollama running with models:
  - [ ] `mistral:7b`
  - [ ] `mixtral:8x7b`
  - [ ] `nomic-embed-text`
- [ ] Nginx running on port 11435
- [ ] Firewall allows port 11435

### Configuration Review
- [ ] `config.py` has correct LLM endpoint
- [ ] `config.py` has correct credentials
- [ ] Feature flags set appropriately
- [ ] Custom CSS theme preserved

---

## 🔧 POST-DEPLOYMENT CONFIGURATION

### 1. Verify Deployment

After Railway deploys:

1. **Check App Loads**
   - Visit: https://your-app.up.railway.app
   - Should see 4 main tabs
   - Sidebar should be visible

2. **Test Navigation**
   - Click through all tabs
   - All sub-tabs should load
   - No errors in console

3. **Test LLM Connection**
   - Go to Setup → Connections
   - Should see "✅ LLM Connected & Ready"

4. **Test RAG**
   - Go to Setup → HCMPACT Knowledge Base
   - Upload a test document
   - Should see "Indexed X chunks"

### 2. Seed Initial Data

**Create Test Project:**
1. Go to Setup → Projects & Clients
2. Create test project: "Test Implementation"
3. Set as active

**Upload Test HCMPACT Doc:**
1. Go to Setup → HCMPACT Knowledge Base
2. Upload a sample standard
3. Verify indexing works

**Test Analysis:**
1. Go to Work → Analysis & Templates
2. Upload a sample customer document
3. Run analysis
4. Verify results display

---

## 🐛 TROUBLESHOOTING

### App Won't Start

**Error: ModuleNotFoundError**
```
Solution: Check requirements.txt deployed correctly
Verify: All dependencies installed by Railway
```

**Error: Cannot import 'render_X_page'**
```
Solution: Check all __init__.py files exist
Verify: Directory structure matches exactly
```

### RAG Not Working

**Error: "No module named 'chromadb'"**
```
Solution: Ensure chromadb in requirements.txt
Server: Verify chromadb installed on Hetzner
```

**Error: "Cannot connect to embedding model"**
```
Solution: Check Ollama running: systemctl status ollama
Verify: nomic-embed-text pulled: ollama list
```

### Modules Not Loading

**Some pages show "under development"**
```
This is normal! Stub modules show this message.
Assign to team members to develop.
```

**Navigation works but page is blank**
```
Check: __init__.py has render_X_page() function
Check: Function name matches import in app.py
```

---

## 📊 DEPLOYMENT VERIFICATION

### Success Criteria

After deployment, verify ALL these work:

- [ ] **App loads** without errors
- [ ] **All 4 main tabs** visible
- [ ] **All 12 sub-tabs** load
- [ ] **Sidebar** displays correctly
- [ ] **Project selector** works
- [ ] **AI model selector** works
- [ ] **Quick stats** show data
- [ ] **LLM connection** active
- [ ] **RAG indexing** works
- [ ] **Document upload** works
- [ ] **Analysis runs** successfully
- [ ] **Chat** responds
- [ ] **No console errors**

### Performance Benchmarks

Expected performance:
- **Page load**: < 2 seconds
- **File upload**: < 5 seconds (for 10MB file)
- **Document parsing**: < 10 seconds
- **RAG indexing**: < 30 seconds (first upload)
- **AI analysis**: 30-60 seconds (depends on model)
- **Chat response**: 10-20 seconds (Fast mode)

---

## 🔄 UPDATE WORKFLOW (After Initial Deployment)

### For Bug Fixes

1. **Identify Module**
   - Find which file has the bug
   - Example: `pages/work/analysis/upload.py`

2. **Fix in Module**
   - Edit only that file
   - Test locally if possible

3. **Deploy**
   - Update file in GitHub
   - Commit: "Fix: Upload validation in analysis module"
   - Railway auto-deploys

4. **Verify**
   - Test the specific feature
   - No need to retest entire app

### For New Features

1. **Create New Module**
   - Add file to appropriate directory
   - Example: `pages/work/analysis/ocr_scanner.py`

2. **Import in Orchestrator**
   - Update `pages/work/analysis/__init__.py`
   - Add function call in workflow

3. **Test**
   - Module can be tested independently
   - Integration test with orchestrator

4. **Deploy**
   - Add new file to GitHub
   - Commit: "Feature: OCR scanner in analysis"

### For Module Improvements

**Example: Improve Template Generator**

1. **Assign to Developer**
   - Person D owns `template_filler.py`

2. **They Work Independently**
   - Edit only their file
   - Test with mock data
   - No conflicts with others

3. **Submit PR**
   - Pull request with their changes
   - You review

4. **Merge & Deploy**
   - Merge to main
   - Railway auto-deploys
   - Only their module updates

---

## 🎯 ROLLBACK PROCEDURE

### If Deployment Fails

**Option 1: Revert Commit**
```bash
git revert HEAD
git push origin main
```

**Option 2: Restore Tag**
```bash
git checkout v2.1-pre-modular
git push origin main --force
```

**Option 3: Railway Rollback**
1. Go to Railway dashboard
2. Click "Deployments"
3. Find last working deployment
4. Click "Redeploy"

### If Specific Module Fails

**Don't rollback entire app!**

1. **Identify failing module**
2. **Replace with stub**:
   ```python
   def render_X_page():
       st.error("This module is temporarily disabled")
   ```
3. **Deploy stub**
4. **Fix module offline**
5. **Redeploy when fixed**

---

## 📝 DEPLOYMENT LOG TEMPLATE

Keep a log of deployments:

```
=== DEPLOYMENT LOG ===

Date: 2025-11-15
Version: v3.0.0
Type: Full modular architecture
Deployed By: [Your Name]

Changes:
- Converted to modular architecture
- Added RAG integration
- Restructured navigation
- Centralized configuration

Pre-Deployment Checks:
✅ Backup created (tag: v2.1-pre-modular)
✅ Requirements verified
✅ Server dependencies installed
✅ Configuration reviewed

Deployment:
- Started: 14:00 UTC
- Railway build time: 4min 32sec
- Completed: 14:05 UTC

Post-Deployment Tests:
✅ App loads
✅ Navigation works
✅ LLM connected
✅ RAG indexing works
✅ Analysis runs successfully

Issues: None

Next Steps:
- Monitor for 24 hours
- Train team on new structure
- Assign module ownership
```

---

## 🎓 TRAINING MATERIALS

After deployment, train your team:

1. **For End Users**
   - New navigation structure
   - Where to find features
   - No functional changes

2. **For Developers**
   - Read TEAM_GUIDE.md
   - Understand module ownership
   - Learn independent development workflow

3. **For Project Managers**
   - How to assign modules
   - How to track progress
   - How to coordinate releases

---

## 📞 SUPPORT

### Deployment Issues
- Check Railway logs
- Review error messages
- Verify all files deployed

### Module Development Issues
- Read TEAM_GUIDE.md
- Check module template
- Test independently

### Architecture Questions
- Read ARCHITECTURE.md
- Review module interfaces
- Check dependencies

---

## ✅ DEPLOYMENT COMPLETE!

Once all success criteria met:

1. ✅ Tag the deployment: `git tag v3.0.0-production`
2. ✅ Document any issues encountered
3. ✅ Update team on new structure
4. ✅ Assign module ownership (see MODULE_OWNERSHIP.md)
5. ✅ Monitor for 24-48 hours
6. ✅ Celebrate! 🎉

**You now have a production-grade, scalable, team-friendly architecture!**
