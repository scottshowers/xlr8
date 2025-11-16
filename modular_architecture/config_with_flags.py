"""
Application Configuration with Feature Flag System
Centralized settings for XLR8

FEATURE FLAGS: Control which experimental/new features are enabled
Team members can toggle these to test their work without affecting production
"""

import os
from typing import Dict, Any


class FeatureFlags:
    """
    Feature flag system for safe module deployment.
    
    How to use:
    1. Team member develops new feature
    2. Merge to main with flag = False
    3. Test in production with flag = True
    4. If good, make it default
    5. If bad, flip back to False (instant rollback!)
    
    NO NEED TO REVERT CODE - JUST FLIP FLAGS!
    """
    
    # ========================================
    # PDF PARSER FLAGS
    # ========================================
    
    USE_IMPROVED_PDF_PARSER = False
    """
    Enable improved PDF parser with better table extraction.
    Owner: [Team Member Name]
    Status: In Development
    Rollback: Set to False
    """
    
    USE_OCR_PARSER = False
    """
    Enable OCR-based PDF parsing for scanned documents.
    Owner: [Team Member Name]
    Status: Experimental
    Rollback: Set to False
    """
    
    ENABLE_AI_PDF_ANALYSIS = False
    """
    Use AI to analyze PDF structure before parsing.
    Owner: [Team Member Name]
    Status: Experimental
    Rollback: Set to False
    """
    
    # ========================================
    # RAG SYSTEM FLAGS
    # ========================================
    
    USE_ADVANCED_RAG = False
    """
    Enable advanced RAG with reranking and hybrid search.
    Owner: [Team Member Name]
    Status: In Development
    Rollback: Set to False
    """
    
    USE_PINECONE_RAG = False
    """
    Use Pinecone instead of ChromaDB for vector storage.
    Owner: [Team Member Name]
    Status: Experimental
    Rollback: Set to False
    """
    
    ENABLE_RAG_CACHING = True
    """
    Cache RAG query results for faster responses.
    Owner: Core Team
    Status: Production
    Rollback: Set to False if causing memory issues
    """
    
    # ========================================
    # LLM FLAGS
    # ========================================
    
    USE_GPT4_FALLBACK = False
    """
    Use GPT-4 as fallback when local LLM fails.
    Owner: [Team Member Name]
    Status: Experimental
    Requires: OpenAI API key
    Rollback: Set to False
    """
    
    ENABLE_MULTI_MODEL_COMPARISON = False
    """
    Show responses from multiple LLMs side-by-side.
    Owner: [Team Member Name]
    Status: In Development
    Rollback: Set to False
    """
    
    # ========================================
    # TEMPLATE GENERATION FLAGS
    # ========================================
    
    USE_ADVANCED_TEMPLATES = False
    """
    Enable advanced template generation with AI enhancement.
    Owner: [Team Member Name]
    Status: In Development
    Rollback: Set to False
    """
    
    ENABLE_TEMPLATE_VALIDATION = True
    """
    Validate templates against UKG schemas before generation.
    Owner: Core Team
    Status: Production
    Rollback: Set to False if causing delays
    """
    
    USE_EXCEL_MACROS = False
    """
    Generate Excel files with VBA macros for automation.
    Owner: [Team Member Name]
    Status: Experimental
    Security: Review required
    Rollback: Set to False
    """
    
    # ========================================
    # UI/UX FLAGS
    # ========================================
    
    ENABLE_DARK_MODE = False
    """
    Enable dark mode theme.
    Owner: [Team Member Name]
    Status: In Development
    Rollback: Set to False
    """
    
    USE_NEW_CHAT_INTERFACE = True
    """
    Use new Claude-style chat interface.
    Owner: Core Team
    Status: Production
    Rollback: Set to False to use old interface
    """
    
    SHOW_DEBUG_INFO = False
    """
    Show debug information for developers.
    Owner: Core Team
    Status: Development Only
    Rollback: Always False in production
    """
    
    # ========================================
    # INTEGRATION FLAGS
    # ========================================
    
    ENABLE_UKG_API_INTEGRATION = False
    """
    Enable direct UKG API integration.
    Owner: [Team Member Name]
    Status: Experimental
    Requires: UKG API credentials
    Rollback: Set to False
    """
    
    ENABLE_SLACK_NOTIFICATIONS = False
    """
    Send notifications to Slack.
    Owner: [Team Member Name]
    Status: Experimental
    Requires: Slack webhook
    Rollback: Set to False
    """
    
    # ========================================
    # PERFORMANCE FLAGS
    # ========================================
    
    ENABLE_PARALLEL_PROCESSING = True
    """
    Process multiple documents in parallel.
    Owner: Core Team
    Status: Production
    Rollback: Set to False if causing issues
    """
    
    USE_AGGRESSIVE_CACHING = False
    """
    Cache everything aggressively for speed.
    Owner: [Team Member Name]
    Status: Experimental
    Warning: High memory usage
    Rollback: Set to False
    """
    
    @classmethod
    def get_all_flags(cls) -> Dict[str, bool]:
        """Get all feature flags and their status."""
        return {
            key: getattr(cls, key)
            for key in dir(cls)
            if key.isupper() and not key.startswith('_')
        }
    
    @classmethod
    def get_enabled_flags(cls) -> list:
        """Get list of currently enabled flags."""
        return [
            key for key, value in cls.get_all_flags().items()
            if value is True
        ]


