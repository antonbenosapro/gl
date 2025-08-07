-- Accounting Standards Compliance Enhancement
-- Implements full ASC 830 (US GAAP) and IAS 21 (IFRS) compliance for foreign currency
-- Date: August 6, 2025
-- Author: Claude Code Assistant

BEGIN;

-- =============================================================================
-- PHASE 1: FUNCTIONAL CURRENCY FRAMEWORK
-- =============================================================================

-- Entity functional currency tracking
CREATE TABLE IF NOT EXISTS entity_functional_currency (
    entity_id VARCHAR(10) PRIMARY KEY,
    entity_name VARCHAR(100) NOT NULL,
    functional_currency VARCHAR(3) NOT NULL,
    effective_date DATE NOT NULL,
    previous_functional_currency VARCHAR(3),
    change_reason VARCHAR(200),
    
    -- ASC 830-10 Assessment Factors
    primary_economic_environment VARCHAR(100),
    cash_flow_indicators JSONB, -- {primary_currency, intercompany_flows, local_financing}
    sales_price_indicators JSONB, -- {sales_currency, pricing_sensitivity, competition}
    cost_indicators JSONB, -- {cost_currency, labor_costs, material_costs}
    financing_indicators JSONB, -- {debt_currency, equity_currency, dividend_currency}
    
    -- Assessment conclusion and review
    assessment_methodology VARCHAR(50), -- ASC_830, IAS_21, HYBRID
    assessment_conclusion TEXT,
    risk_factors TEXT,
    next_review_date DATE,
    
    -- Audit trail
    assessed_by VARCHAR(50) NOT NULL,
    approved_by VARCHAR(50),
    assessment_date DATE NOT NULL,
    approval_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_entity_functional_currency_entity FOREIGN KEY (entity_id) REFERENCES companycode(companycodeid)
);

-- Functional currency assessment history
CREATE TABLE IF NOT EXISTS functional_currency_history (
    history_id SERIAL PRIMARY KEY,
    entity_id VARCHAR(10) NOT NULL,
    effective_date DATE NOT NULL,
    functional_currency VARCHAR(3) NOT NULL,
    previous_currency VARCHAR(3),
    change_type VARCHAR(20), -- INITIAL, CHANGE, REVIEW
    assessment_factors JSONB,
    business_justification TEXT,
    financial_impact_analysis JSONB,
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_functional_currency_history_entity FOREIGN KEY (entity_id) REFERENCES companycode(companycodeid)
);

-- =============================================================================  
-- PHASE 2: MONETARY VS NON-MONETARY CLASSIFICATION
-- =============================================================================

-- Enhance GL accounts with monetary classification
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='glaccount' AND column_name='monetary_classification') THEN
        ALTER TABLE glaccount ADD COLUMN monetary_classification VARCHAR(20) DEFAULT 'MONETARY';
        ALTER TABLE glaccount ADD COLUMN translation_method VARCHAR(20) DEFAULT 'CURRENT_RATE';
        ALTER TABLE glaccount ADD COLUMN fx_sensitivity VARCHAR(10) DEFAULT 'HIGH'; -- HIGH, MEDIUM, LOW, NONE
        ALTER TABLE glaccount ADD COLUMN hedge_accounting_eligible BOOLEAN DEFAULT false;
        ALTER TABLE glaccount ADD COLUMN standards_notes TEXT;
    END IF;
END $$;

-- Update existing accounts with proper classification
UPDATE glaccount SET 
    monetary_classification = 'MONETARY',
    translation_method = 'CURRENT_RATE',
    fx_sensitivity = 'HIGH'
WHERE accounttype IN ('ASSETS', 'LIABILITIES') 
AND glaccountid IN ('100001', '100002', '115001', '115002', '210001', '210002', '225001', '232001', '231001');

UPDATE glaccount SET 
    monetary_classification = 'NON_MONETARY', 
    translation_method = 'HISTORICAL_RATE',
    fx_sensitivity = 'LOW'
WHERE accounttype IN ('ASSETS') 
AND glaccountid IN ('150001', '120001'); -- Fixed assets, inventory

UPDATE glaccount SET
    monetary_classification = 'EQUITY',
    translation_method = 'HISTORICAL_RATE', 
    fx_sensitivity = 'NONE'
WHERE accounttype = 'EQUITY';

UPDATE glaccount SET
    monetary_classification = 'REVENUE_EXPENSE',
    translation_method = 'AVERAGE_RATE',
    fx_sensitivity = 'MEDIUM'  
WHERE accounttype IN ('REVENUE', 'EXPENSES');

-- =============================================================================
-- PHASE 3: CUMULATIVE TRANSLATION ADJUSTMENT (CTA) TRACKING
-- =============================================================================

