"""Authentication service layer"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from db_config import engine
from auth.models import (
    User, UserCreate, UserUpdate, Role, Permission, UserSession, 
    LoginRequest, LoginResponse, TokenPayload, AuditLog, AccessType
)
from auth.security import security_manager, rate_limiter, password_checker
from utils.logger import get_logger, log_user_action, log_database_operation
from config import settings

logger = get_logger("auth.service")


class AuthenticationError(Exception):
    """Authentication related errors"""
    pass


class AuthorizationError(Exception):
    """Authorization related errors"""
    pass


class UserService:
    """User management service"""
    
    def create_user(self, user_data: UserCreate, created_by: Optional[int] = None) -> User:
        """Create a new user"""
        try:
            # Hash password
            password_hash = security_manager.hash_password(user_data.password)
            
            with engine.begin() as conn:
                # Insert user
                result = conn.execute(text("""
                    INSERT INTO users (username, email, password_hash, first_name, last_name, 
                                     must_change_password, created_by)
                    VALUES (:username, :email, :password_hash, :first_name, :last_name, 
                            :must_change_password, :created_by)
                    RETURNING id, created_at
                """), {
                    'username': user_data.username,
                    'email': user_data.email,
                    'password_hash': password_hash,
                    'first_name': user_data.first_name,
                    'last_name': user_data.last_name,
                    'must_change_password': user_data.must_change_password,
                    'created_by': created_by
                })
                
                user_row = result.first()
                user_id = user_row[0]
                
                # Assign roles if provided
                if user_data.role_ids:
                    for role_id in user_data.role_ids:
                        conn.execute(text("""
                            INSERT INTO user_roles (user_id, role_id, granted_by)
                            VALUES (:user_id, :role_id, :granted_by)
                        """), {
                            'user_id': user_id,
                            'role_id': role_id,
                            'granted_by': created_by
                        })
                
                log_database_operation("INSERT", "users", str(user_id))
                log_user_action(created_by or "system", "create_user", f"Created user {user_data.username}")
                
                return self.get_user_by_id(user_id)
                
        except IntegrityError as e:
            if "username" in str(e):
                raise AuthenticationError("Username already exists")
            elif "email" in str(e):
                raise AuthenticationError("Email already exists")
            else:
                raise AuthenticationError("User creation failed")
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            raise AuthenticationError("User creation failed")
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, username, email, first_name, last_name, is_active, is_verified,
                           must_change_password, password_changed_at, last_login_at,
                           failed_login_attempts, locked_until, created_at, updated_at,
                           created_by, updated_by
                    FROM users 
                    WHERE id = :user_id
                """), {'user_id': user_id})
                
                row = result.first()
                if row:
                    return User(**row._asdict())
                return None
                
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, username, email, first_name, last_name, is_active, is_verified,
                           must_change_password, password_changed_at, last_login_at,
                           failed_login_attempts, locked_until, created_at, updated_at,
                           created_by, updated_by
                    FROM users 
                    WHERE username = :username
                """), {'username': username})
                
                row = result.first()
                if row:
                    return User(**row._asdict())
                return None
                
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            return None
    
    def update_user(self, user_id: int, user_data: UserUpdate, updated_by: Optional[int] = None) -> Optional[User]:
        """Update user information"""
        try:
            update_fields = []
            params = {'user_id': user_id, 'updated_by': updated_by}
            
            if user_data.email is not None:
                update_fields.append("email = :email")
                params['email'] = user_data.email
            
            if user_data.first_name is not None:
                update_fields.append("first_name = :first_name")
                params['first_name'] = user_data.first_name
            
            if user_data.last_name is not None:
                update_fields.append("last_name = :last_name")
                params['last_name'] = user_data.last_name
            
            if user_data.is_active is not None:
                update_fields.append("is_active = :is_active")
                params['is_active'] = user_data.is_active
            
            if not update_fields:
                return self.get_user_by_id(user_id)
            
            with engine.begin() as conn:
                # Update user
                conn.execute(text(f"""
                    UPDATE users 
                    SET {', '.join(update_fields)}, updated_by = :updated_by, updated_at = CURRENT_TIMESTAMP
                    WHERE id = :user_id
                """), params)
                
                # Update roles if provided
                if user_data.role_ids is not None:
                    # Remove existing roles
                    conn.execute(text("DELETE FROM user_roles WHERE user_id = :user_id"), 
                               {'user_id': user_id})
                    
                    # Add new roles
                    for role_id in user_data.role_ids:
                        conn.execute(text("""
                            INSERT INTO user_roles (user_id, role_id, granted_by)
                            VALUES (:user_id, :role_id, :granted_by)
                        """), {
                            'user_id': user_id,
                            'role_id': role_id,
                            'granted_by': updated_by
                        })
                
                log_database_operation("UPDATE", "users", str(user_id))
                log_user_action(updated_by or "system", "update_user", f"Updated user {user_id}")
                
                return self.get_user_by_id(user_id)
                
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {e}")
            raise AuthenticationError("User update failed")
    
    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        """Change user password"""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            
            # Get current password hash
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT password_hash FROM users WHERE id = :user_id
                """), {'user_id': user_id})
                
                row = result.first()
                if not row:
                    return False
                
                # Verify current password
                if not security_manager.verify_password(current_password, row[0]):
                    return False
                
                # Hash new password
                new_password_hash = security_manager.hash_password(new_password)
                
                # Update password
                conn.execute(text("""
                    UPDATE users 
                    SET password_hash = :password_hash, 
                        password_changed_at = CURRENT_TIMESTAMP,
                        must_change_password = FALSE,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :user_id
                """), {
                    'password_hash': new_password_hash,
                    'user_id': user_id
                })
                
                log_user_action(user_id, "change_password", "Password changed successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error changing password for user {user_id}: {e}")
            return False
    
    def get_user_permissions(self, user_id: int, conn=None) -> List[str]:
        """Get all permissions for a user"""
        try:
            if conn is not None:
                # Use existing connection
                result = conn.execute(text("""
                    SELECT DISTINCT p.name
                    FROM permissions p
                    JOIN role_permissions rp ON p.id = rp.permission_id
                    JOIN user_roles ur ON rp.role_id = ur.role_id
                    WHERE ur.user_id = :user_id
                """), {'user_id': user_id})
                return [row[0] for row in result]
            else:
                # Create new connection
                with engine.connect() as new_conn:
                    result = new_conn.execute(text("""
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
    
    def get_user_companies(self, user_id: int, conn=None) -> List[str]:
        """Get companies user has access to"""
        try:
            if conn is not None:
                # Use existing connection
                result = conn.execute(text("""
                    SELECT company_code FROM user_company_access 
                    WHERE user_id = :user_id
                """), {'user_id': user_id})
                return [row[0] for row in result]
            else:
                # Create new connection
                with engine.connect() as new_conn:
                    result = new_conn.execute(text("""
                        SELECT company_code FROM user_company_access 
                        WHERE user_id = :user_id
                    """), {'user_id': user_id})
                    return [row[0] for row in result]
                
        except Exception as e:
            logger.error(f"Error getting companies for user {user_id}: {e}")
            return []


class AuthenticationService:
    """Authentication service"""
    
    def __init__(self):
        self.user_service = UserService()
    
    def authenticate(self, login_request: LoginRequest, ip_address: str = None, user_agent: str = None) -> LoginResponse:
        """Authenticate user and return login response"""
        username = login_request.username.lower().strip()
        
        # Check rate limiting
        if rate_limiter.is_rate_limited(username):
            log_user_action(username, "login_failed", "Rate limited")
            raise AuthenticationError("Too many failed login attempts. Please try again later.")
        
        try:
            # Get user
            user = self.user_service.get_user_by_username(username)
            if not user:
                rate_limiter.record_attempt(username)
                log_user_action(username, "login_failed", "User not found")
                raise AuthenticationError("Invalid username or password")
            
            # Check if user is locked
            if user.is_locked:
                log_user_action(user.id, "login_failed", "Account locked")
                raise AuthenticationError("Account is locked. Please contact administrator.")
            
            # Check if user is active
            if not user.is_active:
                log_user_action(user.id, "login_failed", "Account inactive")
                raise AuthenticationError("Account is inactive. Please contact administrator.")
            
            # Verify password
            try:
                with engine.connect() as conn:
                    result = conn.execute(text("""
                        SELECT password_hash FROM users WHERE id = :user_id
                    """), {'user_id': user.id})
                    
                    row = result.first()
                    if not row:
                        rate_limiter.record_attempt(username)
                        log_user_action(user.id, "login_failed", "No password hash found")
                        raise AuthenticationError("Invalid username or password")
                    
                    password_valid = security_manager.verify_password(login_request.password, row[0])
                    
                if not password_valid:
                    # Handle failed login in separate transaction
                    try:
                        self._handle_failed_login(user.id, ip_address, user_agent)
                    except Exception as e:
                        logger.error(f"Error handling failed login: {e}")
                    
                    rate_limiter.record_attempt(username)
                    log_user_action(user.id, "login_failed", "Invalid password")
                    raise AuthenticationError("Invalid username or password")
                    
            except AuthenticationError:
                raise
            except Exception as e:
                logger.error(f"Error during password verification: {e}")
                raise AuthenticationError("Authentication failed")
            
            # Successful login
            rate_limiter.clear_attempts(username)
            return self._handle_successful_login(user, login_request.remember_me, ip_address, user_agent)
            
        except AuthenticationError:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise AuthenticationError("Authentication failed")
    
    def _handle_successful_login(self, user: User, remember_me: bool, ip_address: str, user_agent: str) -> LoginResponse:
        """Handle successful login"""
        try:
            with engine.begin() as conn:
                # Reset failed login attempts
                conn.execute(text("""
                    UPDATE users 
                    SET failed_login_attempts = 0, last_login_at = CURRENT_TIMESTAMP
                    WHERE id = :user_id
                """), {'user_id': user.id})
                
                # Create session
                expires_at = datetime.utcnow() + timedelta(
                    hours=24 if remember_me else settings.session_timeout_minutes / 60
                )
                
                result = conn.execute(text("""
                    INSERT INTO user_sessions (user_id, session_token, ip_address, user_agent, expires_at)
                    VALUES (:user_id, :session_token, :ip_address, :user_agent, :expires_at)
                    RETURNING id
                """), {
                    'user_id': user.id,
                    'session_token': f"session_{datetime.utcnow().timestamp()}_{user.id}",
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'expires_at': expires_at
                })
                
                session_id = result.first()[0]
                
                # Create tokens
                access_token = security_manager.create_access_token(
                    user.id, user.username, session_id
                )
                refresh_token = security_manager.create_refresh_token(
                    user.id, user.username, session_id
                ) if remember_me else None
                
                # Update session with tokens
                conn.execute(text("""
                    UPDATE user_sessions 
                    SET refresh_token = :refresh_token
                    WHERE id = :session_id
                """), {
                    'refresh_token': refresh_token,
                    'session_id': session_id
                })
                
                # Get user permissions and companies
                permissions = self.user_service.get_user_permissions(user.id, conn)
                companies = self.user_service.get_user_companies(user.id, conn)
                
                log_user_action(user.id, "login_success", f"Successful login from {ip_address}")
                
                return LoginResponse(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_in=settings.jwt_expiration_hours * 3600,
                    user=user,
                    permissions=permissions,
                    companies=companies
                )
                
        except Exception as e:
            logger.error(f"Error handling successful login: {e}")
            raise AuthenticationError("Login processing failed")
    
    def _handle_failed_login(self, user_id: int, ip_address: str, user_agent: str):
        """Handle failed login attempt"""
        try:
            with engine.begin() as conn:
                # Increment failed attempts
                conn.execute(text("""
                    UPDATE users 
                    SET failed_login_attempts = failed_login_attempts + 1
                    WHERE id = :user_id
                """), {'user_id': user_id})
                
                # Check if user should be locked
                result = conn.execute(text("""
                    SELECT failed_login_attempts FROM users WHERE id = :user_id
                """), {'user_id': user_id})
                
                failed_attempts = result.first()[0]
                
                if failed_attempts >= settings.max_login_attempts:
                    locked_until = datetime.utcnow() + timedelta(minutes=settings.lockout_duration_minutes)
                    conn.execute(text("""
                        UPDATE users 
                        SET locked_until = :locked_until
                        WHERE id = :user_id
                    """), {
                        'locked_until': locked_until,
                        'user_id': user_id
                    })
                    
                    log_user_action(user_id, "account_locked", "Account locked due to failed login attempts")
                
        except Exception as e:
            logger.error(f"Error handling failed login: {e}")
    
    def refresh_token(self, refresh_token: str) -> Optional[LoginResponse]:
        """Refresh access token using refresh token"""
        try:
            # Verify refresh token
            payload = security_manager.verify_token(refresh_token)
            if not payload or payload.get('type') != 'refresh':
                return None
            
            user_id = payload.get('sub')
            session_id = payload.get('session_id')
            
            # Verify session is still active
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT us.id, us.expires_at, u.username
                    FROM user_sessions us
                    JOIN users u ON us.user_id = u.id
                    WHERE us.id = :session_id AND us.refresh_token = :refresh_token 
                    AND us.is_active = TRUE AND us.expires_at > CURRENT_TIMESTAMP
                """), {
                    'session_id': session_id,
                    'refresh_token': refresh_token
                })
                
                row = result.first()
                if not row:
                    return None
                
                username = row[2]
                
                # Create new access token
                access_token = security_manager.create_access_token(
                    user_id, username, session_id
                )
                
                # Update session last accessed
                conn.execute(text("""
                    UPDATE user_sessions 
                    SET last_accessed_at = CURRENT_TIMESTAMP
                    WHERE id = :session_id
                """), {'session_id': session_id})
                
                # Get user and permissions
                user = self.user_service.get_user_by_id(user_id)
                permissions = self.user_service.get_user_permissions(user_id)
                companies = self.user_service.get_user_companies(user_id)
                
                return LoginResponse(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_in=settings.jwt_expiration_hours * 3600,
                    user=user,
                    permissions=permissions,
                    companies=companies
                )
                
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None
    
    def logout(self, session_token: str):
        """Logout user by invalidating session"""
        try:
            with engine.begin() as conn:
                conn.execute(text("""
                    UPDATE user_sessions 
                    SET is_active = FALSE
                    WHERE session_token = :session_token
                """), {'session_token': session_token})
                
                log_user_action(None, "logout", "User logged out")
                
        except Exception as e:
            logger.error(f"Error during logout: {e}")


