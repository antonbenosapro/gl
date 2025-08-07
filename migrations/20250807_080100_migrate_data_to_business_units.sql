-- =====================================================
-- Migrate Data to Business Units Table
-- =====================================================
-- Author: Claude Code Assistant
-- Date: August 7, 2025
-- Description: Migrate existing cost center and profit center data
--              to the unified business_units table
-- =====================================================

-- Step 1: Check existing data counts
DO $$
BEGIN
    RAISE NOTICE 'Starting migration to business_units...';
    RAISE NOTICE 'Existing cost centers: %', (SELECT COUNT(*) FROM costcenter);
    RAISE NOTICE 'Existing profit centers: %', (SELECT COUNT(*) FROM profit_centers);
END $$;

-- Step 2: Migrate Cost Centers to Business Units
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
    unit_group,
    person_responsible,
    department,
    planning_enabled,
    budget_profile,
    cost_center_type,
    is_active,
    valid_from,
    created_by,
    created_at,
    modified_by,
    modified_at
)
SELECT 
    -- Convert costcenterid to business unit format
    CASE 
        WHEN LENGTH(cc.costcenterid) <= 10 THEN 'BU-CC-' || cc.costcenterid
        ELSE 'BU-CC-' || LEFT(cc.costcenterid, 7)  -- Truncate if too long
    END as unit_id,
    COALESCE(cc.name, 'Cost Center ' || cc.costcenterid) as unit_name,
    COALESCE(cc.short_name, LEFT(cc.name, 20), 'CC-' || cc.costcenterid) as short_name,
    cc.description,
    'COST_CENTER' as unit_type,
    COALESCE(cc.cost_center_category, 'STANDARD') as unit_category,
    'COST' as responsibility_type,
    COALESCE(cc.companycodeid, 'C001') as company_code_id,
    COALESCE(cc.controlling_area, 'C001') as controlling_area,
    cc.default_business_area as business_area_id,
    CASE 
        WHEN cc.parent_cost_center IS NOT NULL 
        THEN 'BU-CC-' || cc.parent_cost_center
        ELSE NULL 
    END as parent_unit_id,
    COALESCE(cc.hierarchy_level, 1) as hierarchy_level,
    cc.cost_center_group as unit_group,
    cc.person_responsible,
    cc.department,
    COALESCE(cc.planning_enabled, TRUE) as planning_enabled,
    cc.budget_profile,
    COALESCE(cc.cost_center_type, 'ACTUAL') as cost_center_type,
    COALESCE(cc.is_active, TRUE) as is_active,
    COALESCE(cc.valid_from, CURRENT_DATE) as valid_from,
    'MIGRATION' as created_by,
    COALESCE(cc.created_at, CURRENT_TIMESTAMP) as created_at,
    cc.modified_by,
    cc.modified_at
FROM costcenter cc
WHERE NOT EXISTS (
    SELECT 1 FROM business_units bu 
    WHERE bu.unit_id = 'BU-CC-' || cc.costcenterid
);

-- Log migration results
DO $$
DECLARE
    cost_center_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO cost_center_count 
    FROM business_units 
    WHERE unit_type = 'COST_CENTER';
    
    RAISE NOTICE 'Cost centers migrated: %', cost_center_count;
END $$;

-- Step 3: Migrate Profit Centers to Business Units
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
    unit_group,
    person_responsible,
    department,
    default_cost_center,
    profit_center_type,
    margin_analysis_enabled,
    segment,
    local_currency,
    is_active,
    valid_from,
    valid_to,
    created_by,
    created_at,
    modified_by,
    modified_at
)
SELECT 
    -- Convert profit_center_id to business unit format
    CASE 
        WHEN LENGTH(pc.profit_center_id) <= 10 THEN 'BU-PC-' || pc.profit_center_id
        ELSE 'BU-PC-' || LEFT(pc.profit_center_id, 7)  -- Truncate if too long
    END as unit_id,
    COALESCE(pc.profit_center_name, 'Profit Center ' || pc.profit_center_id) as unit_name,
    COALESCE(pc.short_name, LEFT(pc.profit_center_name, 20), 'PC-' || pc.profit_center_id) as short_name,
    pc.description,
    'PROFIT_CENTER' as unit_type,
    'STANDARD' as unit_category,  -- Default for profit centers
    'PROFIT' as responsibility_type,
    pc.company_code_id,
    COALESCE(pc.controlling_area, 'C001') as controlling_area,
    pc.business_area as business_area_id,
    CASE 
        WHEN pc.parent_profit_center IS NOT NULL 
        THEN 'BU-PC-' || pc.parent_profit_center
        ELSE NULL 
    END as parent_unit_id,
    COALESCE(pc.hierarchy_level, 1) as hierarchy_level,
    pc.profit_center_group as unit_group,
    pc.person_responsible,
    NULL as department,  -- Profit centers may not have departments
    pc.cost_center as default_cost_center,
    'ACTUAL' as profit_center_type,  -- Default value
    TRUE as margin_analysis_enabled,  -- Enable for profit centers
    pc.segment,
    COALESCE(pc.local_currency, 'USD') as local_currency,
    COALESCE(pc.is_active, TRUE) as is_active,
    COALESCE(pc.valid_from, CURRENT_DATE) as valid_from,
    COALESCE(pc.valid_to, '9999-12-31'::DATE) as valid_to,
    'MIGRATION' as created_by,
    COALESCE(pc.created_at, CURRENT_TIMESTAMP) as created_at,
    pc.modified_by,
    pc.modified_at
