-- Migration: Create Profit Center Master Data
-- Date: August 6, 2025
-- Purpose: Implement SAP-aligned profit center master for profitability analysis

-- Create profit_centers master table
CREATE TABLE IF NOT EXISTS profit_centers (
    -- Primary Key
    profit_center_id VARCHAR(20) PRIMARY KEY,
    
    -- Basic Information
    profit_center_name VARCHAR(100) NOT NULL,
    short_name VARCHAR(20) NOT NULL,
    description TEXT,
    
    -- Organizational Assignment
    company_code_id VARCHAR(10) NOT NULL,
    controlling_area VARCHAR(4) DEFAULT 'C001',
    business_area VARCHAR(4),
    
    -- Hierarchy and Structure
    parent_profit_center VARCHAR(20),
    profit_center_group VARCHAR(10),
    hierarchy_level INTEGER DEFAULT 1,
    
    -- Responsibility and Management
    person_responsible VARCHAR(50),
    cost_center VARCHAR(10),
    segment VARCHAR(10),
    
    -- Validity and Control
    valid_from DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_to DATE DEFAULT '9999-12-31',
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Currency and Reporting
    local_currency VARCHAR(3) DEFAULT 'USD',
    profit_center_currency VARCHAR(3) DEFAULT 'USD',
    
    -- Planning and Budgeting
    planning_enabled BOOLEAN DEFAULT TRUE,
    budget_profile VARCHAR(10),
    
    -- Integration Settings
    automatic_account_assignment BOOLEAN DEFAULT FALSE,
    derivation_rule VARCHAR(20),
    
    -- Audit Fields
    created_by VARCHAR(50) NOT NULL DEFAULT 'SYSTEM',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_by VARCHAR(50),
    modified_at TIMESTAMP,
    
    -- Constraints
    CONSTRAINT fk_profit_center_parent 
        FOREIGN KEY (parent_profit_center) REFERENCES profit_centers(profit_center_id),
    CONSTRAINT chk_valid_dates 
        CHECK (valid_to >= valid_from)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_profit_centers_company ON profit_centers(company_code_id);
CREATE INDEX IF NOT EXISTS idx_profit_centers_active ON profit_centers(is_active, valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_profit_centers_hierarchy ON profit_centers(parent_profit_center, hierarchy_level);
CREATE INDEX IF NOT EXISTS idx_profit_centers_group ON profit_centers(profit_center_group);

-- Insert standard profit centers
INSERT INTO profit_centers (
    profit_center_id, profit_center_name, short_name, description,
    company_code_id, controlling_area, person_responsible, is_active, created_by
) VALUES
-- Corporate Level
('PC-CORP', 'Corporate Headquarters', 'CORP', 'Corporate headquarters and shared services', 
 '1000', 'C001', 'CEO', TRUE, 'SAP_MIGRATION'),

-- Sales and Marketing
('PC-SALES-US', 'Sales - United States', 'SALES-US', 'US domestic sales operations', 
 '1000', 'C001', 'VP Sales', TRUE, 'SAP_MIGRATION'),
 
('PC-SALES-INT', 'Sales - International', 'SALES-INT', 'International sales operations', 
 '1000', 'C001', 'VP Sales', TRUE, 'SAP_MIGRATION'),
 
('PC-MKTG', 'Marketing', 'MKTG', 'Marketing and brand management', 
 '1000', 'C001', 'CMO', TRUE, 'SAP_MIGRATION'),

-- Operations
('PC-PROD-MFG', 'Production - Manufacturing', 'PROD-MFG', 'Manufacturing operations', 
 '1000', 'C001', 'Plant Manager', TRUE, 'SAP_MIGRATION'),
 
('PC-PROD-QC', 'Production - Quality Control', 'PROD-QC', 'Quality control and assurance', 
 '1000', 'C001', 'QC Manager', TRUE, 'SAP_MIGRATION'),

-- Support Functions
('PC-IT', 'Information Technology', 'IT', 'IT systems and support', 
 '1000', 'C001', 'CTO', TRUE, 'SAP_MIGRATION'),
 
('PC-HR', 'Human Resources', 'HR', 'Human resources and payroll', 
 '1000', 'C001', 'CHRO', TRUE, 'SAP_MIGRATION'),
 
('PC-FIN', 'Finance', 'FIN', 'Finance and accounting operations', 
 '1000', 'C001', 'CFO', TRUE, 'SAP_MIGRATION'),

-- Regional Centers
('PC-EAST', 'Eastern Region', 'EAST', 'Eastern regional operations', 
 '1000', 'C001', 'Regional Manager', TRUE, 'SAP_MIGRATION'),
 
('PC-WEST', 'Western Region', 'WEST', 'Western regional operations', 
 '1000', 'C001', 'Regional Manager', TRUE, 'SAP_MIGRATION'),
 
('PC-CENTRAL', 'Central Region', 'CENTRAL', 'Central regional operations', 
 '1000', 'C001', 'Regional Manager', TRUE, 'SAP_MIGRATION');

-- Create profit center assignments table
CREATE TABLE IF NOT EXISTS profit_center_assignments (
    assignment_id SERIAL PRIMARY KEY,
    
    -- Assignment Details
    profit_center_id VARCHAR(20) NOT NULL,
    object_type VARCHAR(10) NOT NULL, -- 'GLACCOUNT', 'COSTCENTER', 'EMPLOYEE', etc.
    object_id VARCHAR(50) NOT NULL,
    
    -- Assignment Control
    assignment_type VARCHAR(10) DEFAULT 'MANUAL', -- 'MANUAL', 'AUTO', 'DERIVED'
    priority INTEGER DEFAULT 100,
    
    -- Validity
    valid_from DATE NOT NULL DEFAULT CURRENT_DATE,
    valid_to DATE DEFAULT '9999-12-31',
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Audit Fields
    created_by VARCHAR(50) DEFAULT 'SYSTEM',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    FOREIGN KEY (profit_center_id) REFERENCES profit_centers(profit_center_id),
    UNIQUE(object_type, object_id, valid_from)
);

-- Create indexes for assignments
CREATE INDEX IF NOT EXISTS idx_pc_assignments_pc ON profit_center_assignments(profit_center_id);
CREATE INDEX IF NOT EXISTS idx_pc_assignments_object ON profit_center_assignments(object_type, object_id);
CREATE INDEX IF NOT EXISTS idx_pc_assignments_active ON profit_center_assignments(is_active, valid_from, valid_to);

-- Create profit center hierarchy view
CREATE OR REPLACE VIEW v_profit_center_hierarchy AS
WITH RECURSIVE pc_hierarchy AS (
    -- Root level profit centers
    SELECT 
        profit_center_id,
        profit_center_name,
        parent_profit_center,
        hierarchy_level,
        profit_center_id AS root_pc,
        CAST(profit_center_name AS TEXT) AS hierarchy_path
    FROM profit_centers 
    WHERE parent_profit_center IS NULL
    
    UNION ALL
    
    -- Child profit centers
    SELECT 
        pc.profit_center_id,
        pc.profit_center_name,
        pc.parent_profit_center,
        pc.hierarchy_level,
        pch.root_pc,
        CAST(pch.hierarchy_path || ' > ' || pc.profit_center_name AS TEXT)
    FROM profit_centers pc
    INNER JOIN pc_hierarchy pch ON pc.parent_profit_center = pch.profit_center_id
)
SELECT * FROM pc_hierarchy;

-- Create profit center summary view
CREATE OR REPLACE VIEW v_profit_center_summary AS
SELECT 
    pc.profit_center_id,
    pc.profit_center_name,
    pc.short_name,
    pc.company_code_id,
    pc.controlling_area,
    pc.person_responsible,
    pc.is_active,
    pc.valid_from,
    pc.valid_to,
    COUNT(pca.assignment_id) as total_assignments,
    COUNT(CASE WHEN pca.object_type = 'GLACCOUNT' THEN 1 END) as gl_account_assignments,
    COUNT(CASE WHEN pca.object_type = 'COSTCENTER' THEN 1 END) as cost_center_assignments
FROM profit_centers pc
LEFT JOIN profit_center_assignments pca ON pc.profit_center_id = pca.profit_center_id 
    AND pca.is_active = TRUE
    AND CURRENT_DATE BETWEEN pca.valid_from AND pca.valid_to
GROUP BY pc.profit_center_id, pc.profit_center_name, pc.short_name, 
         pc.company_code_id, pc.controlling_area, pc.person_responsible,
         pc.is_active, pc.valid_from, pc.valid_to;

-- Create audit trigger for profit_centers
CREATE OR REPLACE FUNCTION update_profit_centers_modified()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_by = COALESCE(NEW.modified_by, 'SYSTEM');
    NEW.modified_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_profit_centers_modified
    BEFORE UPDATE ON profit_centers
    FOR EACH ROW
    EXECUTE FUNCTION update_profit_centers_modified();

-- Add profit center integration to existing tables
-- Update journalentryline to support profit center
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'journalentryline' AND column_name = 'profit_center_id'
    ) THEN
        ALTER TABLE journalentryline ADD COLUMN profit_center_id VARCHAR(20);
        ALTER TABLE journalentryline ADD CONSTRAINT fk_jel_profit_center 
            FOREIGN KEY (profit_center_id) REFERENCES profit_centers(profit_center_id);
    END IF;
END $$;

-- Add profit center to glaccount for automatic derivation
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'glaccount' AND column_name = 'default_profit_center'
    ) THEN
        ALTER TABLE glaccount ADD COLUMN default_profit_center VARCHAR(20);
        ALTER TABLE glaccount ADD CONSTRAINT fk_glaccount_profit_center 
            FOREIGN KEY (default_profit_center) REFERENCES profit_centers(profit_center_id);
    END IF;