-- CTA tracking for ASC 830 and IAS 21 compliance
CREATE TABLE IF NOT EXISTS cumulative_translation_adjustment (
    cta_id SERIAL PRIMARY KEY,
    entity_id VARCHAR(10) NOT NULL,
    ledger_id VARCHAR(10) NOT NULL,
    accounting_standard VARCHAR(20) NOT NULL, -- ASC_830, IAS_21
    
    -- Currency information
    functional_currency VARCHAR(3) NOT NULL,
    reporting_currency VARCHAR(3) NOT NULL,
    currency_pair VARCHAR(7) NOT NULL, -- e.g., EURUSD
    
    -- Period information
    fiscal_year INTEGER NOT NULL,
    fiscal_period INTEGER NOT NULL,
    period_end_date DATE NOT NULL,
    
    -- CTA balances
    opening_cta DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    period_movement DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    closing_cta DECIMAL(15,2) NOT NULL DEFAULT 0.00,
    
    -- Recycling tracking (for disposals)
    recycled_to_pnl DECIMAL(15,2) DEFAULT 0.00,
    recycling_date DATE,
    disposal_reason VARCHAR(100),
    disposal_entity VARCHAR(100),
    
    -- Component breakdown
    asset_translation_adj DECIMAL(15,2) DEFAULT 0.00,
    liability_translation_adj DECIMAL(15,2) DEFAULT 0.00,
    equity_translation_adj DECIMAL(15,2) DEFAULT 0.00,
    
    -- Hedge accounting
    net_investment_hedge_adj DECIMAL(15,2) DEFAULT 0.00,
    hedge_effectiveness DECIMAL(8,4) DEFAULT 1.0000,
    
    -- Audit trail
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_cta_entity FOREIGN KEY (entity_id) REFERENCES companycode(companycodeid),
    CONSTRAINT fk_cta_ledger FOREIGN KEY (ledger_id) REFERENCES ledger(ledgerid),
    CONSTRAINT uk_cta_period UNIQUE (entity_id, ledger_id, accounting_standard, fiscal_year, fiscal_period)
);

-- =============================================================================
-- PHASE 4: HYPERINFLATIONARY ECONOMY SUPPORT  
-- =============================================================================

-- Hyperinflationary economy monitoring
CREATE TABLE IF NOT EXISTS hyperinflationary_economies (
    economy_id SERIAL PRIMARY KEY,
    country_code VARCHAR(3) NOT NULL,
    country_name VARCHAR(100) NOT NULL,
    currency_code VARCHAR(3) NOT NULL,
    
    -- Status tracking
    status VARCHAR(20) NOT NULL DEFAULT 'NORMAL', -- NORMAL, HYPERINFLATIONARY, MONITORING
    status_effective_date DATE NOT NULL,
    cumulative_inflation_rate DECIMAL(8,4),
    annual_inflation_rate DECIMAL(8,4),
    
    -- Monitoring criteria
    three_year_cumulative_rate DECIMAL(8,4),
    monetary_policy_indicators TEXT,
    economic_environment_factors TEXT,
    
    -- Price index information
    price_index_series VARCHAR(50),
    base_index_date DATE,
    current_index_value DECIMAL(12,4),
    index_source VARCHAR(100),
    
    -- Review and approval
    last_assessment_date DATE,
    next_review_date DATE,
    assessment_conclusion TEXT,
    assessed_by VARCHAR(50),
    approved_by VARCHAR(50),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uk_hyperinflationary_country_currency UNIQUE (country_code, currency_code)
);

-- Price index history for restatement calculations
CREATE TABLE IF NOT EXISTS price_index_history (
    index_id SERIAL PRIMARY KEY,
    economy_id INTEGER NOT NULL,
    index_date DATE NOT NULL,
    index_value DECIMAL(12,4) NOT NULL,
    monthly_change_rate DECIMAL(8,4),
    annual_change_rate DECIMAL(8,4),
    data_source VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_price_index_economy FOREIGN KEY (economy_id) REFERENCES hyperinflationary_economies(economy_id),
    CONSTRAINT uk_price_index_date UNIQUE (economy_id, index_date)
);

-- =============================================================================
-- PHASE 5: ENHANCED FX REVALUATION WITH STANDARDS COMPLIANCE
-- =============================================================================

