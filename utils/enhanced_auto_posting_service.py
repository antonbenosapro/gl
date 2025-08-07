"""
Enhanced Auto-Posting Service with Parallel Ledger Support

This service extends the existing auto-posting functionality to include
automated parallel ledger posting with currency translation and derivation rules.

Author: Claude Code Assistant
Date: August 6, 2025
"""

import logging
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from sqlalchemy import text
from db_config import engine
from utils.auto_posting_service import AutoPostingService
from utils.parallel_posting_service import ParallelPostingService
from utils.workflow_engine import WorkflowEngine
from utils.logger import get_logger

logger = get_logger("enhanced_auto_posting")

class EnhancedAutoPostingService:
    """Enhanced auto-posting service with parallel ledger support."""
    
    def __init__(self):
        """Initialize the enhanced auto-posting service."""
        self.base_auto_posting = AutoPostingService()
        self.parallel_posting = ParallelPostingService()
        self.workflow_engine = WorkflowEngine()
        self.system_user = "ENHANCED_AUTO_POSTER"
        
    def process_approved_entries_with_parallel_posting(self, company_code: str = None) -> Dict:
        """
        Process all approved journal entries for automatic posting including parallel ledgers.
        
        Args:
            company_code: Optional company code filter
            
        Returns:
            Dictionary with comprehensive processing results
        """
        results = {
            "processed_at": datetime.now(),
            "total_eligible": 0,
            "posted_successfully": 0,
            "failed_postings": [],
            "success_documents": [],
            "parallel_posting_results": {},
            "errors": []
        }
        
        try:
            # Get eligible documents using the base service
            eligible_docs = self.base_auto_posting._get_auto_posting_eligible_documents(company_code)
            results["total_eligible"] = len(eligible_docs)
            
            if not eligible_docs:
                logger.info("No documents eligible for automatic posting")
                return results
            
            logger.info(f"Processing {len(eligible_docs)} documents for enhanced auto-posting with parallel ledgers")
            
            # Process each document
            for doc in eligible_docs:
                doc_number = doc["document_number"]
                doc_company = doc["company_code"]
                
                try:
                    # Step 1: Standard GL posting to leading ledger
                    success, message = self.base_auto_posting.auto_post_single_document(
                        doc_number, doc_company
                    )
                    
                    if success:
                        results["posted_successfully"] += 1
                        results["success_documents"].append({
                            "document": doc_number,
                            "company": doc_company,
                            "amount": doc["total_amount"],
                            "message": message,
                            "parallel_posting": "pending"
                        })
                        
                        logger.info(f"Successfully posted to leading ledger: {doc_number}")
                        
                        # Step 2: Parallel ledger posting
                        try:
                            parallel_results = self.parallel_posting.process_approved_document_to_all_ledgers(
                                doc_number, doc_company
                            )
                            
                            results["parallel_posting_results"][doc_number] = parallel_results
                            
                            # Update success document with parallel results
                            for success_doc in results["success_documents"]:
                                if success_doc["document"] == doc_number:
                                    success_doc["parallel_posting"] = "completed"
                                    success_doc["parallel_ledgers"] = parallel_results["successful_ledgers"]
                                    success_doc["parallel_total"] = parallel_results["total_ledgers"]
                                    break
                            
                            logger.info(f"Parallel posting completed for {doc_number}: {parallel_results['successful_ledgers']}/{parallel_results['total_ledgers']} ledgers")
                            
                        except Exception as pe:
                            # Parallel posting failed, but main posting succeeded
                            error_msg = f"Parallel posting failed for {doc_number}: {str(pe)}"
                            logger.error(error_msg)
                            results["errors"].append(error_msg)
                            
                            # Update success document status
                            for success_doc in results["success_documents"]:
                                if success_doc["document"] == doc_number:
                                    success_doc["parallel_posting"] = "failed"
                                    success_doc["parallel_error"] = str(pe)
                                    break
                    else:
                        # Main posting failed
                        results["failed_postings"].append({
                            "document": doc_number,
                            "company": doc_company,
                            "error": message,
                            "stage": "main_posting"
                        })
                        logger.error(f"Failed to post {doc_number} to leading ledger: {message}")
                        
                except Exception as e:
                    error_msg = str(e)
                    results["failed_postings"].append({
                        "document": doc_number,
                        "company": doc_company,
                        "error": error_msg,
                        "stage": "general_error"
                    })
                    logger.error(f"Error processing {doc_number}: {error_msg}")
            
            # Generate summary statistics
            self._generate_processing_summary(results)
            
        except Exception as e:
            error_msg = f"Enhanced auto-posting service error: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(error_msg)
        
        return results
    
    def process_single_document_with_parallel_posting(self, document_number: str, 
                                                    company_code: str) -> Dict:
        """
        Process a single document for posting to all ledgers.
        
        Args:
            document_number: Document to process
            company_code: Company code
            
        Returns:
            Dictionary with processing results
        """
        results = {
            "document_number": document_number,
            "company_code": company_code,
            "processed_at": datetime.now(),
            "main_posting_success": False,
            "parallel_posting_success": False,
            "main_posting_message": "",
            "parallel_posting_results": {},
            "errors": []
        }
        
        try:
            # Verify document is eligible
            if not self.base_auto_posting._is_eligible_for_auto_posting(document_number, company_code):
                results["errors"].append("Document not eligible for automatic posting")
                return results
            
            # Step 1: Main posting to leading ledger
            success, message = self.base_auto_posting.auto_post_single_document(
                document_number, company_code
            )
            
            results["main_posting_success"] = success
            results["main_posting_message"] = message
            
            if success:
                logger.info(f"Main posting successful for {document_number}")
                
                # Step 2: Parallel posting
                try:
                    parallel_results = self.parallel_posting.process_approved_document_to_all_ledgers(
                        document_number, company_code
                    )
                    
                    results["parallel_posting_results"] = parallel_results
                    results["parallel_posting_success"] = parallel_results["successful_ledgers"] > 0
                    
                    logger.info(f"Enhanced posting completed for {document_number}")
                    
                except Exception as pe:
                    error_msg = f"Parallel posting failed: {str(pe)}"
                    results["errors"].append(error_msg)
                    logger.error(f"Parallel posting failed for {document_number}: {pe}")
            else:
                logger.error(f"Main posting failed for {document_number}: {message}")
                
        except Exception as e:
            error_msg = f"Error in enhanced single document processing: {str(e)}"
            results["errors"].append(error_msg)
            logger.error(error_msg)
        
        return results
    
    def _generate_processing_summary(self, results: Dict):
        """Generate comprehensive processing summary."""
        try:
            total_documents = results["total_eligible"]
            successful_main = results["posted_successfully"]
            
            # Calculate parallel posting statistics
            parallel_stats = {
                "total_with_parallel": 0,
                "successful_parallel": 0,
                "failed_parallel": 0,
                "total_parallel_ledgers": 0,
                "successful_parallel_ledgers": 0
            }
            
            for doc_number, parallel_result in results["parallel_posting_results"].items():
                parallel_stats["total_with_parallel"] += 1
                parallel_stats["total_parallel_ledgers"] += parallel_result["total_ledgers"]
                parallel_stats["successful_parallel_ledgers"] += parallel_result["successful_ledgers"]
                
                if parallel_result["successful_ledgers"] > 0:
                    parallel_stats["successful_parallel"] += 1
                else:
                    parallel_stats["failed_parallel"] += 1
            
            # Add summary to results
            results["processing_summary"] = {
                "main_posting": {
                    "total_eligible": total_documents,
                    "successful": successful_main,
                    "failed": total_documents - successful_main,
                    "success_rate": (successful_main / total_documents * 100) if total_documents > 0 else 0
                },
                "parallel_posting": parallel_stats,
                "overall_success_rate": (
                    (successful_main + parallel_stats["successful_parallel"]) / 
                    (total_documents + parallel_stats["total_with_parallel"]) * 100
                ) if (total_documents + parallel_stats["total_with_parallel"]) > 0 else 0
            }
            
            # Log comprehensive summary
            main_rate = results["processing_summary"]["main_posting"]["success_rate"]
            parallel_rate = (parallel_stats["successful_parallel_ledgers"] / parallel_stats["total_parallel_ledgers"] * 100) if parallel_stats["total_parallel_ledgers"] > 0 else 0
            
            logger.info(f"Enhanced auto-posting summary:")
            logger.info(f"  Main posting: {successful_main}/{total_documents} documents ({main_rate:.1f}%)")
            logger.info(f"  Parallel posting: {parallel_stats['successful_parallel_ledgers']}/{parallel_stats['total_parallel_ledgers']} ledgers ({parallel_rate:.1f}%)")
            
        except Exception as e:
            logger.error(f"Error generating processing summary: {e}")
    
    def get_enhanced_posting_statistics(self, company_code: str = None, 
                                      days_back: int = 30) -> Dict:
        """Get comprehensive statistics including parallel posting performance."""
        try:
            # Get base auto-posting statistics
            base_stats = self.base_auto_posting.get_auto_posting_statistics(company_code, days_back)
            
            # Get parallel posting statistics
            with engine.connect() as conn:
                where_clause = "WHERE jeh.parallel_posted_at >= CURRENT_DATE - :days_back * INTERVAL '1 DAY'"
                params = {"days_back": days_back}
                
                if company_code:
                    where_clause += " AND jeh.companycodeid = :company_code"
                    params["company_code"] = company_code
                
                # Parallel posting statistics
                result = conn.execute(text(f"""
                    SELECT 
                        COUNT(*) as total_parallel_posted,
                        SUM(parallel_ledger_count) as total_ledger_attempts,
                        SUM(parallel_success_count) as total_ledger_successes,
                        AVG(parallel_success_count::numeric / NULLIF(parallel_ledger_count, 0) * 100) as avg_success_rate,
                        COUNT(CASE WHEN parallel_success_count = parallel_ledger_count THEN 1 END) as fully_successful_documents
                    FROM journalentryheader jeh
                    {where_clause}
                    AND parallel_posted = true
                """), params).fetchone()
                
                # Recent parallel posting activity
                activity_result = conn.execute(text(f"""
                    SELECT 
                        DATE(parallel_posted_at) as posting_date,
                        COUNT(*) as documents_count,
                        SUM(parallel_ledger_count) as ledger_attempts,
                        SUM(parallel_success_count) as ledger_successes
                    FROM journalentryheader jeh
                    {where_clause}
                    AND parallel_posted = true
                    GROUP BY DATE(parallel_posted_at)
                    ORDER BY posting_date DESC
                    LIMIT 10
                """), params).fetchall()
                
                # Ledger-specific statistics
                ledger_stats = conn.execute(text("""
                    SELECT 
                        l.ledgerid,
                        l.description,
                        l.accounting_principle,
                        COUNT(jeh_parallel.*) as parallel_documents_created,
                        AVG(CASE 
                            WHEN jeh_parallel.posted_at IS NOT NULL THEN 1.0 
                            ELSE 0.0 
                        END) * 100 as success_rate
                    FROM ledger l
                    LEFT JOIN journalentryheader jeh_parallel ON jeh_parallel.documentnumber LIKE '%_' || l.ledgerid
                        AND jeh_parallel.parallel_source_doc IS NOT NULL
                        AND jeh_parallel.createdat >= CURRENT_DATE - :days_back * INTERVAL '1 DAY'
                    WHERE l.isleadingledger = false
                    GROUP BY l.ledgerid, l.description, l.accounting_principle
                    ORDER BY parallel_documents_created DESC
                """), {"days_back": days_back}).fetchall()
                
                parallel_stats = {
                    "period_days": days_back,
                    "total_documents_with_parallel": result[0] if result else 0,
                    "total_ledger_attempts": result[1] if result else 0,
                    "total_ledger_successes": result[2] if result else 0,
                    "average_success_rate": float(result[3]) if result and result[3] else 0,
                    "fully_successful_documents": result[4] if result else 0,
                    "daily_activity": [
                        {
                            "date": row[0],
                            "documents": row[1],
                            "ledger_attempts": row[2],
                            "ledger_successes": row[3],
                            "success_rate": (row[3] / row[2] * 100) if row[2] > 0 else 0
                        }
                        for row in activity_result
                    ],
                    "ledger_performance": [
                        {
                            "ledger_id": row[0],
                            "description": row[1],
                            "accounting_principle": row[2],
                            "documents_created": row[3],
                            "success_rate": float(row[4]) if row[4] else 0
                        }
                        for row in ledger_stats
                    ]
                }
                
                # Combine with base statistics
                enhanced_stats = {
                    "base_auto_posting": base_stats,
                    "parallel_posting": parallel_stats,
                    "combined_performance": {
                        "total_processing_success_rate": (
                            parallel_stats["average_success_rate"] + 
                            (base_stats.get("success_rate", 0) if isinstance(base_stats, dict) else 0)
                        ) / 2 if parallel_stats["average_success_rate"] > 0 else 0
                    }
                }
                
                return enhanced_stats
                
        except Exception as e:
            logger.error(f"Error getting enhanced posting statistics: {e}")
            return {"error": str(e)}
    
    def validate_parallel_ledger_balances(self, document_number: str, 
                                        company_code: str) -> Dict:
        """Validate that parallel ledger balances are consistent."""
        try:
            with engine.connect() as conn:
                # Get all related documents (source and parallel)
                result = conn.execute(text("""
                    WITH related_documents AS (
                        SELECT documentnumber, parallel_source_doc, 
                               CASE WHEN parallel_source_doc IS NULL THEN 'SOURCE' ELSE 'PARALLEL' END as doc_type
                        FROM journalentryheader 
                        WHERE documentnumber = :doc 
                        OR parallel_source_doc = :doc
                    )
                    SELECT 
                        rd.documentnumber,
                        rd.doc_type,
                        jel.ledgerid,
                        SUM(jel.debitamount) as total_debits,
                        SUM(jel.creditamount) as total_credits,
                        SUM(jel.debitamount - jel.creditamount) as net_balance
                    FROM related_documents rd
                    JOIN journalentryline jel ON jel.documentnumber = rd.documentnumber
                        AND jel.companycodeid = :cc
                    GROUP BY rd.documentnumber, rd.doc_type, jel.ledgerid
                    ORDER BY jel.ledgerid, rd.doc_type
                """), {
                    "doc": document_number,
                    "cc": company_code
                }).fetchall()
                
                # Organize results by ledger
                ledger_balances = {}
                for row in result:
                    ledger_id = row[2]
                    if ledger_id not in ledger_balances:
                        ledger_balances[ledger_id] = []
                    
                    ledger_balances[ledger_id].append({
                        "document": row[0],
                        "type": row[1],
                        "debits": float(row[3]),
                        "credits": float(row[4]),
                        "balance": float(row[5])
                    })
                
                # Validate consistency
                validation_results = {
                    "document_number": document_number,
                    "company_code": company_code,
                    "validation_date": datetime.now(),
                    "ledger_balances": ledger_balances,
                    "is_consistent": True,
                    "discrepancies": []
                }
                
                # Check that all parallel ledgers have balanced entries
                for ledger_id, entries in ledger_balances.items():
                    total_balance = sum(entry["balance"] for entry in entries)
                    if abs(total_balance) > 0.01:  # Allow small rounding differences
                        validation_results["is_consistent"] = False
                        validation_results["discrepancies"].append({
                            "ledger": ledger_id,
                            "imbalance": total_balance,
                            "entries": entries
                        })
                
                return validation_results
                
        except Exception as e:
            logger.error(f"Error validating parallel ledger balances: {e}")
            return {"error": str(e)}

