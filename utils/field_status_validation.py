"""
Field Status Group Validation Engine
Implements 3-level hierarchy for field control validation in journal entries and other postings.

Hierarchy (highest to lowest priority):
1. Document Type FSG (document-specific overrides)
2. GL Account FSG (account-specific overrides)  
3. Account Group Default FSG (inherited defaults)

Author: Claude Code Assistant
Date: August 7, 2025
"""

from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import text
from db_config import engine
from utils.logger import get_logger
from dataclasses import dataclass
from enum import Enum

logger = get_logger("field_status_validation")


class FieldStatusType(Enum):
    """Field status control types"""
    SUP = "SUP"  # Suppress - field is hidden
    REQ = "REQ"  # Required - field must be filled
    OPT = "OPT"  # Optional - field can be filled
    DIS = "DIS"  # Display - field shown but not editable


@dataclass
class FieldStatusGroup:
    """Field Status Group configuration"""
    group_id: str
    group_name: str
    business_unit_status: FieldStatusType
    business_area_status: FieldStatusType
    tax_code_status: FieldStatusType
    reference_field_status: FieldStatusType
    document_header_text_status: FieldStatusType
    assignment_field_status: FieldStatusType
    text_field_status: FieldStatusType
    trading_partner_status: FieldStatusType
    partner_company_status: FieldStatusType
    payment_terms_status: FieldStatusType
    baseline_date_status: FieldStatusType
    amount_in_local_currency_status: FieldStatusType
    exchange_rate_status: FieldStatusType
    quantity_status: FieldStatusType
    base_unit_status: FieldStatusType
    house_bank_status: FieldStatusType
    account_id_status: FieldStatusType
    is_active: bool = True
    allow_negative_postings: bool = True


@dataclass
class PostingData:
    """Data structure for posting validation"""
    document_type: Optional[str] = None
    gl_account_id: Optional[str] = None
    business_unit_id: Optional[str] = None
    business_area: Optional[str] = None
    tax_code: Optional[str] = None
    reference: Optional[str] = None
    document_header_text: Optional[str] = None
    assignment: Optional[str] = None
    text: Optional[str] = None
    trading_partner: Optional[str] = None
    partner_company: Optional[str] = None
    payment_terms: Optional[str] = None
    baseline_date: Optional[str] = None
    amount_local_currency: Optional[float] = None
    exchange_rate: Optional[float] = None
    quantity: Optional[float] = None
    base_unit: Optional[str] = None
    house_bank: Optional[str] = None
    account_id: Optional[str] = None


class FieldStatusValidationError(Exception):
    """Custom exception for field status validation errors"""
    def __init__(self, field_name: str, message: str, field_status: FieldStatusType):
        self.field_name = field_name
        self.message = message
        self.field_status = field_status
        super().__init__(f"{field_name}: {message}")


