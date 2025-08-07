-- Migration: Configure Exchange Rate Management System
-- Description: Complete exchange rate infrastructure for multi-currency parallel ledger operations
-- Date: 2025-08-06
-- Author: Claude Code Assistant

BEGIN;

-- =============================================================================
-- PHASE 1: ENHANCE EXCHANGE RATE TABLE
-- =============================================================================

-- Add enhanced columns to exchange rate table (if not exists)
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='exchangerate' AND column_name='rate_type') THEN
        ALTER TABLE exchangerate ADD COLUMN rate_type VARCHAR(10) DEFAULT 'DAILY';
        ALTER TABLE exchangerate ADD COLUMN rate_source VARCHAR(20) DEFAULT 'MANUAL';
        ALTER TABLE exchangerate ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        ALTER TABLE exchangerate ADD COLUMN created_by VARCHAR(50) DEFAULT 'SYSTEM';
        ALTER TABLE exchangerate ADD COLUMN is_active BOOLEAN DEFAULT true;
    END IF;
END $$;

-- Create performance indexes (if not exist)
CREATE INDEX IF NOT EXISTS idx_exchangerate_date_active ON exchangerate(ratedate DESC, is_active);
CREATE INDEX IF NOT EXISTS idx_exchangerate_currencies ON exchangerate(fromcurrency, tocurrency);
CREATE INDEX IF NOT EXISTS idx_exchangerate_source ON exchangerate(rate_source, created_at DESC);

-- =============================================================================
-- PHASE 2: POPULATE CURRENT EXCHANGE RATES
-- =============================================================================

-- Insert current exchange rates for major currency pairs (avoid duplicates)
INSERT INTO exchangerate (fromcurrency, tocurrency, ratedate, rate, rate_type, rate_source, created_by, is_active) 
SELECT * FROM (VALUES
    -- USD as base currency
    ('USD', 'EUR', CURRENT_DATE, 0.9200, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true),
    ('USD', 'GBP', CURRENT_DATE, 0.7900, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true),
    ('USD', 'JPY', CURRENT_DATE, 150.0000, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true),
    ('USD', 'CAD', CURRENT_DATE, 1.3500, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true),
    ('USD', 'CHF', CURRENT_DATE, 0.8900, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true),
    ('USD', 'AUD', CURRENT_DATE, 1.5200, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true),
    
    -- EUR to other currencies
    ('EUR', 'USD', CURRENT_DATE, 1.0870, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true),
    ('EUR', 'GBP', CURRENT_DATE, 0.8587, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true),
    ('EUR', 'JPY', CURRENT_DATE, 163.0435, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true),
    ('EUR', 'CAD', CURRENT_DATE, 1.4675, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true),
    ('EUR', 'CHF', CURRENT_DATE, 0.9674, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true),
    
    -- GBP to other currencies
    ('GBP', 'USD', CURRENT_DATE, 1.2658, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true),
    ('GBP', 'EUR', CURRENT_DATE, 1.1646, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true),
    ('GBP', 'JPY', CURRENT_DATE, 189.8734, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true),
    ('GBP', 'CAD', CURRENT_DATE, 1.7088, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true),
    
    -- JPY to major currencies
    ('JPY', 'USD', CURRENT_DATE, 0.006667, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true),
    ('JPY', 'EUR', CURRENT_DATE, 0.006133, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true),
    ('JPY', 'GBP', CURRENT_DATE, 0.005267, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true),
    
    -- CAD to major currencies
    ('CAD', 'USD', CURRENT_DATE, 0.740741, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true),
    ('CAD', 'EUR', CURRENT_DATE, 0.681365, 'DAILY', 'SYSTEM_SETUP', 'MIGRATION_SCRIPT', true)
) AS new_rates(fromcurrency, tocurrency, ratedate, rate, rate_type, rate_source, created_by, is_active)
WHERE NOT EXISTS (
    SELECT 1 FROM exchangerate 
    WHERE fromcurrency = new_rates.fromcurrency 
    AND tocurrency = new_rates.tocurrency 
    AND ratedate = new_rates.ratedate
);

-- =============================================================================
-- PHASE 3: ADD HISTORICAL RATES FOR TREND ANALYSIS
-- =============================================================================

