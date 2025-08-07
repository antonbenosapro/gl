-- Migration: Add Approval Workflow System
-- Created: 2025-08-04
-- Purpose: Enterprise-grade approval workflow for journal entries

-- Add workflow status to journalentryheader
ALTER TABLE journalentryheader 
ADD COLUMN IF NOT EXISTS workflow_status VARCHAR(20) DEFAULT 'DRAFT';

ALTER TABLE journalentryheader 
ADD COLUMN IF NOT EXISTS submitted_for_approval_at TIMESTAMP;

ALTER TABLE journalentryheader 
ADD COLUMN IF NOT EXISTS submitted_by VARCHAR(50);

ALTER TABLE journalentryheader 
ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP;

ALTER TABLE journalentryheader 
ADD COLUMN IF NOT EXISTS approved_by VARCHAR(50);

ALTER TABLE journalentryheader 
ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMP;

ALTER TABLE journalentryheader 
ADD COLUMN IF NOT EXISTS rejected_by VARCHAR(50);

ALTER TABLE journalentryheader 
ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

ALTER TABLE journalentryheader 
ADD COLUMN IF NOT EXISTS posted_at TIMESTAMP;

ALTER TABLE journalentryheader 
ADD COLUMN IF NOT EXISTS posted_by VARCHAR(50);

-- Add check constraint for workflow status
ALTER TABLE journalentryheader 
ADD CONSTRAINT chk_workflow_status CHECK (workflow_status IN ('DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'POSTED', 'CANCELLED'));

-- Create approval levels configuration table
CREATE TABLE IF NOT EXISTS approval_levels (
    id SERIAL PRIMARY KEY,
    level_name VARCHAR(50) NOT NULL,
    level_order INTEGER NOT NULL,
    min_amount DECIMAL(15,2) DEFAULT 0,
    max_amount DECIMAL(15,2),
    company_code VARCHAR(5),
    department VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(level_order, company_code)
);

-- Create approvers table (who can approve at what levels)
CREATE TABLE IF NOT EXISTS approvers (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    approval_level_id INTEGER NOT NULL,
    company_code VARCHAR(5),
    department VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    delegated_to VARCHAR(50), -- For delegation
    delegation_start_date DATE,
    delegation_end_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (approval_level_id) REFERENCES approval_levels(id),
    FOREIGN KEY (user_id) REFERENCES users(username),
    UNIQUE(user_id, approval_level_id, company_code)
);

-- Create workflow instances table (tracks approval flow for each entry)
CREATE TABLE IF NOT EXISTS workflow_instances (
    id SERIAL PRIMARY KEY,
    document_number VARCHAR(20) NOT NULL,
    company_code VARCHAR(5) NOT NULL,
    workflow_type VARCHAR(20) DEFAULT 'STANDARD', -- STANDARD, MULTI_LEVEL, EMERGENCY
    current_step INTEGER DEFAULT 1,
    total_steps INTEGER DEFAULT 1,
    required_approval_level_id INTEGER,
    status VARCHAR(20) DEFAULT 'PENDING',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (document_number, company_code) REFERENCES journalentryheader(documentnumber, companycodeid),
    FOREIGN KEY (required_approval_level_id) REFERENCES approval_levels(id)
);

-- Create approval steps table (individual approval actions)
CREATE TABLE IF NOT EXISTS approval_steps (
    id SERIAL PRIMARY KEY,
    workflow_instance_id INTEGER NOT NULL,
    step_number INTEGER NOT NULL,
    approval_level_id INTEGER NOT NULL,
    assigned_to VARCHAR(50) NOT NULL,
    action VARCHAR(20), -- PENDING, APPROVED, REJECTED, DELEGATED
    action_by VARCHAR(50),
    action_at TIMESTAMP,
    comments TEXT,
    time_limit TIMESTAMP, -- For escalation
    escalated_to VARCHAR(50),
    escalated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workflow_instance_id) REFERENCES workflow_instances(id),
    FOREIGN KEY (approval_level_id) REFERENCES approval_levels(id),
    FOREIGN KEY (assigned_to) REFERENCES users(username),
    FOREIGN KEY (action_by) REFERENCES users(username)
);

-- Create approval notifications table
CREATE TABLE IF NOT EXISTS approval_notifications (
    id SERIAL PRIMARY KEY,
    workflow_instance_id INTEGER NOT NULL,
    recipient VARCHAR(50) NOT NULL,
    notification_type VARCHAR(20) NOT NULL, -- APPROVAL_REQUEST, APPROVED, REJECTED, ESCALATED
    subject VARCHAR(200),
    message TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP,
    is_read BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (workflow_instance_id) REFERENCES workflow_instances(id),
    FOREIGN KEY (recipient) REFERENCES users(username)
);

-- Create workflow audit log
CREATE TABLE IF NOT EXISTS workflow_audit_log (
    id SERIAL PRIMARY KEY,
    document_number VARCHAR(20) NOT NULL,
    company_code VARCHAR(5) NOT NULL,
    action VARCHAR(50) NOT NULL,
    performed_by VARCHAR(50) NOT NULL,
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    old_status VARCHAR(20),
    new_status VARCHAR(20),
    comments TEXT,
    ip_address INET,
    user_agent TEXT
);

-- Insert default approval levels
INSERT INTO approval_levels (level_name, level_order, min_amount, max_amount, company_code) VALUES
('Supervisor', 1, 0, 9999.99, '1000'),
('Manager', 2, 10000.00, 99999.99, '1000'),
('Director', 3, 100000.00, NULL, '1000'),
('Supervisor', 1, 0, 9999.99, '2000'),
('Manager', 2, 10000.00, 99999.99, '2000'),
('Director', 3, 100000.00, NULL, '2000')
ON CONFLICT DO NOTHING;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_workflow_status ON journalentryheader(workflow_status);
CREATE INDEX IF NOT EXISTS idx_submitted_for_approval ON journalentryheader(submitted_for_approval_at);
CREATE INDEX IF NOT EXISTS idx_workflow_instances_status ON workflow_instances(status);
CREATE INDEX IF NOT EXISTS idx_approval_steps_assigned ON approval_steps(assigned_to, action);
CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON approval_notifications(recipient, is_read);

-- Add comments for documentation
COMMENT ON COLUMN journalentryheader.workflow_status IS 'Workflow status: DRAFT, PENDING_APPROVAL, APPROVED, REJECTED, POSTED, CANCELLED';
COMMENT ON TABLE approval_levels IS 'Configuration for approval levels and limits';
COMMENT ON TABLE approvers IS 'Users authorized to approve at specific levels';
COMMENT ON TABLE workflow_instances IS 'Tracks approval workflow for each journal entry';
COMMENT ON TABLE approval_steps IS 'Individual approval steps within workflows';
COMMENT ON TABLE approval_notifications IS 'Notifications sent to approvers';
COMMENT ON TABLE workflow_audit_log IS 'Complete audit trail of workflow actions';

-- Insert migration record
INSERT INTO schema_migrations (migration_name, executed_at) 
VALUES ('20250804_150000_add_approval_workflow', CURRENT_TIMESTAMP)
ON CONFLICT (migration_name) DO NOTHING;