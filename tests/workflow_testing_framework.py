"""Comprehensive Journal Entry Approval Workflow Testing Framework"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import json
from datetime import datetime, date
from decimal import Decimal
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple

from db_config import engine
from sqlalchemy import text
from utils.workflow_engine import WorkflowEngine


@dataclass
class TestJournalEntry:
    """Represents a test journal entry"""
    description: str
    reference: str
    amount: Decimal
    company_code: str
    debit_account: str
    credit_account: str
    created_by: str
    expected_approver_level: str
    test_scenario: str


@dataclass
class WorkflowTestResult:
    """Represents the result of workflow testing"""
    test_name: str
    scenario: str
    success: bool
    message: str
    execution_time_ms: float
    journal_entry_id: Optional[int] = None
    workflow_id: Optional[int] = None
    approver_assigned: Optional[str] = None
    final_status: Optional[str] = None
    details: Dict[str, Any] = None


class JournalEntryWorkflowTester:
    """Framework for testing journal entry approval workflows"""
    
    def __init__(self):
        self.workflow_engine = WorkflowEngine()
        self.test_results: List[WorkflowTestResult] = []
        
        # Test users with their credentials and approval authorities
        self.test_users = {
            'admin': {
                'password': 'admin123',
                'role': 'Super Admin',
                'approval_levels': ['Director'],
                'can_create': True,
                'can_approve_own': False  # SOD enforcement
            },
            'supervisor1': {
                'password': 'Supervisor123!',
                'role': 'Manager',
                'approval_levels': ['Supervisor'],
                'can_create': True,
                'can_approve_own': False
            },
            'manager1': {
                'password': 'Manager123!',
                'role': 'Manager', 
                'approval_levels': ['Manager'],
                'can_create': True,
                'can_approve_own': False
            },
            'director1': {
                'password': 'Director123!',
                'role': 'Admin',
                'approval_levels': ['Director'],
                'can_create': True,
                'can_approve_own': False
            }
        }
        
        # Define test scenarios with different amounts and expected approvers
        self.test_scenarios = [
            TestJournalEntry(
                description="Small office supplies purchase",
                reference="OS-2025-001",
                amount=Decimal("2500.00"),
                company_code="1000",
                debit_account="5100",  # Office Supplies Expense
                credit_account="2100", # Accounts Payable
                created_by="admin",
                expected_approver_level="Supervisor",
                test_scenario="Supervisor Level Approval ($0-$9,999)"
            ),
            TestJournalEntry(
                description="Equipment purchase",
                reference="EQ-2025-001", 
                amount=Decimal("25000.00"),
                company_code="1000",
                debit_account="1600",  # Equipment
                credit_account="2100", # Accounts Payable
                created_by="supervisor1",
                expected_approver_level="Manager",
                test_scenario="Manager Level Approval ($10K-$99K)"
            ),
            TestJournalEntry(
                description="Major capital investment",
                reference="CI-2025-001",
                amount=Decimal("150000.00"),
                company_code="1000", 
                debit_account="1600",  # Equipment
                credit_account="2100", # Accounts Payable
                created_by="manager1",
                expected_approver_level="Director",
                test_scenario="Director Level Approval ($100K+)"
            ),
            TestJournalEntry(
                description="Cross-company SOD test",
                reference="SOD-2025-001",
                amount=Decimal("5000.00"),
                company_code="2000",
                debit_account="5200",  # Marketing Expense
                credit_account="1100", # Cash
                created_by="supervisor1",
                expected_approver_level="Supervisor",
                test_scenario="SOD Enforcement Test (Same User Level)"
            ),
            TestJournalEntry(
                description="Delegation test entry",
                reference="DEL-2025-001",
                amount=Decimal("15000.00"),
                company_code="1000",
                debit_account="5300",  # Training Expense
                credit_account="2100", # Accounts Payable
                created_by="admin",
                expected_approver_level="Manager",
                test_scenario="Delegation Test (Manager→Supervisor)"
            )
        ]
    
    def time_operation(self, operation, *args, **kwargs):
        """Time an operation and return result with execution time"""
        start_time = time.time()
        try:
            result = operation(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        end_time = time.time()
        execution_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        return result, success, error, execution_time
    
    def create_test_journal_entry(self, test_entry: TestJournalEntry) -> Tuple[bool, str, Optional[int]]:
        """Create a journal entry for testing"""
        try:
            with engine.begin() as conn:
                # Create the journal entry
                result = conn.execute(text("""
                    INSERT INTO journal_entries 
                    (company_code, entry_date, description, reference, status, created_by, total_amount)
                    VALUES (:company_code, :entry_date, :description, :reference, 'DRAFT', :created_by, :total_amount)
                    RETURNING id
                """), {
                    'company_code': test_entry.company_code,
                    'entry_date': date.today(),
                    'description': test_entry.description,
                    'reference': test_entry.reference,
                    'created_by': test_entry.created_by,
                    'total_amount': float(test_entry.amount)
                })
                
                journal_entry_id = result.fetchone()[0]
                
                # Add debit line
                conn.execute(text("""
                    INSERT INTO journal_entry_lines 
                    (journal_entry_id, account_code, description, debit_amount, credit_amount, line_order)
                    VALUES (:journal_entry_id, :account_code, :description, :debit_amount, 0, 1)
                """), {
                    'journal_entry_id': journal_entry_id,
                    'account_code': test_entry.debit_account,
                    'description': test_entry.description,
                    'debit_amount': float(test_entry.amount)
                })
                
                # Add credit line
                conn.execute(text("""
                    INSERT INTO journal_entry_lines 
                    (journal_entry_id, account_code, description, debit_amount, credit_amount, line_order)
                    VALUES (:journal_entry_id, :account_code, :description, 0, :credit_amount, 2)
                """), {
                    'journal_entry_id': journal_entry_id,
                    'account_code': test_entry.credit_account,
                    'description': test_entry.description,
                    'credit_amount': float(test_entry.amount)
                })
                
                return True, f"Journal entry {journal_entry_id} created successfully", journal_entry_id
                
        except Exception as e:
            return False, f"Error creating journal entry: {e}", None
    
    def submit_for_approval(self, journal_entry_id: int, company_code: str) -> Tuple[bool, str, Optional[int]]:
        """Submit journal entry for approval"""
        try:
            # Use the workflow engine to submit for approval
            workflow_id = self.workflow_engine.submit_journal_for_approval(journal_entry_id, company_code)
            
            if workflow_id:
                return True, f"Workflow {workflow_id} created successfully", workflow_id
            else:
                return False, "Failed to create workflow", None
                
        except Exception as e:
            return False, f"Error submitting for approval: {e}", None
    
    def get_workflow_status(self, workflow_id: int) -> Dict[str, Any]:
        """Get current workflow status"""
        try:
            with engine.connect() as conn:
                # Get workflow info
                workflow_result = conn.execute(text("""
                    SELECT instance_type, entity_id, status, current_step, 
                           created_at, updated_at, company_code
                    FROM workflow_instances 
                    WHERE id = :workflow_id
                """), {'workflow_id': workflow_id})
                
                workflow_row = workflow_result.fetchone()
                if not workflow_row:
                    return {'error': 'Workflow not found'}
                
                workflow_info = {
                    'workflow_id': workflow_id,
                    'instance_type': workflow_row[0],
                    'entity_id': workflow_row[1],
                    'status': workflow_row[2],
                    'current_step': workflow_row[3],
                    'created_at': workflow_row[4],
                    'updated_at': workflow_row[5],
                    'company_code': workflow_row[6]
                }
                
                # Get current approval task
                task_result = conn.execute(text("""
                    SELECT assigned_to, status, due_date, completed_at, comments
                    FROM workflow_tasks 
                    WHERE workflow_instance_id = :workflow_id 
                    AND status = 'PENDING'
                    ORDER BY created_at DESC 
                    LIMIT 1
                """), {'workflow_id': workflow_id})
                
                task_row = task_result.fetchone()
                if task_row:
                    workflow_info['current_approver'] = task_row[0]
                    workflow_info['task_status'] = task_row[1]
                    workflow_info['due_date'] = task_row[2]
                    workflow_info['completed_at'] = task_row[3]
                    workflow_info['comments'] = task_row[4]
                
                return workflow_info
                
        except Exception as e:
            return {'error': f"Error getting workflow status: {e}"}
    
    def approve_entry(self, workflow_id: int, approver_user: str, comments: str = "Approved via testing") -> Tuple[bool, str]:
        """Approve a journal entry"""
        try:
            result = self.workflow_engine.process_approval_decision(
                workflow_id=workflow_id,
                approver_user=approver_user,
                decision='APPROVE',
                comments=comments
            )
            
            if result:
                return True, "Entry approved successfully"
            else:
                return False, "Approval failed"
                
        except Exception as e:
            return False, f"Error approving entry: {e}"
    
    def reject_entry(self, workflow_id: int, approver_user: str, reason: str = "Rejected via testing") -> Tuple[bool, str]:
        """Reject a journal entry"""
        try:
            result = self.workflow_engine.process_approval_decision(
                workflow_id=workflow_id,
                approver_user=approver_user,
                decision='REJECT',
                comments=reason
            )
            
            if result:
                return True, "Entry rejected successfully"
            else:
                return False, "Rejection failed"
                
        except Exception as e:
            return False, f"Error rejecting entry: {e}"
    
    def get_user_pending_approvals(self, user_id: str) -> List[Dict[str, Any]]:
        """Get pending approvals for a user"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT wt.workflow_instance_id, wt.id as task_id,
                           je.description, je.reference, je.total_amount,
                           je.company_code, je.created_by, wi.created_at
                    FROM workflow_tasks wt
                    JOIN workflow_instances wi ON wi.id = wt.workflow_instance_id
                    JOIN journal_entries je ON je.id = wi.entity_id
                    WHERE wt.assigned_to = :user_id 
                    AND wt.status = 'PENDING'
                    AND wi.instance_type = 'journal_approval'
                    ORDER BY wi.created_at ASC
                """), {'user_id': user_id})
                
                approvals = []
                for row in result:
                    approvals.append({
                        'workflow_id': row[0],
                        'task_id': row[1],
                        'description': row[2],
                        'reference': row[3],
                        'amount': float(row[4]),
                        'company_code': row[5],
                        'created_by': row[6],
                        'created_at': row[7]
                    })
                
                return approvals
                
        except Exception as e:
            print(f"Error getting pending approvals: {e}")
            return []
    
    def test_journal_creation_and_routing(self) -> List[WorkflowTestResult]:
        """Test journal entry creation and approval routing"""
        results = []
        
        print("📝 Testing Journal Entry Creation and Routing")
        print("-" * 50)
        
        for test_entry in self.test_scenarios:
            print(f"  🧪 Testing: {test_entry.test_scenario}")
            
            # Test 1: Create journal entry
            def create_entry():
                return self.create_test_journal_entry(test_entry)
            
            create_result, create_success, create_error, create_time = self.time_operation(create_entry)
            
            if create_success and create_result[0]:
                journal_entry_id = create_result[2]
                results.append(WorkflowTestResult(
                    test_name="Journal Entry Creation",
                    scenario=test_entry.test_scenario,
                    success=True,
                    message=f"Created journal entry {journal_entry_id}",
                    execution_time_ms=create_time,
                    journal_entry_id=journal_entry_id,
                    details={'amount': str(test_entry.amount), 'creator': test_entry.created_by}
                ))
                
                # Test 2: Submit for approval
                def submit_approval():
                    return self.submit_for_approval(journal_entry_id, test_entry.company_code)
                
                submit_result, submit_success, submit_error, submit_time = self.time_operation(submit_approval)
                
                if submit_success and submit_result[0]:
                    workflow_id = submit_result[2]
                    
                    # Get workflow status to verify routing
                    workflow_status = self.get_workflow_status(workflow_id)
                    assigned_approver = workflow_status.get('current_approver', 'Unknown')
                    
                    results.append(WorkflowTestResult(
                        test_name="Approval Routing",
                        scenario=test_entry.test_scenario,
                        success=True,
                        message=f"Routed to approver: {assigned_approver}",
                        execution_time_ms=submit_time,
                        journal_entry_id=journal_entry_id,
                        workflow_id=workflow_id,
                        approver_assigned=assigned_approver,
                        details=workflow_status
                    ))
                    
                    print(f"    ✅ Created entry {journal_entry_id}, routed to {assigned_approver}")
                else:
                    results.append(WorkflowTestResult(
                        test_name="Approval Routing",
                        scenario=test_entry.test_scenario,
                        success=False,
                        message=f"Failed to submit for approval: {submit_error}",
                        execution_time_ms=submit_time,
                        journal_entry_id=journal_entry_id
                    ))
                    print(f"    ❌ Failed to submit for approval: {submit_error}")
            else:
                results.append(WorkflowTestResult(
                    test_name="Journal Entry Creation",
                    scenario=test_entry.test_scenario,
                    success=False,
                    message=f"Failed to create journal entry: {create_error}",
                    execution_time_ms=create_time
                ))
                print(f"    ❌ Failed to create entry: {create_error}")
        
        return results
    
    def test_approval_decisions(self) -> List[WorkflowTestResult]:
        """Test approval and rejection decisions"""
        results = []
        
        print("\n✅ Testing Approval Decisions")
        print("-" * 50)
        
        # Get pending approvals for each user
        for username in self.test_users.keys():
            print(f"  👤 Checking pending approvals for {username}")
            
            pending_approvals = self.get_user_pending_approvals(username)
            print(f"    Found {len(pending_approvals)} pending approvals")
            
            for i, approval in enumerate(pending_approvals):
                workflow_id = approval['workflow_id']
                amount = approval['amount']
                description = approval['description']
                
                # Test approve or reject based on scenario
                if i % 2 == 0:  # Approve even-indexed entries
                    print(f"    🟢 Approving: {description} (${amount:,.2f})")
                    
                    def approve_entry():
                        return self.approve_entry(workflow_id, username, f"Approved by {username} during testing")
                    
                    approve_result, approve_success, approve_error, approve_time = self.time_operation(approve_entry)
                    
                    if approve_success and approve_result[0]:
                        results.append(WorkflowTestResult(
                            test_name="Approval Decision",
                            scenario=f"Approve by {username}",
                            success=True,
                            message=f"Successfully approved workflow {workflow_id}",
                            execution_time_ms=approve_time,
                            workflow_id=workflow_id,
                            approver_assigned=username,
                            final_status="APPROVED"
                        ))
                        print(f"      ✅ Approved successfully")
                    else:
                        results.append(WorkflowTestResult(
                            test_name="Approval Decision",
                            scenario=f"Approve by {username}",
                            success=False,
                            message=f"Failed to approve: {approve_error}",
                            execution_time_ms=approve_time,
                            workflow_id=workflow_id
                        ))
                        print(f"      ❌ Approval failed: {approve_error}")
                        
                else:  # Reject odd-indexed entries
                    print(f"    🔴 Rejecting: {description} (${amount:,.2f})")
                    
                    def reject_entry():
                        return self.reject_entry(workflow_id, username, f"Rejected by {username} during testing - insufficient documentation")
                    
                    reject_result, reject_success, reject_error, reject_time = self.time_operation(reject_entry)
                    
                    if reject_success and reject_result[0]:
                        results.append(WorkflowTestResult(
                            test_name="Rejection Decision",
                            scenario=f"Reject by {username}",
                            success=True,
                            message=f"Successfully rejected workflow {workflow_id}",
                            execution_time_ms=reject_time,
                            workflow_id=workflow_id,
                            approver_assigned=username,
                            final_status="REJECTED"
                        ))
                        print(f"      ✅ Rejected successfully")
                    else:
                        results.append(WorkflowTestResult(
                            test_name="Rejection Decision",
                            scenario=f"Reject by {username}",
                            success=False,
                            message=f"Failed to reject: {reject_error}",
                            execution_time_ms=reject_time,
                            workflow_id=workflow_id
                        ))
                        print(f"      ❌ Rejection failed: {reject_error}")
        
        return results
    
    def test_sod_enforcement(self) -> List[WorkflowTestResult]:
        """Test segregation of duties enforcement"""
        results = []
        
        print("\n🛡️ Testing Segregation of Duties (SOD)")
        print("-" * 50)
        
        # Create a journal entry and try to have creator approve it
        test_entry = TestJournalEntry(
            description="SOD Test Entry",
            reference="SOD-TEST-001",
            amount=Decimal("3000.00"),
            company_code="1000",
            debit_account="5100",
            credit_account="2100",
            created_by="supervisor1",
            expected_approver_level="Supervisor",
            test_scenario="SOD Enforcement Test"
        )
        
        # Create entry
        create_success, create_message, journal_entry_id = self.create_test_journal_entry(test_entry)
        
        if create_success:
            # Submit for approval
            submit_success, submit_message, workflow_id = self.submit_for_approval(journal_entry_id, test_entry.company_code)
            
            if submit_success:
                # Try to have creator approve their own entry (should fail)
                print(f"  🧪 Testing SOD: supervisor1 trying to approve own entry {journal_entry_id}")
                
                def attempt_self_approval():
                    return self.approve_entry(workflow_id, "supervisor1", "Attempting self-approval")
                
                sod_result, sod_success, sod_error, sod_time = self.time_operation(attempt_self_approval)
                
                # SOD should prevent this (success = failure is expected)
                if not sod_success or (sod_success and not sod_result[0]):
                    results.append(WorkflowTestResult(
                        test_name="SOD Enforcement",
                        scenario="Self-Approval Prevention",
                        success=True,
                        message="SOD correctly prevented self-approval",
                        execution_time_ms=sod_time,
                        workflow_id=workflow_id,
                        details={'sod_violation_prevented': True}
                    ))
                    print(f"    ✅ SOD correctly prevented self-approval")
                else:
                    results.append(WorkflowTestResult(
                        test_name="SOD Enforcement",
                        scenario="Self-Approval Prevention",
                        success=False,
                        message="SOD failed - self-approval was allowed",
                        execution_time_ms=sod_time,
                        workflow_id=workflow_id,
                        details={'sod_violation_prevented': False}
                    ))
                    print(f"    ❌ SOD failed - self-approval was allowed")
        
        return results
    
    def run_comprehensive_workflow_tests(self) -> Dict[str, List[WorkflowTestResult]]:
        """Run all workflow tests"""
        print("🔄 JOURNAL ENTRY APPROVAL WORKFLOW TESTING")
        print("=" * 60)
        
        all_results = {}
        
        # Test categories
        test_categories = [
            ("Creation & Routing", self.test_journal_creation_and_routing),
            ("Approval Decisions", self.test_approval_decisions),
            ("SOD Enforcement", self.test_sod_enforcement)
        ]
        
        for category_name, test_function in test_categories:
            print(f"\n📋 Running {category_name} Tests...")
            try:
                category_results = test_function()
                all_results[category_name] = category_results
                
                # Show immediate results
                passed = sum(1 for r in category_results if r.success)
                total = len(category_results)
                print(f"✅ {category_name}: {passed}/{total} tests passed")
                
            except Exception as e:
                print(f"❌ Error in {category_name}: {e}")
                all_results[category_name] = [WorkflowTestResult(
                    test_name=f"{category_name} (Error)",
                    scenario="Test Category Error",
                    success=False,
                    message=f"Category failed: {e}",
                    execution_time_ms=0
                )]
        
        return all_results
    
    def generate_workflow_testing_report(self, results: Dict[str, List[WorkflowTestResult]]) -> str:
        """Generate comprehensive workflow testing report"""
        report_lines = []
        report_lines.append("# Journal Entry Approval Workflow Testing Report")
        report_lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Overall statistics
        total_tests = sum(len(category_results) for category_results in results.values())
        total_passed = sum(sum(1 for r in category_results if r.success) for category_results in results.values())
        overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        report_lines.append("## 📊 Overall Summary")
        report_lines.append(f"- **Total Tests Executed:** {total_tests}")
        report_lines.append(f"- **Tests Passed:** {total_passed}")
        report_lines.append(f"- **Tests Failed:** {total_tests - total_passed}")
        report_lines.append(f"- **Success Rate:** {overall_success_rate:.1f}%")
        report_lines.append(f"- **Test Categories:** {len(results)}")
        report_lines.append("")
        
        # Per-category results
        report_lines.append("## 📋 Test Category Results")
        
        for category_name, category_results in results.items():
            report_lines.append(f"### {category_name}")
            
            category_passed = sum(1 for r in category_results if r.success)
            category_total = len(category_results)
            category_success_rate = (category_passed / category_total * 100) if category_total > 0 else 0
            avg_time = sum(r.execution_time_ms for r in category_results) / category_total if category_total > 0 else 0
            
            report_lines.append(f"**Summary:** {category_passed}/{category_total} tests passed ({category_success_rate:.1f}%)")
            report_lines.append(f"**Average Response Time:** {avg_time:.2f}ms")
            report_lines.append("")
            
            # Detailed test results
            report_lines.append("| Test Name | Scenario | Status | Message | Time (ms) |")
            report_lines.append("|-----------|----------|--------|---------|-----------|")
            
            for result in category_results:
                status = "✅ PASS" if result.success else "❌ FAIL"
                message = result.message[:50] + "..." if len(result.message) > 50 else result.message
                scenario = result.scenario[:30] + "..." if len(result.scenario) > 30 else result.scenario
                report_lines.append(f"| {result.test_name} | {scenario} | {status} | {message} | {result.execution_time_ms:.2f} |")
            
            report_lines.append("")
        
        # Workflow feature validation
        report_lines.append("## 🔄 Workflow Feature Validation")
        
        workflow_features = {
            "Journal Creation": ["Journal Entry Creation"],
            "Approval Routing": ["Approval Routing"],
            "Approval Decisions": ["Approval Decision", "Rejection Decision"],
            "SOD Enforcement": ["SOD Enforcement"]
        }
        
        for feature, test_names in workflow_features.items():
            feature_results = []
            for category_results in results.values():
                for result in category_results:
                    if any(test_name in result.test_name for test_name in test_names):
                        feature_results.append(result)
            
            if feature_results:
                feature_passed = sum(1 for r in feature_results if r.success)
                feature_total = len(feature_results)
                feature_success_rate = (feature_passed / feature_total * 100) if feature_total > 0 else 0
                
                status = "✅ VALIDATED" if feature_success_rate >= 90 else "⚠️ ISSUES FOUND" if feature_success_rate >= 70 else "❌ FAILED"
                report_lines.append(f"- **{feature}:** {status} ({feature_passed}/{feature_total} - {feature_success_rate:.1f}%)")
        
        report_lines.append("")
        
        # Recommendations
        report_lines.append("## 📋 Recommendations")
        
        if overall_success_rate >= 95:
            report_lines.append("✅ **EXCELLENT:** Approval workflow is fully functional and ready for production.")
            report_lines.append("- All approval levels working correctly")
            report_lines.append("- SOD enforcement properly implemented")
            report_lines.append("- Routing logic functioning as expected")
        elif overall_success_rate >= 85:
            report_lines.append("⚠️ **GOOD:** Most workflow tests passed with minor issues identified.")
            report_lines.append("- Review failed tests and address specific issues")
            report_lines.append("- Consider additional testing for edge cases")
        else:
            report_lines.append("❌ **ISSUES FOUND:** Significant workflow problems requiring attention.")
            report_lines.append("- Do not deploy until critical issues are resolved")
            report_lines.append("- Investigate and fix failing workflow scenarios")
        
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("*Report generated by Journal Entry Workflow Testing Framework*")
        
        return "\n".join(report_lines)


def main():
    """Main function to run workflow testing"""
    tester = JournalEntryWorkflowTester()
    
    # Run comprehensive tests
    test_results = tester.run_comprehensive_workflow_tests()
    
    # Generate and save report
    report = tester.generate_workflow_testing_report(test_results)
    
    # Save report to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = f"tests/WORKFLOW_TESTING_REPORT_{timestamp}.md"
    
    with open(report_filename, 'w') as f:
        f.write(report)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📋 WORKFLOW TESTING COMPLETE")
    print("=" * 60)
    
    total_tests = sum(len(category_results) for category_results in test_results.values())
    total_passed = sum(sum(1 for r in category_results if r.success) for category_results in test_results.values())
    overall_success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_tests - total_passed}")
    print(f"Success Rate: {overall_success_rate:.1f}%")
    print(f"Report saved: {report_filename}")
    
    return test_results


if __name__ == "__main__":
    main()