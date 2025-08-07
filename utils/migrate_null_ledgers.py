#!/usr/bin/env python3
"""
Null Ledger Migration Utility

This utility fixes existing journal entry lines with NULL ledgerid values,
ensuring full enterprise compliance and backward compatibility.

Usage:
    python3 utils/migrate_null_ledgers.py [--dry-run] [--batch-size 1000]

Author: Claude Code Assistant
Date: August 6, 2025
"""

import sys
import os
sys.path.append('/home/anton/erp/gl')

import argparse
from datetime import datetime
from utils.ledger_assignment_service import ledger_assignment_service
from utils.logger import get_logger

logger = get_logger("migrate_null_ledgers")

def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description="Migrate NULL ledger assignments")
    parser.add_argument('--dry-run', action='store_true', 
                       help="Show what would be changed without making changes")
    parser.add_argument('--batch-size', type=int, default=1000,
                       help="Number of documents to process in each batch")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🏦 NULL LEDGER MIGRATION UTILITY")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE MIGRATION'}")
    print(f"Batch Size: {args.batch_size}")
    print(f"Started: {datetime.now()}")
    print()
    
    if args.dry_run:
        print("🔍 DRY RUN - No changes will be made")
        print("This will show you what would be migrated:")
        print()
    
    try:
        # Get migration statistics
        if args.dry_run:
            # In dry run, just show statistics
            from db_config import engine
            from sqlalchemy import text
            
            with engine.connect() as conn:
                stats = conn.execute(text("""
                    SELECT 
                        COUNT(DISTINCT documentnumber || '|' || companycodeid) as documents_affected,
                        COUNT(*) as total_lines_null,
                        MIN(documentnumber) as first_doc,
                        MAX(documentnumber) as last_doc
                    FROM journalentryline 
                    WHERE ledgerid IS NULL OR ledgerid = ''
                """)).mappings().first()
                
                print(f"📊 MIGRATION SCOPE:")
                print(f"   Documents affected: {stats['documents_affected']}")
                print(f"   Lines to migrate: {stats['total_lines_null']}")
                print(f"   Document range: {stats['first_doc']} to {stats['last_doc']}")
                print()
                
                # Show sample documents that would be affected
                sample_docs = conn.execute(text("""
                    SELECT DISTINCT documentnumber, companycodeid,
                           COUNT(*) as null_lines
                    FROM journalentryline 
                    WHERE ledgerid IS NULL OR ledgerid = ''
                    GROUP BY documentnumber, companycodeid
                    ORDER BY documentnumber
                    LIMIT 10
                """)).mappings().all()
                
                print("📋 SAMPLE AFFECTED DOCUMENTS:")
                for doc in sample_docs:
                    print(f"   {doc['documentnumber']} ({doc['companycodeid']}) - {doc['null_lines']} lines")
                print()
                
                # Show default ledger that would be assigned
                default_ledger = ledger_assignment_service.get_leading_ledger()
                ledger_info = ledger_assignment_service.get_all_ledgers()
                ledger_desc = ledger_info.get(default_ledger, {}).get('description', 'Unknown')
                
                print(f"🎯 DEFAULT LEDGER ASSIGNMENT:")
                print(f"   Ledger ID: {default_ledger}")
                print(f"   Description: {ledger_desc}")
                print()
                
                print("💡 To execute the migration, run without --dry-run flag")
                
        else:
            # Execute actual migration
            print("🚀 EXECUTING MIGRATION...")
            print()
            
            stats = ledger_assignment_service.migrate_historical_null_ledgers(
                batch_size=args.batch_size
            )
            
            print("✅ MIGRATION COMPLETED!")
            print(f"📊 RESULTS:")
            print(f"   Documents processed: {stats['documents_processed']}")
            print(f"   Lines updated: {stats['lines_updated']}")
            print(f"   Errors encountered: {stats['errors']}")
            print()
            
            if stats['errors'] > 0:
                print("⚠️  Some errors were encountered. Check the logs for details.")
            else:
                print("🎉 Migration completed successfully with no errors!")
                
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"❌ MIGRATION FAILED: {e}")
        return 1
    
    print(f"Completed: {datetime.now()}")
    print("=" * 80)
    return 0

if __name__ == "__main__":
    sys.exit(main())