class AuthorizationService:
    """Authorization service for role-based access control"""
    
    def check_permission(self, user_id: int, permission: str) -> bool:
        """Check if user has specific permission"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*)
                    FROM permissions p
                    JOIN role_permissions rp ON p.id = rp.permission_id
                    JOIN user_roles ur ON rp.role_id = ur.role_id
                    WHERE ur.user_id = :user_id AND p.name = :permission
                """), {
                    'user_id': user_id,
                    'permission': permission
                })
                
                return result.first()[0] > 0
                
        except Exception as e:
            logger.error(f"Error checking permission {permission} for user {user_id}: {e}")
            return False
    
    def check_company_access(self, user_id: int, company_code: str, access_type: AccessType = AccessType.READ_ONLY) -> bool:
        """Check if user has access to specific company"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT access_type
                    FROM user_company_access 
                    WHERE user_id = :user_id AND company_code = :company_code
                """), {
                    'user_id': user_id,
                    'company_code': company_code
                })
                
                row = result.first()
                if not row:
                    return False
                
                user_access = AccessType(row[0])
                
                # Check access level hierarchy
                if access_type == AccessType.READ_ONLY:
                    return True  # Any access level allows read
                elif access_type == AccessType.READ_WRITE:
                    return user_access in [AccessType.READ_WRITE, AccessType.ADMIN]
                elif access_type == AccessType.ADMIN:
                    return user_access == AccessType.ADMIN
                
                return False
                
        except Exception as e:
            logger.error(f"Error checking company access for user {user_id}: {e}")
            return False


# Global service instances
user_service = UserService()
auth_service = AuthenticationService()
authz_service = AuthorizationService()