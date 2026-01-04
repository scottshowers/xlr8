"""
XLR8 CHROMADB CLIENT - SINGLETON MANAGER
=========================================

Single source of truth for ChromaDB client instantiation.

PROBLEM SOLVED:
Multiple files were creating their own ChromaDB clients with different settings:
- utils/rag_handler.py: PersistentClient with allow_reset=True
- backend/utils/upload_enrichment.py: PersistentClient without allow_reset
- backend/utils/standards_processor.py: In-memory Client()

This caused conflicts and unpredictable behavior.

SOLUTION:
One singleton ChromaDB client used everywhere. Import get_chromadb_client() instead
of creating chromadb.PersistentClient() directly.

Author: XLR8 Team
Version: 1.0.0
Deploy to: utils/chromadb_client.py
"""

import os
import sys
import threading
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# SINGLETON IMPLEMENTATION
# =============================================================================

_CHROMADB_SINGLETON_KEY = '_xlr8_chromadb_client_instance'
_CHROMADB_SINGLETON_LOCK = threading.Lock()

# Default settings
DEFAULT_CHROMADB_PATH = "/data/chromadb"
FALLBACK_CHROMADB_PATH = ".chromadb"


def get_chromadb_client():
    """
    Get or create the singleton ChromaDB PersistentClient.
    
    Uses sys.modules to ensure ONE instance per process, regardless of
    whether this module is imported as 'utils.chromadb_client'
    or 'backend.utils.chromadb_client'.
    
    Thread-safe: uses lock to prevent race conditions.
    
    Returns:
        chromadb.PersistentClient or chromadb.Client (in-memory fallback)
    """
    # Fast path - if already exists, return immediately
    if _CHROMADB_SINGLETON_KEY in sys.modules:
        client = sys.modules[_CHROMADB_SINGLETON_KEY]
        # Verify it's a ChromaDB client (has heartbeat method)
        if hasattr(client, 'heartbeat'):
            return client
    
    # Slow path - need to create, use lock
    with _CHROMADB_SINGLETON_LOCK:
        # Double-check after acquiring lock
        if _CHROMADB_SINGLETON_KEY not in sys.modules:
            client = _create_chromadb_client()
            sys.modules[_CHROMADB_SINGLETON_KEY] = client
            logger.warning(f"[CHROMADB] Created singleton client (id={id(client)}, pid={os.getpid()})")
        else:
            client = sys.modules[_CHROMADB_SINGLETON_KEY]
            # Verify it's valid
            if not hasattr(client, 'heartbeat'):
                logger.warning("[CHROMADB] Invalid singleton, recreating...")
                client = _create_chromadb_client()
                sys.modules[_CHROMADB_SINGLETON_KEY] = client
        
        return client


def _create_chromadb_client():
    """
    Create a ChromaDB client with standardized settings.
    
    Tries PersistentClient first, falls back to in-memory if that fails.
    """
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError:
        logger.error("[CHROMADB] chromadb package not installed!")
        raise ImportError("chromadb package is required. Run: pip install chromadb")
    
    # Determine persist directory
    persist_directory = os.getenv('CHROMADB_PATH', DEFAULT_CHROMADB_PATH)
    
    # Check if we can use the primary path
    if not os.path.exists(persist_directory):
        try:
            os.makedirs(persist_directory, exist_ok=True)
            logger.info(f"[CHROMADB] Created storage directory: {persist_directory}")
        except (OSError, PermissionError) as e:
            logger.warning(f"[CHROMADB] Cannot create {persist_directory}: {e}")
            persist_directory = None
    
    # Fallback to local directory
    if persist_directory is None:
        persist_directory = os.path.join(os.getcwd(), FALLBACK_CHROMADB_PATH)
        try:
            os.makedirs(persist_directory, exist_ok=True)
            logger.warning(f"[CHROMADB] Using local fallback: {persist_directory}")
        except (OSError, PermissionError):
            persist_directory = None
    
    # Try to create PersistentClient
    if persist_directory:
        try:
            client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True  # Standardized setting
                )
            )
            logger.info(f"[CHROMADB] PersistentClient initialized at {persist_directory}")
            return client
        except Exception as e:
            logger.error(f"[CHROMADB] Failed to create PersistentClient: {e}")
    
    # Ultimate fallback: in-memory client
    logger.warning("[CHROMADB] Falling back to in-memory client (data will not persist)")
    return chromadb.Client()


def get_chromadb_collection(
    name: str = "documents",
    metadata: dict = None
):
    """
    Get or create a ChromaDB collection.
    
    Args:
        name: Collection name (default: "documents")
        metadata: Collection metadata (default: cosine similarity)
    
    Returns:
        ChromaDB collection
    """
    client = get_chromadb_client()
    
    if metadata is None:
        metadata = {"hnsw:space": "cosine"}
    
    return client.get_or_create_collection(
        name=name,
        metadata=metadata
    )


def reset_chromadb_client():
    """
    Reset the singleton ChromaDB client.
    
    Use this if you need to force reconnection, e.g., after issues or for testing.
    """
    if _CHROMADB_SINGLETON_KEY in sys.modules:
        del sys.modules[_CHROMADB_SINGLETON_KEY]
        logger.info("[CHROMADB] Singleton client reset")


# =============================================================================
# CONVENIENCE EXPORTS
# =============================================================================

def get_documents_collection():
    """Get the main documents collection."""
    return get_chromadb_collection("documents")


def get_standards_collection():
    """Get the standards/rules collection."""
    return get_chromadb_collection(
        name="xlr8_standards_rules",
        metadata={"description": "Extracted compliance rules"}
    )
