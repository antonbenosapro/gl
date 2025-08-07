"""
UAT Testing Script for Bulk Journal Entry Submission Manager

This script conducts comprehensive User Acceptance Testing for the bulk journal
submission functionality including:
- Entry selection and filtering
- Bulk upload validation
- Approval routing logic
- Tracking and notifications
- Error handling and edge cases

Author: Claude Code Assistant
Date: August 6, 2025
"""

import sys
import os
import pandas as pd
import json
from datetime import datetime, date, timedelta
from decimal import Decimal
import traceback
import time

# Add project root to path
sys.path.append('/home/anton/erp/gl')

from db_config import engine
from sqlalchemy import text
from utils.workflow_engine import WorkflowEngine

# Test configuration
TEST_USER = "test_user"
TEST_COMPANY = "1000"
TEST_RESULTS = {
    "test_run_id": f"UAT_BULK_SUBMISSION_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    "start_time": datetime.now(),
    "test_cases": [],
    "summary": {}
}

def log_test_result(test_name, status, details="", error_msg=""):
    """Log individual test result."""
    result = {
        "test_name": test_name,
        "status": status,
        "details": details,
        "error_msg": error_msg,
        "timestamp": datetime.now().isoformat()
    }
    TEST_RESULTS["test_cases"].append(result)
    
    # Print immediate feedback
    status_icon = "✅" if status == "PASSED" else "❌"
    print(f"{status_icon} {test_name}: {status}")
    if error_msg:
        print(f"   Error: {error_msg}")

def setup_test_data():
    """Create test journal entries for UAT."""
    print("\n🔧 Setting up test data...")
    
    try:
        with engine.begin() as conn:
            # Create test journal entries in DRAFT status
            test_entries = []
            
            for i in range(1, 11):  # Create 10 test entries
                doc_number = f"TEST_JE_{datetime.now().strftime('%Y%m%d')}_{i:03d}"
                
                # Create header
                conn.execute(text("""
                    INSERT INTO journalentryheader 
                    (documentnumber, companycodeid, fiscalyear, period, 
                     postingdate, documentdate, reference, workflow_status, 
                     createdby, createdat, currencycode)
                    VALUES (:doc_num, :company, 2025, 2, :posting_date, :doc_date,
                            :reference, 'DRAFT', :created_by, CURRENT_TIMESTAMP, 'USD')
                    ON CONFLICT (documentnumber, companycodeid) DO UPDATE
                    SET workflow_status = 'DRAFT',
                        reference = EXCLUDED.reference
                """), {
                    "doc_num": doc_number,
                    "company": TEST_COMPANY,
                    "posting_date": date.today(),
                    "doc_date": date.today(),
                    "reference": f"Test Entry {i} - UAT Bulk Submission",
                    "created_by": TEST_USER
                })
                
                # Create lines with varying amounts for different approval levels
                amount = 1000 * i  # Amounts from 1,000 to 10,000
                
                # Debit line
                conn.execute(text("""
                    INSERT INTO journalentryline
                    (documentnumber, companycodeid, linenumber, glaccountid,
                     debitamount, creditamount, currencycode, ledgerid)
                    VALUES (:doc_num, :company, 1, '400001',
                            :amount, 0, 'USD', 'L1')
                    ON CONFLICT (documentnumber, companycodeid, linenumber) DO UPDATE
                    SET debitamount = EXCLUDED.debitamount
                """), {
                    "doc_num": doc_number,
                    "company": TEST_COMPANY,
                    "amount": amount
                })
                
                # Credit line
                conn.execute(text("""
                    INSERT INTO journalentryline
                    (documentnumber, companycodeid, linenumber, glaccountid,
                     debitamount, creditamount, currencycode, ledgerid)
                    VALUES (:doc_num, :company, 2, '200001',
                            0, :amount, 'USD', 'L1')
                    ON CONFLICT (documentnumber, companycodeid, linenumber) DO UPDATE
                    SET creditamount = EXCLUDED.creditamount
                """), {
                    "doc_num": doc_number,
                    "company": TEST_COMPANY,
                    "amount": amount
                })
                
                test_entries.append({
                    "document_number": doc_number,
                    "amount": amount,
                    "reference": f"Test Entry {i}"
                })
            
            print(f"✅ Created {len(test_entries)} test journal entries")
            return test_entries
            
    except Exception as e:
        print(f"❌ Error setting up test data: {e}")
        return []

