"""
Unified Registration Service for XLR8
======================================

SINGLE SOURCE OF TRUTH for all data registration.

Every upload path MUST use this service:
- upload.py (regular files)
- upload.py (standards mode)  
- register_extractor.py (payroll registers)
- Any future upload mechanisms

This ensures:
- Consistent DocumentRegistry entries
- Complete lineage tracking
- File hashing and integrity
- Uploader accountability
- Timing metrics
- Error capture
- Quality scoring

Deploy to: backend/utils/registration_service.py

Usage:
    from utils.registration_service import RegistrationService
    
    # For structured data (Excel/CSV → DuckDB)
    result = RegistrationService.register_structured(
        filename="payroll.xlsx",
        project_id=project_id,
        tables_created=["tea1000_payroll"],
        row_count=1500,
        file_content=content_bytes,
        uploaded_by_id=user_id,
        uploaded_by_email=user_email,
        source="upload"  # or "register_extractor"
    )
    
    # For embedded data (PDF/DOCX → ChromaDB)
    result = RegistrationService.register_embedded(
        filename="handbook.pdf",
        project_id=project_id,
        chunk_count=45,
        truth_type="intent",
        file_content=content_bytes,
        uploaded_by_id=user_id
    )
    
    # For standards/rules
    result = RegistrationService.register_standards(
        filename="flsa_regulations.pdf",
        domain="compliance",
        rules_extracted=23,
        file_content=content_bytes
    )

Author: XLR8 Team
Version: 1.0.0
"""

import hashlib
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class RegistrationSource(Enum):
    """Where the registration originated from."""
    UPLOAD = "upload"                    # Standard upload.py
    REGISTER_EXTRACTOR = "register_extractor"  # Payroll register extraction
    STANDARDS = "standards"              # Standards/rules upload
    MIGRATION = "migration"              # Data migration/import
    API = "api"                          # Direct API call
    SYSTEM = "system"                    # System-generated


class StorageType(Enum):
    """Where the data is stored."""
    DUCKDB = "duckdb"
    CHROMADB = "chromadb"
    BOTH = "both"
    RULES = "rules"  # Standards rule registry


class TruthType(Enum):
    """The Three Truths classification."""
    REALITY = "reality"        # Customer data (DuckDB)
    INTENT = "intent"          # Customer docs (ChromaDB)
    REFERENCE = "reference"    # Best practice/standards (ChromaDB)


@dataclass
class RegistrationResult:
    """Result of a registration operation."""
    success: bool
    filename: str
    registry_id: Optional[str] = None
    lineage_edges: int = 0
    file_hash: Optional[str] = None
    error: Optional[str] = None
    warnings: List[str] = None
    timing_ms: int = 0
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "filename": self.filename,
            "registry_id": self.registry_id,
            "lineage_edges": self.lineage_edges,
            "file_hash": self.file_hash,
            "error": self.error,
            "warnings": self.warnings,
            "timing_ms": self.timing_ms
        }


# =============================================================================
# REGISTRATION SERVICE
# =============================================================================

