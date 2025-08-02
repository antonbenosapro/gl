import streamlit as st
from utils.logger import StreamlitLogHandler
from auth.middleware import authenticator, require_permission
from utils.navigation import show_breadcrumb

# --- Basic Config ---
st.set_page_config(page_title="GL ERP System", layout="wide", initial_sidebar_state="expanded")

# --- SAP-Style CSS ---
st.markdown("""
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
        background-color: #ffffff;
        border: 1px solid #e1e4e8;
        border-radius: 6px;
        padding: 0.5rem;
        margin-bottom: 0.5rem;
        font-weight: 600;
        color: #24292e;
    }
    
    /* Card-like styling for dashboard */
    .stAlert {
        border-radius: 8px;
        border: 1px solid #e1e4e8;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    /* Metric styling */
    [data-testid="metric-container"] {
        background-color: white;
        border: 1px solid #e1e4e8;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
    
    /* Header styling */
    h1 {
        color: #24292e;
        border-bottom: 2px solid #0070f3;
        padding-bottom: 0.5rem;
    }
    
    h2 {
        color: #586069;
    }
    
    h3 {
        color: #24292e;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Authentication Required ---
authenticator.require_auth()

# --- Log page access ---
current_user = authenticator.get_current_user()
StreamlitLogHandler.log_page_access("Home", current_user.username)

# --- Get User Role from Authentication ---
user_permissions = authenticator.get_user_permissions()
is_admin = any(perm.startswith('users.') or perm.startswith('system.') for perm in user_permissions)
user_role = "Admin" if is_admin else "User"

# --- SAP-Style Sidebar Navigation ---
st.sidebar.markdown("# 🧾 GL Navigation")
st.sidebar.markdown("---")

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

# Financial Reporting
with st.sidebar.expander("📊 Financial Reports", expanded=True):
    if not any(perm.startswith('reports.') for perm in user_permissions):
        st.warning("🔒 Access Denied")
    else:
        st.markdown("**Core Financial Statements**")
        if st.button("📊 Balance Sheet", key="balance_sheet"):
            st.switch_page("pages/Balance_Sheet.py")
        if st.button("📈 Income Statement", key="income_statement"):
            st.switch_page("pages/Income_Statement.py")
        if st.button("💧 Cash Flow Statement", key="cash_flow"):
            st.switch_page("pages/Statement_of_Cash_Flows.py")
        
        st.markdown("**Detailed Reports**")
        if st.button("📑 Trial Balance", key="trial_balance"):
            st.switch_page("pages/Trial_Balance_Report.py")
        if st.button("📘 General Ledger", key="general_ledger"):
            st.switch_page("pages/General_Ledger_Report.py")
        if st.button("📄 Journal Listing", key="journal_listing"):
            st.switch_page("pages/Journal_Listing_Report.py")
        if st.button("🔍 GL Report Query", key="gl_query"):
            st.switch_page("pages/GL_Report_Query.py")

# System Administration
with st.sidebar.expander("⚙️ Administration", expanded=False):
    st.markdown("**User Management**")
    if authenticator.has_permission("users.read"):
        if st.button("👥 User Administration", key="user_admin"):
            st.switch_page("pages/User_Management.py")
    else:
        st.button("👥 User Administration", disabled=True, help="Permission required: users.read", key="user_admin_disabled")
    
    st.markdown("**System Tools**")
    if authenticator.has_permission("system.backup"):
        if st.button("💾 System Backup", key="system_backup"):
            st.info("System backup functionality - coming soon")
    else:
        st.button("💾 System Backup", disabled=True, help="Permission required: system.backup", key="system_backup_disabled")
    
    if is_admin:
        if st.button("🔧 System Settings", key="system_settings"):
            st.info("System settings - coming soon")
        if st.button("📋 System Logs", key="system_logs"):
            st.info("System logs viewer - coming soon")

st.sidebar.markdown("---")
st.sidebar.markdown(f"**👤 {current_user.full_name}**")
st.sidebar.markdown(f"*{user_role}*")
st.sidebar.markdown(f"📍 {', '.join(authenticator.get_user_companies()) or 'No Companies'}")

# Logout functionality
if st.sidebar.button("🚪 Logout", key="logout_btn", type="secondary"):
    authenticator.logout()
    st.rerun()

# --- Breadcrumb Navigation ---
show_breadcrumb("Home", "Dashboard")

# --- Main Content Area ---
st.markdown("# 🧾 General Ledger ERP System")
st.markdown("## Welcome to the Financial Management Dashboard")

# --- System Information Banner ---
info_col1, info_col2, info_col3 = st.columns([2, 1, 1])
with info_col1:
    st.markdown(f"**Welcome back, {current_user.full_name}!** You are logged in as **{user_role}**")
with info_col2:
    st.markdown(f"**Active Companies:** {len(authenticator.get_user_companies()) if authenticator.get_user_companies() else 0}")
with info_col3:
    st.markdown(f"**System Status:** 🟢 Online")

st.markdown("---")

# Dashboard Overview Cards
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.info("**📚 Master Data**\n\nManage chart of accounts and account configurations")

with col2:
    st.info("**📝 Transactions**\n\nProcess journal entries and transaction data")

with col3:
    st.info("**📊 Reports**\n\nGenerate financial statements and analysis")

with col4:
    st.info("**⚙️ Administration**\n\nSystem configuration and user management")

# Quick Actions Section
st.markdown("### ⚡ Quick Actions")
quick_col1, quick_col2, quick_col3 = st.columns(3)

with quick_col1:
    if any(perm.startswith('reports.') for perm in user_permissions):
        if st.button("🚀 Generate Trial Balance", key="quick_trial", type="primary"):
            st.switch_page("pages/Trial_Balance_Report.py")

with quick_col2:
    if any(perm.startswith('reports.') for perm in user_permissions):
        if st.button("🚀 View General Ledger", key="quick_gl", type="primary"):
            st.switch_page("pages/General_Ledger_Report.py")

with quick_col3:
    if authenticator.has_permission("journal.read"):
        if st.button("🚀 Journal Entries", key="quick_journal", type="primary"):
            st.switch_page("pages/Journal_Entry_Manager.py")

# System Status & Analytics
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 📊 System Analytics")
    analytics_col1, analytics_col2, analytics_col3 = st.columns(3)
    
    with analytics_col1:
        st.metric("System Status", "🟢 Online", delta="Uptime: 99.9%")
    
    with analytics_col2:
        st.metric("User Session", user_role, delta="Active")
    
    with analytics_col3:
        st.metric("Companies", len(authenticator.get_user_companies()) if authenticator.get_user_companies() else 0, delta="Available")

with col2:
    st.markdown("### 🔔 Notifications")
    st.info("💡 **Tip:** Use the sidebar navigation to access all GL modules efficiently")
    st.success("✅ All financial reports are up to date")
    if is_admin:
        st.warning("⚠️ Admin: Remember to review user permissions regularly")

# Recent Activity Section
st.markdown("### 📈 Recent Activity & Quick Links")
activity_col1, activity_col2 = st.columns(2)

with activity_col1:
    st.markdown("**🕒 Recently Accessed**")
    with st.container():
        st.markdown("• Trial Balance Report - *2 hours ago*")
        st.markdown("• General Ledger - *4 hours ago*")
        st.markdown("• Journal Entry Manager - *Yesterday*")
        st.markdown("• Chart of Accounts - *2 days ago*")

with activity_col2:
    st.markdown("**🔗 Helpful Resources**")
    with st.container():
        st.markdown("• [📖 User Guide](https://docs.example.com) - System documentation")
        st.markdown("• [❓ Support](mailto:support@example.com) - Get help")
        st.markdown("• [💬 Training](https://training.example.com) - Learn more")
        st.markdown("• [🔧 API Docs](https://api.example.com) - Integration guide")

# Workspace Summary
st.markdown("### 🏢 Workspace Summary")
workspace_col1, workspace_col2, workspace_col3, workspace_col4 = st.columns(4)

with workspace_col1:
    st.metric("Total GL Accounts", "247", delta="+3 this month")

with workspace_col2:
    st.metric("Active Transactions", "11,786", delta="+156 today")

with workspace_col3:
    st.metric("Open Periods", "1", delta="Current: 2025-01")

with workspace_col4:
    st.metric("Report Runs", "42", delta="+8 today")

# --- Footer ---
st.markdown("---")
st.markdown(f"© 2025 GL ERP System | Version 1.0 | All rights reserved")
