"""Streamlit authentication middleware"""

import streamlit as st
from typing import Optional, List, Callable, Any
from functools import wraps
import time

from auth.models import User, LoginRequest
from auth.simple_auth import simple_auth_service, AuthenticationError
from auth.security import security_manager
from utils.logger import get_logger, StreamlitLogHandler

logger = get_logger("auth.middleware")


class StreamlitAuthenticator:
    """Streamlit authentication manager"""
    
    def __init__(self):
        self.session_key_user = "authenticated_user"
        self.session_key_token = "access_token"
        self.session_key_permissions = "user_permissions"
        self.session_key_companies = "user_companies"
        self.session_key_login_time = "login_time"
    
    def initialize_session(self):
        """Initialize session state for authentication"""
        if self.session_key_user not in st.session_state:
            st.session_state[self.session_key_user] = None
        if self.session_key_token not in st.session_state:
            st.session_state[self.session_key_token] = None
        if self.session_key_permissions not in st.session_state:
            st.session_state[self.session_key_permissions] = []
        if self.session_key_companies not in st.session_state:
            st.session_state[self.session_key_companies] = []
        if self.session_key_login_time not in st.session_state:
            st.session_state[self.session_key_login_time] = None
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        self.initialize_session()
        
        user = st.session_state.get(self.session_key_user)
        token = st.session_state.get(self.session_key_token)
        
        if not user or not token:
            return False
        
        # Verify token is still valid
        payload = security_manager.verify_token(token)
        if not payload:
            self.logout()
            return False
        
        # Check session timeout
        login_time = st.session_state.get(self.session_key_login_time)
        if login_time:
            from config import settings
            session_timeout = settings.session_timeout_minutes * 60
            if time.time() - login_time > session_timeout:
                self.logout()
                st.warning("Session expired. Please log in again.")
                return False
        
        return True
    
    def get_current_user(self) -> Optional[User]:
        """Get current authenticated user"""
        if self.is_authenticated():
            return st.session_state.get(self.session_key_user)
        return None
    
    def get_user_permissions(self) -> List[str]:
        """Get current user's permissions"""
        if self.is_authenticated():
            return st.session_state.get(self.session_key_permissions, [])
        return []
    
    def get_user_companies(self) -> List[str]:
        """Get companies current user has access to"""
        if self.is_authenticated():
            return st.session_state.get(self.session_key_companies, [])
        return []
    
    def has_permission(self, permission: str) -> bool:
        """Check if current user has specific permission"""
        permissions = self.get_user_permissions()
        return permission in permissions
    
    def login(self, username: str, password: str, remember_me: bool = False) -> tuple[bool, str]:
        """Login user"""
        try:
            # Get client info
            ip_address = self._get_client_ip()
            user_agent = self._get_user_agent()
            
            # Authenticate
            login_request = LoginRequest(
                username=username,
                password=password,
                remember_me=remember_me
            )
            
            login_response = simple_auth_service.authenticate(
                login_request, ip_address, user_agent
            )
            
            # Store in session
            st.session_state[self.session_key_user] = login_response.user
            st.session_state[self.session_key_token] = login_response.access_token
            st.session_state[self.session_key_permissions] = login_response.permissions
            st.session_state[self.session_key_companies] = login_response.companies
            st.session_state[self.session_key_login_time] = time.time()
            
            StreamlitLogHandler.log_user_action("login_success", login_response.user.username)
            
            return True, "Login successful"
            
        except AuthenticationError as e:
            StreamlitLogHandler.log_user_action("login_failed", username)
            return False, str(e)
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False, "Login failed. Please try again."
    
    def logout(self):
        """Logout current user"""
        user = st.session_state.get(self.session_key_user)
        if user:
            StreamlitLogHandler.log_user_action("logout", user.username)
        
        # Clear session state
        st.session_state[self.session_key_user] = None
        st.session_state[self.session_key_token] = None
        st.session_state[self.session_key_permissions] = []
        st.session_state[self.session_key_companies] = []
        st.session_state[self.session_key_login_time] = None
        
        # Force rerun to redirect to login
        st.rerun()
    
    def require_auth(self):
        """Require authentication for current page"""
        if not self.is_authenticated():
            self.show_login_page()
            st.stop()
    
    def require_permission(self, permission: str):
        """Require specific permission for current page"""
        self.require_auth()
        
        if not self.has_permission(permission):
            st.error("❌ Access Denied: You don't have permission to access this page.")
            st.info(f"Required permission: {permission}")
            st.stop()
    
    def show_login_page(self):
        """Show login page"""
        st.set_page_config(page_title="GL ERP - Login", layout="centered")
        
        # Custom CSS for login page
        st.markdown("""
        <style>
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            background-color: white;
        }
        .login-header {
            text-align: center;
            margin-bottom: 2rem;
        }
        .login-title {
            color: #1f77b4;
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 0.5rem;
        }
        .login-subtitle {
            color: #666;
            font-size: 1rem;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Center the login form
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("""
            <div class="login-container">
                <div class="login-header">
                    <div class="login-title">🧾 GL ERP</div>
                    <div class="login-subtitle">General Ledger System</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("### 🔐 Sign In")
            
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                remember_me = st.checkbox("Remember me")
                
                col_login, col_forgot = st.columns(2)
                with col_login:
                    login_button = st.form_submit_button("🚀 Sign In", use_container_width=True)
                with col_forgot:
                    if st.form_submit_button("🔑 Forgot Password?", use_container_width=True):
                        st.info("Please contact your system administrator to reset your password.")
                
                if login_button:
                    if not username or not password:
                        st.error("Please enter both username and password.")
                    else:
                        with st.spinner("Signing in..."):
                            success, message = self.login(username, password, remember_me)
                            
                            if success:
                                st.success(message)
                                time.sleep(1)  # Brief pause to show success message
                                st.rerun()
                            else:
                                st.error(message)
            
            # System info
            st.markdown("---")
            st.markdown("""
            <div style="text-align: center; color: #666; font-size: 0.8rem;">
                <p>GL ERP System v2.0.0</p>
                <p>For support, contact your system administrator</p>
            </div>
            """, unsafe_allow_html=True)
    
    def show_user_menu(self):
        """Show user menu in sidebar"""
        if not self.is_authenticated():
            return
        
        user = self.get_current_user()
        
        with st.sidebar:
            st.markdown("---")
            st.markdown(f"👤 **{user.full_name}**")
            st.markdown(f"*{user.username}*")
            
            if user.must_change_password:
                st.warning("⚠️ You must change your password")
                if st.button("Change Password"):
                    self._show_change_password_dialog()
            
            # User menu
            with st.expander("⚙️ Account Settings"):
                if st.button("🔐 Change Password"):
                    self._show_change_password_dialog()
                
                if st.button("👥 My Profile"):
                    self._show_profile_dialog()
                
                st.markdown("---")
                if st.button("🚪 Sign Out"):
                    self.logout()
            
            # Show permissions if user is admin
            if self.has_permission("users.read"):
                with st.expander("🔍 My Permissions"):
                    permissions = self.get_user_permissions()
                    for perm in sorted(permissions):
                        st.text(f"✓ {perm}")
    
    def _show_change_password_dialog(self):
        """Show change password dialog"""
        st.markdown("### 🔐 Change Password")
        
        with st.form("change_password_form"):
            current_password = st.text_input("Current Password", type="password")
            new_password = st.text_input("New Password", type="password")
            confirm_password = st.text_input("Confirm New Password", type="password")
            
            if st.form_submit_button("Change Password"):
                if not all([current_password, new_password, confirm_password]):
                    st.error("Please fill in all fields")
                elif new_password != confirm_password:
                    st.error("New passwords do not match")
                else:
                    user = self.get_current_user()
                    from auth.service import user_service
                    
                    success = user_service.change_password(
                        user.id, current_password, new_password
                    )
                    
                    if success:
                        st.success("Password changed successfully!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Failed to change password. Please check your current password.")
    
    def _show_profile_dialog(self):
        """Show user profile dialog"""
        st.markdown("### 👤 My Profile")
        
        user = self.get_current_user()
        
        st.text_input("Username", value=user.username, disabled=True)
        st.text_input("Email", value=user.email, disabled=True)
        st.text_input("Full Name", value=user.full_name, disabled=True)
        
        if user.last_login_at:
            st.text_input("Last Login", value=user.last_login_at.strftime("%Y-%m-%d %H:%M:%S"), disabled=True)
        
        companies = self.get_user_companies()
        if companies:
            st.text_area("Company Access", value="\n".join(companies), disabled=True)
    
    def _get_client_ip(self) -> str:
        """Get client IP address"""
        # In production, you might get this from headers
        return "127.0.0.1"
    
    def _get_user_agent(self) -> str:
        """Get user agent string"""
        # In production, you might get this from headers
        return "Streamlit/1.47.1"


def require_auth(func: Callable) -> Callable:
    """Decorator to require authentication for a function"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        authenticator.require_auth()
        return func(*args, **kwargs)
    return wrapper


def require_permission(permission: str):
    """Decorator to require specific permission for a function"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            authenticator.require_permission(permission)
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_company_access(company_code: str, access_type: str = "read_only"):
    """Decorator to require company access for a function"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            authenticator.require_auth()
            user = authenticator.get_current_user()
            
            from auth.models import AccessType
            from auth.service import authz_service
            
            if not authz_service.check_company_access(user.id, company_code, AccessType(access_type)):
                st.error(f"❌ Access Denied: You don't have {access_type} access to company {company_code}")
                st.stop()
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Global authenticator instance
authenticator = StreamlitAuthenticator()