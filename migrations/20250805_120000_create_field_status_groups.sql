-- Migration: Create Field Status Groups for SAP-Aligned Posting Control
-- Date: August 5, 2025
-- Purpose: Implement SAP-style field status groups for posting control and validation

-- Create field_status_groups table
CREATE TABLE IF NOT EXISTS field_status_groups (
    -- Primary Key
    group_id VARCHAR(10) PRIMARY KEY,
    
    -- Basic Information
    group_name VARCHAR(100) NOT NULL,
    group_description TEXT,
    
    -- Document Header Field Controls
    reference_field_status VARCHAR(10) DEFAULT 'OPT' CHECK (reference_field_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    document_header_text_status VARCHAR(10) DEFAULT 'OPT' CHECK (document_header_text_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    
    -- Line Item Field Controls
    assignment_field_status VARCHAR(10) DEFAULT 'OPT' CHECK (assignment_field_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    text_field_status VARCHAR(10) DEFAULT 'OPT' CHECK (text_field_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    cost_center_status VARCHAR(10) DEFAULT 'OPT' CHECK (cost_center_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    profit_center_status VARCHAR(10) DEFAULT 'OPT' CHECK (profit_center_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    business_area_status VARCHAR(10) DEFAULT 'OPT' CHECK (business_area_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    
    -- Partner and Intercompany Controls
    trading_partner_status VARCHAR(10) DEFAULT 'SUP' CHECK (trading_partner_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    partner_company_status VARCHAR(10) DEFAULT 'SUP' CHECK (partner_company_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    
    -- Tax and Payment Controls  
    tax_code_status VARCHAR(10) DEFAULT 'OPT' CHECK (tax_code_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    payment_terms_status VARCHAR(10) DEFAULT 'SUP' CHECK (payment_terms_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    baseline_date_status VARCHAR(10) DEFAULT 'SUP' CHECK (baseline_date_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    
    -- Amount and Currency Controls
    amount_in_local_currency_status VARCHAR(10) DEFAULT 'DIS' CHECK (amount_in_local_currency_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    exchange_rate_status VARCHAR(10) DEFAULT 'OPT' CHECK (exchange_rate_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    
    -- Additional Control Fields
    quantity_status VARCHAR(10) DEFAULT 'SUP' CHECK (quantity_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    base_unit_status VARCHAR(10) DEFAULT 'SUP' CHECK (base_unit_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    
    -- House Bank and Payment
    house_bank_status VARCHAR(10) DEFAULT 'SUP' CHECK (house_bank_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    account_id_status VARCHAR(10) DEFAULT 'SUP' CHECK (account_id_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    
    -- Status and Control
    is_active BOOLEAN DEFAULT TRUE,
    allow_negative_postings BOOLEAN DEFAULT TRUE,
    
    -- Audit Fields
    created_by VARCHAR(50) NOT NULL DEFAULT 'SYSTEM',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_by VARCHAR(50),
    modified_at TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_field_status_groups_active ON field_status_groups(is_active);

-- Insert standard SAP-aligned field status groups
INSERT INTO field_status_groups (
    group_id, group_name, group_description,
    reference_field_status, document_header_text_status, assignment_field_status, text_field_status,
    cost_center_status, profit_center_status, business_area_status,
    tax_code_status, is_active, created_by
) VALUES 

-- Standard Asset Account Controls
('ASSET01', 'Standard Asset Accounts', 'Standard field controls for asset accounts',
 'OPT', 'OPT', 'OPT', 'OPT', 'SUP', 'OPT', 'SUP', 'SUP', TRUE, 'SAP_MIGRATION'),

-- Receivables Account Controls  
('RECV01', 'Receivables Account Controls', 'Field controls for customer receivables',
 'REQ', 'OPT', 'REQ', 'OPT', 'SUP', 'REQ', 'OPT', 'SUP', TRUE, 'SAP_MIGRATION'),

-- Payables Account Controls
('PAYB01', 'Payables Account Controls', 'Field controls for vendor payables', 
 'REQ', 'OPT', 'REQ', 'OPT', 'SUP', 'REQ', 'OPT', 'SUP', TRUE, 'SAP_MIGRATION'),

-- Revenue Account Controls
('REV01', 'Revenue Account Controls', 'Field controls for revenue accounts',
 'OPT', 'OPT', 'OPT', 'OPT', 'REQ', 'REQ', 'REQ', 'REQ', TRUE, 'SAP_MIGRATION'),

-- Expense Account Controls  
('EXP01', 'Expense Account Controls', 'Field controls for expense accounts',
 'OPT', 'OPT', 'REQ', 'REQ', 'REQ', 'REQ', 'REQ', 'SUP', TRUE, 'SAP_MIGRATION'),

-- Cost of Goods Sold Controls
('COGS01', 'COGS Account Controls', 'Field controls for cost of goods sold accounts',
 'OPT', 'OPT', 'REQ', 'REQ', 'REQ', 'REQ', 'REQ', 'SUP', TRUE, 'SAP_MIGRATION'),

-- Financial Accounts (Interest, etc.)
('FIN01', 'Financial Account Controls', 'Field controls for financial income/expense accounts',
 'OPT', 'OPT', 'OPT', 'OPT', 'SUP', 'REQ', 'OPT', 'SUP', TRUE, 'SAP_MIGRATION'),

-- Intercompany Account Controls
('INTER01', 'Intercompany Controls', 'Field controls for intercompany accounts',
 'REQ', 'REQ', 'REQ', 'REQ', 'OPT', 'REQ', 'REQ', 'SUP', TRUE, 'SAP_MIGRATION'),

-- Statistical Account Controls
('STAT01', 'Statistical Account Controls', 'Field controls for statistical accounts',
 'OPT', 'OPT', 'OPT', 'REQ', 'OPT', 'OPT', 'OPT', 'SUP', TRUE, 'SAP_MIGRATION'),

-- Cash Account Controls
('CASH01', 'Cash Account Controls', 'Field controls for cash and bank accounts',
 'OPT', 'OPT', 'OPT', 'OPT', 'SUP', 'SUP', 'SUP', 'SUP', TRUE, 'SAP_MIGRATION');

-- Create field_status_groups_detail table for extended field controls
CREATE TABLE IF NOT EXISTS field_status_groups_detail (
    detail_id SERIAL PRIMARY KEY,
    group_id VARCHAR(10) NOT NULL,
    field_name VARCHAR(50) NOT NULL,
    field_status VARCHAR(10) NOT NULL CHECK (field_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    field_description TEXT,
    validation_rule TEXT,
    
    -- Audit Fields
    created_by VARCHAR(50) DEFAULT 'SYSTEM',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    FOREIGN KEY (group_id) REFERENCES field_status_groups(group_id),
    UNIQUE(group_id, field_name)
);

-- Insert detailed field controls for specific scenarios
INSERT INTO field_status_groups_detail (group_id, field_name, field_status, field_description) VALUES
-- Revenue account detailed controls
('REV01', 'CUSTOMER_NUMBER', 'OPT', 'Customer number for revenue tracking'),
('REV01', 'SALES_ORDER', 'OPT', 'Sales order reference'),
('REV01', 'PRODUCT_CODE', 'OPT', 'Product or service code'),

-- Expense account detailed controls  
('EXP01', 'VENDOR_NUMBER', 'OPT', 'Vendor number for expense tracking'),
('EXP01', 'PURCHASE_ORDER', 'OPT', 'Purchase order reference'),
('EXP01', 'APPROVAL_CODE', 'OPT', 'Expense approval reference'),

-- Intercompany detailed controls
('INTER01', 'PARTNER_COMPANY', 'REQ', 'Partner company code mandatory'),
('INTER01', 'ELIMINATION_FLAG', 'REQ', 'Consolidation elimination indicator'),

-- Asset account detailed controls
('ASSET01', 'ASSET_NUMBER', 'OPT', 'Fixed asset number'),
('ASSET01', 'DEPRECIATION_KEY', 'SUP', 'Depreciation calculation key');

-- Create view for field status group summary
CREATE OR REPLACE VIEW v_field_status_summary AS
SELECT 
    fsg.group_id,
    fsg.group_name,
    fsg.group_description,
    fsg.cost_center_status,
    fsg.profit_center_status,
    fsg.business_area_status,
    fsg.tax_code_status,
    fsg.trading_partner_status,
    COUNT(fsgd.detail_id) as additional_field_controls,
    fsg.is_active
FROM field_status_groups fsg
LEFT JOIN field_status_groups_detail fsgd ON fsg.group_id = fsgd.group_id
GROUP BY fsg.group_id, fsg.group_name, fsg.group_description, 
         fsg.cost_center_status, fsg.profit_center_status, fsg.business_area_status,
         fsg.tax_code_status, fsg.trading_partner_status, fsg.is_active;

-- Update account_groups with default field status groups
UPDATE account_groups SET default_field_status_group = 
    CASE 
        WHEN group_code = 'CASH' THEN 'CASH01'
        WHEN group_code = 'RECV' THEN 'RECV01'  
        WHEN group_code IN ('INVT', 'PREP', 'FXAS', 'INVA') THEN 'ASSET01'
        WHEN group_code = 'PAYB' THEN 'PAYB01'
        WHEN group_code IN ('ACCR', 'STDB', 'LTDB') THEN 'ASSET01'
        WHEN group_code IN ('EQTY', 'RETE', 'OCIE') THEN 'ASSET01'
        WHEN group_code = 'SALE' THEN 'REV01'
        WHEN group_code = 'OINC' THEN 'FIN01'
        WHEN group_code = 'COGS' THEN 'COGS01'
        WHEN group_code = 'OPEX' THEN 'EXP01'
        WHEN group_code = 'FINX' THEN 'FIN01'
        WHEN group_code = 'STAT' THEN 'STAT01'
        ELSE 'ASSET01'
    END
WHERE default_field_status_group IS NULL;

-- Update glaccount table with appropriate field status groups
UPDATE glaccount SET field_status_group = 
    CASE 
        WHEN account_group_code IS NOT NULL THEN 
            (SELECT default_field_status_group FROM account_groups WHERE group_code = account_group_code)
        ELSE 'ASSET01'
    END
WHERE field_status_group IS NULL;

-- Create audit trigger for field_status_groups
CREATE OR REPLACE FUNCTION update_field_status_groups_modified()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_by = COALESCE(NEW.modified_by, 'SYSTEM');
    NEW.modified_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_field_status_groups_modified
    BEFORE UPDATE ON field_status_groups
    FOR EACH ROW
    EXECUTE FUNCTION update_field_status_groups_modified();

-- Add table comments
COMMENT ON TABLE field_status_groups IS 'SAP-style field status groups for posting control';
COMMENT ON TABLE field_status_groups_detail IS 'Detailed field controls for specific business scenarios';
COMMENT ON VIEW v_field_status_summary IS 'Summary view of field status group configurations';

-- Field status codes explanation
COMMENT ON COLUMN field_status_groups.cost_center_status IS 'SUP=Suppressed, REQ=Required, OPT=Optional, DIS=Display Only';
COMMENT ON COLUMN field_status_groups.profit_center_status IS 'SUP=Suppressed, REQ=Required, OPT=Optional, DIS=Display Only';
COMMENT ON COLUMN field_status_groups.business_area_status IS 'SUP=Suppressed, REQ=Required, OPT=Optional, DIS=Display Only';
COMMENT ON COLUMN field_status_groups.tax_code_status IS 'SUP=Suppressed, REQ=Required, OPT=Optional, DIS=Display Only';