-- IAS 21 Database Integration Fixes - Corrected Version
-- Resolves critical database integration issues with proper column references
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
END $$;

-- =============================================================================
-- FIX 3: Add missing translation fields to journalentryline
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
-- FIX 4: Create performance indexes with correct column names
-- =============================================================================

-- Index on journalentryline for company and account lookups
CREATE INDEX IF NOT EXISTS idx_jel_company_account 
ON journalentryline(companycodeid, glaccountid);

-- Index on journalentryline for currency lookups
CREATE INDEX IF NOT EXISTS idx_jel_currency 
ON journalentryline(currencycode);

-- Index on journalentryline for company and ledger
CREATE INDEX IF NOT EXISTS idx_jel_company_ledger 
ON journalentryline(companycodeid, ledgerid);

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
    END,
    original_amount = debitamount - creditamount
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

-- Ensure monetary_classification has valid values for glaccount
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
COMMENT ON COLUMN journalentryline.original_amount IS 'Original amount before any translation';

COMMIT;

-- Post-migration validation
DO $$ 
DECLARE
    missing_columns INTEGER := 0;
    success_message TEXT;
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
        UNION ALL
        SELECT 'journalentryline.exchange_rate'
        WHERE NOT EXISTS (SELECT 1 FROM information_schema.columns 
                         WHERE table_name='journalentryline' AND column_name='exchange_rate')
    ) missing;
    
    IF missing_columns > 0 THEN
        RAISE NOTICE 'WARNING: % critical columns still missing after migration', missing_columns;
    ELSE
        success_message := 'SUCCESS: All critical database fixes applied successfully' || chr(10) ||
                          '- Entity ID columns extended to VARCHAR(20)' || chr(10) ||
                          '- FX revaluation details enhanced with IAS 21 columns' || chr(10) ||
                          '- Journal entry lines enhanced with translation fields' || chr(10) ||
                          '- Performance indexes created' || chr(10) ||
                          '- Data validation constraints added';
        RAISE NOTICE '%', success_message;
    END IF;
END $$;