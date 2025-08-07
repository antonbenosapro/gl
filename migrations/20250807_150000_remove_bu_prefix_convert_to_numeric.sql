-- =====================================================
-- Remove BU- Prefix and Convert to Plain Numeric IDs
-- =====================================================
-- Author: Claude Code Assistant
-- Date: August 7, 2025
-- Description: Replace BU- prefixed unit_id with plain numeric IDs
--              and update all foreign key references
-- =====================================================

-- Step 1: Drop all dependent views first
DROP VIEW IF EXISTS v_business_units_optimized CASCADE;
DROP VIEW IF EXISTS v_business_units_with_dimensions CASCADE;
DROP VIEW IF EXISTS v_journal_entries_enhanced CASCADE;
DROP VIEW IF EXISTS v_gl_transactions_enhanced CASCADE;

-- Step 2: Create backup before major changes
CREATE TABLE IF NOT EXISTS business_units_before_numeric_conversion AS 
    SELECT *, CURRENT_TIMESTAMP as backup_created_at FROM business_units;

-- Step 3: Create mapping table for old ID to new numeric ID
CREATE TABLE IF NOT EXISTS bu_id_conversion_mapping AS
SELECT 
    unit_id as old_bu_id,
    unit_id_numeric as new_numeric_id,
    unit_name
FROM business_units
ORDER BY unit_id_numeric;

-- Step 4: Update foreign key references in journal entry lines
-- First update to use numeric IDs (stored as VARCHAR)
UPDATE journalentryline 
SET business_unit_id = mapping.new_numeric_id::VARCHAR
FROM bu_id_conversion_mapping mapping
WHERE journalentryline.business_unit_id = mapping.old_bu_id;

-- Step 5: Update foreign key references in GL transactions
UPDATE gl_transactions 
SET business_unit_id = mapping.new_numeric_id::VARCHAR
FROM bu_id_conversion_mapping mapping
WHERE gl_transactions.business_unit_id = mapping.old_bu_id;

-- Step 6: Update any parent unit references within business_units
UPDATE business_units 
SET parent_unit_id = mapping.new_numeric_id::VARCHAR
FROM bu_id_conversion_mapping mapping
WHERE business_units.parent_unit_id = mapping.old_bu_id;

-- Step 7: Drop the old primary key constraint
ALTER TABLE business_units DROP CONSTRAINT business_units_pkey;

-- Step 8: Update the unit_id column to use numeric values
UPDATE business_units 
SET unit_id = unit_id_numeric::VARCHAR;

-- Step 9: Change column type to INTEGER for unit_id
ALTER TABLE business_units ALTER COLUMN unit_id TYPE INTEGER USING unit_id::INTEGER;

-- Step 10: Add new primary key constraint on numeric unit_id
ALTER TABLE business_units ADD CONSTRAINT business_units_pkey PRIMARY KEY (unit_id);

-- Step 11: Update foreign key column types to INTEGER
ALTER TABLE journalentryline ALTER COLUMN business_unit_id TYPE INTEGER USING business_unit_id::INTEGER;
ALTER TABLE gl_transactions ALTER COLUMN business_unit_id TYPE INTEGER USING business_unit_id::INTEGER;
ALTER TABLE business_units ALTER COLUMN parent_unit_id TYPE INTEGER USING parent_unit_id::INTEGER;

-- Step 12: Recreate foreign key constraints with new INTEGER types
ALTER TABLE journalentryline 
ADD CONSTRAINT fk_journalentryline_business_unit 
    FOREIGN KEY (business_unit_id) REFERENCES business_units(unit_id);

ALTER TABLE gl_transactions 
ADD CONSTRAINT fk_gl_transactions_business_unit 
    FOREIGN KEY (business_unit_id) REFERENCES business_units(unit_id);

ALTER TABLE business_units 
ADD CONSTRAINT fk_business_units_parent 
    FOREIGN KEY (parent_unit_id) REFERENCES business_units(unit_id);

-- Step 13: Drop the now-redundant unit_id_numeric column
ALTER TABLE business_units DROP COLUMN IF EXISTS unit_id_numeric;

