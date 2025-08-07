-- =====================================================
-- Create Backward Compatibility Views
-- =====================================================
-- Author: Claude Code Assistant
-- Date: August 7, 2025
-- Description: Create views that maintain compatibility with existing
--              applications that expect costcenter and profit_centers tables
-- =====================================================

-- Step 1: Drop existing compatibility views if they exist (from previous migration)
DROP VIEW IF EXISTS costcenter CASCADE;
DROP VIEW IF EXISTS profit_centers CASCADE;

-- Step 2: Create comprehensive costcenter compatibility view
CREATE OR REPLACE VIEW costcenter AS
SELECT 
    -- Map business unit fields back to cost center fields
    REPLACE(bu.unit_id, 'BU-CC-', '') as costcenterid,
    bu.company_code_id as companycodeid,
    bu.unit_name as name,
    bu.short_name,
    bu.description,
    bu.unit_category as cost_center_category,
    bu.controlling_area,
    bu.person_responsible,
    bu.department,
    bu.unit_group as cost_center_group,
    -- Map parent relationship back
    CASE 
        WHEN bu.parent_unit_id IS NOT NULL 
        THEN REPLACE(bu.parent_unit_id, 'BU-CC-', '')
        ELSE NULL 
    END as parent_cost_center,
    bu.hierarchy_level,
    bu.planning_enabled,
    bu.budget_profile,
    bu.cost_center_type,
    -- Map default business area
    bu.business_area_id as default_business_area,
    -- Additional fields for compatibility
    bu.local_currency,
    bu.is_active,
    bu.valid_from,
    bu.valid_to,
    bu.status,
    bu.created_by,
    bu.created_at,
    bu.modified_by,
    bu.modified_at
FROM business_units bu
WHERE bu.unit_type IN ('COST_CENTER', 'BOTH')
AND bu.is_active = TRUE;

-- Step 3: Create comprehensive profit_centers compatibility view  
CREATE OR REPLACE VIEW profit_centers AS
SELECT
    -- Map business unit fields back to profit center fields
    REPLACE(bu.unit_id, 'BU-', '') as profit_center_id,
    bu.unit_name as profit_center_name,
    bu.short_name,
    bu.description,
    bu.company_code_id,
    bu.controlling_area,
    bu.business_area_id as business_area,
    -- Map parent relationship back
    CASE 
        WHEN bu.parent_unit_id IS NOT NULL 
        THEN REPLACE(bu.parent_unit_id, 'BU-', '')
        ELSE NULL 
    END as parent_profit_center,
    bu.unit_group as profit_center_group,
    bu.hierarchy_level,
    bu.person_responsible,
    bu.default_cost_center as cost_center,
    bu.segment,
    bu.local_currency,
    bu.valid_from,
    bu.valid_to,
    bu.is_active,
    bu.status,
    bu.created_by,
    bu.created_at,
    bu.modified_by,
    bu.modified_at
FROM business_units bu
WHERE bu.unit_type IN ('PROFIT_CENTER', 'BOTH')
AND bu.is_active = TRUE;

-- Step 4: Create enhanced mapping views that show the old-to-new relationships
CREATE OR REPLACE VIEW v_costcenter_business_unit_mapping AS
SELECT 
    REPLACE(bu.unit_id, 'BU-CC-', '') as old_costcenterid,
    bu.unit_id as new_unit_id,
    bu.unit_name,
    bu.unit_type,
    bu.generated_code,
    bu.product_line_id,
    bu.location_code,
    pl.product_line_name,
    rl.location_name
FROM business_units bu
LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
WHERE bu.unit_type IN ('COST_CENTER', 'BOTH');

CREATE OR REPLACE VIEW v_profit_center_business_unit_mapping AS
SELECT 
    REPLACE(bu.unit_id, 'BU-', '') as old_profit_center_id,
    bu.unit_id as new_unit_id,
    bu.unit_name,
    bu.unit_type,
    bu.generated_code,
    bu.product_line_id,
    bu.location_code,
    pl.product_line_name,
    rl.location_name
FROM business_units bu
LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
WHERE bu.unit_type IN ('PROFIT_CENTER', 'BOTH');

-- Step 5: Create enhanced reporting views that leverage the new capabilities
CREATE OR REPLACE VIEW v_business_units_with_dimensions AS
SELECT 
    bu.unit_id,
    bu.unit_name,
    bu.short_name,
    bu.unit_type,
    bu.responsibility_type,
    bu.unit_category,
    -- Product Line Dimension
    bu.product_line_id,
    pl.product_line_name,
    pl.product_category,
    pl.product_family,
    pl.lifecycle_stage,
    pl.industry_sector,
    -- Location Dimension
    bu.location_code,
    rl.location_name,
    rl.location_level,
    rl.country_code,
    rl.location_type,
    -- Generated Code
    bu.generated_code,
    -- Business Area Dimension
    bu.business_area_id,
    ba.business_area_name,
    -- Management Information
    bu.person_responsible,
    bu.department,
    -- Status
    bu.is_active,
    bu.status
