-- =====================================================
-- Location and Product Line Master Data Implementation (FIXED)
-- =====================================================
-- Author: Claude Code Assistant
-- Date: August 7, 2025
-- Description: Creates reporting locations and product lines master data tables
--              to support enhanced management reporting and organizational structuring
-- =====================================================

-- First, add missing business areas if they don't exist
INSERT INTO business_areas (business_area_id, business_area_name, short_name, business_area_type) 
VALUES 
    ('LA', 'Latin America', 'LATAM', 'GEOGRAPHIC'),
    ('MEA', 'Middle East & Africa', 'MEA', 'GEOGRAPHIC')
ON CONFLICT (business_area_id) DO NOTHING;

-- Drop existing tables if they exist (for clean migration)
DROP TABLE IF EXISTS cost_center_location_product CASCADE;
DROP TABLE IF EXISTS profit_center_location_product CASCADE;
DROP TABLE IF EXISTS reporting_locations CASCADE;
DROP TABLE IF EXISTS product_lines CASCADE;

-- =====================================================
-- 1. CREATE REPORTING LOCATIONS TABLE
-- =====================================================
CREATE TABLE reporting_locations (
    location_code VARCHAR(6) PRIMARY KEY,  -- 6-digit location code
    location_name VARCHAR(100) NOT NULL,
    location_level VARCHAR(20) NOT NULL CHECK (location_level IN (
        'GLOBAL', 'REGION', 'COUNTRY', 'STATE', 'CITY', 'SITE', 'BUILDING', 'FLOOR'
    )),
    parent_location VARCHAR(6),
    
    -- Geographic Information
    country_code VARCHAR(3),
    state_province VARCHAR(50),
    city VARCHAR(50),
    address_line_1 VARCHAR(100),
    address_line_2 VARCHAR(100),
    postal_code VARCHAR(20),
    latitude DECIMAL(10,6),
    longitude DECIMAL(10,6),
    timezone VARCHAR(50),
    
    -- Business Attributes
    business_area_id VARCHAR(4),
    location_type VARCHAR(20) CHECK (location_type IN (
        'HEADQUARTERS', 'OFFICE', 'PLANT', 'WAREHOUSE', 'STORE', 'DC', 'BRANCH', 'OTHER'
    )),
    is_consolidation_unit BOOLEAN DEFAULT FALSE,
    consolidation_currency VARCHAR(3),
    
    -- Operational Attributes
    is_manufacturing BOOLEAN DEFAULT FALSE,
    is_sales BOOLEAN DEFAULT FALSE,
    is_distribution BOOLEAN DEFAULT FALSE,
    is_service BOOLEAN DEFAULT FALSE,
    is_administrative BOOLEAN DEFAULT FALSE,
    
    -- Management Information
    location_manager VARCHAR(100),
    contact_phone VARCHAR(30),
    contact_email VARCHAR(100),
    
    -- Status and Audit
    is_active BOOLEAN DEFAULT TRUE,
    valid_from DATE DEFAULT CURRENT_DATE,
    valid_to DATE DEFAULT '9999-12-31',
    created_by VARCHAR(50) NOT NULL DEFAULT 'SYSTEM',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_by VARCHAR(50),
    modified_at TIMESTAMP,
    
    -- Constraints
    FOREIGN KEY (parent_location) REFERENCES reporting_locations(location_code),
    FOREIGN KEY (business_area_id) REFERENCES business_areas(business_area_id)
);

-- Create indexes for reporting performance
CREATE INDEX idx_reporting_locations_level ON reporting_locations(location_level);
CREATE INDEX idx_reporting_locations_parent ON reporting_locations(parent_location);
CREATE INDEX idx_reporting_locations_business_area ON reporting_locations(business_area_id);
CREATE INDEX idx_reporting_locations_country ON reporting_locations(country_code);
CREATE INDEX idx_reporting_locations_active ON reporting_locations(is_active);
CREATE INDEX idx_reporting_locations_type ON reporting_locations(location_type);

