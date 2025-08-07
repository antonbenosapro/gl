#!/usr/bin/env python3
"""
Field Status Group Validation - Quality Assurance Testing (QAT)
==============================================================
This script performs comprehensive QAT for FSG validation functions.

Test Scope:
1. FSG hierarchy resolution (Document Type → GL Account → Account Group)
2. Field suppression and requirement validation
3. Null value handling
4. Business unit validation triggers
5. Integration with Journal Entry Manager

Author: Claude Code Assistant
Date: August 2025
"""

import sys
import os
import json
import pandas as pd
from datetime import datetime, date
from decimal import Decimal
import traceback

# Add project root to path
sys.path.append('/home/anton/erp/gl')

from sqlalchemy import text
from db_config import engine
from utils.field_status_validation import (
    field_status_engine,
    validate_journal_entry_line,
    PostingData,
    FieldStatusValidationError
)

# Test results storage
test_results = {
    "test_run": datetime.now().isoformat(),
    "test_type": "FSG_VALIDATION_QAT",
    "tests": [],
    "summary": {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0
    }
}

def log_test(test_name, status, details="", error=None):
    """Log test result"""
    test_results["tests"].append({
        "test_name": test_name,
        "status": status,
        "details": details,
        "error": str(error) if error else None,
        "timestamp": datetime.now().isoformat()
    })
    test_results["summary"]["total"] += 1
    if status == "PASS":
        test_results["summary"]["passed"] += 1
    elif status == "FAIL":
        test_results["summary"]["failed"] += 1
    else:
        test_results["summary"]["errors"] += 1
    
    print(f"{'✅' if status == 'PASS' else '❌'} {test_name}: {status}")
    if details:
        print(f"   Details: {details}")
    if error:
        print(f"   Error: {error}")

def test_fsg_hierarchy_resolution():
    """Test FSG hierarchy resolution logic"""
    test_name = "FSG Hierarchy Resolution"
    try:
        # Test 1: Document Type FSG (highest priority)
        fsg = field_status_engine.get_effective_field_status_group(
            document_type='KA',  # Vendor Invoice
            gl_account_id='200000'  # AP account
        )
        
        if fsg and fsg.group_id == 'VENDOR01':
            log_test(f"{test_name} - Document Type Priority", "PASS", 
                    f"Correctly resolved to VENDOR01 for doc type KA")
        else:
            log_test(f"{test_name} - Document Type Priority", "FAIL",
                    f"Expected VENDOR01, got {fsg.group_id if fsg else 'None'}")
        
        # Test 2: GL Account FSG (medium priority)
        fsg = field_status_engine.get_effective_field_status_group(
            document_type='SA',  # General Journal
            gl_account_id='110000'  # AR account
        )
        
        if fsg and fsg.group_id == 'RECV01':
            log_test(f"{test_name} - GL Account Priority", "PASS",
                    f"Correctly resolved to RECV01 for GL 110000")
        else:
            log_test(f"{test_name} - GL Account Priority", "FAIL",
                    f"Expected RECV01, got {fsg.group_id if fsg else 'None'}")
        
        # Test 3: Account Group FSG (lowest priority)
        fsg = field_status_engine.get_effective_field_status_group(
            document_type='SA',
            gl_account_id='550000'  # Expense account
        )
        
        if fsg and fsg.group_id == 'EXP01':
            log_test(f"{test_name} - Account Group Priority", "PASS",
                    f"Correctly resolved to EXP01 for expense account")
        else:
            log_test(f"{test_name} - Account Group Priority", "FAIL",
                    f"Expected EXP01, got {fsg.group_id if fsg else 'None'}")
            
    except Exception as e:
        log_test(test_name, "ERROR", error=e)

def test_null_value_handling():
    """Test null value handling in FSG validation"""
    test_name = "Null Value Handling"
    try:
        # Test various null representations
        null_values = [None, '', 'nan', 'None', 'none', 'NaN', pd.NA, float('nan')]
        
        for idx, null_val in enumerate(null_values):
            is_valid, errors = validate_journal_entry_line(
                document_type='SA',
                gl_account_id='400001',  # Revenue account that requires BU
                business_unit_id=null_val,
                business_area=null_val,
                tax_code=null_val,
                line_number=idx + 1
            )
            
            # Should fail because business_unit is required for revenue accounts
            if not is_valid and any('Business Unit' in err for err in errors):
                log_test(f"{test_name} - Null Type {idx+1}", "PASS",
                        f"Correctly detected missing required BU for null type: {type(null_val)}")
            else:
                log_test(f"{test_name} - Null Type {idx+1}", "FAIL",
                        f"Failed to detect missing BU for null: {null_val}")
                
    except Exception as e:
        log_test(test_name, "ERROR", error=e)

