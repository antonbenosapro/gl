-- =====================================================
-- Create Unified Responsibility Centers Table
-- =====================================================
-- Author: Claude Code Assistant
-- Date: August 7, 2025
-- Description: Create unified responsibility_centers table to replace
--              separate costcenter and profit_centers tables with
--              integrated Product Line and Location support
-- =====================================================

-- Step 1: Create the unified responsibility_centers table
CREATE TABLE responsibility_centers (
    -- Primary Identification
    center_id VARCHAR(20) PRIMARY KEY,              -- Unified identifier
    center_name VARCHAR(100) NOT NULL,              -- Full name
    short_name VARCHAR(20) NOT NULL,                -- Abbreviated name
    description TEXT,                               -- Detailed description
    
    -- Center Classification and Type
    center_type VARCHAR(15) NOT NULL                -- COST_CENTER, PROFIT_CENTER, BOTH
        CHECK (center_type IN ('COST_CENTER', 'PROFIT_CENTER', 'BOTH')),
    center_category VARCHAR(20) DEFAULT 'STANDARD'  -- STANDARD, OVERHEAD, REVENUE, INVESTMENT, etc.
        CHECK (center_category IN ('STANDARD', 'OVERHEAD', 'REVENUE', 'INVESTMENT', 'SERVICE', 'AUXILIARY')),
    responsibility_type VARCHAR(15) DEFAULT 'COST'  -- COST, REVENUE, PROFIT, INVESTMENT
        CHECK (responsibility_type IN ('COST', 'REVENUE', 'PROFIT', 'INVESTMENT')),
    
    -- Organizational Hierarchy
    company_code_id VARCHAR(10) NOT NULL,
    controlling_area VARCHAR(4) DEFAULT 'C001',
    business_area_id VARCHAR(4),
    parent_center_id VARCHAR(20),                   -- Self-referencing for hierarchy
    hierarchy_level INTEGER DEFAULT 1,
    center_group VARCHAR(20),                       -- Grouping for reporting
    
    -- Product Line and Location Integration (NEW!)
    location_code VARCHAR(6),                       -- FK to reporting_locations
    product_line_id VARCHAR(4),                     -- FK to product_lines
    generated_code VARCHAR(10) GENERATED ALWAYS AS (
        CASE 
            WHEN product_line_id IS NOT NULL AND location_code IS NOT NULL 
            THEN COALESCE(product_line_id, '0000') || location_code
            ELSE NULL
        END
    ) STORED,                                       -- Automatic 4+6 digit code generation
    
    -- Management and Control
    person_responsible VARCHAR(100),                -- Manager/Owner
    person_responsible_email VARCHAR(100),          -- Contact email
    department VARCHAR(50),                         -- Department assignment
    segment VARCHAR(20),                            -- Business segment
    division VARCHAR(20),                           -- Division assignment
    
    -- Cost Center Specific Fields
    planning_enabled BOOLEAN DEFAULT TRUE,          -- Budget planning enabled
    budget_profile VARCHAR(20),                     -- Budget profile reference
    cost_center_type VARCHAR(15) DEFAULT 'ACTUAL'  -- ACTUAL, STATISTICAL, etc.
        CHECK (cost_center_type IN ('ACTUAL', 'STATISTICAL', 'AUXILIARY')),
    overhead_allocation VARCHAR(15),                -- Overhead allocation method
    
    -- Profit Center Specific Fields  
    default_cost_center VARCHAR(20),                -- Associated cost center
    profit_center_type VARCHAR(15) DEFAULT 'ACTUAL' -- ACTUAL, DUMMY, etc.
        CHECK (profit_center_type IN ('ACTUAL', 'DUMMY', 'DERIVED')),
    revenue_recognition VARCHAR(20),                -- Revenue recognition method
    margin_analysis_enabled BOOLEAN DEFAULT FALSE, -- Enable margin analysis
    
    -- Financial and Currency
    local_currency VARCHAR(3) DEFAULT 'USD',
    functional_currency VARCHAR(3) DEFAULT 'USD',
    
    -- Performance and Analytics
    kpi_enabled BOOLEAN DEFAULT TRUE,               -- Enable KPI tracking
    analytics_enabled BOOLEAN DEFAULT TRUE,        -- Enable analytics
    consolidation_unit VARCHAR(20),                 -- Consolidation reference
    
    -- Operational Attributes
    is_manufacturing BOOLEAN DEFAULT FALSE,         -- Manufacturing center
    is_sales BOOLEAN DEFAULT FALSE,                 -- Sales center
    is_service BOOLEAN DEFAULT FALSE,               -- Service center
    is_overhead BOOLEAN DEFAULT FALSE,              -- Overhead center
    is_external BOOLEAN DEFAULT FALSE,              -- External center (partners)
    
    -- Validity and Status
    valid_from DATE DEFAULT CURRENT_DATE,
    valid_to DATE DEFAULT '9999-12-31',
    is_active BOOLEAN DEFAULT TRUE,
    status VARCHAR(10) DEFAULT 'ACTIVE'             -- ACTIVE, INACTIVE, BLOCKED
        CHECK (status IN ('ACTIVE', 'INACTIVE', 'BLOCKED', 'PLANNED')),
    
    -- Audit Trail
    created_by VARCHAR(50) DEFAULT 'SYSTEM',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_by VARCHAR(50),
    modified_at TIMESTAMP,
    
    -- Constraints and Foreign Keys
    FOREIGN KEY (company_code_id) REFERENCES company_codes(company_code_id),
    FOREIGN KEY (business_area_id) REFERENCES business_areas(business_area_id),
    FOREIGN KEY (location_code) REFERENCES reporting_locations(location_code),
    FOREIGN KEY (product_line_id) REFERENCES product_lines(product_line_id),
    FOREIGN KEY (parent_center_id) REFERENCES responsibility_centers(center_id),
    
    -- Business Logic Constraints
    CONSTRAINT chk_profit_center_fields 
        CHECK (
            CASE 
                WHEN center_type IN ('PROFIT_CENTER', 'BOTH') 
                THEN margin_analysis_enabled IS NOT NULL
                ELSE TRUE
            END
        ),
    CONSTRAINT chk_cost_center_fields
        CHECK (
            CASE 
                WHEN center_type IN ('COST_CENTER', 'BOTH')
                THEN planning_enabled IS NOT NULL
                ELSE TRUE
            END
        ),
    CONSTRAINT chk_valid_date_range
        CHECK (valid_from <= valid_to)
);

