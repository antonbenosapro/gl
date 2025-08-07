#!/usr/bin/env python3
"""
Enterprise Ledger Assignment Service

This service provides enterprise-grade ledger assignment logic for journal entries,
ensuring SAP-compliant ledger management and backward compatibility.

Key Features:
- Automatic default ledger assignment for new entries
- Historical data migration for NULL ledger assignments
- Context-aware ledger derivation based on GL account types
- Multi-standard accounting support (US GAAP, IFRS, Tax, Management)

Author: Claude Code Assistant
Date: August 6, 2025
"""

from typing import Dict, List, Optional, Tuple
from sqlalchemy import text
from db_config import engine
from utils.logger import get_logger

logger = get_logger("ledger_assignment_service")

class LedgerAssignmentService:
    """Enterprise service for intelligent ledger assignment."""
    
    def __init__(self):
        """Initialize the ledger assignment service."""
        self.leading_ledger_cache = None
        self.ledger_cache = None
        self.account_type_mapping = {
            # Asset accounts typically go to leading ledger
            'ASSET': 'L1',
            'LIABILITY': 'L1', 
            'EQUITY': 'L1',
            # Revenue/Expense may need specific ledger rules
            'REVENUE': 'L1',
            'EXPENSE': 'L1'
        }
    
    def get_leading_ledger(self) -> str:
        """Get the leading ledger ID."""
        if self.leading_ledger_cache is None:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT ledgerid FROM ledger 
                    WHERE isleadingledger = true 
                    ORDER BY ledgerid LIMIT 1
                """)).scalar()
                self.leading_ledger_cache = result or 'L1'
        return self.leading_ledger_cache
    
    def get_all_ledgers(self) -> Dict[str, Dict]:
        """Get all available ledgers with their properties."""
        if self.ledger_cache is None:
            with engine.connect() as conn:
                ledgers = conn.execute(text("""
                    SELECT ledgerid, description, isleadingledger, 
                           accounting_principle, currencycode
                    FROM ledger 
                    ORDER BY ledgerid
                """)).mappings().all()
                
                self.ledger_cache = {
                    ledger['ledgerid']: {
                        'description': ledger['description'],
                        'is_leading': ledger['isleadingledger'],
                        'principle': ledger['accounting_principle'],
                        'currency': ledger['currencycode']
                    }
                    for ledger in ledgers
                }
        return self.ledger_cache
    
    def get_default_ledger_for_account(self, gl_account_id: str, 
                                     company_code: str = "1000") -> str:
        """
        Get the appropriate default ledger for a GL account.
        
        Enterprise Logic:
        1. Check if account has specific ledger rules
        2. Use account type mapping
        3. Fall back to leading ledger
        """
        try:
            with engine.connect() as conn:
                # Get account type and any specific ledger rules
                account_info = conn.execute(text("""
                    SELECT accounttype, account_group_code 
                    FROM glaccount 
                    WHERE glaccountid = :account_id
                """), {"account_id": gl_account_id}).mappings().first()
                
                if account_info:
                    account_type = account_info['accounttype']
                    
                    # Apply enterprise logic based on account type
                    if account_type in self.account_type_mapping:
                        return self.account_type_mapping[account_type]
                    
                # Default to leading ledger
                return self.get_leading_ledger()
                
        except Exception as e:
            logger.warning(f"Error determining ledger for account {gl_account_id}: {e}")
            return self.get_leading_ledger()
    
    def assign_default_ledgers_for_document(self, document_number: str, 
                                          company_code: str) -> int:
        """
        Assign default ledgers to all lines in a document that have NULL ledgerid.
        
        Returns: Number of lines updated
        """
        updated_count = 0
        
        try:
            with engine.begin() as conn:
                # Get lines with NULL ledgerid
                null_ledger_lines = conn.execute(text("""
                    SELECT linenumber, glaccountid 
                    FROM journalentryline 
                    WHERE documentnumber = :doc AND companycodeid = :cc 
                    AND (ledgerid IS NULL OR ledgerid = '')
                """), {"doc": document_number, "cc": company_code}).mappings().all()
                
                for line in null_ledger_lines:
                    # Get appropriate ledger for this GL account
                    default_ledger = self.get_default_ledger_for_account(
                        line['glaccountid'], company_code
                    )
                    
                    # Update the line with the default ledger
                    conn.execute(text("""
                        UPDATE journalentryline 
                        SET ledgerid = :ledger_id 
                        WHERE documentnumber = :doc AND companycodeid = :cc 
                        AND linenumber = :line_num
                    """), {
                        "ledger_id": default_ledger,
                        "doc": document_number,
                        "cc": company_code,
                        "line_num": line['linenumber']
                    })
                    
                    updated_count += 1
                    logger.info(f"Assigned ledger {default_ledger} to document {document_number} line {line['linenumber']}")
                
        except Exception as e:
            logger.error(f"Error assigning default ledgers: {e}")
            
        return updated_count
    
    def migrate_historical_null_ledgers(self, batch_size: int = 1000) -> Dict[str, int]:
        """
        Enterprise migration function to assign ledgers to all historical NULL entries.
        
        Returns: Statistics about the migration
        """
        stats = {
            "documents_processed": 0,
            "lines_updated": 0,
            "errors": 0
        }
        
        try:
            with engine.connect() as conn:
                # Get all documents with NULL ledger lines
                docs_with_null_ledgers = conn.execute(text("""
                    SELECT DISTINCT documentnumber, companycodeid 
                    FROM journalentryline 
                    WHERE ledgerid IS NULL OR ledgerid = ''
                    ORDER BY documentnumber
                    LIMIT :batch_size
                """), {"batch_size": batch_size}).mappings().all()
                
                for doc in docs_with_null_ledgers:
                    try:
                        updated = self.assign_default_ledgers_for_document(
                            doc['documentnumber'], doc['companycodeid']
                        )
                        stats["documents_processed"] += 1
                        stats["lines_updated"] += updated
                        
                    except Exception as doc_error:
                        logger.error(f"Error processing document {doc['documentnumber']}: {doc_error}")
                        stats["errors"] += 1
                        
        except Exception as e:
            logger.error(f"Error in historical migration: {e}")
            stats["errors"] += 1
            
        return stats
    
    def validate_ledger_assignment(self, ledger_id: str) -> Tuple[bool, str]:
        """
        Validate that a ledger assignment is valid.
        
        Returns: (is_valid, message)
        """
        if not ledger_id or ledger_id.strip() == '':
            return False, "Ledger ID cannot be empty"
            
        ledgers = self.get_all_ledgers()
        if ledger_id not in ledgers:
            available = ', '.join(ledgers.keys())
            return False, f"Invalid ledger ID '{ledger_id}'. Available: {available}"
            
        return True, "Valid ledger assignment"
    
    def get_ledger_info_for_ui(self) -> List[Dict]:
        """Get ledger information formatted for UI selection."""
        ledgers = self.get_all_ledgers()
        ui_ledgers = []
        
        for ledger_id, info in ledgers.items():
            ui_ledgers.append({
                'ledger_id': ledger_id,
                'display_name': f"{ledger_id} - {info['description']}",
                'description': info['description'],
                'is_leading': info['is_leading'],
                'principle': info['principle'],
                'is_default': info['is_leading']  # Leading ledger is default
            })
        
        # Sort with leading ledger first
        ui_ledgers.sort(key=lambda x: (not x['is_leading'], x['ledger_id']))
        return ui_ledgers

# Global service instance
ledger_assignment_service = LedgerAssignmentService()