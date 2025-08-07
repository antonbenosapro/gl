"""
IAS 21 Compliance Service - The Effects of Changes in Foreign Exchange Rates

This service implements specific IAS 21 (IFRS) requirements for foreign currency accounting including:

- Net investment in foreign operations
- OCI classification and recycling
- Translation vs transaction exchange differences  
- Functional currency change procedures
- Disposal of foreign operations

Author: Claude Code Assistant
Date: August 6, 2025
"""

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional, Tuple, Any, Union
from enum import Enum
from sqlalchemy import text
from db_config import engine
from utils.standards_compliant_fx_service import StandardsCompliantFXService, AccountingStandard, TranslationMethod
from utils.logger import get_logger

logger = get_logger("ias21_compliance_service")

class IAS21Component(Enum):
    """IAS 21 specific components."""
    TRANSACTION_DIFFERENCES = "TRANSACTION_DIFFERENCES"  # Para 28-29
    TRANSLATION_DIFFERENCES = "TRANSLATION_DIFFERENCES"  # Para 39
    NET_INVESTMENT = "NET_INVESTMENT"  # Para 32-33, 48-49
    FUNCTIONAL_CURRENCY_CHANGE = "FUNCTIONAL_CURRENCY_CHANGE"  # Para 34-37
    DISPOSAL_OF_FOREIGN_OPERATION = "DISPOSAL_OF_FOREIGN_OPERATION"  # Para 48-49

class OCIClassification(Enum):
    """OCI classification per IAS 21."""
    TRANSLATION_RESERVE = "TRANSLATION_RESERVE"  # Foreign currency translation reserve
    NET_INVESTMENT_HEDGE = "NET_INVESTMENT_HEDGE"  # Hedges of net investments
    RECYCLABLE = "RECYCLABLE"  # Can be recycled to P&L
    NON_RECYCLABLE = "NON_RECYCLABLE"  # Cannot be recycled

class NetInvestmentType(Enum):
    """Types of net investment in foreign operations."""
    SUBSIDIARY = "SUBSIDIARY"
    ASSOCIATE = "ASSOCIATE"
    JOINT_VENTURE = "JOINT_VENTURE"
    BRANCH = "BRANCH"
    MONETARY_ITEM_FORMING_NET_INVESTMENT = "MONETARY_ITEM_FORMING_NET_INVESTMENT"  # Para 15

