-- Migration: Convert Existing Accounts to 6-Digit SAP Structure
-- Date: August 5, 2025
-- Purpose: Migrate existing 4-digit accounts to 6-digit SAP-aligned structure

-- Temporarily disable constraints and triggers
ALTER TABLE glaccount DISABLE TRIGGER tr_validate_account_range;
ALTER TABLE journalentryline DROP CONSTRAINT IF EXISTS fk_journalentryline_glaccount;
ALTER TABLE gl_account_balances DROP CONSTRAINT IF EXISTS fk_gl_account_balances_glaccount;

-- Create account mapping table for migration tracking
CREATE TABLE IF NOT EXISTS account_migration_mapping (
    old_account_id VARCHAR(10),
    new_account_id VARCHAR(10),
    account_name VARCHAR(100),
    account_group_code VARCHAR(10),
    migration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    migration_status VARCHAR(20) DEFAULT 'PENDING',
    PRIMARY KEY (old_account_id)
);

-- Define the account mapping from 4-digit to 6-digit SAP structure
INSERT INTO account_migration_mapping (old_account_id, new_account_id, account_name, account_group_code) 
SELECT 
    glaccountid as old_account_id,
    CASE 
        -- Cash accounts: 1000-1099 -> 100000-109999
        WHEN glaccountid BETWEEN '1000' AND '1099' THEN 
            LPAD((100000 + (glaccountid::INTEGER - 1000))::TEXT, 6, '0')
        -- Receivables: 1100-1199 -> 110000-119999  
        WHEN glaccountid BETWEEN '1100' AND '1199' THEN 
            LPAD((110000 + (glaccountid::INTEGER - 1100))::TEXT, 6, '0')
        -- Inventory: 1200-1299 -> 120000-129999
        WHEN glaccountid BETWEEN '1200' AND '1299' THEN 
            LPAD((120000 + (glaccountid::INTEGER - 1200))::TEXT, 6, '0')
        -- Prepaids: 1300-1399 -> 130000-139999
        WHEN glaccountid BETWEEN '1300' AND '1399' THEN 
            LPAD((130000 + (glaccountid::INTEGER - 1300))::TEXT, 6, '0')
        -- Fixed Assets: 1400-1799 -> 140000-179999
        WHEN glaccountid BETWEEN '1400' AND '1799' THEN 
            LPAD((140000 + (glaccountid::INTEGER - 1400))::TEXT, 6, '0')
        -- Investments: 1800-1899 -> 180000-199999
        WHEN glaccountid BETWEEN '1800' AND '1899' THEN 
            LPAD((180000 + (glaccountid::INTEGER - 1800))::TEXT, 6, '0')
        -- Payables: 2000-2199 -> 200000-219999
        WHEN glaccountid BETWEEN '2000' AND '2199' THEN 
            LPAD((200000 + (glaccountid::INTEGER - 2000))::TEXT, 6, '0')
        -- Accruals: 2200-2399 -> 220000-239999
        WHEN glaccountid BETWEEN '2200' AND '2399' THEN 
            LPAD((220000 + (glaccountid::INTEGER - 2200))::TEXT, 6, '0')
        -- Short-term Debt: 2400-2499 -> 240000-249999
        WHEN glaccountid BETWEEN '2400' AND '2499' THEN 
            LPAD((240000 + (glaccountid::INTEGER - 2400))::TEXT, 6, '0')
        -- Long-term Debt: 2500-2999 -> 250000-299999
        WHEN glaccountid BETWEEN '2500' AND '2999' THEN 
            LPAD((250000 + (glaccountid::INTEGER - 2500))::TEXT, 6, '0')
        -- Equity: 3000-3199 -> 300000-319999
        WHEN glaccountid BETWEEN '3000' AND '3199' THEN 
            LPAD((300000 + (glaccountid::INTEGER - 3000))::TEXT, 6, '0')
        -- Retained Earnings: 3200-3499 -> 320000-349999
        WHEN glaccountid BETWEEN '3200' AND '3499' THEN 
            LPAD((320000 + (glaccountid::INTEGER - 3200))::TEXT, 6, '0')
        -- Other Equity: 3500-3999 -> 350000-399999  
        WHEN glaccountid BETWEEN '3500' AND '3999' THEN 
            LPAD((350000 + (glaccountid::INTEGER - 3500))::TEXT, 6, '0')
        -- Sales Revenue: 4000-4499 -> 400000-449999
        WHEN glaccountid BETWEEN '4000' AND '4499' THEN 
            LPAD((400000 + (glaccountid::INTEGER - 4000))::TEXT, 6, '0')
        -- Other Income: 4500-4999 -> 450000-499999
        WHEN glaccountid BETWEEN '4500' AND '4999' THEN 
            LPAD((450000 + (glaccountid::INTEGER - 4500))::TEXT, 6, '0')
        -- COGS: 5000-5499 -> 500000-549999
        WHEN glaccountid BETWEEN '5000' AND '5499' THEN 
            LPAD((500000 + (glaccountid::INTEGER - 5000))::TEXT, 6, '0')
        -- Operating Expenses: 5500-6499 -> 550000-649999
        WHEN glaccountid BETWEEN '5500' AND '6499' THEN 
            LPAD((550000 + (glaccountid::INTEGER - 5500))::TEXT, 6, '0')
        -- Financial Expenses: 6500-6999 -> 650000-699999
        WHEN glaccountid BETWEEN '6500' AND '6999' THEN 
            LPAD((650000 + (glaccountid::INTEGER - 6500))::TEXT, 6, '0')
        -- Statistical: 9000-9999 -> 900000-999999
        WHEN glaccountid BETWEEN '9000' AND '9999' THEN 
            LPAD((900000 + (glaccountid::INTEGER - 9000))::TEXT, 6, '0')
        -- Default mapping for any unmapped accounts
        ELSE LPAD(glaccountid, 6, '0')
    END as new_account_id,
    accountname,
    CASE 
        WHEN glaccountid BETWEEN '1000' AND '1099' THEN 'CASH'
        WHEN glaccountid BETWEEN '1100' AND '1199' THEN 'RECV'
        WHEN glaccountid BETWEEN '1200' AND '1299' THEN 'INVT'
        WHEN glaccountid BETWEEN '1300' AND '1399' THEN 'PREP'
        WHEN glaccountid BETWEEN '1400' AND '1799' THEN 'FXAS'
        WHEN glaccountid BETWEEN '1800' AND '1899' THEN 'INVA'
        WHEN glaccountid BETWEEN '2000' AND '2199' THEN 'PAYB'
        WHEN glaccountid BETWEEN '2200' AND '2399' THEN 'ACCR'
        WHEN glaccountid BETWEEN '2400' AND '2499' THEN 'STDB'
        WHEN glaccountid BETWEEN '2500' AND '2999' THEN 'LTDB'
        WHEN glaccountid BETWEEN '3000' AND '3199' THEN 'EQTY'
        WHEN glaccountid BETWEEN '3200' AND '3499' THEN 'RETE'
        WHEN glaccountid BETWEEN '3500' AND '3999' THEN 'OCIE'
        WHEN glaccountid BETWEEN '4000' AND '4499' THEN 'SALE'
        WHEN glaccountid BETWEEN '4500' AND '4999' THEN 'OINC'
        WHEN glaccountid BETWEEN '5000' AND '5499' THEN 'COGS'
        WHEN glaccountid BETWEEN '5500' AND '6499' THEN 'OPEX'
        WHEN glaccountid BETWEEN '6500' AND '6999' THEN 'FINX'
        WHEN glaccountid BETWEEN '9000' AND '9999' THEN 'STAT'
        ELSE 'OPEX'
    END as account_group_code
