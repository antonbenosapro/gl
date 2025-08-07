-- =====================================================
-- Add Oil Field Services Product Lines
-- =====================================================
-- Author: Claude Code Assistant
-- Date: August 7, 2025
-- Description: Add comprehensive oil field services product lines
--              for upstream, midstream, and downstream operations
-- =====================================================

-- Oil & Gas Industry Product Line Structure:
-- 7000 - Oil Field Services (Top Level)
-- 71XX - Drilling Services
-- 72XX - Production Services  
-- 73XX - Well Services
-- 74XX - Seismic Services
-- 75XX - Equipment & Tools
-- 76XX - Logistics Services
-- 77XX - Environmental Services
-- 78XX - Digital Services

-- =====================================================
-- TOP LEVEL: Oil Field Services Category
-- =====================================================

INSERT INTO product_lines (
    product_line_id, product_line_name, short_name, description,
    product_category, business_area_id, lifecycle_stage, industry_sector,
    is_manufactured, is_purchased, is_service, is_digital,
    requires_serialization, requires_lot_tracking,
    is_active, valid_from, created_by
) VALUES
('7000', 'Oil Field Services', 'OFS', 'Comprehensive oil field services for upstream operations', 
 'Energy Services', 'ENGY', 'MATURITY', 'ENERGY', FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, TRUE, CURRENT_DATE, 'MIGRATION');

-- =====================================================
-- LEVEL 1: Service Categories
-- =====================================================

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
('7200', 'Production Services', 'PROD', '7000', 'Energy Services', 'Production', 'ENGY', 'MATURITY', 'ENERGY', FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, TRUE, 'MIGRATION'),

-- Well Services
('7300', 'Well Services', 'WELL', '7000', 'Energy Services', 'Well Operations', 'ENGY', 'MATURITY', 'ENERGY', FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, TRUE, 'MIGRATION'),

-- Seismic Services
('7400', 'Seismic Services', 'SEIS', '7000', 'Energy Services', 'Exploration', 'ENGY', 'GROWTH', 'ENERGY', FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, TRUE, 'MIGRATION'),

-- Equipment & Tools
('7500', 'Equipment & Tools', 'EQUIP', '7000', 'Energy Services', 'Equipment', 'ENGY', 'MATURITY', 'ENERGY', TRUE, TRUE, FALSE, FALSE, TRUE, FALSE, TRUE, 'MIGRATION'),

-- Logistics Services
('7600', 'Logistics Services', 'LOG', '7000', 'Energy Services', 'Logistics', 'ENGY', 'MATURITY', 'ENERGY', FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, TRUE, 'MIGRATION'),

-- Environmental Services
('7700', 'Environmental Services', 'ENV', '7000', 'Energy Services', 'Environmental', 'ENGY', 'GROWTH', 'ENERGY', FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, TRUE, 'MIGRATION'),

-- Digital Services
('7800', 'Digital Services', 'DIGI', '7000', 'Energy Services', 'Digital', 'ENGY', 'GROWTH', 'ENERGY', FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, TRUE, 'MIGRATION');

-- =====================================================
-- LEVEL 2: Specific Service Lines
-- =====================================================

INSERT INTO product_lines (
    product_line_id, product_line_name, short_name, parent_product_line,
    product_category, product_family, business_area_id, lifecycle_stage, industry_sector,
    product_manager, revenue_recognition_method, standard_margin_percentage, target_margin_percentage,
    is_manufactured, is_purchased, is_service, is_digital,
    requires_serialization, requires_lot_tracking, regulatory_classification,
    is_active, created_by
) VALUES

-- ===== DRILLING SERVICES =====
('7110', 'Directional Drilling', 'DD', '7100', 'Energy Services', 'Drilling', 'ENGY', 'MATURITY', 'ENERGY',
 'John Smith', 'OVER_TIME', 25.00, 30.00, FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, 'API SPEC', TRUE, 'MIGRATION'),

('7120', 'Drilling Fluids', 'FLUID', '7100', 'Energy Services', 'Drilling', 'ENGY', 'MATURITY', 'ENERGY',
 'Sarah Johnson', 'POINT_IN_TIME', 35.00, 40.00, TRUE, FALSE, TRUE, FALSE, FALSE, TRUE, 'API 13A', TRUE, 'MIGRATION'),

('7130', 'Casing & Cementing', 'CASE', '7100', 'Energy Services', 'Drilling', 'ENGY', 'MATURITY', 'ENERGY',
 'Mike Davis', 'OVER_TIME', 28.00, 35.00, TRUE, FALSE, TRUE, FALSE, TRUE, FALSE, 'API 10A', TRUE, 'MIGRATION'),

('7140', 'Measurement While Drilling', 'MWD', '7100', 'Energy Services', 'Drilling', 'ENGY', 'GROWTH', 'ENERGY',
 'Lisa Chen', 'OVER_TIME', 45.00, 50.00, FALSE, FALSE, TRUE, TRUE, TRUE, FALSE, 'API RP 7G', TRUE, 'MIGRATION'),