-- =====================================================
-- 2. CREATE PRODUCT LINES TABLE
-- =====================================================
CREATE TABLE product_lines (
    product_line_id VARCHAR(6) PRIMARY KEY,  -- 6-digit product line code
    product_line_name VARCHAR(100) NOT NULL,
    short_name VARCHAR(20),
    description TEXT,
    
    -- Product Hierarchy
    parent_product_line VARCHAR(6),
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
    industry_sector VARCHAR(50),  -- CPG, PHARMA, AUTO, TECH, etc.
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
    FOREIGN KEY (parent_product_line) REFERENCES product_lines(product_line_id),
    FOREIGN KEY (business_area_id) REFERENCES business_areas(business_area_id)
);

-- Create indexes for reporting performance
CREATE INDEX idx_product_lines_parent ON product_lines(parent_product_line);
CREATE INDEX idx_product_lines_category ON product_lines(product_category);
CREATE INDEX idx_product_lines_business_area ON product_lines(business_area_id);
CREATE INDEX idx_product_lines_lifecycle ON product_lines(lifecycle_stage);
CREATE INDEX idx_product_lines_active ON product_lines(is_active);
CREATE INDEX idx_product_lines_industry ON product_lines(industry_sector);

-- =====================================================
-- 3. CREATE LOCATION-PRODUCT MAPPING TABLES
-- =====================================================

-- Cost Center Location-Product Mapping
CREATE TABLE cost_center_location_product (
    cost_center_id VARCHAR(20) PRIMARY KEY,
    location_code VARCHAR(6) NOT NULL,
    product_line_id VARCHAR(6),
    generated_code VARCHAR(12) GENERATED ALWAYS AS (
        COALESCE(product_line_id, '000000') || location_code
    ) STORED,
    encoding_method VARCHAR(20) DEFAULT 'PRODUCT_LOCATION',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cost_center_id) REFERENCES costcenter(costcenterid),
    FOREIGN KEY (location_code) REFERENCES reporting_locations(location_code),
    FOREIGN KEY (product_line_id) REFERENCES product_lines(product_line_id)
);

-- Profit Center Location-Product Mapping
CREATE TABLE profit_center_location_product (
    profit_center_id VARCHAR(20) PRIMARY KEY,
    location_code VARCHAR(6) NOT NULL,
    product_line_id VARCHAR(6),
    generated_code VARCHAR(12) GENERATED ALWAYS AS (
        COALESCE(product_line_id, '000000') || location_code
    ) STORED,
    encoding_method VARCHAR(20) DEFAULT 'PRODUCT_LOCATION',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (profit_center_id) REFERENCES profit_centers(profit_center_id),
    FOREIGN KEY (location_code) REFERENCES reporting_locations(location_code),
    FOREIGN KEY (product_line_id) REFERENCES product_lines(product_line_id)
);

-- =====================================================
-- 4. INSERT SAMPLE LOCATION DATA (Fixed order for FK constraints)
-- =====================================================

-- Global/Regional Locations (Top Level - no parent dependencies)
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, business_area_id, location_type, is_consolidation_unit) VALUES
('000001', 'Global Headquarters', 'GLOBAL', NULL, 'USA', 'CORP', 'HEADQUARTERS', TRUE);

-- Regional Locations (depend on Global)
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, business_area_id, location_type, is_consolidation_unit) VALUES
('100000', 'North America Region', 'REGION', '000001', NULL, 'NA', 'OFFICE', TRUE),
('200000', 'Europe Region', 'REGION', '000001', NULL, 'EU', 'OFFICE', TRUE),
('300000', 'Asia Pacific Region', 'REGION', '000001', NULL, 'APAC', 'OFFICE', TRUE),
('400000', 'Latin America Region', 'REGION', '000001', NULL, 'LA', 'OFFICE', TRUE),
('500000', 'Middle East & Africa Region', 'REGION', '000001', NULL, 'MEA', 'OFFICE', TRUE);

-- Country Locations (USA - depends on Region)
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, state_province, business_area_id, location_type) VALUES
('110000', 'United States', 'COUNTRY', '100000', 'USA', NULL, 'NA', 'OFFICE');

