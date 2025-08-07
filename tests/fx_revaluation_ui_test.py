"""
FX Revaluation UI Test

Test to verify the FX Revaluation Manager UI components load properly
and identify any issues preventing the Run button from being visible.
"""

import sys
sys.path.append('.')

import streamlit as st
from datetime import date

def test_fx_revaluation_ui():
    """Test FX Revaluation UI components."""
    print("🧪 FX Revaluation UI Component Test")
    print("=" * 50)
    
    try:
        # Test imports
        from pages.FX_Revaluation_Manager import (
            show_revaluation_runner, 
            get_available_ledgers,
            get_revaluation_configuration,
            get_current_fx_balances
        )
        print("✅ Import successful")
        
        # Test helper functions
        ledgers = get_available_ledgers()
        print(f"✅ Available ledgers: {ledgers}")
        
        # Test configuration function
        config_df = get_revaluation_configuration("1000", ["L1"])
        print(f"✅ Configuration query: {len(config_df)} records")
        
        # Test current balances function
        balances_df = get_current_fx_balances("1000", ["L1"])
        print(f"✅ FX balances query: {len(balances_df)} records")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_button_visibility():
    """Test if button visibility conditions are met."""
    print("\n🔍 Button Visibility Test")
    print("=" * 30)
    
    try:
        # Test if the show_revaluation_runner function has all required components
        import inspect
        from pages.FX_Revaluation_Manager import show_revaluation_runner
        
        # Get function source
        source = inspect.getsource(show_revaluation_runner)
        
        # Check for button
        if 'st.button("▶️ Run FX Revaluation"' in source:
            print("✅ Run button found in source code")
        else:
            print("❌ Run button NOT found in source code")
            
        # Check for form elements that could hide button
        if 'st.form(' in source:
            print("⚠️ Form element detected - button might be inside form")
        
        # Check for conditional logic that could hide button
        if 'if ' in source and 'button' in source:
            print("⚠️ Conditional logic detected around button")
            
        return True
        
    except Exception as e:
        print(f"❌ Error analyzing button: {e}")
        return False

def test_database_dependencies():
    """Test database dependencies for the UI."""
    print("\n📊 Database Dependencies Test")
    print("=" * 35)
    
    try:
        from sqlalchemy import text
        from db_config import engine
        
        # Test required tables exist
        required_tables = [
            'fx_revaluation_runs',
            'fx_revaluation_config',
            'ledger',
            'journalentryline'
        ]
        
        with engine.connect() as conn:
            for table in required_tables:
                try:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    print(f"✅ Table {table}: {result} records")
                except Exception as e:
                    print(f"❌ Table {table}: {e}")
                    return False
        
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def simulate_ui_load():
    """Simulate UI loading to find issues."""
    print("\n🖥️ UI Loading Simulation")
    print("=" * 30)
    
    try:
        # Mock Streamlit session state
        class MockSessionState:
            def __init__(self):
                self.fx_service = None
                self.currency_service = None
        
        # Test service initialization
        from utils.fx_revaluation_service import FXRevaluationService
        from utils.currency_service import CurrencyTranslationService
        
        fx_service = FXRevaluationService()
        currency_service = CurrencyTranslationService()
        print("✅ Services initialized successfully")
        
        # Test critical UI functions
        from pages.FX_Revaluation_Manager import (
            get_configured_accounts_count,
            get_recent_runs_count,
            get_supported_currencies_count
        )
        
        accounts = get_configured_accounts_count()
        runs = get_recent_runs_count()
        currencies = get_supported_currencies_count()
        
        print(f"✅ UI metrics loaded: {accounts} accounts, {runs} runs, {currencies} currencies")
        
        return True
        
    except Exception as e:
        print(f"❌ UI loading error: {e}")
        return False

def main():
    """Run all tests."""
    print("🔍 FX Revaluation UI Investigation")
    print("=" * 60)
    
    all_passed = True
    
    # Test UI components
    if not test_fx_revaluation_ui():
        all_passed = False
    
    # Test button visibility
    if not test_button_visibility():
        all_passed = False
    
    # Test database dependencies
    if not test_database_dependencies():
        all_passed = False
    
    # Simulate UI loading
    if not simulate_ui_load():
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All tests passed! UI should be functional.")
        print("\nPossible reasons button is not visible:")
        print("1. Authentication required - user not logged in")
        print("2. Streamlit caching issues - try clearing cache")
        print("3. UI not refreshed - try reloading page")
        print("4. Sidebar selection - ensure 'Run Revaluation' tab is selected")
    else:
        print("❌ Some tests failed. Check errors above.")
    
    return all_passed

if __name__ == "__main__":
    main()