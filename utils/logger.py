"""Centralized logging configuration for the GL ERP system"""

import sys
from pathlib import Path
from loguru import logger
from config import settings


def setup_logger():
    """Setup loguru logger with proper configuration"""
    
    # Remove default handler
    logger.remove()
    
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Console handler
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        colorize=True
    )
    
    # File handler for general logs
    logger.add(
        log_dir / "gl_erp.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="10 MB",
        retention="30 days",
        compression="zip"
    )
    
    # File handler for errors only
    logger.add(
        log_dir / "errors.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation="5 MB",
        retention="90 days",
        compression="zip"
    )
    
    # File handler for database operations
    logger.add(
        log_dir / "database.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        filter=lambda record: "database" in record["name"].lower() or "db" in record["extra"].get("context", ""),
        rotation="10 MB",
        retention="7 days",
        compression="zip"
    )
    
    return logger


# Initialize logger
app_logger = setup_logger()


def get_logger(name: str = None):
    """Get a logger instance with optional name"""
    if name:
        return logger.bind(name=name)
    return logger


def log_database_operation(operation: str, table: str, record_id: str = None):
    """Log database operations with consistent format"""
    extra_info = f"table={table}"
    if record_id:
        extra_info += f", record_id={record_id}"
    
    logger.bind(context="database").info(f"Database {operation}: {extra_info}")


def log_user_action(user: str, action: str, details: str = None):
    """Log user actions for audit trail"""
    message = f"User '{user}' performed action: {action}"
    if details:
        message += f" - {details}"
    
    logger.bind(context="user_action").info(message)


def log_validation_error(field: str, value: str, error: str):
    """Log validation errors"""
    logger.bind(context="validation").warning(
        f"Validation failed for field '{field}' with value '{value}': {error}"
    )


def log_system_event(event: str, details: dict = None):
    """Log system events"""
    message = f"System event: {event}"
    if details:
        message += f" - Details: {details}"
    
    logger.bind(context="system").info(message)


class StreamlitLogHandler:
    """Custom log handler for Streamlit applications"""
    
    @staticmethod
    def log_page_access(page_name: str, user: str = "unknown"):
        """Log page access"""
        logger.bind(context="page_access").info(f"Page '{page_name}' accessed by user '{user}'")
    
    @staticmethod
    def log_form_submission(form_name: str, success: bool, user: str = "unknown", errors: list = None):
        """Log form submissions"""
        status = "successful" if success else "failed"
        message = f"Form '{form_name}' submission {status} by user '{user}'"
        
        if not success and errors:
            message += f" - Errors: {', '.join(errors)}"
        
        level = "info" if success else "warning"
        getattr(logger.bind(context="form_submission"), level)(message)
    
    @staticmethod
    def log_data_export(export_type: str, records_count: int, user: str = "unknown"):
        """Log data exports"""
        logger.bind(context="data_export").info(
            f"Data export '{export_type}' with {records_count} records by user '{user}'"
        )
    
    @staticmethod
    def log_user_action(user: str, action: str, details: str = None):
        """Log user actions for audit trail"""
        message = f"User '{user}' performed action: {action}"
        if details:
            message += f" - {details}"
        
        logger.bind(context="user_action").info(message)