"""
Production Database Configuration for Cloud Deployment
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def get_database_url():
    """Get database URL from environment variables"""
    # Railway automatically provides DATABASE_URL
    database_url = os.getenv('DATABASE_URL')
    
    if database_url:
        # Fix for SQLAlchemy 2.0+ (Railway uses postgresql://, but SQLAlchemy prefers postgresql+psycopg2://)
        if database_url.startswith('postgresql://'):
            database_url = database_url.replace('postgresql://', 'postgresql+psycopg2://', 1)
        return database_url
    
    # Fallback for other cloud providers
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'erp_gl')
    db_user = os.getenv('DB_USER', 'postgres')
    db_password = os.getenv('DB_PASSWORD', '')
    
    return f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

# Create engine with production settings
database_url = get_database_url()
engine = create_engine(
    database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False  # Set to True for debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()

# For compatibility with existing code
if __name__ == "__main__":
    print(f"Database URL: {database_url}")
    print("Testing connection...")
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print("✅ Database connection successful!")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")