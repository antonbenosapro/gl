"""Performance testing for security features"""

import time
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.middleware import StreamlitAuthenticator
from auth.session_manager import SecureSessionManager  
from auth.security_monitor import SecurityMonitor
from unittest.mock import patch


def time_function(func, *args, **kwargs):
    """Time a function execution"""
    start = time.time()
    result = func(*args, **kwargs)
    end = time.time()
    return result, (end - start) * 1000  # Return result and time in ms


def test_csrf_token_performance():
    """Test CSRF token generation and validation performance"""
    print("🔒 Testing CSRF Token Performance...")
    
    authenticator = StreamlitAuthenticator()
    mock_session = {}
    
    with patch('streamlit.session_state', mock_session):
        # Test token generation
        times = []
        for i in range(1000):
            _, exec_time = time_function(authenticator.generate_csrf_token)
            times.append(exec_time)
        
        avg_generation = sum(times) / len(times)
        max_generation = max(times)
        
        # Test token validation
        token = authenticator.generate_csrf_token()
        times = []
        for i in range(1000):
            _, exec_time = time_function(authenticator.validate_csrf_token, token)
            times.append(exec_time)
        
        avg_validation = sum(times) / len(times)
        max_validation = max(times)
        
        print(f"  Token Generation: Avg={avg_generation:.3f}ms, Max={max_generation:.3f}ms")
        print(f"  Token Validation: Avg={avg_validation:.3f}ms, Max={max_validation:.3f}ms")
        
        return avg_generation < 1.0 and avg_validation < 0.5  # Performance thresholds


def test_session_manager_performance():
    """Test session persistence performance"""
    print("💾 Testing Session Manager Performance...")
    
    session_manager = SecureSessionManager("test-secret-key")
    
    user_data = {
        'user_id': 123,
        'username': 'testuser',
        'permissions': ['read', 'write', 'admin'],
        'companies': ['COMP01', 'COMP02', 'COMP03'],
        'csrf_token': 'test-csrf-token-with-long-value'
    }
    
    # Test session creation
    times = []
    for i in range(1000):
        _, exec_time = time_function(session_manager.create_session_data, user_data, False)
        times.append(exec_time)
    
    avg_creation = sum(times) / len(times)
    max_creation = max(times)
    
    # Test session validation
    session_cookie = session_manager.create_session_data(user_data, False)
    times = []
    for i in range(1000):
        _, exec_time = time_function(session_manager.validate_session_data, session_cookie)
        times.append(exec_time)
    
    avg_validation = sum(times) / len(times)
    max_validation = max(times)
    
    print(f"  Session Creation: Avg={avg_creation:.3f}ms, Max={max_creation:.3f}ms")
    print(f"  Session Validation: Avg={avg_validation:.3f}ms, Max={max_validation:.3f}ms")
    
    return avg_creation < 2.0 and avg_validation < 1.0  # Performance thresholds


def test_security_monitor_performance():
    """Test security monitoring performance"""
    print("🚨 Testing Security Monitor Performance...")
    
    monitor = SecurityMonitor()
    
    # Test failed login recording
    times = []
    for i in range(1000):
        username = f"user{i % 100}"  # Cycle through 100 users
        ip = f"192.168.1.{i % 255}"   # Cycle through IPs
        _, exec_time = time_function(
            monitor.record_failed_login, username, ip, "Mozilla/5.0", "Test"
        )
        times.append(exec_time)
    
    avg_record = sum(times) / len(times)
    max_record = max(times)
    
    # Test IP suspicious check
    times = []
    test_ips = [f"192.168.1.{i}" for i in range(100)]
    for i in range(1000):
        ip = test_ips[i % 100]
        _, exec_time = time_function(monitor.is_ip_suspicious, ip)
        times.append(exec_time)
    
    avg_check = sum(times) / len(times)
    max_check = max(times)
    
    # Test security summary
    _, summary_time = time_function(monitor.get_security_summary, 24)
    
    print(f"  Failed Login Recording: Avg={avg_record:.3f}ms, Max={max_record:.3f}ms")
    print(f"  IP Suspicious Check: Avg={avg_check:.3f}ms, Max={max_check:.3f}ms")
    print(f"  Security Summary: {summary_time:.3f}ms")
    
    return avg_record < 0.5 and avg_check < 0.1  # Performance thresholds