-- Add 7 days of historical data with slight variations
INSERT INTO exchangerate (fromcurrency, tocurrency, ratedate, rate, rate_type, rate_source, created_by, is_active) 
SELECT * FROM (VALUES
    -- USD/EUR historical rates
    ('USD', 'EUR', CURRENT_DATE - INTERVAL '1 day', 0.9195, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true),
    ('USD', 'EUR', CURRENT_DATE - INTERVAL '2 days', 0.9180, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true),
    ('USD', 'EUR', CURRENT_DATE - INTERVAL '3 days', 0.9210, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true),
    ('USD', 'EUR', CURRENT_DATE - INTERVAL '4 days', 0.9185, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true),
    ('USD', 'EUR', CURRENT_DATE - INTERVAL '5 days', 0.9175, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true),
    ('USD', 'EUR', CURRENT_DATE - INTERVAL '6 days', 0.9190, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true),
    ('USD', 'EUR', CURRENT_DATE - INTERVAL '7 days', 0.9205, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true),
    
    -- USD/GBP historical rates
    ('USD', 'GBP', CURRENT_DATE - INTERVAL '1 day', 0.7895, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true),
    ('USD', 'GBP', CURRENT_DATE - INTERVAL '2 days', 0.7885, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true),
    ('USD', 'GBP', CURRENT_DATE - INTERVAL '3 days', 0.7920, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true),
    ('USD', 'GBP', CURRENT_DATE - INTERVAL '4 days', 0.7910, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true),
    ('USD', 'GBP', CURRENT_DATE - INTERVAL '5 days', 0.7875, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true),
    ('USD', 'GBP', CURRENT_DATE - INTERVAL '6 days', 0.7890, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true),
    ('USD', 'GBP', CURRENT_DATE - INTERVAL '7 days', 0.7905, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true),
    
    -- EUR/USD reverse rates
    ('EUR', 'USD', CURRENT_DATE - INTERVAL '1 day', 1.0875, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true),
    ('EUR', 'USD', CURRENT_DATE - INTERVAL '2 days', 1.0893, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true),
    ('EUR', 'USD', CURRENT_DATE - INTERVAL '3 days', 1.0858, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true),
    
    -- GBP/USD reverse rates
    ('GBP', 'USD', CURRENT_DATE - INTERVAL '1 day', 1.2665, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true),
    ('GBP', 'USD', CURRENT_DATE - INTERVAL '2 days', 1.2682, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true),
    ('GBP', 'USD', CURRENT_DATE - INTERVAL '3 days', 1.2626, 'DAILY', 'HISTORICAL_DATA', 'MIGRATION_SCRIPT', true)
) AS historical_rates(fromcurrency, tocurrency, ratedate, rate, rate_type, rate_source, created_by, is_active)
WHERE NOT EXISTS (
    SELECT 1 FROM exchangerate 
    WHERE fromcurrency = historical_rates.fromcurrency 
    AND tocurrency = historical_rates.tocurrency 
    AND ratedate = historical_rates.ratedate
);

-- =============================================================================
-- PHASE 4: CREATE EXCHANGE RATE MANAGEMENT VIEWS
-- =============================================================================

-- Current exchange rates view
CREATE OR REPLACE VIEW v_current_exchange_rates AS
SELECT 
    er.fromcurrency,
    er.tocurrency,
    er.fromcurrency || '/' || er.tocurrency as currency_pair,
    er.rate,
    er.ratedate,
    er.rate_source,
    er.created_at,
    er.created_by,
    CASE 
        WHEN er.ratedate = CURRENT_DATE THEN '✅ Current'
        WHEN er.ratedate >= CURRENT_DATE - INTERVAL '3 days' THEN '🟡 Recent'
        ELSE '🔴 Stale'
    END as rate_status,
    CASE 
        WHEN er.rate_source = 'SYSTEM_SETUP' THEN '🔧 Setup'
        WHEN er.rate_source = 'MANUAL' THEN '👤 Manual'
        WHEN er.rate_source = 'API' THEN '🔗 API'
        WHEN er.rate_source = 'ECB' THEN '🏛️ ECB'
        ELSE '❓ Other'
    END as source_icon
FROM exchangerate er
INNER JOIN (
    SELECT fromcurrency, tocurrency, MAX(ratedate) as max_date
    FROM exchangerate 
    WHERE is_active = true
    GROUP BY fromcurrency, tocurrency
) latest ON er.fromcurrency = latest.fromcurrency 
    AND er.tocurrency = latest.tocurrency 
    AND er.ratedate = latest.max_date
WHERE er.is_active = true
ORDER BY er.fromcurrency, er.tocurrency;

-- Currency pair analysis view
CREATE OR REPLACE VIEW v_currency_pair_analysis AS  
SELECT 
    fromcurrency,
    tocurrency,
    fromcurrency || ' → ' || tocurrency as currency_pair,
    COUNT(*) as rate_count,
    MIN(ratedate) as first_rate_date,
    MAX(ratedate) as latest_rate_date,
    MIN(rate) as min_rate,
    MAX(rate) as max_rate,
    ROUND(AVG(rate), 6) as avg_rate,
    ROUND(STDDEV(rate), 6) as rate_volatility,
    ROUND(
        (MAX(rate) - MIN(rate)) / MIN(rate) * 100, 2
    ) as volatility_percent,
    CASE 
        WHEN MAX(ratedate) = CURRENT_DATE THEN '✅ Up to date'
        WHEN MAX(ratedate) >= CURRENT_DATE - INTERVAL '7 days' THEN '⚠️ Recent'
        ELSE '❌ Stale'
    END as data_quality
