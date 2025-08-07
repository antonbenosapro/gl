#!/usr/bin/env python3
"""
User Posting Access Analysis
Comprehensive report on who has GL posting access and permissions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from sqlalchemy import text
from db_config import engine

def analyze_posting_access():
    """Analyze user posting access and permissions"""
    
    print("👤 USER POSTING ACCESS ANALYSIS")
    print("=" * 60)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    with engine.connect() as conn:
        
        # 1. USERS WITH POSTING PERMISSIONS
        print("\n🔐 USERS WITH GL POSTING PERMISSIONS")
        print("-" * 50)
        
        result = conn.execute(text("""
            SELECT u.username, u.first_name, u.last_name, u.email, r.name as role,
                   STRING_AGG(p.name, ', ' ORDER BY p.name) as permissions
            FROM users u 
            JOIN user_roles ur ON u.id = ur.user_id 
            JOIN roles r ON ur.role_id = r.id 
            JOIN role_permissions rp ON r.id = rp.role_id 
            JOIN permissions p ON rp.permission_id = p.id 
            WHERE p.name IN ('journal.post', 'journal.approve', 'journal.emergency_post') 
            GROUP BY u.username, u.first_name, u.last_name, u.email, r.name
            ORDER BY u.username
        """))
        
        posting_users = result.fetchall()
        
        if posting_users:
            for user in posting_users:
                print(f"✅ {user[0]} ({user[1]} {user[2]})")
                print(f"   Email: {user[3]}")
                print(f"   Role: {user[4]}")
                print(f"   Posting Permissions: {user[5]}")
                print()
        else:
            print("❌ No users found with posting permissions!")
        
        # 2. POSTING PERMISSIONS BREAKDOWN
        print("\n📊 POSTING PERMISSIONS BREAKDOWN")
        print("-" * 50)
        
        posting_permissions = ['journal.post', 'journal.approve', 'journal.emergency_post']
        
        for permission in posting_permissions:
            result = conn.execute(text("""
                SELECT COUNT(DISTINCT u.id) 
                FROM users u 
                JOIN user_roles ur ON u.id = ur.user_id 
                JOIN roles r ON ur.role_id = r.id 
                JOIN role_permissions rp ON r.id = rp.role_id 
                JOIN permissions p ON rp.permission_id = p.id 
                WHERE p.name = :perm AND u.is_active = true
            """), {"perm": permission})
            
            count = result.fetchone()[0]
            
            result = conn.execute(text("""
                SELECT u.username 
                FROM users u 
                JOIN user_roles ur ON u.id = ur.user_id 
                JOIN roles r ON ur.role_id = r.id 
                JOIN role_permissions rp ON r.id = rp.role_id 
                JOIN permissions p ON rp.permission_id = p.id 
                WHERE p.name = :perm AND u.is_active = true
                ORDER BY u.username
            """), {"perm": permission})
            
            users = [row[0] for row in result.fetchall()]
            
            print(f"🔑 {permission}: {count} users")
            print(f"   Users: {', '.join(users) if users else 'None'}")
            print()
        
        # 3. COMPANY ACCESS ANALYSIS
        print("\n🏢 COMPANY ACCESS ANALYSIS")
        print("-" * 50)
        
        result = conn.execute(text("""
            SELECT COUNT(*) FROM user_company_access
        """))
        company_access_count = result.fetchone()[0]
        
        if company_access_count == 0:
            print("⚠️  WARNING: No company access configured!")
            print("   This means users may not have access to specific companies.")
            print("   Consider configuring company access for posting users.")
            
            # Show available companies
            result = conn.execute(text("""
                SELECT companycodeid, name FROM companycode ORDER BY companycodeid
            """))
            companies = result.fetchall()
            
            print(f"\n   Available Companies ({len(companies)}):")
            for company in companies:
                print(f"   - {company[0]}: {company[1] or 'No Name'}")
        else:
            result = conn.execute(text("""
                SELECT u.username, uca.company_code, uca.access_type
                FROM users u 
                JOIN user_company_access uca ON u.id = uca.user_id
                ORDER BY u.username, uca.company_code
            """))
            
            company_access = result.fetchall()
            print(f"✅ Company access configured for {len(set(ca[0] for ca in company_access))} users:")
            
            current_user = None
            for access in company_access:
                if access[0] != current_user:
                    current_user = access[0]
                    print(f"\n   {current_user}:")
                print(f"     - {access[1]} ({access[2]})")
        
        # 4. SEGREGATION OF DUTIES ANALYSIS
        print("\n🛡️ SEGREGATION OF DUTIES ANALYSIS")
        print("-" * 50)
        
        # Check users who can both create and post
        result = conn.execute(text("""
            SELECT u.username, u.first_name, u.last_name,
                   BOOL_OR(p.name = 'journal.create') as can_create,
                   BOOL_OR(p.name = 'journal.post') as can_post,
                   BOOL_OR(p.name = 'journal.approve') as can_approve
            FROM users u 
            JOIN user_roles ur ON u.id = ur.user_id 
            JOIN roles r ON ur.role_id = r.id 
            JOIN role_permissions rp ON r.id = rp.role_id 
            JOIN permissions p ON rp.permission_id = p.id 
            WHERE p.name IN ('journal.create', 'journal.post', 'journal.approve')
            GROUP BY u.username, u.first_name, u.last_name
            ORDER BY u.username
        """))
        
        sod_analysis = result.fetchall()
        
        create_and_post = []
        create_and_approve = []
        all_permissions = []
        
        for user in sod_analysis:
            username = user[0]
            can_create = user[3]
            can_post = user[4] 
            can_approve = user[5]
            
            if can_create and can_post:
                create_and_post.append(username)
            if can_create and can_approve:
                create_and_approve.append(username)
            if can_create and can_post and can_approve:
                all_permissions.append(username)
        
        if all_permissions:
            print(f"⚠️  SOD RISK: {len(all_permissions)} users have CREATE + POST + APPROVE permissions:")
            for user in all_permissions:
                print(f"   - {user}")
            print("   Consider segregating these duties for better control.")
        else:
            print("✅ No users have all three permissions (CREATE + POST + APPROVE)")
        
        if create_and_post:
            print(f"\n⚠️  SOD NOTE: {len(create_and_post)} users can CREATE + POST:")
            for user in create_and_post:
                print(f"   - {user}")
            print("   Posting engine enforces that users cannot post their own entries.")
        
        # 5. RECOMMENDATIONS
        print("\n💡 RECOMMENDATIONS")
        print("-" * 50)
        
        recommendations = []
        
        if company_access_count == 0:
            recommendations.append("Configure company access for all posting users")
        
        if all_permissions:
            recommendations.append("Consider segregating CREATE/POST/APPROVE duties")
        
        if len(posting_users) < 2:
            recommendations.append("Ensure at least 2 users have posting access for segregation")
        
        emergency_users = [u for u in posting_users if 'journal.emergency_post' in u[5]]
        if not emergency_users:
            recommendations.append("Consider granting emergency posting to at least one admin user")
        
        if not recommendations:
            recommendations.append("Current access configuration appears appropriate")
        
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
        
        # 6. SUMMARY
        print("\n📋 SUMMARY")
        print("-" * 50)
        
        total_users = conn.execute(text("SELECT COUNT(*) FROM users WHERE is_active = true")).fetchone()[0]
        posting_user_count = len(posting_users)
        
        print(f"Total Active Users: {total_users}")
        print(f"Users with Posting Access: {posting_user_count}")
        print(f"Posting Access Coverage: {(posting_user_count/total_users*100):.1f}%")
        print(f"Company Access Configured: {'Yes' if company_access_count > 0 else 'No'}")
        print(f"Emergency Posting Available: {'Yes' if emergency_users else 'No'}")
        
        # Final status
        if posting_user_count > 0 and not all_permissions:
            status = "🟢 GOOD"
        elif posting_user_count > 0:
            status = "🟡 REVIEW NEEDED"
        else:
            status = "🔴 CRITICAL"
        
        print(f"Overall Security Status: {status}")

if __name__ == "__main__":
    analyze_posting_access()