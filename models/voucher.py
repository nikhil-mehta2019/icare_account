from dataclasses import dataclass, field
from datetime import datetime
from datetime import date as date_type, date as dt_date  # Aliases to avoid conflict
from typing import Optional, Dict, Any
from enum import Enum
import uuid

from .account_head import VoucherType

class VoucherStatus(str, Enum):
    DRAFT = "Draft"
    PENDING_REVIEW = "Pending Review"
    APPROVED = "Approved"
    EXPORTED = "Exported"
    REJECTED = "Rejected"

@dataclass
class Voucher:
    """
    Represents an accounting voucher entry.
    """
    # Use default_factory for mutable types or dynamic defaults
    voucher_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: datetime = field(default_factory=datetime.now)
    voucher_type: VoucherType = VoucherType.CREDIT
    account_code: str = ""
    account_name: str = ""
    amount: float = 0.0
    segment: str = ""
    narration: str = ""
    reference_id: Optional[str] = None
    status: VoucherStatus = VoucherStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "System"
    source: str = "Manual"
    tds_ledger: Optional[str] = None
    # === NEW FIELDS (Debit Support) ===
    party_name: Optional[str] = None
    invoice_no: Optional[str] = None
    invoice_date: Optional[dt_date] = None
    # ==================================

    # Period dates
    from_date: Optional[date_type] = None
    to_date: Optional[date_type] = None

    # === NEW FIELDS (Credit Sales Support) ===
    # Explicit sequential number (e.g., CR-SAL-202602-0001)
    voucher_no: Optional[str] = None 
    product_code: str = ""
    location: str = ""
    billing_type: str = ""
    revenue_details: str = ""
    # GST Breakdown (Credit Sales Only)
    cgst_amount: float = 0.0
    sgst_amount: float = 0.0
    igst_amount: float = 0.0

    # === UI & ACCOUNTING MAPPING STATES (CRITICAL FOR REVIEW TAB) ===
    party_ledger: str = ""
    expense_ledger: str = ""
    tally_head: str = ""
    base_amount: float = 0.0
    net_payable: float = 0.0
    
    def __post_init__(self):
        """Validate voucher data after initialization."""
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        
        # Convert datetime to date if needed for period dates
        if isinstance(self.from_date, datetime):
            self.from_date = self.from_date.date()
        if isinstance(self.to_date, datetime):
            self.to_date = self.to_date.date()
        # Same check for invoice_date
        if isinstance(self.invoice_date, datetime):
            self.invoice_date = self.invoice_date.date()
    
    @property
    def is_debit(self) -> bool:
        return self.voucher_type == VoucherType.DEBIT
    
    @property
    def is_credit(self) -> bool:
        return self.voucher_type == VoucherType.CREDIT
    
    @property
    def tally_voucher_type(self) -> str:
        return "Receipt" if self.is_credit else "Payment"
    
    def to_dict(self) -> dict:
        """Convert voucher to dictionary for serialization."""
        
        # Robustly handle status (Enum vs String)
        status_val = self.status
        if hasattr(self.status, 'value'):
            status_val = self.status.value
            
        return {
            'voucher_id': self.voucher_id,
            'date': self.date.isoformat() if isinstance(self.date, datetime) else self.date,
            'voucher_type': self.voucher_type.value if hasattr(self.voucher_type, 'value') else self.voucher_type,
            'account_code': getattr(self, 'account_code', ''),
            'account_name': getattr(self, 'account_name', ''),
            'amount': getattr(self, 'amount', 0.0),
            'segment': getattr(self, 'segment', ''),
            'narration': getattr(self, 'narration', ''),
            'reference_id': getattr(self, 'reference_id', None),
            'status': status_val,  
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'created_by': getattr(self, 'created_by', 'System'),
            'source': getattr(self, 'source', 'Manual'),
            'tds_ledger': getattr(self, 'tds_ledger', None),
            
            # Debit Support
            'party_name': getattr(self, 'party_name', None),
            'invoice_no': getattr(self, 'invoice_no', None),
            'invoice_date': self.invoice_date.isoformat() if getattr(self, 'invoice_date', None) else None,
            
            # Dates
            'from_date': self.from_date.isoformat() if getattr(self, 'from_date', None) else None,
            'to_date': self.to_date.isoformat() if getattr(self, 'to_date', None) else None,

            # Credit Sales Support
            'voucher_no': getattr(self, 'voucher_no', None),
            'product_code': getattr(self, 'product_code', ''),
            'location': getattr(self, 'location', ''),
            'billing_type': getattr(self, 'billing_type', ''),
            'revenue_details': self.revenue_details,
            # GST Breakdown
            'cgst_amount': getattr(self, 'cgst_amount', 0.0),
            'sgst_amount': getattr(self, 'sgst_amount', 0.0),
            'igst_amount': getattr(self, 'igst_amount', 0.0),

            # UI & Accounting Mapping States
            'party_ledger': getattr(self, 'party_ledger', ''),
            'expense_ledger': getattr(self, 'expense_ledger', ''),
            'tally_head': getattr(self, 'tally_head', ''),
            'base_amount': getattr(self, 'base_amount', 0.0),
            'net_payable': getattr(self, 'net_payable', 0.0)
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Voucher':
        """Create voucher from dictionary."""
        # Enum conversion
        voucher_type = data.get('voucher_type', 'Credit')
        if isinstance(voucher_type, str):
            try:
                voucher_type = VoucherType(voucher_type)
            except ValueError:
                voucher_type = VoucherType.CREDIT # Fallback
        
        status = data.get('status', 'Draft')
        if isinstance(status, str):
            try:
                status = VoucherStatus(status)
            except ValueError:
                found = False
                for s in VoucherStatus:
                    if s.value == status:
                        status = s
                        found = True
                        break
                if not found:
                    status = VoucherStatus.DRAFT

        # Date parsing helpers
        def parse_datetime(val):
            if isinstance(val, str): 
                try: return datetime.fromisoformat(val)
                except: return datetime.now()
            return val or datetime.now()

        def parse_date(val):
            if isinstance(val, str): 
                try: return dt_date.fromisoformat(val)
                except: return None
            return val

        return cls(
            voucher_id=data.get('voucher_id', str(uuid.uuid4())),
            date=parse_datetime(data.get('date')),
            voucher_type=voucher_type,
            account_code=data.get('account_code', ''),
            account_name=data.get('account_name', ''),
            amount=float(data.get('amount', 0.0)),
            segment=data.get('segment', ''),
            narration=data.get('narration', ''),
            reference_id=data.get('reference_id'),
            status=status,
            created_at=parse_datetime(data.get('created_at')),
            created_by=data.get('created_by', 'System'),
            source=data.get('source', 'Manual'),
            tds_ledger=data.get('tds_ledger'),
            
            # Debit Support
            party_name=data.get('party_name'),
            invoice_no=data.get('invoice_no'),
            invoice_date=parse_date(data.get('invoice_date')),
            
            # Dates
            from_date=parse_date(data.get('from_date')),
            to_date=parse_date(data.get('to_date')),

            # Credit Sales Support
            voucher_no=data.get('voucher_no'),
            product_code=data.get('product_code', ''),
            location=data.get('location', ''),
            billing_type=data.get('billing_type', ''),
            revenue_details=data.get('revenue_details', ''),
            # GST Breakdown
            cgst_amount=float(data.get('cgst_amount', 0.0)),
            sgst_amount=float(data.get('sgst_amount', 0.0)),
            igst_amount=float(data.get('igst_amount', 0.0)),

            # UI & Accounting Mapping States
            party_ledger=data.get('party_ledger', ''),
            expense_ledger=data.get('expense_ledger', ''),
            tally_head=data.get('tally_head', ''),
            base_amount=float(data.get('base_amount', 0.0)),
         
            net_payable=float(data.get('net_payable', 0.0))
        )