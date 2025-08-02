"""
SAP-Style Navigation Component for GL ERP System
Provides consistent sidebar navigation across all pages
"""
import streamlit as st
from auth.middleware import authenticator

def show_sap_sidebar():
    """Display the SAP-style sidebar navigation"""
    
    # Get current user info
    current_user = authenticator.get_current_user()
    user_permissions = authenticator.get_user_permissions()
    is_admin = any(perm.startswith('users.') or perm.startswith('system.') for perm in user_permissions)
    user_role = "Admin" if is_admin else "User"
    
    st.sidebar.markdown("# 🧾 GL Navigation")
    st.sidebar.markdown("---")

    # Master Data Management
    with st.sidebar.expander("📚 Master Data", expanded=False):
        st.markdown("**Chart of Accounts**")
        if st.button("🏠 Dashboard", key="nav_home"):
            st.switch_page("Home.py")
        if st.button("📘 Chart of Accounts Setup", key="nav_coa_setup"):
            st.switch_page("pages/1_Chart_of_Accounts.py")
        if st.button("📋 Chart of Accounts Report", key="nav_coa_report"):
            st.switch_page("pages/Chart_of_Accounts_Report.py")
        
        st.markdown("**Account Management**")
        if authenticator.has_permission("glaccount.create"):
            if st.button("➕ Create GL Account", key="nav_gl_create"):
                st.switch_page("pages/GL_Account_Entry.py")
        else:
            st.button("➕ Create GL Account", disabled=True, help="Permission required: glaccount.create", key="nav_gl_create_disabled")

    # Transaction Processing
    with st.sidebar.expander("📝 Transactions", expanded=False):
        st.markdown("**Journal Entries**")
        if authenticator.has_permission("journal.read"):
            if st.button("📄 Journal Entry Manager", key="nav_je_manager"):
                st.switch_page("pages/Journal_Entry_Manager.py")
        else:
            st.button("📄 Journal Entry Manager", disabled=True, help="Permission required: journal.read", key="nav_je_manager_disabled")
        
        st.markdown("**Data Entry**")
        if authenticator.has_permission("glaccount.create"):
            if st.button("📥 Manual Journal Entry", key="nav_manual_je"):
                st.switch_page("pages/GL_Account_Entry.py")
        else:
            st.button("📥 Manual Journal Entry", disabled=True, help="Permission required: glaccount.create", key="nav_manual_je_disabled")

    # Financial Reporting
    with st.sidebar.expander("📊 Financial Reports", expanded=False):
        if not any(perm.startswith('reports.') for perm in user_permissions):
            st.warning("🔒 Access Denied")
        else:
            st.markdown("**Core Financial Statements**")
            if st.button("📊 Balance Sheet", key="nav_balance_sheet"):
                st.switch_page("pages/Balance_Sheet.py")
            if st.button("📈 Income Statement", key="nav_income_statement"):
                st.switch_page("pages/Income_Statement.py")
            if st.button("💧 Cash Flow Statement", key="nav_cash_flow"):
                st.switch_page("pages/Statement_of_Cash_Flows.py")
            
            st.markdown("**Detailed Reports**")
            if st.button("📑 Trial Balance", key="nav_trial_balance"):
                st.switch_page("pages/Trial_Balance_Report.py")
            if st.button("📘 General Ledger", key="nav_general_ledger"):
                st.switch_page("pages/General_Ledger_Report.py")
            if st.button("📄 Journal Listing", key="nav_journal_listing"):
                st.switch_page("pages/Journal_Listing_Report.py")
            if st.button("🔍 GL Report Query", key="nav_gl_query"):
                st.switch_page("pages/GL_Report_Query.py")
            
            st.markdown("**Analytics**")
            if st.button("📈 Revenue & EBITDA Trend", key="nav_revenue_ebitda"):
                st.switch_page("pages/Revenue_EBITDA_Trend.py")
            if st.button("📊 Revenue & Expenses Trend", key="nav_revenue_expenses"):
                st.switch_page("pages/Revenue_Expenses_Trend.py")
            if st.button("📈 Profitability Metrics", key="nav_profitability"):
                st.switch_page("pages/Profitability_Metrics.py")
            if st.button("💧 Liquidity & Working Capital", key="nav_liquidity"):
                st.switch_page("pages/Liquidity_Working_Capital_Metrics.py")

    # System Administration
    with st.sidebar.expander("⚙️ Administration", expanded=False):
        st.markdown("**User Management**")
        if authenticator.has_permission("users.read"):
            if st.button("👥 User Administration", key="nav_user_admin"):
                st.switch_page("pages/User_Management.py")
        else:
            st.button("👥 User Administration", disabled=True, help="Permission required: users.read", key="nav_user_admin_disabled")
        
        st.markdown("**System Tools**")
        if authenticator.has_permission("system.backup"):
            if st.button("💾 System Backup", key="nav_system_backup"):
                st.info("System backup functionality - coming soon")
        else:
            st.button("💾 System Backup", disabled=True, help="Permission required: system.backup", key="nav_system_backup_disabled")
        
        if is_admin:
            if st.button("🔧 System Settings", key="nav_system_settings"):
                st.info("System settings - coming soon")
            if st.button("📋 System Logs", key="nav_system_logs"):
                st.info("System logs viewer - coming soon")

    # User Information
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**👤 {current_user.full_name}**")
    st.sidebar.markdown(f"*{user_role}*")
    st.sidebar.markdown(f"📍 {', '.join(authenticator.get_user_companies()) or 'No Companies'}")

    # Logout functionality
    if st.sidebar.button("🚪 Logout", key="nav_logout_btn", type="secondary"):
        authenticator.logout()
        st.rerun()

def show_breadcrumb(page_title, *path):
    """Display breadcrumb navigation"""
    breadcrumb_path = "Home"
    for item in path:
        breadcrumb_path += f" > {item}"
    
    st.markdown(f"""
    <div style="background-color: #f8f9fa; padding: 0.5rem 1rem; border-radius: 4px; margin-bottom: 1rem; border-left: 4px solid #0070f3;">
        <span style="color: #586069; font-size: 0.875rem;">📍 Navigation: </span>
        <span style="color: #24292e; font-weight: 500;">{breadcrumb_path}</span>
    </div>
    """, unsafe_allow_html=True)