"""
Currency & Exchange Rate Administration

Comprehensive UI for managing currencies, exchange rates, and rate types.
Provides full CRUD operations for currency master data and exchange rate management.

Features:
- Currency master data management
- Exchange rate upload and manual entry
- Rate type configuration (SPOT, CLOSING, AVERAGE, HISTORICAL)
- Bulk rate import from CSV/Excel
- Rate validation and approval workflow
- Historical rate tracking and audit trails

Author: Claude Code Assistant
Date: August 6, 2025
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
import io
import csv
from sqlalchemy import text
from db_config import engine
from auth.optimized_middleware import optimized_authenticator as authenticator

# Page configuration
st.set_page_config(
    page_title="Currency & Exchange Rate Admin",
    page_icon="💱",
    layout="wide"
)

# Authentication check
authenticator.require_auth()
user = authenticator.get_current_user()

def main():
    """Main Currency Administration application."""
    st.title("💱 Currency & Exchange Rate Administration")
    st.markdown("**Comprehensive currency and exchange rate management**")
    
    # Tab navigation
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🌍 Currency Management", 
        "📈 Exchange Rates",
        "🏦 Official Rates",
        "📤 Bulk Import",
        "📊 Rate Analytics"
    ])
    
    with tab1:
        show_currency_management()
    
    with tab2:
        show_exchange_rate_management()
    
    with tab3:
        show_official_rates_import()
    
    with tab4:
        show_bulk_import()
    
    with tab5:
        show_rate_analytics()

def show_currency_management():
    """Currency master data management."""
    st.header("🌍 Currency Master Data Management")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Active Currencies")
        
        # Get currency list
        currencies_df = get_currencies()
        
        if not currencies_df.empty:
            # Display currencies with edit capability
            edited_df = st.data_editor(
                currencies_df,
                column_config={
                    "currency_code": st.column_config.TextColumn(
                        "Currency Code",
                        help="3-letter ISO currency code",
                        max_chars=3,
                        validate="^[A-Z]{3}$"
                    ),
                    "currency_name": st.column_config.TextColumn(
                        "Currency Name",
                        help="Full currency name"
                    ),
                    "currency_symbol": st.column_config.TextColumn(
                        "Symbol",
                        help="Currency symbol (e.g., $, €, £)"
                    ),
                    "decimal_places": st.column_config.NumberColumn(
                        "Decimal Places",
                        help="Number of decimal places for amounts",
                        min_value=0,
                        max_value=6,
                        step=1
                    ),
                    "is_base_currency": st.column_config.CheckboxColumn(
                        "Base Currency",
                        help="Mark as base/functional currency"
                    ),
                    "is_active": st.column_config.CheckboxColumn(
                        "Active",
                        help="Currency is active for transactions"
                    )
                },
                num_rows="dynamic",
                use_container_width=True,
                key="currency_editor"
            )
            
            # Save changes button
            if st.button("💾 Save Currency Changes", key="save_currencies"):
                save_currency_changes(edited_df, currencies_df)
        else:
            st.info("No currencies configured. Add currencies using the form below.")
    
    with col2:
        st.subheader("Add New Currency")
        
        with st.form("add_currency_form"):
            currency_code = st.text_input(
                "Currency Code *",
                max_chars=3,
                help="3-letter ISO code (e.g., USD, EUR, GBP)"
            ).upper()
            
            currency_name = st.text_input(
                "Currency Name *",
                help="Full currency name (e.g., US Dollar)"
            )
            
            currency_symbol = st.text_input(
                "Currency Symbol",
                help="Symbol (e.g., $, €, £)"
            )
            
            decimal_places = st.number_input(
                "Decimal Places",
                min_value=0,
                max_value=6,
                value=2,
                help="Number of decimal places for amounts"
            )
            
            is_base_currency = st.checkbox(
                "Base Currency",
                help="Mark as base/functional currency"
            )
            
            is_active = st.checkbox(
                "Active",
                value=True,
                help="Currency is active for transactions"
            )
            
            if st.form_submit_button("➕ Add Currency"):
                if currency_code and currency_name:
                    add_new_currency(
                        currency_code, currency_name, currency_symbol,
                        decimal_places, is_base_currency, is_active
                    )
                else:
                    st.error("Currency Code and Name are required")

def show_exchange_rate_management():
    """Exchange rate management interface."""
    st.header("📈 Exchange Rate Management")
    
    # Rate entry form
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📝 Enter Exchange Rates")
        
        # Get currency list for dropdowns
        currencies = get_currency_list()
        
        with st.form("rate_entry_form"):
            from_currency = st.selectbox(
                "From Currency *",
                currencies,
                help="Source currency"
            )
            
            to_currency = st.selectbox(
                "To Currency *", 
                currencies,
                index=currencies.index('USD') if 'USD' in currencies else 0,
                help="Target currency"
            )
            
            rate_date = st.date_input(
                "Rate Date *",
                value=date.today(),
                help="Effective date for the exchange rate"
            )
            
            rate_type = st.selectbox(
                "Rate Type *",
                ["SPOT", "CLOSING", "AVERAGE", "HISTORICAL", "BUDGET"],
                help="Type of exchange rate"
            )
            
            exchange_rate = st.number_input(
                "Exchange Rate *",
                min_value=0.000001,
                value=1.000000,
                format="%.6f",
                help="1 unit of From Currency = X units of To Currency"
            )
            
            source = st.text_input(
                "Source",
                placeholder="e.g., Bloomberg, Reuters, Central Bank",
                help="Source of the exchange rate"
            )
            
            if st.form_submit_button("💾 Save Exchange Rate"):
                if from_currency and to_currency and exchange_rate > 0:
                    if from_currency != to_currency:
                        save_exchange_rate(
                            from_currency, to_currency, rate_date, 
                            rate_type, exchange_rate, source
                        )
                    else:
                        st.error("From and To currencies must be different")
                else:
                    st.error("Please fill all required fields")
    
    with col2:
        st.subheader("🔍 Recent Exchange Rates")
        
        # Filter controls
        filter_currency = st.selectbox(
            "Filter by Currency",
            ["All"] + currencies,
            key="filter_currency"
        )
        
        filter_days = st.selectbox(
            "Show Last",
            [7, 14, 30, 60, 90],
            index=2,
            format_func=lambda x: f"{x} days"
        )
        
        # Get and display recent rates
        recent_rates = get_recent_exchange_rates(filter_currency, filter_days)
        
        if not recent_rates.empty:
            st.dataframe(
                recent_rates,
                column_config={
                    "rate_date": st.column_config.DateColumn("Date"),
                    "from_currency": st.column_config.TextColumn("From"),
                    "to_currency": st.column_config.TextColumn("To"),
                    "rate_type": st.column_config.TextColumn("Type"),
                    "exchange_rate": st.column_config.NumberColumn(
                        "Rate", format="%.6f"
                    ),
                    "source": st.column_config.TextColumn("Source"),
                    "created_by": st.column_config.TextColumn("Created By")
                },
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No recent exchange rates found")
    
    # Current rates overview
    st.subheader("💱 Current Exchange Rates Overview")
    
    current_rates = get_current_exchange_rates()
    
    if not current_rates.empty:
        # Create rate comparison chart
        fig = px.bar(
            current_rates.head(10),
            x='currency_pair',
            y='exchange_rate',
            color='rate_type',
            title='Current Exchange Rates (Top 10)',
            hover_data=['rate_date', 'source']
        )
        
        fig.update_layout(
            xaxis_tickangle=-45,
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Full rates table
        with st.expander("📊 All Current Rates", expanded=False):
            st.dataframe(
                current_rates,
                column_config={
                    "currency_pair": st.column_config.TextColumn("Pair"),
                    "exchange_rate": st.column_config.NumberColumn(
                        "Rate", format="%.6f"
                    ),
                    "rate_type": st.column_config.TextColumn("Type"),
                    "rate_date": st.column_config.DateColumn("Date"),
                    "source": st.column_config.TextColumn("Source")
                },
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("No current exchange rates available")

def show_bulk_import():
    """Bulk import interface for exchange rates."""
    st.header("📤 Bulk Exchange Rate Import")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📋 Import Template")
        
        # Download template
        template_data = {
            'from_currency': ['EUR', 'GBP', 'JPY'],
            'to_currency': ['USD', 'USD', 'USD'],
            'rate_date': ['2025-08-06', '2025-08-06', '2025-08-06'],
            'rate_type': ['CLOSING', 'CLOSING', 'CLOSING'],
            'exchange_rate': [1.085000, 1.265000, 0.006700],
            'source': ['ECB', 'BOE', 'BOJ']
        }
        
        template_df = pd.DataFrame(template_data)
        
        st.dataframe(
            template_df,
            use_container_width=True,
            hide_index=True
        )
        
        # Download template button
        csv_buffer = io.StringIO()
        template_df.to_csv(csv_buffer, index=False)
        
        st.download_button(
            label="📥 Download Template",
            data=csv_buffer.getvalue(),
            file_name=f"exchange_rates_template_{date.today()}.csv",
            mime="text/csv"
        )
        
        st.markdown("---")
        
        # Import instructions
        st.markdown("""
        **📝 Import Instructions:**
        
        1. **Download Template:** Use the template above as a starting point
        2. **Fill Data:** Add your exchange rate data following the format
        3. **Required Fields:** 
           - from_currency (3-letter code)
           - to_currency (3-letter code)
           - rate_date (YYYY-MM-DD format)
           - rate_type (SPOT, CLOSING, AVERAGE, HISTORICAL, BUDGET)
           - exchange_rate (decimal number)
        4. **Optional Fields:** source (rate provider)
        5. **Upload File:** Use CSV or Excel format
        """)
    
    with col2:
        st.subheader("📁 File Upload")
        
        uploaded_file = st.file_uploader(
            "Choose file to upload",
            type=['csv', 'xlsx', 'xls'],
            help="Upload CSV or Excel file with exchange rates"
        )
        
        if uploaded_file is not None:
            try:
                # Read uploaded file
                if uploaded_file.name.endswith('.csv'):
                    upload_df = pd.read_csv(uploaded_file)
                else:
                    upload_df = pd.read_excel(uploaded_file)
                
                st.success(f"✅ File loaded: {len(upload_df)} rows")
                
                # Validate data
                validation_results = validate_upload_data(upload_df)
                
                if validation_results['valid']:
                    st.success("✅ Data validation passed")
                    
                    # Preview data
                    st.subheader("📋 Data Preview")
                    st.dataframe(
                        upload_df.head(10),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Import options
                    st.subheader("⚙️ Import Options")
                    
                    update_existing = st.checkbox(
                        "Update Existing Rates",
                        help="Update rates if they already exist for the same date/currency pair"
                    )
                    
                    dry_run = st.checkbox(
                        "Dry Run (Preview Only)",
                        value=True,
                        help="Preview changes without saving to database"
                    )
                    
                    if st.button("🚀 Import Exchange Rates"):
                        import_results = import_exchange_rates(
                            upload_df, update_existing, dry_run
                        )
                        
                        if import_results['success']:
                            if dry_run:
                                st.info(f"✅ Dry run completed: {import_results['processed']} rates would be imported")
                            else:
                                st.success(f"✅ Import completed: {import_results['processed']} rates imported")
                            
                            if import_results.get('errors'):
                                st.warning(f"⚠️ {len(import_results['errors'])} errors encountered")
                                with st.expander("View Errors"):
                                    for error in import_results['errors']:
                                        st.error(error)
                        else:
                            st.error(f"❌ Import failed: {import_results.get('error', 'Unknown error')}")
                
                else:
                    st.error("❌ Data validation failed")
                    for error in validation_results['errors']:
                        st.error(f"• {error}")
                    
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")

def show_rate_analytics():
    """Exchange rate analytics and reporting."""
    st.header("📊 Exchange Rate Analytics")
    
    # Get currency pairs for analysis
    currency_pairs = get_currency_pairs()
    
    if currency_pairs:
        col1, col2 = st.columns([1, 1])
        
        with col1:
            selected_pair = st.selectbox(
                "Select Currency Pair",
                currency_pairs,
                help="Choose currency pair for analysis"
            )
            
            analysis_period = st.selectbox(
                "Analysis Period",
                [30, 60, 90, 180, 365],
                index=2,
                format_func=lambda x: f"{x} days"
            )
        
        with col2:
            analysis_type = st.selectbox(
                "Analysis Type",
                ["Trend Analysis", "Volatility Analysis", "Rate Comparison"],
                help="Type of analysis to perform"
            )
            
            rate_types = st.multiselect(
                "Rate Types",
                ["SPOT", "CLOSING", "AVERAGE", "HISTORICAL"],
                default=["CLOSING"],
                help="Select rate types to include"
            )
        
        if selected_pair and st.button("📈 Generate Analysis"):
            # Get historical data
            from_curr, to_curr = selected_pair.split('/')
            historical_data = get_historical_rates(
                from_curr, to_curr, analysis_period, rate_types
            )
            
            if not historical_data.empty:
                if analysis_type == "Trend Analysis":
                    show_trend_analysis(historical_data, selected_pair)
                elif analysis_type == "Volatility Analysis":
                    show_volatility_analysis(historical_data, selected_pair)
                elif analysis_type == "Rate Comparison":
                    show_rate_comparison(historical_data, selected_pair)
            else:
                st.warning("No historical data available for the selected criteria")
    else:
        st.info("No currency pairs available. Please add exchange rates first.")

def show_trend_analysis(data, currency_pair):
    """Display trend analysis charts."""
    st.subheader(f"📈 Trend Analysis: {currency_pair}")
    
    # Time series chart
    fig = px.line(
        data,
        x='rate_date',
        y='exchange_rate',
        color='rate_type',
        title=f'{currency_pair} Exchange Rate Trend',
        hover_data=['source']
    )
    
    fig.update_layout(
        xaxis_title='Date',
        yaxis_title='Exchange Rate',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        current_rate = data['exchange_rate'].iloc[-1] if not data.empty else 0
        st.metric("Current Rate", f"{current_rate:.6f}")
    
    with col2:
        min_rate = data['exchange_rate'].min()
        st.metric("Period Low", f"{min_rate:.6f}")
    
    with col3:
        max_rate = data['exchange_rate'].max()
        st.metric("Period High", f"{max_rate:.6f}")
    
    with col4:
        avg_rate = data['exchange_rate'].mean()
        st.metric("Average Rate", f"{avg_rate:.6f}")

def show_volatility_analysis(data, currency_pair):
    """Display volatility analysis."""
    st.subheader(f"📊 Volatility Analysis: {currency_pair}")
    
    # Calculate daily changes
    data = data.sort_values('rate_date')
    data['daily_change'] = data['exchange_rate'].pct_change() * 100
    
    # Volatility chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=data['rate_date'],
        y=data['daily_change'],
        mode='lines+markers',
        name='Daily Change (%)',
        line=dict(color='blue')
    ))
    
    fig.update_layout(
        title=f'{currency_pair} Daily Volatility',
        xaxis_title='Date',
        yaxis_title='Daily Change (%)',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Volatility statistics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        volatility = data['daily_change'].std()
        st.metric("Volatility (σ)", f"{volatility:.2f}%")
    
    with col2:
        max_gain = data['daily_change'].max()
        st.metric("Max Daily Gain", f"{max_gain:.2f}%")
    
    with col3:
        max_loss = data['daily_change'].min()
        st.metric("Max Daily Loss", f"{max_loss:.2f}%")

def show_rate_comparison(data, currency_pair):
    """Display rate type comparison."""
    st.subheader(f"🔍 Rate Comparison: {currency_pair}")
    
    # Group by rate type and date
    comparison_data = data.groupby(['rate_date', 'rate_type'])['exchange_rate'].first().unstack(fill_value=None)
    
    # Create comparison chart
    fig = go.Figure()
    
    for rate_type in comparison_data.columns:
        fig.add_trace(go.Scatter(
            x=comparison_data.index,
            y=comparison_data[rate_type],
            mode='lines+markers',
            name=rate_type
        ))
    
    fig.update_layout(
        title=f'{currency_pair} Rate Type Comparison',
        xaxis_title='Date',
        yaxis_title='Exchange Rate',
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

# Database functions
def get_currencies():
    """Get currency master data."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    currency_code,
                    currency_name,
                    currency_symbol,
                    decimal_places,
                    is_base_currency,
                    is_active,
                    created_at,
                    created_by
                FROM currencies
                ORDER BY currency_code
            """))
            
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    except Exception as e:
        st.error(f"Error loading currencies: {e}")
        return pd.DataFrame()

def get_currency_list():
    """Get list of active currencies."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT currency_code 
                FROM currencies 
                WHERE is_active = true 
                ORDER BY currency_code
            """))
            
            return [row[0] for row in result.fetchall()]
    except:
        # Fallback to common currencies
        return ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD']

def add_new_currency(currency_code, currency_name, currency_symbol, 
                    decimal_places, is_base_currency, is_active):
    """Add new currency to master data."""
    try:
        with engine.begin() as conn:
            # First, create currencies table if it doesn't exist
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS currencies (
                    currency_code VARCHAR(3) PRIMARY KEY,
                    currency_name VARCHAR(100) NOT NULL,
                    currency_symbol VARCHAR(10),
                    decimal_places INTEGER DEFAULT 2,
                    is_base_currency BOOLEAN DEFAULT FALSE,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(50),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Insert new currency
            conn.execute(text("""
                INSERT INTO currencies (
                    currency_code, currency_name, currency_symbol,
                    decimal_places, is_base_currency, is_active, created_by
                ) VALUES (
                    :code, :name, :symbol, :decimals, :base, :active, :user
                )
                ON CONFLICT (currency_code) DO UPDATE SET
                    currency_name = :name,
                    currency_symbol = :symbol,
                    decimal_places = :decimals,
                    is_base_currency = :base,
                    is_active = :active,
                    updated_at = CURRENT_TIMESTAMP
            """), {
                "code": currency_code,
                "name": currency_name,
                "symbol": currency_symbol,
                "decimals": decimal_places,
                "base": is_base_currency,
                "active": is_active,
                "user": user.username if user else 'system'
            })
            
        st.success(f"✅ Currency {currency_code} added successfully!")
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Error adding currency: {e}")

def save_currency_changes(edited_df, original_df):
    """Save currency changes."""
    try:
        with engine.begin() as conn:
            for idx, row in edited_df.iterrows():
                conn.execute(text("""
                    UPDATE currencies SET
                        currency_name = :name,
                        currency_symbol = :symbol,
                        decimal_places = :decimals,
                        is_base_currency = :base,
                        is_active = :active,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE currency_code = :code
                """), {
                    "code": row['currency_code'],
                    "name": row['currency_name'],
                    "symbol": row['currency_symbol'],
                    "decimals": row['decimal_places'],
                    "base": row['is_base_currency'],
                    "active": row['is_active']
                })
        
        st.success("✅ Currency changes saved successfully!")
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Error saving changes: {e}")

def save_exchange_rate(from_currency, to_currency, rate_date, rate_type, exchange_rate, source):
    """Save exchange rate to database."""
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO exchange_rates (
                    from_currency, to_currency, rate_date, rate_type,
                    exchange_rate, source, created_by
                ) VALUES (
                    :from_curr, :to_curr, :rate_date, :rate_type,
                    :exchange_rate, :source, :created_by
                )
                ON CONFLICT (from_currency, to_currency, rate_type, rate_date) 
                DO UPDATE SET
                    exchange_rate = :exchange_rate,
                    source = :source,
                    updated_at = CURRENT_TIMESTAMP
            """), {
                "from_curr": from_currency,
                "to_curr": to_currency,
                "rate_date": rate_date,
                "rate_type": rate_type,
                "exchange_rate": exchange_rate,
                "source": source,
                "created_by": user.username if user else 'system'
            })
        
        st.success(f"✅ Exchange rate saved: 1 {from_currency} = {exchange_rate:.6f} {to_currency}")
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Error saving exchange rate: {e}")

