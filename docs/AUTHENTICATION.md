# Authentication & Authorization System

## Overview

The GL ERP system includes a comprehensive enterprise-grade authentication and authorization system with the following features:

- **JWT Token-based Authentication** - Secure token-based authentication with refresh tokens
- **Role-Based Access Control (RBAC)** - Granular permissions system with role hierarchy
- **Password Security** - Strong password requirements with bcrypt hashing
- **Session Management** - User session tracking and timeout
- **Rate Limiting** - Protection against brute force attacks
- **Audit Logging** - Complete audit trail of authentication events
- **Multi-Company Support** - User access control per company

## Architecture

```
auth/
├── models.py          # Pydantic models for authentication
├── security.py       # Security utilities (JWT, hashing, rate limiting)
├── service.py         # Business logic layer
└── middleware.py      # Streamlit integration middleware
```

## Database Schema

### Core Tables

- **users** - User accounts with authentication details
- **roles** - User roles (admin, manager, user, viewer)
- **permissions** - Granular permissions (resource.action format)
- **role_permissions** - Many-to-many role-permission mapping
- **user_roles** - Many-to-many user-role mapping
- **user_sessions** - Active user sessions with JWT tokens
- **audit_logs** - Complete audit trail
- **user_company_access** - Multi-company access control

### Default Roles & Permissions

| Role | Description | Key Permissions |
|------|-------------|-----------------|
| **super_admin** | System administrator | All permissions |
| **admin** | Company administrator | All except system.* |
| **manager** | Department manager | Read/write, no delete |
| **user** | Regular user | Basic CRUD operations |
| **viewer** | Read-only access | Read-only permissions |

## Security Features

### Password Requirements
- Minimum 8 characters (configurable)
- Must contain uppercase, lowercase, numbers, and special characters
- No common patterns (123, abc, password, etc.)
- Strength scoring and feedback

### JWT Tokens
- **Access Token**: Short-lived (24 hours default)
- **Refresh Token**: Long-lived (30 days) for "remember me"
- **Algorithm**: HS256 with configurable secret
- **Payload**: User ID, username, session ID, expiration

### Rate Limiting
- Maximum 5 failed login attempts (configurable)
- 30-minute lockout duration (configurable)
- Per-user tracking with automatic cleanup

### Session Management
- Database-backed session tracking
- Configurable session timeout (60 minutes default)
- Session invalidation on logout
- IP address and user agent tracking

## Usage

### Protecting Pages

```python
from auth.middleware import authenticator, require_permission

# Require authentication
authenticator.require_auth()

# Require specific permission
authenticator.require_permission("users.read")

# Using decorators
@require_permission("glaccount.create")
def create_account():
    # Protected function
    pass
```

### Checking Permissions

```python
# Check if user has permission
if authenticator.has_permission("users.create"):
    # Show create button
    pass

# Get current user
user = authenticator.get_current_user()

# Get user permissions
permissions = authenticator.get_user_permissions()

# Get user companies
companies = authenticator.get_user_companies()
```

### User Management

```python
from auth.service import user_service
from auth.models import UserCreate

# Create new user
user_data = UserCreate(
    username="newuser",
    email="user@company.com",
    password="SecurePass123!",
    role_ids=[2, 3]  # Assign roles
)
new_user = user_service.create_user(user_data, created_by=current_user.id)

# Update user
user_update = UserUpdate(email="new@company.com")
user_service.update_user(user_id, user_update, updated_by=current_user.id)

# Change password
success = user_service.change_password(user_id, "old_pass", "new_pass")
```

## Configuration

Environment variables for authentication:

```bash
# Security Settings
JWT_SECRET_KEY=your-jwt-secret-here-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
SESSION_TIMEOUT_MINUTES=60

# Password Policy
PASSWORD_MIN_LENGTH=8
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION_MINUTES=30
```

## Default Admin Account

The system creates a default admin account during setup:

- **Username**: `admin`
- **Email**: `admin@company.com`
- **Password**: `Admin123!`
- **Role**: `super_admin`

