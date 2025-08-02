#!/usr/bin/env python3
"""
Database migration script for GL ERP system
Handles schema migrations and data migrations
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from db_config import engine
from sqlalchemy import text
from utils.logger import get_logger

logger = get_logger("migrate_database")


class DatabaseMigration:
    """Database migration utility"""
    
    def __init__(self):
        self.migrations_dir = Path("migrations")
        self.migrations_dir.mkdir(exist_ok=True)
        self.engine = engine
    
    def create_migration_table(self):
        """Create migration tracking table if it doesn't exist"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(50) PRIMARY KEY,
            description TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            applied_by VARCHAR(100) DEFAULT CURRENT_USER
        );
        """
        
        try:
            with self.engine.begin() as conn:
                conn.execute(text(create_table_sql))
            logger.info("Migration tracking table created/verified")
            return True
        except Exception as e:
            logger.error(f"Failed to create migration table: {e}")
            return False
    
    def get_applied_migrations(self):
        """Get list of applied migrations"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT version FROM schema_migrations ORDER BY version"))
                return {row[0] for row in result}
        except Exception as e:
            logger.error(f"Failed to get applied migrations: {e}")
            return set()
    
    def get_pending_migrations(self):
        """Get list of pending migrations"""
        applied = self.get_applied_migrations()
        available = set()
        
        for migration_file in self.migrations_dir.glob("*.sql"):
            # Extract version from filename (format: YYYYMMDD_HHMMSS_description.sql)
            version = migration_file.stem.split('_')[0] + '_' + migration_file.stem.split('_')[1]
            available.add((version, migration_file))
        
        pending = []
        for version, file_path in available:
            if version not in applied:
                pending.append((version, file_path))
        
        return sorted(pending)
    
    def apply_migration(self, version: str, file_path: Path):
        """Apply a single migration"""
        logger.info(f"Applying migration {version}: {file_path.name}")
        
        try:
            with open(file_path, 'r') as f:
                migration_sql = f.read()
            
            with self.engine.begin() as conn:
                # Execute migration
                conn.execute(text(migration_sql))
                
                # Record migration as applied
                conn.execute(text("""
                    INSERT INTO schema_migrations (version, description) 
                    VALUES (:version, :description)
                """), {
                    'version': version,
                    'description': file_path.stem
                })
            
            logger.info(f"Migration {version} applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply migration {version}: {e}")
            return False
    
    def run_migrations(self):
        """Run all pending migrations"""
        if not self.create_migration_table():
            return False
        
        pending = self.get_pending_migrations()
        
        if not pending:
            logger.info("No pending migrations")
            return True
        
        logger.info(f"Found {len(pending)} pending migrations")
        
        for version, file_path in pending:
            if not self.apply_migration(version, file_path):
                logger.error(f"Migration failed at {version}")
                return False
        
        logger.info("All migrations applied successfully")
        return True
    
    def create_migration_file(self, description: str):
        """Create a new migration file template"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{description.lower().replace(' ', '_')}.sql"
        file_path = self.migrations_dir / filename
        
        template = f"""-- Migration: {description}
-- Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
-- Version: {timestamp}