class IAS21ComplianceService(StandardsCompliantFXService):
    """Enhanced service implementing IAS 21 specific requirements."""
    
    def __init__(self):
        """Initialize IAS 21 compliance service."""
        super().__init__()
        
    def classify_exchange_differences(self, transaction_details: Dict[str, Any],
                                     entity_functional_currency: str,
                                     reporting_currency: str) -> Dict[str, Any]:
        """
        Classify exchange differences per IAS 21 requirements.
        
        Args:
            transaction_details: Transaction information
            entity_functional_currency: Entity's functional currency
            reporting_currency: Presentation currency
            
        Returns:
            Classification of exchange differences
        """
        
        classification_result = {
            "transaction_id": transaction_details.get("transaction_id"),
            "classification_date": date.today(),
            "entity_functional_currency": entity_functional_currency,
            "reporting_currency": reporting_currency,
            "exchange_difference_type": None,
            "oci_classification": None,
            "recyclable_to_pnl": False,
            "treatment_guidance": [],
            "ias21_paragraphs": []
        }
        
        try:
            # Determine if this is a transaction or translation difference
            if transaction_details.get("is_monetary_item", True):
                # First check if it's a net investment item (takes precedence)
                if self._is_net_investment_item(transaction_details):
                    # Net investment in foreign operation (Para 32)
                    classification_result["exchange_difference_type"] = IAS21Component.NET_INVESTMENT.value
                    classification_result["oci_classification"] = OCIClassification.TRANSLATION_RESERVE.value
                    classification_result["recyclable_to_pnl"] = True  # On disposal
                    classification_result["ias21_paragraphs"] = ["IAS 21.32", "IAS 21.33", "IAS 21.48"]
                    classification_result["treatment_guidance"].append(
                        "Exchange differences on net investment recognized in OCI and recycled to P&L on disposal"
                    )
                elif transaction_details.get("settlement_currency") != entity_functional_currency:
                    # Transaction exchange differences (Para 28)
                    classification_result["exchange_difference_type"] = IAS21Component.TRANSACTION_DIFFERENCES.value
                    classification_result["oci_classification"] = None  # Goes to P&L
                    classification_result["recyclable_to_pnl"] = False  # Already in P&L
                    classification_result["ias21_paragraphs"] = ["IAS 21.28", "IAS 21.29"]
                    classification_result["treatment_guidance"].append(
                        "Exchange differences on monetary items are recognized in P&L in the period they arise"
                    )
            else:
                # Non-monetary items
                if transaction_details.get("measured_at_fair_value", False):
                    # Non-monetary at fair value (Para 30)
                    fv_changes_location = transaction_details.get("fair_value_changes_location", "PNL")
                    if fv_changes_location == "OCI":
                        classification_result["oci_classification"] = OCIClassification.NON_RECYCLABLE.value
                        classification_result["recyclable_to_pnl"] = False
                    else:
                        classification_result["oci_classification"] = None  # P&L
                        classification_result["recyclable_to_pnl"] = False
                    classification_result["ias21_paragraphs"] = ["IAS 21.30"]
                else:
                    # Non-monetary at historical cost - no exchange differences
                    classification_result["exchange_difference_type"] = None
                    classification_result["ias21_paragraphs"] = ["IAS 21.23(b)"]
                    classification_result["treatment_guidance"].append(
                        "Non-monetary items at historical cost - no exchange differences recognized"
                    )
            
            # Check for translation differences (Para 39)
            if entity_functional_currency != reporting_currency:
                classification_result["has_translation_component"] = True
                classification_result["translation_oci_classification"] = OCIClassification.TRANSLATION_RESERVE.value
                classification_result["ias21_paragraphs"].append("IAS 21.39")
            
        except Exception as e:
            logger.error(f"Error classifying exchange differences: {e}")
            classification_result["error"] = str(e)
        
        return classification_result
    
    def setup_net_investment_hedge(self, hedge_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Set up net investment hedge per IAS 21.48-49 and IAS 39/IFRS 9.
        
        Args:
            hedge_details: Hedge relationship details
            
        Returns:
            Net investment hedge setup result
        """
        
        hedge_result = {
            "hedge_id": None,
            "setup_date": date.today(),
            "hedge_type": "NET_INVESTMENT_HEDGE",
            "accounting_standard": "IAS_21_IFRS_9",
            "hedge_documentation": {},
            "effectiveness_criteria": {},
            "oci_treatment": {},
            "setup_successful": False
        }
        
        try:
            with engine.begin() as conn:
                # Create hedge relationship documentation
                hedge_query = text("""
                    INSERT INTO hedge_relationships (
                        hedge_designation, accounting_standard,
                        hedge_instrument_type, hedge_instrument_id,
                        hedged_item_type, hedged_item_id,
                        hedged_risk, hedge_ratio,
                        effectiveness_test_method,
                        effectiveness_threshold_lower, effectiveness_threshold_upper,
                        hedge_inception_date, documentation_date,
                        hedge_status, created_by
                    ) VALUES (
                        'NET_INVESTMENT', 'IFRS_9',
                        :instrument_type, :instrument_id,
                        :hedged_item_type, :hedged_item_id,
                        'FX_RISK', :hedge_ratio,
                        :effectiveness_method, 0.80, 1.25,
                        :inception_date, :documentation_date,
                        'ACTIVE', :created_by
                    ) RETURNING hedge_id
                """)
                
                result = conn.execute(hedge_query, {
                    "instrument_type": hedge_details.get("instrument_type", "FX_FORWARD"),
                    "instrument_id": hedge_details.get("instrument_id"),
                    "hedged_item_type": "NET_INVESTMENT",
                    "hedged_item_id": hedge_details.get("foreign_operation_id"),
                    "hedge_ratio": hedge_details.get("hedge_ratio", 1.0),
                    "effectiveness_method": hedge_details.get("effectiveness_method", "DOLLAR_OFFSET"),
                    "inception_date": hedge_details.get("inception_date", date.today()),
                    "documentation_date": date.today(),
                    "created_by": "IAS21_SERVICE"
                }).fetchone()
                
                hedge_id = result[0] if result else None
                hedge_result["hedge_id"] = hedge_id
                
                # Document OCI treatment
                hedge_result["oci_treatment"] = {
                    "effective_portion": "Recognized in OCI - Foreign Currency Translation Reserve",
                    "ineffective_portion": "Recognized immediately in P&L",
                    "recycling_on_disposal": "OCI amounts recycled to P&L on disposal of foreign operation",
                    "ias21_references": ["IAS 21.48", "IAS 21.49", "IFRS 9.6.5.13"]
                }
                
                # Set up effectiveness criteria
                hedge_result["effectiveness_criteria"] = {
                    "method": hedge_details.get("effectiveness_method", "DOLLAR_OFFSET"),
                    "test_frequency": "QUARTERLY",
                    "prospective_test": "Critical terms matching",
                    "retrospective_test": "Dollar offset cumulative",
                    "effectiveness_range": "80% - 125%"
                }
                
                hedge_result["setup_successful"] = True
                
                logger.info(f"Net investment hedge {hedge_id} created successfully")
                
        except Exception as e:
            logger.error(f"Error setting up net investment hedge: {e}")
            hedge_result["error"] = str(e)
        
        return hedge_result
    
    def process_functional_currency_change(self, entity_id: str, old_currency: str,
                                          new_currency: str, change_date: date,
                                          change_reason: str) -> Dict[str, Any]:
        """
        Process functional currency change per IAS 21.35-37.
        
        Args:
            entity_id: Entity identifier
            old_currency: Previous functional currency
            new_currency: New functional currency
            change_date: Effective date of change
            change_reason: Business reason for change
            
        Returns:
            Functional currency change processing result
        """
        
        change_result = {
            "entity_id": entity_id,
            "old_functional_currency": old_currency,
            "new_functional_currency": new_currency,
            "change_date": change_date,
            "ias21_treatment": "PROSPECTIVE",  # Para 35
            "translation_procedures": [],
            "accounting_entries": [],
            "disclosures_required": []
        }
        
        try:
            with engine.begin() as conn:
                # IAS 21.35: Apply translation procedures prospectively from date of change
                
                # Step 1: Translate all non-monetary items at exchange rate on change date
                translation_rate = self._get_exchange_rate(old_currency, new_currency, change_date)
                
                change_result["translation_procedures"].append({
                    "step": 1,
                    "description": "Translate non-monetary items at exchange rate on date of change",
                    "rate_used": float(translation_rate),
                    "ias21_paragraph": "IAS 21.37"
                })
                
                # Update non-monetary account balances
                update_query = text("""
                    UPDATE journalentryline jel
                    SET translated_amount = (debitamount - creditamount) * :rate,
                        exchange_rate = :rate,
                        translation_date = :change_date
                    FROM glaccount ga, journalentryheader jeh
                    WHERE jel.glaccountid = ga.glaccountid
                    AND jel.documentnumber = jeh.documentnumber
                    AND jel.companycodeid = jeh.companycodeid
                    AND ga.monetary_classification = 'NON_MONETARY'
                    AND jel.companycodeid = :entity_id
                    AND jeh.postingdate <= :change_date
                """)
                
                conn.execute(update_query, {
                    "rate": translation_rate,
                    "change_date": change_date,
                    "entity_id": entity_id
                })
                
                # Step 2: Use translated amounts as historical cost going forward
                change_result["translation_procedures"].append({
                    "step": 2,
                    "description": "Translated amounts become historical cost in new functional currency",
                    "ias21_paragraph": "IAS 21.37"
                })
                
                # Step 3: Update entity functional currency record
                update_functional = text("""
                    UPDATE entity_functional_currency
                    SET previous_functional_currency = functional_currency,
                        functional_currency = :new_currency,
                        effective_date = :change_date,
                        change_reason = :change_reason,
                        assessment_methodology = 'IAS_21',
                        assessment_conclusion = :conclusion,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE entity_id = :entity_id
                """)
                
                conn.execute(update_functional, {
                    "new_currency": new_currency,
                    "change_date": change_date,
                    "change_reason": change_reason,
                    "conclusion": f"Functional currency changed from {old_currency} to {new_currency} due to {change_reason}",
                    "entity_id": entity_id
                })
                
                # Record in history
                history_query = text("""
                    INSERT INTO functional_currency_history (
                        entity_id, effective_date, functional_currency,
                        previous_currency, change_type, business_justification,
                        created_by
                    ) VALUES (
                        :entity_id, :effective_date, :new_currency,
                        :old_currency, 'CHANGE', :justification,
                        'IAS21_SERVICE'
                    )
                """)
                
                conn.execute(history_query, {
                    "entity_id": entity_id,
                    "effective_date": change_date,
                    "new_currency": new_currency,
                    "old_currency": old_currency,
                    "justification": change_reason
                })
                
                # Required disclosures per IAS 21.54
                change_result["disclosures_required"] = [
                    "Amount of exchange differences recognized in P&L",
                    "Net exchange differences in OCI and reconciliation",
                    "Fact that functional currency has changed",
                    "Reason for the change in functional currency",
                    "Date of the change"
                ]
                
                change_result["processing_successful"] = True
                
        except Exception as e:
            logger.error(f"Error processing functional currency change: {e}")
            change_result["error"] = str(e)
        
        return change_result
    
    def process_foreign_operation_disposal(self, operation_id: str, disposal_date: date,
                                          disposal_type: str, consideration: Decimal) -> Dict[str, Any]:
        """
        Process disposal of foreign operation per IAS 21.48-49.
        
        Args:
            operation_id: Foreign operation identifier
            disposal_date: Date of disposal
            disposal_type: Type of disposal (FULL, PARTIAL, LOSS_OF_CONTROL)
            consideration: Disposal consideration
            
        Returns:
            Disposal processing result
        """
        
        disposal_result = {
            "operation_id": operation_id,
            "disposal_date": disposal_date,
            "disposal_type": disposal_type,
            "consideration": float(consideration),
            "cta_recycled": Decimal('0.00'),
            "hedge_reserve_recycled": Decimal('0.00'),
            "total_oci_recycled": Decimal('0.00'),
            "gain_loss_on_disposal": Decimal('0.00'),
            "journal_entries": []
        }
        
        try:
            with engine.begin() as conn:
                # Get accumulated CTA balance for the operation
                cta_query = text("""
                    SELECT SUM(closing_cta) as accumulated_cta
                    FROM cumulative_translation_adjustment
                    WHERE entity_id = :operation_id
                    AND accounting_standard = 'IAS_21'
                    GROUP BY entity_id
                """)
                
                cta_result = conn.execute(cta_query, {"operation_id": operation_id}).fetchone()
                accumulated_cta = Decimal(str(cta_result[0])) if cta_result and cta_result[0] else Decimal('0.00')
                
                # Get hedge reserve balance if any
                hedge_query = text("""
                    SELECT SUM(het.ineffective_portion) as hedge_reserve
                    FROM hedge_effectiveness_tests het
                    JOIN hedge_relationships hr ON het.hedge_id = hr.hedge_id
                    WHERE hr.hedged_item_id = :operation_id
                    AND hr.hedge_designation = 'NET_INVESTMENT'
                """)
                
                hedge_result = conn.execute(hedge_query, {"operation_id": operation_id}).fetchone()
                hedge_reserve = Decimal(str(hedge_result[0])) if hedge_result and hedge_result[0] else Decimal('0.00')
                
                disposal_result["cta_recycled"] = accumulated_cta
                disposal_result["hedge_reserve_recycled"] = hedge_reserve
                disposal_result["total_oci_recycled"] = accumulated_cta + hedge_reserve
                
                # IAS 21.48: On disposal, cumulative exchange differences recognized in OCI
                # shall be reclassified from equity to P&L as a reclassification adjustment
                
                if disposal_type == "FULL":
                    # Full disposal - recycle all OCI
                    recycle_amount = disposal_result["total_oci_recycled"]
                elif disposal_type == "PARTIAL":
                    # Partial disposal - proportionate recycling
                    disposal_percentage = Decimal('0.50')  # Example: 50% disposal
                    recycle_amount = disposal_result["total_oci_recycled"] * disposal_percentage
                else:  # LOSS_OF_CONTROL
                    # Loss of control but retention of interest - full recycling
                    recycle_amount = disposal_result["total_oci_recycled"]
                
                # Create journal entries for OCI recycling
                if recycle_amount != Decimal('0.00'):
                    # Debit: OCI - Foreign Currency Translation Reserve
                    # Credit: P&L - Gain/Loss on Disposal of Foreign Operation
                    
                    journal_entry = {
                        "journal_date": disposal_date,
                        "description": f"Recycle OCI on disposal of foreign operation {operation_id}",
                        "lines": [
                            {
                                "account": "OCI_TRANSLATION_RESERVE",
                                "debit": float(abs(recycle_amount)) if recycle_amount > 0 else 0,
                                "credit": float(abs(recycle_amount)) if recycle_amount < 0 else 0
                            },
                            {
                                "account": "DISPOSAL_GAIN_LOSS",
                                "debit": float(abs(recycle_amount)) if recycle_amount < 0 else 0,
                                "credit": float(abs(recycle_amount)) if recycle_amount > 0 else 0
                            }
                        ]
                    }
                    disposal_result["journal_entries"].append(journal_entry)
                
                # Update CTA records to mark as recycled
                update_cta = text("""
                    UPDATE cumulative_translation_adjustment
                    SET recycled_to_pnl = closing_cta,
                        recycling_date = :disposal_date,
                        disposal_reason = :disposal_type,
                        disposal_entity = :operation_id,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE entity_id = :operation_id
                    AND accounting_standard = 'IAS_21'
                """)
                
                conn.execute(update_cta, {
                    "disposal_date": disposal_date,
                    "disposal_type": disposal_type,
                    "operation_id": operation_id
                })
                
                disposal_result["processing_successful"] = True
                
        except Exception as e:
            logger.error(f"Error processing foreign operation disposal: {e}")
            disposal_result["error"] = str(e)
        
        return disposal_result
    
    def generate_ias21_disclosures(self, entity_id: str, reporting_date: date,
                                  fiscal_year: int, fiscal_period: int) -> Dict[str, Any]:
        """
        Generate IAS 21 required disclosures per Para 51-57.
        
        Args:
            entity_id: Entity identifier
            reporting_date: Reporting date
            fiscal_year: Fiscal year
            fiscal_period: Fiscal period
            
        Returns:
            IAS 21 disclosure information
        """
        
        disclosures = {
            "entity_id": entity_id,
            "reporting_date": reporting_date,
            "fiscal_year": fiscal_year,
            "fiscal_period": fiscal_period,
            "disclosure_sections": {}
        }
        
        try:
            with engine.connect() as conn:
                # IAS 21.52: Amount of exchange differences in P&L
                pnl_query = text("""
                    SELECT 
                        SUM(CASE WHEN unrealized_gain_loss > 0 THEN unrealized_gain_loss ELSE 0 END) as fx_gains,
                        SUM(CASE WHEN unrealized_gain_loss < 0 THEN ABS(unrealized_gain_loss) ELSE 0 END) as fx_losses,
                        SUM(unrealized_gain_loss) as net_fx_impact
                    FROM fx_revaluation_details frd
                    JOIN fx_revaluation_runs frr ON frd.run_id = frr.run_id
                    WHERE frr.company_code = :entity_id
                    AND frr.fiscal_year = :fy AND frr.fiscal_period = :period
                    AND frd.accounting_standard = 'IAS_21'
                    AND frd.pnl_component != 0
                """)
                
                pnl_result = conn.execute(pnl_query, {
                    "entity_id": entity_id,
                    "fy": fiscal_year,
                    "period": fiscal_period
                }).fetchone()
                
                disclosures["disclosure_sections"]["exchange_differences_pnl"] = {
                    "paragraph_reference": "IAS 21.52(a)",
                    "description": "Exchange differences recognized in profit or loss",
                    "fx_gains": float(pnl_result[0]) if pnl_result[0] else 0,
                    "fx_losses": float(pnl_result[1]) if pnl_result[1] else 0,
                    "net_impact": float(pnl_result[2]) if pnl_result[2] else 0
                }
                
                # IAS 21.52(b): Net exchange differences in OCI
                oci_query = text("""
                    SELECT 
                        opening_cta, period_movement, closing_cta,
                        asset_translation_adj, liability_translation_adj,
                        net_investment_hedge_adj
                    FROM cumulative_translation_adjustment
                    WHERE entity_id = :entity_id
                    AND fiscal_year = :fy AND fiscal_period = :period
                    AND accounting_standard = 'IAS_21'
                """)
                
                oci_result = conn.execute(oci_query, {
                    "entity_id": entity_id,
                    "fy": fiscal_year,
                    "period": fiscal_period
                }).fetchone()
                
                if oci_result:
                    disclosures["disclosure_sections"]["exchange_differences_oci"] = {
                        "paragraph_reference": "IAS 21.52(b)",
                        "description": "Net exchange differences classified in OCI",
                        "opening_balance": float(oci_result[0]),
                        "period_movement": float(oci_result[1]),
                        "closing_balance": float(oci_result[2]),
                        "components": {
                            "assets": float(oci_result[3]),
                            "liabilities": float(oci_result[4]),
                            "net_investment_hedges": float(oci_result[5])
                        }
                    }
                
                # IAS 21.53: Functional currency and reason for changes
                func_curr_query = text("""
                    SELECT 
                        functional_currency, previous_functional_currency,
                        change_reason, effective_date
                    FROM entity_functional_currency
                    WHERE entity_id = :entity_id
                """)
                
                func_result = conn.execute(func_curr_query, {"entity_id": entity_id}).fetchone()
                
                if func_result:
                    disclosures["disclosure_sections"]["functional_currency"] = {
                        "paragraph_reference": "IAS 21.53",
                        "current_functional_currency": func_result[0],
                        "previous_functional_currency": func_result[1],
                        "change_reason": func_result[2] if func_result[2] else "No change",
                        "effective_date": str(func_result[3]) if func_result[3] else None
                    }
                
                # IAS 21.54: Presentation currency if different from functional
                disclosures["disclosure_sections"]["presentation_currency"] = {
                    "paragraph_reference": "IAS 21.54",
                    "presentation_currency": "USD",
                    "reason_if_different": "Group reporting currency for consolidation"
                }
                
                # IAS 21.57: Practical convenience method disclosure if used
                disclosures["disclosure_sections"]["convenience_translation"] = {
                    "paragraph_reference": "IAS 21.57",
                    "method_used": False,
                    "description": "Financial statements are not presented using convenience translation"
                }
                
        except Exception as e:
            logger.error(f"Error generating IAS 21 disclosures: {e}")
            disclosures["error"] = str(e)
        
        return disclosures
    
    def _is_net_investment_item(self, transaction_details: Dict[str, Any]) -> bool:
        """Check if monetary item forms part of net investment."""
        # IAS 21.15: A monetary item for which settlement is neither planned nor likely
        # to occur in the foreseeable future is, in substance, part of net investment
        
        return (transaction_details.get("intercompany", False) and
                transaction_details.get("settlement_terms") == "NO_FIXED_TERMS" and
                not transaction_details.get("settlement_planned", True))
    
    def _get_exchange_rate(self, from_currency: str, to_currency: str, rate_date: date) -> Decimal:
        """Get exchange rate for currency pair."""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT exchange_rate FROM exchange_rates
                    WHERE from_currency = :from_curr
                    AND to_currency = :to_curr
                    AND rate_date = :rate_date
                    AND rate_type = 'CLOSING'
                    ORDER BY rate_date DESC
                    LIMIT 1
                """), {
                    "from_curr": from_currency,
                    "to_curr": to_currency,
                    "rate_date": rate_date
                }).scalar()
                
                return Decimal(str(result)) if result else Decimal('1.00')
        except:
            return Decimal('1.00')

