-- Migration: Create Business Area Master Data
-- Date: August 6, 2025
-- Purpose: Implement SAP-aligned business area master for segment reporting

-- Create business_areas master table
CREATE TABLE IF NOT EXISTS business_areas (
    -- Primary Key
    business_area_id VARCHAR(4) PRIMARY KEY,
    
    -- Basic Information
    business_area_name VARCHAR(100) NOT NULL,
    short_name VARCHAR(20) NOT NULL,
    description TEXT,
    
    -- Organizational Assignment
    company_code_id VARCHAR(10),
    controlling_area VARCHAR(4) DEFAULT 'C001',
    
    -- Hierarchy and Structure
    parent_business_area VARCHAR(4),
    business_area_group VARCHAR(10),
    hierarchy_level INTEGER DEFAULT 1,
    
    -- Reporting and Analysis
    segment_for_reporting VARCHAR(4),
    consolidation_business_area VARCHAR(4),
    
    -- Financial Control
    currency VARCHAR(3) DEFAULT 'USD',
    budget_responsible VARCHAR(50),
    
    -- Integration Settings
    balance_sheet_preparation BOOLEAN DEFAULT TRUE,
    profit_loss_preparation BOOLEAN DEFAULT TRUE,
    statistical_postings_allowed BOOLEAN DEFAULT TRUE,
    
    -- Consolidation Control
    consolidation_relevant BOOLEAN DEFAULT TRUE,
    elimination_business_area VARCHAR(4),
    
    -- Validity and Control
    valid_from DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_to DATE DEFAULT '9999-12-31',
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Audit Fields
    created_by VARCHAR(50) NOT NULL DEFAULT 'SYSTEM',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_by VARCHAR(50),
    modified_at TIMESTAMP,
    
    -- Constraints
    CONSTRAINT fk_business_area_parent 
        FOREIGN KEY (parent_business_area) REFERENCES business_areas(business_area_id),
    CONSTRAINT chk_ba_valid_dates 
        CHECK (valid_to >= valid_from)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_business_areas_company ON business_areas(company_code_id);
CREATE INDEX IF NOT EXISTS idx_business_areas_active ON business_areas(is_active, valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_business_areas_hierarchy ON business_areas(parent_business_area, hierarchy_level);
CREATE INDEX IF NOT EXISTS idx_business_areas_segment ON business_areas(segment_for_reporting);

-- Insert standard business areas
INSERT INTO business_areas (
    business_area_id, business_area_name, short_name, description,
    company_code_id, controlling_area, budget_responsible, 
    consolidation_relevant, is_active, created_by
) VALUES

-- Core Business Areas
('CORP', 'Corporate', 'CORP', 'Corporate headquarters and shared services',
 '1000', 'C001', 'CFO', TRUE, TRUE, 'SAP_MIGRATION'),

-- Product Lines
('PROD', 'Products', 'PROD', 'Product development and manufacturing',
 '1000', 'C001', 'VP Product', TRUE, TRUE, 'SAP_MIGRATION'),
 
('SERV', 'Services', 'SERV', 'Professional services and consulting',
 '1000', 'C001', 'VP Services', TRUE, TRUE, 'SAP_MIGRATION'),
 
('TECH', 'Technology', 'TECH', 'Technology platforms and solutions',
 '1000', 'C001', 'CTO', TRUE, TRUE, 'SAP_MIGRATION'),

-- Geographic Segments
('NA', 'North America', 'N-AM', 'North American operations',
 '1000', 'C001', 'Regional VP', TRUE, TRUE, 'SAP_MIGRATION'),
 
('EU', 'Europe', 'EURO', 'European operations',
 '1000', 'C001', 'Regional VP', TRUE, TRUE, 'SAP_MIGRATION'),
 
('APAC', 'Asia Pacific', 'APAC', 'Asia Pacific operations',
 '1000', 'C001', 'Regional VP', TRUE, TRUE, 'SAP_MIGRATION'),

-- Functional Areas
('SALE', 'Sales', 'SALE', 'Sales and marketing operations',
 '1000', 'C001', 'VP Sales', TRUE, TRUE, 'SAP_MIGRATION'),
 
('R&D', 'Research & Development', 'R&D', 'Research and development activities',
 '1000', 'C001', 'VP R&D', TRUE, TRUE, 'SAP_MIGRATION'),
 
('SUPP', 'Support', 'SUPP', 'Support functions and shared services',
 '1000', 'C001', 'COO', FALSE, TRUE, 'SAP_MIGRATION');

-- Create business area assignments table
CREATE TABLE IF NOT EXISTS business_area_assignments (
    assignment_id SERIAL PRIMARY KEY,
    
    -- Assignment Details
    business_area_id VARCHAR(4) NOT NULL,
    object_type VARCHAR(10) NOT NULL, -- 'GLACCOUNT', 'CUSTOMER', 'VENDOR', 'PROFITCENTER', etc.
    object_id VARCHAR(50) NOT NULL,
    
    -- Assignment Control
    assignment_type VARCHAR(10) DEFAULT 'MANUAL', -- 'MANUAL', 'AUTO', 'DERIVED'
    assignment_percentage DECIMAL(5,2) DEFAULT 100.00,
    priority INTEGER DEFAULT 100,
    
    -- Validity
    valid_from DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_to DATE DEFAULT '9999-12-31',
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Audit Fields
    created_by VARCHAR(50) DEFAULT 'SYSTEM',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    FOREIGN KEY (business_area_id) REFERENCES business_areas(business_area_id),
    UNIQUE(object_type, object_id, business_area_id, valid_from),
    CHECK (assignment_percentage > 0 AND assignment_percentage <= 100)
);

-- Create indexes for assignments
CREATE INDEX IF NOT EXISTS idx_ba_assignments_ba ON business_area_assignments(business_area_id);
CREATE INDEX IF NOT EXISTS idx_ba_assignments_object ON business_area_assignments(object_type, object_id);
CREATE INDEX IF NOT EXISTS idx_ba_assignments_active ON business_area_assignments(is_active, valid_from, valid_to);

-- Create business area derivation rules table
CREATE TABLE IF NOT EXISTS business_area_derivation_rules (
    rule_id SERIAL PRIMARY KEY,
    
    -- Rule Definition
    rule_name VARCHAR(100) NOT NULL,
    rule_description TEXT,
    priority INTEGER DEFAULT 100,
    
    -- Condition Logic
    source_field VARCHAR(50) NOT NULL, -- 'PROFIT_CENTER', 'COST_CENTER', 'GL_ACCOUNT', etc.
    condition_operator VARCHAR(10) DEFAULT '=', -- '=', 'IN', 'LIKE', 'BETWEEN'
    condition_value TEXT NOT NULL,
    
    -- Derivation Result
    target_business_area VARCHAR(4) NOT NULL,
    percentage DECIMAL(5,2) DEFAULT 100.00,
    
    -- Additional Conditions
    company_code_filter VARCHAR(10),
    document_type_filter VARCHAR(2),
    
    -- Rule Control
    is_active BOOLEAN DEFAULT TRUE,
    effective_from DATE DEFAULT CURRENT_DATE,
    effective_to DATE DEFAULT '9999-12-31',
    
    -- Audit Fields
    created_by VARCHAR(50) DEFAULT 'SYSTEM',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    FOREIGN KEY (target_business_area) REFERENCES business_areas(business_area_id),
    CHECK (percentage > 0 AND percentage <= 100)
);

-- Create indexes for derivation rules
CREATE INDEX IF NOT EXISTS idx_ba_derivation_source ON business_area_derivation_rules(source_field);
CREATE INDEX IF NOT EXISTS idx_ba_derivation_active ON business_area_derivation_rules(is_active, effective_from, effective_to);
CREATE INDEX IF NOT EXISTS idx_ba_derivation_priority ON business_area_derivation_rules(priority);

-- Insert standard derivation rules
INSERT INTO business_area_derivation_rules (
    rule_name, rule_description, source_field, condition_operator, condition_value,
    target_business_area, priority, created_by
) VALUES

-- Profit Center Based Rules
('Sales PC to Sales BA', 'Map sales profit centers to sales business area', 
 'PROFIT_CENTER', 'LIKE', 'PC-SALES%', 'SALE', 10, 'SAP_MIGRATION'),
 
('Production PC to Product BA', 'Map production profit centers to product business area',
 'PROFIT_CENTER', 'LIKE', 'PC-PROD%', 'PROD', 10, 'SAP_MIGRATION'),
 
('IT PC to Support BA', 'Map IT profit center to support business area',
 'PROFIT_CENTER', '=', 'PC-IT', 'SUPP', 10, 'SAP_MIGRATION'),
 
('Finance PC to Corporate BA', 'Map finance profit center to corporate business area',
 'PROFIT_CENTER', '=', 'PC-FIN', 'CORP', 10, 'SAP_MIGRATION'),

-- GL Account Based Rules
('Revenue Accounts to Sales BA', 'Map revenue GL accounts to sales business area',
 'GL_ACCOUNT', 'LIKE', '4%', 'SALE', 20, 'SAP_MIGRATION'),
 
('COGS Accounts to Product BA', 'Map COGS accounts to product business area',
 'GL_ACCOUNT', 'LIKE', '500001', 'PROD', 20, 'SAP_MIGRATION'),
 
('R&D Expenses to R&D BA', 'Map R&D expenses to research business area',
 'GL_ACCOUNT', '=', '500200', 'R&D', 20, 'SAP_MIGRATION'),

-- Cost Center Based Rules  
('Marketing CC to Sales BA', 'Map marketing cost centers to sales business area',
 'COST_CENTER', 'LIKE', 'MKTG%', 'SALE', 30, 'SAP_MIGRATION'),
 
('Admin CC to Corporate BA', 'Map admin cost centers to corporate business area',
 'COST_CENTER', 'LIKE', 'ADMIN%', 'CORP', 30, 'SAP_MIGRATION');

-- Create business area hierarchy view
CREATE OR REPLACE VIEW v_business_area_hierarchy AS
WITH RECURSIVE ba_hierarchy AS (
    -- Root level business areas
    SELECT 
        business_area_id,
        business_area_name,
        parent_business_area,
        hierarchy_level,
        business_area_id AS root_ba,
        CAST(business_area_name AS TEXT) AS hierarchy_path
    FROM business_areas 
    WHERE parent_business_area IS NULL
    
    UNION ALL
    
    -- Child business areas
    SELECT 
        ba.business_area_id,
        ba.business_area_name,
        ba.parent_business_area,
        ba.hierarchy_level,
        bah.root_ba,
        CAST(bah.hierarchy_path || ' > ' || ba.business_area_name AS TEXT)
    FROM business_areas ba
    INNER JOIN ba_hierarchy bah ON ba.parent_business_area = bah.business_area_id
)
SELECT * FROM ba_hierarchy;

-- Create business area summary view
CREATE OR REPLACE VIEW v_business_area_summary AS
SELECT 
    ba.business_area_id,
    ba.business_area_name,
    ba.short_name,
    ba.company_code_id,
    ba.controlling_area,
    ba.budget_responsible,
    ba.consolidation_relevant,
    ba.is_active,
    ba.valid_from,
    ba.valid_to,
    COUNT(baa.assignment_id) as total_assignments,
    COUNT(CASE WHEN baa.object_type = 'GLACCOUNT' THEN 1 END) as gl_account_assignments,
    COUNT(CASE WHEN baa.object_type = 'PROFITCENTER' THEN 1 END) as profit_center_assignments,
    COUNT(badr.rule_id) as derivation_rules
FROM business_areas ba
LEFT JOIN business_area_assignments baa ON ba.business_area_id = baa.business_area_id 
    AND baa.is_active = TRUE
    AND CURRENT_DATE BETWEEN baa.valid_from AND baa.valid_to
LEFT JOIN business_area_derivation_rules badr ON ba.business_area_id = badr.target_business_area
    AND badr.is_active = TRUE
    AND CURRENT_DATE BETWEEN badr.effective_from AND badr.effective_to
GROUP BY ba.business_area_id, ba.business_area_name, ba.short_name, 
         ba.company_code_id, ba.controlling_area, ba.budget_responsible,
         ba.consolidation_relevant, ba.is_active, ba.valid_from, ba.valid_to;

-- Create audit trigger for business_areas
CREATE OR REPLACE FUNCTION update_business_areas_modified()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_by = COALESCE(NEW.modified_by, 'SYSTEM');
    NEW.modified_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_business_areas_modified
    BEFORE UPDATE ON business_areas
    FOR EACH ROW
    EXECUTE FUNCTION update_business_areas_modified();

-- Add business area integration to existing tables
-- Update journalentryline to support business area
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'journalentryline' AND column_name = 'business_area_id'
    ) THEN
        ALTER TABLE journalentryline ADD COLUMN business_area_id VARCHAR(4);
        ALTER TABLE journalentryline ADD CONSTRAINT fk_jel_business_area 
            FOREIGN KEY (business_area_id) REFERENCES business_areas(business_area_id);
    END IF;
END $$;

-- Add business area to glaccount for automatic derivation
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'glaccount' AND column_name = 'default_business_area'
    ) THEN
        ALTER TABLE glaccount ADD COLUMN default_business_area VARCHAR(4);
        ALTER TABLE glaccount ADD CONSTRAINT fk_glaccount_business_area 
            FOREIGN KEY (default_business_area) REFERENCES business_areas(business_area_id);
    END IF;
