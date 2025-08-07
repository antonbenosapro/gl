-- Migration: Update Field Status Groups to use Business Unit instead of separate Cost/Profit Center (FIXED)
-- Date: August 7, 2025
-- Purpose: Consolidate cost_center_status and profit_center_status into business_unit_status

-- Step 1: Drop dependent view first
DROP VIEW IF EXISTS v_field_status_summary CASCADE;

-- Step 2: Add new business_unit_status column (if not exists)
ALTER TABLE field_status_groups 
ADD COLUMN IF NOT EXISTS business_unit_status VARCHAR(10) DEFAULT 'OPT' 
CHECK (business_unit_status IN ('SUP', 'REQ', 'OPT', 'DIS'));

-- Step 3: Migrate existing data - Copy profit_center_status to business_unit_status
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns 
               WHERE table_name = 'field_status_groups' 
               AND column_name = 'profit_center_status') THEN
        
        -- Copy profit_center_status exactly to business_unit_status as per user requirement
        UPDATE field_status_groups
        SET business_unit_status = profit_center_status;
    END IF;
END $$;

-- Step 4: Drop the old columns (if they exist)
ALTER TABLE field_status_groups 
DROP COLUMN IF EXISTS cost_center_status CASCADE,
DROP COLUMN IF EXISTS profit_center_status CASCADE;

-- Step 5: Business unit status is already set from profit_center_status copy above
-- No additional updates needed since we're copying profit_center_status exactly

-- Step 6: Recreate the view with business_unit_status
CREATE OR REPLACE VIEW v_field_status_summary AS
SELECT 
    group_id,
    group_name,
    group_description,
    business_unit_status,
    business_area_status,
    tax_code_status,
    reference_field_status,
    document_header_text_status,
    is_active
FROM field_status_groups;

-- Step 7: Add index for the new column
CREATE INDEX IF NOT EXISTS idx_field_status_groups_business_unit ON field_status_groups(business_unit_status);

-- Step 8: Add comment to document the change
COMMENT ON COLUMN field_status_groups.business_unit_status IS 'Unified field status control for business units (replacing separate cost/profit center controls)';

-- Log the migration (create log table if doesn't exist)
CREATE TABLE IF NOT EXISTS system_migration_log (
    id SERIAL PRIMARY KEY,
    migration_name VARCHAR(255),
    migration_status VARCHAR(50),
    details TEXT,
    executed_by VARCHAR(100),
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO system_migration_log (migration_name, migration_status, details, executed_by)
VALUES ('Update Field Status Groups to Business Units', 'SUCCESS', 
        'Consolidated cost_center_status and profit_center_status into business_unit_status', 
        'SYSTEM');