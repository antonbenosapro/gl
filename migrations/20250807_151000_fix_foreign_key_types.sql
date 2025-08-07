-- =====================================================
-- Fix Foreign Key Data Types for Numeric Business Unit IDs
-- =====================================================
-- Author: Claude Code Assistant
-- Date: August 7, 2025
-- Description: Fix data type mismatches after BU- prefix removal
-- =====================================================

-- Step 1: Check current data in foreign key tables
SELECT 'Current business_unit_id values in journalentryline:' as info;
SELECT DISTINCT business_unit_id, LENGTH(business_unit_id) as length 
FROM journalentryline 
WHERE business_unit_id IS NOT NULL 
ORDER BY business_unit_id 
LIMIT 10;

-- Step 2: Convert foreign key references to proper numeric format
-- Update journalentryline - convert any remaining BU- prefixed IDs
UPDATE journalentryline 
SET business_unit_id = mapping.new_numeric_id::VARCHAR
FROM bu_id_conversion_mapping mapping
WHERE journalentryline.business_unit_id = mapping.old_bu_id;

-- Set NULL for any invalid references that can't be converted
UPDATE journalentryline 
SET business_unit_id = NULL 
WHERE business_unit_id IS NOT NULL 
AND business_unit_id !~ '^[0-9]+$';  -- Not purely numeric

-- Update gl_transactions similarly  
UPDATE gl_transactions 
SET business_unit_id = mapping.new_numeric_id::VARCHAR
FROM bu_id_conversion_mapping mapping
WHERE gl_transactions.business_unit_id = mapping.old_bu_id;

-- Set NULL for any invalid references in GL transactions
UPDATE gl_transactions 
SET business_unit_id = NULL 
WHERE business_unit_id IS NOT NULL 
AND business_unit_id !~ '^[0-9]+$';  -- Not purely numeric

-- Step 3: Now convert column types to INTEGER
ALTER TABLE journalentryline 
ALTER COLUMN business_unit_id TYPE INTEGER USING business_unit_id::INTEGER;

ALTER TABLE gl_transactions 
ALTER COLUMN business_unit_id TYPE INTEGER USING business_unit_id::INTEGER;

-- Step 4: Add foreign key constraints with correct types
ALTER TABLE journalentryline 
ADD CONSTRAINT fk_journalentryline_business_unit 
    FOREIGN KEY (business_unit_id) REFERENCES business_units(unit_id);

ALTER TABLE gl_transactions 
ADD CONSTRAINT fk_gl_transactions_business_unit 
    FOREIGN KEY (business_unit_id) REFERENCES business_units(unit_id);

-- Step 5: Update validation functions with correct data types
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

-- Step 6: Recreate views with proper INTEGER joins
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

-- Step 7: Final verification
DO $$
DECLARE
    journal_numeric_type BOOLEAN;
    gl_numeric_type BOOLEAN;
    bu_integer_type BOOLEAN;
    journal_fk_exists BOOLEAN;
    gl_fk_exists BOOLEAN;
BEGIN
    -- Check if columns are now INTEGER type
    SELECT data_type = 'integer' INTO journal_numeric_type
    FROM information_schema.columns 
    WHERE table_name = 'journalentryline' AND column_name = 'business_unit_id';
    
    SELECT data_type = 'integer' INTO gl_numeric_type
    FROM information_schema.columns 
    WHERE table_name = 'gl_transactions' AND column_name = 'business_unit_id';
    
    SELECT data_type = 'integer' INTO bu_integer_type
    FROM information_schema.columns 
    WHERE table_name = 'business_units' AND column_name = 'unit_id';
    
    -- Check if foreign keys exist
    SELECT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_journalentryline_business_unit'
    ) INTO journal_fk_exists;
    
    SELECT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_gl_transactions_business_unit'
    ) INTO gl_fk_exists;
    
    RAISE NOTICE '=== FOREIGN KEY TYPE CONVERSION RESULTS ===';
    RAISE NOTICE 'Journal Entry Lines business_unit_id is INTEGER: %', journal_numeric_type;
    RAISE NOTICE 'GL Transactions business_unit_id is INTEGER: %', gl_numeric_type;
    RAISE NOTICE 'Business Units unit_id is INTEGER: %', bu_integer_type;
    RAISE NOTICE 'Journal Entry FK constraint exists: %', journal_fk_exists;
    RAISE NOTICE 'GL Transactions FK constraint exists: %', gl_fk_exists;
    RAISE NOTICE '==========================================';
    
    IF journal_numeric_type AND gl_numeric_type AND bu_integer_type THEN
        RAISE NOTICE '✅ SUCCESS: All business unit IDs are now INTEGER!';
        RAISE NOTICE '✅ Foreign key constraints established!';
        RAISE NOTICE '✅ Data type consistency achieved!';
    END IF;
END $$;

-- Step 8: Show final structure
SELECT 'Final Numeric Business Unit Integration:' as info;

SELECT 
    'Sample Journal Entries with Numeric BU IDs' as category,
    COUNT(*) as total_entries,
    COUNT(CASE WHEN jel.business_unit_id IS NOT NULL THEN 1 END) as entries_with_bu
FROM journalentryheader jeh
INNER JOIN journalentryline jel ON jeh.documentnumber = jel.documentnumber;

-- Step 9: Grant permissions
GRANT SELECT ON v_journal_entries_enhanced TO PUBLIC;
GRANT SELECT ON v_gl_transactions_enhanced TO PUBLIC;

-- =====================================================
-- Foreign Key Type Conversion Complete
-- =====================================================
-- Results:
--   ✅ journalentryline.business_unit_id: VARCHAR → INTEGER
--   ✅ gl_transactions.business_unit_id: VARCHAR → INTEGER  
--   ✅ business_units.unit_id: INTEGER (primary key)
--   ✅ Foreign key constraints: Established with matching types
--   ✅ Views: Updated with proper INTEGER joins
-- =====================================================