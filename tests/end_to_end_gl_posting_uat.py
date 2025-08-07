#!/usr/bin/env python3
"""
End-to-End GL Posting UAT (User Acceptance Testing)
Complete testing framework for the GL posting workflow
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import text
from typing import Dict, List, Any
import time
import json

from db_config import engine
from utils.gl_posting_engine import GLPostingEngine
from utils.workflow_engine import WorkflowEngine

class GLPostingUAT:
    """Comprehensive UAT testing for GL posting workflow"""
    
    def __init__(self):
        self.posting_engine = GLPostingEngine()
        self.workflow_engine = WorkflowEngine()
        self.test_results = []
        self.test_data = {}
        
    def run_complete_uat(self) -> Dict[str, Any]:
        """Execute complete UAT testing suite"""
        
        print("🧪 Starting End-to-End GL Posting UAT")
        print("=" * 60)
        
        # Initialize test environment
        self._setup_test_environment()
        
        # Execute test scenarios
        test_scenarios = [
            ("Test Environment Setup", self._test_environment_setup),
            ("Journal Entry Creation", self._test_journal_entry_creation),
            ("Workflow Approval Process", self._test_workflow_approval),
            ("GL Posting Individual Document", self._test_individual_posting),
            ("Batch Posting", self._test_batch_posting),
            ("Account Balance Verification", self._test_account_balances),
            ("Preview Functionality", self._test_preview_functionality),
            ("Security & Segregation of Duties", self._test_security_controls),
            ("Error Handling", self._test_error_handling),
            ("Audit Trail Verification", self._test_audit_trail)
        ]
        
        for scenario_name, test_function in test_scenarios:
            print(f"\n📋 Testing: {scenario_name}")
            print("-" * 40)
            
            try:
                result = test_function()
                self._record_test_result(scenario_name, "PASS", result)
                print(f"✅ {scenario_name}: PASSED")
            except Exception as e:
                self._record_test_result(scenario_name, "FAIL", str(e))
                print(f"❌ {scenario_name}: FAILED - {e}")
        
        # Generate comprehensive report
        return self._generate_uat_report()
    
    def _setup_test_environment(self):
        """Setup clean test environment"""
        
        # Create test company if not exists
        with engine.connect() as conn:
            with conn.begin():
                # Check if test company exists
                result = conn.execute(text("""
                    SELECT companycodeid FROM companycode WHERE companycodeid = 'TEST'
                """))
                
                if not result.fetchone():
                    conn.execute(text("""
                        INSERT INTO companycode (companycodeid, name, currencycode)
                        VALUES ('TEST', 'Test Company for UAT', 'USD')
                    """))
                
                # Ensure fiscal period is open for testing
                current_year = datetime.now().year
                current_period = datetime.now().month
                
                conn.execute(text("""
                    INSERT INTO fiscal_period_controls (
                        company_code, fiscal_year, posting_period, period_status,
                        period_start_date, period_end_date, allow_posting, created_by
                    ) VALUES (
                        'TEST', :year, :period, 'OPEN',
                        :start_date, :end_date, true, 'UAT_SYSTEM'
                    )
                    ON CONFLICT (company_code, fiscal_year, posting_period)
                    DO UPDATE SET period_status = 'OPEN', allow_posting = true
                """), {
                    "year": current_year,
                    "period": current_period,
                    "start_date": date(current_year, current_period, 1),
                    "end_date": date(current_year, current_period, 28)
                })
                
                # Create test GL accounts if not exist
                test_accounts = [
                    ('100001', 'Test Cash Account', 'ASSET'),
                    ('200001', 'Test Accounts Payable', 'LIABILITY'),
                    ('300001', 'Test Revenue Account', 'REVENUE'),
                    ('400001', 'Test Expense Account', 'EXPENSE')
                ]
                
                for account_id, account_name, account_type in test_accounts:
                    conn.execute(text("""
                        INSERT INTO glaccount (glaccountid, companycodeid, accountname, accounttype)
                        VALUES (:id, 'TEST', :name, :type)
                        ON CONFLICT (glaccountid) DO NOTHING
                    """), {"id": account_id, "name": account_name, "type": account_type})
    
    def _test_environment_setup(self) -> Dict:
        """Test 1: Verify test environment is properly configured"""
        
        results = {}
        
        with engine.connect() as conn:
            # Check test company exists
            result = conn.execute(text("""
                SELECT companycodeid, name FROM companycode WHERE companycodeid = 'TEST'
            """))
            company = result.fetchone()
            results["company_exists"] = company is not None
            
            # Check fiscal period controls
            result = conn.execute(text("""
                SELECT period_status, allow_posting FROM fiscal_period_controls
                WHERE company_code = 'TEST' AND fiscal_year = :year AND posting_period = :period
            """), {"year": datetime.now().year, "period": datetime.now().month})
            period = result.fetchone()
            results["period_open"] = period and period[0] == 'OPEN' and period[1]
            
            # Check test GL accounts
            result = conn.execute(text("""
                SELECT COUNT(*) FROM glaccount WHERE glaccountid LIKE '1%' OR glaccountid LIKE '2%'
                OR glaccountid LIKE '3%' OR glaccountid LIKE '4%'
            """))
            account_count = result.fetchone()[0]
            results["accounts_available"] = account_count >= 4
        
        if not all(results.values()):
            raise Exception(f"Environment setup failed: {results}")
        
        return results
    
    def _test_journal_entry_creation(self) -> Dict:
        """Test 2: Create test journal entries for posting"""
        
        results = {}
        test_entries = []
        
        # Create 3 test journal entries
        for i in range(1, 4):
            doc_number = f"JE-UAT-{datetime.now().strftime('%Y%m%d')}-{i:03d}"
            
            with engine.connect() as conn:
                with conn.begin():
                    # Create header
                    conn.execute(text("""
                        INSERT INTO journalentryheader (
                            documentnumber, companycodeid, postingdate, fiscalyear, period,
                            reference, currencycode, createdby, workflow_status
                        ) VALUES (
                            :doc, 'TEST', CURRENT_DATE, :year, :period,
                            :ref, 'USD', 'uat_tester', 'DRAFT'
                        )
                    """), {
                        "doc": doc_number,
                        "year": datetime.now().year,
                        "period": datetime.now().month,
                        "ref": f"UAT Test Entry {i}"
                    })
                    
                    # Create balanced lines (Debit Cash, Credit Revenue)
                    amount = Decimal(f"{i * 100}.00")  # $100, $200, $300
                    
                    lines = [
                        (1, '100001', amount, None, f"Test debit entry {i}"),
                        (2, '300001', None, amount, f"Test credit entry {i}")
                    ]
                    
                    for line_num, account, debit, credit, desc in lines:
                        conn.execute(text("""
                            INSERT INTO journalentryline (
                                documentnumber, companycodeid, linenumber, glaccountid,
                                debitamount, creditamount, description
                            ) VALUES (
                                :doc, 'TEST', :line, :account, :debit, :credit, :desc
                            )
                        """), {
                            "doc": doc_number,
                            "line": line_num,
                            "account": account,
                            "debit": debit,
                            "credit": credit,
                            "desc": desc
                        })
            
            test_entries.append(doc_number)
            print(f"   Created journal entry: {doc_number} (Amount: ${amount})")
        
        self.test_data["journal_entries"] = test_entries
        results["entries_created"] = len(test_entries)
        results["document_numbers"] = test_entries
        
        return results
    
    def _test_workflow_approval(self) -> Dict:
        """Test 3: Test workflow approval process"""
        
        results = {}
        approved_entries = []
        
        for doc_number in self.test_data["journal_entries"]:
            try:
                # Submit for approval
                success, message = self.workflow_engine.submit_for_approval(doc_number, 'TEST', 'uat_tester')
                if not success:
                    raise Exception(f"Submit failed: {message}")
                
                # Approve the document (using different user to satisfy segregation of duties)
                success, message = self.workflow_engine.approve_document(doc_number, 'TEST', 'uat_approver', 'UAT approval')
                if not success:
                    raise Exception(f"Approval failed: {message}")
                
                approved_entries.append(doc_number)
                print(f"   Approved: {doc_number}")
                
            except Exception as e:
                print(f"   Failed to approve {doc_number}: {e}")
        
        self.test_data["approved_entries"] = approved_entries
        results["approved_count"] = len(approved_entries)
        results["approved_documents"] = approved_entries
        
        if len(approved_entries) == 0:
            raise Exception("No documents were successfully approved")
        
        return results
    
    def _test_individual_posting(self) -> Dict:
        """Test 4: Test individual document posting"""
        
        results = {}
        
        if not self.test_data.get("approved_entries"):
            raise Exception("No approved entries available for posting")
        
        # Test posting the first approved entry
        doc_number = self.test_data["approved_entries"][0]
        
        success, message = self.posting_engine.post_journal_entry(
            doc_number, 'TEST', 'uat_poster', date.today()
        )
        
        if not success:
            raise Exception(f"Individual posting failed: {message}")
        
        # Verify posting status in database
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT workflow_status, posted_at, posted_by
                FROM journalentryheader
                WHERE documentnumber = :doc AND companycodeid = 'TEST'
            """), {"doc": doc_number})
            
            row = result.fetchone()
            if not row or row[0] != 'POSTED':
                raise Exception("Document status not updated to POSTED")
        
        self.test_data["posted_individual"] = doc_number
        results["posted_document"] = doc_number
        results["posting_message"] = message
        
        print(f"   Successfully posted: {doc_number}")
        return results
    
    def _test_batch_posting(self) -> Dict:
        """Test 5: Test batch posting functionality"""
        
        results = {}
        
        # Get remaining approved entries for batch posting
        remaining_entries = [doc for doc in self.test_data["approved_entries"] 
                           if doc != self.test_data.get("posted_individual")]
        
        if not remaining_entries:
            raise Exception("No entries available for batch posting")
        
        batch_results = self.posting_engine.post_multiple_journal_entries(
            remaining_entries, 'TEST', 'uat_poster', date.today()
        )
        
        if batch_results["posted_successfully"] == 0:
            raise Exception("Batch posting failed - no documents posted")
        
        results["batch_results"] = batch_results
        results["total_processed"] = batch_results["total_documents"]
        results["successful_posts"] = batch_results["posted_successfully"]
        results["failed_posts"] = len(batch_results["failed_documents"])
        
        print(f"   Batch processed: {results['successful_posts']}/{results['total_processed']} successful")
        return results
    
    def _test_account_balances(self) -> Dict:
        """Test 6: Verify GL account balances are correctly updated"""
        
        results = {}
        
        # Check balances for test accounts
        test_accounts = ['100001', '300001']  # Cash and Revenue accounts used in test entries
        
        for account in test_accounts:
            balance = self.posting_engine.get_account_balance('TEST', account)
            results[f"account_{account}"] = balance
            
            print(f"   Account {account} - YTD Balance: ${balance.get('ytd_balance', 0):,.2f}")
        
        # Verify that debits and credits balance
        cash_balance = results.get("account_100001", {}).get("ytd_balance", 0)
        revenue_balance = results.get("account_300001", {}).get("ytd_balance", 0)
        
        # Cash should be positive (debits), Revenue should be negative (credits)
        if cash_balance <= 0:
            raise Exception(f"Cash account balance incorrect: {cash_balance}")
        
        if revenue_balance >= 0:
            raise Exception(f"Revenue account balance incorrect: {revenue_balance}")
        
        # Total should balance (cash debit = revenue credit)
        if abs(cash_balance + revenue_balance) > 0.01:  # Allow for rounding
            raise Exception(f"Accounts don't balance: Cash {cash_balance} + Revenue {revenue_balance}")
        
        results["balance_check"] = "PASSED"
        return results
    
    def _test_preview_functionality(self) -> Dict:
        """Test 7: Test document preview functionality"""
        
        results = {}
        
        # Test data retrieval for preview
        posted_doc = self.test_data.get("posted_individual")
        if not posted_doc:
            raise Exception("No posted document available for preview testing")
        
        with engine.connect() as conn:
            # Test header retrieval
            header_result = conn.execute(text("""
                SELECT documentnumber, reference, postingdate, fiscalyear, period,
                       currencycode, createdby, posted_by, posted_at
                FROM journalentryheader
                WHERE documentnumber = :doc AND companycodeid = 'TEST'
            """), {"doc": posted_doc})
            
            header = header_result.fetchone()
            if not header:
                raise Exception("Preview header data not found")
            
            # Test lines retrieval
            lines_result = conn.execute(text("""
                SELECT jel.linenumber, jel.glaccountid, ga.accountname,
                       jel.debitamount, jel.creditamount, jel.description
                FROM journalentryline jel
                LEFT JOIN glaccount ga ON ga.glaccountid = jel.glaccountid
                WHERE jel.documentnumber = :doc AND jel.companycodeid = 'TEST'
                ORDER BY jel.linenumber
            """), {"doc": posted_doc})
            
            lines = lines_result.fetchall()
            if len(lines) < 2:
                raise Exception("Preview lines data incomplete")
        
        results["header_fields"] = len(header)
        results["line_count"] = len(lines)
        results["preview_data_complete"] = True
        
        print(f"   Preview data: {results['header_fields']} header fields, {results['line_count']} lines")
        return results
    
    def _test_security_controls(self) -> Dict:
        """Test 8: Test security and segregation of duties"""
        
        results = {}
        
        # Test 1: Try to post a document created by the same user (should fail)
        with engine.connect() as conn:
            with conn.begin():
                # Create a test document
                test_doc = f"JE-SOD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                conn.execute(text("""
                    INSERT INTO journalentryheader (
                        documentnumber, companycodeid, postingdate, fiscalyear, period,
                        reference, currencycode, createdby, workflow_status
                    ) VALUES (
                        :doc, 'TEST', CURRENT_DATE, :year, :period,
                        'SOD Test', 'USD', 'same_user', 'APPROVED'
                    )
                """), {
                    "doc": test_doc,
                    "year": datetime.now().year,
                    "period": datetime.now().month
                })
                
                # Add lines
                conn.execute(text("""
                    INSERT INTO journalentryline (
                        documentnumber, companycodeid, linenumber, glaccountid,
                        debitamount, creditamount, description
                    ) VALUES 
                    (:doc, 'TEST', 1, '100001', 100.00, NULL, 'SOD Test Debit'),
                    (:doc, 'TEST', 2, '300001', NULL, 100.00, 'SOD Test Credit')
                """), {"doc": test_doc})
        
        # Try to post with same user (should fail)
        success, message = self.posting_engine.post_journal_entry(
            test_doc, 'TEST', 'same_user', date.today()
        )
        
        results["segregation_of_duties"] = not success
        results["sod_message"] = message
        
        if success:
            raise Exception("Segregation of duties check failed - same user was able to post their own entry")
        
        print(f"   Segregation of duties: PASSED - {message}")
        
        # Test 2: Try to post unapproved document
        with engine.connect() as conn:
            with conn.begin():
                test_doc2 = f"JE-UNAPP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                conn.execute(text("""
                    INSERT INTO journalentryheader (
                        documentnumber, companycodeid, postingdate, fiscalyear, period,
                        reference, currencycode, createdby, workflow_status
                    ) VALUES (
                        :doc, 'TEST', CURRENT_DATE, :year, :period,
                        'Unapproved Test', 'USD', 'creator', 'DRAFT'
                    )
                """), {
                    "doc": test_doc2,
                    "year": datetime.now().year,
                    "period": datetime.now().month
                })
        
        success2, message2 = self.posting_engine.post_journal_entry(
            test_doc2, 'TEST', 'different_user', date.today()
        )
        
        results["approval_check"] = not success2
        results["approval_message"] = message2
        
        if success2:
            raise Exception("Approval check failed - unapproved document was posted")
        
        print(f"   Approval requirement: PASSED - {message2}")
        return results
    
    def _test_error_handling(self) -> Dict:
        """Test 9: Test various error conditions"""
        
        results = {}
        error_tests = []
        
        # Test 1: Non-existent document
        success, message = self.posting_engine.post_journal_entry(
            "NONEXISTENT", 'TEST', 'uat_poster', date.today()
        )
        error_tests.append(("non_existent_doc", not success, message))
        
        # Test 2: Already posted document
        posted_doc = self.test_data.get("posted_individual")
        if posted_doc:
            success, message = self.posting_engine.post_journal_entry(
                posted_doc, 'TEST', 'uat_poster', date.today()
            )
            error_tests.append(("already_posted", not success, message))
        
        # Test 3: Invalid company code
        if self.test_data.get("approved_entries"):
            success, message = self.posting_engine.post_journal_entry(
                self.test_data["approved_entries"][0], 'INVALID', 'uat_poster', date.today()
            )
            error_tests.append(("invalid_company", not success, message))
        
        for test_name, passed, msg in error_tests:
            results[test_name] = {"passed": passed, "message": msg}
            status = "PASSED" if passed else "FAILED"
            print(f"   {test_name}: {status} - {msg}")
        
        # All error tests should pass (i.e., properly handle errors)
        if not all(test[1] for test in error_tests):
            raise Exception("Some error handling tests failed")
        
        return results
    
    def _test_audit_trail(self) -> Dict:
        """Test 10: Verify audit trail is properly maintained"""
        
        results = {}
        
        # Check posting audit trail
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM posting_audit_trail
                WHERE company_code = 'TEST' AND action_type = 'POST'
                AND action_timestamp >= CURRENT_DATE
            """))
            
            audit_count = result.fetchone()[0]
            results["audit_trail_entries"] = audit_count
            
            # Check GL transactions
            result = conn.execute(text("""
                SELECT COUNT(*) FROM gl_transactions
                WHERE company_code = 'TEST' AND posting_date >= CURRENT_DATE
            """))
            
            transaction_count = result.fetchone()[0]
            results["gl_transactions"] = transaction_count
            
            # Check posting documents
            result = conn.execute(text("""
                SELECT COUNT(*) FROM posting_documents
                WHERE company_code = 'TEST' AND posting_date >= CURRENT_DATE
            """))
            
            document_count = result.fetchone()[0]
            results["posting_documents"] = document_count
        
        print(f"   Audit trail entries: {audit_count}")
        print(f"   GL transactions: {transaction_count}")
        print(f"   Posting documents: {document_count}")
        
        if audit_count == 0:
            raise Exception("No audit trail entries found")
        
        return results
    
    def _record_test_result(self, test_name: str, status: str, details: Any):
        """Record test result"""
        
        self.test_results.append({
            "test_name": test_name,
            "status": status,
            "timestamp": datetime.now(),
            "details": details
        })
    
    def _generate_uat_report(self) -> Dict[str, Any]:
        """Generate comprehensive UAT report"""
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["status"] == "PASS")
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = {
            "uat_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "success_rate": success_rate,
                "test_date": datetime.now().isoformat(),
                "status": "PASSED" if failed_tests == 0 else "FAILED"
            },
            "test_results": self.test_results,
            "test_data": self.test_data,
            "environment": {
                "company_code": "TEST",
                "fiscal_year": datetime.now().year,
                "posting_period": datetime.now().month,
                "test_date": date.today().isoformat()
            }
        }
        
        return report

def main():
    """Main function to run UAT"""
    
    uat = GLPostingUAT()
    report = uat.run_complete_uat()
    
    print("\n" + "=" * 60)
    print("🏁 UAT COMPLETION SUMMARY")
    print("=" * 60)
    
    summary = report["uat_summary"]
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed_tests']}")
    print(f"Failed: {summary['failed_tests']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(f"Overall Status: {summary['status']}")
    
    # Save detailed report
    report_file = f"/home/anton/erp/gl/tests/UAT_GL_POSTING_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\nDetailed report saved to: {report_file}")
    
    return report

if __name__ == "__main__":
    main()