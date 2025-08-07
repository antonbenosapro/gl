#!/usr/bin/env python3
"""
Phase 2 Master Data QAT Framework

Comprehensive Quality Assurance Testing for:
- Profit Center Management
- Document Type Management  
- Business Area Management

Author: Claude Code Assistant
Date: August 6, 2025
"""

import sys
import os
import json
import time
import traceback
from datetime import datetime, date
from typing import Dict, List, Any, Tuple

# Add project root to path
sys.path.append('/home/anton/erp/gl')

try:
    import streamlit as st
    from sqlalchemy import text
    from db_config import engine
    import pandas as pd
    import subprocess
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some dependencies not available: {e}")
    DEPENDENCIES_AVAILABLE = False

class Phase2MasterDataQAT:
    """Quality Assurance Testing framework for Phase 2 master data features."""
    
    def __init__(self):
        self.test_results = []
        self.start_time = datetime.now()
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.warnings = 0
        
    def log_test(self, test_name: str, status: str, details: str = "", 
                 duration: float = 0.0, error: str = ""):
        """Log individual test result."""
        result = {
            'test_name': test_name,
            'status': status,  # PASS, FAIL, WARNING, SKIP
            'details': details,
            'duration_ms': round(duration * 1000, 2),
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        if status == "PASS":
            self.passed_tests += 1
            print(f"✅ {test_name}: {details}")
        elif status == "FAIL":
            self.failed_tests += 1
            print(f"❌ {test_name}: {details}")
            if error:
                print(f"   Error: {error}")
        elif status == "WARNING":
            self.warnings += 1
            print(f"⚠️  {test_name}: {details}")
        else:  # SKIP
            print(f"⏭️  {test_name}: {details}")
        
        self.total_tests += 1

    def test_database_connectivity(self) -> bool:
        """Test database connection and basic queries."""
        test_start = time.time()
        
        try:
            with engine.connect() as conn:
                # Test basic connectivity
                result = conn.execute(text("SELECT 1 as test"))
                if result.fetchone()[0] == 1:
                    duration = time.time() - test_start
                    self.log_test(
                        "Database Connectivity",
                        "PASS",
                        f"Connection established and basic query executed in {duration:.3f}s",
                        duration
                    )
                    return True
                else:
                    self.log_test(
                        "Database Connectivity", 
                        "FAIL",
                        "Basic query returned unexpected result"
                    )
                    return False
                    
        except Exception as e:
            duration = time.time() - test_start
            self.log_test(
                "Database Connectivity",
                "FAIL", 
                "Failed to connect to database",
                duration,
                str(e)
            )
            return False

    def test_profit_center_tables(self) -> Dict[str, Any]:
        """Test profit center database structures."""
        test_results = {}
        
        # Test profit_centers table
        test_start = time.time()
        try:
            with engine.connect() as conn:
                # Check table exists and structure
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = 'profit_centers'
                    ORDER BY ordinal_position
                """))
                columns = result.fetchall()
                
                expected_columns = [
                    'profit_center_id', 'profit_center_name', 'short_name', 
                    'company_code_id', 'controlling_area', 'person_responsible'
                ]
                found_columns = [col[0] for col in columns]
                
                missing_columns = [col for col in expected_columns if col not in found_columns]
                
                if not missing_columns:
                    duration = time.time() - test_start
                    self.log_test(
                        "Profit Center Table Structure",
                        "PASS",
                        f"All required columns present ({len(columns)} total columns)",
                        duration
                    )
                    test_results['table_structure'] = True
                else:
                    duration = time.time() - test_start
                    self.log_test(
                        "Profit Center Table Structure",
                        "FAIL",
                        f"Missing columns: {missing_columns}",
                        duration
                    )
                    test_results['table_structure'] = False
                
        except Exception as e:
            duration = time.time() - test_start
            self.log_test(
                "Profit Center Table Structure",
                "FAIL",
                "Failed to query table structure",
                duration,
                str(e)
            )
            test_results['table_structure'] = False
        
        # Test profit center data
        test_start = time.time()
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM profit_centers"))
                count = result.fetchone()[0]
                
                if count > 0:
                    duration = time.time() - test_start
                    self.log_test(
                        "Profit Center Data",
                        "PASS",
                        f"Found {count} profit centers in database",
                        duration
                    )
                    test_results['data_present'] = True
                else:
                    duration = time.time() - test_start
                    self.log_test(
                        "Profit Center Data",
                        "WARNING",
                        "No profit center data found (expected for fresh installation)",
                        duration
                    )
                    test_results['data_present'] = False
                    
        except Exception as e:
            duration = time.time() - test_start
            self.log_test(
                "Profit Center Data",
                "FAIL",
                "Failed to query profit center data",
                duration,
                str(e)
            )
            test_results['data_present'] = False
        
        # Test profit center views
        test_start = time.time()
        try:
            with engine.connect() as conn:
                # Test summary view
                result = conn.execute(text("SELECT * FROM v_profit_center_summary LIMIT 1"))
                summary_works = True
                
                # Test hierarchy view
                result = conn.execute(text("SELECT * FROM v_profit_center_hierarchy LIMIT 1"))
                hierarchy_works = True
                
                duration = time.time() - test_start
                self.log_test(
                    "Profit Center Views",
                    "PASS",
                    "Summary and hierarchy views are functional",
                    duration
                )
                test_results['views_functional'] = True
                
        except Exception as e:
            duration = time.time() - test_start
            self.log_test(
                "Profit Center Views",
                "FAIL",
                "Views are not functional",
                duration,
                str(e)
            )
            test_results['views_functional'] = False
        
        return test_results

    def test_document_type_tables(self) -> Dict[str, Any]:
        """Test document type database structures."""
        test_results = {}
        
        # Test document_types table
        test_start = time.time()
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'document_types'
                    ORDER BY ordinal_position
                """))
                columns = result.fetchall()
                
                expected_columns = [
                    'document_type', 'document_type_name', 'account_types_allowed',
                    'workflow_required', 'approval_required', 'field_status_group'
                ]
                found_columns = [col[0] for col in columns]
                
                missing_columns = [col for col in expected_columns if col not in found_columns]
                
                if not missing_columns:
                    duration = time.time() - test_start
                    self.log_test(
                        "Document Type Table Structure",
                        "PASS",
                        f"All required columns present ({len(columns)} total columns)",
                        duration
                    )
                    test_results['table_structure'] = True
                else:
                    duration = time.time() - test_start
                    self.log_test(
                        "Document Type Table Structure",
                        "FAIL",
                        f"Missing columns: {missing_columns}",
                        duration
                    )
                    test_results['table_structure'] = False
                
        except Exception as e:
            duration = time.time() - test_start
            self.log_test(
                "Document Type Table Structure",
                "FAIL",
                "Failed to query table structure",
                duration,
                str(e)
            )
            test_results['table_structure'] = False
        
        # Test document type data
        test_start = time.time()
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM document_types WHERE is_active = TRUE"))
                count = result.fetchone()[0]
                
                # Get sample data
                sample_result = conn.execute(text("SELECT document_type, document_type_name FROM document_types LIMIT 5"))
                samples = sample_result.fetchall()
                
                if count > 0:
                    duration = time.time() - test_start
                    sample_types = [f"{s[0]}({s[1]})" for s in samples]
                    self.log_test(
                        "Document Type Data",
                        "PASS",
                        f"Found {count} active document types: {', '.join(sample_types)}",
                        duration
                    )
                    test_results['data_present'] = True
                else:
                    duration = time.time() - test_start
                    self.log_test(
                        "Document Type Data",
                        "WARNING",
                        "No document type data found",
                        duration
                    )
                    test_results['data_present'] = False
                    
        except Exception as e:
            duration = time.time() - test_start
            self.log_test(
                "Document Type Data",
                "FAIL",
                "Failed to query document type data",
                duration,
                str(e)
            )
            test_results['data_present'] = False
        
        # Test number ranges table
        test_start = time.time()
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM document_number_ranges"))
                count = result.fetchone()[0]
                
                if count > 0:
                    duration = time.time() - test_start
                    self.log_test(
                        "Document Number Ranges",
                        "PASS",
                        f"Found {count} number range configurations",
                        duration
                    )
                    test_results['number_ranges'] = True
                else:
                    duration = time.time() - test_start
                    self.log_test(
                        "Document Number Ranges",
                        "WARNING",
                        "No number ranges configured",
                        duration
                    )
                    test_results['number_ranges'] = False
                    
        except Exception as e:
            duration = time.time() - test_start
            self.log_test(
                "Document Number Ranges",
                "FAIL",
                "Failed to query number ranges",
                duration,
                str(e)
            )
            test_results['number_ranges'] = False
        
        return test_results

    def test_business_area_tables(self) -> Dict[str, Any]:
        """Test business area database structures."""
        test_results = {}
        
        # Test business_areas table
        test_start = time.time()
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'business_areas'
                    ORDER BY ordinal_position
                """))
                columns = result.fetchall()
                
                expected_columns = [
                    'business_area_id', 'business_area_name', 'short_name',
                    'consolidation_relevant', 'budget_responsible'
                ]
                found_columns = [col[0] for col in columns]
                
                missing_columns = [col for col in expected_columns if col not in found_columns]
                
                if not missing_columns:
                    duration = time.time() - test_start
                    self.log_test(
                        "Business Area Table Structure",
                        "PASS",
                        f"All required columns present ({len(columns)} total columns)",
                        duration
                    )
                    test_results['table_structure'] = True
                else:
                    duration = time.time() - test_start
                    self.log_test(
                        "Business Area Table Structure",
                        "FAIL",
                        f"Missing columns: {missing_columns}",
                        duration
                    )
                    test_results['table_structure'] = False
                
        except Exception as e:
            duration = time.time() - test_start
            self.log_test(
                "Business Area Table Structure",
                "FAIL",
                "Failed to query table structure",
                duration,
                str(e)
            )
            test_results['table_structure'] = False
        
        # Test business area data
        test_start = time.time()
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM business_areas WHERE is_active = TRUE"))
                count = result.fetchone()[0]
                
                # Get sample data
                sample_result = conn.execute(text("SELECT business_area_id, business_area_name FROM business_areas LIMIT 5"))
                samples = sample_result.fetchall()
                
                if count > 0:
                    duration = time.time() - test_start
                    sample_areas = [f"{s[0]}({s[1]})" for s in samples]
                    self.log_test(
                        "Business Area Data",
                        "PASS",
                        f"Found {count} active business areas: {', '.join(sample_areas)}",
                        duration
                    )
                    test_results['data_present'] = True
                else:
                    duration = time.time() - test_start
                    self.log_test(
                        "Business Area Data",
                        "WARNING",
                        "No business area data found",
                        duration
                    )
                    test_results['data_present'] = False
                    
        except Exception as e:
            duration = time.time() - test_start
            self.log_test(
                "Business Area Data",
                "FAIL",
                "Failed to query business area data",
                duration,
                str(e)
            )
            test_results['data_present'] = False
        
        # Test derivation rules
        test_start = time.time()
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM business_area_derivation_rules WHERE is_active = TRUE"))
                count = result.fetchone()[0]
                
                if count > 0:
                    duration = time.time() - test_start
                    self.log_test(
                        "Business Area Derivation Rules",
                        "PASS",
                        f"Found {count} active derivation rules",
                        duration
                    )
                    test_results['derivation_rules'] = True
                else:
                    duration = time.time() - test_start
                    self.log_test(
                        "Business Area Derivation Rules",
                        "WARNING",
                        "No derivation rules configured",
                        duration
                    )
                    test_results['derivation_rules'] = False
                    
        except Exception as e:
            duration = time.time() - test_start
            self.log_test(
                "Business Area Derivation Rules",
                "FAIL",
                "Failed to query derivation rules",
                duration,
                str(e)
            )
            test_results['derivation_rules'] = False
        
        return test_results

    def test_ui_file_structure(self) -> Dict[str, Any]:
        """Test that all UI files exist and have basic structure."""
        test_results = {}
        
        ui_files = {
            'Profit_Center_Management.py': '/home/anton/erp/gl/pages/Profit_Center_Management.py',
            'Document_Type_Management.py': '/home/anton/erp/gl/pages/Document_Type_Management.py',
            'Business_Area_Management.py': '/home/anton/erp/gl/pages/Business_Area_Management.py'
        }
        
        for file_name, file_path in ui_files.items():
            test_start = time.time()
            try:
                if os.path.exists(file_path):
                    # Check file size
                    file_size = os.path.getsize(file_path)
                    
                    # Read file and check for key components
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Check for required components
                    required_components = [
                        'import streamlit as st',
                        'def main():',
                        'st.title(',
                        'authenticator.require_auth()',
                        'show_breadcrumb('
                    ]
                    
                    missing_components = [comp for comp in required_components if comp not in content]
                    
                    if not missing_components and file_size > 1000:
                        duration = time.time() - test_start
                        self.log_test(
                            f"UI File: {file_name}",
                            "PASS",
                            f"File exists and contains required components ({file_size:,} bytes)",
                            duration
                        )
                        test_results[file_name] = True
                    else:
                        duration = time.time() - test_start
                        issues = []
                        if missing_components:
                            issues.append(f"Missing components: {missing_components}")
                        if file_size <= 1000:
                            issues.append(f"File too small: {file_size} bytes")
                        
                        self.log_test(
                            f"UI File: {file_name}",
                            "FAIL",
                            f"Issues found: {'; '.join(issues)}",
                            duration
                        )
                        test_results[file_name] = False
                else:
                    duration = time.time() - test_start
                    self.log_test(
                        f"UI File: {file_name}",
                        "FAIL",
                        f"File does not exist at {file_path}",
                        duration
                    )
                    test_results[file_name] = False
                    
            except Exception as e:
                duration = time.time() - test_start
                self.log_test(
                    f"UI File: {file_name}",
                    "FAIL",
                    "Failed to read or analyze file",
                    duration,
                    str(e)
                )
                test_results[file_name] = False
        
        return test_results

    def test_data_integrity(self) -> Dict[str, Any]:
        """Test data integrity across all Phase 2 features."""
        test_results = {}
        
        # Test foreign key relationships
        test_start = time.time()
        try:
            with engine.connect() as conn:
                # Test profit center assignments referential integrity
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM profit_center_assignments pca
                    LEFT JOIN profit_centers pc ON pca.profit_center_id = pc.profit_center_id
                    WHERE pc.profit_center_id IS NULL
                """))
                orphaned_pc_assignments = result.fetchone()[0]
                
                # Test business area assignments referential integrity
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM business_area_assignments baa
                    LEFT JOIN business_areas ba ON baa.business_area_id = ba.business_area_id
                    WHERE ba.business_area_id IS NULL
                """))
                orphaned_ba_assignments = result.fetchone()[0]
                
                # Test document type number ranges referential integrity
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM document_number_ranges dnr
                    LEFT JOIN document_types dt ON dnr.document_type = dt.document_type
                    WHERE dt.document_type IS NULL
                """))
                orphaned_number_ranges = result.fetchone()[0]
                
                total_orphaned = orphaned_pc_assignments + orphaned_ba_assignments + orphaned_number_ranges
                
                if total_orphaned == 0:
                    duration = time.time() - test_start
                    self.log_test(
                        "Data Referential Integrity",
                        "PASS",
                        "All foreign key relationships are valid",
                        duration
                    )
                    test_results['referential_integrity'] = True
                else:
                    duration = time.time() - test_start
                    self.log_test(
                        "Data Referential Integrity",
                        "FAIL",
                        f"Found {total_orphaned} orphaned records across assignment tables",
                        duration
                    )
                    test_results['referential_integrity'] = False
                    
        except Exception as e:
            duration = time.time() - test_start
            self.log_test(
                "Data Referential Integrity",
                "FAIL",
                "Failed to check referential integrity",
                duration,
                str(e)
            )
            test_results['referential_integrity'] = False
        
        # Test data constraints
        test_start = time.time()
        try:
            with engine.connect() as conn:
                # Test profit center ID format (should be alphanumeric)
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM profit_centers 
                    WHERE profit_center_id ~ '^[A-Za-z0-9-_]+$'
                """))
                valid_pc_ids = result.fetchone()[0]
                
                result = conn.execute(text("SELECT COUNT(*) FROM profit_centers"))
                total_pcs = result.fetchone()[0]
                
                # Test business area ID format (should be 4 characters max)
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM business_areas 
                    WHERE LENGTH(business_area_id) <= 4
                """))
                valid_ba_ids = result.fetchone()[0]
                
                result = conn.execute(text("SELECT COUNT(*) FROM business_areas"))
                total_bas = result.fetchone()[0]
                
                # Test document type format (should be 2 characters)
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM document_types 
                    WHERE LENGTH(document_type) = 2
                """))
                valid_dt_ids = result.fetchone()[0]
                
                result = conn.execute(text("SELECT COUNT(*) FROM document_types"))
                total_dts = result.fetchone()[0]
                
                if (valid_pc_ids == total_pcs and valid_ba_ids == total_bas and valid_dt_ids == total_dts):
                    duration = time.time() - test_start
                    self.log_test(
                        "Data Format Constraints",
                        "PASS",
                        f"All IDs follow proper format conventions (PC:{valid_pc_ids}, BA:{valid_ba_ids}, DT:{valid_dt_ids})",
                        duration
                    )
                    test_results['format_constraints'] = True
                else:
                    duration = time.time() - test_start
                    issues = []
                    if valid_pc_ids != total_pcs:
                        issues.append(f"PC IDs: {valid_pc_ids}/{total_pcs} valid")
                    if valid_ba_ids != total_bas:
                        issues.append(f"BA IDs: {valid_ba_ids}/{total_bas} valid")
                    if valid_dt_ids != total_dts:
                        issues.append(f"DT IDs: {valid_dt_ids}/{total_dts} valid")
                    
                    self.log_test(
                        "Data Format Constraints",
                        "FAIL",
                        f"Format issues found: {'; '.join(issues)}",
                        duration
                    )
                    test_results['format_constraints'] = False
                    
        except Exception as e:
            duration = time.time() - test_start
            self.log_test(
                "Data Format Constraints",
                "FAIL",
                "Failed to check format constraints",
                duration,
                str(e)
            )
            test_results['format_constraints'] = False
        
        return test_results

    def test_ui_python_syntax(self) -> Dict[str, Any]:
        """Test Python syntax of UI files."""
        test_results = {}
        
        ui_files = {
            'Profit_Center_Management.py': '/home/anton/erp/gl/pages/Profit_Center_Management.py',
            'Document_Type_Management.py': '/home/anton/erp/gl/pages/Document_Type_Management.py',
            'Business_Area_Management.py': '/home/anton/erp/gl/pages/Business_Area_Management.py'
        }
        
        for file_name, file_path in ui_files.items():
            test_start = time.time()
            try:
                if os.path.exists(file_path):
                    # Test Python syntax by compiling
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source_code = f.read()
                    
                    compile(source_code, file_path, 'exec')
                    
                    duration = time.time() - test_start
                    self.log_test(
                        f"Python Syntax: {file_name}",
                        "PASS",
                        "File compiles without syntax errors",
                        duration
                    )
                    test_results[file_name] = True
                else:
                    duration = time.time() - test_start
                    self.log_test(
                        f"Python Syntax: {file_name}",
                        "FAIL",
                        f"File does not exist",
                        duration
                    )
                    test_results[file_name] = False
                    
            except SyntaxError as e:
                duration = time.time() - test_start
                self.log_test(
                    f"Python Syntax: {file_name}",
                    "FAIL",
                    f"Syntax error at line {e.lineno}: {e.msg}",
                    duration,
                    str(e)
                )
                test_results[file_name] = False
            except Exception as e:
                duration = time.time() - test_start
                self.log_test(
                    f"Python Syntax: {file_name}",
                    "FAIL",
                    "Failed to check syntax",
                    duration,
                    str(e)
                )
                test_results[file_name] = False
        
        return test_results

    def run_comprehensive_qat(self) -> Dict[str, Any]:
        """Run comprehensive Quality Assurance Testing."""
        print("🚀 Starting Phase 2 Master Data QAT")
        print("=" * 60)
        
        qat_results = {
            'start_time': self.start_time.isoformat(),
            'test_categories': {},
            'summary': {},
            'recommendations': []
        }
        
        # Test 1: Database Connectivity
        print("\n📡 Testing Database Connectivity...")
        db_connected = self.test_database_connectivity()
        
        if not db_connected:
            print("❌ Database connectivity failed. Skipping database-dependent tests.")
            qat_results['test_categories']['database'] = {'skipped': True, 'reason': 'No database connection'}
        else:
            # Test 2: Profit Center Tables
            print("\n💼 Testing Profit Center Database Structure...")
            qat_results['test_categories']['profit_centers'] = self.test_profit_center_tables()
            
            # Test 3: Document Type Tables
            print("\n📄 Testing Document Type Database Structure...")
            qat_results['test_categories']['document_types'] = self.test_document_type_tables()
            
            # Test 4: Business Area Tables
            print("\n🏢 Testing Business Area Database Structure...")
            qat_results['test_categories']['business_areas'] = self.test_business_area_tables()
            
            # Test 5: Data Integrity
            print("\n🔍 Testing Data Integrity...")
            qat_results['test_categories']['data_integrity'] = self.test_data_integrity()
        
        # Test 6: UI File Structure
        print("\n🖥️  Testing UI File Structure...")
        qat_results['test_categories']['ui_files'] = self.test_ui_file_structure()
        
        # Test 7: Python Syntax
        print("\n🐍 Testing Python Syntax...")
        qat_results['test_categories']['python_syntax'] = self.test_ui_python_syntax()
        
        # Generate summary
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        qat_results['summary'] = {
            'end_time': end_time.isoformat(),
            'total_duration_seconds': round(total_duration, 2),
            'total_tests': self.total_tests,
            'passed_tests': self.passed_tests,
            'failed_tests': self.failed_tests,
            'warnings': self.warnings,
            'success_rate': round((self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0, 1)
        }
        
        qat_results['detailed_results'] = self.test_results
        
        # Generate recommendations
        self.generate_recommendations(qat_results)
        
        return qat_results

    def generate_recommendations(self, qat_results: Dict[str, Any]):
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Check success rate
        success_rate = qat_results['summary']['success_rate']
        if success_rate < 80:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Overall Quality',
                'issue': f'Success rate is {success_rate}% (below 80% threshold)',
                'recommendation': 'Review and fix failing tests before production deployment'
            })
        
        # Check for database issues
        if 'database' in qat_results['test_categories'] and qat_results['test_categories']['database'].get('skipped'):
            recommendations.append({
                'priority': 'CRITICAL',
                'category': 'Database',
                'issue': 'Database connectivity failed',
                'recommendation': 'Verify database connection settings and ensure database is running'
            })
        
        # Check for missing data
        for category in ['profit_centers', 'document_types', 'business_areas']:
            if category in qat_results['test_categories']:
                if not qat_results['test_categories'][category].get('data_present', True):
                    recommendations.append({
                        'priority': 'MEDIUM',
                        'category': category.replace('_', ' ').title(),
                        'issue': f'No {category.replace("_", " ")} data found',
                        'recommendation': f'Execute migration scripts to populate {category.replace("_", " ")} master data'
                    })
        
        # Check for UI issues
        if 'ui_files' in qat_results['test_categories']:
            ui_results = qat_results['test_categories']['ui_files']
            failed_files = [file for file, success in ui_results.items() if not success]
            if failed_files:
                recommendations.append({
                    'priority': 'HIGH',
                    'category': 'UI Files',
                    'issue': f'UI file issues: {", ".join(failed_files)}',
                    'recommendation': 'Review and fix UI file structure and content issues'
                })
        
        # Check for syntax issues
        if 'python_syntax' in qat_results['test_categories']:
            syntax_results = qat_results['test_categories']['python_syntax']
            failed_syntax = [file for file, success in syntax_results.items() if not success]
            if failed_syntax:
                recommendations.append({
                    'priority': 'CRITICAL',
                    'category': 'Python Syntax',
                    'issue': f'Syntax errors in: {", ".join(failed_syntax)}',
                    'recommendation': 'Fix Python syntax errors before deployment'
                })
        
        qat_results['recommendations'] = recommendations

def main():
    """Run the Phase 2 Master Data QAT."""
    
    if not DEPENDENCIES_AVAILABLE:
        print("❌ Required dependencies not available. Please ensure all modules are installed.")
        return
    
    qat = Phase2MasterDataQAT()
    results = qat.run_comprehensive_qat()
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 QAT SUMMARY")
    print("=" * 60)
    
    summary = results['summary']
    print(f"⏱️  Total Duration: {summary['total_duration_seconds']}s")
    print(f"🧪 Total Tests: {summary['total_tests']}")
    print(f"✅ Passed: {summary['passed_tests']}")
    print(f"❌ Failed: {summary['failed_tests']}")
    print(f"⚠️  Warnings: {summary['warnings']}")
    print(f"📈 Success Rate: {summary['success_rate']}%")
    
    # Print recommendations
    if results['recommendations']:
        print(f"\n📋 RECOMMENDATIONS ({len(results['recommendations'])})")
        print("-" * 40)
        for i, rec in enumerate(results['recommendations'], 1):
            print(f"{i}. [{rec['priority']}] {rec['category']}")
            print(f"   Issue: {rec['issue']}")
            print(f"   Recommendation: {rec['recommendation']}")
            print()
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"/home/anton/erp/gl/tests/phase2_master_data_qat_results_{timestamp}.json"
    
    try:
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"💾 Detailed results saved to: {results_file}")
    except Exception as e:
        print(f"⚠️  Could not save results file: {e}")
    
    # Determine overall status
    if summary['success_rate'] >= 90:
        status = "EXCELLENT"
        emoji = "🏆"
    elif summary['success_rate'] >= 80:
        status = "GOOD"
        emoji = "✅"
    elif summary['success_rate'] >= 70:
        status = "ACCEPTABLE"
        emoji = "⚠️"
    else:
        status = "NEEDS IMPROVEMENT"
        emoji = "❌"
    
    print(f"\n{emoji} OVERALL QAT STATUS: {status} ({summary['success_rate']}%)")
    
    return results

if __name__ == "__main__":
    main()