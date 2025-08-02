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
        companies = ['C001', 'C002', 'C003']  # This would come from a companies table
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
        
        col_update, col_delete = st.columns(2)
        
        with col_update:
            update_submitted = st.form_submit_button("Update User", type="primary")
        
        with col_delete:
            if authenticator.has_permission("users.delete"):
                delete_submitted = st.form_submit_button("Delete User", type="secondary")
            else:
                delete_submitted = False
        
        if update_submitted:
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
                
                if reset_password:
                    with engine.begin() as conn:
                        conn.execute(text("""
                            UPDATE users 
                            SET must_change_password = TRUE
                            WHERE id = :user_id
                        """), {'user_id': user_data['id']})
                
                st.success("User updated successfully!")
                StreamlitLogHandler.log_form_submission("update_user", True, current_user.username)
                
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                logger.error(f"Error updating user: {e}")
                st.error("Failed to update user")
        
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
                
                if st.button(f"✏️ Edit User: {selected_user_option.split(' (')[0]}"):
                    st.session_state.selected_user_id = selected_user_id
                    st.rerun()
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

# Navigation is now handled by the SAP-style sidebar