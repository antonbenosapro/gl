-- Migration: Integrate GL Transactions with Phase 2 Master Data
-- Date: August 7, 2025
-- Purpose: Add Phase 2 master data fields to gl_transactions and update posting logic

-- Add Phase 2 master data fields to gl_transactions table
ALTER TABLE gl_transactions ADD COLUMN IF NOT EXISTS profit_center_id VARCHAR(20);
ALTER TABLE gl_transactions ADD COLUMN IF NOT EXISTS business_area_id VARCHAR(4);
ALTER TABLE gl_transactions ADD COLUMN IF NOT EXISTS document_type VARCHAR(2) DEFAULT 'SA';

-- Add foreign key constraints for Phase 2 integration
DO $$ 
BEGIN
    -- Add profit center FK if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_gl_transactions_profit_center'
    ) THEN
        ALTER TABLE gl_transactions ADD CONSTRAINT fk_gl_transactions_profit_center 
            FOREIGN KEY (profit_center_id) REFERENCES profit_centers(profit_center_id);
    END IF;
    
    -- Add business area FK if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_gl_transactions_business_area'
    ) THEN
        ALTER TABLE gl_transactions ADD CONSTRAINT fk_gl_transactions_business_area 
            FOREIGN KEY (business_area_id) REFERENCES business_areas(business_area_id);
    END IF;
    
    -- Add document type FK if not exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_gl_transactions_document_type'
    ) THEN
        ALTER TABLE gl_transactions ADD CONSTRAINT fk_gl_transactions_document_type 
            FOREIGN KEY (document_type) REFERENCES document_types(document_type);
    END IF;
END $$;

-- Create indexes for Phase 2 fields for performance
CREATE INDEX IF NOT EXISTS idx_gl_transactions_profit_center ON gl_transactions(profit_center_id);
CREATE INDEX IF NOT EXISTS idx_gl_transactions_business_area ON gl_transactions(business_area_id);
CREATE INDEX IF NOT EXISTS idx_gl_transactions_document_type ON gl_transactions(document_type);
CREATE INDEX IF NOT EXISTS idx_gl_transactions_phase2_combo ON gl_transactions(profit_center_id, business_area_id);

-- Update existing transactions with Phase 2 data based on derivation rules
-- This will populate Phase 2 fields for existing transactions using intelligent derivation

-- Step 1: Update document_type for existing transactions
UPDATE gl_transactions 
SET document_type = CASE 
    WHEN source_doc_type = 'JE' THEN 'SA'  -- Journal Entry → Standard Accounting
    WHEN source_doc_type = 'AP' THEN 'KR'  -- Accounts Payable → Vendor Invoice
    WHEN source_doc_type = 'AR' THEN 'DR'  -- Accounts Receivable → Customer Invoice  
    WHEN source_doc_type = 'CASH' THEN 'CA' -- Cash → Cash Journal
    ELSE 'SA'
END
WHERE document_type IS NULL OR document_type = 'SA';

-- Step 2: Update profit_center_id based on cost_center assignments and GL account derivation
UPDATE gl_transactions 
SET profit_center_id = CASE 
    -- First try cost center default profit center
    WHEN cost_center IS NOT NULL THEN (
        SELECT cc.default_profit_center 
        FROM costcenter cc 
        WHERE cc.costcenterid = gl_transactions.cost_center
        AND cc.default_profit_center IS NOT NULL
        LIMIT 1
    )
    -- Then try GL account default profit center  
    WHEN gl_account IS NOT NULL THEN (
        SELECT ga.default_profit_center
        FROM glaccount ga
        WHERE ga.glaccountid = gl_transactions.gl_account
        AND ga.default_profit_center IS NOT NULL
        LIMIT 1
    )
    -- Finally, use derivation rules from profit center assignments
    ELSE (
        SELECT pca.profit_center_id
        FROM profit_center_assignments pca
        WHERE pca.object_type = 'GLACCOUNT'
        AND pca.object_id = gl_transactions.gl_account
        AND pca.is_active = TRUE
        AND CURRENT_DATE BETWEEN pca.valid_from AND pca.valid_to
        ORDER BY pca.priority
        LIMIT 1
    )
