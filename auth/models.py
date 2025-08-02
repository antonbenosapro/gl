"""Authentication data models"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, field_validator
from enum import Enum


class AccessType(str, Enum):
    """User access types for companies"""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"


class UserStatus(str, Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    PENDING = "pending"


class User(BaseModel):
    """User model"""
    id: Optional[int] = None
    username: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    must_change_password: bool = False
    password_changed_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v.strip().lower()
    
    @property
    def full_name(self) -> str:
        """Get user's full name"""
        parts = [self.first_name, self.last_name]
        return ' '.join(filter(None, parts)) or self.username
    
    @property
    def is_locked(self) -> bool:
        """Check if user account is locked"""
        return self.locked_until and self.locked_until > datetime.utcnow()
    
    @property
    def status(self) -> UserStatus:
        """Get user account status"""
        if self.is_locked:
            return UserStatus.LOCKED
        elif not self.is_active:
            return UserStatus.INACTIVE
        elif not self.is_verified:
            return UserStatus.PENDING
        else:
            return UserStatus.ACTIVE


class UserCreate(BaseModel):
    """User creation model"""
    username: str
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role_ids: Optional[List[int]] = []
    must_change_password: bool = True
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        from config import settings
        if len(v) < settings.password_min_length:
            raise ValueError(f'Password must be at least {settings.password_min_length} characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v


class UserUpdate(BaseModel):
    """User update model"""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None
    role_ids: Optional[List[int]] = None


class PasswordChange(BaseModel):
    """Password change model"""
    current_password: str
    new_password: str
    confirm_password: str
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('Passwords do not match')
        return v


class Role(BaseModel):
    """Role model"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    permissions: Optional[List['Permission']] = []


class Permission(BaseModel):
    """Permission model"""
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    resource: str
    action: str
    created_at: Optional[datetime] = None


class UserSession(BaseModel):
    """User session model"""
    id: Optional[int] = None
    user_id: int
    session_token: str
    refresh_token: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool = True
    expires_at: datetime
    created_at: Optional[datetime] = None
    last_accessed_at: Optional[datetime] = None


class LoginRequest(BaseModel):
    """Login request model"""
    username: str
    password: str
    remember_me: bool = False


class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user: User
    permissions: List[str] = []
    companies: List[str] = []


class TokenPayload(BaseModel):
    """JWT token payload model"""
    sub: int  # user_id
    username: str
    exp: datetime
    iat: datetime
    type: str = "access"  # access or refresh
    session_id: Optional[int] = None


class AuditLog(BaseModel):
    """Audit log model"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    action: str
    resource: Optional[str] = None
    resource_id: Optional[str] = None
    old_values: Optional[Dict[str, Any]] = None
    new_values: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None


class UserCompanyAccess(BaseModel):
    """User company access model"""
    user_id: int
    company_code: str
    access_type: AccessType = AccessType.READ_WRITE
    granted_at: Optional[datetime] = None
    granted_by: Optional[int] = None