
# Performance Optimizations - Add to top of existing pages
from utils.streamlit_optimization import monitor_session_health, setup_auto_refresh
from utils.db_connection_manager import get_db_connection, read_sql

# Initialize optimizations
monitor_session_health()
setup_auto_refresh(25)  # Auto-refresh every 25 minutes
