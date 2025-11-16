"""
Supabase Client for XLR8
Handles connection to Supabase database

This replaces ephemeral session storage with persistent database storage.
"""

import os
from typing import Optional
from supabase import create_client, Client
import streamlit as st


class SupabaseClient:
    """
    Singleton Supabase client for XLR8
    
    Manages connection to Supabase and provides client instance.
    """
    
    _instance: Optional[Client] = None
    _url: Optional[str] = None
    _key: Optional[str] = None
    
    @classmethod
    def get_client(cls) -> Optional[Client]:
        """
        Get Supabase client instance (singleton pattern)
        
        Returns:
            Supabase client or None if credentials not configured
        
        Example:
            supabase = SupabaseClient.get_client()
            if supabase:
                result = supabase.table('projects').select('*').execute()
        """
        
        # Get credentials from environment
        if not cls._url:
            cls._url = os.getenv('SUPABASE_URL')
        if not cls._key:
            cls._key = os.getenv('SUPABASE_KEY')
        
        # Check if configured
        if not cls._url or not cls._key:
            return None
        
        # Create client if not exists
        if cls._instance is None:
            try:
                cls._instance = create_client(cls._url, cls._key)
            except Exception as e:
                st.error(f"Failed to connect to Supabase: {str(e)}")
                return None
        
        return cls._instance
    
    @classmethod
    def is_configured(cls) -> bool:
        """
        Check if Supabase is properly configured
        
        Returns:
            True if SUPABASE_URL and SUPABASE_KEY are set
        
        Example:
            if SupabaseClient.is_configured():
                # Use Supabase
            else:
                # Use session state
        """
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        return bool(url and key)
    
    @classmethod
    def test_connection(cls) -> dict:
        """
        Test Supabase connection
        
        Returns:
            {
                'connected': bool,
                'message': str,
                'tables': list  # Available tables
            }
        
        Example:
            status = SupabaseClient.test_connection()
            if status['connected']:
                print("Supabase ready!")
        """
        client = cls.get_client()
        
        if not client:
            return {
                'connected': False,
                'message': 'Supabase credentials not configured',
                'tables': []
            }
        
        try:
            # Try to query projects table (should exist)
            response = client.table('projects').select('id').limit(1).execute()
            
            return {
                'connected': True,
                'message': 'Supabase connected successfully',
                'tables': ['projects', 'documents', 'chat_history', 'user_preferences']
            }
        except Exception as e:
            return {
                'connected': False,
                'message': f'Connection failed: {str(e)}',
                'tables': []
            }
    
    @classmethod
    def reset_client(cls):
        """
        Reset client instance (useful for testing or credential changes)
        
        Example:
            SupabaseClient.reset_client()
            # Next get_client() call will create new instance
        """
        cls._instance = None
        cls._url = None
        cls._key = None


# Convenience function for getting client
def get_supabase() -> Optional[Client]:
    """
    Convenience function to get Supabase client
    
    Returns:
        Supabase client or None
    
    Example:
        from utils.database.supabase_client import get_supabase
        
        supabase = get_supabase()
        if supabase:
            projects = supabase.table('projects').select('*').execute()
    """
    return SupabaseClient.get_client()


# For backward compatibility and ease of use
supabase_client = get_supabase
