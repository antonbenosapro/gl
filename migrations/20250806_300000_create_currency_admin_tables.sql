-- Currency Administration Tables
-- Creates tables for currency master data and exchange rates management
-- Date: August 6, 2025

-- Create currencies master table
CREATE TABLE IF NOT EXISTS currencies (
    currency_code VARCHAR(3) PRIMARY KEY,
    currency_name VARCHAR(100) NOT NULL,
    currency_symbol VARCHAR(10),
    decimal_places INTEGER DEFAULT 2 CHECK (decimal_places >= 0 AND decimal_places <= 6),
    is_base_currency BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50) DEFAULT 'system',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_currency_code_format CHECK (LENGTH(currency_code) = 3 AND currency_code ~ '^[A-Z]{3}$')
);

-- Create exchange_rates table with proper constraints
CREATE TABLE IF NOT EXISTS exchange_rates (
    rate_id SERIAL PRIMARY KEY,
    from_currency VARCHAR(3) NOT NULL,
    to_currency VARCHAR(3) NOT NULL,
    rate_date DATE NOT NULL,
    rate_type VARCHAR(20) NOT NULL CHECK (rate_type IN ('SPOT', 'CLOSING', 'AVERAGE', 'HISTORICAL', 'BUDGET')),
    exchange_rate DECIMAL(15,6) NOT NULL CHECK (exchange_rate > 0),
    source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50) DEFAULT 'system',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uk_exchange_rates UNIQUE (from_currency, to_currency, rate_type, rate_date),
    CONSTRAINT chk_currency_diff CHECK (from_currency != to_currency),
    CONSTRAINT chk_currency_format_from CHECK (LENGTH(from_currency) = 3 AND from_currency ~ '^[A-Z]{3}$'),
    CONSTRAINT chk_currency_format_to CHECK (LENGTH(to_currency) = 3 AND to_currency ~ '^[A-Z]{3}$')
);

-- Insert default currencies
INSERT INTO currencies (currency_code, currency_name, currency_symbol, decimal_places, is_base_currency, is_active, created_by)
VALUES 
    ('USD', 'US Dollar', '$', 2, true, true, 'MIGRATION'),
    ('EUR', 'Euro', '€', 2, false, true, 'MIGRATION'),
    ('GBP', 'British Pound', '£', 2, false, true, 'MIGRATION'),
    ('JPY', 'Japanese Yen', '¥', 0, false, true, 'MIGRATION'),
    ('CHF', 'Swiss Franc', 'CHF', 2, false, true, 'MIGRATION'),
    ('CAD', 'Canadian Dollar', 'C$', 2, false, true, 'MIGRATION'),
    ('AUD', 'Australian Dollar', 'A$', 2, false, true, 'MIGRATION')
ON CONFLICT (currency_code) DO UPDATE SET
    currency_name = EXCLUDED.currency_name,
    currency_symbol = EXCLUDED.currency_symbol,
    updated_at = CURRENT_TIMESTAMP;

-- Insert sample exchange rates for current date
INSERT INTO exchange_rates (from_currency, to_currency, rate_date, rate_type, exchange_rate, source, created_by)
VALUES 
    ('EUR', 'USD', CURRENT_DATE, 'CLOSING', 1.085000, 'ECB', 'MIGRATION'),
    ('GBP', 'USD', CURRENT_DATE, 'CLOSING', 1.265000, 'BOE', 'MIGRATION'),
    ('JPY', 'USD', CURRENT_DATE, 'CLOSING', 0.006700, 'BOJ', 'MIGRATION'),
    ('CHF', 'USD', CURRENT_DATE, 'CLOSING', 1.092000, 'SNB', 'MIGRATION'),
    ('CAD', 'USD', CURRENT_DATE, 'CLOSING', 0.734500, 'BOC', 'MIGRATION'),
    ('AUD', 'USD', CURRENT_DATE, 'CLOSING', 0.678900, 'RBA', 'MIGRATION'),
    
    -- Add some historical rates
    ('EUR', 'USD', CURRENT_DATE - 1, 'CLOSING', 1.083500, 'ECB', 'MIGRATION'),
    ('EUR', 'USD', CURRENT_DATE - 2, 'CLOSING', 1.087200, 'ECB', 'MIGRATION'),
    ('EUR', 'USD', CURRENT_DATE - 3, 'CLOSING', 1.084800, 'ECB', 'MIGRATION'),
    
    ('GBP', 'USD', CURRENT_DATE - 1, 'CLOSING', 1.263200, 'BOE', 'MIGRATION'),
    ('GBP', 'USD', CURRENT_DATE - 2, 'CLOSING', 1.267800, 'BOE', 'MIGRATION'),
    ('GBP', 'USD', CURRENT_DATE - 3, 'CLOSING', 1.261500, 'BOE', 'MIGRATION')
ON CONFLICT (from_currency, to_currency, rate_type, rate_date) DO UPDATE SET
    exchange_rate = EXCLUDED.exchange_rate,
    source = EXCLUDED.source,
    updated_at = CURRENT_TIMESTAMP;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_exchange_rates_currency_pair ON exchange_rates(from_currency, to_currency);
CREATE INDEX IF NOT EXISTS idx_exchange_rates_date ON exchange_rates(rate_date DESC);
CREATE INDEX IF NOT EXISTS idx_exchange_rates_type ON exchange_rates(rate_type);
CREATE INDEX IF NOT EXISTS idx_exchange_rates_source ON exchange_rates(source);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to both tables
DROP TRIGGER IF EXISTS update_currencies_updated_at ON currencies;
CREATE TRIGGER update_currencies_updated_at 
    BEFORE UPDATE ON currencies 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_exchange_rates_updated_at ON exchange_rates;
CREATE TRIGGER update_exchange_rates_updated_at 
    BEFORE UPDATE ON exchange_rates 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE currencies IS 'Master data for currencies supported by the system';
COMMENT ON TABLE exchange_rates IS 'Exchange rates between currencies with different rate types and historical tracking';

COMMENT ON COLUMN currencies.currency_code IS 'ISO 4217 3-letter currency code';
COMMENT ON COLUMN currencies.is_base_currency IS 'Indicates if this is the base/functional currency for the organization';
COMMENT ON COLUMN exchange_rates.rate_type IS 'Type of exchange rate: SPOT, CLOSING, AVERAGE, HISTORICAL, or BUDGET';
COMMENT ON COLUMN exchange_rates.exchange_rate IS '1 unit of from_currency equals this many units of to_currency';