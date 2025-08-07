# Approver Configuration Guide

## Overview

The Enterprise Approval Workflow system uses a flexible, role-based approver configuration that supports:
- **Multi-level approvals** based on transaction amounts
- **Company-specific approvers** for multi-entity organizations  
- **Delegation capabilities** for temporary coverage
- **Department-based routing** (optional)

## Configuration Methods

### Method 1: Direct SQL Configuration

```sql
-- Step 1: Configure Approval Levels
INSERT INTO approval_levels (level_name, level_order, min_amount, max_amount, company_code, is_active) VALUES
('Supervisor', 1, 0.00, 9999.99, '1000', TRUE),
('Manager', 2, 10000.00, 99999.99, '1000', TRUE),
('Director', 3, 100000.00, NULL, '1000', TRUE);

-- Step 2: Assign Approvers to Levels
INSERT INTO approvers (user_id, approval_level_id, company_code, is_active) VALUES
('john.supervisor', 1, '1000', TRUE),
('jane.manager', 2, '1000', TRUE),
('bob.director', 3, '1000', TRUE);
```

### Method 2: Using Configuration Script

```bash
# Run the approver configuration script
python3 scripts/configure_approvers.py
```

### Method 3: API/Function Calls

```python
from scripts.configure_approvers import add_new_approver

# Add individual approvers
add_new_approver('new.supervisor', 'Supervisor', '1000')
add_new_approver('new.manager', 'Manager', '1000')
```

## Approval Level Configuration

### Database Table: `approval_levels`

| Field | Type | Description |
|-------|------|-------------|
| `id` | Serial | Primary key |
| `level_name` | VARCHAR | Name of approval level (e.g., 'Supervisor') |
| `level_order` | INTEGER | Order in approval hierarchy (1, 2, 3...) |
| `min_amount` | DECIMAL | Minimum amount for this level |
| `max_amount` | DECIMAL | Maximum amount (NULL = unlimited) |
| `company_code` | VARCHAR | Company code for multi-entity support |
| `department` | VARCHAR | Optional department filtering |
| `is_active` | BOOLEAN | Whether level is active |

### Standard Configuration

```sql
-- Company 1000 Approval Levels
INSERT INTO approval_levels (level_name, level_order, min_amount, max_amount, company_code) VALUES
('Supervisor', 1, 0, 9999.99, '1000'),      -- $0 - $9,999.99
('Manager', 2, 10000, 99999.99, '1000'),    -- $10,000 - $99,999.99  
('Director', 3, 100000, NULL, '1000');      -- $100,000+
```

## Approver Assignment

### Database Table: `approvers`

| Field | Type | Description |
|-------|------|-------------|
| `id` | Serial | Primary key |
| `user_id` | VARCHAR | Username of approver |
| `approval_level_id` | INTEGER | FK to approval_levels |
| `company_code` | VARCHAR | Company code |
| `department` | VARCHAR | Optional department |
| `is_active` | BOOLEAN | Whether assignment is active |
| `delegated_to` | VARCHAR | Temporary delegate username |
| `delegation_start_date` | DATE | Delegation start date |
| `delegation_end_date` | DATE | Delegation end date |

### Assignment Examples

```sql
-- Basic approver assignments
INSERT INTO approvers (user_id, approval_level_id, company_code, is_active) VALUES
('supervisor1', 1, '1000', TRUE),   -- Supervisor level
('manager1', 2, '1000', TRUE),      -- Manager level  
('director1', 3, '1000', TRUE);     -- Director level

-- Multi-company approver (same person, multiple companies)
INSERT INTO approvers (user_id, approval_level_id, company_code, is_active) VALUES
('regional.manager', 2, '1000', TRUE),
('regional.manager', 2, '2000', TRUE);

-- Department-specific approver
INSERT INTO approvers (user_id, approval_level_id, company_code, department, is_active) VALUES
('finance.supervisor', 1, '1000', 'FINANCE', TRUE);
```

## Delegation Configuration

Delegation allows temporary assignment of approval authority:

```sql
-- Set up delegation (manager on vacation, supervisor covers)
UPDATE approvers 
SET delegated_to = 'backup.supervisor',
    delegation_start_date = '2025-08-15',
    delegation_end_date = '2025-08-25'
WHERE user_id = 'manager1' AND company_code = '1000';

-- Remove delegation
UPDATE approvers 
SET delegated_to = NULL,
    delegation_start_date = NULL,
    delegation_end_date = NULL
WHERE user_id = 'manager1' AND company_code = '1000';
```

## Advanced Configuration