class AppConfig:
    """Main application configuration"""
    
    # App Info
    APP_NAME = "XLR8"
    APP_ICON = "⚡"
    VERSION = "3.1"  # Incremented for modular architecture
    TAGLINE = "UKG Implementation Accelerator by HCMPACT"
    
    # LLM Configuration
    LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "http://178.156.190.64:11435")
    LLM_DEFAULT_MODEL = os.getenv("LLM_MODEL", "deepseek-r1:7b")
    LLM_USERNAME = os.getenv("LLM_USERNAME", "xlr8")
    LLM_PASSWORD = os.getenv("LLM_PASSWORD", "Argyle76226#")
    
    # RAG Configuration
    RAG_PERSIST_DIR = os.getenv("CHROMADB_PATH", "/root/.xlr8_chroma")
    
    # Embedding Configuration
    EMBED_ENDPOINT = os.getenv("EMBED_ENDPOINT", "http://178.156.190.64:11435")
    EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
    
    # File Upload Limits
    MAX_FILE_SIZE_MB = 200
    
    # Module Selection Based on Feature Flags
    @staticmethod
    def get_pdf_parser():
        """Get the appropriate PDF parser based on feature flags."""
        if FeatureFlags.USE_OCR_PARSER:
            from utils.parsers.ocr_pdf_parser import OCRPDFParser
            return OCRPDFParser()
        elif FeatureFlags.USE_IMPROVED_PDF_PARSER:
            from utils.parsers.improved_pdf_parser import ImprovedPDFParser
            return ImprovedPDFParser()
        else:
            # Default/original parser
            from utils.parsers.pdf_parser import EnhancedPayrollParser
            return EnhancedPayrollParser()
    
    @staticmethod
    def get_rag_handler():
        """Get the appropriate RAG handler based on feature flags."""
        if FeatureFlags.USE_PINECONE_RAG:
            from utils.rag.pinecone_handler import PineconeRAGHandler
            return PineconeRAGHandler()
        elif FeatureFlags.USE_ADVANCED_RAG:
            from utils.rag.advanced_handler import AdvancedRAGHandler
            return AdvancedRAGHandler()
        else:
            # Default/original handler
            from utils.rag.handler import RAGHandler
            return RAGHandler()
    
    @staticmethod
    def get_template_generator():
        """Get the appropriate template generator based on feature flags."""
        if FeatureFlags.USE_ADVANCED_TEMPLATES:
            from utils.templates.advanced_generator import AdvancedTemplateGenerator
            return AdvancedTemplateGenerator()
        else:
            # Default/original generator
            from utils.templates.basic_generator import BasicTemplateGenerator
            return BasicTemplateGenerator()
    
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
    
    /* Feature flag indicator */
    .feature-flag-enabled {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        background-color: #4CAF50;
        color: white;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    
    .feature-flag-disabled {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        background-color: #9E9E9E;
        color: white;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: bold;
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


# Helper function to check if experimental features are enabled
def has_experimental_features() -> bool:
    """Check if any experimental features are enabled."""
    experimental_flags = [
        'USE_OCR_PARSER',
        'ENABLE_AI_PDF_ANALYSIS',
        'USE_ADVANCED_RAG',
        'USE_PINECONE_RAG',
        'USE_GPT4_FALLBACK',
        'ENABLE_MULTI_MODEL_COMPARISON',
        'USE_ADVANCED_TEMPLATES',
        'USE_EXCEL_MACROS',
        'ENABLE_UKG_API_INTEGRATION',
        'USE_AGGRESSIVE_CACHING'
    ]
    
    return any(getattr(FeatureFlags, flag, False) for flag in experimental_flags)


# Helper function for development mode
def is_development_mode() -> bool:
    """Check if running in development mode."""
    return FeatureFlags.SHOW_DEBUG_INFO or os.getenv("ENVIRONMENT") == "development"
