-- =====================================================
-- Complete Location Code Trimming: Final Migration
-- =====================================================
-- Author: Claude Code Assistant
-- Date: August 7, 2025
-- Description: Complete the transition from 6-digit to 4-digit location codes
--              by updating primary keys and all foreign key references
-- =====================================================

-- Step 1: Create backup of current state
CREATE TABLE IF NOT EXISTS location_codes_final_backup AS 
    SELECT *, CURRENT_TIMESTAMP as backup_created_at FROM reporting_locations;

CREATE TABLE IF NOT EXISTS business_units_final_backup AS 
    SELECT *, CURRENT_TIMESTAMP as backup_created_at FROM business_units;

-- Step 2: Update business_units to reference 4-digit location codes
UPDATE business_units bu
SET location_code = rl.location_code_4digit
FROM reporting_locations rl
WHERE bu.location_code = rl.location_code
AND rl.location_code_4digit IS NOT NULL;

-- Step 3: Drop foreign key constraint temporarily
ALTER TABLE business_units DROP CONSTRAINT IF EXISTS fk_business_units_new_location;
ALTER TABLE business_units DROP CONSTRAINT IF EXISTS fk_business_units_location;

-- Step 4: Update parent location references in reporting_locations
-- First, create a mapping of old to new codes
CREATE TEMPORARY TABLE location_mapping AS
SELECT 
    location_code as old_code,
    location_code_4digit as new_code
FROM reporting_locations
WHERE location_code_4digit IS NOT NULL;

-- Update parent location references to use 4-digit codes
UPDATE reporting_locations rl
SET parent_location_code = lm.new_code
FROM location_mapping lm
WHERE rl.parent_location_code = lm.old_code;

-- Step 5: Update the primary location_code column to 4-digit format
UPDATE reporting_locations 
SET location_code = location_code_4digit
WHERE location_code_4digit IS NOT NULL;

-- Step 6: Drop the temporary 4-digit column since it's now the primary
ALTER TABLE reporting_locations DROP COLUMN IF EXISTS location_code_4digit;

-- Step 7: Update column constraints to 4-digit format
ALTER TABLE reporting_locations ALTER COLUMN location_code TYPE VARCHAR(4);
ALTER TABLE business_units ALTER COLUMN location_code TYPE VARCHAR(4);

-- Step 8: Recreate foreign key constraints with new 4-digit format
ALTER TABLE business_units 
ADD CONSTRAINT fk_business_units_location 
    FOREIGN KEY (location_code) REFERENCES reporting_locations(location_code);

-- Self-referencing constraint for location hierarchy
ALTER TABLE reporting_locations DROP CONSTRAINT IF EXISTS fk_reporting_locations_new_parent;
ALTER TABLE reporting_locations DROP CONSTRAINT IF EXISTS fk_reporting_locations_parent;
ALTER TABLE reporting_locations 
ADD CONSTRAINT fk_reporting_locations_parent 
    FOREIGN KEY (parent_location_code) REFERENCES reporting_locations(location_code);

-- Step 9: Update generated codes to use new 4-digit format
UPDATE business_units 
SET generated_code = product_line_id || location_code
WHERE product_line_id IS NOT NULL AND location_code IS NOT NULL;

-- Also update the 8-digit codes
UPDATE business_units 
SET generated_code_8digit = product_line_id || location_code
WHERE product_line_id IS NOT NULL AND location_code IS NOT NULL;

-- Step 10: Update the generated column definition and triggers
DROP TRIGGER IF EXISTS tr_business_units_generated_code ON business_units;

CREATE OR REPLACE FUNCTION update_business_unit_generated_code()
RETURNS TRIGGER AS $$
BEGIN
    -- Update both generated code formats
    NEW.generated_code := CASE 
        WHEN NEW.product_line_id IS NOT NULL AND NEW.location_code IS NOT NULL 
        THEN NEW.product_line_id || NEW.location_code
        ELSE NULL
    END;
    
    NEW.generated_code_8digit := CASE 
        WHEN NEW.product_line_id IS NOT NULL AND NEW.location_code IS NOT NULL 
        THEN NEW.product_line_id || NEW.location_code
        ELSE NULL
    END;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_business_units_generated_code
    BEFORE INSERT OR UPDATE OF product_line_id, location_code ON business_units
    FOR EACH ROW 
    EXECUTE FUNCTION update_business_unit_generated_code();

-- Step 11: Update views to reflect final 4-digit codes
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
    bu.location_code as location_code_4d,       -- Now 4-digit primary code
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

