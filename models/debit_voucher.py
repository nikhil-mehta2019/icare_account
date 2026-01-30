"""Debit Voucher Models - Purchase, Payroll, Journal with GST/TDS/RCM support."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum
import uuid


class DebitVoucherType(Enum):
    """Types of Debit Vouchers."""
    PURCHASE = "Purchase"
    PAYROLL = "Payroll"
    JOURNAL = "Journal"


class GSTApplicability(Enum):
    """GST applicability types."""
    NORMAL = "Normal"
    RCM = "RCM"  # Reverse Charge Mechanism
    NOT_APPLICABLE = "Not Applicable"


class TransactionType(Enum):
    """Transaction type based on location."""
    INTER_STATE = "Inter-State"
    INTRA_STATE = "Intra-State"
    IMPORT = "Import"
    NOT_APPLICABLE = "Not Applicable"


class TDSSection(Enum):
    """TDS sections commonly used."""
    TDS_194C = "194C"  # Contractors
    TDS_194I = "194I"  # Rent
    TDS_194J = "194J"  # Professional/Technical
    TDS_194H = "194H"  # Commission
    TDS_195 = "195"    # Non-resident
    TDS_194A = "194A"  # Interest
    NONE = "None"


@dataclass
class GSTConfig:
    """GST configuration and calculation."""
    applicability: GSTApplicability = GSTApplicability.NOT_APPLICABLE
    transaction_type: TransactionType = TransactionType.NOT_APPLICABLE
    rate: float = 0.0  # GST rate percentage (e.g., 18.0 for 18%)
    
    # Input GST (Normal purchases)
    input_cgst_ledger: str = "Input CGST"
    input_sgst_ledger: str = "Input SGST"
    input_igst_ledger: str = "Input IGST"
    cgst_amount: float = 0.0
    sgst_amount: float = 0.0
    igst_amount: float = 0.0
    
    # RCM GST (Reverse Charge)
    rcm_output_cgst_ledger: str = "Output CGST (RCM)"
    rcm_output_sgst_ledger: str = "Output SGST (RCM)"
    rcm_output_igst_ledger: str = "Output IGST (RCM)"
    rcm_cgst_amount: float = 0.0
    rcm_sgst_amount: float = 0.0
    rcm_igst_amount: float = 0.0
    
    def calculate_gst(self, base_amount: float) -> None:
        """Calculate GST amounts based on configuration."""
        if self.applicability == GSTApplicability.NOT_APPLICABLE:
            self.cgst_amount = 0.0
            self.sgst_amount = 0.0
            self.igst_amount = 0.0
            self.rcm_cgst_amount = 0.0
            self.rcm_sgst_amount = 0.0
            self.rcm_igst_amount = 0.0
            return
        
        gst_amount = base_amount * (self.rate / 100)
        
        if self.applicability == GSTApplicability.NORMAL:
            if self.transaction_type == TransactionType.INTRA_STATE:
                # Split into CGST and SGST
                self.cgst_amount = round(gst_amount / 2, 2)
                self.sgst_amount = round(gst_amount / 2, 2)
                self.igst_amount = 0.0
            else:  # Inter-State or Import
                self.cgst_amount = 0.0
                self.sgst_amount = 0.0
                self.igst_amount = round(gst_amount, 2)
        
        elif self.applicability == GSTApplicability.RCM:
            if self.transaction_type == TransactionType.INTRA_STATE:
                self.rcm_cgst_amount = round(gst_amount / 2, 2)
                self.rcm_sgst_amount = round(gst_amount / 2, 2)
                self.rcm_igst_amount = 0.0
            else:  # Inter-State or Import
                self.rcm_cgst_amount = 0.0
                self.rcm_sgst_amount = 0.0
                self.rcm_igst_amount = round(gst_amount, 2)
    
    @property
    def total_input_gst(self) -> float:
        """Total input GST amount."""
        return self.cgst_amount + self.sgst_amount + self.igst_amount
    
    @property
    def total_rcm_gst(self) -> float:
        """Total RCM GST amount."""
        return self.rcm_cgst_amount + self.rcm_sgst_amount + self.rcm_igst_amount
    
    def to_dict(self) -> dict:
        return {
            'applicability': self.applicability.value,
            'transaction_type': self.transaction_type.value,
            'rate': self.rate,
            'input_cgst_ledger': self.input_cgst_ledger,
            'input_sgst_ledger': self.input_sgst_ledger,
            'input_igst_ledger': self.input_igst_ledger,
            'cgst_amount': self.cgst_amount,
            'sgst_amount': self.sgst_amount,
            'igst_amount': self.igst_amount,
            'rcm_output_cgst_ledger': self.rcm_output_cgst_ledger,
            'rcm_output_sgst_ledger': self.rcm_output_sgst_ledger,
            'rcm_output_igst_ledger': self.rcm_output_igst_ledger,
            'rcm_cgst_amount': self.rcm_cgst_amount,
            'rcm_sgst_amount': self.rcm_sgst_amount,
            'rcm_igst_amount': self.rcm_igst_amount
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GSTConfig':
        applicability = data.get('applicability', 'Not Applicable')
        if isinstance(applicability, str):
            applicability = GSTApplicability(applicability)
        
        transaction_type = data.get('transaction_type', 'Not Applicable')
        if isinstance(transaction_type, str):
            transaction_type = TransactionType(transaction_type)
        
        return cls(
            applicability=applicability,
            transaction_type=transaction_type,
            rate=data.get('rate', 0.0),
            input_cgst_ledger=data.get('input_cgst_ledger', 'Input CGST'),
            input_sgst_ledger=data.get('input_sgst_ledger', 'Input SGST'),
            input_igst_ledger=data.get('input_igst_ledger', 'Input IGST'),
            cgst_amount=data.get('cgst_amount', 0.0),
            sgst_amount=data.get('sgst_amount', 0.0),
            igst_amount=data.get('igst_amount', 0.0),
            rcm_output_cgst_ledger=data.get('rcm_output_cgst_ledger', 'Output CGST (RCM)'),
            rcm_output_sgst_ledger=data.get('rcm_output_sgst_ledger', 'Output SGST (RCM)'),
            rcm_output_igst_ledger=data.get('rcm_output_igst_ledger', 'Output IGST (RCM)'),
            rcm_cgst_amount=data.get('rcm_cgst_amount', 0.0),
            rcm_sgst_amount=data.get('rcm_sgst_amount', 0.0),
            rcm_igst_amount=data.get('rcm_igst_amount', 0.0)
        )


@dataclass
class TDSConfig:
    """TDS configuration and calculation."""
    applicable: bool = False
    section: TDSSection = TDSSection.NONE
    rate: float = 0.0  # TDS rate percentage
    ledger: str = ""
    amount: float = 0.0
    
    def calculate_tds(self, base_amount: float) -> None:
        """Calculate TDS amount."""
        if not self.applicable or self.section == TDSSection.NONE:
            self.amount = 0.0
            return
        self.amount = round(base_amount * (self.rate / 100), 2)
    
    @staticmethod
    def get_default_rate(section: TDSSection) -> float:
        """Get default TDS rate for section."""
        rates = {
            TDSSection.TDS_194C: 2.0,   # Contractors - 2%
            TDSSection.TDS_194I: 10.0,  # Rent - 10%
            TDSSection.TDS_194J: 10.0,  # Professional - 10%
            TDSSection.TDS_194H: 5.0,   # Commission - 5%
            TDSSection.TDS_195: 10.0,   # Non-resident - varies
            TDSSection.TDS_194A: 10.0,  # Interest - 10%
            TDSSection.NONE: 0.0
        }
        return rates.get(section, 0.0)
    
    @staticmethod
    def get_ledger_name(section: TDSSection) -> str:
        """Get default TDS ledger name for section."""
        ledgers = {
            TDSSection.TDS_194C: "TDS Payable - 194C",
            TDSSection.TDS_194I: "TDS Payable - 194I",
            TDSSection.TDS_194J: "TDS Payable - 194J",
            TDSSection.TDS_194H: "TDS Payable - 194H",
            TDSSection.TDS_195: "TDS Payable - 195",
            TDSSection.TDS_194A: "TDS Payable - 194A",
            TDSSection.NONE: ""
        }
        return ledgers.get(section, "")
    
    def to_dict(self) -> dict:
        return {
            'applicable': self.applicable,
            'section': self.section.value,
            'rate': self.rate,
            'ledger': self.ledger,
            'amount': self.amount
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TDSConfig':
        section = data.get('section', 'None')
        if isinstance(section, str):
            section = TDSSection(section)
        
        return cls(
            applicable=data.get('applicable', False),
            section=section,
            rate=data.get('rate', 0.0),
            ledger=data.get('ledger', ''),
            amount=data.get('amount', 0.0)
        )


@dataclass
class PurchaseVoucher:
    """
    Purchase Voucher with full GST, TDS, and RCM support.
    
    Scenarios supported:
    - Normal GST purchase (Inter-State: IGST, Intra-State: CGST+SGST)
    - GST + TDS
    - RCM (Reverse Charge Mechanism)
    - GST + TDS + RCM
    - Asset purchase
    - Expense purchase
    - Non-GST purchase
    """
    
    voucher_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    voucher_type: DebitVoucherType = DebitVoucherType.PURCHASE
    voucher_no: str = ""
    voucher_date: datetime = field(default_factory=datetime.now)
    
    # Party/Supplier
    supplier_ledger: str = ""
    supplier_gstin: str = ""
    
    # Invoice details
    invoice_no: str = ""
    invoice_date: datetime = field(default_factory=datetime.now)
    
    # Expense/Asset
    expense_ledger: str = ""  # Main Code - Tally Ledger
    expense_subcode: str = ""  # Subcode - MIS identity
    cost_centre: str = ""
    
    # Amounts
    base_amount: float = 0.0
    
    # GST Configuration
    gst: GSTConfig = field(default_factory=GSTConfig)
    
    # TDS Configuration
    tds: TDSConfig = field(default_factory=TDSConfig)
    
    # Narration
    narration: str = ""
    
    # Tracking
    from_location: str = ""
    to_location: str = ""
    business_unit: str = ""
    
    # Status
    status: str = "Pending"
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def total_gst_amount(self) -> float:
        """Total GST (Input or RCM)."""
        return self.gst.total_input_gst + self.gst.total_rcm_gst
    
    @property
    def net_payable(self) -> float:
        """Net amount payable to supplier (Base + GST - TDS)."""
        total = self.base_amount + self.gst.total_input_gst
        if self.gst.applicability == GSTApplicability.RCM:
            # In RCM, GST is paid separately, not to supplier
            total = self.base_amount
        total -= self.tds.amount
        return round(total, 2)
    
    @property
    def tally_ledger_name(self) -> str:
        """Get ledger name for Tally with subcode."""
        if self.expense_subcode:
            return f"{self.expense_ledger} - {self.expense_subcode}"
        return self.expense_ledger
    
    def calculate_all(self) -> None:
        """Calculate all GST and TDS amounts."""
        self.gst.calculate_gst(self.base_amount)
        self.tds.calculate_tds(self.base_amount)
    
    def to_dict(self) -> dict:
        return {
            'voucher_id': self.voucher_id,
            'voucher_type': self.voucher_type.value,
            'voucher_no': self.voucher_no,
            'voucher_date': self.voucher_date.isoformat(),
            'supplier_ledger': self.supplier_ledger,
            'supplier_gstin': self.supplier_gstin,
            'invoice_no': self.invoice_no,
            'invoice_date': self.invoice_date.isoformat(),
            'expense_ledger': self.expense_ledger,
            'expense_subcode': self.expense_subcode,
            'cost_centre': self.cost_centre,
            'base_amount': self.base_amount,
            'gst': self.gst.to_dict(),
            'tds': self.tds.to_dict(),
            'narration': self.narration,
            'from_location': self.from_location,
            'to_location': self.to_location,
            'business_unit': self.business_unit,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PurchaseVoucher':
        voucher_date = data.get('voucher_date')
        if isinstance(voucher_date, str):
            voucher_date = datetime.fromisoformat(voucher_date)
        
        invoice_date = data.get('invoice_date')
        if isinstance(invoice_date, str):
            invoice_date = datetime.fromisoformat(invoice_date)
        
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        return cls(
            voucher_id=data.get('voucher_id', str(uuid.uuid4())),
            voucher_type=DebitVoucherType.PURCHASE,
            voucher_no=data.get('voucher_no', ''),
            voucher_date=voucher_date or datetime.now(),
            supplier_ledger=data.get('supplier_ledger', ''),
            supplier_gstin=data.get('supplier_gstin', ''),
            invoice_no=data.get('invoice_no', ''),
            invoice_date=invoice_date or datetime.now(),
            expense_ledger=data.get('expense_ledger', ''),
            expense_subcode=data.get('expense_subcode', ''),
            cost_centre=data.get('cost_centre', ''),
            base_amount=float(data.get('base_amount', 0.0)),
            gst=GSTConfig.from_dict(data.get('gst', {})),
            tds=TDSConfig.from_dict(data.get('tds', {})),
            narration=data.get('narration', ''),
            from_location=data.get('from_location', ''),
            to_location=data.get('to_location', ''),
            business_unit=data.get('business_unit', ''),
            status=data.get('status', 'Pending'),
            created_at=created_at or datetime.now()
        )


@dataclass
class PayrollVoucher:
    """
    Payroll Voucher - Simple Debit for salary payments.
    
    Used for:
    - Staff Salary
    - Management Salary
    - Contractor Payments
    
    No GST, No RCM. Optional TDS (future-ready).
    """
    
    voucher_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    voucher_type: DebitVoucherType = DebitVoucherType.PAYROLL
    voucher_no: str = ""
    voucher_date: datetime = field(default_factory=datetime.now)
    
    # Party/Employee
    party_ledger: str = ""  # Employee or Contractor name
    employee_id: str = ""
    
    # Salary details
    salary_ledger: str = ""  # Main Code - Tally Ledger (e.g., "Salary of Employees")
    salary_subcode: str = ""  # Subcode - MIS identity (e.g., "Staff", "Management")
    
    # Amount
    amount: float = 0.0
    
    # Period
    month_period: str = ""  # e.g., "Jan 2025", "2025-01"
    
    # TDS (Optional - future ready)
    tds: TDSConfig = field(default_factory=TDSConfig)
    
    # Narration
    narration: str = ""
    
    # Status
    status: str = "Pending"
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def net_payable(self) -> float:
        """Net amount payable (Amount - TDS)."""
        return round(self.amount - self.tds.amount, 2)
    
    @property
    def tally_ledger_name(self) -> str:
        """Get ledger name for Tally with subcode."""
        if self.salary_subcode:
            return f"{self.salary_ledger} - {self.salary_subcode}"
        return self.salary_ledger
    
    def to_dict(self) -> dict:
        return {
            'voucher_id': self.voucher_id,
            'voucher_type': self.voucher_type.value,
            'voucher_no': self.voucher_no,
            'voucher_date': self.voucher_date.isoformat(),
            'party_ledger': self.party_ledger,
            'employee_id': self.employee_id,
            'salary_ledger': self.salary_ledger,
            'salary_subcode': self.salary_subcode,
            'amount': self.amount,
            'month_period': self.month_period,
            'tds': self.tds.to_dict(),
            'narration': self.narration,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PayrollVoucher':
        voucher_date = data.get('voucher_date')
        if isinstance(voucher_date, str):
            voucher_date = datetime.fromisoformat(voucher_date)
        
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        return cls(
            voucher_id=data.get('voucher_id', str(uuid.uuid4())),
            voucher_type=DebitVoucherType.PAYROLL,
            voucher_no=data.get('voucher_no', ''),
            voucher_date=voucher_date or datetime.now(),
            party_ledger=data.get('party_ledger', ''),
            employee_id=data.get('employee_id', ''),
            salary_ledger=data.get('salary_ledger', ''),
            salary_subcode=data.get('salary_subcode', ''),
            amount=float(data.get('amount', 0.0)),
            month_period=data.get('month_period', ''),
            tds=TDSConfig.from_dict(data.get('tds', {})),
            narration=data.get('narration', ''),
            status=data.get('status', 'Pending'),
            created_at=created_at or datetime.now()
        )


@dataclass
class JournalEntry:
    """Single journal entry line (Debit or Credit)."""
    ledger: str = ""
    ledger_subcode: str = ""
    is_debit: bool = True
    amount: float = 0.0
    
    @property
    def tally_ledger_name(self) -> str:
        if self.ledger_subcode:
            return f"{self.ledger} - {self.ledger_subcode}"
        return self.ledger
    
    def to_dict(self) -> dict:
        return {
            'ledger': self.ledger,
            'ledger_subcode': self.ledger_subcode,
            'is_debit': self.is_debit,
            'amount': self.amount
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'JournalEntry':
        return cls(
            ledger=data.get('ledger', ''),
            ledger_subcode=data.get('ledger_subcode', ''),
            is_debit=data.get('is_debit', True),
            amount=float(data.get('amount', 0.0))
        )


@dataclass
class JournalVoucher:
    """
    Journal Voucher - For adjustments, provisions, and internal transfers.
    
    Debit and Credit entries allowed inside the same voucher.
    No GST, No TDS, No RCM.
    """
    
    voucher_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    voucher_type: DebitVoucherType = DebitVoucherType.JOURNAL
    voucher_no: str = ""
    voucher_date: datetime = field(default_factory=datetime.now)
    
    # Journal entries (multiple debits and credits)
    entries: List[JournalEntry] = field(default_factory=list)
    
    # Narration
    narration: str = ""
    
    # Status
    status: str = "Pending"
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def total_debit(self) -> float:
        """Total of all debit entries."""
        return sum(e.amount for e in self.entries if e.is_debit)
    
    @property
    def total_credit(self) -> float:
        """Total of all credit entries."""
        return sum(e.amount for e in self.entries if not e.is_debit)
    
    @property
    def is_balanced(self) -> bool:
        """Check if journal is balanced (Debit = Credit)."""
        return abs(self.total_debit - self.total_credit) < 0.01
    
    def add_debit(self, ledger: str, amount: float, subcode: str = "") -> None:
        """Add a debit entry."""
        self.entries.append(JournalEntry(
            ledger=ledger,
            ledger_subcode=subcode,
            is_debit=True,
            amount=amount
        ))
    
    def add_credit(self, ledger: str, amount: float, subcode: str = "") -> None:
        """Add a credit entry."""
        self.entries.append(JournalEntry(
            ledger=ledger,
            ledger_subcode=subcode,
            is_debit=False,
            amount=amount
        ))
    
    def to_dict(self) -> dict:
        return {
            'voucher_id': self.voucher_id,
            'voucher_type': self.voucher_type.value,
            'voucher_no': self.voucher_no,
            'voucher_date': self.voucher_date.isoformat(),
            'entries': [e.to_dict() for e in self.entries],
            'narration': self.narration,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'JournalVoucher':
        voucher_date = data.get('voucher_date')
        if isinstance(voucher_date, str):
            voucher_date = datetime.fromisoformat(voucher_date)
        
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        entries = [JournalEntry.from_dict(e) for e in data.get('entries', [])]
        
        return cls(
            voucher_id=data.get('voucher_id', str(uuid.uuid4())),
            voucher_type=DebitVoucherType.JOURNAL,
            voucher_no=data.get('voucher_no', ''),
            voucher_date=voucher_date or datetime.now(),
            entries=entries,
            narration=data.get('narration', ''),
            status=data.get('status', 'Pending'),
            created_at=created_at or datetime.now()
        )
