-- =====================================================
-- Create Unified Business Units Table
-- =====================================================
-- Author: Claude Code Assistant
-- Date: August 7, 2025
-- Description: Create unified business_units table to replace
--              separate costcenter and profit_centers tables with
--              integrated Product Line and Location support
-- =====================================================

-- Step 1: Create the unified business_units table
CREATE TABLE business_units (
    -- Primary Identification
    unit_id VARCHAR(20) PRIMARY KEY,              -- Unified identifier (e.g., BU-SMART-NYC)
    unit_name VARCHAR(100) NOT NULL,              -- Full name (e.g., Smartphones Business Unit NYC)
    short_name VARCHAR(20) NOT NULL,              -- Abbreviated name (e.g., SMART-NYC)
    description TEXT,                             -- Detailed description
    
    -- Business Unit Classification
    unit_type VARCHAR(15) NOT NULL                -- COST_CENTER, PROFIT_CENTER, BOTH
        CHECK (unit_type IN ('COST_CENTER', 'PROFIT_CENTER', 'BOTH')),
    unit_category VARCHAR(20) DEFAULT 'STANDARD'  -- STANDARD, OVERHEAD, REVENUE, INVESTMENT
        CHECK (unit_category IN ('STANDARD', 'OVERHEAD', 'REVENUE', 'INVESTMENT', 'SERVICE', 'AUXILIARY')),
    responsibility_type VARCHAR(15) DEFAULT 'COST' -- COST, REVENUE, PROFIT, INVESTMENT
        CHECK (responsibility_type IN ('COST', 'REVENUE', 'PROFIT', 'INVESTMENT')),
    
    -- Organizational Hierarchy
    company_code_id VARCHAR(10) NOT NULL,
    controlling_area VARCHAR(4) DEFAULT 'C001',
    business_area_id VARCHAR(4),
    parent_unit_id VARCHAR(20),                   -- Self-referencing for hierarchy
    hierarchy_level INTEGER DEFAULT 1,
    unit_group VARCHAR(20),                       -- Grouping for reporting
    
    -- Product Line and Location Integration
    location_code VARCHAR(6),                     -- FK to reporting_locations
    product_line_id VARCHAR(4),                   -- FK to product_lines  
    generated_code VARCHAR(10) GENERATED ALWAYS AS (
        CASE 
            WHEN product_line_id IS NOT NULL AND location_code IS NOT NULL 
            THEN COALESCE(product_line_id, '0000') || location_code
            ELSE NULL
        END
    ) STORED,                                     -- Automatic 4+6 digit code generation
    
    -- Management and Control
    person_responsible VARCHAR(100),              -- Manager/Owner
    person_responsible_email VARCHAR(100),        -- Contact email
    department VARCHAR(50),                       -- Department assignment
    segment VARCHAR(20),                          -- Business segment
    division VARCHAR(20),                         -- Division assignment
    
    -- Cost Center Specific Fields
    planning_enabled BOOLEAN DEFAULT TRUE,        -- Budget planning enabled
    budget_profile VARCHAR(20),                   -- Budget profile reference
    cost_center_type VARCHAR(15) DEFAULT 'ACTUAL' -- ACTUAL, STATISTICAL
        CHECK (cost_center_type IN ('ACTUAL', 'STATISTICAL', 'AUXILIARY')),
    
    -- Profit Center Specific Fields  
    default_cost_center VARCHAR(20),              -- Associated cost center
    profit_center_type VARCHAR(15) DEFAULT 'ACTUAL' -- ACTUAL, DUMMY
        CHECK (profit_center_type IN ('ACTUAL', 'DUMMY', 'DERIVED')),
    revenue_recognition VARCHAR(20),              -- Revenue recognition method
    margin_analysis_enabled BOOLEAN DEFAULT FALSE, -- Enable margin analysis
    
    -- Financial and Currency
    local_currency VARCHAR(3) DEFAULT 'USD',
    functional_currency VARCHAR(3) DEFAULT 'USD',
    
    -- Performance and Analytics
    kpi_enabled BOOLEAN DEFAULT TRUE,             -- Enable KPI tracking
    analytics_enabled BOOLEAN DEFAULT TRUE,      -- Enable analytics
    consolidation_unit VARCHAR(20),               -- Consolidation reference
    
    -- Operational Attributes
    is_manufacturing BOOLEAN DEFAULT FALSE,       -- Manufacturing unit
    is_sales BOOLEAN DEFAULT FALSE,               -- Sales unit
    is_service BOOLEAN DEFAULT FALSE,             -- Service unit
    is_overhead BOOLEAN DEFAULT FALSE,            -- Overhead unit
    is_external BOOLEAN DEFAULT FALSE,            -- External unit (partners)
    
    -- Validity and Status
    valid_from DATE DEFAULT CURRENT_DATE,
    valid_to DATE DEFAULT '9999-12-31',
    is_active BOOLEAN DEFAULT TRUE,
    status VARCHAR(10) DEFAULT 'ACTIVE'           -- ACTIVE, INACTIVE, BLOCKED
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
    FOREIGN KEY (parent_unit_id) REFERENCES business_units(unit_id),
    
    -- Business Logic Constraints
    CONSTRAINT chk_profit_center_fields 
        CHECK (
            CASE 
                WHEN unit_type IN ('PROFIT_CENTER', 'BOTH') 
                THEN margin_analysis_enabled IS NOT NULL
                ELSE TRUE
            END
        ),
    CONSTRAINT chk_cost_center_fields
        CHECK (
            CASE 
                WHEN unit_type IN ('COST_CENTER', 'BOTH')
                THEN planning_enabled IS NOT NULL
                ELSE TRUE
            END
        ),
    CONSTRAINT chk_valid_date_range
        CHECK (valid_from <= valid_to)
);