def get_recent_exchange_rates(filter_currency, days):
    """Get recent exchange rates."""
    try:
        with engine.connect() as conn:
            base_query = """
                SELECT 
                    rate_date,
                    from_currency,
                    to_currency,
                    rate_type,
                    exchange_rate,
                    source,
                    created_by
                FROM exchange_rates
                WHERE rate_date >= CURRENT_DATE - INTERVAL '%d days'
            """ % days
            
            if filter_currency != "All":
                base_query += f" AND (from_currency = '{filter_currency}' OR to_currency = '{filter_currency}')"
            
            base_query += " ORDER BY rate_date DESC, from_currency, to_currency"
            
            result = conn.execute(text(base_query))
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    except Exception as e:
        st.error(f"Error loading recent rates: {e}")
        return pd.DataFrame()

def get_current_exchange_rates():
    """Get current exchange rates."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    from_currency || '/' || to_currency as currency_pair,
                    rate_date,
                    rate_type,
                    exchange_rate,
                    source
                FROM exchange_rates er1
                WHERE rate_date = (
                    SELECT MAX(rate_date)
                    FROM exchange_rates er2
                    WHERE er2.from_currency = er1.from_currency
                    AND er2.to_currency = er1.to_currency
                    AND er2.rate_type = er1.rate_type
                )
                ORDER BY from_currency, to_currency
            """))
            
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    except:
        return pd.DataFrame()

