-- =====================================================
-- Fix Profit Center Migration to Business Units
-- =====================================================
-- Author: Claude Code Assistant
-- Date: August 7, 2025
-- Description: Fix profit center migration issues and complete data transfer
-- =====================================================

-- Step 1: Clear any problematic profit center entries that might have partial data
DELETE FROM business_units WHERE unit_type = 'PROFIT_CENTER' AND created_by = 'MIGRATION';

-- Step 2: Re-migrate Profit Centers with corrected logic
INSERT INTO business_units (
    unit_id, 
    unit_name, 
    short_name, 
    description,
    unit_type,
    unit_category,
    responsibility_type,
    company_code_id,
    controlling_area,
    business_area_id,
    parent_unit_id,
    hierarchy_level,
    person_responsible,
    default_cost_center,
    profit_center_type,
    margin_analysis_enabled,
    segment,
    local_currency,
    is_active,
    valid_from,
    valid_to,
    created_by,
    created_at
)
SELECT 
    -- Ensure unique unit_id by using profit_center_id directly with BU- prefix
    'BU-' || pc.profit_center_id as unit_id,
    COALESCE(pc.profit_center_name, 'Profit Center ' || pc.profit_center_id) as unit_name,
    COALESCE(pc.short_name, LEFT(pc.profit_center_name, 20), pc.profit_center_id) as short_name,
    pc.description,
    'PROFIT_CENTER' as unit_type,
    'STANDARD' as unit_category,
    'PROFIT' as responsibility_type,
    pc.company_code_id,
    COALESCE(pc.controlling_area, 'C001') as controlling_area,
    pc.business_area as business_area_id,
    -- Handle parent relationships carefully
    CASE 
        WHEN pc.parent_profit_center IS NOT NULL 
        THEN 'BU-' || pc.parent_profit_center
        ELSE NULL 
    END as parent_unit_id,
    COALESCE(pc.hierarchy_level, 1) as hierarchy_level,
    pc.person_responsible,
    pc.cost_center as default_cost_center,
    'ACTUAL' as profit_center_type,
    TRUE as margin_analysis_enabled,
    pc.segment,
    COALESCE(pc.local_currency, 'USD') as local_currency,
    COALESCE(pc.is_active, TRUE) as is_active,
    COALESCE(pc.valid_from, CURRENT_DATE) as valid_from,
    COALESCE(pc.valid_to, '9999-12-31'::DATE) as valid_to,
    'MIGRATION' as created_by,
    COALESCE(pc.created_at, CURRENT_TIMESTAMP) as created_at
FROM profit_centers pc
WHERE NOT EXISTS (
    SELECT 1 FROM business_units bu 
    WHERE bu.unit_id = 'BU-' || pc.profit_center_id
);

-- Step 3: Add sample business units with valid location codes only
-- First, let's check what location codes actually exist and use them
INSERT INTO business_units (
    unit_id,
    unit_name,
    short_name,
    unit_type,
    unit_category,
    responsibility_type,
    company_code_id,
    business_area_id,
    product_line_id,
    location_code,
    person_responsible,
    department,
    planning_enabled,
    margin_analysis_enabled,
    is_active,
    created_by
)
SELECT * FROM (VALUES
    -- Use existing location codes from our location table
    ('BU-SMART-GLOBAL', 'Smartphones Global Operations', 'SMART-GLOB', 'BOTH', 'STANDARD', 'PROFIT', 'C001', 'TECH', '1110', '000001', 'John Smith', 'Product Development', TRUE, TRUE, TRUE, 'SAMPLE'),
    ('BU-OFS-NA', 'Oil Field Services North America', 'OFS-NA', 'PROFIT_CENTER', 'REVENUE', 'PROFIT', 'C001', 'ENGY', '7000', '100000', 'Mike Wilson', 'Energy Operations', TRUE, TRUE, TRUE, 'SAMPLE'),
    ('BU-BEV-GLOBAL', 'Beverages Global Operations', 'BEV-GLOB', 'PROFIT_CENTER', 'REVENUE', 'PROFIT', 'C001', 'PROD', '5110', '000001', 'Carlos Silva', 'FMCG Operations', TRUE, TRUE, TRUE, 'SAMPLE'),
    -- Location-only business units  
    ('BU-EMEA-REG', 'EMEA Regional Operations', 'EMEA', 'COST_CENTER', 'OVERHEAD', 'COST', 'C001', 'EU', NULL, '200000', 'Emma Brown', 'Regional Management', TRUE, FALSE, TRUE, 'SAMPLE'),
    ('BU-APAC-REG', 'APAC Regional Operations', 'APAC', 'COST_CENTER', 'OVERHEAD', 'COST', 'C001', 'APAC', NULL, '300000', 'Li Wei', 'Regional Management', TRUE, FALSE, TRUE, 'SAMPLE')
) AS v(unit_id, unit_name, short_name, unit_type, unit_category, responsibility_type, company_code_id, business_area_id, product_line_id, location_code, person_responsible, department, planning_enabled, margin_analysis_enabled, is_active, created_by)
WHERE EXISTS (SELECT 1 FROM reporting_locations rl WHERE rl.location_code = v.location_code)
  AND EXISTS (SELECT 1 FROM product_lines pl WHERE pl.product_line_id = v.product_line_id OR v.product_line_id IS NULL)
  AND NOT EXISTS (SELECT 1 FROM business_units bu WHERE bu.unit_id = v.unit_id);

-- Step 4: Show final migration results
DO $$
DECLARE
    cost_centers INTEGER;
    profit_centers INTEGER;
    dual_units INTEGER;
    sample_units INTEGER;
    total_units INTEGER;
    units_with_codes INTEGER;
BEGIN
    SELECT COUNT(*) INTO cost_centers FROM business_units WHERE unit_type = 'COST_CENTER';
    SELECT COUNT(*) INTO profit_centers FROM business_units WHERE unit_type = 'PROFIT_CENTER';  
    SELECT COUNT(*) INTO dual_units FROM business_units WHERE unit_type = 'BOTH';
    SELECT COUNT(*) INTO sample_units FROM business_units WHERE created_by = 'SAMPLE';
    SELECT COUNT(*) INTO total_units FROM business_units;
    SELECT COUNT(*) INTO units_with_codes FROM business_units WHERE generated_code IS NOT NULL;
    
    RAISE NOTICE '=== FINAL MIGRATION SUMMARY ===';
    RAISE NOTICE 'Cost Center Units: %', cost_centers;
    RAISE NOTICE 'Profit Center Units: %', profit_centers;
    RAISE NOTICE 'Dual-Purpose Units: %', dual_units;
    RAISE NOTICE 'Sample Units Added: %', sample_units;
    RAISE NOTICE 'Total Business Units: %', total_units;
    RAISE NOTICE 'Units with Generated Codes: %', units_with_codes;
    RAISE NOTICE '=========================';
END $$;

-- Step 5: Show some examples of the new generated codes
SELECT 
    unit_id,
    unit_name,
    unit_type,
    product_line_id,
    location_code,
    generated_code
FROM business_units 
WHERE generated_code IS NOT NULL
ORDER BY unit_id;

-- =====================================================
-- Profit Center Migration Fixed
-- =====================================================