-- ===== PRODUCTION SERVICES =====
('7210', 'Artificial Lift', 'AL', '7200', 'Energy Services', 'Production', 'ENGY', 'MATURITY', 'ENERGY',
 'Robert Wilson', 'OVER_TIME', 30.00, 35.00, TRUE, FALSE, TRUE, FALSE, TRUE, FALSE, 'API 11E', TRUE, 'MIGRATION'),

('7220', 'Flow Assurance', 'FLOW', '7200', 'Energy Services', 'Production', 'ENGY', 'GROWTH', 'ENERGY',
 'Emma Brown', 'OVER_TIME', 40.00, 45.00, FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, 'API RP 14E', TRUE, 'MIGRATION'),

('7230', 'Production Optimization', 'PROD-OPT', '7200', 'Energy Services', 'Production', 'ENGY', 'GROWTH', 'ENERGY',
 'David Garcia', 'OVER_TIME', 38.00, 42.00, FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, 'ISO 29001', TRUE, 'MIGRATION'),

('7240', 'Enhanced Oil Recovery', 'EOR', '7200', 'Energy Services', 'Production', 'ENGY', 'GROWTH', 'ENERGY',
 'Jennifer Lee', 'PERCENTAGE_COMPLETION', 35.00, 40.00, TRUE, FALSE, TRUE, FALSE, FALSE, TRUE, 'API RP 63', TRUE, 'MIGRATION'),

-- ===== WELL SERVICES =====
('7310', 'Well Intervention', 'WI', '7300', 'Energy Services', 'Well Operations', 'ENGY', 'MATURITY', 'ENERGY',
 'Thomas Anderson', 'OVER_TIME', 32.00, 38.00, FALSE, FALSE, TRUE, FALSE, TRUE, FALSE, 'API RP 17B', TRUE, 'MIGRATION'),

('7320', 'Coiled Tubing', 'CT', '7300', 'Energy Services', 'Well Operations', 'ENGY', 'MATURITY', 'ENERGY',
 'Maria Rodriguez', 'OVER_TIME', 28.00, 33.00, TRUE, FALSE, TRUE, FALSE, TRUE, FALSE, 'API 5ST', TRUE, 'MIGRATION'),

('7330', 'Wireline Services', 'WL', '7300', 'Energy Services', 'Well Operations', 'ENGY', 'MATURITY', 'ENERGY',
 'James Taylor', 'OVER_TIME', 42.00, 48.00, FALSE, FALSE, TRUE, TRUE, TRUE, FALSE, 'API RP 7G-2', TRUE, 'MIGRATION'),

('7340', 'Hydraulic Fracturing', 'FRAC', '7300', 'Energy Services', 'Well Operations', 'ENGY', 'GROWTH', 'ENERGY',
 'Susan Miller', 'OVER_TIME', 25.00, 30.00, TRUE, FALSE, TRUE, FALSE, FALSE, TRUE, 'API RP 19D', TRUE, 'MIGRATION'),

-- ===== SEISMIC SERVICES =====
('7410', '2D/3D Seismic Survey', 'SEIS-3D', '7400', 'Energy Services', 'Exploration', 'ENGY', 'MATURITY', 'ENERGY',
 'Paul Johnson', 'PERCENTAGE_COMPLETION', 35.00, 40.00, FALSE, FALSE, TRUE, TRUE, TRUE, FALSE, 'ISO 19901-1', TRUE, 'MIGRATION'),

('7420', '4D Seismic Monitoring', 'SEIS-4D', '7400', 'Energy Services', 'Exploration', 'ENGY', 'GROWTH', 'ENERGY',
 'Rachel Kim', 'PERCENTAGE_COMPLETION', 45.00, 50.00, FALSE, FALSE, TRUE, TRUE, TRUE, FALSE, 'ISO 19901-1', TRUE, 'MIGRATION'),

('7430', 'Microseismic Monitoring', 'MICRO', '7400', 'Energy Services', 'Exploration', 'ENGY', 'GROWTH', 'ENERGY',
 'Kevin Chang', 'OVER_TIME', 50.00, 55.00, FALSE, FALSE, TRUE, TRUE, TRUE, FALSE, 'API RP 19D20', TRUE, 'MIGRATION'),

-- ===== EQUIPMENT & TOOLS =====
('7510', 'Drilling Equipment', 'DRILL-EQ', '7500', 'Energy Services', 'Equipment', 'ENGY', 'MATURITY', 'ENERGY',
 'Michael Brown', 'POINT_IN_TIME', 20.00, 25.00, TRUE, TRUE, FALSE, FALSE, TRUE, FALSE, 'API 7K', TRUE, 'MIGRATION'),

