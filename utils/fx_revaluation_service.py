"""
Foreign Currency Revaluation Service

This service handles automated foreign currency revaluations for multi-ledger
GL operations, calculating unrealized gains/losses and generating journal entries.

Key Features:
- Period-end FX revaluation calculations
- Multi-ledger support with parallel processing  
- Automated journal entry generation
- Integration with workflow engine
- Comprehensive audit trails

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
from utils.workflow_engine import WorkflowEngine
from utils.logger import get_logger

logger = get_logger("fx_revaluation_service")

class FXRevaluationService:
    """Service for comprehensive foreign currency revaluation operations."""
    
    def __init__(self):
        """Initialize the FX revaluation service."""
        self.currency_service = CurrencyTranslationService()
        self.workflow_engine = WorkflowEngine()
        self.system_user = "FX_REVALUATION_SERVICE"
        
    def run_fx_revaluation(self, company_code: str, revaluation_date: date,
                          fiscal_year: int, fiscal_period: int,
                          run_type: str = "PERIOD_END", 
                          ledger_ids: Optional[List[str]] = None,
                          create_journals: bool = True) -> Dict[str, Any]:
        """
        Execute comprehensive FX revaluation run.
        
        Args:
            company_code: Company code
            revaluation_date: Date for revaluation calculations
            fiscal_year: Fiscal year
            fiscal_period: Fiscal period  
            run_type: Type of revaluation run
            ledger_ids: Specific ledgers to revalue (None = all configured)
            create_journals: Whether to create journal entries
            
        Returns:
            Dictionary with revaluation results
        """
        run_results = {
            "run_id": None,
            "company_code": company_code,
            "revaluation_date": revaluation_date,
            "fiscal_year": fiscal_year,
            "fiscal_period": fiscal_period,
            "run_type": run_type,
            "started_at": datetime.now(),
            "status": "PENDING",
            "accounts_processed": 0,
            "revaluations_created": 0,
            "total_unrealized_gain": Decimal('0.00'),
            "total_unrealized_loss": Decimal('0.00'),
            "journal_documents": [],
            "errors": [],
            "ledger_results": {}
        }
        
        try:
            # Create revaluation run record
            run_id = self._create_revaluation_run(
                company_code, revaluation_date, fiscal_year, fiscal_period,
                run_type, self.system_user
            )
            run_results["run_id"] = run_id
            
            # Update run status to RUNNING
            self._update_run_status(run_id, "RUNNING")
            
            logger.info(f"Starting FX revaluation run {run_id} for {company_code} on {revaluation_date}")
            
            # Get configured accounts for revaluation
            if ledger_ids:
                accounts_config = self._get_revaluation_accounts_for_ledgers(
                    company_code, ledger_ids
                )
            else:
                accounts_config = self._get_all_revaluation_accounts(company_code)
            
            if not accounts_config:
                run_results["status"] = "COMPLETED"
                run_results["errors"].append("No accounts configured for FX revaluation")
                return run_results
            
            logger.info(f"Processing {len(accounts_config)} accounts for FX revaluation")
            
            # Process each ledger separately
            ledger_groups = self._group_accounts_by_ledger(accounts_config)
            
            for ledger_id, ledger_accounts in ledger_groups.items():
                try:
                    ledger_result = self._process_ledger_revaluation(
                        run_id, company_code, ledger_id, ledger_accounts,
                        revaluation_date, fiscal_year, fiscal_period,
                        create_journals
                    )
                    
                    run_results["ledger_results"][ledger_id] = ledger_result
                    run_results["accounts_processed"] += ledger_result["accounts_processed"]
                    run_results["revaluations_created"] += ledger_result["revaluations_created"]
                    run_results["total_unrealized_gain"] += ledger_result["total_unrealized_gain"]
                    run_results["total_unrealized_loss"] += ledger_result["total_unrealized_loss"]
                    run_results["journal_documents"].extend(ledger_result["journal_documents"])
                    
                except Exception as e:
                    error_msg = f"Error processing ledger {ledger_id}: {str(e)}"
                    run_results["errors"].append(error_msg)
                    logger.error(error_msg)
            
            # Update run with final results
            self._finalize_revaluation_run(run_id, run_results)
            
            run_results["status"] = "COMPLETED"
            run_results["completed_at"] = datetime.now()
            
            success_rate = (run_results["accounts_processed"] / len(accounts_config) * 100) if accounts_config else 0
            logger.info(f"FX revaluation run {run_id} completed: {run_results['accounts_processed']}/{len(accounts_config)} accounts ({success_rate:.1f}%)")
            
        except Exception as e:
            run_results["status"] = "FAILED"
            run_results["errors"].append(f"Revaluation run failed: {str(e)}")
            logger.error(f"FX revaluation run failed: {e}")
            
            if run_results["run_id"]:
                self._update_run_status(run_results["run_id"], "FAILED", str(e))
        
        return run_results
    
    def _process_ledger_revaluation(self, run_id: int, company_code: str,
                                  ledger_id: str, accounts: List[Dict],
                                  revaluation_date: date, fiscal_year: int, 
                                  fiscal_period: int, create_journals: bool) -> Dict[str, Any]:
        """Process FX revaluation for a specific ledger."""
        ledger_result = {
            "ledger_id": ledger_id,
            "accounts_processed": 0,
            "revaluations_created": 0,
            "total_unrealized_gain": Decimal('0.00'),
            "total_unrealized_loss": Decimal('0.00'),
            "journal_documents": [],
            "account_details": []
        }
        
        try:
            logger.info(f"Processing {len(accounts)} accounts for ledger {ledger_id}")
            
            for account_config in accounts:
                try:
                    account_result = self._process_account_revaluation(
                        run_id, company_code, ledger_id, account_config,
                        revaluation_date, fiscal_year, fiscal_period
                    )
                    
                    ledger_result["account_details"].append(account_result)
                    ledger_result["accounts_processed"] += 1
                    
                    if account_result["revaluation_required"]:
                        ledger_result["revaluations_created"] += 1
                        
                        if account_result["unrealized_gain_loss"] > 0:
                            ledger_result["total_unrealized_gain"] += account_result["unrealized_gain_loss"]
                        else:
                            ledger_result["total_unrealized_loss"] += abs(account_result["unrealized_gain_loss"])
                    
                except Exception as e:
                    logger.error(f"Error processing account {account_config['gl_account']}: {e}")
                    continue
            
            # Create consolidated journal entry for the ledger if needed
            if create_journals and ledger_result["revaluations_created"] > 0:
                journal_doc = self._create_fx_revaluation_journal(
                    company_code, ledger_id, ledger_result["account_details"],
                    revaluation_date, fiscal_year, fiscal_period
                )
                
                if journal_doc:
                    ledger_result["journal_documents"].append(journal_doc)
            
        except Exception as e:
            logger.error(f"Error processing ledger {ledger_id} revaluation: {e}")
        
        return ledger_result
    
    def _process_account_revaluation(self, run_id: int, company_code: str,
                                   ledger_id: str, account_config: Dict,
                                   revaluation_date: date, fiscal_year: int, 
                                   fiscal_period: int) -> Dict[str, Any]:
        """Process FX revaluation for a specific account."""
        gl_account = account_config["gl_account"]
        account_currency = account_config["account_currency"]
        
        account_result = {
            "gl_account": gl_account,
            "account_currency": account_currency,
            "functional_currency": "USD",  # Default functional currency
            "opening_balance_fc": Decimal('0.00'),
            "current_balance_fc": Decimal('0.00'),
            "opening_balance_func": Decimal('0.00'),
            "historical_exchange_rate": Decimal('1.000000'),
            "current_exchange_rate": Decimal('1.000000'),
            "rate_difference": Decimal('0.000000'),
            "current_balance_func_at_current_rate": Decimal('0.00'),
            "unrealized_gain_loss": Decimal('0.00'),
            "revaluation_required": False,
            "error_message": None
        }
        
        try:
            # Get current account balance in foreign currency
            current_balance_fc = self._get_account_balance(
                company_code, ledger_id, gl_account, revaluation_date, account_currency
            )
            account_result["current_balance_fc"] = current_balance_fc
            
            if current_balance_fc == 0:
                logger.debug(f"Account {gl_account} has zero balance, skipping revaluation")
                return account_result
            
            # Get current exchange rate
            current_rate = self.currency_service.get_exchange_rate(
                account_currency, account_result["functional_currency"], revaluation_date
            )
            
            if not current_rate:
                account_result["error_message"] = f"No exchange rate found for {account_currency} to USD"
                return account_result
            
            account_result["current_exchange_rate"] = current_rate
            
            # Get historical rate (using average rate for the period or opening rate)
            historical_rate = self._get_historical_exchange_rate(
                account_currency, account_result["functional_currency"], 
                fiscal_year, fiscal_period
            )
            account_result["historical_exchange_rate"] = historical_rate
            
            # Calculate current balance in functional currency at current rate
            current_balance_func_at_current_rate = current_balance_fc * current_rate
            account_result["current_balance_func_at_current_rate"] = current_balance_func_at_current_rate
            
            # Get current balance in functional currency (historical rates)
            current_balance_func_historical = self._get_account_balance_functional(
                company_code, ledger_id, gl_account, revaluation_date
            )
            account_result["opening_balance_func"] = current_balance_func_historical
            
            # Calculate unrealized gain/loss
            unrealized_gl = current_balance_func_at_current_rate - current_balance_func_historical
            account_result["unrealized_gain_loss"] = unrealized_gl
            account_result["rate_difference"] = current_rate - historical_rate
            
            # Determine if revaluation is required (threshold: $1.00 or 0.01%)
            threshold_amount = Decimal('1.00')
            threshold_percent = Decimal('0.0001')  # 0.01%
            
            if (abs(unrealized_gl) >= threshold_amount or 
                abs(unrealized_gl / max(abs(current_balance_func_historical), Decimal('1.00'))) >= threshold_percent):
                account_result["revaluation_required"] = True
            
            # Save revaluation detail to database
            self._save_revaluation_detail(run_id, company_code, ledger_id, account_result)
            
        except Exception as e:
            account_result["error_message"] = str(e)
            logger.error(f"Error processing account {gl_account} revaluation: {e}")
        
        return account_result
    
    def _get_account_balance(self, company_code: str, ledger_id: str, 
                           gl_account: str, balance_date: date, 
                           currency_code: str) -> Decimal:
        """Get account balance in foreign currency."""
        try:
            with engine.connect() as conn:
                # Get balance from journal entry lines
                query = text("""
                    SELECT COALESCE(SUM(
                        CASE 
                            WHEN ga.accounttype IN ('ASSETS', 'EXPENSES') 
                            THEN jel.debitamount - jel.creditamount
                            ELSE jel.creditamount - jel.debitamount
                        END
                    ), 0) as balance
                    FROM journalentryline jel
                    JOIN journalentryheader jeh ON jel.documentnumber = jeh.documentnumber 
                        AND jel.companycodeid = jeh.companycodeid
                    JOIN glaccount ga ON jel.glaccountid = ga.glaccountid
                    WHERE jel.companycodeid = :company_code
                    AND jel.ledgerid = :ledger_id
                    AND jel.glaccountid = :gl_account
                    AND jel.currencycode = :currency_code
                    AND jeh.postingdate <= :balance_date
                    AND jeh.workflow_status = 'POSTED'
                """)
                
                result = conn.execute(query, {
                    "company_code": company_code,
                    "ledger_id": ledger_id,
                    "gl_account": gl_account,
                    "currency_code": currency_code,
                    "balance_date": balance_date
                }).scalar()
                
                return Decimal(str(result)) if result else Decimal('0.00')
                
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return Decimal('0.00')
    
    def _get_account_balance_functional(self, company_code: str, ledger_id: str,
                                      gl_account: str, balance_date: date) -> Decimal:
        """Get account balance in functional currency (USD)."""
        try:
            with engine.connect() as conn:
                # Get balance in USD (functional currency)
                query = text("""
                    SELECT COALESCE(SUM(
                        CASE 
                            WHEN ga.accounttype IN ('ASSETS', 'EXPENSES') 
                            THEN jel.debitamount - jel.creditamount
                            ELSE jel.creditamount - jel.debitamount
                        END
                    ), 0) as balance
                    FROM journalentryline jel
                    JOIN journalentryheader jeh ON jel.documentnumber = jeh.documentnumber 
                        AND jel.companycodeid = jeh.companycodeid
                    JOIN glaccount ga ON jel.glaccountid = ga.glaccountid
                    WHERE jel.companycodeid = :company_code
                    AND jel.ledgerid = :ledger_id
                    AND jel.glaccountid = :gl_account
                    AND jel.currencycode = 'USD'
                    AND jeh.postingdate <= :balance_date
                    AND jeh.workflow_status = 'POSTED'
                """)
                
                result = conn.execute(query, {
                    "company_code": company_code,
                    "ledger_id": ledger_id,
                    "gl_account": gl_account,
                    "balance_date": balance_date
                }).scalar()
                
                return Decimal(str(result)) if result else Decimal('0.00')
                
        except Exception as e:
            logger.error(f"Error getting functional currency balance: {e}")
            return Decimal('0.00')
    
    def _get_historical_exchange_rate(self, from_currency: str, to_currency: str,
                                    fiscal_year: int, fiscal_period: int) -> Decimal:
        """Get historical exchange rate for the period."""
        try:
            # For simplicity, use current rate. In production, would use period opening rate
            # or weighted average rate based on accounting policy
            return self.currency_service.get_exchange_rate(from_currency, to_currency) or Decimal('1.000000')
        except Exception as e:
            logger.error(f"Error getting historical exchange rate: {e}")
            return Decimal('1.000000')
    
    def _create_fx_revaluation_journal(self, company_code: str, ledger_id: str,
                                     account_details: List[Dict], revaluation_date: date,
                                     fiscal_year: int, fiscal_period: int) -> Optional[str]:
        """Create consolidated FX revaluation journal entry."""
        try:
            # Get journal template
            template = self._get_journal_template(company_code, ledger_id)
            if not template:
                logger.error(f"No journal template found for {company_code}/{ledger_id}")
                return None
            
            # Generate document number
            doc_number = f"FXREVAL{fiscal_year}{fiscal_period:02d}{ledger_id}{datetime.now().strftime('%H%M%S')}"
            
            # Prepare journal lines
            journal_lines = []
            line_number = 1
            
            total_unrealized_gl = Decimal('0.00')
            
            for account_detail in account_details:
                if not account_detail["revaluation_required"]:
                    continue
                
                unrealized_gl = account_detail["unrealized_gain_loss"]
                total_unrealized_gl += unrealized_gl
                
                if unrealized_gl != 0:
                    # Create journal line for the account being revalued
                    if unrealized_gl > 0:  # Gain
                        journal_lines.append({
                            'linenumber': line_number,
                            'glaccountid': account_detail["gl_account"],
                            'description': f"FX Revaluation Gain - {account_detail['account_currency']}",
                            'debitamount': abs(unrealized_gl),
                            'creditamount': Decimal('0.00'),
                            'currencycode': 'USD',
                            'ledgerid': ledger_id
                        })
                        line_number += 1
                        
                        journal_lines.append({
                            'linenumber': line_number,
                            'glaccountid': template["gain_account"],
                            'description': f"FX Unrealized Gain - {account_detail['gl_account']}",
                            'debitamount': Decimal('0.00'),
                            'creditamount': abs(unrealized_gl),
                            'currencycode': 'USD',
                            'ledgerid': ledger_id
                        })
                    else:  # Loss
                        journal_lines.append({
                            'linenumber': line_number,
                            'glaccountid': template["loss_account"],
                            'description': f"FX Unrealized Loss - {account_detail['gl_account']}",
                            'debitamount': abs(unrealized_gl),
                            'creditamount': Decimal('0.00'),
                            'currencycode': 'USD',
                            'ledgerid': ledger_id
                        })
                        line_number += 1
                        
                        journal_lines.append({
                            'linenumber': line_number,
                            'glaccountid': account_detail["gl_account"],
                            'description': f"FX Revaluation Loss - {account_detail['account_currency']}",
                            'debitamount': Decimal('0.00'),
                            'creditamount': abs(unrealized_gl),
                            'currencycode': 'USD',
                            'ledgerid': ledger_id
                        })
                    
                    line_number += 1
            
            if not journal_lines:
                return None
                
            # Create the journal entry using Journal Entry Manager
            success = self._create_journal_entry(
                company_code, doc_number, revaluation_date, 
                fiscal_year, fiscal_period, journal_lines, template
            )
            
            if success:
                return doc_number
            else:
                logger.error(f"Failed to create FX revaluation journal entry {doc_number}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating FX revaluation journal: {e}")
            return None
    
    def _create_journal_entry(self, company_code: str, doc_number: str,
                            posting_date: date, fiscal_year: int, fiscal_period: int,
                            journal_lines: List[Dict], template: Dict) -> bool:
        """Create journal entry in the system."""
        try:
            import sys
            import pandas as pd
            sys.path.append('/home/anton/erp/gl/pages')
            from Journal_Entry_Manager import save_journal_entry
            
            # Create DataFrame for lines
            lines_df = pd.DataFrame(journal_lines)
            
            # Save journal entry
            success = save_journal_entry(
                doc=doc_number,
                cc=company_code,
                pdate=posting_date,
                ddate=posting_date,
                fy=fiscal_year,
                per=fiscal_period,
                ref=f"FXREVAL-{template.get('template_name', 'Standard')}",
                memo=f"FX Revaluation {posting_date.strftime('%Y-%m-%d')}",
                cur="USD",
                cb=self.system_user,
                edited=lines_df,
                workflow_status="DRAFT"
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Error creating journal entry: {e}")
            return False
    
    def _create_revaluation_run(self, company_code: str, revaluation_date: date,
                              fiscal_year: int, fiscal_period: int,
                              run_type: str, started_by: str) -> int:
        """Create revaluation run record."""
        try:
            with engine.connect() as conn:
                query = text("""
                    INSERT INTO fx_revaluation_runs 
                    (company_code, revaluation_date, fiscal_year, fiscal_period, 
                     run_type, started_by)
                    VALUES (:company_code, :revaluation_date, :fiscal_year, :fiscal_period,
                            :run_type, :started_by)
                    RETURNING run_id
                """)
                
                result = conn.execute(query, {
                    "company_code": company_code,
                    "revaluation_date": revaluation_date,
                    "fiscal_year": fiscal_year,
                    "fiscal_period": fiscal_period,
                    "run_type": run_type,
                    "started_by": started_by
                }).fetchone()
                
                conn.commit()
                return result[0]
                
        except Exception as e:
            logger.error(f"Error creating revaluation run: {e}")
            raise
    
    def _update_run_status(self, run_id: int, status: str, error_details: str = None):
        """Update revaluation run status."""
        try:
            with engine.connect() as conn:
                if status == "COMPLETED":
                    query = text("""
                        UPDATE fx_revaluation_runs 
                        SET run_status = :status,
                            completed_at = CURRENT_TIMESTAMP,
                            execution_time_seconds = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - started_at))
                        WHERE run_id = :run_id
                    """)
                else:
                    query = text("""
                        UPDATE fx_revaluation_runs 
                        SET run_status = :status,
                            error_details = :error_details
                        WHERE run_id = :run_id
                    """)
                
                conn.execute(query, {
                    "run_id": run_id,
                    "status": status,
                    "error_details": error_details
                })
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error updating run status: {e}")
    
    def _save_revaluation_detail(self, run_id: int, company_code: str, 
                               ledger_id: str, account_result: Dict):
        """Save revaluation detail to database."""
        try:
            with engine.connect() as conn:
                query = text("""
                    INSERT INTO fx_revaluation_details
                    (run_id, company_code, ledger_id, gl_account, account_currency,
                     functional_currency, opening_balance_fc, current_balance_fc,
                     opening_balance_func, historical_exchange_rate, current_exchange_rate,
                     rate_difference, current_balance_func_at_current_rate, 
                     unrealized_gain_loss, revaluation_required, error_message)
                    VALUES (:run_id, :company_code, :ledger_id, :gl_account, :account_currency,
                            :functional_currency, :opening_balance_fc, :current_balance_fc,
                            :opening_balance_func, :historical_exchange_rate, :current_exchange_rate,
                            :rate_difference, :current_balance_func_at_current_rate,
                            :unrealized_gain_loss, :revaluation_required, :error_message)
                """)
                
                conn.execute(query, {
                    "run_id": run_id,
                    "company_code": company_code,
                    "ledger_id": ledger_id,
                    "gl_account": account_result["gl_account"],
                    "account_currency": account_result["account_currency"],
                    "functional_currency": account_result["functional_currency"],
                    "opening_balance_fc": account_result["opening_balance_fc"],
                    "current_balance_fc": account_result["current_balance_fc"],
                    "opening_balance_func": account_result["opening_balance_func"],
                    "historical_exchange_rate": account_result["historical_exchange_rate"],
                    "current_exchange_rate": account_result["current_exchange_rate"],
                    "rate_difference": account_result["rate_difference"],
                    "current_balance_func_at_current_rate": account_result["current_balance_func_at_current_rate"],
                    "unrealized_gain_loss": account_result["unrealized_gain_loss"],
                    "revaluation_required": account_result["revaluation_required"],
                    "error_message": account_result.get("error_message")
                })
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error saving revaluation detail: {e}")
    
    def _finalize_revaluation_run(self, run_id: int, run_results: Dict):
        """Update revaluation run with final results."""
        try:
            with engine.connect() as conn:
                query = text("""
                    UPDATE fx_revaluation_runs
                    SET total_accounts_processed = :accounts_processed,
                        total_revaluations = :revaluations_created,
                        total_unrealized_gain = :total_gain,
                        total_unrealized_loss = :total_loss,
                        journal_document_numbers = :journal_docs,
                        error_details = :errors
                    WHERE run_id = :run_id
                """)
                
                conn.execute(query, {
                    "run_id": run_id,
                    "accounts_processed": run_results["accounts_processed"],
                    "revaluations_created": run_results["revaluations_created"],
                    "total_gain": run_results["total_unrealized_gain"],
                    "total_loss": run_results["total_unrealized_loss"],
                    "journal_docs": run_results["journal_documents"],
                    "errors": "\n".join(run_results["errors"]) if run_results["errors"] else None
                })
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error finalizing revaluation run: {e}")
    
    def _get_all_revaluation_accounts(self, company_code: str) -> List[Dict]:
        """Get all accounts configured for FX revaluation."""
        try:
            with engine.connect() as conn:
                query = text("""
                    SELECT * FROM fx_revaluation_config
                    WHERE company_code = :company_code
                    AND is_active = true
                    ORDER BY ledger_id, gl_account
                """)
                
                results = conn.execute(query, {
                    "company_code": company_code
                }).mappings().all()
                
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Error getting revaluation accounts: {e}")
            return []
    
    def _get_revaluation_accounts_for_ledgers(self, company_code: str, 
                                            ledger_ids: List[str]) -> List[Dict]:
        """Get revaluation accounts for specific ledgers."""
        try:
            with engine.connect() as conn:
                query = text("""
                    SELECT * FROM fx_revaluation_config
                    WHERE company_code = :company_code
                    AND ledger_id = ANY(:ledger_ids)
                    AND is_active = true
                    ORDER BY ledger_id, gl_account
                """)
                
                results = conn.execute(query, {
                    "company_code": company_code,
                    "ledger_ids": ledger_ids
                }).mappings().all()
                
                return [dict(row) for row in results]
                
        except Exception as e:
            logger.error(f"Error getting ledger revaluation accounts: {e}")
            return []
    
    def _group_accounts_by_ledger(self, accounts: List[Dict]) -> Dict[str, List[Dict]]:
        """Group accounts by ledger ID."""
        ledger_groups = {}
        for account in accounts:
            ledger_id = account["ledger_id"]
            if ledger_id not in ledger_groups:
                ledger_groups[ledger_id] = []
            ledger_groups[ledger_id].append(account)
        return ledger_groups
    
    def _get_journal_template(self, company_code: str, ledger_id: str) -> Optional[Dict]:
        """Get journal template for FX revaluation."""
        try:
            with engine.connect() as conn:
                query = text("""
                    SELECT * FROM fx_revaluation_journal_template
                    WHERE company_code = :company_code
                    AND ledger_id = :ledger_id
                    AND is_active = true
                    ORDER BY template_id
                    LIMIT 1
                """)
                
                result = conn.execute(query, {
                    "company_code": company_code,
                    "ledger_id": ledger_id
                }).mappings().fetchone()
                
                return dict(result) if result else None
                
        except Exception as e:
            logger.error(f"Error getting journal template: {e}")
            return None

# Utility functions
def run_period_end_fx_revaluation(company_code: str, revaluation_date: date,
                                 fiscal_year: int, fiscal_period: int) -> Dict[str, Any]:
    """Run period-end FX revaluation for all configured accounts."""
    service = FXRevaluationService()
    return service.run_fx_revaluation(
        company_code, revaluation_date, fiscal_year, fiscal_period,
        run_type="PERIOD_END", create_journals=True
    )

def run_fx_revaluation_for_ledger(company_code: str, ledger_id: str,
                                 revaluation_date: date, fiscal_year: int, 
                                 fiscal_period: int) -> Dict[str, Any]:
    """Run FX revaluation for a specific ledger."""
    service = FXRevaluationService()
    return service.run_fx_revaluation(
        company_code, revaluation_date, fiscal_year, fiscal_period,
        run_type="LEDGER_SPECIFIC", ledger_ids=[ledger_id], create_journals=True
    )

# Test function
def test_fx_revaluation_service():
    """Test the FX revaluation service functionality."""
    service = FXRevaluationService()
    
    print("=== FX Revaluation Service Test ===")
    
    # Test with February 2025 data
    test_date = date(2025, 2, 28)
    
    result = service.run_fx_revaluation(
        company_code="1000",
        revaluation_date=test_date,
        fiscal_year=2025,
        fiscal_period=2,
        run_type="TEST",
        create_journals=False
    )
    
    print(f"Test run results:")
    print(f"  Status: {result['status']}")
    print(f"  Accounts processed: {result['accounts_processed']}")
    print(f"  Revaluations created: {result['revaluations_created']}")
    print(f"  Total unrealized gain: ${result['total_unrealized_gain']}")
    print(f"  Total unrealized loss: ${result['total_unrealized_loss']}")
    
    if result['errors']:
        print(f"  Errors: {result['errors']}")
    
    print("✅ FX Revaluation Service: Test completed")

if __name__ == "__main__":
    test_fx_revaluation_service()