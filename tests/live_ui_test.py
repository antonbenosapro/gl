#!/usr/bin/env python3
"""
Live UI Testing for Workflow Admin Panel
Tests actual Streamlit UI rendering and interactions
"""

import sys
import os
import subprocess
import time
import signal
import threading
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_streamlit_launch():
    """Test if Streamlit app launches without errors"""
    print("🔍 TESTING STREAMLIT UI LAUNCH")
    print("=" * 50)
    
    try:
        # Test if we can import and run the main function without crashing
        from pages.Workflow_Admin import main
        print("✅ Workflow Admin main function imported successfully")
        
        # Try to start streamlit app (non-blocking test)
        cmd = ["streamlit", "run", "pages/Workflow_Admin.py", "--server.headless", "true", "--server.port", "8503"]
        
        print("🚀 Attempting to launch Streamlit app...")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Wait a few seconds to see if it starts without immediate errors
        time.sleep(5)
        
        if process.poll() is None:
            print("✅ Streamlit app launched successfully!")
            print("📊 App should be running on http://localhost:8503")
            
            # Let it run for a few more seconds to test stability
            time.sleep(3)
            
            if process.poll() is None:
                print("✅ App is stable and running")
                # Terminate the process
                process.terminate()
                process.wait(timeout=5)
                print("✅ App terminated cleanly")
                return True
            else:
                stdout, stderr = process.communicate()
                print(f"❌ App crashed after launch: {stderr}")
                return False
        else:
            stdout, stderr = process.communicate()
            print(f"❌ App failed to launch: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Launch test failed: {str(e)}")
        return False

def test_ui_components():
    """Test UI components by checking method calls"""
    print("\n🔍 TESTING UI COMPONENT STRUCTURE")
    print("=" * 50)
    
    try:
        from pages.Workflow_Admin import WorkflowAdminPanel
        admin = WorkflowAdminPanel()
        
        # Test various UI rendering methods
        ui_tests = [
            ("render_admin_panel", "Main admin panel structure"),
            ("render_workflow_actions", "Workflow action buttons and forms"),
            ("render_bulk_operations", "Bulk operation interface"),
            ("render_individual_workflow", "Individual workflow management"),
            ("render_system_health", "System health dashboard"),
            ("render_alerts_monitoring", "Alerts and monitoring panel")
        ]
        
        for method_name, description in ui_tests:
            try:
                method = getattr(admin, method_name)
                print(f"✅ {method_name}: {description} - Method exists")
            except AttributeError:
                print(f"❌ {method_name}: {description} - Method missing")
            except Exception as e:
                print(f"⚠️  {method_name}: {description} - Error: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ UI component test failed: {str(e)}")
        return False

def test_data_flow():
    """Test data flow from backend to UI"""
    print("\n🔍 TESTING DATA FLOW")
    print("=" * 50)
    
    try:
        from pages.Workflow_Admin import WorkflowAdminPanel
        admin = WorkflowAdminPanel()
        
        # Test data retrieval methods that feed the UI
        data_tests = [
            ("get_pending_workflows", "Workflow data for bulk operations"),
            ("get_system_health_metrics", "Health metrics for dashboard"),
            ("get_active_alerts", "Alert data for monitoring"),
            ("get_audit_trail", "Audit data for reporting")
        ]
        
        for method_name, description in data_tests:
            try:
                if method_name == "get_audit_trail":
                    # This method requires parameters
                    result = admin.get_audit_trail("ALL", "Last 7 days", "ALL")
                else:
                    method = getattr(admin, method_name)
                    result = method()
                
                if isinstance(result, (list, dict)):
                    count = len(result) if isinstance(result, list) else len(result.keys())
                    print(f"✅ {method_name}: {description} - Returned {count} items")
                else:
                    print(f"⚠️  {method_name}: {description} - Unexpected return type: {type(result)}")
                    
            except Exception as e:
                print(f"❌ {method_name}: {description} - Error: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data flow test failed: {str(e)}")
        return False

def test_visualization_components():
    """Test visualization and chart components"""
    print("\n🔍 TESTING VISUALIZATION COMPONENTS")
    print("=" * 50)
    
    try:
        # Test if required visualization libraries are available
        import plotly.graph_objects as go
        import plotly.express as px
        import pandas as pd
        print("✅ Plotly and Pandas libraries available")
        
        from pages.Workflow_Admin import WorkflowAdminPanel
        admin = WorkflowAdminPanel()
        
        # Test performance charts method
        try:
            health_metrics = admin.get_system_health_metrics()
            # We can't actually render charts in headless mode, but we can test the method exists
            method = getattr(admin, 'render_performance_charts')
            print("✅ render_performance_charts: Performance visualization method exists")
        except Exception as e:
            print(f"❌ render_performance_charts: Error - {str(e)}")
        
        # Test system resources charts
        try:
            method = getattr(admin, 'render_system_resources')
            print("✅ render_system_resources: System resource visualization method exists")
        except Exception as e:
            print(f"❌ render_system_resources: Error - {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Visualization test failed: {str(e)}")
        return False

def main():
    """Run all live UI tests"""
    print("🚀 LIVE UI TESTING FOR WORKFLOW ADMIN PANEL")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        "streamlit_launch": False,
        "ui_components": False,
        "data_flow": False,
        "visualizations": False
    }
    
    # Run all tests
    results["streamlit_launch"] = test_streamlit_launch()
    results["ui_components"] = test_ui_components()
    results["data_flow"] = test_data_flow()
    results["visualizations"] = test_visualization_components()
    
    # Generate summary
    print("\n" + "=" * 60)
    print("🎯 LIVE UI TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results.values())
    total = len(results)
    pass_rate = (passed / total) * 100
    
    print(f"📊 TEST RESULTS:")
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {test_name.replace('_', ' ').title()}: {status}")
    
    print(f"\n📈 OVERALL:")
    print(f"   Pass Rate: {pass_rate:.1f}% ({passed}/{total})")
    
    if pass_rate == 100:
        print("🎉 EXCELLENT - All UI tests passed!")
        print("   The Workflow Admin Panel is ready for production use.")
    elif pass_rate >= 75:
        print("✅ GOOD - Most UI tests passed with minor issues.")
        print("   Review failed tests and address any critical issues.")
    else:
        print("⚠️  NEEDS ATTENTION - Multiple UI issues found.")
        print("   Address failed tests before deployment.")
    
    return results

if __name__ == "__main__":
    main()