"""
Optimized Database Connection Manager for Streamlit
Prevents connection leaks and improves performance
"""

import streamlit as st
from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
import time
import threading
import gc
from typing import Optional, Any, Dict
import os
import psutil
import logging

logger = logging.getLogger(__name__)

class DatabaseConnectionManager:
    """Manages database connections efficiently for Streamlit apps"""
    
    def __init__(self):
        self._engine = None
        self._connection_count = 0
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
        self._lock = threading.Lock()
        
    def get_engine(self, force_recreate: bool = False):
        """Get or create database engine with proper pooling for Streamlit"""
        
        if force_recreate or self._engine is None:
            with self._lock:
                if force_recreate and self._engine:
                    self._engine.dispose()
                    self._engine = None
                
                if self._engine is None:
                    database_url = os.getenv('DATABASE_URL')
                    
                    if database_url:
                        # Production environment
                        if database_url.startswith('postgresql://'):
                            database_url = database_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
                        
                        # Use NullPool for Streamlit to avoid connection pooling issues
                        self._engine = create_engine(
                            database_url,
                            poolclass=NullPool,  # No connection pooling - better for Streamlit
                            echo=False,
                            connect_args={
                                "connect_timeout": 10,
                                "options": "-c statement_timeout=30000"  # 30 second query timeout
                            }
                        )
                    else:
                        # Local development
                        try:
                            from config import settings
                            database_url = settings.database_url
                        except ImportError:
                            database_url = "postgresql+psycopg2://postgres:admin123@localhost:5432/gl_erp"
                        
                        # Use smaller pool for local development
                        self._engine = create_engine(
                            database_url,
                            poolclass=QueuePool,
                            pool_size=5,          # Smaller pool
                            max_overflow=10,      # Less overflow
                            pool_pre_ping=True,   # Check connection health
                            pool_recycle=1800,    # Recycle every 30 minutes
                            pool_timeout=20,      # Shorter timeout
                            echo=False,
                            connect_args={
                                "connect_timeout": 10,
                                "options": "-c statement_timeout=30000"
                            }
                        )
        
        return self._engine
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections with automatic cleanup"""
        conn = None
        try:
            engine = self.get_engine()
            conn = engine.connect()
            self._connection_count += 1
            
            # Log if too many connections
            if self._connection_count > 50:
                logger.warning(f"High connection count: {self._connection_count}")
            
            yield conn
            
        except SQLAlchemyError as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                try:
                    conn.close()
                except:
                    pass
                self._connection_count -= 1
            
            # Periodic cleanup
            self._periodic_cleanup()
    
    def _periodic_cleanup(self):
        """Periodically clean up resources"""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            with self._lock:
                self._last_cleanup = current_time
                
                # Force garbage collection
                gc.collect()
                
                # Check memory usage
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                if memory_mb > 500:  # If using more than 500MB
                    logger.warning(f"High memory usage: {memory_mb:.1f}MB")
                    
                    # Dispose of engine to release all connections
                    if self._engine:
                        self._engine.dispose()
    
    def execute_query(self, query: str, params: Dict = None, fetch: str = "all"):
        """Execute a query with automatic connection management"""
        with self.get_connection() as conn:
            result = conn.execute(text(query), params or {})
            
            if fetch == "all":
                return result.fetchall()
            elif fetch == "one":
                return result.fetchone()
            elif fetch == "df":
                return pd.DataFrame(result.fetchall(), columns=result.keys())
            else:
                return result
    
    def read_sql(self, query: str, params: Dict = None) -> pd.DataFrame:
        """Read SQL query into pandas DataFrame with connection management"""
        with self.get_connection() as conn:
            return pd.read_sql(text(query), conn, params=params)
    
    def dispose(self):
        """Dispose of the engine and all connections"""
        if self._engine:
            self._engine.dispose()
            self._engine = None
            self._connection_count = 0

# Global instance
db_manager = DatabaseConnectionManager()

# Streamlit-specific session state management
def get_db_manager() -> DatabaseConnectionManager:
    """Get or create database manager in Streamlit session state"""
    if 'db_manager' not in st.session_state:
        st.session_state.db_manager = DatabaseConnectionManager()
    return st.session_state.db_manager

@contextmanager
def get_db_connection():
    """Convenience function for getting database connection"""
    manager = get_db_manager()
    with manager.get_connection() as conn:
        yield conn

def execute_query(query: str, params: Dict = None, fetch: str = "all"):
    """Convenience function for executing queries"""
    manager = get_db_manager()
    return manager.execute_query(query, params, fetch)

def read_sql(query: str, params: Dict = None) -> pd.DataFrame:
    """Convenience function for reading SQL into DataFrame"""
    manager = get_db_manager()
    return manager.read_sql(query, params)

# Cleanup function for Streamlit
def cleanup_connections():
    """Clean up all database connections - call on app shutdown"""
    if 'db_manager' in st.session_state:
        st.session_state.db_manager.dispose()
        del st.session_state.db_manager