-- State Locations (depends on Country)
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, state_province, business_area_id, location_type) VALUES
('111000', 'USA - East', 'STATE', '110000', 'USA', 'NY', 'NA', 'OFFICE'),
('112000', 'USA - Midwest', 'STATE', '110000', 'USA', 'OH', 'NA', 'PLANT'),
('113000', 'USA - West', 'STATE', '110000', 'USA', 'CA', 'NA', 'DC');

-- City Locations (depends on State)
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, state_province, city, business_area_id, location_type, is_manufacturing, is_distribution) VALUES
('111100', 'New York City', 'CITY', '111000', 'USA', 'NY', 'New York', 'NA', 'OFFICE', FALSE, FALSE),
('112100', 'Ohio Manufacturing', 'CITY', '112000', 'USA', 'OH', 'Cincinnati', 'PROD', 'PLANT', TRUE, FALSE),
('113100', 'California Distribution', 'CITY', '113000', 'USA', 'CA', 'Los Angeles', 'NA', 'DC', FALSE, TRUE);

-- Site Locations (depends on City)
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, state_province, city, business_area_id, location_type, is_manufacturing, is_distribution) VALUES
('111110', 'NYC Headquarters', 'SITE', '111100', 'USA', 'NY', 'New York', 'CORP', 'HEADQUARTERS', FALSE, FALSE),
('112110', 'Cincinnati Plant', 'SITE', '112100', 'USA', 'OH', 'Cincinnati', 'PROD', 'PLANT', TRUE, FALSE),
('113110', 'LA Distribution Center', 'SITE', '113100', 'USA', 'CA', 'Los Angeles', 'NA', 'DC', FALSE, TRUE);

-- Building Locations (depends on Site)
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, state_province, city, business_area_id, location_type) VALUES
('111111', 'NYC HQ - Building A', 'BUILDING', '111110', 'USA', 'NY', 'New York', 'CORP', 'OFFICE'),
('111112', 'NYC HQ - Building B', 'BUILDING', '111110', 'USA', 'NY', 'New York', 'CORP', 'OFFICE');

-- European Locations (hierarchical order)
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, business_area_id, location_type) VALUES
('210000', 'Germany', 'COUNTRY', '200000', 'DEU', 'EU', 'OFFICE'),
('211000', 'Bavaria', 'STATE', '210000', 'DEU', 'EU', 'OFFICE'),
('211100', 'Munich', 'CITY', '211000', 'DEU', 'EU', 'OFFICE'),
('211110', 'Munich Office', 'SITE', '211100', 'DEU', 'EU', 'OFFICE'),
('220000', 'United Kingdom', 'COUNTRY', '200000', 'GBR', 'EU', 'OFFICE'),
('221100', 'London', 'CITY', '220000', 'GBR', 'EU', 'OFFICE'),
('221110', 'London Office', 'SITE', '221100', 'GBR', 'EU', 'OFFICE');

-- Asia Pacific Locations (hierarchical order)
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, business_area_id, location_type, is_manufacturing) VALUES
('310000', 'Japan', 'COUNTRY', '300000', 'JPN', 'APAC', 'OFFICE', FALSE),
('311100', 'Tokyo', 'CITY', '310000', 'JPN', 'APAC', 'OFFICE', FALSE),
('311110', 'Tokyo Office', 'SITE', '311100', 'JPN', 'APAC', 'OFFICE', FALSE),
('320000', 'China', 'COUNTRY', '300000', 'CHN', 'APAC', 'PLANT', TRUE),
('321100', 'Shanghai', 'CITY', '320000', 'CHN', 'APAC', 'PLANT', TRUE),
('321110', 'Shanghai Plant', 'SITE', '321100', 'CHN', 'APAC', 'PLANT', TRUE);

-- =====================================================
-- 5. INSERT SAMPLE PRODUCT LINE DATA (Top-down hierarchy)
-- =====================================================

