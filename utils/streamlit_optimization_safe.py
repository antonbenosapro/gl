"""
Safe Streamlit Performance Optimization Utilities
Fallback version with optional dependencies
"""

import streamlit as st
import time
import gc
import logging
from functools import wraps, lru_cache
from datetime import datetime, timedelta
import hashlib
import pickle

logger = logging.getLogger(__name__)

# Optional import for psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available - some monitoring features disabled")

class StreamlitOptimizer:
    """Optimization utilities for Streamlit applications"""
    
    @staticmethod
    def initialize_session():
        """Initialize session state with performance optimizations"""
        
        # Performance tracking
        if 'page_load_times' not in st.session_state:
            st.session_state.page_load_times = []
        
        if 'last_activity' not in st.session_state:
            st.session_state.last_activity = time.time()
        
        if 'cache_timestamps' not in st.session_state:
            st.session_state.cache_timestamps = {}
        
        if 'query_cache' not in st.session_state:
            st.session_state.query_cache = {}
        
        # Memory management
        if 'last_gc' not in st.session_state:
            st.session_state.last_gc = time.time()
    
    @staticmethod
    def track_activity():
        """Track user activity to prevent timeout"""
        st.session_state.last_activity = time.time()
    
    @staticmethod
    def check_session_health():
        """Check session health and perform maintenance"""
        current_time = time.time()
        
        # Check for inactivity
        if 'last_activity' in st.session_state:
            inactive_time = current_time - st.session_state.last_activity
            if inactive_time > 1800:  # 30 minutes
                st.warning("⚠️ Session inactive for 30 minutes. Please refresh if you experience issues.")
        
        # Periodic garbage collection
        if 'last_gc' in st.session_state:
            if current_time - st.session_state.last_gc > 300:  # Every 5 minutes
                gc.collect()
                st.session_state.last_gc = current_time
        
        # Memory check (only if psutil available)
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                if memory_mb > 800:  # If using more than 800MB
                    logger.warning(f"High memory usage: {memory_mb:.1f}MB")
                    # Clear some caches
                    if 'query_cache' in st.session_state:
                        st.session_state.query_cache = {}
                    gc.collect()
            except Exception as e:
                logger.debug(f"Memory check failed: {e}")
    
    @staticmethod
    def cache_query_result(query_key: str, result, ttl: int = 300):
        """Cache query results with TTL"""
        if 'query_cache' not in st.session_state:
            st.session_state.query_cache = {}
        
        st.session_state.query_cache[query_key] = {
            'result': result,
            'timestamp': time.time(),
            'ttl': ttl
        }
    
    @staticmethod
    def get_cached_result(query_key: str):
        """Get cached query result if still valid"""
        if 'query_cache' not in st.session_state:
            return None
        
        if query_key in st.session_state.query_cache:
            cache_entry = st.session_state.query_cache[query_key]
            if time.time() - cache_entry['timestamp'] < cache_entry['ttl']:
                return cache_entry['result']
            else:
                # Remove expired entry
                del st.session_state.query_cache[query_key]
        
        return None
    
    @staticmethod
    def clear_old_cache():
        """Clear expired cache entries"""
        if 'query_cache' not in st.session_state:
            return
        
        current_time = time.time()
        expired_keys = []
        
        for key, entry in st.session_state.query_cache.items():
            if current_time - entry['timestamp'] > entry['ttl']:
                expired_keys.append(key)
        
        for key in expired_keys:
            del st.session_state.query_cache[key]

