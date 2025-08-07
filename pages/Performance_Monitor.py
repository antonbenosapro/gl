"""
Performance Monitoring Dashboard
Monitor Streamlit app performance and session health
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import psutil
import gc
import sys
import os

from auth.optimized_middleware import optimized_authenticator as authenticator
from utils.navigation import show_breadcrumb
from utils.streamlit_optimization import StreamlitOptimizer, monitor_session_health
from utils.db_connection_manager import get_db_manager

st.set_page_config(
    page_title="Performance Monitor",
    page_icon="📊",
    layout="wide"
)

# Authentication
authenticator.require_auth()
user = authenticator.get_current_user()

# Only allow admins
if not authenticator.has_permission("system.admin"):
    st.error("🚫 Access Denied: Admin permissions required")
    st.stop()

def main():
    monitor_session_health()
    
    show_breadcrumb("Performance Monitor", "System", "Monitoring")
    
    st.title("📊 Performance Monitoring Dashboard")
    st.markdown("*Real-time monitoring of Streamlit app performance and resource usage*")
    
    # Refresh controls
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        auto_refresh = st.checkbox("Auto-refresh (10s)", value=False)
    with col2:
        if st.button("🔄 Refresh Now"):
            st.rerun()
    with col3:
        if st.button("🗑️ Clear Cache"):
            st.cache_data.clear()
            if 'query_cache' in st.session_state:
                st.session_state.query_cache = {}
            st.success("Cache cleared!")
    
    if auto_refresh:
        time.sleep(10)
        st.rerun()
    
    # System Resources
    st.header("🖥️ System Resources")
    
    process = psutil.Process()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        memory_mb = process.memory_info().rss / 1024 / 1024
        memory_color = "normal"
        if memory_mb > 800:
            memory_color = "inverse"
        st.metric("Memory Usage", f"{memory_mb:.1f} MB", delta=None)
    
    with col2:
        cpu_percent = process.cpu_percent(interval=1)
        st.metric("CPU Usage", f"{cpu_percent:.1f}%")
    
    with col3:
        try:
            db_manager = get_db_manager()
            conn_count = getattr(db_manager, '_connection_count', 0)
            st.metric("DB Connections", conn_count)
        except:
            st.metric("DB Connections", "N/A")
    
    with col4:
        cache_size = len(st.session_state.get('query_cache', {}))
        st.metric("Cached Queries", cache_size)
    
    # Session Health
    st.header("🔐 Session Health")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'last_activity' in st.session_state:
            last_activity = datetime.fromtimestamp(st.session_state.last_activity)
            inactive_time = (datetime.now() - last_activity).total_seconds()
            
            status = "🟢 Active"
            if inactive_time > 300:  # 5 minutes
                status = "🟡 Idle"
            if inactive_time > 1200:  # 20 minutes
                status = "🟠 Warning"
            if inactive_time > 1800:  # 30 minutes
                status = "🔴 Critical"
            
            st.metric("Session Status", status)
            st.metric("Last Activity", f"{inactive_time:.0f}s ago")
        else:
            st.metric("Session Status", "Unknown")
    
    with col2:
        session_size = len(st.session_state)
        session_keys = list(st.session_state.keys())
        st.metric("Session Variables", session_size)
        
        if st.checkbox("Show Session Keys"):
            st.write(session_keys)
    
    # Performance History
    if 'page_load_times' in st.session_state and st.session_state.page_load_times:
        st.header("⏱️ Performance History")
        
        load_times_df = pd.DataFrame(st.session_state.page_load_times)
        load_times_df['timestamp'] = pd.to_datetime(load_times_df['timestamp'], unit='s')
        
        # Recent performance chart
        fig = px.line(
            load_times_df.tail(50), 
            x='timestamp', 
            y='duration', 
            color='function',
            title='Page Load Times (Last 50)',
            labels={'duration': 'Duration (seconds)', 'timestamp': 'Time'}
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Performance stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_time = load_times_df['duration'].mean()
            st.metric("Average Load Time", f"{avg_time:.2f}s")
        
        with col2:
            max_time = load_times_df['duration'].max()
            st.metric("Slowest Load", f"{max_time:.2f}s")
        
        with col3:
            slow_pages = len(load_times_df[load_times_df['duration'] > 3])
            st.metric("Slow Loads (>3s)", slow_pages)
        
        # Function performance breakdown
        if st.checkbox("Show Function Breakdown"):
            func_stats = load_times_df.groupby('function')['duration'].agg(['mean', 'max', 'count']).reset_index()
            func_stats.columns = ['Function', 'Avg Time', 'Max Time', 'Count']
            st.dataframe(func_stats.sort_values('Avg Time', ascending=False))
    
    # Database Performance
    st.header("🗄️ Database Performance")
    
    try:
        from utils.db_connection_manager import execute_query
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Active connections
            active_connections = execute_query(
                "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'",
                fetch="one"
            )
            st.metric("Active DB Sessions", active_connections[0] if active_connections else 0)
            
            # Long running queries
            long_queries = execute_query(
                """SELECT count(*) FROM pg_stat_activity 
                   WHERE state = 'active' 
                   AND now() - query_start > interval '30 seconds'""",
                fetch="one"
            )
            st.metric("Long Queries (>30s)", long_queries[0] if long_queries else 0)
        
        with col2:
            # Database size
            db_size = execute_query(
                "SELECT pg_size_pretty(pg_database_size(current_database()))",
                fetch="one"
            )
            st.metric("Database Size", db_size[0] if db_size else "Unknown")
            
            # Table count
            table_count = execute_query(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'",
                fetch="one"
            )
            st.metric("Tables", table_count[0] if table_count else 0)
        
        # Recent queries (if available)
        if st.checkbox("Show Recent Queries"):
            try:
                recent_queries = execute_query(
                    """SELECT query, state, now() - query_start as duration
                       FROM pg_stat_activity 
                       WHERE query NOT LIKE '%pg_stat_activity%'
                       AND query_start IS NOT NULL
                       ORDER BY query_start DESC 
                       LIMIT 10""",
                    fetch="df"
                )
                
                if not recent_queries.empty:
                    st.dataframe(recent_queries)
                else:
                    st.info("No recent queries found")
            except Exception as e:
                st.warning(f"Cannot access query stats: {e}")
    
    except Exception as e:
        st.error(f"Database performance monitoring unavailable: {e}")
    
    # Cache Analysis
    if 'query_cache' in st.session_state and st.session_state.query_cache:
        st.header("💾 Cache Analysis")
        
        cache_data = []
        current_time = time.time()
        
        for key, entry in st.session_state.query_cache.items():
            age = current_time - entry['timestamp']
            cache_data.append({
                'Key': key[:50] + "..." if len(key) > 50 else key,
                'Age (seconds)': int(age),
                'TTL': entry['ttl'],
                'Expired': age > entry['ttl']
            })
        
        cache_df = pd.DataFrame(cache_data)
        
        col1, col2 = st.columns(2)
        
        with col1:
            expired_count = cache_df['Expired'].sum()
            st.metric("Expired Entries", expired_count)
        
        with col2:
            valid_count = len(cache_df) - expired_count
            st.metric("Valid Entries", valid_count)
        
        if st.checkbox("Show Cache Details"):
            st.dataframe(cache_df)
        
        # Cache cleanup
        if st.button("🧹 Clean Expired Cache"):
            optimizer = StreamlitOptimizer()
            optimizer.clear_old_cache()
            st.success("Expired cache entries cleared!")
            st.rerun()
    
    # Optimization Recommendations
    st.header("💡 Optimization Recommendations")
    
    recommendations = []
    
    if memory_mb > 800:
        recommendations.append("🔴 High memory usage detected. Consider clearing cache or restarting session.")
    
    if cpu_percent > 80:
        recommendations.append("🔴 High CPU usage. Check for long-running operations.")
    
    if cache_size > 100:
        recommendations.append("🟡 Large cache size. Consider clearing unused cache entries.")
    
    if 'last_activity' in st.session_state:
        inactive_time = time.time() - st.session_state.last_activity
        if inactive_time > 1200:
            recommendations.append("🟡 Long inactive session. Consider refreshing the page.")
    
    if 'page_load_times' in st.session_state and st.session_state.page_load_times:
        avg_load_time = sum(t['duration'] for t in st.session_state.page_load_times[-10:]) / min(10, len(st.session_state.page_load_times))
        if avg_load_time > 3:
            recommendations.append("🔴 Slow average load times. Check database queries and optimizations.")
    
    if not recommendations:
        recommendations.append("🟢 System performance is good!")
    
    for rec in recommendations:
        st.write(rec)
    
    # Quick Actions
    st.header("⚡ Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔥 Force GC"):
            gc.collect()
            st.success("Garbage collection forced!")
    
    with col2:
        if st.button("💾 Clear All Cache"):
            st.cache_data.clear()
            if 'query_cache' in st.session_state:
                st.session_state.query_cache = {}
            st.success("All cache cleared!")
    
    with col3:
        if st.button("🔄 Reset Session"):
            for key in list(st.session_state.keys()):
                if key not in ['authenticated_user', 'access_token']:  # Keep auth
                    del st.session_state[key]
            st.success("Session reset!")
            st.rerun()
    
    with col4:
        if st.button("📊 Export Stats"):
            stats = {
                'memory_mb': memory_mb,
                'cpu_percent': cpu_percent,
                'cache_size': cache_size,
                'session_size': session_size,
                'timestamp': datetime.now().isoformat()
            }
            st.json(stats)

if __name__ == "__main__":
    main()