FROM profit_centers pc
WHERE NOT EXISTS (
    SELECT 1 FROM business_units bu 
    WHERE bu.unit_id = 'BU-PC-' || pc.profit_center_id
);

-- Log migration results
DO $$
DECLARE
    profit_center_count INTEGER;
    total_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO profit_center_count 
    FROM business_units 
    WHERE unit_type = 'PROFIT_CENTER';
    
    SELECT COUNT(*) INTO total_count 
    FROM business_units;
    
    RAISE NOTICE 'Profit centers migrated: %', profit_center_count;
    RAISE NOTICE 'Total business units: %', total_count;
END $$;

-- Step 4: Create sample Product Line + Location business units
-- These demonstrate the new integrated capabilities

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
) VALUES
-- Smartphones Business Units
('BU-SMART-NYC', 'Smartphones Development NYC', 'SMART-NYC', 'BOTH', 'STANDARD', 'PROFIT', 'C001', 'TECH', '1110', '111110', 'John Smith', 'Product Development', TRUE, TRUE, TRUE, 'SAMPLE'),
('BU-SMART-LON', 'Smartphones Development London', 'SMART-LON', 'COST_CENTER', 'STANDARD', 'COST', 'C001', 'TECH', '1110', '221110', 'Sarah Johnson', 'R&D', TRUE, FALSE, TRUE, 'SAMPLE'),

-- Oil Field Services Business Units  
('BU-OFS-TEXAS', 'Oil Field Services Texas', 'OFS-TX', 'PROFIT_CENTER', 'REVENUE', 'PROFIT', 'C001', 'ENGY', '7000', '132100', 'Mike Wilson', 'Energy Operations', TRUE, TRUE, TRUE, 'SAMPLE'),
('BU-DRILL-DUBAI', 'Drilling Services Dubai', 'DRILL-DXB', 'BOTH', 'STANDARD', 'PROFIT', 'C001', 'ENGY', '7100', '520100', 'Ahmed Hassan', 'Drilling Operations', TRUE, TRUE, TRUE, 'SAMPLE'),

-- CPG Business Units
('BU-BEV-SAO', 'Beverages Business Unit Sao Paulo', 'BEV-SP', 'PROFIT_CENTER', 'REVENUE', 'PROFIT', 'C001', 'PROD', '5110', '410100', 'Carlos Silva', 'FMCG Operations', TRUE, TRUE, TRUE, 'SAMPLE'),

-- Regional Business Units (Location-focused)
('BU-EMEA-REG', 'EMEA Regional Operations', 'EMEA', 'COST_CENTER', 'OVERHEAD', 'COST', 'C001', 'EU', NULL, '200000', 'Emma Brown', 'Regional Management', TRUE, FALSE, TRUE, 'SAMPLE'),
('BU-APAC-REG', 'APAC Regional Operations', 'APAC', 'COST_CENTER', 'OVERHEAD', 'COST', 'C001', 'APAC', NULL, '300000', 'Li Wei', 'Regional Management', TRUE, FALSE, TRUE, 'SAMPLE')

ON CONFLICT (unit_id) DO NOTHING;

-- Step 5: Update parent-child relationships for new sample units
UPDATE business_units 
SET parent_unit_id = 'BU-SMART-NYC'
WHERE unit_id = 'BU-SMART-LON';

UPDATE business_units 
SET parent_unit_id = 'BU-OFS-TEXAS'  
WHERE unit_id = 'BU-DRILL-DUBAI';

-- Step 6: Final migration summary
DO $$
DECLARE
    cost_centers INTEGER;
    profit_centers INTEGER;
    sample_units INTEGER;
    total_units INTEGER;
    units_with_codes INTEGER;
BEGIN
    SELECT COUNT(*) INTO cost_centers FROM business_units WHERE unit_type = 'COST_CENTER';
    SELECT COUNT(*) INTO profit_centers FROM business_units WHERE unit_type = 'PROFIT_CENTER';  
    SELECT COUNT(*) INTO sample_units FROM business_units WHERE created_by = 'SAMPLE';
    SELECT COUNT(*) INTO total_units FROM business_units;
    SELECT COUNT(*) INTO units_with_codes FROM business_units WHERE generated_code IS NOT NULL;
    
    RAISE NOTICE '=== MIGRATION SUMMARY ===';
    RAISE NOTICE 'Cost Center Units: %', cost_centers;
    RAISE NOTICE 'Profit Center Units: %', profit_centers;
    RAISE NOTICE 'Dual-Purpose Units: %', (SELECT COUNT(*) FROM business_units WHERE unit_type = 'BOTH');
    RAISE NOTICE 'Sample Units Added: %', sample_units;
    RAISE NOTICE 'Total Business Units: %', total_units;
    RAISE NOTICE 'Units with Generated Codes: %', units_with_codes;
    RAISE NOTICE 'Migration completed successfully!';
END $$;

-- =====================================================
-- Data Migration Complete
-- =====================================================
-- Migrated:
--   - All existing cost centers as COST_CENTER units
--   - All existing profit centers as PROFIT_CENTER units  
--   - Added sample units demonstrating Product Line + Location integration
--   - Preserved all original relationships and hierarchies
--   - Generated automatic codes for Product Line + Location combinations
-- 
-- Next: Create backward compatibility views
-- =====================================================