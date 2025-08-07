"""
SQL Helper Functions for PostgreSQL
Common utilities to handle PostgreSQL-specific syntax properly
"""

from sqlalchemy import text
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

def build_date_filter(column: str, days_back: int, operator: str = ">=") -> tuple:
    """
    Build a proper PostgreSQL date filter with interval
    
    Args:
        column: The date/timestamp column name
        days_back: Number of days to go back
        operator: Comparison operator (>=, >, <=, <, =)
    
    Returns:
        Tuple of (where_clause, params_dict)
    """
    where_clause = f"{column} {operator} CURRENT_DATE - :days_back * INTERVAL '1 DAY'"
    params = {"days_back": days_back}
    
    return where_clause, params

def build_datetime_filter(column: str, hours_back: int, operator: str = ">=") -> tuple:
    """
    Build a proper PostgreSQL datetime filter with interval
    
    Args:
        column: The timestamp column name  
        hours_back: Number of hours to go back
        operator: Comparison operator
    
    Returns:
        Tuple of (where_clause, params_dict)
    """
    where_clause = f"{column} {operator} NOW() - :hours_back * INTERVAL '1 HOUR'"
    params = {"hours_back": hours_back}
    
    return where_clause, params

def build_between_dates_filter(column: str, start_date: datetime, end_date: datetime) -> tuple:
    """
    Build a BETWEEN dates filter
    
    Args:
        column: The date column name
        start_date: Start date
        end_date: End date
    
    Returns:
        Tuple of (where_clause, params_dict)
    """
    where_clause = f"{column} BETWEEN :start_date AND :end_date"
    params = {"start_date": start_date, "end_date": end_date}
    
    return where_clause, params

def build_recent_records_query(base_query: str, date_column: str, days_back: int = 30) -> tuple:
    """
    Add recent records filter to an existing query
    
    Args:
        base_query: The base SQL query
        date_column: Column to filter on
        days_back: Number of days back
    
    Returns:
        Tuple of (modified_query, params_dict)
    """
    # Check if query already has WHERE clause
    if "WHERE" in base_query.upper():
        modified_query = f"{base_query} AND {date_column} >= CURRENT_DATE - :days_back * INTERVAL '1 DAY'"
    else:
        modified_query = f"{base_query} WHERE {date_column} >= CURRENT_DATE - :days_back * INTERVAL '1 DAY'"
    
    params = {"days_back": days_back}
    
    return modified_query, params

def format_postgresql_interval(amount: int, unit: str) -> str:
    """
    Format PostgreSQL interval properly
    
    Args:
        amount: The amount (number)
        unit: The unit (DAY, HOUR, MINUTE, MONTH, YEAR)
    
    Returns:
        Properly formatted interval string
    """
    valid_units = ['DAY', 'HOUR', 'MINUTE', 'MONTH', 'YEAR', 'WEEK']
    unit = unit.upper()
    
    if unit not in valid_units:
        raise ValueError(f"Invalid interval unit: {unit}. Must be one of {valid_units}")
    
    if unit == 'DAY':
        return f"{amount} * INTERVAL '1 DAY'"
    elif unit == 'HOUR':
        return f"{amount} * INTERVAL '1 HOUR'"
    elif unit == 'MINUTE':
        return f"{amount} * INTERVAL '1 MINUTE'"
    elif unit == 'MONTH':
        return f"{amount} * INTERVAL '1 MONTH'"
    elif unit == 'YEAR':
        return f"{amount} * INTERVAL '1 YEAR'"
    elif unit == 'WEEK':
        return f"{amount} * INTERVAL '1 WEEK'"

def safe_sql_query(query: str, params: Dict[str, Any], connection) -> Any:
    """
    Execute SQL query safely with proper error handling
    
    Args:
        query: SQL query string
        params: Query parameters
        connection: Database connection
    
    Returns:
        Query result or None if error
    """
    try:
        result = connection.execute(text(query), params)
        return result
    except Exception as e:
        print(f"SQL Error: {e}")
        print(f"Query: {query}")
        print(f"Params: {params}")
        return None

# Common query patterns
class CommonQueries:
    """Common SQL query patterns for the ERP system"""
    
    @staticmethod
    def get_recent_journal_entries(days_back: int = 30, status_filter: Optional[str] = None) -> tuple:
        """Get recent journal entries with proper date filtering"""
        query = """
            SELECT documentnumber, reference, workflow_status, createdby, createdat
            FROM journalentryheader
            WHERE createdat >= CURRENT_DATE - :days_back * INTERVAL '1 DAY'
        """
        params = {"days_back": days_back}
        
        if status_filter:
            query += " AND workflow_status = :status"
            params["status"] = status_filter
        
        query += " ORDER BY createdat DESC"
        
        return query, params
    
    @staticmethod
    def get_workflow_items(days_back: int = 30, status_filter: Optional[str] = None) -> tuple:
        """Get workflow items with proper date filtering"""
        query = """
            SELECT wi.id, wi.document_number, wi.status, wi.created_at
            FROM workflow_instances wi
            WHERE wi.created_at >= CURRENT_DATE - :days_back * INTERVAL '1 DAY'
        """
        params = {"days_back": days_back}
        
        if status_filter:
            query += " AND wi.status = :status"
            params["status"] = status_filter
        
        query += " ORDER BY wi.created_at DESC"
        
        return query, params
    
    @staticmethod
    def get_user_submissions(username: str, days_back: int = 30) -> tuple:
        """Get user submissions with proper date filtering"""
        query = """
            SELECT jeh.documentnumber as document_number,
                   jeh.reference,
                   jeh.workflow_status as status,
                   jeh.submitted_for_approval_at as submitted_at,
                   jeh.approved_by as assigned_approver,
                   COALESCE(SUM(GREATEST(jel.debitamount, jel.creditamount)), 0) as total_amount,
                   'Standard' as approval_level
            FROM journalentryheader jeh
            LEFT JOIN journalentryline jel ON jeh.documentnumber = jel.documentnumber
            WHERE jeh.createdby = :username
            AND jeh.submitted_for_approval_at >= CURRENT_DATE - :days_back * INTERVAL '1 DAY'
            AND jeh.workflow_status IN ('PENDING_APPROVAL', 'APPROVED', 'REJECTED')
            GROUP BY jeh.documentnumber, jeh.reference, jeh.workflow_status, 
                     jeh.submitted_for_approval_at, jeh.approved_by
            ORDER BY jeh.submitted_for_approval_at DESC
        """
        params = {"username": username, "days_back": days_back}
        
        return query, params

# Usage examples for documentation:
"""
# Example usage:

# 1. Simple date filter
where_clause, params = build_date_filter("createdat", 30)
# Result: "createdat >= CURRENT_DATE - :days_back * INTERVAL '1 DAY'", {"days_back": 30}

# 2. Recent records
query, params = build_recent_records_query(
    "SELECT * FROM journalentryheader", 
    "createdat", 
    7
)

# 3. Common patterns
query, params = CommonQueries.get_recent_journal_entries(30, "DRAFT")

# 4. Safe execution
with engine.connect() as conn:
    result = safe_sql_query(query, params, conn)
    if result:
        data = result.fetchall()
"""