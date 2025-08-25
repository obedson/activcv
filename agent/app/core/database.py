"""
Database connection and utilities
"""

import os
from typing import Optional
from supabase import create_client, Client
from app.core.config import settings


class Database:
    """Database connection manager"""
    
    _client: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Client:
        """Get Supabase client instance"""
        if cls._client is None:
            cls._client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_ANON_KEY
            )
        return cls._client
    
    @classmethod
    def get_service_client(cls) -> Client:
        """Get Supabase service client with elevated permissions"""
        return create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )


# Convenience function
def get_db() -> Client:
    """Get database client"""
    return Database.get_client()