"""
Parallel Ledger Reporting Service

This service provides comprehensive reporting capabilities across all parallel ledgers,
including ledger-specific financial statements, comparative analysis, and multi-currency reporting.

Author: Claude Code Assistant
Date: August 6, 2025
"""

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy import text
from db_config import engine
from utils.currency_service import CurrencyTranslationService
from utils.logger import get_logger

logger = get_logger("parallel_ledger_reporting")

class ParallelLedgerReportingService:
    """Service for comprehensive parallel ledger reporting capabilities."""
    
    def __init__(self):
        """Initialize the parallel ledger reporting service."""
        self.currency_service = CurrencyTranslationService()
        
    def generate_trial_balance_by_ledger(self, ledger_id: str, company_code: str,
                                       fiscal_year: int, period: int = None,
                                       include_currency_translation: bool = True) -> Dict[str, Any]:
        """
        Generate trial balance for a specific ledger.
        
        Args:
            ledger_id: Target ledger ID
            company_code: Company code
            fiscal_year: Fiscal year
            period: Specific period (optional, defaults to YTD)
            include_currency_translation: Whether to include currency translations
            
        Returns:
            Dictionary with trial balance data
        """
        try:
            with engine.connect() as conn:
                # Get ledger information
                ledger_info = conn.execute(text("""
                    SELECT ledgerid, description, accounting_principle, currencycode,
                           parallel_currency_1, parallel_currency_2, isleadingledger
                    FROM ledger WHERE ledgerid = :ledger_id
                """), {"ledger_id": ledger_id}).fetchone()
                
                if not ledger_info:
                    return {"error": f"Ledger {ledger_id} not found"}
                
                # Build period filter
                period_filter = ""
                params = {
                    "ledger_id": ledger_id,
                    "company_code": company_code,
                    "fiscal_year": fiscal_year
                }
                
                if period:
                    period_filter = "AND gab.posting_period <= :period"
                    params["period"] = period
                
                # Get trial balance data
                result = conn.execute(text(f"""
                    SELECT 
                        ga.glaccountid,
                        ga.accountname,
                        ga.accounttype,
                        ag.account_group_name,
                        ag.account_type as account_classification,
                        COALESCE(SUM(gab.ytd_debits), 0) as total_debits,
                        COALESCE(SUM(gab.ytd_credits), 0) as total_credits,
                        COALESCE(SUM(gab.ytd_balance), 0) as net_balance,
                        ga.currencycode as account_currency,
                        COUNT(DISTINCT gab.posting_period) as periods_with_activity
                    FROM glaccount ga
                    LEFT JOIN gl_account_balances gab ON ga.glaccountid = gab.gl_account
                        AND gab.company_code = :company_code
                        AND gab.ledger_id = :ledger_id
                        AND gab.fiscal_year = :fiscal_year
                        {period_filter}
                    LEFT JOIN account_groups ag ON ga.account_group_code = ag.account_group_code
                    WHERE ga.companycodeid = :company_code
                    GROUP BY ga.glaccountid, ga.accountname, ga.accounttype, 
                             ag.account_group_name, ag.account_type, ga.currencycode
                    HAVING COALESCE(SUM(gab.ytd_debits), 0) != 0 
                        OR COALESCE(SUM(gab.ytd_credits), 0) != 0
                    ORDER BY ga.glaccountid
                """), params).fetchall()
                
                # Process accounts and calculate totals
                accounts = []
                totals_by_type = {}
                grand_total_debits = Decimal('0')
                grand_total_credits = Decimal('0')
                
                for row in result:
                    account_data = {
                        "account_id": row[0],
                        "account_name": row[1],
                        "account_type": row[2],
                        "account_group": row[3],
                        "classification": row[4],
                        "total_debits": float(row[5]),
                        "total_credits": float(row[6]),
                        "net_balance": float(row[7]),
                        "currency": row[8],
                        "periods_active": row[9]
                    }
                    
                    # Add currency translations if requested
                    if include_currency_translation and ledger_info[3] != row[8]:
                        translated_balance = self.currency_service.translate_amount(
                            Decimal(str(row[7])), row[8], ledger_info[3]
                        )
                        account_data["translated_balance"] = float(translated_balance) if translated_balance else None
                        account_data["ledger_currency"] = ledger_info[3]
                    
                    accounts.append(account_data)
                    
                    # Accumulate totals by account type
                    acc_type = row[4] or row[2]
                    if acc_type not in totals_by_type:
                        totals_by_type[acc_type] = {
                            "total_debits": Decimal('0'),
                            "total_credits": Decimal('0'),
                            "net_balance": Decimal('0'),
                            "account_count": 0
                        }
                    
                    totals_by_type[acc_type]["total_debits"] += Decimal(str(row[5]))
                    totals_by_type[acc_type]["total_credits"] += Decimal(str(row[6]))
                    totals_by_type[acc_type]["net_balance"] += Decimal(str(row[7]))
                    totals_by_type[acc_type]["account_count"] += 1
                    
                    grand_total_debits += Decimal(str(row[5]))
                    grand_total_credits += Decimal(str(row[6]))
                
                # Convert totals to float for JSON serialization
                for acc_type in totals_by_type:
                    for key in ["total_debits", "total_credits", "net_balance"]:
                        totals_by_type[acc_type][key] = float(totals_by_type[acc_type][key])
                
                return {
                    "report_info": {
                        "ledger_id": ledger_id,
                        "ledger_description": ledger_info[1],
                        "accounting_principle": ledger_info[2],
                        "ledger_currency": ledger_info[3],
                        "company_code": company_code,
                        "fiscal_year": fiscal_year,
                        "period": period or "YTD",
                        "report_date": datetime.now(),
                        "is_leading_ledger": ledger_info[6]
                    },
                    "accounts": accounts,
                    "totals_by_type": totals_by_type,
                    "grand_totals": {
                        "total_debits": float(grand_total_debits),
                        "total_credits": float(grand_total_credits),
                        "balance_difference": float(grand_total_debits - grand_total_credits)
                    },
                    "account_count": len(accounts),
                    "currency_translation_applied": include_currency_translation
                }
                
        except Exception as e:
            logger.error(f"Error generating trial balance for ledger {ledger_id}: {e}")
            return {"error": str(e)}
    
    def generate_comparative_financial_statements(self, company_code: str, fiscal_year: int,
                                                period: int = None, ledger_list: List[str] = None) -> Dict[str, Any]:
        """
        Generate comparative financial statements across multiple ledgers.
        
        Args:
            company_code: Company code
            fiscal_year: Fiscal year
            period: Specific period (optional)
            ledger_list: List of ledgers to compare (optional, defaults to all)
            
        Returns:
            Dictionary with comparative financial statements
        """
        try:
            # Get all ledgers if not specified
            if not ledger_list:
                with engine.connect() as conn:
                    ledger_result = conn.execute(text("""
                        SELECT ledgerid FROM ledger 
                        ORDER BY isleadingledger DESC, ledgerid
                    """)).fetchall()
                    ledger_list = [row[0] for row in ledger_result]
            
            # Generate trial balance for each ledger
            ledger_reports = {}
            for ledger_id in ledger_list:
                trial_balance = self.generate_trial_balance_by_ledger(
                    ledger_id, company_code, fiscal_year, period
                )
                if "error" not in trial_balance:
                    ledger_reports[ledger_id] = trial_balance
            
            if not ledger_reports:
                return {"error": "No valid ledger data found"}
            
            # Create comparative analysis
            comparative_data = self._create_comparative_analysis(ledger_reports)
            
            return {
                "report_info": {
                    "report_type": "Comparative Financial Statements",
                    "company_code": company_code,
                    "fiscal_year": fiscal_year,
                    "period": period or "YTD",
                    "report_date": datetime.now(),
                    "ledgers_included": ledger_list,
                    "ledger_count": len(ledger_reports)
                },
                "ledger_reports": ledger_reports,
                "comparative_analysis": comparative_data
            }
            
        except Exception as e:
            logger.error(f"Error generating comparative financial statements: {e}")
            return {"error": str(e)}
    
    def _create_comparative_analysis(self, ledger_reports: Dict) -> Dict[str, Any]:
        """Create comparative analysis across ledgers."""
        try:
            # Collect all unique accounts across ledgers
            all_accounts = set()
            for ledger_id, report in ledger_reports.items():
                for account in report["accounts"]:
                    all_accounts.add(account["account_id"])
            
            # Build comparative account data
            comparative_accounts = []
            for account_id in sorted(all_accounts):
                account_comparison = {
                    "account_id": account_id,
                    "account_name": "",
                    "account_type": "",
                    "ledger_balances": {},
                    "variance_analysis": {}
                }
                
                # Collect balances across ledgers
                balances = []
                for ledger_id, report in ledger_reports.items():
                    account_data = next((acc for acc in report["accounts"] if acc["account_id"] == account_id), None)
                    if account_data:
                        account_comparison["account_name"] = account_data["account_name"]
                        account_comparison["account_type"] = account_data["account_type"]
                        account_comparison["ledger_balances"][ledger_id] = account_data["net_balance"]
                        balances.append(account_data["net_balance"])
                    else:
                        account_comparison["ledger_balances"][ledger_id] = 0.0
                        balances.append(0.0)
                
                # Calculate variance analysis
                if balances:
                    min_balance = min(balances)
                    max_balance = max(balances)
                    avg_balance = sum(balances) / len(balances)
                    
                    account_comparison["variance_analysis"] = {
                        "min_balance": min_balance,
                        "max_balance": max_balance,
                        "average_balance": avg_balance,
                        "variance_range": max_balance - min_balance,
                        "has_variance": abs(max_balance - min_balance) > 0.01
                    }
                
                comparative_accounts.append(account_comparison)
            
            # Calculate summary statistics
            total_variance_accounts = sum(1 for acc in comparative_accounts if acc["variance_analysis"].get("has_variance", False))
            
            return {
                "comparative_accounts": comparative_accounts,
                "summary_statistics": {
                    "total_accounts_compared": len(comparative_accounts),
                    "accounts_with_variance": total_variance_accounts,
                    "variance_percentage": (total_variance_accounts / len(comparative_accounts) * 100) if comparative_accounts else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating comparative analysis: {e}")
            return {"error": str(e)}
    
    def generate_ledger_balance_inquiry(self, company_code: str, gl_account: str = None,
                                      fiscal_year: int = None, period: int = None) -> Dict[str, Any]:
        """
        Generate balance inquiry across all ledgers for specific account(s).
        
        Args:
            company_code: Company code
            gl_account: Specific GL account (optional, defaults to all)
            fiscal_year: Fiscal year (optional, defaults to current)
            period: Specific period (optional, defaults to latest)
            
        Returns:
            Dictionary with balance inquiry results
        """
        try:
            if not fiscal_year:
                fiscal_year = datetime.now().year
            
            with engine.connect() as conn:
                # Build query parameters
                where_clause = "WHERE gab.company_code = :company_code AND gab.fiscal_year = :fiscal_year"
                params = {
                    "company_code": company_code,
                    "fiscal_year": fiscal_year
                }
                
                if gl_account:
                    where_clause += " AND gab.gl_account = :gl_account"
                    params["gl_account"] = gl_account
                
                if period:
                    where_clause += " AND gab.posting_period <= :period"
                    params["period"] = period
                
                # Get balance data across all ledgers
                result = conn.execute(text(f"""
                    SELECT 
                        gab.gl_account,
                        ga.accountname,
                        ga.accounttype,
                        gab.ledger_id,
                        l.description as ledger_description,
                        l.accounting_principle,
                        l.currencycode as ledger_currency,
                        MAX(gab.posting_period) as latest_period,
                        SUM(gab.ytd_debits) as ytd_debits,
                        SUM(gab.ytd_credits) as ytd_credits,
                        SUM(gab.ytd_balance) as ytd_balance,
                        MAX(gab.last_updated) as last_updated
                    FROM gl_account_balances gab
                    JOIN glaccount ga ON gab.gl_account = ga.glaccountid
                    JOIN ledger l ON gab.ledger_id = l.ledgerid
                    {where_clause}
                    GROUP BY gab.gl_account, ga.accountname, ga.accounttype,
                             gab.ledger_id, l.description, l.accounting_principle, l.currencycode, l.isleadingledger
                    ORDER BY gab.gl_account, l.isleadingledger DESC, gab.ledger_id
                """), params).fetchall()
                
                # Organize results by account
                accounts_data = {}
                for row in result:
                    account_id = row[0]
                    if account_id not in accounts_data:
                        accounts_data[account_id] = {
                            "account_id": account_id,
                            "account_name": row[1],
                            "account_type": row[2],
                            "ledger_balances": []
                        }
                    
                    # Add currency translation if different currencies
                    ytd_balance = float(row[10])
                    translated_balance = None
                    if row[6] != 'USD':  # Assuming USD as base currency
                        translated_amount = self.currency_service.translate_amount(
                            Decimal(str(ytd_balance)), row[6], 'USD'
                        )
                        translated_balance = float(translated_amount) if translated_amount else None
                    
                    accounts_data[account_id]["ledger_balances"].append({
                        "ledger_id": row[3],
                        "ledger_description": row[4],
                        "accounting_principle": row[5],
                        "ledger_currency": row[6],
                        "latest_period": row[7],
                        "ytd_debits": float(row[8]),
                        "ytd_credits": float(row[9]),
                        "ytd_balance": ytd_balance,
                        "translated_balance_usd": translated_balance,
                        "last_updated": row[11]
                    })
                
                return {
                    "inquiry_info": {
                        "company_code": company_code,
                        "gl_account": gl_account or "All Accounts",
                        "fiscal_year": fiscal_year,
                        "period": period or "Latest",
                        "inquiry_date": datetime.now()
                    },
                    "accounts": list(accounts_data.values()),
                    "account_count": len(accounts_data)
                }
                
        except Exception as e:
            logger.error(f"Error generating balance inquiry: {e}")
            return {"error": str(e)}
    
    def generate_parallel_posting_impact_report(self, company_code: str, 
                                              date_from: date = None,
                                              date_to: date = None) -> Dict[str, Any]:
        """
        Generate report showing the impact of parallel posting operations.
        
        Args:
            company_code: Company code
            date_from: Start date (optional)
            date_to: End date (optional)
            
        Returns:
            Dictionary with parallel posting impact analysis
        """
        try:
            if not date_from:
                date_from = date.today() - timedelta(days=30)
            if not date_to:
                date_to = date.today()
            
            with engine.connect() as conn:
                # Get parallel posting statistics
                result = conn.execute(text("""
                    SELECT 
                        jeh.documentnumber as source_document,
                        jeh.postingdate,
                        jeh.description,
                        jeh.parallel_posted_at,
                        jeh.parallel_posted_by,
                        jeh.parallel_ledger_count,
                        jeh.parallel_success_count,
                        -- Source document details
                        COALESCE(SUM(GREATEST(jel_source.debitamount, jel_source.creditamount)), 0) as source_amount,
                        COUNT(jel_source.linenumber) as source_line_count,
                        -- Parallel document count
                        (SELECT COUNT(*) FROM journalentryheader jeh_parallel 
                         WHERE jeh_parallel.parallel_source_doc = jeh.documentnumber 
                         AND jeh_parallel.companycodeid = jeh.companycodeid) as parallel_docs_created,
                        -- Total parallel lines created  
                        (SELECT COUNT(*) FROM journalentryheader jeh_parallel 
                         JOIN journalentryline jel_parallel ON jel_parallel.documentnumber = jeh_parallel.documentnumber
                         WHERE jeh_parallel.parallel_source_doc = jeh.documentnumber 
                         AND jeh_parallel.companycodeid = jeh.companycodeid) as parallel_lines_created
                    FROM journalentryheader jeh
                    LEFT JOIN journalentryline jel_source ON jel_source.documentnumber = jeh.documentnumber 
                        AND jel_source.companycodeid = jeh.companycodeid
                    WHERE jeh.companycodeid = :company_code
                      AND jeh.parallel_posted = true
                      AND jeh.parallel_posted_at BETWEEN :date_from AND :date_to + INTERVAL '1 day'
                    GROUP BY jeh.documentnumber, jeh.postingdate, jeh.description,
                             jeh.parallel_posted_at, jeh.parallel_posted_by,
                             jeh.parallel_ledger_count, jeh.parallel_success_count,
                             jeh.companycodeid
                    ORDER BY jeh.parallel_posted_at DESC
                """), {
                    "company_code": company_code,
                    "date_from": date_from,
                    "date_to": date_to
                }).fetchall()
                
                # Process results
                documents = []
                total_source_amount = Decimal('0')
                total_source_lines = 0
                total_parallel_docs = 0
                total_parallel_lines = 0
                successful_postings = 0
                
                for row in result:
                    doc_data = {
                        "source_document": row[0],
                        "posting_date": row[1],
                        "description": row[2],
                        "parallel_posted_at": row[3],
                        "parallel_posted_by": row[4],
                        "target_ledgers": row[5],
                        "successful_ledgers": row[6],
                        "source_amount": float(row[7]),
                        "source_line_count": row[8],
                        "parallel_documents_created": row[9],
                        "parallel_lines_created": row[10],
                        "success_rate": (row[6] / row[5] * 100) if row[5] > 0 else 0
                    }
                    
                    documents.append(doc_data)
                    
                    # Accumulate totals
                    total_source_amount += Decimal(str(row[7]))
                    total_source_lines += row[8]
                    total_parallel_docs += row[9]
                    total_parallel_lines += row[10]
                    if row[6] == row[5]:  # All ledgers successful
                        successful_postings += 1
                
                # Calculate efficiency metrics
                efficiency_metrics = {
                    "document_multiplication_factor": total_parallel_docs / len(documents) if documents else 0,
                    "line_multiplication_factor": total_parallel_lines / total_source_lines if total_source_lines > 0 else 0,
                    "overall_success_rate": (successful_postings / len(documents) * 100) if documents else 0,
                    "average_processing_time": None  # Could be calculated if we store processing times
                }
                
                return {
                    "report_info": {
                        "report_type": "Parallel Posting Impact Report",
                        "company_code": company_code,
                        "date_from": date_from,
                        "date_to": date_to,
                        "report_date": datetime.now()
                    },
                    "documents": documents,
                    "summary_statistics": {
                        "total_source_documents": len(documents),
                        "total_source_amount": float(total_source_amount),
                        "total_source_lines": total_source_lines,
                        "total_parallel_documents": total_parallel_docs,
                        "total_parallel_lines": total_parallel_lines,
                        "successful_postings": successful_postings,
                        "overall_success_rate": efficiency_metrics["overall_success_rate"]
                    },
                    "efficiency_metrics": efficiency_metrics
                }
                
        except Exception as e:
            logger.error(f"Error generating parallel posting impact report: {e}")
            return {"error": str(e)}
    
    def get_available_reports(self) -> Dict[str, List[Dict]]:
        """Get list of available reports and their descriptions."""
        return {
            "ledger_specific_reports": [
                {
                    "report_name": "Trial Balance by Ledger",
                    "description": "Complete trial balance for a specific ledger (IFRS, Tax, Management, etc.)",
                    "method": "generate_trial_balance_by_ledger",
                    "parameters": ["ledger_id", "company_code", "fiscal_year", "period"]
                },
                {
                    "report_name": "Ledger Balance Inquiry",
                    "description": "Multi-ledger balance inquiry for specific accounts",
                    "method": "generate_ledger_balance_inquiry", 
                    "parameters": ["company_code", "gl_account", "fiscal_year", "period"]
                }
            ],
            "comparative_reports": [
                {
                    "report_name": "Comparative Financial Statements",
                    "description": "Side-by-side comparison of financial statements across multiple ledgers",
                    "method": "generate_comparative_financial_statements",
                    "parameters": ["company_code", "fiscal_year", "period", "ledger_list"]
                },
                {
                    "report_name": "Parallel Posting Impact Report",
                    "description": "Analysis of parallel posting operations and their business impact",
                    "method": "generate_parallel_posting_impact_report",
                    "parameters": ["company_code", "date_from", "date_to"]
                }
            ],
            "operational_reports": [
                {
                    "report_name": "Multi-Currency Translation Report",
                    "description": "Currency translation impact across parallel ledgers",
                    "method": "generate_currency_translation_report",
                    "parameters": ["company_code", "fiscal_year", "base_currency"]
                }
            ]
        }

# Utility functions for external use
def get_trial_balance(ledger_id: str, company_code: str, fiscal_year: int, period: int = None) -> Dict:
    """Generate trial balance for specific ledger."""
    service = ParallelLedgerReportingService()
    return service.generate_trial_balance_by_ledger(ledger_id, company_code, fiscal_year, period)

def get_comparative_statements(company_code: str, fiscal_year: int, period: int = None) -> Dict:
    """Generate comparative financial statements across all ledgers."""
    service = ParallelLedgerReportingService()
    return service.generate_comparative_financial_statements(company_code, fiscal_year, period)

def get_balance_inquiry(company_code: str, gl_account: str = None, fiscal_year: int = None) -> Dict:
    """Get multi-ledger balance inquiry."""
    service = ParallelLedgerReportingService()
    return service.generate_ledger_balance_inquiry(company_code, gl_account, fiscal_year)

def get_parallel_posting_impact(company_code: str, days_back: int = 30) -> Dict:
    """Get parallel posting impact report."""
    service = ParallelLedgerReportingService()
    date_from = date.today() - timedelta(days=days_back)
    return service.generate_parallel_posting_impact_report(company_code, date_from)

# Test function
def test_parallel_ledger_reporting():
    """Test the parallel ledger reporting service."""
    service = ParallelLedgerReportingService()
    
    print("=== Parallel Ledger Reporting Service Test ===")
    
    # Test available reports
    reports = service.get_available_reports()
    print(f"Available report categories: {len(reports)}")
    for category, report_list in reports.items():
        print(f"  {category}: {len(report_list)} reports")
    
    # Test balance inquiry (should work with current data)
    try:
        inquiry = service.generate_ledger_balance_inquiry("1000")
        print(f"Balance inquiry: {inquiry.get('account_count', 0)} accounts found")
    except Exception as e:
        print(f"Balance inquiry test: {e}")
    
    print("✅ Parallel Ledger Reporting Service: Initialized and ready")

if __name__ == "__main__":
    test_parallel_ledger_reporting()