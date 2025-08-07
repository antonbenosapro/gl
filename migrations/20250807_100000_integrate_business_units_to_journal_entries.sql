-- =====================================================
-- Integrate Business Units into Journal Entry System
-- =====================================================
-- Author: Claude Code Assistant
-- Date: August 7, 2025
-- Description: Add business_unit_id field to journal entry lines table
--              and create mapping triggers for automatic assignment
-- =====================================================

-- Step 1: Add business_unit_id column to journalentryline table
ALTER TABLE journalentryline 
ADD COLUMN business_unit_id VARCHAR(20);

-- Add foreign key constraint to business_units
ALTER TABLE journalentryline
ADD CONSTRAINT fk_journalentryline_business_unit
FOREIGN KEY (business_unit_id) REFERENCES business_units(unit_id);

-- Add index for performance
CREATE INDEX idx_journalentryline_business_unit ON journalentryline(business_unit_id);

-- Step 2: Create mapping function to auto-assign business units based on cost center
CREATE OR REPLACE FUNCTION map_journal_cost_center_to_business_unit(p_cost_center VARCHAR(10))
RETURNS VARCHAR(20) AS $$
DECLARE
    v_unit_id VARCHAR(20);
BEGIN
    -- Try to find business unit by cost center mapping
    SELECT unit_id INTO v_unit_id
    FROM business_units
    WHERE (
        unit_id LIKE 'BU-' || p_cost_center || '%' OR
        short_name = p_cost_center OR
        unit_id = 'BU-CC-' || p_cost_center
    )
    AND unit_type IN ('COST_CENTER', 'BOTH')
    AND is_active = TRUE
    LIMIT 1;
    
    -- If not found, try enhanced mapping
    IF v_unit_id IS NULL THEN
        v_unit_id := CASE p_cost_center
            WHEN 'SALES01' THEN 'BU-SALES01'
            WHEN 'FAC01' THEN 'BU-FAC01'
            WHEN 'ADMIN01' THEN 'BU-ADMIN01'
            WHEN 'PROD01' THEN 'BU-PROD01'
            WHEN 'HR01' THEN 'BU-HR01'
            WHEN 'TAX01' THEN 'BU-TAX01'
            WHEN 'FIN01' THEN 'BU-FIN01'
            WHEN 'IT01' THEN 'BU-IT01'
            WHEN 'EQUITY01' THEN 'BU-EQUITY01'
            WHEN 'PAYROLL01' THEN 'BU-PAYROLL01'
            WHEN 'SERV01' THEN 'BU-SERV01'
            WHEN 'PURCH01' THEN 'BU-PURCH01'
            WHEN 'CASH01' THEN 'BU-CASH01'
            WHEN 'MKTG01' THEN 'BU-MKTG01'
            ELSE NULL
        END;
    END IF;
    
    RETURN v_unit_id;
END;
$$ LANGUAGE plpgsql;

-- Step 3: Update existing journal entry lines with business unit mappings
UPDATE journalentryline 
SET business_unit_id = map_journal_cost_center_to_business_unit(costcenterid)
WHERE costcenterid IS NOT NULL 
AND costcenterid != ''
AND business_unit_id IS NULL;

-- Step 4: Create trigger for automatic business unit assignment on new journal entries
CREATE OR REPLACE FUNCTION validate_journal_entry_business_unit()
RETURNS TRIGGER AS $$
BEGIN
    -- If business_unit_id is provided, ensure it's valid and active
    IF NEW.business_unit_id IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1 FROM business_units 
            WHERE unit_id = NEW.business_unit_id 
            AND is_active = TRUE
        ) THEN
            RAISE EXCEPTION 'Invalid or inactive business unit: %', NEW.business_unit_id;
        END IF;
    END IF;
    
    -- If costcenterid is provided and business_unit_id is null, try to auto-map
    IF NEW.costcenterid IS NOT NULL AND NEW.costcenterid != '' 
       AND NEW.business_unit_id IS NULL THEN
        NEW.business_unit_id = map_journal_cost_center_to_business_unit(NEW.costcenterid);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Drop existing trigger if exists
DROP TRIGGER IF EXISTS tr_journalentryline_business_unit_validation ON journalentryline;

CREATE TRIGGER tr_journalentryline_business_unit_validation
BEFORE INSERT OR UPDATE ON journalentryline
FOR EACH ROW EXECUTE FUNCTION validate_journal_entry_business_unit();

-- Step 5: Create enhanced journal entry view with business unit information
CREATE OR REPLACE VIEW v_journal_entries_enhanced AS
SELECT 
    jeh.documentnumber,
    jeh.companycodeid,
    jeh.reference,
    jeh.postingdate,
    jeh.workflow_status,
    jel.linenumber,
    jel.glaccountid,
    ga.glaccount_name,
    jel.debitamount,
    jel.creditamount,
    jel.description as line_description,
    -- Original cost center (maintained for backward compatibility)
    jel.costcenterid,
    -- New business unit integration
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