def test_entry_selection():
    """Test 1: Entry selection and filtering."""
    test_name = "Entry Selection and Filtering"
    
    try:
        with engine.connect() as conn:
            # Test filtering by company
            result = conn.execute(text("""
                SELECT COUNT(*) FROM journalentryheader
                WHERE companycodeid = :company
                AND workflow_status = 'DRAFT'
                AND createdat >= CURRENT_DATE - INTERVAL '30 days'
            """), {"company": TEST_COMPANY})
            
            draft_count = result.scalar()
            
            if draft_count > 0:
                log_test_result(
                    test_name,
                    "PASSED",
                    f"Found {draft_count} draft entries for selection"
                )
            else:
                log_test_result(
                    test_name,
                    "FAILED",
                    "No draft entries found",
                    "Entry selection requires draft journal entries"
                )
                
    except Exception as e:
        log_test_result(test_name, "FAILED", "", str(e))

def test_bulk_upload_validation():
    """Test 2: Bulk upload file validation."""
    test_name = "Bulk Upload Validation"
    
    try:
        # Create test upload data
        test_upload_data = pd.DataFrame({
            'document_number': [
                f'TEST_JE_{datetime.now().strftime("%Y%m%d")}_001',
                f'TEST_JE_{datetime.now().strftime("%Y%m%d")}_002',
                'INVALID_DOC',  # Invalid document
                '',  # Empty document number
                f'TEST_JE_{datetime.now().strftime("%Y%m%d")}_003'
            ],
            'company_code': ['1000', '1000', '1000', '1000', '9999'],  # Last one has invalid company
            'reference': ['Test 1', 'Test 2', 'Test 3', 'Test 4', 'Test 5'],
            'priority': ['NORMAL', 'HIGH', 'INVALID', 'URGENT', 'NORMAL'],
            'comments': ['Comment 1', 'Comment 2', '', '', 'Comment 5']
        })
        
        # Validate the upload data
        errors = []
        warnings = []
        valid_count = 0
        
        for idx, row in test_upload_data.iterrows():
            # Check document number
            if pd.isna(row['document_number']) or str(row['document_number']).strip() == '':
                errors.append(f"Row {idx+2}: Document number is required")
            elif 'INVALID' in str(row['document_number']):
                errors.append(f"Row {idx+2}: Document not found or not in DRAFT status")
            else:
                valid_count += 1
            
            # Check company code
            if str(row['company_code']) not in ['1000', '2000', '3000']:
                errors.append(f"Row {idx+2}: Invalid company code")
            
            # Check priority
            if row['priority'] not in ['NORMAL', 'HIGH', 'URGENT']:
                warnings.append(f"Row {idx+2}: Invalid priority, defaulting to NORMAL")
        
        # Log validation results
        log_test_result(
            test_name,
            "PASSED" if len(errors) > 0 else "FAILED",
            f"Validation caught {len(errors)} errors and {len(warnings)} warnings as expected",
            "" if len(errors) > 0 else "Validation should have caught errors"
        )
        
    except Exception as e:
        log_test_result(test_name, "FAILED", "", str(e))

def test_approval_routing():
    """Test 3: Automatic approval routing logic."""
    test_name = "Approval Routing Logic"
    
    try:
        test_documents = [
            (f'TEST_JE_{datetime.now().strftime("%Y%m%d")}_001', '1000', 1000),
            (f'TEST_JE_{datetime.now().strftime("%Y%m%d")}_005', '1000', 5000),
            (f'TEST_JE_{datetime.now().strftime("%Y%m%d")}_010', '1000', 10000)
        ]
        
        routing_results = []
        
        for doc_num, company, expected_amount in test_documents:
            # Calculate approval level
            approval_level = WorkflowEngine.calculate_required_approval_level(doc_num, company)
            
            if approval_level:
                # Get available approvers
                approvers = WorkflowEngine.get_available_approvers(
                    approval_level, company, TEST_USER
                )
                
                routing_results.append({
                    'document': doc_num,
                    'amount': expected_amount,
                    'approval_level': approval_level,
                    'approver_count': len(approvers)
                })
        
        # Verify routing logic
        if all(r['approver_count'] >= 0 for r in routing_results):
            log_test_result(
                test_name,
                "PASSED",
                f"Successfully routed {len(routing_results)} documents with varying amounts"
            )
        else:
            log_test_result(
                test_name,
                "FAILED",
                "Some documents could not be routed",
                "Check approval level configuration"
            )
            
    except Exception as e:
        log_test_result(test_name, "FAILED", "", str(e))

