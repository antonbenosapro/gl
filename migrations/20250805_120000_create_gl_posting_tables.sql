-- ================================================
-- GL POSTING TABLES MIGRATION
-- Enterprise General Ledger Posting Architecture
-- Following SAP FI-CO Best Practices
-- Date: 2025-08-05
-- ================================================

-- =================================
-- 1. FISCAL PERIOD CONTROLS TABLE
-- =================================
CREATE TABLE IF NOT EXISTS fiscal_period_controls (
    control_id             SERIAL PRIMARY KEY,
    company_code           VARCHAR(10) NOT NULL,
    fiscal_year            INTEGER NOT NULL,
    posting_period         INTEGER NOT NULL,
    
    -- Period Status
    period_status          VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    
    -- Date Ranges
    period_start_date      DATE NOT NULL,
    period_end_date        DATE NOT NULL,
    
    -- Control Settings
    allow_posting          BOOLEAN DEFAULT TRUE,
    allow_clearing         BOOLEAN DEFAULT TRUE,
    
    -- Special Periods
    is_special_period      BOOLEAN DEFAULT FALSE,
    special_period_type    VARCHAR(20), -- ADJUSTMENT, CARRYFORWARD
    
    -- Audit
    created_by             VARCHAR(50) NOT NULL,
    created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified_by       VARCHAR(50),
    last_modified_at       TIMESTAMP,
    
    UNIQUE(company_code, fiscal_year, posting_period),
    CONSTRAINT chk_period_status CHECK (
        period_status IN ('OPEN', 'CLOSED_POSTING', 'CLOSED_DISPLAY', 'LOCKED')
    ),
    CONSTRAINT chk_posting_period CHECK (posting_period BETWEEN 1 AND 16),
    CONSTRAINT fk_period_company FOREIGN KEY (company_code) REFERENCES companycode(companycodeid)
);

-- =================================
-- 2. POSTING DOCUMENTS TABLE (Document Headers)
-- =================================
CREATE TABLE IF NOT EXISTS posting_documents (
    document_id            BIGSERIAL PRIMARY KEY,
    company_code           VARCHAR(10) NOT NULL,
    document_number        VARCHAR(20) NOT NULL,
    fiscal_year            INTEGER NOT NULL,
    
    -- Document Classification
    document_type          VARCHAR(10) DEFAULT 'SA',  -- Standard Journal Entry
    source_system          VARCHAR(10) DEFAULT 'GL',
    reference              VARCHAR(50),
    
    -- Dates
    posting_date           DATE NOT NULL,
    document_date          DATE NOT NULL,
    entry_date             DATE DEFAULT CURRENT_DATE,
    
    -- Currency
    document_currency      VARCHAR(3) NOT NULL,
    exchange_rate          NUMERIC(9,5) DEFAULT 1.0,
    
    -- Totals (for validation)
    total_debit            NUMERIC(15,2) NOT NULL,
    total_credit           NUMERIC(15,2) NOT NULL,
    
    -- Source Reference
    source_document        VARCHAR(20),
    source_document_type   VARCHAR(10) DEFAULT 'JE',
    
    -- Status
    document_status        VARCHAR(10) DEFAULT 'ACTIVE',
    reversal_indicator     VARCHAR(1),
    
    -- Audit
    posted_by              VARCHAR(50) NOT NULL,
    posted_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_balanced_document CHECK (total_debit = total_credit),
    CONSTRAINT chk_document_status CHECK (document_status IN ('ACTIVE', 'REVERSED', 'PARKED')),
    CONSTRAINT fk_posting_company FOREIGN KEY (company_code) REFERENCES companycode(companycodeid),
    UNIQUE(company_code, document_number, fiscal_year)
);

