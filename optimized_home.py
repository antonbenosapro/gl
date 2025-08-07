import streamlit as st
from utils.logger import StreamlitLogHandler
from auth.optimized_middleware import optimized_authenticator as authenticator, require_permission
from utils.navigation import show_breadcrumb
from utils.streamlit_optimization import (
    StreamlitOptimizer, monitor_session_health, setup_auto_refresh,
    performance_tracker, safe_execute
)
from utils.db_connection_manager import cleanup_connections
import atexit
import signal

# --- Performance Optimizations ---
@performance_tracker
def initialize_app():
    """Initialize app with optimizations"""
    # Session optimization
    monitor_session_health()
    
    # Auto-refresh setup (25 minutes to prevent 30-minute timeout)
    setup_auto_refresh(25)
    
    # Cleanup connections on exit
    atexit.register(cleanup_connections)

# --- Basic Config ---
st.set_page_config(
    page_title="GL ERP System", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# Initialize optimizations
initialize_app()

# --- SAP-Style CSS (Optimized) ---
@st.cache_data
def get_css_styles():
    """Cache CSS styles to prevent re-rendering"""
    return """
<style>
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8f9fa;
    }
    
    /* Main content area */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Custom button styling for SAP look */
    .stButton > button {
        background-color: #0070f3;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 0.5rem 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        width: 100%;
        margin-bottom: 0.25rem;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        background-color: #0051cc;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    
    /* Disabled button styling */
    .stButton > button:disabled {
        background-color: #e5e5e5;
        color: #999999;
        cursor: not-allowed;
    }
    
    /* Sidebar expander styling */
    .streamlit-expanderHeader {
        background-color: #f0f0f0;
        border-radius: 4px;
        font-weight: 600;
    }
    
    /* Header styling */
    .header-style {
        background: linear-gradient(90deg, #0070f3, #00c6ff);
        padding: 1rem;
        border-radius: 8px;
        color: white;
        margin-bottom: 2rem;
    }
    
    /* Metric styling */
    .metric-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #0070f3;
    }
    
    /* Warning box */
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        border-radius: 4px;
        padding: 0.75rem;
        margin: 0.5rem 0;
    }
    
    /* Session health indicator */
    .session-health {
        position: fixed;
        top: 10px;
        right: 10px;
        background: rgba(0, 255, 0, 0.1);
        padding: 5px 10px;
        border-radius: 15px;
        font-size: 12px;
        z-index: 999;
    }
</style>
"""

st.markdown(get_css_styles(), unsafe_allow_html=True)

# Session health indicator
if 'last_activity' in st.session_state:
    import time
    inactive_time = time.time() - st.session_state.last_activity
    if inactive_time < 300:  # Less than 5 minutes
        st.markdown(
            '<div class="session-health">🟢 Session Active</div>', 
            unsafe_allow_html=True
        )
    elif inactive_time < 1200:  # Less than 20 minutes
        st.markdown(
            '<div class="session-health" style="background: rgba(255, 255, 0, 0.1)">🟡 Session Idle</div>', 
            unsafe_allow_html=True
        )

# --- Authentication Required ---
@performance_tracker
def handle_authentication():
    """Handle authentication with performance tracking"""
    try:
        authenticator.require_auth()
        return True
    except Exception as e:
        st.error(f"Authentication error: {e}")
        st.stop()
        return False

if not handle_authentication():
    st.stop()

# --- Get User Info (Cached) ---
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_user_info():
    """Get user information with caching"""
    try:
        current_user = authenticator.get_current_user()
        user_permissions = authenticator.get_user_permissions()
        is_admin = any(perm.startswith('users.') or perm.startswith('system.') for perm in user_permissions)
        user_role = "Admin" if is_admin else "User"
        
        return {
            'user': current_user,
            'permissions': user_permissions,
            'is_admin': is_admin,
            'role': user_role
        }
    except Exception as e:
        st.error(f"Error getting user info: {e}")
        return None

user_info = safe_execute(get_user_info)
if not user_info:
    st.error("Failed to load user information")
    st.stop()

current_user = user_info['user']
user_permissions = user_info['permissions']
is_admin = user_info['is_admin']
user_role = user_info['role']

# --- Log page access ---
safe_execute(lambda: StreamlitLogHandler.log_page_access("Home", current_user.username))

# --- Optimized Sidebar Navigation ---
@performance_tracker
def render_sidebar():
    """Render sidebar with performance optimizations"""
    
    st.sidebar.markdown("# 🧾 GL Navigation")
    st.sidebar.markdown("---")
    
    # Performance info for admins
    if is_admin and st.sidebar.checkbox("Show Performance Info"):
        if 'page_load_times' in st.session_state:
            recent_loads = st.session_state.page_load_times[-5:]
            if recent_loads:
                avg_time = sum(load['duration'] for load in recent_loads) / len(recent_loads)
                st.sidebar.metric("Avg Load Time", f"{avg_time:.2f}s")
    
    # Master Data Management
    with st.sidebar.expander("📚 Master Data", expanded=False):
        st.markdown("**Chart of Accounts**")
        if st.button("📘 Chart of Accounts Setup", key="coa_setup"):
            st.switch_page("pages/1_Chart_of_Accounts.py")
        if st.button("📋 Chart of Accounts Report", key="coa_report"):
            st.switch_page("pages/Chart_of_Accounts_Report.py")
        
        st.markdown("**Account Management**")
        if authenticator.has_permission("glaccount.create"):
            if st.button("➕ Create GL Account", key="gl_create"):
                st.switch_page("pages/GL_Account_Entry.py")
        else:
            st.button("➕ Create GL Account", disabled=True, help="Permission required: glaccount.create", key="gl_create_disabled")

    # Transaction Processing
    with st.sidebar.expander("📝 Transactions", expanded=False):
        st.markdown("**Journal Entries**")
        if authenticator.has_permission("journal.read"):
            if st.button("📄 Journal Entry Manager", key="je_manager"):
                st.switch_page("pages/Journal_Entry_Manager.py")
        else:
            st.button("📄 Journal Entry Manager", disabled=True, help="Permission required: journal.read", key="je_manager_disabled")
        
        st.markdown("**Data Entry**")
        if authenticator.has_permission("glaccount.create"):
            if st.button("📥 Manual Journal Entry", key="manual_je"):
                st.switch_page("pages/GL_Account_Entry.py")
        else:
            st.button("📥 Manual Journal Entry", disabled=True, help="Permission required: glaccount.create", key="manual_je_disabled")
    
    # Reporting
    with st.sidebar.expander("📊 Reporting", expanded=False):
        if st.button("📈 General Ledger Report", key="gl_report"):
            st.switch_page("pages/General_Ledger_Report.py")
        if st.button("⚖️ Trial Balance", key="trial_balance"):
            st.switch_page("pages/Trial_Balance_Report.py")
        if st.button("💼 Balance Sheet", key="balance_sheet"):
            st.switch_page("pages/Balance_Sheet.py")
        if st.button("💰 Income Statement", key="income_statement"):
            st.switch_page("pages/Income_Statement.py")
    
    # Workflow & Approval
    with st.sidebar.expander("🔄 Workflow", expanded=False):
        if authenticator.has_permission("workflow.read"):
            if st.button("📋 Approval Dashboard", key="approval_dash"):
                st.switch_page("pages/Approval_Dashboard.py")
        if authenticator.has_permission("workflow.admin"):
            if st.button("⚙️ Workflow Admin", key="workflow_admin"):
                st.switch_page("pages/Workflow_Admin.py")
    
    # System Administration
    if is_admin:
        with st.sidebar.expander("🔧 Administration", expanded=False):
            if st.button("👥 User Management", key="user_mgmt"):
                st.switch_page("pages/User_Management.py")
            if st.button("🏢 Business Units", key="business_units"):
                st.switch_page("pages/Business_Unit_Management.py")
            if st.button("💱 Currency Admin", key="currency_admin"):
                st.switch_page("pages/Currency_Exchange_Admin.py")
    
    # Session Management
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Session**")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🔄 Refresh", help="Refresh session"):
            st.rerun()
    
    with col2:
        if st.button("🚪 Logout"):
            authenticator.logout()
            st.rerun()

