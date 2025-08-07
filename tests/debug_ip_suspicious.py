"""Debug script for IP suspicious test"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from auth.security_monitor import SecurityMonitor
import time

def debug_ip_suspicious():
    monitor = SecurityMonitor()
    
    # Clear state
    monitor.failed_attempts.clear()
    monitor.suspicious_ips.clear()
    monitor.recent_events.clear()
    monitor.last_alerts.clear()
    
    ip_address = "192.168.1.999"
    
    print(f"IP threshold: {monitor.ip_attempt_threshold}")
    print(f"IP window: {monitor.ip_attempt_window}")
    
    # Initially not suspicious
    print(f"Initially suspicious: {monitor.is_ip_suspicious(ip_address)}")
    
    # Add attempts up to threshold
    print(f"Adding {monitor.ip_attempt_threshold} failed attempts...")
    for i in range(monitor.ip_attempt_threshold):
        monitor.record_failed_login(f"uniqueuser{i}", ip_address, "Mozilla/5.0")
        print(f"  Attempt {i+1}: IP has {len(monitor.suspicious_ips[ip_address])} attempts")
    
    print(f"Final attempts for IP: {len(monitor.suspicious_ips[ip_address])}")
    print(f"Timestamps: {list(monitor.suspicious_ips[ip_address])}")
    print(f"Current time: {time.time()}")
    print(f"Window cutoff: {time.time() - monitor.ip_attempt_window}")
    
    # Check suspicious status
    result = monitor.is_ip_suspicious(ip_address)
    print(f"Is suspicious after {monitor.ip_attempt_threshold} attempts: {result}")
    
    # Check what is_ip_suspicious is actually doing
    current_time = time.time()
    cutoff_time = current_time - monitor.ip_attempt_window
    recent_attempts = sum(
        1 for timestamp in monitor.suspicious_ips[ip_address]
        if timestamp > cutoff_time
    )
    print(f"Recent attempts (manual count): {recent_attempts}")
    print(f"Threshold: {monitor.ip_attempt_threshold}")
    print(f"Should be suspicious: {recent_attempts >= monitor.ip_attempt_threshold}")

if __name__ == "__main__":
    debug_ip_suspicious()