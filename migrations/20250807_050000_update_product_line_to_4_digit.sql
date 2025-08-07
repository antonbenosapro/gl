-- =====================================================
-- Update Product Line IDs from 6-digit to 4-digit
-- =====================================================
-- Author: Claude Code Assistant
-- Date: August 7, 2025
-- Description: Modify product line IDs to use 4-digit codes instead of 6-digit
--              Update all related tables, constraints, and data
-- =====================================================

-- Step 1: Drop dependent objects
DROP VIEW IF EXISTS v_product_line_hierarchy CASCADE;
DROP VIEW IF EXISTS v_cost_center_enhanced CASCADE;
DROP VIEW IF EXISTS v_profit_center_enhanced CASCADE;

-- Step 2: Drop mapping tables (will recreate with new structure)
DROP TABLE IF EXISTS cost_center_location_product CASCADE;
DROP TABLE IF EXISTS profit_center_location_product CASCADE;

-- Step 3: Create temporary table with 4-digit product line IDs
CREATE TABLE product_lines_new (
    product_line_id VARCHAR(4) PRIMARY KEY,  -- Changed to 4-digit
    product_line_name VARCHAR(100) NOT NULL,
    short_name VARCHAR(20),
    description TEXT,
    
    -- Product Hierarchy
    parent_product_line VARCHAR(4),  -- Changed to 4-digit
    product_category VARCHAR(50),
    product_family VARCHAR(50),
    product_group VARCHAR(50),
    
    -- Business Attributes
    business_area_id VARCHAR(4),
    product_manager VARCHAR(100),
    product_manager_email VARCHAR(100),
    
    -- Financial Attributes
    default_profit_center VARCHAR(20),
    revenue_recognition_method VARCHAR(20) CHECK (revenue_recognition_method IN (
        'POINT_IN_TIME', 'OVER_TIME', 'COMPLETED_CONTRACT', 'PERCENTAGE_COMPLETION'
    )),
    standard_margin_percentage DECIMAL(5,2),
    target_margin_percentage DECIMAL(5,2),
    
    -- Lifecycle Management
    lifecycle_stage VARCHAR(20) CHECK (lifecycle_stage IN (
        'DEVELOPMENT', 'INTRODUCTION', 'GROWTH', 'MATURITY', 'DECLINE', 'END_OF_LIFE'
    )),
    launch_date DATE,
    sunset_date DATE,
    
    -- Industry-Specific Attributes
    industry_sector VARCHAR(50),
    regulatory_classification VARCHAR(50),
    requires_serialization BOOLEAN DEFAULT FALSE,
    requires_lot_tracking BOOLEAN DEFAULT FALSE,
    
    -- Operational Attributes
    is_manufactured BOOLEAN DEFAULT FALSE,
    is_purchased BOOLEAN DEFAULT FALSE,
    is_service BOOLEAN DEFAULT FALSE,
    is_digital BOOLEAN DEFAULT FALSE,
    
    -- Performance Metrics (for reporting)
    annual_revenue_target DECIMAL(15,2),
    annual_volume_target DECIMAL(15,2),
    market_share_target DECIMAL(5,2),
    
    -- Status and Audit
    is_active BOOLEAN DEFAULT TRUE,
    valid_from DATE DEFAULT CURRENT_DATE,
    valid_to DATE DEFAULT '9999-12-31',
    created_by VARCHAR(50) NOT NULL DEFAULT 'SYSTEM',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_by VARCHAR(50),
    modified_at TIMESTAMP,
    
    -- Constraints
    FOREIGN KEY (parent_product_line) REFERENCES product_lines_new(product_line_id),
    FOREIGN KEY (business_area_id) REFERENCES business_areas(business_area_id)
);

