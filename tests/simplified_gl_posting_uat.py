#!/usr/bin/env python3
"""
Simplified GL Posting UAT
Focus on core GL posting functionality with direct document approval
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import text
from typing import Dict, List, Any
import time
import json

from db_config import engine
from utils.gl_posting_engine import GLPostingEngine

class SimplifiedGLPostingUAT:
    """Simplified UAT focusing on GL posting core functionality"""
    
    def __init__(self):
        self.posting_engine = GLPostingEngine()
        self.test_results = []
        self.test_data = {}
        
    def run_simplified_uat(self) -> Dict[str, Any]:
        """Execute simplified UAT testing suite"""
        
        print("🧪 Starting Simplified GL Posting UAT")
        print("=" * 60)
        
        # Initialize test environment
        self._setup_test_environment()
        
        # Execute test scenarios
        test_scenarios = [
            ("Environment Setup", self._test_environment_setup),
            ("Create Approved Journal Entries", self._create_approved_entries),
            ("Individual Document Posting", self._test_individual_posting),
            ("Batch Posting", self._test_batch_posting), 
            ("Account Balances", self._test_account_balances),
            ("Preview Functionality", self._test_preview_functionality),
            ("Security Controls", self._test_security_controls),
            ("Audit Trail", self._test_audit_trail)
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
        
        return self._generate_uat_report()
    
    def _setup_test_environment(self):
        """Setup clean test environment"""
        
        with engine.connect() as conn:
            with conn.begin():
                # Create test company
                conn.execute(text("""
                    INSERT INTO companycode (companycodeid, name, currencycode)
                    VALUES ('TEST', 'Test Company for UAT', 'USD')
                    ON CONFLICT (companycodeid) DO NOTHING
                """))
                
                # Setup fiscal period
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
                
                # Create test GL accounts
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
        """Test 1: Verify test environment"""
        
        results = {}
        
        with engine.connect() as conn:
            # Check test company
            result = conn.execute(text("""
                SELECT companycodeid, name FROM companycode WHERE companycodeid = 'TEST'
            """))
            results["company_exists"] = result.fetchone() is not None
            
            # Check fiscal period
            result = conn.execute(text("""
                SELECT period_status, allow_posting FROM fiscal_period_controls
                WHERE company_code = 'TEST' AND fiscal_year = :year AND posting_period = :period
            """), {"year": datetime.now().year, "period": datetime.now().month})
            period = result.fetchone()
            results["period_open"] = period and period[0] == 'OPEN' and period[1]
            
            # Check accounts
            result = conn.execute(text("""
                SELECT COUNT(*) FROM glaccount WHERE companycodeid = 'TEST'
            """))
            results["accounts_count"] = result.fetchone()[0]
        
        if not all([results["company_exists"], results["period_open"], results["accounts_count"] >= 4]):
            raise Exception(f"Environment setup failed: {results}")
        
        return results
    
    def _create_approved_entries(self) -> Dict:
        """Test 2: Create approved journal entries directly"""
        
        results = {}
        test_entries = []
        
        # Create 3 test journal entries with APPROVED status
        for i in range(1, 4):
            doc_number = f"UAT{datetime.now().strftime('%Y%m%d')}{i:03d}"
            
            with engine.connect() as conn:
                with conn.begin():
                    # Create header with APPROVED status
                    conn.execute(text("""
                        INSERT INTO journalentryheader (
                            documentnumber, companycodeid, postingdate, fiscalyear, period,
                            reference, currencycode, createdby, workflow_status
                        ) VALUES (
                            :doc, 'TEST', CURRENT_DATE, :year, :period,
                            :ref, 'USD', 'uat_creator', 'APPROVED'
                        )
                    """), {
                        "doc": doc_number,
                        "year": datetime.now().year,
                        "period": datetime.now().month,
                        "ref": f"UAT Test Entry {i}"
                    })
                    
                    # Create balanced lines
                    amount = Decimal(f"{i * 100}.00")
                    
                    lines = [
                        (1, '100001', amount, None, f"Test debit {i}"),
                        (2, '300001', None, amount, f"Test credit {i}")
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
            print(f"   Created approved entry: {doc_number} (Amount: ${amount})")
        
        self.test_data["approved_entries"] = test_entries
        results["entries_created"] = len(test_entries)
        results["document_numbers"] = test_entries
        
        return results
    
    def _test_individual_posting(self) -> Dict:
        """Test 3: Individual document posting"""
        
        results = {}
        
        if not self.test_data.get("approved_entries"):
            raise Exception("No approved entries available")
        
        # Post the first entry
        doc_number = self.test_data["approved_entries"][0]
        
        success, message = self.posting_engine.post_journal_entry(
            doc_number, 'TEST', 'uat_poster', date.today()
        )
        
        if not success:
            raise Exception(f"Individual posting failed: {message}")
        
        # Verify posting status
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
        """Test 4: Batch posting"""
        
        results = {}
        
        # Get remaining entries
        remaining_entries = [doc for doc in self.test_data["approved_entries"] 
                           if doc != self.test_data.get("posted_individual")]
        
        if not remaining_entries:
            raise Exception("No entries available for batch posting")
        
        batch_results = self.posting_engine.post_multiple_journal_entries(
            remaining_entries, 'TEST', 'uat_poster', date.today()
        )
        
        if batch_results["posted_successfully"] == 0:
            raise Exception("Batch posting failed")
        
        results["batch_results"] = batch_results
        results["successful_posts"] = batch_results["posted_successfully"]
        
        print(f"   Batch posted: {results['successful_posts']} documents")
        return results
    
    def _test_account_balances(self) -> Dict:
        """Test 5: Account balances verification"""
        
        results = {}
        
        # Check balances for test accounts
        test_accounts = ['100001', '300001']
        
        for account in test_accounts:
            balance = self.posting_engine.get_account_balance('TEST', account)
            results[f"account_{account}"] = balance
            
            print(f"   Account {account} - YTD Balance: ${balance.get('ytd_balance', 0):,.2f}")
        
        # Verify balances
        cash_balance = results.get("account_100001", {}).get("ytd_balance", 0)
        revenue_balance = results.get("account_300001", {}).get("ytd_balance", 0)
        
        if cash_balance <= 0:
            raise Exception(f"Cash account balance incorrect: {cash_balance}")
        
        if revenue_balance >= 0:
            raise Exception(f"Revenue account balance incorrect: {revenue_balance}")
        
        # Check balance equation
        if abs(cash_balance + revenue_balance) > 0.01:
            raise Exception(f"Accounts don't balance: Cash {cash_balance} + Revenue {revenue_balance}")
        
        results["balance_check"] = "PASSED"
        return results
    
    def _test_preview_functionality(self) -> Dict:
        """Test 6: Preview functionality"""
        
        results = {}
        
        posted_doc = self.test_data.get("posted_individual")
        if not posted_doc:
            raise Exception("No posted document available")
        
        with engine.connect() as conn:
            # Test header data retrieval
            header_result = conn.execute(text("""
                SELECT documentnumber, reference, postingdate, fiscalyear, period,
                       currencycode, createdby, posted_by, posted_at
                FROM journalentryheader
                WHERE documentnumber = :doc AND companycodeid = 'TEST'
            """), {"doc": posted_doc})
            
            header = header_result.fetchone()
            if not header:
                raise Exception("Preview header data not found")
            
            # Test lines data retrieval
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
        
        print(f"   Preview data: {results['header_fields']} header fields, {results['line_count']} lines")
        return results
    
    def _test_security_controls(self) -> Dict:
        """Test 7: Security controls"""
        
        results = {}
        
        # Test segregation of duties
        with engine.connect() as conn:
            with conn.begin():
                test_doc = f"SOD{datetime.now().strftime('%Y%m%d%H%M%S')}"
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
            raise Exception("Segregation of duties failed")
        
        print(f"   Segregation of duties: PASSED - {message}")
        return results
    
    def _test_audit_trail(self) -> Dict:
        """Test 8: Audit trail verification"""
        
        results = {}
        
        with engine.connect() as conn:
            # Check posting audit trail
            result = conn.execute(text("""
                SELECT COUNT(*) FROM posting_audit_trail
                WHERE company_code = 'TEST' AND action_type = 'POST'
                AND action_timestamp >= CURRENT_DATE
            """))
            audit_count = result.fetchone()[0]
            
            # Check GL transactions
            result = conn.execute(text("""
                SELECT COUNT(*) FROM gl_transactions
                WHERE company_code = 'TEST' AND posting_date >= CURRENT_DATE
            """))
            transaction_count = result.fetchone()[0]
            
            # Check posting documents
            result = conn.execute(text("""
                SELECT COUNT(*) FROM posting_documents
                WHERE company_code = 'TEST' AND posting_date >= CURRENT_DATE
            """))
            document_count = result.fetchone()[0]
        
        results["audit_trail_entries"] = audit_count
        results["gl_transactions"] = transaction_count
        results["posting_documents"] = document_count
        
        print(f"   Audit trail: {audit_count} entries")
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
        """Generate UAT report"""
        
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
    """Main function to run simplified UAT"""
    
    uat = SimplifiedGLPostingUAT()
    report = uat.run_simplified_uat()
    
    print("\n" + "=" * 60)
    print("🏁 SIMPLIFIED UAT COMPLETION SUMMARY")
    print("=" * 60)
    
    summary = report["uat_summary"]
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed_tests']}")
    print(f"Failed: {summary['failed_tests']}")
    print(f"Success Rate: {summary['success_rate']:.1f}%")
    print(f"Overall Status: {summary['status']}")
    
    # Save report
    report_file = f"/home/anton/erp/gl/tests/SIMPLIFIED_UAT_GL_POSTING_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\nDetailed report saved to: {report_file}")
    
    return report

if __name__ == "__main__":
    main()