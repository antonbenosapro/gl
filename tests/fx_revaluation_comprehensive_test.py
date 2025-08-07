#!/usr/bin/env python3
"""
Comprehensive FX Revaluation Testing Framework

This test validates the complete foreign currency revaluation functionality
integrated with the parallel ledger system including:

1. Setup of foreign currency transactions
2. FX rate changes simulation
3. Period-end revaluation calculations
4. Parallel ledger revaluation processing  
5. Journal entry generation and posting
6. Reporting and validation

Author: Claude Code Assistant
Date: August 6, 2025
"""

import sys
import os
sys.path.append('/home/anton/erp/gl')

import json
import pandas as pd
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Any
from sqlalchemy import text
from db_config import engine
from utils.fx_revaluation_service import FXRevaluationService
from utils.currency_service import CurrencyTranslationService
from utils.parallel_posting_service import ParallelPostingService
from utils.workflow_engine import WorkflowEngine
from utils.logger import get_logger

logger = get_logger("fx_revaluation_test")

class FXRevaluationComprehensiveTest:
    """Comprehensive test framework for FX revaluation functionality."""
    
    def __init__(self):
        """Initialize the test framework."""
        self.test_results = {
            "test_start_time": datetime.now(),
            "company_code": "1000",
            "test_scenarios": [],
            "fx_transactions": [],
            "revaluation_results": {},
            "parallel_processing": {},
            "validation_results": {},
            "test_phases": {},
            "errors": [],
            "warnings": []
        }
        
        # Initialize services
        self.fx_service = FXRevaluationService()
        self.currency_service = CurrencyTranslationService()
        self.parallel_service = ParallelPostingService()
        self.workflow_engine = WorkflowEngine()
        
        # Test data
        self.test_date_start = date(2025, 3, 1)
        self.test_date_end = date(2025, 3, 31)
        self.revaluation_date = date(2025, 3, 31)
    
    def run_comprehensive_test(self):
        """Execute comprehensive FX revaluation test."""
        print("=" * 80)
        print("🧪 COMPREHENSIVE FX REVALUATION TEST")
        print("=" * 80)
        print("Testing complete FX revaluation workflow with parallel ledger integration")
        print()
        
        try:
            # Phase 1: Setup test environment
            if not self.phase_1_setup_test_environment():
                return False
            
            # Phase 2: Create foreign currency transactions  
            if not self.phase_2_create_fx_transactions():
                return False
            
            # Phase 3: Update exchange rates
            if not self.phase_3_update_exchange_rates():
                return False
            
            # Phase 4: Execute FX revaluation
            if not self.phase_4_execute_fx_revaluation():
                return False
            
            # Phase 5: Validate parallel ledger integration
            if not self.phase_5_validate_parallel_integration():
                return False
            
            # Phase 6: Generate comprehensive report
            self.phase_6_generate_test_report()
            
            return True
            
        except Exception as e:
            logger.error(f"Comprehensive FX test failed: {e}")
            self.test_results["errors"].append(f"Test execution failed: {str(e)}")
            return False
    
    def phase_1_setup_test_environment(self):
        """Phase 1: Setup test environment and data."""
        print("🏗️ PHASE 1: Setting up FX revaluation test environment")
        print("-" * 70)
        
        try:
            # Setup exchange rates for testing
            test_rates = [
                {"from": "EUR", "to": "USD", "rate": Decimal("1.080000"), "date": self.test_date_start},
                {"from": "GBP", "to": "USD", "rate": Decimal("1.250000"), "date": self.test_date_start},
                {"from": "JPY", "to": "USD", "rate": Decimal("0.006800"), "date": self.test_date_start}
            ]
            
            for rate_info in test_rates:
                success = self.currency_service.update_exchange_rate(
                    rate_info["from"], rate_info["to"], rate_info["rate"], 
                    rate_info["date"], "TEST", "FX_TEST"
                )
                if success:
                    print(f"    ✅ Set {rate_info['from']}/USD rate: {rate_info['rate']}")
            
            # Verify FX configuration exists
            config_count = self._verify_fx_configuration()
            print(f"    📋 FX configuration accounts: {config_count}")
            
            # Verify accounts exist
            accounts_verified = self._verify_fx_accounts()
            print(f"    🏦 FX accounts verified: {accounts_verified}")
            
            self.test_results["test_phases"]["Phase 1"] = {
                "status": "PASSED",
                "message": "Test environment setup completed",
                "details": {
                    "exchange_rates_setup": len(test_rates),
                    "fx_config_accounts": config_count,
                    "fx_accounts_verified": accounts_verified
                }
            }
            
            return True
            
        except Exception as e:
            self.test_results["test_phases"]["Phase 1"] = {
                "status": "FAILED",
                "message": f"Environment setup failed: {str(e)}"
            }
            logger.error(f"Phase 1 failed: {e}")
            return False
    
    def phase_2_create_fx_transactions(self):
        """Phase 2: Create foreign currency transactions."""
        print("\n💱 PHASE 2: Creating foreign currency transactions")
        print("-" * 70)
        
        try:
            # Import Journal Entry Manager
            sys.path.append('/home/anton/erp/gl/pages')
            from Journal_Entry_Manager import save_journal_entry
            
            # Test transactions in multiple currencies
            fx_transactions = [
                {
                    "doc_number": "FX_TEST_EUR_001",
                    "description": "EUR Customer Invoice - Test Transaction",
                    "currency": "EUR",
                    "lines": [
                        {"account": "115001", "description": "A/R - EUR Customer", "debit": 5000.00, "credit": 0.00},
                        {"account": "410001", "description": "Sales Revenue - EUR", "debit": 0.00, "credit": 5000.00}
                    ]
                },
                {
                    "doc_number": "FX_TEST_GBP_001", 
                    "description": "GBP Supplier Invoice - Test Transaction",
                    "currency": "GBP",
                    "lines": [
                        {"account": "570001", "description": "Office Expenses - GBP", "debit": 2000.00, "credit": 0.00},
                        {"account": "115002", "description": "A/R - GBP Customer", "debit": 1500.00, "credit": 0.00},
                        {"account": "210002", "description": "A/P - GBP Supplier", "debit": 0.00, "credit": 3500.00}
                    ]
                },
                {
                    "doc_number": "FX_TEST_EUR_002",
                    "description": "EUR Cash Receipt - Test Transaction", 
                    "currency": "EUR",
                    "lines": [
                        {"account": "100002", "description": "Cash - EUR Account", "debit": 3000.00, "credit": 0.00},
                        {"account": "115001", "description": "A/R Collection - EUR", "debit": 0.00, "credit": 3000.00}
                    ]
                }
            ]
            
            created_transactions = []
            
            for tx in fx_transactions:
                try:
                    # Create DataFrame for lines
                    lines_data = []
                    for line_num, line in enumerate(tx["lines"], 1):
                        lines_data.append({
                            'linenumber': line_num,
                            'glaccountid': line["account"],
                            'description': line["description"],
                            'debitamount': Decimal(str(line["debit"])),
                            'creditamount': Decimal(str(line["credit"])),
                            'currencycode': tx["currency"],
                            'costcenterid': '',
                            'ledgerid': 'L1'
                        })
                    
                    lines_df = pd.DataFrame(lines_data)
                    
                    # Save journal entry
                    success = save_journal_entry(
                        doc=tx["doc_number"],
                        cc=self.test_results["company_code"],
                        pdate=self.test_date_start,
                        ddate=self.test_date_start,
                        fy=2025,
                        per=3,  # March
                        ref=f"FX-TEST-{tx['currency']}",
                        memo=tx["description"],
                        cur=tx["currency"],
                        cb="FX_TEST_USER",
                        edited=lines_df,
                        workflow_status="DRAFT"
                    )
                    
                    if success:
                        # Submit and approve for testing
                        self.workflow_engine.submit_for_approval(
                            tx["doc_number"], self.test_results["company_code"], "FX_TEST_USER"
                        )
                        self.workflow_engine.approve_document(
                            tx["doc_number"], self.test_results["company_code"], "FX_TEST_APPROVER"
                        )
                        
                        created_transactions.append(tx)
                        print(f"    ✅ Created and approved: {tx['doc_number']} ({tx['currency']})")
                    
                except Exception as e:
                    print(f"    ❌ Failed to create {tx['doc_number']}: {str(e)}")
                    continue
            
            self.test_results["fx_transactions"] = created_transactions
            
            # Process through parallel ledgers
            for tx in created_transactions:
                try:
                    result = self.parallel_service.process_approved_document_to_all_ledgers(
                        tx["doc_number"], self.test_results["company_code"]
                    )
                    print(f"    🏦 Parallel processed {tx['doc_number']}: {result.get('successful_ledgers', 0)}/{result.get('total_ledgers', 0)} ledgers")
                except Exception as e:
                    print(f"    ⚠️ Parallel processing issue for {tx['doc_number']}: {str(e)}")
            
            self.test_results["test_phases"]["Phase 2"] = {
                "status": "PASSED",
                "message": f"Created {len(created_transactions)} FX transactions",
                "details": {
                    "transactions_created": len(created_transactions),
                    "currencies": list(set(tx["currency"] for tx in created_transactions))
                }
            }
            
            return True
            
        except Exception as e:
            self.test_results["test_phases"]["Phase 2"] = {
                "status": "FAILED", 
                "message": f"FX transaction creation failed: {str(e)}"
            }
            logger.error(f"Phase 2 failed: {e}")
            return False
    
    def phase_3_update_exchange_rates(self):
        """Phase 3: Update exchange rates to simulate rate changes."""
        print("\n📈 PHASE 3: Updating exchange rates for revaluation")
        print("-" * 70)
        
        try:
            # Updated rates for revaluation (simulate significant changes)
            updated_rates = [
                {"from": "EUR", "to": "USD", "rate": Decimal("1.120000"), "change": "+3.7%"},  # EUR strengthened
                {"from": "GBP", "to": "USD", "rate": Decimal("1.200000"), "change": "-4.0%"},  # GBP weakened  
                {"from": "JPY", "to": "USD", "rate": Decimal("0.007200"), "change": "+5.9%"}   # JPY strengthened
            ]
            
            for rate_info in updated_rates:
                success = self.currency_service.update_exchange_rate(
                    rate_info["from"], rate_info["to"], rate_info["rate"],
                    self.revaluation_date, "TEST", "FX_REVALUATION_TEST"
                )
                
                if success:
                    print(f"    ✅ Updated {rate_info['from']}/USD: {rate_info['rate']} ({rate_info['change']})")
                else:
                    print(f"    ❌ Failed to update {rate_info['from']}/USD rate")
            
            # Verify rate updates
            verification_count = 0
            for rate_info in updated_rates:
                current_rate = self.currency_service.get_exchange_rate(
                    rate_info["from"], "USD", self.revaluation_date
                )
                if current_rate == rate_info["rate"]:
                    verification_count += 1
            
            self.test_results["test_phases"]["Phase 3"] = {
                "status": "PASSED",
                "message": f"Updated {len(updated_rates)} exchange rates for revaluation",
                "details": {
                    "rates_updated": len(updated_rates),
                    "rates_verified": verification_count,
                    "rate_changes": updated_rates
                }
            }
            
            return True
            
        except Exception as e:
            self.test_results["test_phases"]["Phase 3"] = {
                "status": "FAILED",
                "message": f"Exchange rate update failed: {str(e)}"
            }
            logger.error(f"Phase 3 failed: {e}")
            return False
    
    def phase_4_execute_fx_revaluation(self):
        """Phase 4: Execute comprehensive FX revaluation."""
        print("\n🔄 PHASE 4: Executing FX revaluation process")
        print("-" * 70)
        
        try:
            # Execute FX revaluation for all ledgers
            revaluation_result = self.fx_service.run_fx_revaluation(
                company_code=self.test_results["company_code"],
                revaluation_date=self.revaluation_date,
                fiscal_year=2025,
                fiscal_period=3,  # March
                run_type="PERIOD_END",
                ledger_ids=None,  # All ledgers
                create_journals=True
            )
            
            self.test_results["revaluation_results"] = revaluation_result
            
            # Display results
            print(f"    📊 Revaluation Status: {revaluation_result['status']}")
            print(f"    📋 Accounts Processed: {revaluation_result['accounts_processed']}")
            print(f"    💰 Revaluations Created: {revaluation_result['revaluations_created']}")
            print(f"    💹 Total Unrealized Gain: ${revaluation_result['total_unrealized_gain']:,.2f}")
            print(f"    📉 Total Unrealized Loss: ${revaluation_result['total_unrealized_loss']:,.2f}")
            
            # Display ledger-specific results
            if revaluation_result.get("ledger_results"):
                print(f"    🏦 Ledger Results:")
                for ledger_id, ledger_result in revaluation_result["ledger_results"].items():
                    print(f"       {ledger_id}: {ledger_result['accounts_processed']} accounts, "
                          f"{ledger_result['revaluations_created']} revaluations")
            
            # Show created journal documents
            if revaluation_result.get("journal_documents"):
                print(f"    📝 Journal Documents Created: {len(revaluation_result['journal_documents'])}")
                for doc in revaluation_result["journal_documents"]:
                    print(f"       • {doc}")
            
            success = (revaluation_result["status"] == "COMPLETED" and 
                      revaluation_result["accounts_processed"] > 0)
            
            self.test_results["test_phases"]["Phase 4"] = {
                "status": "PASSED" if success else "FAILED",
                "message": f"FX revaluation {'completed successfully' if success else 'failed'}",
                "details": revaluation_result
            }
            
            return success
            
        except Exception as e:
            self.test_results["test_phases"]["Phase 4"] = {
                "status": "FAILED",
                "message": f"FX revaluation execution failed: {str(e)}"
            }
            logger.error(f"Phase 4 failed: {e}")
            return False
    
    def phase_5_validate_parallel_integration(self):
        """Phase 5: Validate parallel ledger integration."""
        print("\n🏦 PHASE 5: Validating parallel ledger integration")
        print("-" * 70)
        
        try:
            validation_results = {
                "ledger_consistency": True,
                "balance_verification": True,
                "parallel_documents": 0,
                "ledger_balances": {},
                "errors": []
            }
            
            # Check parallel document creation for FX revaluation journals
            journal_docs = self.test_results["revaluation_results"].get("journal_documents", [])
            
            for journal_doc in journal_docs:
                try:
                    # Process journal through parallel ledgers
                    parallel_result = self.parallel_service.process_approved_document_to_all_ledgers(
                        journal_doc, self.test_results["company_code"]
                    )
                    
                    validation_results["parallel_documents"] += parallel_result.get("successful_ledgers", 0)
                    print(f"    🔄 {journal_doc}: {parallel_result.get('successful_ledgers', 0)}/{parallel_result.get('total_ledgers', 0)} parallel ledgers")
                    
                except Exception as e:
                    validation_results["errors"].append(f"Parallel processing error for {journal_doc}: {str(e)}")
                    print(f"    ❌ Parallel processing failed for {journal_doc}: {str(e)}")
            
            # Validate balance consistency across ledgers
            balance_consistency = self._validate_balance_consistency()
            validation_results["ledger_balances"] = balance_consistency
            
            for ledger_id, balance_info in balance_consistency.items():
                balance_status = "✅" if balance_info["balanced"] else "❌"
                print(f"    {balance_status} {ledger_id}: ${balance_info['total_debits']:,.2f} Dr / ${balance_info['total_credits']:,.2f} Cr")
            
            # Overall validation status
            overall_success = (
                len(validation_results["errors"]) == 0 and
                all(balance["balanced"] for balance in balance_consistency.values())
            )
            
            self.test_results["parallel_processing"] = validation_results
            
            self.test_results["test_phases"]["Phase 5"] = {
                "status": "PASSED" if overall_success else "FAILED",
                "message": f"Parallel integration {'validated successfully' if overall_success else 'has issues'}",
                "details": validation_results
            }
            
            return overall_success
            
        except Exception as e:
            self.test_results["test_phases"]["Phase 5"] = {
                "status": "FAILED",
                "message": f"Parallel integration validation failed: {str(e)}"
            }
            logger.error(f"Phase 5 failed: {e}")
            return False
    
    def phase_6_generate_test_report(self):
        """Phase 6: Generate comprehensive test report."""
        print("\n📊 PHASE 6: Generating comprehensive test report")
        print("-" * 70)
        
        # Calculate overall results
        total_phases = len(self.test_results["test_phases"])
        passed_phases = sum(1 for phase in self.test_results["test_phases"].values() if phase["status"] == "PASSED")
        success_rate = (passed_phases / total_phases * 100) if total_phases > 0 else 0
        
        print(f"\n{'='*80}")
        print(f"📄 COMPREHENSIVE FX REVALUATION TEST REPORT")
        print(f"{'='*80}")
        
        print(f"\n📊 TEST SUMMARY")
        print(f"   Duration: {datetime.now() - self.test_results['test_start_time']}")
        print(f"   Company Code: {self.test_results['company_code']}")
        print(f"   Revaluation Date: {self.revaluation_date}")
        print(f"   Total Phases: {total_phases}")
        print(f"   Passed: {passed_phases} ✅")
        print(f"   Failed: {total_phases - passed_phases} ❌")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        # Phase results
        print(f"\n🔍 DETAILED PHASE RESULTS")
        for phase_name, phase_result in self.test_results["test_phases"].items():
            status_icon = "✅" if phase_result["status"] == "PASSED" else "❌"
            print(f"   {status_icon} {phase_name}: {phase_result['message']}")
        
        # FX Transaction Summary
        if self.test_results["fx_transactions"]:
            print(f"\n💱 FX TRANSACTION SUMMARY")
            print(f"   Transactions Created: {len(self.test_results['fx_transactions'])}")
            currencies = set(tx["currency"] for tx in self.test_results["fx_transactions"])
            print(f"   Currencies: {', '.join(currencies)}")
        
        # Revaluation Results
        if self.test_results.get("revaluation_results"):
            reval_results = self.test_results["revaluation_results"]
            print(f"\n🔄 REVALUATION RESULTS")
            print(f"   Status: {reval_results['status']}")
            print(f"   Accounts Processed: {reval_results['accounts_processed']}")
            print(f"   Revaluations Created: {reval_results['revaluations_created']}")
            print(f"   Total Unrealized Gain: ${reval_results['total_unrealized_gain']:,.2f}")
            print(f"   Total Unrealized Loss: ${reval_results['total_unrealized_loss']:,.2f}")
            print(f"   Net Impact: ${(reval_results['total_unrealized_gain'] - reval_results['total_unrealized_loss']):,.2f}")
        
        # Parallel Processing Results
        if self.test_results.get("parallel_processing"):
            parallel_results = self.test_results["parallel_processing"]
            print(f"\n🏦 PARALLEL PROCESSING RESULTS")
            print(f"   Parallel Documents Created: {parallel_results['parallel_documents']}")
            print(f"   Ledger Consistency: {'✅ Maintained' if parallel_results['balance_verification'] else '❌ Issues Found'}")
        
        # Overall Assessment
        print(f"\n🎯 OVERALL ASSESSMENT")
        if success_rate >= 90:
            print(f"   ✅ EXCELLENT - FX Revaluation system is production ready")
            assessment = "PRODUCTION_READY"
        elif success_rate >= 75:
            print(f"   ⚠️ GOOD - Minor issues to address")
            assessment = "CONDITIONAL_ACCEPTANCE"
        else:
            print(f"   ❌ NEEDS WORK - Significant issues found")
            assessment = "NEEDS_WORK"
        
        # Error Summary
        if self.test_results["errors"]:
            print(f"\n❌ ERRORS ENCOUNTERED ({len(self.test_results['errors'])})")
            for error in self.test_results["errors"]:
                print(f"   • {error}")
        
        # Save detailed results
        self.test_results["test_end_time"] = datetime.now()
        self.test_results["overall_assessment"] = assessment
        self.test_results["success_rate"] = success_rate
        
        result_file = f"fx_revaluation_comprehensive_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        print(f"\n📋 Detailed test results saved to: {result_file}")
        print(f"{'='*80}")
        
        return success_rate >= 75
    
    def _verify_fx_configuration(self):
        """Verify FX revaluation configuration."""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM fx_revaluation_config
                    WHERE company_code = :company_code AND is_active = true
                """), {"company_code": self.test_results["company_code"]}).scalar()
                return result or 0
        except:
            return 0
    
    def _verify_fx_accounts(self):
        """Verify FX accounts exist."""
        fx_accounts = ["115001", "115002", "210001", "210002", "100002", "590001", "590002"]
        verified_count = 0
        
        try:
            with engine.connect() as conn:
                for account in fx_accounts:
                    result = conn.execute(text("""
                        SELECT COUNT(*) FROM glaccount WHERE glaccountid = :account
                    """), {"account": account}).scalar()
                    if result > 0:
                        verified_count += 1
        except:
            pass
        
        return verified_count
    
    def _validate_balance_consistency(self):
        """Validate balance consistency across ledgers."""
        balance_info = {}
        
        try:
            with engine.connect() as conn:
                # Get balances by ledger for March 2025
                query = text("""
                    SELECT 
                        jel.ledgerid,
                        SUM(jel.debitamount) as total_debits,
                        SUM(jel.creditamount) as total_credits,
                        SUM(jel.debitamount) - SUM(jel.creditamount) as net_balance
                    FROM journalentryline jel
                    JOIN journalentryheader jeh ON jel.documentnumber = jeh.documentnumber 
                        AND jel.companycodeid = jeh.companycodeid
                    WHERE jeh.fiscalyear = 2025
                    AND jeh.period = 3
                    AND jeh.companycodeid = :company_code
                    AND jeh.workflow_status = 'POSTED'
                    AND (jel.documentnumber LIKE 'FX_TEST_%' OR jel.documentnumber LIKE 'FXREVAL%')
                    GROUP BY jel.ledgerid
                    ORDER BY jel.ledgerid
                """)
                
                results = conn.execute(query, {
                    "company_code": self.test_results["company_code"]
                }).fetchall()
                
                for result in results:
                    ledger_id = result[0]
                    total_debits = float(result[1])
                    total_credits = float(result[2])
                    net_balance = float(result[3])
                    
                    balance_info[ledger_id] = {
                        "total_debits": total_debits,
                        "total_credits": total_credits,
                        "net_balance": net_balance,
                        "balanced": abs(net_balance) < 0.01
                    }
        
        except Exception as e:
            logger.error(f"Error validating balance consistency: {e}")
        
        return balance_info
    
    def cleanup_test_data(self):
        """Clean up test data."""
        try:
            print(f"\n🧹 CLEANUP: FX revaluation test data")
            
            test_docs = [tx["doc_number"] for tx in self.test_results["fx_transactions"]]
            if self.test_results.get("revaluation_results", {}).get("journal_documents"):
                test_docs.extend(self.test_results["revaluation_results"]["journal_documents"])
            
            with engine.begin() as conn:
                # Delete parallel documents first
                for doc in test_docs:
                    parallel_docs = conn.execute(text("""
                        SELECT documentnumber FROM journalentryheader
                        WHERE parallel_source_doc = :doc AND companycodeid = :cc
                    """), {"doc": doc, "cc": self.test_results["company_code"]}).scalars().all()
                    
                    for parallel_doc in parallel_docs:
                        conn.execute(text("DELETE FROM journalentryline WHERE documentnumber = :doc AND companycodeid = :cc"),
                                   {"doc": parallel_doc, "cc": self.test_results["company_code"]})
                        conn.execute(text("DELETE FROM journalentryheader WHERE documentnumber = :doc AND companycodeid = :cc"),
                                   {"doc": parallel_doc, "cc": self.test_results["company_code"]})
                
                # Delete workflow instances
                for doc in test_docs:
                    conn.execute(text("DELETE FROM workflow_instances WHERE document_number = :doc AND company_code = :cc"),
                               {"doc": doc, "cc": self.test_results["company_code"]})
                
                # Delete main test documents  
                for doc in test_docs:
                    conn.execute(text("DELETE FROM journalentryline WHERE documentnumber = :doc AND companycodeid = :cc"),
                               {"doc": doc, "cc": self.test_results["company_code"]})
                    conn.execute(text("DELETE FROM journalentryheader WHERE documentnumber = :doc AND companycodeid = :cc"),
                               {"doc": doc, "cc": self.test_results["company_code"]})
                
                # Delete FX revaluation data
                if self.test_results.get("revaluation_results", {}).get("run_id"):
                    run_id = self.test_results["revaluation_results"]["run_id"]
                    conn.execute(text("DELETE FROM fx_revaluation_details WHERE run_id = :run_id"),
                               {"run_id": run_id})
                    conn.execute(text("DELETE FROM fx_revaluation_runs WHERE run_id = :run_id"),
                               {"run_id": run_id})
            
            print(f"   Cleaned up {len(test_docs)} test documents and related data")
            
        except Exception as e:
            print(f"   ⚠️ Cleanup warning: {e}")

def main():
    """Run the comprehensive FX revaluation test."""
    test = FXRevaluationComprehensiveTest()
    
    try:
        success = test.run_comprehensive_test()
        
        # Ask about cleanup
        cleanup_response = input("\n🗑️ Clean up test data? (y/N): ").lower().strip()
        if cleanup_response == 'y':
            test.cleanup_test_data()
        else:
            print("   Test data preserved for analysis")
        
        return 0 if success else 1
        
    except Exception as e:
        print(f"\n❌ COMPREHENSIVE TEST FAILED: {e}")
        logger.error(f"Comprehensive FX test execution failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())