### Multiple Approvers per Level

```sql
-- Multiple supervisors for load balancing
INSERT INTO approvers (user_id, approval_level_id, company_code, is_active) VALUES
('supervisor1', 1, '1000', TRUE),
('supervisor2', 1, '1000', TRUE),
('supervisor3', 1, '1000', TRUE);
```

### Department-Based Routing

```sql
-- Different approvers by department
INSERT INTO approvers (user_id, approval_level_id, company_code, department, is_active) VALUES
('finance.supervisor', 1, '1000', 'FINANCE', TRUE),
('ops.supervisor', 1, '1000', 'OPERATIONS', TRUE),
('hr.supervisor', 1, '1000', 'HR', TRUE);
```

### Custom Amount Thresholds

```sql
-- Special approval level for sensitive accounts
INSERT INTO approval_levels (level_name, level_order, min_amount, max_amount, company_code) VALUES
('CFO', 4, 500000, NULL, '1000');  -- $500K+ requires CFO

INSERT INTO approvers (user_id, approval_level_id, company_code, is_active) VALUES
('cfo', 4, '1000', TRUE);
```

## Management Commands

### View Current Configuration

```sql
-- Show all approval levels
SELECT al.company_code, al.level_name, al.level_order,
       al.min_amount, al.max_amount, al.is_active
FROM approval_levels al
ORDER BY al.company_code, al.level_order;

-- Show all approvers with their levels
SELECT a.company_code, a.user_id, al.level_name, 
       a.is_active, a.delegated_to
FROM approvers a
JOIN approval_levels al ON al.id = a.approval_level_id
ORDER BY a.company_code, al.level_order, a.user_id;
```

### Activate/Deactivate Approvers

```sql
-- Deactivate an approver (temporary)
UPDATE approvers 
SET is_active = FALSE 
WHERE user_id = 'supervisor1' AND company_code = '1000';

-- Reactivate an approver
UPDATE approvers 
SET is_active = TRUE 
WHERE user_id = 'supervisor1' AND company_code = '1000';
```

### Bulk Operations

```sql
-- Deactivate all approvers for a company (during reorganization)
UPDATE approvers SET is_active = FALSE WHERE company_code = '1000';

-- Change approval thresholds
UPDATE approval_levels 
SET max_amount = 19999.99 
WHERE level_name = 'Supervisor';
```

## User Interface Access

### For Admin Users
- **User Management** → Assign users to approval roles
- **System Settings** → Configure approval levels and thresholds
- **Reports** → View approval activity and performance

### For End Users
- **Approval Dashboard** → Shows pending approvals based on user's assigned levels
- **Journal Entry Manager** → Automatically routes based on amount and approver availability

## Troubleshooting

### Common Issues

1. **"No available approvers found"**
   - Check that approvers are assigned to the required level
   - Verify approvers are active (`is_active = TRUE`)
   - Check delegation dates haven't expired

2. **"Cannot approve your own journal entry"**
   - This is correct SOD behavior
   - Assign different users to approval levels
   - Use delegation if needed

3. **Wrong approval level selected**
   - Check amount thresholds in `approval_levels`
   - Verify min/max amounts don't overlap incorrectly

### Diagnostic Queries

```sql
-- Check which approval level an amount would route to
SELECT level_name, min_amount, max_amount
FROM approval_levels 
WHERE company_code = '1000'
AND 15000 >= min_amount 
AND (15000 <= max_amount OR max_amount IS NULL)
ORDER BY level_order
LIMIT 1;

-- Find available approvers for a level
SELECT a.user_id, a.is_active, a.delegated_to
FROM approvers a
JOIN approval_levels al ON al.id = a.approval_level_id
WHERE al.level_name = 'Manager' 
AND a.company_code = '1000'
AND a.is_active = TRUE;
```

## Security Considerations

1. **Segregation of Duties**: Users cannot approve their own entries
2. **Active Directory Integration**: Approver usernames must match system users
3. **Audit Trail**: All approver assignments and changes are logged
4. **Delegation Control**: Delegation periods are enforced automatically
5. **Multi-Factor**: Consider requiring MFA for high-value approvals

## Best Practices

1. **Minimum 2 People per Level**: Avoid single points of failure
2. **Clear Amount Thresholds**: No gaps or overlaps in approval ranges
3. **Regular Review**: Quarterly review of approver assignments
4. **Backup Approvers**: Always have delegation options available
5. **Documentation**: Keep approver matrix updated and communicated

---

**Last Updated**: August 4, 2025  
**Version**: 1.0