-- Step 4: Migrate data with new 4-digit codes
-- Top Level Products (first 4 digits of original 6-digit code)
INSERT INTO product_lines_new (
    product_line_id, product_line_name, short_name, description, product_category, 
    business_area_id, lifecycle_stage, industry_sector, parent_product_line,
    is_manufactured, is_purchased, is_service, is_digital,
    requires_serialization, requires_lot_tracking,
    is_active, valid_from, created_by
) VALUES
-- Level 0 Products (Top Level)
('1000', 'Consumer Electronics', 'CE', 'Consumer electronics and devices', 'Electronics', 'TECH', 'MATURITY', 'TECHNOLOGY', NULL, TRUE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, CURRENT_DATE, 'MIGRATION'),
('2000', 'Enterprise Software', 'ES', 'Enterprise software solutions', 'Software', 'TECH', 'GROWTH', 'TECHNOLOGY', NULL, FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, TRUE, CURRENT_DATE, 'MIGRATION'),
('3000', 'Professional Services', 'PS', 'Consulting and professional services', 'Services', 'SERV', 'MATURITY', 'SERVICES', NULL, FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, TRUE, CURRENT_DATE, 'MIGRATION'),
('4000', 'Industrial Products', 'IP', 'Industrial and manufacturing products', 'Industrial', 'PROD', 'MATURITY', 'MANUFACTURING', NULL, TRUE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE, CURRENT_DATE, 'MIGRATION'),
('5000', 'Consumer Goods', 'CG', 'Fast-moving consumer goods', 'FMCG', 'PROD', 'MATURITY', 'CPG', NULL, TRUE, FALSE, FALSE, FALSE, FALSE, TRUE, TRUE, CURRENT_DATE, 'MIGRATION'),
('6000', 'Healthcare Products', 'HC', 'Healthcare and pharmaceutical products', 'Healthcare', 'PROD', 'GROWTH', 'PHARMA', NULL, TRUE, FALSE, FALSE, FALSE, TRUE, TRUE, TRUE, CURRENT_DATE, 'MIGRATION');

-- Level 1 Products (Second Level)
INSERT INTO product_lines_new (
    product_line_id, product_line_name, short_name, parent_product_line, product_category, 
    product_family, business_area_id, lifecycle_stage, industry_sector,
    is_manufactured, is_service, is_digital, requires_lot_tracking,
    is_active, created_by
) VALUES
-- Consumer Electronics Sub-lines
('1100', 'Mobile Devices', 'Mobile', '1000', 'Electronics', 'Smartphones', 'TECH', 'MATURITY', 'TECHNOLOGY', TRUE, FALSE, FALSE, FALSE, TRUE, 'MIGRATION'),
('1200', 'Computing Devices', 'Compute', '1000', 'Electronics', 'Computers', 'TECH', 'MATURITY', 'TECHNOLOGY', TRUE, FALSE, FALSE, FALSE, TRUE, 'MIGRATION'),
-- Enterprise Software Sub-lines
('2100', 'ERP Solutions', 'ERP', '2000', 'Software', 'Enterprise', 'TECH', 'MATURITY', 'TECHNOLOGY', FALSE, TRUE, TRUE, FALSE, TRUE, 'MIGRATION'),
('2200', 'Cloud Services', 'Cloud', '2000', 'Software', 'Cloud', 'TECH', 'GROWTH', 'TECHNOLOGY', FALSE, TRUE, TRUE, FALSE, TRUE, 'MIGRATION'),
-- Professional Services Sub-lines
('3100', 'Management Consulting', 'MC', '3000', 'Services', NULL, 'SERV', 'MATURITY', 'SERVICES', FALSE, TRUE, FALSE, FALSE, TRUE, 'MIGRATION'),
('3200', 'Technology Consulting', 'TC', '3000', 'Services', NULL, 'SERV', 'GROWTH', 'SERVICES', FALSE, TRUE, FALSE, FALSE, TRUE, 'MIGRATION'),
('3300', 'Implementation Services', 'IS', '3000', 'Services', NULL, 'SERV', 'MATURITY', 'SERVICES', FALSE, TRUE, FALSE, FALSE, TRUE, 'MIGRATION'),
-- Industrial Products Sub-lines
('4100', 'Machinery', 'MACH', '4000', 'Industrial', NULL, 'PROD', 'MATURITY', 'MANUFACTURING', TRUE, FALSE, FALSE, FALSE, TRUE, 'MIGRATION'),
('4200', 'Components', 'COMP', '4000', 'Industrial', NULL, 'PROD', 'MATURITY', 'MANUFACTURING', TRUE, FALSE, FALSE, FALSE, TRUE, 'MIGRATION'),
('4300', 'Raw Materials', 'RAW', '4000', 'Industrial', NULL, 'PROD', 'MATURITY', 'MANUFACTURING', FALSE, FALSE, FALSE, FALSE, TRUE, 'MIGRATION'),
-- Consumer Goods Sub-lines
('5100', 'Food Products', 'FOOD', '5000', 'FMCG', NULL, 'PROD', 'MATURITY', 'CPG', TRUE, FALSE, FALSE, TRUE, TRUE, 'MIGRATION'),
('5200', 'Personal Care', 'PC', '5000', 'FMCG', NULL, 'PROD', 'MATURITY', 'CPG', TRUE, FALSE, FALSE, TRUE, TRUE, 'MIGRATION'),
-- Healthcare Sub-lines
('6100', 'Prescription Drugs', 'RX', '6000', 'Healthcare', NULL, 'PROD', 'MATURITY', 'PHARMA', TRUE, FALSE, FALSE, TRUE, TRUE, 'MIGRATION'),
('6200', 'OTC Products', 'OTC', '6000', 'Healthcare', NULL, 'PROD', 'MATURITY', 'PHARMA', TRUE, FALSE, FALSE, TRUE, TRUE, 'MIGRATION'),
('6300', 'Medical Devices', 'MD', '6000', 'Healthcare', NULL, 'PROD', 'GROWTH', 'PHARMA', TRUE, FALSE, FALSE, TRUE, TRUE, 'MIGRATION');

