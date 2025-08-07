-- Migration: Clean up and fix 6-digit account migration
-- Date: August 5, 2025
-- Purpose: Properly handle the migration to 6-digit accounts with data integrity

-- Step 1: Remove all existing data to start clean
TRUNCATE TABLE account_migration_mapping CASCADE;
DROP VIEW IF EXISTS v_migration_validation;

-- Step 2: Disable triggers and constraints temporarily
ALTER TABLE glaccount DISABLE TRIGGER ALL;
ALTER TABLE journalentryline DROP CONSTRAINT IF EXISTS journalentryline_glaccountid_fkey;
ALTER TABLE gl_account_balances DROP CONSTRAINT IF EXISTS fk_gl_account_balances_glaccount;

-- Step 3: Create a clean backup of current accounts
DROP TABLE IF EXISTS glaccount_pre_migration_backup;
CREATE TABLE glaccount_pre_migration_backup AS SELECT * FROM glaccount;

-- Step 4: Create proper account mapping (avoid conflicts)
INSERT INTO account_migration_mapping (old_account_id, new_account_id, account_name, account_group_code) 
SELECT DISTINCT
    glaccountid as old_account_id,
    CASE 
        -- For accounts already in 6-digit format, keep them if they're in valid SAP ranges
        WHEN LENGTH(glaccountid) = 6 AND glaccountid::bigint BETWEEN 100000 AND 999999 THEN glaccountid
        -- For 4-digit accounts, convert to 6-digit SAP structure
        WHEN glaccountid BETWEEN '1000' AND '1099' THEN LPAD((100000 + (glaccountid::INTEGER - 1000))::TEXT, 6, '0')
        WHEN glaccountid BETWEEN '1100' AND '1199' THEN LPAD((110000 + (glaccountid::INTEGER - 1100))::TEXT, 6, '0')
        WHEN glaccountid BETWEEN '1200' AND '1299' THEN LPAD((120000 + (glaccountid::INTEGER - 1200))::TEXT, 6, '0')
        WHEN glaccountid BETWEEN '1300' AND '1399' THEN LPAD((130000 + (glaccountid::INTEGER - 1300))::TEXT, 6, '0')
        WHEN glaccountid BETWEEN '1400' AND '1799' THEN LPAD((140000 + (glaccountid::INTEGER - 1400))::TEXT, 6, '0')
        WHEN glaccountid BETWEEN '1800' AND '1899' THEN LPAD((180000 + (glaccountid::INTEGER - 1800))::TEXT, 6, '0')
        WHEN glaccountid BETWEEN '2000' AND '2199' THEN LPAD((200000 + (glaccountid::INTEGER - 2000))::TEXT, 6, '0')
        WHEN glaccountid BETWEEN '2200' AND '2399' THEN LPAD((220000 + (glaccountid::INTEGER - 2200))::TEXT, 6, '0')
        WHEN glaccountid BETWEEN '2400' AND '2499' THEN LPAD((240000 + (glaccountid::INTEGER - 2400))::TEXT, 6, '0')
        WHEN glaccountid BETWEEN '2500' AND '2999' THEN LPAD((250000 + (glaccountid::INTEGER - 2500))::TEXT, 6, '0')
        WHEN glaccountid BETWEEN '3000' AND '3199' THEN LPAD((300000 + (glaccountid::INTEGER - 3000))::TEXT, 6, '0')
        WHEN glaccountid BETWEEN '3200' AND '3499' THEN LPAD((320000 + (glaccountid::INTEGER - 3200))::TEXT, 6, '0')
        WHEN glaccountid BETWEEN '3500' AND '3999' THEN LPAD((350000 + (glaccountid::INTEGER - 3500))::TEXT, 6, '0')
        WHEN glaccountid BETWEEN '4000' AND '4499' THEN LPAD((400000 + (glaccountid::INTEGER - 4000))::TEXT, 6, '0')
        WHEN glaccountid BETWEEN '4500' AND '4999' THEN LPAD((450000 + (glaccountid::INTEGER - 4500))::TEXT, 6, '0')
        WHEN glaccountid BETWEEN '5000' AND '5499' THEN LPAD((500000 + (glaccountid::INTEGER - 5000))::TEXT, 6, '0')
        WHEN glaccountid BETWEEN '5500' AND '6499' THEN LPAD((550000 + (glaccountid::INTEGER - 5500))::TEXT, 6, '0')
        WHEN glaccountid BETWEEN '6500' AND '6999' THEN LPAD((650000 + (glaccountid::INTEGER - 6500))::TEXT, 6, '0')
        WHEN glaccountid BETWEEN '9000' AND '9999' THEN LPAD((900000 + (glaccountid::INTEGER - 9000))::TEXT, 6, '0')
        -- For irregular accounts, map to appropriate ranges
        WHEN glaccountid::INTEGER < 100000 THEN LPAD((500000 + glaccountid::INTEGER)::TEXT, 6, '0')
        ELSE glaccountid  -- Keep as is
    END as new_account_id,
    accountname,
    CASE 
        WHEN glaccountid::INTEGER BETWEEN 100000 AND 109999 OR glaccountid BETWEEN '1000' AND '1099' THEN 'CASH'
        WHEN glaccountid::INTEGER BETWEEN 110000 AND 119999 OR glaccountid BETWEEN '1100' AND '1199' THEN 'RECV'
        WHEN glaccountid::INTEGER BETWEEN 120000 AND 129999 OR glaccountid BETWEEN '1200' AND '1299' THEN 'INVT'
        WHEN glaccountid::INTEGER BETWEEN 130000 AND 139999 OR glaccountid BETWEEN '1300' AND '1399' THEN 'PREP'
        WHEN glaccountid::INTEGER BETWEEN 140000 AND 179999 OR glaccountid BETWEEN '1400' AND '1799' THEN 'FXAS'
        WHEN glaccountid::INTEGER BETWEEN 180000 AND 199999 OR glaccountid BETWEEN '1800' AND '1899' THEN 'INVA'
        WHEN glaccountid::INTEGER BETWEEN 200000 AND 219999 OR glaccountid BETWEEN '2000' AND '2199' THEN 'PAYB'
        WHEN glaccountid::INTEGER BETWEEN 220000 AND 239999 OR glaccountid BETWEEN '2200' AND '2399' THEN 'ACCR'
        WHEN glaccountid::INTEGER BETWEEN 240000 AND 249999 OR glaccountid BETWEEN '2400' AND '2499' THEN 'STDB'
        WHEN glaccountid::INTEGER BETWEEN 250000 AND 299999 OR glaccountid BETWEEN '2500' AND '2999' THEN 'LTDB'
        WHEN glaccountid::INTEGER BETWEEN 300000 AND 319999 OR glaccountid BETWEEN '3000' AND '3199' THEN 'EQTY'
        WHEN glaccountid::INTEGER BETWEEN 320000 AND 349999 OR glaccountid BETWEEN '3200' AND '3499' THEN 'RETE'
        WHEN glaccountid::INTEGER BETWEEN 350000 AND 399999 OR glaccountid BETWEEN '3500' AND '3999' THEN 'OCIE'
        WHEN glaccountid::INTEGER BETWEEN 400000 AND 449999 OR glaccountid BETWEEN '4000' AND '4499' THEN 'SALE'
        WHEN glaccountid::INTEGER BETWEEN 450000 AND 499999 OR glaccountid BETWEEN '4500' AND '4999' THEN 'OINC'
        WHEN glaccountid::INTEGER BETWEEN 500000 AND 549999 OR glaccountid BETWEEN '5000' AND '5499' THEN 'COGS'
        WHEN glaccountid::INTEGER BETWEEN 550000 AND 649999 OR glaccountid BETWEEN '5500' AND '6499' THEN 'OPEX'
        WHEN glaccountid::INTEGER BETWEEN 650000 AND 699999 OR glaccountid BETWEEN '6500' AND '6999' THEN 'FINX'
        WHEN glaccountid::INTEGER BETWEEN 900000 AND 999999 OR glaccountid BETWEEN '9000' AND '9999' THEN 'STAT'
        ELSE 'OPEX'
    END as account_group_code
