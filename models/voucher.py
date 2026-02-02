from dataclasses import dataclass, field
from datetime import datetime
from datetime import date as date_type, date as dt_date  # Aliases to avoid conflict
from typing import Optional
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
    
    # === NEW FIELDS (Debit Support) ===
    party_name: Optional[str] = None
    invoice_no: Optional[str] = None
    invoice_date: Optional[dt_date] = None  # Using alias 'dt_date'
    # ==================================

    # Period dates
    from_date: Optional[date_type] = None
    to_date: Optional[date_type] = None
    
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
        return {
            'voucher_id': self.voucher_id,
            'date': self.date.isoformat() if isinstance(self.date, datetime) else self.date,
            'voucher_type': self.voucher_type.value,
            'account_code': self.account_code,
            'account_name': self.account_name,
            'amount': self.amount,
            'segment': self.segment,
            'narration': self.narration,
            'reference_id': self.reference_id,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            'created_by': self.created_by,
            'source': self.source,
            
            # === NEW FIELDS ===
            'party_name': self.party_name,
            'invoice_no': self.invoice_no,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            # ==================
            
            'from_date': self.from_date.isoformat() if self.from_date else None,
            'to_date': self.to_date.isoformat() if self.to_date else None
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
                status = VoucherStatus.DRAFT

        # Date parsing helpers
        def parse_datetime(val):
            if isinstance(val, str): return datetime.fromisoformat(val)
            return val or datetime.now()

        def parse_date(val):
            if isinstance(val, str): return dt_date.fromisoformat(val)
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
            
            # === NEW FIELDS ===
            party_name=data.get('party_name'),
            invoice_no=data.get('invoice_no'),
            invoice_date=parse_date(data.get('invoice_date')),
            # ==================
            
            from_date=parse_date(data.get('from_date')),
            to_date=parse_date(data.get('to_date'))
        )