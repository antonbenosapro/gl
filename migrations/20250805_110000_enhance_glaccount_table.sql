-- Migration: Enhance GL Account Table for SAP-Aligned Structure
-- Date: August 5, 2025
-- Purpose: Add SAP-style fields to glaccount table for enhanced functionality

-- First, let's backup the current structure
CREATE TABLE IF NOT EXISTS glaccount_backup_20250805 AS SELECT * FROM glaccount;

-- Add new SAP-aligned columns to glaccount table
ALTER TABLE glaccount 
    -- Account Group Assignment
    ADD COLUMN IF NOT EXISTS account_group_code VARCHAR(10),
    
    -- SAP-Style Account Classification
    ADD COLUMN IF NOT EXISTS account_class VARCHAR(20) CHECK (account_class IN ('ASSETS', 'LIABILITIES', 'EQUITY', 'REVENUE', 'EXPENSES', 'STATISTICAL')),
    ADD COLUMN IF NOT EXISTS balance_sheet_indicator BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS pnl_statement_type VARCHAR(20) CHECK (pnl_statement_type IN ('REVENUE', 'EXPENSES', 'NOT_APPLICABLE')),
    
    -- Account Control Fields
    ADD COLUMN IF NOT EXISTS short_text VARCHAR(20),
    ADD COLUMN IF NOT EXISTS long_text VARCHAR(50),
    ADD COLUMN IF NOT EXISTS account_currency VARCHAR(3) DEFAULT 'USD',
    ADD COLUMN IF NOT EXISTS only_balances_in_local_currency BOOLEAN DEFAULT FALSE,
    
    -- Posting Control
    ADD COLUMN IF NOT EXISTS posting_without_tax_allowed BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS line_item_display BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS open_item_management BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS sort_key VARCHAR(10),
    ADD COLUMN IF NOT EXISTS authorization_group VARCHAR(10),
    
    -- Field Status and Validation
    ADD COLUMN IF NOT EXISTS field_status_group VARCHAR(10),
    ADD COLUMN IF NOT EXISTS supplement_automatic_postings BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS relevant_to_cash_flow BOOLEAN DEFAULT FALSE,
    
    -- Account Assignment Objects
    ADD COLUMN IF NOT EXISTS account_managed_in_ext_system BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS house_bank_account VARCHAR(10),
    ADD COLUMN IF NOT EXISTS planning_level VARCHAR(20) DEFAULT 'ACCOUNT' CHECK (planning_level IN ('ACCOUNT', 'COST_CENTER', 'PROFIT_CENTER')),
    
    -- Tolerance and Control
    ADD COLUMN IF NOT EXISTS tolerance_group VARCHAR(10),
    ADD COLUMN IF NOT EXISTS inflation_key VARCHAR(10),
    
    -- Account Blocking and Status
    ADD COLUMN IF NOT EXISTS blocked_for_posting BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS blocked_for_planning BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS marked_for_deletion BOOLEAN DEFAULT FALSE,
    
    -- Integration and Reconciliation
    ADD COLUMN IF NOT EXISTS reconciliation_account_type VARCHAR(20) CHECK (reconciliation_account_type IN ('VENDOR', 'CUSTOMER', 'ASSET', 'MATERIAL', 'NONE')),
    ADD COLUMN IF NOT EXISTS alternative_account_number VARCHAR(20),
    
    -- Trading Partner and Intercompany
    ADD COLUMN IF NOT EXISTS trading_partner_required BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS default_trading_partner VARCHAR(10),
    
    -- Reporting and Analytics
    ADD COLUMN IF NOT EXISTS functional_area VARCHAR(10),
    ADD COLUMN IF NOT EXISTS profit_center_required BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS cost_center_required BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS business_area_required BOOLEAN DEFAULT FALSE,
    
    -- Migration and Audit
    ADD COLUMN IF NOT EXISTS migrated_from_legacy VARCHAR(20),
    ADD COLUMN IF NOT EXISTS migration_date TIMESTAMP,
    ADD COLUMN IF NOT EXISTS last_used_date DATE,
    ADD COLUMN IF NOT EXISTS usage_frequency INTEGER DEFAULT 0;

-- Add foreign key constraint to account_groups
ALTER TABLE glaccount 
    ADD CONSTRAINT fk_glaccount_account_group 
    FOREIGN KEY (account_group_code) REFERENCES account_groups(group_code);

-- Create indexes for improved performance
CREATE INDEX IF NOT EXISTS idx_glaccount_group_code ON glaccount(account_group_code);
CREATE INDEX IF NOT EXISTS idx_glaccount_class ON glaccount(account_class);
CREATE INDEX IF NOT EXISTS idx_glaccount_reconciliation ON glaccount(reconciliation_account_type);
CREATE INDEX IF NOT EXISTS idx_glaccount_status ON glaccount(blocked_for_posting, marked_for_deletion);
CREATE INDEX IF NOT EXISTS idx_glaccount_field_status ON glaccount(field_status_group);

