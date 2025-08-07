-- Foreign Currency Revaluation Tables
-- Creates comprehensive FX revaluation functionality for enterprise GL system
-- Date: August 6, 2025

-- FX Revaluation Configuration Table
CREATE TABLE IF NOT EXISTS fx_revaluation_config (
    id SERIAL PRIMARY KEY,
    company_code VARCHAR(10) NOT NULL,
    ledger_id VARCHAR(10) NOT NULL,
    gl_account VARCHAR(20) NOT NULL,
    account_currency VARCHAR(3) NOT NULL,
    revaluation_method VARCHAR(20) NOT NULL DEFAULT 'PERIOD_END', -- PERIOD_END, DAILY, MONTHLY
    revaluation_account VARCHAR(20), -- GL account for unrealized gains/losses
    translation_method VARCHAR(20) NOT NULL DEFAULT 'CURRENT_RATE', -- CURRENT_RATE, AVERAGE_RATE
    is_balance_sheet_account BOOLEAN NOT NULL DEFAULT true,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(50),
    
    CONSTRAINT fk_fx_revaluation_config_company FOREIGN KEY (company_code) REFERENCES companycode(companycodeid),
    CONSTRAINT fk_fx_revaluation_config_ledger FOREIGN KEY (ledger_id) REFERENCES ledger(ledgerid),
    CONSTRAINT fk_fx_revaluation_config_glaccount FOREIGN KEY (gl_account) REFERENCES glaccount(glaccountid),
    CONSTRAINT uk_fx_revaluation_config UNIQUE (company_code, ledger_id, gl_account)
);

-- FX Revaluation Runs Table
CREATE TABLE IF NOT EXISTS fx_revaluation_runs (
    run_id SERIAL PRIMARY KEY,
    company_code VARCHAR(10) NOT NULL,
    revaluation_date DATE NOT NULL,
    fiscal_year INTEGER NOT NULL,
    fiscal_period INTEGER NOT NULL,
    run_type VARCHAR(20) NOT NULL DEFAULT 'PERIOD_END', -- PERIOD_END, ADHOC, MONTH_END
    base_currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    run_status VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING, RUNNING, COMPLETED, FAILED
    total_accounts_processed INTEGER DEFAULT 0,
    total_revaluations INTEGER DEFAULT 0,
    total_unrealized_gain DECIMAL(15,2) DEFAULT 0.00,
    total_unrealized_loss DECIMAL(15,2) DEFAULT 0.00,
    journal_document_numbers TEXT[], -- Array of created journal document numbers
    error_details TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_by VARCHAR(50) NOT NULL,
    completed_at TIMESTAMP,
    execution_time_seconds INTEGER,
    
    CONSTRAINT fk_fx_revaluation_runs_company FOREIGN KEY (company_code) REFERENCES companycode(companycodeid),
    CONSTRAINT uk_fx_revaluation_run UNIQUE (company_code, revaluation_date, run_type)
);

-- FX Revaluation Details Table
CREATE TABLE IF NOT EXISTS fx_revaluation_details (
    detail_id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL,
    company_code VARCHAR(10) NOT NULL,
    ledger_id VARCHAR(10) NOT NULL,
    gl_account VARCHAR(20) NOT NULL,
    account_currency VARCHAR(3) NOT NULL,
    functional_currency VARCHAR(3) NOT NULL,
    
    -- Balance information
    opening_balance_fc DECIMAL(15,2) NOT NULL, -- Foreign currency balance
    current_balance_fc DECIMAL(15,2) NOT NULL, -- Current foreign currency balance
    opening_balance_func DECIMAL(15,2) NOT NULL, -- Functional currency (historical rate)
    
    -- Exchange rate information  
    historical_exchange_rate DECIMAL(10,6) NOT NULL,
    current_exchange_rate DECIMAL(10,6) NOT NULL,
    rate_difference DECIMAL(10,6) NOT NULL,
    
    -- Revaluation calculations
    current_balance_func_at_current_rate DECIMAL(15,2) NOT NULL, -- FC balance * current rate
    unrealized_gain_loss DECIMAL(15,2) NOT NULL, -- Difference requiring revaluation
    revaluation_required BOOLEAN NOT NULL DEFAULT false,
    
    -- Journal entry details
    journal_document_number VARCHAR(50),
    dr_account VARCHAR(20), -- Debit account for revaluation entry
    cr_account VARCHAR(20), -- Credit account for revaluation entry
    
    -- Metadata
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    
    CONSTRAINT fk_fx_revaluation_details_run FOREIGN KEY (run_id) REFERENCES fx_revaluation_runs(run_id),
    CONSTRAINT fk_fx_revaluation_details_company FOREIGN KEY (company_code) REFERENCES companycode(companycodeid),
    CONSTRAINT fk_fx_revaluation_details_ledger FOREIGN KEY (ledger_id) REFERENCES ledger(ledgerid),
    CONSTRAINT fk_fx_revaluation_details_glaccount FOREIGN KEY (gl_account) REFERENCES glaccount(glaccountid)
);