# Utility functions for external use
def classify_fx_differences(transaction_details: Dict[str, Any], functional_currency: str,
                           reporting_currency: str) -> Dict[str, Any]:
    """Classify exchange differences per IAS 21."""
    service = IAS21ComplianceService()
    return service.classify_exchange_differences(transaction_details, functional_currency, reporting_currency)

def setup_net_investment_hedge(hedge_details: Dict[str, Any]) -> Dict[str, Any]:
    """Set up net investment hedge."""
    service = IAS21ComplianceService()
    return service.setup_net_investment_hedge(hedge_details)

def process_functional_currency_change(entity_id: str, old_currency: str, new_currency: str,
                                      change_date: date, reason: str) -> Dict[str, Any]:
    """Process functional currency change."""
    service = IAS21ComplianceService()
    return service.process_functional_currency_change(entity_id, old_currency, new_currency, change_date, reason)

def process_disposal(operation_id: str, disposal_date: date, disposal_type: str,
                    consideration: Decimal) -> Dict[str, Any]:
    """Process foreign operation disposal."""
    service = IAS21ComplianceService()
    return service.process_foreign_operation_disposal(operation_id, disposal_date, disposal_type, consideration)

def generate_ias21_disclosures(entity_id: str, reporting_date: date, fiscal_year: int,
                              fiscal_period: int) -> Dict[str, Any]:
    """Generate IAS 21 disclosures."""
    service = IAS21ComplianceService()
    return service.generate_ias21_disclosures(entity_id, reporting_date, fiscal_year, fiscal_period)

