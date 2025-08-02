"""Simplified authentication service to fix transaction issues"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import text

from db_config import engine
from auth.models import LoginRequest, LoginResponse, User
from auth.security import security_manager, rate_limiter
from utils.logger import get_logger, log_user_action

logger = get_logger("simple_auth")


class AuthenticationError(Exception):
    """Authentication related errors"""
    pass


class SimpleAuthService:
    """Simplified authentication service without nested transactions"""
    
    def authenticate(self, login_request: LoginRequest, ip_address: str = None, user_agent: str = None) -> LoginResponse:
        """Authenticate user and return login response"""
        username = login_request.username.lower().strip()
        
        # Check rate limiting
        if rate_limiter.is_rate_limited(username):
            log_user_action(username, "login_failed", "Rate limited")
            raise AuthenticationError("Too many failed login attempts. Please try again later.")
        
        try:
            # Get user and verify password in one query
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, username, email, first_name, last_name, is_active, is_verified,
                           must_change_password, password_changed_at, last_login_at,
                           failed_login_attempts, locked_until, created_at, updated_at,
                           created_by, updated_by, password_hash
                    FROM users 
                    WHERE username = :username AND is_active = true
                """), {'username': username})
                
                row = result.first()
                if not row:
                    rate_limiter.record_attempt(username)
                    log_user_action(username, "login_failed", "User not found or inactive")
                    raise AuthenticationError("Invalid username or password")
                
                # Extract user data and password hash
                user_data = dict(row._mapping)
                password_hash = user_data.pop('password_hash')
                
                # Create user object
                user = User(**user_data)
                
                # Check if user is locked
                if user.locked_until and user.locked_until > datetime.utcnow():
                    log_user_action(user.id, "login_failed", "Account locked")
                    raise AuthenticationError("Account is locked. Please contact administrator.")
                
                # Verify password
                if not security_manager.verify_password(login_request.password, password_hash):
                    self._handle_failed_login(user.id)
                    rate_limiter.record_attempt(username)
                    log_user_action(user.id, "login_failed", "Invalid password")
                    raise AuthenticationError("Invalid username or password")
            
            # Password is valid - handle successful login
            rate_limiter.clear_attempts(username)
            return self._handle_successful_login(user, login_request.remember_me, ip_address, user_agent)
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise AuthenticationError("Authentication failed")
    
    def _handle_failed_login(self, user_id: int):
        """Handle failed login attempt"""
        try:
            with engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("""
                        UPDATE users 
                        SET failed_login_attempts = failed_login_attempts + 1
                        WHERE id = :user_id
                    """), {'user_id': user_id})
        except Exception as e:
            logger.error(f"Error handling failed login: {e}")
    
    def _handle_successful_login(self, user: User, remember_me: bool, ip_address: str, user_agent: str) -> LoginResponse:
        """Handle successful login"""
        try:
            # Get permissions and companies first
            permissions = self._get_user_permissions(user.id)
            companies = self._get_user_companies(user.id)
            
            # Create tokens
            access_token = security_manager.create_access_token(user.id, user.username)
            refresh_token = security_manager.create_refresh_token(user.id, user.username) if remember_me else None
            
            # Update database
            with engine.connect() as conn:
                with conn.begin():
                    # Reset failed login attempts and update last login
                    conn.execute(text("""
                        UPDATE users 
                        SET failed_login_attempts = 0, last_login_at = CURRENT_TIMESTAMP
                        WHERE id = :user_id
                    """), {'user_id': user.id})
                    
                    # Create session record
                    expires_at = datetime.utcnow() + timedelta(hours=24 if remember_me else 8)
                    conn.execute(text("""
                        INSERT INTO user_sessions (user_id, session_token, ip_address, user_agent, expires_at, refresh_token)
                        VALUES (:user_id, :session_token, :ip_address, :user_agent, :expires_at, :refresh_token)
                    """), {
                        'user_id': user.id,
                        'session_token': f"session_{datetime.utcnow().timestamp()}_{user.id}",
                        'ip_address': ip_address,
                        'user_agent': user_agent,
                        'expires_at': expires_at,
                        'refresh_token': refresh_token
                    })
            
            log_user_action(user.id, "login_success", f"Successful login from {ip_address}")
            
            return LoginResponse(
                user=user,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=8 * 3600,  # 8 hours in seconds
                permissions=permissions,
                companies=companies
            )
        except Exception as e:
            logger.error(f"Error handling successful login: {e}")
            raise AuthenticationError("Login processing failed")
    
    def _get_user_permissions(self, user_id: int) -> list[str]:
        """Get user permissions"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT DISTINCT p.name
                    FROM permissions p
                    JOIN role_permissions rp ON p.id = rp.permission_id
                    JOIN user_roles ur ON rp.role_id = ur.role_id
                    WHERE ur.user_id = :user_id
                """), {'user_id': user_id})
                return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Error getting permissions for user {user_id}: {e}")
            return []
    
    def _get_user_companies(self, user_id: int) -> list[str]:
        """Get user companies"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT company_code FROM user_company_access 
                    WHERE user_id = :user_id
                """), {'user_id': user_id})
                return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Error getting companies for user {user_id}: {e}")
            return []


# Create global instance
simple_auth_service = SimpleAuthService()