END
WHERE profit_center_id IS NULL;

-- Step 3: Update business_area_id using similar logic
UPDATE gl_transactions 
SET business_area_id = CASE 
    -- First try cost center default business area
    WHEN cost_center IS NOT NULL THEN (
        SELECT cc.default_business_area 
        FROM costcenter cc 
        WHERE cc.costcenterid = gl_transactions.cost_center
        AND cc.default_business_area IS NOT NULL
        LIMIT 1
    )
    -- Then try GL account default business area
    WHEN gl_account IS NOT NULL THEN (
        SELECT ga.default_business_area
        FROM glaccount ga
        WHERE ga.glaccountid = gl_transactions.gl_account
        AND ga.default_business_area IS NOT NULL
        LIMIT 1
    )
    -- Then use business area derivation rules
    ELSE (
        SELECT badr.target_business_area
        FROM business_area_derivation_rules badr
        WHERE badr.is_active = TRUE
        AND CURRENT_DATE BETWEEN badr.effective_from AND badr.effective_to
        AND (
            (badr.source_field = 'GL_ACCOUNT' AND badr.condition_value = gl_transactions.gl_account) OR
            (badr.source_field = 'COST_CENTER' AND badr.condition_value = gl_transactions.cost_center) OR
            (badr.source_field = 'GL_ACCOUNT' AND badr.condition_operator = 'LIKE' 
             AND gl_transactions.gl_account LIKE badr.condition_value)
        )
        ORDER BY badr.priority
        LIMIT 1
    )
    -- Finally, try business area assignments
    WHEN business_area_id IS NULL THEN (
        SELECT baa.business_area_id
        FROM business_area_assignments baa
        WHERE baa.object_type = 'GLACCOUNT'
        AND baa.object_id = gl_transactions.gl_account
        AND baa.is_active = TRUE
        AND CURRENT_DATE BETWEEN baa.valid_from AND baa.valid_to
        ORDER BY baa.assignment_percentage DESC
        LIMIT 1
    )
END
WHERE business_area_id IS NULL;

-- Step 4: Set fallback values for transactions that couldn't be derived
UPDATE gl_transactions 
SET 
    profit_center_id = COALESCE(profit_center_id, 'PC-CORP'),
    business_area_id = COALESCE(business_area_id, 'CORP')
WHERE profit_center_id IS NULL OR business_area_id IS NULL;

-- Create enhanced GL transactions summary view with Phase 2 integration
CREATE OR REPLACE VIEW v_gl_transactions_summary AS
SELECT 
    gt.transaction_id,
    gt.document_number,
    gt.line_item,
    gt.posting_date,
    gt.gl_account,
    ga.accountname,
    gt.cost_center,
    cc.name as cost_center_name,
    gt.profit_center_id,
    pc.profit_center_name,
    gt.business_area_id,
    ba.business_area_name,
    gt.document_type,
    dt.document_type_name,
    gt.ledger_id,
    gt.debit_amount,
    gt.credit_amount,
    gt.local_currency_amount,
    gt.document_currency,
    gt.line_text,
    gt.posted_by,
    gt.posted_at,
    gt.document_status
FROM gl_transactions gt
LEFT JOIN glaccount ga ON gt.gl_account = ga.glaccountid
LEFT JOIN costcenter cc ON gt.cost_center = cc.costcenterid
LEFT JOIN profit_centers pc ON gt.profit_center_id = pc.profit_center_id
LEFT JOIN business_areas ba ON gt.business_area_id = ba.business_area_id
LEFT JOIN document_types dt ON gt.document_type = dt.document_type;

