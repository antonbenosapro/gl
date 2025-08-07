import os
from typing import Optional
from pydantic import validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application configuration settings"""
    
    # Database settings
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "gl_erp"
    db_user: str = "postgres"
    db_password: str = "admin123"
    database_url: Optional[str] = None
    
    # Application settings
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    
    # Streamlit settings
    streamlit_server_port: int = 8501
    streamlit_server_address: str = "localhost"
    
    # Security settings
    secret_key: str = "default-secret-key"
    jwt_secret_key: str = "default-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    session_timeout_minutes: int = 480  # 8 hours (was 60)
    max_inactivity_minutes: int = 240   # 4 hours of inactivity allowed
    max_session_hours: int = 24         # 24 hours absolute maximum
    password_min_length: int = 8
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30
    
    # Feature flags
    enable_caching: bool = True
    cache_ttl: int = 300
    
    @validator('database_url', pre=True, always=True)
    def build_database_url(cls, v, values):
        """Build database URL from components if not provided"""
        if v:
            return v
        return (
            f"postgresql://{values.get('db_user')}:{values.get('db_password')}"
            f"@{values.get('db_host')}:{values.get('db_port')}/{values.get('db_name')}"
        )
    
    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()