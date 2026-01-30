"""AccountHead Model - Represents chart of accounts entries."""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class VoucherType(Enum):
    """Voucher type - Debit or Credit."""
    DEBIT = "Debit"
    CREDIT = "Credit"


@dataclass
class AccountHead:
    """
    Represents an account head in the Chart of Accounts.
    
    Uses 4-digit coding system:
    - 1000-1999: Operating Sales (Credit)
    - 2000-2999: Other Income (Credit)
    - 3000-3999: Loans/Liabilities (Credit)
    - 4000-4999: Asset Sales (Credit)
    - 5000-5999: Direct Costs (Debit)
    - 6000-6999: Fixed Overheads (Debit)
    - 7000-7999: Marketing/Sales (Debit)
    - 8000-8999: Finance/Assets (Debit)
    """
    
    code: str  # 4-digit code (e.g., "1101")
    voucher_type: VoucherType  # Debit or Credit
    main_head: str  # e.g., "Sales Income"
    sub_head: str  # e.g., "Retail (Wix)"
    sub_sub_head: Optional[str] = None  # e.g., "Online Cert - Basic"
    segment_tag: str = ""  # Default segment (Retail, Kenya, India, POOL)
    usual_narration: str = ""  # Default narration template
    is_active: bool = True
    requires_segment_selection: bool = False  # If user must pick segment
    
    def __post_init__(self):
        """Validate account head data after initialization."""
        if not self.code or len(self.code) != 4:
            raise ValueError(f"Account code must be 4 digits: {self.code}")
        if not self.code.isdigit():
            raise ValueError(f"Account code must be numeric: {self.code}")
        if not self.main_head:
            raise ValueError("Main head cannot be empty")
    
    @property
    def display_name(self) -> str:
        """Get display name for dropdown."""
        parts = [self.code, self.main_head, self.sub_head]
        if self.sub_sub_head:
            parts.append(self.sub_sub_head)
        return " - ".join(parts)
    
    @property
    def ledger_name(self) -> str:
        """Get ledger name for Tally export (uses sub-sub-head)."""
        return self.sub_sub_head or self.sub_head
    
    @property
    def code_range(self) -> str:
        """Get the code range category."""
        code_int = int(self.code)
        if 1000 <= code_int < 2000:
            return "Operating Sales"
        elif 2000 <= code_int < 3000:
            return "Other Income"
        elif 3000 <= code_int < 4000:
            return "Loans/Liabilities"
        elif 4000 <= code_int < 5000:
            return "Asset Sales"
        elif 5000 <= code_int < 6000:
            return "Direct Costs"
        elif 6000 <= code_int < 7000:
            return "Fixed Overheads"
        elif 7000 <= code_int < 8000:
            return "Marketing/Sales"
        elif 8000 <= code_int < 9000:
            return "Finance/Assets"
        return "Unknown"
    
    def to_dict(self) -> dict:
        """Convert account head to dictionary for serialization."""
        return {
            'code': self.code,
            'voucher_type': self.voucher_type.value,
            'main_head': self.main_head,
            'sub_head': self.sub_head,
            'sub_sub_head': self.sub_sub_head,
            'segment_tag': self.segment_tag,
            'usual_narration': self.usual_narration,
            'is_active': self.is_active,
            'requires_segment_selection': self.requires_segment_selection
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AccountHead':
        """Create account head from dictionary."""
        voucher_type = data.get('voucher_type', 'Credit')
        if isinstance(voucher_type, str):
            voucher_type = VoucherType(voucher_type)
        
        return cls(
            code=data.get('code', ''),
            voucher_type=voucher_type,
            main_head=data.get('main_head', ''),
            sub_head=data.get('sub_head', ''),
            sub_sub_head=data.get('sub_sub_head'),
            segment_tag=data.get('segment_tag', ''),
            usual_narration=data.get('usual_narration', ''),
            is_active=data.get('is_active', True),
            requires_segment_selection=data.get('requires_segment_selection', False)
        )