def test_client_detection_performance():
    """Test client IP and user agent detection performance"""
    print("🌐 Testing Client Detection Performance...")
    
    authenticator = StreamlitAuthenticator()
    
    # Test IP detection with various header scenarios
    test_scenarios = [
        {'x-forwarded-for': '192.168.1.100, 10.0.0.1'},
        {'x-real-ip': '203.0.113.42'},
        {'cf-connecting-ip': '198.51.100.23'},
        {},  # No headers
    ]
    
    ip_times = []
    ua_times = []
    
    for scenario in test_scenarios:
        for i in range(250):  # 250 x 4 scenarios = 1000 tests
            with patch('streamlit.context') as mock_context:
                mock_context.headers = scenario
                
                _, ip_time = time_function(authenticator._get_client_ip)
                _, ua_time = time_function(authenticator._get_user_agent)
                
                ip_times.append(ip_time)
                ua_times.append(ua_time)
    
    avg_ip = sum(ip_times) / len(ip_times)
    max_ip = max(ip_times)
    avg_ua = sum(ua_times) / len(ua_times)
    max_ua = max(ua_times)
    
    print(f"  IP Detection: Avg={avg_ip:.3f}ms, Max={max_ip:.3f}ms")
    print(f"  User Agent Detection: Avg={avg_ua:.3f}ms, Max={max_ua:.3f}ms")
    
    return avg_ip < 0.5 and avg_ua < 0.5  # Performance thresholds


def test_memory_usage():
    """Test memory usage of security components"""
    print("🧠 Testing Memory Usage...")
    
    import tracemalloc
    
    tracemalloc.start()
    
    # Create instances
    authenticator = StreamlitAuthenticator()
    session_manager = SecureSessionManager("test-key")
    monitor = SecurityMonitor()
    
    # Simulate workload
    mock_session = {}
    
    with patch('streamlit.session_state', mock_session):
        # Generate CSRF tokens
        for i in range(100):
            authenticator.generate_csrf_token()
        
        # Create session data
        user_data = {'user_id': 123, 'username': 'test'}
        for i in range(100):
            session_manager.create_session_data(user_data, False)
        
        # Record security events
        for i in range(100):
            monitor.record_failed_login(f"user{i}", f"192.168.1.{i}", "Mozilla/5.0")
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    current_mb = current / 1024 / 1024
    peak_mb = peak / 1024 / 1024
    
    print(f"  Current Memory: {current_mb:.2f} MB")
    print(f"  Peak Memory: {peak_mb:.2f} MB")
    
    return peak_mb < 10.0  # Memory usage threshold


def run_performance_tests():
    """Run all performance tests"""
    print("⚡ Security Features Performance Testing")
    print("=" * 50)
    
    tests = [
        ("CSRF Token Performance", test_csrf_token_performance),
        ("Session Manager Performance", test_session_manager_performance),
        ("Security Monitor Performance", test_security_monitor_performance),
        ("Client Detection Performance", test_client_detection_performance),
        ("Memory Usage", test_memory_usage),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            start_time = time.time()
            passed = test_func()
            end_time = time.time()
            
            status = "✅ PASS" if passed else "⚠️  SLOW"
            duration = (end_time - start_time) * 1000
            
            print(f"  Status: {status} ({duration:.1f}ms total)")
            results.append((test_name, passed, duration))
            
        except Exception as e:
            print(f"  Status: ❌ ERROR - {e}")
            results.append((test_name, False, 0))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 PERFORMANCE TEST SUMMARY")
    print("=" * 50)
    
    passed_tests = sum(1 for _, passed, _ in results if passed)
    total_tests = len(results)
    total_time = sum(duration for _, _, duration in results)
    
    print(f"Tests Passed: {passed_tests}/{total_tests}")
    print(f"Total Time: {total_time:.1f}ms")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
    
    print(f"\n🎯 Performance Benchmarks:")
    for test_name, passed, duration in results:
        status = "✅" if passed else "⚠️"
        print(f"  {status} {test_name}: {duration:.1f}ms")


if __name__ == "__main__":
    run_performance_tests()