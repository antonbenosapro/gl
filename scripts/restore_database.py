#!/usr/bin/env python3
"""
Database restoration script for GL ERP system
Supports restoring from backup files with various options
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from utils.logger import get_logger

logger = get_logger("restore_database")


class DatabaseRestore:
    """Database restoration utility"""
    
    def __init__(self):
        self.backup_dir = Path("backups")
        self.db_params = self._parse_database_url()
    
    def _parse_database_url(self):
        """Parse database URL to extract connection parameters"""
        url = settings.database_url
        parts = url.replace('postgresql://', '').split('@')
        user_pass = parts[0].split(':')
        host_port_db = parts[1].split('/')
        host_port = host_port_db[0].split(':')
        
        return {
            'user': user_pass[0],
            'password': user_pass[1] if len(user_pass) > 1 else '',
            'host': host_port[0],
            'port': host_port[1] if len(host_port) > 1 else '5432',
            'database': host_port_db[1]
        }
    
    def restore_from_file(self, backup_file: Path, confirm: bool = False):
        """Restore database from backup file"""
        if not backup_file.exists():
            logger.error(f"Backup file not found: {backup_file}")
            return False
        
        if not confirm:
            response = input(
                f"WARNING: This will overwrite the current database '{self.db_params['database']}'.\n"
                f"Are you sure you want to restore from '{backup_file.name}'? (yes/no): "
            )
            if response.lower() != 'yes':
                print("Restoration cancelled.")
                return False
        
        logger.info(f"Starting database restoration from {backup_file}")
        
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_params['password']
        
        # Use psql to restore
        cmd = [
            'psql',
            '-h', self.db_params['host'],
            '-p', self.db_params['port'],
            '-U', self.db_params['user'],
            '-d', self.db_params['database'],
            '-f', str(backup_file),
            '-v', 'ON_ERROR_STOP=1'
        ]
        
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Database restoration completed successfully from {backup_file}")
                return True
            else:
                logger.error(f"Restoration failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Restoration failed with exception: {e}")
            return False
    
    def list_backups(self):
        """List available backup files"""
        backups = list(self.backup_dir.glob("*.sql"))
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        print(f"\nAvailable backup files in {self.backup_dir}:")
        print("-" * 80)
        for i, backup in enumerate(backups, 1):
            size = backup.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"{i:2}. {backup.name:<45} {size:>8.2f} MB  {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not backups:
            print("No backup files found.")
            return None
        
        return backups
    
    def interactive_restore(self):
        """Interactive restoration process"""
        backups = self.list_backups()
        if not backups:
            return False
        
        while True:
            try:
                choice = input(f"\nSelect backup to restore (1-{len(backups)}) or 'q' to quit: ").strip()
                if choice.lower() == 'q':
                    return False
                
                index = int(choice) - 1
                if 0 <= index < len(backups):
                    selected_backup = backups[index]
                    break
                else:
                    print(f"Invalid selection. Please choose 1-{len(backups)}")
            except ValueError:
                print("Invalid input. Please enter a number or 'q'")
        
        print(f"\nSelected backup: {selected_backup.name}")
        size = selected_backup.stat().st_size / (1024 * 1024)
        mtime = datetime.fromtimestamp(selected_backup.stat().st_mtime)
        print(f"Size: {size:.2f} MB")
        print(f"Created: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return self.restore_from_file(selected_backup)
    
    def verify_backup_integrity(self, backup_file: Path):
        """Verify backup file integrity"""
        if not backup_file.exists():
            logger.error(f"Backup file not found: {backup_file}")
            return False
        
        logger.info(f"Verifying backup file integrity: {backup_file}")
        
        try:
            # Basic check: ensure file is not empty and contains SQL content
            with open(backup_file, 'r') as f:
                content = f.read(1000)  # Read first 1000 characters
                
                if not content.strip():
                    logger.error("Backup file is empty")
                    return False
                
                # Check for common SQL patterns
                sql_patterns = ['CREATE', 'INSERT', 'COPY', '--']
                if not any(pattern in content.upper() for pattern in sql_patterns):
                    logger.error("Backup file does not appear to contain valid SQL")
                    return False
            
            logger.info("Basic backup file integrity check passed")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying backup file: {e}")
            return False


def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(description="Database restoration utility for GL ERP")
    parser.add_argument('--file', help='Path to backup file to restore')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Interactive mode to select backup file')
    parser.add_argument('--list', action='store_true', help='List available backup files')
    parser.add_argument('--verify', help='Verify integrity of backup file')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    restore_util = DatabaseRestore()
    
    if args.list:
        restore_util.list_backups()
        return
    
    if args.verify:
        backup_file = Path(args.verify)
        if restore_util.verify_backup_integrity(backup_file):
            print(f"Backup file integrity check passed: {backup_file}")
        else:
            print(f"Backup file integrity check failed: {backup_file}")
            sys.exit(1)
        return
    
    if args.interactive:
        success = restore_util.interactive_restore()
    elif args.file:
        backup_file = Path(args.file)
        success = restore_util.restore_from_file(backup_file, args.yes)
    else:
        print("Error: Please specify --file or use --interactive mode")
        sys.exit(1)
    
    if success:
        print("Database restoration completed successfully")
    else:
        print("Database restoration failed")
        sys.exit(1)


if __name__ == "__main__":
    main()