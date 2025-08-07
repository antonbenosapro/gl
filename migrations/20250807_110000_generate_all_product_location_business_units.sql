-- =====================================================
-- Generate Business Units for All Product Line × Location Combinations
-- =====================================================
-- Author: Claude Code Assistant
-- Date: August 7, 2025
-- Description: Create comprehensive business units matrix covering every
--              product line and location combination for global operations
-- =====================================================

-- Step 1: Show the scale we're working with
DO $$
DECLARE
    product_count INTEGER;
    location_count INTEGER;
    potential_combinations INTEGER;
BEGIN
    SELECT COUNT(*) INTO product_count FROM product_lines WHERE is_active = TRUE;
    SELECT COUNT(*) INTO location_count FROM reporting_locations WHERE is_active = TRUE;
    potential_combinations := product_count * location_count;
    
    RAISE NOTICE '=== BUSINESS UNIT GENERATION SCOPE ===';
    RAISE NOTICE 'Active Product Lines: %', product_count;
    RAISE NOTICE 'Active Locations: %', location_count;
    RAISE NOTICE 'Total Combinations: %', potential_combinations;
    RAISE NOTICE 'Starting mass business unit generation...';
END $$;

-- Step 2: Create function to generate unit names and descriptions
CREATE OR REPLACE FUNCTION generate_business_unit_name(
    p_product_name VARCHAR(100),
    p_location_name VARCHAR(100),
    p_location_level VARCHAR(20)
) RETURNS VARCHAR(100) AS $$
BEGIN
    -- Create intelligent business unit names based on location level
    RETURN CASE 
        WHEN p_location_level = 'GLOBAL' THEN p_product_name || ' - Global Operations'
        WHEN p_location_level = 'REGION' THEN p_product_name || ' - ' || p_location_name || ' Region'
        WHEN p_location_level = 'COUNTRY' THEN p_product_name || ' - ' || p_location_name
        WHEN p_location_level = 'STATE' THEN p_product_name || ' - ' || p_location_name || ' State'
        WHEN p_location_level = 'CITY' THEN p_product_name || ' - ' || p_location_name || ' City'
        WHEN p_location_level = 'SITE' THEN p_product_name || ' - ' || p_location_name || ' Site'
        WHEN p_location_level = 'BUILDING' THEN p_product_name || ' - ' || p_location_name || ' Building'
        WHEN p_location_level = 'FLOOR' THEN p_product_name || ' - ' || p_location_name || ' Floor'
        ELSE p_product_name || ' - ' || p_location_name
    END;
END;
$$ LANGUAGE plpgsql;

-- Step 3: Determine unit type based on product and location characteristics
CREATE OR REPLACE FUNCTION determine_unit_type(
    p_product_category VARCHAR(50),
    p_industry_sector VARCHAR(50),
    p_location_level VARCHAR(20)
) RETURNS VARCHAR(15) AS $$
BEGIN
    -- Strategic unit type assignment
    RETURN CASE 
        -- Profit centers for customer-facing operations
        WHEN p_product_category IN ('SALES', 'CUSTOMER_SERVICES', 'RETAIL') THEN 'PROFIT_CENTER'
        WHEN p_industry_sector IN ('CONSUMER_ELECTRONICS', 'FOOD_BEVERAGES', 'AUTOMOTIVE', 'RETAIL') 
             AND p_location_level IN ('COUNTRY', 'STATE', 'CITY') THEN 'PROFIT_CENTER'
        -- Cost centers for support and manufacturing
        WHEN p_product_category IN ('MANUFACTURING', 'OPERATIONS', 'SUPPORT', 'INFRASTRUCTURE') THEN 'COST_CENTER'
        WHEN p_industry_sector IN ('OIL_GAS', 'MANUFACTURING', 'INFRASTRUCTURE') THEN 'COST_CENTER'
        -- Regional operations are often dual-purpose
        WHEN p_location_level IN ('GLOBAL', 'REGION') THEN 'BOTH'
        -- Default to cost center for specific operational units
        ELSE 'COST_CENTER'
    END;
END;
$$ LANGUAGE plpgsql;

-- Step 4: Mass generation of business units with progress tracking
DO $$
DECLARE
    pl_record RECORD;
    loc_record RECORD;
    unit_id VARCHAR(20);
    unit_name VARCHAR(100);
    short_name VARCHAR(20);
    unit_type VARCHAR(15);
    responsibility_type VARCHAR(20);
    unit_category VARCHAR(20);
    generated_code VARCHAR(10);
    processed_count INTEGER := 0;
    success_count INTEGER := 0;
    total_combinations INTEGER;
    progress_interval INTEGER;
