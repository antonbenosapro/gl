-- =====================================================
-- Create Fixed Views and Complete Implementation
-- =====================================================

-- Location Hierarchy View (Fixed)
CREATE OR REPLACE VIEW v_location_hierarchy AS
WITH RECURSIVE location_tree AS (
    SELECT 
        l.location_code,
        l.location_name,
        l.location_level,
        l.parent_location,
        l.location_code::VARCHAR(500) AS path,
        l.location_name::VARCHAR(2000) AS full_path,
        0 AS level
    FROM reporting_locations l
    WHERE l.parent_location IS NULL
    
    UNION ALL
    
    SELECT 
        l.location_code,
        l.location_name,
        l.location_level,
        l.parent_location,
        (lt.path || '/' || l.location_code)::VARCHAR(500) AS path,
        (lt.full_path || ' > ' || l.location_name)::VARCHAR(2000) AS full_path,
        lt.level + 1 AS level
    FROM reporting_locations l
    INNER JOIN location_tree lt ON l.parent_location = lt.location_code
)
SELECT * FROM location_tree
ORDER BY path;

-- Product Line Hierarchy View (Fixed)
CREATE OR REPLACE VIEW v_product_line_hierarchy AS
WITH RECURSIVE product_tree AS (
    SELECT 
        p.product_line_id,
        p.product_line_name,
        p.parent_product_line,
        p.product_category,
        p.product_line_id::VARCHAR(500) AS path,
        p.product_line_name::VARCHAR(2000) AS full_path,
        0 AS level
    FROM product_lines p
    WHERE p.parent_product_line IS NULL
    
    UNION ALL
    
    SELECT 
        p.product_line_id,
        p.product_line_name,
        p.parent_product_line,
        p.product_category,
        (pt.path || '/' || p.product_line_id)::VARCHAR(500) AS path,
        (pt.full_path || ' > ' || p.product_line_name)::VARCHAR(2000) AS full_path,
        pt.level + 1 AS level
    FROM product_lines p
    INNER JOIN product_tree pt ON p.parent_product_line = pt.product_line_id
)
SELECT * FROM product_tree
ORDER BY path;

-- Cost Center Enhanced View with Location and Product Line (Fixed)
CREATE OR REPLACE VIEW v_cost_center_enhanced AS
SELECT 
    cc.costcenterid,
    cc.name AS cost_center_name,
    cc.department,
    clp.location_code,
    rl.location_name,
    rl.location_level,
    rl.country_code,
    rl.location_type,
    clp.product_line_id,
    pl.product_line_name,
    pl.product_category,
    pl.lifecycle_stage,
    clp.generated_code,
    cc.is_active
FROM costcenter cc
LEFT JOIN cost_center_location_product clp ON cc.costcenterid = clp.cost_center_id
LEFT JOIN reporting_locations rl ON clp.location_code = rl.location_code
LEFT JOIN product_lines pl ON clp.product_line_id = pl.product_line_id;

-- Profit Center Enhanced View with Location and Product Line (Fixed)
CREATE OR REPLACE VIEW v_profit_center_enhanced AS
SELECT 
    pc.profit_center_id,
    pc.profit_center_name,
    pc.company_code_id,
    plp.location_code,
    rl.location_name,
    rl.location_level,
    rl.country_code,
    rl.location_type,
    plp.product_line_id,
    pl.product_line_name,
    pl.product_category,
    pl.lifecycle_stage,
    plp.generated_code,
    pc.is_active
FROM profit_centers pc
LEFT JOIN profit_center_location_product plp ON pc.profit_center_id = plp.profit_center_id
LEFT JOIN reporting_locations rl ON plp.location_code = rl.location_code
LEFT JOIN product_lines pl ON plp.product_line_id = pl.product_line_id;

-- Grant permissions
GRANT SELECT ON v_location_hierarchy TO PUBLIC;
GRANT SELECT ON v_product_line_hierarchy TO PUBLIC;
GRANT SELECT ON v_cost_center_enhanced TO PUBLIC;
GRANT SELECT ON v_profit_center_enhanced TO PUBLIC;