('7520', 'Completion Tools', 'COMP', '7500', 'Energy Services', 'Equipment', 'ENGY', 'MATURITY', 'ENERGY',
 'Amy White', 'POINT_IN_TIME', 25.00, 30.00, TRUE, TRUE, FALSE, FALSE, TRUE, FALSE, 'API 11D1', TRUE, 'MIGRATION'),

('7530', 'Safety Equipment', 'SAFETY', '7500', 'Energy Services', 'Equipment', 'ENGY', 'MATURITY', 'ENERGY',
 'Daniel Martinez', 'POINT_IN_TIME', 30.00, 35.00, TRUE, TRUE, FALSE, FALSE, TRUE, FALSE, 'API RP 500', TRUE, 'MIGRATION'),

-- ===== LOGISTICS SERVICES =====
('7610', 'Offshore Logistics', 'OFFSHORE', '7600', 'Energy Services', 'Logistics', 'ENGY', 'MATURITY', 'ENERGY',
 'Patricia Davis', 'OVER_TIME', 18.00, 22.00, FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, 'IMO SOLAS', TRUE, 'MIGRATION'),

('7620', 'Supply Chain Management', 'SCM', '7600', 'Energy Services', 'Logistics', 'ENGY', 'GROWTH', 'ENERGY',
 'Christopher Wilson', 'OVER_TIME', 22.00, 28.00, FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, 'ISO 28000', TRUE, 'MIGRATION'),

-- ===== ENVIRONMENTAL SERVICES =====
('7710', 'Environmental Compliance', 'ENV-COMP', '7700', 'Energy Services', 'Environmental', 'ENGY', 'GROWTH', 'ENERGY',
 'Linda Garcia', 'OVER_TIME', 35.00, 40.00, FALSE, FALSE, TRUE, FALSE, FALSE, FALSE, 'EPA RCRA', TRUE, 'MIGRATION'),

('7720', 'Waste Management', 'WASTE', '7700', 'Energy Services', 'Environmental', 'ENGY', 'MATURITY', 'ENERGY',
 'Steven Lee', 'OVER_TIME', 25.00, 30.00, FALSE, FALSE, TRUE, FALSE, FALSE, TRUE, 'EPA TSCA', TRUE, 'MIGRATION'),

-- ===== DIGITAL SERVICES =====
('7810', 'Digital Twin', 'TWIN', '7800', 'Energy Services', 'Digital', 'ENGY', 'INTRODUCTION', 'ENERGY',
 'Jessica Taylor', 'OVER_TIME', 55.00, 60.00, FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, 'ISO 23247', TRUE, 'MIGRATION'),

('7820', 'Predictive Analytics', 'PREDICT', '7800', 'Energy Services', 'Digital', 'ENGY', 'GROWTH', 'ENERGY',
 'Ryan Miller', 'OVER_TIME', 50.00, 55.00, FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, 'ISO 27001', TRUE, 'MIGRATION'),

('7830', 'Remote Operations', 'REMOTE', '7800', 'Energy Services', 'Digital', 'ENGY', 'GROWTH', 'ENERGY',
 'Nicole Anderson', 'OVER_TIME', 48.00, 52.00, FALSE, FALSE, TRUE, TRUE, FALSE, FALSE, 'IEC 61508', TRUE, 'MIGRATION');

-- =====================================================
-- Add Energy Business Area if not exists
-- =====================================================

INSERT INTO business_areas (business_area_id, business_area_name, description, is_active)
VALUES ('ENGY', 'Energy Services', 'Oil field services and energy sector operations', TRUE)
ON CONFLICT (business_area_id) DO NOTHING;

-- =====================================================
-- Update Statistics
-- =====================================================

-- Total oil field services product lines added: 32
-- Categories: 8 main service categories
-- Specific Services: 24 detailed service lines
-- Coverage: Complete upstream oil & gas service portfolio

-- Summary by Category:
-- 7100 - Drilling Services: 4 products (DD, FLUID, CASE, MWD)
-- 7200 - Production Services: 4 products (AL, FLOW, PROD-OPT, EOR)  
-- 7300 - Well Services: 4 products (WI, CT, WL, FRAC)
-- 7400 - Seismic Services: 3 products (SEIS-3D, SEIS-4D, MICRO)
-- 7500 - Equipment & Tools: 3 products (DRILL-EQ, COMP, SAFETY)
-- 7600 - Logistics Services: 2 products (OFFSHORE, SCM)
-- 7700 - Environmental Services: 2 products (ENV-COMP, WASTE)
-- 7800 - Digital Services: 3 products (TWIN, PREDICT, REMOTE)

-- Industry Compliance Standards Included:
-- API (American Petroleum Institute) standards
-- ISO (International Organization for Standardization) 
-- EPA (Environmental Protection Agency) regulations
-- IMO (International Maritime Organization) standards
-- IEC (International Electrotechnical Commission)