-- FX Revaluation Journal Template Table
CREATE TABLE IF NOT EXISTS fx_revaluation_journal_template (
    template_id SERIAL PRIMARY KEY,
    company_code VARCHAR(10) NOT NULL,
    ledger_id VARCHAR(10) NOT NULL,
    template_name VARCHAR(100) NOT NULL,
    
    -- Template configuration
    gain_account VARCHAR(20) NOT NULL, -- Account for unrealized gains
    loss_account VARCHAR(20) NOT NULL, -- Account for unrealized losses
    offset_account_pattern VARCHAR(50), -- Pattern for determining offset account
    
    -- Journal entry details
    document_type VARCHAR(10) DEFAULT 'FX',
    reference_prefix VARCHAR(20) DEFAULT 'FXREVAL',
    description_template VARCHAR(200) DEFAULT 'FX Revaluation - {account} {currency} {date}',
    
    -- Posting configuration
    auto_post BOOLEAN NOT NULL DEFAULT false,
    requires_approval BOOLEAN NOT NULL DEFAULT true,
    approval_workflow VARCHAR(50),
    
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(50) NOT NULL,
    
    CONSTRAINT fk_fx_journal_template_company FOREIGN KEY (company_code) REFERENCES companycode(companycodeid),
    CONSTRAINT fk_fx_journal_template_ledger FOREIGN KEY (ledger_id) REFERENCES ledger(ledgerid),
    CONSTRAINT uk_fx_journal_template UNIQUE (company_code, ledger_id, template_name)
);

