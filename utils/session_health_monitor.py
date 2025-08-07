"""Session Health Monitor for GL ERP System"""

import streamlit as st
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd

def show_session_health_sidebar():
    """Show session health information in sidebar"""
    if 'authenticated_user' not in st.session_state or not st.session_state['authenticated_user']:
        return
    
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🩺 Session Health")
        
        # Get session info
        login_time = st.session_state.get('login_time', 0)
        last_activity = st.session_state.get('last_activity', 0)
        user = st.session_state.get('authenticated_user')
        
        if login_time and user:
            # Calculate session duration
            current_time = time.time()
            session_duration = current_time - login_time
            
            # Format duration
            hours, remainder = divmod(int(session_duration), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            # Session status
            if session_duration < 4 * 3600:  # Less than 4 hours
                status_color = "🟢"
                status_text = "Healthy"
            elif session_duration < 6 * 3600:  # Less than 6 hours
                status_color = "🟡"
                status_text = "Active"
            else:  # More than 6 hours
                status_color = "🟠"
                status_text = "Long Running"
            
            st.markdown(f"""
            **Status:** {status_color} {status_text}  
            **Duration:** {hours:02d}h {minutes:02d}m  
            **User:** {user.username}
            """)
            
            # Activity indicator
            if last_activity:
                activity_age = current_time - last_activity
                if activity_age < 300:  # 5 minutes
                    activity_status = "🟢 Active"
                elif activity_age < 1800:  # 30 minutes
                    activity_status = "🟡 Idle"
                else:
                    activity_status = "🔴 Inactive"
                
                st.caption(f"Activity: {activity_status}")
            
            # Quick actions
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄", help="Refresh Session"):
                    st.session_state['last_activity'] = current_time
                    st.rerun()
            
            with col2:
                if st.button("📊", help="Session Stats"):
                    st.session_state['show_session_stats'] = True

def show_session_statistics():
    """Show detailed session statistics"""
    if not st.session_state.get('show_session_stats', False):
        return
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Session Statistics")
    
    login_time = st.session_state.get('login_time', 0)
    last_activity = st.session_state.get('last_activity', 0)
    
    if login_time:
        current_time = time.time()
        
        # Calculate metrics
        total_duration = current_time - login_time
        activity_gap = current_time - (last_activity or login_time)
        
        # Display metrics
        st.sidebar.metric("Total Session", f"{total_duration/3600:.1f}h")
        st.sidebar.metric("Last Activity", f"{activity_gap/60:.1f}m ago")
        st.sidebar.metric("Auth Checks", st.session_state.get('auth_check_count', 0))
        
        # Close stats
        if st.sidebar.button("❌ Close Stats"):
            st.session_state['show_session_stats'] = False
            st.rerun()

def show_session_dashboard():
    """Show comprehensive session dashboard"""
    st.title("🩺 Session Health Dashboard")
    
    # Current session overview
    col1, col2, col3, col4 = st.columns(4)
    
    login_time = st.session_state.get('login_time', 0)
    last_activity = st.session_state.get('last_activity', 0)
    user = st.session_state.get('authenticated_user')
    
    if login_time and user:
        current_time = time.time()
        session_duration = current_time - login_time
        activity_gap = current_time - (last_activity or login_time)
        
        with col1:
            st.metric("Session Duration", f"{session_duration/3600:.1f}h")
        
        with col2:
            st.metric("User", user.username)
        
        with col3:
            st.metric("Last Activity", f"{activity_gap/60:.1f}m ago")
        
        with col4:
            persistent_session = st.session_state.get('_persistent_session')
            st.metric("Persistent", "✅ Yes" if persistent_session else "❌ No")
    
    # Session timeline
    st.subheader("📈 Session Timeline")
    
    # Simulated session activity data (in production, this would come from logs)
    if login_time:
        # Create timeline data
        timeline_data = []
        start_time = datetime.fromtimestamp(login_time)
        current_dt = datetime.fromtimestamp(current_time)
        
        # Generate activity points (simulated)
        import random
        time_points = []
        dt = start_time
        while dt < current_dt:
            # Simulate activity every 15-60 minutes
            gap = random.randint(15, 60)
            dt += timedelta(minutes=gap)
            if dt < current_dt:
                time_points.append(dt)
        
        if time_points:
            timeline_df = pd.DataFrame({
                'timestamp': time_points,
                'activity': ['Page Load'] * len(time_points),
                'duration': [random.uniform(0.5, 3.0) for _ in time_points]
            })
            
            fig = px.scatter(
                timeline_df, 
                x='timestamp', 
                y='activity',
                size='duration',
                title="Session Activity Timeline",
                color_discrete_sequence=['#1f77b4']
            )
            
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    # Session health metrics
    st.subheader("🔍 Health Metrics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Session health score
        if login_time:
            health_score = calculate_session_health_score(session_duration, activity_gap)
            
            fig = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = health_score,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Session Health Score"},
                delta = {'reference': 80},
                gauge = {
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 80], 'color': "yellow"},
                        {'range': [80, 100], 'color': "lightgreen"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Performance metrics
        st.markdown("### 📊 Performance Metrics")
        
        metrics_data = {
            'Metric': [
                'Auth Cache Hits',
                'Token Refreshes', 
                'Session Restores',
                'Page Loads',
                'DB Queries'
            ],
            'Count': [
                st.session_state.get('auth_cache_hits', 0),
                st.session_state.get('token_refreshes', 0),
                st.session_state.get('session_restores', 0),
                st.session_state.get('page_loads', 0),
                st.session_state.get('db_queries', 0)
            ]
        }
        
        metrics_df = pd.DataFrame(metrics_data)
        st.dataframe(metrics_df, hide_index=True, use_container_width=True)
    
    # Session recommendations
    show_session_recommendations(session_duration if login_time else 0, activity_gap if login_time else 0)

def calculate_session_health_score(session_duration: float, activity_gap: float) -> float:
    """Calculate a health score for the current session"""
    score = 100
    
    # Penalize very long sessions (over 8 hours)
    if session_duration > 8 * 3600:
        score -= min(30, (session_duration - 8 * 3600) / 3600 * 5)
    
    # Penalize long inactivity (over 30 minutes)
    if activity_gap > 30 * 60:
        score -= min(40, (activity_gap - 30 * 60) / 60 * 2)
    
    # Bonus for recent activity (under 5 minutes)
    if activity_gap < 5 * 60:
        score += 5
    
    return max(0, min(100, score))

def show_session_recommendations(session_duration: float, activity_gap: float):
    """Show session health recommendations"""
    st.subheader("💡 Recommendations")
    
    recommendations = []
    
    if session_duration > 12 * 3600:  # Over 12 hours
        recommendations.append({
            'icon': '🔄',
            'title': 'Long Session Detected',
            'description': 'Consider logging out and back in for optimal performance.',
            'priority': 'high'
        })
    elif session_duration > 8 * 3600:  # Over 8 hours
        recommendations.append({
            'icon': '⏰',
            'title': 'Extended Session',
            'description': 'Your session has been running for a while. Everything looks good!',
            'priority': 'medium'
        })
    
    if activity_gap > 60 * 60:  # Over 1 hour
        recommendations.append({
            'icon': '💤',
            'title': 'Long Inactivity',
            'description': 'Click refresh or navigate to a page to update your activity.',
            'priority': 'medium'
        })
    
    if not st.session_state.get('_persistent_session'):
        recommendations.append({
            'icon': '💾',
            'title': 'Enable Remember Me',
            'description': 'Enable "Remember me" on login to maintain sessions across browser restarts.',
            'priority': 'low'
        })
    
    if not recommendations:
        st.success("✅ Your session is healthy! No recommendations at this time.")
    else:
        for rec in recommendations:
            if rec['priority'] == 'high':
                st.error(f"{rec['icon']} **{rec['title']}**: {rec['description']}")
            elif rec['priority'] == 'medium':
                st.warning(f"{rec['icon']} **{rec['title']}**: {rec['description']}")
            else:
                st.info(f"{rec['icon']} **{rec['title']}**: {rec['description']}")

def increment_counter(key: str):
    """Increment a session counter"""
    if key not in st.session_state:
        st.session_state[key] = 0
    st.session_state[key] += 1

# Auto-increment page loads counter
if 'page_loads' not in st.session_state:
    st.session_state['page_loads'] = 0
st.session_state['page_loads'] += 1