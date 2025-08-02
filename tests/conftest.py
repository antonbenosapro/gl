import pytest
import pandas as pd
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool


@pytest.fixture
def mock_engine():
    """Create a mock SQLAlchemy engine for testing"""
    engine = Mock()
    connection = Mock()
    engine.connect.return_value.__enter__ = Mock(return_value=connection)
    engine.connect.return_value.__exit__ = Mock(return_value=None)
    engine.begin.return_value.__enter__ = Mock(return_value=connection)
    engine.begin.return_value.__exit__ = Mock(return_value=None)
    return engine


@pytest.fixture
def sample_glaccount_data():
    """Sample GL Account data for testing"""
    return pd.DataFrame({
        'GLAccountID': ['1001', '1002', '2001'],
        'CompanyCodeID': ['C001', 'C001', 'C001'],
        'AccountName': ['Cash', 'Accounts Receivable', 'Accounts Payable'],
        'AccountType': ['Asset', 'Asset', 'Liability'],
        'IsReconAccount': [True, False, False],
        'IsOpenItemManaged': [False, True, True]
    })


@pytest.fixture
def sample_journal_entry_data():
    """Sample Journal Entry data for testing"""
    return {
        'header': {
            'documentnumber': 'JE00001',
            'companycodeid': 'C001',
            'postingdate': '2025-01-01',
            'documentdate': '2025-01-01',
            'fiscalyear': 2025,
            'period': 1,
            'reference': 'Test Entry',
            'currencycode': 'USD',
            'createdby': 'testuser'
        },
        'lines': [
            {
                'linenumber': 1,
                'glaccountid': '1001',
                'description': 'Test Debit',
                'debitamount': 100.00,
                'creditamount': 0.00,
                'currencycode': 'USD',
                'ledgerid': 'L001'
            },
            {
                'linenumber': 2,
                'glaccountid': '2001',
                'description': 'Test Credit',
                'debitamount': 0.00,
                'creditamount': 100.00,
                'currencycode': 'USD',
                'ledgerid': 'L001'
            }
        ]
    }