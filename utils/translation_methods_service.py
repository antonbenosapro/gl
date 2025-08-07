"""
Translation Methods Service - Current Rate and Temporal Methods

This service implements the two primary translation methods required by IAS 21 and ASC 830:
- Current Rate Method (IAS 21.39, ASC 830-30)
- Temporal Method (ASC 830-20, remeasurement)

Author: Claude Code Assistant
Date: August 6, 2025
"""

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
from sqlalchemy import text
from db_config import engine
from utils.currency_service import CurrencyTranslationService
from utils.logger import get_logger

logger = get_logger("translation_methods_service")

class TranslationMethodType(Enum):
    """Translation method types."""
    CURRENT_RATE_METHOD = "CURRENT_RATE_METHOD"  # All assets/liabilities at current rate
    TEMPORAL_METHOD = "TEMPORAL_METHOD"  # Monetary at current, non-monetary at historical

class AccountTranslationRate(Enum):
    """Rate types for account translation."""
    CURRENT = "CURRENT"  # Closing rate at period end
    HISTORICAL = "HISTORICAL"  # Rate when item was acquired
    AVERAGE = "AVERAGE"  # Weighted average for period
    SPECIFIC = "SPECIFIC"  # Specific rate for transaction

class FinancialStatementItem(Enum):
    """Financial statement classification."""
    ASSETS = "ASSETS"
    LIABILITIES = "LIABILITIES"
    EQUITY = "EQUITY"
    REVENUE = "REVENUE"
    EXPENSES = "EXPENSES"
    GAINS_LOSSES = "GAINS_LOSSES"

