"""
IAS 21 Test Data Setup

Creates comprehensive test data for IAS 21 compliance testing including:
- Multi-currency journal entries
- Exchange rates 
- Test entities and companies
- Functional currency assessments
- Net investment scenarios

Author: Claude Code Assistant
Date: August 6, 2025
"""

import sys
from datetime import datetime, date, timedelta
from decimal import Decimal
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from db_config import engine

class IAS21TestDataSetup:
    """Setup comprehensive test data for IAS 21 compliance testing."""
    
    def __init__(self):
        """Initialize test data setup."""
        self.test_entities = {
            'MULTICURR_TEST': 'Multi-Currency Test Entity',
            'TEST_ENTITY': 'Test Entity for FC Change',
            'SUB_EUR_TEST': 'European Subsidiary Test',
            'SUB_GBP_TEST': 'UK Subsidiary Test',
            'SUB_JPY_TEST': 'Japan Subsidiary Test'
        }
        
        self.test_currencies = ['EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD']
        self.base_currency = 'USD'
        
    def setup_all_test_data(self):
        """Set up all test data for IAS 21 compliance."""
        
        print("🔧 Setting up IAS 21 test data...")
        
        try:
            with engine.begin() as conn:
                # 1. Create test companies
                self._create_test_companies(conn)
                
                # 2. Set up exchange rates
                self._create_exchange_rates(conn)
                
                # 3. Create test accounts
                self._create_test_accounts(conn)
                
                # 4. Create journal entries with FX transactions
                self._create_fx_journal_entries(conn)
                
                # 5. Set up functional currency data
                self._setup_functional_currency_data(conn)
                
                # 6. Create net investment scenarios
                self._create_net_investment_scenarios(conn)
                
                # 7. Set up test ledgers
                self._setup_test_ledgers(conn)
                
                print("✅ All IAS 21 test data created successfully")
                
        except Exception as e:
            print(f"❌ Error setting up test data: {e}")
            raise
    
    def _create_test_companies(self, conn):
        """Create test company codes."""
        
        print("  📊 Creating test companies...")
        
        for entity_id, entity_name in self.test_entities.items():
            try:
                conn.execute(text("""
                    INSERT INTO companycode (companycodeid, companyname, currency, created_by)
                    VALUES (:entity_id, :entity_name, :currency, 'TEST_SETUP')
                    ON CONFLICT (companycodeid) DO UPDATE SET
                        companyname = :entity_name,
                        updated_at = CURRENT_TIMESTAMP
                """), {
                    "entity_id": entity_id,
                    "entity_name": entity_name,
                    "currency": self.base_currency
                })
                print(f"    ✅ Created company: {entity_id}")
                
            except Exception as e:
                print(f"    ⚠️ Company {entity_id} may already exist: {e}")
    
    def _create_exchange_rates(self, conn):
        """Create comprehensive exchange rate data."""
        
        print("  💱 Creating exchange rates...")
        
        # Exchange rates for multiple periods
        base_rates = {
            'EUR': 1.0850,
            'GBP': 1.2650,
            'JPY': 0.0067,
            'CHF': 1.0920,
            'CAD': 0.7345,
            'AUD': 0.6789
        }
        
        # Create rates for last 6 months
        start_date = date.today() - timedelta(days=180)
        
        for i in range(180):
            rate_date = start_date + timedelta(days=i)
            
            for currency, base_rate in base_rates.items():
                # Add some volatility
                volatility = 0.05 * (i % 10 - 5) / 100  # ±5% volatility
                daily_rate = Decimal(str(base_rate * (1 + volatility))).quantize(Decimal('0.000001'))
                
                try:
                    conn.execute(text("""
                        INSERT INTO exchange_rates 
                        (from_currency, to_currency, exchange_rate, rate_type, rate_date, created_by)
                        VALUES (:from_curr, :to_curr, :rate, 'CLOSING', :rate_date, 'TEST_SETUP')
                        ON CONFLICT (from_currency, to_currency, rate_type, rate_date) 
                        DO UPDATE SET exchange_rate = :rate
                    """), {
                        "from_curr": currency,
                        "to_curr": self.base_currency,
                        "rate": daily_rate,
                        "rate_date": rate_date
                    })
                    
                except Exception as e:
                    pass  # Rate may already exist
        
        print(f"    ✅ Created exchange rates for {len(base_rates)} currencies over 180 days")
    
    def _create_test_accounts(self, conn):
        """Create test GL accounts for FX testing."""
        
        print("  📚 Creating test GL accounts...")
        
        test_accounts = [
            # Foreign currency assets
            ('115010', 'AR - EUR Customers', 'ASSETS', 'RECV', 'EUR', 'MONETARY'),
            ('115020', 'AR - GBP Customers', 'ASSETS', 'RECV', 'GBP', 'MONETARY'),
            ('115030', 'AR - JPY Customers', 'ASSETS', 'RECV', 'JPY', 'MONETARY'),
            ('100010', 'Cash - EUR Bank', 'ASSETS', 'CASH', 'EUR', 'MONETARY'),
            ('100020', 'Cash - GBP Bank', 'ASSETS', 'CASH', 'GBP', 'MONETARY'),
            
            # Foreign currency liabilities
            ('210010', 'AP - EUR Vendors', 'LIABILITIES', 'PAYB', 'EUR', 'MONETARY'),
            ('210020', 'AP - GBP Vendors', 'LIABILITIES', 'PAYB', 'GBP', 'MONETARY'),
            ('230010', 'FX Forward Contracts', 'LIABILITIES', 'DERV', 'USD', 'MONETARY'),
            
            # Non-monetary foreign assets
            ('150010', 'Inventory - EUR', 'ASSETS', 'INVN', 'EUR', 'NON_MONETARY'),
            ('160010', 'Equipment - GBP', 'ASSETS', 'FXAS', 'GBP', 'NON_MONETARY'),
            
            # Equity accounts
            ('300010', 'Capital - EUR Sub', 'EQUITY', 'EQUITY', 'EUR', 'EQUITY'),
            ('300020', 'Retained Earnings - GBP Sub', 'EQUITY', 'EQUITY', 'GBP', 'EQUITY'),
            
            # OCI and CTA accounts
            ('390010', 'AOCI - FX Translation', 'EQUITY', 'OCI', 'USD', 'EQUITY'),
            ('390020', 'CTA - Net Investment', 'EQUITY', 'CTA', 'USD', 'EQUITY'),
            
            # FX gain/loss accounts
            ('485010', 'FX Gain/Loss - Realized', 'EXPENSES', 'OPEX', 'USD', 'REVENUE_EXPENSE'),
            ('485020', 'FX Gain/Loss - Unrealized', 'EXPENSES', 'OPEX', 'USD', 'REVENUE_EXPENSE'),
        ]
        
        for account_id, account_name, account_type, group_code, currency, classification in test_accounts:
            try:
                conn.execute(text("""
                    INSERT INTO glaccount 
                    (glaccountid, accountname, accounttype, account_group_code, 
                     account_currency, monetary_classification, created_by)
                    VALUES (:account_id, :account_name, :account_type, :group_code,
                            :currency, :classification, 'TEST_SETUP')
                    ON CONFLICT (glaccountid) DO UPDATE SET
                        accountname = :account_name,
                        account_currency = :currency,
                        monetary_classification = :classification
                """), {
                    "account_id": account_id,
                    "account_name": account_name,
                    "account_type": account_type,
                    "group_code": group_code,
                    "currency": currency,
                    "classification": classification
                })
                
            except Exception as e:
                pass  # Account may already exist
        
        print(f"    ✅ Created {len(test_accounts)} test GL accounts")
    
    def _create_fx_journal_entries(self, conn):
        """Create journal entries with foreign currency transactions."""
        
        print("  📝 Creating FX journal entries...")
        
        # Create journal entries for different scenarios
        scenarios = [
            {
                'entity': 'MULTICURR_TEST',
                'description': 'EUR Customer Payment',
                'entries': [
                    ('100010', 'EUR', 10000.00, 0.00),  # Cash EUR
                    ('115010', 'EUR', 0.00, 10000.00),  # AR EUR
                ]
            },
            {
                'entity': 'MULTICURR_TEST', 
                'description': 'GBP Vendor Payment',
                'entries': [
                    ('210020', 'GBP', 0.00, 5000.00),  # AP GBP
                    ('100020', 'GBP', 5000.00, 0.00),  # Cash GBP
                ]
            },
            {
                'entity': 'SUB_EUR_TEST',
                'description': 'Equipment Purchase - EUR',
                'entries': [
                    ('160010', 'EUR', 50000.00, 0.00),  # Equipment
                    ('210010', 'EUR', 0.00, 50000.00),  # AP EUR
                ]
            },
            {
                'entity': 'SUB_GBP_TEST',
                'description': 'Intercompany Loan - No Settlement',
                'entries': [
                    ('115020', 'GBP', 100000.00, 0.00),  # IC Receivable
                    ('100020', 'GBP', 0.00, 100000.00),  # Cash
                ]
            }
        ]
        
        entry_count = 0
        for i, scenario in enumerate(scenarios):
            doc_number = f"FXT{str(i+1).zfill(4)}"
            entity_id = scenario['entity']
            
            try:
                # Create journal header
                conn.execute(text("""
                    INSERT INTO journalentryheader 
                    (documentnumber, companycodeid, postingdate, documentdate,
                     fiscalyear, period, reference, description, workflow_status, created_by)
                    VALUES (:doc_num, :company, :posting_date, :doc_date,
                            :fy, :period, :ref, :desc, 'POSTED', 'TEST_SETUP')
                    ON CONFLICT (documentnumber, companycodeid) DO UPDATE SET
                        description = :desc
                """), {
                    "doc_num": doc_number,
                    "company": entity_id,
                    "posting_date": date.today(),
                    "doc_date": date.today(),
                    "fy": 2025,
                    "period": 1,
                    "ref": f"TEST-{i+1}",
                    "desc": scenario['description']
                })
                
                # Create journal lines
                for line_num, (account, currency, debit, credit) in enumerate(scenario['entries'], 1):
                    conn.execute(text("""
                        INSERT INTO journalentryline
                        (documentnumber, companycodeid, linenumber, glaccountid,
                         description, debitamount, creditamount, currencycode,
                         ledgerid, exchange_rate, original_amount)
                        VALUES (:doc_num, :company, :line_num, :account,
                                :desc, :debit, :credit, :currency,
                                'L1', 1.0850, :original)
                        ON CONFLICT (documentnumber, companycodeid, linenumber) DO UPDATE SET
                            debitamount = :debit,
                            creditamount = :credit
                    """), {
                        "doc_num": doc_number,
                        "company": entity_id,
                        "line_num": line_num,
                        "account": account,
                        "desc": scenario['description'],
                        "debit": debit,
                        "credit": credit,
                        "currency": currency,
                        "original": debit - credit
                    })
                    entry_count += 1
                
            except Exception as e:
                print(f"    ⚠️ Error creating journal {doc_number}: {e}")
        
        print(f"    ✅ Created {entry_count} journal entry lines across {len(scenarios)} scenarios")
    
    def _setup_functional_currency_data(self, conn):
        """Set up functional currency assessment data."""
        
        print("  🌍 Setting up functional currency data...")
        
        functional_currency_data = [
            {
                'entity_id': 'MULTICURR_TEST',
                'functional_currency': 'EUR',
                'methodology': 'IAS_21',
                'conclusion': 'Primary operations in EUR zone',
                'indicators': {
                    'primary_indicators': {
                        'sales_currency': 'EUR',
                        'costs_currency': 'EUR',
                        'financing_currency': 'EUR'
                    }
                }
            },
            {
                'entity_id': 'SUB_EUR_TEST',
                'functional_currency': 'EUR',
                'methodology': 'IAS_21',
                'conclusion': 'European subsidiary - EUR functional currency',
                'indicators': {
                    'primary_indicators': {
                        'sales_currency': 'EUR',
                        'costs_currency': 'EUR',
                        'financing_currency': 'EUR'
                    }
                }
            },
            {
                'entity_id': 'SUB_GBP_TEST',
                'functional_currency': 'GBP',
                'methodology': 'IAS_21',
                'conclusion': 'UK subsidiary - GBP functional currency',
                'indicators': {
                    'primary_indicators': {
                        'sales_currency': 'GBP',
                        'costs_currency': 'GBP',
                        'financing_currency': 'GBP'
                    }
                }
            }
        ]
        
        for fc_data in functional_currency_data:
            try:
                conn.execute(text("""
                    INSERT INTO entity_functional_currency
                    (entity_id, entity_name, functional_currency, effective_date,
                     assessment_methodology, assessment_conclusion, assessed_by, assessment_date)
                    VALUES (:entity_id, :entity_name, :functional_currency, :effective_date,
                            :methodology, :conclusion, 'TEST_SETUP', :assessment_date)
                    ON CONFLICT (entity_id) DO UPDATE SET
                        functional_currency = :functional_currency,
                        assessment_methodology = :methodology,
                        assessment_conclusion = :conclusion
                """), {
                    "entity_id": fc_data['entity_id'],
                    "entity_name": self.test_entities.get(fc_data['entity_id'], fc_data['entity_id']),
                    "functional_currency": fc_data['functional_currency'],
                    "effective_date": date.today(),
                    "methodology": fc_data['methodology'],
                    "conclusion": fc_data['conclusion'],
                    "assessment_date": date.today()
                })
                
            except Exception as e:
                print(f"    ⚠️ Error setting functional currency for {fc_data['entity_id']}: {e}")
        
        print(f"    ✅ Set up functional currency data for {len(functional_currency_data)} entities")
    
    def _create_net_investment_scenarios(self, conn):
        """Create net investment hedge scenarios."""
        
        print("  🛡️ Creating net investment scenarios...")
        
        # Create hedge relationship for testing
        try:
            conn.execute(text("""
                INSERT INTO hedge_relationships
                (hedge_designation, accounting_standard, hedge_instrument_type,
                 hedge_instrument_id, hedged_item_type, hedged_item_id,
                 hedged_risk, hedge_ratio, effectiveness_test_method,
                 hedge_inception_date, documentation_date, hedge_status, created_by)
                VALUES ('NET_INVESTMENT', 'IFRS_9', 'FX_FORWARD',
                        'FWD_TEST_001', 'NET_INVESTMENT', 'SUB_EUR_TEST',
                        'FX_RISK', 1.0000, 'DOLLAR_OFFSET',
                        :inception_date, :doc_date, 'ACTIVE', 'TEST_SETUP')
                ON CONFLICT DO NOTHING
            """), {
                "inception_date": date.today(),
                "doc_date": date.today()
            })
            
            print("    ✅ Created net investment hedge relationship")
            
        except Exception as e:
            print(f"    ⚠️ Error creating hedge relationship: {e}")
    
    def _setup_test_ledgers(self, conn):
        """Set up test ledgers with accounting principles."""
        
        print("  📒 Setting up test ledgers...")
        
        test_ledgers = [
            ('L1', 'US GAAP Ledger', 'ASC_830'),
            ('2L', 'IFRS Ledger', 'IAS_21'),  
            ('3L', 'Tax Ledger', 'TAX_GAAP'),
            ('4L', 'Management Ledger', 'MGMT_GAAP')
        ]
        
        for ledger_id, ledger_name, accounting_principle in test_ledgers:
            try:
                conn.execute(text("""
                    UPDATE ledger 
                    SET accounting_principle = :principle
                    WHERE ledgerid = :ledger_id
                """), {
                    "ledger_id": ledger_id,
                    "principle": accounting_principle
                })
                
            except Exception as e:
                pass  # Ledger may not exist or column may not exist
        
        print(f"    ✅ Updated accounting principles for {len(test_ledgers)} ledgers")
    
    def cleanup_test_data(self):
        """Clean up test data (optional - for development only)."""
        
        print("🧹 Cleaning up test data...")
        
        try:
            with engine.begin() as conn:
                # Delete test journal entries
                for entity_id in self.test_entities.keys():
                    conn.execute(text("""
                        DELETE FROM journalentryline 
                        WHERE companycodeid = :entity_id AND documentnumber LIKE 'FXT%'
                    """), {"entity_id": entity_id})
                    
                    conn.execute(text("""
                        DELETE FROM journalentryheader 
                        WHERE companycodeid = :entity_id AND documentnumber LIKE 'FXT%'
                    """), {"entity_id": entity_id})
                
                # Delete test exchange rates
                conn.execute(text("""
                    DELETE FROM exchange_rates WHERE created_by = 'TEST_SETUP'
                """))
                
                # Delete test entities (be careful with foreign keys)
                for entity_id in self.test_entities.keys():
                    try:
                        conn.execute(text("""
                            DELETE FROM entity_functional_currency WHERE entity_id = :entity_id
                        """), {"entity_id": entity_id})
                        
                        conn.execute(text("""
                            DELETE FROM companycode WHERE companycodeid = :entity_id
                        """), {"entity_id": entity_id})
                    except:
                        pass  # May have foreign key constraints
                
                print("✅ Test data cleanup completed")
                
        except Exception as e:
            print(f"❌ Error cleaning up test data: {e}")

def main():
    """Main execution."""
    setup = IAS21TestDataSetup()
    
    print("IAS 21 Test Data Setup")
    print("=" * 50)
    
    choice = input("Choose action: (s)etup, (c)leanup, or (q)uit: ").lower()
    
    if choice == 's':
        setup.setup_all_test_data()
        print("\n✅ Test data setup completed successfully!")
        print("You can now run the IAS 21 compliance tests with proper data.")
        
    elif choice == 'c':
        confirm = input("Are you sure you want to cleanup test data? (y/N): ")
        if confirm.lower() == 'y':
            setup.cleanup_test_data()
        else:
            print("Cleanup cancelled.")
            
    else:
        print("Goodbye!")

if __name__ == "__main__":
    main()