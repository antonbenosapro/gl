#!/usr/bin/env python3
"""
Create GL Accounts for UAT Testing

This script creates the necessary GL accounts for the bulk posting UAT test scenarios.

Author: Claude Code Assistant  
Date: August 6, 2025
"""

import sys
import os
sys.path.append('/home/anton/erp/gl')

from sqlalchemy import text
from db_config import engine
from utils.logger import get_logger

logger = get_logger("create_uat_accounts")

def create_uat_accounts():
    """Create GL accounts needed for UAT testing."""
    
    # UAT Test accounts needed - using valid account ranges
    uat_accounts = [
        # Revenue accounts (400xxx-449xxx = SALE group)
        {"id": "410001", "name": "Sales Revenue", "type": "REVENUE", "group": "SALE"},
        
        # Expense accounts (550xxx-649xxx = OPEX group)  
        {"id": "570001", "name": "Office Supplies Expense", "type": "EXPENSES", "group": "OPEX"},
        {"id": "580001", "name": "Rent Expense", "type": "EXPENSES", "group": "OPEX"},
        {"id": "610001", "name": "Salary Expense", "type": "EXPENSES", "group": "OPEX"},
        {"id": "620001", "name": "Payroll Tax Expense", "type": "EXPENSES", "group": "OPEX"},
        
        # Asset accounts (110xxx-119xxx = RECV, 140xxx-179xxx = FXAS)
        {"id": "115001", "name": "Accounts Receivable - Trade", "type": "ASSETS", "group": "RECV"},
        {"id": "150001", "name": "Equipment - IFRS Valuation", "type": "ASSETS", "group": "FXAS"},
        
        # Liability accounts (200xxx-219xxx = PAYB, 220xxx-239xxx = ACCR)
        {"id": "210001", "name": "Accounts Payable - Trade", "type": "LIABILITIES", "group": "PAYB"},
        {"id": "225001", "name": "Payroll Payable", "type": "LIABILITIES", "group": "ACCR"},
        {"id": "231001", "name": "Sales Tax Payable", "type": "LIABILITIES", "group": "ACCR"},
        {"id": "232001", "name": "Tax Withholding Payable", "type": "LIABILITIES", "group": "ACCR"},
        
        # Equity accounts (350xxx-399xxx = OCIE)
        {"id": "350001", "name": "Revaluation Reserve", "type": "EQUITY", "group": "OCIE"}
    ]
    
    print("Creating UAT GL Accounts...")
    print("=" * 50)
    
    created_count = 0
    skipped_count = 0
    
    try:
        with engine.begin() as conn:
            for account in uat_accounts:
                # Check if account already exists
                exists = conn.execute(text("""
                    SELECT COUNT(*) FROM glaccount WHERE glaccountid = :account_id
                """), {"account_id": account["id"]}).scalar()
                
                if exists > 0:
                    print(f"   ⏭️ Skipped {account['id']}: {account['name']} (already exists)")
                    skipped_count += 1
                    continue
                
                # Create the account
                conn.execute(text("""
                    INSERT INTO glaccount 
                    (glaccountid, accountname, accounttype, account_group_code, account_currency)
                    VALUES (:account_id, :account_name, :account_type, :group_code, 'USD')
                """), {
                    "account_id": account["id"],
                    "account_name": account["name"],
                    "account_type": account["type"], 
                    "group_code": account["group"]
                })
                
                print(f"   ✅ Created {account['id']}: {account['name']} ({account['type']})")
                created_count += 1
        
        print("=" * 50)
        print(f"Account Creation Summary:")
        print(f"   Created: {created_count}")
        print(f"   Skipped: {skipped_count}")
        print(f"   Total processed: {len(uat_accounts)}")
        
        return created_count > 0 or skipped_count == len(uat_accounts)
        
    except Exception as e:
        logger.error(f"Error creating UAT accounts: {e}")
        print(f"❌ Error creating accounts: {e}")
        return False

if __name__ == "__main__":
    success = create_uat_accounts()
    sys.exit(0 if success else 1)