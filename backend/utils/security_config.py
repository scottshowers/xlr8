"""
XLR8 Security Configuration
============================
Manages security settings with persistence and runtime toggling.

Safe Mode: All risky features OFF by default.

Author: XLR8 Platform
Date: December 8, 2025
"""

import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import threading

# Default configuration - SAFE MODE (risky features OFF)
DEFAULT_CONFIG = {
    # Middleware toggles
    "rate_limiting_enabled": False,      # OFF by default - can cause issues during testing
    "input_validation_enabled": False,   # OFF by default - can block legitimate queries
    "audit_logging_enabled": True,       # ON - safe, just watches
    "security_headers_enabled": True,    # ON - safe, just adds headers
    
    # Rate limit settings (when enabled)
    "rate_limits": {
        "api": {"max_requests": 100, "period_seconds": 60},
        "upload": {"max_requests": 10, "period_seconds": 60},
        "llm_cloud": {"max_requests": 20, "period_seconds": 60},
        "llm_local": {"max_requests": 50, "period_seconds": 60},
        "export": {"max_requests": 5, "period_seconds": 300},
        "auth": {"max_requests": 5, "period_seconds": 60},
    },
    
    # PII settings
    "pii_auto_scan_uploads": False,      # OFF - scan on demand only
    "pii_auto_mask_chat": False,         # OFF - don't auto-mask chat
    "pii_scan_before_llm": True,         # ON - scan before sending to external LLM
    
    # Prompt sanitization
    "prompt_sanitization_enabled": True, # ON - blocks injection attempts
    "prompt_sanitization_log_only": True, # Log but don't block (safe mode)
    
    # CORS
    "cors_origins": [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://xlr8-six.vercel.app",
    ],
    
    # Audit settings
    "audit_to_file": True,
    "audit_file_path": "/data/audit.log",
    "audit_to_database": False,          # OFF until DB migration run
    "audit_retention_days": 90,
    
    # Metadata
    "last_updated": None,
    "updated_by": None,
}


class SecurityConfig:
    """
    Security configuration manager with file persistence.
    
    Usage:
        config = SecurityConfig()
        
        # Read
        if config.get("rate_limiting_enabled"):
            apply_rate_limiting()
        
        # Write
        config.set("rate_limiting_enabled", True)
        config.save()
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern - one config instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: str = "/data/security_config.json"):
        if getattr(self, '_initialized', False):
            return
            
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self._load()
        self._initialized = True
    
    def _load(self):
        """Load config from file or use defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    saved = json.load(f)
                # Merge with defaults (in case new fields added)
                self.config = {**DEFAULT_CONFIG, **saved}
            except Exception as e:
                print(f"Warning: Could not load security config: {e}")
                self.config = DEFAULT_CONFIG.copy()
        else:
            self.config = DEFAULT_CONFIG.copy()
            self._save()  # Create initial file
    
    def _save(self):
        """Save config to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2, default=str)
        except Exception as e:
            print(f"Warning: Could not save security config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any, updated_by: str = "system") -> None:
        """Set a config value."""
        with self._lock:
            self.config[key] = value
            self.config["last_updated"] = datetime.utcnow().isoformat()
            self.config["updated_by"] = updated_by
            self._save()
    
    def update(self, updates: Dict[str, Any], updated_by: str = "system") -> None:
        """Update multiple values."""
        with self._lock:
            self.config.update(updates)
            self.config["last_updated"] = datetime.utcnow().isoformat()
            self.config["updated_by"] = updated_by
            self._save()
    
    def get_all(self) -> Dict[str, Any]:
        """Get entire config."""
        return self.config.copy()
    
    def reset_to_defaults(self, updated_by: str = "system") -> None:
        """Reset all settings to defaults."""
        with self._lock:
            self.config = DEFAULT_CONFIG.copy()
            self.config["last_updated"] = datetime.utcnow().isoformat()
            self.config["updated_by"] = updated_by
            self._save()
    
    def get_rate_limits_tuple(self) -> Dict[str, tuple]:
        """Get rate limits in the format expected by RateLimiter."""
        limits = self.get("rate_limits", {})
        return {
            key: (val["max_requests"], val["period_seconds"])
            for key, val in limits.items()
        }


# Global instance
_security_config: Optional[SecurityConfig] = None


def get_security_config() -> SecurityConfig:
    """Get the global security config instance."""
    global _security_config
    if _security_config is None:
        _security_config = SecurityConfig()
    return _security_config


def reset_security_config() -> SecurityConfig:
    """Force reset of the security config (useful after file changes)."""
    global _security_config
    SecurityConfig._instance = None
    _security_config = SecurityConfig()
    return _security_config