-- Step 2: Create indexes for optimal performance
CREATE INDEX idx_responsibility_centers_type ON responsibility_centers(center_type);
CREATE INDEX idx_responsibility_centers_company ON responsibility_centers(company_code_id);
CREATE INDEX idx_responsibility_centers_business_area ON responsibility_centers(business_area_id);
CREATE INDEX idx_responsibility_centers_location ON responsibility_centers(location_code);
CREATE INDEX idx_responsibility_centers_product_line ON responsibility_centers(product_line_id);
CREATE INDEX idx_responsibility_centers_generated_code ON responsibility_centers(generated_code);
CREATE INDEX idx_responsibility_centers_parent ON responsibility_centers(parent_center_id);
CREATE INDEX idx_responsibility_centers_hierarchy ON responsibility_centers(hierarchy_level);
CREATE INDEX idx_responsibility_centers_active ON responsibility_centers(is_active);
CREATE INDEX idx_responsibility_centers_valid_from ON responsibility_centers(valid_from);
CREATE INDEX idx_responsibility_centers_person ON responsibility_centers(person_responsible);

-- Step 3: Create trigger for automatic modified timestamp update
CREATE OR REPLACE FUNCTION update_responsibility_centers_modified()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_responsibility_centers_modified
BEFORE UPDATE ON responsibility_centers
FOR EACH ROW EXECUTE FUNCTION update_responsibility_centers_modified();

-- Step 4: Create helper functions for responsibility center operations
CREATE OR REPLACE FUNCTION generate_responsibility_center_code(
    p_product_line_id VARCHAR(4),
    p_location_code VARCHAR(6)
) RETURNS VARCHAR(10) AS $$
BEGIN
    -- Format: PPPPLLLLLL (Product Line + Location)
    -- Returns NULL if either parameter is NULL
    IF p_product_line_id IS NULL OR p_location_code IS NULL THEN
        RETURN NULL;
    END IF;
    
    RETURN COALESCE(p_product_line_id, '0000') || p_location_code;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION decode_responsibility_center_code(
    p_center_code VARCHAR(10)
) RETURNS TABLE(product_line_id VARCHAR(4), location_code VARCHAR(6)) AS $$
BEGIN
    -- Only decode if code is exactly 10 characters
    IF LENGTH(p_center_code) != 10 THEN
        RETURN;
    END IF;
    
    RETURN QUERY
    SELECT 
        SUBSTRING(p_center_code FROM 1 FOR 4)::VARCHAR(4) AS product_line_id,
        SUBSTRING(p_center_code FROM 5 FOR 6)::VARCHAR(6) AS location_code;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION validate_responsibility_center(
    p_center_type VARCHAR(15),
    p_responsibility_type VARCHAR(15)
) RETURNS BOOLEAN AS $$
BEGIN
    -- Business logic validation
    CASE p_center_type
        WHEN 'COST_CENTER' THEN
            RETURN p_responsibility_type IN ('COST');
        WHEN 'PROFIT_CENTER' THEN
            RETURN p_responsibility_type IN ('REVENUE', 'PROFIT');
        WHEN 'BOTH' THEN
            RETURN p_responsibility_type IN ('COST', 'REVENUE', 'PROFIT', 'INVESTMENT');
        ELSE
            RETURN FALSE;
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- Step 5: Create enhanced views for hierarchical and analytical reporting
CREATE OR REPLACE VIEW v_responsibility_center_hierarchy AS
WITH RECURSIVE center_tree AS (
    -- Root level centers (no parent)
    SELECT 
        rc.center_id,
        rc.center_name,
        rc.center_type,
        rc.parent_center_id,
        rc.center_id::VARCHAR(500) AS path,
        rc.center_name::VARCHAR(2000) AS full_path,
        0 AS level
    FROM responsibility_centers rc
    WHERE rc.parent_center_id IS NULL
    AND rc.is_active = TRUE
    
    UNION ALL
    
    -- Child centers
    SELECT 
        rc.center_id,
        rc.center_name,
        rc.center_type,
        rc.parent_center_id,
        (ct.path || '/' || rc.center_id)::VARCHAR(500) AS path,
        (ct.full_path || ' > ' || rc.center_name)::VARCHAR(2000) AS full_path,
        ct.level + 1 AS level
    FROM responsibility_centers rc
    INNER JOIN center_tree ct ON rc.parent_center_id = ct.center_id
    WHERE rc.is_active = TRUE
)
SELECT * FROM center_tree
ORDER BY path;

