"""
Supabase Client for XLR8
Handles connection to Supabase database
"""

import os
import logging
from typing import Optional
from supabase import create_client, Client

logger = logging.getLogger(__name__)


class SupabaseClient:
    """Singleton Supabase client for XLR8"""
    
    _instance: Optional[Client] = None
    _url: Optional[str] = None
    _key: Optional[str] = None
    
    @classmethod
    def get_client(cls) -> Optional[Client]:
        """Get Supabase client instance (singleton)"""
        
        if not cls._url:
            cls._url = os.getenv('SUPABASE_URL')
        if not cls._key:
            cls._key = os.getenv('SUPABASE_KEY')
        
        if not cls._url or not cls._key:
            return None
        
        if cls._instance is None:
            try:
                cls._instance = create_client(cls._url, cls._key)
            except Exception as e:
                logger.error(f"Failed to connect to Supabase: {str(e)}")
                return None
        
        return cls._instance
    
    @classmethod
    def is_configured(cls) -> bool:
        """Check if Supabase is configured"""
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        return bool(url and key)
    
    @classmethod
    def test_connection(cls) -> dict:
        """Test Supabase connection"""
        client = cls.get_client()
        
        if not client:
            return {
                'connected': False,
                'message': 'Supabase not configured',
                'tables': []
            }
        
        try:
            response = client.table('customers').select('id').limit(1).execute()
            
            return {
                'connected': True,
                'message': 'Connected',
                'tables': ['customers', 'documents', 'chat_history', 'user_preferences']
            }
        except Exception as e:
            return {
                'connected': False,
                'message': f'Failed: {str(e)}',
                'tables': []
            }
    
    @classmethod
    def reset_client(cls):
        """Reset client instance"""
        cls._instance = None
        cls._url = None
        cls._key = None


def get_supabase() -> Optional[Client]:
    """Convenience function to get Supabase client"""
    return SupabaseClient.get_client()


supabase_client = get_supabase
