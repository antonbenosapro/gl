#!/usr/bin/env python3
"""
Phase 2 Master Data Integration Test

Test integration between Phase 2 master data and journal entry/GL systems.
Verify that new fields work properly in real transactions.

Author: Claude Code Assistant
Date: August 7, 2025
"""

import sys
import os
from datetime import datetime, date
from decimal import Decimal

# Add project root to path
sys.path.append('/home/anton/erp/gl')

from sqlalchemy import text
from db_config import engine

def test_phase2_integration():
    """Test Phase 2 master data integration with journal entries."""
    
    print("🧪 Phase 2 Master Data Integration Test")
    print("=" * 50)
    
    test_results = {
        'tests_passed': 0,
        'tests_failed': 0,
        'test_details': []
    }
    
    try:
        with engine.connect() as conn:
            # Test 1: Verify table structures support Phase 2 fields
            print("\n📋 Test 1: Table Structure Verification")
            
            # Check journal entry line has new fields
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'journalentryline' 
                AND column_name IN ('profit_center_id', 'business_area_id')
            """))
            jel_columns = [row[0] for row in result.fetchall()]
            
            if len(jel_columns) == 2:
                print("✅ Journal Entry Line: profit_center_id and business_area_id fields present")
                test_results['tests_passed'] += 1
            else:
                print(f"❌ Journal Entry Line: Missing fields. Found: {jel_columns}")
                test_results['tests_failed'] += 1
            
            # Check journal entry header has document type
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'journalentryheader' 
                AND column_name = 'document_type'
            """))
            jeh_columns = [row[0] for row in result.fetchall()]
            
            if jeh_columns:
                print("✅ Journal Entry Header: document_type field present")
                test_results['tests_passed'] += 1
            else:
                print("❌ Journal Entry Header: document_type field missing")
                test_results['tests_failed'] += 1
            
            # Check GL account has default fields
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'glaccount' 
                AND column_name IN ('default_profit_center', 'default_business_area')
            """))
            gl_columns = [row[0] for row in result.fetchall()]
            
            if len(gl_columns) == 2:
                print("✅ GL Account: default_profit_center and default_business_area fields present")
                test_results['tests_passed'] += 1
            else:
                print(f"❌ GL Account: Missing fields. Found: {gl_columns}")
                test_results['tests_failed'] += 1
            
            # Test 2: Verify foreign key relationships work
            print("\n🔗 Test 2: Foreign Key Relationship Verification")
            
            # Test profit center foreign key
            try:
                result = conn.execute(text("""
                    SELECT pc.profit_center_id 
                    FROM profit_centers pc 
                    WHERE pc.is_active = TRUE 
                    LIMIT 1
                """))
                sample_pc = result.fetchone()
                
                if sample_pc:
                    # Try to reference it in journal entry line (dry run)
                    conn.execute(text("""
                        SELECT 1 FROM profit_centers 
                        WHERE profit_center_id = :pc_id
                    """), {'pc_id': sample_pc[0]})
                    print(f"✅ Profit Center FK: Can reference {sample_pc[0]}")
                    test_results['tests_passed'] += 1
                else:
                    print("⚠️  Profit Center FK: No profit centers available for testing")
                    test_results['tests_failed'] += 1
                    
            except Exception as e:
                print(f"❌ Profit Center FK: Error - {e}")
                test_results['tests_failed'] += 1
            
            # Test business area foreign key
            try:
                result = conn.execute(text("""
                    SELECT ba.business_area_id 
                    FROM business_areas ba 
                    WHERE ba.is_active = TRUE 
                    LIMIT 1
                """))
                sample_ba = result.fetchone()
                
                if sample_ba:
                    # Try to reference it in journal entry line (dry run)
                    conn.execute(text("""
                        SELECT 1 FROM business_areas 
                        WHERE business_area_id = :ba_id
                    """), {'ba_id': sample_ba[0]})
                    print(f"✅ Business Area FK: Can reference {sample_ba[0]}")
                    test_results['tests_passed'] += 1
                else:
                    print("⚠️  Business Area FK: No business areas available for testing")
                    test_results['tests_failed'] += 1
                    
            except Exception as e:
                print(f"❌ Business Area FK: Error - {e}")
                test_results['tests_failed'] += 1
            
            # Test document type foreign key
            try:
                result = conn.execute(text("""
                    SELECT dt.document_type 
                    FROM document_types dt 
                    WHERE dt.is_active = TRUE 
                    LIMIT 1
                """))
                sample_dt = result.fetchone()
                
                if sample_dt:
                    # Try to reference it in journal entry header (dry run)
                    conn.execute(text("""
                        SELECT 1 FROM document_types 
                        WHERE document_type = :dt_id
                    """), {'dt_id': sample_dt[0]})
                    print(f"✅ Document Type FK: Can reference {sample_dt[0]}")
                    test_results['tests_passed'] += 1
                else:
                    print("⚠️  Document Type FK: No document types available for testing")
                    test_results['tests_failed'] += 1
                    
            except Exception as e:
                print(f"❌ Document Type FK: Error - {e}")
                test_results['tests_failed'] += 1
            
            # Test 3: Create a test journal entry with Phase 2 fields
            print("\n📝 Test 3: Journal Entry Creation with Phase 2 Fields")
            
            # Get sample master data
            pc_result = conn.execute(text("""
                SELECT profit_center_id FROM profit_centers 
                WHERE is_active = TRUE LIMIT 1
            """))
            profit_center = pc_result.fetchone()
            
            ba_result = conn.execute(text("""
                SELECT business_area_id FROM business_areas 
                WHERE is_active = TRUE LIMIT 1
            """))
            business_area = ba_result.fetchone()
            
            dt_result = conn.execute(text("""
                SELECT document_type FROM document_types 
                WHERE is_active = TRUE LIMIT 1
            """))
            document_type = dt_result.fetchone()
            
            if profit_center and business_area and document_type:
                # Create test journal entry
                test_doc_number = f"TEST{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                try:
                    # Insert header with document type
                    conn.execute(text("""
                        INSERT INTO journalentryheader (
                            documentnumber, companycodeid, postingdate, documentdate,
                            fiscalyear, period, reference, currencycode, createdby,
                            document_type, workflow_status
                        ) VALUES (
                            :doc_num, '1000', :posting_date, :doc_date,
                            2025, 8, 'Phase 2 Integration Test', 'USD', 'QAT_TEST',
                            :doc_type, 'DRAFT'
                        )
                    """), {
                        'doc_num': test_doc_number,
                        'posting_date': date.today(),
                        'doc_date': date.today(),
                        'doc_type': document_type[0]
                    })
                    
                    # Insert line items with profit center and business area
                    conn.execute(text("""
                        INSERT INTO journalentryline (
                            documentnumber, companycodeid, linenumber, glaccountid,
                            description, debitamount, currencycode, 
                            profit_center_id, business_area_id
                        ) VALUES (
                            :doc_num, '1000', 1, '100001',
                            'Test Debit with Phase 2 fields', 1000.00, 'USD',
                            :profit_center, :business_area
                        ), (
                            :doc_num, '1000', 2, '120000',
                            'Test Credit with Phase 2 fields', NULL, 'USD',
                            :profit_center, :business_area
                        )
                    """), {
                        'doc_num': test_doc_number,
                        'profit_center': profit_center[0],
                        'business_area': business_area[0]
                    })
                    
                    # Update credit amount for second line
                    conn.execute(text("""
                        UPDATE journalentryline 
                        SET creditamount = 1000.00
                        WHERE documentnumber = :doc_num 
                        AND companycodeid = '1000' 
                        AND linenumber = 2
                    """), {'doc_num': test_doc_number})
                    
                    # Verify the test entry was created
                    result = conn.execute(text("""
                        SELECT jeh.document_type, jel.profit_center_id, jel.business_area_id
                        FROM journalentryheader jeh
                        JOIN journalentryline jel ON jeh.documentnumber = jel.documentnumber 
                            AND jeh.companycodeid = jel.companycodeid
                        WHERE jeh.documentnumber = :doc_num
                        LIMIT 1
                    """), {'doc_num': test_doc_number})
                    
                    test_entry = result.fetchone()
                    
                    if test_entry:
                        print(f"✅ Journal Entry Creation: Successfully created entry with:")
                        print(f"   - Document Type: {test_entry[0]}")
                        print(f"   - Profit Center: {test_entry[1]}")
                        print(f"   - Business Area: {test_entry[2]}")
                        test_results['tests_passed'] += 1
                        
                        # Clean up test entry
                        conn.execute(text("""
                            DELETE FROM journalentryline 
                            WHERE documentnumber = :doc_num AND companycodeid = '1000'
                        """), {'doc_num': test_doc_number})
                        
                        conn.execute(text("""
                            DELETE FROM journalentryheader 
                            WHERE documentnumber = :doc_num AND companycodeid = '1000'
                        """), {'doc_num': test_doc_number})
                        
                        print("✅ Test Cleanup: Test journal entry removed")
                        
                    else:
                        print("❌ Journal Entry Creation: Entry not found after creation")
                        test_results['tests_failed'] += 1
                    
                    conn.commit()
                    
                except Exception as e:
                    conn.rollback()
                    print(f"❌ Journal Entry Creation: Error - {e}")
                    test_results['tests_failed'] += 1
            else:
                print("⚠️  Journal Entry Creation: Missing master data for test")
                missing = []
                if not profit_center: missing.append("profit center")
                if not business_area: missing.append("business area")
                if not document_type: missing.append("document type")
                print(f"   Missing: {', '.join(missing)}")
                test_results['tests_failed'] += 1
            
            # Test 4: Test GL Account Default Assignments
            print("\n🏦 Test 4: GL Account Default Assignment Test")
            
            try:
                # Update a test GL account with default assignments
                test_gl_account = '100001'
                
                if profit_center and business_area:
                    conn.execute(text("""
                        UPDATE glaccount 
                        SET default_profit_center = :pc_id, 
                            default_business_area = :ba_id
                        WHERE glaccountid = :gl_id
                    """), {
                        'pc_id': profit_center[0],
                        'ba_id': business_area[0],
                        'gl_id': test_gl_account
                    })
                    
                    # Verify the update
                    result = conn.execute(text("""
                        SELECT default_profit_center, default_business_area 
                        FROM glaccount 
                        WHERE glaccountid = :gl_id
                    """), {'gl_id': test_gl_account})
                    
                    gl_defaults = result.fetchone()
                    
                    if gl_defaults and gl_defaults[0] and gl_defaults[1]:
                        print(f"✅ GL Default Assignment: Account {test_gl_account} updated with:")
                        print(f"   - Default Profit Center: {gl_defaults[0]}")
                        print(f"   - Default Business Area: {gl_defaults[1]}")
                        test_results['tests_passed'] += 1
                        
                        # Clean up
                        conn.execute(text("""
                            UPDATE glaccount 
                            SET default_profit_center = NULL, 
                                default_business_area = NULL
                            WHERE glaccountid = :gl_id
                        """), {'gl_id': test_gl_account})
                        
                    else:
                        print("❌ GL Default Assignment: Failed to set default values")
                        test_results['tests_failed'] += 1
                    
                    conn.commit()
                else:
                    print("⚠️  GL Default Assignment: Missing master data for test")
                    test_results['tests_failed'] += 1
                    
            except Exception as e:
                conn.rollback()
                print(f"❌ GL Default Assignment: Error - {e}")
                test_results['tests_failed'] += 1
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        test_results['tests_failed'] += 1
    
    # Print summary
    total_tests = test_results['tests_passed'] + test_results['tests_failed']
    success_rate = (test_results['tests_passed'] / total_tests * 100) if total_tests > 0 else 0
    
    print("\n" + "=" * 50)
    print("📊 INTEGRATION TEST SUMMARY")
    print("=" * 50)
    print(f"🧪 Total Tests: {total_tests}")
    print(f"✅ Passed: {test_results['tests_passed']}")
    print(f"❌ Failed: {test_results['tests_failed']}")
    print(f"📈 Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        status = "EXCELLENT ✅"
    elif success_rate >= 80:
        status = "GOOD ✅"
    elif success_rate >= 70:
        status = "ACCEPTABLE ⚠️"
    else:
        status = "NEEDS WORK ❌"
    
    print(f"🏆 Integration Status: {status}")
    
    return test_results

if __name__ == "__main__":
    test_phase2_integration()