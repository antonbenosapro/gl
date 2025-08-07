-- =====================================================
-- Integrate Business Units into GL Transactions
-- =====================================================
-- Author: Claude Code Assistant
-- Date: August 7, 2025
-- Description: Add business unit integration to GL transactions table
--              and create migration path from cost_center to business_unit_id
-- =====================================================

-- Step 1: Add business_unit_id column to gl_transactions
ALTER TABLE gl_transactions 
ADD COLUMN business_unit_id VARCHAR(20);

-- Add foreign key constraint to business_units
ALTER TABLE gl_transactions
ADD CONSTRAINT fk_gl_transactions_business_unit
FOREIGN KEY (business_unit_id) REFERENCES business_units(unit_id);

-- Add index for performance
CREATE INDEX idx_gl_transactions_business_unit ON gl_transactions(business_unit_id);

-- Step 2: Create mapping function to convert cost_center to business_unit_id
CREATE OR REPLACE FUNCTION map_cost_center_to_business_unit(p_cost_center VARCHAR(10))
RETURNS VARCHAR(20) AS $$
DECLARE
    v_unit_id VARCHAR(20);
BEGIN
    -- Try to find direct mapping from old cost center ID
    SELECT unit_id INTO v_unit_id
    FROM business_units
    WHERE unit_id = 'BU-CC-' || p_cost_center
    AND unit_type IN ('COST_CENTER', 'BOTH')
    AND is_active = TRUE;
    
    -- If not found, try to find by matching name or alternative mapping
    IF v_unit_id IS NULL THEN
        -- Try to find by matching the cost center pattern
        SELECT unit_id INTO v_unit_id
        FROM business_units
        WHERE (
            unit_id LIKE '%' || p_cost_center || '%' OR
            short_name LIKE '%' || p_cost_center || '%'
        )
        AND unit_type IN ('COST_CENTER', 'BOTH', 'PROFIT_CENTER')
        AND is_active = TRUE
        LIMIT 1;
    END IF;
    
    RETURN v_unit_id;
END;
$$ LANGUAGE plpgsql;

-- Step 3: Update existing GL transactions with business unit mappings
-- First, let's see what cost centers we have
DO $$
BEGIN
    RAISE NOTICE 'Analyzing cost center usage in GL transactions...';
END $$;

-- Show current cost center distribution
SELECT 
    cost_center,
    COUNT(*) as transaction_count,
    map_cost_center_to_business_unit(cost_center) as suggested_business_unit
FROM gl_transactions 
WHERE cost_center IS NOT NULL AND cost_center != ''
GROUP BY cost_center
ORDER BY transaction_count DESC;

-- Step 4: Update GL transactions with business unit IDs where we can map them
UPDATE gl_transactions 
SET business_unit_id = map_cost_center_to_business_unit(cost_center)
WHERE cost_center IS NOT NULL 
AND cost_center != ''
AND map_cost_center_to_business_unit(cost_center) IS NOT NULL;

-- Step 5: Create enhanced GL transactions view with business unit information
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
    -- Original cost center (maintained for backward compatibility)
    gt.cost_center,
    -- New business unit integration
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

-- Step 6: Create business unit financial analysis views
CREATE OR REPLACE VIEW v_business_unit_financial_summary AS
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
    COUNT(gt.transaction_id) as transaction_count,
    SUM(gt.debit_amount) as total_debits,
    SUM(gt.credit_amount) as total_credits,
    SUM(gt.local_currency_amount) as net_amount,
    -- Period analysis
    MIN(gt.posting_date) as first_transaction_date,
    MAX(gt.posting_date) as last_transaction_date
FROM business_units bu
LEFT JOIN gl_transactions gt ON bu.unit_id = gt.business_unit_id
LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
WHERE bu.is_active = TRUE
GROUP BY bu.unit_id, bu.unit_name, bu.unit_type, bu.responsibility_type, 
         pl.product_line_name, pl.industry_sector, rl.location_name, 
         rl.country_code, bu.generated_code;

