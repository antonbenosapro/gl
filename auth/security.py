"""Security utilities for authentication"""

import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from config import settings
from utils.logger import get_logger

logger = get_logger("auth.security")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityManager:
    """Handles password hashing, JWT tokens, and security operations"""
    
    def __init__(self):
        self.jwt_algorithm = settings.jwt_algorithm
        self.jwt_secret = settings.jwt_secret_key
        self.jwt_expiration_hours = settings.jwt_expiration_hours
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        try:
            return pwd_context.hash(password)
        except Exception as e:
            logger.error(f"Error hashing password: {e}")
            raise
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    def create_access_token(
        self, 
        user_id: int, 
        username: str, 
        session_id: Optional[int] = None,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a JWT access token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=self.jwt_expiration_hours)
        
        payload = {
            "sub": str(user_id),  # JWT standard requires string subject
            "username": username,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access",
            "session_id": session_id
        }
        
        try:
            token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
            logger.info(f"Created access token for user {username}")
            return token
        except Exception as e:
            logger.error(f"Error creating access token: {e}")
            raise
    
    def create_refresh_token(
        self, 
        user_id: int, 
        username: str, 
        session_id: Optional[int] = None
    ) -> str:
        """Create a JWT refresh token"""
        expire = datetime.utcnow() + timedelta(days=30)  # Refresh tokens last longer
        
        payload = {
            "sub": str(user_id),  # JWT standard requires string subject
            "username": username,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "session_id": session_id
        }
        
        try:
            token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
            logger.info(f"Created refresh token for user {username}")
            return token
        except Exception as e:
            logger.error(f"Error creating refresh token: {e}")
            raise
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return None
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode token without verification (for debugging)"""
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception as e:
            logger.error(f"Error decoding token: {e}")
            return None
    
    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired"""
        payload = self.decode_token(token)
        if not payload:
            return True
        
        exp = payload.get('exp')
        if not exp:
            return True
        
        return datetime.fromtimestamp(exp) < datetime.utcnow()
    
    def get_token_remaining_time(self, token: str) -> Optional[timedelta]:
        """Get remaining time for token"""
        payload = self.decode_token(token)
        if not payload:
            return None
        
        exp = payload.get('exp')
        if not exp:
            return None
        
        expire_time = datetime.fromtimestamp(exp)
        remaining = expire_time - datetime.utcnow()
        
        return remaining if remaining.total_seconds() > 0 else None


class PasswordStrengthChecker:
    """Check password strength and provide feedback"""
    
    @staticmethod
    def check_strength(password: str) -> Dict[str, Any]:
        """Check password strength and return detailed feedback"""
        feedback = {
            "score": 0,
            "is_valid": False,
            "messages": [],
            "requirements": {
                "length": False,
                "uppercase": False,
                "lowercase": False,
                "numbers": False,
                "special_chars": False,
                "no_common_patterns": False
            }
        }
        
        # Length check
        if len(password) >= settings.password_min_length:
            feedback["requirements"]["length"] = True
            feedback["score"] += 1
        else:
            feedback["messages"].append(f"Password must be at least {settings.password_min_length} characters long")
        
        # Uppercase check
        if any(c.isupper() for c in password):
            feedback["requirements"]["uppercase"] = True
            feedback["score"] += 1
        else:
            feedback["messages"].append("Password must contain at least one uppercase letter")
        
        # Lowercase check
        if any(c.islower() for c in password):
            feedback["requirements"]["lowercase"] = True
            feedback["score"] += 1
        else:
            feedback["messages"].append("Password must contain at least one lowercase letter")
        
        # Numbers check
        if any(c.isdigit() for c in password):
            feedback["requirements"]["numbers"] = True
            feedback["score"] += 1
        else:
            feedback["messages"].append("Password must contain at least one number")
        
        # Special characters check
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if any(c in special_chars for c in password):
            feedback["requirements"]["special_chars"] = True
            feedback["score"] += 1
        else:
            feedback["messages"].append("Password must contain at least one special character")
        
        # Common patterns check
        common_patterns = ["123", "abc", "password", "admin", "user", "qwerty"]
        if not any(pattern in password.lower() for pattern in common_patterns):
            feedback["requirements"]["no_common_patterns"] = True
            feedback["score"] += 1
        else:
            feedback["messages"].append("Password contains common patterns")
        
        # Calculate final score
        feedback["is_valid"] = feedback["score"] >= 5
        
        return feedback


class RateLimiter:
    """Rate limiting for login attempts"""
    
    def __init__(self):
        self.attempts = {}  # In production, use Redis or database
    
    def is_rate_limited(self, identifier: str) -> bool:
        """Check if identifier is rate limited"""
        now = datetime.utcnow()
        
        if identifier not in self.attempts:
            return False
        
        attempts = self.attempts[identifier]
        
        # Clean old attempts (older than lockout duration)
        cutoff = now - timedelta(minutes=settings.lockout_duration_minutes)
        self.attempts[identifier] = [attempt for attempt in attempts if attempt > cutoff]
        
        # Check if rate limited
        return len(self.attempts[identifier]) >= settings.max_login_attempts
    
    def record_attempt(self, identifier: str):
        """Record a failed login attempt"""
        now = datetime.utcnow()
        
        if identifier not in self.attempts:
            self.attempts[identifier] = []
        
        self.attempts[identifier].append(now)
        
        # Keep only recent attempts
        cutoff = now - timedelta(minutes=settings.lockout_duration_minutes)
        self.attempts[identifier] = [attempt for attempt in self.attempts[identifier] if attempt > cutoff]
    
    def clear_attempts(self, identifier: str):
        """Clear attempts for identifier (after successful login)"""
        if identifier in self.attempts:
            del self.attempts[identifier]


# Global instances
security_manager = SecurityManager()
password_checker = PasswordStrengthChecker()
rate_limiter = RateLimiter()