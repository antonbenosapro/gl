-- Migration: Create Document Type Master Data
-- Date: August 6, 2025
-- Purpose: Implement SAP-aligned document type configuration for posting control

-- Create document_types master table
CREATE TABLE IF NOT EXISTS document_types (
    -- Primary Key
    document_type VARCHAR(2) PRIMARY KEY,
    
    -- Basic Information
    document_type_name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Document Control
    number_range_object VARCHAR(10) DEFAULT 'JE_DOC',
    number_range_year_dependent BOOLEAN DEFAULT TRUE,
    reversal_document_type VARCHAR(2),
    
    -- Authorization and Control
    authorization_group VARCHAR(10),
    account_types_allowed VARCHAR(20) DEFAULT 'DKSA', -- D=Customer, K=Vendor, S=GL, A=Asset
    
    -- Posting Control
    negative_postings_allowed BOOLEAN DEFAULT TRUE,
    cross_company_postings BOOLEAN DEFAULT FALSE,
    reference_procedure VARCHAR(10) DEFAULT 'NORMAL',
    
    -- Workflow and Processing
    workflow_required BOOLEAN DEFAULT FALSE,
    automatic_workflow BOOLEAN DEFAULT FALSE,
    approval_required BOOLEAN DEFAULT FALSE,
    default_approval_level INTEGER DEFAULT 1,
    
    -- Integration Settings
    cash_management_integration BOOLEAN DEFAULT FALSE,
    fixed_asset_integration BOOLEAN DEFAULT FALSE,
    material_management_integration BOOLEAN DEFAULT FALSE,
    
    -- Field Status Control
    field_status_group VARCHAR(10),
    header_field_control VARCHAR(10) DEFAULT 'STANDARD',
    line_item_field_control VARCHAR(10) DEFAULT 'STANDARD',
    
    -- Currency and Exchange
    foreign_currency_allowed BOOLEAN DEFAULT TRUE,
    exchange_rate_required BOOLEAN DEFAULT FALSE,
    exchange_rate_type VARCHAR(10) DEFAULT 'M', -- M=Average, B=Buying, S=Selling
    
    -- Tax Processing
    tax_calculation_procedure VARCHAR(10),
    input_tax_allowed BOOLEAN DEFAULT TRUE,
    output_tax_allowed BOOLEAN DEFAULT TRUE,
    
    -- Period and Date Control
    posting_period_check BOOLEAN DEFAULT TRUE,
    baseline_date_calculation VARCHAR(10) DEFAULT 'DOC_DATE',
    
    -- Status and Control
    is_active BOOLEAN DEFAULT TRUE,
    is_system_document BOOLEAN DEFAULT FALSE,
    
    -- Audit Fields
    created_by VARCHAR(50) NOT NULL DEFAULT 'SYSTEM',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_by VARCHAR(50),
    modified_at TIMESTAMP,
    
    -- Constraints
    FOREIGN KEY (field_status_group) REFERENCES field_status_groups(group_id),
    FOREIGN KEY (reversal_document_type) REFERENCES document_types(document_type)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_document_types_active ON document_types(is_active);
CREATE INDEX IF NOT EXISTS idx_document_types_workflow ON document_types(workflow_required, approval_required);
CREATE INDEX IF NOT EXISTS idx_document_types_field_status ON document_types(field_status_group);

-- Insert standard SAP-aligned document types
INSERT INTO document_types (
    document_type, document_type_name, description,
    account_types_allowed, field_status_group, workflow_required, approval_required,
    is_active, created_by
) VALUES

-- Standard Journal Entries
('SA', 'General Journal Entry', 'Standard journal entry for general ledger postings',
 'S', 'ASSET01', FALSE, FALSE, TRUE, 'SAP_MIGRATION'),

-- Customer Transactions
('DR', 'Customer Invoice', 'Customer billing and accounts receivable',
 'DS', 'RECV01', FALSE, TRUE, TRUE, 'SAP_MIGRATION'),
 
('DZ', 'Customer Payment', 'Customer payment receipt and cash application',
 'DS', 'CASH01', FALSE, FALSE, TRUE, 'SAP_MIGRATION'),
 
('DG', 'Customer Credit Memo', 'Customer credit memo and adjustments',
 'DS', 'RECV01', TRUE, TRUE, TRUE, 'SAP_MIGRATION'),

-- Vendor Transactions  
('KR', 'Vendor Invoice', 'Vendor invoice and accounts payable',
 'KS', 'PAYB01', FALSE, TRUE, TRUE, 'SAP_MIGRATION'),
 
('KZ', 'Vendor Payment', 'Vendor payment and cash disbursement',
 'KS', 'CASH01', FALSE, TRUE, TRUE, 'SAP_MIGRATION'),
 
('KG', 'Vendor Credit Memo', 'Vendor credit memo and adjustments',
 'KS', 'PAYB01', FALSE, FALSE, TRUE, 'SAP_MIGRATION'),

-- Asset Transactions
('AA', 'Asset Acquisition', 'Fixed asset acquisition and capitalization',
 'AS', 'ASSET01', TRUE, TRUE, TRUE, 'SAP_MIGRATION'),
 
('AB', 'Asset Retirement', 'Fixed asset retirement and disposal',
 'AS', 'ASSET01', TRUE, TRUE, TRUE, 'SAP_MIGRATION'),
 
('AF', 'Asset Depreciation', 'Automatic depreciation posting',
 'S', 'ASSET01', FALSE, FALSE, TRUE, 'SAP_MIGRATION'),

-- Bank and Cash
('BK', 'Bank Statement', 'Bank statement processing and reconciliation',
 'S', 'CASH01', FALSE, FALSE, TRUE, 'SAP_MIGRATION'),
 
('CA', 'Cash Journal', 'Cash receipt and payment journal',
 'S', 'CASH01', FALSE, FALSE, TRUE, 'SAP_MIGRATION'),

-- Period-End and Adjustments
('PJ', 'Period-End Journal', 'Month-end and year-end adjusting entries',
 'S', 'ASSET01', TRUE, TRUE, TRUE, 'SAP_MIGRATION'),
 
('AC', 'Accrual Entry', 'Accrual and deferral postings',
 'S', 'ASSET01', FALSE, TRUE, TRUE, 'SAP_MIGRATION'),
 
('RE', 'Reversal Entry', 'Document reversal and correction',
 'S', 'ASSET01', FALSE, TRUE, TRUE, 'SAP_MIGRATION'),

-- Inventory and Materials
('WA', 'Goods Receipt', 'Inventory goods receipt posting',
 'S', 'ASSET01', FALSE, FALSE, TRUE, 'SAP_MIGRATION'),
 
('WE', 'Goods Issue', 'Inventory goods issue and consumption',
 'S', 'COGS01', FALSE, FALSE, TRUE, 'SAP_MIGRATION'),

-- Intercompany and Consolidation
('IC', 'Intercompany Entry', 'Intercompany transactions and eliminations',
 'S', 'INTER01', TRUE, TRUE, TRUE, 'SAP_MIGRATION'),
 
('CO', 'Consolidation Entry', 'Consolidation adjustments and eliminations',
 'S', 'INTER01', TRUE, TRUE, TRUE, 'SAP_MIGRATION'),

-- Foreign Exchange
('FX', 'FX Revaluation', 'Foreign exchange revaluation postings',
 'S', 'FIN01', TRUE, TRUE, TRUE, 'SAP_MIGRATION'),
 
('FE', 'FX Realized', 'Realized foreign exchange gains/losses',
 'S', 'FIN01', FALSE, FALSE, TRUE, 'SAP_MIGRATION');

-- Create document type number ranges table
CREATE TABLE IF NOT EXISTS document_number_ranges (
    range_id SERIAL PRIMARY KEY,
    
    -- Range Definition
    document_type VARCHAR(2) NOT NULL,
    company_code_id VARCHAR(10) NOT NULL,
    fiscal_year INTEGER,
    
    -- Number Range Control
    range_from BIGINT NOT NULL DEFAULT 1000000000,
    range_to BIGINT NOT NULL DEFAULT 9999999999,
    current_number BIGINT DEFAULT 1000000000,
    
    -- Range Settings
    number_length INTEGER DEFAULT 10,
    alphanumeric BOOLEAN DEFAULT FALSE,
    prefix VARCHAR(10),
    suffix VARCHAR(10),
    
    -- Control Settings
    external_numbering BOOLEAN DEFAULT FALSE,
    interval_size INTEGER DEFAULT 1,
    warning_percentage DECIMAL(5,2) DEFAULT 90.0,
    
    -- Status and Control
    is_active BOOLEAN DEFAULT TRUE,
    range_exhausted BOOLEAN DEFAULT FALSE,
    
    -- Audit Fields
    created_by VARCHAR(50) DEFAULT 'SYSTEM',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP,
    
    -- Constraints
    FOREIGN KEY (document_type) REFERENCES document_types(document_type),
    UNIQUE(document_type, company_code_id, fiscal_year)
);

-- Create indexes for number ranges
CREATE INDEX IF NOT EXISTS idx_doc_number_ranges_type ON document_number_ranges(document_type);
CREATE INDEX IF NOT EXISTS idx_doc_number_ranges_company ON document_number_ranges(company_code_id);
CREATE INDEX IF NOT EXISTS idx_doc_number_ranges_year ON document_number_ranges(fiscal_year);

-- Insert default number ranges for current year
INSERT INTO document_number_ranges (
    document_type, company_code_id, fiscal_year, 
    range_from, range_to, current_number, created_by
) VALUES
-- Standard ranges for company 1000, current year
('SA', '1000', 2025, 1000000000, 1999999999, 1000000001, 'SAP_MIGRATION'),
('DR', '1000', 2025, 2000000000, 2999999999, 2000000001, 'SAP_MIGRATION'),
('DZ', '1000', 2025, 2100000000, 2199999999, 2100000001, 'SAP_MIGRATION'),
('KR', '1000', 2025, 3000000000, 3999999999, 3000000001, 'SAP_MIGRATION'),
('KZ', '1000', 2025, 3100000000, 3199999999, 3100000001, 'SAP_MIGRATION'),
('AA', '1000', 2025, 4000000000, 4099999999, 4000000001, 'SAP_MIGRATION'),
('AB', '1000', 2025, 4100000000, 4199999999, 4100000001, 'SAP_MIGRATION'),
('AF', '1000', 2025, 4200000000, 4299999999, 4200000001, 'SAP_MIGRATION'),
('BK', '1000', 2025, 5000000000, 5099999999, 5000000001, 'SAP_MIGRATION'),
('PJ', '1000', 2025, 6000000000, 6999999999, 6000000001, 'SAP_MIGRATION'),
('IC', '1000', 2025, 7000000000, 7999999999, 7000000001, 'SAP_MIGRATION'),
('FX', '1000', 2025, 8000000000, 8099999999, 8000000001, 'SAP_MIGRATION');

-- Create document type field controls table
CREATE TABLE IF NOT EXISTS document_type_field_controls (
    control_id SERIAL PRIMARY KEY,
    
    -- Document Type Assignment
    document_type VARCHAR(2) NOT NULL,
    field_name VARCHAR(50) NOT NULL,
    
    -- Field Control
    field_status VARCHAR(10) NOT NULL CHECK (field_status IN ('SUP', 'REQ', 'OPT', 'DIS')),
    field_group VARCHAR(20) DEFAULT 'GENERAL',
    
    -- Validation Rules
    validation_rule TEXT,
    default_value TEXT,
    
    -- Conditional Logic
    condition_field VARCHAR(50),
    condition_value TEXT,
    condition_operator VARCHAR(10) DEFAULT '=',
    
    -- Status and Control
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Audit Fields
    created_by VARCHAR(50) DEFAULT 'SYSTEM',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    FOREIGN KEY (document_type) REFERENCES document_types(document_type),
    UNIQUE(document_type, field_name)
);

-- Create view for document type summary
CREATE OR REPLACE VIEW v_document_type_summary AS
SELECT 
    dt.document_type,
    dt.document_type_name,
    dt.description,
    dt.field_status_group,
    dt.workflow_required,
    dt.approval_required,
    dt.is_active,
    COUNT(dnr.range_id) as number_ranges_configured,
    COUNT(dtfc.control_id) as field_controls_defined,
    MAX(dnr.current_number) as highest_document_number
FROM document_types dt
LEFT JOIN document_number_ranges dnr ON dt.document_type = dnr.document_type
LEFT JOIN document_type_field_controls dtfc ON dt.document_type = dtfc.document_type
GROUP BY dt.document_type, dt.document_type_name, dt.description, 
         dt.field_status_group, dt.workflow_required, dt.approval_required, dt.is_active;

-- Create audit trigger for document_types
CREATE OR REPLACE FUNCTION update_document_types_modified()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_by = COALESCE(NEW.modified_by, 'SYSTEM');
    NEW.modified_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_document_types_modified
    BEFORE UPDATE ON document_types
    FOR EACH ROW
    EXECUTE FUNCTION update_document_types_modified();

-- Add document type to existing journal entry tables
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'journalentryheader' AND column_name = 'document_type'
    ) THEN
        ALTER TABLE journalentryheader ADD COLUMN document_type VARCHAR(2) DEFAULT 'SA';
        ALTER TABLE journalentryheader ADD CONSTRAINT fk_jeh_document_type 
            FOREIGN KEY (document_type) REFERENCES document_types(document_type);
    END IF;
END $$;

-- Add table comments
COMMENT ON TABLE document_types IS 'SAP-aligned document type master for posting control';
COMMENT ON TABLE document_number_ranges IS 'Document number range configuration by type and company';
COMMENT ON TABLE document_type_field_controls IS 'Field-level controls for specific document types';
COMMENT ON VIEW v_document_type_summary IS 'Summary view of document type configurations';

-- Field comments
COMMENT ON COLUMN document_types.account_types_allowed IS 'D=Customer, K=Vendor, S=GL Account, A=Asset';
COMMENT ON COLUMN document_types.reference_procedure IS 'NORMAL=Standard, HEADER=From Header, LINE=From Line Item';
COMMENT ON COLUMN document_number_ranges.warning_percentage IS 'Percentage threshold for range exhaustion warning';