-- Top Level Product Lines (no parent dependencies)
INSERT INTO product_lines (product_line_id, product_line_name, short_name, description, product_category, business_area_id, lifecycle_stage, industry_sector) VALUES
('100000', 'Consumer Electronics', 'CE', 'Consumer electronics and devices', 'Electronics', 'TECH', 'MATURITY', 'TECHNOLOGY'),
('200000', 'Enterprise Software', 'ES', 'Enterprise software solutions', 'Software', 'TECH', 'GROWTH', 'TECHNOLOGY'),
('300000', 'Professional Services', 'PS', 'Consulting and professional services', 'Services', 'SERV', 'MATURITY', 'SERVICES'),
('400000', 'Industrial Products', 'IP', 'Industrial and manufacturing products', 'Industrial', 'PROD', 'MATURITY', 'MANUFACTURING'),
('500000', 'Consumer Goods', 'CG', 'Fast-moving consumer goods', 'FMCG', 'PROD', 'MATURITY', 'CPG'),
('600000', 'Healthcare Products', 'HC', 'Healthcare and pharmaceutical products', 'Healthcare', 'PROD', 'GROWTH', 'PHARMA');

-- Second Level Product Lines
INSERT INTO product_lines (product_line_id, product_line_name, short_name, parent_product_line, product_category, product_family, business_area_id, lifecycle_stage, industry_sector) VALUES
-- Consumer Electronics
('110000', 'Mobile Devices', 'Mobile', '100000', 'Electronics', 'Smartphones', 'TECH', 'MATURITY', 'TECHNOLOGY'),
('120000', 'Computing Devices', 'Compute', '100000', 'Electronics', 'Computers', 'TECH', 'MATURITY', 'TECHNOLOGY'),
-- Enterprise Software
('210000', 'ERP Solutions', 'ERP', '200000', 'Software', 'Enterprise', 'TECH', 'MATURITY', 'TECHNOLOGY'),
('220000', 'Cloud Services', 'Cloud', '200000', 'Software', 'Cloud', 'TECH', 'GROWTH', 'TECHNOLOGY'),
-- Professional Services
('310000', 'Management Consulting', 'MC', '300000', 'Services', NULL, 'SERV', 'MATURITY', 'SERVICES'),
('320000', 'Technology Consulting', 'TC', '300000', 'Services', NULL, 'SERV', 'GROWTH', 'SERVICES'),
('330000', 'Implementation Services', 'IS', '300000', 'Services', NULL, 'SERV', 'MATURITY', 'SERVICES'),
-- Industrial Products
('410000', 'Machinery', 'MACH', '400000', 'Industrial', NULL, 'PROD', 'MATURITY', 'MANUFACTURING'),
('420000', 'Components', 'COMP', '400000', 'Industrial', NULL, 'PROD', 'MATURITY', 'MANUFACTURING'),
('430000', 'Raw Materials', 'RAW', '400000', 'Industrial', NULL, 'PROD', 'MATURITY', 'MANUFACTURING'),
-- Consumer Goods
('510000', 'Food Products', 'FOOD', '500000', 'FMCG', NULL, 'PROD', 'MATURITY', 'CPG'),
('520000', 'Personal Care', 'PC', '500000', 'FMCG', NULL, 'PROD', 'MATURITY', 'CPG'),
-- Healthcare
('610000', 'Prescription Drugs', 'RX', '600000', 'Healthcare', NULL, 'PROD', 'MATURITY', 'PHARMA'),
('620000', 'OTC Products', 'OTC', '600000', 'Healthcare', NULL, 'PROD', 'MATURITY', 'PHARMA'),
('630000', 'Medical Devices', 'MD', '600000', 'Healthcare', NULL, 'PROD', 'GROWTH', 'PHARMA');