CREATE OR REPLACE VIEW v_responsibility_center_enhanced AS
SELECT 
    rc.center_id,
    rc.center_name,
    rc.short_name,
    rc.center_type,
    rc.responsibility_type,
    rc.center_category,
    -- Location information
    rc.location_code,
    rl.location_name,
    rl.location_level,
    rl.country_code,
    rl.location_type,
    -- Product line information  
    rc.product_line_id,
    pl.product_line_name,
    pl.product_category,
    pl.lifecycle_stage,
    pl.industry_sector,
    -- Generated code
    rc.generated_code,
    -- Management information
    rc.person_responsible,
    rc.department,
    rc.business_area_id,
    ba.business_area_name,
    -- Status and validity
    rc.is_active,
    rc.valid_from,
    rc.valid_to,
    rc.status
FROM responsibility_centers rc
LEFT JOIN reporting_locations rl ON rc.location_code = rl.location_code
LEFT JOIN product_lines pl ON rc.product_line_id = pl.product_line_id
LEFT JOIN business_areas ba ON rc.business_area_id = ba.business_area_id;

-- Step 6: Create backward compatibility views
CREATE OR REPLACE VIEW costcenter AS
SELECT 
    center_id as costcenterid,
    center_name as name,
    short_name,
    description,
    company_code_id as companycodeid,
    controlling_area,
    person_responsible,
    department,
    center_group as cost_center_group,
    parent_center_id as parent_cost_center,
    hierarchy_level,
    planning_enabled,
    budget_profile,
    cost_center_type,
    business_area_id as default_business_area,
    is_active,
    valid_from,
    valid_to,
    created_by,
    created_at,
    modified_by,
    modified_at
FROM responsibility_centers
WHERE center_type IN ('COST_CENTER', 'BOTH')
AND is_active = TRUE;

CREATE OR REPLACE VIEW profit_centers AS
SELECT
    center_id as profit_center_id,
    center_name as profit_center_name,
    short_name,
    description,
    company_code_id,
    controlling_area,
    business_area_id as business_area,
    parent_center_id as parent_profit_center,
    center_group as profit_center_group,
    hierarchy_level,
    person_responsible,
    default_cost_center as cost_center,
    segment,
    local_currency,
    valid_from,
    valid_to,
    is_active,
    created_by,
    created_at,
    modified_by,
    modified_at
FROM responsibility_centers
WHERE center_type IN ('PROFIT_CENTER', 'BOTH')
AND is_active = TRUE;

-- Step 7: Grant appropriate permissions
GRANT SELECT, INSERT, UPDATE ON responsibility_centers TO PUBLIC;
GRANT SELECT ON v_responsibility_center_hierarchy TO PUBLIC;
GRANT SELECT ON v_responsibility_center_enhanced TO PUBLIC;
GRANT SELECT ON costcenter TO PUBLIC;
GRANT SELECT ON profit_centers TO PUBLIC;

-- Step 8: Create sample data for demonstration
-- This will be populated in a separate migration after this table is created

-- =====================================================
-- Migration Summary
-- =====================================================
-- Created: responsibility_centers table with full feature set
-- Features: 
--   - Unified cost center and profit center management
--   - Integrated Product Line and Location support  
--   - Automatic 10-digit code generation (4+6)
--   - Hierarchical organization structure
--   - Enhanced analytics and reporting capabilities
--   - Backward compatibility views
--   - Performance-optimized indexes
--   - Business logic validation functions
--   - Comprehensive audit trail
-- 
-- Next Steps:
--   1. Run data migration script to populate from existing tables
--   2. Update GL transactions to reference responsibility_centers
--   3. Create UI management interface
--   4. Update reporting queries
-- =====================================================