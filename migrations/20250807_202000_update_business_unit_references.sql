-- Update Business Unit References to use Generated Code
-- This handles the design fix where business_unit_id should use generated_code format

BEGIN;

-- Step 1: Add a new column for generated_code reference in journalentryline
ALTER TABLE journalentryline 
ADD COLUMN IF NOT EXISTS business_unit_code VARCHAR(20);

-- Step 2: Populate business_unit_code from existing business_unit_id
UPDATE journalentryline jel
SET business_unit_code = bu.generated_code
FROM business_units bu
WHERE jel.business_unit_id = bu.unit_id
  AND bu.generated_code IS NOT NULL
  AND bu.generated_code <> '';

-- Step 3: Create index on the new column
CREATE INDEX IF NOT EXISTS idx_journalentryline_business_unit_code 
ON journalentryline(business_unit_code);

-- Step 4: Add foreign key constraint for the new column
ALTER TABLE journalentryline 
ADD CONSTRAINT fk_journalentryline_business_unit_code 
FOREIGN KEY (business_unit_code) REFERENCES business_units(generated_code);

-- Step 5: Create a view that shows both old and new business unit references
CREATE OR REPLACE VIEW journal_entry_line_enhanced AS
SELECT 
    jel.*,
    bu.unit_name as business_unit_name,
    bu.product_line_id,
    bu.location_code
FROM journalentryline jel
LEFT JOIN business_units bu ON (
    jel.business_unit_code = bu.generated_code 
    OR (jel.business_unit_code IS NULL AND jel.business_unit_id = bu.unit_id)
);

-- Step 6: Verify the migration
SELECT 
    'MIGRATION_VERIFICATION' as step,
    COUNT(*) as total_lines,
    COUNT(business_unit_id) as with_old_unit_id,
    COUNT(business_unit_code) as with_new_unit_code,
    COUNT(CASE WHEN business_unit_id IS NOT NULL AND business_unit_code IS NOT NULL THEN 1 END) as both_populated
FROM journalentryline;

-- Step 7: Show sample of migrated data
SELECT 
    'SAMPLE_DATA' as step,
    documentnumber,
    linenumber,
    business_unit_id as old_unit_id,
    business_unit_code as new_unit_code,
    description
FROM journalentryline 
WHERE business_unit_code IS NOT NULL
LIMIT 10;

COMMIT;

-- Note: The old business_unit_id column is kept for backwards compatibility
-- New applications should use business_unit_code
-- A future migration can remove business_unit_id once all applications are updated