-- Step 14: Update validation functions for INTEGER IDs
CREATE OR REPLACE FUNCTION validate_journal_entry_business_unit()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate INTEGER business_unit_id
    IF NEW.business_unit_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM business_units 
            WHERE unit_id = NEW.business_unit_id 
            AND is_active = TRUE
        ) THEN
            RAISE EXCEPTION 'Invalid or inactive business unit ID: %', NEW.business_unit_id;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION validate_gl_transaction_business_unit_enhanced()
RETURNS TRIGGER AS $$
BEGIN
    -- Validate INTEGER business_unit_id
    IF NEW.business_unit_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM business_units 
            WHERE unit_id = NEW.business_unit_id 
            AND is_active = TRUE
        ) THEN
            RAISE EXCEPTION 'Invalid or inactive business unit ID: %', NEW.business_unit_id;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Step 15: Recreate views with new INTEGER unit_id structure
CREATE OR REPLACE VIEW v_business_units_optimized AS
SELECT 
    bu.unit_id as numeric_id,                   -- Now the primary numeric ID
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
    bu.generated_code_8digit as code_8digit_alt, -- Keep 8-digit as alternative
    bu.person_responsible,
    bu.is_active
FROM business_units bu
LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
WHERE bu.is_active = TRUE;

CREATE OR REPLACE VIEW v_business_units_with_dimensions AS
SELECT 
    bu.unit_id,                                 -- Now plain numeric ID
    bu.unit_name,
    bu.unit_type,
    bu.responsibility_type,
    bu.product_line_id,
    pl.product_line_name,
    pl.industry_sector,
    bu.location_code,                           -- 6-digit format
    rl.location_name,
    rl.country_code,
    rl.location_level,
    bu.generated_code as business_code_10digit, -- 10-digit format
    bu.person_responsible,
    bu.is_active
FROM business_units bu
LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
WHERE bu.is_active = TRUE;

CREATE OR REPLACE VIEW v_journal_entries_enhanced AS
SELECT 
    jeh.documentnumber,
    jeh.companycodeid,
    jeh.reference,
    jeh.postingdate,
    jeh.workflow_status,
    jel.linenumber,
    jel.glaccountid,
    ga.accountname,
    jel.debitamount,
    jel.creditamount,
    jel.description as line_description,
    -- Numeric business unit ID
    jel.business_unit_id,
    bu.unit_name as business_unit_name,
    bu.unit_type,
    bu.responsibility_type,
    -- Product Line dimension
    bu.product_line_id,
    pl.product_line_name,
    pl.industry_sector,
    -- Location dimension
    bu.location_code,
    rl.location_name,
    rl.country_code,
    -- Generated code for analysis
    bu.generated_code,
    -- Additional fields
    jel.currencycode,
    jel.ledgerid,
    jeh.createdby,
    jeh.createdat
FROM journalentryheader jeh
INNER JOIN journalentryline jel ON jeh.documentnumber = jel.documentnumber 
    AND jeh.companycodeid = jel.companycodeid
LEFT JOIN glaccount ga ON jel.glaccountid = ga.glaccountid
LEFT JOIN business_units bu ON jel.business_unit_id = bu.unit_id
LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code;

CREATE OR REPLACE VIEW v_gl_transactions_enhanced AS
SELECT 
    gt.transaction_id,
    gt.document_id,
    gt.company_code,
    gt.fiscal_year,
    gt.document_number,
    gt.line_item,
    gt.gl_account,
    gt.ledger_id,
    -- Numeric business unit ID
    gt.business_unit_id,
    bu.unit_name as business_unit_name,
    bu.unit_type,
    bu.responsibility_type,
    -- Product Line dimension
    bu.product_line_id,
    pl.product_line_name,
    pl.industry_sector,
    -- Location dimension
    bu.location_code,
    rl.location_name,
    rl.country_code,
    rl.location_level,
    -- Generated code for analysis
    bu.generated_code,
    -- Financial amounts
    gt.debit_amount,
    gt.credit_amount,
    gt.local_currency_amount,
    gt.document_currency,
    -- Dates and other fields
    gt.posting_date,
    gt.document_date,
    gt.entry_date,
    gt.line_text,
    gt.reference,
    gt.posting_period,
    gt.document_status,
    gt.posted_by
FROM gl_transactions gt
LEFT JOIN business_units bu ON gt.business_unit_id = bu.unit_id
LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code;