-- Step 6: Create business unit financial analysis view for journal entries
CREATE OR REPLACE VIEW v_journal_business_unit_analysis AS
SELECT 
    bu.unit_id,
    bu.unit_name,
    bu.unit_type,
    bu.responsibility_type,
    pl.product_line_name,
    pl.industry_sector,
    rl.location_name,
    rl.country_code,
    bu.generated_code,
    -- Financial aggregations
    COUNT(jel.docid) as journal_line_count,
    COUNT(DISTINCT jeh.documentnumber) as journal_entry_count,
    SUM(jel.debitamount) as total_debits,
    SUM(jel.creditamount) as total_credits,
    SUM(jel.debitamount - jel.creditamount) as net_amount,
    -- Period analysis
    MIN(jeh.postingdate) as first_journal_date,
    MAX(jeh.postingdate) as last_journal_date,
    -- Status breakdown
    COUNT(CASE WHEN jeh.workflow_status = 'DRAFT' THEN 1 END) as draft_entries,
    COUNT(CASE WHEN jeh.workflow_status = 'PENDING_APPROVAL' THEN 1 END) as pending_entries,
    COUNT(CASE WHEN jeh.workflow_status = 'APPROVED' THEN 1 END) as approved_entries
FROM business_units bu
LEFT JOIN journalentryline jel ON bu.unit_id = jel.business_unit_id
LEFT JOIN journalentryheader jeh ON jel.documentnumber = jeh.documentnumber 
    AND jel.companycodeid = jeh.companycodeid
LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
WHERE bu.is_active = TRUE
GROUP BY bu.unit_id, bu.unit_name, bu.unit_type, bu.responsibility_type, 
         pl.product_line_name, pl.industry_sector, rl.location_name, 
         rl.country_code, bu.generated_code;

-- Step 7: Grant permissions on new views
GRANT SELECT ON v_journal_entries_enhanced TO PUBLIC;
GRANT SELECT ON v_journal_business_unit_analysis TO PUBLIC;

-- Step 8: Show integration results
DO $$
DECLARE
    total_lines INTEGER;
    mapped_lines INTEGER;
    unmapped_lines INTEGER;
    business_units_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_lines FROM journalentryline;
    SELECT COUNT(*) INTO mapped_lines FROM journalentryline WHERE business_unit_id IS NOT NULL;
    SELECT COUNT(*) INTO unmapped_lines FROM journalentryline WHERE business_unit_id IS NULL AND (costcenterid IS NOT NULL AND costcenterid != '');
    SELECT COUNT(*) INTO business_units_count FROM business_units WHERE is_active = TRUE;
    
    RAISE NOTICE '=== JOURNAL ENTRIES BUSINESS UNIT INTEGRATION RESULTS ===';
    RAISE NOTICE 'Total Journal Entry Lines: %', total_lines;
    RAISE NOTICE 'Successfully Mapped to Business Units: %', mapped_lines;
    RAISE NOTICE 'Unmapped Lines (with cost center): %', unmapped_lines;
    RAISE NOTICE 'Total Active Business Units: %', business_units_count;
    RAISE NOTICE 'Integration Success Rate: %%%', ROUND(mapped_lines::DECIMAL / NULLIF(total_lines, 0) * 100, 2);
END $$;

-- Show sample of enhanced journal entries
SELECT 'Sample Enhanced Journal Entries:' as info;
SELECT 
    documentnumber,
    linenumber,
    glaccountid,
    costcenterid,
    business_unit_id,
    business_unit_name,
    unit_type,
    product_line_name,
    location_name,
    generated_code,
    debitamount,
    creditamount
FROM v_journal_entries_enhanced
WHERE business_unit_id IS NOT NULL
ORDER BY documentnumber, linenumber
LIMIT 10;

-- Show business unit activity summary
SELECT 'Business Unit Journal Activity Summary:' as info;
SELECT 
    unit_id,
    unit_name,
    unit_type,
    product_line_name,
    location_name,
    generated_code,
    journal_entry_count,
    journal_line_count,
    total_debits,
    total_credits,
    net_amount
FROM v_journal_business_unit_analysis
WHERE journal_line_count > 0
ORDER BY journal_line_count DESC
LIMIT 15;

-- =====================================================
-- Journal Entries Business Unit Integration Complete
-- =====================================================
-- Added:
--   - business_unit_id column to journalentryline table
--   - Automatic mapping from cost_center to business_unit_id
--   - Enhanced views with full dimensional analysis
--   - Multi-dimensional financial reporting capabilities
--   - Data validation triggers
--   - Performance indexes
-- 
-- Result: Journal Entries now fully integrated with Business Units,
--         Product Lines, and Location dimensions for advanced analytics
-- =====================================================