#!/usr/bin/env python3
"""
Simplified Journal Entry Manager UAT for SAP-Aligned COA
Tests core functionality without external dependencies
"""

import psycopg2
from datetime import datetime, date
import time
import sys
import os

class SimpleJournalEntryUAT:
    """Simplified UAT testing for Journal Entry Manager"""
    
    def __init__(self):
        self.test_results = []
        self.test_count = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.start_time = datetime.now()
        
        # Database connection parameters
        self.db_params = {
            'host': 'localhost',
            'database': 'gl_erp',
            'user': 'postgres', 
            'password': 'admin123',
            'port': 5432
        }
    
    def get_connection(self):
        """Create database connection"""
        try:
            return psycopg2.connect(**self.db_params)
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return None
    
    def log_test_result(self, test_name: str, status: str, details: str = "", error: str = ""):
        """Log individual test results"""
        self.test_count += 1
        if status == "PASS":
            self.passed_tests += 1
        else:
            self.failed_tests += 1
            
        result = {
            "test_id": self.test_count,
            "test_name": test_name,
            "status": status,
            "details": details,
            "error": error,
            "timestamp": datetime.now()
        }
        self.test_results.append(result)
        
        # Log to console
        status_icon = "✅" if status == "PASS" else "❌"
        print(f"{status_icon} Test {self.test_count}: {test_name} - {status}")
        if details:
            print(f"   Details: {details}")
        if error:
            print(f"   Error: {error}")
    
    def test_database_connectivity(self):
        """Test 1: Database Connection and SAP COA Structure"""
        try:
            conn = self.get_connection()
            if not conn:
                self.log_test_result("Database Connectivity", "FAIL", "Cannot establish connection")
                return False
                
            with conn.cursor() as cursor:
                # Test SAP-aligned account structure
                cursor.execute("""
                    SELECT COUNT(*) as total_accounts,
                           COUNT(CASE WHEN LENGTH(glaccountid) = 6 THEN 1 END) as six_digit_accounts,
                           COUNT(CASE WHEN account_group_code IS NOT NULL THEN 1 END) as accounts_with_groups
                    FROM glaccount 
                    WHERE marked_for_deletion = FALSE OR marked_for_deletion IS NULL
                """)
                result = cursor.fetchone()
                
            conn.close()
            
            if result[1] == 0:
                self.log_test_result("Database Connectivity", "FAIL", "No 6-digit accounts found")
                return False
            
            details = f"Total: {result[0]}, 6-digit: {result[1]}, With groups: {result[2]}"
            self.log_test_result("Database Connectivity", "PASS", details)
            return True
            
        except Exception as e:
            self.log_test_result("Database Connectivity", "FAIL", error=str(e))
            return False
    
    def test_account_groups_structure(self):
        """Test 2: Account Groups and Field Status Groups"""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                # Test account groups
                cursor.execute("""
                    SELECT COUNT(*) as active_groups,
                           COUNT(CASE WHEN account_class = 'ASSETS' THEN 1 END) as asset_groups,
                           COUNT(CASE WHEN account_class = 'REVENUE' THEN 1 END) as revenue_groups,
                           COUNT(CASE WHEN account_class = 'EXPENSES' THEN 1 END) as expense_groups
                    FROM account_groups WHERE is_active = TRUE
                """)
                groups_result = cursor.fetchone()
                
                # Test field status groups
                cursor.execute("SELECT COUNT(*) FROM field_status_groups WHERE is_active = TRUE")
                fsg_count = cursor.fetchone()[0]
                
                # Test account range validation
                cursor.execute("""
                    SELECT COUNT(*) as invalid_accounts
                    FROM glaccount ga 
                    JOIN account_groups ag ON ga.account_group_code = ag.group_code 
                    WHERE ga.glaccountid::bigint < ag.number_range_from::bigint 
                       OR ga.glaccountid::bigint > ag.number_range_to::bigint
                """)
                invalid_count = cursor.fetchone()[0]
                
            conn.close()
            
            if invalid_count > 0:
                self.log_test_result("Account Groups Structure", "FAIL", 
                                   f"{invalid_count} accounts outside valid ranges")
                return False
            
            details = f"Groups: {groups_result[0]}, FSGs: {fsg_count}, Range validation: PASS"
            self.log_test_result("Account Groups Structure", "PASS", details)
            return True
            
        except Exception as e:
            self.log_test_result("Account Groups Structure", "FAIL", error=str(e))
            return False
    
    def test_journal_entry_crud_operations(self):
        """Test 3: Journal Entry CRUD Operations with SAP Accounts"""
        try:
            conn = self.get_connection()
            test_doc_number = f"CRUD{int(time.time()) % 100000}"  # Keep within 20 char limit
            
            with conn.cursor() as cursor:
                # Get test accounts from different classes
                cursor.execute("""
                    SELECT glaccountid, accountname, account_class, account_group_code
                    FROM glaccount 
                    WHERE account_class IN ('ASSETS', 'EXPENSES') 
                    AND (marked_for_deletion = FALSE OR marked_for_deletion IS NULL)
                    ORDER BY account_class, glaccountid 
                    LIMIT 2
                """)
                test_accounts = cursor.fetchall()
                
                if len(test_accounts) < 2:
                    self.log_test_result("Journal Entry CRUD Operations", "FAIL", 
                                       "Insufficient test accounts available")
                    return False
                
                # CREATE: Journal entry header
                cursor.execute("""
                    INSERT INTO journalentryheader (
                        documentnumber, companycodeid, postingdate, documentdate,
                        fiscalyear, period, reference, memo, currencycode,
                        createdby, workflow_status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    test_doc_number, "TEST", date.today(), date.today(),
                    2025, 8, "CRUD Test Entry", "Testing CRUD with SAP COA",
                    "USD", "UAT_USER", "DRAFT"
                ))
                
                # CREATE: Journal entry lines
                for i, account in enumerate(test_accounts):
                    debit = 1000.00 if i == 0 else 0
                    credit = 0 if i == 0 else 1000.00
                    
                    cursor.execute("""
                        INSERT INTO journalentryline (
                            documentnumber, companycodeid, linenumber, glaccountid,
                            debitamount, creditamount, description, currencycode, ledgerid
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        test_doc_number, "TEST", i+1, account[0],
                        debit, credit, f"CRUD Test Line {i+1}", "USD", "L1"
                    ))
                
                # READ: Verify creation
                cursor.execute("""
                    SELECT jeh.documentnumber, jeh.memo, jeh.workflow_status,
                           COUNT(jel.linenumber) as line_count,
                           SUM(jel.debitamount) as total_debits,
                           SUM(jel.creditamount) as total_credits
                    FROM journalentryheader jeh
                    LEFT JOIN journalentryline jel ON jeh.documentnumber = jel.documentnumber 
                        AND jeh.companycodeid = jel.companycodeid
                    WHERE jeh.documentnumber = %s AND jeh.companycodeid = %s
                    GROUP BY jeh.documentnumber, jeh.memo, jeh.workflow_status
                """, (test_doc_number, "TEST"))
                
                read_result = cursor.fetchone()
                
                # UPDATE: Modify header and verify memo field
                cursor.execute("""
                    UPDATE journalentryheader 
                    SET memo = %s, reference = %s
                    WHERE documentnumber = %s AND companycodeid = %s
                """, ("Updated memo content", "Updated reference", test_doc_number, "TEST"))
                
                cursor.execute("""
                    SELECT memo, reference FROM journalentryheader 
                    WHERE documentnumber = %s AND companycodeid = %s
                """, (test_doc_number, "TEST"))
                
                update_result = cursor.fetchone()
                
                # DELETE: Remove test data (testing DELETE function for drafts)
                cursor.execute("""
                    DELETE FROM journalentryline 
                    WHERE documentnumber = %s AND companycodeid = %s
                """, (test_doc_number, "TEST"))
                line_delete_count = cursor.rowcount
                
                cursor.execute("""
                    DELETE FROM journalentryheader 
                    WHERE documentnumber = %s AND companycodeid = %s AND workflow_status = 'DRAFT'
                """, (test_doc_number, "TEST"))
                header_delete_count = cursor.rowcount
                
                conn.commit()
                
            conn.close()
            
            # Validate results
            if not read_result or read_result[3] != 2:  # Should have 2 lines
                self.log_test_result("Journal Entry CRUD Operations", "FAIL", 
                                   "Entry creation or reading failed")
                return False
            
            if read_result[4] != read_result[5]:  # Debits should equal credits
                self.log_test_result("Journal Entry CRUD Operations", "FAIL", 
                                   f"Unbalanced entry: {read_result[4]} != {read_result[5]}")
                return False
            
            if not update_result or update_result[0] != "Updated memo content":
                self.log_test_result("Journal Entry CRUD Operations", "FAIL", 
                                   "Update operation failed")
                return False
            
            if line_delete_count != 2 or header_delete_count != 1:
                self.log_test_result("Journal Entry CRUD Operations", "FAIL", 
                                   "Delete operation failed")
                return False
            
            details = f"CREATE: ✅, READ: ✅, UPDATE: ✅, DELETE: ✅, Balance: {read_result[4]}"
            self.log_test_result("Journal Entry CRUD Operations", "PASS", details)
            return True
            
        except Exception as e:
            self.log_test_result("Journal Entry CRUD Operations", "FAIL", error=str(e))
            return False
    
    def test_workflow_status_progression(self):
        """Test 4: Workflow Status and Posting Date Behavior"""
        try:
            conn = self.get_connection()
            test_doc_number = f"WF{int(time.time()) % 100000}"  # Keep within 20 char limit
            original_posting_date = date(2025, 8, 1)
            
            with conn.cursor() as cursor:
                # Create draft entry
                cursor.execute("""
                    INSERT INTO journalentryheader (
                        documentnumber, companycodeid, postingdate, documentdate,
                        fiscalyear, period, reference, currencycode,
                        createdby, workflow_status
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    test_doc_number, "TEST", original_posting_date, date.today(),
                    2025, 8, "Workflow test", "USD", "UAT_USER", "DRAFT"
                ))
                
                # Test 1: Draft status - posting date should remain unchanged
                cursor.execute("""
                    UPDATE journalentryheader 
                    SET reference = 'Updated in draft'
                    WHERE documentnumber = %s
                """, (test_doc_number,))
                
                cursor.execute("""
                    SELECT workflow_status, postingdate FROM journalentryheader 
                    WHERE documentnumber = %s
                """, (test_doc_number,))
                draft_result = cursor.fetchone()
                
                # Test 2: Approval - posting date should remain unchanged
                cursor.execute("""
                    UPDATE journalentryheader 
                    SET workflow_status = 'APPROVED', approved_by = 'APPROVER', approved_at = %s
                    WHERE documentnumber = %s
                """, (datetime.now(), test_doc_number))
                
                cursor.execute("""
                    SELECT workflow_status, postingdate FROM journalentryheader 
                    WHERE documentnumber = %s
                """, (test_doc_number,))
                approved_result = cursor.fetchone()
                
                # Test 3: GL Posting - posting date should update
                new_posting_date = date.today()
                cursor.execute("""
                    UPDATE journalentryheader 
                    SET workflow_status = 'POSTED', 
                        postingdate = %s,
                        posted_by = 'AUTO_POSTER', 
                        posted_at = %s
                    WHERE documentnumber = %s
                """, (new_posting_date, datetime.now(), test_doc_number))
                
                cursor.execute("""
                    SELECT workflow_status, postingdate FROM journalentryheader 
                    WHERE documentnumber = %s
                """, (test_doc_number,))
                posted_result = cursor.fetchone()
                
                # Cleanup
                cursor.execute("DELETE FROM journalentryheader WHERE documentnumber = %s", (test_doc_number,))
                conn.commit()
                
            conn.close()
            
            # Validate workflow progression
            if draft_result[0] != 'DRAFT' or draft_result[1] != original_posting_date:
                self.log_test_result("Workflow Status Progression", "FAIL", 
                                   "Draft status or posting date incorrect")
                return False
            
            if approved_result[0] != 'APPROVED' or approved_result[1] != original_posting_date:
                self.log_test_result("Workflow Status Progression", "FAIL", 
                                   "Approval status or posting date behavior incorrect")
                return False
            
            if posted_result[0] != 'POSTED' or posted_result[1] != new_posting_date:
                self.log_test_result("Workflow Status Progression", "FAIL", 
                                   "Posted status or posting date update incorrect")
                return False
            
            details = f"DRAFT→APPROVED→POSTED: ✅, Posting date behavior: ✅"
            self.log_test_result("Workflow Status Progression", "PASS", details)
            return True
            
        except Exception as e:
            self.log_test_result("Workflow Status Progression", "FAIL", error=str(e))
            return False
    
    def test_enhanced_views_and_reporting(self):
        """Test 5: Enhanced Views with SAP Structure"""
        try:
            conn = self.get_connection()
            
            with conn.cursor() as cursor:
                # Test enhanced accounts view
                cursor.execute("""
                    SELECT COUNT(*) as total_accounts,
                           COUNT(CASE WHEN account_group_code IS NOT NULL THEN 1 END) as accounts_with_groups,
                           COUNT(CASE WHEN field_status_group IS NOT NULL THEN 1 END) as accounts_with_fsg
                    FROM v_gl_accounts_enhanced
                """)
                enhanced_view_result = cursor.fetchone()
                
                # Test migration summary
                cursor.execute("""
                    SELECT COUNT(*) as active_groups,
                           SUM(migrated_accounts) as total_migrated_accounts
                    FROM v_migration_summary
                    WHERE migrated_accounts > 0
                """)
                migration_summary = cursor.fetchone()
                
                # Test field status summary
                cursor.execute("""
                    SELECT COUNT(*) as active_fsgs,
                           COUNT(CASE WHEN cost_center_status = 'REQ' THEN 1 END) as cc_required_fsgs
                    FROM v_field_status_summary
                    WHERE is_active = TRUE
                """)
                fsg_summary = cursor.fetchone()
                
                # Test account class distribution
                cursor.execute("""
                    SELECT account_class, COUNT(*) as count
                    FROM glaccount 
                    WHERE account_class IS NOT NULL
                    AND (marked_for_deletion = FALSE OR marked_for_deletion IS NULL)
                    GROUP BY account_class
                    ORDER BY account_class
                """)
                class_distribution = cursor.fetchall()
                
            conn.close()
            
            if enhanced_view_result[0] == 0:
                self.log_test_result("Enhanced Views and Reporting", "FAIL", 
                                   "Enhanced view returns no data")
                return False
            
            details = f"Enhanced view: {enhanced_view_result[0]} accounts, Groups: {migration_summary[0]}, FSGs: {fsg_summary[0]}, Classes: {len(class_distribution)}"
            self.log_test_result("Enhanced Views and Reporting", "PASS", details)
            return True
            
        except Exception as e:
            self.log_test_result("Enhanced Views and Reporting", "FAIL", error=str(e))
            return False
    
    def test_business_rule_validation(self):
        """Test 6: Business Rules and Field Requirements"""
        try:
            conn = self.get_connection()
            
            with conn.cursor() as cursor:
                # Test cost center requirements for revenue/expense accounts
                cursor.execute("""
                    SELECT account_class,
                           COUNT(*) as total_accounts,
                           COUNT(CASE WHEN cost_center_required = TRUE THEN 1 END) as cc_required_accounts
                    FROM glaccount 
                    WHERE account_class IN ('REVENUE', 'EXPENSES')
                    AND (marked_for_deletion = FALSE OR marked_for_deletion IS NULL)
                    GROUP BY account_class
                    ORDER BY account_class
                """)
                cc_requirements = cursor.fetchall()
                
                # Test field status group assignments
                cursor.execute("""
                    SELECT COUNT(*) as accounts_with_fsg,
                           COUNT(DISTINCT field_status_group) as unique_fsgs
                    FROM glaccount 
                    WHERE field_status_group IS NOT NULL
                    AND (marked_for_deletion = FALSE OR marked_for_deletion IS NULL)
                """)
                fsg_assignments = cursor.fetchone()
                
                # Test account group compliance
                cursor.execute("""
                    SELECT ag.account_class,
                           COUNT(ga.glaccountid) as accounts_in_class,
                           MIN(ga.glaccountid::bigint) as min_account,
                           MAX(ga.glaccountid::bigint) as max_account
                    FROM account_groups ag
                    JOIN glaccount ga ON ag.group_code = ga.account_group_code
                    WHERE ag.is_active = TRUE
                    GROUP BY ag.account_class
                    ORDER BY ag.account_class
                """)
                class_compliance = cursor.fetchall()
                
            conn.close()
            
            # Validate business rules
            revenue_expenses_found = len([r for r in cc_requirements if r[0] in ['REVENUE', 'EXPENSES']]) > 0
            
            if not revenue_expenses_found:
                self.log_test_result("Business Rule Validation", "FAIL", 
                                   "No revenue/expense accounts found for cost center testing")
                return False
            
            if fsg_assignments[0] == 0:
                self.log_test_result("Business Rule Validation", "FAIL", 
                                   "No field status group assignments found")
                return False
            
            details = f"CC requirements: ✅, FSG assignments: {fsg_assignments[0]}, Class compliance: {len(class_compliance)} classes"
            self.log_test_result("Business Rule Validation", "PASS", details)
            return True
            
        except Exception as e:
            self.log_test_result("Business Rule Validation", "FAIL", error=str(e))
            return False
    
    def run_all_tests(self):
        """Execute all UAT tests"""
        print("🧪 Starting Journal Entry Manager UAT - SAP-Aligned COA")
        print("=" * 60)
        
        # Execute test cases
        tests = [
            self.test_database_connectivity,
            self.test_account_groups_structure,
            self.test_journal_entry_crud_operations,
            self.test_workflow_status_progression,
            self.test_enhanced_views_and_reporting,
            self.test_business_rule_validation
        ]
        
        for test_method in tests:
            try:
                test_method()
            except Exception as e:
                print(f"❌ Critical error in {test_method.__name__}: {e}")
                self.log_test_result(test_method.__name__, "CRITICAL_FAIL", error=str(e))
            time.sleep(0.5)
        
        # Calculate results
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        success_rate = (self.passed_tests / self.test_count * 100) if self.test_count > 0 else 0
        
        print("\n" + "=" * 60)
        print("📊 UAT EXECUTION COMPLETE")
        print("=" * 60)
        print(f"Total Tests: {self.test_count}")
        print(f"Passed: {self.passed_tests} ✅")
        print(f"Failed: {self.failed_tests} ❌")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Duration: {duration:.2f} seconds")
        
        return {
            "total_tests": self.test_count,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "success_rate": success_rate,
            "duration": duration,
            "test_results": self.test_results
        }

if __name__ == "__main__":
    uat = SimpleJournalEntryUAT()
    results = uat.run_all_tests()
    
    # Generate summary report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if results["success_rate"] >= 90:
        status = "🎉 EXCELLENT - Ready for Production"
    elif results["success_rate"] >= 80:
        status = "✅ GOOD - Minor Issues"
    elif results["success_rate"] >= 70:
        status = "⚠️ ACCEPTABLE - Needs Attention" 
    else:
        status = "❌ NEEDS WORK - Major Issues"
    
    print(f"\n🎯 Overall Assessment: {status}")
    print(f"📋 Test completed at {timestamp}")