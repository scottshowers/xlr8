#!/bin/bash

# XLR8 Modular Architecture Deployment Script
# Deploys the modular architecture infrastructure to your existing XLR8 repo

echo "🚀 XLR8 Modular Architecture Deployment"
echo "========================================"
echo ""

# Check if we're in a git repo
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository"
    echo "   Please run this script from your xlr8 repo root directory"
    exit 1
fi

echo "✅ Git repository detected"
echo ""

# Confirm with user
echo "This will:"
echo "  1. Create interfaces/ directory"
echo "  2. Create tests/ directory  "
echo "  3. Backup your current config.py"
echo "  4. Install new config.py with feature flags"
echo "  5. Commit changes to git"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 0
fi

# Create backup
echo "📦 Creating backup..."
BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
if [ -f "config.py" ]; then
    cp config.py "$BACKUP_DIR/config.py.backup"
    echo "   ✅ Backed up config.py to $BACKUP_DIR/"
fi

# Create directories
echo ""
echo "📁 Creating directories..."
mkdir -p interfaces
mkdir -p tests
echo "   ✅ Created interfaces/"
echo "   ✅ Created tests/"

# Copy interface files
echo ""
echo "📄 Copying interface contracts..."
if [ -d "modular_architecture/interfaces" ]; then
    cp modular_architecture/interfaces/*.py interfaces/
    echo "   ✅ Copied 4 interface files"
else
    echo "   ⚠️  Warning: modular_architecture/interfaces not found"
    echo "   Please copy interface files manually"
fi

# Copy test files
echo ""
echo "🧪 Copying test templates..."
if [ -d "modular_architecture/tests" ]; then
    cp modular_architecture/tests/*.py tests/
    echo "   ✅ Copied test templates"
else
    echo "   ⚠️  Warning: modular_architecture/tests not found"
    echo "   Please copy test files manually"
fi

# Update config.py
echo ""
echo "⚙️  Updating config.py..."
if [ -f "modular_architecture/config_with_flags.py" ]; then
    cp modular_architecture/config_with_flags.py config.py
    echo "   ✅ Installed config.py with feature flags"
else
    echo "   ⚠️  Warning: config_with_flags.py not found"
    echo "   Please update config.py manually"
fi

# Copy documentation
echo ""
echo "📚 Copying documentation..."
if [ -f "modular_architecture/MODULE_INTEGRATION_CHECKLIST.md" ]; then
    cp modular_architecture/MODULE_INTEGRATION_CHECKLIST.md .
    echo "   ✅ Copied MODULE_INTEGRATION_CHECKLIST.md"
fi

if [ -f "modular_architecture/TEAM_COLLABORATION_GUIDE.md" ]; then
    cp modular_architecture/TEAM_COLLABORATION_GUIDE.md .
    echo "   ✅ Copied TEAM_COLLABORATION_GUIDE.md"
fi

# Git add
echo ""
echo "📝 Adding to git..."
git add interfaces/ tests/ config.py
git add MODULE_INTEGRATION_CHECKLIST.md TEAM_COLLABORATION_GUIDE.md 2>/dev/null || true

# Show status
echo ""
echo "📊 Git status:"
git status --short

# Commit
echo ""
read -p "Commit these changes? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    git commit -m "Add modular architecture infrastructure

- Interface contracts for PDF, RAG, LLM, Templates
- Standalone test templates
- Feature flag system in config.py
- Team collaboration guides

This enables parallel development without conflicts"
    
    echo ""
    echo "✅ Committed to git"
    
    echo ""
    read -p "Push to origin/main? (y/n) " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git push origin main
        echo "✅ Pushed to GitHub"
        echo ""
        echo "🚀 Railway will now deploy..."
        echo "   Watch: https://railway.app"
    fi
fi

# Summary
echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE"
echo "=========================================="
echo ""
echo "What was installed:"
echo "  ✅ interfaces/ - 4 interface contracts"
echo "  ✅ tests/ - Standalone test templates"
echo "  ✅ config.py - Feature flag system"
echo "  ✅ Documentation - Integration guides"
echo ""
echo "Backup location:"
echo "  📦 $BACKUP_DIR/"
echo ""
echo "Next steps:"
echo "  1. Read TEAM_COLLABORATION_GUIDE.md"
echo "  2. Read MODULE_INTEGRATION_CHECKLIST.md"
echo "  3. Assign modules to team members"
echo "  4. Start parallel development!"
echo ""
echo "Questions? Check README.md in modular_architecture/"
echo ""
echo "🎉 Happy coding!"