FROM glaccount
ORDER BY glaccountid;

-- Show mapping preview
SELECT old_account_id, new_account_id, account_name, account_group_code 
FROM account_migration_mapping 
ORDER BY old_account_id;

-- Step 1: Update journal entry lines with new account numbers
UPDATE journalentryline 
SET glaccountid = amm.new_account_id
FROM account_migration_mapping amm
WHERE journalentryline.glaccountid = amm.old_account_id;

-- Step 2: Update GL account balances with new account numbers
UPDATE gl_account_balances 
SET gl_account = amm.new_account_id
FROM account_migration_mapping amm
WHERE gl_account_balances.gl_account = amm.old_account_id;

-- Step 3: Update GL transactions with new account numbers
UPDATE gl_transactions 
SET gl_account = amm.new_account_id
FROM account_migration_mapping amm
WHERE gl_transactions.gl_account = amm.old_account_id;

-- Step 4: Update glaccount table with new account numbers and SAP structure
UPDATE glaccount 
SET 
    glaccountid = amm.new_account_id,
    account_group_code = amm.account_group_code,
    account_class = ag.account_class,
    balance_sheet_indicator = CASE 
        WHEN ag.balance_sheet_type IS NOT NULL THEN TRUE
        ELSE FALSE
    END,
    pnl_statement_type = ag.pnl_type,
    short_text = LEFT(accountname, 20),
    long_text = LEFT(accountname, 50),
    cost_center_required = ag.require_cost_center,
    profit_center_required = ag.require_profit_center,
    business_area_required = ag.require_business_area,
    field_status_group = ag.default_field_status_group,
    migrated_from_legacy = glaccount.glaccountid,
    migration_date = CURRENT_TIMESTAMP
