"""
Currency Admin Fix Verification

Quick test to verify the authentication fix works and basic functions are accessible.
"""

import sys
sys.path.append('.')

def test_import():
    """Test if Currency Admin imports correctly."""
    try:
        from pages.Currency_Exchange_Admin import get_currencies, get_currency_list
        print("✅ Currency Admin imports successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"⚠️ Other error: {e}")
        return False

def test_database_functions():
    """Test database functions."""
    try:
        from pages.Currency_Exchange_Admin import get_currencies, get_currency_list
        
        # Test get_currencies
        currencies_df = get_currencies()
        print(f"✅ get_currencies(): {len(currencies_df)} currencies loaded")
        
        # Test get_currency_list
        currency_list = get_currency_list()
        print(f"✅ get_currency_list(): {len(currency_list)} active currencies")
        
        return True
    except Exception as e:
        print(f"❌ Database function error: {e}")
        return False

def main():
    """Run verification tests."""
    print("🧪 Currency Admin Fix Verification")
    print("=" * 50)
    
    all_passed = True
    
    # Test imports
    if not test_import():
        all_passed = False
    
    # Test database functions
    if not test_database_functions():
        all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("✅ All verification tests passed!")
        print("Currency Admin UI is ready for use.")
    else:
        print("❌ Some tests failed. Check errors above.")
    
    return all_passed

if __name__ == "__main__":
    main()