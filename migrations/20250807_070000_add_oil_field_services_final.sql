-- =====================================================
-- Add Oil Field Services Product Lines (FINAL)
-- =====================================================
-- Author: Claude Code Assistant
-- Date: August 7, 2025
-- Description: Add comprehensive oil field services product lines
--              Final version with corrected field lengths
-- =====================================================

-- Step 1: Add Energy Business Area first
INSERT INTO business_areas (
    business_area_id, business_area_name, short_name, description, 
    company_code_id, is_active, created_by
) VALUES (
    'ENGY', 'Energy Services', 'ENGY', 'Oil field services and energy sector operations', 
    'C001', TRUE, 'MIGRATION'
) ON CONFLICT (business_area_id) DO NOTHING;

-- Step 2: Add TOP LEVEL Oil Field Services Category
INSERT INTO product_lines (
    product_line_id, product_line_name, short_name, description,
    product_category, business_area_id, lifecycle_stage, industry_sector,
    is_manufactured, is_purchased, is_service, is_digital,
    requires_serialization, requires_lot_tracking,
    is_active, valid_from, created_by
) VALUES
('7000', 'Oil Field Services', 'OFS', 'Comprehensive oil field services for upstream operations', 
 'Energy Services', 'ENGY', 'MATURITY', 'ENERGY', FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, TRUE, CURRENT_DATE, 'MIGRATION');

-- Step 3: Add LEVEL 1 Service Categories
INSERT INTO product_lines (
    product_line_id, product_line_name, short_name, parent_product_line,
    product_category, product_family, business_area_id, lifecycle_stage, industry_sector,
    is_manufactured, is_purchased, is_service, is_digital,
    requires_serialization, requires_lot_tracking,
    is_active, created_by
) VALUES
-- Drilling Services
('7100', 'Drilling Services', 'DRILL', '7000', 'Energy Services', 'Drilling', 'ENGY', 'MATURITY', 'ENERGY', FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, TRUE, 'MIGRATION'),
-- Production Services
('7200', 'Production Services', 'PROD-SVC', '7000', 'Energy Services', 'Production', 'ENGY', 'MATURITY', 'ENERGY', FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, TRUE, 'MIGRATION'),
-- Well Services
('7300', 'Well Services', 'WELL-SVC', '7000', 'Energy Services', 'Well Operations', 'ENGY', 'MATURITY', 'ENERGY', FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, TRUE, 'MIGRATION'),
-- Seismic Services
('7400', 'Seismic Services', 'SEIS', '7000', 'Energy Services', 'Exploration', 'ENGY', 'GROWTH', 'ENERGY', FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, TRUE, 'MIGRATION'),
-- Equipment & Tools
('7500', 'Equipment & Tools', 'EQUIP', '7000', 'Energy Services', 'Equipment', 'ENGY', 'MATURITY', 'ENERGY', TRUE, TRUE, FALSE, FALSE, TRUE, FALSE, TRUE, 'MIGRATION'),
-- Logistics Services
('7600', 'Logistics Services', 'LOG-SVC', '7000', 'Energy Services', 'Logistics', 'ENGY', 'MATURITY', 'ENERGY', FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, TRUE, 'MIGRATION'),
-- Environmental Services
('7700', 'Environmental Svcs', 'ENV-SVC', '7000', 'Energy Services', 'Environmental', 'ENGY', 'GROWTH', 'ENERGY', FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, TRUE, 'MIGRATION'),
-- Digital Services
('7800', 'Digital Services', 'DIGI-SVC', '7000', 'Energy Services', 'Digital', 'ENGY', 'GROWTH', 'ENERGY', FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, TRUE, 'MIGRATION');

-- Step 4: Add LEVEL 2 Specific Service Lines (First Batch - Drilling & Production)
INSERT INTO product_lines (
    product_line_id, product_line_name, short_name, parent_product_line,
    product_category, product_family, business_area_id, lifecycle_stage, industry_sector,
    product_manager, standard_margin_percentage, target_margin_percentage,
    is_manufactured, is_purchased, is_service, is_digital,
    requires_serialization, requires_lot_tracking, regulatory_classification,
    is_active, created_by
) VALUES

-- ===== DRILLING SERVICES =====
('7110', 'Directional Drilling', 'DD', '7100', 'Energy Services', 'Drilling', 'ENGY', 'MATURITY', 'ENERGY',
 'John Smith', 25.00, 30.00, FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, 'API SPEC', TRUE, 'MIGRATION'),

('7120', 'Drilling Fluids', 'FLUID', '7100', 'Energy Services', 'Drilling', 'ENGY', 'MATURITY', 'ENERGY',
 'Sarah Johnson', 35.00, 40.00, TRUE, FALSE, TRUE, FALSE, FALSE, TRUE, 'API 13A', TRUE, 'MIGRATION'),

