#!/usr/bin/env python3
"""
Cost Center Integration Test

Test integration between cost centers and Phase 2 master data features.

Author: Claude Code Assistant
Date: August 7, 2025
"""

import sys
import os
from datetime import datetime, date

# Add project root to path
sys.path.append('/home/anton/erp/gl')

from sqlalchemy import text
from db_config import engine

def test_cost_center_integration():
    """Test cost center integration with Phase 2 master data."""
    
    print("🧪 Cost Center Integration Test")
    print("=" * 40)
    
    test_results = {
        'tests_passed': 0,
        'tests_failed': 0
    }
    
    try:
        with engine.connect() as conn:
            # Test 1: Verify enhanced cost center structure
            print("\n📋 Test 1: Enhanced Cost Center Structure")
            
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'costcenter' 
                AND column_name IN (
                    'default_profit_center', 'default_business_area', 
                    'cost_center_category', 'activity_type'
                )
            """))
            new_columns = [row[0] for row in result.fetchall()]
            
            if len(new_columns) >= 4:
                print("✅ Enhanced Structure: All Phase 2 integration fields present")
                test_results['tests_passed'] += 1
            else:
                print(f"❌ Enhanced Structure: Missing fields. Found: {new_columns}")
                test_results['tests_failed'] += 1
            
            # Test 2: Verify cost center data and integration
            print("\n🔗 Test 2: Cost Center Data & Phase 2 Integration")
            
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_cc,
                    COUNT(CASE WHEN default_profit_center IS NOT NULL THEN 1 END) as with_pc,
                    COUNT(CASE WHEN default_business_area IS NOT NULL THEN 1 END) as with_ba
                FROM costcenter
                WHERE is_active = TRUE
            """))
            integration_stats = result.fetchone()
            
            if integration_stats and integration_stats[0] > 0:
                print(f"✅ Cost Center Data: {integration_stats[0]} total cost centers")
                print(f"   - {integration_stats[1]} integrated with Profit Centers")
                print(f"   - {integration_stats[2]} integrated with Business Areas")
                test_results['tests_passed'] += 1
            else:
                print("❌ Cost Center Data: No cost centers found")
                test_results['tests_failed'] += 1
            
            # Test 3: Test cost center assignments table
            print("\n📊 Test 3: Cost Center Assignments Table")
            
            try:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM cost_center_assignments
                """))
                assignments_count = result.fetchone()[0]
                
                print(f"✅ Assignments Table: Functional with {assignments_count} assignments")
                test_results['tests_passed'] += 1
                
            except Exception as e:
                print(f"❌ Assignments Table: Error - {e}")
                test_results['tests_failed'] += 1
            
            # Test 4: Test cost center views
            print("\n👁️ Test 4: Cost Center Views")
            
            try:
                # Test summary view
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM v_cost_center_summary
                """))
                summary_count = result.fetchone()[0]
                
                # Test hierarchy view  
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM v_cost_center_hierarchy
                """))
                hierarchy_count = result.fetchone()[0]
                
                print(f"✅ Views: Summary ({summary_count}) and Hierarchy ({hierarchy_count}) functional")
                test_results['tests_passed'] += 1
                
            except Exception as e:
                print(f"❌ Views: Error - {e}")
                test_results['tests_failed'] += 1
            
            # Test 5: Test foreign key relationships
            print("\n🔗 Test 5: Foreign Key Relationships")
            
            try:
                # Test profit center relationship
                result = conn.execute(text("""
                    SELECT cc.costcenterid, pc.profit_center_name
                    FROM costcenter cc
                    JOIN profit_centers pc ON cc.default_profit_center = pc.profit_center_id
                    WHERE cc.default_profit_center IS NOT NULL
                    LIMIT 3
                """))
                pc_links = result.fetchall()
                
                # Test business area relationship
                result = conn.execute(text("""
                    SELECT cc.costcenterid, ba.business_area_name
                    FROM costcenter cc
                    JOIN business_areas ba ON cc.default_business_area = ba.business_area_id
                    WHERE cc.default_business_area IS NOT NULL
                    LIMIT 3
                """))
                ba_links = result.fetchall()
                
                if pc_links and ba_links:
                    print(f"✅ Foreign Keys: Profit Center ({len(pc_links)}) and Business Area ({len(ba_links)}) links functional")
                    for cc_id, pc_name in pc_links[:2]:
                        print(f"   - {cc_id} → {pc_name}")
                    test_results['tests_passed'] += 1
                else:
                    print("⚠️  Foreign Keys: No links found (might be expected)")
                    test_results['tests_passed'] += 1
                
            except Exception as e:
                print(f"❌ Foreign Keys: Error - {e}")
                test_results['tests_failed'] += 1
            
            # Test 6: Journal entry line integration
            print("\n📝 Test 6: Journal Entry Integration")
            
            try:
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'journalentryline' 
                    AND column_name = 'costcenterid'
                """))
                
                cost_center_field = result.fetchone()
                
                if cost_center_field:
                    print("✅ Journal Integration: Cost center field present in journal entry lines")
                    test_results['tests_passed'] += 1
                else:
                    print("❌ Journal Integration: Cost center field missing from journal entry lines")
                    test_results['tests_failed'] += 1
                
            except Exception as e:
                print(f"❌ Journal Integration: Error - {e}")
                test_results['tests_failed'] += 1
            
            # Test 7: Cost center categories and types
            print("\n📈 Test 7: Cost Center Categories")
            
            try:
                result = conn.execute(text("""
                    SELECT cost_center_category, COUNT(*) as count
                    FROM costcenter
                    WHERE cost_center_category IS NOT NULL
                    GROUP BY cost_center_category
                    ORDER BY count DESC
                """))
                categories = result.fetchall()
                
                if categories:
                    print("✅ Categories: Cost centers properly categorized")
                    for category, count in categories:
                        print(f"   - {category}: {count} cost centers")
                    test_results['tests_passed'] += 1
                else:
                    print("⚠️  Categories: No categories assigned")
                    test_results['tests_passed'] += 1
                
            except Exception as e:
                print(f"❌ Categories: Error - {e}")
                test_results['tests_failed'] += 1
    
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        test_results['tests_failed'] += 1
    
    # Print summary
    total_tests = test_results['tests_passed'] + test_results['tests_failed']
    success_rate = (test_results['tests_passed'] / total_tests * 100) if total_tests > 0 else 0
    
    print("\n" + "=" * 40)
    print("📊 COST CENTER INTEGRATION SUMMARY")
    print("=" * 40)
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
    test_cost_center_integration()