-- Step 12: Update other views
CREATE OR REPLACE VIEW v_business_units_with_dimensions AS
SELECT 
    bu.unit_id,
    bu.unit_name,
    bu.unit_type,
    bu.responsibility_type,
    bu.product_line_id,
    pl.product_line_name,
    pl.industry_sector,
    bu.location_code,                           -- Now 4-digit
    rl.location_name,
    rl.country_code,
    rl.location_level,
    bu.generated_code as business_code_8digit,   -- Now 8-digit
    bu.person_responsible,
    bu.is_active
FROM business_units bu
LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
WHERE bu.is_active = TRUE;

-- Step 13: Verify the final results
DO $$
DECLARE
    locations_4digit INTEGER;
    business_units_with_4digit INTEGER;
    avg_location_length DECIMAL;
    avg_generated_length DECIMAL;
    sample_codes TEXT[];
BEGIN
    -- Count locations with 4-digit codes
    SELECT COUNT(*) INTO locations_4digit 
    FROM reporting_locations 
    WHERE LENGTH(location_code) = 4 AND is_active = TRUE;
    
    -- Count business units with 4-digit location codes
    SELECT COUNT(*) INTO business_units_with_4digit 
    FROM business_units 
    WHERE LENGTH(location_code) = 4 AND location_code IS NOT NULL;
    
    -- Get average lengths
    SELECT AVG(LENGTH(location_code)) INTO avg_location_length 
    FROM reporting_locations WHERE is_active = TRUE;
    
    SELECT AVG(LENGTH(generated_code)) INTO avg_generated_length 
    FROM business_units WHERE generated_code IS NOT NULL;
    
    -- Get sample codes
    SELECT ARRAY_AGG(location_code || ' → ' || generated_code) INTO sample_codes
    FROM (
        SELECT location_code, generated_code 
        FROM business_units 
        WHERE generated_code IS NOT NULL 
        LIMIT 5
    ) samples;
    
    RAISE NOTICE '=== LOCATION CODE TRIMMING FINAL RESULTS ===';
    RAISE NOTICE 'Locations with 4-digit codes: %', locations_4digit;
    RAISE NOTICE 'Business Units with 4-digit location codes: %', business_units_with_4digit;
    RAISE NOTICE 'Average location code length: %', avg_location_length;
    RAISE NOTICE 'Average generated code length: %', avg_generated_length;
    RAISE NOTICE 'Sample location → business codes: %', array_to_string(sample_codes, ', ');
    RAISE NOTICE '==========================================';
    
    IF avg_location_length = 4 AND avg_generated_length = 8 THEN
        RAISE NOTICE '✅ SUCCESS: Location code trimming completed successfully!';
        RAISE NOTICE '✅ All location codes are now 4-digit format';
        RAISE NOTICE '✅ All business unit codes are now 8-digit format';
        RAISE NOTICE '✅ All foreign key relationships updated';
    END IF;
END $$;

-- Step 14: Show sample of final structure
SELECT 'Final Location Code Structure:' as info;

SELECT 
    rl.location_code as code_4digit,
    rl.location_name,
    rl.location_level,
    rl.country_code,
    COUNT(bu.unit_id) as business_units_count
FROM reporting_locations rl
LEFT JOIN business_units bu ON rl.location_code = bu.location_code
WHERE rl.is_active = TRUE
GROUP BY rl.location_code, rl.location_name, rl.location_level, rl.country_code
ORDER BY rl.location_code
LIMIT 15;

-- Step 15: Document the migration
INSERT INTO system_migration_log (
    migration_name,
    tables_removed,
    columns_removed, 
    functions_removed,
    views_updated,
    backup_tables,
    notes
) VALUES (
    'Complete Location Code Trimming - Final Migration',
    ARRAY[]::TEXT[],
    ARRAY['reporting_locations.location_code_4digit']::TEXT[],
    ARRAY[]::TEXT[],
    ARRAY['v_business_units_optimized', 'v_business_units_with_dimensions']::TEXT[],
    ARRAY['location_codes_final_backup', 'business_units_final_backup']::TEXT[],
    'Completed transition from 6-digit to 4-digit location codes. Updated primary keys, foreign key constraints, generated codes, and all views. All location codes and business unit codes now use optimized 4-digit and 8-digit formats respectively.'
);

-- =====================================================
-- Location Code Trimming Complete
-- =====================================================
-- Results:
--   ✅ Location codes: 6-digit → 4-digit (primary column)
--   ✅ Business unit location references: Updated to 4-digit
--   ✅ Generated codes: Now 8-digit format (4+4)
--   ✅ Foreign key constraints: Updated for 4-digit format  
--   ✅ Views: Updated to reflect new code structure
--   ✅ Triggers: Updated for new code generation
-- =====================================================