**⚠️ IMPORTANT**: Change the default password immediately after deployment!

## API Reference

### Authentication Service

```python
from auth.service import auth_service

# Authenticate user
login_response = auth_service.authenticate(login_request, ip_address, user_agent)

# Refresh token
new_response = auth_service.refresh_token(refresh_token)

# Logout
auth_service.logout(session_token)
```

### Authorization Service

```python
from auth.service import authz_service

# Check permission
has_perm = authz_service.check_permission(user_id, "users.create")

# Check company access
has_access = authz_service.check_company_access(user_id, "C001", AccessType.READ_WRITE)
```

## Permission Reference

### User Management
- `users.create` - Create new users
- `users.read` - View user information
- `users.update` - Update user information
- `users.delete` - Delete users
- `users.manage_roles` - Assign/remove user roles

### GL Accounts
- `glaccount.create` - Create GL accounts
- `glaccount.read` - View GL accounts
- `glaccount.update` - Update GL accounts
- `glaccount.delete` - Delete GL accounts

### Journal Entries
- `journal.create` - Create journal entries
- `journal.read` - View journal entries
- `journal.update` - Update journal entries
- `journal.delete` - Delete journal entries
- `journal.post` - Post journal entries

### Reports
- `reports.trial_balance` - View trial balance report
- `reports.balance_sheet` - View balance sheet report
- `reports.income_statement` - View income statement report
- `reports.cash_flow` - View cash flow statement
- `reports.general_ledger` - View general ledger report

### System
- `system.backup` - Create system backups
- `system.restore` - Restore from backups
- `system.settings` - Modify system settings

## Security Best Practices

### Deployment
1. **Change Default Credentials** - Immediately change the default admin password
2. **Use Strong JWT Secret** - Generate a cryptographically secure JWT secret
3. **Enable HTTPS** - Always use HTTPS in production
4. **Regular Backups** - Backup user and session data regularly
5. **Monitor Access** - Review audit logs regularly

### Development
1. **Environment Variables** - Never hardcode secrets in code
2. **Input Validation** - All user inputs are validated
3. **SQL Injection Prevention** - Parameterized queries only
4. **Session Security** - Secure session handling with timeouts
5. **Error Handling** - No sensitive information in error messages

## Troubleshooting

### Common Issues

1. **Login Failed**
   - Check username/password
   - Verify account is active and not locked
   - Check rate limiting status

2. **Permission Denied**
   - Verify user has required permission
   - Check role assignments
   - Confirm company access if applicable

3. **Token Expired**
   - Use refresh token to get new access token
   - Re-authenticate if refresh token expired

4. **Session Timeout**
   - Increase SESSION_TIMEOUT_MINUTES if needed
   - Implement "remember me" functionality

### Debug Commands

```bash
# Check user permissions
python -c "from auth.service import user_service; print(user_service.get_user_permissions(1))"

# Verify token
python -c "from auth.security import security_manager; print(security_manager.verify_token('your_token'))"

# Check password strength
python -c "from auth.security import password_checker; print(password_checker.check_strength('password'))"
```

## Migration Guide

### From Simple Auth
If upgrading from the simple role-based system:

1. Run authentication migration: `make migrate`
2. Create user accounts for existing users
3. Assign appropriate roles
4. Update page protection to use new middleware
5. Test all functionality with different user roles

### Database Migration
The authentication system adds several new tables. Run migrations:

```bash
make migrate
```

This will create all necessary tables and default data.

## Testing

Run authentication tests:

```bash
# Run all auth tests
pytest tests/test_auth*.py -v

# Run specific test
pytest tests/test_auth_security.py::TestSecurityManager::test_password_hashing -v
```

## Support

For authentication-related issues:
1. Check the audit logs for failed authentication attempts
2. Verify user account status and permissions
3. Review session management settings
4. Consult the troubleshooting section above

The authentication system provides comprehensive logging for debugging and audit purposes.