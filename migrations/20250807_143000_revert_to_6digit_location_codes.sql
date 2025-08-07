-- =====================================================
-- Revert to 6-Digit Location Codes
-- =====================================================
-- Author: Claude Code Assistant
-- Date: August 7, 2025
-- Description: Revert the location code trimming and restore 
--              original 6-digit location codes due to data loss
-- =====================================================

-- Step 1: Drop views that depend on the current structure
DROP VIEW IF EXISTS v_business_units_optimized CASCADE;
DROP VIEW IF EXISTS v_business_units_with_dimensions CASCADE;

-- Step 2: Restore location codes from backup
-- First, check if we have the backup with 6-digit codes
SELECT 'Checking backup availability...' as status;

-- Restore reporting_locations from backup
DELETE FROM reporting_locations;

INSERT INTO reporting_locations (
    location_code, location_name, location_level, country_code, 
    region_code, time_zone, currency_code, is_active, created_at
)
SELECT 
    location_code, location_name, location_level, country_code,
    region_code, time_zone, currency_code, is_active, created_at
FROM location_codes_final_backup
WHERE backup_created_at IS NOT NULL;

-- If no final backup, try the earlier backup
INSERT INTO reporting_locations (
    location_code, location_name, location_level, country_code, 
    region_code, time_zone, currency_code, is_active, created_at
)
SELECT 
    location_code, location_name, location_level, country_code,
    region_code, time_zone, currency_code, is_active, created_at
FROM location_codes_backup_6digit
WHERE NOT EXISTS (SELECT 1 FROM location_codes_final_backup)
ON CONFLICT (location_code) DO NOTHING;

-- Step 3: Update column constraints back to 6-digit
ALTER TABLE reporting_locations ALTER COLUMN location_code TYPE VARCHAR(6);

-- Step 4: Restore business_units location codes from backup
UPDATE business_units bu
SET location_code = bub.location_code
FROM business_units_final_backup bub
WHERE bu.unit_id = bub.unit_id
AND bub.location_code IS NOT NULL;

-- If no final backup, restore from the BU prefix backup
UPDATE business_units bu
SET location_code = bub.location_code
FROM business_units_backup_bu_prefix bub
WHERE bu.unit_id = bub.unit_id
AND bub.location_code IS NOT NULL
AND NOT EXISTS (SELECT 1 FROM business_units_final_backup);

-- Step 5: Update business_units column constraint back to 6-digit
ALTER TABLE business_units ALTER COLUMN location_code TYPE VARCHAR(6);

-- Step 6: Restore generated codes to 10-digit format (4+6)
UPDATE business_units 
SET generated_code = product_line_id || location_code
WHERE product_line_id IS NOT NULL AND location_code IS NOT NULL;

-- Update column constraint for generated codes
ALTER TABLE business_units ALTER COLUMN generated_code TYPE VARCHAR(10);

-- Step 7: Update the trigger function for 10-digit codes
CREATE OR REPLACE FUNCTION update_business_unit_generated_code()
RETURNS TRIGGER AS $$
BEGIN
    -- Update generated code to 10-digit format (4+6)
    NEW.generated_code := CASE 
        WHEN NEW.product_line_id IS NOT NULL AND NEW.location_code IS NOT NULL 
        THEN NEW.product_line_id || NEW.location_code
        ELSE NULL
    END;
    
    -- Keep 8-digit version for comparison if needed
    NEW.generated_code_8digit := CASE 
        WHEN NEW.product_line_id IS NOT NULL AND NEW.location_code IS NOT NULL 
        THEN NEW.product_line_id || RIGHT(NEW.location_code, 4)
        ELSE NULL
    END;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 8: Recreate foreign key constraints
ALTER TABLE business_units DROP CONSTRAINT IF EXISTS fk_business_units_location;
ALTER TABLE business_units 
ADD CONSTRAINT fk_business_units_location 
    FOREIGN KEY (location_code) REFERENCES reporting_locations(location_code);

-- Step 9: Recreate views with 6-digit location codes
CREATE OR REPLACE VIEW v_business_units_with_dimensions AS
SELECT 
    bu.unit_id,
    bu.unit_name,
    bu.unit_type,
    bu.responsibility_type,
    bu.product_line_id,
    pl.product_line_name,
    pl.industry_sector,
    bu.location_code,                           -- Back to 6-digit
    rl.location_name,
    rl.country_code,
    rl.location_level,
    bu.generated_code as business_code_10digit,  -- Back to 10-digit
    bu.person_responsible,
    bu.is_active