class FieldStatusGroupEngine:
    """Main Field Status Group validation engine"""
    
    def __init__(self):
        self._fsg_cache = {}  # Cache for FSG configurations
        
    def get_effective_field_status_group(
        self, 
        document_type: Optional[str] = None,
        gl_account_id: Optional[str] = None
    ) -> Optional[FieldStatusGroup]:
        """
        Determine the effective Field Status Group using 3-level hierarchy:
        1. Document Type FSG (highest priority)
        2. GL Account FSG (medium priority)
        3. Account Group Default FSG (lowest priority)
        """
        try:
            with engine.connect() as conn:
                effective_fsg_id = None
                source = None
                
                # Level 1: Check Document Type Override
                if document_type:
                    doc_fsg = conn.execute(text("""
                        SELECT field_status_group, document_type_name
                        FROM document_types 
                        WHERE document_type = :doc_type 
                        AND field_status_group IS NOT NULL
                    """), {"doc_type": document_type}).fetchone()
                    
                    if doc_fsg:
                        effective_fsg_id = doc_fsg[0]
                        source = f"Document Type {document_type} ({doc_fsg[1]})"
                        logger.info(f"Using FSG from document type: {effective_fsg_id}")
                
                # Level 2: Check GL Account Specific (if no document override)
                if not effective_fsg_id and gl_account_id:
                    account_fsg = conn.execute(text("""
                        SELECT field_status_group, accountname
                        FROM glaccount 
                        WHERE glaccountid = :account_id 
                        AND field_status_group IS NOT NULL
                        AND (marked_for_deletion = FALSE OR marked_for_deletion IS NULL)
                    """), {"account_id": gl_account_id}).fetchone()
                    
                    if account_fsg:
                        effective_fsg_id = account_fsg[0]
                        source = f"GL Account {gl_account_id} ({account_fsg[1]})"
                        logger.info(f"Using FSG from GL account: {effective_fsg_id}")
                
                # Level 3: Check Account Group Default (if no account override)
                if not effective_fsg_id and gl_account_id:
                    group_fsg = conn.execute(text("""
                        SELECT ag.default_field_status_group, ag.group_name, ag.group_code
                        FROM glaccount ga
                        JOIN account_groups ag ON ga.account_group_code = ag.group_code
                        WHERE ga.glaccountid = :account_id
                        AND ag.default_field_status_group IS NOT NULL
                        AND ag.is_active = TRUE
                        AND (ga.marked_for_deletion = FALSE OR ga.marked_for_deletion IS NULL)
                    """), {"account_id": gl_account_id}).fetchone()
                    
                    if group_fsg:
                        effective_fsg_id = group_fsg[0]
                        source = f"Account Group {group_fsg[2]} ({group_fsg[1]})"
                        logger.info(f"Using FSG from account group: {effective_fsg_id}")
                
                # If we found an FSG, load its configuration
                if effective_fsg_id:
                    fsg_config = self._load_field_status_group(effective_fsg_id)
                    if fsg_config:
                        logger.info(f"Effective FSG: {effective_fsg_id} from {source}")
                        return fsg_config
                
                logger.warning(f"No Field Status Group found for document_type={document_type}, gl_account={gl_account_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error determining effective FSG: {e}")
            return None
    
    def _load_field_status_group(self, group_id: str) -> Optional[FieldStatusGroup]:
        """Load Field Status Group configuration from database with caching"""
        
        # Check cache first
        if group_id in self._fsg_cache:
            return self._fsg_cache[group_id]
            
        try:
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        group_id, group_name, business_unit_status, business_area_status,
                        tax_code_status, reference_field_status, document_header_text_status,
                        assignment_field_status, text_field_status, trading_partner_status,
                        partner_company_status, payment_terms_status, baseline_date_status,
                        amount_in_local_currency_status, exchange_rate_status, quantity_status,
                        base_unit_status, house_bank_status, account_id_status,
                        is_active, allow_negative_postings
                    FROM field_status_groups 
                    WHERE group_id = :group_id
                """), {"group_id": group_id}).fetchone()
                
                if not result:
                    logger.error(f"Field Status Group {group_id} not found")
                    return None
                
                fsg = FieldStatusGroup(
                    group_id=result[0],
                    group_name=result[1],
                    business_unit_status=FieldStatusType(result[2]),
                    business_area_status=FieldStatusType(result[3]),
                    tax_code_status=FieldStatusType(result[4]),
                    reference_field_status=FieldStatusType(result[5]),
                    document_header_text_status=FieldStatusType(result[6]),
                    assignment_field_status=FieldStatusType(result[7]),
                    text_field_status=FieldStatusType(result[8]),
                    trading_partner_status=FieldStatusType(result[9]),
                    partner_company_status=FieldStatusType(result[10]),
                    payment_terms_status=FieldStatusType(result[11]),
                    baseline_date_status=FieldStatusType(result[12]),
                    amount_in_local_currency_status=FieldStatusType(result[13]),
                    exchange_rate_status=FieldStatusType(result[14]),
                    quantity_status=FieldStatusType(result[15]),
                    base_unit_status=FieldStatusType(result[16]),
                    house_bank_status=FieldStatusType(result[17]),
                    account_id_status=FieldStatusType(result[18]),
                    is_active=result[19],
                    allow_negative_postings=result[20]
                )
                
                # Cache the result
                self._fsg_cache[group_id] = fsg
                return fsg
                
        except Exception as e:
            logger.error(f"Error loading FSG {group_id}: {e}")
            return None
    
    def validate_posting_fields(
        self, 
        posting_data: PostingData,
        line_number: Optional[int] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate posting fields against effective Field Status Group rules
        Returns (is_valid, list_of_errors)
        """
        errors = []
        line_prefix = f"Line {line_number}: " if line_number else ""
        
        # Get effective FSG
        fsg = self.get_effective_field_status_group(
            document_type=posting_data.document_type,
            gl_account_id=posting_data.gl_account_id
        )
        
        if not fsg:
            # If no FSG found, use minimal validation
            logger.warning("No FSG found - using minimal validation")
            return True, []
        
        if not fsg.is_active:
            errors.append(f"{line_prefix}Field Status Group {fsg.group_id} is inactive")
            return False, errors
        
        # Field-by-field validation
        field_validations = [
            ("Business Unit", fsg.business_unit_status, posting_data.business_unit_id),
            ("Business Area", fsg.business_area_status, posting_data.business_area),
            ("Tax Code", fsg.tax_code_status, posting_data.tax_code),
            ("Reference", fsg.reference_field_status, posting_data.reference),
            ("Document Header Text", fsg.document_header_text_status, posting_data.document_header_text),
            ("Assignment", fsg.assignment_field_status, posting_data.assignment),
            ("Text", fsg.text_field_status, posting_data.text),
            ("Trading Partner", fsg.trading_partner_status, posting_data.trading_partner),
            ("Partner Company", fsg.partner_company_status, posting_data.partner_company),
            ("Payment Terms", fsg.payment_terms_status, posting_data.payment_terms),
            ("Baseline Date", fsg.baseline_date_status, posting_data.baseline_date),
            ("Amount Local Currency", fsg.amount_in_local_currency_status, posting_data.amount_local_currency),
            ("Exchange Rate", fsg.exchange_rate_status, posting_data.exchange_rate),
            ("Quantity", fsg.quantity_status, posting_data.quantity),
            ("Base Unit", fsg.base_unit_status, posting_data.base_unit),
            ("House Bank", fsg.house_bank_status, posting_data.house_bank),
            ("Account ID", fsg.account_id_status, posting_data.account_id),
        ]
        
        for field_name, field_status, field_value in field_validations:
            error_msg = self._validate_individual_field(
                field_name, field_status, field_value, line_prefix
            )
            if error_msg:
                errors.append(error_msg)
        
        is_valid = len(errors) == 0
        if is_valid:
            logger.info(f"{line_prefix}All field validations passed using FSG {fsg.group_id}")
        else:
            logger.warning(f"{line_prefix}Field validation failed with {len(errors)} errors using FSG {fsg.group_id}")
            
        return is_valid, errors
    
    def _validate_individual_field(
        self, 
        field_name: str, 
        field_status: FieldStatusType, 
        field_value: Any,
        line_prefix: str = "",
        original_value: Any = None,
        is_new_entry: bool = True
    ) -> Optional[str]:
        """Validate individual field against its status"""
        
        # Check if field has value (not None, not empty string, not just whitespace)
        has_value = (
            field_value is not None and 
            str(field_value).strip() != '' and
            field_value != 0  # Don't treat 0 as empty for numeric fields
        )
        
        if field_status == FieldStatusType.REQ:
            if not has_value:
                return f"{line_prefix}{field_name} is required (FSG: REQ)"
                
        elif field_status == FieldStatusType.SUP:
            if has_value:
                return f"{line_prefix}{field_name} should not be provided (FSG: SUP - Suppressed)"
        
        elif field_status == FieldStatusType.DIS:
            # DIS fields should not be modified in existing entries
            if not is_new_entry and original_value is not None:
                current_str = str(field_value).strip() if field_value is not None else ""
                original_str = str(original_value).strip() if original_value is not None else ""
                if current_str != original_str:
                    return f"{line_prefix}{field_name} is Display Only (DIS) and cannot be changed from '{original_str}' to '{current_str}'"
            # For new entries, DIS fields can have values but user should be warned
            
        # OPT allows any value
        return None
    
    def get_field_controls_for_ui(
        self, 
        document_type: Optional[str] = None,
        gl_account_id: Optional[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get field control configuration for UI rendering
        Returns dict with field names and their control settings
        """
        fsg = self.get_effective_field_status_group(document_type, gl_account_id)
        
        if not fsg:
            # Return default controls if no FSG
            return self._get_default_field_controls()
        
        return {
            "business_unit_id": {
                "status": fsg.business_unit_status.value,
                "required": fsg.business_unit_status == FieldStatusType.REQ,
                "visible": fsg.business_unit_status != FieldStatusType.SUP,
                "editable": fsg.business_unit_status != FieldStatusType.DIS,
                "label": "Business Unit"
            },
            "business_area": {
                "status": fsg.business_area_status.value,
                "required": fsg.business_area_status == FieldStatusType.REQ,
                "visible": fsg.business_area_status != FieldStatusType.SUP,
                "editable": fsg.business_area_status != FieldStatusType.DIS,
                "label": "Business Area"
            },
            "tax_code": {
                "status": fsg.tax_code_status.value,
                "required": fsg.tax_code_status == FieldStatusType.REQ,
                "visible": fsg.tax_code_status != FieldStatusType.SUP,
                "editable": fsg.tax_code_status != FieldStatusType.DIS,
                "label": "Tax Code"
            },
            "reference": {
                "status": fsg.reference_field_status.value,
                "required": fsg.reference_field_status == FieldStatusType.REQ,
                "visible": fsg.reference_field_status != FieldStatusType.SUP,
                "editable": fsg.reference_field_status != FieldStatusType.DIS,
                "label": "Reference"
            },
            "assignment": {
                "status": fsg.assignment_field_status.value,
                "required": fsg.assignment_field_status == FieldStatusType.REQ,
                "visible": fsg.assignment_field_status != FieldStatusType.SUP,
                "editable": fsg.assignment_field_status != FieldStatusType.DIS,
                "label": "Assignment"
            },
            "text": {
                "status": fsg.text_field_status.value,
                "required": fsg.text_field_status == FieldStatusType.REQ,
                "visible": fsg.text_field_status != FieldStatusType.SUP,
                "editable": fsg.text_field_status != FieldStatusType.DIS,
                "label": "Text"
            },
            # Add more fields as needed...
            "_fsg_info": {
                "group_id": fsg.group_id,
                "group_name": fsg.group_name,
                "allow_negative_postings": fsg.allow_negative_postings
            }
        }
    
    def _get_default_field_controls(self) -> Dict[str, Dict[str, Any]]:
        """Return default field controls when no FSG is found"""
        default_fields = ["business_unit_id", "business_area", "tax_code", "reference", "assignment", "text"]
        
        return {
            field: {
                "status": "OPT",
                "required": False,
                "visible": True,
                "editable": True,
                "label": field.replace("_", " ").title()
            }
            for field in default_fields
        }
    
    def clear_cache(self):
        """Clear FSG configuration cache"""
        self._fsg_cache.clear()
        logger.info("Field Status Group cache cleared")


# Global instance
field_status_engine = FieldStatusGroupEngine()


def validate_journal_entry_line(
    document_type: str,
    gl_account_id: str,
    business_unit_id: Optional[str] = None,
    business_area: Optional[str] = None,
    tax_code: Optional[str] = None,
    reference: Optional[str] = None,
    assignment: Optional[str] = None,
    text: Optional[str] = None,
    line_number: Optional[int] = None,
    **kwargs
) -> Tuple[bool, List[str]]:
    """
    Convenience function to validate a journal entry line
    Returns (is_valid, list_of_errors)
    """
    posting_data = PostingData(
        document_type=document_type,
        gl_account_id=gl_account_id,
        business_unit_id=business_unit_id,
        business_area=business_area,
        tax_code=tax_code,
        reference=reference,
        assignment=assignment,
        text=text,
        **kwargs
    )
    
    return field_status_engine.validate_posting_fields(posting_data, line_number)


def get_field_controls_for_account(
    gl_account_id: str,
    document_type: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Convenience function to get field controls for a specific GL account
    """
    return field_status_engine.get_field_controls_for_ui(document_type, gl_account_id)


# Export main classes and functions
__all__ = [
    'FieldStatusGroupEngine',
    'FieldStatusGroup', 
    'PostingData',
    'FieldStatusType',
    'FieldStatusValidationError',
    'field_status_engine',
    'validate_journal_entry_line',
    'get_field_controls_for_account'
]