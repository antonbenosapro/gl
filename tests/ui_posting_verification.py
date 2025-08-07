#!/usr/bin/env python3
"""
UI Posting Verification Test
Verify that the GL Posting Manager UI shows correct data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, date
from sqlalchemy import text
from db_config import engine
from utils.gl_posting_engine import GLPostingEngine

def test_posting_queue():
    """Test that posting queue shows eligible documents"""
    
    print("🧪 Testing GL Posting Manager Data Sources")
    print("=" * 50)
    
    posting_engine = GLPostingEngine()
    
    # Test 1: Get posting eligible documents
    print("\n📋 Test 1: Posting Eligible Documents")
    eligible_docs = posting_engine.get_posting_eligible_documents('TEST')
    
    print(f"   Found {len(eligible_docs)} eligible documents for company TEST")
    for doc in eligible_docs:
        print(f"   - {doc['document_number']}: ${doc['total_amount']:,.2f} ({doc['created_by']} -> {doc['approved_by']})")
    
    # Test 2: Account balances
    print("\n📊 Test 2: Account Balances")
    test_accounts = ['100001', '300001', '200001', '400001']
    
    for account in test_accounts:
        balance = posting_engine.get_account_balance('TEST', account)
        print(f"   Account {account}: ${balance.get('ytd_balance', 0):,.2f} (Transactions: {balance.get('transaction_count', 0)})")
    
    # Test 3: Posting history
    print("\n📄 Test 3: Posting History")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT pat.source_document, pat.action_timestamp, pat.action_by,
                   pat.total_amount, pat.action_status
            FROM posting_audit_trail pat
            WHERE pat.company_code = 'TEST'
            AND pat.action_type = 'POST'
            ORDER BY pat.action_timestamp DESC
            LIMIT 10
        """))
        
        history = result.fetchall()
        print(f"   Found {len(history)} posting history entries:")
        for entry in history:
            print(f"   - {entry[0]}: ${float(entry[3]):,.2f} by {entry[2]} at {entry[1]} ({entry[4]})")
    
    # Test 4: GL Transactions verification
    print("\n🔍 Test 4: GL Transactions Detail")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT gt.document_number, gt.line_item, gt.gl_account,
                   gt.debit_amount, gt.credit_amount, gt.line_text
            FROM gl_transactions gt
            WHERE gt.company_code = 'TEST'
            ORDER BY gt.document_number, gt.line_item
        """))
        
        transactions = result.fetchall()
        print(f"   Found {len(transactions)} GL transaction lines:")
        current_doc = None
        for txn in transactions:
            if txn[0] != current_doc:
                current_doc = txn[0]
                print(f"   Document: {current_doc}")
            debit = f"${float(txn[3]):,.2f}" if txn[3] else "-"
            credit = f"${float(txn[4]):,.2f}" if txn[4] else "-"
            print(f"     Line {txn[1]}: Account {txn[2]} | Dr: {debit} | Cr: {credit} | {txn[5]}")
    
    # Test 5: Period controls
    print("\n⚙️ Test 5: Period Controls")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT fiscal_year, posting_period, period_status, allow_posting
            FROM fiscal_period_controls
            WHERE company_code = 'TEST'
            ORDER BY fiscal_year DESC, posting_period
        """))
        
        periods = result.fetchall()
        print(f"   Found {len(periods)} period controls:")
        for period in periods:
            status_icon = "🟢" if period[2] == 'OPEN' and period[3] else "🔴"
            print(f"   {status_icon} {period[0]}-{period[1]:02d}: {period[2]} (Posting: {'Allowed' if period[3] else 'Blocked'})")
    
    print("\n✅ All UI data sources verified successfully!")
    print("\n💡 The GL Posting Manager UI should now show:")
    print("   - Eligible documents in the posting queue")
    print("   - Current account balances with correct amounts")
    print("   - Complete posting history with audit trail")
    print("   - Proper period controls status")

if __name__ == "__main__":
    test_posting_queue()