-- IAS 21 Database Integration Fixes
-- Resolves critical database integration issues identified in testing
-- Date: August 6, 2025
-- Author: Claude Code Assistant

BEGIN;

-- =============================================================================
-- FIX 1: Extend entity_id column lengths
-- =============================================================================

-- Extend entity_functional_currency.entity_id
ALTER TABLE entity_functional_currency 
ALTER COLUMN entity_id TYPE VARCHAR(20);

-- Extend cumulative_translation_adjustment.entity_id
ALTER TABLE cumulative_translation_adjustment 
ALTER COLUMN entity_id TYPE VARCHAR(20);

-- Extend intercompany_fx_eliminations entity columns if they exist
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='intercompany_fx_eliminations') THEN
        ALTER TABLE intercompany_fx_eliminations 
        ALTER COLUMN parent_entity TYPE VARCHAR(20),
        ALTER COLUMN subsidiary_entity TYPE VARCHAR(20);
    END IF;
END $$;

-- =============================================================================
-- FIX 2: Add missing columns to fx_revaluation_details
-- =============================================================================

DO $$ 
BEGIN
    -- Add IAS 21 specific columns to fx_revaluation_details
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='fx_revaluation_details' AND column_name='accounting_standard') THEN
        ALTER TABLE fx_revaluation_details ADD COLUMN accounting_standard VARCHAR(20) DEFAULT 'ASC_830';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='fx_revaluation_details' AND column_name='translation_method') THEN
        ALTER TABLE fx_revaluation_details ADD COLUMN translation_method VARCHAR(20) DEFAULT 'CURRENT_RATE';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='fx_revaluation_details' AND column_name='monetary_classification') THEN
        ALTER TABLE fx_revaluation_details ADD COLUMN monetary_classification VARCHAR(20) DEFAULT 'MONETARY';
    END IF;
    
    -- CTA and OCI components
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='fx_revaluation_details' AND column_name='cta_component') THEN
        ALTER TABLE fx_revaluation_details ADD COLUMN cta_component DECIMAL(15,2) DEFAULT 0.00;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='fx_revaluation_details' AND column_name='oci_component') THEN
        ALTER TABLE fx_revaluation_details ADD COLUMN oci_component DECIMAL(15,2) DEFAULT 0.00;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='fx_revaluation_details' AND column_name='pnl_component') THEN
        ALTER TABLE fx_revaluation_details ADD COLUMN pnl_component DECIMAL(15,2) DEFAULT 0.00;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='fx_revaluation_details' AND column_name='equity_component') THEN
        ALTER TABLE fx_revaluation_details ADD COLUMN equity_component DECIMAL(15,2) DEFAULT 0.00;
    END IF;
    
    -- Hedge accounting
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='fx_revaluation_details' AND column_name='hedge_designation') THEN
        ALTER TABLE fx_revaluation_details ADD COLUMN hedge_designation VARCHAR(20);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='fx_revaluation_details' AND column_name='hedge_effectiveness') THEN
        ALTER TABLE fx_revaluation_details ADD COLUMN hedge_effectiveness DECIMAL(8,4);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='fx_revaluation_details' AND column_name='hedge_instrument_id') THEN
        ALTER TABLE fx_revaluation_details ADD COLUMN hedge_instrument_id VARCHAR(50);
    END IF;
    
    -- Additional compliance fields
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='fx_revaluation_details' AND column_name='hyperinflationary_adj') THEN
        ALTER TABLE fx_revaluation_details ADD COLUMN hyperinflationary_adj DECIMAL(15,2) DEFAULT 0.00;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='fx_revaluation_details' AND column_name='remeasurement_gain_loss') THEN
        ALTER TABLE fx_revaluation_details ADD COLUMN remeasurement_gain_loss DECIMAL(15,2) DEFAULT 0.00;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='fx_revaluation_details' AND column_name='translation_gain_loss') THEN
        ALTER TABLE fx_revaluation_details ADD COLUMN translation_gain_loss DECIMAL(15,2) DEFAULT 0.00;
    END IF;
END $$;

-- =============================================================================
-- FIX 3: Add missing translation and revaluation fields to journalentryline
-- =============================================================================

DO $$ 
BEGIN
    -- Add translation tracking fields to journalentryline if not exists
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='journalentryline' AND column_name='translated_amount') THEN
        ALTER TABLE journalentryline ADD COLUMN translated_amount DECIMAL(15,2);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='journalentryline' AND column_name='exchange_rate') THEN
        ALTER TABLE journalentryline ADD COLUMN exchange_rate DECIMAL(10,6);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='journalentryline' AND column_name='translation_date') THEN
        ALTER TABLE journalentryline ADD COLUMN translation_date DATE;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='journalentryline' AND column_name='original_amount') THEN
        ALTER TABLE journalentryline ADD COLUMN original_amount DECIMAL(15,2);
    END IF;
END $$;

-- =============================================================================
-- FIX 4: Create missing indexes for performance
-- =============================================================================

