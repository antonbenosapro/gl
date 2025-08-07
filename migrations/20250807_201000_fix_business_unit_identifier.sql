-- SAFER APPROACH: Fix Business Unit Identifier Design
-- Instead of changing unit_id (complex foreign key updates), 
-- we'll standardize on using generated_code as the business unit identifier

BEGIN;

-- Step 1: Ensure all business units have generated_code populated
UPDATE business_units 
SET generated_code = LPAD(product_line_id::text, 4, '0') || LPAD(location_code::text, 6, '0')
WHERE generated_code IS NULL 
  AND product_line_id IS NOT NULL 
  AND location_code IS NOT NULL;

-- Step 2: For records without product_line_id or location_code, use unit_id as generated_code
UPDATE business_units 
SET generated_code = LPAD(unit_id::text, 10, '0')
WHERE generated_code IS NULL OR generated_code = '';

-- Step 3: Create a view that uses generated_code as the primary identifier
CREATE OR REPLACE VIEW business_units_by_code AS
SELECT 
    generated_code as business_unit_code,
    unit_id,
    unit_name,
    short_name,
    description,
    unit_type,
    unit_category,
    product_line_id,
    location_code,
    is_active
FROM business_units
WHERE generated_code IS NOT NULL AND generated_code <> '';

-- Step 4: Update the Journal Entry Manager to use generated_code
-- (This will be done in the application code)

-- Step 5: Verify the fix
SELECT 
    'VERIFICATION' as step,
    COUNT(*) as total_units,
    COUNT(CASE WHEN generated_code IS NOT NULL AND generated_code <> '' THEN 1 END) as with_generated_code,
    MIN(LENGTH(generated_code)) as min_code_length,
    MAX(LENGTH(generated_code)) as max_code_length
FROM business_units;

-- Step 6: Show sample of business units with their codes
SELECT 
    'SAMPLE' as step,
    unit_id,
    generated_code as business_unit_code,
    unit_name,
    product_line_id,
    location_code
FROM business_units 
WHERE generated_code IS NOT NULL 
ORDER BY unit_id 
LIMIT 10;

COMMIT;