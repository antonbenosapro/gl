# Makefile for GL ERP System

.PHONY: help install test run backup restore migrate clean

# Default target
help:
	@echo "Available commands:"
	@echo "  install    - Install dependencies"
	@echo "  test       - Run tests"
	@echo "  run        - Run the Streamlit application"
	@echo "  backup     - Create database backup"
	@echo "  restore    - Restore database (interactive)"
	@echo "  migrate    - Run database migrations"
	@echo "  clean      - Clean temporary files"
	@echo "  setup      - Initial setup (install + migrate)"

# Install dependencies
install:
	pip install -r requirements.txt

# Run tests
test:
	pytest

# Run the application
run:
	streamlit run Home.py

# Create database backup
backup:
	python scripts/backup_database.py --type full

# Restore database (interactive)
restore:
	python scripts/restore_database.py --interactive

# Run database migrations
migrate:
	python scripts/migrate_database.py --run

# Show migration status
migrate-status:
	python scripts/migrate_database.py --status

# Create new migration
migrate-create:
	@read -p "Enter migration description: " desc; \
	python scripts/migrate_database.py --create "$$desc"

# Initialize database with initial migrations
migrate-init:
	python scripts/migrate_database.py --init

# Setup authentication system
auth-setup: migrate
	@echo "Setting up authentication system..."
	@echo "Creating default admin user..."
	@echo "Authentication setup complete!"

# Clean temporary files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".pytest_cache" -exec rm -rf {} +

# Initial setup
setup: install migrate-init migrate
	@echo "Setup complete!"

# Development setup
dev-setup: setup
	@echo "Creating .env file from template..."
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@echo "Development setup complete!"
	@echo "Please edit .env file with your configuration"