-- Step 2: Create indexes for optimal performance
CREATE INDEX idx_business_units_type ON business_units(unit_type);
CREATE INDEX idx_business_units_company ON business_units(company_code_id);
CREATE INDEX idx_business_units_business_area ON business_units(business_area_id);
CREATE INDEX idx_business_units_location ON business_units(location_code);
CREATE INDEX idx_business_units_product_line ON business_units(product_line_id);
CREATE INDEX idx_business_units_generated_code ON business_units(generated_code);
CREATE INDEX idx_business_units_parent ON business_units(parent_unit_id);
CREATE INDEX idx_business_units_hierarchy ON business_units(hierarchy_level);
CREATE INDEX idx_business_units_active ON business_units(is_active);
CREATE INDEX idx_business_units_valid_from ON business_units(valid_from);
CREATE INDEX idx_business_units_person ON business_units(person_responsible);
CREATE INDEX idx_business_units_status ON business_units(status);

-- Step 3: Create trigger for automatic modified timestamp update
CREATE OR REPLACE FUNCTION update_business_units_modified()
RETURNS TRIGGER AS $$
BEGIN
    NEW.modified_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_business_units_modified
BEFORE UPDATE ON business_units
FOR EACH ROW EXECUTE FUNCTION update_business_units_modified();

-- Step 4: Create helper functions for business unit operations
CREATE OR REPLACE FUNCTION generate_business_unit_code(
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

CREATE OR REPLACE FUNCTION decode_business_unit_code(
    p_unit_code VARCHAR(10)
) RETURNS TABLE(product_line_id VARCHAR(4), location_code VARCHAR(6)) AS $$
BEGIN
    -- Only decode if code is exactly 10 characters
    IF LENGTH(p_unit_code) != 10 THEN
        RETURN;
    END IF;
    
    RETURN QUERY
    SELECT 
        SUBSTRING(p_unit_code FROM 1 FOR 4)::VARCHAR(4) AS product_line_id,
        SUBSTRING(p_unit_code FROM 5 FOR 6)::VARCHAR(6) AS location_code;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION validate_business_unit(
    p_unit_type VARCHAR(15),
    p_responsibility_type VARCHAR(15)
) RETURNS BOOLEAN AS $$
BEGIN
    -- Business logic validation
    CASE p_unit_type
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
CREATE OR REPLACE VIEW v_business_unit_hierarchy AS
WITH RECURSIVE unit_tree AS (
    -- Root level units (no parent)
    SELECT 
        bu.unit_id,
        bu.unit_name,
        bu.unit_type,
        bu.parent_unit_id,
        bu.unit_id::VARCHAR(500) AS path,
        bu.unit_name::VARCHAR(2000) AS full_path,
        0 AS level
    FROM business_units bu
    WHERE bu.parent_unit_id IS NULL
    AND bu.is_active = TRUE
    
    UNION ALL
    
    -- Child units
    SELECT 
        bu.unit_id,
        bu.unit_name,
        bu.unit_type,
        bu.parent_unit_id,
        (ut.path || '/' || bu.unit_id)::VARCHAR(500) AS path,
        (ut.full_path || ' > ' || bu.unit_name)::VARCHAR(2000) AS full_path,
        ut.level + 1 AS level
    FROM business_units bu
    INNER JOIN unit_tree ut ON bu.parent_unit_id = ut.unit_id
    WHERE bu.is_active = TRUE
)
SELECT * FROM unit_tree
ORDER BY path;

CREATE OR REPLACE VIEW v_business_unit_enhanced AS
SELECT 
    bu.unit_id,
    bu.unit_name,
    bu.short_name,
    bu.unit_type,
    bu.responsibility_type,
    bu.unit_category,
    -- Location information
    bu.location_code,
    rl.location_name,
    rl.location_level,
    rl.country_code,
    rl.location_type,
    -- Product line information  
    bu.product_line_id,
    pl.product_line_name,
    pl.product_category,
    pl.lifecycle_stage,
    pl.industry_sector,
    -- Generated code
    bu.generated_code,
    -- Management information
    bu.person_responsible,
    bu.department,
    bu.business_area_id,
    ba.business_area_name,
    -- Status and validity
    bu.is_active,
    bu.valid_from,
    bu.valid_to,
    bu.status
FROM business_units bu
LEFT JOIN reporting_locations rl ON bu.location_code = rl.location_code
LEFT JOIN product_lines pl ON bu.product_line_id = pl.product_line_id
LEFT JOIN business_areas ba ON bu.business_area_id = ba.business_area_id;

-- Step 6: Grant appropriate permissions
GRANT SELECT, INSERT, UPDATE ON business_units TO PUBLIC;
GRANT SELECT ON v_business_unit_hierarchy TO PUBLIC;
GRANT SELECT ON v_business_unit_enhanced TO PUBLIC;

-- =====================================================
-- Table Created Successfully
-- =====================================================
-- Created: business_units table with full feature set
-- Features: 
--   - Unified cost center and profit center management
--   - Integrated Product Line and Location support  
--   - Automatic 10-digit code generation (4+6)
--   - Hierarchical organization structure
--   - Enhanced analytics and reporting capabilities
--   - Performance-optimized indexes
--   - Business logic validation functions
--   - Comprehensive audit trail
-- 
-- Next Steps:
--   1. Run data migration scripts
--   2. Create backward compatibility views
--   3. Update GL transactions integration
--   4. Create Business Unit Management UI
-- =====================================================