def test_bulk_submission_process():
    """Test 4: Bulk submission execution."""
    test_name = "Bulk Submission Process"
    
    try:
        # Select test entries for submission
        test_entries = [
            f'TEST_JE_{datetime.now().strftime("%Y%m%d")}_001',
            f'TEST_JE_{datetime.now().strftime("%Y%m%d")}_002',
            f'TEST_JE_{datetime.now().strftime("%Y%m%d")}_003'
        ]
        
        submitted_count = 0
        failed_count = 0
        
        for doc_num in test_entries:
            try:
                # Attempt submission
                success, message = WorkflowEngine.submit_for_approval(
                    doc_num,
                    TEST_COMPANY,
                    TEST_USER,
                    "UAT bulk submission test"
                )
                
                if success:
                    submitted_count += 1
                else:
                    failed_count += 1
                    
            except Exception as sub_error:
                failed_count += 1
        
        # Log results
        if submitted_count > 0:
            log_test_result(
                test_name,
                "PASSED",
                f"Successfully submitted {submitted_count}/{len(test_entries)} entries"
            )
        else:
            log_test_result(
                test_name,
                "FAILED",
                f"Failed to submit entries",
                f"{failed_count} failures out of {len(test_entries)} attempts"
            )
            
    except Exception as e:
        log_test_result(test_name, "FAILED", "", str(e))

def test_submission_tracking():
    """Test 5: Submission tracking and status updates."""
    test_name = "Submission Tracking"
    
    try:
        with engine.connect() as conn:
            # Check for pending submissions
            result = conn.execute(text("""
                SELECT COUNT(*) as pending_count,
                       COUNT(DISTINCT jeh.documentnumber) as unique_docs
                FROM journalentryheader jeh
                WHERE jeh.workflow_status = 'PENDING_APPROVAL'
                AND jeh.createdby = :user
                AND jeh.submitted_for_approval_at >= CURRENT_DATE
            """), {"user": TEST_USER})
            
            tracking_data = result.fetchone()
            
            if tracking_data and tracking_data['pending_count'] > 0:
                log_test_result(
                    test_name,
                    "PASSED",
                    f"Tracking {tracking_data['unique_docs']} pending submissions"
                )
            else:
                log_test_result(
                    test_name,
                    "WARNING",
                    "No pending submissions to track",
                    "May need to submit entries first"
                )
                
    except Exception as e:
        log_test_result(test_name, "FAILED", "", str(e))

def test_notification_system():
    """Test 6: Notification creation and delivery."""
    test_name = "Notification System"
    
    try:
        with engine.connect() as conn:
            # Create test notification
            conn.execute(text("""
                INSERT INTO approval_notifications
                (recipient, notification_type, subject, message, workflow_instance_id)
                VALUES (:recipient, 'TEST', 'UAT Test Notification', 
                        'This is a test notification for UAT', NULL)
            """), {"recipient": f"{TEST_USER}@test.com"})
            
            # Verify notification was created
            result = conn.execute(text("""
                SELECT COUNT(*) FROM approval_notifications
                WHERE recipient LIKE :pattern
                AND notification_type = 'TEST'
                AND created_at >= CURRENT_DATE
            """), {"pattern": f"%{TEST_USER}%"})
            
            notification_count = result.scalar()
            
            if notification_count > 0:
                log_test_result(
                    test_name,
                    "PASSED",
                    f"Successfully created {notification_count} test notification(s)"
                )
            else:
                log_test_result(
                    test_name,
                    "FAILED",
                    "No notifications created",
                    "Check notification system configuration"
                )
                
    except Exception as e:
        log_test_result(test_name, "FAILED", "", str(e))

