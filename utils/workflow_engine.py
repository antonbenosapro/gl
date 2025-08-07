"""
Enterprise Approval Workflow Engine
Handles all approval workflow logic for journal entries
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from sqlalchemy import text
from db_config import engine
from utils.logger import get_logger

logger = get_logger("workflow_engine")

class WorkflowEngine:
    """Enterprise approval workflow engine"""
    
    @staticmethod
    def calculate_required_approval_level(document_number: str, company_code: str) -> Optional[int]:
        """Calculate required approval level based on transaction amount and rules"""
        try:
            # Ensure parameters are strings (handle integer inputs)
            document_number = str(document_number)
            company_code = str(company_code)
            
            with engine.connect() as conn:
                # Get total transaction amount
                result = conn.execute(text("""
                    SELECT COALESCE(SUM(GREATEST(debitamount, creditamount)), 0) as total_amount
                    FROM journalentryline 
                    WHERE documentnumber = :doc AND companycodeid = :cc
                """), {"doc": document_number, "cc": company_code})
                
                total_amount = result.fetchone()[0]
                
                # Find appropriate approval level
                level_result = conn.execute(text("""
                    SELECT id, level_name, min_amount, max_amount
                    FROM approval_levels 
                    WHERE company_code = :cc 
                    AND is_active = TRUE
                    AND :amount >= min_amount 
                    AND (:amount <= max_amount OR max_amount IS NULL)
                    ORDER BY level_order
                    LIMIT 1
                """), {"cc": company_code, "amount": total_amount})
                
                level_row = level_result.fetchone()
                if level_row:
                    logger.info(f"Document {document_number}: Amount ${total_amount:,.2f} requires {level_row[1]} approval")
                    return level_row[0]
                
                # Default to highest level if no match
                default_result = conn.execute(text("""
                    SELECT id FROM approval_levels 
                    WHERE company_code = :cc AND is_active = TRUE
                    ORDER BY level_order DESC LIMIT 1
                """), {"cc": company_code})
                
                default_row = default_result.fetchone()
                return default_row[0] if default_row else None
                
        except Exception as e:
            logger.error(f"Error calculating approval level for {document_number}: {e}")
            return None
    
    @staticmethod
    def get_available_approvers(approval_level_id: int, company_code: str, exclude_user: str = None) -> List[Dict]:
        """Get list of users who can approve at the specified level"""
        try:
            with engine.connect() as conn:
                query = """
                    SELECT DISTINCT a.user_id, u.first_name, u.last_name, u.email,
                           COALESCE(a.delegated_to, a.user_id) as effective_approver,
                           CASE WHEN a.delegated_to IS NOT NULL THEN TRUE ELSE FALSE END as is_delegated
                    FROM approvers a
                    JOIN users u ON u.username = a.user_id
                    WHERE a.approval_level_id = :level_id 
                    AND (a.company_code = :cc OR a.company_code IS NULL)
                    AND a.is_active = TRUE
                    AND (a.delegation_end_date IS NULL OR a.delegation_end_date >= CURRENT_DATE)
                """
                
                params = {"level_id": approval_level_id, "cc": company_code}
                
                if exclude_user:
                    query += " AND a.user_id != :exclude_user"
                    params["exclude_user"] = exclude_user
                
                result = conn.execute(text(query), params)
                
                approvers = []
                for row in result:
                    approvers.append({
                        "user_id": row[0],
                        "full_name": f"{row[1]} {row[2]}".strip(),
                        "email": row[3],
                        "effective_approver": row[4],
                        "is_delegated": row[5]
                    })
                
                return approvers
                
        except Exception as e:
            logger.error(f"Error getting approvers for level {approval_level_id}: {e}")
            return []
    
    @staticmethod
    def submit_for_approval(document_number: str, company_code: str, submitted_by: str, 
                          comments: str = None) -> Tuple[bool, str]:
        """Submit journal entry for approval"""
        try:
            # Ensure parameters are strings (handle integer inputs)
            document_number = str(document_number)
            company_code = str(company_code)
            
            with engine.begin() as conn:
                # Check if already submitted
                existing = conn.execute(text("""
                    SELECT workflow_status FROM journalentryheader 
                    WHERE documentnumber = :doc AND companycodeid = :cc
                """), {"doc": document_number, "cc": company_code}).fetchone()
                
                if not existing:
                    return False, "Document not found"
                
                if existing[0] != 'DRAFT':
                    return False, f"Document is already in {existing[0]} status"
                
                # Calculate required approval level
                approval_level_id = WorkflowEngine.calculate_required_approval_level(document_number, company_code)
                if not approval_level_id:
                    return False, "Could not determine required approval level"
                
                # Get available approvers
                approvers = WorkflowEngine.get_available_approvers(approval_level_id, company_code, submitted_by)
                if not approvers:
                    return False, "No available approvers found for this transaction"
                
                # Update journal entry status
                conn.execute(text("""
                    UPDATE journalentryheader 
                    SET workflow_status = 'PENDING_APPROVAL',
                        submitted_for_approval_at = CURRENT_TIMESTAMP,
                        submitted_by = :submitted_by
                    WHERE documentnumber = :doc AND companycodeid = :cc
                """), {"doc": document_number, "cc": company_code, "submitted_by": submitted_by})
                
                # Create workflow instance
                workflow_result = conn.execute(text("""
                    INSERT INTO workflow_instances 
                    (document_number, company_code, required_approval_level_id, status)
                    VALUES (:doc, :cc, :level_id, 'PENDING')
                    RETURNING id
                """), {"doc": document_number, "cc": company_code, "level_id": approval_level_id})
                
                workflow_id = workflow_result.fetchone()[0]
                
                # Create approval step for each approver
                for i, approver in enumerate(approvers):
                    conn.execute(text("""
                        INSERT INTO approval_steps 
                        (workflow_instance_id, step_number, approval_level_id, assigned_to, 
                         action, time_limit)
                        VALUES (:workflow_id, 1, :level_id, :approver, 'PENDING', :time_limit)
                    """), {
                        "workflow_id": workflow_id,
                        "level_id": approval_level_id,
                        "approver": approver["effective_approver"],
                        "time_limit": datetime.now() + timedelta(days=3)  # 3-day approval limit
                    })
                
                # Create notifications
                for approver in approvers:
                    WorkflowEngine._create_notification(
                        conn, workflow_id, approver["effective_approver"], 
                        "APPROVAL_REQUEST", 
                        f"Journal Entry {document_number} requires your approval",
                        f"Journal Entry {document_number} from {submitted_by} requires your approval. "
                        f"Amount: ${WorkflowEngine._get_document_amount(conn, document_number, company_code):,.2f}"
                    )
                
                # Log workflow action
                WorkflowEngine._log_workflow_action(
                    conn, document_number, company_code, "SUBMITTED_FOR_APPROVAL", 
                    submitted_by, "DRAFT", "PENDING_APPROVAL", comments
                )
                
                logger.info(f"Document {document_number} submitted for approval by {submitted_by}")
                return True, f"Successfully submitted for approval to {len(approvers)} approver(s)"
                
        except Exception as e:
            logger.error(f"Error submitting {document_number} for approval: {e}")
            return False, f"Submission failed: {str(e)}"
    
    @staticmethod
    def approve_document(document_number: str, company_code: str, approved_by: str, comments: str = None) -> Tuple[bool, str]:
        """Approve a journal entry by document number and company code"""
        try:
            # Ensure document_number is string (handle integer inputs)
            document_number = str(document_number)
            company_code = str(company_code)
            
            with engine.connect() as conn:
                # Get workflow instance ID
                result = conn.execute(text("""
                    SELECT id FROM workflow_instances 
                    WHERE document_number = :doc AND company_code = :cc AND status = 'PENDING'
                """), {"doc": document_number, "cc": company_code})
                
                workflow_row = result.fetchone()
                if not workflow_row:
                    # Try direct approval without workflow instance (for testing)
                    return WorkflowEngine.approve_document_direct(document_number, company_code, approved_by, comments)
                
                workflow_instance_id = workflow_row[0]
                return WorkflowEngine.approve_document_by_id(workflow_instance_id, approved_by, comments)
                
        except Exception as e:
            logger.error(f"Error in approve_document: {e}")
            return False, f"Approval failed: {str(e)}"
    
    @staticmethod
    def approve_document_direct(document_number: str, company_code: str, approved_by: str, comments: str = None) -> Tuple[bool, str]:
        """Direct approval without workflow instance (for testing/simple cases)"""
        try:
            # Ensure parameters are strings (handle integer inputs)
            document_number = str(document_number)
            company_code = str(company_code)
            
            with engine.begin() as conn:
                # Check document exists and is in correct status
                result = conn.execute(text("""
                    SELECT workflow_status, createdby FROM journalentryheader
                    WHERE documentnumber = :doc AND companycodeid = :cc
                """), {"doc": document_number, "cc": company_code})
                
                doc_row = result.fetchone()
                if not doc_row:
                    return False, "Document not found"
                
                if doc_row[0] not in ['DRAFT', 'PENDING_APPROVAL']:
                    return False, f"Document cannot be approved (status: {doc_row[0]})"
                
                # Check segregation of duties
                if approved_by == doc_row[1]:
                    return False, "Cannot approve your own journal entry (Segregation of Duties violation)"
                
                # Update journal entry to approved
                conn.execute(text("""
                    UPDATE journalentryheader 
                    SET workflow_status = 'APPROVED',
                        approved_at = CURRENT_TIMESTAMP,
                        approved_by = :approved_by
                    WHERE documentnumber = :doc AND companycodeid = :cc
                """), {"doc": document_number, "cc": company_code, "approved_by": approved_by})
                
                logger.info(f"Document {document_number} approved directly by {approved_by}")
                
        except Exception as e:
            logger.error(f"Error in direct approval: {e}")
            return False, f"Direct approval failed: {str(e)}"
        
        # AUTOMATIC POSTING: Post to GL immediately after approval (outside transaction)
        try:
            from utils.auto_posting_service import auto_posting_service
            
            auto_success, auto_message = auto_posting_service.auto_post_single_document(
                document_number, company_code
            )
            
            if auto_success:
                logger.info(f"Document {document_number} automatically posted to GL: {auto_message}")
                return True, f"Document approved and automatically posted to GL: {auto_message}"
            else:
                logger.warning(f"Document {document_number} approved but auto-posting failed: {auto_message}")
                return True, f"Document approved successfully, but auto-posting failed: {auto_message}"
                
        except Exception as auto_error:
            logger.error(f"Document {document_number} approved but auto-posting error: {auto_error}")
            return True, f"Document approved successfully, but auto-posting encountered an error: {str(auto_error)}"
    
    @staticmethod  
    def approve_document_by_id(workflow_instance_id: int, approved_by: str, comments: str = None) -> Tuple[bool, str]:
        """Approve a journal entry"""
        try:
            with engine.begin() as conn:
                # Get workflow instance details
                workflow = conn.execute(text("""
                    SELECT wi.document_number, wi.company_code, wi.status,
                           jeh.workflow_status, jeh.createdby
                    FROM workflow_instances wi
                    JOIN journalentryheader jeh ON jeh.documentnumber = wi.document_number 
                        AND jeh.companycodeid = wi.company_code
                    WHERE wi.id = :workflow_id
                """), {"workflow_id": workflow_instance_id}).fetchone()
                
                if not workflow:
                    return False, "Workflow instance not found"
                
                doc_number, company_code, wf_status, je_status, created_by = workflow
                
                if wf_status != 'PENDING':
                    return False, f"Workflow is not pending (status: {wf_status})"
                
                # Check if user can approve (segregation of duties)
                if approved_by == created_by:
                    return False, "Cannot approve your own journal entry (Segregation of Duties violation)"
                
                # Update approval step
                conn.execute(text("""
                    UPDATE approval_steps 
                    SET action = 'APPROVED', action_by = :approved_by, action_at = CURRENT_TIMESTAMP,
                        comments = :comments
                    WHERE workflow_instance_id = :workflow_id AND assigned_to = :approved_by
                    AND action = 'PENDING'
                """), {
                    "workflow_id": workflow_instance_id,
                    "approved_by": approved_by,
                    "comments": comments
                })
                
                # Update journal entry
                conn.execute(text("""
                    UPDATE journalentryheader 
                    SET workflow_status = 'APPROVED',
                        approved_at = CURRENT_TIMESTAMP,
                        approved_by = :approved_by
                    WHERE documentnumber = :doc AND companycodeid = :cc
                """), {"doc": doc_number, "cc": company_code, "approved_by": approved_by})
                
                # Update workflow instance
                conn.execute(text("""
                    UPDATE workflow_instances 
                    SET status = 'APPROVED', completed_at = CURRENT_TIMESTAMP
                    WHERE id = :workflow_id
                """), {"workflow_id": workflow_instance_id})
                
                # Create notification to submitter
                WorkflowEngine._create_notification(
                    conn, workflow_instance_id, created_by,
                    "APPROVED",
                    f"Journal Entry {doc_number} has been approved",
                    f"Your journal entry {doc_number} has been approved by {approved_by}. "
                    f"Comments: {comments or 'None'}"
                )
                
                # Log workflow action
                WorkflowEngine._log_workflow_action(
                    conn, doc_number, company_code, "APPROVED", approved_by,
                    "PENDING_APPROVAL", "APPROVED", comments
                )
                
                logger.info(f"Document {doc_number} approved by {approved_by}")
                
        except Exception as e:
            logger.error(f"Error approving workflow {workflow_instance_id}: {e}")
            return False, f"Approval failed: {str(e)}"
        
        # AUTOMATIC POSTING: Post to GL immediately after approval (outside transaction)
        try:
            from utils.auto_posting_service import auto_posting_service
            
            auto_success, auto_message = auto_posting_service.auto_post_single_document(
                doc_number, company_code
            )
            
            if auto_success:
                logger.info(f"Document {doc_number} automatically posted to GL: {auto_message}")
                return True, f"Document approved and automatically posted to GL: {auto_message}"
            else:
                logger.warning(f"Document {doc_number} approved but auto-posting failed: {auto_message}")
                return True, f"Document approved successfully, but auto-posting failed: {auto_message}"
                
        except Exception as auto_error:
            logger.error(f"Document {doc_number} approved but auto-posting error: {auto_error}")
            return True, f"Document approved successfully, but auto-posting encountered an error: {str(auto_error)}"
    
    @staticmethod
    def reject_document(workflow_instance_id: int, rejected_by: str, rejection_reason: str) -> Tuple[bool, str]:
        """Reject a journal entry"""
        try:
            with engine.begin() as conn:
                # Get workflow instance details
                workflow = conn.execute(text("""
                    SELECT wi.document_number, wi.company_code, wi.status,
                           jeh.workflow_status, jeh.createdby
                    FROM workflow_instances wi
                    JOIN journalentryheader jeh ON jeh.documentnumber = wi.document_number 
                        AND jeh.companycodeid = wi.company_code
                    WHERE wi.id = :workflow_id
                """), {"workflow_id": workflow_instance_id}).fetchone()
                
                if not workflow:
                    return False, "Workflow instance not found"
                
                doc_number, company_code, wf_status, je_status, created_by = workflow
                
                if wf_status != 'PENDING':
                    return False, f"Workflow is not pending (status: {wf_status})"
                
                # Update approval step
                conn.execute(text("""
                    UPDATE approval_steps 
                    SET action = 'REJECTED', action_by = :rejected_by, action_at = CURRENT_TIMESTAMP,
                        comments = :reason
                    WHERE workflow_instance_id = :workflow_id AND assigned_to = :rejected_by
                    AND action = 'PENDING'
                """), {
                    "workflow_id": workflow_instance_id,
                    "rejected_by": rejected_by,
                    "reason": rejection_reason
                })
                
                # Update journal entry
                conn.execute(text("""
                    UPDATE journalentryheader 
                    SET workflow_status = 'REJECTED',
                        rejected_at = CURRENT_TIMESTAMP,
                        rejected_by = :rejected_by,
                        rejection_reason = :reason
                    WHERE documentnumber = :doc AND companycodeid = :cc
                """), {
                    "doc": doc_number, 
                    "cc": company_code, 
                    "rejected_by": rejected_by,
                    "reason": rejection_reason
                })
                
                # Update workflow instance
                conn.execute(text("""
                    UPDATE workflow_instances 
                    SET status = 'REJECTED', completed_at = CURRENT_TIMESTAMP
                    WHERE id = :workflow_id
                """), {"workflow_id": workflow_instance_id})
                
                # Create notification to submitter
                WorkflowEngine._create_notification(
                    conn, workflow_instance_id, created_by,
                    "REJECTED",
                    f"Journal Entry {doc_number} has been rejected",
                    f"Your journal entry {doc_number} has been rejected by {rejected_by}. "
                    f"Reason: {rejection_reason}"
                )
                
                # Log workflow action
                WorkflowEngine._log_workflow_action(
                    conn, doc_number, company_code, "REJECTED", rejected_by,
                    "PENDING_APPROVAL", "REJECTED", rejection_reason
                )
                
                logger.info(f"Document {doc_number} rejected by {rejected_by}")
                return True, "Document rejected successfully"
                
        except Exception as e:
            logger.error(f"Error rejecting workflow {workflow_instance_id}: {e}")
            return False, f"Rejection failed: {str(e)}"
    
    @staticmethod
    def get_pending_approvals(user_id: str) -> List[Dict]:
        """Get pending approvals for a specific user"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT wi.id as workflow_id, wi.document_number, wi.company_code,
                           jeh.reference, jeh.postingdate, jeh.currencycode, jeh.createdby,
                           jeh.submitted_for_approval_at, al.level_name,
                           COALESCE(SUM(GREATEST(jel.debitamount, jel.creditamount)), 0) as total_amount,
                           ast.time_limit, ast.comments
                    FROM workflow_instances wi
                    JOIN journalentryheader jeh ON jeh.documentnumber = wi.document_number 
                        AND jeh.companycodeid = wi.company_code
                    JOIN approval_steps ast ON ast.workflow_instance_id = wi.id
                    JOIN approval_levels al ON al.id = wi.required_approval_level_id
                    LEFT JOIN journalentryline jel ON jel.documentnumber = wi.document_number 
                        AND jel.companycodeid = wi.company_code
                    WHERE ast.assigned_to = :user_id 
                    AND ast.action = 'PENDING'
                    AND wi.status = 'PENDING'
                    GROUP BY wi.id, wi.document_number, wi.company_code, jeh.reference, 
                             jeh.postingdate, jeh.currencycode, jeh.createdby, 
                             jeh.submitted_for_approval_at, al.level_name, ast.time_limit, ast.comments
                    ORDER BY jeh.submitted_for_approval_at ASC
                """), {"user_id": user_id})
                
                approvals = []
                for row in result:
                    approvals.append({
                        "workflow_id": row[0],
                        "document_number": row[1],
                        "company_code": row[2],
                        "reference": row[3],
                        "posting_date": row[4],
                        "currency": row[5],
                        "created_by": row[6],
                        "submitted_at": row[7],
                        "approval_level": row[8],
                        "total_amount": float(row[9]),
                        "time_limit": row[10],
                        "comments": row[11],
                        "is_overdue": row[10] and row[10] < datetime.now()
                    })
                
                return approvals
                
        except Exception as e:
            logger.error(f"Error getting pending approvals for {user_id}: {e}")
            return []
    
    @staticmethod
    def _create_notification(conn, workflow_id: int, recipient: str, notification_type: str, 
                           subject: str, message: str):
        """Create a notification record"""
        conn.execute(text("""
            INSERT INTO approval_notifications 
            (workflow_instance_id, recipient, notification_type, subject, message)
            VALUES (:workflow_id, :recipient, :type, :subject, :message)
        """), {
            "workflow_id": workflow_id,
            "recipient": recipient,
            "type": notification_type,
            "subject": subject,
            "message": message
        })
    
    @staticmethod
    def _log_workflow_action(conn, document_number: str, company_code: str, action: str, 
                           performed_by: str, old_status: str, new_status: str, comments: str = None):
        """Log workflow action to audit trail"""
        conn.execute(text("""
            INSERT INTO workflow_audit_log 
            (document_number, company_code, action, performed_by, old_status, new_status, comments)
            VALUES (:doc, :cc, :action, :user, :old_status, :new_status, :comments)
        """), {
            "doc": document_number,
            "cc": company_code,
            "action": action,
            "user": performed_by,
            "old_status": old_status,
            "new_status": new_status,
            "comments": comments
        })
    
    @staticmethod
    def _get_document_amount(conn, document_number: str, company_code: str) -> float:
        """Get total document amount"""
        result = conn.execute(text("""
            SELECT COALESCE(SUM(GREATEST(debitamount, creditamount)), 0)
            FROM journalentryline 
            WHERE documentnumber = :doc AND companycodeid = :cc
        """), {"doc": document_number, "cc": company_code})
        
        return float(result.fetchone()[0])
    
    @staticmethod
    def get_all_workflows(status_filter: str = None, days_back: int = 30) -> List[Dict]:
        """Get all workflow instances (admin view)"""
        try:
            with engine.connect() as conn:
                where_clause = "WHERE wi.created_at >= CURRENT_DATE - :days_back * INTERVAL '1 DAY'"
                params = {"days_back": days_back}
                
                if status_filter and status_filter != 'ALL':
                    where_clause += " AND wi.status = :status"
                    params["status"] = status_filter
                
                result = conn.execute(text(f"""
                    SELECT wi.id as workflow_id, wi.document_number, wi.company_code, wi.status,
                           wi.created_at, wi.completed_at, wi.priority,
                           jeh.reference, jeh.postingdate, jeh.currencycode, jeh.createdby,
                           jeh.submitted_for_approval_at, jeh.approved_by, jeh.approved_at,
                           al.level_name, ast.assigned_to, ast.action, ast.action_by, ast.action_at,
                           ast.comments, ast.time_limit,
                           COALESCE(SUM(GREATEST(jel.debitamount, jel.creditamount)), 0) as total_amount
                    FROM workflow_instances wi
                    JOIN journalentryheader jeh ON jeh.documentnumber = wi.document_number 
                        AND jeh.companycodeid = wi.company_code
                    LEFT JOIN approval_levels al ON al.id = wi.required_approval_level_id
                    LEFT JOIN approval_steps ast ON ast.workflow_instance_id = wi.id
                    LEFT JOIN journalentryline jel ON jel.documentnumber = wi.document_number 
                        AND jel.companycodeid = wi.company_code
                    {where_clause}
                    GROUP BY wi.id, wi.document_number, wi.company_code, wi.status, wi.created_at,
                             wi.completed_at, wi.priority, jeh.reference, jeh.postingdate, 
                             jeh.currencycode, jeh.createdby, jeh.submitted_for_approval_at,
                             jeh.approved_by, jeh.approved_at, al.level_name, ast.assigned_to,
                             ast.action, ast.action_by, ast.action_at, ast.comments, ast.time_limit
                    ORDER BY wi.created_at DESC
                """), params)
                
                workflows = []
                for row in result:
                    is_overdue = (row[20] and row[20] < datetime.now()) if row[20] else False
                    
                    workflows.append({
                        "workflow_id": row[0],
                        "document_number": row[1],
                        "company_code": row[2],
                        "status": row[3],
                        "created_at": row[4],
                        "completed_at": row[5],
                        "priority": row[6] or "NORMAL",
                        "reference": row[7],
                        "posting_date": row[8],
                        "currency": row[9],
                        "created_by": row[10],
                        "submitted_at": row[11],
                        "approved_by": row[12],
                        "approved_at": row[13],
                        "approval_level": row[14],
                        "assigned_to": row[15],
                        "action": row[16],
                        "action_by": row[17],
                        "action_at": row[18],
                        "comments": row[19],
                        "time_limit": row[20],
                        "total_amount": float(row[21]),
                        "is_overdue": is_overdue
                    })
                
                logger.info(f"Retrieved {len(workflows)} workflow instances")
                return workflows
                
        except Exception as e:
            logger.error(f"Error retrieving all workflows: {e}")
            return []
    
    @staticmethod
    def get_workflow_statistics() -> Dict:
        """Get workflow statistics for admin dashboard"""
        try:
            with engine.connect() as conn:
                # Get overall statistics
                stats = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_workflows,
                        COUNT(CASE WHEN wi.status = 'PENDING' THEN 1 END) as pending_count,
                        COUNT(CASE WHEN wi.status = 'APPROVED' THEN 1 END) as approved_count,
                        COUNT(CASE WHEN wi.status = 'REJECTED' THEN 1 END) as rejected_count,
                        COUNT(CASE WHEN ast.time_limit < CURRENT_TIMESTAMP AND wi.status = 'PENDING' THEN 1 END) as overdue_count,
                        AVG(EXTRACT(EPOCH FROM (COALESCE(wi.completed_at, CURRENT_TIMESTAMP) - wi.created_at))/3600)::NUMERIC(10,2) as avg_completion_hours
                    FROM workflow_instances wi
                    LEFT JOIN approval_steps ast ON ast.workflow_instance_id = wi.id AND ast.action = 'PENDING'
                    WHERE wi.created_at >= CURRENT_DATE - INTERVAL '30' DAY
                """)).fetchone()
                
                # Get approval level breakdown
                level_stats = conn.execute(text("""
                    SELECT al.level_name, COUNT(*) as count
                    FROM workflow_instances wi
                    JOIN approval_levels al ON al.id = wi.required_approval_level_id
                    WHERE wi.created_at >= CURRENT_DATE - INTERVAL '30' DAY
                    GROUP BY al.level_name
                    ORDER BY count DESC
                """)).fetchall()
                
                # Get top approvers
                approver_stats = conn.execute(text("""
                    SELECT ast.action_by, COUNT(*) as approval_count
                    FROM approval_steps ast
                    WHERE ast.action IN ('APPROVED', 'REJECTED')
                    AND ast.action_at >= CURRENT_DATE - INTERVAL '30' DAY
                    GROUP BY ast.action_by
                    ORDER BY approval_count DESC
                    LIMIT 5
                """)).fetchall()
                
                return {
                    "total_workflows": stats[0] if stats else 0,
                    "pending_count": stats[1] if stats else 0,
                    "approved_count": stats[2] if stats else 0,
                    "rejected_count": stats[3] if stats else 0,
                    "overdue_count": stats[4] if stats else 0,
                    "avg_completion_hours": float(stats[5]) if stats and stats[5] else 0,
                    "level_breakdown": [{"level": row[0], "count": row[1]} for row in level_stats],
                    "top_approvers": [{"approver": row[0], "count": row[1]} for row in approver_stats]
                }
                
        except Exception as e:
            logger.error(f"Error retrieving workflow statistics: {e}")
            return {
                "total_workflows": 0,
                "pending_count": 0,
                "approved_count": 0,
                "rejected_count": 0,
                "overdue_count": 0,
                "avg_completion_hours": 0,
                "level_breakdown": [],
                "top_approvers": []
            }