-- =================================
-- 3. GL TRANSACTIONS TABLE (Main Posting Table)
-- =================================
CREATE TABLE IF NOT EXISTS gl_transactions (
    -- Primary Keys
    transaction_id          BIGSERIAL PRIMARY KEY,
    document_id            BIGINT NOT NULL,
    company_code           VARCHAR(10) NOT NULL,
    fiscal_year            INTEGER NOT NULL,
    document_number        VARCHAR(20) NOT NULL,
    line_item              INTEGER NOT NULL,
    
    -- Source Document Reference
    source_doc_number      VARCHAR(20) NOT NULL,
    source_doc_type        VARCHAR(10) DEFAULT 'JE',
    source_line_number     INTEGER,
    
    -- Account Information
    gl_account             VARCHAR(10) NOT NULL,
    ledger_id              VARCHAR(10) NOT NULL,
    cost_center            VARCHAR(10),
    
    -- Financial Data
    debit_amount           NUMERIC(15,2),
    credit_amount          NUMERIC(15,2),
    local_currency_amount  NUMERIC(15,2) NOT NULL,
    document_currency      VARCHAR(3) NOT NULL,
    exchange_rate          NUMERIC(9,5) DEFAULT 1.0,
    
    -- Dates
    posting_date           DATE NOT NULL,
    document_date          DATE NOT NULL,
    entry_date             DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Text and References
    line_text              TEXT,
    reference              VARCHAR(50),
    assignment             VARCHAR(18),
    
    -- Status and Control
    posting_period         INTEGER NOT NULL,
    posting_key            VARCHAR(2),
    document_status        VARCHAR(10) DEFAULT 'ACTIVE',
    
    -- Audit
    posted_by              VARCHAR(50) NOT NULL,
    posted_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_debit_or_credit CHECK (
        (debit_amount IS NOT NULL AND credit_amount IS NULL) OR
        (debit_amount IS NULL AND credit_amount IS NOT NULL)
    ),
    CONSTRAINT chk_amounts_positive CHECK (
        COALESCE(debit_amount, 0) >= 0 AND COALESCE(credit_amount, 0) >= 0
    ),
    CONSTRAINT chk_gl_doc_status CHECK (document_status IN ('ACTIVE', 'REVERSED', 'CLEARED')),
    CONSTRAINT fk_gl_document FOREIGN KEY (document_id) REFERENCES posting_documents(document_id),
    CONSTRAINT fk_gl_company FOREIGN KEY (company_code) REFERENCES companycode(companycodeid),
    CONSTRAINT fk_gl_account FOREIGN KEY (gl_account) REFERENCES glaccount(glaccountid),
    CONSTRAINT fk_gl_ledger FOREIGN KEY (ledger_id) REFERENCES ledger(ledgerid),
    UNIQUE(document_id, line_item)
);

-- =================================
-- 4. GL ACCOUNT BALANCES TABLE
-- =================================
CREATE TABLE IF NOT EXISTS gl_account_balances (
    balance_id             BIGSERIAL PRIMARY KEY,
    company_code           VARCHAR(10) NOT NULL,
    gl_account             VARCHAR(10) NOT NULL,
    ledger_id              VARCHAR(10) NOT NULL,
    fiscal_year            INTEGER NOT NULL,
    posting_period         INTEGER NOT NULL,
    
    -- Balance Information
    beginning_balance      NUMERIC(15,2) DEFAULT 0,
    period_debits          NUMERIC(15,2) DEFAULT 0,
    period_credits         NUMERIC(15,2) DEFAULT 0,
    ending_balance         NUMERIC(15,2) NOT NULL,
    
    -- Cumulative Balances
    ytd_debits             NUMERIC(15,2) DEFAULT 0,
    ytd_credits            NUMERIC(15,2) DEFAULT 0,
    ytd_balance            NUMERIC(15,2) NOT NULL,
    
    -- Metadata
    last_updated           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_posting_date      DATE,
    transaction_count      INTEGER DEFAULT 0,
    
    -- Constraints
    CONSTRAINT fk_balance_company FOREIGN KEY (company_code) REFERENCES companycode(companycodeid),
    CONSTRAINT fk_balance_account FOREIGN KEY (gl_account) REFERENCES glaccount(glaccountid),
    CONSTRAINT fk_balance_ledger FOREIGN KEY (ledger_id) REFERENCES ledger(ledgerid),
    CONSTRAINT chk_balance_period CHECK (posting_period BETWEEN 1 AND 16),
    UNIQUE(company_code, gl_account, ledger_id, fiscal_year, posting_period)
);

