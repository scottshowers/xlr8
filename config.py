"""
XLR8 Configuration - SECURE VERSION
Central configuration for all app settings
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()


class Colors:
    """Standardized color palette - Muted Blue Theme"""
    # Primary palette
    PRIMARY = "#8ca6be"      # Main brand color (muted blue)
    SECONDARY = "#98afc5"    # Secondary actions
    ACCENT = "#6d8aa0"       # Highlights/active states
    
    # Backgrounds
    BG_PAGE = "#f5f7f9"      # Page background
    BG_CARD = "#ffffff"      # Card background
    BG_SIDEBAR = "#f8f9fa"   # Sidebar background
    
    # Text
    TEXT_PRIMARY = "#2c3e50"     # Main text
    TEXT_SECONDARY = "#6c757d"   # Secondary text
    TEXT_MUTED = "#7d96a8"       # Muted text
    
    # Status
    SUCCESS = "#28a745"      # Success states
    WARNING = "#ffc107"      # Warning states
    ERROR = "#dc3545"        # Error states
    INFO = "#17a2b8"         # Info states
    
    # Borders
    BORDER_LIGHT = "#e1e8ed"
    BORDER_DARK = "#d1dce5"


class AppConfig:
    """Application configuration and settings"""
    
    # ============================================================================
    # APP IDENTITY
    # ============================================================================
    APP_NAME = "XLR8 by HCMPACT"
    APP_VERSION = "3.0"
    VERSION = "3.0"  # Alias for compatibility
    APP_ICON = ""
    TAGLINE = "UKG Implementation Accelerator by HCMPACT"
    
    # ============================================================================
    # FILE UPLOAD CONFIGURATION
    # ============================================================================
    MAX_FILE_SIZE_MB = 200  # Maximum file upload size
    
    # ============================================================================
    # FEATURE FLAGS
    # ============================================================================
    USE_SUPABASE_PERSISTENCE = True  # Enable Supabase for data persistence
    USE_ADVANCED_RAG = True          # Enable advanced RAG features
    USE_CHAT_STREAMING = True        # Enable streaming chat responses
    ENABLE_DEBUG_MODE = False        # Show debug information
    
    # ============================================================================
    # SUPABASE CONFIGURATION (SECURE - from environment)
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
    # LLM CONFIGURATION (SECURE - from environment)
    # ============================================================================
    LLM_ENDPOINT = os.environ.get('LLM_ENDPOINT', '')
    LLM_USERNAME = os.environ.get('LLM_USERNAME', '')
    LLM_PASSWORD = os.environ.get('LLM_PASSWORD', '')
    LLM_DEFAULT_MODEL = os.environ.get('LLM_DEFAULT_MODEL', 'deepseek-r1:7b')
    LLM_FAST_MODEL = "mistral:7b"  # Fast alternative
    
    # Claude API Configuration (optional - enables hybrid mode)
    CLAUDE_API_KEY = os.environ.get('CLAUDE_API_KEY', '')
    CLAUDE_MODEL = "claude-sonnet-4-20250514"
    
    # Model selection based on task
    LLM_MODELS = {
        'reasoning': 'deepseek-r1:7b',     # Complex reasoning
        'fast': 'mistral:7b',               # Quick responses
        'embedding': 'nomic-embed-text',    # Embeddings
        'hybrid': 'claude-sonnet-4-20250514'  # Claude for synthesis
    }
    
    # ============================================================================
    # RAG CONFIGURATION
    # ============================================================================
    RAG_PERSIST_DIR = "/tmp/xlr8_chroma"  # ChromaDB persistence directory
    RAG_CHUNK_SIZE = 500
    RAG_CHUNK_OVERLAP = 50
    RAG_TOP_K = 5
    RAG_SIMILARITY_THRESHOLD = 0.7
    
    # Embedding Configuration
    EMBED_ENDPOINT = os.environ.get('EMBED_ENDPOINT', os.environ.get('LLM_ENDPOINT', ''))
    EMBED_MODEL = os.environ.get('EMBED_MODEL', 'nomic-embed-text')
    
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
    # CUSTOM CSS (STANDARDIZED COLORS)
    # ============================================================================
    CUSTOM_CSS = f"""
    <style>
    /* XLR8 Custom Styling - STANDARDIZED */
    
    /* Main container */
    .main .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }}
    
    /* Headers - Use primary color */
    h1, h2, h3 {{
        color: {Colors.PRIMARY};
        font-family: "Source Sans Pro", sans-serif;
    }}
    
    /* Info boxes - Consistent colors */
    .info-box {{
        padding: 1rem;
        background-color: {Colors.PRIMARY}15;
        border-left: 4px solid {Colors.PRIMARY};
        border-radius: 4px;
        margin-bottom: 1rem;
    }}
    
    .success-box {{
        padding: 1rem;
        background-color: {Colors.SUCCESS}15;
        border-left: 4px solid {Colors.SUCCESS};
        border-radius: 4px;
        margin-bottom: 1rem;
    }}
    
    .warning-box {{
        padding: 1rem;
        background-color: {Colors.WARNING}15;
        border-left: 4px solid {Colors.WARNING};
        border-radius: 4px;
        margin-bottom: 1rem;
    }}
    
    .error-box {{
        padding: 1rem;
        background-color: {Colors.ERROR}15;
        border-left: 4px solid {Colors.ERROR};
        border-radius: 4px;
        margin-bottom: 1rem;
    }}
    
    /* Buttons - Primary color with hover */
    .stButton > button {{
        background-color: {Colors.PRIMARY};
        color: white;
        border: none;
        border-radius: 4px;
        font-weight: 600;
        transition: all 0.3s;
    }}
    
    .stButton > button:hover {{
        background-color: {Colors.ACCENT};
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(140, 166, 190, 0.3);
    }}
    
    /* Secondary buttons */
    .stButton > button[kind="secondary"] {{
        background-color: white;
        color: {Colors.PRIMARY};
        border: 2px solid {Colors.PRIMARY};
    }}
    
    .stButton > button[kind="secondary"]:hover {{
        background-color: {Colors.PRIMARY};
        color: white;
    }}
    
    /* Cards */
    .metric-card {{
        background: {Colors.BG_CARD};
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border: 1px solid {Colors.BORDER_LIGHT};
    }}
    
    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background-color: {Colors.BG_SIDEBAR};
    }}
    
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {{
        color: {Colors.PRIMARY};
    }}
    
    /* Chat messages */
    .stChatMessage {{
        padding: 1rem;
        margin-bottom: 1rem;
        border-radius: 8px;
        border: 1px solid {Colors.BORDER_LIGHT};
        background: {Colors.BG_CARD};
    }}
    
    /* File uploader */
    .uploadedFile {{
        background-color: {Colors.PRIMARY}10;
        border: 1px solid {Colors.PRIMARY};
        border-radius: 4px;
        padding: 0.5rem;
    }}
    
    /* Expanders */
    .streamlit-expanderHeader {{
        background-color: {Colors.BG_PAGE};
        border-radius: 4px;
        font-weight: 600;
        color: {Colors.TEXT_PRIMARY};
    }}
    
    /* Links */
    a {{
        color: {Colors.PRIMARY};
        text-decoration: none;
    }}
    
    a:hover {{
        color: {Colors.ACCENT};
        text-decoration: underline;
    }}
    
    /* Metrics */
    .stMetric {{
        background: {Colors.BG_CARD};
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid {Colors.BORDER_LIGHT};
    }}
    
    .stMetric label {{
        color: {Colors.TEXT_SECONDARY};
    }}
    
    .stMetric [data-testid="stMetricValue"] {{
        color: {Colors.PRIMARY};
    }}
    
    /* Hide Streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
    /* Smooth transitions */
    * {{
        transition: background-color 0.3s ease, color 0.3s ease;
    }}
    
    /* Responsive spacing */
    @media (max-width: 768px) {{
        .main .block-container {{
            padding: 1rem !important;
        }}
    }}
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
        warnings = []
        
        # Check LLM configuration
        if not cls.LLM_ENDPOINT:
            errors.append("LLM_ENDPOINT not configured in environment variables")
        if not cls.LLM_USERNAME:
            errors.append("LLM_USERNAME not configured in environment variables")
        if not cls.LLM_PASSWORD:
            errors.append("LLM_PASSWORD not configured in environment variables")
        
        # Check Supabase if enabled
        if cls.USE_SUPABASE_PERSISTENCE:
            if not cls.SUPABASE_URL:
                warnings.append("SUPABASE_URL not set (required when USE_SUPABASE_PERSISTENCE=True)")
            if not cls.SUPABASE_KEY:
                warnings.append("SUPABASE_KEY not set (required when USE_SUPABASE_PERSISTENCE=True)")
        
        # Print warnings
        if warnings and cls.ENABLE_DEBUG_MODE:
            print(" Configuration warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        
        return (len(errors) == 0, errors)
    
    @classmethod
    def get_config_summary(cls) -> dict:
        """Get summary of current configuration"""
        return {
            'app_name': cls.APP_NAME,
            'version': cls.APP_VERSION,
            'supabase_enabled': cls.USE_SUPABASE_PERSISTENCE,
            'supabase_configured': bool(cls.SUPABASE_URL and cls.SUPABASE_KEY),
            'llm_configured': bool(cls.LLM_ENDPOINT and cls.LLM_USERNAME and cls.LLM_PASSWORD),
            'llm_endpoint': cls.LLM_ENDPOINT[:50] + '...' if cls.LLM_ENDPOINT else 'Not configured',
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
if not is_valid:
    print(" Configuration errors:")
    for error in errors:
        print(f"  - {error}")
    print("\n Set these environment variables in Railway or .env file")
