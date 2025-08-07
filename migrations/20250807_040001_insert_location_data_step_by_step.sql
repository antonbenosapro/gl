-- =====================================================
-- Location Data Insert - Step by Step (Hierarchical Order)
-- =====================================================

-- Step 1: Global Level
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, business_area_id, location_type, is_consolidation_unit) VALUES
('000001', 'Global Headquarters', 'GLOBAL', NULL, 'USA', 'CORP', 'HEADQUARTERS', TRUE);

-- Step 2: Regional Level  
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, business_area_id, location_type, is_consolidation_unit) VALUES
('100000', 'North America Region', 'REGION', '000001', 'NA', 'OFFICE', TRUE),
('200000', 'Europe Region', 'REGION', '000001', 'EU', 'OFFICE', TRUE),
('300000', 'Asia Pacific Region', 'REGION', '000001', 'APAC', 'OFFICE', TRUE),
('400000', 'Latin America Region', 'REGION', '000001', 'LA', 'OFFICE', TRUE),
('500000', 'Middle East & Africa Region', 'REGION', '000001', 'MEA', 'OFFICE', TRUE);

-- Step 3: Country Level
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, business_area_id, location_type) VALUES
('110000', 'United States', 'COUNTRY', '100000', 'USA', 'NA', 'OFFICE'),
('210000', 'Germany', 'COUNTRY', '200000', 'DEU', 'EU', 'OFFICE'),
('220000', 'United Kingdom', 'COUNTRY', '200000', 'GBR', 'EU', 'OFFICE'),
('310000', 'Japan', 'COUNTRY', '300000', 'JPN', 'APAC', 'OFFICE'),
('320000', 'China', 'COUNTRY', '300000', 'CHN', 'APAC', 'OFFICE');

-- Step 4: State Level  
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, state_province, business_area_id, location_type) VALUES
('111000', 'USA - East', 'STATE', '110000', 'USA', 'NY', 'NA', 'OFFICE'),
('112000', 'USA - Midwest', 'STATE', '110000', 'USA', 'OH', 'NA', 'PLANT'),
('113000', 'USA - West', 'STATE', '110000', 'USA', 'CA', 'NA', 'DC'),
('211000', 'Bavaria', 'STATE', '210000', 'DEU', 'Bavaria', 'EU', 'OFFICE');

-- Step 5: City Level
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, state_province, city, business_area_id, location_type) VALUES
('111100', 'New York City', 'CITY', '111000', 'USA', 'NY', 'New York', 'NA', 'OFFICE'),
('112100', 'Ohio Manufacturing', 'CITY', '112000', 'USA', 'OH', 'Cincinnati', 'PROD', 'PLANT'),
('113100', 'California Distribution', 'CITY', '113000', 'USA', 'CA', 'Los Angeles', 'NA', 'DC'),
('211100', 'Munich', 'CITY', '211000', 'DEU', 'Bavaria', 'EU', 'OFFICE'),
('221100', 'London', 'CITY', '220000', 'GBR', NULL, 'EU', 'OFFICE'),
('311100', 'Tokyo', 'CITY', '310000', 'JPN', NULL, 'APAC', 'OFFICE'),
('321100', 'Shanghai', 'CITY', '320000', 'CHN', NULL, 'APAC', 'PLANT');

-- Step 6: Site Level
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, state_province, city, business_area_id, location_type, is_manufacturing, is_distribution) VALUES
('111110', 'NYC Headquarters', 'SITE', '111100', 'USA', 'NY', 'New York', 'CORP', 'HEADQUARTERS', FALSE, FALSE),
('112110', 'Cincinnati Plant', 'SITE', '112100', 'USA', 'OH', 'Cincinnati', 'PROD', 'PLANT', TRUE, FALSE),
('113110', 'LA Distribution Center', 'SITE', '113100', 'USA', 'CA', 'Los Angeles', 'NA', 'DC', FALSE, TRUE),
('211110', 'Munich Office', 'SITE', '211100', 'DEU', 'Bavaria', 'EU', 'OFFICE', FALSE, FALSE),
('221110', 'London Office', 'SITE', '221100', 'GBR', NULL, 'EU', 'OFFICE', FALSE, FALSE),
('311110', 'Tokyo Office', 'SITE', '311100', 'JPN', NULL, 'APAC', 'OFFICE', FALSE, FALSE),
('321110', 'Shanghai Plant', 'SITE', '321100', 'CHN', NULL, 'APAC', 'PLANT', TRUE, FALSE);

-- Step 7: Building Level
INSERT INTO reporting_locations (location_code, location_name, location_level, parent_location, country_code, state_province, city, business_area_id, location_type) VALUES
('111111', 'NYC HQ - Building A', 'BUILDING', '111110', 'USA', 'NY', 'New York', 'CORP', 'OFFICE'),
('111112', 'NYC HQ - Building B', 'BUILDING', '111110', 'USA', 'NY', 'New York', 'CORP', 'OFFICE');

-- Insert Product Lines (hierarchical)
-- Top Level
INSERT INTO product_lines (product_line_id, product_line_name, short_name, description, product_category, business_area_id, lifecycle_stage, industry_sector) VALUES
('100000', 'Consumer Electronics', 'CE', 'Consumer electronics and devices', 'Electronics', 'TECH', 'MATURITY', 'TECHNOLOGY'),
('200000', 'Enterprise Software', 'ES', 'Enterprise software solutions', 'Software', 'TECH', 'GROWTH', 'TECHNOLOGY'),
('300000', 'Professional Services', 'PS', 'Consulting and professional services', 'Services', 'SERV', 'MATURITY', 'SERVICES'),
('400000', 'Industrial Products', 'IP', 'Industrial and manufacturing products', 'Industrial', 'PROD', 'MATURITY', 'MANUFACTURING'),
('500000', 'Consumer Goods', 'CG', 'Fast-moving consumer goods', 'FMCG', 'PROD', 'MATURITY', 'CPG'),
('600000', 'Healthcare Products', 'HC', 'Healthcare and pharmaceutical products', 'Healthcare', 'PROD', 'GROWTH', 'PHARMA');

