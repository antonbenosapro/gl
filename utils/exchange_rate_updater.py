"""
Exchange Rate Update Utility

This utility provides automated exchange rate updates for the parallel ledger system.
It can fetch rates from external APIs or be used for manual rate updates.

Author: Claude Code Assistant  
Date: August 6, 2025
"""

import logging
import requests
import json
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from .currency_service import CurrencyTranslationService

logger = logging.getLogger(__name__)

class ExchangeRateUpdater:
    """Service for updating exchange rates from various sources."""
    
    def __init__(self):
        """Initialize the exchange rate updater."""
        self.currency_service = CurrencyTranslationService()
        self.supported_providers = ['MANUAL', 'ECB', 'FIXER', 'EXCHANGERATE_API']
        
    def update_rates_manual(self, rates_data: Dict[str, Dict[str, float]], 
                           base_currency: str = 'USD', 
                           rate_date: Optional[date] = None) -> Dict[str, bool]:
        """
        Update exchange rates manually with provided data.
        
        Args:
            rates_data: Dictionary of currency rates {to_currency: rate}
            base_currency: Base currency for the rates
            rate_date: Date for the rates (defaults to current date)
            
        Returns:
            Dictionary with update status for each currency pair
        """
        if rate_date is None:
            rate_date = date.today()
            
        results = {}
        
        for to_currency, rate in rates_data.items():
            try:
                success = self.currency_service.update_exchange_rate(
                    from_currency=base_currency,
                    to_currency=to_currency,
                    rate=Decimal(str(rate)),
                    rate_date=rate_date,
                    rate_source='MANUAL',
                    created_by='ADMIN'
                )
                results[f"{base_currency}_{to_currency}"] = success
                
                if success:
                    logger.info(f"Updated {base_currency}/{to_currency} = {rate}")
                else:
                    logger.error(f"Failed to update {base_currency}/{to_currency}")
                    
            except Exception as e:
                logger.error(f"Error updating {base_currency}/{to_currency}: {e}")
                results[f"{base_currency}_{to_currency}"] = False
                
        return results
    
    def update_rates_from_ecb(self, rate_date: Optional[date] = None) -> Dict[str, bool]:
        """
        Update EUR-based rates from European Central Bank.
        
        Note: This is a mock implementation for demonstration.
        In production, you would call the actual ECB API.
        
        Args:
            rate_date: Date for rates (defaults to current date)
            
        Returns:
            Dictionary with update status for each currency pair
        """
        if rate_date is None:
            rate_date = date.today()
            
        # Mock ECB data (in production, fetch from actual API)
        mock_ecb_rates = {
            'USD': 1.0870,  # EUR to USD
            'GBP': 0.8587,  # EUR to GBP  
            'JPY': 163.04,  # EUR to JPY
            'CAD': 1.4675,  # EUR to CAD
            'CHF': 0.9342,  # EUR to CHF
        }
        
        results = {}
        base_currency = 'EUR'
        
        for to_currency, rate in mock_ecb_rates.items():
            try:
                success = self.currency_service.update_exchange_rate(
                    from_currency=base_currency,
                    to_currency=to_currency,
                    rate=Decimal(str(rate)),
                    rate_date=rate_date,
                    rate_source='ECB',
                    created_by='ECB_API'
                )
                results[f"{base_currency}_{to_currency}"] = success
                
                # Also add reverse rate
                reverse_rate = 1 / Decimal(str(rate))
                success_reverse = self.currency_service.update_exchange_rate(
                    from_currency=to_currency,
                    to_currency=base_currency,
                    rate=reverse_rate,
                    rate_date=rate_date,
                    rate_source='ECB',
                    created_by='ECB_API'
                )
                results[f"{to_currency}_{base_currency}"] = success_reverse
                
            except Exception as e:
                logger.error(f"Error updating ECB rates for {to_currency}: {e}")
                results[f"{base_currency}_{to_currency}"] = False
                
        return results
    
    def update_major_currency_cross_rates(self, rate_date: Optional[date] = None) -> Dict[str, bool]:
        """
        Calculate and update cross rates between major currencies.
        
        Args:
            rate_date: Date for rates
            
        Returns:
            Update status for calculated cross rates
        """
        if rate_date is None:
            rate_date = date.today()
            
        major_currencies = ['USD', 'EUR', 'GBP', 'JPY']
        results = {}
        
        for base_curr in major_currencies:
            for target_curr in major_currencies:
                if base_curr == target_curr:
                    continue
                    
                # Check if direct rate exists
                direct_rate = self.currency_service.get_exchange_rate(
                    base_curr, target_curr, rate_date
                )
                
                if direct_rate is None:
                    # Try to calculate via USD
                    if base_curr != 'USD' and target_curr != 'USD':
                        base_to_usd = self.currency_service.get_exchange_rate(
                            base_curr, 'USD', rate_date
                        )
                        usd_to_target = self.currency_service.get_exchange_rate(
                            'USD', target_curr, rate_date
                        )
                        
                        if base_to_usd and usd_to_target:
                            calculated_rate = base_to_usd * usd_to_target
                            success = self.currency_service.update_exchange_rate(
                                from_currency=base_curr,
                                to_currency=target_curr,
                                rate=calculated_rate,
                                rate_date=rate_date,
                                rate_source='CALCULATED',
                                created_by='CROSS_RATE_CALCULATOR'
                            )
                            results[f"{base_curr}_{target_curr}"] = success
                            
        return results
    
    def validate_rate_consistency(self, tolerance: float = 0.01) -> List[Dict]:
        """
        Validate consistency of exchange rates (triangular arbitrage check).
        
        Args:
            tolerance: Maximum allowed deviation for consistency check
            
        Returns:
            List of inconsistencies found
        """
        inconsistencies = []
        currencies = ['USD', 'EUR', 'GBP']
        
        # Check triangular consistency for major currencies
        for base in currencies:
            for via in currencies:
                for target in currencies:
                    if base == via or via == target or base == target:
                        continue
                        
                    direct_rate = self.currency_service.get_exchange_rate(base, target)
                    base_to_via = self.currency_service.get_exchange_rate(base, via)
                    via_to_target = self.currency_service.get_exchange_rate(via, target)
                    
                    if direct_rate and base_to_via and via_to_target:
                        calculated_rate = base_to_via * via_to_target
                        deviation = abs(float(direct_rate) - float(calculated_rate)) / float(direct_rate)
                        
                        if deviation > tolerance:
                            inconsistencies.append({
                                'path': f"{base} → {target} (direct) vs {base} → {via} → {target}",
                                'direct_rate': float(direct_rate),
                                'calculated_rate': float(calculated_rate),
                                'deviation_percent': deviation * 100
                            })
        
        return inconsistencies
    
    def get_rate_update_summary(self, days: int = 7) -> Dict:
        """
        Get summary of recent rate updates.
        
        Args:
            days: Number of days to look back
            
        Returns:
            Summary of rate update activity
        """
        try:
            from db_config import engine
            from sqlalchemy import text
            
            with engine.connect() as conn:
                query = text("""
                    SELECT 
                        rate_source,
                        COUNT(*) as update_count,
                        COUNT(DISTINCT fromcurrency || tocurrency) as currency_pairs,
                        MIN(created_at) as first_update,
                        MAX(created_at) as latest_update
                    FROM exchangerate 
                    WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    AND is_active = true
                    GROUP BY rate_source
                    ORDER BY update_count DESC
                """ % days)
                
                results = conn.execute(query).fetchall()
                
                summary = {
                    'period_days': days,
                    'total_updates': sum(row[1] for row in results),
                    'sources': [
                        {
                            'source': row[0],
                            'updates': row[1],
                            'currency_pairs': row[2],
                            'first_update': row[3],
                            'latest_update': row[4]
                        }
                        for row in results
                    ]
                }
                
                return summary
                
        except Exception as e:
            logger.error(f"Error getting rate update summary: {e}")
            return {'error': str(e)}
    
    def schedule_daily_update(self, provider: str = 'MANUAL') -> bool:
        """
        Perform daily exchange rate update.
        This would typically be called by a scheduler/cron job.
        
        Args:
            provider: Rate provider to use ('MANUAL', 'ECB', etc.)
            
        Returns:
            True if update successful
        """
        try:
            logger.info(f"Starting daily exchange rate update from {provider}")
            
            if provider == 'ECB':
                results = self.update_rates_from_ecb()
            elif provider == 'MANUAL':
                # Use default rates for manual updates
                default_rates = {
                    'EUR': 0.92,
                    'GBP': 0.79,
                    'JPY': 150.0,
                    'CAD': 1.35
                }
                results = self.update_rates_manual(default_rates, 'USD')
            else:
                logger.warning(f"Provider {provider} not implemented")
                return False
                
            # Update cross rates
            cross_results = self.update_major_currency_cross_rates()
            results.update(cross_results)
            
            # Check for inconsistencies
            inconsistencies = self.validate_rate_consistency()
            if inconsistencies:
                logger.warning(f"Found {len(inconsistencies)} rate inconsistencies")
                
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            
            logger.info(f"Daily update complete: {success_count}/{total_count} successful")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error in daily exchange rate update: {e}")
            return False