def performance_tracker(func):
    """Decorator to track function performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.time()
            duration = end_time - start_time
            
            if duration > 2:  # Log slow operations
                logger.warning(f"Slow operation: {func.__name__} took {duration:.2f}s")
            
            # Track in session state
            if 'page_load_times' in st.session_state:
                st.session_state.page_load_times.append({
                    'function': func.__name__,
                    'duration': duration,
                    'timestamp': time.time()
                })
                
                # Keep only last 100 entries
                if len(st.session_state.page_load_times) > 100:
                    st.session_state.page_load_times = st.session_state.page_load_times[-100:]
    
    return wrapper

def cached_query(ttl: int = 300):
    """Decorator for caching database queries"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = hashlib.md5(
                f"{func.__name__}_{str(args)}_{str(kwargs)}".encode()
            ).hexdigest()
            
            # Check cache
            optimizer = StreamlitOptimizer()
            cached_result = optimizer.get_cached_result(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            optimizer.cache_query_result(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator

def optimize_dataframe_display(df, max_rows: int = 1000):
    """Optimize large dataframe display"""
    if len(df) > max_rows:
        st.warning(f"⚠️ Showing first {max_rows} rows of {len(df)} total rows for performance")
        return df.head(max_rows)
    return df

def batch_process(items, batch_size: int = 100):
    """Process items in batches to avoid memory issues"""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]

# Session health monitor
def monitor_session_health():
    """Monitor and maintain session health"""
    optimizer = StreamlitOptimizer()
    optimizer.initialize_session()
    optimizer.track_activity()
    optimizer.check_session_health()
    optimizer.clear_old_cache()

# Auto-refresh mechanism
def setup_auto_refresh(interval_minutes: int = 25):
    """Setup auto-refresh to prevent session timeout"""
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()
    
    current_time = time.time()
    if current_time - st.session_state.last_refresh > interval_minutes * 60:
        st.session_state.last_refresh = current_time
        # Only auto-refresh if user has been active recently
        if 'last_activity' in st.session_state:
            inactive_time = current_time - st.session_state.last_activity
            if inactive_time < 1800:  # Less than 30 minutes inactive
                st.rerun()

# Memory-efficient data loading
@lru_cache(maxsize=32)
def load_reference_data(data_type: str):
    """Load reference data with caching"""
    try:
        from utils.db_connection_manager import read_sql
        
        queries = {
            'gl_accounts': "SELECT glaccountid, accountname FROM glaccount WHERE (blocked_for_posting = FALSE OR blocked_for_posting IS NULL) AND (marked_for_deletion = FALSE OR marked_for_deletion IS NULL)",
            'company_codes': "SELECT companycodeid, name FROM companycode",
            'business_units': "SELECT unit_id, unit_name, business_unit_id FROM business_units WHERE is_active = TRUE",
            'users': "SELECT username, first_name, last_name FROM users WHERE is_active = TRUE"
        }
        
        if data_type in queries:
            return read_sql(queries[data_type])
    except ImportError:
        # Fallback to regular db access
        try:
            from db_config import engine
            import pandas as pd
            from sqlalchemy import text
            
            queries = {
                'gl_accounts': "SELECT glaccountid, accountname FROM glaccount WHERE (blocked_for_posting = FALSE OR blocked_for_posting IS NULL) AND (marked_for_deletion = FALSE OR marked_for_deletion IS NULL)",
                'company_codes': "SELECT companycodeid, name FROM companycode",
                'business_units': "SELECT unit_id, unit_name, business_unit_id FROM business_units WHERE is_active = TRUE",
                'users': "SELECT username, first_name, last_name FROM users WHERE is_active = TRUE"
            }
            
            if data_type in queries:
                with engine.connect() as conn:
                    return pd.read_sql(text(queries[data_type]), conn)
        except Exception as e:
            logger.error(f"Error loading reference data: {e}")
    
    return None

# Cleanup function
def cleanup_session():
    """Clean up session resources"""
    # Clear caches
    if 'query_cache' in st.session_state:
        del st.session_state.query_cache
    
    # Clear tracking data
    if 'page_load_times' in st.session_state:
        del st.session_state.page_load_times
    
    # Force garbage collection
    gc.collect()

# Error recovery
def safe_execute(func, default=None, error_message=None):
    """Safely execute a function with error recovery"""
    try:
        return func()
    except Exception as e:
        logger.error(f"Error in {getattr(func, '__name__', 'unknown')}: {e}")
        if error_message:
            st.error(error_message)
        else:
            st.error(f"An error occurred: {str(e)}")
        return default