-- Third Level Product Lines
INSERT INTO product_lines (product_line_id, product_line_name, short_name, parent_product_line, product_category, product_family, business_area_id, lifecycle_stage, industry_sector, is_service, is_digital, requires_lot_tracking, requires_serialization, is_manufactured) VALUES
-- Mobile Devices
('111000', 'Smartphones', 'Phone', '110000', 'Electronics', 'Smartphones', 'TECH', 'MATURITY', 'TECHNOLOGY', FALSE, FALSE, FALSE, FALSE, TRUE),
('111100', 'Premium Smartphones', 'Premium', '111000', 'Electronics', 'Smartphones', 'TECH', 'GROWTH', 'TECHNOLOGY', FALSE, FALSE, FALSE, FALSE, TRUE),
('111200', 'Budget Smartphones', 'Budget', '111000', 'Electronics', 'Smartphones', 'TECH', 'MATURITY', 'TECHNOLOGY', FALSE, FALSE, FALSE, FALSE, TRUE),
-- Computing
('121000', 'Laptops', 'Laptop', '120000', 'Electronics', 'Computers', 'TECH', 'MATURITY', 'TECHNOLOGY', FALSE, FALSE, FALSE, FALSE, TRUE),
('122000', 'Tablets', 'Tablet', '120000', 'Electronics', 'Computers', 'TECH', 'DECLINE', 'TECHNOLOGY', FALSE, FALSE, FALSE, FALSE, TRUE),
-- ERP
('211000', 'Financial ERP', 'FIN-ERP', '210000', 'Software', 'Enterprise', 'TECH', 'MATURITY', 'TECHNOLOGY', FALSE, TRUE, FALSE, FALSE, FALSE),
('212000', 'Supply Chain ERP', 'SCM-ERP', '210000', 'Software', 'Enterprise', 'TECH', 'GROWTH', 'TECHNOLOGY', FALSE, TRUE, FALSE, FALSE, FALSE),
-- Cloud
('221000', 'SaaS Applications', 'SaaS', '220000', 'Software', 'Cloud', 'TECH', 'GROWTH', 'TECHNOLOGY', TRUE, TRUE, FALSE, FALSE, FALSE),
('222000', 'Infrastructure Services', 'IaaS', '220000', 'Software', 'Cloud', 'TECH', 'GROWTH', 'TECHNOLOGY', TRUE, TRUE, FALSE, FALSE, FALSE),
-- Food
('511000', 'Beverages', 'BEV', '510000', 'FMCG', NULL, 'PROD', 'MATURITY', 'CPG', FALSE, FALSE, TRUE, FALSE, TRUE),
('512000', 'Snacks', 'SNACK', '510000', 'FMCG', NULL, 'PROD', 'GROWTH', 'CPG', FALSE, FALSE, TRUE, FALSE, TRUE),
-- Personal Care
('521000', 'Skincare', 'SKIN', '520000', 'FMCG', NULL, 'PROD', 'GROWTH', 'CPG', FALSE, FALSE, TRUE, FALSE, TRUE),
('522000', 'Haircare', 'HAIR', '520000', 'FMCG', NULL, 'PROD', 'MATURITY', 'CPG', FALSE, FALSE, TRUE, FALSE, TRUE),
-- Pharma
('611000', 'Oncology', 'ONCO', '610000', 'Healthcare', NULL, 'PROD', 'GROWTH', 'PHARMA', FALSE, FALSE, TRUE, TRUE, TRUE),
('612000', 'Cardiovascular', 'CARDIO', '610000', 'Healthcare', NULL, 'PROD', 'MATURITY', 'PHARMA', FALSE, FALSE, TRUE, TRUE, TRUE);

-- =====================================================
-- 6. CREATE HELPER FUNCTIONS
-- =====================================================

-- Function to generate cost center code from product line and location
CREATE OR REPLACE FUNCTION generate_cost_center_code(
    p_product_line_id VARCHAR(6),
    p_location_code VARCHAR(6)
) RETURNS VARCHAR(12) AS $$
BEGIN
    -- Format: PPPPPPLLLLLL (Product Line + Location)
    RETURN COALESCE(p_product_line_id, '000000') || p_location_code;
END;
$$ LANGUAGE plpgsql;

-- Function to generate profit center code from product line and location
CREATE OR REPLACE FUNCTION generate_profit_center_code(
    p_product_line_id VARCHAR(6),
    p_location_code VARCHAR(6)
) RETURNS VARCHAR(12) AS $$
BEGIN
    -- Format: PPPPPPLLLLLL (Product Line + Location)
    RETURN COALESCE(p_product_line_id, '000000') || p_location_code;