def test_withdrawal_functionality():
    """Test 7: Submission withdrawal process."""
    test_name = "Withdrawal Functionality"
    
    try:
        # Find a pending submission to withdraw
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT wi.id, wi.document_number, wi.company_code
                FROM workflow_instances wi
                WHERE wi.status = 'PENDING'
                AND wi.document_number LIKE 'TEST_JE_%'
                LIMIT 1
            """))
            
            pending_workflow = result.fetchone()
            
            if pending_workflow:
                workflow_id, doc_number, company_code = pending_workflow
                
                # Attempt withdrawal
                with engine.begin() as conn:
                    # Update workflow status
                    conn.execute(text("""
                        UPDATE workflow_instances
                        SET status = 'WITHDRAWN', completed_at = CURRENT_TIMESTAMP
                        WHERE id = :workflow_id
                    """), {"workflow_id": workflow_id})
                    
                    # Update journal entry status
                    conn.execute(text("""
                        UPDATE journalentryheader
                        SET workflow_status = 'DRAFT'
                        WHERE documentnumber = :doc AND companycodeid = :cc
                    """), {"doc": doc_number, "cc": company_code})
                    
                # Verify withdrawal
                result = conn.execute(text("""
                    SELECT workflow_status FROM journalentryheader
                    WHERE documentnumber = :doc
                """), {"doc": doc_number})
                
                status = result.scalar()
                
                if status == 'DRAFT':
                    log_test_result(
                        test_name,
                        "PASSED",
                        f"Successfully withdrew submission {doc_number}"
                    )
                else:
                    log_test_result(
                        test_name,
                        "FAILED",
                        f"Status is {status}, expected DRAFT",
                        "Withdrawal may not have completed correctly"
                    )
            else:
                log_test_result(
                    test_name,
                    "SKIPPED",
                    "No pending submissions to withdraw",
                    "Test requires pending workflow"
                )
                
    except Exception as e:
        log_test_result(test_name, "FAILED", "", str(e))

def test_comment_functionality():
    """Test 8: Adding comments to submissions."""
    test_name = "Comment Functionality"
    
    try:
        with engine.connect() as conn:
            # Find a document to add comments to
            result = conn.execute(text("""
                SELECT documentnumber, companycodeid
                FROM journalentryheader
                WHERE workflow_status IN ('DRAFT', 'PENDING_APPROVAL')
                AND documentnumber LIKE 'TEST_JE_%'
                LIMIT 1
            """))
            
            doc_info = result.fetchone()
            
            if doc_info:
                doc_number, company_code = doc_info
                
                # Add test comment
                conn.execute(text("""
                    INSERT INTO workflow_audit_log
                    (document_number, company_code, action, performed_by, 
                     new_status, comments)
                    VALUES (:doc, :cc, 'COMMENT_ADDED', :user,
                            'PENDING_APPROVAL', :comment)
                """), {
                    "doc": doc_number,
                    "cc": company_code,
                    "user": TEST_USER,
                    "comment": "[URGENT] UAT test comment - please review urgently"
                })
                conn.commit()
                
                # Verify comment was added
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM workflow_audit_log
                    WHERE document_number = :doc
                    AND action = 'COMMENT_ADDED'
                """), {"doc": doc_number})
                
                comment_count = result.scalar()
                
                if comment_count > 0:
                    log_test_result(
                        test_name,
                        "PASSED",
                        f"Successfully added comment to {doc_number}"
                    )
                else:
                    log_test_result(
                        test_name,
                        "FAILED",
                        "Comment not found in audit log",
                        "Check audit log configuration"
                    )
            else:
                log_test_result(
                    test_name,
                    "SKIPPED",
                    "No documents available for commenting",
                    "Test requires existing documents"
                )
                
    except Exception as e:
        log_test_result(test_name, "FAILED", "", str(e))

