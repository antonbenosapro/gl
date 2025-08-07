-- Migration: Create Account Groups Table for SAP-Aligned COA Structure
-- Date: August 5, 2025
-- Purpose: Implement SAP-style account groups for enhanced GL account management

-- Create account_groups table
CREATE TABLE IF NOT EXISTS account_groups (
    -- Primary Key
    group_code VARCHAR(10) PRIMARY KEY,
    
    -- Basic Information
    group_name VARCHAR(100) NOT NULL,
    group_description TEXT,
    
    -- SAP-Aligned Classification
    account_class VARCHAR(20) NOT NULL CHECK (account_class IN ('ASSETS', 'LIABILITIES', 'EQUITY', 'REVENUE', 'EXPENSES', 'STATISTICAL')),
    balance_sheet_type VARCHAR(20) CHECK (balance_sheet_type IN ('ASSETS', 'LIABILITIES', 'EQUITY', 'OFF_BALANCE')),
    pnl_type VARCHAR(20) CHECK (pnl_type IN ('REVENUE', 'EXPENSES', 'NOT_APPLICABLE')),
    
    -- Number Range Control
    number_range_from VARCHAR(10) NOT NULL,
    number_range_to VARCHAR(10) NOT NULL,
    
    -- Account Creation Controls
    require_cost_center BOOLEAN DEFAULT FALSE,
    require_profit_center BOOLEAN DEFAULT FALSE,
    require_business_area BOOLEAN DEFAULT FALSE,
    require_tax_code BOOLEAN DEFAULT FALSE,
    require_trading_partner BOOLEAN DEFAULT FALSE,
    
    -- Field Status Group Assignment
    default_field_status_group VARCHAR(10),
    
    -- Account Behavior Controls
    allow_line_items BOOLEAN DEFAULT TRUE,
    allow_open_items BOOLEAN DEFAULT FALSE,
    reconciliation_account BOOLEAN DEFAULT FALSE,
    planning_level VARCHAR(20) DEFAULT 'ACCOUNT' CHECK (planning_level IN ('ACCOUNT', 'COST_CENTER', 'PROFIT_CENTER')),
    
    -- Integration Settings
    co_posting_required BOOLEAN DEFAULT FALSE,
    sort_key VARCHAR(10),
    
    -- Status and Control
    is_active BOOLEAN DEFAULT TRUE,
    block_manual_postings BOOLEAN DEFAULT FALSE,
    
    -- Audit Fields
    created_by VARCHAR(50) NOT NULL DEFAULT 'SYSTEM',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_by VARCHAR(50),
    modified_at TIMESTAMP,
    
    -- Constraints
    CONSTRAINT ck_number_range CHECK (number_range_from <= number_range_to),
    CONSTRAINT ck_balance_pnl_consistency CHECK (
        (balance_sheet_type IS NOT NULL AND pnl_type = 'NOT_APPLICABLE') OR
        (balance_sheet_type IS NULL AND pnl_type IN ('REVENUE', 'EXPENSES'))
    )
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_account_groups_class ON account_groups(account_class);
CREATE INDEX IF NOT EXISTS idx_account_groups_range ON account_groups(number_range_from, number_range_to);
CREATE INDEX IF NOT EXISTS idx_account_groups_active ON account_groups(is_active);

-- Insert SAP-aligned account groups
INSERT INTO account_groups (
    group_code, group_name, group_description, account_class, balance_sheet_type, pnl_type,
    number_range_from, number_range_to, require_cost_center, require_profit_center,
    allow_line_items, allow_open_items, reconciliation_account, is_active, created_by
) VALUES 
-- ASSETS Groups
('CASH', 'Cash and Cash Equivalents', 'Bank accounts, petty cash, and short-term liquid assets', 'ASSETS', 'ASSETS', 'NOT_APPLICABLE', '100000', '109999', FALSE, FALSE, TRUE, FALSE, FALSE, TRUE, 'SAP_MIGRATION'),
('RECV', 'Accounts Receivable', 'Customer receivables and related accounts', 'ASSETS', 'ASSETS', 'NOT_APPLICABLE', '110000', '119999', FALSE, TRUE, TRUE, TRUE, TRUE, TRUE, 'SAP_MIGRATION'),
('INVT', 'Inventory Assets', 'Raw materials, WIP, and finished goods inventory', 'ASSETS', 'ASSETS', 'NOT_APPLICABLE', '120000', '129999', FALSE, TRUE, TRUE, FALSE, FALSE, TRUE, 'SAP_MIGRATION'),
('PREP', 'Prepaid Expenses', 'Prepaid expenses and other current assets', 'ASSETS', 'ASSETS', 'NOT_APPLICABLE', '130000', '139999', FALSE, TRUE, TRUE, FALSE, FALSE, TRUE, 'SAP_MIGRATION'),
('FXAS', 'Fixed Assets', 'Property, plant, equipment, and depreciation', 'ASSETS', 'ASSETS', 'NOT_APPLICABLE', '140000', '179999', FALSE, TRUE, TRUE, FALSE, FALSE, TRUE, 'SAP_MIGRATION'),
('INVA', 'Investments', 'Long-term investments and securities', 'ASSETS', 'ASSETS', 'NOT_APPLICABLE', '180000', '199999', FALSE, TRUE, TRUE, FALSE, FALSE, TRUE, 'SAP_MIGRATION'),

-- LIABILITIES Groups  
('PAYB', 'Accounts Payable', 'Vendor payables and related accounts', 'LIABILITIES', 'LIABILITIES', 'NOT_APPLICABLE', '200000', '219999', FALSE, TRUE, TRUE, TRUE, TRUE, TRUE, 'SAP_MIGRATION'),
('ACCR', 'Accrued Liabilities', 'Accrued expenses and short-term liabilities', 'LIABILITIES', 'LIABILITIES', 'NOT_APPLICABLE', '220000', '239999', FALSE, TRUE, TRUE, FALSE, FALSE, TRUE, 'SAP_MIGRATION'),
('STDB', 'Short-term Debt', 'Short-term loans and credit facilities', 'LIABILITIES', 'LIABILITIES', 'NOT_APPLICABLE', '240000', '249999', FALSE, TRUE, TRUE, FALSE, FALSE, TRUE, 'SAP_MIGRATION'),
('LTDB', 'Long-term Debt', 'Long-term loans and bonds payable', 'LIABILITIES', 'LIABILITIES', 'NOT_APPLICABLE', '250000', '299999', FALSE, TRUE, TRUE, FALSE, FALSE, TRUE, 'SAP_MIGRATION'),

-- EQUITY Groups
('EQTY', 'Share Capital', 'Share capital and capital contributions', 'EQUITY', 'EQUITY', 'NOT_APPLICABLE', '300000', '319999', FALSE, FALSE, TRUE, FALSE, FALSE, TRUE, 'SAP_MIGRATION'),
('RETE', 'Retained Earnings', 'Retained earnings and profit/loss accounts', 'EQUITY', 'EQUITY', 'NOT_APPLICABLE', '320000', '349999', FALSE, FALSE, TRUE, FALSE, FALSE, TRUE, 'SAP_MIGRATION'),
('OCIE', 'Other Comprehensive Income', 'Translation adjustments and other equity items', 'EQUITY', 'EQUITY', 'NOT_APPLICABLE', '350000', '399999', FALSE, FALSE, TRUE, FALSE, FALSE, TRUE, 'SAP_MIGRATION'),

-- REVENUE Groups
('SALE', 'Sales Revenue', 'Product and service sales revenue', 'REVENUE', NULL, 'REVENUE', '400000', '449999', TRUE, TRUE, TRUE, FALSE, FALSE, TRUE, 'SAP_MIGRATION'),
('OINC', 'Other Income', 'Interest, dividends, and other income', 'REVENUE', NULL, 'REVENUE', '450000', '499999', FALSE, TRUE, TRUE, FALSE, FALSE, TRUE, 'SAP_MIGRATION'),

-- EXPENSE Groups
('COGS', 'Cost of Goods Sold', 'Direct costs of products and services sold', 'EXPENSES', NULL, 'EXPENSES', '500000', '549999', TRUE, TRUE, TRUE, FALSE, FALSE, TRUE, 'SAP_MIGRATION'),
('OPEX', 'Operating Expenses', 'General operating and administrative expenses', 'EXPENSES', NULL, 'EXPENSES', '550000', '649999', TRUE, TRUE, TRUE, FALSE, FALSE, TRUE, 'SAP_MIGRATION'),
('FINX', 'Financial Expenses', 'Interest expense and financial costs', 'EXPENSES', NULL, 'EXPENSES', '650000', '699999', FALSE, TRUE, TRUE, FALSE, FALSE, TRUE, 'SAP_MIGRATION'),

-- STATISTICAL Groups
('STAT', 'Statistical Accounts', 'Statistical and memo accounts for reporting', 'STATISTICAL', 'OFF_BALANCE', 'NOT_APPLICABLE', '900000', '999999', FALSE, FALSE, TRUE, FALSE, FALSE, TRUE, 'SAP_MIGRATION');

-- Create audit trigger for account_groups
CREATE OR REPLACE FUNCTION update_account_groups_modified()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_by = COALESCE(NEW.modified_by, 'SYSTEM');
    NEW.modified_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_account_groups_modified
    BEFORE UPDATE ON account_groups
    FOR EACH ROW
    EXECUTE FUNCTION update_account_groups_modified();

-- Add comments for documentation
COMMENT ON TABLE account_groups IS 'SAP-aligned account groups for GL account classification and control';
COMMENT ON COLUMN account_groups.group_code IS 'Unique account group identifier (4-10 characters)';
COMMENT ON COLUMN account_groups.account_class IS 'High-level account classification following SAP standards';
COMMENT ON COLUMN account_groups.number_range_from IS 'Starting account number for this group';
COMMENT ON COLUMN account_groups.number_range_to IS 'Ending account number for this group';
COMMENT ON COLUMN account_groups.require_cost_center IS 'Mandatory cost center assignment for accounts in this group';
COMMENT ON COLUMN account_groups.default_field_status_group IS 'Default field status group for posting control';
COMMENT ON COLUMN account_groups.reconciliation_account IS 'Indicates if accounts in this group are reconciliation accounts';