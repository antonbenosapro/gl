"""User Management Page"""

import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy import text

from auth.middleware import authenticator, require_permission
from auth.models import UserCreate, UserUpdate, AccessType
from auth.service import user_service, AuthenticationError
from auth.security import password_checker
from db_config import engine
from utils.logger import StreamlitLogHandler, get_logger
from utils.navigation import show_sap_sidebar, show_breadcrumb
from datetime import date
import time

logger = get_logger("user_management")

# Require authentication and permission
authenticator.require_auth()
authenticator.require_permission("users.read")

st.set_page_config(page_title="👥 User Management", layout="wide", initial_sidebar_state="expanded")

# SAP-Style Navigation
show_sap_sidebar()
show_breadcrumb("User Management", "Administration", "Users")

StreamlitLogHandler.log_page_access("User Management", authenticator.get_current_user().username)

st.title("👥 User Management")

# Initialize session state
if 'selected_user_id' not in st.session_state:
    st.session_state.selected_user_id = None
if 'show_create_user' not in st.session_state:
    st.session_state.show_create_user = False

# Tab structure for different management functions
tab1, tab2, tab3, tab4 = st.tabs(["👥 Users", "🎯 Approval Levels", "🔧 Approvers", "🔄 Delegations"])


def load_users():
    """Load all users from database"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT u.id, u.username, u.email, u.first_name, u.last_name,
                       u.is_active, u.is_verified, u.must_change_password,
                       u.last_login_at, u.failed_login_attempts, u.locked_until,
                       u.created_at,
                       STRING_AGG(r.name, ', ') as roles
                FROM users u
                LEFT JOIN user_roles ur ON u.id = ur.user_id
                LEFT JOIN roles r ON ur.role_id = r.id
                GROUP BY u.id, u.username, u.email, u.first_name, u.last_name,
                         u.is_active, u.is_verified, u.must_change_password,
                         u.last_login_at, u.failed_login_attempts, u.locked_until,
                         u.created_at
                ORDER BY u.created_at DESC
            """))
            
            return pd.DataFrame(result.fetchall())
    except Exception as e:
        logger.error(f"Error loading users: {e}")
        st.error("Failed to load users")
        return pd.DataFrame()


def load_roles():
    """Load all roles from database"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, name, description, is_active
                FROM roles
                WHERE is_active = TRUE
                ORDER BY name
            """))
            
            return result.fetchall()
    except Exception as e:
        logger.error(f"Error loading roles: {e}")
        return []


def load_user_roles(user_id: int):
    """Load roles for specific user"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT r.id, r.name
                FROM roles r
                JOIN user_roles ur ON r.id = ur.role_id
                WHERE ur.user_id = :user_id
            """), {'user_id': user_id})
            
            return [row[0] for row in result]
    except Exception as e:
        logger.error(f"Error loading user roles: {e}")
        return []


# Approval Management Helper Functions
@st.cache_data(ttl=10)
def get_approval_levels():
    """Get all approval levels"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT id, level_name, level_order, min_amount, max_amount, 
                   company_code, department, is_active
            FROM approval_levels 
            ORDER BY company_code, level_order
        """))
        return pd.DataFrame(result.fetchall(), columns=[
            'id', 'level_name', 'level_order', 'min_amount', 'max_amount',
            'company_code', 'department', 'is_active'
        ])

@st.cache_data(ttl=10)
def get_approvers():
    """Get all approvers with their approval levels"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT a.id, a.user_id, al.level_name, al.level_order, 
                   a.company_code, a.department, a.is_active,
                   a.delegated_to, a.delegation_start_date, a.delegation_end_date
            FROM approvers a
            JOIN approval_levels al ON al.id = a.approval_level_id
            ORDER BY a.company_code, al.level_order, a.user_id
        """))
        return pd.DataFrame(result.fetchall(), columns=[
            'id', 'user_id', 'level_name', 'level_order', 'company_code', 
            'department', 'is_active', 'delegated_to', 'delegation_start_date', 'delegation_end_date'
        ])