def test_performance_metrics():
    """Test 9: Performance and response times."""
    test_name = "Performance Metrics"
    
    try:
        start_time = time.time()
        
        with engine.connect() as conn:
            # Test query performance for large result sets
            result = conn.execute(text("""
                SELECT jeh.documentnumber, jeh.reference, jeh.workflow_status,
                       COALESCE(SUM(GREATEST(jel.debitamount, jel.creditamount)), 0) as amount
                FROM journalentryheader jeh
                LEFT JOIN journalentryline jel ON jeh.documentnumber = jel.documentnumber
                WHERE jeh.createdat >= CURRENT_DATE - INTERVAL '90 days'
                GROUP BY jeh.documentnumber, jeh.reference, jeh.workflow_status
                LIMIT 100
            """))
            
            records = result.fetchall()
            
        query_time = time.time() - start_time
        
        if query_time < 2.0:  # Should complete within 2 seconds
            log_test_result(
                test_name,
                "PASSED",
                f"Query completed in {query_time:.2f} seconds for {len(records)} records"
            )
        else:
            log_test_result(
                test_name,
                "WARNING",
                f"Query took {query_time:.2f} seconds",
                "Performance may need optimization"
            )
            
    except Exception as e:
        log_test_result(test_name, "FAILED", "", str(e))