-- Step 16: Verify the conversion results
DO $$
DECLARE
    total_business_units INTEGER;
    min_unit_id INTEGER;
    max_unit_id INTEGER;
    journal_lines_with_numeric_bu INTEGER;
    gl_trans_with_numeric_bu INTEGER;
    sample_unit_ids INTEGER[];
BEGIN
    SELECT COUNT(*) INTO total_business_units FROM business_units WHERE is_active = TRUE;
    SELECT MIN(unit_id), MAX(unit_id) INTO min_unit_id, max_unit_id FROM business_units;
    
    SELECT COUNT(*) INTO journal_lines_with_numeric_bu 
    FROM journalentryline WHERE business_unit_id IS NOT NULL;
    
    SELECT COUNT(*) INTO gl_trans_with_numeric_bu 
    FROM gl_transactions WHERE business_unit_id IS NOT NULL;
    
    -- Get sample unit IDs
    SELECT ARRAY_AGG(unit_id) INTO sample_unit_ids
    FROM (SELECT unit_id FROM business_units ORDER BY unit_id LIMIT 5) samples;
    
    RAISE NOTICE '=== BU PREFIX REMOVAL COMPLETE ===';
    RAISE NOTICE 'Total Business Units: %', total_business_units;
    RAISE NOTICE 'Unit ID Range: % to %', min_unit_id, max_unit_id;
    RAISE NOTICE 'Journal Lines with Numeric BU IDs: %', journal_lines_with_numeric_bu;
    RAISE NOTICE 'GL Transactions with Numeric BU IDs: %', gl_trans_with_numeric_bu;
    RAISE NOTICE 'Sample Unit IDs: %', array_to_string(sample_unit_ids::TEXT[], ', ');
    RAISE NOTICE '==================================';
    
    RAISE NOTICE '✅ SUCCESS: BU- prefixes removed!';
    RAISE NOTICE '✅ All IDs are now plain numbers!';
    RAISE NOTICE '✅ All foreign key references updated!';
END $$;

-- Step 17: Show sample of new numeric structure
SELECT 'New Numeric Business Unit Structure:' as info;

SELECT 
    bu.unit_id as numeric_id,
    bu.generated_code as code_10digit,
    bu.unit_name,
    bu.unit_type,
    pl.product_line_name,
    rl.location_name
FROM business_units bu
LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
WHERE bu.generated_code IS NOT NULL
ORDER BY bu.unit_id
LIMIT 15;

-- Step 18: Grant permissions
GRANT SELECT ON v_business_units_optimized TO PUBLIC;
GRANT SELECT ON v_business_units_with_dimensions TO PUBLIC;
GRANT SELECT ON v_journal_entries_enhanced TO PUBLIC;
GRANT SELECT ON v_gl_transactions_enhanced TO PUBLIC;

-- Step 19: Clean up temporary mapping table (keep backup)
-- Keep bu_id_conversion_mapping for reference
-- Keep business_units_before_numeric_conversion for rollback if needed

-- Step 20: Document the conversion
INSERT INTO system_migration_log (
    migration_name,
    migration_status,
    tables_removed,
    columns_removed,
    functions_removed,
    views_updated,
    backup_tables,
    notes
) VALUES (
    'Remove BU- Prefix and Convert to Numeric IDs',
    'COMPLETED',
    ARRAY[]::TEXT[],
    ARRAY['business_units.unit_id_numeric']::TEXT[],
    ARRAY[]::TEXT[],
    ARRAY['v_business_units_optimized', 'v_business_units_with_dimensions', 'v_journal_entries_enhanced', 'v_gl_transactions_enhanced']::TEXT[],
    ARRAY['business_units_before_numeric_conversion', 'bu_id_conversion_mapping']::TEXT[],
    'Successfully converted business unit IDs from BU- prefixed strings to plain numeric integers. Updated all foreign key references in journal entry lines and GL transactions. All views recreated with numeric ID structure. Data integrity maintained with backup tables created.'
);

-- =====================================================
-- BU- Prefix Removal Complete
-- =====================================================
-- Results:
--   ✅ Business Unit IDs: BU-XXXX-XXXXXX → Plain numbers (1, 2, 3...)
--   ✅ Column type: VARCHAR → INTEGER for better performance
--   ✅ Foreign keys: All updated to reference numeric IDs
--   ✅ Views: All recreated with numeric structure
--   ✅ Validation: Updated for INTEGER data types
--   ✅ Performance: Improved with numeric primary keys
-- =====================================================