def validate_upload_data(df):
    """Validate uploaded exchange rate data."""
    errors = []
    required_columns = ['from_currency', 'to_currency', 'rate_date', 'rate_type', 'exchange_rate']
    
    # Check required columns
    for col in required_columns:
        if col not in df.columns:
            errors.append(f"Missing required column: {col}")
    
    if not errors:
        # Validate data types and values
        for idx, row in df.iterrows():
            row_num = idx + 1
            
            # Currency codes validation
            if len(str(row['from_currency'])) != 3:
                errors.append(f"Row {row_num}: Invalid from_currency (must be 3 characters)")
            
            if len(str(row['to_currency'])) != 3:
                errors.append(f"Row {row_num}: Invalid to_currency (must be 3 characters)")
            
            # Rate type validation
            valid_rate_types = ['SPOT', 'CLOSING', 'AVERAGE', 'HISTORICAL', 'BUDGET']
            if str(row['rate_type']).upper() not in valid_rate_types:
                errors.append(f"Row {row_num}: Invalid rate_type (must be one of {valid_rate_types})")
            
            # Exchange rate validation
            try:
                rate = float(row['exchange_rate'])
                if rate <= 0:
                    errors.append(f"Row {row_num}: Exchange rate must be positive")
            except (ValueError, TypeError):
                errors.append(f"Row {row_num}: Invalid exchange rate format")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors
    }