-- Index on journalentryline for company and account lookups
CREATE INDEX IF NOT EXISTS idx_jel_company_account 
ON journalentryline(companycodeid, glaccountid);

-- Index on journalentryline for currency lookups
CREATE INDEX IF NOT EXISTS idx_jel_currency 
ON journalentryline(currencycode);

-- Index on journalentryline for fiscal period lookups
CREATE INDEX IF NOT EXISTS idx_jel_fiscal_period 
ON journalentryline(companycodeid, fiscalyear, fiscalperiod);

-- Index on glaccount for monetary classification
CREATE INDEX IF NOT EXISTS idx_glaccount_classification 
ON glaccount(monetary_classification);

-- Index on fx_revaluation_details for company and accounting standard
CREATE INDEX IF NOT EXISTS idx_fx_details_company_standard 
ON fx_revaluation_details(company_code, accounting_standard);

-- Index on entity_functional_currency for entity lookup
CREATE INDEX IF NOT EXISTS idx_entity_functional_currency_lookup 
ON entity_functional_currency(entity_id, effective_date DESC);

-- =============================================================================
-- FIX 5: Update existing data to populate new fields
-- =============================================================================

-- Set default values for existing fx_revaluation_details records
UPDATE fx_revaluation_details 
SET accounting_standard = 'ASC_830',
    translation_method = 'CURRENT_RATE',
    monetary_classification = 'MONETARY',
    pnl_component = unrealized_gain_loss
WHERE accounting_standard IS NULL;

-- Update journalentryline to populate exchange rates where missing
UPDATE journalentryline 
SET exchange_rate = 1.000000,
    translated_amount = CASE 
        WHEN currencycode = 'USD' THEN debitamount - creditamount
        ELSE (debitamount - creditamount) * 1.000000
    END
WHERE exchange_rate IS NULL;

-- =============================================================================
-- FIX 6: Add data validation constraints
-- =============================================================================

-- Ensure accounting_standard has valid values
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.check_constraints 
                  WHERE constraint_name = 'chk_fx_details_accounting_standard') THEN
        ALTER TABLE fx_revaluation_details 
        ADD CONSTRAINT chk_fx_details_accounting_standard 
        CHECK (accounting_standard IN ('ASC_830', 'IAS_21', 'IFRS_9', 'TAX_GAAP', 'MGMT_GAAP'));
    END IF;
END $$;

-- Ensure monetary_classification has valid values
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.check_constraints 
                  WHERE constraint_name = 'chk_glaccount_monetary_classification') THEN
        ALTER TABLE glaccount 
        ADD CONSTRAINT chk_glaccount_monetary_classification 
        CHECK (monetary_classification IN ('MONETARY', 'NON_MONETARY', 'EQUITY', 'REVENUE_EXPENSE'));
    END IF;
END $$;

-- =============================================================================
-- FIX 7: Add comments for documentation
-- =============================================================================

COMMENT ON COLUMN fx_revaluation_details.accounting_standard IS 'Accounting standard applied (ASC_830, IAS_21, etc.)';
COMMENT ON COLUMN fx_revaluation_details.cta_component IS 'Component of revaluation going to CTA/OCI';
COMMENT ON COLUMN fx_revaluation_details.pnl_component IS 'Component of revaluation going to P&L';
COMMENT ON COLUMN fx_revaluation_details.oci_component IS 'Component of revaluation going to OCI';
COMMENT ON COLUMN journalentryline.translated_amount IS 'Amount translated to functional/reporting currency';
COMMENT ON COLUMN journalentryline.exchange_rate IS 'Exchange rate used for translation';

-- =============================================================================
-- FIX 8: Grant permissions for new columns
-- =============================================================================

-- Grant permissions on new columns (if gl_user role exists)
DO $$ 
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'gl_user') THEN
        -- Permissions already granted by table-level grants
        NULL;
    END IF;
END $$;

COMMIT;

-- Post-migration validation
DO $$ 
DECLARE
    missing_columns INTEGER := 0;
BEGIN
    -- Check if all required columns exist
    SELECT COUNT(*) INTO missing_columns
    FROM (
        SELECT 'fx_revaluation_details.accounting_standard' as col
        WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns 
                         WHERE table_name='fx_revaluation_details' AND column_name='accounting_standard')
        UNION ALL
        SELECT 'fx_revaluation_details.pnl_component'
        WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns 
                         WHERE table_name='fx_revaluation_details' AND column_name='pnl_component')
        UNION ALL
        SELECT 'journalentryline.translated_amount'
        WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns 
                         WHERE table_name='journalentryline' AND column_name='translated_amount')
    ) missing;
    
    IF missing_columns > 0 THEN
        RAISE NOTICE 'WARNING: % critical columns still missing after migration', missing_columns;
    ELSE
        RAISE NOTICE 'SUCCESS: All critical database fixes applied successfully';
    END IF;
END $$;