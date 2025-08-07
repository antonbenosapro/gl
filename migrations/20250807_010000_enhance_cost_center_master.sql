-- Migration: Enhance Cost Center Master Data
-- Date: August 7, 2025
-- Purpose: Enhance cost center table with SAP-aligned fields and Phase 2 integration

-- Add new columns to existing cost center table
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS short_name VARCHAR(20);
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS cost_center_category VARCHAR(10) DEFAULT 'STANDARD';
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS controlling_area VARCHAR(4) DEFAULT 'C001';
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS person_responsible VARCHAR(50);
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS department VARCHAR(50);
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS cost_center_group VARCHAR(10);

-- Hierarchy and Structure
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS parent_cost_center VARCHAR(10);
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS hierarchy_level INTEGER DEFAULT 1;

-- Planning and Control
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS planning_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS budget_profile VARCHAR(10);
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS cost_center_type VARCHAR(10) DEFAULT 'ACTUAL';

-- Integration with Phase 2
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS default_profit_center VARCHAR(20);
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS default_business_area VARCHAR(4);

-- Activity and Status
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS activity_type VARCHAR(20) DEFAULT 'OPERATIONAL';
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS statistical_key_figure VARCHAR(10);
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS capacity_category VARCHAR(10);

-- Validity and Control
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS valid_from DATE DEFAULT CURRENT_DATE;
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS valid_to DATE DEFAULT '9999-12-31';
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS locked_for_posting BOOLEAN DEFAULT FALSE;
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS locked_for_planning BOOLEAN DEFAULT FALSE;

-- Currency and Reporting
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS currency VARCHAR(3) DEFAULT 'USD';
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS alternative_cost_center VARCHAR(10);

-- Audit Fields
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS created_by VARCHAR(50) DEFAULT 'SYSTEM';
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS modified_by VARCHAR(50);
ALTER TABLE costcenter ADD COLUMN IF NOT EXISTS modified_at TIMESTAMP;

-- Add foreign key constraints for Phase 2 integration
DO $$ 
BEGIN
    -- Add profit center FK if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_costcenter_profit_center'
    ) THEN
        ALTER TABLE costcenter ADD CONSTRAINT fk_costcenter_profit_center 
            FOREIGN KEY (default_profit_center) REFERENCES profit_centers(profit_center_id);
    END IF;
    
    -- Add business area FK if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_costcenter_business_area'
    ) THEN
        ALTER TABLE costcenter ADD CONSTRAINT fk_costcenter_business_area 
            FOREIGN KEY (default_business_area) REFERENCES business_areas(business_area_id);
    END IF;
    
    -- Add parent cost center FK if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_costcenter_parent'
    ) THEN
        ALTER TABLE costcenter ADD CONSTRAINT fk_costcenter_parent 
            FOREIGN KEY (parent_cost_center) REFERENCES costcenter(costcenterid);
    END IF;
END $$;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_costcenter_company ON costcenter(companycodeid);
CREATE INDEX IF NOT EXISTS idx_costcenter_active ON costcenter(is_active, valid_from, valid_to);
CREATE INDEX IF NOT EXISTS idx_costcenter_hierarchy ON costcenter(parent_cost_center, hierarchy_level);
CREATE INDEX IF NOT EXISTS idx_costcenter_responsible ON costcenter(person_responsible);
CREATE INDEX IF NOT EXISTS idx_costcenter_category ON costcenter(cost_center_category);
CREATE INDEX IF NOT EXISTS idx_costcenter_profit_center ON costcenter(default_profit_center);
CREATE INDEX IF NOT EXISTS idx_costcenter_business_area ON costcenter(default_business_area);

-- Update existing cost centers with enhanced data
UPDATE costcenter SET 
    short_name = COALESCE(short_name, LEFT(name, 20)),
    description = COALESCE(description, name || ' - Cost Center'),
    cost_center_category = COALESCE(cost_center_category, 'STANDARD'),
    controlling_area = COALESCE(controlling_area, 'C001'),
    person_responsible = COALESCE(person_responsible, 'Manager'),
    department = COALESCE(department, 'General'),
    planning_enabled = COALESCE(planning_enabled, TRUE),
    cost_center_type = COALESCE(cost_center_type, 'ACTUAL'),
    activity_type = COALESCE(activity_type, 'OPERATIONAL'),
    valid_from = COALESCE(valid_from, CURRENT_DATE),
    valid_to = COALESCE(valid_to, '9999-12-31'::date),
    is_active = COALESCE(is_active, TRUE),
    currency = COALESCE(currency, 'USD'),
    created_by = COALESCE(created_by, 'MIGRATION'),
    created_at = COALESCE(created_at, CURRENT_TIMESTAMP)
WHERE short_name IS NULL OR description IS NULL;

