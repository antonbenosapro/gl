"""Reset user passwords for testing purposes"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_config import engine
from sqlalchemy import text
from auth.security import security_manager


def reset_user_passwords():
    """Reset passwords for all test users to known values"""
    print("🔐 RESETTING USER PASSWORDS FOR TESTING")
    print("=" * 50)
    
    # Define test users and their new passwords
    test_users = [
        {'username': 'admin', 'password': 'admin123'},
        {'username': 'supervisor1', 'password': 'Supervisor123!'},
        {'username': 'manager1', 'password': 'Manager123!'},
        {'username': 'director1', 'password': 'Director123!'},
    ]
    
    with engine.begin() as conn:
        for user_data in test_users:
            username = user_data['username']
            new_password = user_data['password']
            
            try:
                # Hash the new password
                password_hash = security_manager.hash_password(new_password)
                
                # Update the user's password in the database
                result = conn.execute(text("""
                    UPDATE users 
                    SET password_hash = :password_hash,
                        must_change_password = FALSE,
                        failed_login_attempts = 0,
                        locked_until = NULL
                    WHERE username = :username
                """), {
                    'password_hash': password_hash,
                    'username': username
                })
                
                if result.rowcount > 0:
                    print(f"✅ Reset password for {username}")
                    
                    # Verify the password works
                    verify_result = security_manager.verify_password(new_password, password_hash)
                    if verify_result:
                        print(f"   ✅ Password verification successful")
                    else:
                        print(f"   ❌ Password verification failed")
                else:
                    print(f"❌ User {username} not found")
                    
            except Exception as e:
                print(f"❌ Error resetting password for {username}: {e}")
    
    print("\n🔐 PASSWORD RESET SUMMARY:")
    print("=" * 30)
    print("admin: admin123")
    print("supervisor1: Supervisor123!")
    print("manager1: Manager123!")
    print("director1: Director123!")
    print("\n✅ All passwords reset successfully!")


if __name__ == "__main__":
    reset_user_passwords()