END $$;

-- Insert sample business area assignments
INSERT INTO business_area_assignments (business_area_id, object_type, object_id, assignment_type, created_by) VALUES
-- Assign revenue accounts to sales business area
('SALE', 'GLACCOUNT', '410001', 'AUTO', 'SAP_MIGRATION'),
('SALE', 'GLACCOUNT', '400002', 'AUTO', 'SAP_MIGRATION'),
('SALE', 'GLACCOUNT', '400003', 'AUTO', 'SAP_MIGRATION'),

-- Assign product accounts to product business area
('PROD', 'GLACCOUNT', '500001', 'AUTO', 'SAP_MIGRATION'),
('PROD', 'GLACCOUNT', '500010', 'AUTO', 'SAP_MIGRATION'),

-- Assign technology accounts to technology business area
('TECH', 'GLACCOUNT', '500070', 'AUTO', 'SAP_MIGRATION'),
('TECH', 'GLACCOUNT', '140100', 'AUTO', 'SAP_MIGRATION'),

-- Assign corporate accounts
('CORP', 'GLACCOUNT', '550000', 'AUTO', 'SAP_MIGRATION'),
('CORP', 'GLACCOUNT', '500101', 'AUTO', 'SAP_MIGRATION'),

-- Assign profit centers to business areas
('SALE', 'PROFITCENTER', 'PC-SALES-US', 'AUTO', 'SAP_MIGRATION'),
('SALE', 'PROFITCENTER', 'PC-SALES-INT', 'AUTO', 'SAP_MIGRATION'),
('SALE', 'PROFITCENTER', 'PC-MKTG', 'AUTO', 'SAP_MIGRATION'),

