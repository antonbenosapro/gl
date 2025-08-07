#!/usr/bin/env python3
"""
Field Status Groups Management UI Test

Comprehensive test of the Field Status Groups Management interface including:
- Basic functionality verification
- Database integration testing
- UI component testing
- Error handling validation

Author: Claude Code Assistant
Date: August 7, 2025
"""

import sys
import os
from datetime import datetime, date
import requests
import time

# Add project root to path
sys.path.append('/home/anton/erp/gl')

from sqlalchemy import text
from db_config import engine

def test_field_status_groups_ui():
    """Test Field Status Groups Management UI functionality."""
    
    print("🧪 Field Status Groups Management UI Test")
    print("=" * 50)
    
    test_results = {
        'tests_passed': 0,
        'tests_failed': 0,
        'issues_found': []
    }
    
    try:
        # Test 1: Database Connection and Data Verification
        print("\n📋 Test 1: Database Connection and Data Verification")
        
        with engine.connect() as conn:
            # Verify field_status_groups table exists and has data
            result = conn.execute(text("SELECT COUNT(*) FROM field_status_groups"))
            groups_count = result.fetchone()[0]
            
            if groups_count > 0:
                print(f"✅ Database: {groups_count} field status groups found")
                test_results['tests_passed'] += 1
            else:
                print("❌ Database: No field status groups found")
                test_results['tests_failed'] += 1
                test_results['issues_found'].append("No field status groups data in database")
        
        # Test 2: Verify Required Database Columns
        print("\n🗃️ Test 2: Database Schema Verification")
        
        with engine.connect() as conn:
            required_columns = [
                'group_id', 'group_name', 'group_description', 'is_active',
                'allow_negative_postings', 'reference_field_status', 'document_header_text_status',
                'assignment_field_status', 'text_field_status', 'cost_center_status',
                'profit_center_status', 'business_area_status', 'trading_partner_status',
                'partner_company_status', 'tax_code_status', 'payment_terms_status',
                'baseline_date_status', 'amount_in_local_currency_status', 'exchange_rate_status',
                'quantity_status', 'base_unit_status', 'house_bank_status', 'account_id_status'
            ]
            
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'field_status_groups'
                AND column_name = ANY(:required_cols)
            """), {'required_cols': required_columns})
            
            existing_columns = [row[0] for row in result.fetchall()]
            missing_columns = set(required_columns) - set(existing_columns)
            
            if not missing_columns:
                print("✅ Schema: All required columns present")
                test_results['tests_passed'] += 1
            else:
                print(f"❌ Schema: Missing columns: {missing_columns}")
                test_results['tests_failed'] += 1
                test_results['issues_found'].append(f"Missing columns: {missing_columns}")
        
        # Test 3: Test SQL Queries Used by UI
        print("\n📊 Test 3: SQL Query Testing")
        
        with engine.connect() as conn:
            try:
                # Test main overview query
                overview_result = conn.execute(text("""
                    SELECT 
                        fsg.group_id,
                        fsg.group_name,
                        fsg.group_description,
                        fsg.is_active,
                        fsg.allow_negative_postings,
                        fsg.created_by,
                        fsg.created_at,
                        fsg.modified_by,
                        fsg.modified_at
                    FROM field_status_groups fsg
                    ORDER BY fsg.group_id
                    LIMIT 5
                """))
                overview_data = overview_result.fetchall()
                
                if overview_data:
                    print(f"✅ Overview Query: Retrieved {len(overview_data)} records")
                    test_results['tests_passed'] += 1
                else:
                    print("⚠️ Overview Query: No data returned")
                    test_results['tests_failed'] += 1
                
            except Exception as e:
                print(f"❌ Overview Query Failed: {e}")
                test_results['tests_failed'] += 1
                test_results['issues_found'].append(f"Overview query error: {e}")
        
        # Test 4: Test Usage Statistics Query
        print("\n📈 Test 4: Usage Statistics Query")
        
        with engine.connect() as conn:
            try:
                usage_result = conn.execute(text("""
                    SELECT 
                        fsg.group_id,
                        fsg.group_name,
                        COUNT(DISTINCT dt.document_type) as document_types_using,
                        COUNT(DISTINCT jeh.companycodeid) as companies_using
                    FROM field_status_groups fsg
                    LEFT JOIN document_types dt ON fsg.group_id = dt.field_status_group
                    LEFT JOIN journalentryheader jeh ON dt.document_type = jeh.document_type
                    GROUP BY fsg.group_id, fsg.group_name
                    ORDER BY fsg.group_id
                    LIMIT 5
                """))
                usage_data = usage_result.fetchall()
                
                print(f"✅ Usage Query: Retrieved {len(usage_data)} records")
                test_results['tests_passed'] += 1
                
                # Show sample data
                for row in usage_data[:3]:
                    print(f"   - Group {row[0]}: {row[2]} doc types, {row[3]} companies")
                
            except Exception as e:
                print(f"❌ Usage Query Failed: {e}")
                test_results['tests_failed'] += 1
                test_results['issues_found'].append(f"Usage query error: {e}")
        
        # Test 5: Test Field Status Analysis
        print("\n🔍 Test 5: Field Status Analysis")
        
        with engine.connect() as conn:
            try:
                analysis_result = conn.execute(text("""
                    SELECT 
                        group_id, group_name,
                        reference_field_status, document_header_text_status, assignment_field_status,
                        text_field_status, cost_center_status, profit_center_status, business_area_status,
                        trading_partner_status, partner_company_status, tax_code_status
                    FROM field_status_groups
                    WHERE is_active = TRUE
                    LIMIT 5
                """))
                analysis_data = analysis_result.fetchall()
                
                if analysis_data:
                    print(f"✅ Field Analysis: Retrieved {len(analysis_data)} active groups")
                    test_results['tests_passed'] += 1
                    
                    # Verify field status values are valid
                    valid_statuses = {'SUP', 'REQ', 'OPT', 'DIS'}
                    invalid_found = False
                    
                    for row in analysis_data:
                        for i in range(2, len(row)):  # Skip group_id and group_name
                            if row[i] and row[i] not in valid_statuses:
                                invalid_found = True
                                print(f"⚠️ Invalid field status found: {row[i]} in group {row[0]}")
                    
                    if not invalid_found:
                        print("✅ Field Status Values: All values are valid (SUP/REQ/OPT/DIS)")
                        test_results['tests_passed'] += 1
                    else:
                        test_results['tests_failed'] += 1
                        test_results['issues_found'].append("Invalid field status values found")
                        
                else:
                    print("❌ Field Analysis: No active groups found")
                    test_results['tests_failed'] += 1
                
            except Exception as e:
                print(f"❌ Field Analysis Failed: {e}")
                test_results['tests_failed'] += 1
                test_results['issues_found'].append(f"Field analysis error: {e}")
        
        # Test 6: Test Create Field Status Group Logic
        print("\n➕ Test 6: Create Field Status Group Logic")
        
        test_group_id = "TEST01"
        
        try:
            with engine.connect() as conn:
                # Clean up any existing test group
                conn.execute(text("DELETE FROM field_status_groups WHERE group_id = :test_id"), 
                           {'test_id': test_group_id})
                
                # Test insert new field status group
                conn.execute(text("""
                    INSERT INTO field_status_groups (
                        group_id, group_name, group_description, is_active, allow_negative_postings,
                        reference_field_status, document_header_text_status, assignment_field_status,
                        text_field_status, cost_center_status, profit_center_status, business_area_status,
                        trading_partner_status, partner_company_status, tax_code_status, payment_terms_status,
                        baseline_date_status, amount_in_local_currency_status, exchange_rate_status,
                        quantity_status, base_unit_status, house_bank_status, account_id_status,
                        created_by
                    ) VALUES (
                        :group_id, :group_name, :description, :is_active, :allow_negative,
                        :ref_field, :doc_header, :assignment, :text_field, :cost_center, :profit_center,
                        :business_area, :trading_partner, :partner_company, :tax_code, :payment_terms,
                        :baseline_date, :local_currency, :exchange_rate, :quantity, :base_unit,
                        :house_bank, :account_id, :created_by
                    )
                """), {
                    'group_id': test_group_id,
                    'group_name': 'Test Field Status Group',
                    'description': 'Test group for UI validation',
                    'is_active': True,
                    'allow_negative': True,
                    'ref_field': 'OPT',
                    'doc_header': 'OPT',
                    'assignment': 'OPT',
                    'text_field': 'OPT',
                    'cost_center': 'REQ',
                    'profit_center': 'REQ',
                    'business_area': 'OPT',
                    'trading_partner': 'SUP',
                    'partner_company': 'SUP',
                    'tax_code': 'OPT',
                    'payment_terms': 'SUP',
                    'baseline_date': 'SUP',
                    'local_currency': 'DIS',
                    'exchange_rate': 'OPT',
                    'quantity': 'SUP',
                    'base_unit': 'SUP',
                    'house_bank': 'SUP',
                    'account_id': 'SUP',
                    'created_by': 'UI_TEST'
                })
                
                # Verify the insert worked
                result = conn.execute(text("SELECT * FROM field_status_groups WHERE group_id = :test_id"), 
                                    {'test_id': test_group_id})
                test_group = result.fetchone()
                
                if test_group:
                    print(f"✅ Create Group: Test group {test_group_id} created successfully")
                    print(f"   - Group Name: {test_group[1]}")
                    print(f"   - Cost Center Status: {test_group[9]}")  # cost_center_status
                    print(f"   - Profit Center Status: {test_group[10]}")  # profit_center_status
                    test_results['tests_passed'] += 1
                else:
                    print(f"❌ Create Group: Test group {test_group_id} was not created")
                    test_results['tests_failed'] += 1
                
                # Clean up test group
                conn.execute(text("DELETE FROM field_status_groups WHERE group_id = :test_id"), 
                           {'test_id': test_group_id})
                conn.commit()
                
        except Exception as e:
            print(f"❌ Create Group Test Failed: {e}")
            test_results['tests_failed'] += 1
            test_results['issues_found'].append(f"Create group test error: {e}")
        
        # Test 7: Test UI Import Dependencies
        print("\n📦 Test 7: UI Import Dependencies")
        
        try:
            # Test imports that the UI uses
            import streamlit as st_test
            import pandas as pd_test
            import plotly.express as px_test
            import plotly.graph_objects as go_test
            from datetime import datetime as dt_test, date as date_test
            from sqlalchemy import text as text_test
            import json as json_test
            
            print("✅ Imports: All required modules import successfully")
            test_results['tests_passed'] += 1
            
        except ImportError as e:
            print(f"❌ Imports: Missing dependency - {e}")
            test_results['tests_failed'] += 1
            test_results['issues_found'].append(f"Import error: {e}")
        
        # Test 8: Test Authentication Integration
        print("\n🔐 Test 8: Authentication Integration")
        
        try:
            from auth.optimized_middleware import optimized_authenticator
            from utils.navigation import show_breadcrumb
            
            print("✅ Authentication: Auth modules import successfully")
            test_results['tests_passed'] += 1
            
        except ImportError as e:
            print(f"❌ Authentication: Auth module import failed - {e}")
            test_results['tests_failed'] += 1
            test_results['issues_found'].append(f"Auth import error: {e}")
        
        # Test 9: Test UI File Structure
        print("\n📁 Test 9: UI File Structure")
        
        ui_file_path = "/home/anton/erp/gl/pages/Field_Status_Groups_Management.py"
        
        if os.path.exists(ui_file_path):
            file_size = os.path.getsize(ui_file_path)
            print(f"✅ File Structure: UI file exists ({file_size} bytes)")
            test_results['tests_passed'] += 1
            
            # Check if file has main functions
            with open(ui_file_path, 'r') as f:
                content = f.read()
                
            required_functions = [
                'show_groups_overview',
                'show_create_field_status_group', 
                'show_field_status_analysis',
                'show_usage_reports',
                'show_advanced_configuration'
            ]
            
            missing_functions = []
            for func in required_functions:
                if f"def {func}(" not in content:
                    missing_functions.append(func)
            
            if not missing_functions:
                print("✅ Functions: All required UI functions present")
                test_results['tests_passed'] += 1
            else:
                print(f"❌ Functions: Missing functions: {missing_functions}")
                test_results['tests_failed'] += 1
                test_results['issues_found'].append(f"Missing functions: {missing_functions}")
                
        else:
            print(f"❌ File Structure: UI file not found at {ui_file_path}")
            test_results['tests_failed'] += 1
            test_results['issues_found'].append("UI file not found")
    
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        test_results['tests_failed'] += 1
        test_results['issues_found'].append(f"Critical error: {e}")
    
    # Print summary
    total_tests = test_results['tests_passed'] + test_results['tests_failed']
    success_rate = (test_results['tests_passed'] / total_tests * 100) if total_tests > 0 else 0
    
    print("\n" + "=" * 50)
    print("📊 FIELD STATUS GROUPS UI TEST SUMMARY")
    print("=" * 50)
    print(f"🧪 Total Tests: {total_tests}")
    print(f"✅ Passed: {test_results['tests_passed']}")
    print(f"❌ Failed: {test_results['tests_failed']}")
    print(f"📈 Success Rate: {success_rate:.1f}%")
    
    if test_results['issues_found']:
        print(f"\n⚠️ Issues Found ({len(test_results['issues_found'])}):")
        for i, issue in enumerate(test_results['issues_found'], 1):
            print(f"   {i}. {issue}")
    
    if success_rate >= 90:
        status = "EXCELLENT ✅"
    elif success_rate >= 80:
        status = "GOOD ✅"
    elif success_rate >= 70:
        status = "ACCEPTABLE ⚠️"
    else:
        status = "NEEDS WORK ❌"
    
    print(f"\n🏆 UI Test Status: {status}")
    
    return test_results

if __name__ == "__main__":
    test_field_status_groups_ui()