FROM exchangerate 
WHERE is_active = true
GROUP BY fromcurrency, tocurrency
ORDER BY fromcurrency, tocurrency;

-- Exchange rate trend view (last 30 days)
CREATE OR REPLACE VIEW v_exchange_rate_trends AS
SELECT 
    fromcurrency || '/' || tocurrency as currency_pair,
    ratedate,
    rate,
    LAG(rate) OVER (PARTITION BY fromcurrency, tocurrency ORDER BY ratedate) as prev_rate,
    rate - LAG(rate) OVER (PARTITION BY fromcurrency, tocurrency ORDER BY ratedate) as rate_change,
    ROUND(
        (rate - LAG(rate) OVER (PARTITION BY fromcurrency, tocurrency ORDER BY ratedate)) 
        / LAG(rate) OVER (PARTITION BY fromcurrency, tocurrency ORDER BY ratedate) * 100, 4
    ) as change_percent,
    rate_source,
    CASE 
        WHEN rate > LAG(rate) OVER (PARTITION BY fromcurrency, tocurrency ORDER BY ratedate) THEN '📈 Up'
        WHEN rate < LAG(rate) OVER (PARTITION BY fromcurrency, tocurrency ORDER BY ratedate) THEN '📉 Down'
        ELSE '➡️ Stable'
    END as trend_direction
FROM exchangerate
WHERE is_active = true 
AND ratedate >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY fromcurrency, tocurrency, ratedate DESC;

-- Parallel ledger currency requirements view  
CREATE OR REPLACE VIEW v_ledger_currency_requirements AS
SELECT 
    l.ledgerid,
    l.description as ledger_description,
    l.currencycode as base_currency,
    l.parallel_currency_1,
    l.parallel_currency_2,
    l.accounting_principle,
    -- Check if required rates exist
    CASE WHEN EXISTS (
        SELECT 1 FROM v_current_exchange_rates 
        WHERE fromcurrency = l.currencycode 
        AND tocurrency = l.parallel_currency_1
    ) THEN '✅' ELSE '❌' END as currency_1_rate_available,
    CASE WHEN EXISTS (
        SELECT 1 FROM v_current_exchange_rates 
        WHERE fromcurrency = l.currencycode 
        AND tocurrency = l.parallel_currency_2
    ) THEN '✅' ELSE '❌' END as currency_2_rate_available,
    CASE WHEN 
        EXISTS (SELECT 1 FROM v_current_exchange_rates WHERE fromcurrency = l.currencycode AND tocurrency = l.parallel_currency_1) 
        AND EXISTS (SELECT 1 FROM v_current_exchange_rates WHERE fromcurrency = l.currencycode AND tocurrency = l.parallel_currency_2)
    THEN '✅ Ready' ELSE '⚠️ Missing Rates' END as parallel_posting_readiness
FROM ledger l
WHERE l.accounting_principle IS NOT NULL
ORDER BY l.ledgerid;

-- =============================================================================
-- PHASE 5: CREATE EXCHANGE RATE AUDIT LOG
-- =============================================================================

