import os
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool, NullPool

def get_database_engine():
    """Get database engine optimized for Streamlit"""
    
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        # Production - use NullPool for better Streamlit compatibility
        if database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
        
        return create_engine(
            database_url,
            poolclass=NullPool,  # No pooling for Streamlit
            echo=False,
            connect_args={
                "connect_timeout": 10,
                "options": "-c statement_timeout=30000"
            }
        )
    
    # Local development - optimized pooling
    try:
        from config import settings
        database_url = settings.database_url
    except ImportError:
        database_url = "postgresql+psycopg2://postgres:admin123@localhost:5432/gl_erp"
    
    return create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=3,           # Smaller pool
        max_overflow=7,        # Less overflow
        pool_pre_ping=True,    # Health check
        pool_recycle=1800,     # 30 min recycle
        pool_timeout=20,       # Shorter timeout
        echo=False,
        connect_args={
            "connect_timeout": 10,
            "options": "-c statement_timeout=30000"
        }
    )

# Create the engine
engine = get_database_engine()
