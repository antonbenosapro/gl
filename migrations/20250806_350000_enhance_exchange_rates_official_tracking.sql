-- Enhancement: Official Exchange Rates Tracking
-- Adds columns to support central bank official rates with regulatory compliance tracking
-- Date: August 6, 2025

BEGIN;

-- Add columns for official rates tracking
ALTER TABLE exchange_rates ADD COLUMN IF NOT EXISTS rate_source_type VARCHAR(20) DEFAULT 'MANUAL';
ALTER TABLE exchange_rates ADD COLUMN IF NOT EXISTS is_official BOOLEAN DEFAULT FALSE;
ALTER TABLE exchange_rates ADD COLUMN IF NOT EXISTS publication_date DATE;
ALTER TABLE exchange_rates ADD COLUMN IF NOT EXISTS updated_by VARCHAR(100);

-- Add comments for new columns
COMMENT ON COLUMN exchange_rates.rate_source_type IS 'Type of rate source: OFFICIAL, COMMERCIAL, MANUAL, API';
COMMENT ON COLUMN exchange_rates.is_official IS 'Flag indicating if rate is from official central bank source';
COMMENT ON COLUMN exchange_rates.publication_date IS 'Date when rate was published by source (may differ from rate_date)';
COMMENT ON COLUMN exchange_rates.updated_by IS 'User or service that last updated the rate';

-- Create index for official rates queries
CREATE INDEX IF NOT EXISTS idx_exchange_rates_official ON exchange_rates(is_official, rate_date, rate_source) WHERE is_official = true;

-- Create index for rate source type
CREATE INDEX IF NOT EXISTS idx_exchange_rates_source_type ON exchange_rates(rate_source_type, rate_date);

-- Update existing rates to set default values
UPDATE exchange_rates 
SET 
    rate_source_type = CASE 
        WHEN rate_source ILIKE '%manual%' OR rate_source IS NULL THEN 'MANUAL'
        WHEN rate_source ILIKE '%api%' THEN 'API'
        ELSE 'MANUAL'
    END,
    is_official = FALSE,
    updated_by = COALESCE(created_by, 'MIGRATION')
WHERE rate_source_type IS NULL;

-- Create view for official rates only
CREATE OR REPLACE VIEW v_official_exchange_rates AS
SELECT 
    from_currency,
    to_currency,
    rate,
    rate_date,
    rate_type,
    rate_source,
    rate_source_type,
    publication_date,
    created_by,
    created_at,
    updated_by,
    updated_at
FROM exchange_rates
WHERE is_official = true
ORDER BY rate_date DESC, rate_source, from_currency;

COMMENT ON VIEW v_official_exchange_rates IS 'View showing only official central bank exchange rates for regulatory compliance';

-- Create function to get latest official rate
CREATE OR REPLACE FUNCTION get_latest_official_rate(
    p_from_currency VARCHAR(3),
    p_to_currency VARCHAR(3),
    p_rate_date DATE DEFAULT CURRENT_DATE
) RETURNS DECIMAL(15,6) AS $$
DECLARE
    v_rate DECIMAL(15,6);
BEGIN
    SELECT rate INTO v_rate
    FROM exchange_rates
    WHERE from_currency = p_from_currency
    AND to_currency = p_to_currency
    AND is_official = true
    AND rate_date <= p_rate_date
    ORDER BY rate_date DESC, publication_date DESC
    LIMIT 1;
    
    RETURN COALESCE(v_rate, 0);
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_latest_official_rate IS 'Get the latest official exchange rate for a currency pair on or before a specific date';

-- Create audit trigger for official rates changes
CREATE OR REPLACE FUNCTION audit_official_rates_change() RETURNS TRIGGER AS $$
BEGIN
    -- Only log changes to official rates
    IF NEW.is_official = true THEN
        INSERT INTO audit_log (
            table_name,
            record_id,
            action,
            old_values,
            new_values,
            changed_by,
            changed_at
        ) VALUES (
            'exchange_rates',
            NEW.rate_id,
            TG_OP,
            CASE WHEN TG_OP = 'UPDATE' THEN row_to_json(OLD) ELSE NULL END,
            row_to_json(NEW),
            COALESCE(NEW.updated_by, NEW.created_by, 'SYSTEM'),
            CURRENT_TIMESTAMP
        );
    END IF;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Create the trigger (only if audit_log table exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'audit_log') THEN
        DROP TRIGGER IF EXISTS trg_audit_official_rates ON exchange_rates;
        CREATE TRIGGER trg_audit_official_rates
            AFTER INSERT OR UPDATE OR DELETE ON exchange_rates
            FOR EACH ROW EXECUTE FUNCTION audit_official_rates_change();
    END IF;
END $$;

-- Create summary view for official rates by source
CREATE OR REPLACE VIEW v_official_rates_summary AS
SELECT 
    rate_source,
    rate_source_type,
    COUNT(*) as total_rates,
    COUNT(DISTINCT from_currency) as currencies_count,
    MIN(rate_date) as earliest_rate,
    MAX(rate_date) as latest_rate,
    MAX(publication_date) as last_publication,
    MAX(updated_at) as last_updated
FROM exchange_rates
WHERE is_official = true
GROUP BY rate_source, rate_source_type
ORDER BY last_updated DESC;

COMMENT ON VIEW v_official_rates_summary IS 'Summary of official exchange rates by source for monitoring and compliance';

-- Insert sample official rate sources metadata
CREATE TABLE IF NOT EXISTS official_rate_sources (
    source_id SERIAL PRIMARY KEY,
    source_code VARCHAR(20) UNIQUE NOT NULL,
    source_name VARCHAR(100) NOT NULL,
    source_description TEXT,
    base_currency VARCHAR(3) NOT NULL,
    frequency VARCHAR(20) NOT NULL,
    publication_time VARCHAR(50),
    api_endpoint VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE official_rate_sources IS 'Registry of official exchange rate sources (central banks, regulatory bodies)';

-- Insert known official sources
INSERT INTO official_rate_sources (source_code, source_name, source_description, base_currency, frequency, publication_time, api_endpoint) 
VALUES 
    ('FED_H10', 'Federal Reserve H.10', 'US Federal Reserve daily bilateral exchange rates', 'USD', 'Daily', '4:15 PM ET', 'https://www.federalreserve.gov/releases/h10/'),
    ('ECB_REF', 'ECB Reference Rates', 'European Central Bank daily reference rates', 'EUR', 'Daily', '4:00 PM CET', 'https://www.ecb.europa.eu/stats/eurofxref/'),
    ('BOE', 'Bank of England', 'Bank of England official exchange rates', 'GBP', 'Daily', 'Various', 'https://www.bankofengland.co.uk/boeapps/database/'),
    ('BIS', 'Bank for International Settlements', 'BIS effective exchange rates', 'USD', 'Monthly', 'Various', 'https://www.bis.org/statistics/eer.htm')
ON CONFLICT (source_code) DO NOTHING;

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_official_rate_sources_modtime 
    BEFORE UPDATE ON official_rate_sources 
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

COMMIT;

-- Verification queries (for testing)
DO $$
BEGIN
    RAISE NOTICE 'Exchange rates schema enhancement completed successfully.';
    RAISE NOTICE 'Total exchange rates: %', (SELECT COUNT(*) FROM exchange_rates);
    RAISE NOTICE 'Official rate sources: %', (SELECT COUNT(*) FROM official_rate_sources);
    RAISE NOTICE 'Official rates view: %', (SELECT COUNT(*) FROM v_official_exchange_rates);
END $$;