-- Add your migration SQL here
-- Example:
-- CREATE TABLE example_table (
--     id SERIAL PRIMARY KEY,
--     name VARCHAR(100) NOT NULL,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- Remember to add rollback instructions in comments if needed
-- Rollback: DROP TABLE example_table;
"""
        
        with open(file_path, 'w') as f:
            f.write(template)
        
        logger.info(f"Created migration file: {file_path}")
        print(f"Migration file created: {file_path}")
        return file_path
    
    def show_migration_status(self):
        """Show current migration status"""
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()
        
        print("\nMigration Status:")
        print("=" * 50)
        print(f"Applied migrations: {len(applied)}")
        print(f"Pending migrations: {len(pending)}")
        
        if applied:
            print("\nApplied migrations:")
            for version in sorted(applied):
                print(f"  ✓ {version}")
        
        if pending:
            print("\nPending migrations:")
            for version, file_path in pending:
                print(f"  • {version} - {file_path.name}")
        
        if not applied and not pending:
            print("No migrations found.")
    
    def rollback_migration(self, version: str):
        """Rollback a specific migration (manual process)"""
        logger.warning(f"Manual rollback required for migration {version}")
        print(f"Manual rollback required for migration {version}")
        print("Please review the migration file and manually execute rollback SQL")
        
        # Remove from migration table
        try:
            with self.engine.begin() as conn:
                conn.execute(text("DELETE FROM schema_migrations WHERE version = :version"), 
                           {'version': version})
            logger.info(f"Removed migration {version} from tracking table")
            print(f"Removed migration {version} from tracking table")
        except Exception as e:
            logger.error(f"Failed to remove migration from tracking: {e}")


def create_initial_migrations():
    """Create initial migration files for the GL ERP system"""
    migrations_dir = Path("migrations")
    migrations_dir.mkdir(exist_ok=True)
    
    # Initial GL Account table migration
    glaccount_migration = """-- Create GL Account table
-- Migration: Initial GL Account table
-- Created: 2025-01-01

CREATE TABLE IF NOT EXISTS glaccount (
    glaccountid VARCHAR(10) PRIMARY KEY,
    companycodeid VARCHAR(5) NOT NULL,
    accountname VARCHAR(100) NOT NULL,
    accounttype VARCHAR(20) NOT NULL CHECK (accounttype IN ('Asset', 'Liability', 'Equity', 'Revenue', 'Expense')),
    isreconaccount BOOLEAN DEFAULT FALSE,
    isopenitemmanaged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_glaccount_company ON glaccount(companycodeid);
CREATE INDEX IF NOT EXISTS idx_glaccount_type ON glaccount(accounttype);

-- Rollback: DROP TABLE glaccount;
"""
    
    # Journal Entry tables migration
    journal_migration = """-- Create Journal Entry tables
-- Migration: Initial Journal Entry tables
-- Created: 2025-01-01

CREATE TABLE IF NOT EXISTS journalentryheader (
    documentnumber VARCHAR(20) NOT NULL,
    companycodeid VARCHAR(5) NOT NULL,
    postingdate DATE NOT NULL,
    documentdate DATE NOT NULL,
    fiscalyear INTEGER NOT NULL,
    period INTEGER NOT NULL CHECK (period BETWEEN 1 AND 12),
    reference VARCHAR(100),
    currencycode VARCHAR(3) NOT NULL,
    createdby VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (documentnumber, companycodeid)
);

CREATE TABLE IF NOT EXISTS journalentryline (
    documentnumber VARCHAR(20) NOT NULL,
    companycodeid VARCHAR(5) NOT NULL,
    linenumber INTEGER NOT NULL,
    glaccountid VARCHAR(10) NOT NULL,
    description VARCHAR(255) NOT NULL,
    debitamount DECIMAL(15,2) DEFAULT 0.00,
    creditamount DECIMAL(15,2) DEFAULT 0.00,
    currencycode VARCHAR(3) NOT NULL,
    ledgerid VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (documentnumber, companycodeid, linenumber),
    FOREIGN KEY (documentnumber, companycodeid) REFERENCES journalentryheader(documentnumber, companycodeid) ON DELETE CASCADE,
    FOREIGN KEY (glaccountid) REFERENCES glaccount(glaccountid),
    CHECK (debitamount >= 0 AND creditamount >= 0),
    CHECK (NOT (debitamount > 0 AND creditamount > 0))
);

CREATE INDEX IF NOT EXISTS idx_journal_header_date ON journalentryheader(postingdate);
CREATE INDEX IF NOT EXISTS idx_journal_header_period ON journalentryheader(fiscalyear, period);
CREATE INDEX IF NOT EXISTS idx_journal_line_account ON journalentryline(glaccountid);

-- Rollback: DROP TABLE journalentryline; DROP TABLE journalentryheader;
"""
    
    # Write migration files
    timestamp1 = "20250101_120000"
    timestamp2 = "20250101_120001"
    
    with open(migrations_dir / f"{timestamp1}_create_glaccount_table.sql", 'w') as f:
        f.write(glaccount_migration)
    
    with open(migrations_dir / f"{timestamp2}_create_journal_entry_tables.sql", 'w') as f:
        f.write(journal_migration)
    
    print(f"Initial migration files created in {migrations_dir}")


def main():
    """Main function to handle command line arguments"""
    parser = argparse.ArgumentParser(description="Database migration utility for GL ERP")
    parser.add_argument('--run', action='store_true', help='Run all pending migrations')
    parser.add_argument('--status', action='store_true', help='Show migration status')
    parser.add_argument('--create', help='Create new migration file with description')
    parser.add_argument('--rollback', help='Mark migration as rolled back (manual process)')
    parser.add_argument('--init', action='store_true', help='Create initial migration files')
    
    args = parser.parse_args()
    
    if args.init:
        create_initial_migrations()
        return
    
    migration_util = DatabaseMigration()
    
    if args.status:
        migration_util.show_migration_status()
    elif args.run:
        success = migration_util.run_migrations()
        if not success:
            sys.exit(1)
    elif args.create:
        migration_util.create_migration_file(args.create)
    elif args.rollback:
        migration_util.rollback_migration(args.rollback)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()