class TranslationMethodsService:
    """Service implementing current rate and temporal translation methods."""
    
    def __init__(self):
        """Initialize translation methods service."""
        self.currency_service = CurrencyTranslationService()
        
    def apply_current_rate_method(self, entity_id: str, functional_currency: str,
                                 presentation_currency: str, translation_date: date,
                                 fiscal_year: int, fiscal_period: int) -> Dict[str, Any]:
        """
        Apply current rate method per IAS 21.39 and ASC 830-30.
        
        Under current rate method:
        - All assets and liabilities: Current exchange rate
        - Equity: Historical rates
        - Income and expenses: Exchange rates at transaction dates (or average)
        - Resulting exchange differences: Recognized in OCI
        
        Args:
            entity_id: Entity identifier
            functional_currency: Entity's functional currency
            presentation_currency: Reporting/presentation currency
            translation_date: Date for translation
            fiscal_year: Fiscal year
            fiscal_period: Fiscal period
            
        Returns:
            Translation results with current rate method
        """
        
        translation_result = {
            "entity_id": entity_id,
            "method": TranslationMethodType.CURRENT_RATE_METHOD.value,
            "functional_currency": functional_currency,
            "presentation_currency": presentation_currency,
            "translation_date": translation_date,
            "fiscal_year": fiscal_year,
            "fiscal_period": fiscal_period,
            "exchange_rates_used": {},
            "translated_balances": {},
            "translation_adjustment": Decimal('0.00'),
            "oci_impact": Decimal('0.00')
        }
        
        try:
            # Get exchange rates
            current_rate = self._get_closing_rate(functional_currency, presentation_currency, translation_date)
            average_rate = self._get_average_rate(functional_currency, presentation_currency, fiscal_year, fiscal_period)
            
            translation_result["exchange_rates_used"] = {
                "current_rate": float(current_rate),
                "average_rate": float(average_rate),
                "rate_date": str(translation_date)
            }
            
            with engine.connect() as conn:
                # Translate assets and liabilities at current rate
                assets_liabilities_query = text("""
                    SELECT 
                        ga.glaccountid,
                        ga.accountname,
                        ga.accounttype,
                        ga.monetary_classification,
                        SUM(CASE 
                            WHEN ga.accounttype IN ('ASSETS', 'EXPENSES') 
                            THEN jel.debitamount - jel.creditamount
                            ELSE jel.creditamount - jel.debitamount
                        END) as balance_fc
                    FROM journalentryline jel
                    JOIN glaccount ga ON jel.glaccountid = ga.glaccountid
                    JOIN journalentryheader jeh ON jel.documentnumber = jeh.documentnumber 
                        AND jel.companycodeid = jeh.companycodeid
                    WHERE jel.companycodeid = :entity_id
                    AND ga.accounttype IN ('ASSETS', 'LIABILITIES')
                    AND jeh.postingdate <= :translation_date
                    AND jeh.workflow_status = 'POSTED'
                    GROUP BY ga.glaccountid, ga.accountname, ga.accounttype, ga.monetary_classification
                    HAVING SUM(CASE 
                        WHEN ga.accounttype IN ('ASSETS', 'EXPENSES') 
                        THEN jel.debitamount - jel.creditamount
                        ELSE jel.creditamount - jel.debitamount
                    END) != 0
                """)
                
                assets_liabilities = conn.execute(assets_liabilities_query, {
                    "entity_id": entity_id,
                    "translation_date": translation_date
                }).mappings().fetchall()
                
                total_assets_translated = Decimal('0.00')
                total_liabilities_translated = Decimal('0.00')
                
                for account in assets_liabilities:
                    balance_fc = Decimal(str(account['balance_fc'])) if account['balance_fc'] else Decimal('0.00')
                    # Current rate method: All A&L at current rate
                    balance_translated = balance_fc * current_rate
                    
                    account_key = f"{account['glaccountid']}_{account['accountname']}"
                    translation_result["translated_balances"][account_key] = {
                        "account_type": account['accounttype'],
                        "balance_fc": float(balance_fc),
                        "rate_applied": float(current_rate),
                        "balance_translated": float(balance_translated),
                        "rate_type": AccountTranslationRate.CURRENT.value
                    }
                    
                    if account['accounttype'] == 'ASSETS':
                        total_assets_translated += balance_translated
                    else:
                        total_liabilities_translated += balance_translated
                
                # Translate equity at historical rates
                equity_query = text("""
                    SELECT 
                        ga.glaccountid,
                        ga.accountname,
                        SUM(jel.creditamount - jel.debitamount) as balance_fc,
                        AVG(COALESCE(jel.exchange_rate, 1.000000)) as historical_rate
                    FROM journalentryline jel
                    JOIN glaccount ga ON jel.glaccountid = ga.glaccountid
                    JOIN journalentryheader jeh ON jel.documentnumber = jeh.documentnumber
                        AND jel.companycodeid = jeh.companycodeid
                    WHERE jel.companycodeid = :entity_id
                    AND ga.accounttype = 'EQUITY'
                    AND jeh.postingdate <= :translation_date
                    AND jeh.workflow_status = 'POSTED'
                    GROUP BY ga.glaccountid, ga.accountname
                """)
                
                equity_accounts = conn.execute(equity_query, {
                    "entity_id": entity_id,
                    "translation_date": translation_date
                }).mappings().fetchall()
                
                total_equity_translated = Decimal('0.00')
                
                for account in equity_accounts:
                    balance_fc = Decimal(str(account['balance_fc'])) if account['balance_fc'] else Decimal('0.00')
                    historical_rate = Decimal(str(account['historical_rate'])) if account['historical_rate'] else current_rate
                    balance_translated = balance_fc * historical_rate
                    
                    account_key = f"{account['glaccountid']}_{account['accountname']}"
                    translation_result["translated_balances"][account_key] = {
                        "account_type": "EQUITY",
                        "balance_fc": float(balance_fc),
                        "rate_applied": float(historical_rate),
                        "balance_translated": float(balance_translated),
                        "rate_type": AccountTranslationRate.HISTORICAL.value
                    }
                    
                    total_equity_translated += balance_translated
                
                # Translate income and expenses at average rate
                income_expense_query = text("""
                    SELECT 
                        ga.glaccountid,
                        ga.accountname,
                        ga.accounttype,
                        SUM(CASE 
                            WHEN ga.accounttype = 'REVENUE' 
                            THEN jel.creditamount - jel.debitamount
                            ELSE jel.debitamount - jel.creditamount
                        END) as balance_fc
                    FROM journalentryline jel
                    JOIN glaccount ga ON jel.glaccountid = ga.glaccountid
                    JOIN journalentryheader jeh ON jel.documentnumber = jeh.documentnumber
                        AND jel.companycodeid = jeh.companycodeid
                    WHERE jel.companycodeid = :entity_id
                    AND ga.accounttype IN ('REVENUE', 'EXPENSES')
                    AND jeh.fiscalyear = :fiscal_year
                    AND jeh.period = :fiscal_period
                    AND jeh.workflow_status = 'POSTED'
                    GROUP BY ga.glaccountid, ga.accountname, ga.accounttype
                """)
                
                income_expenses = conn.execute(income_expense_query, {
                    "entity_id": entity_id,
                    "fiscal_year": fiscal_year,
                    "fiscal_period": fiscal_period
                }).mappings().fetchall()
                
                total_income_translated = Decimal('0.00')
                total_expense_translated = Decimal('0.00')
                
                for account in income_expenses:
                    balance_fc = Decimal(str(account['balance_fc']))
                    # Current rate method: P&L at average rate
                    balance_translated = balance_fc * average_rate
                    
                    account_key = f"{account['glaccountid']}_{account['accountname']}"
                    translation_result["translated_balances"][account_key] = {
                        "account_type": account['accounttype'],
                        "balance_fc": float(balance_fc),
                        "rate_applied": float(average_rate),
                        "balance_translated": float(balance_translated),
                        "rate_type": AccountTranslationRate.AVERAGE.value
                    }
                    
                    if account['accounttype'] == 'REVENUE':
                        total_income_translated += balance_translated
                    else:
                        total_expense_translated += balance_translated
                
                # Calculate translation adjustment (balancing figure to OCI)
                net_assets_translated = total_assets_translated - total_liabilities_translated
                net_income_translated = total_income_translated - total_expense_translated
                beginning_equity_expected = net_assets_translated - net_income_translated
                
                translation_adjustment = beginning_equity_expected - total_equity_translated
                translation_result["translation_adjustment"] = translation_adjustment
                translation_result["oci_impact"] = translation_adjustment
                
                # Save translation results
                self._save_translation_results(translation_result)
                
                logger.info(f"Current rate method translation completed for {entity_id}")
                
        except Exception as e:
            logger.error(f"Error applying current rate method: {e}")
            translation_result["error"] = str(e)
        
        return translation_result
    
    def apply_temporal_method(self, entity_id: str, functional_currency: str,
                             reporting_currency: str, translation_date: date,
                             fiscal_year: int, fiscal_period: int) -> Dict[str, Any]:
        """
        Apply temporal method (remeasurement) per ASC 830-20.
        
        Under temporal method:
        - Monetary items: Current exchange rate
        - Non-monetary items: Historical rates
        - Income statement: Historical rates (except depreciation)
        - Resulting exchange differences: Recognized in P&L
        
        Args:
            entity_id: Entity identifier
            functional_currency: Functional currency
            reporting_currency: Reporting currency
            translation_date: Date for translation
            fiscal_year: Fiscal year
            fiscal_period: Fiscal period
            
        Returns:
            Translation results with temporal method
        """
        
        translation_result = {
            "entity_id": entity_id,
            "method": TranslationMethodType.TEMPORAL_METHOD.value,
            "functional_currency": functional_currency,
            "reporting_currency": reporting_currency,
            "translation_date": translation_date,
            "fiscal_year": fiscal_year,
            "fiscal_period": fiscal_period,
            "exchange_rates_used": {},
            "translated_balances": {},
            "remeasurement_gain_loss": Decimal('0.00'),
            "pnl_impact": Decimal('0.00')
        }
        
        try:
            # Get exchange rates
            current_rate = self._get_closing_rate(functional_currency, reporting_currency, translation_date)
            average_rate = self._get_average_rate(functional_currency, reporting_currency, fiscal_year, fiscal_period)
            
            translation_result["exchange_rates_used"] = {
                "current_rate": float(current_rate),
                "average_rate": float(average_rate),
                "rate_date": str(translation_date)
            }
            
            with engine.connect() as conn:
                # Translate monetary items at current rate
                monetary_query = text("""
                    SELECT 
                        ga.glaccountid,
                        ga.accountname,
                        ga.accounttype,
                        ga.monetary_classification,
                        SUM(CASE 
                            WHEN ga.accounttype IN ('ASSETS', 'EXPENSES') 
                            THEN jel.debitamount - jel.creditamount
                            ELSE jel.creditamount - jel.debitamount
                        END) as balance_fc
                    FROM journalentryline jel
                    JOIN glaccount ga ON jel.glaccountid = ga.glaccountid
                    JOIN journalentryheader jeh ON jel.documentnumber = jeh.documentnumber
                    WHERE jel.companycodeid = :entity_id
                    AND ga.monetary_classification = 'MONETARY'
                    AND jeh.postingdate <= :translation_date
                    AND jeh.workflow_status = 'POSTED'
                    GROUP BY ga.glaccountid, ga.accountname, ga.accounttype, ga.monetary_classification
                """)
                
                monetary_items = conn.execute(monetary_query, {
                    "entity_id": entity_id,
                    "translation_date": translation_date
                }).fetchall()
                
                total_monetary_translated = Decimal('0.00')
                
                for account in monetary_items:
                    balance_fc = Decimal(str(account['balance_fc']))
                    # Temporal method: Monetary at current rate
                    balance_translated = balance_fc * current_rate
                    
                    account_key = f"{account['glaccountid']}_{account['accountname']}"
                    translation_result["translated_balances"][account_key] = {
                        "account_type": account['accounttype'],
                        "monetary_classification": account['monetary_classification'],
                        "balance_fc": float(balance_fc),
                        "rate_applied": float(current_rate),
                        "balance_translated": float(balance_translated),
                        "rate_type": AccountTranslationRate.CURRENT.value
                    }
                    
                    total_monetary_translated += balance_translated
                
                # Translate non-monetary items at historical rates
                non_monetary_query = text("""
                    SELECT 
                        ga.glaccountid,
                        ga.accountname,
                        ga.accounttype,
                        ga.monetary_classification,
                        jel.debitamount - jel.creditamount as balance_fc,
                        jel.exchange_rate as historical_rate,
                        jeh.postingdate as acquisition_date
                    FROM journalentryline jel
                    JOIN glaccount ga ON jel.glaccountid = ga.glaccountid
                    JOIN journalentryheader jeh ON jel.documentnumber = jeh.documentnumber
                    WHERE jel.companycodeid = :entity_id
                    AND ga.monetary_classification = 'NON_MONETARY'
                    AND jeh.postingdate <= :translation_date
                    AND jeh.workflow_status = 'POSTED'
                    ORDER BY jeh.postingdate
                """)
                
                non_monetary_items = conn.execute(non_monetary_query, {
                    "entity_id": entity_id,
                    "translation_date": translation_date
                }).fetchall()
                
                non_monetary_by_account = {}
                
                for item in non_monetary_items:
                    account_id = item['glaccountid']
                    if account_id not in non_monetary_by_account:
                        non_monetary_by_account[account_id] = {
                            "accountname": item['accountname'],
                            "accounttype": item['accounttype'],
                            "items": []
                        }
                    
                    non_monetary_by_account[account_id]["items"].append({
                        "balance_fc": Decimal(str(item['balance_fc'])),
                        "historical_rate": Decimal(str(item['historical_rate'])) if item['historical_rate'] else current_rate,
                        "acquisition_date": item['acquisition_date']
                    })
                
                total_non_monetary_translated = Decimal('0.00')
                
                for account_id, account_data in non_monetary_by_account.items():
                    total_balance_fc = Decimal('0.00')
                    total_balance_translated = Decimal('0.00')
                    weighted_rate = Decimal('0.00')
                    
                    for item in account_data["items"]:
                        balance_fc = item["balance_fc"]
                        historical_rate = item["historical_rate"]
                        total_balance_fc += balance_fc
                        total_balance_translated += balance_fc * historical_rate
                    
                    if total_balance_fc != 0:
                        weighted_rate = total_balance_translated / total_balance_fc
                    
                    account_key = f"{account_id}_{account_data['accountname']}"
                    translation_result["translated_balances"][account_key] = {
                        "account_type": account_data['accounttype'],
                        "monetary_classification": "NON_MONETARY",
                        "balance_fc": float(total_balance_fc),
                        "rate_applied": float(weighted_rate),
                        "balance_translated": float(total_balance_translated),
                        "rate_type": AccountTranslationRate.HISTORICAL.value
                    }
                    
                    total_non_monetary_translated += total_balance_translated
                
                # Calculate remeasurement gain/loss (goes to P&L)
                total_translated = total_monetary_translated + total_non_monetary_translated
                
                # Get historical translated balance for comparison
                historical_balance = self._get_historical_translated_balance(
                    entity_id, fiscal_year, fiscal_period - 1
                )
                
                remeasurement_gain_loss = total_translated - historical_balance
                translation_result["remeasurement_gain_loss"] = remeasurement_gain_loss
                translation_result["pnl_impact"] = remeasurement_gain_loss
                
                # Save translation results
                self._save_translation_results(translation_result)
                
                logger.info(f"Temporal method translation completed for {entity_id}")
                
        except Exception as e:
            logger.error(f"Error applying temporal method: {e}")
            translation_result["error"] = str(e)
        
        return translation_result
    
    def compare_translation_methods(self, entity_id: str, functional_currency: str,
                                   presentation_currency: str, translation_date: date,
                                   fiscal_year: int, fiscal_period: int) -> Dict[str, Any]:
        """
        Compare results between current rate and temporal methods.
        
        Args:
            entity_id: Entity identifier
            functional_currency: Functional currency
            presentation_currency: Presentation currency
            translation_date: Translation date
            fiscal_year: Fiscal year
            fiscal_period: Fiscal period
            
        Returns:
            Comparison of both translation methods
        """
        
        comparison_result = {
            "entity_id": entity_id,
            "translation_date": translation_date,
            "functional_currency": functional_currency,
            "presentation_currency": presentation_currency,
            "current_rate_method": {},
            "temporal_method": {},
            "differences": {},
            "recommendation": ""
        }
        
        try:
            # Apply current rate method
            current_rate_result = self.apply_current_rate_method(
                entity_id, functional_currency, presentation_currency,
                translation_date, fiscal_year, fiscal_period
            )
            
            # Apply temporal method
            temporal_result = self.apply_temporal_method(
                entity_id, functional_currency, presentation_currency,
                translation_date, fiscal_year, fiscal_period
            )
            
            comparison_result["current_rate_method"] = {
                "total_assets": self._sum_by_type(current_rate_result["translated_balances"], "ASSETS"),
                "total_liabilities": self._sum_by_type(current_rate_result["translated_balances"], "LIABILITIES"),
                "total_equity": self._sum_by_type(current_rate_result["translated_balances"], "EQUITY"),
                "translation_adjustment": float(current_rate_result["translation_adjustment"]),
                "oci_impact": float(current_rate_result["oci_impact"]),
                "pnl_impact": 0
            }
            
            comparison_result["temporal_method"] = {
                "total_monetary": self._sum_by_classification(temporal_result["translated_balances"], "MONETARY"),
                "total_non_monetary": self._sum_by_classification(temporal_result["translated_balances"], "NON_MONETARY"),
                "remeasurement_gain_loss": float(temporal_result["remeasurement_gain_loss"]),
                "oci_impact": 0,
                "pnl_impact": float(temporal_result["pnl_impact"])
            }
            
            # Calculate differences
            comparison_result["differences"] = {
                "oci_vs_pnl": abs(current_rate_result["oci_impact"] - temporal_result["pnl_impact"]),
                "volatility_in_pnl": "Higher" if abs(temporal_result["pnl_impact"]) > 0 else "Lower",
                "volatility_in_oci": "Higher" if abs(current_rate_result["oci_impact"]) > 0 else "Lower"
            }
            
            # Recommendation based on accounting standards
            if functional_currency != presentation_currency:
                comparison_result["recommendation"] = (
                    "Use Current Rate Method - Entity's functional currency differs from presentation currency. "
                    "IAS 21.39 and ASC 830-30 require current rate method for translation."
                )
            else:
                comparison_result["recommendation"] = (
                    "Use Temporal Method - Entity's functional currency equals presentation currency. "
                    "ASC 830-20 requires temporal method for remeasurement."
                )
            
        except Exception as e:
            logger.error(f"Error comparing translation methods: {e}")
            comparison_result["error"] = str(e)
        
        return comparison_result
    
    def _get_closing_rate(self, from_currency: str, to_currency: str, rate_date: date) -> Decimal:
        """Get closing exchange rate."""
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
    
    def _get_average_rate(self, from_currency: str, to_currency: str,
                         fiscal_year: int, fiscal_period: int) -> Decimal:
        """Get average exchange rate for period."""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT AVG(exchange_rate) as avg_rate
                    FROM exchange_rates
                    WHERE from_currency = :from_curr
                    AND to_currency = :to_curr
                    AND EXTRACT(YEAR FROM rate_date) = :fiscal_year
                    AND EXTRACT(MONTH FROM rate_date) = :fiscal_period
                    AND rate_type IN ('CLOSING', 'SPOT')
                """), {
                    "from_curr": from_currency,
                    "to_curr": to_currency,
                    "fiscal_year": fiscal_year,
                    "fiscal_period": fiscal_period
                }).scalar()
                
                return Decimal(str(result)) if result else self._get_closing_rate(
                    from_currency, to_currency, date(fiscal_year, fiscal_period, 28)
                )
        except:
            return Decimal('1.00')
    
    def _get_historical_translated_balance(self, entity_id: str, fiscal_year: int,
                                          fiscal_period: int) -> Decimal:
        """Get historical translated balance for comparison."""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT total_translated_balance
                    FROM translation_history
                    WHERE entity_id = :entity_id
                    AND fiscal_year = :fiscal_year
                    AND fiscal_period = :fiscal_period
                    ORDER BY translation_date DESC
                    LIMIT 1
                """), {
                    "entity_id": entity_id,
                    "fiscal_year": fiscal_year,
                    "fiscal_period": fiscal_period
                }).scalar()
                
                return Decimal(str(result)) if result else Decimal('0.00')
        except:
            return Decimal('0.00')
    
    def _save_translation_results(self, translation_result: Dict[str, Any]):
        """Save translation results to database."""
        try:
            with engine.begin() as conn:
                # Save to translation history
                conn.execute(text("""
                    INSERT INTO translation_history (
                        entity_id, translation_method, functional_currency,
                        presentation_currency, translation_date, fiscal_year,
                        fiscal_period, total_translated_balance, translation_adjustment,
                        oci_impact, pnl_impact, created_at, created_by
                    ) VALUES (
                        :entity_id, :method, :func_curr, :pres_curr, :trans_date,
                        :fiscal_year, :fiscal_period, :total_balance, :trans_adj,
                        :oci_impact, :pnl_impact, CURRENT_TIMESTAMP, 'TRANSLATION_SERVICE'
                    )
                """), {
                    "entity_id": translation_result["entity_id"],
                    "method": translation_result["method"],
                    "func_curr": translation_result["functional_currency"],
                    "pres_curr": translation_result["presentation_currency"],
                    "trans_date": translation_result["translation_date"],
                    "fiscal_year": translation_result["fiscal_year"],
                    "fiscal_period": translation_result["fiscal_period"],
                    "total_balance": sum(
                        Decimal(str(item["balance_translated"]))
                        for item in translation_result["translated_balances"].values()
                    ),
                    "trans_adj": translation_result.get("translation_adjustment", 0),
                    "oci_impact": translation_result.get("oci_impact", 0),
                    "pnl_impact": translation_result.get("pnl_impact", 0)
                })
                
        except Exception as e:
            logger.error(f"Error saving translation results: {e}")
    
    def _sum_by_type(self, balances: Dict[str, Any], account_type: str) -> float:
        """Sum translated balances by account type."""
        total = Decimal('0.00')
        for account_data in balances.values():
            if account_data.get("account_type") == account_type:
                total += Decimal(str(account_data["balance_translated"]))
        return float(total)
    
    def _sum_by_classification(self, balances: Dict[str, Any], classification: str) -> float:
        """Sum translated balances by monetary classification."""
        total = Decimal('0.00')
        for account_data in balances.values():
            if account_data.get("monetary_classification") == classification:
                total += Decimal(str(account_data["balance_translated"]))
        return float(total)