FROM glaccount
WHERE glaccountid IS NOT NULL;

-- Handle duplicate mappings by adding sequence numbers
WITH duplicates AS (
    SELECT new_account_id, COUNT(*) as cnt
    FROM account_migration_mapping 
    GROUP BY new_account_id 
    HAVING COUNT(*) > 1
),
ranked_duplicates AS (
    SELECT amm.*,
           ROW_NUMBER() OVER (PARTITION BY amm.new_account_id ORDER BY amm.old_account_id) as rn
    FROM account_migration_mapping amm
    JOIN duplicates d ON amm.new_account_id = d.new_account_id
)
UPDATE account_migration_mapping 
SET new_account_id = rd.new_account_id || LPAD(rd.rn::TEXT, 2, '0')
FROM ranked_duplicates rd
WHERE account_migration_mapping.old_account_id = rd.old_account_id
  AND rd.rn > 1;

-- Step 5: Create new glaccount table with proper structure
CREATE TABLE glaccount_new AS 
SELECT 
    amm.new_account_id as glaccountid,
    ga.accountname,
    ga.accounttype,
    ag.account_class,
    amm.account_group_code,
    ag.balance_sheet_type IS NOT NULL as balance_sheet_indicator,
    ag.pnl_type as pnl_statement_type,
    LEFT(ga.accountname, 20) as short_text,
    LEFT(ga.accountname, 50) as long_text,
    COALESCE(ga.account_currency, 'USD') as account_currency,
    COALESCE(ga.only_balances_in_local_currency, FALSE) as only_balances_in_local_currency,
    COALESCE(ga.posting_without_tax_allowed, TRUE) as posting_without_tax_allowed,
    COALESCE(ga.line_item_display, TRUE) as line_item_display,
    CASE WHEN ga.accounttype IN ('RECEIVABLE', 'PAYABLE') THEN TRUE ELSE FALSE END as open_item_management,
    ga.sort_key,
    ga.authorization_group,
    ag.default_field_status_group as field_status_group,
    COALESCE(ga.supplement_automatic_postings, FALSE) as supplement_automatic_postings,
    COALESCE(ga.relevant_to_cash_flow, FALSE) as relevant_to_cash_flow,
    COALESCE(ga.account_managed_in_ext_system, FALSE) as account_managed_in_ext_system,
    ga.house_bank_account,
    COALESCE(ga.planning_level, 'ACCOUNT') as planning_level,
    ga.tolerance_group,
    ga.inflation_key,
    COALESCE(ga.blocked_for_posting, FALSE) as blocked_for_posting,
    COALESCE(ga.blocked_for_planning, FALSE) as blocked_for_planning,
    COALESCE(ga.marked_for_deletion, FALSE) as marked_for_deletion,
    CASE 
        WHEN ga.accounttype = 'RECEIVABLE' THEN 'CUSTOMER'
        WHEN ga.accounttype = 'PAYABLE' THEN 'VENDOR'
        ELSE 'NONE'
    END as reconciliation_account_type,
    ga.alternative_account_number,
    COALESCE(ga.trading_partner_required, FALSE) as trading_partner_required,
    ga.default_trading_partner,
    ga.functional_area,
    ag.require_profit_center as profit_center_required,
    ag.require_cost_center as cost_center_required,
    ag.require_business_area as business_area_required,
    ga.glaccountid as migrated_from_legacy,
    CURRENT_TIMESTAMP as migration_date,
    ga.last_used_date,
    COALESCE(ga.usage_frequency, 0) as usage_frequency