-- Step 7: Create multi-dimensional financial analysis view
CREATE OR REPLACE VIEW v_multidimensional_financial_analysis AS
SELECT 
    -- Business dimensions
    bu.unit_type,
    bu.responsibility_type,
    pl.industry_sector,
    rl.country_code,
    rl.location_level,
    -- Time dimension
    EXTRACT(YEAR FROM gt.posting_date) as fiscal_year,
    EXTRACT(MONTH FROM gt.posting_date) as fiscal_month,
    -- Financial metrics
    COUNT(gt.transaction_id) as transaction_volume,
    COUNT(DISTINCT bu.unit_id) as business_units_count,
    SUM(gt.debit_amount) as total_debits,
    SUM(gt.credit_amount) as total_credits,
    SUM(gt.local_currency_amount) as net_amount,
    -- Average transaction size
    AVG(ABS(gt.local_currency_amount)) as avg_transaction_size
FROM gl_transactions gt
INNER JOIN business_units bu ON gt.business_unit_id = bu.unit_id
LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
WHERE gt.document_status = 'ACTIVE'
AND bu.is_active = TRUE
GROUP BY bu.unit_type, bu.responsibility_type, pl.industry_sector, 
         rl.country_code, rl.location_level,
         EXTRACT(YEAR FROM gt.posting_date),
         EXTRACT(MONTH FROM gt.posting_date)
HAVING COUNT(gt.transaction_id) > 0;

-- Step 8: Create trigger to ensure business unit consistency
CREATE OR REPLACE FUNCTION validate_gl_transaction_business_unit()
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
    
    -- If cost_center is provided and business_unit_id is null, try to auto-map
    IF NEW.cost_center IS NOT NULL AND NEW.cost_center != '' 
       AND NEW.business_unit_id IS NULL THEN
        NEW.business_unit_id = map_cost_center_to_business_unit(NEW.cost_center);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_gl_transactions_business_unit_validation
BEFORE INSERT OR UPDATE ON gl_transactions
FOR EACH ROW EXECUTE FUNCTION validate_gl_transaction_business_unit();

-- Step 9: Grant permissions on new views
GRANT SELECT ON v_gl_transactions_enhanced TO PUBLIC;
GRANT SELECT ON v_business_unit_financial_summary TO PUBLIC;
GRANT SELECT ON v_multidimensional_financial_analysis TO PUBLIC;

-- Step 10: Show migration results
DO $$
DECLARE
    total_transactions INTEGER;
    mapped_transactions INTEGER;
    unmapped_transactions INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_transactions FROM gl_transactions;
    SELECT COUNT(*) INTO mapped_transactions FROM gl_transactions WHERE business_unit_id IS NOT NULL;
    SELECT COUNT(*) INTO unmapped_transactions FROM gl_transactions WHERE business_unit_id IS NULL AND (cost_center IS NOT NULL AND cost_center != '');
    
    RAISE NOTICE '=== GL TRANSACTIONS BUSINESS UNIT INTEGRATION SUMMARY ===';
    RAISE NOTICE 'Total GL Transactions: %', total_transactions;
    RAISE NOTICE 'Successfully Mapped to Business Units: %', mapped_transactions;
    RAISE NOTICE 'Unmapped Transactions (with cost center): %', unmapped_transactions;
    RAISE NOTICE 'Integration Success Rate: %%%', ROUND(mapped_transactions::DECIMAL / NULLIF(total_transactions, 0) * 100, 2);
END $$;

-- Show sample of enhanced GL transactions
SELECT 'Sample Enhanced GL Transactions:' as info;
SELECT 
    document_number,
    line_item,
    gl_account,
    cost_center,
    business_unit_id,
    business_unit_name,
    unit_type,
    product_line_name,
    location_name,
    generated_code,
    local_currency_amount
FROM v_gl_transactions_enhanced
WHERE business_unit_id IS NOT NULL
LIMIT 5;

-- Show business unit financial summary
SELECT 'Business Unit Financial Summary:' as info;
SELECT 
    unit_id,
    unit_name,
    unit_type,
    product_line_name,
    location_name,
    generated_code,
    transaction_count,
    total_debits,
    total_credits,
    net_amount
FROM v_business_unit_financial_summary
WHERE transaction_count > 0
ORDER BY transaction_count DESC;

-- =====================================================
-- GL Transactions Business Unit Integration Complete
-- =====================================================
-- Added:
--   - business_unit_id column to gl_transactions
--   - Automatic mapping from cost_center to business_unit_id
--   - Enhanced views with full dimensional analysis
--   - Multi-dimensional financial reporting capabilities
--   - Data validation triggers
--   - Performance indexes
-- 
-- Result: GL Transactions now fully integrated with Business Units,
--         Product Lines, and Location dimensions for advanced analytics
-- =====================================================