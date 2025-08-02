-- Migration: Create authentication and authorization tables
-- Created: 2025-08-01 13:00:00
-- Version: 20250801_130000

-- Create roles table
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create permissions table
CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    resource VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create role_permissions junction table
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    must_change_password BOOLEAN DEFAULT FALSE,
    password_changed_at TIMESTAMP,
    last_login_at TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id)
);

-- Create user_roles junction table
CREATE TABLE IF NOT EXISTS user_roles (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by INTEGER REFERENCES users(id),
    PRIMARY KEY (user_id, role_id)
);

-- Create user_sessions table
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE,
    ip_address INET,
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(100),
    resource_id VARCHAR(100),
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create company_access table for multi-company support
CREATE TABLE IF NOT EXISTS user_company_access (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    company_code VARCHAR(10) NOT NULL,
    access_type VARCHAR(20) DEFAULT 'read_write',
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by INTEGER REFERENCES users(id),
    PRIMARY KEY (user_id, company_code)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_locked ON users(locked_until);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON user_sessions(is_active, expires_at);
CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_user_company_access ON user_company_access(user_id, company_code);

-- Insert default roles
INSERT INTO roles (name, description) VALUES 
    ('super_admin', 'System administrator with full access'),
    ('admin', 'Company administrator with full company access'),
    ('manager', 'Department manager with extended access'),
    ('user', 'Regular user with basic access'),
    ('viewer', 'Read-only access to reports and data')
ON CONFLICT (name) DO NOTHING;

-- Insert default permissions
INSERT INTO permissions (name, description, resource, action) VALUES 
    ('users.create', 'Create new users', 'users', 'create'),
    ('users.read', 'View user information', 'users', 'read'),
    ('users.update', 'Update user information', 'users', 'update'),
    ('users.delete', 'Delete users', 'users', 'delete'),
    ('users.manage_roles', 'Assign/remove user roles', 'users', 'manage_roles'),
    
    ('glaccount.create', 'Create GL accounts', 'glaccount', 'create'),
    ('glaccount.read', 'View GL accounts', 'glaccount', 'read'),
    ('glaccount.update', 'Update GL accounts', 'glaccount', 'update'),
    ('glaccount.delete', 'Delete GL accounts', 'glaccount', 'delete'),
    
    ('journal.create', 'Create journal entries', 'journal', 'create'),
    ('journal.read', 'View journal entries', 'journal', 'read'),
    ('journal.update', 'Update journal entries', 'journal', 'update'),
    ('journal.delete', 'Delete journal entries', 'journal', 'delete'),
    ('journal.post', 'Post journal entries', 'journal', 'post'),
    
    ('reports.trial_balance', 'View trial balance report', 'reports', 'trial_balance'),
    ('reports.balance_sheet', 'View balance sheet report', 'reports', 'balance_sheet'),
    ('reports.income_statement', 'View income statement report', 'reports', 'income_statement'),
    ('reports.cash_flow', 'View cash flow statement', 'reports', 'cash_flow'),
    ('reports.general_ledger', 'View general ledger report', 'reports', 'general_ledger'),
    
    ('system.backup', 'Create system backups', 'system', 'backup'),
    ('system.restore', 'Restore from backups', 'system', 'restore'),
    ('system.settings', 'Modify system settings', 'system', 'settings')
ON CONFLICT (name) DO NOTHING;

-- Assign permissions to roles
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM roles r, permissions p 
WHERE r.name = 'super_admin'  -- Super admin gets all permissions
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM roles r, permissions p 
WHERE r.name = 'admin' 
AND p.name NOT IN ('system.backup', 'system.restore', 'system.settings')  -- Admin gets most permissions
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM roles r, permissions p 
WHERE r.name = 'manager' 
AND p.resource IN ('glaccount', 'journal', 'reports')
AND p.action != 'delete'  -- Manager can't delete
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM roles r, permissions p 
WHERE r.name = 'user' 
AND p.resource IN ('glaccount', 'journal')
AND p.action IN ('create', 'read', 'update')  -- User can CRU but not delete
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id 
FROM roles r, permissions p 
WHERE r.name = 'viewer' 
AND p.action = 'read'  -- Viewer can only read
ON CONFLICT DO NOTHING;

-- Create default super admin user (password: Admin123!)
-- Note: This should be changed immediately after deployment
INSERT INTO users (username, email, password_hash, first_name, last_name, is_verified, created_at)
VALUES (
    'admin',
    'admin@company.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LNi7B5QJLZMnBVDV.',  -- Admin123!
    'System',
    'Administrator',
    TRUE,
    CURRENT_TIMESTAMP
) ON CONFLICT (username) DO NOTHING;

-- Assign super_admin role to default admin user
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id 
FROM users u, roles r 
WHERE u.username = 'admin' AND r.name = 'super_admin'
ON CONFLICT DO NOTHING;

-- Create triggers for updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_roles_updated_at BEFORE UPDATE ON roles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Rollback instructions:
-- DROP TABLE IF EXISTS audit_logs CASCADE;
-- DROP TABLE IF EXISTS user_company_access CASCADE;
-- DROP TABLE IF EXISTS user_sessions CASCADE;
-- DROP TABLE IF EXISTS user_roles CASCADE;
-- DROP TABLE IF EXISTS users CASCADE;
-- DROP TABLE IF EXISTS role_permissions CASCADE;
-- DROP TABLE IF EXISTS permissions CASCADE;
-- DROP TABLE IF EXISTS roles CASCADE;
-- DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;