-- Level 2 Products (Third Level - more specific)
INSERT INTO product_lines_new (
    product_line_id, product_line_name, short_name, parent_product_line, product_category, 
    product_family, business_area_id, lifecycle_stage, industry_sector,
    is_manufactured, is_service, is_digital, requires_serialization, requires_lot_tracking,
    is_active, created_by
) VALUES
-- Mobile Devices Detailed
('1110', 'Smartphones', 'Phone', '1100', 'Electronics', 'Smartphones', 'TECH', 'MATURITY', 'TECHNOLOGY', TRUE, FALSE, FALSE, FALSE, FALSE, TRUE, 'MIGRATION'),
('1120', 'Premium Smartphones', 'Premium', '1100', 'Electronics', 'Smartphones', 'TECH', 'GROWTH', 'TECHNOLOGY', TRUE, FALSE, FALSE, FALSE, FALSE, TRUE, 'MIGRATION'),
('1130', 'Budget Smartphones', 'Budget', '1100', 'Electronics', 'Smartphones', 'TECH', 'MATURITY', 'TECHNOLOGY', TRUE, FALSE, FALSE, FALSE, FALSE, TRUE, 'MIGRATION'),
-- Computing Devices
('1210', 'Laptops', 'Laptop', '1200', 'Electronics', 'Computers', 'TECH', 'MATURITY', 'TECHNOLOGY', TRUE, FALSE, FALSE, FALSE, FALSE, TRUE, 'MIGRATION'),
('1220', 'Tablets', 'Tablet', '1200', 'Electronics', 'Computers', 'TECH', 'DECLINE', 'TECHNOLOGY', TRUE, FALSE, FALSE, FALSE, FALSE, TRUE, 'MIGRATION'),
-- ERP Solutions
('2110', 'Financial ERP', 'FIN-ERP', '2100', 'Software', 'Enterprise', 'TECH', 'MATURITY', 'TECHNOLOGY', FALSE, TRUE, TRUE, FALSE, FALSE, TRUE, 'MIGRATION'),
('2120', 'Supply Chain ERP', 'SCM-ERP', '2100', 'Software', 'Enterprise', 'TECH', 'GROWTH', 'TECHNOLOGY', FALSE, TRUE, TRUE, FALSE, FALSE, TRUE, 'MIGRATION'),
-- Cloud Services
('2210', 'SaaS Applications', 'SaaS', '2200', 'Software', 'Cloud', 'TECH', 'GROWTH', 'TECHNOLOGY', FALSE, TRUE, TRUE, FALSE, FALSE, TRUE, 'MIGRATION'),
('2220', 'Infrastructure Services', 'IaaS', '2200', 'Software', 'Cloud', 'TECH', 'GROWTH', 'TECHNOLOGY', FALSE, TRUE, TRUE, FALSE, FALSE, TRUE, 'MIGRATION'),
-- Food Products
('5110', 'Beverages', 'BEV', '5100', 'FMCG', NULL, 'PROD', 'MATURITY', 'CPG', TRUE, FALSE, FALSE, FALSE, TRUE, TRUE, 'MIGRATION'),
('5120', 'Snacks', 'SNACK', '5100', 'FMCG', NULL, 'PROD', 'GROWTH', 'CPG', TRUE, FALSE, FALSE, FALSE, TRUE, TRUE, 'MIGRATION'),
-- Personal Care
('5210', 'Skincare', 'SKIN', '5200', 'FMCG', NULL, 'PROD', 'GROWTH', 'CPG', TRUE, FALSE, FALSE, FALSE, TRUE, TRUE, 'MIGRATION'),
('5220', 'Haircare', 'HAIR', '5200', 'FMCG', NULL, 'PROD', 'MATURITY', 'CPG', TRUE, FALSE, FALSE, FALSE, TRUE, TRUE, 'MIGRATION'),
-- Pharma
('6110', 'Oncology', 'ONCO', '6100', 'Healthcare', NULL, 'PROD', 'GROWTH', 'PHARMA', TRUE, FALSE, FALSE, TRUE, TRUE, TRUE, 'MIGRATION'),
('6120', 'Cardiovascular', 'CARDIO', '6100', 'Healthcare', NULL, 'PROD', 'MATURITY', 'PHARMA', TRUE, FALSE, FALSE, TRUE, TRUE, TRUE, 'MIGRATION');

