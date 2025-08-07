"""
Currency Translation Service for Parallel Ledger Operations

This service provides currency translation capabilities for multi-ledger
operations, supporting real-time and historical exchange rate lookups.

Author: Claude Code Assistant
Date: August 6, 2025
"""

import logging
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, List, Tuple
from sqlalchemy import create_engine, text
from db_config import engine

logger = logging.getLogger(__name__)

class CurrencyTranslationService:
    """Service for currency translation operations in parallel ledger system."""
    
    def __init__(self):
        """Initialize the currency service with database connection."""
        self.engine = engine
        
    def get_exchange_rate(self, from_currency: str, to_currency: str, 
                         rate_date: Optional[date] = None) -> Optional[Decimal]:
        """
        Get exchange rate for specific currency pair and date.
        
        Args:
            from_currency: Source currency code (e.g., 'USD')
            to_currency: Target currency code (e.g., 'EUR') 
            rate_date: Date for rate lookup (defaults to current date)
            
        Returns:
            Exchange rate as Decimal, or None if not found
        """
        if from_currency == to_currency:
            return Decimal('1.000000')
            
        if rate_date is None:
            rate_date = date.today()
            
        try:
            with self.engine.connect() as conn:
                # Try exact date first
                query = text("""
                    SELECT rate FROM exchangerate 
                    WHERE fromcurrency = :from_curr 
                    AND tocurrency = :to_curr 
                    AND ratedate = :rate_date
                    AND is_active = true
                    ORDER BY created_at DESC 
                    LIMIT 1
                """)
                
                result = conn.execute(query, {
                    'from_curr': from_currency,
                    'to_curr': to_currency,
                    'rate_date': rate_date
                }).fetchone()
                
                if result:
                    return Decimal(str(result[0]))
                
                # If exact date not found, get most recent rate before that date
                query_recent = text("""
                    SELECT rate FROM exchangerate 
                    WHERE fromcurrency = :from_curr 
                    AND tocurrency = :to_curr 
                    AND ratedate <= :rate_date
                    AND is_active = true
                    ORDER BY ratedate DESC, created_at DESC 
                    LIMIT 1
                """)
                
                result_recent = conn.execute(query_recent, {
                    'from_curr': from_currency,
                    'to_curr': to_currency,
                    'rate_date': rate_date
                }).fetchone()
                
                if result_recent:
                    return Decimal(str(result_recent[0]))
                    
                logger.warning(f"No exchange rate found for {from_currency} to {to_currency} on or before {rate_date}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting exchange rate: {e}")
            return None
    
    def translate_amount(self, amount: Decimal, from_currency: str, to_currency: str,
                        rate_date: Optional[date] = None, rounding_places: int = 2) -> Optional[Decimal]:
        """
        Convert amount from one currency to another.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code
            rate_date: Date for rate lookup
            rounding_places: Decimal places for rounding (default 2)
            
        Returns:
            Converted amount as Decimal, or None if conversion failed
        """
        if from_currency == to_currency:
            return amount
            
        exchange_rate = self.get_exchange_rate(from_currency, to_currency, rate_date)
        if exchange_rate is None:
            return None
            
        converted_amount = amount * exchange_rate
        
        # Round to specified decimal places
        quantizer = Decimal('0.' + '0' * rounding_places)
        return converted_amount.quantize(quantizer, rounding=ROUND_HALF_UP)
    
    def get_currency_rates_summary(self, base_currency: str = 'USD', 
                                 rate_date: Optional[date] = None) -> List[Dict]:
        """
        Get summary of all exchange rates for a base currency.
        
        Args:
            base_currency: Base currency for rate summary
            rate_date: Date for rates (defaults to current date)
            
        Returns:
            List of dictionaries with currency rate information
        """
        if rate_date is None:
            rate_date = date.today()
            
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT 
                        er.tocurrency,
                        er.rate,
                        er.ratedate,
                        er.rate_source,
                        er.created_at
                    FROM exchangerate er
                    INNER JOIN (
                        SELECT tocurrency, MAX(ratedate) as max_date
                        FROM exchangerate 
                        WHERE fromcurrency = :base_curr 
                        AND ratedate <= :rate_date
                        AND is_active = true
                        GROUP BY tocurrency
                    ) latest ON er.tocurrency = latest.tocurrency 
                    AND er.ratedate = latest.max_date
                    WHERE er.fromcurrency = :base_curr
                    AND er.is_active = true
                    ORDER BY er.tocurrency
                """)
                
                results = conn.execute(query, {
                    'base_curr': base_currency,
                    'rate_date': rate_date
                }).fetchall()
                
                return [
                    {
                        'currency': row[0],
                        'rate': float(row[1]),
                        'rate_date': row[2],
                        'source': row[3],
                        'updated': row[4]
                    }
                    for row in results
                ]
                
        except Exception as e:
            logger.error(f"Error getting currency rates summary: {e}")
            return []
    
    def update_exchange_rate(self, from_currency: str, to_currency: str, 
                           rate: Decimal, rate_date: Optional[date] = None,
                           rate_source: str = 'API', created_by: str = 'SYSTEM') -> bool:
        """
        Update or insert exchange rate for currency pair.
        
        Args:
            from_currency: Source currency code
            to_currency: Target currency code  
            rate: Exchange rate
            rate_date: Rate date (defaults to current date)
            rate_source: Source of the rate (API, MANUAL, etc.)
            created_by: User or system updating the rate
            
        Returns:
            True if successful, False otherwise
        """
        if rate_date is None:
            rate_date = date.today()
            
        try:
            with self.engine.connect() as conn:
                # Check if rate exists for this date
                check_query = text("""
                    SELECT COUNT(*) FROM exchangerate 
                    WHERE fromcurrency = :from_curr 
                    AND tocurrency = :to_curr 
                    AND ratedate = :rate_date
                """)
                
                exists = conn.execute(check_query, {
                    'from_curr': from_currency,
                    'to_curr': to_currency,
                    'rate_date': rate_date
                }).scalar()
                
                if exists > 0:
                    # Update existing rate
                    update_query = text("""
                        UPDATE exchangerate 
                        SET rate = :rate,
                            rate_source = :rate_source,
                            created_by = :created_by,
                            created_at = CURRENT_TIMESTAMP
                        WHERE fromcurrency = :from_curr 
                        AND tocurrency = :to_curr 
                        AND ratedate = :rate_date
                    """)
                    
                    conn.execute(update_query, {
                        'rate': rate,
                        'rate_source': rate_source,
                        'created_by': created_by,
                        'from_curr': from_currency,
                        'to_curr': to_currency,
                        'rate_date': rate_date
                    })
                else:
                    # Insert new rate
                    insert_query = text("""
                        INSERT INTO exchangerate 
                        (fromcurrency, tocurrency, ratedate, rate, rate_type, 
                         rate_source, created_by, is_active)
                        VALUES (:from_curr, :to_curr, :rate_date, :rate, 'DAILY',
                                :rate_source, :created_by, true)
                    """)
                    
                    conn.execute(insert_query, {
                        'from_curr': from_currency,
                        'to_curr': to_currency,
                        'rate_date': rate_date,
                        'rate': rate,
                        'rate_source': rate_source,
                        'created_by': created_by
                    })
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error updating exchange rate: {e}")
            return False
    
    def validate_currency_code(self, currency_code: str) -> bool:
        """
        Validate currency code format.
        
        Args:
            currency_code: 3-letter currency code
            
        Returns:
            True if valid format, False otherwise
        """
        if not currency_code or len(currency_code) != 3:
            return False
        return currency_code.isalpha() and currency_code.isupper()
    
    def get_supported_currencies(self) -> List[str]:
        """
        Get list of currencies with available exchange rates.
        
        Returns:
            List of currency codes
        """
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT DISTINCT fromcurrency as currency FROM exchangerate 
                    WHERE is_active = true
                    UNION 
                    SELECT DISTINCT tocurrency as currency FROM exchangerate 
                    WHERE is_active = true
                    ORDER BY currency
                """)
                
                results = conn.execute(query).fetchall()
                return [row[0] for row in results]
                
        except Exception as e:
            logger.error(f"Error getting supported currencies: {e}")
            return []
    
    def get_rate_history(self, from_currency: str, to_currency: str, 
                        days: int = 30) -> List[Dict]:
        """
        Get historical exchange rates for currency pair.
        
        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            days: Number of days of history to retrieve
            
        Returns:
            List of rate history records
        """
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT 
                        ratedate,
                        rate,
                        rate_source,
                        created_at
                    FROM exchangerate 
                    WHERE fromcurrency = :from_curr 
                    AND tocurrency = :to_curr
                    AND ratedate >= CURRENT_DATE - INTERVAL '%s days'
                    AND is_active = true
                    ORDER BY ratedate DESC
                """ % days)
                
                results = conn.execute(query, {
                    'from_curr': from_currency,
                    'to_curr': to_currency
                }).fetchall()
                
                return [
                    {
                        'date': row[0],
                        'rate': float(row[1]),
                        'source': row[2],
                        'updated': row[3]
                    }
                    for row in results
                ]
                
        except Exception as e:
            logger.error(f"Error getting rate history: {e}")
            return []

# Convenience functions for common operations
def get_usd_to_eur_rate(rate_date: Optional[date] = None) -> Optional[Decimal]:
    """Get USD to EUR exchange rate for specified date."""
    service = CurrencyTranslationService()
    return service.get_exchange_rate('USD', 'EUR', rate_date)

def convert_usd_to_eur(amount: Decimal, rate_date: Optional[date] = None) -> Optional[Decimal]:
    """Convert USD amount to EUR."""
    service = CurrencyTranslationService()
    return service.translate_amount(amount, 'USD', 'EUR', rate_date)

def get_current_rates_summary() -> List[Dict]:
    """Get summary of current exchange rates from USD."""
    service = CurrencyTranslationService()
    return service.get_currency_rates_summary('USD')

# Test function
def test_currency_service():
    """Test the currency translation service functionality."""
    service = CurrencyTranslationService()
    
    print("=== Currency Service Test ===")
    
    # Test rate lookup
    rate = service.get_exchange_rate('USD', 'EUR')
    print(f"USD to EUR rate: {rate}")
    
    # Test amount conversion
    amount = service.translate_amount(Decimal('100.00'), 'USD', 'EUR')
    print(f"$100.00 USD = €{amount} EUR")
    
    # Test currency summary
    rates = service.get_currency_rates_summary('USD')
    print(f"Available rates from USD: {len(rates)} currencies")
    for rate_info in rates:
        print(f"  {rate_info['currency']}: {rate_info['rate']}")

if __name__ == "__main__":
    test_currency_service()