('PROD', 'PROFITCENTER', 'PC-PROD-MFG', 'AUTO', 'SAP_MIGRATION'),
('PROD', 'PROFITCENTER', 'PC-PROD-QC', 'AUTO', 'SAP_MIGRATION'),

('CORP', 'PROFITCENTER', 'PC-CORP', 'AUTO', 'SAP_MIGRATION'),
('CORP', 'PROFITCENTER', 'PC-FIN', 'AUTO', 'SAP_MIGRATION'),

('SUPP', 'PROFITCENTER', 'PC-IT', 'AUTO', 'SAP_MIGRATION'),
('SUPP', 'PROFITCENTER', 'PC-HR', 'AUTO', 'SAP_MIGRATION');

-- Add table comments
COMMENT ON TABLE business_areas IS 'SAP-aligned business area master for segment reporting';
COMMENT ON TABLE business_area_assignments IS 'Object assignments to business areas for segment reporting';
COMMENT ON TABLE business_area_derivation_rules IS 'Rules for automatic business area derivation';
COMMENT ON VIEW v_business_area_hierarchy IS 'Hierarchical view of business area structure';
COMMENT ON VIEW v_business_area_summary IS 'Summary view with assignment and rule statistics';

-- Field comments
COMMENT ON COLUMN business_areas.consolidation_relevant IS 'Include this business area in consolidation reporting';
COMMENT ON COLUMN business_area_assignments.assignment_percentage IS 'Percentage allocation for split assignments';
COMMENT ON COLUMN business_area_derivation_rules.condition_operator IS '=, IN, LIKE, BETWEEN for condition matching';