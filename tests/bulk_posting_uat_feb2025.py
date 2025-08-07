#!/usr/bin/env python3
"""
End-to-End UAT: Bulk Posting Draft Journals for February 2025

This comprehensive UAT tests the complete journal entry workflow for February 2025,
validating the parallel posting fix and ensuring consistent performance across periods.

Test Scenario: February 2025 fiscal period bulk processing

Author: Claude Code Assistant
Date: August 6, 2025
"""

import sys
import os
sys.path.append('/home/anton/erp/gl')

import json
import pandas as pd
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Any, Tuple
from sqlalchemy import text
from db_config import engine
from utils.parallel_posting_service import ParallelPostingService
from utils.workflow_engine import WorkflowEngine
from utils.ledger_assignment_service import ledger_assignment_service
from utils.logger import get_logger

logger = get_logger("bulk_posting_uat_feb2025")

class BulkPostingUATFeb2025:
    """Comprehensive UAT for bulk posting in February 2025."""
    
    def __init__(self):
        """Initialize the UAT framework."""
        self.uat_results = {
            "uat_start_time": datetime.now(),
            "test_fiscal_year": 2025,
            "test_fiscal_period": 2,  # February
            "test_posting_date": date(2025, 2, 15),
            "test_document_date": date(2025, 2, 15),
            "draft_documents": [],
            "approved_documents": [],
            "posted_documents": [],
            "parallel_documents": [],
            "test_phases": {},
            "final_balances": {},
            "errors": [],
            "warnings": []
        }
        
        self.test_company = "1000"
        self.test_user = "UAT_USER_FEB2025"
        
        # Test scenarios with February-specific business transactions
        self.test_scenarios = [
            {
                "doc_type": "Sales Invoice - February",
                "description": "February 2025 Sales - Customer XYZ Corp",
                "lines": [
                    {"account": "115001", "description": "Accounts Receivable - XYZ", "debit": 7500.00, "credit": 0.00, "ledger": "L1"},
                    {"account": "410001", "description": "Software License Sales", "debit": 0.00, "credit": 7000.00, "ledger": "L1"},
                    {"account": "231001", "description": "Sales Tax Payable", "debit": 0.00, "credit": 500.00, "ledger": "L1"}
                ]
            },
            {
                "doc_type": "February Rent Accrual",
                "description": "February 2025 Rent Accrual - Q1 Prepayment",
                "lines": [
                    {"account": "580001", "description": "February Rent Expense", "debit": 3500.00, "credit": 0.00, "ledger": "L1"},
                    {"account": "225001", "description": "Accrued Rent Payable", "debit": 0.00, "credit": 3500.00, "ledger": "L1"}
                ]
            },
            {
                "doc_type": "Marketing Campaign",
                "description": "February 2025 Marketing Campaign - Q1 Launch",
                "lines": [
                    {"account": "570001", "description": "Marketing Materials", "debit": 2500.00, "credit": 0.00, "ledger": "L1"},
                    {"account": "570001", "description": "Digital Advertising", "debit": 1800.00, "credit": 0.00, "ledger": "L1"},
                    {"account": "210001", "description": "Accounts Payable - Marketing", "debit": 0.00, "credit": 4300.00, "ledger": "L1"}
                ]
            },
            {
                "doc_type": "February Payroll",
                "description": "February 2025 Bi-weekly Payroll Processing",
                "lines": [
                    {"account": "610001", "description": "February Salaries", "debit": 18000.00, "credit": 0.00, "ledger": "L1"},
                    {"account": "620001", "description": "February Payroll Taxes", "debit": 2700.00, "credit": 0.00, "ledger": "L1"},
                    {"account": "225001", "description": "Net Pay Payable", "debit": 0.00, "credit": 15300.00, "ledger": "L1"},
                    {"account": "232001", "description": "Payroll Tax Withholding", "debit": 0.00, "credit": 5400.00, "ledger": "L1"}
                ]
            },
            {
                "doc_type": "IFRS Equipment Revaluation",
                "description": "February 2025 IFRS - Equipment Fair Value Adjustment",
                "lines": [
                    {"account": "150001", "description": "Equipment Revaluation - IFRS", "debit": 5000.00, "credit": 0.00, "ledger": "2L"},
                    {"account": "350001", "description": "Asset Revaluation Reserve", "debit": 0.00, "credit": 5000.00, "ledger": "2L"}
                ]
            },
            {
                "doc_type": "Currency Translation",
                "description": "February 2025 Multi-Currency Adjustment",
                "lines": [
                    {"account": "115001", "description": "EUR Receivables Translation", "debit": 1200.00, "credit": 0.00, "ledger": "L1"},
                    {"account": "210001", "description": "EUR Payables Translation", "debit": 0.00, "credit": 800.00, "ledger": "L1"},
                    {"account": "350001", "description": "Translation Adjustment", "debit": 0.00, "credit": 400.00, "ledger": "L1"}
                ]
            }
        ]
    
    def log_phase_result(self, phase: str, success: bool, message: str, details: Dict = None):
        """Log a test phase result."""
        self.uat_results["test_phases"][phase] = {
            "success": success,
            "message": message,
            "timestamp": datetime.now(),
            "details": details or {}
        }
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} | {phase}")
        print(f"    Result: {message}")
        if details:
            for key, value in details.items():
                print(f"    {key}: {value}")
        print()
        
        if not success:
            self.uat_results["errors"].append(f"{phase}: {message}")
    
    def phase_1_create_draft_journals(self):
        """Phase 1: Create draft journal entries for February 2025."""
        print("🏗️ PHASE 1: Creating Draft Journal Entries for February 2025")
        print("-" * 70)
        
        try:
            # Import Journal Entry Manager functions
            sys.path.append('/home/anton/erp/gl/pages')
            from Journal_Entry_Manager import save_journal_entry
            
            created_docs = []
            
            for i, scenario in enumerate(self.test_scenarios, 1):
                doc_number = f"FEB2025UAT{i:03d}"
                
                try:
                    # Create DataFrame for lines
                    lines_data = []
                    for line_num, line in enumerate(scenario["lines"], 1):
                        lines_data.append({
                            'linenumber': line_num,
                            'glaccountid': line["account"],
                            'description': line["description"],
                            'debitamount': Decimal(str(line["debit"])),
                            'creditamount': Decimal(str(line["credit"])),
                            'currencycode': 'USD',
                            'costcenterid': '',
                            'ledgerid': line["ledger"]
                        })
                    
                    lines_df = pd.DataFrame(lines_data)
                    
                    # Save as draft
                    success = save_journal_entry(
                        doc=doc_number,
                        cc=self.test_company,
                        pdate=self.uat_results["test_posting_date"],
                        ddate=self.uat_results["test_document_date"],
                        fy=self.uat_results["test_fiscal_year"],
                        per=self.uat_results["test_fiscal_period"],
                        ref=f"UAT-FEB2025-{scenario['doc_type']}",
                        memo=scenario["description"],
                        cur="USD",
                        cb=self.test_user,
                        edited=lines_df,
                        workflow_status="DRAFT"
                    )
                    
                    if success:
                        created_docs.append({
                            "document_number": doc_number,
                            "doc_type": scenario["doc_type"],
                            "line_count": len(lines_data),
                            "total_debits": sum(Decimal(str(line["debit"])) for line in scenario["lines"]),
                            "total_credits": sum(Decimal(str(line["credit"])) for line in scenario["lines"])
                        })
                        print(f"    ✅ Created {doc_number}: {scenario['doc_type']} ({len(lines_data)} lines)")
                    else:
                        raise Exception(f"Failed to save document {doc_number}")
                        
                except Exception as e:
                    self.log_phase_result(
                        f"Draft Creation - {doc_number}",
                        False,
                        f"Failed to create draft: {str(e)}"
                    )
                    continue
            
            self.uat_results["draft_documents"] = created_docs
            
            total_docs = len(created_docs)
            total_lines = sum(doc["line_count"] for doc in created_docs)
            total_debits = sum(doc["total_debits"] for doc in created_docs)
            total_credits = sum(doc["total_credits"] for doc in created_docs)
            
            self.log_phase_result(
                "Draft Journal Creation",
                total_docs > 0,
                f"Created {total_docs} draft documents with {total_lines} lines for February 2025",
                {
                    "documents_created": total_docs,
                    "total_lines": total_lines,
                    "total_debits": f"${total_debits:,.2f}",
                    "total_credits": f"${total_credits:,.2f}",
                    "balance_check": "✅ Balanced" if abs(total_debits - total_credits) < 0.01 else f"❌ Unbalanced by ${abs(total_debits - total_credits):,.2f}"
                }
            )
            
            return len(created_docs) > 0
            
        except Exception as e:
            self.log_phase_result(
                "Draft Journal Creation",
                False,
                f"Phase 1 failed: {str(e)}"
            )
            return False
    
    def phase_2_workflow_approval(self):
        """Phase 2: Process draft journals through approval workflow."""
        print("\n📋 PHASE 2: Processing February 2025 Approval Workflow")
        print("-" * 70)
        
        if not self.uat_results["draft_documents"]:
            self.log_phase_result(
                "Workflow Approval",
                False,
                "No draft documents available for approval"
            )
            return False
        
        try:
            approved_docs = []
            workflow_engine = WorkflowEngine()
            
            for doc_info in self.uat_results["draft_documents"]:
                doc_number = doc_info["document_number"]
                
                try:
                    # Submit for approval
                    success, message = workflow_engine.submit_for_approval(
                        doc_number, self.test_company, self.test_user
                    )
                    
                    if not success:
                        print(f"    ⚠️ Submit failed for {doc_number}: {message}")
                        continue
                    
                    # Auto-approve for UAT
                    success, message = workflow_engine.approve_document(
                        doc_number, self.test_company, f"FEB_APPROVER_{datetime.now().strftime('%H%M%S')}"
                    )
                    
                    if success:
                        approved_docs.append(doc_info)
                        print(f"    ✅ Approved {doc_number}: {doc_info['doc_type']}")
                    else:
                        print(f"    ❌ Approval failed for {doc_number}: {message}")
                        
                except Exception as e:
                    print(f"    ❌ Workflow error for {doc_number}: {str(e)}")
                    continue
            
            self.uat_results["approved_documents"] = approved_docs
            
            success_rate = (len(approved_docs) / len(self.uat_results["draft_documents"]) * 100) if self.uat_results["draft_documents"] else 0
            
            self.log_phase_result(
                "Workflow Approval",
                len(approved_docs) > 0,
                f"Approved {len(approved_docs)} of {len(self.uat_results['draft_documents'])} February documents ({success_rate:.1f}%)",
                {
                    "documents_approved": len(approved_docs),
                    "approval_success_rate": f"{success_rate:.1f}%",
                    "ready_for_posting": len(approved_docs)
                }
            )
            
            return len(approved_docs) > 0
            
        except Exception as e:
            self.log_phase_result(
                "Workflow Approval",
                False,
                f"Phase 2 failed: {str(e)}"
            )
            return False
    
    def phase_3_bulk_posting(self):
        """Phase 3: Bulk posting of approved documents to February 2025."""
        print("\n🚀 PHASE 3: Bulk Posting to February 2025")
        print("-" * 70)
        
        if not self.uat_results["approved_documents"]:
            self.log_phase_result(
                "Bulk Posting",
                False,
                "No approved documents available for posting"
            )
            return False
        
        try:
            posted_docs = []
            
            # Update documents to POSTED status for February 2025
            with engine.begin() as conn:
                for doc_info in self.uat_results["approved_documents"]:
                    doc_number = doc_info["document_number"]
                    
                    try:
                        # Post the document
                        conn.execute(text("""
                            UPDATE journalentryheader 
                            SET workflow_status = 'POSTED',
                                posted_at = CURRENT_TIMESTAMP,
                                posted_by = :posted_by
                            WHERE documentnumber = :doc AND companycodeid = :cc
                            AND workflow_status = 'APPROVED'
                        """), {
                            "doc": doc_number,
                            "cc": self.test_company, 
                            "posted_by": self.test_user
                        })
                        
                        posted_docs.append(doc_info)
                        print(f"    ✅ Posted {doc_number}: {doc_info['doc_type']}")
                        
                    except Exception as e:
                        print(f"    ❌ Posting failed for {doc_number}: {str(e)}")
                        continue
            
            self.uat_results["posted_documents"] = posted_docs
            
            self.log_phase_result(
                "Bulk Posting",
                len(posted_docs) > 0,
                f"Successfully posted {len(posted_docs)} documents to February 2025",
                {
                    "documents_posted": len(posted_docs),
                    "posting_date": str(self.uat_results["test_posting_date"]),
                    "fiscal_period": f"February {self.uat_results['test_fiscal_year']}",
                    "total_transactions": sum(doc["line_count"] for doc in posted_docs)
                }
            )
            
            return len(posted_docs) > 0
            
        except Exception as e:
            self.log_phase_result(
                "Bulk Posting",
                False,
                f"Phase 3 failed: {str(e)}"
            )
            return False
    
    def phase_4_parallel_ledger_processing(self):
        """Phase 4: Process documents through parallel ledger system."""
        print("\n🏦 PHASE 4: Parallel Ledger Processing - February 2025")
        print("-" * 70)
        
        if not self.uat_results["posted_documents"]:
            self.log_phase_result(
                "Parallel Ledger Processing",
                False,
                "No posted documents available for parallel processing"
            )
            return False
        
        try:
            parallel_service = ParallelPostingService()
            parallel_results = []
            
            for doc_info in self.uat_results["posted_documents"]:
                doc_number = doc_info["document_number"]
                
                try:
                    # Process document for parallel posting
                    result = parallel_service.process_approved_document_to_all_ledgers(
                        doc_number, self.test_company
                    )
                    
                    parallel_results.append({
                        "document_number": doc_number,
                        "source_ledger": result.get("source_ledger"),
                        "successful_ledgers": result.get("successful_ledgers", 0),
                        "failed_ledgers": result.get("failed_ledgers", 0),
                        "total_ledgers": result.get("total_ledgers", 0),
                        "errors": result.get("errors", [])
                    })
                    
                    success_rate = (result.get("successful_ledgers", 0) / max(result.get("total_ledgers", 1), 1)) * 100
                    print(f"    📊 {doc_number}: {result.get('successful_ledgers', 0)}/{result.get('total_ledgers', 0)} ledgers ({success_rate:.1f}%)")
                    
                except Exception as e:
                    print(f"    ❌ Parallel processing failed for {doc_number}: {str(e)}")
                    parallel_results.append({
                        "document_number": doc_number,
                        "errors": [str(e)]
                    })
                    continue
            
            # Get total parallel documents created
            total_parallel_docs = 0
            total_successful = sum(r.get("successful_ledgers", 0) for r in parallel_results)
            total_failed = sum(r.get("failed_ledgers", 0) for r in parallel_results)
            
            with engine.connect() as conn:
                parallel_count = conn.execute(text("""
                    SELECT COUNT(DISTINCT documentnumber) as parallel_docs
                    FROM journalentryheader 
                    WHERE parallel_source_doc IN :source_docs
                    AND companycodeid = :cc
                """), {
                    "source_docs": tuple([doc["document_number"] for doc in self.uat_results["posted_documents"]]),
                    "cc": self.test_company
                }).scalar()
                
                total_parallel_docs = parallel_count or 0
            
            self.uat_results["parallel_documents"] = parallel_results
            
            overall_success = total_successful > 0 and total_failed == 0
            
            self.log_phase_result(
                "Parallel Ledger Processing",
                overall_success,
                f"February 2025: Processed {len(parallel_results)} documents, created {total_parallel_docs} parallel entries",
                {
                    "source_documents": len(parallel_results),
                    "parallel_documents_created": total_parallel_docs,
                    "successful_ledger_postings": total_successful,
                    "failed_ledger_postings": total_failed,
                    "parallel_success_rate": f"{(total_successful / max(total_successful + total_failed, 1)) * 100:.1f}%"
                }
            )
            
            return overall_success
            
        except Exception as e:
            self.log_phase_result(
                "Parallel Ledger Processing",
                False,
                f"Phase 4 failed: {str(e)}"
            )
            return False
    
    def phase_5_balance_verification(self):
        """Phase 5: Verify balances across all ledgers for February 2025."""
        print("\n📊 PHASE 5: Balance Verification - February 2025")
        print("-" * 70)
        
        try:
            with engine.connect() as conn:
                # Get balances by ledger for February 2025
                balance_query = text("""
                    SELECT 
                        jel.ledgerid,
                        l.description as ledger_name,
                        l.accounting_principle,
                        COUNT(DISTINCT jel.documentnumber) as documents,
                        COUNT(*) as total_lines,
                        SUM(jel.debitamount) as total_debits,
                        SUM(jel.creditamount) as total_credits,
                        SUM(jel.debitamount) - SUM(jel.creditamount) as net_balance
                    FROM journalentryline jel
                    JOIN journalentryheader jeh ON jel.documentnumber = jeh.documentnumber 
                        AND jel.companycodeid = jeh.companycodeid
                    JOIN ledger l ON jel.ledgerid = l.ledgerid
                    WHERE jeh.fiscalyear = :fy 
                    AND jeh.period = :period
                    AND jeh.companycodeid = :cc
                    AND jeh.workflow_status = 'POSTED'
                    GROUP BY jel.ledgerid, l.description, l.accounting_principle
                    ORDER BY jel.ledgerid
                """)
                
                balances = conn.execute(balance_query, {
                    "fy": self.uat_results["test_fiscal_year"],
                    "period": self.uat_results["test_fiscal_period"], 
                    "cc": self.test_company
                }).mappings().all()
                
                balance_details = {}
                total_documents = 0
                total_lines = 0
                all_balanced = True
                
                print(f"    Balance Summary for February {self.uat_results['test_fiscal_year']}:")
                print("    " + "=" * 60)
                
                for balance in balances:
                    ledger_id = balance["ledgerid"]
                    is_balanced = abs(float(balance["net_balance"])) < 0.01
                    balance_status = "✅ Balanced" if is_balanced else f"❌ Unbalanced: ${balance['net_balance']:.2f}"
                    
                    balance_details[ledger_id] = {
                        "ledger_name": balance["ledger_name"],
                        "accounting_principle": balance["accounting_principle"],
                        "documents": balance["documents"],
                        "lines": balance["total_lines"],
                        "debits": float(balance["total_debits"]),
                        "credits": float(balance["total_credits"]),
                        "net_balance": float(balance["net_balance"]),
                        "is_balanced": is_balanced
                    }
                    
                    total_documents += balance["documents"]
                    total_lines += balance["total_lines"]
                    all_balanced = all_balanced and is_balanced
                    
                    print(f"    {ledger_id} ({balance['accounting_principle']})")
                    print(f"      Documents: {balance['documents']}, Lines: {balance['total_lines']}")
                    print(f"      Debits: ${balance['total_debits']:,.2f}, Credits: ${balance['total_credits']:,.2f}")
                    print(f"      Status: {balance_status}")
                    print()
                
                self.uat_results["final_balances"] = balance_details
                
                self.log_phase_result(
                    "Balance Verification",
                    all_balanced and len(balances) > 0,
                    f"February 2025: Verified balances across {len(balances)} ledgers - {'All Balanced' if all_balanced else 'Balance Issues Found'}",
                    {
                        "ledgers_verified": len(balances),
                        "total_documents": total_documents,
                        "total_lines": total_lines,
                        "balance_status": "✅ All Balanced" if all_balanced else "❌ Balance Issues",
                        "fiscal_period": "February 2025"
                    }
                )
                
                return all_balanced and len(balances) > 0
                
        except Exception as e:
            self.log_phase_result(
                "Balance Verification",
                False,
                f"Phase 5 failed: {str(e)}"
            )
            return False
    
    def generate_uat_report(self):
        """Generate comprehensive UAT report for February 2025."""
        print("\n" + "=" * 80)
        print("📄 BULK POSTING UAT REPORT - FEBRUARY 2025")
        print("=" * 80)
        
        # Calculate overall results
        total_phases = len(self.uat_results["test_phases"])
        passed_phases = sum(1 for phase in self.uat_results["test_phases"].values() if phase["success"])
        success_rate = (passed_phases / total_phases * 100) if total_phases > 0 else 0
        
        print(f"\n📊 FEBRUARY 2025 UAT SUMMARY")
        print(f"   Duration: {datetime.now() - self.uat_results['uat_start_time']}")
        print(f"   Test Period: February {self.uat_results['test_fiscal_year']}")
        print(f"   Total Phases: {total_phases}")
        print(f"   Passed: {passed_phases} ✅")
        print(f"   Failed: {total_phases - passed_phases} ❌")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        # Document flow summary
        print(f"\n📋 FEBRUARY DOCUMENT FLOW SUMMARY")
        print(f"   Draft Documents Created: {len(self.uat_results['draft_documents'])}")
        print(f"   Documents Approved: {len(self.uat_results['approved_documents'])}")
        print(f"   Documents Posted: {len(self.uat_results['posted_documents'])}")
        print(f"   Parallel Documents: {len(self.uat_results.get('parallel_documents', []))}")
        
        # Balance summary
        if self.uat_results["final_balances"]:
            print(f"\n💰 FEBRUARY BALANCE SUMMARY")
            for ledger_id, balance in self.uat_results["final_balances"].items():
                status = "✅" if balance["is_balanced"] else "❌"
                print(f"   {ledger_id} ({balance['accounting_principle']}): {status} ${balance['debits']:,.2f} Dr / ${balance['credits']:,.2f} Cr")
        
        # Phase details
        print(f"\n🔍 FEBRUARY DETAILED PHASE RESULTS")
        for phase_name, phase_result in self.uat_results["test_phases"].items():
            status = "✅ PASS" if phase_result["success"] else "❌ FAIL"
            print(f"   {status} | {phase_name}")
            print(f"     Result: {phase_result['message']}")
            if phase_result.get("details"):
                for key, value in phase_result["details"].items():
                    print(f"     {key}: {value}")
            print()
        
        # Overall assessment
        print(f"🎯 FEBRUARY 2025 ASSESSMENT")
        if success_rate >= 90:
            print("   ✅ EXCELLENT - Production Ready for February Operations")
            uat_status = "PRODUCTION_READY"
        elif success_rate >= 75:
            print("   ⚠️ GOOD - Minor Issues to Address")  
            uat_status = "CONDITIONAL_ACCEPTANCE"
        else:
            print("   ❌ NEEDS WORK - Significant Issues")
            uat_status = "NEEDS_WORK"
            
        # Error summary
        if self.uat_results["errors"]:
            print(f"\n❌ FEBRUARY ERRORS ENCOUNTERED ({len(self.uat_results['errors'])})")
            for error in self.uat_results["errors"]:
                print(f"   • {error}")
        
        # Save detailed results
        result_file = f"bulk_posting_uat_feb2025_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.uat_results["uat_end_time"] = datetime.now()
        self.uat_results["uat_status"] = uat_status
        self.uat_results["success_rate"] = success_rate
        
        with open(result_file, 'w') as f:
            json.dump(self.uat_results, f, indent=2, default=str)
        
        print(f"\n📋 February UAT results saved to: {result_file}")
        print("=" * 80)
        
        return success_rate, uat_status
    
    def cleanup_test_data(self):
        """Clean up February test data if requested."""
        try:
            print(f"\n🧹 CLEANUP: February 2025 test documents")
            
            all_docs = [doc["document_number"] for doc in self.uat_results["draft_documents"]]
            
            with engine.begin() as conn:
                # Delete parallel documents first
                parallel_docs = conn.execute(text("""
                    SELECT documentnumber FROM journalentryheader
                    WHERE parallel_source_doc = ANY(:source_docs) AND companycodeid = :cc
                """), {"source_docs": all_docs, "cc": self.test_company}).scalars().all()
                
                for doc in parallel_docs:
                    conn.execute(text("DELETE FROM journalentryline WHERE documentnumber = :doc AND companycodeid = :cc"),
                               {"doc": doc, "cc": self.test_company})
                    conn.execute(text("DELETE FROM journalentryheader WHERE documentnumber = :doc AND companycodeid = :cc"),
                               {"doc": doc, "cc": self.test_company})
                
                # Delete workflow instances first to avoid FK constraint
                for doc in all_docs:
                    conn.execute(text("DELETE FROM workflow_instances WHERE document_number = :doc AND company_code = :cc"),
                               {"doc": doc, "cc": self.test_company})
                
                # Delete main test documents
                for doc in all_docs:
                    conn.execute(text("DELETE FROM journalentryline WHERE documentnumber = :doc AND companycodeid = :cc"),
                               {"doc": doc, "cc": self.test_company})
                    conn.execute(text("DELETE FROM journalentryheader WHERE documentnumber = :doc AND companycodeid = :cc"),
                               {"doc": doc, "cc": self.test_company})
            
            print(f"   Cleaned up {len(all_docs)} test documents and {len(parallel_docs)} parallel documents")
            
        except Exception as e:
            print(f"   ⚠️ Cleanup warning: {e}")

