#!/usr/bin/env python3
"""
Debug Workflow Auto-Posting Integration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from decimal import Decimal
from sqlalchemy import text
from db_config import engine
from utils.workflow_engine import WorkflowEngine

def test_workflow_auto_posting():
    """Test workflow with auto-posting"""
    
    print("🔄 Testing Workflow Auto-Posting Integration")
    
    # Create a new test document
    doc_number = f"WF{datetime.now().strftime('%Y%m%d%H%M%S')}"
    company_code = "TEST"
    
    print(f"Creating document: {doc_number}")
    
    with engine.connect() as conn:
        with conn.begin():
            # Create header
            conn.execute(text("""
                INSERT INTO journalentryheader (
                    documentnumber, companycodeid, postingdate, fiscalyear, period,
                    reference, currencycode, createdby, workflow_status
                ) VALUES (
                    :doc, :cc, CURRENT_DATE, :year, :period,
                    'Workflow Auto-Posting Test', 'USD', 'test_creator', 'DRAFT'
                )
            """), {
                "doc": doc_number,
                "cc": company_code,
                "year": datetime.now().year,
                "period": datetime.now().month
            })
            
            # Create lines
            conn.execute(text("""
                INSERT INTO journalentryline (
                    documentnumber, companycodeid, linenumber, glaccountid,
                    debitamount, creditamount, description
                ) VALUES 
                (:doc, :cc, 1, '100001', 250.00, NULL, 'WF test debit'),
                (:doc, :cc, 2, '300001', NULL, 250.00, 'WF test credit')
            """), {"doc": doc_number, "cc": company_code})
    
    print("Document created, now approving...")
    
    # Import here to avoid circular imports
    workflow_engine = WorkflowEngine()
    
    # Approve document
    success, message = workflow_engine.approve_document(
        doc_number, company_code, 'test_approver', 'Workflow test'
    )
    
    print(f"Approval result: {success}")
    print(f"Message: {message}")
    
    # Check final status
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT workflow_status, posted_at, posted_by, auto_posted, auto_posted_at
            FROM journalentryheader
            WHERE documentnumber = :doc AND companycodeid = :cc
        """), {"doc": doc_number, "cc": company_code})
        
        status = result.fetchone()
        print(f"Final status: {status}")

if __name__ == "__main__":
    test_workflow_auto_posting()