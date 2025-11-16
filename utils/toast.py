"""
Professional Toast Notification System
Beautiful, non-intrusive notifications for user actions
"""

import streamlit as st
from typing import Literal, Optional
import time


class ToastManager:
    """Manage toast notifications with auto-dismiss and styling"""
    
    @staticmethod
    def success(message: str, icon: str = "✅", duration: int = 3):
        """
        Show success toast notification
        
        Args:
            message: The message to display
            icon: Emoji icon (default: ✅)
            duration: How long to show in seconds (default: 3)
        """
        st.toast(f"{icon} {message}", icon=icon)
    
    @staticmethod
    def info(message: str, icon: str = "💡", duration: int = 3):
        """Show info toast notification"""
        st.toast(f"{icon} {message}", icon=icon)
    
    @staticmethod
    def warning(message: str, icon: str = "⚠️", duration: int = 4):
        """Show warning toast notification"""
        st.toast(f"{icon} {message}", icon=icon)
    
    @staticmethod
    def error(message: str, icon: str = "❌", duration: int = 5):
        """Show error toast notification (longer duration)"""
        st.toast(f"{icon} {message}", icon=icon)
    
    @staticmethod
    def custom(message: str, icon: str = "🔔"):
        """Show custom toast with any icon"""
        st.toast(f"{icon} {message}", icon=icon)
    
    # Convenience methods for common actions
    
    @staticmethod
    def saved(item_name: str = "Changes"):
        """Quick toast for save actions"""
        st.toast(f"✅ {item_name} saved successfully!", icon="✅")
    
    @staticmethod
    def deleted(item_name: str = "Item"):
        """Quick toast for delete actions"""
        st.toast(f"🗑️ {item_name} deleted", icon="🗑️")
    
    @staticmethod
    def uploaded(file_name: str = "File"):
        """Quick toast for upload actions"""
        st.toast(f"📤 {file_name} uploaded!", icon="📤")
    
    @staticmethod
    def downloaded(file_name: str = "File"):
        """Quick toast for download actions"""
        st.toast(f"📥 {file_name} downloaded!", icon="📥")
    
    @staticmethod
    def copied(item: str = "Text"):
        """Quick toast for copy actions"""
        st.toast(f"📋 {item} copied to clipboard!", icon="📋")
    
    @staticmethod
    def analyzing():
        """Quick toast for analysis start"""
        st.toast("🧠 Analysis started...", icon="🧠")
    
    @staticmethod
    def completed(task: str = "Task"):
        """Quick toast for completion"""
        st.toast(f"🎉 {task} completed!", icon="🎉")
    
    @staticmethod
    def cached():
        """Quick toast for cached results"""
        st.toast("⚡ Retrieved from cache (instant!)", icon="⚡")
    
    @staticmethod
    def connecting():
        """Quick toast for connection attempt"""
        st.toast("🔌 Connecting...", icon="🔌")
    
    @staticmethod
    def connected():
        """Quick toast for successful connection"""
        st.toast("✅ Connected successfully!", icon="✅")
    
    @staticmethod
    def auto_saving():
        """Quick toast for auto-save"""
        st.toast("💾 Auto-saving...", icon="💾")


# Convenience function for quick use
def toast(message: str, type: Literal["success", "info", "warning", "error"] = "info", icon: Optional[str] = None):
    """
    Quick toast function
    
    Usage:
        toast("Project saved!", "success")
        toast("Loading...", "info", "⏳")
        toast("Connection lost", "warning")
        toast("Failed to save", "error")
    """
    if icon is None:
        icons = {
            "success": "✅",
            "info": "💡",
            "warning": "⚠️",
            "error": "❌"
        }
        icon = icons.get(type, "🔔")
    
    if type == "success":
        ToastManager.success(message, icon)
    elif type == "warning":
        ToastManager.warning(message, icon)
    elif type == "error":
        ToastManager.error(message, icon)
    else:
        ToastManager.info(message, icon)


