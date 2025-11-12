# Data Directory

This directory is for runtime data storage:
- Uploaded PDF files (temporary)
- Parsed data (temporary)
- Foundation Intelligence uploads
- Project files
- Cache files

⚠️ **Important:** 
- Add this directory to .gitignore (already done)
- This directory will be created automatically on first run
- Ensure proper permissions for Railway deployment
- Data stored here is temporary and should be backed up if needed

## Directory Structure (Auto-created):

```
data/
├── uploads/           # User uploaded files
├── foundation/        # Foundation Intelligence knowledge base
├── projects/          # Project-specific data
│   └── {project_id}/  # Individual project folders
├── cache/            # Temporary cache files
└── exports/          # Generated export files
```

All subdirectories are created automatically by the application as needed.