# Utility functions for external use
def process_all_eligible_documents(company_code: str = None) -> Dict:
    """Process all eligible documents with enhanced parallel posting."""
    service = EnhancedAutoPostingService()
    return service.process_approved_entries_with_parallel_posting(company_code)

def process_single_document(document_number: str, company_code: str) -> Dict:
    """Process a single document with enhanced parallel posting."""
    service = EnhancedAutoPostingService()
    return service.process_single_document_with_parallel_posting(document_number, company_code)

def get_enhanced_statistics(company_code: str = None, days_back: int = 30) -> Dict:
    """Get enhanced posting statistics including parallel ledger performance."""
    service = EnhancedAutoPostingService()
    return service.get_enhanced_posting_statistics(company_code, days_back)

def validate_document_balances(document_number: str, company_code: str) -> Dict:
    """Validate parallel ledger balance consistency for a document."""
    service = EnhancedAutoPostingService()
    return service.validate_parallel_ledger_balances(document_number, company_code)

# Test function
def test_enhanced_auto_posting():
    """Test the enhanced auto-posting service."""
    service = EnhancedAutoPostingService()
    
    print("=== Enhanced Auto-Posting Service Test ===")
    
    # Test configuration
    print("Service initialized with:")
    print(f"  Base auto-posting: {type(service.base_auto_posting).__name__}")
    print(f"  Parallel posting: {type(service.parallel_posting).__name__}")
    print(f"  System user: {service.system_user}")
    
    # Test statistics
    try:
        stats = service.get_enhanced_posting_statistics(days_back=7)
        print(f"Statistics retrieved: {len(stats)} sections")
    except Exception as e:
        print(f"Statistics test failed: {e}")
    
    print("✅ Enhanced Auto-Posting Service: Initialized and ready")

if __name__ == "__main__":
    test_enhanced_auto_posting()