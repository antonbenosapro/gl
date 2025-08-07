#!/usr/bin/env python3
"""
Debug Auto-Posting Issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.auto_posting_service import auto_posting_service

def debug_auto_posting():
    """Debug auto-posting for specific document"""
    
    doc_number = "AUTO20250805160337"
    company_code = "TEST"
    
    print(f"🔍 Debugging auto-posting for {doc_number}")
    
    # Test eligibility
    is_eligible = auto_posting_service._is_eligible_for_auto_posting(doc_number, company_code)
    print(f"Is Eligible: {is_eligible}")
    
    # Get eligible documents
    eligible_docs = auto_posting_service._get_auto_posting_eligible_documents(company_code)
    print(f"Found {len(eligible_docs)} eligible documents:")
    for doc in eligible_docs:
        print(f"  - {doc['document_number']}: {doc['total_amount']}")
    
    # Try auto-posting
    success, message = auto_posting_service.auto_post_single_document(doc_number, company_code)
    print(f"Auto-post result: {success} - {message}")

if __name__ == "__main__":
    debug_auto_posting()