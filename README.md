# GL ERP System

A modern General Ledger ERP system built with Streamlit, featuring comprehensive testing, validation, logging, and data management capabilities.

## Features

- 📊 **Chart of Accounts Management** - Create and manage GL accounts with inline editing
- 📝 **Journal Entry Management** - Full CRUD operations for journal entries
- 📋 **Financial Reports** - Trial Balance, Balance Sheet, Income Statement, Cash Flow
- 🔐 **Enterprise Authentication** - JWT-based authentication with role-based access control
- 👥 **User Management** - Complete user lifecycle management with role assignment
- 🛡️ **Security Features** - Password policies, rate limiting, session management, audit logging
- ✅ **Input Validation** - Comprehensive validation using Pydantic
- 📝 **Logging System** - Structured logging with Loguru
- 🧪 **Testing Framework** - Pytest-based testing suite
- 🔄 **Database Migrations** - Version-controlled schema migrations
- 💾 **Backup & Restore** - Automated database backup and restore utilities

## Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL database
- Git

### Installation

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd gl
   make dev-setup
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

3. **Run the application:**
   ```bash
   make run
   ```

4. **Login with default admin account:**
   - Username: `admin`
   - Password: `Admin123!`
   - **⚠️ Change this password immediately after first login!**

## Development

### Available Commands

```bash
make help           # Show all available commands
make install        # Install dependencies
make test           # Run tests
make run            # Run Streamlit application
make backup         # Create database backup
make restore        # Restore database (interactive)
make migrate        # Run database migrations
make migrate-status # Show migration status
make clean          # Clean temporary files
```

### Project Structure

```
gl/
├── Home.py                 # Main Streamlit application
├── config.py              # Configuration management
├── db_config.py           # Database configuration
├── requirements.txt       # Python dependencies
├── Makefile              # Development commands
├── auth/                 # Authentication module
│   ├── models.py         # Authentication data models
│   ├── security.py       # Security utilities (JWT, passwords)
│   ├── service.py        # Authentication business logic
│   └── middleware.py     # Streamlit auth integration
├── pages/                # Streamlit pages
│   ├── 1_Chart_of_Accounts.py
│   ├── Journal_Entry_Manager.py
│   ├── User_Management.py
│   └── [other pages...]
├── utils/                # Utility modules
│   ├── validation.py     # Input validation
│   └── logger.py         # Logging utilities
├── tests/                # Test suite
│   ├── conftest.py       # Test configuration
│   ├── test_validation.py
│   └── [other tests...]
├── scripts/              # Database scripts
│   ├── backup_database.py
│   ├── restore_database.py
│   └── migrate_database.py
├── migrations/           # Database migrations
└── logs/                # Application logs
```

## Configuration

Environment variables can be set in `.env` file:

```bash
# Database Configuration  
DATABASE_URL=postgresql://user:password@host:port/database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=gl_erp
DB_USER=postgres
DB_PASSWORD=admin123

# Application Configuration
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO

# Feature Flags
ENABLE_CACHING=true
CACHE_TTL=300
```

## Database Management

### Migrations

```bash
# Initialize migrations
python scripts/migrate_database.py --init

# Run migrations
make migrate

# Check migration status
make migrate-status

# Create new migration
make migrate-create
```

### Backup & Restore

```bash
# Create full backup
make backup

# Interactive restore
make restore

# List available backups
python scripts/backup_database.py --list

# Cleanup old backups (older than 30 days)
python scripts/backup_database.py --cleanup 30
```

## Testing

Run the test suite:

```bash
make test
```

Test specific modules:

```bash
pytest tests/test_validation.py -v
pytest tests/test_journal_entry_manager.py -v
```

## Logging

The application uses structured logging with different log levels:

- **Console**: Real-time logs during development
- **gl_erp.log**: General application logs (rotated)
- **errors.log**: Error-only logs (longer retention)
- **database.log**: Database operation logs

Log files are stored in the `logs/` directory with automatic rotation and compression.

## API Reference

### Validation Classes

- `GLAccountValidator`: Validates GL account data
- `JournalEntryHeaderValidator`: Validates journal entry headers
- `JournalEntryLineValidator`: Validates journal entry lines

### Utility Functions

- `validate_journal_entry_balance()`: Ensures debits equal credits
- `sanitize_string_input()`: Cleans and validates string inputs
- `validate_numeric_input()`: Validates numeric inputs

## Security Best Practices

- Environment-based configuration (no hardcoded credentials)
- Input validation on all forms
- SQL injection prevention with parameterized queries
- Role-based access control
- Audit logging for all operations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run the test suite: `make test`
5. Submit a pull request

## Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check DATABASE_URL in .env
   - Ensure PostgreSQL is running
   - Verify credentials and database exists

2. **Import Errors**
   - Run `make install` to ensure dependencies
   - Check Python version (3.10+ required)

3. **Migration Errors**
   - Check database permissions
   - Ensure migration table exists
   - Review migration files for syntax errors

### Getting Help

Check the logs in `logs/` directory for detailed error information.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### v2.0.0 (Latest)
- ✅ Added comprehensive testing framework
- ✅ Implemented environment-based configuration
- ✅ Added input validation system
- ✅ Integrated structured logging
- ✅ Created database backup/restore utilities
- ✅ Added migration system
- ✅ Improved error handling
- ✅ Added development tools (Makefile)

### v1.0.0
- Initial Streamlit application
- Basic GL account management
- Journal entry functionality
- Simple database connectivity