-- Create Phase 2 analytics view for management reporting
CREATE OR REPLACE VIEW v_gl_phase2_analytics AS
SELECT 
    gt.fiscal_year,
    gt.posting_period,
    gt.profit_center_id,
    pc.profit_center_name,
    gt.business_area_id,
    ba.business_area_name,
    gt.document_type,
    dt.document_type_name,
    gt.cost_center,
    cc.name as cost_center_name,
    COUNT(*) as transaction_count,
    SUM(CASE WHEN gt.debit_amount IS NOT NULL THEN gt.debit_amount ELSE 0 END) as total_debits,
    SUM(CASE WHEN gt.credit_amount IS NOT NULL THEN gt.credit_amount ELSE 0 END) as total_credits,
    SUM(gt.local_currency_amount) as net_amount
FROM gl_transactions gt
LEFT JOIN profit_centers pc ON gt.profit_center_id = pc.profit_center_id
LEFT JOIN business_areas ba ON gt.business_area_id = ba.business_area_id
LEFT JOIN document_types dt ON gt.document_type = dt.document_type
LEFT JOIN costcenter cc ON gt.cost_center = cc.costcenterid
WHERE gt.document_status = 'ACTIVE'
GROUP BY 
    gt.fiscal_year, gt.posting_period, gt.profit_center_id, pc.profit_center_name,
    gt.business_area_id, ba.business_area_name, gt.document_type, dt.document_type_name,
    gt.cost_center, cc.name;

-- Create audit trail view for Phase 2 field changes
CREATE OR REPLACE VIEW v_gl_phase2_audit AS
SELECT 
    gt.transaction_id,
    gt.document_number,
    gt.posting_date,
    gt.gl_account,
    gt.profit_center_id,
    CASE 
        WHEN gt.profit_center_id IS NOT NULL THEN 'ASSIGNED'
        ELSE 'NOT_ASSIGNED'
    END as profit_center_status,
    gt.business_area_id,
    CASE 
        WHEN gt.business_area_id IS NOT NULL THEN 'ASSIGNED' 
        ELSE 'NOT_ASSIGNED'
    END as business_area_status,
    gt.document_type,
    gt.posted_by,
    gt.posted_at
FROM gl_transactions gt;

-- Create function for automatic Phase 2 field derivation during posting
CREATE OR REPLACE FUNCTION derive_phase2_fields(
    p_gl_account VARCHAR(10),
    p_cost_center VARCHAR(10),
    p_document_type VARCHAR(2) DEFAULT 'SA'
) 
RETURNS TABLE(
    derived_profit_center VARCHAR(20),
    derived_business_area VARCHAR(4)
) AS $$
BEGIN
    -- Derive profit center
    SELECT INTO derived_profit_center
        CASE 
            -- First try cost center default
            WHEN p_cost_center IS NOT NULL THEN (
                SELECT cc.default_profit_center 
                FROM costcenter cc 
                WHERE cc.costcenterid = p_cost_center
                AND cc.default_profit_center IS NOT NULL
                LIMIT 1
            )
            -- Then try GL account default
            WHEN p_gl_account IS NOT NULL THEN (
                SELECT ga.default_profit_center
                FROM glaccount ga
                WHERE ga.glaccountid = p_gl_account
                AND ga.default_profit_center IS NOT NULL
                LIMIT 1
            )
            -- Finally use assignments
            ELSE (
                SELECT pca.profit_center_id
                FROM profit_center_assignments pca
                WHERE pca.object_type = 'GLACCOUNT'
                AND pca.object_id = p_gl_account
                AND pca.is_active = TRUE
                ORDER BY pca.priority
                LIMIT 1
            )
        END;
    
    -- Derive business area
    SELECT INTO derived_business_area
        CASE 
            -- First try cost center default
            WHEN p_cost_center IS NOT NULL THEN (
                SELECT cc.default_business_area 
                FROM costcenter cc 
                WHERE cc.costcenterid = p_cost_center
                AND cc.default_business_area IS NOT NULL
                LIMIT 1
            )
            -- Then try GL account default  
            WHEN p_gl_account IS NOT NULL THEN (
                SELECT ga.default_business_area
                FROM glaccount ga
                WHERE ga.glaccountid = p_gl_account
                AND ga.default_business_area IS NOT NULL
                LIMIT 1
            )
            -- Use derivation rules
            ELSE (
                SELECT badr.target_business_area
                FROM business_area_derivation_rules badr
                WHERE badr.is_active = TRUE
                AND (
                    (badr.source_field = 'GL_ACCOUNT' AND badr.condition_value = p_gl_account) OR
                    (badr.source_field = 'COST_CENTER' AND badr.condition_value = p_cost_center)
                )
                ORDER BY badr.priority
                LIMIT 1
            )
        END;
    
    -- Set defaults if still null
    derived_profit_center := COALESCE(derived_profit_center, 'PC-CORP');
    derived_business_area := COALESCE(derived_business_area, 'CORP');
    
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically populate Phase 2 fields on new transactions
CREATE OR REPLACE FUNCTION populate_phase2_fields()
RETURNS TRIGGER AS $$
DECLARE
    derived_fields RECORD;