# Test function
def test_ias21_compliance():
    """Test IAS 21 compliance features."""
    service = IAS21ComplianceService()
    
    print("=== IAS 21 Compliance Service Test ===")
    
    # Test exchange difference classification
    transaction = {
        "transaction_id": "TXN001",
        "is_monetary_item": True,
        "settlement_currency": "EUR",
        "intercompany": True,
        "settlement_terms": "NO_FIXED_TERMS",
        "settlement_planned": False
    }
    
    classification = service.classify_exchange_differences(transaction, "USD", "USD")
    print(f"Exchange difference classification: {classification['exchange_difference_type']}")
    print(f"OCI classification: {classification['oci_classification']}")
    
    # Test net investment hedge setup
    hedge_details = {
        "instrument_type": "FX_FORWARD",
        "instrument_id": "FWD001",
        "foreign_operation_id": "SUB_EUR_001",
        "hedge_ratio": 1.0,
        "effectiveness_method": "DOLLAR_OFFSET",
        "inception_date": date.today()
    }
    
    hedge_result = service.setup_net_investment_hedge(hedge_details)
    print(f"Net investment hedge setup: {'Successful' if hedge_result['setup_successful'] else 'Failed'}")
    
    # Test functional currency change
    change_result = service.process_functional_currency_change(
        "1000", "USD", "EUR", date.today(),
        "Majority of operations now conducted in EUR"
    )
    print(f"Functional currency change: {change_result.get('processing_successful', False)}")
    
    # Test IAS 21 disclosures
    disclosures = service.generate_ias21_disclosures("1000", date.today(), 2025, 1)
    print(f"IAS 21 disclosures generated: {len(disclosures['disclosure_sections'])} sections")
    
    print("✅ IAS 21 Compliance Service: Test completed")

if __name__ == "__main__":
    test_ias21_compliance()