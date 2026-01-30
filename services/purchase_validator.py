"""Purchase Voucher Validation Service - Validates Purchase imports per Excel template rules."""

from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum

from models.debit_voucher import (
    PurchaseVoucher, GSTApplicability, TransactionType, TDSSection,
    GSTConfig, TDSConfig
)
from models.ledger_config import DebitVoucherConfig


class ValidationSeverity(Enum):
    """Severity levels for validation messages."""
    ERROR = "Error"      # Blocks import
    WARNING = "Warning"  # Shows warning but allows import
    INFO = "Info"        # Informational only


@dataclass
class ValidationMessage:
    """Single validation message."""
    field: str
    message: str
    severity: ValidationSeverity
    row_num: int = 0
    
    def __str__(self):
        return f"[{self.severity.value}] Row {self.row_num}: {self.field} - {self.message}"


class PurchaseVoucherValidator:
    """
    Validates Purchase Vouchers per the Excel template rules:
    - GST scenarios: Normal, RCM, Non-GST
    - Transaction types: Inter-State, Intra-State, Import
    - TDS sections: 194C, 194I, 194J, 194H, 195, 194A
    - Balance validations: GST amounts match rates
    - Required fields based on scenario
    """
    
    # GST Rate Tolerance (for floating point comparison)
    GST_TOLERANCE = 0.50
    
    # TDS Threshold limits (for validation)
    TDS_THRESHOLDS = {
        '194C': 30000,   # Contractors - per transaction
        '194I': 240000,  # Rent - annual
        '194J': 30000,   # Professional - per transaction
        '194H': 15000,   # Commission - annual
        '194A': 40000,   # Interest - annual
        '195': 0,        # Non-resident - no threshold
    }
    
    def __init__(self, config: DebitVoucherConfig = None):
        """Initialize validator with optional configuration."""
        self.config = config or DebitVoucherConfig.create_default()
    
    def validate_voucher(self, voucher: PurchaseVoucher, row_num: int = 0) -> List[ValidationMessage]:
        """
        Validate a single purchase voucher.
        
        Returns list of validation messages (errors, warnings, info).
        """
        messages = []
        
        # Required field validations
        messages.extend(self._validate_required_fields(voucher, row_num))
        
        # GST validations
        messages.extend(self._validate_gst(voucher, row_num))
        
        # TDS validations
        messages.extend(self._validate_tds(voucher, row_num))
        
        # RCM validations
        messages.extend(self._validate_rcm(voucher, row_num))
        
        # Amount validations
        messages.extend(self._validate_amounts(voucher, row_num))
        
        # Ledger validations
        messages.extend(self._validate_ledgers(voucher, row_num))
        
        return messages
    
    def validate_batch(self, vouchers: List[PurchaseVoucher]) -> Tuple[List[PurchaseVoucher], List[PurchaseVoucher], List[ValidationMessage]]:
        """
        Validate a batch of vouchers.
        
        Returns:
            - valid_vouchers: Vouchers that passed validation
            - invalid_vouchers: Vouchers with errors
            - all_messages: All validation messages
        """
        valid = []
        invalid = []
        all_messages = []
        
        for i, voucher in enumerate(vouchers, start=1):
            messages = self.validate_voucher(voucher, row_num=i)
            all_messages.extend(messages)
            
            # Check if any errors (not just warnings)
            has_errors = any(m.severity == ValidationSeverity.ERROR for m in messages)
            
            if has_errors:
                invalid.append(voucher)
            else:
                valid.append(voucher)
        
        return valid, invalid, all_messages
    
    def _validate_required_fields(self, voucher: PurchaseVoucher, row_num: int) -> List[ValidationMessage]:
        """Validate required fields are present."""
        messages = []
        
        if not voucher.voucher_no:
            messages.append(ValidationMessage(
                field="Voucher No",
                message="Voucher number is required",
                severity=ValidationSeverity.ERROR,
                row_num=row_num
            ))
        
        if not voucher.supplier_ledger:
            messages.append(ValidationMessage(
                field="Supplier Ledger",
                message="Supplier/Party ledger is required",
                severity=ValidationSeverity.ERROR,
                row_num=row_num
            ))
        
        if not voucher.expense_ledger:
            messages.append(ValidationMessage(
                field="Expense Ledger",
                message="Expense/Asset ledger is required",
                severity=ValidationSeverity.ERROR,
                row_num=row_num
            ))
        
        if voucher.base_amount <= 0:
            messages.append(ValidationMessage(
                field="Base Amount",
                message="Base amount must be greater than zero",
                severity=ValidationSeverity.ERROR,
                row_num=row_num
            ))
        
        return messages
    
    def _validate_gst(self, voucher: PurchaseVoucher, row_num: int) -> List[ValidationMessage]:
        """Validate GST configuration and amounts."""
        messages = []
        gst = voucher.gst
        
        # If GST is applicable, validate transaction type
        if gst.applicability == GSTApplicability.NORMAL:
            if gst.transaction_type == TransactionType.NOT_APPLICABLE:
                messages.append(ValidationMessage(
                    field="Transaction Type",
                    message="Transaction type (Inter/Intra-State) required when GST is applicable",
                    severity=ValidationSeverity.ERROR,
                    row_num=row_num
                ))
            
            # Validate GST amounts based on transaction type
            if gst.transaction_type == TransactionType.INTRA_STATE:
                # Should have CGST + SGST, no IGST
                if gst.igst_amount > 0:
                    messages.append(ValidationMessage(
                        field="IGST",
                        message="IGST should be zero for Intra-State transactions",
                        severity=ValidationSeverity.WARNING,
                        row_num=row_num
                    ))
                
                if gst.cgst_amount <= 0 and gst.sgst_amount <= 0 and voucher.base_amount > 0:
                    messages.append(ValidationMessage(
                        field="CGST/SGST",
                        message="CGST and SGST amounts expected for Intra-State GST",
                        severity=ValidationSeverity.WARNING,
                        row_num=row_num
                    ))
                
                # Validate CGST = SGST
                if abs(gst.cgst_amount - gst.sgst_amount) > self.GST_TOLERANCE:
                    messages.append(ValidationMessage(
                        field="CGST/SGST",
                        message=f"CGST ({gst.cgst_amount}) and SGST ({gst.sgst_amount}) should be equal",
                        severity=ValidationSeverity.WARNING,
                        row_num=row_num
                    ))
            
            elif gst.transaction_type == TransactionType.INTER_STATE:
                # Should have IGST, no CGST/SGST
                if gst.cgst_amount > 0 or gst.sgst_amount > 0:
                    messages.append(ValidationMessage(
                        field="CGST/SGST",
                        message="CGST/SGST should be zero for Inter-State transactions",
                        severity=ValidationSeverity.WARNING,
                        row_num=row_num
                    ))
                
                if gst.igst_amount <= 0 and voucher.base_amount > 0:
                    messages.append(ValidationMessage(
                        field="IGST",
                        message="IGST amount expected for Inter-State transactions",
                        severity=ValidationSeverity.WARNING,
                        row_num=row_num
                    ))
            
            # Validate GST rate range
            total_gst = gst.total_input_gst
            if voucher.base_amount > 0:
                effective_rate = (total_gst / voucher.base_amount) * 100
                valid_rates = [0, 5, 12, 18, 28]
                
                # Check if rate is close to a standard rate
                rate_match = False
                for rate in valid_rates:
                    if abs(effective_rate - rate) < 1.0:  # 1% tolerance
                        rate_match = True
                        break
                
                if not rate_match and total_gst > 0:
                    messages.append(ValidationMessage(
                        field="GST Rate",
                        message=f"Effective GST rate ({effective_rate:.1f}%) doesn't match standard rates (5/12/18/28%)",
                        severity=ValidationSeverity.WARNING,
                        row_num=row_num
                    ))
        
        # Validate GST ledgers
        if gst.applicability == GSTApplicability.NORMAL:
            if gst.transaction_type == TransactionType.INTRA_STATE:
                if not gst.input_cgst_ledger:
                    messages.append(ValidationMessage(
                        field="Input CGST Ledger",
                        message="Input CGST ledger required",
                        severity=ValidationSeverity.ERROR,
                        row_num=row_num
                    ))
                if not gst.input_sgst_ledger:
                    messages.append(ValidationMessage(
                        field="Input SGST Ledger",
                        message="Input SGST ledger required",
                        severity=ValidationSeverity.ERROR,
                        row_num=row_num
                    ))
            elif gst.transaction_type == TransactionType.INTER_STATE:
                if not gst.input_igst_ledger:
                    messages.append(ValidationMessage(
                        field="Input IGST Ledger",
                        message="Input IGST ledger required",
                        severity=ValidationSeverity.ERROR,
                        row_num=row_num
                    ))
        
        return messages
    
    def _validate_tds(self, voucher: PurchaseVoucher, row_num: int) -> List[ValidationMessage]:
        """Validate TDS configuration and amounts."""
        messages = []
        tds = voucher.tds
        
        if tds.applicable:
            # Validate TDS ledger
            if not tds.ledger:
                messages.append(ValidationMessage(
                    field="TDS Ledger",
                    message="TDS ledger required when TDS is applicable",
                    severity=ValidationSeverity.ERROR,
                    row_num=row_num
                ))
            
            # Validate TDS amount
            if tds.amount <= 0:
                messages.append(ValidationMessage(
                    field="TDS Amount",
                    message="TDS amount must be greater than zero when TDS is applicable",
                    severity=ValidationSeverity.ERROR,
                    row_num=row_num
                ))
            
            # Validate TDS rate range
            if voucher.base_amount > 0 and tds.amount > 0:
                effective_rate = (tds.amount / voucher.base_amount) * 100
                
                # Common TDS rates
                valid_rates = [1, 2, 5, 10, 20]
                rate_match = False
                for rate in valid_rates:
                    if abs(effective_rate - rate) < 0.5:
                        rate_match = True
                        break
                
                if not rate_match:
                    messages.append(ValidationMessage(
                        field="TDS Rate",
                        message=f"TDS rate ({effective_rate:.1f}%) is unusual. Common rates: 1/2/5/10/20%",
                        severity=ValidationSeverity.INFO,
                        row_num=row_num
                    ))
            
            # Validate threshold (informational)
            if tds.section != TDSSection.NONE:
                section = tds.section.value
                threshold = self.TDS_THRESHOLDS.get(section, 0)
                if threshold > 0 and voucher.base_amount < threshold:
                    messages.append(ValidationMessage(
                        field="TDS Threshold",
                        message=f"Amount below TDS threshold (₹{threshold:,}) for section {section}",
                        severity=ValidationSeverity.INFO,
                        row_num=row_num
                    ))
        
        return messages
    
    def _validate_rcm(self, voucher: PurchaseVoucher, row_num: int) -> List[ValidationMessage]:
        """Validate RCM (Reverse Charge Mechanism) configuration."""
        messages = []
        gst = voucher.gst
        
        if gst.applicability == GSTApplicability.RCM:
            # Validate RCM GST amounts
            if gst.transaction_type == TransactionType.INTRA_STATE:
                if gst.rcm_igst_amount > 0:
                    messages.append(ValidationMessage(
                        field="RCM IGST",
                        message="RCM IGST should be zero for Intra-State transactions",
                        severity=ValidationSeverity.WARNING,
                        row_num=row_num
                    ))
                
                if gst.rcm_cgst_amount <= 0 and gst.rcm_sgst_amount <= 0:
                    messages.append(ValidationMessage(
                        field="RCM GST",
                        message="RCM CGST/SGST amounts expected for Intra-State RCM",
                        severity=ValidationSeverity.WARNING,
                        row_num=row_num
                    ))
            
            elif gst.transaction_type == TransactionType.INTER_STATE:
                if gst.rcm_cgst_amount > 0 or gst.rcm_sgst_amount > 0:
                    messages.append(ValidationMessage(
                        field="RCM CGST/SGST",
                        message="RCM CGST/SGST should be zero for Inter-State transactions",
                        severity=ValidationSeverity.WARNING,
                        row_num=row_num
                    ))
            
            # Validate RCM ledgers
            if gst.transaction_type == TransactionType.INTRA_STATE:
                if not gst.rcm_output_cgst_ledger:
                    messages.append(ValidationMessage(
                        field="RCM Output CGST Ledger",
                        message="RCM Output CGST ledger required",
                        severity=ValidationSeverity.ERROR,
                        row_num=row_num
                    ))
                if not gst.rcm_output_sgst_ledger:
                    messages.append(ValidationMessage(
                        field="RCM Output SGST Ledger",
                        message="RCM Output SGST ledger required",
                        severity=ValidationSeverity.ERROR,
                        row_num=row_num
                    ))
            elif gst.transaction_type == TransactionType.INTER_STATE:
                if not gst.rcm_output_igst_ledger:
                    messages.append(ValidationMessage(
                        field="RCM Output IGST Ledger",
                        message="RCM Output IGST ledger required",
                        severity=ValidationSeverity.ERROR,
                        row_num=row_num
                    ))
        
        return messages
    
    def _validate_amounts(self, voucher: PurchaseVoucher, row_num: int) -> List[ValidationMessage]:
        """Validate amount calculations."""
        messages = []
        
        # Validate net payable is positive
        if voucher.net_payable < 0:
            messages.append(ValidationMessage(
                field="Net Payable",
                message=f"Net payable amount is negative (₹{voucher.net_payable:,.2f})",
                severity=ValidationSeverity.ERROR,
                row_num=row_num
            ))
        
        # Validate TDS doesn't exceed base amount
        if voucher.tds.amount > voucher.base_amount:
            messages.append(ValidationMessage(
                field="TDS Amount",
                message="TDS amount exceeds base amount",
                severity=ValidationSeverity.ERROR,
                row_num=row_num
            ))
        
        # Validate GST doesn't exceed reasonable percentage (50%)
        if voucher.total_gst_amount > voucher.base_amount * 0.5:
            messages.append(ValidationMessage(
                field="GST Amount",
                message="GST amount exceeds 50% of base amount",
                severity=ValidationSeverity.WARNING,
                row_num=row_num
            ))
        
        return messages
    
    def _validate_ledgers(self, voucher: PurchaseVoucher, row_num: int) -> List[ValidationMessage]:
        """Validate ledger names against configured ledgers."""
        messages = []
        
        # Check if supplier is in configured list (informational)
        supplier_names = [s.name for s in self.config.get_active_suppliers()]
        if supplier_names and voucher.supplier_ledger not in supplier_names:
            messages.append(ValidationMessage(
                field="Supplier Ledger",
                message=f"Supplier '{voucher.supplier_ledger}' not in configured supplier list",
                severity=ValidationSeverity.INFO,
                row_num=row_num
            ))
        
        # Check if expense ledger is in configured list (informational)
        expense_names = [e.display_name for e in self.config.get_active_expense_ledgers()]
        if expense_names and voucher.expense_ledger not in expense_names:
            # Also check main_name only
            main_names = [e.main_name for e in self.config.get_active_expense_ledgers()]
            if voucher.expense_ledger not in main_names:
                messages.append(ValidationMessage(
                    field="Expense Ledger",
                    message=f"Expense '{voucher.expense_ledger}' not in configured expense list",
                    severity=ValidationSeverity.INFO,
                    row_num=row_num
                ))
        
        return messages
    
    def get_validation_summary(self, messages: List[ValidationMessage]) -> dict:
        """Get summary of validation results."""
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]
        infos = [m for m in messages if m.severity == ValidationSeverity.INFO]
        
        return {
            'total_messages': len(messages),
            'errors': len(errors),
            'warnings': len(warnings),
            'info': len(infos),
            'is_valid': len(errors) == 0,
            'error_messages': [str(m) for m in errors],
            'warning_messages': [str(m) for m in warnings]
        }
