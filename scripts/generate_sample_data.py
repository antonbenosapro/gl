#!/usr/bin/env python3
"""
Generate sample journal entries and GL accounts for testing
Creates realistic business transactions across all 12 periods
"""

import sys
import random
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from db_config import engine
from sqlalchemy import text
from utils.logger import get_logger

logger = get_logger("sample_data_generator")


class SampleDataGenerator:
    """Generate realistic sample data for the GL ERP system"""
    
    def __init__(self):
        self.company_code = "1000"  # Use existing company code
        self.fiscal_year = 2025
        self.currency_code = "USD"
        self.ledger_id = "L1"  # Use existing ledger ID
        
        # GL Account structure following standard chart of accounts
        self.gl_accounts = {
            # Assets (1000-1999)
            "1001": ("Cash - Operating Account", "Asset"),
            "1002": ("Cash - Savings Account", "Asset"),
            "1010": ("Petty Cash", "Asset"),
            "1100": ("Accounts Receivable", "Asset"),
            "1200": ("Inventory - Raw Materials", "Asset"),
            "1201": ("Inventory - Finished Goods", "Asset"),
            "1300": ("Prepaid Insurance", "Asset"),
            "1301": ("Prepaid Rent", "Asset"),
            "1400": ("Equipment", "Asset"),
            "1450": ("Accumulated Depreciation - Equipment", "Asset"),
            "1500": ("Office Furniture", "Asset"),
            "1550": ("Accumulated Depreciation - Furniture", "Asset"),
            
            # Liabilities (2000-2999)
            "2001": ("Accounts Payable", "Liability"),
            "2100": ("Accrued Wages", "Liability"),
            "2101": ("Payroll Taxes Payable", "Liability"),
            "2200": ("Sales Tax Payable", "Liability"),
            "2300": ("Notes Payable - Short Term", "Liability"),
            "2400": ("Unearned Revenue", "Liability"),
            "2500": ("Equipment Loan", "Liability"),
            
            # Equity (3000-3999)
            "3001": ("Owner's Capital", "Equity"),
            "3002": ("Retained Earnings", "Equity"),
            "3100": ("Common Stock", "Equity"),
            
            # Revenue (4000-4999)
            "4001": ("Sales Revenue - Products", "Revenue"),
            "4002": ("Sales Revenue - Services", "Revenue"),
            "4100": ("Interest Income", "Revenue"),
            "4200": ("Other Income", "Revenue"),
            
            # Expenses (5000-5999)
            "5001": ("Cost of Goods Sold", "Expense"),
            "5100": ("Salaries and Wages", "Expense"),
            "5101": ("Payroll Taxes", "Expense"),
            "5200": ("Rent Expense", "Expense"),
            "5201": ("Utilities Expense", "Expense"),
            "5202": ("Insurance Expense", "Expense"),
            "5300": ("Office Supplies", "Expense"),
            "5301": ("Marketing Expense", "Expense"),
            "5400": ("Depreciation Expense", "Expense"),
            "5500": ("Interest Expense", "Expense"),
            "5600": ("Professional Services", "Expense"),
            "5700": ("Travel Expense", "Expense"),
            "5800": ("Repairs and Maintenance", "Expense"),
        }
        
        # Transaction templates for realistic journal entries
        self.transaction_templates = [
            # Sales transactions
            {
                "description": "Sale of products to customer #{customer}",
                "entries": [
                    ("1100", "debit", "sales_amount"),  # A/R
                    ("4001", "credit", "sales_amount"),  # Sales Revenue
                ],
                "amount_range": (500, 5000),
                "frequency": 8  # Higher frequency for sales
            },
            {
                "description": "Cash sale #{invoice}",
                "entries": [
                    ("1001", "debit", "sales_amount"),  # Cash
                    ("4001", "credit", "sales_amount"),  # Sales Revenue
                ],
                "amount_range": (100, 2000),
                "frequency": 6
            },
            {
                "description": "Service revenue invoice #{invoice}",
                "entries": [
                    ("1100", "debit", "service_amount"),  # A/R
                    ("4002", "credit", "service_amount"),  # Service Revenue
                ],
                "amount_range": (300, 3000),
                "frequency": 5
            },
            
            # Purchase transactions
            {
                "description": "Purchase of inventory from supplier #{supplier}",
                "entries": [
                    ("1200", "debit", "purchase_amount"),  # Inventory
                    ("2001", "credit", "purchase_amount"),  # A/P
                ],
                "amount_range": (800, 4000),
                "frequency": 6
            },
            {
                "description": "Office supplies purchase",
                "entries": [
                    ("5300", "debit", "supply_amount"),  # Office Supplies
                    ("1001", "credit", "supply_amount"),  # Cash
                ],
                "amount_range": (50, 500),
                "frequency": 3
            },
            
            # Payroll transactions
            {
                "description": "Monthly payroll processing",
                "entries": [
                    ("5100", "debit", "gross_pay"),      # Salaries
                    ("5101", "debit", "payroll_taxes"),  # Payroll Taxes
                    ("2100", "credit", "net_pay"),       # Accrued Wages
                    ("2101", "credit", "tax_withholding"), # Tax Payable
                ],
                "amount_range": (8000, 15000),
                "frequency": 1,  # Once per month
                "multi_line": True
            },
            
            # Rent and utilities
            {
                "description": "Monthly rent payment",
                "entries": [
                    ("5200", "debit", "rent_amount"),  # Rent Expense
                    ("1001", "credit", "rent_amount"), # Cash
                ],
                "amount_range": (2000, 4000),
                "frequency": 1
            },
            {
                "description": "Utilities payment - {utility_type}",
                "entries": [
                    ("5201", "debit", "utility_amount"),  # Utilities
                    ("1001", "credit", "utility_amount"), # Cash
                ],
                "amount_range": (200, 800),
                "frequency": 2
            },
            
            # Customer payments
            {
                "description": "Customer payment received - Check #{check}",
                "entries": [
                    ("1001", "debit", "payment_amount"),  # Cash
                    ("1100", "credit", "payment_amount"), # A/R
                ],
                "amount_range": (500, 5000),
                "frequency": 7
            },
            
            # Vendor payments
            {
                "description": "Payment to vendor #{vendor} - Invoice #{invoice}",
                "entries": [
                    ("2001", "debit", "payment_amount"),  # A/P
                    ("1001", "credit", "payment_amount"), # Cash
                ],
                "amount_range": (300, 3000),
                "frequency": 5
            },
            
            # Equipment and depreciation
            {
                "description": "Equipment purchase - {equipment_type}",
                "entries": [
                    ("1400", "debit", "equipment_cost"),  # Equipment
                    ("1001", "credit", "equipment_cost"), # Cash
                ],
                "amount_range": (1000, 10000),
                "frequency": 1
            },
            {
                "description": "Monthly depreciation expense",
                "entries": [
                    ("5400", "debit", "depreciation_amount"),   # Depreciation Expense
                    ("1450", "credit", "depreciation_amount"),  # Accumulated Depreciation
                ],
                "amount_range": (500, 1500),
                "frequency": 1
            },
            
            # Interest and loans
            {
                "description": "Interest income from savings account",
                "entries": [
                    ("1002", "debit", "interest_amount"),  # Savings
                    ("4100", "credit", "interest_amount"), # Interest Income
                ],
                "amount_range": (25, 200),
                "frequency": 1
            },
            {
                "description": "Loan payment - Principal and Interest",
                "entries": [
                    ("2500", "debit", "principal_amount"),  # Notes Payable
                    ("5500", "debit", "interest_amount"),   # Interest Expense
                    ("1001", "credit", "total_payment"),    # Cash
                ],
                "amount_range": (1000, 3000),
                "frequency": 1,
                "multi_line": True
            },
            
            # Adjusting entries
            {
                "description": "Insurance expense allocation",
                "entries": [
                    ("5202", "debit", "insurance_amount"),  # Insurance Expense
                    ("1300", "credit", "insurance_amount"), # Prepaid Insurance
                ],
                "amount_range": (200, 600),
                "frequency": 1
            },
            
            # Cost of goods sold
            {
                "description": "Cost of goods sold - Sales #{sale_id}",
                "entries": [
                    ("5001", "debit", "cogs_amount"),    # COGS
                    ("1201", "credit", "cogs_amount"),   # Finished Goods
                ],
                "amount_range": (300, 2000),
                "frequency": 6
            },
        ]
    
    def create_gl_accounts(self):
        """Create GL accounts in the database"""
        logger.info("Creating GL accounts...")
        
        try:
            with engine.begin() as conn:
                for account_id, (account_name, account_type) in self.gl_accounts.items():
                    conn.execute(text("""
                        INSERT INTO glaccount (glaccountid, companycodeid, accountname, accounttype, isreconaccount, isopenitemmanaged)
                        VALUES (:account_id, :company_code, :account_name, :account_type, :is_recon, :is_open_item)
                        ON CONFLICT (glaccountid) DO UPDATE SET
                            accountname = EXCLUDED.accountname,
                            accounttype = EXCLUDED.accounttype
                    """), {
                        'account_id': account_id,
                        'company_code': self.company_code,
                        'account_name': account_name,
                        'account_type': account_type,
                        'is_recon': account_id in ['1100', '2001'],  # A/R and A/P are reconciliation accounts
                        'is_open_item': account_id in ['1100', '2001']  # A/R and A/P are open item managed
                    })
            
            logger.info(f"Created {len(self.gl_accounts)} GL accounts")
            
        except Exception as e:
            logger.error(f"Error creating GL accounts: {e}")
            raise
    
    def generate_amount(self, amount_range):
        """Generate a random amount within the specified range"""
        min_amount, max_amount = amount_range
        amount = random.uniform(min_amount, max_amount)
        # Round to 2 decimal places
        return float(Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    
    def get_random_values(self):
        """Get random values for template placeholders"""
        return {
            'customer': random.randint(1001, 9999),
            'supplier': random.randint(2001, 2999),
            'vendor': random.randint(3001, 3999),
            'invoice': random.randint(10001, 99999),
            'check': random.randint(1001, 9999),
            'sale_id': random.randint(5001, 5999),
            'equipment_type': random.choice(['Computer', 'Printer', 'Desk', 'Phone System', 'Software']),
            'utility_type': random.choice(['Electric', 'Gas', 'Water', 'Internet', 'Phone'])
        }
    
    def create_journal_entry(self, period, entry_number, template):
        """Create a single journal entry from template"""
        # Generate random date within the period
        start_date = datetime(self.fiscal_year, period, 1)
        if period == 12:
            end_date = datetime(self.fiscal_year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(self.fiscal_year, period + 1, 1) - timedelta(days=1)
        
        random_date = start_date + timedelta(
            days=random.randint(0, (end_date - start_date).days)
        )
        
        # Generate unique document number - use random component to avoid conflicts
        import time
        random_suffix = random.randint(10000, 99999)
        doc_number = f"ST{self.fiscal_year}{period:02d}{entry_number:04d}{random_suffix}"
        
        # Get random values for template
        random_values = self.get_random_values()
        
        # Generate amounts
        base_amount = self.generate_amount(template['amount_range'])
        
        # Format description
        description = template['description'].format(**random_values)
        
        try:
            with engine.begin() as conn:
                # Create journal entry header
                conn.execute(text("""
                    INSERT INTO journalentryheader 
                    (documentnumber, companycodeid, postingdate, documentdate, fiscalyear, period, reference, currencycode, createdby)
                    VALUES (:doc_number, :company_code, :posting_date, :doc_date, :fiscal_year, :period, :reference, :currency, :created_by)
                """), {
                    'doc_number': doc_number,
                    'company_code': self.company_code,
                    'posting_date': random_date,
                    'doc_date': random_date,
                    'fiscal_year': self.fiscal_year,
                    'period': period,
                    'reference': f"Auto-generated sample data - {description}",
                    'currency': self.currency_code,
                    'created_by': 'system'
                })
                
                # Create journal entry lines
                line_number = 1
                total_debits = 0
                total_credits = 0
                
                if template.get('multi_line'):
                    # Handle complex multi-line entries
                    if 'Monthly payroll' in description:
                        gross_pay = base_amount
                        payroll_taxes = gross_pay * 0.15  # 15% for employer taxes
                        tax_withholding = gross_pay * 0.25  # 25% total withholding
                        net_pay = gross_pay - tax_withholding
                        
                        amounts = {
                            'gross_pay': gross_pay,
                            'payroll_taxes': payroll_taxes,
                            'net_pay': net_pay,
                            'tax_withholding': tax_withholding
                        }
                    elif 'Loan payment' in description:
                        total_payment = base_amount
                        interest_amount = total_payment * 0.3  # 30% interest
                        principal_amount = total_payment - interest_amount
                        
                        amounts = {
                            'total_payment': total_payment,
                            'interest_amount': interest_amount,
                            'principal_amount': principal_amount
                        }
                    
                    # Create lines based on template
                    for account_id, side, amount_key in template['entries']:
                        amount = amounts.get(amount_key, base_amount)
                        
                        debit_amount = amount if side == 'debit' else 0
                        credit_amount = amount if side == 'credit' else 0
                        
                        conn.execute(text("""
                            INSERT INTO journalentryline
                            (documentnumber, companycodeid, linenumber, glaccountid, description, 
                             debitamount, creditamount, currencycode, ledgerid)
                            VALUES (:doc_number, :company_code, :line_number, :account_id, :description,
                                    :debit_amount, :credit_amount, :currency, :ledger_id)
                        """), {
                            'doc_number': doc_number,
                            'company_code': self.company_code,
                            'line_number': line_number,
                            'account_id': account_id,
                            'description': description,
                            'debit_amount': debit_amount,
                            'credit_amount': credit_amount,
                            'currency': self.currency_code,
                            'ledger_id': self.ledger_id
                        })
                        
                        total_debits += debit_amount
                        total_credits += credit_amount
                        line_number += 1
                
                else:
                    # Simple two-line entries
                    for account_id, side, _ in template['entries']:
                        debit_amount = base_amount if side == 'debit' else 0
                        credit_amount = base_amount if side == 'credit' else 0
                        
                        conn.execute(text("""
                            INSERT INTO journalentryline
                            (documentnumber, companycodeid, linenumber, glaccountid, description, 
                             debitamount, creditamount, currencycode, ledgerid)
                            VALUES (:doc_number, :company_code, :line_number, :account_id, :description,
                                    :debit_amount, :credit_amount, :currency, :ledger_id)
                        """), {
                            'doc_number': doc_number,
                            'company_code': self.company_code,
                            'line_number': line_number,
                            'account_id': account_id,
                            'description': description,
                            'debit_amount': debit_amount,
                            'credit_amount': credit_amount,
                            'currency': self.currency_code,
                            'ledger_id': self.ledger_id
                        })
                        
                        total_debits += debit_amount
                        total_credits += credit_amount
                        line_number += 1
                
                # Verify debits equal credits
                if abs(total_debits - total_credits) > 0.01:
                    raise ValueError(f"Debits ({total_debits}) don't equal credits ({total_credits}) for {doc_number}")
                
                logger.debug(f"Created journal entry {doc_number}: {description} (${base_amount:.2f})")
                
        except Exception as e:
            logger.error(f"Error creating journal entry {doc_number}: {e}")
            raise
    
    def generate_journal_entries_for_period(self, period, entries_count=30):
        """Generate journal entries for a specific period"""
        logger.info(f"Generating {entries_count} journal entries for period {period}...")
        
        # Create weighted list of templates based on frequency
        weighted_templates = []
        for template in self.transaction_templates:
            frequency = template.get('frequency', 1)
            weighted_templates.extend([template] * frequency)
        
        entries_created = 0
        batch_size = 100  # Report progress every 100 entries for stress tests
        
        for entry_number in range(1, entries_count + 1):  # Create specified number of entries
            # Select random template
            template = random.choice(weighted_templates)
            
            try:
                self.create_journal_entry(period, entry_number, template)
                entries_created += 1
                
                # Progress reporting for stress tests
                if entries_count >= 100 and entry_number % batch_size == 0:
                    progress = (entry_number / entries_count) * 100
                    logger.info(f"Period {period} - {entry_number}/{entries_count} entries ({progress:.1f}%)")
                
            except Exception as e:
                logger.error(f"Failed to create entry {entry_number} for period {period}: {e}")
                continue
        
        logger.info(f"Created {entries_created} journal entries for period {period}")
        
        # Progress reporting for large batches
        if entries_count >= 100:
            completion_percentage = (entries_created / entries_count) * 100
            logger.info(f"Period {period} completion: {completion_percentage:.1f}% ({entries_created}/{entries_count})")
        
        return entries_created
    
    def generate_all_sample_data(self, entries_per_period=30):
        """Generate all sample data - GL accounts and journal entries"""
        logger.info(f"Starting sample data generation with {entries_per_period} entries per period...")
        
        try:
            # First, create GL accounts
            self.create_gl_accounts()
            
            # Then create journal entries for all 12 periods
            total_entries = 0
            total_expected = entries_per_period * 12
            
            for period in range(1, 13):
                logger.info(f"Starting period {period}/12 ({entries_per_period} entries)...")
                start_time = datetime.utcnow()
                
                entries_count = self.generate_journal_entries_for_period(period, entries_per_period)
                total_entries += entries_count
                
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                logger.info(f"Period {period} completed in {elapsed:.1f}s - Generated {entries_count} entries")
                
                # Overall progress
                overall_progress = (total_entries / total_expected) * 100
                logger.info(f"Overall progress: {overall_progress:.1f}% ({total_entries}/{total_expected})")
            
            logger.info(f"Sample data generation completed successfully!")
            logger.info(f"Total GL accounts created: {len(self.gl_accounts)}")
            logger.info(f"Total journal entries created: {total_entries}")
            
            return total_entries
            
        except Exception as e:
            logger.error(f"Sample data generation failed: {e}")
            raise
    
    def validate_data_integrity(self):
        """Validate the generated data for integrity"""
        logger.info("Validating data integrity...")
        
        try:
            with engine.connect() as conn:
                # Check journal entry balance
                result = conn.execute(text("""
                    SELECT documentnumber, companycodeid,
                           SUM(debitamount) as total_debits,
                           SUM(creditamount) as total_credits,
                           ABS(SUM(debitamount) - SUM(creditamount)) as difference
                    FROM journalentryline
                    WHERE companycodeid = :company_code
                    GROUP BY documentnumber, companycodeid
                    HAVING ABS(SUM(debitamount) - SUM(creditamount)) > 0.01
                """), {'company_code': self.company_code})
                
                unbalanced = result.fetchall()
                if unbalanced:
                    logger.error(f"Found {len(unbalanced)} unbalanced journal entries!")
                    for entry in unbalanced:
                        logger.error(f"  {entry[0]}: Debits={entry[2]:.2f}, Credits={entry[3]:.2f}, Diff={entry[4]:.2f}")
                    return False
                
                # Check for missing GL accounts
                result = conn.execute(text("""
                    SELECT DISTINCT jel.glaccountid
                    FROM journalentryline jel
                    LEFT JOIN glaccount gl ON jel.glaccountid = gl.glaccountid
                    WHERE gl.glaccountid IS NULL
                """))
                
                missing_accounts = result.fetchall()
                if missing_accounts:
                    logger.error(f"Found journal entries with missing GL accounts: {missing_accounts}")
                    return False
                
                # Get summary statistics
                result = conn.execute(text("""
                    SELECT 
                        COUNT(DISTINCT jeh.documentnumber) as total_entries,
                        COUNT(jel.linenumber) as total_lines,
                        SUM(jel.debitamount) as total_debits,
                        SUM(jel.creditamount) as total_credits
                    FROM journalentryheader jeh
                    JOIN journalentryline jel ON jeh.documentnumber = jel.documentnumber 
                        AND jeh.companycodeid = jel.companycodeid
                    WHERE jeh.companycodeid = :company_code
                """), {'company_code': self.company_code})
                
                stats = result.first()
                logger.info(f"Data validation summary:")
                logger.info(f"  Total journal entries: {stats[0]}")
                logger.info(f"  Total journal lines: {stats[1]}")
                logger.info(f"  Total debits: ${stats[2]:,.2f}")
                logger.info(f"  Total credits: ${stats[3]:,.2f}")
                logger.info(f"  Balance check: ${abs(stats[2] - stats[3]):,.2f} difference")
                
                if abs(stats[2] - stats[3]) > 0.01:
                    logger.error("Overall debits and credits don't balance!")
                    return False
                
                logger.info("✅ Data validation passed!")
                return True
                
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return False


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate sample journal entries for GL ERP")
    parser.add_argument('--validate-only', action='store_true', help='Only validate existing data')
    parser.add_argument('--periods', type=int, nargs='+', help='Specific periods to generate (1-12)')
    parser.add_argument('--company', default='1000', help='Company code (default: 1000)')
    parser.add_argument('--entries-per-period', type=int, default=30, help='Number of entries per period (default: 30)')
    parser.add_argument('--stress-test', action='store_true', help='Run stress test with 1000 entries per period')
    
    args = parser.parse_args()
    
    generator = SampleDataGenerator()
    if args.company:
        generator.company_code = args.company
    
    # Handle stress test option
    if args.stress_test:
        args.entries_per_period = 1000
        logger.info("🚀 Stress test mode enabled - generating 1000 entries per period")
    
    try:
        if args.validate_only:
            # Only validate existing data
            success = generator.validate_data_integrity()
            if not success:
                sys.exit(1)
        
        elif args.periods:
            # Generate data for specific periods
            generator.create_gl_accounts()
            total_entries = 0
            
            for period in args.periods:
                if 1 <= period <= 12:
                    entries = generator.generate_journal_entries_for_period(period, args.entries_per_period)
                    total_entries += entries
                else:
                    logger.error(f"Invalid period: {period}. Must be 1-12")
            
            logger.info(f"Generated {total_entries} journal entries for periods {args.periods}")
            generator.validate_data_integrity()
        
        else:
            # Generate all sample data
            total_entries = generator.generate_all_sample_data(args.entries_per_period)
            generator.validate_data_integrity()
            
            print(f"\n✅ Sample data generation completed successfully!")
            print(f"📊 Generated {len(generator.gl_accounts)} GL accounts")
            print(f"📝 Generated {total_entries} journal entries ({args.entries_per_period} per period x 12 periods)")
            print(f"💼 Company: {generator.company_code}")
            print(f"📅 Fiscal Year: {generator.fiscal_year}")
            
            if args.stress_test:
                print(f"🚀 Stress test completed with {total_entries:,} journal entries!")
                print(f"💾 Database performance validated with large dataset")
            
            print(f"\nTo view the data, run the Streamlit application:")
            print(f"  streamlit run Home.py")
    
    except Exception as e:
        logger.error(f"Sample data generation failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()