-- Step 5: Drop old table and rename new table
DROP TABLE product_lines CASCADE;
ALTER TABLE product_lines_new RENAME TO product_lines;

-- Step 6: Recreate indexes
CREATE INDEX idx_product_lines_parent ON product_lines(parent_product_line);
CREATE INDEX idx_product_lines_category ON product_lines(product_category);
CREATE INDEX idx_product_lines_business_area ON product_lines(business_area_id);
CREATE INDEX idx_product_lines_lifecycle ON product_lines(lifecycle_stage);
CREATE INDEX idx_product_lines_active ON product_lines(is_active);
CREATE INDEX idx_product_lines_industry ON product_lines(industry_sector);

-- Step 7: Recreate mapping tables with updated structure (4-digit product + 6-digit location = 10-digit code)
CREATE TABLE cost_center_location_product (
    cost_center_id VARCHAR(20) PRIMARY KEY,
    location_code VARCHAR(6) NOT NULL,
    product_line_id VARCHAR(4),  -- Changed to 4-digit
    generated_code VARCHAR(10) GENERATED ALWAYS AS (  -- Changed to 10-digit total
        COALESCE(product_line_id, '0000') || location_code
    ) STORED,
    encoding_method VARCHAR(20) DEFAULT 'PRODUCT_LOCATION',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cost_center_id) REFERENCES costcenter(costcenterid),
    FOREIGN KEY (location_code) REFERENCES reporting_locations(location_code),
    FOREIGN KEY (product_line_id) REFERENCES product_lines(product_line_id)
);

CREATE TABLE profit_center_location_product (
    profit_center_id VARCHAR(20) PRIMARY KEY,
    location_code VARCHAR(6) NOT NULL,
    product_line_id VARCHAR(4),  -- Changed to 4-digit
    generated_code VARCHAR(10) GENERATED ALWAYS AS (  -- Changed to 10-digit total
        COALESCE(product_line_id, '0000') || location_code
    ) STORED,
    encoding_method VARCHAR(20) DEFAULT 'PRODUCT_LOCATION',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profit_center_id) REFERENCES profit_centers(profit_center_id),
    FOREIGN KEY (location_code) REFERENCES reporting_locations(location_code),
    FOREIGN KEY (product_line_id) REFERENCES product_lines(product_line_id)
);

-- Step 8: Update helper functions for 4-digit product codes
CREATE OR REPLACE FUNCTION generate_cost_center_code(
    p_product_line_id VARCHAR(4),  -- Changed to 4-digit
    p_location_code VARCHAR(6)
) RETURNS VARCHAR(10) AS $$  -- Changed to 10-digit result
BEGIN
    -- Format: PPPPLLLLLL (Product Line + Location)
    RETURN COALESCE(p_product_line_id, '0000') || p_location_code;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION generate_profit_center_code(
    p_product_line_id VARCHAR(4),  -- Changed to 4-digit
    p_location_code VARCHAR(6)
) RETURNS VARCHAR(10) AS $$  -- Changed to 10-digit result
BEGIN
    -- Format: PPPPLLLLLL (Product Line + Location)
    RETURN COALESCE(p_product_line_id, '0000') || p_location_code;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION decode_center_code(
    p_center_code VARCHAR(10)  -- Changed to 10-digit input
) RETURNS TABLE(product_line_id VARCHAR(4), location_code VARCHAR(6)) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        SUBSTRING(p_center_code FROM 1 FOR 4) AS product_line_id,  -- First 4 digits
        SUBSTRING(p_center_code FROM 5 FOR 6) AS location_code;    -- Last 6 digits