-- Insert additional standard cost centers if needed
INSERT INTO costcenter (
    costcenterid, companycodeid, name, short_name, description,
    cost_center_category, controlling_area, person_responsible, department,
    planning_enabled, cost_center_type, activity_type, is_active, created_by
) VALUES
-- Administrative Cost Centers
('ADMIN01', '1000', 'Administration', 'ADMIN01', 'General administration and overhead',
 'ADMIN', 'C001', 'Admin Manager', 'Administration', TRUE, 'ACTUAL', 'SUPPORT', TRUE, 'SAP_MIGRATION'),

('HR01', '1000', 'Human Resources', 'HR01', 'Human resources and payroll',
 'ADMIN', 'C001', 'HR Manager', 'Human Resources', TRUE, 'ACTUAL', 'SUPPORT', TRUE, 'SAP_MIGRATION'),

('FIN01', '1000', 'Finance Department', 'FIN01', 'Finance and accounting',
 'ADMIN', 'C001', 'Finance Manager', 'Finance', TRUE, 'ACTUAL', 'SUPPORT', TRUE, 'SAP_MIGRATION'),

-- Operational Cost Centers
('SALES01', '1000', 'Sales Department', 'SALES01', 'Sales and marketing activities',
 'REVENUE', 'C001', 'Sales Manager', 'Sales', TRUE, 'ACTUAL', 'REVENUE', TRUE, 'SAP_MIGRATION'),

('PROD01', '1000', 'Production Floor', 'PROD01', 'Manufacturing and production',
 'PRODUCTION', 'C001', 'Production Manager', 'Manufacturing', TRUE, 'ACTUAL', 'PRODUCTION', TRUE, 'SAP_MIGRATION'),

('QC01', '1000', 'Quality Control', 'QC01', 'Quality assurance and control',
 'PRODUCTION', 'C001', 'QC Manager', 'Quality', TRUE, 'ACTUAL', 'QUALITY', TRUE, 'SAP_MIGRATION'),

-- Service Cost Centers
('IT01', '1000', 'Information Technology', 'IT01', 'IT infrastructure and support',
 'SERVICE', 'C001', 'IT Manager', 'Information Technology', TRUE, 'ACTUAL', 'SUPPORT', TRUE, 'SAP_MIGRATION'),

('MAINT01', '1000', 'Maintenance', 'MAINT01', 'Equipment maintenance and repair',
 'SERVICE', 'C001', 'Maintenance Manager', 'Maintenance', TRUE, 'ACTUAL', 'MAINTENANCE', TRUE, 'SAP_MIGRATION'),

-- Research and Development
('RD01', '1000', 'Research & Development', 'RD01', 'Product research and development',
 'DEVELOPMENT', 'C001', 'R&D Manager', 'Research & Development', TRUE, 'ACTUAL', 'DEVELOPMENT', TRUE, 'SAP_MIGRATION')

ON CONFLICT (costcenterid) DO NOTHING;

-- Create cost center assignments table
CREATE TABLE IF NOT EXISTS cost_center_assignments (
    assignment_id SERIAL PRIMARY KEY,
    
    -- Assignment Details
    cost_center_id VARCHAR(10) NOT NULL,
    object_type VARCHAR(10) NOT NULL, -- 'EMPLOYEE', 'ASSET', 'GLACCOUNT', etc.
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
    FOREIGN KEY (cost_center_id) REFERENCES costcenter(costcenterid),
    UNIQUE(object_type, object_id, cost_center_id, valid_from),
    CHECK (assignment_percentage > 0 AND assignment_percentage <= 100)
);

-- Create indexes for assignments
CREATE INDEX IF NOT EXISTS idx_cc_assignments_cc ON cost_center_assignments(cost_center_id);
CREATE INDEX IF NOT EXISTS idx_cc_assignments_object ON cost_center_assignments(object_type, object_id);
CREATE INDEX IF NOT EXISTS idx_cc_assignments_active ON cost_center_assignments(is_active, valid_from, valid_to);

-- Create cost center hierarchy view
CREATE OR REPLACE VIEW v_cost_center_hierarchy AS
WITH RECURSIVE cc_hierarchy AS (
    -- Root level cost centers
    SELECT 
        costcenterid,
        name,
        parent_cost_center,
        hierarchy_level,
        costcenterid AS root_cc,
        CAST(name AS TEXT) AS hierarchy_path
    FROM costcenter 
    WHERE parent_cost_center IS NULL
    
    UNION ALL
    
    -- Child cost centers
    SELECT 
        cc.costcenterid,
        cc.name,
        cc.parent_cost_center,
        cc.hierarchy_level,
        cch.root_cc,
        CAST(cch.hierarchy_path || ' > ' || cc.name AS TEXT)
    FROM costcenter cc
    INNER JOIN cc_hierarchy cch ON cc.parent_cost_center = cch.costcenterid
)
SELECT * FROM cc_hierarchy;