# Example usage patterns:
"""
# Method 1: Using ToastManager class (recommended)
from utils.toast import ToastManager

# Quick convenience methods
ToastManager.saved("Project")
ToastManager.deleted("Document")
ToastManager.uploaded("report.pdf")
ToastManager.completed("Analysis")

# Custom messages
ToastManager.success("All templates generated!")
ToastManager.info("Using cached data")
ToastManager.warning("Connection unstable")

# Method 2: Using quick toast function
from utils.toast import toast

toast("Project created!", "success")
toast("Loading data...", "info")
toast("Network issue", "warning")
toast("Failed to connect", "error")

# Method 3: Direct st.toast (if you prefer)
st.toast("✅ Action completed!", icon="✅")
"""


# Context-specific toast helpers

class ChatToasts:
    """Toast notifications specific to chat page"""
    
    @staticmethod
    def searching():
        st.toast("🔍 Searching knowledge base...", icon="🔍")
    
    @staticmethod
    def found_sources(count: int):
        st.toast(f"📚 Found {count} relevant source(s)", icon="📚")
    
    @staticmethod
    def thinking():
        st.toast("🧠 AI is thinking...", icon="🧠")
    
    @staticmethod
    def responded():
        st.toast("✅ Response generated!", icon="✅")
    
    @staticmethod
    def cache_hit():
        st.toast("⚡ Using cached response!", icon="⚡")


class ProjectToasts:
    """Toast notifications specific to projects"""
    
    @staticmethod
    def created(name: str):
        st.toast(f"✅ Project '{name}' created!", icon="✅")
    
    @staticmethod
    def activated(name: str):
        st.toast(f"📌 Activated: {name}", icon="📌")
    
    @staticmethod
    def deleted(name: str):
        st.toast(f"🗑️ Project '{name}' deleted", icon="🗑️")
    
    @staticmethod
    def note_added():
        st.toast("📝 Note added successfully!", icon="📝")


class AnalysisToasts:
    """Toast notifications specific to analysis"""
    
    @staticmethod
    def parsing():
        st.toast("📄 Parsing document...", icon="📄")
    
    @staticmethod
    def parsed():
        st.toast("✅ Document parsed successfully!", icon="✅")
    
    @staticmethod
    def analyzing():
        st.toast("🧠 Analyzing with AI...", icon="🧠")
    
    @staticmethod
    def analyzed():
        st.toast("✅ Analysis complete!", icon="✅")
    
    @staticmethod
    def generating_templates():
        st.toast("⚡ Generating templates...", icon="⚡")
    
    @staticmethod
    def templates_ready():
        st.toast("🎉 Templates ready for download!", icon="🎉")


class KnowledgeToasts:
    """Toast notifications for knowledge base"""
    
    @staticmethod
    def indexing(filename: str):
        st.toast(f"📚 Indexing {filename}...", icon="📚")
    
    @staticmethod
    def indexed(filename: str, chunks: int):
        st.toast(f"✅ {filename} indexed ({chunks} chunks)", icon="✅")
    
    @staticmethod
    def deleted(filename: str):
        st.toast(f"🗑️ {filename} removed from knowledge base", icon="🗑️")


# Progressive toast (for long operations)
class ProgressToast:
    """Show progress updates via toasts"""
    
    def __init__(self, operation: str):
        self.operation = operation
        self.step = 0
    
    def update(self, step: str, icon: str = "⏳"):
        """Update progress"""
        self.step += 1
        st.toast(f"{icon} {self.operation}: {step}", icon=icon)
    
    def complete(self, icon: str = "✅"):
        """Mark as complete"""
        st.toast(f"{icon} {self.operation} completed!", icon=icon)
    
    def error(self, message: str = "Failed"):
        """Mark as failed"""
        st.toast(f"❌ {self.operation}: {message}", icon="❌")


# Example of progressive toast usage:
"""
progress = ProgressToast("Document Analysis")
progress.update("Parsing PDF", "📄")
# ... do parsing ...
progress.update("Running AI analysis", "🧠")
# ... do analysis ...
progress.update("Generating templates", "⚡")
# ... generate templates ...
progress.complete("🎉")
"""