# Create translation history table if not exists
def create_translation_history_table():
    """Create translation history table."""
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS translation_history (
                    history_id SERIAL PRIMARY KEY,
                    entity_id VARCHAR(10) NOT NULL,
                    translation_method VARCHAR(50) NOT NULL,
                    functional_currency VARCHAR(3) NOT NULL,
                    presentation_currency VARCHAR(3) NOT NULL,
                    translation_date DATE NOT NULL,
                    fiscal_year INTEGER NOT NULL,
                    fiscal_period INTEGER NOT NULL,
                    total_translated_balance DECIMAL(15,2),
                    translation_adjustment DECIMAL(15,2),
                    oci_impact DECIMAL(15,2),
                    pnl_impact DECIMAL(15,2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(50),
                    
                    CONSTRAINT uk_translation_history UNIQUE (
                        entity_id, translation_method, translation_date,
                        fiscal_year, fiscal_period
                    )
                )
            """))
            logger.info("Translation history table created successfully")
    except Exception as e:
        logger.error(f"Error creating translation history table: {e}")

# Utility functions
def apply_current_rate_method(entity_id: str, functional_currency: str,
                             presentation_currency: str, translation_date: date,
                             fiscal_year: int, fiscal_period: int) -> Dict[str, Any]:
    """Apply current rate method."""
    service = TranslationMethodsService()
    return service.apply_current_rate_method(
        entity_id, functional_currency, presentation_currency,
        translation_date, fiscal_year, fiscal_period
    )

def apply_temporal_method(entity_id: str, functional_currency: str,
                         reporting_currency: str, translation_date: date,
                         fiscal_year: int, fiscal_period: int) -> Dict[str, Any]:
    """Apply temporal method."""
    service = TranslationMethodsService()
    return service.apply_temporal_method(
        entity_id, functional_currency, reporting_currency,
        translation_date, fiscal_year, fiscal_period
    )

def compare_methods(entity_id: str, functional_currency: str,
                   presentation_currency: str, translation_date: date,
                   fiscal_year: int, fiscal_period: int) -> Dict[str, Any]:
    """Compare translation methods."""
    service = TranslationMethodsService()
    return service.compare_translation_methods(
        entity_id, functional_currency, presentation_currency,
        translation_date, fiscal_year, fiscal_period
    )

# Test function
def test_translation_methods():
    """Test translation methods."""
    # Create table first
    create_translation_history_table()
    
    service = TranslationMethodsService()
    
    print("=== Translation Methods Service Test ===")
    
    # Test current rate method
    current_rate_result = service.apply_current_rate_method(
        "1000", "EUR", "USD", date.today(), 2025, 1
    )
    print(f"Current Rate Method - OCI Impact: {current_rate_result.get('oci_impact', 0)}")
    
    # Test temporal method
    temporal_result = service.apply_temporal_method(
        "1000", "EUR", "USD", date.today(), 2025, 1
    )
    print(f"Temporal Method - P&L Impact: {temporal_result.get('pnl_impact', 0)}")
    
    # Compare methods
    comparison = service.compare_translation_methods(
        "1000", "EUR", "USD", date.today(), 2025, 1
    )
    print(f"Method Comparison - Recommendation: {comparison.get('recommendation', 'N/A')}")
    
    print("✅ Translation Methods Service: Test completed")

if __name__ == "__main__":
    test_translation_methods()