('7130', 'Casing & Cementing', 'CASE', '7100', 'Energy Services', 'Drilling', 'ENGY', 'MATURITY', 'ENERGY',
 'Mike Davis', 28.00, 35.00, TRUE, FALSE, TRUE, FALSE, TRUE, FALSE, 'API 10A', TRUE, 'MIGRATION'),

('7140', 'MWD Services', 'MWD', '7100', 'Energy Services', 'Drilling', 'ENGY', 'GROWTH', 'ENERGY',
 'Lisa Chen', 45.00, 50.00, FALSE, FALSE, TRUE, TRUE, TRUE, FALSE, 'API RP 7G', TRUE, 'MIGRATION'),

-- ===== PRODUCTION SERVICES =====
('7210', 'Artificial Lift', 'AL', '7200', 'Energy Services', 'Production', 'ENGY', 'MATURITY', 'ENERGY',
 'Robert Wilson', 30.00, 35.00, TRUE, FALSE, TRUE, FALSE, TRUE, FALSE, 'API 11E', TRUE, 'MIGRATION'),

('7220', 'Flow Assurance', 'FLOW', '7200', 'Energy Services', 'Production', 'ENGY', 'GROWTH', 'ENERGY',
 'Emma Brown', 40.00, 45.00, FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, 'API RP 14E', TRUE, 'MIGRATION'),

('7230', 'Production Optimize', 'PROD-OPT', '7200', 'Energy Services', 'Production', 'ENGY', 'GROWTH', 'ENERGY',
 'David Garcia', 38.00, 42.00, FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, 'ISO 29001', TRUE, 'MIGRATION'),

('7240', 'Enhanced Oil Recov', 'EOR', '7200', 'Energy Services', 'Production', 'ENGY', 'GROWTH', 'ENERGY',
 'Jennifer Lee', 35.00, 40.00, TRUE, FALSE, TRUE, FALSE, FALSE, TRUE, 'API RP 63', TRUE, 'MIGRATION');

-- Step 5: Add remaining service lines (Second Batch - Well Services & Seismic)
INSERT INTO product_lines (
    product_line_id, product_line_name, short_name, parent_product_line,
    product_category, product_family, business_area_id, lifecycle_stage, industry_sector,
    product_manager, standard_margin_percentage, target_margin_percentage,
    is_manufactured, is_purchased, is_service, is_digital,
    requires_serialization, requires_lot_tracking, regulatory_classification,
    is_active, created_by
) VALUES

-- ===== WELL SERVICES =====
('7310', 'Well Intervention', 'WI', '7300', 'Energy Services', 'Well Operations', 'ENGY', 'MATURITY', 'ENERGY',
 'Thomas Anderson', 32.00, 38.00, FALSE, FALSE, TRUE, FALSE, TRUE, FALSE, 'API RP 17B', TRUE, 'MIGRATION'),

('7320', 'Coiled Tubing', 'CT', '7300', 'Energy Services', 'Well Operations', 'ENGY', 'MATURITY', 'ENERGY',
 'Maria Rodriguez', 28.00, 33.00, TRUE, FALSE, TRUE, FALSE, TRUE, FALSE, 'API 5ST', TRUE, 'MIGRATION'),

('7330', 'Wireline Services', 'WL', '7300', 'Energy Services', 'Well Operations', 'ENGY', 'MATURITY', 'ENERGY',
 'James Taylor', 42.00, 48.00, FALSE, FALSE, TRUE, TRUE, TRUE, FALSE, 'API RP 7G-2', TRUE, 'MIGRATION'),

('7340', 'Hydraulic Frac', 'FRAC', '7300', 'Energy Services', 'Well Operations', 'ENGY', 'GROWTH', 'ENERGY',
 'Susan Miller', 25.00, 30.00, TRUE, FALSE, TRUE, FALSE, FALSE, TRUE, 'API RP 19D', TRUE, 'MIGRATION'),

-- ===== SEISMIC SERVICES =====
('7410', '2D/3D Seismic', 'SEIS-3D', '7400', 'Energy Services', 'Exploration', 'ENGY', 'MATURITY', 'ENERGY',
 'Paul Johnson', 35.00, 40.00, FALSE, FALSE, TRUE, TRUE, TRUE, FALSE, 'ISO 19901-1', TRUE, 'MIGRATION'),

('7420', '4D Seismic Monitor', 'SEIS-4D', '7400', 'Energy Services', 'Exploration', 'ENGY', 'GROWTH', 'ENERGY',
 'Rachel Kim', 45.00, 50.00, FALSE, FALSE, TRUE, TRUE, TRUE, FALSE, 'ISO 19901-1', TRUE, 'MIGRATION'),

