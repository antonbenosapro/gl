#!/usr/bin/env python3
"""
Demo script for authentication system
Run this to test the authentication components
"""

from auth.security import security_manager, password_checker
from auth.models import UserCreate, LoginRequest
import json

def demo_password_security():
    """Demo password hashing and strength checking"""
    print("🔐 Password Security Demo")
    print("=" * 50)
    
    # Test password strength
    passwords = [
        "weak",
        "StrongPass123!",
        "password123",
        "MySecureP@ssw0rd!"
    ]
    
    for pwd in passwords:
        strength = password_checker.check_strength(pwd)
        print(f"Password: {pwd}")
        print(f"  Valid: {strength['is_valid']}")
        print(f"  Score: {strength['score']}/6")
        if strength['messages']:
            print(f"  Issues: {'; '.join(strength['messages'])}")
        print()
    
    # Test password hashing
    password = "TestPassword123!"
    hashed = security_manager.hash_password(password)
    verified = security_manager.verify_password(password, hashed)
    
    print(f"Password hashing:")
    print(f"  Original: {password}")
    print(f"  Hashed: {hashed[:50]}...")
    print(f"  Verification: {verified}")
    print()

def demo_jwt_tokens():
    """Demo JWT token creation and verification"""
    print("🎫 JWT Token Demo")
    print("=" * 50)
    
    user_id = 123
    username = "testuser"
    session_id = 456
    
    # Create access token
    access_token = security_manager.create_access_token(user_id, username, session_id)
    print(f"Access Token: {access_token[:50]}...")
    
    # Verify token
    payload = security_manager.verify_token(access_token)
    print(f"Token Payload: {json.dumps(payload, indent=2, default=str)}")
    
    # Create refresh token
    refresh_token = security_manager.create_refresh_token(user_id, username, session_id)
    print(f"Refresh Token: {refresh_token[:50]}...")
    print()

def demo_user_models():
    """Demo user data models"""
    print("👤 User Models Demo")
    print("=" * 50)
    
    # Test user creation model
    try:
        user_data = UserCreate(
            username="testuser",
            email="test@example.com",
            password="StrongPass123!",
            first_name="Test",
            last_name="User",
            role_ids=[1, 2]
        )
        print(f"Valid User Data: {user_data.username} ({user_data.email})")
    except Exception as e:
        print(f"User validation error: {e}")
    
    # Test invalid user data
    try:
        invalid_user = UserCreate(
            username="x",  # Too short
            email="invalid-email",  # Invalid email
            password="weak",  # Weak password
            first_name="Test",
            last_name="User"
        )
    except Exception as e:
        print(f"Expected validation error: {e}")
    
    print()

def main():
    """Run all demos"""
    print("🧾 GL ERP Authentication System Demo")
    print("=" * 60)
    print()
    
    demo_password_security()
    demo_jwt_tokens()
    demo_user_models()
    
    print("✅ Authentication system demo completed successfully!")
    print("\nTo run the full application:")
    print("  streamlit run Home.py")
    print("\nDefault login credentials:")
    print("  Username: admin")
    print("  Password: Admin123!")
    print("  ⚠️  Change this password after first login!")

if __name__ == "__main__":
    main()