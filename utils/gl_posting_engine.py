"""
Enterprise GL Posting Engine
Following SAP FI-CO Architecture and Best Practices

This module handles the posting of approved journal entries to the General Ledger,
creating actual GL transactions and maintaining account balances.
"""

from datetime import datetime, date
from typing import List, Dict, Optional, Tuple, Any
from decimal import Decimal
from sqlalchemy import text
from db_config import engine
from utils.logger import get_logger
from utils.workflow_engine import WorkflowEngine

logger = get_logger("gl_posting_engine")

class GLPostingEngine:
    """
    Enterprise General Ledger Posting Engine
    Handles posting of approved journal entries to GL tables
    """
    
    @staticmethod
    def post_journal_entry(journal_doc_number: str, company_code: str, 
                          posted_by: str, posting_date: date = None) -> Tuple[bool, str]:
        """
        Main posting method - posts approved journal entry to GL
        
        Args:
            journal_doc_number: Document number to post
            company_code: Company code
            posted_by: User performing the posting
            posting_date: Optional posting date (defaults to today)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            if posting_date is None:
                posting_date = date.today()
            
            logger.info(f"Starting GL posting for document {journal_doc_number}")
            
            with engine.begin() as conn:
                # 1. VALIDATION PHASE
                validation_result = GLPostingEngine._validate_posting_eligibility(
                    conn, journal_doc_number, company_code, posting_date, posted_by
                )
                if not validation_result[0]:
                    return False, validation_result[1]
                
                journal_data = validation_result[2]
                
                # 2. CREATE POSTING DOCUMENT HEADER
                doc_id = GLPostingEngine._create_posting_document(
                    conn, journal_data, posted_by, posting_date
                )
                
                # 3. CREATE GL TRANSACTIONS
                GLPostingEngine._create_gl_transactions(
                    conn, doc_id, journal_data, posted_by, posting_date
                )
                
                # 4. UPDATE ACCOUNT BALANCES
                GLPostingEngine._update_account_balances(
                    conn, journal_data, posting_date
                )
                
                # 5. UPDATE SOURCE DOCUMENT STATUS
                GLPostingEngine._update_journal_entry_status(
                    conn, journal_doc_number, company_code, posted_by, posting_date
                )
                
                # 6. CREATE AUDIT TRAIL
                GLPostingEngine._create_posting_audit_trail(
                    conn, doc_id, journal_data, posted_by, posting_date
                )
                
                logger.info(f"Document {journal_doc_number} posted successfully")
                return True, f"Document {journal_doc_number} posted successfully to GL"
                
        except Exception as e:
            logger.error(f"Error posting document {journal_doc_number}: {e}")
            return False, f"Posting failed: {str(e)}"
    
    @staticmethod
    def post_multiple_journal_entries(journal_doc_numbers: List[str], company_code: str,
                                    posted_by: str, posting_date: date = None) -> Dict[str, Any]:
        """
        Batch posting of multiple journal entries
        
        Args:
            journal_doc_numbers: List of document numbers to post
            company_code: Company code
            posted_by: User performing the posting
            posting_date: Optional posting date
            
        Returns:
            Dictionary with batch posting results
        """
        results = {
            "total_documents": len(journal_doc_numbers),
            "posted_successfully": 0,
            "failed_documents": [],
            "success_documents": [],
            "batch_start_time": datetime.now()
        }
        
        for doc_number in journal_doc_numbers:
            success, message = GLPostingEngine.post_journal_entry(
                doc_number, company_code, posted_by, posting_date
            )
            
            if success:
                results["posted_successfully"] += 1
                results["success_documents"].append({
                    "document": doc_number,
                    "message": message
                })
            else:
                results["failed_documents"].append({
                    "document": doc_number,
                    "error": message
                })
        
        results["batch_end_time"] = datetime.now()
        results["batch_duration"] = (results["batch_end_time"] - results["batch_start_time"]).total_seconds()
        
        logger.info(f"Batch posting completed: {results['posted_successfully']}/{results['total_documents']} successful")
        return results
    
    @staticmethod
    def _validate_posting_eligibility(conn, journal_doc_number: str, company_code: str,
                                    posting_date: date, posted_by: str) -> Tuple[bool, str, Optional[Dict]]:
        """Comprehensive posting eligibility validation"""
        
        # Get journal entry data
        journal_result = conn.execute(text("""
            SELECT jeh.documentnumber, jeh.companycodeid, jeh.workflow_status,
                   jeh.postingdate, jeh.fiscalyear, jeh.period, jeh.currencycode,
                   jeh.createdby, jeh.posted_at, jeh.posted_by
            FROM journalentryheader jeh
            WHERE jeh.documentnumber = :doc AND jeh.companycodeid = :cc
        """), {"doc": journal_doc_number, "cc": company_code})
        
        journal_row = journal_result.fetchone()
        if not journal_row:
            return False, "Journal entry not found", None
        
        # Check workflow status
        if journal_row[2] != 'APPROVED':
            return False, f"Document not approved (status: {journal_row[2]})", None
        
        # Check if already posted
        if journal_row[8] is not None:  # posted_at
            return False, f"Document already posted on {journal_row[8]} by {journal_row[9]}", None
        
        # Check period controls
        fiscal_year = journal_row[4]
        period = journal_row[5]
        
        period_result = conn.execute(text("""
            SELECT period_status, allow_posting
            FROM fiscal_period_controls
            WHERE company_code = :cc AND fiscal_year = :fy AND posting_period = :period
        """), {"cc": company_code, "fy": fiscal_year, "period": period})
        
        period_row = period_result.fetchone()
        if not period_row:
            return False, f"Period {period}/{fiscal_year} not configured", None
        
        if period_row[0] != 'OPEN' or not period_row[1]:
            return False, f"Period {period}/{fiscal_year} is closed for posting", None
        
        # Check segregation of duties
        if posted_by == journal_row[7]:  # createdby
            return False, "Cannot post your own journal entry (Segregation of Duties)", None
        
        # Get journal lines for balance validation
        lines_result = conn.execute(text("""
            SELECT jel.linenumber, jel.glaccountid, jel.debitamount, jel.creditamount,
                   jel.description, jel.business_unit_code, jel.ledgerid, jel.currencycode
            FROM journalentryline jel
            WHERE jel.documentnumber = :doc AND jel.companycodeid = :cc
            ORDER BY jel.linenumber
        """), {"doc": journal_doc_number, "cc": company_code})
        
        lines = lines_result.fetchall()
        if not lines:
            return False, "No journal entry lines found", None
        
        # Validate document balance
        total_debit = sum(Decimal(line[2] or 0) for line in lines)
        total_credit = sum(Decimal(line[3] or 0) for line in lines)
        
        if total_debit != total_credit:
            return False, f"Document not balanced: Debits {total_debit} != Credits {total_credit}", None
        
        if total_debit == 0:
            return False, "Document has zero amount", None
        
        # Validate GL accounts exist and are posting-enabled
        for line in lines:
            gl_account = line[1]
            account_result = conn.execute(text("""
                SELECT glaccountid, accountname, accounttype
                FROM glaccount
                WHERE glaccountid = :account
            """), {"account": gl_account})
            
            if not account_result.fetchone():
                return False, f"GL Account {gl_account} does not exist", None
        
        # Package journal data for posting
        journal_data = {
            "header": {
                "document_number": journal_row[0],
                "company_code": journal_row[1],
                "posting_date": journal_row[3],
                "fiscal_year": journal_row[4],
                "period": journal_row[5],
                "currency_code": journal_row[6],
                "created_by": journal_row[7],
                "total_debit": total_debit,
                "total_credit": total_credit
            },
            "lines": [
                {
                    "line_number": line[0],
                    "gl_account": line[1],
                    "debit_amount": Decimal(line[2] or 0),
                    "credit_amount": Decimal(line[3] or 0),
                    "description": line[4],
                    "business_unit": line[5],
                    "ledger_id": line[6] or '0L',  # Default ledger
                    "currency_code": line[7]
                }
                for line in lines
            ]
        }
        
        return True, "Validation successful", journal_data
    
    @staticmethod
    def _create_posting_document(conn, journal_data: Dict, posted_by: str, posting_date: date) -> int:
        """Create posting document header"""
        
        header = journal_data["header"]
        
        result = conn.execute(text("""
            INSERT INTO posting_documents (
                company_code, document_number, fiscal_year, document_type,
                source_system, posting_date, document_date, document_currency,
                total_debit, total_credit, source_document, source_document_type,
                posted_by, posted_at
            ) VALUES (
                :company_code, :doc_number, :fiscal_year, 'SA',
                'GL', :posting_date, :posting_date, :currency,
                :total_debit, :total_credit, :source_doc, 'JE',
                :posted_by, CURRENT_TIMESTAMP
            ) RETURNING document_id
        """), {
            "company_code": header["company_code"],
            "doc_number": header["document_number"],
            "fiscal_year": header["fiscal_year"],
            "posting_date": posting_date,
            "currency": header["currency_code"],
            "total_debit": header["total_debit"],
            "total_credit": header["total_credit"],
            "source_doc": header["document_number"],
            "posted_by": posted_by
        })
        
        return result.fetchone()[0]
    
    @staticmethod
    def _create_gl_transactions(conn, document_id: int, journal_data: Dict, 
                               posted_by: str, posting_date: date):
        """Create individual GL transaction records"""
        
        header = journal_data["header"]
        
        for line in journal_data["lines"]:
            conn.execute(text("""
                INSERT INTO gl_transactions (
                    document_id, company_code, fiscal_year, document_number, line_item,
                    source_doc_number, source_doc_type, source_line_number,
                    gl_account, ledger_id, business_unit_id,
                    debit_amount, credit_amount, local_currency_amount,
                    document_currency, posting_date, document_date,
                    line_text, posting_period, posted_by, posted_at
                ) VALUES (
                    :doc_id, :company_code, :fiscal_year, :doc_number, :line_item,
                    :source_doc, 'JE', :source_line,
                    :gl_account, :ledger_id, :business_unit,
                    :debit_amount, :credit_amount, :local_amount,
                    :currency, :posting_date, :posting_date,
                    :line_text, :period, :posted_by, CURRENT_TIMESTAMP
                )
            """), {
                "doc_id": document_id,
                "company_code": header["company_code"],
                "fiscal_year": header["fiscal_year"],
                "doc_number": header["document_number"],
                "line_item": line["line_number"],
                "source_doc": header["document_number"],
                "source_line": line["line_number"],
                "gl_account": line["gl_account"],
                "ledger_id": line["ledger_id"],
                "business_unit": line["business_unit"],
                "debit_amount": line["debit_amount"] if line["debit_amount"] > 0 else None,
                "credit_amount": line["credit_amount"] if line["credit_amount"] > 0 else None,
                "local_amount": line["debit_amount"] - line["credit_amount"],
                "currency": line["currency_code"] or header["currency_code"] or 'USD',
                "posting_date": posting_date,
                "line_text": line["description"],
                "period": header["period"],
                "posted_by": posted_by
            })
    
    @staticmethod
    def _update_account_balances(conn, journal_data: Dict, posting_date: date):
        """Update GL account balances"""
        
        header = journal_data["header"]
        
        for line in journal_data["lines"]:
            # Insert or update account balance
            conn.execute(text("""
                INSERT INTO gl_account_balances (
                    company_code, gl_account, ledger_id, fiscal_year, posting_period,
                    beginning_balance, period_debits, period_credits, ending_balance,
                    ytd_debits, ytd_credits, ytd_balance, last_updated, last_posting_date,
                    transaction_count
                ) VALUES (
                    :company_code, :gl_account, :ledger_id, :fiscal_year, :period,
                    0, :debit_amount, :credit_amount, :debit_amount - :credit_amount,
                    :debit_amount, :credit_amount, :debit_amount - :credit_amount,
                    CURRENT_TIMESTAMP, :posting_date, 1
                )
                ON CONFLICT (company_code, gl_account, ledger_id, fiscal_year, posting_period)
                DO UPDATE SET
                    period_debits = gl_account_balances.period_debits + :debit_amount,
                    period_credits = gl_account_balances.period_credits + :credit_amount,
                    ending_balance = gl_account_balances.ending_balance + :debit_amount - :credit_amount,
                    ytd_debits = gl_account_balances.ytd_debits + :debit_amount,
                    ytd_credits = gl_account_balances.ytd_credits + :credit_amount,
                    ytd_balance = gl_account_balances.ytd_balance + :debit_amount - :credit_amount,
                    last_updated = CURRENT_TIMESTAMP,
                    last_posting_date = :posting_date,
                    transaction_count = gl_account_balances.transaction_count + 1
            """), {
                "company_code": header["company_code"],
                "gl_account": line["gl_account"],
                "ledger_id": line["ledger_id"],
                "fiscal_year": header["fiscal_year"],
                "period": header["period"],
                "debit_amount": line["debit_amount"],
                "credit_amount": line["credit_amount"],
                "posting_date": posting_date
            })
    
    @staticmethod
    def _update_journal_entry_status(conn, journal_doc_number: str, company_code: str, posted_by: str, posting_date: date = None):
        """Update journal entry status to POSTED"""
        
        if posting_date is None:
            posting_date = date.today()
        
        conn.execute(text("""
            UPDATE journalentryheader 
            SET workflow_status = 'POSTED',
                postingdate = :posting_date,
                posted_at = CURRENT_TIMESTAMP,
                posted_by = :posted_by
            WHERE documentnumber = :doc AND companycodeid = :cc
        """), {
            "doc": journal_doc_number,
            "cc": company_code,
            "posted_by": posted_by,
            "posting_date": posting_date
        })
    
    @staticmethod
    def _create_posting_audit_trail(conn, document_id: int, journal_data: Dict, 
                                   posted_by: str, posting_date: date):
        """Create audit trail entry for posting"""
        
        header = journal_data["header"]
        
        conn.execute(text("""
            INSERT INTO posting_audit_trail (
                document_id, source_document, company_code, action_type,
                action_by, fiscal_year, posting_period, posting_date,
                total_amount, action_status
            ) VALUES (
                :doc_id, :source_doc, :company_code, 'POST',
                :posted_by, :fiscal_year, :period, :posting_date,
                :total_amount, 'SUCCESS'
            )
        """), {
            "doc_id": document_id,
            "source_doc": header["document_number"],
            "company_code": header["company_code"],
            "posted_by": posted_by,
            "fiscal_year": header["fiscal_year"],
            "period": header["period"],
            "posting_date": posting_date,
            "total_amount": header["total_debit"]
        })
    
    @staticmethod
    def get_posting_eligible_documents(company_code: str = None) -> List[Dict]:
        """Get list of documents eligible for posting"""
        
        try:
            with engine.connect() as conn:
                where_clause = "WHERE jeh.workflow_status = 'APPROVED' AND jeh.posted_at IS NULL"
                params = {}
                
                if company_code:
                    where_clause += " AND jeh.companycodeid = :company_code"
                    params["company_code"] = company_code
                
                result = conn.execute(text(f"""
                    SELECT jeh.documentnumber, jeh.companycodeid, jeh.postingdate,
                           jeh.fiscalyear, jeh.period, jeh.reference, jeh.createdby,
                           jeh.approved_by, jeh.approved_at,
                           COALESCE(SUM(GREATEST(jel.debitamount, jel.creditamount)), 0) as total_amount
                    FROM journalentryheader jeh
                    LEFT JOIN journalentryline jel ON jel.documentnumber = jeh.documentnumber 
                        AND jel.companycodeid = jeh.companycodeid
                    {where_clause}
                    GROUP BY jeh.documentnumber, jeh.companycodeid, jeh.postingdate,
                             jeh.fiscalyear, jeh.period, jeh.reference, jeh.createdby,
                             jeh.approved_by, jeh.approved_at
                    ORDER BY jeh.approved_at DESC
                """), params)
                
                return [
                    {
                        "document_number": row[0],
                        "company_code": row[1],
                        "posting_date": row[2],
                        "fiscal_year": row[3],
                        "period": row[4],
                        "reference": row[5],
                        "created_by": row[6],
                        "approved_by": row[7],
                        "approved_at": row[8],
                        "total_amount": float(row[9])
                    }
                    for row in result
                ]
                
        except Exception as e:
            logger.error(f"Error getting posting eligible documents: {e}")
            return []
    
    @staticmethod
    def get_account_balance(company_code: str, gl_account: str, ledger_id: str = '0L',
                           fiscal_year: int = None, period: int = None) -> Dict:
        """Get current account balance"""
        
        try:
            with engine.connect() as conn:
                if fiscal_year is None:
                    fiscal_year = datetime.now().year
                if period is None:
                    period = datetime.now().month
                
                result = conn.execute(text("""
                    SELECT beginning_balance, period_debits, period_credits, ending_balance,
                           ytd_debits, ytd_credits, ytd_balance, last_posting_date,
                           transaction_count
                    FROM gl_account_balances
                    WHERE company_code = :cc AND gl_account = :account 
                    AND ledger_id = :ledger AND fiscal_year = :fy AND posting_period = :period
                """), {
                    "cc": company_code,
                    "account": gl_account,
                    "ledger": ledger_id,
                    "fy": fiscal_year,
                    "period": period
                })
                
                row = result.fetchone()
                if row:
                    return {
                        "beginning_balance": float(row[0] or 0),
                        "period_debits": float(row[1] or 0),
                        "period_credits": float(row[2] or 0),
                        "ending_balance": float(row[3] or 0),
                        "ytd_debits": float(row[4] or 0),
                        "ytd_credits": float(row[5] or 0),
                        "ytd_balance": float(row[6] or 0),
                        "last_posting_date": row[7],
                        "transaction_count": row[8] or 0
                    }
                else:
                    return {
                        "beginning_balance": 0.0,
                        "period_debits": 0.0,
                        "period_credits": 0.0,
                        "ending_balance": 0.0,
                        "ytd_debits": 0.0,
                        "ytd_credits": 0.0,
                        "ytd_balance": 0.0,
                        "last_posting_date": None,
                        "transaction_count": 0
                    }
                    
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return {}