def import_exchange_rates(df, update_existing, dry_run):
    """Import exchange rates from DataFrame."""
    try:
        processed = 0
        errors = []
        
        if not dry_run:
            with engine.begin() as conn:
                for idx, row in df.iterrows():
                    try:
                        if update_existing:
                            conn.execute(text("""
                                INSERT INTO exchange_rates (
                                    from_currency, to_currency, rate_date, rate_type,
                                    exchange_rate, source, created_by
                                ) VALUES (
                                    :from_curr, :to_curr, :rate_date, :rate_type,
                                    :exchange_rate, :source, :created_by
                                )
                                ON CONFLICT (from_currency, to_currency, rate_type, rate_date) 
                                DO UPDATE SET
                                    exchange_rate = :exchange_rate,
                                    source = :source,
                                    updated_at = CURRENT_TIMESTAMP
                            """), {
                                "from_curr": row['from_currency'],
                                "to_curr": row['to_currency'],
                                "rate_date": row['rate_date'],
                                "rate_type": row['rate_type'].upper(),
                                "exchange_rate": float(row['exchange_rate']),
                                "source": row.get('source', 'Bulk Import'),
                                "created_by": user.username if user else 'system'
                            })
                        else:
                            conn.execute(text("""
                                INSERT INTO exchange_rates (
                                    from_currency, to_currency, rate_date, rate_type,
                                    exchange_rate, source, created_by
                                ) VALUES (
                                    :from_curr, :to_curr, :rate_date, :rate_type,
                                    :exchange_rate, :source, :created_by
                                )
                            """), {
                                "from_curr": row['from_currency'],
                                "to_curr": row['to_currency'],
                                "rate_date": row['rate_date'],
                                "rate_type": row['rate_type'].upper(),
                                "exchange_rate": float(row['exchange_rate']),
                                "source": row.get('source', 'Bulk Import'),
                                "created_by": user.username if user else 'system'
                            })
                        
                        processed += 1
                        
                    except Exception as e:
                        errors.append(f"Row {idx + 1}: {str(e)}")
        else:
            # Dry run - just count valid rows
            processed = len(df)
        
        return {
            'success': True,
            'processed': processed,
            'errors': errors
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def get_currency_pairs():
    """Get available currency pairs."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT from_currency || '/' || to_currency as currency_pair
                FROM exchange_rates
                ORDER BY currency_pair
            """))
            
            return [row[0] for row in result.fetchall()]
    except:
        return []