def test_business_unit_validation():
    """Test business unit requirement validation"""
    test_name = "Business Unit Validation"
    try:
        # Test 1: Revenue account - BU Required
        is_valid, errors = validate_journal_entry_line(
            document_type='SA',
            gl_account_id='400001',  # Revenue
            business_unit_id=None,
            line_number=1
        )
        
        if not is_valid and any('Business Unit' in err and 'required' in err.lower() for err in errors):
            log_test(f"{test_name} - Revenue BU Required", "PASS",
                    "Correctly enforced BU requirement for revenue")
        else:
            log_test(f"{test_name} - Revenue BU Required", "FAIL",
                    f"Failed to enforce BU requirement. Errors: {errors}")
        
        # Test 2: Expense account - BU Required
        is_valid, errors = validate_journal_entry_line(
            document_type='SA',
            gl_account_id='550000',  # Expense
            business_unit_id=None,
            line_number=2
        )
        
        if not is_valid and any('Business Unit' in err and 'required' in err.lower() for err in errors):
            log_test(f"{test_name} - Expense BU Required", "PASS",
                    "Correctly enforced BU requirement for expense")
        else:
            log_test(f"{test_name} - Expense BU Required", "FAIL",
                    f"Failed to enforce BU requirement. Errors: {errors}")
        
        # Test 3: Cash account - BU Suppressed
        is_valid, errors = validate_journal_entry_line(
            document_type='SA',
            gl_account_id='100010',  # Cash
            business_unit_id='1',  # Should be suppressed
            line_number=3
        )
        
        if not is_valid and any('Business Unit' in err and 'not be provided' in err for err in errors):
            log_test(f"{test_name} - Cash BU Suppressed", "PASS",
                    "Correctly suppressed BU for cash account")
        else:
            log_test(f"{test_name} - Cash BU Suppressed", "FAIL",
                    f"Failed to suppress BU. Errors: {errors}")
            
    except Exception as e:
        log_test(test_name, "ERROR", error=e)

def test_field_suppression():
    """Test field suppression rules"""
    test_name = "Field Suppression"
    try:
        # Test suppressed fields with values
        is_valid, errors = validate_journal_entry_line(
            document_type='SA',
            gl_account_id='100010',  # Cash account
            business_unit_id='1',  # Suppressed
            tax_code='V1',  # Suppressed
            business_area='NORTH',  # May be suppressed
            line_number=1
        )
        
        suppression_errors = [err for err in errors if 'should not be provided' in err]
        
        if len(suppression_errors) > 0:
            log_test(f"{test_name} - Suppressed Fields", "PASS",
                    f"Detected {len(suppression_errors)} suppressed field violations")
        else:
            log_test(f"{test_name} - Suppressed Fields", "FAIL",
                    "Failed to detect suppressed field violations")
            
    except Exception as e:
        log_test(test_name, "ERROR", error=e)

def test_required_fields():
    """Test required field validation"""
    test_name = "Required Fields"
    try:
        # Test with all required fields missing
        is_valid, errors = validate_journal_entry_line(
            document_type='DR',  # Customer Invoice
            gl_account_id='110000',  # AR account
            business_unit_id=None,  # Required
            reference=None,  # May be required
            assignment=None,  # May be required
            line_number=1
        )
        
        required_errors = [err for err in errors if 'required' in err.lower()]
        
        if len(required_errors) > 0:
            log_test(f"{test_name} - Missing Required", "PASS",
                    f"Detected {len(required_errors)} missing required fields")
        else:
            log_test(f"{test_name} - Missing Required", "FAIL",
                    "Failed to detect missing required fields")
        
        # Test with all required fields provided
        is_valid, errors = validate_journal_entry_line(
            document_type='DR',
            gl_account_id='110000',
            business_unit_id='1',
            reference='REF001',
            assignment='ASSIGN001',
            text='Customer payment',
            line_number=2
        )
        
        if is_valid:
            log_test(f"{test_name} - All Required Provided", "PASS",
                    "Validation passed with all required fields")
        else:
            log_test(f"{test_name} - All Required Provided", "FAIL",
                    f"Validation failed despite required fields: {errors}")
            
    except Exception as e:
        log_test(test_name, "ERROR", error=e)

