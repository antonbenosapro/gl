"""
Enhanced Workflow Integration with Parallel Posting

This module provides integration between the approval workflow and
the enhanced parallel posting system for automated multi-ledger operations.

Author: Claude Code Assistant
Date: August 6, 2025
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
from sqlalchemy import text
from db_config import engine
from utils.workflow_engine import WorkflowEngine
from utils.enhanced_auto_posting_service import EnhancedAutoPostingService
from utils.logger import get_logger

logger = get_logger("enhanced_workflow_integration")

class EnhancedWorkflowIntegration:
    """Enhanced workflow integration with parallel posting automation."""
    
    def __init__(self):
        """Initialize the enhanced workflow integration."""
        self.workflow_engine = WorkflowEngine()
        self.enhanced_auto_posting = EnhancedAutoPostingService()
        self.system_user = "WORKFLOW_PARALLEL_POSTER"
    
    def approve_document_with_parallel_posting(self, document_number: str, company_code: str,
                                             approver_user: str, approval_notes: str = None,
                                             auto_post: bool = True) -> Dict:
        """
        Approve document and trigger parallel posting across all ledgers.
        
        Args:
            document_number: Document to approve
            company_code: Company code
            approver_user: User performing approval
            approval_notes: Optional approval notes
            auto_post: Whether to trigger automatic posting
            
        Returns:
            Dictionary with approval and posting results
        """
        results = {
            "document_number": document_number,
            "company_code": company_code,
            "approver": approver_user,
            "processed_at": datetime.now(),
            "approval_success": False,
            "posting_success": False,
            "approval_message": "",
            "posting_results": {},
            "errors": []
        }
        
        try:
            # Step 1: Standard workflow approval
            approval_success, approval_message = self._approve_document(
                document_number, company_code, approver_user, approval_notes
            )
            
            results["approval_success"] = approval_success
            results["approval_message"] = approval_message
            
            if not approval_success:
                logger.error(f"Approval failed for {document_number}: {approval_message}")
                return results
            
            logger.info(f"Document {document_number} approved by {approver_user}")
            
            # Step 2: Trigger parallel posting if enabled
            if auto_post:
                try:
                    posting_results = self.enhanced_auto_posting.process_single_document_with_parallel_posting(
                        document_number, company_code
                    )
                    
                    results["posting_results"] = posting_results
                    results["posting_success"] = posting_results["main_posting_success"]
                    
                    if posting_results["main_posting_success"]:
                        logger.info(f"Enhanced posting successful for {document_number}")
                        
                        # Log parallel posting details
                        if posting_results.get("parallel_posting_results"):
                            parallel_results = posting_results["parallel_posting_results"]
                            logger.info(f"Parallel posting: {parallel_results['successful_ledgers']}/{parallel_results['total_ledgers']} ledgers successful")
                    else:
                        logger.error(f"Posting failed for {document_number}: {posting_results['main_posting_message']}")
                        
                except Exception as pe:
                    error_msg = f"Posting error: {str(pe)}"
                    results["errors"].append(error_msg)
                    logger.error(f"Error in automatic posting for {document_number}: {pe}")
            else:
                logger.info(f"Auto-posting disabled for {document_number}")
                
        except Exception as e:
            error_msg = f"Workflow integration error: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(f"Error in enhanced workflow for {document_number}: {e}")
        
        return results
    
    def _approve_document(self, document_number: str, company_code: str,
                         approver_user: str, approval_notes: str = None) -> Tuple[bool, str]:
        """
        Perform document approval using workflow engine.
        
        Args:
            document_number: Document to approve
            company_code: Company code
            approver_user: Approving user
            approval_notes: Optional approval notes
            
        Returns:
            Tuple of (success, message)
        """
        try:
            with engine.connect() as conn:
                # Check current status
                current_status = conn.execute(text("""
                    SELECT workflow_status, approved_by, approved_at
                    FROM journalentryheader
                    WHERE documentnumber = :doc AND companycodeid = :cc
                """), {
                    "doc": document_number,
                    "cc": company_code
                }).fetchone()
                
                if not current_status:
                    return False, "Document not found"
                
                if current_status[0] == 'APPROVED':
                    return False, f"Document already approved by {current_status[1]} at {current_status[2]}"
                
                if current_status[0] != 'PENDING_APPROVAL':
                    return False, f"Document status is {current_status[0]}, cannot approve"
                
                # Verify approver has permission
                approval_level = self.workflow_engine.calculate_required_approval_level(
                    document_number, company_code
                )
                
                if approval_level:
                    approvers = self.workflow_engine.get_available_approvers(
                        approval_level, company_code
                    )
                    
                    approver_found = any(
                        approver['user_id'] == approver_user or 
                        approver['effective_approver'] == approver_user 
                        for approver in approvers
                    )
                    
                    if not approver_found:
                        return False, f"User {approver_user} not authorized to approve this document"
                
                # Perform approval
                with conn.begin():
                    conn.execute(text("""
                        UPDATE journalentryheader 
                        SET workflow_status = 'APPROVED',
                            approved_by = :approver,
                            approved_at = CURRENT_TIMESTAMP
                        WHERE documentnumber = :doc AND companycodeid = :cc
                    """), {
                        "doc": document_number,
                        "cc": company_code,
                        "approver": approver_user
                    })
                    
                    # Log approval in workflow instances
                    conn.execute(text("""
                        UPDATE workflow_instances 
                        SET status = 'COMPLETED',
                            completed_at = CURRENT_TIMESTAMP,
                            completed_by = :approver,
                            notes = :notes
                        WHERE document_number = :doc 
                        AND company_code = :cc 
                        AND status = 'PENDING'
                    """), {
                        "doc": document_number,
                        "cc": company_code,
                        "approver": approver_user,
                        "notes": approval_notes or f"Approved by {approver_user}"
                    })
                
                return True, f"Document approved successfully by {approver_user}"
                
        except Exception as e:
            logger.error(f"Error approving document: {e}")
            return False, f"Approval error: {str(e)}"
    
    def batch_approve_and_post(self, document_list: list, approver_user: str,
                             auto_post: bool = True) -> Dict:
        """
        Batch approve and post multiple documents.
        
        Args:
            document_list: List of (document_number, company_code) tuples
            approver_user: User performing approvals
            auto_post: Whether to trigger automatic posting
            
        Returns:
            Dictionary with batch processing results
        """
        results = {
            "processed_at": datetime.now(),
            "total_documents": len(document_list),
            "successful_approvals": 0,
            "successful_postings": 0,
            "failed_documents": [],
            "successful_documents": [],
            "errors": []
        }
        
        try:
            logger.info(f"Starting batch approval for {len(document_list)} documents by {approver_user}")
            
            for doc_number, company_code in document_list:
                try:
                    doc_result = self.approve_document_with_parallel_posting(
                        doc_number, company_code, approver_user, 
                        auto_post=auto_post
                    )
                    
                    if doc_result["approval_success"]:
                        results["successful_approvals"] += 1
                        
                        if doc_result["posting_success"]:
                            results["successful_postings"] += 1
                            results["successful_documents"].append({
                                "document": doc_number,
                                "company": company_code,
                                "parallel_ledgers": doc_result.get("posting_results", {}).get("parallel_posting_results", {}).get("successful_ledgers", 0)
                            })
                        else:
                            results["failed_documents"].append({
                                "document": doc_number,
                                "company": company_code,
                                "stage": "posting",
                                "error": doc_result.get("posting_results", {}).get("main_posting_message", "Unknown posting error")
                            })
                    else:
                        results["failed_documents"].append({
                            "document": doc_number,
                            "company": company_code,
                            "stage": "approval",
                            "error": doc_result["approval_message"]
                        })
                        
                except Exception as e:
                    error_msg = f"Error processing {doc_number}: {str(e)}"
                    results["failed_documents"].append({
                        "document": doc_number,
                        "company": company_code,
                        "stage": "general",
                        "error": error_msg
                    })
                    logger.error(error_msg)
            
            # Generate summary
            approval_rate = (results["successful_approvals"] / results["total_documents"] * 100) if results["total_documents"] > 0 else 0
            posting_rate = (results["successful_postings"] / results["successful_approvals"] * 100) if results["successful_approvals"] > 0 else 0
            
            logger.info(f"Batch processing complete:")
            logger.info(f"  Approvals: {results['successful_approvals']}/{results['total_documents']} ({approval_rate:.1f}%)")
            logger.info(f"  Postings: {results['successful_postings']}/{results['successful_approvals']} ({posting_rate:.1f}%)")
            
        except Exception as e:
            error_msg = f"Batch processing error: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(error_msg)
        
        return results
    
    def get_pending_approvals_with_posting_preview(self, company_code: str = None,
                                                 approver_user: str = None) -> Dict:
        """
        Get pending approvals with parallel posting impact preview.
        
        Args:
            company_code: Optional company code filter
            approver_user: Optional approver filter
            
        Returns:
            Dictionary with pending approvals and posting preview
        """
        try:
            with engine.connect() as conn:
                where_clause = "WHERE jeh.workflow_status = 'PENDING_APPROVAL'"
                params = {}
                
                if company_code:
                    where_clause += " AND jeh.companycodeid = :company_code"
                    params["company_code"] = company_code
                
                # Get pending documents with financial impact
                result = conn.execute(text(f"""
                    SELECT 
                        jeh.documentnumber,
                        jeh.companycodeid,
                        jeh.postingdate,
                        jeh.reference,
                        jeh.description,
                        jeh.createdby,
                        jeh.submitted_for_approval_at,
                        COALESCE(SUM(GREATEST(jel.debitamount, jel.creditamount)), 0) as total_amount,
                        COUNT(jel.linenumber) as line_count,
                        COUNT(DISTINCT jel.glaccountid) as unique_accounts
                    FROM journalentryheader jeh
                    LEFT JOIN journalentryline jel ON jel.documentnumber = jeh.documentnumber 
                        AND jel.companycodeid = jeh.companycodeid
                    {where_clause}
                    GROUP BY jeh.documentnumber, jeh.companycodeid, jeh.postingdate,
                             jeh.reference, jeh.description, jeh.createdby, jeh.submitted_for_approval_at
                    ORDER BY jeh.submitted_for_approval_at ASC
                """), params).fetchall()
                
                pending_documents = []
                total_financial_impact = 0
                
                for row in result:
                    doc_number = row[0]
                    doc_company = row[1]
                    doc_amount = float(row[7])
                    
                    # Calculate parallel posting impact
                    parallel_ledgers = self.enhanced_auto_posting.parallel_posting._get_parallel_ledgers()
                    
                    document_info = {
                        "document_number": doc_number,
                        "company_code": doc_company,
                        "posting_date": row[2],
                        "reference": row[3],
                        "description": row[4],
                        "created_by": row[5],
                        "submitted_at": row[6],
                        "total_amount": doc_amount,
                        "line_count": row[8],
                        "unique_accounts": row[9],
                        "parallel_posting_preview": {
                            "target_ledgers": len(parallel_ledgers),
                            "estimated_additional_lines": row[8] * len(parallel_ledgers),
                            "currency_translations_required": len([l for l in parallel_ledgers if l['currencycode'] != 'USD']),
                            "ledgers": [
                                {
                                    "ledger_id": ledger["ledgerid"],
                                    "description": ledger["description"],
                                    "accounting_principle": ledger["accounting_principle"]
                                }
                                for ledger in parallel_ledgers
                            ]
                        }
                    }
                    
                    pending_documents.append(document_info)
                    total_financial_impact += doc_amount
                
                return {
                    "query_date": datetime.now(),
                    "pending_count": len(pending_documents),
                    "total_financial_impact": total_financial_impact,
                    "parallel_posting_impact": {
                        "total_additional_documents": len(pending_documents) * len(parallel_ledgers) if pending_documents else 0,
                        "total_additional_lines": sum(doc["parallel_posting_preview"]["estimated_additional_lines"] for doc in pending_documents),
                        "unique_ledgers_affected": len(parallel_ledgers)
                    },
                    "pending_documents": pending_documents
                }
                
        except Exception as e:
            logger.error(f"Error getting pending approvals preview: {e}")
            return {"error": str(e)}

# Utility functions for external use
def approve_and_post_document(document_number: str, company_code: str, 
                            approver_user: str, auto_post: bool = True) -> Dict:
    """Approve document and trigger parallel posting."""
    integration = EnhancedWorkflowIntegration()
    return integration.approve_document_with_parallel_posting(
        document_number, company_code, approver_user, auto_post=auto_post
    )

def batch_approve_documents(document_list: list, approver_user: str, 
                          auto_post: bool = True) -> Dict:
    """Batch approve and post multiple documents."""
    integration = EnhancedWorkflowIntegration()
    return integration.batch_approve_and_post(document_list, approver_user, auto_post)

def get_pending_with_preview(company_code: str = None) -> Dict:
    """Get pending approvals with parallel posting preview."""
    integration = EnhancedWorkflowIntegration()
    return integration.get_pending_approvals_with_posting_preview(company_code)

# Test function
def test_enhanced_workflow_integration():
    """Test the enhanced workflow integration."""
    integration = EnhancedWorkflowIntegration()
    
    print("=== Enhanced Workflow Integration Test ===")
    
    # Test pending approvals preview
    try:
        preview = integration.get_pending_approvals_with_posting_preview()
        print(f"Pending approvals found: {preview.get('pending_count', 0)}")
        print(f"Total financial impact: ${preview.get('total_financial_impact', 0):,.2f}")
        
        if preview.get('parallel_posting_impact'):
            impact = preview['parallel_posting_impact']
            print(f"Parallel posting impact:")
            print(f"  Additional documents: {impact['total_additional_documents']}")
            print(f"  Additional lines: {impact['total_additional_lines']}")
            print(f"  Ledgers affected: {impact['unique_ledgers_affected']}")
    except Exception as e:
        print(f"Preview test failed: {e}")
    
    print("✅ Enhanced Workflow Integration: Initialized and ready")

if __name__ == "__main__":
    test_enhanced_workflow_integration()