END $$;

-- Insert sample profit center assignments
INSERT INTO profit_center_assignments (profit_center_id, object_type, object_id, assignment_type, created_by) VALUES
-- Assign sales accounts to sales profit centers
('PC-SALES-US', 'GLACCOUNT', '410001', 'AUTO', 'SAP_MIGRATION'),
('PC-SALES-US', 'GLACCOUNT', '400002', 'AUTO', 'SAP_MIGRATION'),
('PC-SALES-INT', 'GLACCOUNT', '400003', 'AUTO', 'SAP_MIGRATION'),

-- Assign cost accounts to operational profit centers
('PC-PROD-MFG', 'GLACCOUNT', '500001', 'AUTO', 'SAP_MIGRATION'),
('PC-PROD-MFG', 'GLACCOUNT', '500002', 'AUTO', 'SAP_MIGRATION'),
('PC-PROD-QC', 'GLACCOUNT', '500010', 'AUTO', 'SAP_MIGRATION'),

-- Assign support function accounts
('PC-IT', 'GLACCOUNT', '500070', 'AUTO', 'SAP_MIGRATION'),
('PC-HR', 'GLACCOUNT', '500101', 'AUTO', 'SAP_MIGRATION'),
('PC-FIN', 'GLACCOUNT', '550000', 'AUTO', 'SAP_MIGRATION'),

-- Assign marketing accounts
('PC-MKTG', 'GLACCOUNT', '500301', 'AUTO', 'SAP_MIGRATION'),
('PC-MKTG', 'GLACCOUNT', '400000', 'AUTO', 'SAP_MIGRATION');

-- Add table comments
COMMENT ON TABLE profit_centers IS 'SAP-aligned profit center master data for profitability analysis';
COMMENT ON TABLE profit_center_assignments IS 'Object assignments to profit centers';
COMMENT ON VIEW v_profit_center_hierarchy IS 'Hierarchical view of profit center structure';
COMMENT ON VIEW v_profit_center_summary IS 'Summary view with assignment statistics';

-- Field comments
COMMENT ON COLUMN profit_centers.controlling_area IS 'Controlling area for profit center accounting';
COMMENT ON COLUMN profit_centers.hierarchy_level IS 'Level in profit center hierarchy (1=top)';
COMMENT ON COLUMN profit_center_assignments.object_type IS 'Type of object assigned (GLACCOUNT, COSTCENTER, etc.)';
COMMENT ON COLUMN profit_center_assignments.assignment_type IS 'MANUAL=user assigned, AUTO=rule based, DERIVED=calculated';