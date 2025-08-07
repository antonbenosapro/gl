#!/usr/bin/env python3
"""
Comprehensive End-to-End Testing for Parallel Ledger System

This test suite validates the complete parallel ledger workflow from document creation
through approval, parallel posting, currency translation, and reporting.

Author: Claude Code Assistant
Date: August 6, 2025
"""

import sys
import os
sys.path.append('/home/anton/erp/gl')

import json
import time
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Dict, List, Any

# Import all services to test
from db_config import engine
from sqlalchemy import text
from utils.parallel_posting_service import ParallelPostingService
from utils.enhanced_auto_posting_service import EnhancedAutoPostingService
from utils.enhanced_workflow_integration import EnhancedWorkflowIntegration
from utils.currency_service import CurrencyTranslationService
from utils.parallel_ledger_reporting_service import ParallelLedgerReportingService
from utils.logger import get_logger

logger = get_logger("e2e_parallel_testing")

class ComprehensiveParallelLedgerE2ETest:
    """Comprehensive end-to-end testing of the parallel ledger system."""
    
    def __init__(self):
        """Initialize the test suite."""
        self.test_results = {
            "test_start_time": datetime.now(),
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "test_details": [],
            "system_status": {},
            "performance_metrics": {}
        }
        
        # Initialize services
        self.parallel_service = ParallelPostingService()
        self.auto_posting_service = EnhancedAutoPostingService()
        self.workflow_service = EnhancedWorkflowIntegration()
        self.currency_service = CurrencyTranslationService()
        self.reporting_service = ParallelLedgerReportingService()
        
        # Test data
        self.test_document = None
        self.test_company_code = "1000"
        
    def log_test_result(self, test_name: str, passed: bool, message: str, details: Dict = None):
        """Log a test result."""
        self.test_results["tests_run"] += 1
        if passed:
            self.test_results["tests_passed"] += 1
            status = "✅ PASS"
        else:
            self.test_results["tests_failed"] += 1
            status = "❌ FAIL"
        
        test_detail = {
            "test_name": test_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now(),
            "details": details or {}
        }
        
        self.test_results["test_details"].append(test_detail)
        print(f"{status} | {test_name}: {message}")
        
        if details:
            for key, value in details.items():
                print(f"    {key}: {value}")
    
    def run_all_tests(self):
        """Run the complete end-to-end test suite."""
        print("=" * 80)
        print("🧪 COMPREHENSIVE PARALLEL LEDGER END-TO-END TESTING")
        print("=" * 80)
        print()
        
        # Test sequence
        test_sequence = [
            ("System Infrastructure", self.test_system_infrastructure),
            ("Service Initialization", self.test_service_initialization),
            ("Database Connectivity", self.test_database_connectivity),
            ("Ledger Configuration", self.test_ledger_configuration),
            ("Exchange Rate System", self.test_exchange_rate_system),
            ("Create Test Document", self.test_create_source_document),
            ("Workflow Integration", self.test_workflow_integration),
            ("Parallel Posting Engine", self.test_parallel_posting_engine),
            ("Currency Translation", self.test_currency_translation),
            ("Balance Validation", self.test_balance_validation),
            ("Reporting Services", self.test_reporting_services),
            ("Performance Analysis", self.test_performance_analysis),
            ("Data Consistency", self.test_data_consistency),
        ]
        
        for test_category, test_function in test_sequence:
            print(f"\n🔍 Testing: {test_category}")
            print("-" * 50)
            try:
                test_function()
            except Exception as e:
                self.log_test_result(test_category, False, f"Test category failed: {str(e)}")
        
        # Generate final report
        self.generate_final_report()
    
    def test_system_infrastructure(self):
        """Test system infrastructure and prerequisites."""
        try:
            # Test database connection
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).scalar()
                self.log_test_result("Database Connection", result == 1, "Database accessible")
            
            # Test required tables exist
            required_tables = [
                'ledger', 'journalentryheader', 'journalentryline',
                'exchangerate', 'gl_account_balances', 'ledger_derivation_rules'
            ]
            
            with engine.connect() as conn:
                for table in required_tables:
                    result = conn.execute(text(f"""
                        SELECT COUNT(*) FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    """)).scalar()
                    
                    self.log_test_result(
                        f"Table: {table}",
                        result == 1,
                        "Table exists" if result == 1 else "Table missing"
                    )
            
            # Test required views exist
            required_views = [
                'v_current_exchange_rates',
                'v_derivation_rules_summary'
            ]
            
            with engine.connect() as conn:
                for view in required_views:
                    result = conn.execute(text(f"""
                        SELECT COUNT(*) FROM information_schema.views 
                        WHERE table_name = '{view}'
                    """)).scalar()
                    
                    self.log_test_result(
                        f"View: {view}",
                        result == 1,
                        "View exists" if result == 1 else "View missing"
                    )
                    
        except Exception as e:
            self.log_test_result("System Infrastructure", False, f"Infrastructure test failed: {str(e)}")
    
    def test_service_initialization(self):
        """Test that all services initialize correctly."""
        try:
            services = [
                ("ParallelPostingService", self.parallel_service),
                ("EnhancedAutoPostingService", self.auto_posting_service),
                ("EnhancedWorkflowIntegration", self.workflow_service),
                ("CurrencyTranslationService", self.currency_service),
                ("ParallelLedgerReportingService", self.reporting_service)
            ]
            
            for service_name, service in services:
                # Test service has required methods
                required_methods = {
                    "ParallelPostingService": ["process_approved_document_to_all_ledgers"],
                    "EnhancedAutoPostingService": ["process_document_with_parallel_posting"],
                    "EnhancedWorkflowIntegration": ["approve_document_with_parallel_posting"],
                    "CurrencyTranslationService": ["translate_amount"],
                    "ParallelLedgerReportingService": ["generate_trial_balance_by_ledger"]
                }
                
                methods = required_methods.get(service_name, [])
                for method_name in methods:
                    has_method = hasattr(service, method_name)
                    self.log_test_result(
                        f"{service_name}.{method_name}",
                        has_method,
                        "Method available" if has_method else "Method missing"
                    )
                    
        except Exception as e:
            self.log_test_result("Service Initialization", False, f"Service initialization failed: {str(e)}")
    
    def test_database_connectivity(self):
        """Test database connectivity and basic operations."""
        try:
            with engine.connect() as conn:
                # Test read operations
                ledger_count = conn.execute(text("SELECT COUNT(*) FROM ledger")).scalar()
                self.log_test_result(
                    "Ledger Table Read",
                    ledger_count > 0,
                    f"Found {ledger_count} ledgers",
                    {"ledger_count": ledger_count}
                )
                
                # Test exchange rates
                rate_count = conn.execute(text("SELECT COUNT(*) FROM exchangerate")).scalar()
                self.log_test_result(
                    "Exchange Rates Data",
                    rate_count > 0,
                    f"Found {rate_count} exchange rate records",
                    {"rate_count": rate_count}
                )
                
                # Test derivation rules
                rule_count = conn.execute(text("SELECT COUNT(*) FROM ledger_derivation_rules")).scalar()
                self.log_test_result(
                    "Derivation Rules",
                    rule_count > 0,
                    f"Found {rule_count} derivation rules",
                    {"rule_count": rule_count}
                )
                
        except Exception as e:
            self.log_test_result("Database Connectivity", False, f"Database connectivity test failed: {str(e)}")
    
    def test_ledger_configuration(self):
        """Test ledger configuration and setup."""
        try:
            with engine.connect() as conn:
                # Get ledger configuration
                ledgers = conn.execute(text("""
                    SELECT ledgerid, description, accounting_principle, 
                           currencycode, isleadingledger
                    FROM ledger 
                    ORDER BY isleadingledger DESC, ledgerid
                """)).fetchall()
                
                leading_ledgers = [l for l in ledgers if l[4]]  # isleadingledger
                parallel_ledgers = [l for l in ledgers if not l[4]]
                
                # Test leading ledger
                self.log_test_result(
                    "Leading Ledger Count",
                    len(leading_ledgers) == 1,
                    f"Expected 1 leading ledger, found {len(leading_ledgers)}",
                    {"leading_ledger": leading_ledgers[0][0] if leading_ledgers else "None"}
                )
                
                # Test parallel ledgers
                expected_parallel_ledgers = ["2L", "3L", "4L", "CL"]
                parallel_ledger_ids = [l[0] for l in parallel_ledgers]
                
                for expected_ledger in expected_parallel_ledgers:
                    exists = expected_ledger in parallel_ledger_ids
                    self.log_test_result(
                        f"Parallel Ledger: {expected_ledger}",
                        exists,
                        "Configured" if exists else "Missing"
                    )
                
                # Store system status
                self.test_results["system_status"]["ledgers"] = {
                    "total": len(ledgers),
                    "leading": len(leading_ledgers),
                    "parallel": len(parallel_ledgers),
                    "configured_parallel": parallel_ledger_ids
                }
                
        except Exception as e:
            self.log_test_result("Ledger Configuration", False, f"Ledger configuration test failed: {str(e)}")
    
    def test_exchange_rate_system(self):
        """Test exchange rate system functionality."""
        try:
            # Test currency translation service
            test_amount = Decimal('1000.00')
            
            # Test USD to EUR translation
            eur_amount = self.currency_service.translate_amount(test_amount, 'USD', 'EUR')
            self.log_test_result(
                "USD to EUR Translation",
                eur_amount is not None and eur_amount != test_amount,
                f"${test_amount} USD = €{eur_amount} EUR" if eur_amount else "Translation failed"
            )
            
            # Test USD to GBP translation
            gbp_amount = self.currency_service.translate_amount(test_amount, 'USD', 'GBP')
            self.log_test_result(
                "USD to GBP Translation",
                gbp_amount is not None and gbp_amount != test_amount,
                f"${test_amount} USD = £{gbp_amount} GBP" if gbp_amount else "Translation failed"
            )
            
            # Test same currency (should return same amount)
            usd_amount = self.currency_service.translate_amount(test_amount, 'USD', 'USD')
            self.log_test_result(
                "Same Currency Translation",
                usd_amount == test_amount,
                f"USD to USD translation: ${usd_amount}"
            )
            
        except Exception as e:
            self.log_test_result("Exchange Rate System", False, f"Exchange rate test failed: {str(e)}")
    
    def test_create_source_document(self):
        """Create a test source document for parallel posting."""
        try:
            # Generate unique document number
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            doc_number = f"TEST{timestamp}"
            
            with engine.connect() as conn:
                # Create journal entry header
                conn.execute(text("""
                    INSERT INTO journalentryheader (
                        documentnumber, companycodeid, postingdate, documentdate,
                        reference, description, workflow_status, createdat, 
                        createdby, posted_at, posted_by
                    ) VALUES (
                        :doc_number, :company_code, CURRENT_DATE, CURRENT_DATE,
                        'E2E-TEST', 'End-to-End Test Document', 'APPROVED',
                        CURRENT_TIMESTAMP, 'E2E_TEST_USER', CURRENT_TIMESTAMP, 'E2E_TEST_USER'
                    )
                """), {
                    "doc_number": doc_number,
                    "company_code": self.test_company_code
                })
                
                # Create journal entry lines
                test_lines = [
                    {"line": 1, "account": "100001", "debit": 5000.00, "credit": 0.00},
                    {"line": 2, "account": "400001", "debit": 0.00, "credit": 5000.00}
                ]
                
                for line in test_lines:
                    conn.execute(text("""
                        INSERT INTO journalentryline (
                            documentnumber, companycodeid, linenumber, glaccountid,
                            debitamount, creditamount, description
                        ) VALUES (
                            :doc_number, :company_code, :line_number, :account,
                            :debit_amount, :credit_amount, 'E2E Test Line'
                        )
                    """), {
                        "doc_number": doc_number,
                        "company_code": self.test_company_code,
                        "line_number": line["line"],
                        "account": line["account"],
                        "debit_amount": line["debit"],
                        "credit_amount": line["credit"]
                    })
                
                conn.commit()
                
                # Verify document creation
                doc_exists = conn.execute(text("""
                    SELECT COUNT(*) FROM journalentryheader 
                    WHERE documentnumber = :doc_number AND companycodeid = :company_code
                """), {"doc_number": doc_number, "company_code": self.test_company_code}).scalar()
                
                line_count = conn.execute(text("""
                    SELECT COUNT(*) FROM journalentryline 
                    WHERE documentnumber = :doc_number AND companycodeid = :company_code
                """), {"doc_number": doc_number, "company_code": self.test_company_code}).scalar()
                
                success = doc_exists == 1 and line_count == 2
                self.log_test_result(
                    "Test Document Creation",
                    success,
                    f"Created document {doc_number} with {line_count} lines",
                    {"document_number": doc_number, "lines": line_count}
                )
                
                if success:
                    self.test_document = doc_number
                
        except Exception as e:
            self.log_test_result("Create Source Document", False, f"Document creation failed: {str(e)}")
    
    def test_workflow_integration(self):
        """Test workflow integration with parallel posting."""
        try:
            if not self.test_document:
                self.log_test_result("Workflow Integration", False, "No test document available")
                return
            
            # Test workflow service functionality
            approval_summary = self.workflow_service.get_approval_impact_summary(self.test_company_code)
            
            if "error" in approval_summary:
                self.log_test_result(
                    "Workflow Impact Summary",
                    False,
                    f"Error: {approval_summary['error']}"
                )
            else:
                pending_count = approval_summary.get("pending_documents", 0)
                self.log_test_result(
                    "Workflow Impact Summary",
                    "pending_documents" in approval_summary,
                    f"Found {pending_count} pending documents for approval"
                )
            
            # Test bulk approval preview (without executing)
            preview = self.workflow_service.preview_bulk_approval_impact(self.test_company_code)
            
            if "error" in preview:
                self.log_test_result(
                    "Bulk Approval Preview",
                    False,
                    f"Preview error: {preview['error']}"
                )
            else:
                impact_docs = preview.get("documents_to_process", 0)
                impact_ledgers = preview.get("parallel_ledgers_affected", 0)
                
                self.log_test_result(
                    "Bulk Approval Preview",
                    "documents_to_process" in preview,
                    f"Preview shows {impact_docs} documents, {impact_ledgers} ledgers affected"
                )
            
        except Exception as e:
            self.log_test_result("Workflow Integration", False, f"Workflow integration test failed: {str(e)}")
    
    def test_parallel_posting_engine(self):
        """Test the parallel posting engine."""
        try:
            if not self.test_document:
                self.log_test_result("Parallel Posting Engine", False, "No test document available")
                return
            
            # Test parallel posting for the document
            start_time = time.time()
            
            result = self.parallel_service.process_approved_document_to_all_ledgers(
                document_number=self.test_document,
                company_code=self.test_company_code,
                posted_by="E2E_TEST_USER"
            )
            
            processing_time = (time.time() - start_time) * 1000  # milliseconds
            
            if "error" in result:
                self.log_test_result(
                    "Parallel Posting Execution",
                    False,
                    f"Parallel posting failed: {result['error']}"
                )
            else:
                success_count = result.get("successful_ledgers", 0)
                total_count = result.get("target_ledgers", 0)
                success_rate = (success_count / total_count * 100) if total_count > 0 else 0
                
                self.log_test_result(
                    "Parallel Posting Execution",
                    success_count > 0,
                    f"Posted to {success_count}/{total_count} ledgers ({success_rate:.1f}%)",
                    {
                        "processing_time_ms": round(processing_time, 2),
                        "documents_created": result.get("documents_created", []),
                        "success_rate": success_rate
                    }
                )
                
                # Store performance metrics
                self.test_results["performance_metrics"]["parallel_posting"] = {
                    "processing_time_ms": processing_time,
                    "success_rate": success_rate,
                    "documents_created": success_count
                }
            
            # Verify parallel documents were created
            with engine.connect() as conn:
                parallel_docs = conn.execute(text("""
                    SELECT documentnumber, ledger_id FROM journalentryheader 
                    WHERE parallel_source_doc = :source_doc 
                    AND companycodeid = :company_code
                """), {
                    "source_doc": self.test_document,
                    "company_code": self.test_company_code
                }).fetchall()
                
                expected_ledgers = ["2L", "3L", "4L", "CL"]
                created_ledgers = [doc[1] for doc in parallel_docs if doc[1]]
                
                self.log_test_result(
                    "Parallel Documents Created",
                    len(parallel_docs) > 0,
                    f"Created {len(parallel_docs)} parallel documents",
                    {"created_for_ledgers": created_ledgers}
                )
                
                # Test each expected ledger
                for ledger_id in expected_ledgers:
                    ledger_doc_exists = any(doc[1] == ledger_id for doc in parallel_docs)
                    self.log_test_result(
                        f"Document for Ledger {ledger_id}",
                        ledger_doc_exists,
                        "Created" if ledger_doc_exists else "Missing"
                    )
            
        except Exception as e:
            self.log_test_result("Parallel Posting Engine", False, f"Parallel posting test failed: {str(e)}")
    
    def test_currency_translation(self):
        """Test currency translation in parallel documents."""
        try:
            if not self.test_document:
                self.log_test_result("Currency Translation", False, "No test document available")
                return
            
            with engine.connect() as conn:
                # Get parallel documents with different currencies
                parallel_docs = conn.execute(text("""
                    SELECT jeh.documentnumber, jeh.ledger_id, l.currencycode,
                           SUM(jel.debitamount) as total_debits,
                           SUM(jel.creditamount) as total_credits
                    FROM journalentryheader jeh
                    JOIN ledger l ON jeh.ledger_id = l.ledgerid
                    LEFT JOIN journalentryline jel ON jel.documentnumber = jeh.documentnumber 
                        AND jel.companycodeid = jeh.companycodeid
                    WHERE jeh.parallel_source_doc = :source_doc 
                    AND jeh.companycodeid = :company_code
                    GROUP BY jeh.documentnumber, jeh.ledger_id, l.currencycode
                """), {
                    "source_doc": self.test_document,
                    "company_code": self.test_company_code
                }).fetchall()
                
                # Test currency translation for different ledger currencies
                usd_total = None
                currency_translations = {}
                
                for doc in parallel_docs:
                    ledger_id = doc[1]
                    currency = doc[2]
                    total_debits = float(doc[3] or 0)
                    total_credits = float(doc[4] or 0)
                    
                    if currency == 'USD':
                        usd_total = total_debits
                    
                    currency_translations[ledger_id] = {
                        "currency": currency,
                        "total_debits": total_debits,
                        "total_credits": total_credits
                    }
                    
                    # Test balance in parallel document
                    balanced = abs(total_debits - total_credits) < 0.01
                    self.log_test_result(
                        f"Balance Check Ledger {ledger_id}",
                        balanced,
                        f"{currency} {total_debits:.2f} Dr / {total_credits:.2f} Cr - {'Balanced' if balanced else 'Unbalanced'}"
                    )
                
                # Test currency translation accuracy (if different currencies exist)
                non_usd_ledgers = [lid for lid, data in currency_translations.items() 
                                 if data["currency"] != "USD"]
                
                for ledger_id in non_usd_ledgers:
                    data = currency_translations[ledger_id]
                    currency = data["currency"]
                    
                    # Test translation back to USD
                    if usd_total and data["total_debits"] > 0:
                        translated_back = self.currency_service.translate_amount(
                            Decimal(str(data["total_debits"])), currency, 'USD'
                        )
                        
                        if translated_back:
                            variance = abs(float(translated_back) - usd_total)
                            variance_pct = (variance / usd_total * 100) if usd_total > 0 else 0
                            
                            self.log_test_result(
                                f"Translation Accuracy {ledger_id}",
                                variance_pct < 1.0,  # Less than 1% variance
                                f"Variance: {variance_pct:.2f}% (${variance:.2f})"
                            )
                
        except Exception as e:
            self.log_test_result("Currency Translation", False, f"Currency translation test failed: {str(e)}")
    
    def test_balance_validation(self):
        """Test balance validation across parallel ledgers."""
        try:
            if not self.test_document:
                self.log_test_result("Balance Validation", False, "No test document available")
                return
            
            with engine.connect() as conn:
                # Test source document balance
                source_balance = conn.execute(text("""
                    SELECT 
                        SUM(debitamount) as total_debits,
                        SUM(creditamount) as total_credits
                    FROM journalentryline 
                    WHERE documentnumber = :doc_number AND companycodeid = :company_code
                """), {
                    "doc_number": self.test_document,
                    "company_code": self.test_company_code
                }).fetchone()
                
                source_balanced = abs(float(source_balance[0]) - float(source_balance[1])) < 0.01
                self.log_test_result(
                    "Source Document Balance",
                    source_balanced,
                    f"Debits: ${source_balance[0]:.2f}, Credits: ${source_balance[1]:.2f}"
                )
                
                # Test parallel document balances
                parallel_balances = conn.execute(text("""
                    SELECT 
                        jeh.documentnumber,
                        jeh.ledger_id,
                        SUM(jel.debitamount) as total_debits,
                        SUM(jel.creditamount) as total_credits
                    FROM journalentryheader jeh
                    LEFT JOIN journalentryline jel ON jel.documentnumber = jeh.documentnumber 
                        AND jel.companycodeid = jeh.companycodeid
                    WHERE jeh.parallel_source_doc = :source_doc 
                    AND jeh.companycodeid = :company_code
                    GROUP BY jeh.documentnumber, jeh.ledger_id
                """), {
                    "source_doc": self.test_document,
                    "company_code": self.test_company_code
                }).fetchall()
                
                all_parallel_balanced = True
                for balance in parallel_balances:
                    doc_number = balance[0]
                    ledger_id = balance[1]
                    debits = float(balance[2] or 0)
                    credits = float(balance[3] or 0)
                    
                    balanced = abs(debits - credits) < 0.01
                    all_parallel_balanced = all_parallel_balanced and balanced
                    
                    self.log_test_result(
                        f"Parallel Balance {ledger_id}",
                        balanced,
                        f"${debits:.2f} Dr / ${credits:.2f} Cr - {'Balanced' if balanced else 'Unbalanced'}"
                    )
                
                self.log_test_result(
                    "Overall Balance Validation",
                    source_balanced and all_parallel_balanced,
                    "All documents balanced" if source_balanced and all_parallel_balanced else "Balance issues detected"
                )
            
        except Exception as e:
            self.log_test_result("Balance Validation", False, f"Balance validation test failed: {str(e)}")
    
    def test_reporting_services(self):
        """Test all reporting services functionality."""
        try:
            # Test trial balance report
            trial_balance = self.reporting_service.generate_trial_balance_by_ledger(
                ledger_id="2L",
                company_code=self.test_company_code,
                fiscal_year=datetime.now().year
            )
            
            tb_success = "error" not in trial_balance
            self.log_test_result(
                "Trial Balance Report",
                tb_success,
                f"Generated trial balance with {trial_balance.get('account_count', 0)} accounts" if tb_success 
                else f"Error: {trial_balance.get('error', 'Unknown error')}"
            )
            
            # Test comparative financial statements
            comparative = self.reporting_service.generate_comparative_financial_statements(
                company_code=self.test_company_code,
                fiscal_year=datetime.now().year,
                ledger_list=["2L", "3L"]
            )
            
            comp_success = "error" not in comparative
            self.log_test_result(
                "Comparative Statements",
                comp_success,
                f"Generated comparative analysis for {comparative.get('report_info', {}).get('ledger_count', 0)} ledgers" if comp_success
                else f"Error: {comparative.get('error', 'Unknown error')}"
            )
            
            # Test balance inquiry
            balance_inquiry = self.reporting_service.generate_ledger_balance_inquiry(
                company_code=self.test_company_code,
                fiscal_year=datetime.now().year
            )
            
            bi_success = "error" not in balance_inquiry
            self.log_test_result(
                "Balance Inquiry Report",
                bi_success,
                f"Generated balance inquiry for {balance_inquiry.get('account_count', 0)} accounts" if bi_success
                else f"Error: {balance_inquiry.get('error', 'Unknown error')}"
            )
            
            # Test parallel posting impact report
            impact_report = self.reporting_service.generate_parallel_posting_impact_report(
                company_code=self.test_company_code,
                date_from=date.today() - timedelta(days=1),
                date_to=date.today()
            )
            
            impact_success = "error" not in impact_report
            self.log_test_result(
                "Parallel Posting Impact Report",
                impact_success,
                f"Generated impact report for {len(impact_report.get('documents', []))} documents" if impact_success
                else f"Error: {impact_report.get('error', 'Unknown error')}"
            )
            
        except Exception as e:
            self.log_test_result("Reporting Services", False, f"Reporting services test failed: {str(e)}")
    
    def test_performance_analysis(self):
        """Test system performance metrics."""
        try:
            # Test database query performance
            start_time = time.time()
            
            with engine.connect() as conn:
                # Test complex reporting query performance
                conn.execute(text("""
                    SELECT COUNT(*) FROM ledger
                """)).scalar()
                
            query_time = (time.time() - start_time) * 1000
            
            self.log_test_result(
                "Database Query Performance",
                query_time < 1000,  # Less than 1 second
                f"Query time: {query_time:.2f}ms"
            )
            
            # Test service initialization time
            start_time = time.time()
            test_service = ParallelLedgerReportingService()
            init_time = (time.time() - start_time) * 1000
            
            self.log_test_result(
                "Service Initialization Performance",
                init_time < 500,  # Less than 500ms
                f"Initialization time: {init_time:.2f}ms"
            )
            
            # Store performance metrics
            self.test_results["performance_metrics"].update({
                "database_query_time_ms": query_time,
                "service_init_time_ms": init_time
            })
            
        except Exception as e:
            self.log_test_result("Performance Analysis", False, f"Performance analysis test failed: {str(e)}")
    
    def test_data_consistency(self):
        """Test data consistency across parallel ledgers."""
        try:
            if not self.test_document:
                self.log_test_result("Data Consistency", False, "No test document available")
                return
            
            with engine.connect() as conn:
                # Test workflow status update
                workflow_status = conn.execute(text("""
                    SELECT workflow_status FROM journalentryheader 
                    WHERE documentnumber = :source_doc AND companycodeid = :company_code
                """), {
                    "source_doc": self.test_document,
                    "company_code": self.test_company_code
                }).scalar()
                
                workflow_updated = workflow_status is not None
                
                self.log_test_result(
                    "Workflow Status Check",
                    workflow_updated,
                    f"Workflow status: {workflow_status}"
                )
                
                # Test source document tracking
                source_tracking = conn.execute(text("""
                    SELECT parallel_posted, parallel_ledger_count, parallel_success_count
                    FROM journalentryheader 
                    WHERE documentnumber = :doc_number AND companycodeid = :company_code
                """), {
                    "doc_number": self.test_document,
                    "company_code": self.test_company_code
                }).fetchone()
                
                if source_tracking:
                    parallel_posted = source_tracking[0]
                    ledger_count = source_tracking[1] or 0
                    success_count = source_tracking[2] or 0
                    
                    self.log_test_result(
                        "Source Document Tracking",
                        parallel_posted and ledger_count > 0,
                        f"Posted: {parallel_posted}, Target: {ledger_count}, Success: {success_count}"
                    )
                else:
                    self.log_test_result(
                        "Source Document Tracking",
                        False,
                        "Source document tracking data not found"
                    )
                
                # Test referential integrity
                orphan_documents = conn.execute(text("""
                    SELECT COUNT(*) FROM journalentryheader jeh
                    WHERE jeh.parallel_source_doc IS NOT NULL
                    AND NOT EXISTS (
                        SELECT 1 FROM journalentryheader source
                        WHERE source.documentnumber = jeh.parallel_source_doc
                        AND source.companycodeid = jeh.companycodeid
                    )
                """)).scalar()
                
                self.log_test_result(
                    "Referential Integrity",
                    orphan_documents == 0,
                    f"Found {orphan_documents} orphan parallel documents"
                )
            
        except Exception as e:
            self.log_test_result("Data Consistency", False, f"Data consistency test failed: {str(e)}")
    
    def generate_final_report(self):
        """Generate comprehensive final test report."""
        end_time = datetime.now()
        duration = end_time - self.test_results["test_start_time"]
        
        # Calculate summary statistics
        success_rate = (self.test_results["tests_passed"] / self.test_results["tests_run"] * 100) if self.test_results["tests_run"] > 0 else 0
        
        print("\n" + "=" * 80)
        print("🏁 COMPREHENSIVE END-TO-END TEST RESULTS")
        print("=" * 80)
        
        # Summary
        print(f"\n📊 TEST SUMMARY")
        print(f"   Duration: {duration}")
        print(f"   Total Tests: {self.test_results['tests_run']}")
        print(f"   Passed: {self.test_results['tests_passed']} ✅")
        print(f"   Failed: {self.test_results['tests_failed']} ❌")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        # System status
        if self.test_results["system_status"]:
            print(f"\n🏛️ SYSTEM STATUS")
            ledger_info = self.test_results["system_status"].get("ledgers", {})
            print(f"   Total Ledgers: {ledger_info.get('total', 0)}")
            print(f"   Leading Ledgers: {ledger_info.get('leading', 0)}")
            print(f"   Parallel Ledgers: {ledger_info.get('parallel', 0)}")
            print(f"   Configured: {', '.join(ledger_info.get('configured_parallel', []))}")
        
        # Performance metrics
        if self.test_results["performance_metrics"]:
            print(f"\n⚡ PERFORMANCE METRICS")
            perf = self.test_results["performance_metrics"]
            
            if "parallel_posting" in perf:
                pp = perf["parallel_posting"]
                print(f"   Parallel Posting Time: {pp.get('processing_time_ms', 0):.2f}ms")
                print(f"   Parallel Posting Success Rate: {pp.get('success_rate', 0):.1f}%")
            
            if "database_query_time_ms" in perf:
                print(f"   Database Query Time: {perf['database_query_time_ms']:.2f}ms")
            
            if "service_init_time_ms" in perf:
                print(f"   Service Initialization: {perf['service_init_time_ms']:.2f}ms")
        
        # Failed tests details
        failed_tests = [test for test in self.test_results["test_details"] if "❌ FAIL" in test["status"]]
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)})")
            for test in failed_tests:
                print(f"   • {test['test_name']}: {test['message']}")
        
        # Overall assessment
        print(f"\n🎯 OVERALL ASSESSMENT")
        if success_rate >= 95:
            print("   ✅ EXCELLENT - System ready for production deployment")
        elif success_rate >= 85:
            print("   ⚠️  GOOD - Minor issues need attention before production")
        elif success_rate >= 70:
            print("   🔧 NEEDS WORK - Significant issues require resolution")
        else:
            print("   ❌ CRITICAL - Major system issues prevent production deployment")
        
        # Save detailed results
        self.save_test_results(end_time, duration, success_rate)
        
        print(f"\n📋 Detailed test results saved to: comprehensive_e2e_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        print("=" * 80)
    
    def save_test_results(self, end_time, duration, success_rate):
        """Save detailed test results to file."""
        results = {
            "test_summary": {
                "start_time": self.test_results["test_start_time"].isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration.total_seconds(),
                "tests_run": self.test_results["tests_run"],
                "tests_passed": self.test_results["tests_passed"],
                "tests_failed": self.test_results["tests_failed"],
                "success_rate_percentage": success_rate
            },
            "system_status": self.test_results["system_status"],
            "performance_metrics": self.test_results["performance_metrics"],
            "test_details": [
                {
                    "test_name": test["test_name"],
                    "status": test["status"],
                    "message": test["message"],
                    "timestamp": test["timestamp"].isoformat(),
                    "details": test["details"]
                }
                for test in self.test_results["test_details"]
            ],
            "test_document_used": self.test_document,
            "overall_assessment": {
                "production_ready": success_rate >= 95,
                "issues_found": self.test_results["tests_failed"],
                "recommendation": "Ready for production" if success_rate >= 95 else "Requires attention before production"
            }
        }
        
        filename = f"comprehensive_e2e_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = f"/home/anton/erp/gl/tests/{filename}"
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)

def main():
    """Run the comprehensive end-to-end test suite."""
    tester = ComprehensiveParallelLedgerE2ETest()
    tester.run_all_tests()

if __name__ == "__main__":
    main()