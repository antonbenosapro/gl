#!/usr/bin/env python3
"""
Migration script to switch from standard auth to optimized authentication middleware.
This script updates import statements across all pages to use the optimized authenticator.

Usage: python utils/migrate_to_optimized_auth.py
"""

import os
import re
from pathlib import Path

def migrate_file(file_path: Path) -> bool:
    """
    Migrate a single file to use optimized authentication.
    
    Args:
        file_path: Path to the file to migrate
        
    Returns:
        True if file was modified, False otherwise
    """
    try:
        # Read current content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace import statements
        replacements = [
            # Replace authenticator import
            (
                r'from auth\.middleware import authenticator',
                'from auth.optimized_middleware import optimized_authenticator as authenticator'
            ),
            # Replace direct middleware imports
            (
                r'from auth\.middleware import (.*)',
                r'from auth.optimized_middleware import \1'
            ),
            # Update any direct authenticator usage (if needed)
            (
                r'StreamlitAuthenticator\(\)',
                'OptimizedStreamlitAuthenticator()'
            )
        ]
        
        # Apply replacements
        for pattern, replacement in replacements:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Migrated: {file_path}")
            return True
        else:
            print(f"⏭️  No changes needed: {file_path}")
            return False
            
    except Exception as e:
        print(f"❌ Error migrating {file_path}: {e}")
        return False

def find_python_files() -> list:
    """Find all Python files that might need migration."""
    python_files = []
    
    # Directories to search
    search_dirs = [
        'pages',
        '.',  # Root directory (for Home.py, etc.)
        'auth',  # Auth modules themselves
        'utils'  # Utility modules
    ]
    
    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            for root, dirs, files in os.walk(search_dir):
                # Skip virtual environment and hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'env']
                
                for file in files:
                    if file.endswith('.py') and not file.startswith('.'):
                        file_path = Path(root) / file
                        python_files.append(file_path)
    
    return python_files

def check_file_needs_migration(file_path: Path) -> bool:
    """Check if a file needs migration."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for auth middleware imports
        patterns = [
            r'from auth\.middleware import',
            r'authenticator\.require_auth',
            r'StreamlitAuthenticator'
        ]
        
        for pattern in patterns:
            if re.search(pattern, content):
                return True
        
        return False
        
    except Exception:
        return False

def backup_file(file_path: Path):
    """Create a backup of the original file."""
    backup_path = file_path.with_suffix(f'{file_path.suffix}.backup')
    try:
        import shutil
        shutil.copy2(file_path, backup_path)
        print(f"📁 Backup created: {backup_path}")
    except Exception as e:
        print(f"⚠️  Warning: Could not create backup for {file_path}: {e}")

def main():
    """Main migration function."""
    print("🔄 Starting migration to optimized authentication middleware")
    print("=" * 60)
    
    # Find all Python files
    python_files = find_python_files()
    print(f"📋 Found {len(python_files)} Python files")
    
    # Filter files that need migration
    files_to_migrate = []
    for file_path in python_files:
        if check_file_needs_migration(file_path):
            files_to_migrate.append(file_path)
    
    print(f"🎯 {len(files_to_migrate)} files need migration")
    
    if not files_to_migrate:
        print("✅ No files need migration")
        return
    
    # Ask for confirmation
    print("\n📝 Files to be migrated:")
    for file_path in files_to_migrate:
        print(f"   • {file_path}")
    
    response = input(f"\n❓ Proceed with migration? [y/N]: ").lower().strip()
    if response not in ['y', 'yes']:
        print("❌ Migration cancelled")
        return
    
    # Create backups and migrate
    print("\n🚀 Starting migration...")
    migrated_count = 0
    
    for file_path in files_to_migrate:
        # Create backup
        backup_file(file_path)
        
        # Migrate file
        if migrate_file(file_path):
            migrated_count += 1
    
    print(f"\n✅ Migration completed!")
    print(f"📊 Summary:")
    print(f"   • Files processed: {len(files_to_migrate)}")
    print(f"   • Files migrated: {migrated_count}")
    print(f"   • Backups created: {len(files_to_migrate)}")
    
    print(f"\n🎉 Optimized authentication is now active!")
    print(f"📈 Benefits:")
    print(f"   • 8-hour session duration (was 1 hour)")
    print(f"   • 4-hour inactivity tolerance")
    print(f"   • Automatic token refresh")
    print(f"   • Reduced authentication overhead")
    print(f"   • Better session persistence")
    
    print(f"\n⚠️  Important notes:")
    print(f"   • Restart your Streamlit app to apply changes")
    print(f"   • Users will need to log in again once")
    print(f"   • Backup files created (.py.backup)")

if __name__ == "__main__":
    main()