FROM business_units bu
LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
LEFT JOIN business_areas ba ON bu.business_area_id = ba.business_area_id;

-- Step 6: Create views for financial reporting integration
CREATE OR REPLACE VIEW v_gl_transaction_business_units AS
SELECT DISTINCT
    gt.cost_center,
    bu.unit_id,
    bu.unit_name,
    bu.unit_type,
    bu.generated_code,
    bu.product_line_id,
    pl.product_line_name,
    pl.industry_sector,
    bu.location_code,
    rl.location_name,
    rl.country_code
FROM gl_transactions gt
LEFT JOIN business_units bu ON (
    gt.cost_center = REPLACE(bu.unit_id, 'BU-CC-', '') OR
    gt.cost_center = REPLACE(bu.unit_id, 'BU-', '') OR
    gt.cost_center = bu.unit_id
)
LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
WHERE gt.cost_center IS NOT NULL;

-- Step 7: Create update triggers for backward compatibility
-- These ensure that updates to the compatibility views update the underlying business_units table

CREATE OR REPLACE FUNCTION costcenter_update_trigger()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE business_units 
    SET 
        unit_name = NEW.name,
        short_name = NEW.short_name,
        description = NEW.description,
        unit_category = NEW.cost_center_category,
        controlling_area = NEW.controlling_area,
        person_responsible = NEW.person_responsible,
        department = NEW.department,
        planning_enabled = NEW.planning_enabled,
        budget_profile = NEW.budget_profile,
        cost_center_type = NEW.cost_center_type,
        business_area_id = NEW.default_business_area,
        is_active = NEW.is_active,
        modified_by = NEW.modified_by,
        modified_at = CURRENT_TIMESTAMP
    WHERE unit_id = 'BU-CC-' || NEW.costcenterid
    AND unit_type IN ('COST_CENTER', 'BOTH');
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION profit_centers_update_trigger()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE business_units 
    SET 
        unit_name = NEW.profit_center_name,
        short_name = NEW.short_name,
        description = NEW.description,
        controlling_area = NEW.controlling_area,
        business_area_id = NEW.business_area,
        person_responsible = NEW.person_responsible,
        default_cost_center = NEW.cost_center,
        segment = NEW.segment,
        local_currency = NEW.local_currency,
        is_active = NEW.is_active,
        modified_by = NEW.modified_by,
        modified_at = CURRENT_TIMESTAMP
    WHERE unit_id = 'BU-' || NEW.profit_center_id
    AND unit_type IN ('PROFIT_CENTER', 'BOTH');
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the triggers
CREATE TRIGGER costcenter_view_update
    INSTEAD OF UPDATE ON costcenter
    FOR EACH ROW
    EXECUTE FUNCTION costcenter_update_trigger();

CREATE TRIGGER profit_centers_view_update
    INSTEAD OF UPDATE ON profit_centers
    FOR EACH ROW
    EXECUTE FUNCTION profit_centers_update_trigger();

-- Step 8: Grant permissions on all views
GRANT SELECT ON costcenter TO PUBLIC;
GRANT SELECT ON profit_centers TO PUBLIC;
GRANT SELECT ON v_costcenter_business_unit_mapping TO PUBLIC;
GRANT SELECT ON v_profit_center_business_unit_mapping TO PUBLIC;
GRANT SELECT ON v_business_units_with_dimensions TO PUBLIC;
GRANT SELECT ON v_gl_transaction_business_units TO PUBLIC;

-- Step 9: Test the compatibility views
DO $$
DECLARE
    cc_count INTEGER;
    pc_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO cc_count FROM costcenter;
    SELECT COUNT(*) INTO pc_count FROM profit_centers;
    
    RAISE NOTICE '=== BACKWARD COMPATIBILITY VERIFICATION ===';
    RAISE NOTICE 'Cost Centers visible in compatibility view: %', cc_count;
    RAISE NOTICE 'Profit Centers visible in compatibility view: %', pc_count;
    RAISE NOTICE 'Backward compatibility views created successfully!';
END $$;

-- Step 10: Show sample data from enhanced views
SELECT 'Enhanced Business Units View' as view_name;
SELECT unit_id, unit_name, unit_type, generated_code, product_line_name, location_name 
FROM v_business_units_with_dimensions 
WHERE generated_code IS NOT NULL
LIMIT 5;

SELECT 'Cost Center Compatibility View' as view_name;
SELECT costcenterid, name, cost_center_category 
FROM costcenter 
LIMIT 3;

SELECT 'Profit Center Compatibility View' as view_name;
SELECT profit_center_id, profit_center_name, business_area 
FROM profit_centers 
LIMIT 3;

-- =====================================================
-- Backward Compatibility Views Complete
-- =====================================================
-- Created:
--   - costcenter view (maintains full compatibility)
--   - profit_centers view (maintains full compatibility)
--   - Mapping views (show old-to-new relationships)
--   - Enhanced reporting views (leverage new dimensions)
--   - Update triggers (allow updates through compatibility views)
-- 
-- Applications can continue using costcenter and profit_centers
-- as if they were tables, with full CRUD support maintained.
-- =====================================================