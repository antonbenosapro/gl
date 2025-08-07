-- =====================================================
-- Simple Revert to 6-Digit Location Codes
-- =====================================================
-- Author: Claude Code Assistant
-- Date: August 7, 2025
-- Description: Direct reversion to 6-digit location codes using backup data
-- =====================================================

-- Step 1: Drop constraints and triggers temporarily
ALTER TABLE business_units DROP CONSTRAINT IF EXISTS fk_business_units_location;
DROP TRIGGER IF EXISTS tr_business_units_generated_code ON business_units;

-- Step 2: Update business_units to use original 6-digit location codes from backup
UPDATE business_units bu
SET location_code = bub.location_code
FROM reporting_locations_backup_6digit bub
INNER JOIN reporting_locations rl ON rl.location_name = bub.location_name
WHERE bu.location_code = rl.location_code;

-- Step 3: Clear current reporting_locations and restore from backup
TRUNCATE reporting_locations;

INSERT INTO reporting_locations (
    location_code, location_name, location_level, country_code, 
    time_zone, currency_code, is_active, created_at
)
SELECT 
    location_code, location_name, location_level, country_code,
    time_zone, currency_code, is_active, created_at
FROM reporting_locations_backup_6digit;

-- Step 4: Update column constraints to accommodate 6-digit codes
ALTER TABLE reporting_locations ALTER COLUMN location_code TYPE VARCHAR(6);
ALTER TABLE business_units ALTER COLUMN location_code TYPE VARCHAR(6);
ALTER TABLE business_units ALTER COLUMN generated_code TYPE VARCHAR(10);

-- Step 5: Update generated codes to 10-digit format (4+6)
UPDATE business_units 
SET generated_code = product_line_id || location_code
WHERE product_line_id IS NOT NULL AND location_code IS NOT NULL;

-- Step 6: Recreate the trigger function for 10-digit codes
CREATE OR REPLACE FUNCTION update_business_unit_generated_code()
RETURNS TRIGGER AS $$
BEGIN
    NEW.generated_code := CASE 
        WHEN NEW.product_line_id IS NOT NULL AND NEW.location_code IS NOT NULL 
        THEN NEW.product_line_id || NEW.location_code
        ELSE NULL
    END;
    
    NEW.generated_code_8digit := CASE 
        WHEN NEW.product_line_id IS NOT NULL AND NEW.location_code IS NOT NULL 
        THEN NEW.product_line_id || RIGHT(NEW.location_code, 4)
        ELSE NULL
    END;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 7: Recreate constraints and triggers
ALTER TABLE business_units 
ADD CONSTRAINT fk_business_units_location 
    FOREIGN KEY (location_code) REFERENCES reporting_locations(location_code);

CREATE TRIGGER tr_business_units_generated_code
    BEFORE INSERT OR UPDATE OF product_line_id, location_code ON business_units
    FOR EACH ROW 
    EXECUTE FUNCTION update_business_unit_generated_code();

-- Step 8: Update views
CREATE OR REPLACE VIEW v_business_units_optimized AS
SELECT 
    bu.unit_id_numeric as numeric_id,           
    bu.unit_id as original_id,                  
    bu.unit_name,
    bu.unit_type,
    bu.responsibility_type,
    bu.product_line_id,
    pl.product_line_name,
    pl.industry_sector,
    bu.location_code as location_code_6d,       -- 6-digit location code
    rl.location_name,
    rl.country_code,
    bu.generated_code as code_10digit,          -- 10-digit generated code
    bu.generated_code_8digit as code_8digit_alt,
    bu.person_responsible,
    bu.is_active
FROM business_units bu
LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
WHERE bu.is_active = TRUE;

-- Step 9: Verify results
DO $$
DECLARE
    locations_6digit INTEGER;
    business_units_10digit INTEGER;
    avg_location_length DECIMAL;
    avg_generated_length DECIMAL;
BEGIN
    SELECT COUNT(*) INTO locations_6digit 
    FROM reporting_locations WHERE LENGTH(location_code) = 6;
    
    SELECT COUNT(*) INTO business_units_10digit 
    FROM business_units WHERE LENGTH(generated_code) = 10 AND generated_code IS NOT NULL;
    
    SELECT AVG(LENGTH(location_code)) INTO avg_location_length 
    FROM reporting_locations WHERE is_active = TRUE;
    
    SELECT AVG(LENGTH(generated_code)) INTO avg_generated_length 
    FROM business_units WHERE generated_code IS NOT NULL;
    
    RAISE NOTICE '=== REVERSION TO 6-DIGIT COMPLETE ===';
    RAISE NOTICE 'Locations with 6-digit codes: %', locations_6digit;
    RAISE NOTICE 'Business Units with 10-digit codes: %', business_units_10digit;
    RAISE NOTICE 'Average location code length: %', avg_location_length;
    RAISE NOTICE 'Average generated code length: %', avg_generated_length;
    RAISE NOTICE '===================================';
    
    IF avg_location_length = 6 AND avg_generated_length = 10 THEN
        RAISE NOTICE '✅ SUCCESS: Reverted to 6-digit location codes!';
        RAISE NOTICE '✅ Reverted to 10-digit generated codes!';
    END IF;
END $$;

-- Step 10: Show sample of restored data
SELECT 'Restored 6-Digit Location Codes:' as info;

SELECT location_code, location_name, location_level, country_code 
FROM reporting_locations 
ORDER BY location_code 
LIMIT 15;

GRANT SELECT ON v_business_units_optimized TO PUBLIC;

-- =====================================================
-- Simple Revert Complete
-- =====================================================