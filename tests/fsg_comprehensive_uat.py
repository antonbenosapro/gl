"""
Field Status Group Comprehensive User Acceptance Testing (UAT)
Tests all 3 levels of FSG hierarchy with real-world scenarios

Test Scenarios:
1. Document Type Override Level (Highest Priority)
2. GL Account Specific Level (Medium Priority) 
3. Account Group Default Level (Lowest Priority)
4. Field Status Types (REQ, OPT, SUP, DIS)
5. Real-world posting scenarios
6. Error handling and edge cases

Author: Claude Code Assistant
Date: August 7, 2025
"""

import sys
import os
sys.path.append('/home/anton/erp/gl')

import json
from datetime import datetime, date
from utils.field_status_validation import (
    FieldStatusGroupEngine,
    PostingData,
    FieldStatusType,
    validate_journal_entry_line,
    get_field_controls_for_account,
    field_status_engine
)
from db_config import engine
from sqlalchemy import text


class FSGUATRunner:
    """Comprehensive UAT test runner for Field Status Groups"""
    
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        
    def log_test(self, test_name, expected, actual, passed, details=""):
        """Log test result"""
        result = {
            "test_name": test_name,
            "expected": expected,
            "actual": actual,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        
        if passed:
            self.passed += 1
            print(f"✅ {test_name}")
            if details:
                print(f"   Details: {details}")
        else:
            self.failed += 1
            print(f"❌ {test_name}")
            print(f"   Expected: {expected}")
            print(f"   Actual: {actual}")
            if details:
                print(f"   Details: {details}")
        print()

    def run_level1_document_type_tests(self):
        """Test Level 1: Document Type Override (Highest Priority)"""
        print("🔴 LEVEL 1 TESTS: Document Type Override (Highest Priority)")
        print("=" * 60)
        
        # Test 1.1: General Journal (SA) should use ASSET01 FSG
        fsg = field_status_engine.get_effective_field_status_group(
            document_type='SA',
            gl_account_id='400001'  # Revenue account that normally uses REV01
        )
        
        self.log_test(
            "L1.1 - General Journal uses ASSET01 FSG (overrides account FSG)",
            "ASSET01",
            fsg.group_id if fsg else None,
            fsg and fsg.group_id == 'ASSET01',
            f"Document SA overrides account 400001's normal FSG"
        )
        
        # Test 1.2: Cash Journal (CA) should use CASH01 FSG
        fsg = field_status_engine.get_effective_field_status_group(
            document_type='CA',
            gl_account_id='400001'  # Revenue account
        )
        
        self.log_test(
            "L1.2 - Cash Journal uses CASH01 FSG (overrides account FSG)",
            "CASH01", 
            fsg.group_id if fsg else None,
            fsg and fsg.group_id == 'CASH01',
            f"Document CA overrides account 400001's normal FSG"
        )
        
        # Test 1.3: Customer Invoice (DR) should use RECV01 FSG
        fsg = field_status_engine.get_effective_field_status_group(
            document_type='DR',
            gl_account_id='100010'  # Cash account
        )
        
        self.log_test(
            "L1.3 - Customer Invoice uses RECV01 FSG (overrides account FSG)",
            "RECV01",
            fsg.group_id if fsg else None, 
            fsg and fsg.group_id == 'RECV01',
            f"Document DR overrides account 100010's normal FSG"
        )
        
        # Test 1.4: Document type validation with ASSET01 (Business Unit = OPT)
        is_valid, errors = validate_journal_entry_line(
            document_type='SA',       # Uses ASSET01
            gl_account_id='400001',   # Revenue account
            business_unit_id=None,    # ASSET01 makes this OPT
            tax_code=None,           # ASSET01 makes this SUP
            line_number=1
        )
        
        self.log_test(
            "L1.4 - ASSET01 validation (Business Unit OPT, Tax Code SUP)",
            True,
            is_valid,
            is_valid == True,
            f"ASSET01 should allow missing business unit and tax code"
        )

    def run_level2_account_specific_tests(self):
        """Test Level 2: GL Account Specific (Medium Priority)"""
        print("🟡 LEVEL 2 TESTS: GL Account Specific (Medium Priority)")
        print("=" * 60)
        
        # Test 2.1: Revenue account without document type should use its FSG
        fsg = field_status_engine.get_effective_field_status_group(
            gl_account_id='400001'  # Revenue account should use REV01
        )
        
        self.log_test(
            "L2.1 - Revenue account uses REV01 FSG (no document override)",
            "REV01",
            fsg.group_id if fsg else None,
            fsg and fsg.group_id == 'REV01',
            "Account 400001 should inherit REV01 from its account group"
        )
        
        # Test 2.2: Cash account should use CASH01 FSG
        fsg = field_status_engine.get_effective_field_status_group(
            gl_account_id='100010'  # Cash account should use CASH01
        )
        
        self.log_test(
            "L2.2 - Cash account uses CASH01 FSG (no document override)",
            "CASH01",
            fsg.group_id if fsg else None,
            fsg and fsg.group_id == 'CASH01',
            "Account 100010 should inherit CASH01 from its account group"
        )
        
        # Test 2.3: Revenue account validation (REV01 requires Business Unit + Tax Code)
        is_valid, errors = validate_journal_entry_line(
            document_type=None,       # No document type to test account-level FSG
            gl_account_id='400001',   # Revenue account (REV01)
            business_unit_id=None,    # REV01 requires this
            tax_code=None,           # REV01 requires this
            business_area=None,      # REV01 requires this
            line_number=1
        )
        
        expected_errors = 3  # Business Unit, Tax Code, Business Area all required
        actual_errors = len(errors)
        
        self.log_test(
            "L2.3 - REV01 validation (Business Unit, Tax Code, Business Area required)",
            f"False, {expected_errors} errors",
            f"{is_valid}, {actual_errors} errors",
            is_valid == False and actual_errors >= 3,
            f"Errors: {errors[:3] if errors else 'None'}"
        )
        
        # Test 2.4: Cash account validation (CASH01 suppresses Business Unit)
        is_valid, errors = validate_journal_entry_line(
            document_type=None,       # No document type to test account-level FSG
            gl_account_id='100010',   # Cash account (CASH01)
            business_unit_id='123',   # CASH01 suppresses this
            line_number=1
        )
        
        self.log_test(
            "L2.4 - CASH01 validation (Business Unit suppressed)",
            "False, 1+ errors",
            f"{is_valid}, {len(errors)} errors",
            is_valid == False and len(errors) >= 1,
            f"Should error on suppressed Business Unit: {errors[0] if errors else 'No error'}"
        )

    def run_level3_account_group_tests(self):
        """Test Level 3: Account Group Default (Lowest Priority)"""  
        print("🟢 LEVEL 3 TESTS: Account Group Default (Lowest Priority)")
        print("=" * 60)
        
        # Get account group assignments from database
        try:
            with engine.connect() as conn:
                account_groups = conn.execute(text("""
                    SELECT ag.group_code, ag.group_name, ag.default_field_status_group,
                           COUNT(ga.glaccountid) as account_count
                    FROM account_groups ag 
                    LEFT JOIN glaccount ga ON ag.group_code = ga.account_group_code
                    WHERE ag.is_active = TRUE AND ag.default_field_status_group IS NOT NULL
                    GROUP BY ag.group_code, ag.group_name, ag.default_field_status_group
                    ORDER BY ag.group_code
                """)).fetchall()
                
                # Test 3.1: Verify all account groups have default FSG
                self.log_test(
                    "L3.1 - All active account groups have default FSG",
                    ">= 10 groups",
                    f"{len(account_groups)} groups",
                    len(account_groups) >= 10,
                    f"Groups with FSG: {[row[0] for row in account_groups]}"
                )
                
                # Test 3.2: Check specific account group mappings
                group_mappings = {row[0]: row[2] for row in account_groups}
                
                expected_mappings = {
                    'SALE': 'REV01',   # Revenue accounts
                    'CASH': 'CASH01',  # Cash accounts  
                    'OPEX': 'EXP01',   # Expense accounts
                    'COGS': 'COGS01',  # Cost of goods sold
                }
                
                for group_code, expected_fsg in expected_mappings.items():
                    actual_fsg = group_mappings.get(group_code)
                    self.log_test(
                        f"L3.2 - Account Group {group_code} maps to {expected_fsg}",
                        expected_fsg,
                        actual_fsg,
                        actual_fsg == expected_fsg,
                        f"Group {group_code} should use {expected_fsg} as default FSG"
                    )
                
        except Exception as e:
            self.log_test(
                "L3.1 - Database connectivity for account group test",
                "Success",
                f"Error: {e}",
                False,
                "Could not load account group data"
            )

    def run_field_status_type_tests(self):
        """Test Field Status Types (REQ, OPT, SUP, DIS)"""
        print("🔵 FIELD STATUS TYPE TESTS: REQ, OPT, SUP, DIS")  
        print("=" * 60)
        
        # Test 4.1: REQ (Required) field validation
        is_valid, errors = validate_journal_entry_line(
            document_type=None,       # No document type - use account FSG
            gl_account_id='400001',   # Revenue account (REV01)
            business_unit_id=None,    # Required but missing
            tax_code='V1',           # Required and provided
            business_area='US',      # Required and provided  
            line_number=1
        )
        
        business_unit_error = any('Business Unit' in error and 'required' in error for error in errors)
        
        self.log_test(
            "ST.1 - REQ field validation (missing required field)",
            "False, Business Unit error",
            f"{is_valid}, BU error: {business_unit_error}",
            is_valid == False and business_unit_error,
            f"Should fail with Business Unit required error"
        )
        
        # Test 4.2: SUP (Suppressed) field validation  
        is_valid, errors = validate_journal_entry_line(
            document_type=None,       # No document type - use account FSG
            gl_account_id='100010',   # Cash account (CASH01)
            business_unit_id='123',   # Suppressed but provided
            line_number=1
        )
        
        suppression_error = any('should not be provided' in error and 'SUP' in error for error in errors)
        
        self.log_test(
            "ST.2 - SUP field validation (provided suppressed field)",
            "False, Suppression error", 
            f"{is_valid}, Suppression error: {suppression_error}",
            is_valid == False and suppression_error,
            f"Should fail with suppression error"
        )
        
        # Test 4.3: OPT (Optional) field validation
        is_valid, errors = validate_journal_entry_line(
            document_type=None,       # No document type - use account FSG
            gl_account_id='120000',   # Asset account (ASSET01) 
            business_unit_id=None,    # Optional - not required
            tax_code=None,           # Suppressed - should be empty
            line_number=1
        )
        
        self.log_test(
            "ST.3 - OPT field validation (optional field not provided)",
            "True", 
            f"{is_valid}",
            is_valid == True,
            f"Optional fields should not cause validation errors"
        )

    def run_real_world_scenarios(self):
        """Test real-world posting scenarios"""
        print("🌎 REAL-WORLD SCENARIO TESTS")
        print("=" * 60)
        
        # Scenario 1: Complete Sales Invoice Entry
        print("Scenario 1: Sales Invoice Journal Entry")
        
        # Debit: Accounts Receivable (require customer info)
        is_valid_debit, debit_errors = validate_journal_entry_line(
            document_type='DR',      # Customer Invoice
            gl_account_id='110000',  # Accounts Receivable  
            business_unit_id='100',  # Sales division
            business_area='NORTH',   # North region
            line_number=1
        )
        
        # Credit: Sales Revenue (require business unit and tax)
        is_valid_credit, credit_errors = validate_journal_entry_line(
            document_type='DR',      # Customer Invoice
            gl_account_id='400001',  # Sales Revenue
            business_unit_id='100',  # Sales division
            tax_code='V1',          # Sales tax
            business_area='NORTH',   # North region  
            line_number=2
        )
        
        overall_valid = is_valid_debit and is_valid_credit
        total_errors = len(debit_errors) + len(credit_errors)
        
        self.log_test(
            "RW.1 - Complete Sales Invoice Entry",
            "Both lines valid",
            f"Debit: {is_valid_debit}, Credit: {is_valid_credit}, Total errors: {total_errors}",
            overall_valid and total_errors == 0,
            f"Sales invoice should pass all validations"
        )
        
        # Scenario 2: Cash Receipt Entry
        print("Scenario 2: Cash Receipt Entry")
        
        # Debit: Cash Account (minimal requirements)
        is_valid_cash, cash_errors = validate_journal_entry_line(
            document_type='CA',      # Cash Journal
            gl_account_id='100010',  # Cash in Bank
            business_unit_id=None,   # CASH01 suppresses this
            line_number=1
        )
        
        self.log_test(
            "RW.2 - Cash Receipt Entry", 
            "Valid",
            f"{is_valid_cash}, errors: {len(cash_errors)}",
            is_valid_cash and len(cash_errors) == 0,
            f"Cash entries should have minimal field requirements"
        )
        
        # Scenario 3: Expense Entry (missing required fields)
        print("Scenario 3: Expense Entry with Missing Fields")
        
        is_valid_expense, expense_errors = validate_journal_entry_line(
            document_type=None,      # No document type - use account FSG
            gl_account_id='500001',  # Operating Expenses
            business_unit_id=None,   # EXP01 requires this
            business_area=None,      # EXP01 requires this  
            line_number=1
        )
        
        expected_expense_errors = 2  # Business Unit + Business Area
        
        self.log_test(
            "RW.3 - Expense Entry Missing Required Fields",
            f"False, {expected_expense_errors}+ errors",
            f"{is_valid_expense}, {len(expense_errors)} errors", 
            is_valid_expense == False and len(expense_errors) >= 2,
            f"Expense accounts should require business unit and area"
        )

    def run_edge_case_tests(self):
        """Test edge cases and error handling"""
        print("🔬 EDGE CASE TESTS")
        print("=" * 60)
        
        # Test E.1: Invalid GL Account
        fsg = field_status_engine.get_effective_field_status_group(
            gl_account_id='999999'  # Non-existent account
        )
        
        self.log_test(
            "E.1 - Invalid GL Account handling",
            "None (graceful failure)",
            f"{fsg}",
            fsg is None,
            "Should gracefully handle non-existent accounts"
        )
        
        # Test E.2: Invalid Document Type  
        fsg = field_status_engine.get_effective_field_status_group(
            document_type='XX',      # Non-existent document type
            gl_account_id='400001'   # Valid account
        )
        
        # Should fallback to account-level FSG
        self.log_test(
            "E.2 - Invalid Document Type handling",
            "REV01 (fallback to account FSG)",
            fsg.group_id if fsg else None,
            fsg and fsg.group_id == 'REV01',
            "Should fallback to account FSG when document type not found"
        )
        
        # Test E.3: Empty field values
        is_valid, errors = validate_journal_entry_line(
            document_type=None,       # No document type - use account FSG
            gl_account_id='400001',   # Revenue account
            business_unit_id='',      # Empty string (should be treated as None)
            tax_code='   ',          # Whitespace only
            line_number=1
        )
        
        self.log_test(
            "E.3 - Empty field value handling",
            "False, validation errors",
            f"{is_valid}, {len(errors)} errors",
            is_valid == False and len(errors) >= 2,
            "Empty strings and whitespace should be treated as missing"
        )

    def run_performance_tests(self):
        """Test performance characteristics"""
        print("⚡ PERFORMANCE TESTS")
        print("=" * 60)
        
        import time
        
        # Test P.1: FSG Cache Performance
        start_time = time.time()
        
        # Load same FSG multiple times (should use cache)
        for _ in range(100):
            fsg = field_status_engine.get_effective_field_status_group(gl_account_id='400001')
            
        cache_time = time.time() - start_time
        
        self.log_test(
            "P.1 - FSG Cache Performance (100 lookups)",
            "< 0.1 seconds",
            f"{cache_time:.3f} seconds",
            cache_time < 0.1,
            f"Cached lookups should be very fast"
        )
        
        # Test P.2: Validation Performance
        start_time = time.time()
        
        # Validate 100 journal lines
        for i in range(100):
            is_valid, errors = validate_journal_entry_line(
                document_type=None,       # No document type - use account FSG
                gl_account_id='400001',
                business_unit_id='123', 
                tax_code='V1',
                business_area='US',
                line_number=i+1
            )
            
        validation_time = time.time() - start_time
        
        self.log_test(
            "P.2 - Validation Performance (100 validations)",
            "< 1.0 seconds",
            f"{validation_time:.3f} seconds",
            validation_time < 1.0,
            f"Validation should be fast enough for real-time use"
        )

    def generate_report(self):
        """Generate comprehensive UAT report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        report = {
            "uat_summary": {
                "test_date": datetime.now().isoformat(),
                "total_tests": len(self.results),
                "tests_passed": self.passed,
                "tests_failed": self.failed,
                "success_rate": f"{(self.passed/len(self.results)*100):.1f}%" if self.results else "0%",
                "overall_status": "PASS" if self.failed == 0 else "FAIL"
            },
            "test_categories": {
                "level_1_document_type": {"tests": 4, "description": "Document Type Override Tests"},
                "level_2_account_specific": {"tests": 4, "description": "GL Account Specific Tests"},
                "level_3_account_group": {"tests": 6, "description": "Account Group Default Tests"},
                "field_status_types": {"tests": 3, "description": "Field Status Type Tests"},
                "real_world_scenarios": {"tests": 3, "description": "Real-World Scenario Tests"},
                "edge_cases": {"tests": 3, "description": "Edge Case Tests"},
                "performance": {"tests": 2, "description": "Performance Tests"}
            },
            "detailed_results": self.results
        }
        
        # Save report to file
        report_file = f"fsg_uat_report_{timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report_file, report

    def run_all_tests(self):
        """Run complete FSG UAT test suite"""
        print("🧪 FIELD STATUS GROUP COMPREHENSIVE UAT")
        print("=" * 80)
        print(f"Test Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print()
        
        # Clear cache to ensure fresh tests
        field_status_engine.clear_cache()
        
        # Run all test categories
        self.run_level1_document_type_tests()
        self.run_level2_account_specific_tests()  
        self.run_level3_account_group_tests()
        self.run_field_status_type_tests()
        self.run_real_world_scenarios()
        self.run_edge_case_tests()
        self.run_performance_tests()
        
        # Generate final report
        print("📊 GENERATING FINAL REPORT")
        print("=" * 60)
        
        report_file, report = self.generate_report()
        
        # Print summary
        summary = report["uat_summary"]
        print(f"🎯 UAT SUMMARY")
        print(f"   Total Tests: {summary['total_tests']}")
        print(f"   Passed: {summary['tests_passed']}")
        print(f"   Failed: {summary['tests_failed']}")
        print(f"   Success Rate: {summary['success_rate']}")
        print(f"   Overall Status: {summary['overall_status']}")
        print()
        
        if summary['overall_status'] == 'PASS':
            print("🎉 ALL FSG UAT TESTS PASSED!")
            print("✅ Field Status Group Validation Engine is ready for production!")
        else:
            print("❌ Some FSG UAT tests failed - review detailed results")
            
        print(f"📁 Detailed report saved to: {report_file}")
        
        return report_file, summary['overall_status'] == 'PASS'


def main():
    """Main UAT execution function"""
    uat_runner = FSGUATRunner()
    report_file, all_passed = uat_runner.run_all_tests()
    
    return report_file, all_passed


if __name__ == "__main__":
    main()