-- Migration: Add auto-posting fields to journal entry header
-- Date: 2025-08-05 14:00:00
-- Description: Add fields to track automatic posting status

BEGIN;

-- Add auto-posting tracking fields to journalentryheader
ALTER TABLE journalentryheader 
ADD COLUMN IF NOT EXISTS auto_posted BOOLEAN DEFAULT false NOT NULL,
ADD COLUMN IF NOT EXISTS auto_posted_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS auto_posted_by VARCHAR(50);

-- Add index for auto-posting queries
CREATE INDEX IF NOT EXISTS idx_journalentryheader_auto_posted 
ON journalentryheader (workflow_status, auto_posted, posted_at);

-- Add comments
COMMENT ON COLUMN journalentryheader.auto_posted IS 'Flag indicating if document was automatically posted';
COMMENT ON COLUMN journalentryheader.auto_posted_at IS 'Timestamp when document was automatically posted';
COMMENT ON COLUMN journalentryheader.auto_posted_by IS 'System user that performed automatic posting';

COMMIT;