-- Second Level
INSERT INTO product_lines (product_line_id, product_line_name, short_name, parent_product_line, product_category, product_family, business_area_id, lifecycle_stage, industry_sector) VALUES
('110000', 'Mobile Devices', 'Mobile', '100000', 'Electronics', 'Smartphones', 'TECH', 'MATURITY', 'TECHNOLOGY'),
('120000', 'Computing Devices', 'Compute', '100000', 'Electronics', 'Computers', 'TECH', 'MATURITY', 'TECHNOLOGY'),
('210000', 'ERP Solutions', 'ERP', '200000', 'Software', 'Enterprise', 'TECH', 'MATURITY', 'TECHNOLOGY'),
('220000', 'Cloud Services', 'Cloud', '200000', 'Software', 'Cloud', 'TECH', 'GROWTH', 'TECHNOLOGY'),
('310000', 'Management Consulting', 'MC', '300000', 'Services', NULL, 'SERV', 'MATURITY', 'SERVICES'),
('320000', 'Technology Consulting', 'TC', '300000', 'Services', NULL, 'SERV', 'GROWTH', 'SERVICES'),
('330000', 'Implementation Services', 'IS', '300000', 'Services', NULL, 'SERV', 'MATURITY', 'SERVICES'),
('410000', 'Machinery', 'MACH', '400000', 'Industrial', NULL, 'PROD', 'MATURITY', 'MANUFACTURING'),
('420000', 'Components', 'COMP', '400000', 'Industrial', NULL, 'PROD', 'MATURITY', 'MANUFACTURING'),
('430000', 'Raw Materials', 'RAW', '400000', 'Industrial', NULL, 'PROD', 'MATURITY', 'MANUFACTURING'),
('510000', 'Food Products', 'FOOD', '500000', 'FMCG', NULL, 'PROD', 'MATURITY', 'CPG'),
('520000', 'Personal Care', 'PC', '500000', 'FMCG', NULL, 'PROD', 'MATURITY', 'CPG'),
('610000', 'Prescription Drugs', 'RX', '600000', 'Healthcare', NULL, 'PROD', 'MATURITY', 'PHARMA'),
('620000', 'OTC Products', 'OTC', '600000', 'Healthcare', NULL, 'PROD', 'MATURITY', 'PHARMA'),
('630000', 'Medical Devices', 'MD', '600000', 'Healthcare', NULL, 'PROD', 'GROWTH', 'PHARMA');

-- Third Level  
INSERT INTO product_lines (product_line_id, product_line_name, short_name, parent_product_line, product_category, product_family, business_area_id, lifecycle_stage, industry_sector) VALUES
('111000', 'Smartphones', 'Phone', '110000', 'Electronics', 'Smartphones', 'TECH', 'MATURITY', 'TECHNOLOGY'),
('111100', 'Premium Smartphones', 'Premium', '111000', 'Electronics', 'Smartphones', 'TECH', 'GROWTH', 'TECHNOLOGY'),
('111200', 'Budget Smartphones', 'Budget', '111000', 'Electronics', 'Smartphones', 'TECH', 'MATURITY', 'TECHNOLOGY'),
('121000', 'Laptops', 'Laptop', '120000', 'Electronics', 'Computers', 'TECH', 'MATURITY', 'TECHNOLOGY'),
('122000', 'Tablets', 'Tablet', '120000', 'Electronics', 'Computers', 'TECH', 'DECLINE', 'TECHNOLOGY'),
('211000', 'Financial ERP', 'FIN-ERP', '210000', 'Software', 'Enterprise', 'TECH', 'MATURITY', 'TECHNOLOGY'),
('212000', 'Supply Chain ERP', 'SCM-ERP', '210000', 'Software', 'Enterprise', 'TECH', 'GROWTH', 'TECHNOLOGY'),
('221000', 'SaaS Applications', 'SaaS', '220000', 'Software', 'Cloud', 'TECH', 'GROWTH', 'TECHNOLOGY'),
('222000', 'Infrastructure Services', 'IaaS', '220000', 'Software', 'Cloud', 'TECH', 'GROWTH', 'TECHNOLOGY'),
('511000', 'Beverages', 'BEV', '510000', 'FMCG', NULL, 'PROD', 'MATURITY', 'CPG'),
('512000', 'Snacks', 'SNACK', '510000', 'FMCG', NULL, 'PROD', 'GROWTH', 'CPG'),
('521000', 'Skincare', 'SKIN', '520000', 'FMCG', NULL, 'PROD', 'GROWTH', 'CPG'),
('522000', 'Haircare', 'HAIR', '520000', 'FMCG', NULL, 'PROD', 'MATURITY', 'CPG'),
('611000', 'Oncology', 'ONCO', '610000', 'Healthcare', NULL, 'PROD', 'GROWTH', 'PHARMA'),
('612000', 'Cardiovascular', 'CARDIO', '610000', 'Healthcare', NULL, 'PROD', 'MATURITY', 'PHARMA');