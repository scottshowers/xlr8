"""
XLR8 Configuration
All application settings in one place

SECURITY NOTE: This file contains hardcoded credentials for the LOCAL LLM only.
UKG API credentials and other sensitive data are stored in session state (not persisted).
"""

class AppConfig:
    """Main application configuration"""
    
    # Application Info
    APP_NAME = "XLR8 by HCMPACT"
    VERSION = "3.0.0"
    TAGLINE = "UKG Implementation Accelerator"
    APP_ICON = "⚡"
    
    # LLM Configuration (Local Ollama)
    LLM_ENDPOINT = "http://178.156.190.64:11435"
    LLM_USERNAME = "xlr8"
    LLM_PASSWORD = "Argyle76226#"
    LLM_DEFAULT_MODEL = "mistral:7b"
    LLM_TIMEOUT = 300  # seconds
    
    # Available LLM Models
    LLM_MODELS = {
        "mistral:7b": {
            "name": "⚡ Fast (Recommended)",
            "description": "Perfect for: PDF parsing, categorization, summaries",
            "ram": "5GB",
            "speed": "Fast"
        },
        "mixtral:8x7b": {
            "name": "🧠 Thorough",
            "description": "Best for: Strategic analysis, complex reasoning",
            "ram": "26GB",
            "speed": "Slower"
        }
    }
    
    # RAG Configuration
    RAG_CHUNK_SIZE = 500
    RAG_CHUNK_OVERLAP = 50
    RAG_SEARCH_RESULTS = 5
    RAG_PERSIST_DIR = "/root/.xlr8_chroma"
    RAG_EMBED_MODEL = "nomic-embed-text"
    
    # HCMPACT Categories
    HCMPACT_CATEGORIES = [
        "PRO Core",
        "WFM",
        "Templates",
        "Prompts",
        "Ben Admin",
        "Recruiting",
        "Onboarding",
        "Performance",
        "Compensation",
        "Succession",
        "Doc Manager",
        "UKG Service Delivery",
        "Project Management",
        "Search & Selection",
        "Change Management",
        "HCMPACT Service Delivery",
        "Industry Research"
    ]
    
    # File Upload Settings
    MAX_FILE_SIZE_MB = 200
    ALLOWED_EXTENSIONS = {
        'pdf': ['pdf'],
        'excel': ['xlsx', 'xls', 'csv'],
        'word': ['docx', 'doc'],
        'text': ['txt', 'md']
    }
    
    # Custom CSS Theme (Darker Muted Blue)
    CUSTOM_CSS = """
    <style>
        /* Modern styling with darker muted blues */
        .main {
            padding: 2rem;
            background-color: #e8edf2;
        }
        
        .stButton>button {
            width: 100%;
            border-radius: 6px;
            height: 3rem;
            font-weight: 600;
            transition: all 0.3s;
            background-color: #6d8aa0;
            color: white;
            border: none;
        }
        
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(109, 138, 160, 0.4);
            background-color: #7d96a8;
        }
        
        .success-box {
            background-color: rgba(109, 138, 160, 0.15);
            border-left: 4px solid #6d8aa0;
            padding: 1rem;
            border-radius: 6px;
            margin: 1rem 0;
            color: #1a2332;
        }
        
        .info-box {
            background-color: rgba(125, 150, 168, 0.15);
            border-left: 4px solid #7d96a8;
            padding: 1rem;
            border-radius: 6px;
            margin: 1rem 0;
            color: #1a2332;
        }
        
        .warning-box {
            background-color: rgba(140, 166, 190, 0.15);
            border-left: 4px solid #8ca6be;
            padding: 1rem;
            border-radius: 6px;
            margin: 1rem 0;
            color: #1a2332;
        }
        
        /* Sidebar styling */
        section[data-testid="stSidebar"] {
            background-color: white;
            border-right: 1px solid #e1e8ed;
        }
        
        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
            border-bottom: 2px solid #e1e8ed;
        }
        
        .stTabs [data-baseweb="tab"] {
            background-color: transparent;
            border-bottom: 3px solid transparent;
            color: #6d8aa0;
            padding: 0.75rem 1.5rem;
            font-weight: 600;
        }
        
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
            background-color: rgba(109, 138, 160, 0.1);
            border-bottom: 3px solid #6d8aa0;
            color: #1a2332;
        }
        
        h1, h2, h3 {
            color: #1a2332;
        }
    </style>
    """


class SecurityConfig:
    """Security-related configuration"""
    
    # Session timeout (minutes)
    SESSION_TIMEOUT = 120
    
    # Audit log retention (days)
    AUDIT_RETENTION_DAYS = 365
    
    # Password requirements (for future user management)
    MIN_PASSWORD_LENGTH = 12
    REQUIRE_SPECIAL_CHAR = True
    REQUIRE_NUMBER = True
    REQUIRE_UPPERCASE = True
    
    # API Rate Limiting (requests per minute)
    API_RATE_LIMIT = 60
    
    # Allowed IPs (None = allow all)
    ALLOWED_IPS = None


class FeatureFlags:
    """Feature toggles for progressive rollout"""
    
    ENABLE_USER_MANAGEMENT = False  # Not implemented yet
    ENABLE_AUDIT_LOGS = False  # Not implemented yet
    ENABLE_UKG_API = True
    ENABLE_ANTHROPIC_API = False  # Cloud API disabled by default
    ENABLE_TEMPLATE_GENERATION = True
    ENABLE_RAG_SEARCH = True
    ENABLE_TESTING_MODULE = True