def test_fsg_effective_determination():
    """Test FSG effective determination for various scenarios"""
    test_name = "FSG Effective Determination"
    
    test_cases = [
        # (doc_type, gl_account, expected_fsg, description)
        ('KA', '200000', 'VENDOR01', 'Vendor invoice AP'),
        ('DR', '110000', 'RECV01', 'Customer invoice AR'),
        ('SA', '400001', 'REV01', 'General journal revenue'),
        ('SA', '550000', 'EXP01', 'General journal expense'),
        ('CA', '100010', 'CASH01', 'Cash journal'),
        ('SA', '120000', 'ASSET01', 'General journal inventory'),
    ]
    
    for doc_type, gl_account, expected_fsg, description in test_cases:
        try:
            fsg = field_status_engine.get_effective_field_status_group(
                document_type=doc_type,
                gl_account_id=gl_account
            )
            
            if fsg and fsg.group_id == expected_fsg:
                log_test(f"{test_name} - {description}", "PASS",
                        f"Correctly resolved to {expected_fsg}")
            else:
                log_test(f"{test_name} - {description}", "FAIL",
                        f"Expected {expected_fsg}, got {fsg.group_id if fsg else 'None'}")
                
        except Exception as e:
            log_test(f"{test_name} - {description}", "ERROR", error=e)

def test_pandas_integration():
    """Test pandas DataFrame integration for null handling"""
    test_name = "Pandas Integration"
    try:
        # Create test DataFrame similar to journal entry lines
        df = pd.DataFrame({
            'glaccountid': ['400001', '550000', '100010'],
            'business_unit_id': [pd.NA, '', '1'],
            'tax_code': [None, 'V1', 'V2'],
            'business_area': ['', pd.NA, 'NORTH']
        })
        
        for idx, row in df.iterrows():
            gl_account = str(row['glaccountid'])
            
            # Test null value detection
            bu_value = row['business_unit_id']
            is_null = pd.isna(bu_value) or bu_value is None or str(bu_value).strip() in ['', 'nan', 'None']
            
            if idx == 0 and is_null:  # First row should have null BU
                log_test(f"{test_name} - Row {idx+1} Null Detection", "PASS",
                        f"Correctly detected null BU for GL {gl_account}")
            elif idx == 2 and not is_null:  # Third row should have value
                log_test(f"{test_name} - Row {idx+1} Value Detection", "PASS",
                        f"Correctly detected BU value '1' for GL {gl_account}")
                
    except Exception as e:
        log_test(test_name, "ERROR", error=e)

def test_database_fsg_configuration():
    """Test database FSG configuration integrity"""
    test_name = "Database FSG Configuration"
    try:
        with engine.connect() as conn:
            # Check FSG assignments
            result = conn.execute(text("""
                SELECT COUNT(*) as total,
                       COUNT(DISTINCT fsg.group_id) as unique_fsgs,
                       COUNT(CASE WHEN fsg.business_unit_status = 'REQ' THEN 1 END) as bu_required,
                       COUNT(CASE WHEN fsg.business_unit_status = 'SUP' THEN 1 END) as bu_suppressed
                FROM field_status_groups fsg
                WHERE fsg.is_active = TRUE
            """)).fetchone()
            
            if result['total'] > 0:
                log_test(f"{test_name} - FSG Records", "PASS",
                        f"Found {result['total']} active FSGs, {result['bu_required']} require BU, {result['bu_suppressed']} suppress BU")
            else:
                log_test(f"{test_name} - FSG Records", "FAIL",
                        "No active FSG records found")
            
            # Check account group assignments
            result = conn.execute(text("""
                SELECT COUNT(*) as total,
                       COUNT(DISTINCT default_field_status_group) as unique_assignments
                FROM account_groups
                WHERE default_field_status_group IS NOT NULL
            """)).fetchone()
            
            if result['total'] > 0:
                log_test(f"{test_name} - Account Group Assignments", "PASS",
                        f"Found {result['total']} account groups with FSG assignments")
            else:
                log_test(f"{test_name} - Account Group Assignments", "FAIL",
                        "No account groups have FSG assignments")
                
    except Exception as e:
        log_test(test_name, "ERROR", error=e)

def main():
    """Run all QAT tests"""
    print("=" * 60)
    print("FSG VALIDATION - QUALITY ASSURANCE TESTING")
    print("=" * 60)
    print(f"Test Run: {datetime.now()}")
    print("-" * 60)
    
    # Run test suites
    test_fsg_hierarchy_resolution()
    test_null_value_handling()
    test_business_unit_validation()
    test_field_suppression()
    test_required_fields()
    test_fsg_effective_determination()
    test_pandas_integration()
    test_database_fsg_configuration()
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {test_results['summary']['total']}")
    print(f"✅ Passed: {test_results['summary']['passed']}")
    print(f"❌ Failed: {test_results['summary']['failed']}")
    print(f"⚠️ Errors: {test_results['summary']['errors']}")
    
    pass_rate = (test_results['summary']['passed'] / test_results['summary']['total'] * 100) if test_results['summary']['total'] > 0 else 0
    print(f"\nPass Rate: {pass_rate:.1f}%")
    
    # Save results
    output_file = f"/home/anton/erp/gl/tests/fsg_qat_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(test_results, f, indent=2, default=str)
    print(f"\nResults saved to: {output_file}")
    
    return test_results

if __name__ == "__main__":
    main()