# Render sidebar
safe_execute(render_sidebar)

# --- Main Content ---
@performance_tracker
def render_main_content():
    """Render main content with optimizations"""
    
    # Header
    show_breadcrumb("Home", "Dashboard", "General Ledger ERP")
    
    st.markdown(
        f"""
        <div class="header-style">
            <h1>🧾 General Ledger ERP System</h1>
            <p>Welcome back, <strong>{current_user.first_name} {current_user.last_name}</strong> 
               | Role: <strong>{user_role}</strong> | 
               Session: <span style="color: #00ff88;">Active</span>
            </p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # Quick Actions
    st.subheader("🚀 Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if authenticator.has_permission("journal.create"):
            if st.button("📝 Create Journal Entry", type="primary"):
                st.switch_page("pages/Journal_Entry_Manager.py")
        else:
            st.button("📝 Create Journal Entry", disabled=True, help="Permission required")
    
    with col2:
        if st.button("📊 View Reports"):
            st.switch_page("pages/General_Ledger_Report.py")
    
    with col3:
        if authenticator.has_permission("workflow.read"):
            if st.button("✅ Approvals"):
                st.switch_page("pages/Approval_Dashboard.py")
        else:
            st.button("✅ Approvals", disabled=True, help="Permission required")
    
    with col4:
        if st.button("🔍 Query Data"):
            st.switch_page("pages/GL_Report_Query.py")
    
    # System Status (Cached)
    @st.cache_data(ttl=60)  # Cache for 1 minute
    def get_system_status():
        """Get system status with caching"""
        try:
            from utils.db_connection_manager import execute_query
            
            # Quick system health checks
            pending_approvals = execute_query(
                "SELECT COUNT(*) FROM journalentryheader WHERE workflow_status = 'PENDING_APPROVAL'",
                fetch="one"
            )[0]
            
            draft_entries = execute_query(
                "SELECT COUNT(*) FROM journalentryheader WHERE workflow_status = 'DRAFT'",
                fetch="one"
            )[0]
            
            total_accounts = execute_query(
                "SELECT COUNT(*) FROM glaccount WHERE (blocked_for_posting = FALSE OR blocked_for_posting IS NULL) AND (marked_for_deletion = FALSE OR marked_for_deletion IS NULL)",
                fetch="one"
            )[0]
            
            return {
                'pending_approvals': pending_approvals,
                'draft_entries': draft_entries,
                'total_accounts': total_accounts
            }
        except Exception as e:
            st.error(f"Error getting system status: {e}")
            return None
    
    # Display system status
    st.subheader("📊 System Status")
    
    status = safe_execute(get_system_status)
    if status:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Pending Approvals", status['pending_approvals'])
        
        with col2:
            st.metric("Draft Entries", status['draft_entries'])
        
        with col3:
            st.metric("Active GL Accounts", status['total_accounts'])
    else:
        st.warning("Unable to load system status")
    
    # Recent Activity (if user has permissions)
    if authenticator.has_permission("journal.read"):
        with st.expander("📋 Recent Journal Entries"):
            @st.cache_data(ttl=300)  # Cache for 5 minutes
            def get_recent_entries():
                try:
                    from utils.db_connection_manager import read_sql
                    return read_sql("""
                        SELECT documentnumber, reference, workflow_status, createdby, createdat
                        FROM journalentryheader
                        ORDER BY createdat DESC
                        LIMIT 10
                    """)
                except Exception as e:
                    st.error(f"Error loading recent entries: {e}")
                    return None
            
            recent_entries = safe_execute(get_recent_entries)
            if recent_entries is not None and not recent_entries.empty:
                st.dataframe(
                    recent_entries,
                    use_container_width=True,
                    column_config={
                        'documentnumber': 'Document',
                        'reference': 'Reference',
                        'workflow_status': 'Status',
                        'createdby': 'Created By',
                        'createdat': st.column_config.DatetimeColumn('Created')
                    }
                )
            else:
                st.info("No recent entries to display")
    
    # Performance tip
    if 'last_activity' in st.session_state:
        import time
        inactive_time = time.time() - st.session_state.last_activity
        if inactive_time > 600:  # 10 minutes inactive
            st.warning("💡 **Performance Tip**: Consider refreshing the page if you experience slowdowns after prolonged inactivity.")

# Render main content
safe_execute(render_main_content)

# --- Footer ---
st.markdown("---")
st.markdown("*GL ERP System - Optimized Version | Session Management Active*")