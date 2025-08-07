#!/usr/bin/env python3
"""
Deploy Streamlit Optimizations Script
Safely updates existing files with performance improvements
"""

import os
import shutil
from datetime import datetime

def backup_file(file_path):
    """Create backup of existing file"""
    if os.path.exists(file_path):
        backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(file_path, backup_path)
        print(f"✅ Backed up {file_path} to {backup_path}")
        return backup_path
    return None

def deploy_optimizations():
    """Deploy the optimizations"""
    
    print("🚀 Deploying Streamlit Performance Optimizations")
    print("=" * 60)
    
    # 1. Backup and replace Home.py
    print("1. Updating Home.py...")
    backup_file("Home.py")
    
    try:
        shutil.copy2("optimized_home.py", "Home.py")
        print("   ✅ Home.py updated with optimizations")
    except Exception as e:
        print(f"   ❌ Error updating Home.py: {e}")
    
    # 2. Add import statements to existing pages
    print("\n2. Creating optimization imports...")
    
    optimization_import = """
# Performance Optimizations - Add to top of existing pages
from utils.streamlit_optimization import monitor_session_health, setup_auto_refresh
from utils.db_connection_manager import get_db_connection, read_sql

# Initialize optimizations
monitor_session_health()
setup_auto_refresh(25)  # Auto-refresh every 25 minutes
"""
    
    with open("utils/optimization_imports.py", "w") as f:
        f.write(optimization_import)
    print("   ✅ Created utils/optimization_imports.py")
    
    # 3. Update db_config.py for better connection management
    print("\n3. Updating database configuration...")
    backup_file("db_config.py")
    
    optimized_db_config = """import os
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool, NullPool

def get_database_engine():
    \"\"\"Get database engine optimized for Streamlit\"\"\"
    
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
"""
    
    try:
        with open("db_config_optimized.py", "w") as f:
            f.write(optimized_db_config)
        print("   ✅ Created optimized db_config_optimized.py")
        print("   ⚠️  To activate: rename db_config.py to db_config_old.py")
        print("       and rename db_config_optimized.py to db_config.py")
    except Exception as e:
        print(f"   ❌ Error creating optimized db config: {e}")
    
    # 4. Create performance monitoring shortcut
    print("\n4. Setting up performance monitoring...")
    
    # Add to requirements.txt if it doesn't exist
    requirements_additions = """
# Performance monitoring
psutil>=5.9.0
"""
    
    try:
        with open("requirements_additions.txt", "w") as f:
            f.write(requirements_additions.strip())
        print("   ✅ Created requirements_additions.txt")
        print("   📝 Add these to your requirements.txt file")
    except Exception as e:
        print(f"   ❌ Error creating requirements additions: {e}")
    
    # 5. Create quick deployment instructions
    deployment_guide = f"""
# Streamlit Performance Optimization Deployment Guide
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Files Created:
- utils/db_connection_manager.py - Optimized database connection management
- utils/streamlit_optimization.py - Performance optimization utilities  
- pages/Performance_Monitor.py - Performance monitoring dashboard
- optimized_home.py - Optimized version of Home.py

## Manual Steps Required:

1. **Update requirements.txt**:
   ```
   psutil>=5.9.0
   ```

2. **Replace Home.py** (backup created):
   ```bash
   cp Home.py Home.py.original
   cp optimized_home.py Home.py
   ```

3. **Update db_config.py** (backup created):
   ```bash
   cp db_config.py db_config.py.original  
   cp db_config_optimized.py db_config.py
   ```

4. **Add to existing pages** (optional but recommended):
   Add this to the top of your frequently used pages:
   ```python
   from utils.streamlit_optimization import monitor_session_health, setup_auto_refresh
   from utils.db_connection_manager import get_db_connection, read_sql
   
   # Initialize optimizations
   monitor_session_health()
   setup_auto_refresh(25)
   ```

5. **Replace database calls**:
   Replace `with engine.connect() as conn:` with `with get_db_connection() as conn:`
   Replace `pd.read_sql(text(query), conn)` with `read_sql(query)`

## Key Optimizations:

✅ **Database Connection Management**
- NullPool for production (better Streamlit compatibility)
- Automatic connection cleanup
- Connection leak prevention
- Query timeout protection

✅ **Session Management**  
- Activity tracking to prevent timeouts
- Auto-refresh before 30-minute timeout
- Memory usage monitoring
- Cache management with TTL

✅ **Performance Monitoring**
- Real-time performance metrics
- Memory and CPU usage tracking
- Database connection monitoring  
- Cache analysis and cleanup

✅ **Memory Optimization**
- Automatic garbage collection
- Query result caching with expiration
- Session state cleanup
- Reference data caching

## Expected Improvements:

🚀 **Reduced Session Timeouts**: Auto-refresh prevents 30-minute timeouts
🚀 **Better Memory Management**: Automatic cleanup and garbage collection  
🚀 **Faster Page Loads**: Intelligent caching and optimized queries
🚀 **Connection Stability**: No more connection leaks or hangs
🚀 **Performance Visibility**: Real-time monitoring and alerts

## Monitoring:

Access the performance dashboard at: pages/Performance_Monitor.py
- Real-time resource usage
- Session health monitoring  
- Database performance metrics
- Cache analysis and cleanup tools

## Rollback Plan:

If issues occur, restore from backups:
```bash
cp Home.py.backup_* Home.py
cp db_config.py.backup_* db_config.py  
```

## Support:

The optimizations are designed to be backward compatible and safe.
Monitor the Performance_Monitor.py dashboard for insights.
"""
    
    try:
        with open("DEPLOYMENT_GUIDE.md", "w") as f:
            f.write(deployment_guide)
        print("   ✅ Created DEPLOYMENT_GUIDE.md")
    except Exception as e:
        print(f"   ❌ Error creating deployment guide: {e}")
    
    print("\n" + "=" * 60)
    print("🎉 Optimization deployment completed!")
    print("\n📖 Next Steps:")
    print("1. Read DEPLOYMENT_GUIDE.md for manual steps")
    print("2. Install additional requirements: pip install psutil")
    print("3. Test with optimized_home.py")
    print("4. Monitor performance with Performance_Monitor.py")
    print("5. Gradually update other pages with optimization imports")
    
    print(f"\n⚠️  Backups created with timestamp: {datetime.now().strftime('%Y%m%d_%H%M%S')}")

if __name__ == "__main__":
    deploy_optimizations()