BEGIN
    -- Only populate if fields are not already set
    IF NEW.profit_center_id IS NULL OR NEW.business_area_id IS NULL THEN
        SELECT * INTO derived_fields 
        FROM derive_phase2_fields(NEW.gl_account, NEW.cost_center, NEW.document_type);
        
        NEW.profit_center_id := COALESCE(NEW.profit_center_id, derived_fields.derived_profit_center);
        NEW.business_area_id := COALESCE(NEW.business_area_id, derived_fields.derived_business_area);
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create the trigger
DROP TRIGGER IF EXISTS tr_gl_transactions_phase2_derivation ON gl_transactions;
CREATE TRIGGER tr_gl_transactions_phase2_derivation
    BEFORE INSERT OR UPDATE ON gl_transactions
    FOR EACH ROW
    EXECUTE FUNCTION populate_phase2_fields();

-- Add comments for documentation
COMMENT ON COLUMN gl_transactions.profit_center_id IS 'Profit center for profitability analysis - derived automatically';
COMMENT ON COLUMN gl_transactions.business_area_id IS 'Business area for segment reporting - derived automatically';
COMMENT ON COLUMN gl_transactions.document_type IS 'Document type for posting control - derived from source';

COMMENT ON VIEW v_gl_transactions_summary IS 'Enhanced GL transactions view with Phase 2 master data integration';
COMMENT ON VIEW v_gl_phase2_analytics IS 'Phase 2 analytics for management reporting by profit center and business area';
COMMENT ON FUNCTION derive_phase2_fields(VARCHAR, VARCHAR, VARCHAR) IS 'Automatic derivation of Phase 2 fields based on master data rules';

-- Analyze updated table for query optimization
ANALYZE gl_transactions;

-- Print integration summary
DO $$
DECLARE
    total_transactions INTEGER;
    with_profit_center INTEGER;
    with_business_area INTEGER;
    with_both INTEGER;
BEGIN
    SELECT COUNT(*) INTO total_transactions FROM gl_transactions;
    SELECT COUNT(*) INTO with_profit_center FROM gl_transactions WHERE profit_center_id IS NOT NULL;
    SELECT COUNT(*) INTO with_business_area FROM gl_transactions WHERE business_area_id IS NOT NULL;
    SELECT COUNT(*) INTO with_both FROM gl_transactions WHERE profit_center_id IS NOT NULL AND business_area_id IS NOT NULL;
    
    RAISE NOTICE 'GL Transactions Phase 2 Integration Summary:';
    RAISE NOTICE '  Total Transactions: %', total_transactions;
    RAISE NOTICE '  With Profit Center: % (%.1f%%)', with_profit_center, (with_profit_center::numeric / total_transactions * 100);
    RAISE NOTICE '  With Business Area: % (%.1f%%)', with_business_area, (with_business_area::numeric / total_transactions * 100);
    RAISE NOTICE '  With Both Fields: % (%.1f%%)', with_both, (with_both::numeric / total_transactions * 100);
END $$;