-- =================================
-- 5. POSTING AUDIT TRAIL TABLE
-- =================================
CREATE TABLE IF NOT EXISTS posting_audit_trail (
    audit_id               BIGSERIAL PRIMARY KEY,
    
    -- Document References
    document_id            BIGINT,
    source_document        VARCHAR(20) NOT NULL,
    company_code           VARCHAR(10) NOT NULL,
    
    -- Action Information
    action_type            VARCHAR(20) NOT NULL, -- POST, REVERSE, PARK
    action_timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action_by              VARCHAR(50) NOT NULL,
    
    -- Details
    fiscal_year            INTEGER NOT NULL,
    posting_period         INTEGER NOT NULL,
    posting_date           DATE NOT NULL,
    total_amount           NUMERIC(15,2),
    
    -- Status
    action_status          VARCHAR(10) DEFAULT 'SUCCESS',
    error_message          TEXT,
    
    -- Additional Context
    batch_id               VARCHAR(20),
    processing_time_ms     INTEGER,
    
    CONSTRAINT chk_action_type CHECK (action_type IN ('POST', 'REVERSE', 'PARK', 'UNPARK')),
    CONSTRAINT chk_action_status CHECK (action_status IN ('SUCCESS', 'FAILED', 'WARNING')),
    CONSTRAINT fk_audit_company FOREIGN KEY (company_code) REFERENCES companycode(companycodeid)
);

-- =================================
-- 6. ENHANCE EXISTING CHART OF ACCOUNTS
-- =================================
ALTER TABLE glaccount ADD COLUMN IF NOT EXISTS account_group VARCHAR(10);
ALTER TABLE glaccount ADD COLUMN IF NOT EXISTS balance_sheet_item VARCHAR(10);
ALTER TABLE glaccount ADD COLUMN IF NOT EXISTS pl_item VARCHAR(10);
ALTER TABLE glaccount ADD COLUMN IF NOT EXISTS functional_area VARCHAR(16);
ALTER TABLE glaccount ADD COLUMN IF NOT EXISTS account_currency VARCHAR(3);
ALTER TABLE glaccount ADD COLUMN IF NOT EXISTS only_balances_in_local_currency BOOLEAN DEFAULT FALSE;
ALTER TABLE glaccount ADD COLUMN IF NOT EXISTS line_item_management BOOLEAN DEFAULT FALSE;
ALTER TABLE glaccount ADD COLUMN IF NOT EXISTS sort_key VARCHAR(3);
ALTER TABLE glaccount ADD COLUMN IF NOT EXISTS posting_without_tax BOOLEAN DEFAULT TRUE;
ALTER TABLE glaccount ADD COLUMN IF NOT EXISTS field_status_group VARCHAR(4);

-- =================================
-- 7. CREATE INDEXES FOR PERFORMANCE
-- =================================

-- Posting Documents Indexes
CREATE INDEX IF NOT EXISTS idx_posting_docs_company_year ON posting_documents(company_code, fiscal_year);
CREATE INDEX IF NOT EXISTS idx_posting_docs_posting_date ON posting_documents(posting_date);
CREATE INDEX IF NOT EXISTS idx_posting_docs_source ON posting_documents(source_document, source_document_type);
CREATE INDEX IF NOT EXISTS idx_posting_docs_posted_by ON posting_documents(posted_by);

-- GL Transactions Indexes
CREATE INDEX IF NOT EXISTS idx_gl_trans_account_date ON gl_transactions(gl_account, posting_date);
CREATE INDEX IF NOT EXISTS idx_gl_trans_company_period ON gl_transactions(company_code, fiscal_year, posting_period);
CREATE INDEX IF NOT EXISTS idx_gl_trans_source ON gl_transactions(source_doc_number, source_doc_type);
CREATE INDEX IF NOT EXISTS idx_gl_trans_cost_center ON gl_transactions(cost_center);
CREATE INDEX IF NOT EXISTS idx_gl_trans_posting_date ON gl_transactions(posting_date);
CREATE INDEX IF NOT EXISTS idx_gl_trans_ledger ON gl_transactions(ledger_id);

-- Account Balances Indexes
CREATE INDEX IF NOT EXISTS idx_balances_account_year ON gl_account_balances(gl_account, fiscal_year);
CREATE INDEX IF NOT EXISTS idx_balances_company_period ON gl_account_balances(company_code, fiscal_year, posting_period);
CREATE INDEX IF NOT EXISTS idx_balances_ledger ON gl_account_balances(ledger_id);
CREATE INDEX IF NOT EXISTS idx_balances_last_updated ON gl_account_balances(last_updated);

-- Period Controls Indexes
CREATE INDEX IF NOT EXISTS idx_period_controls_company ON fiscal_period_controls(company_code, fiscal_year);
CREATE INDEX IF NOT EXISTS idx_period_controls_status ON fiscal_period_controls(period_status);

