from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
from config import settings

engine = create_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=20,          # Increased pool size for concurrent users
    max_overflow=30,       # Allow more overflow connections
    pool_pre_ping=True,
    pool_recycle=3600,     # Recycle connections every hour
    pool_timeout=30,       # Timeout for getting connection from pool
    echo=settings.debug and settings.log_level == 'DEBUG'
)
