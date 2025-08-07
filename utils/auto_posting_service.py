"""
Automatic GL Posting Service
Handles automatic posting of approved journal entries to General Ledger
"""

from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from sqlalchemy import text
from db_config import engine
from utils.gl_posting_engine import GLPostingEngine
from utils.logger import get_logger

logger = get_logger("auto_posting_service")

class AutoPostingService:
    """Service to handle automatic posting of approved journal entries"""
    
    def __init__(self):
        self.posting_engine = GLPostingEngine()
        self.system_user = "AUTO_POSTER"
        
    def process_approved_entries(self, company_code: str = None) -> Dict:
        """
        Process all approved journal entries for automatic posting
        
        Args:
            company_code: Optional company code filter
            
        Returns:
            Dictionary with processing results
        """
        results = {
            "processed_at": datetime.now(),
            "total_eligible": 0,
            "posted_successfully": 0,
            "failed_postings": [],
            "success_documents": [],
            "errors": []
        }
        
        try:
            # Get eligible documents for auto-posting
            eligible_docs = self._get_auto_posting_eligible_documents(company_code)
            results["total_eligible"] = len(eligible_docs)
            
            if not eligible_docs:
                logger.info("No documents eligible for automatic posting")
                return results
            
            logger.info(f"Processing {len(eligible_docs)} documents for automatic posting")
            
            # Process each document
            for doc in eligible_docs:
                doc_number = doc["document_number"]
                doc_company = doc["company_code"]
                
                try:
                    # Attempt auto-posting
                    success, message = self.posting_engine.post_journal_entry(
                        doc_number, doc_company, self.system_user, date.today()
                    )
                    
                    if success:
                        results["posted_successfully"] += 1
                        results["success_documents"].append({
                            "document": doc_number,
                            "company": doc_company,
                            "amount": doc["total_amount"],
                            "message": message
                        })
                        logger.info(f"Auto-posted document {doc_number}: {message}")
                        
                        # Update auto-posting flag
                        self._mark_as_auto_posted(doc_number, doc_company)
                        
                    else:
                        results["failed_postings"].append({
                            "document": doc_number,
                            "company": doc_company,
                            "error": message
                        })
                        logger.error(f"Failed to auto-post {doc_number}: {message}")
                        
                except Exception as e:
                    error_msg = str(e)
                    results["failed_postings"].append({
                        "document": doc_number,
                        "company": doc_company,
                        "error": error_msg
                    })
                    logger.error(f"Error auto-posting {doc_number}: {error_msg}")
            
            # Log summary
            success_rate = (results["posted_successfully"] / results["total_eligible"] * 100) if results["total_eligible"] > 0 else 0
            logger.info(f"Auto-posting completed: {results['posted_successfully']}/{results['total_eligible']} successful ({success_rate:.1f}%)")
            
        except Exception as e:
            error_msg = f"Auto-posting service error: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(error_msg)
        
        return results
    
    def auto_post_single_document(self, document_number: str, company_code: str) -> Tuple[bool, str]:
        """
        Auto-post a single approved document
        
        Args:
            document_number: Document to post
            company_code: Company code
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Verify document is eligible for auto-posting
            if not self._is_eligible_for_auto_posting(document_number, company_code):
                return False, "Document not eligible for automatic posting"
            
            # Perform posting
            success, message = self.posting_engine.post_journal_entry(
                document_number, company_code, self.system_user, date.today()
            )
            
            if success:
                # Mark as auto-posted
                self._mark_as_auto_posted(document_number, company_code)
                logger.info(f"Single auto-post successful: {document_number}")
            else:
                logger.error(f"Single auto-post failed: {document_number} - {message}")
            
            return success, message
            
        except Exception as e:
            error_msg = f"Error in single auto-post: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _get_auto_posting_eligible_documents(self, company_code: str = None) -> List[Dict]:
        """Get documents eligible for automatic posting"""
        
        try:
            with engine.connect() as conn:
                where_clause = """
                    WHERE jeh.workflow_status = 'APPROVED' 
                    AND jeh.posted_at IS NULL
                    AND jeh.auto_posted = false
                """
                params = {}
                
                if company_code:
                    where_clause += " AND jeh.companycodeid = :company_code"
                    params["company_code"] = company_code
                
                result = conn.execute(text(f"""
                    SELECT jeh.documentnumber, jeh.companycodeid, jeh.postingdate,
                           jeh.fiscalyear, jeh.period, jeh.reference, jeh.createdby,
                           jeh.approved_by, jeh.approved_at,
                           COALESCE(SUM(GREATEST(jel.debitamount, jel.creditamount)), 0) as total_amount
                    FROM journalentryheader jeh
                    LEFT JOIN journalentryline jel ON jel.documentnumber = jeh.documentnumber 
                        AND jel.companycodeid = jeh.companycodeid
                    {where_clause}
                    GROUP BY jeh.documentnumber, jeh.companycodeid, jeh.postingdate,
                             jeh.fiscalyear, jeh.period, jeh.reference, jeh.createdby,
                             jeh.approved_by, jeh.approved_at
                    ORDER BY jeh.approved_at ASC
                """), params)
                
                return [
                    {
                        "document_number": row[0],
                        "company_code": row[1],
                        "posting_date": row[2],
                        "fiscal_year": row[3],
                        "period": row[4],
                        "reference": row[5],
                        "created_by": row[6],
                        "approved_by": row[7],
                        "approved_at": row[8],
                        "total_amount": float(row[9])
                    }
                    for row in result
                ]
                
        except Exception as e:
            logger.error(f"Error getting auto-posting eligible documents: {e}")
            return []
    
    def _is_eligible_for_auto_posting(self, document_number: str, company_code: str) -> bool:
        """Check if a document is eligible for automatic posting"""
        
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT workflow_status, posted_at, auto_posted
                    FROM journalentryheader
                    WHERE documentnumber = :doc AND companycodeid = :cc
                """), {"doc": document_number, "cc": company_code})
                
                row = result.fetchone()
                if not row:
                    return False
                
                return (row[0] == 'APPROVED' and 
                        row[1] is None and 
                        not row[2])  # auto_posted is false
                
        except Exception as e:
            logger.error(f"Error checking auto-posting eligibility: {e}")
            return False
    
    def _mark_as_auto_posted(self, document_number: str, company_code: str):
        """Mark document as auto-posted to prevent duplicate processing"""
        
        try:
            with engine.connect() as conn:
                with conn.begin():
                    conn.execute(text("""
                        UPDATE journalentryheader 
                        SET auto_posted = true,
                            auto_posted_at = CURRENT_TIMESTAMP,
                            auto_posted_by = :auto_poster
                        WHERE documentnumber = :doc AND companycodeid = :cc
                    """), {
                        "doc": document_number,
                        "cc": company_code,
                        "auto_poster": self.system_user
                    })
                    
        except Exception as e:
            logger.error(f"Error marking document as auto-posted: {e}")
    
    def get_auto_posting_statistics(self, company_code: str = None, days_back: int = 30) -> Dict:
        """Get statistics on automatic posting performance"""
        
        try:
            with engine.connect() as conn:
                where_clause = "WHERE jeh.auto_posted_at >= CURRENT_DATE - :days_back * INTERVAL '1 DAY'"
                params = {"days_back": days_back}
                
                if company_code:
                    where_clause += " AND jeh.companycodeid = :company_code"
                    params["company_code"] = company_code
                
                # Auto-posted documents
                result = conn.execute(text(f"""
                    SELECT COUNT(*), 
                           COALESCE(SUM(
                               (SELECT SUM(GREATEST(jel.debitamount, jel.creditamount))
                                FROM journalentryline jel 
                                WHERE jel.documentnumber = jeh.documentnumber 
                                AND jel.companycodeid = jeh.companycodeid)
                           ), 0) as total_amount
                    FROM journalentryheader jeh
                    {where_clause} AND jeh.auto_posted = true
                """), params)
                
                auto_posted = result.fetchone()
                
                # Failed postings (approved but not posted and not auto-posted)
                result = conn.execute(text(f"""
                    SELECT COUNT(*)
                    FROM journalentryheader jeh
                    WHERE jeh.workflow_status = 'APPROVED' 
                    AND jeh.posted_at IS NULL 
                    AND jeh.auto_posted = false
                    AND jeh.approved_at >= CURRENT_DATE - :days_back * INTERVAL '1 DAY'
                    {' AND jeh.companycodeid = :company_code' if company_code else ''}
                """), params)
                
                pending_count = result.fetchone()[0]
                
                return {
                    "period_days": days_back,
                    "company_code": company_code or "ALL",
                    "auto_posted_count": auto_posted[0],
                    "auto_posted_amount": float(auto_posted[1]),
                    "pending_auto_post": pending_count,
                    "success_rate": (auto_posted[0] / (auto_posted[0] + pending_count) * 100) if (auto_posted[0] + pending_count) > 0 else 0
                }
                
        except Exception as e:
            logger.error(f"Error getting auto-posting statistics: {e}")
            return {}

# Global service instance
auto_posting_service = AutoPostingService()