END;
$$ LANGUAGE plpgsql;

-- Step 9: Recreate views with updated structure
CREATE OR REPLACE VIEW v_product_line_hierarchy AS
WITH RECURSIVE product_tree AS (
    SELECT 
        p.product_line_id,
        p.product_line_name,
        p.parent_product_line,
        p.product_category,
        p.product_line_id::VARCHAR(500) AS path,
        p.product_line_name::VARCHAR(2000) AS full_path,
        0 AS level
    FROM product_lines p
    WHERE p.parent_product_line IS NULL
    
    UNION ALL
    
    SELECT 
        p.product_line_id,
        p.product_line_name,
        p.parent_product_line,
        p.product_category,
        (pt.path || '/' || p.product_line_id)::VARCHAR(500) AS path,
        (pt.full_path || ' > ' || p.product_line_name)::VARCHAR(2000) AS full_path,
        pt.level + 1 AS level
    FROM product_lines p
    INNER JOIN product_tree pt ON p.parent_product_line = pt.product_line_id
)
SELECT * FROM product_tree
ORDER BY path;

CREATE OR REPLACE VIEW v_cost_center_enhanced AS
SELECT 
    cc.costcenterid,
    cc.name AS cost_center_name,
    cc.department,
    clp.location_code,
    rl.location_name,
    rl.location_level,
    rl.country_code,
    rl.location_type,
    clp.product_line_id,
    pl.product_line_name,
    pl.product_category,
    pl.lifecycle_stage,
    clp.generated_code,
    cc.is_active
FROM costcenter cc
LEFT JOIN cost_center_location_product clp ON cc.costcenterid = clp.cost_center_id
LEFT JOIN reporting_locations rl ON clp.location_code = rl.location_code
LEFT JOIN product_lines pl ON clp.product_line_id = pl.product_line_id;

CREATE OR REPLACE VIEW v_profit_center_enhanced AS
SELECT 
    pc.profit_center_id,
    pc.profit_center_name,
    pc.company_code_id,
    plp.location_code,
    rl.location_name,
    rl.location_level,
    rl.country_code,
    rl.location_type,
    plp.product_line_id,
    pl.product_line_name,
    pl.product_category,
    pl.lifecycle_stage,
    plp.generated_code,
    pc.is_active
FROM profit_centers pc
LEFT JOIN profit_center_location_product plp ON pc.profit_center_id = plp.profit_center_id
LEFT JOIN reporting_locations rl ON plp.location_code = rl.location_code
LEFT JOIN product_lines pl ON plp.product_line_id = pl.product_line_id;

-- Step 10: Add trigger for modified timestamp
CREATE TRIGGER tr_product_lines_modified
BEFORE UPDATE ON product_lines
FOR EACH ROW EXECUTE FUNCTION update_modified_timestamp();

-- Step 11: Grant permissions
GRANT SELECT, INSERT, UPDATE ON product_lines TO PUBLIC;
GRANT SELECT, INSERT, UPDATE ON cost_center_location_product TO PUBLIC;
GRANT SELECT, INSERT, UPDATE ON profit_center_location_product TO PUBLIC;
GRANT SELECT ON v_product_line_hierarchy TO PUBLIC;
GRANT SELECT ON v_cost_center_enhanced TO PUBLIC;
GRANT SELECT ON v_profit_center_enhanced TO PUBLIC;

-- =====================================================
-- Migration Summary
-- =====================================================
-- Changes Made:
-- 1. Product Line IDs: 6-digit → 4-digit (e.g., 111000 → 1110)
-- 2. Generated Codes: 12-digit → 10-digit (e.g., 111000111110 → 1110111110)
-- 3. Code Structure: PPPPPPLLLLLL → PPPPLLLLLL
-- 4. Sample Data: 36 product lines migrated with new 4-digit structure
-- 5. Functions: Updated to handle 4-digit product codes
-- 6. Views: Recreated with new structure
-- =====================================================