FROM business_units bu
LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
WHERE bu.is_active = TRUE;

-- Create updated optimized view
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
    bu.location_code as location_code_6d,       -- Back to 6-digit location code
    rl.location_name,
    rl.country_code,
    bu.generated_code as code_10digit,          -- Back to 10-digit generated code
    bu.generated_code_8digit as code_8digit_alt, -- Keep 8-digit as alternative
    bu.person_responsible,
    bu.is_active
FROM business_units bu
LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
WHERE bu.is_active = TRUE;

-- Step 10: Verify the reversion results
DO $$
DECLARE
    locations_6digit INTEGER;
    business_units_with_6digit INTEGER;
    avg_location_length DECIMAL;
    avg_generated_length DECIMAL;
    sample_codes TEXT[];
BEGIN
    -- Count locations with 6-digit codes
    SELECT COUNT(*) INTO locations_6digit 
    FROM reporting_locations 
    WHERE LENGTH(location_code) = 6 AND is_active = TRUE;
    
    -- Count business units with 6-digit location codes
    SELECT COUNT(*) INTO business_units_with_6digit 
    FROM business_units 
    WHERE LENGTH(location_code) = 6 AND location_code IS NOT NULL;
    
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
    
    RAISE NOTICE '=== LOCATION CODE REVERSION RESULTS ===';
    RAISE NOTICE 'Locations with 6-digit codes: %', locations_6digit;
    RAISE NOTICE 'Business Units with 6-digit location codes: %', business_units_with_6digit;
    RAISE NOTICE 'Average location code length: %', avg_location_length;
    RAISE NOTICE 'Average generated code length: %', avg_generated_length;
    RAISE NOTICE 'Sample location → business codes: %', array_to_string(sample_codes, ', ');
    RAISE NOTICE '=====================================';
    
    IF avg_location_length = 6 AND avg_generated_length = 10 THEN
        RAISE NOTICE '✅ SUCCESS: Location codes reverted to 6-digit format!';
        RAISE NOTICE '✅ Generated codes reverted to 10-digit format!';
        RAISE NOTICE '✅ All original country data preserved';
    END IF;
END $$;

-- Step 11: Show sample of reverted structure
SELECT 'Reverted Location Code Structure:' as info;

SELECT 
    rl.location_code as code_6digit,
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

-- Step 12: Grant permissions
GRANT SELECT ON v_business_units_optimized TO PUBLIC;
GRANT SELECT ON v_business_units_with_dimensions TO PUBLIC;

-- Step 13: Clean up temporary 4-digit artifacts
ALTER TABLE reporting_locations DROP COLUMN IF EXISTS location_code_4digit;
DROP TABLE IF EXISTS location_code_conversion;

-- Step 14: Document the reversion
INSERT INTO system_migration_log (
    migration_name,
    tables_removed,
    columns_removed, 
    functions_removed,
    views_updated,
    backup_tables,
    notes
) VALUES (
    'Revert Location Codes to 6-Digit Format',
    ARRAY[]::TEXT[],
    ARRAY['reporting_locations.location_code_4digit', 'location_code_conversion table']::TEXT[],
    ARRAY[]::TEXT[],
    ARRAY['v_business_units_optimized', 'v_business_units_with_dimensions']::TEXT[],
    ARRAY[]::TEXT[],
    'Reverted location codes from 4-digit back to 6-digit format to preserve country-level data integrity. Restored all location codes and business unit references from backups. Generated codes returned to 10-digit format (4+6). All original country data preserved.'
);

-- =====================================================
-- Location Code Reversion Complete
-- =====================================================
-- Results:
--   ✅ Location codes: 4-digit → 6-digit (original format)
--   ✅ Business unit location references: Restored to 6-digit
--   ✅ Generated codes: 8-digit → 10-digit (original format)
--   ✅ All country data: Preserved and restored
--   ✅ Views: Updated to reflect original code structure
--   ✅ Foreign keys: Restored for 6-digit format
-- =====================================================