-- Audit Trail Indexes
CREATE INDEX IF NOT EXISTS idx_audit_source_doc ON posting_audit_trail(source_document, company_code);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON posting_audit_trail(action_timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_action_by ON posting_audit_trail(action_by);

-- =================================
-- 8. INSERT INITIAL PERIOD CONTROLS
-- =================================

-- Insert period controls for current fiscal year (2025)
INSERT INTO fiscal_period_controls (
    company_code, fiscal_year, posting_period, 
    period_start_date, period_end_date, created_by
) 
SELECT 
    cc.companycodeid,
    2025,
    generate_series(1, 12) as period,
    DATE '2025-01-01' + (generate_series(1, 12) - 1) * INTERVAL '1 month' as start_date,
    (DATE '2025-01-01' + generate_series(1, 12) * INTERVAL '1 month' - INTERVAL '1 day') as end_date,
    'SYSTEM'
FROM companycode cc
ON CONFLICT (company_code, fiscal_year, posting_period) DO NOTHING;

-- =================================
-- 9. CREATE VIEWS FOR REPORTING
-- =================================

-- Account Balance Summary View
CREATE OR REPLACE VIEW v_account_balance_summary AS
SELECT 
    b.company_code,
    b.gl_account,
    a.accountname,
    a.accounttype,
    b.ledger_id,
    l.description as ledger_description,
    b.fiscal_year,
    MAX(b.posting_period) as current_period,
    SUM(b.ytd_debits) as ytd_debits,
    SUM(b.ytd_credits) as ytd_credits,
    SUM(b.ytd_balance) as current_balance,
    MAX(b.last_posting_date) as last_posting_date
FROM gl_account_balances b
JOIN glaccount a ON a.glaccountid = b.gl_account
JOIN ledger l ON l.ledgerid = b.ledger_id
GROUP BY b.company_code, b.gl_account, a.accountname, a.accounttype, 
         b.ledger_id, l.description, b.fiscal_year;

-- GL Transaction Details View
CREATE OR REPLACE VIEW v_gl_transaction_details AS
SELECT 
    t.transaction_id,
    t.company_code,
    t.document_number,
    t.line_item,
    t.gl_account,
    a.accountname,
    a.accounttype,
    t.debit_amount,
    t.credit_amount,
    t.local_currency_amount,
    t.document_currency,
    t.posting_date,
    t.document_date,
    t.line_text,
    t.reference,
    t.cost_center,
    t.ledger_id,
    l.description as ledger_description,
    t.source_doc_number,
    t.posted_by,
    t.posted_at,
    d.document_type,
    d.source_system
FROM gl_transactions t
JOIN glaccount a ON a.glaccountid = t.gl_account
JOIN ledger l ON l.ledgerid = t.ledger_id
JOIN posting_documents d ON d.document_id = t.document_id;

-- =================================
-- 10. ADD COMMENTS FOR DOCUMENTATION
-- =================================

COMMENT ON TABLE fiscal_period_controls IS 'Controls posting periods for each company code - equivalent to SAP period controls';
COMMENT ON TABLE posting_documents IS 'GL posting document headers - equivalent to SAP BKPF table';
COMMENT ON TABLE gl_transactions IS 'Individual GL transaction line items - equivalent to SAP BSEG table';
COMMENT ON TABLE gl_account_balances IS 'Account balance summaries by period - optimized for reporting';
COMMENT ON TABLE posting_audit_trail IS 'Complete audit trail of all posting activities';

COMMENT ON COLUMN posting_documents.document_type IS 'Document type: SA=Standard Journal, AB=Accrual, etc.';
COMMENT ON COLUMN gl_transactions.posting_key IS 'Posting key determines debit/credit and account behavior';
COMMENT ON COLUMN fiscal_period_controls.period_status IS 'OPEN=Allow posting, CLOSED_POSTING=Display only, LOCKED=No access';

-- =================================
-- MIGRATION COMPLETE
-- =================================

-- Log successful migration
INSERT INTO posting_audit_trail (
    source_document, company_code, action_type, action_by, 
    fiscal_year, posting_period, posting_date, action_status
)
SELECT 
    'MIGRATION_20250805',
    companycodeid,
    'POST',
    'SYSTEM',
    2025,
    8,
    CURRENT_DATE,
    'SUCCESS'
FROM companycode;

COMMIT;