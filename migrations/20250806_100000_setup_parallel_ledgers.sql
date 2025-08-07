-- Migration: Setup Parallel Ledgers
-- Description: Configure parallel ledger infrastructure for multi-standard accounting
-- Date: 2025-08-06
-- Author: Claude Code Assistant

BEGIN;

-- =============================================================================
-- PHASE 1: ENHANCE LEDGER INFRASTRUCTURE
-- =============================================================================

-- Add enhanced columns to ledger table (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ledger' AND column_name='accounting_principle') THEN
        ALTER TABLE ledger ADD COLUMN accounting_principle VARCHAR(20);
        ALTER TABLE ledger ADD COLUMN parallel_currency_1 VARCHAR(3);
        ALTER TABLE ledger ADD COLUMN parallel_currency_2 VARCHAR(3);
        ALTER TABLE ledger ADD COLUMN consolidation_ledger BOOLEAN DEFAULT false;
        ALTER TABLE ledger ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE ledger ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
    END IF;
END $$;

-- Update existing leading ledger with enhanced information
UPDATE ledger SET 
    accounting_principle = 'US_GAAP',
    parallel_currency_1 = 'EUR',
    parallel_currency_2 = 'GBP',
    consolidation_ledger = true,
    updated_at = CURRENT_TIMESTAMP
WHERE ledgerid = 'L1' AND accounting_principle IS NULL;

-- Insert new parallel ledgers (avoid duplicates)
INSERT INTO ledger (ledgerid, description, isleadingledger, currencycode, accounting_principle, parallel_currency_1, parallel_currency_2, consolidation_ledger) 
SELECT * FROM (VALUES
    ('2L', 'IFRS Reporting Ledger', false, 'USD', 'IFRS', 'EUR', 'GBP', false),
    ('3L', 'Tax Reporting Ledger', false, 'USD', 'TAX_GAAP', 'EUR', 'GBP', false),
    ('4L', 'Management Reporting Ledger', false, 'USD', 'MGMT_GAAP', 'EUR', 'GBP', false),
    ('CL', 'Consolidation Ledger', false, 'USD', 'IFRS', 'EUR', 'GBP', true)
) AS new_ledgers(ledgerid, description, isleadingledger, currencycode, accounting_principle, parallel_currency_1, parallel_currency_2, consolidation_ledger)
WHERE NOT EXISTS (SELECT 1 FROM ledger WHERE ledger.ledgerid = new_ledgers.ledgerid);

-- =============================================================================
-- PHASE 2: CREATE DERIVATION RULES INFRASTRUCTURE
-- =============================================================================

-- Create ledger derivation rules table (if not exists)
CREATE TABLE IF NOT EXISTS ledger_derivation_rules (
    rule_id SERIAL PRIMARY KEY,
    source_ledger VARCHAR(10) REFERENCES ledger(ledgerid),
    target_ledger VARCHAR(10) REFERENCES ledger(ledgerid),
    gl_account VARCHAR(10),
    account_group_filter VARCHAR(20),
    derivation_rule VARCHAR(50), -- 'COPY', 'TRANSLATE', 'EXCLUDE', 'RECLASSIFY', 'ADJUST'
    target_account VARCHAR(10),
    conversion_factor NUMERIC(9,5) DEFAULT 1.0,
    adjustment_reason VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance (if not exist)
CREATE INDEX IF NOT EXISTS idx_derivation_rules_source_target ON ledger_derivation_rules(source_ledger, target_ledger);
CREATE INDEX IF NOT EXISTS idx_derivation_rules_account ON ledger_derivation_rules(gl_account);
CREATE INDEX IF NOT EXISTS idx_derivation_rules_active ON ledger_derivation_rules(is_active);

-- =============================================================================
-- PHASE 3: POPULATE STANDARD DERIVATION RULES
-- =============================================================================

-- US GAAP (L1) to IFRS (2L) standard mappings
INSERT INTO ledger_derivation_rules (source_ledger, target_ledger, account_group_filter, derivation_rule, adjustment_reason) 
SELECT * FROM (VALUES
    -- Asset accounts
    ('L1', '2L', 'CASH', 'COPY', 'Cash accounts identical in both standards'),
    ('L1', '2L', 'RECV', 'COPY', 'Receivables identical in both standards'),
    ('L1', '2L', 'INVT', 'COPY', 'Inventory valuation identical'),
    ('L1', '2L', 'PREP', 'COPY', 'Prepaid expenses identical'),
    ('L1', '2L', 'FXAS', 'ADJUST', 'Fixed assets may require revaluation adjustments'),
    ('L1', '2L', 'INVA', 'ADJUST', 'Investments may have fair value differences'),
    
    -- Liability accounts
    ('L1', '2L', 'PAYB', 'COPY', 'Payables identical in both standards'),
    ('L1', '2L', 'ACCR', 'COPY', 'Accruals identical in both standards'),
    ('L1', '2L', 'STDB', 'COPY', 'Short-term debt identical'),
    ('L1', '2L', 'LTDB', 'ADJUST', 'Long-term debt may require fair value adjustments'),
    
    -- Equity accounts
    ('L1', '2L', 'EQTY', 'COPY', 'Share capital identical'),
    ('L1', '2L', 'RETE', 'ADJUST', 'Retained earnings adjusted for IFRS differences'),
    ('L1', '2L', 'OCIE', 'ADJUST', 'OCI may have different components under IFRS'),
    
    -- Revenue accounts
    ('L1', '2L', 'SALE', 'COPY', 'Revenue recognition similar under IFRS 15'),
    ('L1', '2L', 'OINC', 'COPY', 'Other income identical'),
    
    -- Expense accounts
    ('L1', '2L', 'COGS', 'COPY', 'COGS identical in both standards'),
    ('L1', '2L', 'OPEX', 'ADJUST', 'Operating expenses may have timing differences'),
    ('L1', '2L', 'FINX', 'ADJUST', 'Financial expenses may have classification differences')
) AS rules(source_ledger, target_ledger, account_group_filter, derivation_rule, adjustment_reason)
WHERE NOT EXISTS (
    SELECT 1 FROM ledger_derivation_rules 
    WHERE source_ledger = rules.source_ledger 
    AND target_ledger = rules.target_ledger 
    AND account_group_filter = rules.account_group_filter
);

-- US GAAP (L1) to Tax Ledger (3L) mappings
INSERT INTO ledger_derivation_rules (source_ledger, target_ledger, account_group_filter, derivation_rule, adjustment_reason) 
SELECT * FROM (VALUES
    ('L1', '3L', 'CASH', 'COPY', 'Cash position identical for tax'),
    ('L1', '3L', 'RECV', 'COPY', 'Receivables at book value for tax'),
    ('L1', '3L', 'INVT', 'ADJUST', 'Inventory may use different costing methods for tax'),
    ('L1', '3L', 'FXAS', 'ADJUST', 'Fixed assets use tax depreciation schedules'),
    ('L1', '3L', 'PAYB', 'COPY', 'Payables identical for tax'),
    ('L1', '3L', 'ACCR', 'ADJUST', 'Accruals may differ based on tax deductibility'),
    ('L1', '3L', 'EQTY', 'COPY', 'Equity base identical for tax'),
    ('L1', '3L', 'SALE', 'ADJUST', 'Revenue recognition may differ for tax timing'),
    ('L1', '3L', 'COGS', 'ADJUST', 'COGS timing may differ for tax'),
    ('L1', '3L', 'OPEX', 'ADJUST', 'Operating expenses subject to tax limitations'),
    ('L1', '3L', 'FINX', 'ADJUST', 'Interest expense may be limited for tax')
) AS rules(source_ledger, target_ledger, account_group_filter, derivation_rule, adjustment_reason)
WHERE NOT EXISTS (
    SELECT 1 FROM ledger_derivation_rules 
    WHERE source_ledger = rules.source_ledger 
    AND target_ledger = rules.target_ledger 
    AND account_group_filter = rules.account_group_filter
);

-- US GAAP (L1) to Management Ledger (4L) mappings
INSERT INTO ledger_derivation_rules (source_ledger, target_ledger, account_group_filter, derivation_rule, adjustment_reason) 
SELECT * FROM (VALUES
    ('L1', '4L', 'CASH', 'COPY', 'Cash identical for management reporting'),
    ('L1', '4L', 'RECV', 'ADJUST', 'Receivables may include management reserves'),
    ('L1', '4L', 'INVT', 'ADJUST', 'Inventory at current replacement cost'),
    ('L1', '4L', 'FXAS', 'ADJUST', 'Fixed assets at current market values'),
    ('L1', '4L', 'PAYB', 'COPY', 'Payables identical'),
    ('L1', '4L', 'SALE', 'ADJUST', 'Revenue may include management adjustments'),
    ('L1', '4L', 'COGS', 'ADJUST', 'COGS may include standard cost variances'),
    ('L1', '4L', 'OPEX', 'ADJUST', 'Operating expenses with management allocations')
) AS rules(source_ledger, target_ledger, account_group_filter, derivation_rule, adjustment_reason)
WHERE NOT EXISTS (
    SELECT 1 FROM ledger_derivation_rules 
    WHERE source_ledger = rules.source_ledger 
    AND target_ledger = rules.target_ledger 
    AND account_group_filter = rules.account_group_filter
);

-- =============================================================================
-- PHASE 4: CREATE MANAGEMENT VIEWS
-- =============================================================================

-- Comprehensive ledger configuration view
CREATE OR REPLACE VIEW v_ledger_configuration AS
SELECT 
    l.ledgerid,
    l.description,
    l.isleadingledger,
    l.currencycode,
    l.accounting_principle,
    l.parallel_currency_1,
    l.parallel_currency_2,
    l.consolidation_ledger,
    l.created_at,
    COUNT(ldr.rule_id) as derivation_rules_count
FROM ledger l
LEFT JOIN ledger_derivation_rules ldr ON l.ledgerid = ldr.target_ledger AND ldr.is_active = true
GROUP BY l.ledgerid, l.description, l.isleadingledger, l.currencycode, 
         l.accounting_principle, l.parallel_currency_1, l.parallel_currency_2, 
         l.consolidation_ledger, l.created_at
ORDER BY l.ledgerid;

-- Detailed derivation rules view
CREATE OR REPLACE VIEW v_derivation_rules_summary AS
SELECT 
    ldr.rule_id,
    ldr.source_ledger,
    sl.description as source_description,
    sl.accounting_principle as source_principle,
    ldr.target_ledger,
    tl.description as target_description,
    tl.accounting_principle as target_principle,
    ldr.account_group_filter,
    ldr.derivation_rule,
    ldr.conversion_factor,
    ldr.adjustment_reason,
    ldr.is_active,
    ldr.created_at
FROM ledger_derivation_rules ldr
JOIN ledger sl ON ldr.source_ledger = sl.ledgerid
JOIN ledger tl ON ldr.target_ledger = tl.ledgerid
ORDER BY ldr.source_ledger, ldr.target_ledger, ldr.account_group_filter;

-- Parallel ledger readiness view
CREATE OR REPLACE VIEW v_parallel_ledger_readiness AS
SELECT 
    'Ledger Configuration' as component,
    COUNT(ledgerid) as configured_count,
    CASE WHEN COUNT(ledgerid) >= 4 THEN '✅ Ready' ELSE '⚠️ Incomplete' END as status
FROM ledger
WHERE accounting_principle IS NOT NULL

UNION ALL

SELECT 
    'Derivation Rules' as component,
    COUNT(rule_id) as configured_count,
    CASE WHEN COUNT(rule_id) >= 30 THEN '✅ Ready' ELSE '⚠️ Incomplete' END as status
FROM ledger_derivation_rules
WHERE is_active = true

UNION ALL

SELECT 
    'Exchange Rates' as component,
    COUNT(*) as configured_count,
    CASE WHEN COUNT(*) > 0 THEN '✅ Ready' ELSE '❌ Missing' END as status
FROM exchangerate
WHERE ratedate >= CURRENT_DATE - INTERVAL '7 days';

-- =============================================================================
-- PHASE 5: CREATE AUDIT AND TRACKING
-- =============================================================================

-- Create parallel ledger audit log
CREATE TABLE IF NOT EXISTS parallel_ledger_audit_log (
    log_id SERIAL PRIMARY KEY,
    operation VARCHAR(20), -- 'SETUP', 'CONFIG', 'POST', 'ADJUST'
    source_ledger VARCHAR(10),
    target_ledger VARCHAR(10),
    document_number VARCHAR(20),
    gl_account VARCHAR(10),
    amount NUMERIC(18,2),
    derivation_rule VARCHAR(50),
    details TEXT,
    created_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on audit log
CREATE INDEX IF NOT EXISTS idx_parallel_audit_date ON parallel_ledger_audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_parallel_audit_ledger ON parallel_ledger_audit_log(source_ledger, target_ledger);

-- Log the initial setup
INSERT INTO parallel_ledger_audit_log (operation, details, created_by) VALUES
('SETUP', 'Parallel ledger infrastructure initialized with 5 ledgers and derivation rules', 'MIGRATION_SCRIPT');

COMMIT;

-- =============================================================================
-- POST-MIGRATION VERIFICATION
-- =============================================================================

-- Display configuration summary
\echo ''
\echo '========================================='
\echo 'PARALLEL LEDGER SETUP COMPLETE'
\echo '========================================='
\echo ''

SELECT 'LEDGER CONFIGURATION' as section, '' as details
UNION ALL
SELECT ledgerid, CONCAT(description, ' (', accounting_principle, ')') FROM ledger ORDER BY ledgerid;

\echo ''

SELECT 'DERIVATION RULES SUMMARY' as section, '' as details
UNION ALL  
SELECT CONCAT(source_ledger, ' → ', target_ledger), 
       CONCAT(COUNT(*), ' rules configured') 
FROM ledger_derivation_rules 
WHERE is_active = true 
GROUP BY source_ledger, target_ledger 
ORDER BY source_ledger, target_ledger;

\echo ''
\echo 'Next Steps:'
\echo '1. Configure exchange rates for multi-currency support'
\echo '2. Implement parallel posting automation'
\echo '3. Set up ledger-specific reporting'
\echo '4. Test end-to-end parallel ledger functionality'
\echo ''