-- Migration: Fix Account Group Ranges for Existing Account Structure
-- Date: August 5, 2025
-- Purpose: Adjust account group ranges to accommodate existing 4-digit account numbers

-- Temporarily disable the validation trigger
ALTER TABLE glaccount DISABLE TRIGGER tr_validate_account_range;

-- Update account group ranges to match existing account structure
UPDATE account_groups SET
    number_range_from = CASE group_code
        WHEN 'CASH' THEN '1000'
        WHEN 'RECV' THEN '1100'  
        WHEN 'INVT' THEN '1200'
        WHEN 'PREP' THEN '1300'
        WHEN 'FXAS' THEN '1400'
        WHEN 'INVA' THEN '1800'
        WHEN 'PAYB' THEN '2000'
        WHEN 'ACCR' THEN '2200'
        WHEN 'STDB' THEN '2400'
        WHEN 'LTDB' THEN '2500'
        WHEN 'EQTY' THEN '3000'
        WHEN 'RETE' THEN '3200'
        WHEN 'OCIE' THEN '3500'
        WHEN 'SALE' THEN '4000'
        WHEN 'OINC' THEN '4500'
        WHEN 'COGS' THEN '5000'
        WHEN 'OPEX' THEN '5500'
        WHEN 'FINX' THEN '6500'
        WHEN 'STAT' THEN '9000'
        ELSE number_range_from
    END,
    number_range_to = CASE group_code
        WHEN 'CASH' THEN '1099'
        WHEN 'RECV' THEN '1199'
        WHEN 'INVT' THEN '1299'
        WHEN 'PREP' THEN '1399'
        WHEN 'FXAS' THEN '1799'
        WHEN 'INVA' THEN '1899'
        WHEN 'PAYB' THEN '2199'
        WHEN 'ACCR' THEN '2399'
        WHEN 'STDB' THEN '2499'
        WHEN 'LTDB' THEN '2999'
        WHEN 'EQTY' THEN '3199'
        WHEN 'RETE' THEN '3499'
        WHEN 'OCIE' THEN '3999'
        WHEN 'SALE' THEN '4499'
        WHEN 'OINC' THEN '4999'
        WHEN 'COGS' THEN '5499'
        WHEN 'OPEX' THEN '6499'
        WHEN 'FINX' THEN '6999'
        WHEN 'STAT' THEN '9999'
        ELSE number_range_to
    END
WHERE group_code IN ('CASH', 'RECV', 'INVT', 'PREP', 'FXAS', 'INVA', 'PAYB', 'ACCR', 'STDB', 'LTDB',
                     'EQTY', 'RETE', 'OCIE', 'SALE', 'OINC', 'COGS', 'OPEX', 'FINX', 'STAT');

-- Fix account group assignments based on existing account structure
UPDATE glaccount SET account_group_code = 
    CASE 
        -- Cash accounts (1000-1099)
        WHEN glaccountid BETWEEN '1000' AND '1099' THEN 'CASH'
        -- Receivables (1100-1199)  
        WHEN glaccountid BETWEEN '1100' AND '1199' THEN 'RECV'
        -- Inventory (1200-1299)
        WHEN glaccountid BETWEEN '1200' AND '1299' THEN 'INVT'
        -- Prepaid (1300-1399)
        WHEN glaccountid BETWEEN '1300' AND '1399' THEN 'PREP'
        -- Fixed Assets (1400-1799)
        WHEN glaccountid BETWEEN '1400' AND '1799' THEN 'FXAS'
        -- Investments (1800-1899)
        WHEN glaccountid BETWEEN '1800' AND '1899' THEN 'INVA'
        -- Payables (2000-2199)
        WHEN glaccountid BETWEEN '2000' AND '2199' THEN 'PAYB'
        -- Accrued Liabilities (2200-2399)
        WHEN glaccountid BETWEEN '2200' AND '2399' THEN 'ACCR'
        -- Short-term Debt (2400-2499)
        WHEN glaccountid BETWEEN '2400' AND '2499' THEN 'STDB'
        -- Long-term Debt (2500-2999)
        WHEN glaccountid BETWEEN '2500' AND '2999' THEN 'LTDB'
        -- Equity (3000-3199)
        WHEN glaccountid BETWEEN '3000' AND '3199' THEN 'EQTY'
        -- Retained Earnings (3200-3499)
        WHEN glaccountid BETWEEN '3200' AND '3499' THEN 'RETE'
        -- Other Comprehensive Income (3500-3999)
        WHEN glaccountid BETWEEN '3500' AND '3999' THEN 'OCIE'
        -- Sales Revenue (4000-4499)
        WHEN glaccountid BETWEEN '4000' AND '4499' THEN 'SALE'
        -- Other Income (4500-4999) 
        WHEN glaccountid BETWEEN '4500' AND '4999' THEN 'OINC'
        -- Cost of Goods Sold (5000-5499)
        WHEN glaccountid BETWEEN '5000' AND '5499' THEN 'COGS'
        -- Operating Expenses (5500-6499)
        WHEN glaccountid BETWEEN '5500' AND '6499' THEN 'OPEX'
        -- Financial Expenses (6500-6999)
        WHEN glaccountid BETWEEN '6500' AND '6999' THEN 'FINX'
        -- Statistical (9000-9999)
        WHEN glaccountid BETWEEN '9000' AND '9999' THEN 'STAT'
        ELSE account_group_code
    END;

