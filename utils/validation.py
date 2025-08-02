"""Input validation utilities for the GL ERP system"""

import re
from datetime import datetime, date
from typing import Union, List, Optional, Any
import pandas as pd
from pydantic import BaseModel, validator, ValidationError


class ValidationError(Exception):
    """Custom validation error"""
    pass


class GLAccountValidator(BaseModel):
    """Validator for GL Account data"""
    glaccountid: str
    companycodeid: str
    accountname: str
    accounttype: str
    isreconaccount: bool = False
    isopenitemmanaged: bool = False
    
    @validator('glaccountid')
    def validate_gl_account_id(cls, v):
        if not v or not v.strip():
            raise ValueError('GL Account ID cannot be empty')
        if not re.match(r'^[A-Z0-9]{3,10}$', v.strip()):
            raise ValueError('GL Account ID must be 3-10 alphanumeric characters')
        return v.strip().upper()
    
    @validator('companycodeid')
    def validate_company_code(cls, v):
        if not v or not v.strip():
            raise ValueError('Company Code cannot be empty')
        if not re.match(r'^[A-Z0-9]{2,5}$', v.strip()):
            raise ValueError('Company Code must be 2-5 alphanumeric characters')
        return v.strip().upper()
    
    @validator('accountname')
    def validate_account_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Account Name cannot be empty')
        if len(v.strip()) > 100:
            raise ValueError('Account Name cannot exceed 100 characters')
        return v.strip()
    
    @validator('accounttype')
    def validate_account_type(cls, v):
        valid_types = ['Asset', 'Liability', 'Equity', 'Revenue', 'Expense']
        if v not in valid_types:
            raise ValueError(f'Account Type must be one of: {", ".join(valid_types)}')
        return v


class JournalEntryHeaderValidator(BaseModel):
    """Validator for Journal Entry Header data"""
    documentnumber: str
    companycodeid: str
    postingdate: Union[str, date]
    documentdate: Union[str, date]
    fiscalyear: int
    period: int
    reference: str = ""
    currencycode: str
    createdby: str = ""
    
    @validator('documentnumber')
    def validate_document_number(cls, v):
        if not v or not v.strip():
            raise ValueError('Document Number cannot be empty')
        if not re.match(r'^[A-Z]{2}\d{5,15}$', v.strip()):
            raise ValueError('Document Number must follow format: XX##### (e.g., JE00001, JE2025121001, ST202512099969361)')
        return v.strip().upper()
    
    @validator('companycodeid')
    def validate_company_code(cls, v):
        if not v or not v.strip():
            raise ValueError('Company Code cannot be empty')
        if not re.match(r'^[A-Z0-9]{2,5}$', v.strip()):
            raise ValueError('Company Code must be 2-5 alphanumeric characters')
        return v.strip().upper()
    
    @validator('postingdate', 'documentdate')
    def validate_dates(cls, v):
        if isinstance(v, str):
            try:
                return datetime.strptime(v, '%Y-%m-%d').date()
            except ValueError:
                raise ValueError('Date must be in YYYY-MM-DD format')
        return v
    
    @validator('fiscalyear')
    def validate_fiscal_year(cls, v):
        current_year = datetime.now().year
        if v < 2000 or v > current_year + 5:
            raise ValueError(f'Fiscal Year must be between 2000 and {current_year + 5}')
        return v
    
    @validator('period')
    def validate_period(cls, v):
        if v < 1 or v > 12:
            raise ValueError('Period must be between 1 and 12')
        return v
    
    @validator('currencycode')
    def validate_currency_code(cls, v):
        if not v or not v.strip():
            raise ValueError('Currency Code cannot be empty')
        if not re.match(r'^[A-Z]{3}$', v.strip()):
            raise ValueError('Currency Code must be 3 letters (e.g., USD, EUR)')
        return v.strip().upper()


class JournalEntryLineValidator(BaseModel):
    """Validator for Journal Entry Line data"""
    linenumber: int
    glaccountid: str
    description: str
    debitamount: float = 0.0
    creditamount: float = 0.0
    currencycode: str
    ledgerid: Optional[str] = None
    
    @validator('glaccountid')
    def validate_gl_account_id(cls, v):
        if not v or not v.strip():
            raise ValueError('GL Account ID cannot be empty')
        return v.strip().upper()
    
    @validator('description')
    def validate_description(cls, v):
        if not v or not v.strip():
            raise ValueError('Description cannot be empty')
        if len(v.strip()) > 255:
            raise ValueError('Description cannot exceed 255 characters')
        return v.strip()
    
    @validator('debitamount', 'creditamount')
    def validate_amounts(cls, v):
        if v < 0:
            raise ValueError('Amounts cannot be negative')
        return round(v, 2)
    
    def validate_debit_credit_balance(self):
        """Validate that exactly one of debit or credit is non-zero"""
        if self.debitamount > 0 and self.creditamount > 0:
            raise ValueError('Line cannot have both debit and credit amounts')
        if self.debitamount == 0 and self.creditamount == 0:
            raise ValueError('Line must have either debit or credit amount')


def validate_journal_entry_balance(lines: List[JournalEntryLineValidator]) -> bool:
    """Validate that total debits equal total credits"""
    total_debits = sum(line.debitamount for line in lines)
    total_credits = sum(line.creditamount for line in lines)
    
    if abs(total_debits - total_credits) > 0.01:  # Allow for small rounding differences
        raise ValidationError(f'Total debits ({total_debits:.2f}) must equal total credits ({total_credits:.2f})')
    
    return True


def validate_dataframe_columns(df: pd.DataFrame, required_columns: List[str]) -> List[str]:
    """Validate that DataFrame has required columns"""
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValidationError(f'Missing required columns: {", ".join(missing_columns)}')
    return []


def sanitize_string_input(value: Any, max_length: Optional[int] = None) -> str:
    """Sanitize string input by stripping whitespace and limiting length"""
    if value is None:
        return ""
    
    sanitized = str(value).strip()
    
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized


def validate_numeric_input(value: Any, min_value: Optional[float] = None, 
                          max_value: Optional[float] = None) -> float:
    """Validate and convert numeric input"""
    try:
        numeric_value = float(value)
    except (ValueError, TypeError):
        raise ValidationError(f'Invalid numeric value: {value}')
    
    if min_value is not None and numeric_value < min_value:
        raise ValidationError(f'Value {numeric_value} is below minimum {min_value}')
    
    if max_value is not None and numeric_value > max_value:
        raise ValidationError(f'Value {numeric_value} is above maximum {max_value}')
    
    return numeric_value