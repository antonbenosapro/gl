#!/usr/bin/env python3
"""
Automatic Posting End-to-End Test
Test the complete automatic posting workflow: Create -> Approve -> Auto-Post
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import text
from db_config import engine
from utils.workflow_engine import WorkflowEngine
from utils.auto_posting_service import auto_posting_service

def test_automatic_posting():
    """Test complete automatic posting workflow"""
    
    print("🤖 AUTOMATIC POSTING END-TO-END TEST")
    print("=" * 60)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    workflow_engine = WorkflowEngine()
    test_results = []
    
    try:
        # TEST 1: Create a journal entry for auto-posting
        print("\n📝 TEST 1: Creating Journal Entry")
        print("-" * 40)
        
        doc_number = f"AUTO{datetime.now().strftime('%Y%m%d%H%M%S')}"
        company_code = "TEST"
        
        with engine.connect() as conn:
            with conn.begin():
                # Create header
                conn.execute(text("""
                    INSERT INTO journalentryheader (
                        documentnumber, companycodeid, postingdate, fiscalyear, period,
                        reference, currencycode, createdby, workflow_status
                    ) VALUES (
                        :doc, :cc, CURRENT_DATE, :year, :period,
                        'Auto-Posting Test Entry', 'USD', 'test_creator', 'DRAFT'
                    )
                """), {
                    "doc": doc_number,
                    "cc": company_code,
                    "year": datetime.now().year,
                    "period": datetime.now().month
                })
                
                # Create balanced lines
                lines = [
                    (1, '100001', Decimal('500.00'), None, "Auto-posting test debit"),
                    (2, '300001', None, Decimal('500.00'), "Auto-posting test credit")
                ]
                
                for line_num, account, debit, credit, desc in lines:
                    conn.execute(text("""
                        INSERT INTO journalentryline (
                            documentnumber, companycodeid, linenumber, glaccountid,
                            debitamount, creditamount, description
                        ) VALUES (
                            :doc, :cc, :line, :account, :debit, :credit, :desc
                        )
                    """), {
                        "doc": doc_number,
                        "cc": company_code,
                        "line": line_num,
                        "account": account,
                        "debit": debit,
                        "credit": credit,
                        "desc": desc
                    })
        
        print(f"✅ Created journal entry: {doc_number}")
        print(f"   Amount: $500.00")
        print(f"   Status: DRAFT")
        test_results.append(("Journal Creation", "PASSED"))
        
        # TEST 2: Verify initial status
        print("\n🔍 TEST 2: Verify Initial Status")
        print("-" * 40)
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT workflow_status, posted_at, auto_posted
                FROM journalentryheader
                WHERE documentnumber = :doc AND companycodeid = :cc
            """), {"doc": doc_number, "cc": company_code})
            
            initial_status = result.fetchone()
            
            print(f"   Workflow Status: {initial_status[0]}")
            print(f"   Posted At: {initial_status[1] or 'Not Posted'}")
            print(f"   Auto Posted: {initial_status[2]}")
            
            if initial_status[0] == 'DRAFT' and not initial_status[1] and not initial_status[2]:
                print("✅ Initial status correct")
                test_results.append(("Initial Status", "PASSED"))
            else:
                print("❌ Initial status incorrect")
                test_results.append(("Initial Status", "FAILED"))
        
        # TEST 3: Approve document (should trigger auto-posting)
        print("\n✅ TEST 3: Approve Document (Auto-Posting Trigger)")
        print("-" * 40)
        
        approval_success, approval_message = workflow_engine.approve_document(
            doc_number, company_code, 'test_approver', 'Auto-posting test approval'
        )
        
        print(f"   Approval Success: {approval_success}")
        print(f"   Approval Message: {approval_message}")
        
        if approval_success:
            print("✅ Document approval successful")
            test_results.append(("Document Approval", "PASSED"))
        else:
            print("❌ Document approval failed")
            test_results.append(("Document Approval", "FAILED"))
            return test_results
        
        # TEST 4: Verify automatic posting occurred
        print("\n🤖 TEST 4: Verify Automatic Posting")
        print("-" * 40)
        
        with engine.connect() as conn:
            # Check journal entry status
            result = conn.execute(text("""
                SELECT workflow_status, posted_at, posted_by, auto_posted, auto_posted_at, auto_posted_by
                FROM journalentryheader
                WHERE documentnumber = :doc AND companycodeid = :cc
            """), {"doc": doc_number, "cc": company_code})
            
            final_status = result.fetchone()
            
            print(f"   Workflow Status: {final_status[0]}")
            print(f"   Posted At: {final_status[1]}")
            print(f"   Posted By: {final_status[2]}")
            print(f"   Auto Posted: {final_status[3]}")
            print(f"   Auto Posted At: {final_status[4]}")
            print(f"   Auto Posted By: {final_status[5]}")
            
            # Check GL transactions
            result = conn.execute(text("""
                SELECT COUNT(*) FROM gl_transactions
                WHERE company_code = :cc AND document_number = :doc
            """), {"cc": company_code, "doc": doc_number})
            
            gl_transaction_count = result.fetchone()[0]
            print(f"   GL Transactions Created: {gl_transaction_count}")
            
            # Check posting documents
            result = conn.execute(text("""
                SELECT COUNT(*) FROM posting_documents
                WHERE company_code = :cc AND source_document = :doc
            """), {"cc": company_code, "doc": doc_number})
            
            posting_doc_count = result.fetchone()[0]
            print(f"   Posting Documents Created: {posting_doc_count}")
            
            # Check audit trail
            result = conn.execute(text("""
                SELECT COUNT(*) FROM posting_audit_trail
                WHERE company_code = :cc AND source_document = :doc
            """), {"cc": company_code, "doc": doc_number})
            
            audit_count = result.fetchone()[0]
            print(f"   Audit Trail Entries: {audit_count}")
            
            # Verify posting success
            posting_success = (
                final_status[0] == 'POSTED' and
                final_status[1] is not None and  # posted_at
                final_status[2] == 'AUTO_POSTER' and  # posted_by
                final_status[3] == True and  # auto_posted
                final_status[4] is not None and  # auto_posted_at
                final_status[5] == 'AUTO_POSTER' and  # auto_posted_by
                gl_transaction_count == 2 and  # 2 GL transaction lines
                posting_doc_count == 1 and  # 1 posting document
                audit_count == 1  # 1 audit trail entry
            )
            
            if posting_success:
                print("✅ Automatic posting successful")
                test_results.append(("Automatic Posting", "PASSED"))
            else:
                print("❌ Automatic posting failed")
                test_results.append(("Automatic Posting", "FAILED"))
        
        # TEST 5: Verify account balances updated
        print("\n💰 TEST 5: Verify Account Balance Updates")
        print("-" * 40)
        
        # Check Cash account (100001)
        cash_balance = auto_posting_service.posting_engine.get_account_balance('TEST', '100001')
        print(f"   Cash Account (100001) Balance: ${cash_balance.get('ytd_balance', 0):,.2f}")
        
        # Check Revenue account (300001)
        revenue_balance = auto_posting_service.posting_engine.get_account_balance('TEST', '300001')
        print(f"   Revenue Account (300001) Balance: ${revenue_balance.get('ytd_balance', 0):,.2f}")
        
        # Verify balance equation
        total_balance = cash_balance.get('ytd_balance', 0) + revenue_balance.get('ytd_balance', 0)
        print(f"   Total Balance Check: ${total_balance:,.2f}")
        
        if abs(total_balance) < 0.01:  # Should be zero (balanced)
            print("✅ Account balances updated correctly")
            test_results.append(("Balance Updates", "PASSED"))
        else:
            print("❌ Account balances incorrect")
            test_results.append(("Balance Updates", "FAILED"))
        
        # TEST 6: Test auto-posting statistics
        print("\n📊 TEST 6: Auto-Posting Statistics")
        print("-" * 40)
        
        stats = auto_posting_service.get_auto_posting_statistics('TEST', 1)
        
        print(f"   Auto-Posted Count: {stats.get('auto_posted_count', 0)}")
        print(f"   Auto-Posted Amount: ${stats.get('auto_posted_amount', 0):,.2f}")
        print(f"   Pending Auto-Post: {stats.get('pending_auto_post', 0)}")
        print(f"   Success Rate: {stats.get('success_rate', 0):.1f}%")
        
        if stats.get('auto_posted_count', 0) > 0:
            print("✅ Auto-posting statistics working")
            test_results.append(("Statistics", "PASSED"))
        else:
            print("❌ Auto-posting statistics not working")
            test_results.append(("Statistics", "FAILED"))
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        test_results.append(("Test Execution", "FAILED"))
    
    # FINAL RESULTS
    print("\n" + "=" * 60)
    print("🏁 AUTOMATIC POSTING TEST RESULTS")
    print("=" * 60)
    
    passed_tests = sum(1 for result in test_results if result[1] == "PASSED")
    total_tests = len(test_results)
    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    for test_name, result in test_results:
        status_icon = "✅" if result == "PASSED" else "❌"
        print(f"{status_icon} {test_name}: {result}")
    
    print(f"\nSummary: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED - AUTOMATIC POSTING IS WORKING!")
        print("\n💡 What happens now:")
        print("   1. Journal entries are created in DRAFT status")
        print("   2. When approved, they automatically post to GL")
        print("   3. Account balances are updated in real-time")
        print("   4. Complete audit trail is maintained")
        print("   5. No manual posting step required!")
    else:
        print("⚠️  SOME TESTS FAILED - REVIEW NEEDED")
    
    return test_results

if __name__ == "__main__":
    test_automatic_posting()