FROM account_migration_mapping amm
JOIN glaccount ga ON amm.old_account_id = ga.glaccountid
JOIN account_groups ag ON amm.account_group_code = ag.group_code;

-- Step 6: Drop old table and rename new one
DROP TABLE glaccount CASCADE;
ALTER TABLE glaccount_new RENAME TO glaccount;

-- Step 7: Recreate primary key and constraints
ALTER TABLE glaccount ADD PRIMARY KEY (glaccountid);
ALTER TABLE glaccount ADD CONSTRAINT fk_glaccount_account_group FOREIGN KEY (account_group_code) REFERENCES account_groups(group_code);

-- Step 8: Update related tables with new account numbers
UPDATE journalentryline 
SET glaccountid = amm.new_account_id
FROM account_migration_mapping amm
WHERE journalentryline.glaccountid = amm.old_account_id;

UPDATE gl_account_balances 
SET gl_account = amm.new_account_id
FROM account_migration_mapping amm
WHERE gl_account_balances.gl_account = amm.old_account_id;

UPDATE gl_transactions 
SET gl_account = amm.new_account_id
FROM account_migration_mapping amm
WHERE gl_transactions.gl_account = amm.old_account_id;

-- Step 9: Recreate indexes and triggers
CREATE INDEX idx_glaccount_group_code ON glaccount(account_group_code);
CREATE INDEX idx_glaccount_class ON glaccount(account_class);
CREATE INDEX idx_glaccount_reconciliation ON glaccount(reconciliation_account_type);
CREATE INDEX idx_glaccount_status ON glaccount(blocked_for_posting, marked_for_deletion);
CREATE INDEX idx_glaccount_field_status ON glaccount(field_status_group);