-- Create cost center summary view
CREATE OR REPLACE VIEW v_cost_center_summary AS
SELECT 
    cc.costcenterid,
    cc.name,
    cc.short_name,
    cc.companycodeid,
    cc.cost_center_category,
    cc.person_responsible,
    cc.department,
    cc.default_profit_center,
    cc.default_business_area,
    cc.is_active,
    cc.valid_from,
    cc.valid_to,
    COUNT(cca.assignment_id) as total_assignments,
    COUNT(CASE WHEN cca.object_type = 'EMPLOYEE' THEN 1 END) as employee_assignments,
    COUNT(CASE WHEN cca.object_type = 'ASSET' THEN 1 END) as asset_assignments
FROM costcenter cc
LEFT JOIN cost_center_assignments cca ON cc.costcenterid = cca.cost_center_id 
    AND cca.is_active = TRUE
    AND CURRENT_DATE BETWEEN cca.valid_from AND cca.valid_to
GROUP BY cc.costcenterid, cc.name, cc.short_name, 
         cc.companycodeid, cc.cost_center_category, cc.person_responsible, cc.department,
         cc.default_profit_center, cc.default_business_area,
         cc.is_active, cc.valid_from, cc.valid_to;

-- Create audit trigger for costcenter
CREATE OR REPLACE FUNCTION update_costcenter_modified()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_by = COALESCE(NEW.modified_by, 'SYSTEM');
    NEW.modified_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_costcenter_modified
    BEFORE UPDATE ON costcenter
    FOR EACH ROW
    EXECUTE FUNCTION update_costcenter_modified();

-- Add sample assignments
INSERT INTO cost_center_assignments (cost_center_id, object_type, object_id, assignment_type, created_by) VALUES
-- Assign GL accounts to cost centers
('ADMIN01', 'GLACCOUNT', '500101', 'AUTO', 'SAP_MIGRATION'),
('HR01', 'GLACCOUNT', '500102', 'AUTO', 'SAP_MIGRATION'),
('FIN01', 'GLACCOUNT', '550000', 'AUTO', 'SAP_MIGRATION'),
('SALES01', 'GLACCOUNT', '500301', 'AUTO', 'SAP_MIGRATION'),
('PROD01', 'GLACCOUNT', '500001', 'AUTO', 'SAP_MIGRATION'),
('QC01', 'GLACCOUNT', '500010', 'AUTO', 'SAP_MIGRATION'),
('IT01', 'GLACCOUNT', '500070', 'AUTO', 'SAP_MIGRATION'),
('RD01', 'GLACCOUNT', '500200', 'AUTO', 'SAP_MIGRATION')
ON CONFLICT DO NOTHING;

-- Assign cost centers to profit centers for integration
UPDATE costcenter SET 
    default_profit_center = CASE 
        WHEN costcenterid IN ('ADMIN01', 'FIN01') THEN 'PC-CORP'
        WHEN costcenterid IN ('SALES01') THEN 'PC-SALES-US' 
        WHEN costcenterid IN ('PROD01', 'QC01') THEN 'PC-PROD-MFG'
        WHEN costcenterid IN ('IT01') THEN 'PC-IT'
        WHEN costcenterid IN ('HR01') THEN 'PC-HR'
        WHEN costcenterid IN ('RD01') THEN 'PC-CORP'
        ELSE NULL
    END,
    default_business_area = CASE 
        WHEN costcenterid IN ('ADMIN01', 'FIN01') THEN 'CORP'
        WHEN costcenterid IN ('SALES01') THEN 'SALE' 
        WHEN costcenterid IN ('PROD01', 'QC01') THEN 'PROD'
        WHEN costcenterid IN ('IT01', 'HR01') THEN 'SUPP'
        WHEN costcenterid IN ('RD01') THEN 'R&D'
        ELSE NULL
    END
WHERE default_profit_center IS NULL AND default_business_area IS NULL;

-- Add table and view comments
COMMENT ON TABLE costcenter IS 'Enhanced cost center master data with SAP alignment and Phase 2 integration';
COMMENT ON TABLE cost_center_assignments IS 'Object assignments to cost centers for cost allocation';
COMMENT ON VIEW v_cost_center_hierarchy IS 'Hierarchical view of cost center structure';
COMMENT ON VIEW v_cost_center_summary IS 'Summary view with assignment statistics and Phase 2 integration';

-- Field comments
COMMENT ON COLUMN costcenter.cost_center_category IS 'STANDARD, ADMIN, REVENUE, PRODUCTION, SERVICE, DEVELOPMENT';
COMMENT ON COLUMN costcenter.cost_center_type IS 'ACTUAL, PLAN, BUDGET, STATISTICAL';
COMMENT ON COLUMN costcenter.activity_type IS 'OPERATIONAL, SUPPORT, REVENUE, PRODUCTION, QUALITY, MAINTENANCE, DEVELOPMENT';
COMMENT ON COLUMN cost_center_assignments.assignment_percentage IS 'Percentage allocation for split assignments';
COMMENT ON COLUMN cost_center_assignments.object_type IS 'EMPLOYEE, ASSET, GLACCOUNT, etc.';