BEGIN
    -- Calculate total for progress tracking
    SELECT COUNT(*) * (SELECT COUNT(*) FROM reporting_locations WHERE is_active = TRUE) 
    INTO total_combinations 
    FROM product_lines WHERE is_active = TRUE;
    
    progress_interval := GREATEST(1, total_combinations / 20); -- Report every 5%
    
    RAISE NOTICE 'Starting generation of % business unit combinations...', total_combinations;
    
    -- Loop through all product lines
    FOR pl_record IN 
        SELECT product_line_id, product_line_name, product_category, industry_sector
        FROM product_lines 
        WHERE is_active = TRUE
        ORDER BY industry_sector, product_line_name
    LOOP
        -- Loop through all locations for each product line
        FOR loc_record IN
            SELECT location_code, location_name, location_level, country_code
            FROM reporting_locations
            WHERE is_active = TRUE
            ORDER BY location_level, location_name
        LOOP
            processed_count := processed_count + 1;
            
            -- Generate business unit identifiers
            unit_id := 'BU-' || pl_record.product_line_id || '-' || loc_record.location_code;
            generated_code := pl_record.product_line_id || loc_record.location_code;
            unit_name := generate_business_unit_name(pl_record.product_line_name, loc_record.location_name, loc_record.location_level);
            short_name := LEFT(pl_record.product_line_id || '-' || LEFT(loc_record.location_name, 10), 20);
            
            -- Determine unit characteristics
            unit_type := determine_unit_type(pl_record.product_category, pl_record.industry_sector, loc_record.location_level);
            responsibility_type := CASE unit_type 
                WHEN 'PROFIT_CENTER' THEN 'PROFIT'
                WHEN 'BOTH' THEN 'PROFIT'
                ELSE 'COST'
            END;
            unit_category := CASE 
                WHEN loc_record.location_level IN ('GLOBAL', 'REGION') THEN 'OVERHEAD'
                WHEN unit_type = 'PROFIT_CENTER' THEN 'REVENUE'
                ELSE 'STANDARD'
            END;
            
            -- Insert business unit (with conflict handling)
            BEGIN
                INSERT INTO business_units (
                    unit_id,
                    unit_name,
                    short_name,
                    unit_type,
                    unit_category,
                    responsibility_type,
                    company_code_id,
                    product_line_id,
                    location_code,
                    department,
                    segment,
                    planning_enabled,
                    margin_analysis_enabled,
                    is_active,
                    status,
                    local_currency,
                    created_by,
                    valid_from
                ) VALUES (
                    unit_id,
                    unit_name,
                    short_name,
                    unit_type,
                    unit_category,
                    responsibility_type,
                    'C001', -- Default company
                    pl_record.product_line_id,
                    loc_record.location_code,
                    pl_record.industry_sector,
                    CASE loc_record.location_level 
                        WHEN 'GLOBAL' THEN 'GLOBAL'
                        WHEN 'REGION' THEN 'REGIONAL'
                        ELSE 'LOCAL'
                    END,
                    TRUE, -- Planning enabled
                    (unit_type IN ('PROFIT_CENTER', 'BOTH')), -- Margin analysis for profit centers
                    TRUE, -- Active
                    'ACTIVE',
                    CASE loc_record.country_code
                        WHEN 'US' THEN 'USD'
                        WHEN 'GB' THEN 'GBP'
                        WHEN 'DE' THEN 'EUR'
                        WHEN 'FR' THEN 'EUR'
                        WHEN 'JP' THEN 'JPY'
                        WHEN 'CA' THEN 'CAD'
                        WHEN 'AU' THEN 'AUD'
                        ELSE 'USD'
                    END,
                    'SYSTEM_GENERATOR',
                    CURRENT_DATE
                );
                
                success_count := success_count + 1;
                
            EXCEPTION 
                WHEN unique_violation THEN
                    -- Skip duplicates silently
                    NULL;
                WHEN OTHERS THEN
                    -- Log other errors but continue
                    RAISE WARNING 'Failed to create business unit %: %', unit_id, SQLERRM;
            END;
            
            -- Progress reporting
            IF processed_count % progress_interval = 0 THEN
                RAISE NOTICE 'Progress: %/% (%.1f%%) - Created: % units', 
                    processed_count, total_combinations,
                    (processed_count::DECIMAL / total_combinations * 100),
                    success_count;
            END IF;
        END LOOP;
    END LOOP;
    
    RAISE NOTICE '=== BUSINESS UNIT GENERATION COMPLETE ===';
    RAISE NOTICE 'Total Combinations Processed: %', processed_count;
    RAISE NOTICE 'Business Units Created: %', success_count;
    RAISE NOTICE 'Success Rate: %.2f%%', (success_count::DECIMAL / processed_count * 100);
END $$;

-- Step 5: Analyze the generated business units
SELECT 'Business Unit Generation Summary:' as info;

-- Show creation statistics
SELECT 
    'Generation Statistics' as category,
    COUNT(*) as total_business_units,
    COUNT(CASE WHEN generated_code IS NOT NULL THEN 1 END) as product_location_units,
    COUNT(CASE WHEN unit_type = 'COST_CENTER' THEN 1 END) as cost_centers,
    COUNT(CASE WHEN unit_type = 'PROFIT_CENTER' THEN 1 END) as profit_centers,
    COUNT(CASE WHEN unit_type = 'BOTH' THEN 1 END) as dual_purpose_units
FROM business_units;