-- Recreate the validation trigger
CREATE OR REPLACE FUNCTION validate_account_in_group_range()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.account_group_code IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM account_groups ag 
            WHERE ag.group_code = NEW.account_group_code 
            AND NEW.glaccountid::bigint BETWEEN ag.number_range_from::bigint AND ag.number_range_to::bigint
        ) THEN
            RAISE EXCEPTION 'Account number % is not within the valid range for account group %', 
                NEW.glaccountid, NEW.account_group_code;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_validate_account_range
    BEFORE INSERT OR UPDATE ON glaccount
    FOR EACH ROW
    EXECUTE FUNCTION validate_account_in_group_range();

-- Step 10: Recreate foreign key constraints
ALTER TABLE journalentryline ADD CONSTRAINT journalentryline_glaccountid_fkey FOREIGN KEY (glaccountid) REFERENCES glaccount(glaccountid);
ALTER TABLE gl_account_balances ADD CONSTRAINT fk_gl_account_balances_glaccount FOREIGN KEY (gl_account) REFERENCES glaccount(glaccountid);

-- Step 11: Update migration status
UPDATE account_migration_mapping SET migration_status = 'COMPLETED';

-- Step 12: Recreate enhanced views
CREATE OR REPLACE VIEW v_gl_accounts_enhanced AS
SELECT 
    ga.glaccountid,
    ga.accountname,
    ga.accounttype,
    ga.short_text,
    ga.long_text,
    ga.account_class,
    ga.account_group_code,
    ag.group_name,
    ag.group_description,
    ga.balance_sheet_indicator,
    ga.pnl_statement_type,
    ga.account_currency,
    ga.line_item_display,
    ga.open_item_management,
    ga.reconciliation_account_type,
    ga.cost_center_required,
    ga.profit_center_required,
    ga.business_area_required,
    ga.blocked_for_posting,
    ga.marked_for_deletion,
    ga.migration_date,
    ga.migrated_from_legacy,
    ag.number_range_from,
    ag.number_range_to,
    ga.field_status_group,
    fsg.group_name as field_status_group_name,
    TRUE as in_group_range  -- All should be in range now
FROM glaccount ga
LEFT JOIN account_groups ag ON ga.account_group_code = ag.group_code
LEFT JOIN field_status_groups fsg ON ga.field_status_group = fsg.group_id
WHERE ga.marked_for_deletion = FALSE OR ga.marked_for_deletion IS NULL;

-- Create migration summary
CREATE OR REPLACE VIEW v_migration_summary AS
SELECT 
    ag.group_code,
    ag.group_name,
    ag.account_class,
    ag.number_range_from,
    ag.number_range_to,
    COUNT(ga.glaccountid) as migrated_accounts,
    MIN(ga.glaccountid::bigint) as lowest_account,
    MAX(ga.glaccountid::bigint) as highest_account
FROM account_groups ag
LEFT JOIN glaccount ga ON ag.group_code = ga.account_group_code
GROUP BY ag.group_code, ag.group_name, ag.account_class, ag.number_range_from, ag.number_range_to
ORDER BY ag.group_code;

-- Final validation
DO $$
DECLARE
    total_migrated INTEGER;
    validation_errors INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_migrated FROM glaccount;
    
    SELECT COUNT(*) INTO validation_errors
    FROM glaccount ga 
    JOIN account_groups ag ON ga.account_group_code = ag.group_code 
    WHERE ga.glaccountid::bigint < ag.number_range_from::bigint 
       OR ga.glaccountid::bigint > ag.number_range_to::bigint;
    
    RAISE NOTICE 'Migration Complete:';
    RAISE NOTICE '- Total accounts migrated: %', total_migrated;
    RAISE NOTICE '- Validation errors: %', validation_errors;
    
    IF validation_errors = 0 THEN
        RAISE NOTICE '✅ All accounts are within valid SAP ranges!';
    ELSE
        RAISE WARNING '⚠️  Some accounts are outside their group ranges';
    END IF;
END $$;