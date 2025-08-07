-- Migration: Update Field Status Groups to use Business Unit instead of separate Cost/Profit Center
-- Date: August 7, 2025
-- Purpose: Consolidate cost_center_status and profit_center_status into business_unit_status

-- Step 1: Add new business_unit_status column
ALTER TABLE field_status_groups 
ADD COLUMN IF NOT EXISTS business_unit_status VARCHAR(10) DEFAULT 'OPT' 
CHECK (business_unit_status IN ('SUP', 'REQ', 'OPT', 'DIS'));

-- Step 2: Migrate existing data
-- Logic: If either cost_center or profit_center was required, make business_unit required
-- If both were suppressed, suppress business_unit
-- Otherwise keep as optional
UPDATE field_status_groups
SET business_unit_status = 
    CASE 
        WHEN cost_center_status = 'REQ' OR profit_center_status = 'REQ' THEN 'REQ'
        WHEN cost_center_status = 'SUP' AND profit_center_status = 'SUP' THEN 'SUP'
        WHEN cost_center_status = 'DIS' OR profit_center_status = 'DIS' THEN 'DIS'
        ELSE 'OPT'
    END;

-- Step 3: Drop the old columns
ALTER TABLE field_status_groups 
DROP COLUMN IF EXISTS cost_center_status,
DROP COLUMN IF EXISTS profit_center_status;

-- Step 4: Update existing field status groups with proper business unit requirements
UPDATE field_status_groups SET business_unit_status = 'SUP' WHERE group_id IN ('ASSET01');
UPDATE field_status_groups SET business_unit_status = 'REQ' WHERE group_id IN ('RECV01', 'PAYB01');
UPDATE field_status_groups SET business_unit_status = 'REQ' WHERE group_id IN ('REV01', 'EXP01', 'COGS01');
UPDATE field_status_groups SET business_unit_status = 'REQ' WHERE group_id IN ('FIN01', 'INTER01');
UPDATE field_status_groups SET business_unit_status = 'OPT' WHERE group_id IN ('TAX01', 'BANK01');
UPDATE field_status_groups SET business_unit_status = 'SUP' WHERE group_id IN ('STAT01');

-- Step 5: Add index for the new column
CREATE INDEX IF NOT EXISTS idx_field_status_groups_business_unit ON field_status_groups(business_unit_status);

-- Step 6: Add comment to document the change
COMMENT ON COLUMN field_status_groups.business_unit_status IS 'Unified field status control for business units (replacing separate cost/profit center controls)';

-- Log the migration
INSERT INTO system_migration_log (migration_name, status, details, executed_by)
VALUES ('Update Field Status Groups to Business Units', 'SUCCESS', 
        'Consolidated cost_center_status and profit_center_status into business_unit_status', 
        'SYSTEM');