-- Enhance fx_revaluation_details for standards compliance
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='fx_revaluation_details' AND column_name='accounting_standard') THEN
        ALTER TABLE fx_revaluation_details ADD COLUMN accounting_standard VARCHAR(20) DEFAULT 'ASC_830';
        ALTER TABLE fx_revaluation_details ADD COLUMN translation_method VARCHAR(20) DEFAULT 'CURRENT_RATE';
        ALTER TABLE fx_revaluation_details ADD COLUMN monetary_classification VARCHAR(20) DEFAULT 'MONETARY';
        
        -- CTA and OCI components
        ALTER TABLE fx_revaluation_details ADD COLUMN cta_component DECIMAL(15,2) DEFAULT 0.00;
        ALTER TABLE fx_revaluation_details ADD COLUMN oci_component DECIMAL(15,2) DEFAULT 0.00;
        ALTER TABLE fx_revaluation_details ADD COLUMN pnl_component DECIMAL(15,2) DEFAULT 0.00;
        ALTER TABLE fx_revaluation_details ADD COLUMN equity_component DECIMAL(15,2) DEFAULT 0.00;
        
        -- Hedge accounting
        ALTER TABLE fx_revaluation_details ADD COLUMN hedge_designation VARCHAR(20); -- CASH_FLOW, NET_INVESTMENT, FAIR_VALUE
        ALTER TABLE fx_revaluation_details ADD COLUMN hedge_effectiveness DECIMAL(8,4);
        ALTER TABLE fx_revaluation_details ADD COLUMN hedge_instrument_id VARCHAR(50);
        
        -- Additional compliance fields
        ALTER TABLE fx_revaluation_details ADD COLUMN hyperinflationary_adj DECIMAL(15,2) DEFAULT 0.00;
        ALTER TABLE fx_revaluation_details ADD COLUMN remeasurement_gain_loss DECIMAL(15,2) DEFAULT 0.00;
        ALTER TABLE fx_revaluation_details ADD COLUMN translation_gain_loss DECIMAL(15,2) DEFAULT 0.00;
    END IF;
END $$;

-- =============================================================================
-- PHASE 6: HEDGE ACCOUNTING FRAMEWORK
-- =============================================================================

