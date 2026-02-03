from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Union, Dict, Any
from enum import Enum

# Enums
class DebitVoucherType(str, Enum):
    PURCHASE = "Purchase"
    PAYROLL = "Payroll"
    JOURNAL = "Journal"

class GSTApplicability(str, Enum):
    APPLICABLE = "Applicable"
    NOT_APPLICABLE = "Not Applicable"
    RCM = "RCM"
    NORMAL = "Normal"

class TransactionType(str, Enum):
    INTER_STATE = "Inter-State"
    INTRA_STATE = "Intra-State"
    IMPORT = "Import"
    NOT_APPLICABLE = "Not Applicable"

class TDSSection(str, Enum):
    NONE = "None"
    TDS_194C = "194C - Payments to Contractors"
    TDS_194J = "194J - Fees for Professional Services"
    TDS_194I = "194I - Rent"
    TDS_194H = "194H - Commission or Brokerage"
    TDS_195 = "195 - Other Sums (Non-Resident)"
    TDS_194A = "194A - Interest other than 'Interest on securities'"

# Config Objects
@dataclass
class GSTConfig:
    applicability: GSTApplicability = GSTApplicability.NOT_APPLICABLE
    transaction_type: TransactionType = TransactionType.NOT_APPLICABLE
    input_cgst_ledger: str = "Input CGST"
    input_sgst_ledger: str = "Input SGST"
    input_igst_ledger: str = "Input IGST"
    cgst_amount: float = 0.0
    sgst_amount: float = 0.0
    igst_amount: float = 0.0
    # RCM fields
    rcm_output_cgst_ledger: str = "Output CGST (RCM)"
    rcm_output_sgst_ledger: str = "Output SGST (RCM)"
    rcm_output_igst_ledger: str = "Output IGST (RCM)"
    rcm_cgst_amount: float = 0.0
    rcm_sgst_amount: float = 0.0
    rcm_igst_amount: float = 0.0

    def to_dict(self):
        return {
            "applicability": self.applicability.value if hasattr(self.applicability, 'value') else self.applicability,
            "transaction_type": self.transaction_type.value if hasattr(self.transaction_type, 'value') else self.transaction_type,
            "input_cgst_ledger": self.input_cgst_ledger,
            "input_sgst_ledger": self.input_sgst_ledger,
            "input_igst_ledger": self.input_igst_ledger,
            "cgst_amount": self.cgst_amount,
            "sgst_amount": self.sgst_amount,
            "igst_amount": self.igst_amount,
            "rcm_output_cgst_ledger": self.rcm_output_cgst_ledger,
            "rcm_output_sgst_ledger": self.rcm_output_sgst_ledger,
            "rcm_output_igst_ledger": self.rcm_output_igst_ledger,
            "rcm_cgst_amount": self.rcm_cgst_amount,
            "rcm_sgst_amount": self.rcm_sgst_amount,
            "rcm_igst_amount": self.rcm_igst_amount
        }

@dataclass
class TDSConfig:
    applicable: bool = False
    section: TDSSection = TDSSection.NONE
    ledger: str = ""
    amount: float = 0.0

    def to_dict(self):
        return {
            "applicable": self.applicable,
            "section": self.section.value if hasattr(self.section, 'value') else self.section,
            "ledger": self.ledger,
            "amount": self.amount
        }

# Journal Entry Item
@dataclass
class JournalEntry:
    ledger: str
    debit_amount: float = 0.0
    credit_amount: float = 0.0
    subcode: str = ""
    
    def to_dict(self):
        return {
            "ledger": self.ledger,
            "debit_amount": self.debit_amount,
            "credit_amount": self.credit_amount,
            "subcode": self.subcode
        }

# Vouchers
@dataclass
class BaseVoucher:
    voucher_no: str
    voucher_date: datetime
    narration: str = ""
    status: str = "Draft"
    voucher_type: DebitVoucherType = DebitVoucherType.JOURNAL
    voucher_id: str = "" # Unique ID for updates

    def __post_init__(self):
        # Auto-convert string dates back to datetime if needed
        if isinstance(self.voucher_date, str):
            try:
                self.voucher_date = datetime.strptime(self.voucher_date, "%Y-%m-%d")
            except ValueError:
                pass

    def to_dict(self):
        return {
            "voucher_id": self.voucher_id or self.voucher_no,
            "voucher_no": self.voucher_no,
            "voucher_date": self.voucher_date.strftime("%Y-%m-%d") if isinstance(self.voucher_date, datetime) else self.voucher_date,
            "narration": self.narration,
            "status": self.status,
            "voucher_type": self.voucher_type.value if hasattr(self.voucher_type, 'value') else self.voucher_type
        }

