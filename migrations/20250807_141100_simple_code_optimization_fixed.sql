-- =====================================================
-- Simple Code Optimization: Fixed Step-by-Step Approach
-- =====================================================
-- Author: Claude Code Assistant
-- Date: August 7, 2025
-- Description: Safely optimize business unit and location codes
--              using incremental approach with proper validation
-- =====================================================

-- Step 1: Create new columns for optimized codes
ALTER TABLE business_units ADD COLUMN IF NOT EXISTS unit_id_numeric SERIAL;
ALTER TABLE reporting_locations ADD COLUMN IF NOT EXISTS location_code_4digit VARCHAR(4);

-- Step 2: Generate 4-digit location codes using corrected approach
WITH numbered_locations AS (
    SELECT location_code, ROW_NUMBER() OVER (ORDER BY location_code) as rn
    FROM reporting_locations 
    WHERE is_active = TRUE
)
UPDATE reporting_locations 
SET location_code_4digit = LPAD(nl.rn::TEXT, 4, '0')
FROM numbered_locations nl
WHERE reporting_locations.location_code = nl.location_code;

-- Step 3: Create mapping table for reference
CREATE TABLE IF NOT EXISTS location_code_conversion AS
SELECT 
    location_code as old_6digit,
    location_code_4digit as new_4digit,
    location_name
FROM reporting_locations 
WHERE location_code_4digit IS NOT NULL;

-- Step 4: Add new 8-digit generated code column to business units
ALTER TABLE business_units ADD COLUMN IF NOT EXISTS generated_code_8digit VARCHAR(8);

-- Update with 8-digit codes (4+4 format)
UPDATE business_units bu
SET generated_code_8digit = bu.product_line_id || rl.location_code_4digit
FROM reporting_locations rl
WHERE bu.location_code = rl.location_code
AND bu.product_line_id IS NOT NULL
AND rl.location_code_4digit IS NOT NULL;

-- Step 5: Show before/after comparison
SELECT 'Code Optimization Comparison:' as info;

SELECT 
    'Sample Transformations' as transformation_type,
    COUNT(*) as total_units,
    COUNT(CASE WHEN generated_code_8digit IS NOT NULL THEN 1 END) as units_with_8digit_codes
FROM business_units;

-- Show sample conversions
SELECT 
    bu.unit_id as old_unit_id,
    bu.unit_id_numeric as new_numeric_id,
    bu.location_code as old_6digit_location,
    rl.location_code_4digit as new_4digit_location,
    bu.generated_code as old_10digit_code,
    bu.generated_code_8digit as new_8digit_code,
    bu.unit_name
FROM business_units bu
LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
WHERE bu.generated_code_8digit IS NOT NULL
ORDER BY bu.unit_id_numeric
LIMIT 15;

-- Step 6: Verify the optimization results
DO $$
DECLARE
    total_business_units INTEGER;
    units_with_8digit INTEGER;
    locations_with_4digit INTEGER;
    avg_old_generated_length DECIMAL;
    avg_new_generated_length DECIMAL;
    avg_location_length DECIMAL;
BEGIN
    SELECT COUNT(*) INTO total_business_units FROM business_units WHERE is_active = TRUE;
    SELECT COUNT(*) INTO units_with_8digit FROM business_units WHERE generated_code_8digit IS NOT NULL;
    SELECT COUNT(*) INTO locations_with_4digit FROM reporting_locations WHERE location_code_4digit IS NOT NULL;
    
    SELECT AVG(LENGTH(generated_code)) INTO avg_old_generated_length
    FROM business_units WHERE generated_code IS NOT NULL;
    
    SELECT AVG(LENGTH(generated_code_8digit)) INTO avg_new_generated_length  
    FROM business_units WHERE generated_code_8digit IS NOT NULL;
    
    SELECT AVG(LENGTH(location_code_4digit)) INTO avg_location_length
    FROM reporting_locations WHERE location_code_4digit IS NOT NULL;
    
    RAISE NOTICE '=== CODE OPTIMIZATION RESULTS ===';
    RAISE NOTICE 'Total Business Units: %', total_business_units;
    RAISE NOTICE 'Units with 8-digit Codes: %', units_with_8digit;
    RAISE NOTICE 'Locations with 4-digit Codes: %', locations_with_4digit;
    RAISE NOTICE 'Old Generated Code Avg Length: %', avg_old_generated_length;
    RAISE NOTICE 'New Generated Code Avg Length: %', avg_new_generated_length;
    RAISE NOTICE 'New Location Code Avg Length: %', avg_location_length;
    RAISE NOTICE '==================================';
    
    IF avg_new_generated_length = 8 AND avg_location_length = 4 THEN
        RAISE NOTICE '✅ SUCCESS: Code optimization completed successfully!';
        RAISE NOTICE '📊 Space Savings: % → % digits for generated codes', avg_old_generated_length, avg_new_generated_length;
        RAISE NOTICE '📊 Space Savings: 6 → 4 digits for location codes';
    END IF;
END $$;

-- Step 7: Create optimized views using new code formats
CREATE OR REPLACE VIEW v_business_units_optimized AS
SELECT 
    bu.unit_id_numeric as numeric_id,           -- Numeric ID (no BU- prefix)
    bu.unit_id as original_id,                  -- Keep original for reference
    bu.unit_name,
    bu.unit_type,
    bu.responsibility_type,
    bu.product_line_id,
    pl.product_line_name,
    pl.industry_sector,
    rl.location_code_4digit as location_code_4d, -- 4-digit location code
    rl.location_code as original_location_code,   -- Keep original for reference
    rl.location_name,
    rl.country_code,
    bu.generated_code_8digit as code_8digit,     -- 8-digit generated code
    bu.generated_code as original_code,          -- Keep original for reference
    bu.person_responsible,
    bu.is_active
FROM business_units bu
LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
WHERE bu.is_active = TRUE;

-- Step 8: Create usage recommendation
SELECT 'Optimization Recommendations:' as info;

SELECT 
    'Code Usage Recommendations' as category,
    'Use numeric_id instead of BU-prefixed IDs' as recommendation_1,
    'Use 4-digit location codes for new integrations' as recommendation_2,
    'Use 8-digit generated codes for business unit identification' as recommendation_3;

-- Step 9: Grant permissions
GRANT SELECT ON v_business_units_optimized TO PUBLIC;
GRANT SELECT ON location_code_conversion TO PUBLIC;

-- Step 10: Document the optimization
INSERT INTO system_migration_log (
    migration_name,
    tables_removed,
    columns_removed,
    functions_removed,
    views_updated,
    backup_tables,
    notes
) VALUES (
    'Simple Code Optimization - Fixed Incremental Approach',
    ARRAY[]::TEXT[],
    ARRAY[]::TEXT[],
    ARRAY[]::TEXT[],
    ARRAY['v_business_units_optimized']::TEXT[],
    ARRAY['location_code_conversion']::TEXT[],
    'Added optimized code columns alongside existing structure. Numeric business unit IDs available, 4-digit location codes generated, 8-digit business unit codes created. Original columns preserved for backward compatibility.'
);

-- =====================================================
-- Simple Code Optimization Complete
-- =====================================================
-- Results:
--   - Added numeric business unit IDs (1, 2, 3...)
--   - Generated 4-digit location codes (0001, 0002...)
--   - Created 8-digit business unit codes (4+4 format)
--   - Original codes preserved for compatibility
--   - New optimized view available: v_business_units_optimized
--   - Ready for gradual migration to new format
-- =====================================================