-- Hedge relationships documentation
CREATE TABLE IF NOT EXISTS hedge_relationships (
    hedge_id SERIAL PRIMARY KEY,
    hedge_designation VARCHAR(20) NOT NULL, -- CASH_FLOW, NET_INVESTMENT, FAIR_VALUE
    accounting_standard VARCHAR(20) NOT NULL, -- ASC_815, IFRS_9
    
    -- Hedge relationship details
    hedge_instrument_type VARCHAR(50) NOT NULL, -- FX_FORWARD, FX_OPTION, CROSS_CURRENCY_SWAP
    hedge_instrument_id VARCHAR(50) NOT NULL,
    hedged_item_type VARCHAR(50) NOT NULL, -- FORECASTED_TRANSACTION, NET_INVESTMENT, RECOGNIZED_ASSET_LIABILITY
    hedged_item_id VARCHAR(50) NOT NULL,
    
    -- Risk management
    hedged_risk VARCHAR(50) NOT NULL, -- FX_RISK, INTEREST_RATE_RISK
    hedge_ratio DECIMAL(8,4) DEFAULT 1.0000,
    
    -- Effectiveness testing
    effectiveness_test_method VARCHAR(50), -- DOLLAR_OFFSET, REGRESSION, SCENARIO
    effectiveness_threshold_lower DECIMAL(8,4) DEFAULT 0.8000,
    effectiveness_threshold_upper DECIMAL(8,4) DEFAULT 1.2500,
    
    -- Documentation and dates
    hedge_inception_date DATE NOT NULL,
    hedge_termination_date DATE,
    documentation_date DATE NOT NULL,
    
    -- Status tracking
    hedge_status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, DISCONTINUED, TERMINATED, EXPIRED
    last_effectiveness_test_date DATE,
    next_effectiveness_test_date DATE,
    
    -- Audit trail
    created_by VARCHAR(50) NOT NULL,
    approved_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Hedge effectiveness testing results
CREATE TABLE IF NOT EXISTS hedge_effectiveness_tests (
    test_id SERIAL PRIMARY KEY,
    hedge_id INTEGER NOT NULL,
    test_date DATE NOT NULL,
    test_period_start DATE NOT NULL,
    test_period_end DATE NOT NULL,
    
    -- Test results
    effectiveness_ratio DECIMAL(8,4) NOT NULL,
    dollar_offset_test_result DECIMAL(15,2),
    regression_r_squared DECIMAL(8,6),
    
    -- Pass/fail determination
    test_passed BOOLEAN NOT NULL,
    ineffective_portion DECIMAL(15,2) DEFAULT 0.00,
    
    -- Supporting data
    hedge_instrument_fair_value_change DECIMAL(15,2),
    hedged_item_fair_value_change DECIMAL(15,2),
    excluded_components DECIMAL(15,2) DEFAULT 0.00,
    
    -- Documentation
    test_methodology TEXT,
    test_conclusion TEXT,
    testing_performed_by VARCHAR(50),
    reviewed_by VARCHAR(50),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_hedge_effectiveness_hedge FOREIGN KEY (hedge_id) REFERENCES hedge_relationships(hedge_id)
);

-- =============================================================================
-- PHASE 7: INTERCOMPANY AND CONSOLIDATION FX
-- =============================================================================

-- Intercompany FX eliminations
CREATE TABLE IF NOT EXISTS intercompany_fx_eliminations (
    elimination_id SERIAL PRIMARY KEY,
    consolidation_entity VARCHAR(10) NOT NULL,
    parent_entity VARCHAR(10) NOT NULL,
    subsidiary_entity VARCHAR(10) NOT NULL,
    
    -- Period information
    consolidation_date DATE NOT NULL,
    fiscal_year INTEGER NOT NULL,
    fiscal_period INTEGER NOT NULL,
    
    -- FX information
    parent_functional_currency VARCHAR(3) NOT NULL,
    subsidiary_functional_currency VARCHAR(3) NOT NULL,
    consolidation_currency VARCHAR(3) NOT NULL,
    
    -- Elimination amounts
    intercompany_receivable DECIMAL(15,2) DEFAULT 0.00,
    intercompany_payable DECIMAL(15,2) DEFAULT 0.00,
    fx_difference_elimination DECIMAL(15,2) DEFAULT 0.00,
    
    -- Translation adjustments
    parent_translation_adj DECIMAL(15,2) DEFAULT 0.00,
    subsidiary_translation_adj DECIMAL(15,2) DEFAULT 0.00,
    consolidation_adj DECIMAL(15,2) DEFAULT 0.00,
    
    created_by VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_ic_elimination_parent FOREIGN KEY (parent_entity) REFERENCES companycode(companycodeid),
    CONSTRAINT fk_ic_elimination_subsidiary FOREIGN KEY (subsidiary_entity) REFERENCES companycode(companycodeid)
);

-- =============================================================================
-- PHASE 8: INITIAL DATA SETUP
-- =============================================================================

-- Insert default entity functional currency (US operations)
INSERT INTO entity_functional_currency (
    entity_id, entity_name, functional_currency, effective_date,
    primary_economic_environment, assessment_methodology, assessment_conclusion,
    assessed_by, assessment_date, next_review_date
) VALUES (
    '1000', 'Primary US Entity', 'USD', '2025-01-01',
    'United States - primary operations, sales, and financing in USD',
    'ASC_830', 'USD determined as functional currency based on primary economic environment analysis',
    'SYSTEM_SETUP', '2025-01-01', '2025-12-31'
) ON CONFLICT (entity_id) DO NOTHING;

-- Insert common hyperinflationary economy monitoring
INSERT INTO hyperinflationary_economies (
    country_code, country_name, currency_code, status, status_effective_date,
    cumulative_inflation_rate, price_index_series, assessed_by
) VALUES 
('ARG', 'Argentina', 'ARS', 'HYPERINFLATIONARY', '2025-01-01', 300.0, 'INDEC_CPI', 'SYSTEM_SETUP'),
('TUR', 'Turkey', 'TRY', 'MONITORING', '2025-01-01', 85.0, 'TURKSTAT_CPI', 'SYSTEM_SETUP'),
('VEN', 'Venezuela', 'VES', 'HYPERINFLATIONARY', '2025-01-01', 1500.0, 'BCV_INPC', 'SYSTEM_SETUP')
ON CONFLICT (country_code, currency_code) DO NOTHING;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_functional_currency_entity ON entity_functional_currency(entity_id);
CREATE INDEX IF NOT EXISTS idx_cta_entity_period ON cumulative_translation_adjustment(entity_id, fiscal_year, fiscal_period);
CREATE INDEX IF NOT EXISTS idx_hyperinflation_status ON hyperinflationary_economies(status, currency_code);
CREATE INDEX IF NOT EXISTS idx_hedge_relationships_active ON hedge_relationships(hedge_status, hedge_inception_date);
CREATE INDEX IF NOT EXISTS idx_price_index_date ON price_index_history(economy_id, index_date DESC);

-- Add comments for documentation
COMMENT ON TABLE entity_functional_currency IS 'ASC 830 and IAS 21 functional currency assessment and tracking';
COMMENT ON TABLE cumulative_translation_adjustment IS 'CTA tracking for foreign currency translation adjustments';
COMMENT ON TABLE hyperinflationary_economies IS 'Hyperinflationary economy monitoring per IAS 29';
COMMENT ON TABLE hedge_relationships IS 'Hedge accounting documentation per ASC 815 and IFRS 9';
COMMENT ON COLUMN glaccount.monetary_classification IS 'Monetary vs non-monetary classification for translation';
COMMENT ON COLUMN fx_revaluation_details.cta_component IS 'Component of revaluation going to CTA/OCI';

COMMIT;