-- Show distribution by industry sector
SELECT 'Industry Distribution:' as info;
SELECT 
    pl.industry_sector,
    COUNT(*) as business_units_count,
    COUNT(CASE WHEN bu.unit_type = 'PROFIT_CENTER' THEN 1 END) as profit_centers,
    COUNT(CASE WHEN bu.unit_type = 'COST_CENTER' THEN 1 END) as cost_centers
FROM business_units bu
INNER JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
WHERE bu.generated_code IS NOT NULL
GROUP BY pl.industry_sector
ORDER BY business_units_count DESC
LIMIT 10;

-- Show distribution by location level
SELECT 'Location Level Distribution:' as info;
SELECT 
    rl.location_level,
    COUNT(*) as business_units_count,
    COUNT(CASE WHEN bu.unit_type = 'PROFIT_CENTER' THEN 1 END) as profit_centers,
    COUNT(CASE WHEN bu.unit_type = 'BOTH' THEN 1 END) as dual_purpose
FROM business_units bu
INNER JOIN reporting_locations rl ON bu.location_code = rl.location_code
WHERE bu.generated_code IS NOT NULL
GROUP BY rl.location_level
ORDER BY business_units_count DESC;

-- Show sample of generated business units
SELECT 'Sample Generated Business Units:' as info;
SELECT 
    bu.unit_id,
    bu.unit_name,
    bu.unit_type,
    pl.product_line_name,
    pl.industry_sector,
    rl.location_name,
    rl.location_level,
    rl.country_code,
    bu.generated_code,
    bu.local_currency
FROM business_units bu
INNER JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
INNER JOIN reporting_locations rl ON bu.location_code = rl.location_code
WHERE bu.created_by = 'SYSTEM_GENERATOR'
ORDER BY pl.industry_sector, rl.location_level, bu.unit_name
LIMIT 20;

-- Step 6: Create summary view for the massive business units dataset
CREATE OR REPLACE VIEW v_generated_business_units_summary AS
SELECT 
    pl.industry_sector,
    rl.location_level,
    rl.country_code,
    bu.unit_type,
    bu.responsibility_type,
    bu.local_currency,
    COUNT(*) as units_count,
    string_agg(DISTINCT bu.unit_category, ', ') as categories,
    MIN(bu.created_at) as first_created,
    MAX(bu.created_at) as last_created
FROM business_units bu
INNER JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
INNER JOIN reporting_locations rl ON bu.location_code = rl.location_code
WHERE bu.created_by = 'SYSTEM_GENERATOR'
AND bu.generated_code IS NOT NULL
GROUP BY pl.industry_sector, rl.location_level, rl.country_code, 
         bu.unit_type, bu.responsibility_type, bu.local_currency
ORDER BY pl.industry_sector, rl.location_level, units_count DESC;

-- Grant permissions
GRANT SELECT ON v_generated_business_units_summary TO PUBLIC;

-- Clean up helper functions (optional)
-- DROP FUNCTION IF EXISTS generate_business_unit_name(VARCHAR, VARCHAR, VARCHAR);
-- DROP FUNCTION IF EXISTS determine_unit_type(VARCHAR, VARCHAR, VARCHAR);

-- Step 7: Final verification and health check
DO $$
DECLARE
    total_business_units INTEGER;
    product_location_units INTEGER;
    unique_products INTEGER;
    unique_locations INTEGER;
    coverage_percentage DECIMAL;
BEGIN
    SELECT COUNT(*) INTO total_business_units FROM business_units WHERE is_active = TRUE;
    SELECT COUNT(*) INTO product_location_units FROM business_units WHERE generated_code IS NOT NULL;
    SELECT COUNT(DISTINCT product_line_id) INTO unique_products FROM business_units WHERE generated_code IS NOT NULL;
    SELECT COUNT(DISTINCT location_code) INTO unique_locations FROM business_units WHERE generated_code IS NOT NULL;
    
    coverage_percentage := (product_location_units::DECIMAL / 
                           ((SELECT COUNT(*) FROM product_lines WHERE is_active = TRUE) * 
                            (SELECT COUNT(*) FROM reporting_locations WHERE is_active = TRUE))) * 100;
    
    RAISE NOTICE '=== FINAL BUSINESS UNITS SYSTEM STATUS ===';
    RAISE NOTICE 'Total Active Business Units: %', total_business_units;
    RAISE NOTICE 'Product-Location Business Units: %', product_location_units;
    RAISE NOTICE 'Product Lines Covered: %', unique_products;
    RAISE NOTICE 'Locations Covered: %', unique_locations;
    RAISE NOTICE 'Matrix Coverage: %.2f%%', coverage_percentage;
    RAISE NOTICE '==============================================';
    RAISE NOTICE 'Global Business Unit Matrix Generation: COMPLETE';
END $$;

-- =====================================================
-- Global Business Unit Matrix Generation Complete
-- =====================================================
-- Result: Comprehensive business units created for every
--         product line and location combination, providing
--         complete global operational structure for
--         multi-dimensional financial analysis and reporting
-- =====================================================