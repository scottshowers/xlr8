"""
Application Configuration
Centralized settings for XLR8
"""

import os


class AppConfig:
    """Main application configuration"""
    
    # App Info
    APP_NAME = "XLR8"
    APP_ICON = "⚡"
    VERSION = "3.0"
    TAGLINE = "UKG Implementation Accelerator by HCMPACT"
    
    # LLM Configuration
    LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "http://178.156.190.64:11435")
    LLM_DEFAULT_MODEL = os.getenv("LLM_MODEL", "deepseek-r1:7b")
    LLM_USERNAME = os.getenv("LLM_USERNAME", "xlr8")
    LLM_PASSWORD = os.getenv("LLM_PASSWORD", "Argyle76226#")
    
    # RAG Configuration
    # Using ephemeral storage (will reset on rebuilds)
    RAG_PERSIST_DIR = os.getenv("CHROMADB_PATH", "/root/.xlr8_chroma")
    
    # File Upload Limits
    MAX_FILE_SIZE_MB = 200  # Maximum file upload size in MB
    
    # Embedding Configuration
    EMBED_ENDPOINT = os.getenv("EMBED_ENDPOINT", "http://178.156.190.64:11435")
    EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
    
    # Custom CSS
    CUSTOM_CSS = """
    <style>
    /* Main container */
    .main {
        padding: 1rem 2rem;
    }
    
    /* Info boxes */
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #e7f3ff;
        border-left: 4px solid #2196F3;
        margin: 1rem 0;
    }
    
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #e8f5e9;
        border-left: 4px solid #4CAF50;
        margin: 1rem 0;
    }
    
    .warning-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #fff3e0;
        border-left: 4px solid #FF9800;
        margin: 1rem 0;
    }
    
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        margin: 1rem 0;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #1976D2;
    }
    
    /* Buttons */
    .stButton>button {
        border-radius: 0.5rem;
    }
    
    /* Chat messages */
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #1976D2;
    }
    </style>
    """
