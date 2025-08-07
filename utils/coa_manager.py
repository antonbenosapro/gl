"""
COA Management Utilities
Provides functions for managing Chart of Accounts, Account Groups, and Field Status Groups
"""

from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import text
from db_config import engine
from utils.logger import get_logger
from datetime import datetime

logger = get_logger("coa_manager")

class COAManager:
    """Chart of Accounts Management Class"""
    
    @staticmethod
    def validate_account_number(account_id: str, account_group_code: str) -> Tuple[bool, str]:
        """Validate if account number is within the allowed range for the account group"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT number_range_from, number_range_to, group_name
                    FROM account_groups 
                    WHERE group_code = :group_code AND is_active = TRUE
                """), {"group_code": account_group_code}).fetchone()
                
                if not result:
                    return False, f"Account group {account_group_code} not found or inactive"
                
                range_from, range_to, group_name = result
                account_num = int(account_id)
                range_from_num = int(range_from)
                range_to_num = int(range_to)
                
                if range_from_num <= account_num <= range_to_num:
                    return True, "Account number is within valid range"
                else:
                    return False, f"Account {account_id} is outside range {range_from}-{range_to} for group {group_name}"
                    
        except ValueError:
            return False, "Account ID must be numeric"
        except Exception as e:
            logger.error(f"Account validation error: {e}")
            return False, f"Validation error: {str(e)}"
    
    @staticmethod
    def get_next_available_account(account_group_code: str) -> Optional[str]:
        """Get the next available account number in the specified group"""
        try:
            with engine.connect() as conn:
                # Get group range
                group_info = conn.execute(text("""
                    SELECT number_range_from, number_range_to
                    FROM account_groups 
                    WHERE group_code = :group_code AND is_active = TRUE
                """), {"group_code": account_group_code}).fetchone()
                
                if not group_info:
                    return None
                
                range_from, range_to = group_info
                
                # Find existing accounts in this range
                existing_accounts = conn.execute(text("""
                    SELECT glaccountid::bigint as account_num
                    FROM glaccount 
                    WHERE account_group_code = :group_code
                    AND glaccountid::bigint BETWEEN :range_from AND :range_to
                    AND (marked_for_deletion = FALSE OR marked_for_deletion IS NULL)
                    ORDER BY glaccountid::bigint
                """), {
                    "group_code": account_group_code,
                    "range_from": int(range_from),
                    "range_to": int(range_to)
                }).fetchall()
                
                used_numbers = {row[0] for row in existing_accounts}
                
                # Find first available number
                for num in range(int(range_from), int(range_to) + 1):
                    if num not in used_numbers:
                        return str(num).zfill(6)  # Return as 6-digit string
                
                return None  # No available numbers
                
        except Exception as e:
            logger.error(f"Error finding next available account: {e}")
            return None
    
    @staticmethod
    def get_account_group_info(group_code: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about an account group"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT group_code, group_name, group_description, account_class,
                           balance_sheet_type, pnl_type, number_range_from, number_range_to,
                           require_cost_center, require_profit_center, require_business_area,
                           require_tax_code, require_trading_partner, default_field_status_group,
                           allow_line_items, allow_open_items, reconciliation_account,
                           is_active, created_by, created_at
                    FROM account_groups 
                    WHERE group_code = :group_code
                """), {"group_code": group_code}).fetchone()
                
                if not result:
                    return None
                
                return {
                    "group_code": result[0],
                    "group_name": result[1],
                    "group_description": result[2],
                    "account_class": result[3],
                    "balance_sheet_type": result[4],
                    "pnl_type": result[5],
                    "number_range_from": result[6],
                    "number_range_to": result[7],
                    "require_cost_center": result[8],
                    "require_profit_center": result[9],
                    "require_business_area": result[10],
                    "require_tax_code": result[11],
                    "require_trading_partner": result[12],
                    "default_field_status_group": result[13],
                    "allow_line_items": result[14],
                    "allow_open_items": result[15],
                    "reconciliation_account": result[16],
                    "is_active": result[17],
                    "created_by": result[18],
                    "created_at": result[19]
                }
                
        except Exception as e:
            logger.error(f"Error getting account group info: {e}")
            return None
    
    @staticmethod
    def get_field_status_group_info(group_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a field status group"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT group_id, group_name, group_description,
                           cost_center_status, profit_center_status, business_area_status,
                           tax_code_status, trading_partner_status, reference_field_status,
                           document_header_text_status, assignment_field_status, text_field_status,
                           is_active, created_by, created_at
                    FROM field_status_groups 
                    WHERE group_id = :group_id
                """), {"group_id": group_id}).fetchone()
                
                if not result:
                    return None
                
                return {
                    "group_id": result[0],
                    "group_name": result[1],
                    "group_description": result[2],
                    "cost_center_status": result[3],
                    "profit_center_status": result[4],
                    "business_area_status": result[5],
                    "tax_code_status": result[6],
                    "trading_partner_status": result[7],
                    "reference_field_status": result[8],
                    "document_header_text_status": result[9],
                    "assignment_field_status": result[10],
                    "text_field_status": result[11],
                    "is_active": result[12],
                    "created_by": result[13],
                    "created_at": result[14]
                }
                
        except Exception as e:
            logger.error(f"Error getting field status group info: {e}")
            return None
    
    @staticmethod
    def validate_gl_account_data(account_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate GL account data before creation/update"""
        errors = []
        
        # Required fields
        required_fields = ['glaccountid', 'accountname', 'account_group_code']
        for field in required_fields:
            if not account_data.get(field):
                errors.append(f"{field} is required")
        
        # Account ID format validation
        account_id = account_data.get('glaccountid', '')
        if account_id:
            if not account_id.isdigit():
                errors.append("Account ID must be numeric")
            elif len(account_id) != 6:
                errors.append("Account ID must be 6 digits")
        
        # Account name length
        account_name = account_data.get('accountname', '')
        if len(account_name) > 100:
            errors.append("Account name cannot exceed 100 characters")
        
        # Validate account group exists and account is in range
        account_group = account_data.get('account_group_code')
        if account_group and account_id:
            is_valid, message = COAManager.validate_account_number(account_id, account_group)
            if not is_valid:
                errors.append(message)
        
        return len(errors) == 0, errors
    
    @staticmethod
    def create_gl_account(account_data: Dict[str, Any], created_by: str) -> Tuple[bool, str]:
        """Create a new GL account with full validation"""
        try:
            # Validate data
            is_valid, errors = COAManager.validate_gl_account_data(account_data)
            if not is_valid:
                return False, "; ".join(errors)
            
            with engine.connect() as conn:
                with conn.begin():
                    # Check if account already exists
                    existing = conn.execute(text("""
                        SELECT COUNT(*) FROM glaccount WHERE glaccountid = :id
                    """), {"id": account_data['glaccountid']}).fetchone()[0]
                    
                    if existing > 0:
                        return False, f"Account {account_data['glaccountid']} already exists"
                    
                    # Get account group information
                    ag_info = COAManager.get_account_group_info(account_data['account_group_code'])
                    if not ag_info:
                        return False, f"Account group {account_data['account_group_code']} not found"
                    
                    # Get field status group info
                    fsg_info = COAManager.get_field_status_group_info(ag_info['default_field_status_group'])
                    
                    # Create the account
                    conn.execute(text("""
                        INSERT INTO glaccount (
                            glaccountid, accountname, accounttype, account_class, account_group_code,
                            balance_sheet_indicator, pnl_statement_type, short_text, long_text,
                            account_currency, line_item_display, open_item_management,
                            cost_center_required, profit_center_required, business_area_required,
                            field_status_group, reconciliation_account_type, planning_level,
                            created_by, migration_date, migrated_from_legacy
                        ) VALUES (
                            :glaccountid, :accountname, :accounttype, :account_class, :account_group_code,
                            :balance_sheet_indicator, :pnl_statement_type, :short_text, :long_text,
                            :account_currency, :line_item_display, :open_item_management,
                            :cost_center_required, :profit_center_required, :business_area_required,
                            :field_status_group, :reconciliation_account_type, :planning_level,
                            :created_by, CURRENT_TIMESTAMP, 'COA_MANAGEMENT'
                        )
                    """), {
                        "glaccountid": account_data['glaccountid'],
                        "accountname": account_data['accountname'],
                        "accounttype": account_data.get('accounttype', 'STANDARD'),
                        "account_class": ag_info['account_class'],
                        "account_group_code": account_data['account_group_code'],
                        "balance_sheet_indicator": ag_info['balance_sheet_type'] is not None,
                        "pnl_statement_type": ag_info['pnl_type'] or 'NOT_APPLICABLE',
                        "short_text": account_data.get('short_text', account_data['accountname'][:20]),
                        "long_text": account_data.get('long_text', account_data['accountname'][:50]),
                        "account_currency": account_data.get('account_currency', 'USD'),
                        "line_item_display": account_data.get('line_item_display', True),
                        "open_item_management": account_data.get('open_item_management', False),
                        "cost_center_required": ag_info['require_cost_center'],
                        "profit_center_required": ag_info['require_profit_center'],
                        "business_area_required": ag_info['require_business_area'],
                        "field_status_group": ag_info['default_field_status_group'],
                        "reconciliation_account_type": COAManager._determine_reconciliation_type(account_data.get('accounttype', 'STANDARD')),
                        "planning_level": account_data.get('planning_level', 'ACCOUNT'),
                        "created_by": created_by
                    })
                    
                    return True, f"Account {account_data['glaccountid']} created successfully"
                    
        except Exception as e:
            logger.error(f"Error creating GL account: {e}")
            return False, f"Creation failed: {str(e)}"
    
    @staticmethod
    def _determine_reconciliation_type(account_type: str) -> str:
        """Determine reconciliation account type based on account type"""
        mapping = {
            'RECEIVABLE': 'CUSTOMER',
            'PAYABLE': 'VENDOR',
            'ASSET': 'ASSET',
            'MATERIAL': 'MATERIAL'
        }
        return mapping.get(account_type, 'NONE')
    
    @staticmethod
    def get_coa_statistics() -> Dict[str, Any]:
        """Get comprehensive COA statistics"""
        try:
            with engine.connect() as conn:
                # Account groups stats
                ag_stats = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_groups,
                        COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_groups,
                        COUNT(DISTINCT account_class) as distinct_classes
                    FROM account_groups
                """)).fetchone()
                
                # GL accounts stats
                gl_stats = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_accounts,
                        COUNT(CASE WHEN marked_for_deletion = FALSE OR marked_for_deletion IS NULL THEN 1 END) as active_accounts,
                        COUNT(DISTINCT account_class) as classes_in_use,
                        COUNT(DISTINCT account_group_code) as groups_in_use
                    FROM glaccount
                """)).fetchone()
                
                # Field status groups stats
                fsg_stats = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_fsgs,
                        COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_fsgs
                    FROM field_status_groups
                """)).fetchone()
                
                # Usage by class
                class_usage = conn.execute(text("""
                    SELECT 
                        account_class,
                        COUNT(*) as account_count
                    FROM glaccount 
                    WHERE marked_for_deletion = FALSE OR marked_for_deletion IS NULL
                    GROUP BY account_class
                    ORDER BY account_class
                """)).fetchall()
                
                # Range utilization
                range_utilization = conn.execute(text("""
                    SELECT 
                        ag.group_code,
                        ag.group_name,
                        ag.account_class,
                        ag.number_range_from,
                        ag.number_range_to,
                        COUNT(ga.glaccountid) as used_accounts,
                        (ag.number_range_to::bigint - ag.number_range_from::bigint + 1) as total_range,
                        ROUND(COUNT(ga.glaccountid) * 100.0 / 
                              NULLIF((ag.number_range_to::bigint - ag.number_range_from::bigint + 1), 0), 2) as utilization_pct
                    FROM account_groups ag
                    LEFT JOIN glaccount ga ON ag.group_code = ga.account_group_code
                        AND (ga.marked_for_deletion = FALSE OR ga.marked_for_deletion IS NULL)
                    WHERE ag.is_active = TRUE
                    GROUP BY ag.group_code, ag.group_name, ag.account_class, 
                             ag.number_range_from, ag.number_range_to
                    ORDER BY utilization_pct DESC
                """)).fetchall()
                
                return {
                    "account_groups": {
                        "total": ag_stats[0],
                        "active": ag_stats[1],
                        "distinct_classes": ag_stats[2]
                    },
                    "gl_accounts": {
                        "total": gl_stats[0],
                        "active": gl_stats[1],
                        "classes_in_use": gl_stats[2],
                        "groups_in_use": gl_stats[3]
                    },
                    "field_status_groups": {
                        "total": fsg_stats[0],
                        "active": fsg_stats[1]
                    },
                    "class_usage": [{"class": row[0], "count": row[1]} for row in class_usage],
                    "range_utilization": [
                        {
                            "group_code": row[0],
                            "group_name": row[1],
                            "account_class": row[2],
                            "range_from": row[3],
                            "range_to": row[4],
                            "used_accounts": row[5],
                            "total_range": row[6],
                            "utilization_pct": row[7]
                        }
                        for row in range_utilization
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error getting COA statistics: {e}")
            return {}
    
    @staticmethod
    def search_accounts(search_term: str, account_group: str = None, account_class: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Search GL accounts with optional filters"""
        try:
            with engine.connect() as conn:
                where_conditions = ["(ga.marked_for_deletion = FALSE OR ga.marked_for_deletion IS NULL)"]
                params = {}
                
                if search_term:
                    where_conditions.append("(UPPER(ga.glaccountid) LIKE UPPER(:search) OR UPPER(ga.accountname) LIKE UPPER(:search))")
                    params["search"] = f"%{search_term}%"
                
                if account_group:
                    where_conditions.append("ga.account_group_code = :group")
                    params["group"] = account_group
                
                if account_class:
                    where_conditions.append("ga.account_class = :class")
                    params["class"] = account_class
                
                where_clause = " AND ".join(where_conditions)
                
                results = conn.execute(text(f"""
                    SELECT 
                        ga.glaccountid, ga.accountname, ga.account_class, ga.account_group_code,
                        ga.short_text, ga.long_text, ga.balance_sheet_indicator, ga.pnl_statement_type,
                        ga.cost_center_required, ga.profit_center_required, ga.business_area_required,
                        ga.field_status_group, ga.reconciliation_account_type, ag.group_name
                    FROM glaccount ga
                    LEFT JOIN account_groups ag ON ga.account_group_code = ag.group_code
                    WHERE {where_clause}
                    ORDER BY ga.glaccountid
                    LIMIT :limit
                """), {**params, "limit": limit}).fetchall()
                
                return [
                    {
                        "glaccountid": row[0],
                        "accountname": row[1],
                        "account_class": row[2],
                        "account_group_code": row[3],
                        "short_text": row[4],
                        "long_text": row[5],
                        "balance_sheet_indicator": row[6],
                        "pnl_statement_type": row[7],
                        "cost_center_required": row[8],
                        "profit_center_required": row[9],
                        "business_area_required": row[10],
                        "field_status_group": row[11],
                        "reconciliation_account_type": row[12],
                        "group_name": row[13]
                    }
                    for row in results
                ]
                
        except Exception as e:
            logger.error(f"Error searching accounts: {e}")
            return []

# Singleton instance
coa_manager = COAManager()