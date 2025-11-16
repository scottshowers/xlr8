"""
XLR8 Configuration
Central configuration for all app settings
"""

import os
from typing import Optional


class AppConfig:
    """Application configuration and settings"""
    
    # ============================================================================
    # APP IDENTITY
    # ============================================================================
    APP_NAME = "XLR8 by HCMPACT"
    APP_VERSION = "3.0"
    APP_ICON = "⚡"
    
    # ============================================================================
    # FEATURE FLAGS
    # ============================================================================
    USE_SUPABASE_PERSISTENCE = True  # Enable Supabase for data persistence
    USE_ADVANCED_RAG = True          # Enable advanced RAG features
    USE_CHAT_STREAMING = True        # Enable streaming chat responses
    ENABLE_DEBUG_MODE = False        # Show debug information
    
    # ============================================================================
    # SUPABASE CONFIGURATION
    # ============================================================================
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
    
    @classmethod
    def get_supabase_handler(cls):
        """
        Get initialized Supabase handler
        
        Returns:
            SupabaseHandler instance or None if not configured
        """
        if not cls.USE_SUPABASE_PERSISTENCE:
            return None
        
        if not cls.SUPABASE_URL or not cls.SUPABASE_KEY:
            raise ValueError("Supabase credentials not configured. Set SUPABASE_URL and SUPABASE_KEY environment variables.")
        
        from utils.data.supabase_handler import SupabaseHandler
        return SupabaseHandler(cls.SUPABASE_URL, cls.SUPABASE_KEY)
    
    # ============================================================================
    # LLM CONFIGURATION (Local LLM on Hetzner)
    # ============================================================================
    LLM_ENDPOINT = "http://178.156.190.64:11435"
    LLM_USERNAME = "xlr8"
    LLM_PASSWORD = "Argyle76226#"
    LLM_DEFAULT_MODEL = "deepseek-r1:7b"  # Default model
    LLM_FAST_MODEL = "mistral:7b"         # Fast alternative
    
    # Model selection based on task
    LLM_MODELS = {
        'reasoning': 'deepseek-r1:7b',     # Complex reasoning
        'fast': 'mistral:7b',               # Quick responses
        'embedding': 'nomic-embed-text'     # Embeddings
    }
    
    # ============================================================================
    # RAG CONFIGURATION
    # ============================================================================
    RAG_CHUNK_SIZE = 500
    RAG_CHUNK_OVERLAP = 50
    RAG_TOP_K = 5
    RAG_SIMILARITY_THRESHOLD = 0.7
    
    @classmethod
    def get_rag_handler(cls):
        """
        Get initialized RAG handler based on configuration
        
        Returns:
            Appropriate RAG handler instance
        """
        try:
            # Try ChromaDB handler first (production)
            from utils.rag.chromadb_handler import ChromaDBHandler
            return ChromaDBHandler(
                endpoint=cls.LLM_ENDPOINT,
                username=cls.LLM_USERNAME,
                password=cls.LLM_PASSWORD
            )
        except Exception as e:
            # Fallback to basic handler
            from utils.rag.basic_handler import BasicRAGHandler
            return BasicRAGHandler(
                endpoint=cls.LLM_ENDPOINT,
                username=cls.LLM_USERNAME,
                password=cls.LLM_PASSWORD
            )
    
    # ============================================================================
    # UI CONFIGURATION
    # ============================================================================
    THEME_COLOR = "#1976D2"
    BACKGROUND_COLOR = "#f5f7f9"
    CARD_BACKGROUND = "#ffffff"
    TEXT_COLOR = "#2c3e50"
    
    # ============================================================================
    # CUSTOM CSS
    # ============================================================================
    CUSTOM_CSS = """
    <style>
    /* XLR8 Custom Styling */
    
    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #1976D2;
        font-family: "Source Sans Pro", sans-serif;
    }
    
    /* Info boxes */
    .info-box {
        padding: 1rem;
        background-color: #e3f2fd;
        border-left: 4px solid #1976D2;
        border-radius: 4px;
        margin-bottom: 1rem;
    }
    
    .success-box {
        padding: 1rem;
        background-color: #e8f5e9;
        border-left: 4px solid #4caf50;
        border-radius: 4px;
        margin-bottom: 1rem;
    }
    
    .warning-box {
        padding: 1rem;
        background-color: #fff3e0;
        border-left: 4px solid #ff9800;
        border-radius: 4px;
        margin-bottom: 1rem;
    }
    
    .error-box {
        padding: 1rem;
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        border-radius: 4px;
        margin-bottom: 1rem;
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 4px;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Cards */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }
    
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #1976D2;
    }
    
    /* Chat messages */
    .stChatMessage {
        padding: 1rem;
        margin-bottom: 1rem;
        border-radius: 8px;
        border: 1px solid #e5e7eb;
    }
    
    /* File uploader */
    .uploadedFile {
        background-color: #f0f7ff;
        border: 1px solid #1976D2;
        border-radius: 4px;
        padding: 0.5rem;
    }
    
    /* Expanders */
    .streamlit-expanderHeader {
        background-color: #f5f7f9;
        border-radius: 4px;
        font-weight: 600;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Smooth transitions */
    * {
        transition: background-color 0.3s ease;
    }
    </style>
    """
    
    # ============================================================================
    # VALIDATION
    # ============================================================================
    @classmethod
    def validate_config(cls) -> tuple[bool, list[str]]:
        """
        Validate configuration
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check LLM configuration
        if not cls.LLM_ENDPOINT:
            errors.append("LLM_ENDPOINT not configured")
        
        # Check Supabase if enabled
        if cls.USE_SUPABASE_PERSISTENCE:
            if not cls.SUPABASE_URL:
                errors.append("SUPABASE_URL not set (required when USE_SUPABASE_PERSISTENCE=True)")
            if not cls.SUPABASE_KEY:
                errors.append("SUPABASE_KEY not set (required when USE_SUPABASE_PERSISTENCE=True)")
        
        return (len(errors) == 0, errors)
    
    @classmethod
    def get_config_summary(cls) -> dict:
        """Get summary of current configuration"""
        return {
            'app_name': cls.APP_NAME,
            'version': cls.APP_VERSION,
            'supabase_enabled': cls.USE_SUPABASE_PERSISTENCE,
            'supabase_configured': bool(cls.SUPABASE_URL and cls.SUPABASE_KEY),
            'llm_endpoint': cls.LLM_ENDPOINT,
            'llm_model': cls.LLM_DEFAULT_MODEL,
            'advanced_rag': cls.USE_ADVANCED_RAG,
            'debug_mode': cls.ENABLE_DEBUG_MODE
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_llm_config() -> dict:
    """Get LLM configuration"""
    return {
        'endpoint': AppConfig.LLM_ENDPOINT,
        'username': AppConfig.LLM_USERNAME,
        'password': AppConfig.LLM_PASSWORD,
        'default_model': AppConfig.LLM_DEFAULT_MODEL,
        'models': AppConfig.LLM_MODELS
    }


def get_rag_config() -> dict:
    """Get RAG configuration"""
    return {
        'chunk_size': AppConfig.RAG_CHUNK_SIZE,
        'chunk_overlap': AppConfig.RAG_CHUNK_OVERLAP,
        'top_k': AppConfig.RAG_TOP_K,
        'similarity_threshold': AppConfig.RAG_SIMILARITY_THRESHOLD
    }


def is_supabase_enabled() -> bool:
    """Check if Supabase is enabled and configured"""
    return (AppConfig.USE_SUPABASE_PERSISTENCE and 
            bool(AppConfig.SUPABASE_URL) and 
            bool(AppConfig.SUPABASE_KEY))


# Validate configuration on import
is_valid, errors = AppConfig.validate_config()
if not is_valid and AppConfig.ENABLE_DEBUG_MODE:
    print("⚠️ Configuration warnings:")
    for error in errors:
        print(f"  - {error}")