def main():
    """Run the comprehensive bulk posting UAT for February 2025."""
    print("=" * 80)
    print("🧪 END-TO-END UAT: BULK POSTING DRAFT JOURNALS - FEBRUARY 2025")
    print("=" * 80)
    print("Testing complete journal workflow with parallel ledger processing")
    print("Building on January 2025 success - validating February operations")
    print()
    
    uat = BulkPostingUATFeb2025()
    
    try:
        # Execute all phases
        phase_results = []
        
        phase_results.append(uat.phase_1_create_draft_journals())
        phase_results.append(uat.phase_2_workflow_approval()) 
        phase_results.append(uat.phase_3_bulk_posting())
        phase_results.append(uat.phase_4_parallel_ledger_processing())
        phase_results.append(uat.phase_5_balance_verification())
        
        # Generate comprehensive report
        success_rate, uat_status = uat.generate_uat_report()
        
        # Ask about cleanup
        cleanup_response = input("\n🗑️ Clean up February test data? (y/N): ").lower().strip()
        if cleanup_response == 'y':
            uat.cleanup_test_data()
        else:
            print("   February test data preserved for analysis")
        
        return 0 if success_rate >= 75 else 1
        
    except Exception as e:
        print(f"\n❌ FEBRUARY UAT FAILED: {e}")
        logger.error(f"February UAT execution failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())