-- Update the account class and other fields based on corrected account groups
UPDATE glaccount SET 
    account_class = ag.account_class,
    balance_sheet_indicator = CASE 
        WHEN ag.balance_sheet_type IS NOT NULL THEN TRUE
        ELSE FALSE
    END,
    pnl_statement_type = ag.pnl_type,
    cost_center_required = ag.require_cost_center,
    profit_center_required = ag.require_profit_center,
    business_area_required = ag.require_business_area,
    field_status_group = ag.default_field_status_group
FROM account_groups ag 
WHERE glaccount.account_group_code = ag.group_code;

-- Re-enable the validation trigger
ALTER TABLE glaccount ENABLE TRIGGER tr_validate_account_range;

-- Verify all accounts are now within their group ranges
DO $$
DECLARE
    invalid_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO invalid_count
    FROM glaccount ga 
    JOIN account_groups ag ON ga.account_group_code = ag.group_code 
    WHERE ga.glaccountid::bigint < ag.number_range_from::bigint 
       OR ga.glaccountid::bigint > ag.number_range_to::bigint;
    
    IF invalid_count > 0 THEN
        RAISE WARNING 'Still have % accounts outside their group ranges', invalid_count;
    ELSE
        RAISE NOTICE 'All accounts are now within their assigned group ranges';
    END IF;
END $$;

-- Update the view to refresh with new data
DROP VIEW IF EXISTS v_gl_accounts_enhanced;
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
    ag.number_range_from,
    ag.number_range_to,
    ga.field_status_group,
    fsg.group_name as field_status_group_name,
    CASE 
        WHEN ga.glaccountid::bigint BETWEEN ag.number_range_from::bigint AND ag.number_range_to::bigint 
        THEN TRUE 
        ELSE FALSE 
    END as in_group_range
FROM glaccount ga
LEFT JOIN account_groups ag ON ga.account_group_code = ag.group_code
LEFT JOIN field_status_groups fsg ON ga.field_status_group = fsg.group_id
WHERE ga.marked_for_deletion = FALSE OR ga.marked_for_deletion IS NULL;

-- Create summary report of the migration
CREATE OR REPLACE VIEW v_coa_migration_summary AS
SELECT 
    ag.group_code,
    ag.group_name,
    ag.account_class,
    ag.number_range_from,
    ag.number_range_to,
    COUNT(ga.glaccountid) as account_count,
    ag.default_field_status_group,
    ag.require_cost_center,
    ag.require_profit_center,
    ag.is_active
FROM account_groups ag
LEFT JOIN glaccount ga ON ag.group_code = ga.account_group_code 
    AND (ga.marked_for_deletion = FALSE OR ga.marked_for_deletion IS NULL)
GROUP BY ag.group_code, ag.group_name, ag.account_class, ag.number_range_from, 
         ag.number_range_to, ag.default_field_status_group, ag.require_cost_center,
         ag.require_profit_center, ag.is_active
ORDER BY ag.group_code;

COMMENT ON VIEW v_coa_migration_summary IS 'Summary of SAP-aligned COA migration results by account group';