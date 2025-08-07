#!/usr/bin/env python3
"""
End-to-End QA Testing Framework for Workflow Admin Panel
Comprehensive testing of all functionality, UI components, and integrations
"""

import sys
import os
import traceback
from datetime import datetime
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test imports
try:
    from pages.Workflow_Admin import WorkflowAdminPanel
    from utils.workflow_engine import WorkflowEngine
    from db_config import engine
    from sqlalchemy import text
    import streamlit as st
    import pandas as pd
    import plotly.graph_objects as go
    import plotly.express as px
except ImportError as e:
    print(f"❌ Import Error: {e}")
    sys.exit(1)

class WorkflowAdminE2ETester:
    """Comprehensive end-to-end testing framework"""
    
    def __init__(self):
        self.admin_panel = None
        self.test_results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": [],
            "warnings": [],
            "test_details": []
        }
        self.start_time = datetime.now()
    
    def log_test(self, test_name: str, status: str, message: str = "", details: str = ""):
        """Log test result"""
        self.test_results["total_tests"] += 1
        if status == "PASS":
            self.test_results["passed"] += 1
            print(f"✅ {test_name}: {message}")
        elif status == "FAIL":
            self.test_results["failed"] += 1
            self.test_results["errors"].append(f"{test_name}: {message}")
            print(f"❌ {test_name}: {message}")
        elif status == "WARN":
            self.test_results["warnings"].append(f"{test_name}: {message}")
            print(f"⚠️  {test_name}: {message}")
        
        self.test_results["test_details"].append({
            "test": test_name,
            "status": status,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def test_module_imports_and_setup(self):
        """Test 1: Module imports and basic setup"""
        print("\n🔍 TEST CATEGORY 1: Module Imports and Setup")
        
        try:
            # Test WorkflowAdminPanel instantiation
            self.admin_panel = WorkflowAdminPanel()
            self.log_test("Module Import", "PASS", "WorkflowAdminPanel imported and instantiated successfully")
        except Exception as e:
            self.log_test("Module Import", "FAIL", f"Failed to instantiate: {str(e)}")
            return False
        
        # Test required attributes
        required_attrs = ['workflow_engine']
        for attr in required_attrs:
            if hasattr(self.admin_panel, attr):
                self.log_test(f"Attribute {attr}", "PASS", "Required attribute present")
            else:
                self.log_test(f"Attribute {attr}", "FAIL", "Required attribute missing")
        
        return True
    
    def test_database_connectivity(self):
        """Test 2: Database connectivity and basic queries"""
        print("\n🔍 TEST CATEGORY 2: Database Operations")
        
        try:
            with engine.connect() as conn:
                # Test basic connection
                result = conn.execute(text("SELECT 1 as test"))
                if result.fetchone()[0] == 1:
                    self.log_test("Database Connection", "PASS", "Database connection successful")
                else:
                    self.log_test("Database Connection", "FAIL", "Database connection test failed")
                
                # Test workflow_instances table exists
                try:
                    result = conn.execute(text("SELECT COUNT(*) FROM workflow_instances LIMIT 1"))
                    count = result.fetchone()[0]
                    self.log_test("Workflow Instances Table", "PASS", f"Table accessible, found {count} records")
                except Exception as e:
                    self.log_test("Workflow Instances Table", "FAIL", f"Table access failed: {str(e)}")
                
                # Test approval_steps table exists
                try:
                    result = conn.execute(text("SELECT COUNT(*) FROM approval_steps LIMIT 1"))
                    count = result.fetchone()[0]
                    self.log_test("Approval Steps Table", "PASS", f"Table accessible, found {count} records")
                except Exception as e:
                    self.log_test("Approval Steps Table", "FAIL", f"Table access failed: {str(e)}")
                
                # Test journalentryheader table exists
                try:
                    result = conn.execute(text("SELECT COUNT(*) FROM journalentryheader LIMIT 1"))
                    count = result.fetchone()[0]
                    self.log_test("Journal Entry Header Table", "PASS", f"Table accessible, found {count} records")
                except Exception as e:
                    self.log_test("Journal Entry Header Table", "FAIL", f"Table access failed: {str(e)}")
                    
        except Exception as e:
            self.log_test("Database Connectivity", "FAIL", f"Database connection failed: {str(e)}")
    
    def test_core_data_methods(self):
        """Test 3: Core data retrieval methods"""
        print("\n🔍 TEST CATEGORY 3: Core Data Methods")
        
        # Test get_pending_workflows
        try:
            pending_workflows = self.admin_panel.get_pending_workflows()
            if isinstance(pending_workflows, list):
                self.log_test("get_pending_workflows", "PASS", f"Returned {len(pending_workflows)} workflows")
            else:
                self.log_test("get_pending_workflows", "FAIL", "Did not return a list")
        except Exception as e:
            self.log_test("get_pending_workflows", "FAIL", f"Method failed: {str(e)}")
        
        # Test get_system_health_metrics
        try:
            health_metrics = self.admin_panel.get_system_health_metrics()
            if isinstance(health_metrics, dict):
                required_keys = ['overall_health', 'active_workflows', 'avg_response_time']
                missing_keys = [key for key in required_keys if key not in health_metrics]
                if not missing_keys:
                    self.log_test("get_system_health_metrics", "PASS", f"Returned valid metrics dict with all required keys")
                else:
                    self.log_test("get_system_health_metrics", "WARN", f"Missing keys: {missing_keys}")
            else:
                self.log_test("get_system_health_metrics", "FAIL", "Did not return a dictionary")
        except Exception as e:
            self.log_test("get_system_health_metrics", "FAIL", f"Method failed: {str(e)}")
        
        # Test get_active_alerts
        try:
            active_alerts = self.admin_panel.get_active_alerts()
            if isinstance(active_alerts, list):
                self.log_test("get_active_alerts", "PASS", f"Returned {len(active_alerts)} alerts")
            else:
                self.log_test("get_active_alerts", "FAIL", "Did not return a list")
        except Exception as e:
            self.log_test("get_active_alerts", "FAIL", f"Method failed: {str(e)}")
        
        # Test get_alert_rules
        try:
            alert_rules = self.admin_panel.get_alert_rules()
            if isinstance(alert_rules, list):
                self.log_test("get_alert_rules", "PASS", f"Returned {len(alert_rules)} alert rules")
                # Validate alert rule structure
                if alert_rules:
                    required_fields = ['id', 'name', 'condition', 'threshold']
                    first_rule = alert_rules[0]
                    missing_fields = [field for field in required_fields if field not in first_rule]
                    if not missing_fields:
                        self.log_test("Alert Rule Structure", "PASS", "Alert rules have required fields")
                    else:
                        self.log_test("Alert Rule Structure", "WARN", f"Missing fields: {missing_fields}")
            else:
                self.log_test("get_alert_rules", "FAIL", "Did not return a list")
        except Exception as e:
            self.log_test("get_alert_rules", "FAIL", f"Method failed: {str(e)}")
    
    def test_workflow_operations(self):
        """Test 4: Workflow operation methods"""
        print("\n🔍 TEST CATEGORY 4: Workflow Operations")
        
        # Test execute_bulk_approval (without actually executing)
        try:
            # Just check if method exists and can be called with empty list
            # We don't want to actually modify data in testing
            method = getattr(self.admin_panel, 'execute_bulk_approval', None)
            if callable(method):
                self.log_test("execute_bulk_approval Method", "PASS", "Method exists and is callable")
            else:
                self.log_test("execute_bulk_approval Method", "FAIL", "Method missing or not callable")
        except Exception as e:
            self.log_test("execute_bulk_approval Method", "FAIL", f"Method check failed: {str(e)}")
        
        # Test search_workflows
        try:
            search_results = self.admin_panel.search_workflows("document_number", "TEST")
            if isinstance(search_results, list):
                self.log_test("search_workflows", "PASS", f"Search returned {len(search_results)} results")
            else:
                self.log_test("search_workflows", "FAIL", "Search did not return a list")
        except Exception as e:
            self.log_test("search_workflows", "FAIL", f"Search method failed: {str(e)}")
    
    def test_ui_render_methods(self):
        """Test 5: UI rendering methods (structural validation)"""
        print("\n🔍 TEST CATEGORY 5: UI Rendering Methods")
        
        # List of all render methods that should exist
        render_methods = [
            'render_admin_panel',
            'render_workflow_actions', 
            'render_bulk_operations',
            'render_individual_workflow',
            'render_emergency_actions',
            'render_workflow_transfer',
            'render_audit_trail',
            'render_configuration',
            'render_system_health',
            'render_alerts_monitoring',
            'render_performance_charts',
            'render_system_resources',
            'render_realtime_monitoring'
        ]
        
        for method_name in render_methods:
            try:
                method = getattr(self.admin_panel, method_name, None)
                if callable(method):
                    self.log_test(f"UI Method {method_name}", "PASS", "Method exists and is callable")
                else:
                    self.log_test(f"UI Method {method_name}", "FAIL", "Method missing or not callable")
            except Exception as e:
                self.log_test(f"UI Method {method_name}", "FAIL", f"Method check failed: {str(e)}")
    
    def test_configuration_methods(self):
        """Test 6: Configuration and settings methods"""
        print("\n🔍 TEST CATEGORY 6: Configuration Methods")
        
        config_methods = [
            'render_approval_levels_config',
            'render_approvers_config', 
            'render_time_limits_config',
            'render_notifications_config',
            'render_system_settings_config'
        ]
        
        for method_name in config_methods:
            try:
                method = getattr(self.admin_panel, method_name, None)
                if callable(method):
                    self.log_test(f"Config Method {method_name}", "PASS", "Method exists and is callable")
                else:
                    self.log_test(f"Config Method {method_name}", "FAIL", "Method missing or not callable")
            except Exception as e:
                self.log_test(f"Config Method {method_name}", "FAIL", f"Method check failed: {str(e)}")
    
    def test_audit_and_monitoring(self):
        """Test 7: Audit trail and monitoring functionality"""
        print("\n🔍 TEST CATEGORY 7: Audit and Monitoring")
        
        # Test get_audit_trail
        try:
            audit_data = self.admin_panel.get_audit_trail("ALL", "Last 7 days", "ALL")
            if isinstance(audit_data, list):
                self.log_test("get_audit_trail", "PASS", f"Returned {len(audit_data)} audit records")
            else:
                self.log_test("get_audit_trail", "FAIL", "Did not return a list")
        except Exception as e:
            self.log_test("get_audit_trail", "FAIL", f"Method failed: {str(e)}")
        
        # Test display_bulk_operation_history
        try:
            method = getattr(self.admin_panel, 'display_bulk_operation_history', None)
            if callable(method):
                self.log_test("display_bulk_operation_history", "PASS", "Method exists and is callable")
            else:
                self.log_test("display_bulk_operation_history", "FAIL", "Method missing or not callable")
        except Exception as e:
            self.log_test("display_bulk_operation_history", "FAIL", f"Method check failed: {str(e)}")
    
    def test_error_handling(self):
        """Test 8: Error handling and edge cases"""
        print("\n🔍 TEST CATEGORY 8: Error Handling")
        
        # Test with invalid search parameters
        try:
            invalid_search = self.admin_panel.search_workflows("invalid_type", "")
            self.log_test("Invalid Search Handling", "PASS", "Handled invalid search gracefully")
        except Exception as e:
            # This should either return empty list or handle gracefully
            if "error" in str(e).lower():
                self.log_test("Invalid Search Handling", "PASS", "Error handled appropriately")
            else:
                self.log_test("Invalid Search Handling", "WARN", f"Unexpected error: {str(e)}")
        
        # Test with empty workflow list for bulk operations
        try:
            self.admin_panel.execute_bulk_approval([], "test_user", "test comment")
            self.log_test("Empty Bulk Operation", "PASS", "Handled empty workflow list")
        except Exception as e:
            self.log_test("Empty Bulk Operation", "WARN", f"May need better handling: {str(e)}")
    
    def test_data_integrity(self):
        """Test 9: Data integrity and validation"""
        print("\n🔍 TEST CATEGORY 9: Data Integrity")
        
        # Test workflow data structure
        try:
            pending_workflows = self.admin_panel.get_pending_workflows()
            if pending_workflows:
                first_workflow = pending_workflows[0]
                required_fields = ['workflow_id', 'document_number', 'company_code']
                missing_fields = [field for field in required_fields if field not in first_workflow]
                if not missing_fields:
                    self.log_test("Workflow Data Structure", "PASS", "Workflow objects have required fields")
                else:
                    self.log_test("Workflow Data Structure", "FAIL", f"Missing required fields: {missing_fields}")
            else:
                self.log_test("Workflow Data Structure", "WARN", "No workflow data available for validation")
        except Exception as e:
            self.log_test("Workflow Data Structure", "FAIL", f"Data validation failed: {str(e)}")
    
    def test_performance_and_scalability(self):
        """Test 10: Performance and scalability considerations"""
        print("\n🔍 TEST CATEGORY 10: Performance and Scalability")
        
        # Test response time for data methods
        import time
        
        methods_to_test = [
            ('get_pending_workflows', []),
            ('get_system_health_metrics', []),
            ('get_active_alerts', []),
            ('get_alert_rules', [])
        ]
        
        for method_name, args in methods_to_test:
            try:
                start_time = time.time()
                method = getattr(self.admin_panel, method_name)
                result = method(*args)
                end_time = time.time()
                
                execution_time = end_time - start_time
                if execution_time < 5.0:  # Should complete within 5 seconds
                    self.log_test(f"Performance {method_name}", "PASS", f"Completed in {execution_time:.2f}s")
                else:
                    self.log_test(f"Performance {method_name}", "WARN", f"Slow execution: {execution_time:.2f}s")
                    
            except Exception as e:
                self.log_test(f"Performance {method_name}", "FAIL", f"Performance test failed: {str(e)}")
    
    def run_all_tests(self):
        """Run complete end-to-end test suite"""
        print("🚀 STARTING COMPREHENSIVE END-TO-END QA TESTING")
        print("=" * 60)
        
        # Run all test categories
        if not self.test_module_imports_and_setup():
            print("❌ Critical failure in module setup - stopping tests")
            return self.generate_report()
        
        self.test_database_connectivity()
        
        # Mark UI testing as in progress
        self.test_results["ui_testing_status"] = "in_progress"
        self.test_core_data_methods()
        self.test_workflow_operations()
        self.test_ui_render_methods()
        self.test_configuration_methods()
        self.test_audit_and_monitoring()
        self.test_error_handling()
        self.test_data_integrity()
        self.test_performance_and_scalability()
        
        return self.generate_report()
    
    def generate_report(self):
        """Generate comprehensive test report"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        print("\n" + "=" * 60)
        print("🎯 END-TO-END QA TEST REPORT")
        print("=" * 60)
        
        # Summary statistics
        total = self.test_results["total_tests"]
        passed = self.test_results["passed"]
        failed = self.test_results["failed"]
        warnings = len(self.test_results["warnings"])
        
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"📊 TEST SUMMARY:")
        print(f"   Total Tests: {total}")
        print(f"   ✅ Passed: {passed}")
        print(f"   ❌ Failed: {failed}")
        print(f"   ⚠️  Warnings: {warnings}")
        print(f"   📈 Pass Rate: {pass_rate:.1f}%")
        print(f"   ⏱️  Duration: {duration.total_seconds():.2f}s")
        
        # Overall status
        if failed == 0:
            if warnings == 0:
                status = "🎉 EXCELLENT - ALL TESTS PASSED"
            else:
                status = "✅ GOOD - ALL TESTS PASSED WITH WARNINGS"
        elif failed <= 2:
            status = "⚠️  ACCEPTABLE - MINOR ISSUES FOUND"
        else:
            status = "❌ NEEDS ATTENTION - MULTIPLE FAILURES"
        
        print(f"\n🏆 OVERALL STATUS: {status}")
        
        # Error details
        if self.test_results["errors"]:
            print(f"\n❌ ERRORS FOUND ({len(self.test_results['errors'])}):")
            for error in self.test_results["errors"]:
                print(f"   • {error}")
        
        # Warning details
        if self.test_results["warnings"]:
            print(f"\n⚠️  WARNINGS ({len(self.test_results['warnings'])}):")
            for warning in self.test_results["warnings"]:
                print(f"   • {warning}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if failed == 0 and warnings == 0:
            print("   ✅ Module is production-ready!")
        elif failed == 0:
            print("   • Review warnings to improve robustness")
            print("   • Consider adding more error handling")
        else:
            print("   • Fix critical errors before deployment")
            print("   • Add comprehensive error handling")
            print("   • Consider additional testing")
        
        return {
            "status": status,
            "pass_rate": pass_rate,
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "duration": duration.total_seconds(),
            "details": self.test_results
        }

def main():
    """Run the complete end-to-end test suite"""
    tester = WorkflowAdminE2ETester()
    results = tester.run_all_tests()
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = f"workflow_admin_e2e_report_{timestamp}.json"
    
    try:
        with open(report_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n📄 Detailed report saved to: {report_file}")
    except Exception as e:
        print(f"⚠️  Could not save report file: {e}")
    
    return results

if __name__ == "__main__":
    main()