-- FX Account Balances Historical Table
CREATE TABLE IF NOT EXISTS fx_account_balances_history (
    history_id SERIAL PRIMARY KEY,
    company_code VARCHAR(10) NOT NULL,
    ledger_id VARCHAR(10) NOT NULL,
    gl_account VARCHAR(20) NOT NULL,
    balance_date DATE NOT NULL,
    
    -- Balance tracking
    balance_fc DECIMAL(15,2) NOT NULL, -- Balance in foreign currency
    balance_func DECIMAL(15,2) NOT NULL, -- Balance in functional currency
    exchange_rate DECIMAL(10,6) NOT NULL,
    currency_code VARCHAR(3) NOT NULL,
    
    -- Revaluation tracking
    last_revaluation_date DATE,
    cumulative_unrealized_gl DECIMAL(15,2) DEFAULT 0.00,
    period_revaluation_amount DECIMAL(15,2) DEFAULT 0.00,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_fx_balance_history_company FOREIGN KEY (company_code) REFERENCES companycode(companycodeid),
    CONSTRAINT fk_fx_balance_history_ledger FOREIGN KEY (ledger_id) REFERENCES ledger(ledgerid),
    CONSTRAINT fk_fx_balance_history_glaccount FOREIGN KEY (gl_account) REFERENCES glaccount(glaccountid),
    CONSTRAINT uk_fx_balance_history UNIQUE (company_code, ledger_id, gl_account, balance_date)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_fx_revaluation_config_company_ledger ON fx_revaluation_config(company_code, ledger_id);
CREATE INDEX IF NOT EXISTS idx_fx_revaluation_config_account ON fx_revaluation_config(gl_account);
CREATE INDEX IF NOT EXISTS idx_fx_revaluation_runs_date ON fx_revaluation_runs(revaluation_date DESC);
CREATE INDEX IF NOT EXISTS idx_fx_revaluation_runs_company ON fx_revaluation_runs(company_code);
CREATE INDEX IF NOT EXISTS idx_fx_revaluation_details_run ON fx_revaluation_details(run_id);
CREATE INDEX IF NOT EXISTS idx_fx_revaluation_details_account ON fx_revaluation_details(company_code, ledger_id, gl_account);
CREATE INDEX IF NOT EXISTS idx_fx_journal_template_company_ledger ON fx_revaluation_journal_template(company_code, ledger_id);
CREATE INDEX IF NOT EXISTS idx_fx_balance_history_date ON fx_account_balances_history(company_code, ledger_id, balance_date DESC);

-- Insert default FX revaluation configuration for common accounts
INSERT INTO fx_revaluation_config (
    company_code, ledger_id, gl_account, account_currency, 
    revaluation_method, revaluation_account, is_balance_sheet_account, 
    created_by
) VALUES 
-- USD-based company with EUR transactions
('1000', 'L1', '115001', 'EUR', 'PERIOD_END', '485001', true, 'SYSTEM_SETUP'), -- A/R in EUR
('1000', 'L1', '210001', 'EUR', 'PERIOD_END', '485001', true, 'SYSTEM_SETUP'), -- A/P in EUR
('1000', 'L1', '100002', 'EUR', 'PERIOD_END', '485001', true, 'SYSTEM_SETUP'), -- Cash EUR
-- IFRS Ledger
('1000', '2L', '115001', 'EUR', 'PERIOD_END', '485002', true, 'SYSTEM_SETUP'), -- A/R in EUR - IFRS
('1000', '2L', '210001', 'EUR', 'PERIOD_END', '485002', true, 'SYSTEM_SETUP'), -- A/P in EUR - IFRS
-- GBP accounts
('1000', 'L1', '115002', 'GBP', 'PERIOD_END', '485001', true, 'SYSTEM_SETUP'), -- A/R in GBP
('1000', 'L1', '210002', 'GBP', 'PERIOD_END', '485001', true, 'SYSTEM_SETUP') -- A/P in GBP
ON CONFLICT (company_code, ledger_id, gl_account) DO NOTHING;

-- Create FX Gain/Loss GL Accounts
INSERT INTO glaccount (glaccountid, accountname, accounttype, account_group_code, account_currency, created_by) VALUES
('485001', 'FX Unrealized Gain/Loss - USD Ledger', 'EXPENSES', 'OPEX', 'USD', 'SYSTEM_SETUP'),
('485002', 'FX Unrealized Gain/Loss - IFRS', 'EXPENSES', 'OPEX', 'USD', 'SYSTEM_SETUP'),
('486001', 'FX Realized Gain/Loss', 'EXPENSES', 'OPEX', 'USD', 'SYSTEM_SETUP'),
('100002', 'Cash - EUR Account', 'ASSETS', 'CASH', 'EUR', 'SYSTEM_SETUP'),
('115002', 'Accounts Receivable - GBP', 'ASSETS', 'RECV', 'GBP', 'SYSTEM_SETUP'),
('210002', 'Accounts Payable - GBP', 'LIABILITIES', 'PAYB', 'GBP', 'SYSTEM_SETUP')
ON CONFLICT (glaccountid) DO NOTHING;

-- Insert default journal templates
INSERT INTO fx_revaluation_journal_template (
    company_code, ledger_id, template_name, gain_account, loss_account,
    description_template, auto_post, created_by
) VALUES
('1000', 'L1', 'Standard FX Revaluation', '485001', '485001', 'FX Revaluation {account} {currency} {date}', false, 'SYSTEM_SETUP'),
('1000', '2L', 'IFRS FX Revaluation', '485002', '485002', 'IFRS FX Revaluation {account} {currency} {date}', false, 'SYSTEM_SETUP'),
('1000', '3L', 'Tax FX Revaluation', '485001', '485001', 'Tax FX Revaluation {account} {currency} {date}', false, 'SYSTEM_SETUP'),
('1000', '4L', 'Management FX Revaluation', '485001', '485001', 'Management FX Revaluation {account} {currency} {date}', false, 'SYSTEM_SETUP'),
('1000', 'CL', 'Consolidation FX Revaluation', '485001', '485001', 'Consolidation FX Revaluation {account} {currency} {date}', false, 'SYSTEM_SETUP')
ON CONFLICT (company_code, ledger_id, template_name) DO NOTHING;

-- Add comments for documentation
COMMENT ON TABLE fx_revaluation_config IS 'Configuration for foreign currency revaluation by account and ledger';
COMMENT ON TABLE fx_revaluation_runs IS 'Master table tracking each FX revaluation run execution';
COMMENT ON TABLE fx_revaluation_details IS 'Detailed results of FX revaluation calculations and journal entries';
COMMENT ON TABLE fx_revaluation_journal_template IS 'Templates for generating FX revaluation journal entries';
COMMENT ON TABLE fx_account_balances_history IS 'Historical tracking of account balances and revaluations';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON fx_revaluation_config TO gl_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON fx_revaluation_runs TO gl_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON fx_revaluation_details TO gl_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON fx_revaluation_journal_template TO gl_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON fx_account_balances_history TO gl_user;
GRANT USAGE, SELECT ON SEQUENCE fx_revaluation_config_id_seq TO gl_user;
GRANT USAGE, SELECT ON SEQUENCE fx_revaluation_runs_run_id_seq TO gl_user;
GRANT USAGE, SELECT ON SEQUENCE fx_revaluation_details_detail_id_seq TO gl_user;
GRANT USAGE, SELECT ON SEQUENCE fx_revaluation_journal_template_template_id_seq TO gl_user;
GRANT USAGE, SELECT ON SEQUENCE fx_account_balances_history_history_id_seq TO gl_user;

COMMIT;