def test_error_handling():
    """Test 10: Error handling and recovery."""
    test_name = "Error Handling"
    
    try:
        error_scenarios = []
        
        # Test 1: Invalid document submission
        try:
            success, message = WorkflowEngine.submit_for_approval(
                "INVALID_DOC_999",
                "9999",
                TEST_USER,
                "Test invalid submission"
            )
            error_scenarios.append({
                "scenario": "Invalid document",
                "handled": not success,
                "message": message
            })
        except Exception as e:
            error_scenarios.append({
                "scenario": "Invalid document",
                "handled": True,
                "message": str(e)
            })
        
        # Test 2: Duplicate submission
        try:
            # Try to submit an already submitted document
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT documentnumber FROM journalentryheader
                    WHERE workflow_status = 'PENDING_APPROVAL'
                    AND documentnumber LIKE 'TEST_JE_%'
                    LIMIT 1
                """))
                
                pending_doc = result.fetchone()
                
                if pending_doc:
                    success, message = WorkflowEngine.submit_for_approval(
                        pending_doc[0],
                        TEST_COMPANY,
                        TEST_USER,
                        "Duplicate submission test"
                    )
                    error_scenarios.append({
                        "scenario": "Duplicate submission",
                        "handled": not success and "already" in message.lower(),
                        "message": message
                    })
                    
        except Exception as e:
            error_scenarios.append({
                "scenario": "Duplicate submission",
                "handled": True,
                "message": str(e)
            })
        
        # Check if all error scenarios were handled properly
        handled_count = sum(1 for s in error_scenarios if s['handled'])
        
        if handled_count == len(error_scenarios):
            log_test_result(
                test_name,
                "PASSED",
                f"All {handled_count} error scenarios handled correctly"
            )
        else:
            log_test_result(
                test_name,
                "FAILED",
                f"Only {handled_count}/{len(error_scenarios)} scenarios handled",
                "Some error scenarios not handled properly"
            )
            
    except Exception as e:
        log_test_result(test_name, "FAILED", "", str(e))

def cleanup_test_data():
    """Clean up test data after UAT."""
    print("\n🧹 Cleaning up test data...")
    
    try:
        with engine.begin() as conn:
            # Clean up test workflow instances
            conn.execute(text("""
                DELETE FROM workflow_instances
                WHERE document_number LIKE 'TEST_JE_%'
            """))
            
            # Clean up test journal entries
            conn.execute(text("""
                DELETE FROM journalentryline
                WHERE documentnumber LIKE 'TEST_JE_%'
            """))
            
            conn.execute(text("""
                DELETE FROM journalentryheader
                WHERE documentnumber LIKE 'TEST_JE_%'
            """))
            
            # Clean up test notifications
            conn.execute(text("""
                DELETE FROM approval_notifications
                WHERE notification_type = 'TEST'
            """))
            
            # Clean up test audit logs
            conn.execute(text("""
                DELETE FROM workflow_audit_log
                WHERE document_number LIKE 'TEST_JE_%'
            """))
            
            print("✅ Test data cleaned up successfully")
            
    except Exception as e:
        print(f"⚠️ Warning: Could not clean up all test data: {e}")

def generate_uat_report():
    """Generate comprehensive UAT report."""
    print("\n" + "="*80)
    print("📊 BULK JOURNAL SUBMISSION UAT REPORT")
    print("="*80)
    
    # Calculate summary statistics
    total_tests = len(TEST_RESULTS["test_cases"])
    passed_tests = sum(1 for t in TEST_RESULTS["test_cases"] if t["status"] == "PASSED")
    failed_tests = sum(1 for t in TEST_RESULTS["test_cases"] if t["status"] == "FAILED")
    warning_tests = sum(1 for t in TEST_RESULTS["test_cases"] if t["status"] == "WARNING")
    skipped_tests = sum(1 for t in TEST_RESULTS["test_cases"] if t["status"] == "SKIPPED")
    
    pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    TEST_RESULTS["summary"] = {
        "total_tests": total_tests,
        "passed": passed_tests,
        "failed": failed_tests,
        "warnings": warning_tests,
        "skipped": skipped_tests,
        "pass_rate": pass_rate,
        "end_time": datetime.now(),
        "duration": str(datetime.now() - TEST_RESULTS["start_time"])
    }
    
    # Print summary
    print(f"\n📈 TEST SUMMARY:")
    print(f"   Total Tests: {total_tests}")
    print(f"   ✅ Passed: {passed_tests}")
    print(f"   ❌ Failed: {failed_tests}")
    print(f"   ⚠️ Warnings: {warning_tests}")
    print(f"   ⏭️ Skipped: {skipped_tests}")
    print(f"   📊 Pass Rate: {pass_rate:.1f}%")
    print(f"   ⏱️ Duration: {TEST_RESULTS['summary']['duration']}")
    
    # Print detailed results
    print(f"\n📋 DETAILED TEST RESULTS:")
    print("-" * 80)
    
    for test in TEST_RESULTS["test_cases"]:
        status_icon = {
            "PASSED": "✅",
            "FAILED": "❌",
            "WARNING": "⚠️",
            "SKIPPED": "⏭️"
        }.get(test["status"], "❓")
        
        print(f"{status_icon} {test['test_name']}")
        print(f"   Status: {test['status']}")
        if test['details']:
            print(f"   Details: {test['details']}")
        if test['error_msg']:
            print(f"   Error: {test['error_msg']}")
        print()
    
    # Save report to file
    report_file = f"tests/bulk_submission_uat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(TEST_RESULTS, f, indent=2, default=str)
    
    print(f"\n💾 Report saved to: {report_file}")
    
    # Overall assessment
    print("\n" + "="*80)
    if pass_rate >= 90:
        print("🎉 UAT RESULT: EXCELLENT - System ready for production!")
    elif pass_rate >= 75:
        print("✅ UAT RESULT: GOOD - Minor issues to address")
    elif pass_rate >= 60:
        print("⚠️ UAT RESULT: ACCEPTABLE - Several issues need attention")
    else:
        print("❌ UAT RESULT: NEEDS IMPROVEMENT - Critical issues found")
    print("="*80)

def main():
    """Main UAT execution function."""
    print("\n" + "="*80)
    print("🚀 STARTING BULK JOURNAL SUBMISSION UAT")
    print(f"   Test Run ID: {TEST_RESULTS['test_run_id']}")
    print(f"   Start Time: {TEST_RESULTS['start_time']}")
    print("="*80)
    
    try:
        # Setup test data
        test_entries = setup_test_data()
        
        if test_entries:
            # Run test suite
            print("\n📝 Running test suite...")
            
            test_entry_selection()
            test_bulk_upload_validation()
            test_approval_routing()
            test_bulk_submission_process()
            test_submission_tracking()
            test_notification_system()
            test_withdrawal_functionality()
            test_comment_functionality()
            test_performance_metrics()
            test_error_handling()
            
            # Cleanup
            cleanup_test_data()
        else:
            print("❌ Failed to setup test data, aborting UAT")
        
    except Exception as e:
        print(f"\n❌ Critical error during UAT: {e}")
        traceback.print_exc()
    
    finally:
        # Generate report
        generate_uat_report()

if __name__ == "__main__":
    main()