@dataclass
class PurchaseVoucher(BaseVoucher):
    supplier_ledger: str = ""
    invoice_no: str = ""
    invoice_date: datetime = field(default_factory=datetime.now)
    expense_ledger: str = ""
    expense_subcode: str = ""
    cost_centre: str = ""
    base_amount: float = 0.0
    gst: GSTConfig = field(default_factory=GSTConfig)
    tds: TDSConfig = field(default_factory=TDSConfig)
    from_location: str = ""
    to_location: str = ""
    business_unit: str = ""

    def __post_init__(self):
        super().__post_init__()
        self.voucher_type = DebitVoucherType.PURCHASE
        # Auto-convert dicts to objects (Deserialization fix)
        if isinstance(self.gst, dict): self.gst = GSTConfig(**self.gst)
        if isinstance(self.tds, dict): self.tds = TDSConfig(**self.tds)
        if isinstance(self.invoice_date, str):
            try:
                self.invoice_date = datetime.strptime(self.invoice_date, "%Y-%m-%d")
            except: pass

    @property
    def total_amount(self) -> float:
        total = self.base_amount + self.gst.cgst_amount + self.gst.sgst_amount + self.gst.igst_amount
        if self.tds.applicable:
            total -= self.tds.amount
        return total
    
    def to_dict(self):
        data = super().to_dict()
        data.update({
            "supplier_ledger": self.supplier_ledger,
            "invoice_no": self.invoice_no,
            "invoice_date": self.invoice_date.strftime("%Y-%m-%d") if isinstance(self.invoice_date, datetime) else self.invoice_date,
            "expense_ledger": self.expense_ledger,
            "expense_subcode": self.expense_subcode,
            "cost_centre": self.cost_centre,
            "base_amount": self.base_amount,
            "gst": self.gst.to_dict(),
            "tds": self.tds.to_dict(),
            "from_location": self.from_location,
            "to_location": self.to_location,
            "business_unit": self.business_unit,
            "amount": self.total_amount # Saved for list view
        })
        return data

@dataclass
class PayrollVoucher(BaseVoucher):
    party_ledger: str = ""
    employee_id: str = ""
    salary_ledger: str = ""
    salary_subcode: str = ""
    amount: float = 0.0
    month_period: str = ""
    tds: TDSConfig = field(default_factory=TDSConfig)

    def __post_init__(self):
        super().__post_init__()
        self.voucher_type = DebitVoucherType.PAYROLL
        if isinstance(self.tds, dict): self.tds = TDSConfig(**self.tds)

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "party_ledger": self.party_ledger,
            "employee_id": self.employee_id,
            "salary_ledger": self.salary_ledger,
            "salary_subcode": self.salary_subcode,
            "amount": self.amount,
            "month_period": self.month_period,
            "tds": self.tds.to_dict()
        })
        return data

@dataclass
class JournalVoucher(BaseVoucher):
    entries: List[JournalEntry] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        self.voucher_type = DebitVoucherType.JOURNAL
        # CRITICAL FIX: Convert list of dicts back to JournalEntry objects
        if self.entries and isinstance(self.entries, list) and len(self.entries) > 0:
            if isinstance(self.entries[0], dict):
                self.entries = [JournalEntry(**e) for e in self.entries]

    def add_debit(self, ledger: str, amount: float, subcode: str = ""):
        self.entries.append(JournalEntry(ledger, debit_amount=amount, subcode=subcode))

    def add_credit(self, ledger: str, amount: float, subcode: str = ""):
        self.entries.append(JournalEntry(ledger, credit_amount=amount, subcode=subcode))

    @property
    def total_debit(self) -> float:
        return sum(e.debit_amount for e in self.entries)

    @property
    def total_credit(self) -> float:
        return sum(e.credit_amount for e in self.entries)
    
    @property
    def is_balanced(self) -> bool:
        return abs(self.total_debit - self.total_credit) < 0.01

    def to_dict(self):
        data = super().to_dict()
        data.update({
            # Save entries as list of dicts
            "entries": [e.to_dict() for e in self.entries],
            "amount": self.total_debit, # Save total for list view
            "party_ledger": "Multiple (Journal)" 
        })
        return data