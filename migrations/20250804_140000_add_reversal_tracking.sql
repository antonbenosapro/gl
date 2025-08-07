-- Migration: Add Journal Entry Reversal Tracking
-- Created: 2025-08-04
-- Purpose: Enterprise-grade audit trail for journal entry reversals

-- Add status and reversal tracking columns to journalentryheader
ALTER TABLE journalentryheader 
ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'ACTIVE';

ALTER TABLE journalentryheader 
ADD COLUMN IF NOT EXISTS reversal_of VARCHAR(20);

ALTER TABLE journalentryheader 
ADD COLUMN IF NOT EXISTS reversed_by VARCHAR(20);

ALTER TABLE journalentryheader 
ADD COLUMN IF NOT EXISTS reversal_date DATE;

ALTER TABLE journalentryheader 
ADD COLUMN IF NOT EXISTS reversal_reason TEXT;

ALTER TABLE journalentryheader 
ADD COLUMN IF NOT EXISTS reversal_created_by VARCHAR(50);

-- Add check constraint for status
ALTER TABLE journalentryheader 
ADD CONSTRAINT chk_status CHECK (status IN ('ACTIVE', 'REVERSED', 'REVERSING'));

-- Note: Foreign key constraints for reversal references would create circular dependencies
-- We'll handle referential integrity in the application layer instead

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_journal_status ON journalentryheader(status);
CREATE INDEX IF NOT EXISTS idx_journal_reversal_of ON journalentryheader(reversal_of);
CREATE INDEX IF NOT EXISTS idx_journal_reversed_by ON journalentryheader(reversed_by);
CREATE INDEX IF NOT EXISTS idx_journal_reversal_date ON journalentryheader(reversal_date);

-- Create audit table for reversal operations
CREATE TABLE IF NOT EXISTS journal_reversal_audit (
    id SERIAL PRIMARY KEY,
    original_document VARCHAR(20) NOT NULL,
    reversal_document VARCHAR(20) NOT NULL, 
    company_code VARCHAR(5) NOT NULL,
    reversal_date DATE NOT NULL,
    reversal_reason TEXT,
    requested_by VARCHAR(50) NOT NULL,
    approved_by VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    original_total_debit DECIMAL(15,2),
    original_total_credit DECIMAL(15,2),
    FOREIGN KEY (original_document, company_code) REFERENCES journalentryheader(documentnumber, companycodeid),
    FOREIGN KEY (reversal_document, company_code) REFERENCES journalentryheader(documentnumber, companycodeid)
);

-- Add comments for documentation
COMMENT ON COLUMN journalentryheader.status IS 'Entry status: ACTIVE, REVERSED, REVERSING';
COMMENT ON COLUMN journalentryheader.reversal_of IS 'Document number this entry reverses';
COMMENT ON COLUMN journalentryheader.reversed_by IS 'Document number that reverses this entry';
COMMENT ON COLUMN journalentryheader.reversal_date IS 'Date when reversal was created';
COMMENT ON COLUMN journalentryheader.reversal_reason IS 'Business reason for reversal';
COMMENT ON COLUMN journalentryheader.reversal_created_by IS 'User who created the reversal';

COMMENT ON TABLE journal_reversal_audit IS 'Audit trail for journal entry reversals';

-- Insert migration record
INSERT INTO schema_migrations (migration_name, executed_at) 
VALUES ('20250804_140000_add_reversal_tracking', CURRENT_TIMESTAMP)
ON CONFLICT (migration_name) DO NOTHING;