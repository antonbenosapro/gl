-- Migration: Consolidate Exchange Rate Tables
-- Date: August 7, 2025
-- Purpose: Consolidate duplicate exchange rate tables and clean up duplicates

-- Step 1: Backup and analyze existing data
CREATE TABLE IF NOT EXISTS exchangerate_backup_20250807 AS 
SELECT * FROM exchangerate;

CREATE TABLE IF NOT EXISTS exchange_rates_backup_20250807 AS 
SELECT * FROM exchange_rates;

-- Step 2: Migrate data from old exchangerate table to new exchange_rates table
-- Only insert data that doesn't already exist in the new table
INSERT INTO exchange_rates (
    from_currency, to_currency, rate_date, rate_type, exchange_rate,
    source, created_at, created_by, rate_source_type, is_official
)
SELECT DISTINCT
    er_old.fromcurrency as from_currency,
    er_old.tocurrency as to_currency, 
    er_old.ratedate as rate_date,
    COALESCE(er_old.rate_type, 'SPOT') as rate_type,
    er_old.rate as exchange_rate,
    COALESCE(er_old.rate_source, 'MIGRATED_FROM_OLD_TABLE') as source,
    COALESCE(er_old.created_at, CURRENT_TIMESTAMP) as created_at,
    COALESCE(er_old.created_by, 'MIGRATION') as created_by,
    COALESCE(er_old.rate_source, 'MANUAL') as rate_source_type,
    COALESCE(er_old.is_active, true) as is_official
FROM exchangerate er_old
WHERE NOT EXISTS (
    SELECT 1 FROM exchange_rates er_new 
    WHERE er_new.from_currency = er_old.fromcurrency
    AND er_new.to_currency = er_old.tocurrency
    AND er_new.rate_date = er_old.ratedate
    AND er_new.rate_type = COALESCE(er_old.rate_type, 'SPOT')
)
AND er_old.rate IS NOT NULL 
AND er_old.rate > 0;

-- Step 3: Update any references from old table to new table
-- Check for any views or functions that might reference the old table

-- Update Currency_Exchange_Admin.py and other code to use exchange_rates table consistently

-- Step 4: Create a unified view for backward compatibility
CREATE OR REPLACE VIEW v_exchange_rates_unified AS
SELECT 
    er.rate_id,
    er.from_currency as fromcurrency,
    er.to_currency as tocurrency,
    er.rate_date as ratedate,
    er.exchange_rate as rate,
    er.rate_type,
    er.source as rate_source,
    er.created_at,
    er.created_by,
    er.is_official as is_active,
    er.rate_source_type,
    er.publication_date,
    er.updated_at,
    er.updated_by
FROM exchange_rates er
WHERE er.exchange_rate > 0
ORDER BY er.rate_date DESC, er.from_currency, er.to_currency;

-- Step 5: Drop the old exchangerate table after verification
-- NOTE: This is commented out for safety - uncomment after verification
-- DROP TABLE IF EXISTS exchangerate;

-- Step 6: Add comments and update documentation
COMMENT ON TABLE exchange_rates IS 'Unified exchange rate table - consolidates all exchange rate data';
COMMENT ON VIEW v_exchange_rates_unified IS 'Backward compatibility view for old exchangerate table structure';

-- Step 7: Update indexes for optimal performance
-- The exchange_rates table already has good indexes, but let's ensure they're optimized

-- Step 8: Analyze the consolidated table
ANALYZE exchange_rates;

-- Step 9: Create summary of consolidation
DO $$
DECLARE
    old_table_count INTEGER;
    new_table_count INTEGER;
    migrated_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO old_table_count FROM exchangerate;
    SELECT COUNT(*) INTO new_table_count FROM exchange_rates;
    
    -- Count records that were migrated (approximately)
    SELECT COUNT(*) INTO migrated_count 
    FROM exchange_rates 
    WHERE created_by = 'MIGRATION' OR source = 'MIGRATED_FROM_OLD_TABLE';
    
    RAISE NOTICE 'Exchange Rate Table Consolidation Summary:';
    RAISE NOTICE '  Old exchangerate table records: %', old_table_count;
    RAISE NOTICE '  New exchange_rates table records: %', new_table_count;
    RAISE NOTICE '  Records migrated from old table: %', migrated_count;
    RAISE NOTICE '  Consolidation completed successfully';
END $$;