# Utility functions for common operations
def update_usd_rates(rates: Dict[str, float]) -> bool:
    """Quick update of USD-based rates."""
    updater = ExchangeRateUpdater()
    results = updater.update_rates_manual(rates, 'USD')
    return all(results.values())

def get_current_rate_status() -> Dict:
    """Get current status of exchange rate data."""
    updater = ExchangeRateUpdater()
    return updater.get_rate_update_summary(7)

def validate_rates() -> List[Dict]:
    """Validate current exchange rate consistency."""
    updater = ExchangeRateUpdater()
    return updater.validate_rate_consistency()

# Test function
def test_exchange_rate_updater():
    """Test the exchange rate updater functionality."""
    updater = ExchangeRateUpdater()
    
    print("=== Exchange Rate Updater Test ===")
    
    # Test manual update
    test_rates = {
        'EUR': 0.925,
        'GBP': 0.785,
        'CAD': 1.345
    }
    
    results = updater.update_rates_manual(test_rates, 'USD')
    print(f"Manual update results: {results}")
    
    # Test rate validation
    inconsistencies = updater.validate_rate_consistency()
    print(f"Rate inconsistencies found: {len(inconsistencies)}")
    
    # Test update summary
    summary = updater.get_rate_update_summary(7)
    print(f"Recent updates: {summary.get('total_updates', 0)}")

if __name__ == "__main__":
    test_exchange_rate_updater()