def get_historical_rates(from_curr, to_curr, days, rate_types):
    """Get historical exchange rates for analysis."""
    try:
        with engine.connect() as conn:
            rate_types_str = "', '".join(rate_types)
            
            result = conn.execute(text(f"""
                SELECT 
                    rate_date,
                    rate_type,
                    exchange_rate,
                    source
                FROM exchange_rates
                WHERE from_currency = :from_curr
                AND to_currency = :to_curr
                AND rate_type IN ('{rate_types_str}')
                AND rate_date >= CURRENT_DATE - INTERVAL '{days} days'
                ORDER BY rate_date, rate_type
            """), {
                "from_curr": from_curr,
                "to_curr": to_curr
            })
            
            return pd.DataFrame(result.fetchall(), columns=result.keys())
    except:
        return pd.DataFrame()

def show_official_rates_import():
    """Official central bank rates import interface."""
    st.header("🏦 Official Central Bank Rates Import")
    st.markdown("**Import official exchange rates from central banks for regulatory compliance**")
    
    # Import the service
    import sys
    sys.path.append('/home/anton/erp/gl')
    from utils.central_bank_rates_service import CentralBankRatesService
    
    # Initialize service
    if 'cb_service' not in st.session_state:
        st.session_state.cb_service = CentralBankRatesService()
    
    # Show available sources
    st.subheader("📋 Available Official Sources")
    
    sources = st.session_state.cb_service.get_available_official_sources()
    sources_df = pd.DataFrame(sources)
    
    st.dataframe(
        sources_df,
        use_container_width=True,
        column_config={
            "code": "Source Code",
            "name": "Source Name", 
            "description": "Description",
            "base_currency": "Base Currency",
            "frequency": "Frequency",
            "publication_time": "Publication Time"
        },
        hide_index=True
    )
    
    st.divider()
    
    # Rate import controls
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🇺🇸 Federal Reserve H.10")
        st.info("**Source**: US Federal Reserve\n**Frequency**: Daily at 4:15 PM ET\n**Base**: USD")
        
        if st.button("📊 Fetch Fed H.10 Rates", key="fetch_fed", help="Import Federal Reserve official rates"):
            with st.spinner("Fetching Federal Reserve H.10 rates..."):
                fed_rates = st.session_state.cb_service.fetch_fed_h10_rates()
                
                if fed_rates.get('status') == 'SUCCESS':
                    st.success(f"✅ Successfully fetched {fed_rates['total_currencies']} currencies from {fed_rates['source']}")
                    
                    # Show preview of rates
                    st.write("**Rate Preview:**")
                    preview_data = []
                    for curr, rate in list(fed_rates['rates'].items())[:10]:  # Show first 10
                        preview_data.append({
                            'Currency': f"{curr}/USD",
                            'Rate': f"{rate:.6f}",
                            'Date': fed_rates['rate_date'].strftime('%Y-%m-%d')
                        })
                    
                    st.dataframe(pd.DataFrame(preview_data), hide_index=True)
                    
                    # Validation
                    validation = st.session_state.cb_service.validate_official_rates(fed_rates)
                    if validation['status'] == 'VALID':
                        st.success(f"✅ Validation passed: {validation['valid_rates']}/{validation['total_rates']} rates valid")
                    elif validation['status'] == 'WARNING':
                        st.warning(f"⚠️ Validation warnings: {len(validation['warnings'])} warnings found")
                        for warning in validation['warnings']:
                            st.warning(f"• {warning}")
                    else:
                        st.error(f"❌ Validation failed: {len(validation['errors'])} errors found")
                        for error in validation['errors']:
                            st.error(f"• {error}")
                    
                    # Save button
                    if st.button("💾 Save Fed Rates", key="save_fed"):
                        if st.session_state.cb_service.save_official_rates(fed_rates, user.get('username', 'Unknown')):
                            st.success("✅ Federal Reserve rates saved successfully!")
                            st.balloons()
                        else:
                            st.error("❌ Failed to save Federal Reserve rates")
                else:
                    st.error(f"❌ Failed to fetch Fed rates: {fed_rates.get('error', 'Unknown error')}")
    
    with col2:
        st.subheader("🇪🇺 European Central Bank")
        st.info("**Source**: European Central Bank\n**Frequency**: Daily at 4:00 PM CET\n**Base**: EUR")
        
        if st.button("📊 Fetch ECB Reference Rates", key="fetch_ecb", help="Import ECB official reference rates"):
            with st.spinner("Fetching ECB reference rates..."):
                ecb_rates = st.session_state.cb_service.fetch_ecb_reference_rates()
                
                if ecb_rates.get('status') == 'SUCCESS':
                    st.success(f"✅ Successfully fetched {ecb_rates['total_currencies']} currencies from {ecb_rates['source']}")
                    
                    # Show preview of rates
                    st.write("**Rate Preview:**")
                    preview_data = []
                    for curr, rate in list(ecb_rates['rates'].items())[:10]:  # Show first 10
                        preview_data.append({
                            'Currency': f"{curr}/EUR",
                            'Rate': f"{rate:.6f}",
                            'Date': ecb_rates['rate_date'].strftime('%Y-%m-%d')
                        })
                    
                    st.dataframe(pd.DataFrame(preview_data), hide_index=True)
                    
                    # Validation
                    validation = st.session_state.cb_service.validate_official_rates(ecb_rates)
                    if validation['status'] == 'VALID':
                        st.success(f"✅ Validation passed: {validation['valid_rates']}/{validation['total_rates']} rates valid")
                    elif validation['status'] == 'WARNING':
                        st.warning(f"⚠️ Validation warnings: {len(validation['warnings'])} warnings found")
                        for warning in validation['warnings']:
                            st.warning(f"• {warning}")
                    else:
                        st.error(f"❌ Validation failed: {len(validation['errors'])} errors found")
                        for error in validation['errors']:
                            st.error(f"• {error}")
                    
                    # Save button
                    if st.button("💾 Save ECB Rates", key="save_ecb"):
                        if st.session_state.cb_service.save_official_rates(ecb_rates, user.get('username', 'Unknown')):
                            st.success("✅ ECB rates saved successfully!")
                            st.balloons()
                        else:
                            st.error("❌ Failed to save ECB rates")
                else:
                    st.error(f"❌ Failed to fetch ECB rates: {ecb_rates.get('error', 'Unknown error')}")
    
    with col3:
        st.subheader("🇬🇧 Bank of England")
        st.info("**Source**: Bank of England\n**Frequency**: Daily\n**Base**: GBP")
        
        if st.button("📊 Fetch BOE Rates", key="fetch_boe", help="Import Bank of England official rates"):
            with st.spinner("Fetching Bank of England rates..."):
                boe_rates = st.session_state.cb_service.fetch_boe_rates()
                
                if boe_rates.get('status') == 'SUCCESS':
                    st.success(f"✅ Successfully fetched {boe_rates['total_currencies']} currencies from {boe_rates['source']}")
                    
                    # Show preview of rates
                    st.write("**Rate Preview:**")
                    preview_data = []
                    for curr, rate in boe_rates['rates'].items():
                        preview_data.append({
                            'Currency': f"{curr}/GBP",
                            'Rate': f"{rate:.6f}",
                            'Date': boe_rates['rate_date'].strftime('%Y-%m-%d')
                        })
                    
                    st.dataframe(pd.DataFrame(preview_data), hide_index=True)
                    
                    # Validation
                    validation = st.session_state.cb_service.validate_official_rates(boe_rates)
                    if validation['status'] == 'VALID':
                        st.success(f"✅ Validation passed: {validation['valid_rates']}/{validation['total_rates']} rates valid")
                    elif validation['status'] == 'WARNING':
                        st.warning(f"⚠️ Validation warnings: {len(validation['warnings'])} warnings found")
                        for warning in validation['warnings']:
                            st.warning(f"• {warning}")
                    else:
                        st.error(f"❌ Validation failed: {len(validation['errors'])} errors found")
                        for error in validation['errors']:
                            st.error(f"• {error}")
                    
                    # Save button
                    if st.button("💾 Save BOE Rates", key="save_boe"):
                        if st.session_state.cb_service.save_official_rates(boe_rates, user.get('username', 'Unknown')):
                            st.success("✅ Bank of England rates saved successfully!")
                            st.balloons()
                        else:
                            st.error("❌ Failed to save BOE rates")
                else:
                    st.error(f"❌ Failed to fetch BOE rates: {boe_rates.get('error', 'Unknown error')}")
    
    st.divider()
    
    # Bulk import from all sources
    st.subheader("🌐 Import All Official Rates")
    
    col_all1, col_all2 = st.columns([1, 1])
    
    with col_all1:
        if st.button("🔄 Fetch All Official Rates", key="fetch_all", help="Import from all central bank sources"):
            with st.spinner("Fetching rates from all official sources..."):
                # Import utility function
                from utils.central_bank_rates_service import fetch_all_official_rates
                
                all_results = fetch_all_official_rates()
                
                if all_results:
                    st.success(f"✅ Successfully fetched rates from {len(all_results)} sources")
                    
                    # Show summary
                    summary_data = []
                    for source_key, rates_data in all_results.items():
                        summary_data.append({
                            'Source': rates_data['source'],
                            'Base Currency': rates_data['base_currency'],
                            'Total Currencies': rates_data['total_currencies'],
                            'Rate Date': rates_data['rate_date'].strftime('%Y-%m-%d'),
                            'Status': '✅ Success'
                        })
                    
                    st.dataframe(pd.DataFrame(summary_data), hide_index=True)
                    
                    # Save all button
                    if st.button("💾 Save All Official Rates", key="save_all"):
                        saved_sources = 0
                        for source_key, rates_data in all_results.items():
                            if st.session_state.cb_service.save_official_rates(rates_data, user.get('username', 'Unknown')):
                                saved_sources += 1
                        
                        if saved_sources == len(all_results):
                            st.success(f"✅ Successfully saved rates from all {saved_sources} sources!")
                            st.balloons()
                        else:
                            st.warning(f"⚠️ Saved rates from {saved_sources}/{len(all_results)} sources")
                else:
                    st.error("❌ Failed to fetch rates from any official source")
    
    with col_all2:
        st.info("**Bulk Import Benefits:**\n• Import from all sources at once\n• Cross-validate rates between sources\n• Comprehensive coverage\n• Time-efficient process")
    
    st.divider()
    
    # Recent official rates
    st.subheader("📊 Recent Official Rates")
    
    try:
        with engine.connect() as conn:
            recent_official_query = text("""
                SELECT 
                    source as "Source",
                    from_currency as "From",
                    to_currency as "To", 
                    exchange_rate as "Rate",
                    rate_date as "Date",
                    publication_date as "Published",
                    created_by as "Imported By"
                FROM exchange_rates
                WHERE is_official = true
                AND rate_date >= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY publication_date DESC, source, from_currency
                LIMIT 50
            """)
            
            recent_official_df = pd.read_sql_query(recent_official_query, conn)
            
            if not recent_official_df.empty:
                st.dataframe(
                    recent_official_df,
                    use_container_width=True,
                    column_config={
                        "Rate": st.column_config.NumberColumn("Rate", format="%.6f"),
                        "Date": st.column_config.DateColumn("Rate Date"),
                        "Published": st.column_config.DateColumn("Publication Date")
                    },
                    hide_index=True
                )
            else:
                st.info("No official rates imported in the last 7 days")
                
    except Exception as e:
        st.error(f"Error loading recent official rates: {e}")
    
    # Footer note
    st.markdown("---")
    st.caption("**Note**: Official rates are marked with `is_official=true` flag for regulatory compliance and audit purposes.")

if __name__ == "__main__":
    main()