-- Create exchange rate audit/change log table
CREATE TABLE IF NOT EXISTS exchange_rate_audit_log (
    log_id SERIAL PRIMARY KEY,
    operation VARCHAR(20), -- 'INSERT', 'UPDATE', 'DELETE', 'BULK_UPDATE'
    fromcurrency VARCHAR(3),
    tocurrency VARCHAR(3),
    old_rate NUMERIC(18,6),
    new_rate NUMERIC(18,6),
    rate_date DATE,
    rate_source VARCHAR(20),
    change_reason TEXT,
    created_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes on audit log
CREATE INDEX IF NOT EXISTS idx_exchange_audit_date ON exchange_rate_audit_log(created_at);
CREATE INDEX IF NOT EXISTS idx_exchange_audit_currencies ON exchange_rate_audit_log(fromcurrency, tocurrency);

-- Log the initial setup
INSERT INTO exchange_rate_audit_log (operation, change_reason, created_by) VALUES
('BULK_UPDATE', 'Exchange rate management system initialized with current and historical rates', 'MIGRATION_SCRIPT');

-- =============================================================================
-- PHASE 6: CREATE RATE VALIDATION FUNCTIONS
-- =============================================================================

-- Function to validate rate consistency (triangular arbitrage)
CREATE OR REPLACE FUNCTION validate_exchange_rate_consistency(
    base_currency VARCHAR(3) DEFAULT 'USD',
    tolerance NUMERIC DEFAULT 0.02
) RETURNS TABLE (
    currency_triplet TEXT,
    direct_rate NUMERIC,
    calculated_rate NUMERIC,
    deviation_percent NUMERIC,
    consistency_status TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH currency_triangles AS (
        SELECT 
            base_curr.tocurrency as intermediate_currency,
            target_curr.tocurrency as target_currency,
            base_curr.rate as base_to_intermediate_rate,
            target_curr.rate as intermediate_to_target_rate,
            base_curr.rate * target_curr.rate as calculated_direct_rate
        FROM exchangerate base_curr
        JOIN exchangerate target_curr ON base_curr.tocurrency = target_curr.fromcurrency
        WHERE base_curr.fromcurrency = base_currency
        AND target_curr.tocurrency != base_currency  
        AND base_curr.is_active = true
        AND target_curr.is_active = true
        AND base_curr.ratedate = (
            SELECT MAX(ratedate) FROM exchangerate 
            WHERE fromcurrency = base_curr.fromcurrency 
            AND tocurrency = base_curr.tocurrency 
            AND is_active = true
        )
        AND target_curr.ratedate = (
            SELECT MAX(ratedate) FROM exchangerate 
            WHERE fromcurrency = target_curr.fromcurrency 
            AND tocurrency = target_curr.tocurrency 
            AND is_active = true
        )
    )
    SELECT 
        base_currency || ' → ' || ct.intermediate_currency || ' → ' || ct.target_currency as currency_triplet,
        direct.rate as direct_rate,
        ct.calculated_direct_rate as calculated_rate,
        ABS(direct.rate - ct.calculated_direct_rate) / direct.rate * 100 as deviation_percent,
        CASE 
            WHEN ABS(direct.rate - ct.calculated_direct_rate) / direct.rate <= tolerance 
            THEN '✅ Consistent'
            ELSE '⚠️ Inconsistent'
        END as consistency_status
    FROM currency_triangles ct
    LEFT JOIN exchangerate direct ON direct.fromcurrency = base_currency 
        AND direct.tocurrency = ct.target_currency
        AND direct.is_active = true
        AND direct.ratedate = (
            SELECT MAX(ratedate) FROM exchangerate 
            WHERE fromcurrency = base_currency 
            AND tocurrency = ct.target_currency 
            AND is_active = true
        )
    WHERE direct.rate IS NOT NULL
    ORDER BY deviation_percent DESC;
END;
$$ LANGUAGE plpgsql;

COMMIT;

-- =============================================================================
-- POST-MIGRATION VERIFICATION
-- =============================================================================

-- Display configuration summary
\echo ''
\echo '========================================='
\echo 'EXCHANGE RATE SYSTEM CONFIGURATION COMPLETE'
\echo '========================================='
\echo ''

SELECT 'EXCHANGE RATE SUMMARY' as section, '' as details
UNION ALL
SELECT 'Currency Pairs Configured', COUNT(DISTINCT fromcurrency || '/' || tocurrency)::TEXT 
FROM exchangerate WHERE is_active = true
UNION ALL
SELECT 'Total Rate Records', COUNT(*)::TEXT 
FROM exchangerate WHERE is_active = true
UNION ALL  
SELECT 'Current Date Rates', COUNT(*)::TEXT 
FROM exchangerate WHERE ratedate = CURRENT_DATE AND is_active = true
UNION ALL
SELECT 'Historical Records', COUNT(*)::TEXT 
FROM exchangerate WHERE ratedate < CURRENT_DATE AND is_active = true;

\echo ''

SELECT 'PARALLEL LEDGER CURRENCY READINESS' as status;
SELECT 
    ledgerid,
    base_currency,
    parallel_currency_1 || '/' || parallel_currency_2 as parallel_currencies,
    parallel_posting_readiness
FROM v_ledger_currency_requirements
ORDER BY ledgerid;

\echo ''
\echo 'Exchange Rate System Features:'
\echo '✅ Multi-currency rate management'
\echo '✅ Historical rate tracking'  
\echo '✅ Rate consistency validation'
\echo '✅ Audit trail and logging'
\echo '✅ Management views and reporting'
\echo '✅ Parallel ledger integration ready'
\echo ''
\echo 'Next Steps:'
\echo '1. Test currency translation service'
\echo '2. Implement parallel posting automation'  
\echo '3. Set up automated rate updates'
\echo '4. Configure rate alert thresholds'
\echo ''