#!/usr/bin/env python3
"""
Database backup script for GL ERP system
Supports full backups, incremental backups, and table-specific backups
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

logger = get_logger("backup_database")


class DatabaseBackup:
    """Database backup utility"""
    
    def __init__(self):
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # Parse database URL for connection parameters
        self.db_params = self._parse_database_url()
    
    def _parse_database_url(self):
        """Parse database URL to extract connection parameters"""
        url = settings.database_url
        # postgresql://user:password@host:port/dbname
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
    
    def create_full_backup(self, filename_suffix: str = None):
        """Create a full database backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = f"_{filename_suffix}" if filename_suffix else ""
        filename = f"gl_erp_full_backup_{timestamp}{suffix}.sql"
        backup_path = self.backup_dir / filename
        
        logger.info(f"Starting full database backup to {backup_path}")
        
        # Set environment variable for password
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_params['password']
        
        # Run pg_dump
        cmd = [
            'pg_dump',
            '-h', self.db_params['host'],
            '-p', self.db_params['port'],
            '-U', self.db_params['user'],
            '-d', self.db_params['database'],
            '-f', str(backup_path),
            '--verbose',
            '--clean',
            '--if-exists',
            '--create'
        ]
        
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Full backup completed successfully: {backup_path}")
                return backup_path
            else:
                logger.error(f"Backup failed: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"Backup failed with exception: {e}")
            return None
    
    def create_schema_backup(self):
        """Create a schema-only backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gl_erp_schema_backup_{timestamp}.sql"
        backup_path = self.backup_dir / filename
        
        logger.info(f"Starting schema backup to {backup_path}")
        
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_params['password']
        
        cmd = [
            'pg_dump',
            '-h', self.db_params['host'],
            '-p', self.db_params['port'],
            '-U', self.db_params['user'],
            '-d', self.db_params['database'],
            '-f', str(backup_path),
            '--schema-only',
            '--verbose'
        ]
        
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Schema backup completed successfully: {backup_path}")
                return backup_path
            else:
                logger.error(f"Schema backup failed: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"Schema backup failed with exception: {e}")
            return None
    
    def create_table_backup(self, table_name: str):
        """Create a backup of a specific table"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gl_erp_{table_name}_backup_{timestamp}.sql"
        backup_path = self.backup_dir / filename
        
        logger.info(f"Starting backup of table '{table_name}' to {backup_path}")
        
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_params['password']
        
        cmd = [
            'pg_dump',
            '-h', self.db_params['host'],
            '-p', self.db_params['port'],
            '-U', self.db_params['user'],
            '-d', self.db_params['database'],
            '-t', table_name,
            '-f', str(backup_path),
            '--verbose'
        ]
        
        try:
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            if result.returncode == 0:
                logger.info(f"Table backup completed successfully: {backup_path}")
                return backup_path
            else:
                logger.error(f"Table backup failed: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"Table backup failed with exception: {e}")
            return None
    
    def cleanup_old_backups(self, days_to_keep: int = 30):
        """Remove backup files older than specified days"""
        logger.info(f"Cleaning up backups older than {days_to_keep} days")
        
        cutoff_time = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
        removed_count = 0
        
        for backup_file in self.backup_dir.glob("*.sql"):
            if backup_file.stat().st_mtime < cutoff_time:
                backup_file.unlink()
                removed_count += 1
                logger.info(f"Removed old backup: {backup_file}")
        
        logger.info(f"Cleanup completed. Removed {removed_count} old backup files")
    
    def list_backups(self):
        """List all available backups"""
        backups = list(self.backup_dir.glob("*.sql"))
        backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        print(f"\nAvailable backups in {self.backup_dir}:")
        print("-" * 80)
        for backup in backups:
            size = backup.stat().st_size / (1024 * 1024)  # Size in MB
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"{backup.name:<50} {size:>8.2f} MB  {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not backups:
            print("No backups found.")


def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(description="Database backup utility for GL ERP")
    parser.add_argument('--type', choices=['full', 'schema', 'table'], default='full',
                       help='Type of backup to create')
    parser.add_argument('--table', help='Table name for table-specific backup')
    parser.add_argument('--suffix', help='Suffix to add to backup filename')
    parser.add_argument('--cleanup', type=int, metavar='DAYS',
                       help='Remove backups older than DAYS')
    parser.add_argument('--list', action='store_true', help='List available backups')
    
    args = parser.parse_args()
    
    backup_util = DatabaseBackup()
    
    if args.list:
        backup_util.list_backups()
        return
    
    if args.cleanup:
        backup_util.cleanup_old_backups(args.cleanup)
        return
    
    if args.type == 'full':
        result = backup_util.create_full_backup(args.suffix)
    elif args.type == 'schema':
        result = backup_util.create_schema_backup()
    elif args.type == 'table':
        if not args.table:
            print("Error: --table argument required for table backup")
            sys.exit(1)
        result = backup_util.create_table_backup(args.table)
    
    if result:
        print(f"Backup completed successfully: {result}")
    else:
        print("Backup failed. Check logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()