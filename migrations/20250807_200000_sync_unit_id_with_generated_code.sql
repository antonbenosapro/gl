-- Migration: Sync unit_id with generated_code for Business Units
-- Date: August 7, 2025
-- Purpose: Fix design mistake where unit_id should match generated_code (product_line_id + location_code)

-- WARNING: This is a complex migration that affects foreign key relationships
-- Execute in maintenance window with application offline

BEGIN;

-- Step 1: Create a mapping table for old unit_id to new unit_id (generated_code)
CREATE TEMPORARY TABLE unit_id_mapping AS
SELECT 
    unit_id as old_unit_id,
    CASE 
        WHEN generated_code IS NOT NULL AND generated_code != '' 
        THEN generated_code::integer
        ELSE unit_id  -- Keep existing unit_id if no generated_code
    END as new_unit_id,
    generated_code,
    unit_name
FROM business_units
WHERE generated_code IS NOT NULL AND generated_code != ''
ORDER BY unit_id;

-- Step 2: Show mapping for review
SELECT 'UNIT_ID_MAPPING' as step, old_unit_id, new_unit_id, generated_code, unit_name 
FROM unit_id_mapping 
LIMIT 10;

-- Step 3: Disable foreign key constraints temporarily
SET session_replication_role = replica;

-- Step 4: Update business_units table first
UPDATE business_units 
SET unit_id = m.new_unit_id::integer
FROM unit_id_mapping m 
WHERE business_units.unit_id = m.old_unit_id
  AND m.new_unit_id != m.old_unit_id;

-- Step 5: Update journalentryline foreign key references
UPDATE journalentryline jel
SET business_unit_id = m.new_unit_id
FROM unit_id_mapping m
WHERE jel.business_unit_id = m.old_unit_id
  AND m.new_unit_id != m.old_unit_id;

-- Step 6: Update glaccount foreign key references
UPDATE glaccount ga
SET default_business_unit = m.new_unit_id
FROM unit_id_mapping m
WHERE ga.default_business_unit = m.old_unit_id
  AND m.new_unit_id != m.old_unit_id;

-- Step 7: Update product_lines foreign key references  
UPDATE product_lines pl
SET default_business_unit = m.new_unit_id
FROM unit_id_mapping m
WHERE pl.default_business_unit = m.old_unit_id
  AND m.new_unit_id != m.old_unit_id;

-- Step 8: Update business_units parent relationships
UPDATE business_units bu
SET parent_unit_id = m.new_unit_id
FROM unit_id_mapping m
WHERE bu.parent_unit_id = m.old_unit_id
  AND m.new_unit_id != m.old_unit_id;

-- Step 9: Re-enable foreign key constraints
SET session_replication_role = DEFAULT;

-- Step 10: Verify the changes
SELECT 'VERIFICATION' as step, 
       COUNT(*) as total_units,
       COUNT(CASE WHEN unit_id::text = generated_code THEN 1 END) as matching_units,
       COUNT(CASE WHEN unit_id::text != generated_code THEN 1 END) as non_matching_units
FROM business_units 
WHERE generated_code IS NOT NULL AND generated_code != '';

-- Step 11: Show sample of updated records
SELECT 'SAMPLE_RESULTS' as step, unit_id, generated_code, unit_name 
FROM business_units 
WHERE generated_code IS NOT NULL AND generated_code != '' 
  AND unit_id::text = generated_code
LIMIT 10;

COMMIT;

-- Note: This migration should be tested thoroughly in a development environment first
-- The foreign key updates are complex and could affect data integrity if not done carefully