-- Update existing accounts with basic SAP-aligned data based on current structure
UPDATE glaccount SET 
    short_text = LEFT(accountname, 20),
    long_text = LEFT(accountname, 50),
    account_class = CASE 
        WHEN LEFT(glaccountid, 1) = '1' THEN 'ASSETS'
        WHEN LEFT(glaccountid, 1) = '2' THEN 'LIABILITIES' 
        WHEN LEFT(glaccountid, 1) = '3' THEN 'EQUITY'
        WHEN LEFT(glaccountid, 1) = '4' THEN 'REVENUE'
        WHEN LEFT(glaccountid, 1) = '5' THEN 'EXPENSES'
        WHEN LEFT(glaccountid, 1) = '9' THEN 'STATISTICAL'
        ELSE 'ASSETS'
    END,
    balance_sheet_indicator = CASE 
        WHEN LEFT(glaccountid, 1) IN ('1', '2', '3') THEN TRUE
        ELSE FALSE
    END,
    pnl_statement_type = CASE 
        WHEN LEFT(glaccountid, 1) = '4' THEN 'REVENUE'
        WHEN LEFT(glaccountid, 1) = '5' THEN 'EXPENSES'
        ELSE 'NOT_APPLICABLE'
    END,
    account_group_code = CASE 
        WHEN LEFT(glaccountid, 2) = '10' THEN 'CASH'
        WHEN LEFT(glaccountid, 2) = '11' THEN 'RECV'
        WHEN LEFT(glaccountid, 2) = '12' THEN 'INVT'
        WHEN LEFT(glaccountid, 2) = '13' THEN 'PREP'
        WHEN LEFT(glaccountid, 2) IN ('14', '15', '16', '17') THEN 'FXAS'
        WHEN LEFT(glaccountid, 2) IN ('18', '19') THEN 'INVA'
        WHEN LEFT(glaccountid, 2) IN ('20', '21') THEN 'PAYB'
        WHEN LEFT(glaccountid, 2) IN ('22', '23') THEN 'ACCR'
        WHEN LEFT(glaccountid, 2) = '24' THEN 'STDB'
        WHEN LEFT(glaccountid, 2) IN ('25', '26', '27', '28', '29') THEN 'LTDB'
        WHEN LEFT(glaccountid, 2) IN ('30', '31') THEN 'EQTY'
        WHEN LEFT(glaccountid, 2) IN ('32', '33', '34') THEN 'RETE'
        WHEN LEFT(glaccountid, 2) IN ('35', '36', '37', '38', '39') THEN 'OCIE'
        WHEN LEFT(glaccountid, 2) IN ('40', '41', '42', '43', '44') THEN 'SALE'
        WHEN LEFT(glaccountid, 2) IN ('45', '46', '47', '48', '49') THEN 'OINC'
        WHEN LEFT(glaccountid, 2) IN ('50', '51', '52', '53', '54') THEN 'COGS'
        WHEN LEFT(glaccountid, 2) IN ('55', '56', '57', '58', '59', '60', '61', '62', '63', '64') THEN 'OPEX'
        WHEN LEFT(glaccountid, 2) IN ('65', '66', '67', '68', '69') THEN 'FINX'
        WHEN LEFT(glaccountid, 1) = '9' THEN 'STAT'
        ELSE 'OPEX'  -- Default for unclassified accounts
    END,
    line_item_display = TRUE,
    open_item_management = CASE 
        WHEN accounttype IN ('RECEIVABLE', 'PAYABLE') THEN TRUE
        ELSE FALSE
    END,
    reconciliation_account_type = CASE 
        WHEN accounttype = 'RECEIVABLE' THEN 'CUSTOMER'
        WHEN accounttype = 'PAYABLE' THEN 'VENDOR'
        ELSE 'NONE'
    END,
    migrated_from_legacy = 'ORIGINAL_SYSTEM',
    migration_date = CURRENT_TIMESTAMP
WHERE account_group_code IS NULL;  -- Only update unmigrated accounts

-- Set field requirements based on account groups
UPDATE glaccount SET 
    cost_center_required = ag.require_cost_center,
    profit_center_required = ag.require_profit_center,
    business_area_required = ag.require_business_area,
    field_status_group = ag.default_field_status_group
FROM account_groups ag 
WHERE glaccount.account_group_code = ag.group_code 
    AND glaccount.cost_center_required IS NULL;

-- Create view for enhanced account information
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
    CASE 
        WHEN ga.glaccountid::bigint BETWEEN ag.number_range_from::bigint AND ag.number_range_to::bigint 
        THEN TRUE 
        ELSE FALSE 
    END as in_group_range
FROM glaccount ga
LEFT JOIN account_groups ag ON ga.account_group_code = ag.group_code
WHERE ga.marked_for_deletion = FALSE OR ga.marked_for_deletion IS NULL;

-- Create function to validate account number ranges
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

-- Create trigger for account range validation
CREATE TRIGGER tr_validate_account_range
    BEFORE INSERT OR UPDATE ON glaccount
    FOR EACH ROW
    EXECUTE FUNCTION validate_account_in_group_range();

-- Add table comments
COMMENT ON COLUMN glaccount.account_group_code IS 'Reference to account_groups table for SAP-style classification';
COMMENT ON COLUMN glaccount.account_class IS 'High-level account classification (ASSETS, LIABILITIES, etc.)';
COMMENT ON COLUMN glaccount.short_text IS 'Short description for account (20 characters)';
COMMENT ON COLUMN glaccount.long_text IS 'Long description for account (50 characters)';
COMMENT ON COLUMN glaccount.field_status_group IS 'Controls field behavior during posting';
COMMENT ON COLUMN glaccount.reconciliation_account_type IS 'Type of reconciliation account (CUSTOMER, VENDOR, etc.)';
COMMENT ON COLUMN glaccount.cost_center_required IS 'Indicates if cost center is mandatory for postings';
COMMENT ON VIEW v_gl_accounts_enhanced IS 'Enhanced view of GL accounts with account group information and validation';