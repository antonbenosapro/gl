"""
Parallel Posting Service for Multi-Ledger Operations

This service handles automated posting of approved journal entries across
all parallel ledgers with proper currency translation and derivation rule application.

Author: Claude Code Assistant
Date: August 6, 2025
"""

import logging
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional, Tuple, Any
from sqlalchemy import text
from db_config import engine
from utils.currency_service import CurrencyTranslationService
from utils.gl_posting_engine import GLPostingEngine
from utils.logger import get_logger

logger = get_logger("parallel_posting_service")

class ParallelPostingService:
    """Service for automated parallel ledger posting with currency translation."""
    
    def __init__(self):
        """Initialize the parallel posting service."""
        self.currency_service = CurrencyTranslationService()
        self.posting_engine = GLPostingEngine()
        self.system_user = "PARALLEL_POSTER"
        
    def process_approved_document_to_all_ledgers(self, document_number: str, 
                                               company_code: str) -> Dict[str, Any]:
        """
        Process an approved document for parallel posting across all active ledgers.
        
        Args:
            document_number: Journal entry document number
            company_code: Company code
            
        Returns:
            Dictionary with processing results for each ledger
        """
        results = {
            "document_number": document_number,
            "company_code": company_code,
            "processed_at": datetime.now(),
            "source_ledger": None,
            "ledger_results": {},
            "total_ledgers": 0,
            "successful_ledgers": 0,
            "failed_ledgers": 0,
            "errors": []
        }
        
        try:
            # Get source ledger (leading ledger)
            source_ledger = self._get_leading_ledger()
            if not source_ledger:
                results["errors"].append("No leading ledger configured")
                return results
                
            results["source_ledger"] = source_ledger
            
            # Get all target ledgers for parallel posting
            target_ledgers = self._get_parallel_ledgers(exclude_leading=True)
            results["total_ledgers"] = len(target_ledgers)
            
            if not target_ledgers:
                logger.info("No parallel ledgers configured - posting to source ledger only")
                # Post to source ledger only
                success, message = self._post_to_single_ledger(
                    document_number, company_code, source_ledger
                )
                results["ledger_results"][source_ledger] = {
                    "success": success,
                    "message": message,
                    "posted_lines": 0
                }
                results["successful_ledgers"] = 1 if success else 0
                results["failed_ledgers"] = 0 if success else 1
                return results
            
            logger.info(f"Processing document {document_number} for parallel posting to {len(target_ledgers)} ledgers")
            
            # Post to each target ledger using derivation rules
            for target_ledger in target_ledgers:
                try:
                    ledger_result = self._process_parallel_posting_to_ledger(
                        document_number, company_code, source_ledger, target_ledger
                    )
                    
                    results["ledger_results"][target_ledger["ledgerid"]] = ledger_result
                    
                    if ledger_result["success"]:
                        results["successful_ledgers"] += 1
                        logger.info(f"Successfully posted to {target_ledger['ledgerid']}: {ledger_result['message']}")
                    else:
                        results["failed_ledgers"] += 1
                        logger.error(f"Failed posting to {target_ledger['ledgerid']}: {ledger_result['message']}")
                        
                except Exception as e:
                    error_msg = f"Error processing ledger {target_ledger['ledgerid']}: {str(e)}"
                    results["ledger_results"][target_ledger["ledgerid"]] = {
                        "success": False,
                        "message": error_msg,
                        "posted_lines": 0
                    }
                    results["failed_ledgers"] += 1
                    logger.error(error_msg)
            
            # Update document status
            if results["successful_ledgers"] > 0:
                self._update_parallel_posting_status(document_number, company_code, results)
            
            # Log summary
            success_rate = (results["successful_ledgers"] / results["total_ledgers"] * 100) if results["total_ledgers"] > 0 else 0
            logger.info(f"Parallel posting complete: {results['successful_ledgers']}/{results['total_ledgers']} successful ({success_rate:.1f}%)")
            
        except Exception as e:
            error_msg = f"Parallel posting error for {document_number}: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(error_msg)
        
        return results
    
    def _process_parallel_posting_to_ledger(self, document_number: str, company_code: str,
                                          source_ledger: str, target_ledger: Dict) -> Dict[str, Any]:
        """
        Process posting to a single parallel ledger with derivation rules and currency translation.
        
        Args:
            document_number: Journal entry document number
            company_code: Company code  
            source_ledger: Source ledger ID
            target_ledger: Target ledger configuration
            
        Returns:
            Dictionary with posting results
        """
        result = {
            "success": False,
            "message": "",
            "posted_lines": 0,
            "currency_translations": 0,
            "derivation_adjustments": 0
        }
        
        try:
            # Get source journal entry lines
            source_lines = self._get_journal_entry_lines(document_number, company_code, source_ledger)
            if not source_lines:
                result["message"] = "No source journal entry lines found"
                return result
            
            # Apply derivation rules to create parallel ledger entries
            parallel_lines = []
            currency_translations = 0
            derivation_adjustments = 0
            
            for source_line in source_lines:
                parallel_line = self._apply_derivation_rules(
                    source_line, source_ledger, target_ledger["ledgerid"]
                )
                
                if parallel_line:
                    # Apply currency translation if needed
                    translated_line = self._apply_currency_translation(
                        parallel_line, target_ledger, source_line["posting_date"]
                    )
                    
                    if translated_line != parallel_line:
                        currency_translations += 1
                    
                    if translated_line["gl_account"] != source_line["gl_account"]:
                        derivation_adjustments += 1
                    
                    parallel_lines.append(translated_line)
            
            if not parallel_lines:
                result["message"] = "No lines generated after applying derivation rules"
                return result
            
            # Validate parallel entry balance
            if not self._validate_parallel_entry_balance(parallel_lines):
                result["message"] = "Parallel entry does not balance"
                return result
            
            # Create parallel ledger journal entry
            success, message = self._create_parallel_journal_entry(
                document_number, company_code, target_ledger["ledgerid"], parallel_lines
            )
            
            result["success"] = success
            result["message"] = message
            result["posted_lines"] = len(parallel_lines)
            result["currency_translations"] = currency_translations
            result["derivation_adjustments"] = derivation_adjustments
            
        except Exception as e:
            result["message"] = f"Error in parallel posting: {str(e)}"
            logger.error(f"Error processing parallel posting: {e}")
        
        return result
    
    def _get_leading_ledger(self) -> Optional[str]:
        """Get the leading ledger ID."""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT ledgerid FROM ledger 
                    WHERE isleadingledger = true 
                    LIMIT 1
                """)).fetchone()
                
                return result[0] if result else None
                
        except Exception as e:
            logger.error(f"Error getting leading ledger: {e}")
            return None
    
    def _get_parallel_ledgers(self, exclude_leading: bool = True) -> List[Dict]:
        """Get all parallel ledgers for posting."""
        try:
            with engine.connect() as conn:
                where_clause = ""
                if exclude_leading:
                    where_clause = "WHERE isleadingledger = false"
                
                result = conn.execute(text(f"""
                    SELECT ledgerid, description, accounting_principle, 
                           currencycode, parallel_currency_1, parallel_currency_2,
                           consolidation_ledger
                    FROM ledger 
                    {where_clause}
                    ORDER BY ledgerid
                """)).fetchall()
                
                return [
                    {
                        "ledgerid": row[0],
                        "description": row[1],
                        "accounting_principle": row[2],
                        "currencycode": row[3],
                        "parallel_currency_1": row[4],
                        "parallel_currency_2": row[5],
                        "consolidation_ledger": row[6]
                    }
                    for row in result
                ]
                
        except Exception as e:
            logger.error(f"Error getting parallel ledgers: {e}")
            return []
    
    def _get_journal_entry_lines(self, document_number: str, company_code: str, 
                               ledger_id: str) -> List[Dict]:
        """Get journal entry lines for a specific ledger."""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        jel.linenumber as line_id,
                        jel.glaccountid as gl_account,
                        jel.debitamount,
                        jel.creditamount,
                        jel.currencycode,
                        jel.description,
                        jel.business_unit_code as business_unit,
                        NULL as profitcenter,
                        NULL as businessarea,
                        jeh.postingdate as posting_date,
                        ga.account_group_code
                    FROM journalentryline jel
                    JOIN journalentryheader jeh ON jel.documentnumber = jeh.documentnumber 
                        AND jel.companycodeid = jeh.companycodeid
                    LEFT JOIN glaccount ga ON jel.glaccountid = ga.glaccountid
                    WHERE jel.documentnumber = :doc 
                    AND jel.companycodeid = :cc
                    AND jel.ledgerid = :ledger
                    ORDER BY jel.linenumber
                """), {
                    "doc": document_number,
                    "cc": company_code, 
                    "ledger": ledger_id
                }).fetchall()
                
                return [
                    {
                        "line_id": row[0],
                        "gl_account": row[1],
                        "debit_amount": Decimal(str(row[2])) if row[2] else Decimal('0'),
                        "credit_amount": Decimal(str(row[3])) if row[3] else Decimal('0'),
                        "currency_code": row[4],
                        "description": row[5],
                        "business_unit": row[6],
                        "profit_center": row[7],
                        "business_area": row[8],
                        "posting_date": row[9],
                        "account_group_id": row[10]
                    }
                    for row in result
                ]
                
        except Exception as e:
            logger.error(f"Error getting journal entry lines: {e}")
            return []
    
    def _apply_derivation_rules(self, source_line: Dict, source_ledger: str, 
                              target_ledger: str) -> Optional[Dict]:
        """
        Apply derivation rules to transform source line for target ledger.
        
        Args:
            source_line: Source journal entry line
            source_ledger: Source ledger ID
            target_ledger: Target ledger ID
            
        Returns:
            Transformed line or None if should be excluded
        """
        try:
            with engine.connect() as conn:
                # Get derivation rule for this account group or specific account
                result = conn.execute(text("""
                    SELECT derivation_rule, target_account, conversion_factor, adjustment_reason
                    FROM ledger_derivation_rules
                    WHERE source_ledger = :source
                    AND target_ledger = :target
                    AND (
                        (gl_account IS NOT NULL AND gl_account = :account)
                        OR (account_group_filter IS NOT NULL AND account_group_filter = :account_group)
                        OR (gl_account IS NULL AND account_group_filter IS NULL)
                    )
                    AND is_active = true
                    ORDER BY 
                        CASE WHEN gl_account IS NOT NULL THEN 1 
                             WHEN account_group_filter IS NOT NULL THEN 2 
                             ELSE 3 END
                    LIMIT 1
                """), {
                    "source": source_ledger,
                    "target": target_ledger,
                    "account": source_line["gl_account"],
                    "account_group": source_line["account_group_id"]
                }).fetchone()
                
                if not result:
                    # No specific rule found, use COPY as default
                    derivation_rule = "COPY"
                    target_account = source_line["gl_account"]
                    conversion_factor = Decimal('1.0')
                    adjustment_reason = "Default copy rule"
                else:
                    derivation_rule = result[0]
                    target_account = result[1] or source_line["gl_account"]
                    conversion_factor = Decimal(str(result[2])) if result[2] else Decimal('1.0')
                    adjustment_reason = result[3]
                
                # Apply derivation rule
                if derivation_rule == "EXCLUDE":
                    return None  # Skip this line for target ledger
                
                # Create derived line
                derived_line = source_line.copy()
                derived_line["gl_account"] = target_account
                derived_line["derivation_rule"] = derivation_rule
                derived_line["adjustment_reason"] = adjustment_reason
                
                # Apply conversion factor for adjustments
                if derivation_rule == "ADJUST" and conversion_factor != Decimal('1.0'):
                    derived_line["debit_amount"] = derived_line["debit_amount"] * conversion_factor
                    derived_line["credit_amount"] = derived_line["credit_amount"] * conversion_factor
                
                return derived_line
                
        except Exception as e:
            logger.error(f"Error applying derivation rules: {e}")
            return source_line.copy()  # Fallback to copy
    
    def _apply_currency_translation(self, line: Dict, target_ledger: Dict, 
                                  posting_date: date) -> Dict:
        """
        Apply currency translation to journal entry line if needed.
        
        Args:
            line: Journal entry line
            target_ledger: Target ledger configuration
            posting_date: Posting date for exchange rate lookup
            
        Returns:
            Line with currency translation applied
        """
        try:
            source_currency = line["currency_code"]
            target_currency = target_ledger["currencycode"]
            
            # If currencies are the same, no translation needed
            if source_currency == target_currency:
                return line
            
            # Translate amounts
            translated_line = line.copy()
            
            if line["debit_amount"] > 0:
                translated_amount = self.currency_service.translate_amount(
                    line["debit_amount"], source_currency, target_currency, posting_date
                )
                if translated_amount:
                    translated_line["debit_amount"] = translated_amount
            
            if line["credit_amount"] > 0:
                translated_amount = self.currency_service.translate_amount(
                    line["credit_amount"], source_currency, target_currency, posting_date
                )
                if translated_amount:
                    translated_line["credit_amount"] = translated_amount
            
            # Update currency code
            translated_line["currency_code"] = target_currency
            
            # Add translation information to description
            if source_currency != target_currency:
                exchange_rate = self.currency_service.get_exchange_rate(
                    source_currency, target_currency, posting_date
                )
                translated_line["description"] = f"{line['description']} [Translated {source_currency}→{target_currency} @ {exchange_rate}]"
            
            return translated_line
            
        except Exception as e:
            logger.error(f"Error applying currency translation: {e}")
            return line  # Return original if translation fails
    
    def _validate_parallel_entry_balance(self, lines: List[Dict]) -> bool:
        """Validate that parallel entry debits equal credits."""
        try:
            total_debits = sum(line["debit_amount"] for line in lines)
            total_credits = sum(line["credit_amount"] for line in lines)
            
            # Allow small rounding differences (0.01)
            difference = abs(total_debits - total_credits)
            return difference <= Decimal('0.01')
            
        except Exception as e:
            logger.error(f"Error validating parallel entry balance: {e}")
            return False
    
    def _create_parallel_journal_entry(self, document_number: str, company_code: str,
                                     target_ledger: str, lines: List[Dict]) -> Tuple[bool, str]:
        """Create journal entry in parallel ledger."""
        try:
            with engine.connect() as conn:
                with conn.begin():
                    # Create parallel document number
                    parallel_doc_number = f"{document_number}_{target_ledger}"
                    
                    # Check if parallel entry already exists
                    existing = conn.execute(text("""
                        SELECT COUNT(*) FROM journalentryheader 
                        WHERE documentnumber = :doc AND companycodeid = :cc
                    """), {
                        "doc": parallel_doc_number,
                        "cc": company_code
                    }).scalar()
                    
                    if existing > 0:
                        return False, f"Parallel entry {parallel_doc_number} already exists"
                    
                    # Get original header information
                    header_info = conn.execute(text("""
                        SELECT postingdate, fiscalyear, period, reference, description,
                               createdby, approved_by, approved_at, posted_at, posted_by
                        FROM journalentryheader
                        WHERE documentnumber = :doc AND companycodeid = :cc
                    """), {
                        "doc": document_number,
                        "cc": company_code
                    }).fetchone()
                    
                    if not header_info:
                        return False, "Original journal entry header not found"
                    
                    # Create parallel header - use COALESCE for timestamp fields
                    conn.execute(text("""
                        INSERT INTO journalentryheader 
                        (documentnumber, companycodeid, postingdate, fiscalyear, period, 
                         reference, description, createdby, createdat, workflow_status,
                         approved_by, approved_at, posted_at, posted_by, parallel_source_doc)
                        VALUES 
                        (:doc, :cc, :posting_date, :fy, :period,
                         :reference, :description, :created_by, CURRENT_TIMESTAMP, 'APPROVED',
                         :approved_by, COALESCE(:approved_at, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP, :posted_by, :source_doc)
                    """), {
                        "doc": parallel_doc_number,
                        "cc": company_code,
                        "posting_date": header_info[0],
                        "fy": header_info[1], 
                        "period": header_info[2],
                        "reference": f"Parallel from {document_number}",
                        "description": f"[{target_ledger}] {header_info[4] or 'Parallel Entry'}",
                        "created_by": self.system_user,
                        "approved_by": header_info[6] or self.system_user,  # approved_by
                        "approved_at": header_info[7],  # approved_at timestamp (allow None)
                        "posted_by": header_info[9] or self.system_user,  # posted_by
                        "source_doc": document_number
                    })
                    
                    # Create parallel lines
                    for i, line in enumerate(lines, 1):
                        conn.execute(text("""
                            INSERT INTO journalentryline
                            (documentnumber, companycodeid, linenumber, glaccountid, ledgerid,
                             debitamount, creditamount, currencycode, description,
                             business_unit_code)
                            VALUES
                            (:doc, :cc, :line_id, :account, :ledger,
                             :debit, :credit, :currency, :description,
                             :business_unit)
                        """), {
                            "doc": parallel_doc_number,
                            "cc": company_code,
                            "line_id": i,
                            "account": line["gl_account"],
                            "ledger": target_ledger,
                            "debit": line["debit_amount"],
                            "credit": line["credit_amount"],
                            "currency": line["currency_code"],
                            "description": line["description"],
                            "business_unit": line.get("business_unit")
                        })
                    
                    # Update GL account balances for parallel ledger
                    self._update_parallel_ledger_balances(
                        company_code, target_ledger, lines, header_info[0]
                    )
            
            return True, f"Created parallel entry {parallel_doc_number} with {len(lines)} lines"
            
        except Exception as e:
            error_msg = f"Error creating parallel journal entry: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _update_parallel_ledger_balances(self, company_code: str, ledger_id: str,
                                       lines: List[Dict], posting_date: date):
        """Update GL account balances for parallel ledger."""
        try:
            # Get fiscal year and period
            fiscal_year = posting_date.year
            period = posting_date.month
            
            with engine.connect() as conn:
                for line in lines:
                    # Update or insert balance record
                    conn.execute(text("""
                        INSERT INTO gl_account_balances 
                        (company_code, ledger_id, gl_account, fiscal_year, posting_period,
                         ytd_debits, ytd_credits, ytd_balance)
                        VALUES (:cc, :ledger, :account, :fy, :period, :debit, :credit, :balance)
                        ON CONFLICT (company_code, ledger_id, gl_account, fiscal_year, posting_period)
                        DO UPDATE SET
                            ytd_debits = gl_account_balances.ytd_debits + :debit,
                            ytd_credits = gl_account_balances.ytd_credits + :credit,
                            ytd_balance = gl_account_balances.ytd_balance + :balance,
                            last_updated = CURRENT_TIMESTAMP
                    """), {
                        "cc": company_code,
                        "ledger": ledger_id,
                        "account": line["gl_account"],
                        "fy": fiscal_year,
                        "period": period,
                        "debit": line["debit_amount"],
                        "credit": line["credit_amount"],
                        "balance": line["debit_amount"] - line["credit_amount"]
                    })
            
        except Exception as e:
            logger.error(f"Error updating parallel ledger balances: {e}")
    
    def _update_parallel_posting_status(self, document_number: str, company_code: str, 
                                      results: Dict):
        """Update document with parallel posting status."""
        try:
            with engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("""
                        UPDATE journalentryheader 
                        SET parallel_posted = true,
                            parallel_posted_at = CURRENT_TIMESTAMP,
                            parallel_posted_by = :posted_by,
                            parallel_ledger_count = :ledger_count,
                            parallel_success_count = :success_count
                        WHERE documentnumber = :doc AND companycodeid = :cc
                    """), {
                        "doc": document_number,
                        "cc": company_code,
                        "posted_by": self.system_user,
                        "ledger_count": results["total_ledgers"],
                        "success_count": results["successful_ledgers"]
                    })
                    
        except Exception as e:
            logger.error(f"Error updating parallel posting status: {e}")
    
    def get_parallel_posting_summary(self, document_number: str, 
                                   company_code: str) -> Dict[str, Any]:
        """Get summary of parallel posting results for a document."""
        try:
            with engine.connect() as conn:
                # Get parallel posting status
                status_result = conn.execute(text("""
                    SELECT parallel_posted, parallel_posted_at, parallel_posted_by,
                           parallel_ledger_count, parallel_success_count
                    FROM journalentryheader
                    WHERE documentnumber = :doc AND companycodeid = :cc
                """), {
                    "doc": document_number,
                    "cc": company_code
                }).fetchone()
                
                if not status_result:
                    return {"error": "Document not found"}
                
                # Get parallel document details
                parallel_docs = conn.execute(text("""
                    SELECT documentnumber, description, posted_at, posted_by,
                           (SELECT COUNT(*) FROM journalentryline WHERE documentnumber = jeh.documentnumber) as line_count
                    FROM journalentryheader jeh
                    WHERE parallel_source_doc = :doc AND companycodeid = :cc
                    ORDER BY documentnumber
                """), {
                    "doc": document_number,
                    "cc": company_code
                }).fetchall()
                
                return {
                    "source_document": document_number,
                    "parallel_posted": status_result[0],
                    "posted_at": status_result[1],
                    "posted_by": status_result[2],
                    "total_ledgers": status_result[3] or 0,
                    "successful_ledgers": status_result[4] or 0,
                    "parallel_documents": [
                        {
                            "document_number": row[0],
                            "description": row[1],
                            "posted_at": row[2],
                            "posted_by": row[3],
                            "line_count": row[4]
                        }
                        for row in parallel_docs
                    ]
                }
                
        except Exception as e:
            logger.error(f"Error getting parallel posting summary: {e}")
            return {"error": str(e)}

# Utility functions for external use
def post_document_to_all_ledgers(document_number: str, company_code: str) -> Dict[str, Any]:
    """Post a single document to all parallel ledgers."""
    service = ParallelPostingService()
    return service.process_approved_document_to_all_ledgers(document_number, company_code)

def get_document_parallel_status(document_number: str, company_code: str) -> Dict[str, Any]:
    """Get parallel posting status for a document."""
    service = ParallelPostingService()
    return service.get_parallel_posting_summary(document_number, company_code)

# Test function
def test_parallel_posting_service():
    """Test the parallel posting service functionality."""
    service = ParallelPostingService()
    
    print("=== Parallel Posting Service Test ===")
    
    # Test ledger configuration
    source_ledger = service._get_leading_ledger()
    parallel_ledgers = service._get_parallel_ledgers()
    
    print(f"Source ledger: {source_ledger}")
    print(f"Parallel ledgers: {len(parallel_ledgers)}")
    for ledger in parallel_ledgers:
        print(f"  - {ledger['ledgerid']}: {ledger['description']} ({ledger['accounting_principle']})")
    
    print("✅ Parallel Posting Service: Initialized and ready")

if __name__ == "__main__":
    test_parallel_posting_service()