('7430', 'Microseismic Mon', 'MICRO', '7400', 'Energy Services', 'Exploration', 'ENGY', 'GROWTH', 'ENERGY',
 'Kevin Chang', 50.00, 55.00, FALSE, FALSE, TRUE, TRUE, TRUE, FALSE, 'API RP 19D20', TRUE, 'MIGRATION'),

-- ===== EQUIPMENT & TOOLS =====
('7510', 'Drilling Equipment', 'DRILL-EQ', '7500', 'Energy Services', 'Equipment', 'ENGY', 'MATURITY', 'ENERGY',
 'Michael Brown', 20.00, 25.00, TRUE, TRUE, FALSE, FALSE, TRUE, FALSE, 'API 7K', TRUE, 'MIGRATION'),

('7520', 'Completion Tools', 'COMP', '7500', 'Energy Services', 'Equipment', 'ENGY', 'MATURITY', 'ENERGY',
 'Amy White', 25.00, 30.00, TRUE, TRUE, FALSE, FALSE, TRUE, FALSE, 'API 11D1', TRUE, 'MIGRATION'),

('7530', 'Safety Equipment', 'SAFETY', '7500', 'Energy Services', 'Equipment', 'ENGY', 'MATURITY', 'ENERGY',
 'Daniel Martinez', 30.00, 35.00, TRUE, TRUE, FALSE, FALSE, TRUE, FALSE, 'API RP 500', TRUE, 'MIGRATION');

-- Step 6: Add final service lines (Third Batch - Logistics, Environmental, Digital)
INSERT INTO product_lines (
    product_line_id, product_line_name, short_name, parent_product_line,
    product_category, product_family, business_area_id, lifecycle_stage, industry_sector,
    product_manager, standard_margin_percentage, target_margin_percentage,
    is_manufactured, is_purchased, is_service, is_digital,
    requires_serialization, requires_lot_tracking, regulatory_classification,
    is_active, created_by
) VALUES

-- ===== LOGISTICS SERVICES =====
('7610', 'Offshore Logistics', 'OFFSHORE', '7600', 'Energy Services', 'Logistics', 'ENGY', 'MATURITY', 'ENERGY',
 'Patricia Davis', 18.00, 22.00, FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, 'IMO SOLAS', TRUE, 'MIGRATION'),

('7620', 'Supply Chain Mgmt', 'SCM', '7600', 'Energy Services', 'Logistics', 'ENGY', 'GROWTH', 'ENERGY',
 'Christopher Wilson', 22.00, 28.00, FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, 'ISO 28000', TRUE, 'MIGRATION'),

-- ===== ENVIRONMENTAL SERVICES =====
('7710', 'Environmental Comp', 'ENV-COMP', '7700', 'Energy Services', 'Environmental', 'ENGY', 'GROWTH', 'ENERGY',
 'Linda Garcia', 35.00, 40.00, FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, 'EPA RCRA', TRUE, 'MIGRATION'),

('7720', 'Waste Management', 'WASTE', '7700', 'Energy Services', 'Environmental', 'ENGY', 'MATURITY', 'ENERGY',
 'Steven Lee', 25.00, 30.00, FALSE, FALSE, TRUE, FALSE, FALSE, TRUE, 'EPA TSCA', TRUE, 'MIGRATION'),

-- ===== DIGITAL SERVICES =====
('7810', 'Digital Twin', 'TWIN', '7800', 'Energy Services', 'Digital', 'ENGY', 'INTRODUCTION', 'ENERGY',
 'Jessica Taylor', 55.00, 60.00, FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, 'ISO 23247', TRUE, 'MIGRATION'),

('7820', 'Predictive Analyt', 'PREDICT', '7800', 'Energy Services', 'Digital', 'ENGY', 'GROWTH', 'ENERGY',
 'Ryan Miller', 50.00, 55.00, FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, 'ISO 27001', TRUE, 'MIGRATION'),

('7830', 'Remote Operations', 'REMOTE', '7800', 'Energy Services', 'Digital', 'ENGY', 'GROWTH', 'ENERGY',
 'Nicole Anderson', 48.00, 52.00, FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, 'IEC 61508', TRUE, 'MIGRATION');

-- =====================================================
-- Migration Summary
-- =====================================================
-- Added: 1 top-level category (7000)
-- Added: 8 service categories (71XX-78XX)  
-- Added: 24 specific service lines (7XXX)
-- Total: 33 new oil field services product lines
-- Industry: ENERGY sector with comprehensive upstream services
-- =====================================================