class RegistrationService:
    """
    Unified registration service for all XLR8 data ingestion.
    
    EVERY upload path must use this service to ensure:
    - Consistent registry entries
    - Complete lineage tracking
    - Proper metadata capture
    """
    
    # ==========================================================================
    # CORE UTILITIES
    # ==========================================================================
    
    @staticmethod
    def _calculate_hash(content: bytes) -> str:
        """Calculate SHA-256 hash of file content."""
        if not content:
            return None
        return hashlib.sha256(content).hexdigest()
    
    @staticmethod
    def _get_supabase():
        """Get Supabase client."""
        try:
            from utils.database.supabase_client import get_supabase
            return get_supabase()
        except ImportError:
            try:
                from backend.utils.database.supabase_client import get_supabase
                return get_supabase()
            except ImportError:
                return None
    
    @staticmethod
    def _get_models():
        """Get model classes."""
        try:
            from utils.database.models import DocumentRegistryModel, LineageModel, ProjectModel
            return DocumentRegistryModel, LineageModel, ProjectModel
        except ImportError:
            try:
                from backend.utils.database.models import DocumentRegistryModel, LineageModel, ProjectModel
                return DocumentRegistryModel, LineageModel, ProjectModel
            except ImportError:
                logger.error("[REGISTRATION] Could not import models")
                return None, None, None
    
    @staticmethod
    def _resolve_project_id(project: str) -> Optional[str]:
        """Resolve project name to UUID."""
        if not project:
            return None
        
        # Check if already a UUID
        if len(project) == 36 and '-' in project:
            return project
        
        # Global/reference library projects have no project_id
        global_names = ['global', '__global__', 'global/universal', 'reference library', 
                        'reference_library', '__standards__', 'standards']
        if project.lower() in global_names:
            return None
        
        # Look up by name
        _, _, ProjectModel = RegistrationService._get_models()
        if ProjectModel:
            proj = ProjectModel.get_by_name(project)
            if proj:
                return proj.get('id')
        
        return None
    
    # ==========================================================================
    # MAIN REGISTRATION METHODS
    # ==========================================================================
    
    @staticmethod
    def register_structured(
        filename: str,
        project: str = None,
        project_id: str = None,
        tables_created: List[str] = None,
        row_count: int = 0,
        column_count: int = 0,
        sheet_count: int = None,
        file_content: bytes = None,
        file_size: int = None,
        file_type: str = None,
        uploaded_by_id: str = None,
        uploaded_by_email: str = None,
        job_id: str = None,
        source: RegistrationSource = RegistrationSource.UPLOAD,
        classification_confidence: float = 0.9,
        content_domain: List[str] = None,
        processing_time_ms: int = None,
        parse_time_ms: int = None,
        storage_time_ms: int = None,
        metadata: Dict[str, Any] = None
    ) -> RegistrationResult:
        """
        Register structured data (Excel/CSV → DuckDB).
        
        Called by:
        - upload.py for Excel/CSV files
        - register_extractor.py for payroll registers
        - Smart PDF analyzer for tabular PDFs
        """
        start = time.time()
        result = RegistrationResult(success=False, filename=filename)
        
        try:
            DocumentRegistryModel, LineageModel, _ = RegistrationService._get_models()
            
            if not DocumentRegistryModel:
                result.error = "DocumentRegistryModel not available"
                return result
            
            # Resolve project_id if not provided
            if not project_id and project:
                project_id = RegistrationService._resolve_project_id(project)
            
            # Calculate file hash
            file_hash = None
            if file_content:
                file_hash = RegistrationService._calculate_hash(file_content)
                result.file_hash = file_hash
                if not file_size:
                    file_size = len(file_content)
            
            # Infer file type if not provided
            if not file_type:
                ext = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
                file_type = ext
            
            # Determine if global
            is_global = project_id is None and project and project.lower() in [
                'global', '__global__', 'global/universal', 'reference library'
            ]
            
            # Register in DocumentRegistry
            registry_result = DocumentRegistryModel.register(
                filename=filename,
                file_type=file_type,
                truth_type='reality',  # Structured data = customer reality
                classification_method='auto_detected' if source == RegistrationSource.REGISTER_EXTRACTOR else 'content_analysis',
                classification_confidence=classification_confidence,
                content_domain=content_domain or [],
                storage_type='duckdb',
                project_id=project_id,
                is_global=is_global,
                duckdb_tables=tables_created or [],
                row_count=row_count,
                sheet_count=sheet_count,
                parse_status='success',
                processing_time_ms=processing_time_ms,
                parse_time_ms=parse_time_ms,
                storage_time_ms=storage_time_ms,
                file_hash=file_hash,
                file_size_bytes=file_size,
                uploaded_by_id=uploaded_by_id,
                uploaded_by_email=uploaded_by_email,
                metadata={
                    **(metadata or {}),
                    'registration_source': source.value if isinstance(source, RegistrationSource) else source,
                    'column_count': column_count,
                    'registered_at': datetime.utcnow().isoformat()
                }
            )
            
            if registry_result:
                result.registry_id = registry_result.get('id')
                logger.info(f"[REGISTRATION] Registered structured: {filename} ({row_count} rows)")
            else:
                result.warnings.append("Registry insert returned None")
            
            # Track lineage: file → table(s)
            if LineageModel and tables_created:
                for table_name in tables_created:
                    LineageModel.track(
                        source_type=LineageModel.NODE_FILE,
                        source_id=filename,
                        target_type=LineageModel.NODE_TABLE,
                        target_id=table_name,
                        relationship=LineageModel.REL_PARSED,
                        project_id=project_id,
                        job_id=job_id,
                        created_by_id=uploaded_by_id,
                        metadata={
                            'rows': row_count,
                            'source': source.value if isinstance(source, RegistrationSource) else source
                        }
                    )
                    result.lineage_edges += 1
                
                logger.info(f"[REGISTRATION] Tracked lineage: {filename} → {len(tables_created)} table(s)")
            
            result.success = True
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"[REGISTRATION] Structured registration failed: {e}")
        
        result.timing_ms = int((time.time() - start) * 1000)
        return result
    
    @staticmethod
    def register_embedded(
        filename: str,
        project: str = None,
        project_id: str = None,
        chunk_count: int = 0,
        truth_type: str = "intent",
        file_content: bytes = None,
        file_size: int = None,
        file_type: str = None,
        uploaded_by_id: str = None,
        uploaded_by_email: str = None,
        job_id: str = None,
        source: RegistrationSource = RegistrationSource.UPLOAD,
        classification_confidence: float = 0.8,
        content_domain: List[str] = None,
        functional_area: str = None,
        processing_time_ms: int = None,
        embedding_time_ms: int = None,
        storage_time_ms: int = None,
        metadata: Dict[str, Any] = None
    ) -> RegistrationResult:
        """
        Register embedded/vector data (PDF/DOCX/TXT → ChromaDB).
        
        Called by:
        - upload.py for unstructured documents
        - Any semantic document ingestion
        """
        start = time.time()
        result = RegistrationResult(success=False, filename=filename)
        
        try:
            DocumentRegistryModel, LineageModel, _ = RegistrationService._get_models()
            
            if not DocumentRegistryModel:
                result.error = "DocumentRegistryModel not available"
                return result
            
            # Resolve project_id
            if not project_id and project:
                project_id = RegistrationService._resolve_project_id(project)
            
            # Calculate file hash
            file_hash = None
            if file_content:
                file_hash = RegistrationService._calculate_hash(file_content)
                result.file_hash = file_hash
                if not file_size:
                    file_size = len(file_content)
            
            # Infer file type
            if not file_type:
                ext = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
                file_type = ext
            
            # Determine if global
            is_global = truth_type == 'reference' or (
                project_id is None and project and project.lower() in [
                    'global', '__global__', 'global/universal', 'reference library'
                ]
            )
            
            # Map truth_type to storage
            storage_type = 'chromadb'
            
            # Register in DocumentRegistry
            registry_result = DocumentRegistryModel.register(
                filename=filename,
                file_type=file_type,
                truth_type=truth_type,
                classification_method='content_analysis',
                classification_confidence=classification_confidence,
                content_domain=content_domain or [],
                storage_type=storage_type,
                project_id=project_id,
                is_global=is_global,
                chunk_count=chunk_count,
                parse_status='success',
                processing_time_ms=processing_time_ms,
                embedding_time_ms=embedding_time_ms,
                storage_time_ms=storage_time_ms,
                file_hash=file_hash,
                file_size_bytes=file_size,
                uploaded_by_id=uploaded_by_id,
                uploaded_by_email=uploaded_by_email,
                metadata={
                    **(metadata or {}),
                    'registration_source': source.value if isinstance(source, RegistrationSource) else source,
                    'functional_area': functional_area,
                    'registered_at': datetime.utcnow().isoformat()
                }
            )
            
            if registry_result:
                result.registry_id = registry_result.get('id')
                logger.info(f"[REGISTRATION] Registered embedded: {filename} ({chunk_count} chunks)")
            else:
                result.warnings.append("Registry insert returned None")
            
            # Track lineage: file → chunks
            if LineageModel and chunk_count > 0:
                LineageModel.track(
                    source_type=LineageModel.NODE_FILE,
                    source_id=filename,
                    target_type=LineageModel.NODE_CHUNK,
                    target_id=f"{filename}:chunks",
                    relationship=LineageModel.REL_EMBEDDED,
                    project_id=project_id,
                    job_id=job_id,
                    created_by_id=uploaded_by_id,
                    metadata={
                        'chunk_count': chunk_count,
                        'truth_type': truth_type,
                        'source': source.value if isinstance(source, RegistrationSource) else source
                    }
                )
                result.lineage_edges += 1
                logger.info(f"[REGISTRATION] Tracked lineage: {filename} → {chunk_count} chunks")
            
            result.success = True
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"[REGISTRATION] Embedded registration failed: {e}")
        
        result.timing_ms = int((time.time() - start) * 1000)
        return result
    
    @staticmethod
    def register_standards(
        filename: str,
        domain: str = "general",
        rules_extracted: int = 0,
        document_id: str = None,
        title: str = None,
        page_count: int = None,
        file_content: bytes = None,
        file_size: int = None,
        file_type: str = None,
        uploaded_by_id: str = None,
        uploaded_by_email: str = None,
        metadata: Dict[str, Any] = None
    ) -> RegistrationResult:
        """
        Register standards/rules documents.
        
        Called by:
        - upload.py standards mode
        - Standards processor
        
        These are GLOBAL/REFERENCE documents that apply across all projects.
        """
        start = time.time()
        result = RegistrationResult(success=False, filename=filename)
        
        try:
            DocumentRegistryModel, LineageModel, _ = RegistrationService._get_models()
            
            if not DocumentRegistryModel:
                result.error = "DocumentRegistryModel not available"
                return result
            
            # Calculate file hash
            file_hash = None
            if file_content:
                file_hash = RegistrationService._calculate_hash(file_content)
                result.file_hash = file_hash
                if not file_size:
                    file_size = len(file_content)
            
            # Infer file type
            if not file_type:
                ext = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
                file_type = ext
            
            # Standards are ALWAYS global reference documents
            registry_result = DocumentRegistryModel.register(
                filename=filename,
                file_type=file_type,
                truth_type='reference',  # Standards = best practice/reference
                classification_method='standards_processor',
                classification_confidence=0.95,
                content_domain=[domain, 'compliance', 'standards'],
                storage_type='rules',  # Special storage type for standards
                project_id=None,  # Global
                is_global=True,
                parse_status='success',
                page_count=page_count,
                file_hash=file_hash,
                file_size_bytes=file_size,
                uploaded_by_id=uploaded_by_id,
                uploaded_by_email=uploaded_by_email,
                metadata={
                    **(metadata or {}),
                    'registration_source': 'standards',
                    'document_id': document_id,
                    'title': title,
                    'domain': domain,
                    'rules_extracted': rules_extracted,
                    'registered_at': datetime.utcnow().isoformat()
                }
            )
            
            if registry_result:
                result.registry_id = registry_result.get('id')
                logger.info(f"[REGISTRATION] Registered standards: {filename} ({rules_extracted} rules)")
            else:
                result.warnings.append("Registry insert returned None")
            
            # Track lineage: file → rules
            if LineageModel and rules_extracted > 0:
                LineageModel.track(
                    source_type=LineageModel.NODE_FILE,
                    source_id=filename,
                    target_type='rules',  # Special node type for standards
                    target_id=document_id or f"{filename}:rules",
                    relationship='extracted',
                    project_id=None,  # Global
                    created_by_id=uploaded_by_id,
                    metadata={
                        'rules_count': rules_extracted,
                        'domain': domain
                    }
                )
                result.lineage_edges += 1
                logger.info(f"[REGISTRATION] Tracked lineage: {filename} → {rules_extracted} rules")
            
            result.success = True
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"[REGISTRATION] Standards registration failed: {e}")
        
        result.timing_ms = int((time.time() - start) * 1000)
        return result
    
    @staticmethod
    def register_hybrid(
        filename: str,
        project: str = None,
        project_id: str = None,
        tables_created: List[str] = None,
        row_count: int = 0,
        chunk_count: int = 0,
        truth_type: str = "reality",
        file_content: bytes = None,
        file_size: int = None,
        file_type: str = None,
        uploaded_by_id: str = None,
        uploaded_by_email: str = None,
        job_id: str = None,
        source: RegistrationSource = RegistrationSource.UPLOAD,
        metadata: Dict[str, Any] = None
    ) -> RegistrationResult:
        """
        Register hybrid data (both structured AND embedded).
        
        Called by:
        - Smart PDF analyzer (tables + text from same PDF)
        - Any file that goes to both DuckDB AND ChromaDB
        """
        start = time.time()
        result = RegistrationResult(success=False, filename=filename)
        
        try:
            DocumentRegistryModel, LineageModel, _ = RegistrationService._get_models()
            
            if not DocumentRegistryModel:
                result.error = "DocumentRegistryModel not available"
                return result
            
            # Resolve project_id
            if not project_id and project:
                project_id = RegistrationService._resolve_project_id(project)
            
            # Calculate file hash
            file_hash = None
            if file_content:
                file_hash = RegistrationService._calculate_hash(file_content)
                result.file_hash = file_hash
                if not file_size:
                    file_size = len(file_content)
            
            # Infer file type
            if not file_type:
                ext = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
                file_type = ext
            
            # Register with BOTH storage type
            registry_result = DocumentRegistryModel.register(
                filename=filename,
                file_type=file_type,
                truth_type=truth_type,
                classification_method='smart_pdf_analyzer',
                classification_confidence=0.9,
                storage_type='both',
                project_id=project_id,
                is_global=False,
                duckdb_tables=tables_created or [],
                row_count=row_count,
                chunk_count=chunk_count,
                parse_status='success',
                file_hash=file_hash,
                file_size_bytes=file_size,
                uploaded_by_id=uploaded_by_id,
                uploaded_by_email=uploaded_by_email,
                metadata={
                    **(metadata or {}),
                    'registration_source': source.value if isinstance(source, RegistrationSource) else source,
                    'hybrid': True,
                    'registered_at': datetime.utcnow().isoformat()
                }
            )
            
            if registry_result:
                result.registry_id = registry_result.get('id')
                logger.info(f"[REGISTRATION] Registered hybrid: {filename} ({row_count} rows, {chunk_count} chunks)")
            
            # Track lineage for BOTH paths
            if LineageModel:
                # File → Tables
                if tables_created:
                    for table_name in tables_created:
                        LineageModel.track(
                            source_type=LineageModel.NODE_FILE,
                            source_id=filename,
                            target_type=LineageModel.NODE_TABLE,
                            target_id=table_name,
                            relationship=LineageModel.REL_PARSED,
                            project_id=project_id,
                            job_id=job_id,
                            created_by_id=uploaded_by_id,
                            metadata={'rows': row_count, 'source': 'smart_pdf'}
                        )
                        result.lineage_edges += 1
                
                # File → Chunks
                if chunk_count > 0:
                    LineageModel.track(
                        source_type=LineageModel.NODE_FILE,
                        source_id=filename,
                        target_type=LineageModel.NODE_CHUNK,
                        target_id=f"{filename}:chunks",
                        relationship=LineageModel.REL_EMBEDDED,
                        project_id=project_id,
                        job_id=job_id,
                        created_by_id=uploaded_by_id,
                        metadata={'chunk_count': chunk_count, 'source': 'smart_pdf'}
                    )
                    result.lineage_edges += 1
            
            result.success = True
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"[REGISTRATION] Hybrid registration failed: {e}")
        
        result.timing_ms = int((time.time() - start) * 1000)
        return result
    
    # ==========================================================================
    # ERROR REGISTRATION
    # ==========================================================================
    
    @staticmethod
    def register_failed(
        filename: str,
        error_message: str,
        error_details: Dict[str, Any] = None,
        project: str = None,
        project_id: str = None,
        file_content: bytes = None,
        file_type: str = None,
        uploaded_by_id: str = None,
        uploaded_by_email: str = None,
        source: RegistrationSource = RegistrationSource.UPLOAD
    ) -> RegistrationResult:
        """
        Register a failed upload attempt.
        
        Even failures should be tracked for debugging and audit.
        """
        start = time.time()
        result = RegistrationResult(success=False, filename=filename)
        
        try:
            DocumentRegistryModel, _, _ = RegistrationService._get_models()
            
            if not DocumentRegistryModel:
                result.error = "DocumentRegistryModel not available"
                return result
            
            # Resolve project_id
            if not project_id and project:
                project_id = RegistrationService._resolve_project_id(project)
            
            # Calculate file hash even for failures
            file_hash = None
            file_size = None
            if file_content:
                file_hash = RegistrationService._calculate_hash(file_content)
                file_size = len(file_content)
            
            # Register with failed status
            registry_result = DocumentRegistryModel.register(
                filename=filename,
                file_type=file_type or 'unknown',
                truth_type='unknown',
                classification_method='failed',
                classification_confidence=0,
                storage_type='none',
                project_id=project_id,
                is_global=False,
                parse_status='failed',
                file_hash=file_hash,
                file_size_bytes=file_size,
                uploaded_by_id=uploaded_by_id,
                uploaded_by_email=uploaded_by_email,
                error_message=error_message,
                error_details=error_details or {},
                metadata={
                    'registration_source': source.value if isinstance(source, RegistrationSource) else source,
                    'failed_at': datetime.utcnow().isoformat()
                }
            )
            
            if registry_result:
                result.registry_id = registry_result.get('id')
                logger.warning(f"[REGISTRATION] Registered failure: {filename} - {error_message}")
            
            # Mark result as "successful" registration of a failure
            result.success = True
            result.error = error_message  # Keep the original error for reference
            
        except Exception as e:
            result.error = f"Failed to register failure: {e}"
            logger.error(f"[REGISTRATION] Could not register failure: {e}")
        
        result.timing_ms = int((time.time() - start) * 1000)
        return result
    
    # ==========================================================================
    # UNREGISTRATION (DELETE SUPPORT)
    # ==========================================================================
    
    @staticmethod
    def unregister(
        filename: str,
        project_id: str = None,
        delete_lineage: bool = True
    ) -> RegistrationResult:
        """
        Unregister a file and optionally its lineage.
        
        Called by delete endpoints to maintain consistency.
        """
        start = time.time()
        result = RegistrationResult(success=False, filename=filename)
        
        try:
            DocumentRegistryModel, LineageModel, _ = RegistrationService._get_models()
            
            # Unregister from DocumentRegistry
            if DocumentRegistryModel:
                DocumentRegistryModel.unregister(filename, project_id)
                logger.info(f"[REGISTRATION] Unregistered: {filename}")
            
            # Delete lineage edges
            if delete_lineage and LineageModel:
                edges_deleted = LineageModel.delete_for_source('file', filename, project_id)
                result.lineage_edges = edges_deleted
                logger.info(f"[REGISTRATION] Deleted {edges_deleted} lineage edges for: {filename}")
            
            result.success = True
            
        except Exception as e:
            result.error = str(e)
            logger.error(f"[REGISTRATION] Unregister failed: {e}")
        
        result.timing_ms = int((time.time() - start) * 1000)
        return result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def register_structured(**kwargs) -> RegistrationResult:
    """Convenience wrapper for RegistrationService.register_structured()"""
    return RegistrationService.register_structured(**kwargs)

def register_embedded(**kwargs) -> RegistrationResult:
    """Convenience wrapper for RegistrationService.register_embedded()"""
    return RegistrationService.register_embedded(**kwargs)

def register_standards(**kwargs) -> RegistrationResult:
    """Convenience wrapper for RegistrationService.register_standards()"""
    return RegistrationService.register_standards(**kwargs)

def register_hybrid(**kwargs) -> RegistrationResult:
    """Convenience wrapper for RegistrationService.register_hybrid()"""
    return RegistrationService.register_hybrid(**kwargs)

def register_failed(**kwargs) -> RegistrationResult:
    """Convenience wrapper for RegistrationService.register_failed()"""
    return RegistrationService.register_failed(**kwargs)

def unregister(**kwargs) -> RegistrationResult:
    """Convenience wrapper for RegistrationService.unregister()"""
    return RegistrationService.unregister(**kwargs)