FROM account_migration_mapping amm
JOIN account_groups ag ON amm.account_group_code = ag.group_code
WHERE glaccount.glaccountid = amm.old_account_id;

-- Update migration status
UPDATE account_migration_mapping SET migration_status = 'COMPLETED';

-- Re-enable constraints and triggers
ALTER TABLE glaccount ENABLE TRIGGER tr_validate_account_range;

-- Recreate foreign key constraints with new structure
ALTER TABLE journalentryline 
    ADD CONSTRAINT fk_journalentryline_glaccount 
    FOREIGN KEY (glaccountid) REFERENCES glaccount(glaccountid);

ALTER TABLE gl_account_balances 
    ADD CONSTRAINT fk_gl_account_balances_glaccount 
    FOREIGN KEY (gl_account) REFERENCES glaccount(glaccountid);

-- Verify migration results
DO $$
DECLARE
    total_migrated INTEGER;
    total_original INTEGER;
    validation_errors INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_original FROM account_migration_mapping;
    SELECT COUNT(*) INTO total_migrated FROM glaccount WHERE migration_date IS NOT NULL;
    
    -- Check for accounts outside their group ranges
    SELECT COUNT(*) INTO validation_errors
    FROM glaccount ga 
    JOIN account_groups ag ON ga.account_group_code = ag.group_code 
    WHERE ga.glaccountid::bigint < ag.number_range_from::bigint 
       OR ga.glaccountid::bigint > ag.number_range_to::bigint;
    
    RAISE NOTICE 'Migration Summary:';
    RAISE NOTICE '- Original accounts: %', total_original;
    RAISE NOTICE '- Migrated accounts: %', total_migrated;
    RAISE NOTICE '- Validation errors: %', validation_errors;
    
    IF validation_errors = 0 AND total_migrated = total_original THEN
        RAISE NOTICE 'Migration completed successfully!';
    ELSE
        RAISE WARNING 'Migration completed with issues. Please review.';
    END IF;
END $$;

-- Create final validation view
CREATE OR REPLACE VIEW v_migration_validation AS
SELECT 
    amm.old_account_id,
    amm.new_account_id,
    amm.account_name,
    amm.account_group_code,
    ga.glaccountid as current_glaccount_id,
    ag.group_name,
    ag.number_range_from,
    ag.number_range_to,
    CASE 
        WHEN ga.glaccountid::bigint BETWEEN ag.number_range_from::bigint AND ag.number_range_to::bigint 
        THEN 'VALID' 
        ELSE 'INVALID' 
    END as range_validation,
    amm.migration_status
FROM account_migration_mapping amm
JOIN glaccount ga ON amm.new_account_id = ga.glaccountid
JOIN account_groups ag ON amm.account_group_code = ag.group_code
ORDER BY amm.old_account_id;

COMMENT ON VIEW v_migration_validation IS 'Validation view for 6-digit account migration results';