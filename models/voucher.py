"""Voucher Model - Represents accounting voucher entries."""

from dataclasses import dataclass, field
from datetime import datetime
from datetime import date as date_type  # Alias to avoid confusion with field name
from typing import Optional, Union
from enum import Enum
import uuid

from .account_head import VoucherType


class VoucherStatus(Enum):
    """Status of a voucher in the workflow."""
    DRAFT = "Draft"
    PENDING_REVIEW = "Pending Review"
    APPROVED = "Approved"
    EXPORTED = "Exported"
    REJECTED = "Rejected"


@dataclass
class Voucher:
    """
    Represents an accounting voucher entry.
    
    This is the core transaction record that will be:
    1. Validated for consistency
    2. Used for MIS reporting
    3. Exported to Tally XML
    
    Supports period dates for salaries, rent, subscriptions, etc.
    """
    
    voucher_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    date: datetime = field(default_factory=datetime.now)
    voucher_type: VoucherType = VoucherType.CREDIT
    account_code: str = ""
    account_name: str = ""  # Display name from account head
    amount: float = 0.0
    segment: str = ""
    narration: str = ""
    reference_id: str = field(default=None)  # e.g., Wix Order ID
    status: VoucherStatus = VoucherStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    created_by: str = "System"
    source: str = "Manual"  # "Manual" or "Wix Import" or "Bulk Import"
    
    # Period dates for salaries, rent, subscriptions, accumulated entries
    from_date: date_type = field(default=None)
    to_date: date_type = field(default=None)
    
    def __post_init__(self):
        """Validate voucher data after initialization."""
        if self.amount < 0:
            raise ValueError("Amount cannot be negative")
        
        # Convert datetime to date if needed for period dates
        if isinstance(self.from_date, datetime):
            self.from_date = self.from_date.date()
        if isinstance(self.to_date, datetime):
            self.to_date = self.to_date.date()
    
    @property
    def is_debit(self) -> bool:
        """Check if this is a debit voucher."""
        return self.voucher_type == VoucherType.DEBIT
    
    @property
    def is_credit(self) -> bool:
        """Check if this is a credit voucher."""
        return self.voucher_type == VoucherType.CREDIT
    
    @property
    def tally_voucher_type(self) -> str:
        """Get Tally voucher type for XML export."""
        return "Receipt" if self.is_credit else "Payment"
    
    @property
    def period_display(self) -> str:
        """Get formatted period display string."""
        if self.from_date and self.to_date:
            if self.from_date == self.to_date:
                return self.from_date.strftime("%d-%b-%Y")
            return f"{self.from_date.strftime('%d-%b')} to {self.to_date.strftime('%d-%b-%Y')}"
        return ""
    
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
            'from_date': self.from_date.isoformat() if self.from_date else None,
            'to_date': self.to_date.isoformat() if self.to_date else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Voucher':
        """Create voucher from dictionary."""
        voucher_type = data.get('voucher_type', 'Credit')
        if isinstance(voucher_type, str):
            voucher_type = VoucherType(voucher_type)
        
        status = data.get('status', 'Draft')
        if isinstance(status, str):
            status = VoucherStatus(status)
        
        voucher_date = data.get('date')
        if isinstance(voucher_date, str):
            voucher_date = datetime.fromisoformat(voucher_date)
        elif voucher_date is None:
            voucher_date = datetime.now()
        
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.now()
        
        from_date_val = data.get('from_date')
        if isinstance(from_date_val, str):
            from_date_val = date_type.fromisoformat(from_date_val)
        
        to_date_val = data.get('to_date')
        if isinstance(to_date_val, str):
            to_date_val = date_type.fromisoformat(to_date_val)
        
        return cls(
            voucher_id=data.get('voucher_id', str(uuid.uuid4())),
            date=voucher_date,
            voucher_type=voucher_type,
            account_code=data.get('account_code', ''),
            account_name=data.get('account_name', ''),
            amount=float(data.get('amount', 0.0)),
            segment=data.get('segment', ''),
            narration=data.get('narration', ''),
            reference_id=data.get('reference_id'),
            status=status,
            created_at=created_at,
            created_by=data.get('created_by', 'System'),
            source=data.get('source', 'Manual'),
            from_date=from_date_val,
            to_date=to_date_val
        )
