"""Comprehensive User Testing Framework for Security Features"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
from datetime import datetime
from unittest.mock import patch, MagicMock
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

from auth.middleware import StreamlitAuthenticator
from auth.simple_auth import simple_auth_service
from auth.security_monitor import security_monitor
from auth.session_manager import session_manager


@dataclass
class TestUser:
    """Represents a test user with credentials and expected permissions"""
    username: str
    password: str
    full_name: str
    email: str
    role: str
    approval_authority: str
    companies: List[str]
    permissions: List[str]
    must_change_password: bool = True
    is_active: bool = True


@dataclass
class UserTestResult:
    """Represents the result of user testing"""
    username: str
    test_name: str
    success: bool
    message: str
    execution_time_ms: float
    details: Dict[str, Any] = None


class UserTestingFramework:
    """Framework for testing all users with new security features"""
    
    def __init__(self):
        self.authenticator = StreamlitAuthenticator()
        self.test_results: List[UserTestResult] = []
        
        # Define all system users based on documentation
        self.test_users = [
            TestUser(
                username="supervisor1",
                password="Supervisor123!",
                full_name="John Supervisor", 
                email="supervisor1@company.com",
                role="Manager",
                approval_authority="$0 - $9,999.99",
                companies=["1000", "2000"],
                permissions=["journal.read", "journal.create", "journal.approve_level_1"]
            ),
            TestUser(
                username="manager1",
                password="Manager123!",
                full_name="Jane Manager",
                email="manager1@company.com", 
                role="Manager",
                approval_authority="$10,000 - $99,999.99",
                companies=["1000", "2000"],
                permissions=["journal.read", "journal.create", "journal.approve_level_2"]
            ),
            TestUser(
                username="director1", 
                password="Director123!",
                full_name="Robert Director",
                email="director1@company.com",
                role="Admin",
                approval_authority="$100,000+",
                companies=["1000", "2000"],
                permissions=["journal.read", "journal.create", "journal.approve_level_3", "users.read"]
            ),
            TestUser(
                username="admin",
                password="admin123",  # Updated password
                full_name="System Administrator",
                email="admin@company.com",
                role="Super Admin", 
                approval_authority="All levels",
                companies=["1000", "2000"],
                permissions=["*"],  # All permissions
                must_change_password=False
            )
        ]
    
    def time_operation(self, operation, *args, **kwargs):
        """Time an operation and return result with execution time"""
        start_time = time.time()
        try:
            result = operation(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        return result, success, error, execution_time
    
    def test_user_authentication(self, user: TestUser) -> List[UserTestResult]:
        """Test basic authentication for a user"""
        results = []
        
        # Test 1: Valid login
        with patch('streamlit.session_state', {}):
            mock_session = {}
            with patch('streamlit.session_state', mock_session):
                def attempt_login():
                    return self.authenticator.login(user.username, user.password, remember_me=False)
                
                result, success, error, exec_time = self.time_operation(attempt_login)
                
                if success and result[0]:  # result is (success_bool, message)
                    results.append(UserTestResult(
                        username=user.username,
                        test_name="Valid Login",
                        success=True,
                        message=f"Successfully authenticated: {result[1]}",
                        execution_time_ms=exec_time,
                        details={"login_response": result}
                    ))
                else:
                    results.append(UserTestResult(
                        username=user.username,
                        test_name="Valid Login", 
                        success=False,
                        message=f"Login failed: {error or (result[1] if result else 'Unknown error')}",
                        execution_time_ms=exec_time
                    ))
        
        # Test 2: Invalid password
        with patch('streamlit.session_state', {}):
            mock_session = {}
            with patch('streamlit.session_state', mock_session):
                def attempt_invalid_login():
                    return self.authenticator.login(user.username, "wrong_password", remember_me=False)
                
                result, success, error, exec_time = self.time_operation(attempt_invalid_login)
                
                # We expect this to fail (success=True means the test passed)
                if success and not result[0]:  # Login should fail
                    results.append(UserTestResult(
                        username=user.username,
                        test_name="Invalid Password Rejection",
                        success=True,
                        message=f"Correctly rejected invalid password: {result[1]}",
                        execution_time_ms=exec_time
                    ))
                else:
                    results.append(UserTestResult(
                        username=user.username,
                        test_name="Invalid Password Rejection",
                        success=False,
                        message=f"Should have rejected invalid password: {error or 'Unexpected success'}",
                        execution_time_ms=exec_time
                    ))
        
        return results
    
    def test_csrf_protection(self, user: TestUser) -> List[UserTestResult]:
        """Test CSRF protection for a user"""
        results = []
        
        with patch('streamlit.session_state', {}):
            mock_session = {}
            with patch('streamlit.session_state', mock_session):
                # First login the user
                self.authenticator.login(user.username, user.password, remember_me=False)
                
                # Test CSRF token generation
                def generate_csrf():
                    return self.authenticator.generate_csrf_token()
                
                result, success, error, exec_time = self.time_operation(generate_csrf)
                
                if success and result:
                    results.append(UserTestResult(
                        username=user.username,
                        test_name="CSRF Token Generation",
                        success=True,
                        message=f"Generated CSRF token: {result[:16]}...",
                        execution_time_ms=exec_time,
                        details={"token_length": len(result)}
                    ))
                    
                    # Test CSRF token validation
                    def validate_csrf():
                        return self.authenticator.validate_csrf_token(result)
                    
                    val_result, val_success, val_error, val_exec_time = self.time_operation(validate_csrf)
                    
                    if val_success and val_result:
                        results.append(UserTestResult(
                            username=user.username,
                            test_name="CSRF Token Validation",
                            success=True,
                            message="CSRF token validation successful",
                            execution_time_ms=val_exec_time
                        ))
                    else:
                        results.append(UserTestResult(
                            username=user.username,
                            test_name="CSRF Token Validation", 
                            success=False,
                            message=f"CSRF validation failed: {val_error}",
                            execution_time_ms=val_exec_time
                        ))
                else:
                    results.append(UserTestResult(
                        username=user.username,
                        test_name="CSRF Token Generation",
                        success=False,
                        message=f"CSRF token generation failed: {error}",
                        execution_time_ms=exec_time
                    ))
        
        return results
    
    def test_session_persistence(self, user: TestUser) -> List[UserTestResult]:
        """Test session persistence for a user"""
        results = []
        
        # Test session data creation
        user_data = {
            'user_id': 123,
            'username': user.username,
            'permissions': user.permissions,
            'companies': user.companies,
            'csrf_token': 'test-csrf-token'
        }
        
        def create_session():
            return session_manager.create_session_data(user_data, remember_me=True)
        
        result, success, error, exec_time = self.time_operation(create_session)
        
        if success and result:
            results.append(UserTestResult(
                username=user.username,
                test_name="Session Data Creation",
                success=True,
                message="Session cookie created successfully",
                execution_time_ms=exec_time,
                details={"cookie_length": len(result)}
            ))
            
            # Test session validation
            def validate_session():
                return session_manager.validate_session_data(result)
            
            val_result, val_success, val_error, val_exec_time = self.time_operation(validate_session)
            
            if val_success and val_result:
                results.append(UserTestResult(
                    username=user.username,
                    test_name="Session Data Validation",
                    success=True,
                    message="Session validation successful",
                    execution_time_ms=val_exec_time,
                    details={"restored_username": val_result.get('username')}
                ))
            else:
                results.append(UserTestResult(
                    username=user.username,
                    test_name="Session Data Validation",
                    success=False,
                    message=f"Session validation failed: {val_error}",
                    execution_time_ms=val_exec_time
                ))
        else:
            results.append(UserTestResult(
                username=user.username,
                test_name="Session Data Creation",
                success=False,
                message=f"Session creation failed: {error}",
                execution_time_ms=exec_time
            ))
        
        return results
    
    def test_security_monitoring(self, user: TestUser) -> List[UserTestResult]:
        """Test security monitoring for a user"""
        results = []
        
        # Test failed login recording
        def record_failed_login():
            security_monitor.record_failed_login(
                user.username, "192.168.1.100", "Mozilla/5.0", "Test failed login"
            )
            return True
        
        result, success, error, exec_time = self.time_operation(record_failed_login)
        
        if success:
            results.append(UserTestResult(
                username=user.username,
                test_name="Failed Login Recording",
                success=True,
                message="Failed login recorded successfully",
                execution_time_ms=exec_time
            ))
        else:
            results.append(UserTestResult(
                username=user.username,
                test_name="Failed Login Recording",
                success=False,
                message=f"Failed login recording error: {error}",
                execution_time_ms=exec_time
            ))
        
        # Test successful login recording
        def record_successful_login():
            security_monitor.record_successful_login(
                user.username, "192.168.1.100", "Mozilla/5.0"
            )
            return True
        
        result, success, error, exec_time = self.time_operation(record_successful_login)
        
        if success:
            results.append(UserTestResult(
                username=user.username,
                test_name="Successful Login Recording",
                success=True,
                message="Successful login recorded successfully",
                execution_time_ms=exec_time
            ))
        else:
            results.append(UserTestResult(
                username=user.username,
                test_name="Successful Login Recording",
                success=False,
                message=f"Successful login recording error: {error}",
                execution_time_ms=exec_time
            ))
        
        return results
    
    def test_ip_and_user_agent_detection(self, user: TestUser) -> List[UserTestResult]:
        """Test IP and User Agent detection for a user"""
        results = []
        
        # Test IP detection with various headers
        test_scenarios = [
            {'x-forwarded-for': '203.0.113.42'},
            {'x-real-ip': '198.51.100.23'},
            {'cf-connecting-ip': '192.0.2.1'},
            {}  # No headers
        ]
        
        for i, headers in enumerate(test_scenarios):
            with patch('streamlit.context') as mock_context:
                mock_context.headers = headers
                
                def detect_ip():
                    return self.authenticator._get_client_ip()
                
                result, success, error, exec_time = self.time_operation(detect_ip)
                
                if success and result:
                    results.append(UserTestResult(
                        username=user.username,
                        test_name=f"IP Detection Scenario {i+1}",
                        success=True,
                        message=f"Detected IP: {result}",
                        execution_time_ms=exec_time,
                        details={"headers": headers, "detected_ip": result}
                    ))
                else:
                    results.append(UserTestResult(
                        username=user.username,
                        test_name=f"IP Detection Scenario {i+1}",
                        success=False,
                        message=f"IP detection failed: {error}",
                        execution_time_ms=exec_time
                    ))
        
        # Test User Agent detection
        with patch('streamlit.context') as mock_context:
            mock_context.headers = {'user-agent': 'Mozilla/5.0 (Test Browser)'}
            
            def detect_ua():
                return self.authenticator._get_user_agent()
            
            result, success, error, exec_time = self.time_operation(detect_ua)
            
            if success and result:
                results.append(UserTestResult(
                    username=user.username,
                    test_name="User Agent Detection",
                    success=True,
                    message=f"Detected UA: {result}",
                    execution_time_ms=exec_time,
                    details={"user_agent": result}
                ))
            else:
                results.append(UserTestResult(
                    username=user.username,
                    test_name="User Agent Detection",
                    success=False,
                    message=f"User agent detection failed: {error}",
                    execution_time_ms=exec_time
                ))
        
        return results
    
    def run_comprehensive_user_tests(self) -> Dict[str, List[UserTestResult]]:
        """Run all tests for all users"""
        print("🧪 Starting Comprehensive User Testing")
        print("=" * 60)
        
        all_results = {}
        
        for user in self.test_users:
            print(f"\n👤 Testing User: {user.username} ({user.full_name})")
            print("-" * 40)
            
            user_results = []
            
            # Run all test categories
            test_categories = [
                ("Authentication", self.test_user_authentication),
                ("CSRF Protection", self.test_csrf_protection),
                ("Session Persistence", self.test_session_persistence),
                ("Security Monitoring", self.test_security_monitoring),
                ("IP/UA Detection", self.test_ip_and_user_agent_detection)
            ]
            
            for category_name, test_function in test_categories:
                print(f"  🔬 Running {category_name} tests...")
                try:
                    category_results = test_function(user)
                    user_results.extend(category_results)
                    
                    # Show immediate results
                    passed = sum(1 for r in category_results if r.success)
                    total = len(category_results)
                    print(f"    ✅ {passed}/{total} tests passed")
                    
                except Exception as e:
                    print(f"    ❌ Error in {category_name}: {e}")
                    user_results.append(UserTestResult(
                        username=user.username,
                        test_name=f"{category_name} (Error)",
                        success=False,
                        message=f"Test category failed: {e}",
                        execution_time_ms=0
                    ))
            
            all_results[user.username] = user_results
            
            # Summary for this user
            total_tests = len(user_results)
            passed_tests = sum(1 for r in user_results if r.success)
            avg_time = sum(r.execution_time_ms for r in user_results) / total_tests if total_tests > 0 else 0
            
            print(f"  📊 User Summary: {passed_tests}/{total_tests} passed ({passed_tests/total_tests*100:.1f}%)")
            print(f"  ⏱️  Average Response Time: {avg_time:.2f}ms")
        
        return all_results
    
    def generate_user_testing_report(self, results: Dict[str, List[UserTestResult]]) -> str:
        """Generate a comprehensive user testing report"""
        report_lines = []
        report_lines.append("# User Testing Report - Security Features")
        report_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Overall statistics
        total_tests = sum(len(user_results) for user_results in results.values())
        total_passed = sum(sum(1 for r in user_results if r.success) for user_results in results.values())
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        report_lines.append("## 📊 Overall Summary")
        report_lines.append(f"- **Total Tests Executed:** {total_tests}")
        report_lines.append(f"- **Tests Passed:** {total_passed}")
        report_lines.append(f"- **Tests Failed:** {total_tests - total_passed}")
        report_lines.append(f"- **Success Rate:** {overall_success_rate:.1f}%")
        report_lines.append(f"- **Users Tested:** {len(results)}")
        report_lines.append("")
        
        # Per-user results
        report_lines.append("## 👥 Per-User Results")
        
        for username, user_results in results.items():
            user = next((u for u in self.test_users if u.username == username), None)
            
            report_lines.append(f"### {username} - {user.full_name if user else 'Unknown'}")
            report_lines.append(f"**Role:** {user.role if user else 'Unknown'}")
            report_lines.append(f"**Authority:** {user.approval_authority if user else 'Unknown'}")
            report_lines.append("")
            
            user_passed = sum(1 for r in user_results if r.success)
            user_total = len(user_results)
            user_success_rate = (user_passed / user_total * 100) if user_total > 0 else 0
            avg_time = sum(r.execution_time_ms for r in user_results) / user_total if user_total > 0 else 0
            
            report_lines.append(f"**Summary:** {user_passed}/{user_total} tests passed ({user_success_rate:.1f}%)")
            report_lines.append(f"**Average Response Time:** {avg_time:.2f}ms")
            report_lines.append("")
            
            # Detailed test results
            report_lines.append("| Test Name | Status | Message | Time (ms) |")
            report_lines.append("|-----------|--------|---------|-----------|")
            
            for result in user_results:
                status = "✅ PASS" if result.success else "❌ FAIL"
                message = result.message[:50] + "..." if len(result.message) > 50 else result.message
                report_lines.append(f"| {result.test_name} | {status} | {message} | {result.execution_time_ms:.2f} |")
            
            report_lines.append("")
        
        # Security feature validation
        report_lines.append("## 🛡️ Security Feature Validation")
        
        security_features = {
            "Authentication": ["Valid Login", "Invalid Password Rejection"],
            "CSRF Protection": ["CSRF Token Generation", "CSRF Token Validation"],
            "Session Management": ["Session Data Creation", "Session Data Validation"],
            "Security Monitoring": ["Failed Login Recording", "Successful Login Recording"],
            "Client Detection": ["IP Detection", "User Agent Detection"]
        }
        
        for feature, test_names in security_features.items():
            feature_results = []
            for username, user_results in results.items():
                for result in user_results:
                    if any(test_name in result.test_name for test_name in test_names):
                        feature_results.append(result)
            
            if feature_results:
                feature_passed = sum(1 for r in feature_results if r.success)
                feature_total = len(feature_results)
                feature_success_rate = (feature_passed / feature_total * 100) if feature_total > 0 else 0
                
                status = "✅ VALIDATED" if feature_success_rate >= 90 else "⚠️ ISSUES FOUND" if feature_success_rate >= 70 else "❌ FAILED"
                report_lines.append(f"- **{feature}:** {status} ({feature_passed}/{feature_total} - {feature_success_rate:.1f}%)")
        
        report_lines.append("")
        
        # Recommendations
        report_lines.append("## 📋 Recommendations")
        
        if overall_success_rate >= 95:
            report_lines.append("✅ **EXCELLENT:** All users successfully tested with new security features.")
            report_lines.append("- System is ready for production deployment")
            report_lines.append("- All security enhancements working as expected")
        elif overall_success_rate >= 85:
            report_lines.append("⚠️ **GOOD:** Most tests passed with minor issues identified.")
            report_lines.append("- Review failed tests and address specific issues")
            report_lines.append("- Consider additional testing for failed scenarios")
        else:
            report_lines.append("❌ **ISSUES FOUND:** Significant problems identified requiring attention.")
            report_lines.append("- Do not deploy until critical issues are resolved")
            report_lines.append("- Investigate and fix failing test scenarios")
        
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("*Report generated by User Testing Framework*")
        
        return "\n".join(report_lines)


def main():
    """Main function to run user testing"""
    framework = UserTestingFramework()
    
    # Run comprehensive tests
    test_results = framework.run_comprehensive_user_tests()
    
    # Generate and save report
    report = framework.generate_user_testing_report(test_results)
    
    # Save report to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"tests/USER_TESTING_REPORT_{timestamp}.md"
    
    with open(report_filename, 'w') as f:
        f.write(report)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📋 USER TESTING COMPLETE")
    print("=" * 60)
    
    total_tests = sum(len(user_results) for user_results in test_results.values())
    total_passed = sum(sum(1 for r in user_results if r.success) for user_results in test_results.values())
    overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_tests - total_passed}")
    print(f"Success Rate: {overall_success_rate:.1f}%")
    print(f"Report saved: {report_filename}")
    
    return test_results


if __name__ == "__main__":
    main()