def refresh_approval_data():
    """Clear cached approval data to refresh"""
    get_approval_levels.clear()
    get_approvers.clear()


def create_user_form():
    """Show create user form"""
    st.markdown("### ➕ Create New User")
    
    with st.form("create_user_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("Username*", help="Unique username for login")
            email = st.text_input("Email*", help="User's email address")
            first_name = st.text_input("First Name")
        
        with col2:
            last_name = st.text_input("Last Name")
            password = st.text_input("Password*", type="password", help="Temporary password")
            must_change_password = st.checkbox("Must change password on first login", value=True)
        
        # Role selection
        st.markdown("**Assign Roles:**")
        roles = load_roles()
        role_options = {f"{role[1]} - {role[2] or 'No description'}": role[0] for role in roles}
        selected_roles = st.multiselect("Select roles", options=list(role_options.keys()))
        role_ids = [role_options[role] for role in selected_roles]
        
        # Company access
        st.markdown("**Company Access:**")
        companies = ['1000', '2000', 'C003']  # This would come from a companies table
        selected_companies = st.multiselect("Select companies", options=companies)
        
        submitted = st.form_submit_button("Create User", type="primary")
        
        if submitted:
            if not all([username, email, password]):
                st.error("Please fill in all required fields (marked with *)")
                return
            
            # Check password strength
            password_strength = password_checker.check_strength(password)
            if not password_strength["is_valid"]:
                st.error("Password does not meet requirements:")
                for msg in password_strength["messages"]:
                    st.error(f"• {msg}")
                return
            
            try:
                # Create user
                user_data = UserCreate(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    role_ids=role_ids,
                    must_change_password=must_change_password
                )
                
                current_user = authenticator.get_current_user()
                new_user = user_service.create_user(user_data, current_user.id)
                
                # Add company access
                if selected_companies:
                    with engine.begin() as conn:
                        for company in selected_companies:
                            conn.execute(text("""
                                INSERT INTO user_company_access (user_id, company_code, access_type, granted_by)
                                VALUES (:user_id, :company_code, :access_type, :granted_by)
                            """), {
                                'user_id': new_user.id,
                                'company_code': company,
                                'access_type': AccessType.READ_WRITE.value,
                                'granted_by': current_user.id
                            })
                
                st.success(f"User '{username}' created successfully!")
                StreamlitLogHandler.log_form_submission("create_user", True, current_user.username)
                
                # Reset form
                st.session_state.show_create_user = False
                st.rerun()
                
            except AuthenticationError as e:
                st.error(str(e))
                StreamlitLogHandler.log_form_submission("create_user", False, current_user.username, [str(e)])
            except Exception as e:
                logger.error(f"Error creating user: {e}")
                st.error("Failed to create user")


def edit_user_form(user_data):
    """Show edit user form"""
    st.markdown(f"### ✏️ Edit User: {user_data['username']}")
    
    with st.form("edit_user_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            email = st.text_input("Email", value=user_data['email'] or "")
            first_name = st.text_input("First Name", value=user_data['first_name'] or "")
            is_active = st.checkbox("Active", value=user_data['is_active'])
        
        with col2:
            last_name = st.text_input("Last Name", value=user_data['last_name'] or "")
            is_verified = st.checkbox("Verified", value=user_data['is_verified'])
            reset_password = st.checkbox("Force password change on next login")
        
        # Role selection
        st.markdown("**Assign Roles:**")
        roles = load_roles()
        current_role_ids = load_user_roles(user_data['id'])
        role_options = {f"{role[1]} - {role[2] or 'No description'}": role[0] for role in roles}
        
        selected_roles = st.multiselect(
            "Select roles", 
            options=list(role_options.keys()),
            default=[k for k, v in role_options.items() if v in current_role_ids]
        )
        role_ids = [role_options[role] for role in selected_roles]
        
        # Admin password reset section
        if authenticator.has_permission("users.update"):
            st.divider()
            st.markdown("**🔐 Admin Password Reset:**")
            
            col_reset1, col_reset2 = st.columns(2)
            with col_reset1:
                new_password = st.text_input(
                    "Set New Password (optional)", 
                    type="password",
                    help="Leave blank to only force password change. Enter new password to reset it directly."
                )
            with col_reset2:
                confirm_password = st.text_input(
                    "Confirm New Password", 
                    type="password",
                    help="Re-enter the new password to confirm."
                )
            
            # Password validation
            password_error = None
            if new_password and confirm_password:
                if new_password != confirm_password:
                    password_error = "Passwords do not match"
                elif len(new_password) < 8:
                    password_error = "Password must be at least 8 characters"
                elif not any(c.isupper() for c in new_password):
                    password_error = "Password must contain at least one uppercase letter"
                elif not any(c.islower() for c in new_password):
                    password_error = "Password must contain at least one lowercase letter"
                elif not any(c.isdigit() for c in new_password):
                    password_error = "Password must contain at least one number"
            
            if password_error:
                st.error(f"❌ {password_error}")
            elif new_password and confirm_password and new_password == confirm_password:
                st.success("✅ Password meets security requirements")
        
        col_update, col_delete = st.columns(2)
        
        with col_update:
            update_submitted = st.form_submit_button("Update User", type="primary")
        
        with col_delete:
            if authenticator.has_permission("users.delete"):
                delete_submitted = st.form_submit_button("Delete User", type="secondary")
            else:
                delete_submitted = False
        
        if update_submitted:
            # Check password reset validation first
            if new_password and password_error:
                st.error(f"❌ Cannot update user: {password_error}")
                return
            
            try:
                user_update = UserUpdate(
                    email=email if email != user_data['email'] else None,
                    first_name=first_name if first_name != user_data['first_name'] else None,
                    last_name=last_name if last_name != user_data['last_name'] else None,
                    is_active=is_active if is_active != user_data['is_active'] else None,
                    role_ids=role_ids
                )
                
                current_user = authenticator.get_current_user()
                user_service.update_user(user_data['id'], user_update, current_user.id)
                
                # Handle password reset/force change
                with engine.begin() as conn:
                    if new_password and confirm_password and new_password == confirm_password:
                        # Admin is setting a new password - use security manager for consistency
                        from auth.security import security_manager
                        password_hash = security_manager.hash_password(new_password)
                        
                        conn.execute(text("""
                            UPDATE users 
                            SET password_hash = :password_hash, must_change_password = TRUE
                            WHERE id = :user_id
                        """), {'user_id': user_data['id'], 'password_hash': password_hash})
                        
                        st.success(f"✅ Password reset successfully for {user_data['username']}! User must change password on next login.")
                        
                    elif reset_password:
                        # Admin is just forcing password change
                        conn.execute(text("""
                            UPDATE users 
                            SET must_change_password = TRUE
                            WHERE id = :user_id
                        """), {'user_id': user_data['id']})
                        
                        st.success(f"✅ {user_data['username']} will be required to change password on next login.")
                
                if not new_password:
                    st.success("User updated successfully!")
                    
                StreamlitLogHandler.log_form_submission("update_user", True, current_user.username)
                
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                logger.error(f"Error updating user: {e}")
                st.error(f"Failed to update user: {e}")
        
        if delete_submitted:
            st.warning("⚠️ Are you sure you want to delete this user? This action cannot be undone.")
            if st.button("Confirm Delete", type="secondary"):
                try:
                    with engine.begin() as conn:
                        # Delete user (cascading deletes will handle related records)
                        conn.execute(text("DELETE FROM users WHERE id = :user_id"), 
                                   {'user_id': user_data['id']})
                    
                    st.success("User deleted successfully!")
                    current_user = authenticator.get_current_user()
                    StreamlitLogHandler.log_form_submission("delete_user", True, current_user.username)
                    
                    st.session_state.selected_user_id = None
                    st.rerun()
                    
                except Exception as e:
                    logger.error(f"Error deleting user: {e}")
                    st.error("Failed to delete user")


# TAB 1: USER MANAGEMENT
with tab1:
    # Main UI
    col_header, col_actions = st.columns([3, 1])

    with col_header:
        st.markdown("Manage system users, roles, and permissions")

    with col_actions:
        if authenticator.has_permission("users.create"):
            if st.button("➕ Create User"):
                st.session_state.show_create_user = True
                st.session_state.selected_user_id = None

    # Show appropriate form
    if st.session_state.show_create_user:
        create_user_form()
        
        if st.button("❌ Cancel"):
            st.session_state.show_create_user = False
            st.rerun()

    elif st.session_state.selected_user_id:
        # Load user data for editing
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, username, email, first_name, last_name, is_active, is_verified,
                           must_change_password, last_login_at, failed_login_attempts, locked_until
                    FROM users 
                    WHERE id = :user_id
                """), {'user_id': st.session_state.selected_user_id})
                
                user_row = result.first()
                if user_row:
                    user_data = user_row._asdict()
                    edit_user_form(user_data)
                else:
                    st.error("User not found")
                    st.session_state.selected_user_id = None
        except Exception as e:
            logger.error(f"Error loading user for edit: {e}")
            st.error("Failed to load user data")
        
        if st.button("⬅️ Back to User List"):
            st.session_state.selected_user_id = None
            st.rerun()

    else:
        # Show user list
        st.markdown("### 📋 User List")
        
        users_df = load_users()
        
        if not users_df.empty:
            # Format data for display
            display_df = users_df.copy()
            display_df['status'] = display_df.apply(lambda row: 
                '🔒 Locked' if row['locked_until'] and pd.to_datetime(row['locked_until']) > datetime.now()
                else '❌ Inactive' if not row['is_active']
                else '⚠️ Unverified' if not row['is_verified']
                else '✅ Active', axis=1)
            
            display_df['last_login'] = pd.to_datetime(display_df['last_login_at']).dt.strftime('%Y-%m-%d %H:%M')
            display_df['created'] = pd.to_datetime(display_df['created_at']).dt.strftime('%Y-%m-%d')
            
            # Select columns to display
            display_columns = ['username', 'email', 'first_name', 'last_name', 'status', 
                             'roles', 'last_login', 'failed_login_attempts', 'created']
            
            display_df = display_df[['id'] + display_columns]
            
            # Show data table with selection
            st.dataframe(
                display_df,
                column_config={
                    "id": st.column_config.NumberColumn("ID"),
                    "username": st.column_config.TextColumn("Username"),
                    "email": st.column_config.TextColumn("Email"),
                    "first_name": st.column_config.TextColumn("First Name"),
                    "last_name": st.column_config.TextColumn("Last Name"),
                    "status": st.column_config.TextColumn("Status"),
                    "roles": st.column_config.TextColumn("Roles"),
                    "last_login": st.column_config.TextColumn("Last Login"),
                    "failed_login_attempts": st.column_config.NumberColumn("Failed Attempts"),
                    "created": st.column_config.TextColumn("Created"),
                },
                use_container_width=True,
                hide_index=True
            )
            
            # User selection dropdown
            if authenticator.has_permission("users.update"):
                st.markdown("### ✏️ Select User to Edit")
                user_options = {f"{row['username']} ({row['email']})": row['id'] 
                              for _, row in display_df.iterrows()}
                
                selected_user_option = st.selectbox(
                    "Select a user to edit:",
                    options=[""] + list(user_options.keys()),
                    format_func=lambda x: "Select a user..." if x == "" else x
                )
                
                if selected_user_option and selected_user_option != "":
                    selected_user_id = user_options[selected_user_option]
                    username = selected_user_option.split(' (')[0]
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"✏️ Edit User: {username}"):
                            st.session_state.selected_user_id = selected_user_id
                            st.rerun()
                    
                    with col2:
                        if st.button(f"🔐 Reset Password: {username}", type="secondary"):
                            # Quick password reset functionality
                            try:
                                import secrets
                                from auth.security import security_manager
                                
                                # Generate temporary password
                                temp_password = f"Temp{secrets.randbelow(9999):04d}!"
                                
                                # Hash the password using security manager for consistency
                                password_hash = security_manager.hash_password(temp_password)
                                
                                with engine.begin() as conn:
                                    conn.execute(text("""
                                        UPDATE users 
                                        SET password_hash = :password_hash, must_change_password = TRUE
                                        WHERE id = :user_id
                                    """), {'user_id': selected_user_id, 'password_hash': password_hash})
                                
                                st.success(f"✅ Password reset for {username}")
                                st.info(f"🔑 **New temporary password:** `{temp_password}`")
                                st.warning("⚠️ User must change this password on next login")
                                
                                current_user = authenticator.get_current_user()
                                StreamlitLogHandler.log_form_submission("reset_password", True, current_user.username)
                                
                            except Exception as e:
                                logger.error(f"Error resetting password: {e}")
                                st.error(f"❌ Failed to reset password: {e}")
            else:
                st.info("You don't have permission to edit users")
            
            # Statistics
            st.markdown("### 📊 User Statistics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Users", len(users_df))
            
            with col2:
                active_users = len(users_df[users_df['is_active'] == True])
                st.metric("Active Users", active_users)
            
            with col3:
                locked_users = len(users_df[
                    (users_df['locked_until'].notna()) & 
                    (pd.to_datetime(users_df['locked_until']) > datetime.now())
                ])
                st.metric("Locked Users", locked_users)
            
            with col4:
                unverified_users = len(users_df[users_df['is_verified'] == False])
                st.metric("Unverified Users", unverified_users)
        
        else:
            st.info("No users found in the system")


# TAB 2: APPROVAL LEVELS MANAGEMENT
with tab2:
    if not authenticator.has_permission("workflow.manage"):
        st.error("🚫 You don't have permission to manage approval workflows")
    else:
        st.header("🎯 Approval Levels Management")
        
        # Add new approval level section
        with st.expander("➕ Add New Approval Level", expanded=False):
            with st.form("add_level_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    new_level_name = st.text_input("Level Name", placeholder="e.g., Senior Manager")
                    new_level_order = st.number_input("Level Order", min_value=1, max_value=10, value=1)
                    new_company_code = st.selectbox("Company Code", ["1000", "2000", "3000"])
                
                with col2:
                    new_min_amount = st.number_input("Minimum Amount", min_value=0.0, value=0.0, format="%.2f")
                    new_max_amount = st.number_input("Maximum Amount (0 = Unlimited)", min_value=0.0, value=0.0, format="%.2f")
                    new_department = st.text_input("Department (Optional)", placeholder="e.g., FINANCE")
                
                if st.form_submit_button("➕ Add Approval Level", type="primary"):
                    try:
                        with engine.begin() as conn:
                            max_amt = None if new_max_amount == 0 else new_max_amount
                            dept = None if not new_department.strip() else new_department.strip()
                            
                            conn.execute(text("""
                                INSERT INTO approval_levels 
                                (level_name, level_order, min_amount, max_amount, company_code, department, is_active)
                                VALUES (:name, :order, :min_amt, :max_amt, :company, :dept, TRUE)
                            """), {
                                'name': new_level_name,
                                'order': new_level_order,
                                'min_amt': new_min_amount,
                                'max_amt': max_amt,
                                'company': new_company_code,
                                'dept': dept
                            })
                            
                            st.success(f"✅ Added approval level: {new_level_name}")
                            refresh_approval_data()
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"❌ Error adding approval level: {e}")
        
        st.divider()
        
        # Existing approval levels
        st.subheader("📊 Existing Approval Levels")
        
        try:
            levels_df = get_approval_levels()
            
            if not levels_df.empty:
                # Create editable dataframe
                edited_levels = st.data_editor(
                    levels_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "id": st.column_config.NumberColumn("ID", disabled=True),
                        "level_name": st.column_config.TextColumn("Level Name", required=True),
                        "level_order": st.column_config.NumberColumn("Order", min_value=1, max_value=10),
                        "min_amount": st.column_config.NumberColumn("Min Amount", format="$%.2f"),
                        "max_amount": st.column_config.NumberColumn("Max Amount", format="$%.2f"),
                        "company_code": st.column_config.SelectboxColumn("Company", options=["1000", "2000", "3000"]),
                        "department": st.column_config.TextColumn("Department"),
                        "is_active": st.column_config.CheckboxColumn("Active")
                    },
                    key="levels_editor"
                )
                
                # Update button
                if st.button("💾 Save Changes", key="save_levels"):
                    try:
                        with engine.begin() as conn:
                            for idx, row in edited_levels.iterrows():
                                max_amt = None if pd.isna(row['max_amount']) or row['max_amount'] == 0 else row['max_amount']
                                dept = None if pd.isna(row['department']) or not row['department'].strip() else row['department'].strip()
                                
                                conn.execute(text("""
                                    UPDATE approval_levels 
                                    SET level_name = :name, level_order = :order, 
                                        min_amount = :min_amt, max_amount = :max_amt,
                                        company_code = :company, department = :dept, is_active = :active
                                    WHERE id = :id
                                """), {
                                    'id': row['id'],
                                    'name': row['level_name'],
                                    'order': row['level_order'],
                                    'min_amt': row['min_amount'],
                                    'max_amt': max_amt,
                                    'company': row['company_code'],
                                    'dept': dept,
                                    'active': row['is_active']
                                })
                        
                        st.success("✅ Approval levels updated successfully!")
                        refresh_approval_data()
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error updating approval levels: {e}")
            else:
                st.info("No approval levels configured yet.")
        except Exception as e:
            st.error(f"Error loading approval levels: {e}")


# TAB 3: APPROVERS MANAGEMENT  
with tab3:
    if not authenticator.has_permission("workflow.manage"):
        st.error("🚫 You don't have permission to manage approval workflows")
    else:
        st.header("👥 Approvers Management")
        
        # Add new approver section
        with st.expander("➕ Add New Approver", expanded=False):
            with st.form("add_approver_form"):
                col1, col2 = st.columns(2)
                
                # Get available users and levels
                try:
                    users_df = load_users()
                    available_users = [(row['username'], f"{row['first_name']} {row['last_name']} ({row['username']})") for _, row in users_df.iterrows() if row['is_active']]
                    levels_df = get_approval_levels()
                    
                    with col1:
                        if available_users:
                            selected_user = st.selectbox(
                                "Select User", 
                                options=[user[0] for user in available_users],
                                format_func=lambda x: next(user[1] for user in available_users if user[0] == x)
                            )
                        else:
                            st.error("No active users found")
                            selected_user = None
                        
                        approver_company = st.selectbox("Company Code", ["1000", "2000", "3000"])
                    
                    with col2:
                        # Filter levels by selected company
                        company_levels = levels_df[
                            (levels_df['company_code'] == approver_company) & 
                            (levels_df['is_active'] == True)
                        ].sort_values('level_order')
                        
                        if not company_levels.empty:
                            selected_level = st.selectbox(
                                "Approval Level",
                                options=company_levels['id'].tolist(),
                                format_func=lambda x: f"{company_levels[company_levels['id']==x]['level_name'].iloc[0]} (Level {company_levels[company_levels['id']==x]['level_order'].iloc[0]})"
                            )
                        else:
                            st.error(f"No active approval levels for company {approver_company}")
                            selected_level = None
                        
                        approver_department = st.text_input("Department (Optional)", placeholder="e.g., FINANCE")
                    
                    if st.form_submit_button("➕ Add Approver", type="primary") and selected_user and selected_level:
                        try:
                            with engine.begin() as conn:
                                dept = None if not approver_department.strip() else approver_department.strip()
                                
                                conn.execute(text("""
                                    INSERT INTO approvers 
                                    (user_id, approval_level_id, company_code, department, is_active)
                                    VALUES (:user_id, :level_id, :company, :dept, TRUE)
                                """), {
                                    'user_id': selected_user,
                                    'level_id': selected_level,
                                    'company': approver_company,
                                    'dept': dept
                                })
                                
                                level_name = company_levels[company_levels['id']==selected_level]['level_name'].iloc[0]
                                st.success(f"✅ Added {selected_user} as {level_name} approver for company {approver_company}")
                                refresh_approval_data()
                                st.rerun()
                                
                        except Exception as e:
                            if "duplicate key" in str(e).lower():
                                st.error("❌ This user is already assigned to this approval level for this company")
                            else:
                                st.error(f"❌ Error adding approver: {e}")
                                
                except Exception as e:
                    st.error(f"Error loading data: {e}")
        
        st.divider()
        
        # Existing approvers
        st.subheader("👥 Existing Approvers")
        
        try:
            approvers_df = get_approvers()
            
            if not approvers_df.empty:
                # Create editable dataframe  
                edited_approvers = st.data_editor(
                    approvers_df[[
                        'id', 'user_id', 'level_name', 'company_code', 'department', 
                        'is_active', 'delegated_to', 'delegation_start_date', 'delegation_end_date'
                    ]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "id": st.column_config.NumberColumn("ID", disabled=True),
                        "user_id": st.column_config.TextColumn("User ID", disabled=True),
                        "level_name": st.column_config.TextColumn("Level", disabled=True),
                        "company_code": st.column_config.TextColumn("Company", disabled=True),
                        "department": st.column_config.TextColumn("Department"),
                        "is_active": st.column_config.CheckboxColumn("Active"),
                        "delegated_to": st.column_config.TextColumn("Delegated To"),
                        "delegation_start_date": st.column_config.DateColumn("Delegation Start"),
                        "delegation_end_date": st.column_config.DateColumn("Delegation End")
                    },
                    key="approvers_editor"
                )
                
                if st.button("💾 Save Changes", key="save_approvers"):
                    try:
                        with engine.begin() as conn:
                            for idx, row in edited_approvers.iterrows():
                                dept = None if pd.isna(row['department']) or not str(row['department']).strip() else str(row['department']).strip()
                                delegated = None if pd.isna(row['delegated_to']) or not str(row['delegated_to']).strip() else str(row['delegated_to']).strip()
                                start_date = None if pd.isna(row['delegation_start_date']) else row['delegation_start_date']
                                end_date = None if pd.isna(row['delegation_end_date']) else row['delegation_end_date']
                                
                                conn.execute(text("""
                                    UPDATE approvers 
                                    SET department = :dept, is_active = :active,
                                        delegated_to = :delegated, 
                                        delegation_start_date = :start_date,
                                        delegation_end_date = :end_date
                                    WHERE id = :id
                                """), {
                                    'id': row['id'],
                                    'dept': dept,
                                    'active': row['is_active'],
                                    'delegated': delegated,
                                    'start_date': start_date,
                                    'end_date': end_date
                                })
                        
                        st.success("✅ Approver assignments updated successfully!")
                        refresh_approval_data()
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error updating approvers: {e}")
            else:
                st.info("No approvers configured yet.")
        except Exception as e:
            st.error(f"Error loading approvers: {e}")


# TAB 4: DELEGATIONS MANAGEMENT
with tab4:
    if not authenticator.has_permission("workflow.manage"):
        st.error("🚫 You don't have permission to manage approval workflows")
    else:
        st.header("🔄 Delegation Management")
        
        try:
            approvers_df = get_approvers()
            active_approvers = approvers_df[approvers_df['is_active'] == True]
            
            # Quick delegation setup
            with st.expander("⚡ Quick Delegation Setup", expanded=True):
                with st.form("delegation_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**From (Original Approver):**")
                        if not active_approvers.empty:
                            from_approver = st.selectbox(
                                "Select Approver to Delegate",
                                options=active_approvers['id'].tolist(),
                                format_func=lambda x: f"{active_approvers[active_approvers['id']==x]['user_id'].iloc[0]} ({active_approvers[active_approvers['id']==x]['level_name'].iloc[0]} - {active_approvers[active_approvers['id']==x]['company_code'].iloc[0]})"
                            )
                        else:
                            st.error("No active approvers found")
                            from_approver = None
                        
                        delegation_start = st.date_input("Delegation Start Date", value=date.today())
                    
                    with col2:
                        st.write("**To (Delegate):**")
                        users_df = load_users()
                        available_users = [(row['username'], f"{row['first_name']} {row['last_name']} ({row['username']})") for _, row in users_df.iterrows() if row['is_active']]
                        
                        if available_users:
                            to_user = st.selectbox(
                                "Delegate To",
                                options=[user[0] for user in available_users],
                                format_func=lambda x: next(user[1] for user in available_users if user[0] == x)
                            )
                        else:
                            st.error("No users available")
                            to_user = None
                        
                        delegation_end = st.date_input("Delegation End Date", value=date.today())
                    
                    if st.form_submit_button("🔄 Set Delegation", type="primary") and from_approver and to_user:
                        try:
                            with engine.begin() as conn:
                                conn.execute(text("""
                                    UPDATE approvers 
                                    SET delegated_to = :to_user,
                                        delegation_start_date = :start_date,
                                        delegation_end_date = :end_date
                                    WHERE id = :approver_id
                                """), {
                                    'approver_id': from_approver,
                                    'to_user': to_user,
                                    'start_date': delegation_start,
                                    'end_date': delegation_end
                                })
                                
                                approver_info = active_approvers[active_approvers['id']==from_approver].iloc[0]
                                st.success(f"✅ Delegation set: {approver_info['user_id']} → {to_user} ({delegation_start} to {delegation_end})")
                                refresh_approval_data()
                                st.rerun()
                                
                        except Exception as e:
                            st.error(f"❌ Error setting delegation: {e}")
            
            st.divider()
            
            # Current delegations
            st.subheader("📋 Current Delegations")
            
            delegated_approvers = approvers_df[approvers_df['delegated_to'].notna()]
            
            if not delegated_approvers.empty:
                for _, delegation in delegated_approvers.iterrows():
                    with st.container():
                        col1, col2, col3 = st.columns([3, 2, 1])
                        
                        with col1:
                            status = "🟢 Active" if delegation['is_active'] else "🔴 Inactive"
                            st.write(f"**{delegation['user_id']}** → **{delegation['delegated_to']}**")
                            st.caption(f"{delegation['level_name']} Level, Company {delegation['company_code']} | {status}")
                        
                        with col2:
                            if pd.notna(delegation['delegation_start_date']) and pd.notna(delegation['delegation_end_date']):
                                st.write(f"📅 {delegation['delegation_start_date']} to {delegation['delegation_end_date']}")
                                
                                # Check if delegation is expired
                                if delegation['delegation_end_date'] < date.today():
                                    st.error("⚠️ Delegation expired")
                                elif delegation['delegation_start_date'] > date.today():
                                    st.info("⏳ Delegation not yet active")
                                else:
                                    st.success("✅ Currently active")
                            else:
                                st.write("📅 No date range set")
                        
                        with col3:
                            if st.button("❌ Remove", key=f"remove_delegation_{delegation['id']}"):
                                try:
                                    with engine.begin() as conn:
                                        conn.execute(text("""
                                            UPDATE approvers 
                                            SET delegated_to = NULL,
                                                delegation_start_date = NULL,
                                                delegation_end_date = NULL
                                            WHERE id = :id
                                        """), {'id': delegation['id']})
                                        
                                        st.success(f"✅ Removed delegation for {delegation['user_id']}")
                                        refresh_approval_data()
                                        st.rerun()
                                        
                                except Exception as e:
                                    st.error(f"❌ Error removing delegation: {e}")
                        
                        st.divider()
            else:
                st.info("No active delegations found.")
        except Exception as e:
            st.error(f"Error loading delegation data: {e}")

# Footer
st.divider()
col1, col2, col3 = st.columns([1, 1, 3])

with col1:
    if st.button("🔄 Refresh Data"):
        refresh_approval_data()
        st.rerun()

with col2:
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Navigation is now handled by the SAP-style sidebar