END;
$$ LANGUAGE plpgsql;

-- Function to decode cost/profit center to get product line and location
CREATE OR REPLACE FUNCTION decode_center_code(
    p_center_code VARCHAR(12)
) RETURNS TABLE(product_line_id VARCHAR(6), location_code VARCHAR(6)) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        SUBSTRING(p_center_code FROM 1 FOR 6) AS product_line_id,
        SUBSTRING(p_center_code FROM 7 FOR 6) AS location_code;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- 7. CREATE VIEWS FOR REPORTING
-- =====================================================

-- Location Hierarchy View (Fixed)
CREATE OR REPLACE VIEW v_location_hierarchy AS
WITH RECURSIVE location_tree AS (
    SELECT 
        l.location_code,
        l.location_name,
        l.location_level,
        l.parent_location,
        l.location_code::VARCHAR(500) AS path,
        l.location_name::VARCHAR(2000) AS full_path,
        0 AS level
    FROM reporting_locations l
    WHERE l.parent_location IS NULL
    
    UNION ALL
    
    SELECT 
        l.location_code,
        l.location_name,
        l.location_level,
        l.parent_location,
        (lt.path || '/' || l.location_code)::VARCHAR(500) AS path,
        (lt.full_path || ' > ' || l.location_name)::VARCHAR(2000) AS full_path,
        lt.level + 1 AS level
    FROM reporting_locations l
    INNER JOIN location_tree lt ON l.parent_location = lt.location_code
)
SELECT * FROM location_tree
ORDER BY path;

-- Product Line Hierarchy View (Fixed)
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

-- Cost Center Enhanced View with Location and Product Line (Fixed)
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
    cc.isactive
FROM costcenter cc
LEFT JOIN cost_center_location_product clp ON cc.costcenterid = clp.cost_center_id
LEFT JOIN reporting_locations rl ON clp.location_code = rl.location_code
LEFT JOIN product_lines pl ON clp.product_line_id = pl.product_line_id;

-- Profit Center Enhanced View with Location and Product Line (Fixed)
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

-- =====================================================
-- 8. UPDATE TRIGGERS
-- =====================================================

-- Trigger to update modified timestamp
CREATE OR REPLACE FUNCTION update_modified_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_reporting_locations_modified
BEFORE UPDATE ON reporting_locations
FOR EACH ROW EXECUTE FUNCTION update_modified_timestamp();

CREATE TRIGGER tr_product_lines_modified
BEFORE UPDATE ON product_lines
FOR EACH ROW EXECUTE FUNCTION update_modified_timestamp();

-- =====================================================
-- 9. GRANT PERMISSIONS
-- =====================================================

-- Grant appropriate permissions (adjust as needed)
GRANT SELECT, INSERT, UPDATE ON reporting_locations TO PUBLIC;
GRANT SELECT, INSERT, UPDATE ON product_lines TO PUBLIC;
GRANT SELECT ON v_location_hierarchy TO PUBLIC;
GRANT SELECT ON v_product_line_hierarchy TO PUBLIC;
GRANT SELECT ON v_cost_center_enhanced TO PUBLIC;
GRANT SELECT ON v_profit_center_enhanced TO PUBLIC;

-- =====================================================
-- Migration Summary
-- =====================================================
-- Tables Created:
-- 1. reporting_locations (30 sample locations)
-- 2. product_lines (35 sample product lines)
-- 3. cost_center_location_product (mapping table)
-- 4. profit_center_location_product (mapping table)
--
-- Views Created:
-- 1. v_location_hierarchy (hierarchical location view)
-- 2. v_product_line_hierarchy (hierarchical product line view)
-- 3. v_cost_center_enhanced (cost centers with location/product)
-- 4. v_profit_center_enhanced (profit centers with location/product)
--
-- Functions Created:
-- 1. generate_cost_center_code()
-- 2. generate_profit_center_code()
-- 3. decode_center_code()
-- =====================================================