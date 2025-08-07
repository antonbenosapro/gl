-- Simple Business Unit Code Column Rename
-- Rename generated_code to business_unit_code for clarity

BEGIN;

-- Step 1: Add new column
ALTER TABLE business_units ADD COLUMN business_unit_code VARCHAR(20);

-- Step 2: Copy data from generated_code to business_unit_code
UPDATE business_units SET business_unit_code = generated_code;

-- Step 3: Create index on new column
CREATE INDEX idx_business_units_business_unit_code ON business_units(business_unit_code);

-- Step 4: Add unique constraint
ALTER TABLE business_units ADD CONSTRAINT uk_business_units_business_unit_code UNIQUE (business_unit_code);

-- Step 5: Verify the data
SELECT 'VERIFICATION' as step, COUNT(*) as total, COUNT(business_unit_code) as with_code FROM business_units;

-- Step 6: Show sample
SELECT 'SAMPLE' as step, unit_id, business_unit_code, unit_name FROM business_units LIMIT 5;

COMMIT;