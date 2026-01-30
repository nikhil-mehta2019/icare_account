"""Ledger Configuration Models for Admin Settings."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
import json


@dataclass
class SupplierLedger:
    """Supplier/Party ledger configuration."""
    code: str
    name: str
    gstin: str = ""
    state: str = ""
    is_rcm_applicable: bool = False
    default_tds_section: str = "None"
    is_active: bool = True
    
    def to_dict(self) -> dict:
        return {
            'code': self.code,
            'name': self.name,
            'gstin': self.gstin,
            'state': self.state,
            'is_rcm_applicable': self.is_rcm_applicable,
            'default_tds_section': self.default_tds_section,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SupplierLedger':
        return cls(
            code=data.get('code', ''),
            name=data.get('name', ''),
            gstin=data.get('gstin', ''),
            state=data.get('state', ''),
            is_rcm_applicable=data.get('is_rcm_applicable', False),
            default_tds_section=data.get('default_tds_section', 'None'),
            is_active=data.get('is_active', True)
        )


@dataclass
class ExpenseLedger:
    """Expense/Asset ledger configuration with subcodes."""
    main_code: str  # Tally Ledger code
    main_name: str  # Tally Ledger name
    subcode: str = ""  # MIS subcode
    subcode_name: str = ""  # MIS subcode name
    default_gst_rate: float = 18.0
    default_cost_centre: str = ""
    is_asset: bool = False
    is_active: bool = True
    
    @property
    def display_name(self) -> str:
        if self.subcode_name:
            return f"{self.main_name} - {self.subcode_name}"
        return self.main_name
    
    @property
    def tally_ledger(self) -> str:
        if self.subcode:
            return f"{self.main_name} - {self.subcode_name}"
        return self.main_name
    
    def to_dict(self) -> dict:
        return {
            'main_code': self.main_code,
            'main_name': self.main_name,
            'subcode': self.subcode,
            'subcode_name': self.subcode_name,
            'default_gst_rate': self.default_gst_rate,
            'default_cost_centre': self.default_cost_centre,
            'is_asset': self.is_asset,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ExpenseLedger':
        return cls(
            main_code=data.get('main_code', ''),
            main_name=data.get('main_name', ''),
            subcode=data.get('subcode', ''),
            subcode_name=data.get('subcode_name', ''),
            default_gst_rate=data.get('default_gst_rate', 18.0),
            default_cost_centre=data.get('default_cost_centre', ''),
            is_asset=data.get('is_asset', False),
            is_active=data.get('is_active', True)
        )


@dataclass
class GSTLedgerMapping:
    """GST ledger mapping configuration."""
    # Input GST ledgers (for normal purchases)
    input_cgst: str = "Input CGST"
    input_sgst: str = "Input SGST"
    input_igst: str = "Input IGST"
    
    # Output GST ledgers (for RCM)
    output_cgst_rcm: str = "Output CGST (RCM)"
    output_sgst_rcm: str = "Output SGST (RCM)"
    output_igst_rcm: str = "Output IGST (RCM)"
    
    # Standard GST rates
    gst_rates: List[float] = field(default_factory=lambda: [0.0, 5.0, 12.0, 18.0, 28.0])
    
    def to_dict(self) -> dict:
        return {
            'input_cgst': self.input_cgst,
            'input_sgst': self.input_sgst,
            'input_igst': self.input_igst,
            'output_cgst_rcm': self.output_cgst_rcm,
            'output_sgst_rcm': self.output_sgst_rcm,
            'output_igst_rcm': self.output_igst_rcm,
            'gst_rates': self.gst_rates
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'GSTLedgerMapping':
        return cls(
            input_cgst=data.get('input_cgst', 'Input CGST'),
            input_sgst=data.get('input_sgst', 'Input SGST'),
            input_igst=data.get('input_igst', 'Input IGST'),
            output_cgst_rcm=data.get('output_cgst_rcm', 'Output CGST (RCM)'),
            output_sgst_rcm=data.get('output_sgst_rcm', 'Output SGST (RCM)'),
            output_igst_rcm=data.get('output_igst_rcm', 'Output IGST (RCM)'),
            gst_rates=data.get('gst_rates', [0.0, 5.0, 12.0, 18.0, 28.0])
        )


@dataclass
class TDSLedgerMapping:
    """TDS ledger mapping configuration."""
    tds_194c: str = "TDS Payable - 194C"
    tds_194c_rate: float = 2.0
    
    tds_194i: str = "TDS Payable - 194I"
    tds_194i_rate: float = 10.0
    
    tds_194j: str = "TDS Payable - 194J"
    tds_194j_rate: float = 10.0
    
    tds_194h: str = "TDS Payable - 194H"
    tds_194h_rate: float = 5.0
    
    tds_195: str = "TDS Payable - 195"
    tds_195_rate: float = 10.0
    
    tds_194a: str = "TDS Payable - 194A"
    tds_194a_rate: float = 10.0
    
    def get_ledger(self, section: str) -> str:
        mapping = {
            '194C': self.tds_194c,
            '194I': self.tds_194i,
            '194J': self.tds_194j,
            '194H': self.tds_194h,
            '195': self.tds_195,
            '194A': self.tds_194a
        }
        return mapping.get(section, '')
    
    def get_rate(self, section: str) -> float:
        mapping = {
            '194C': self.tds_194c_rate,
            '194I': self.tds_194i_rate,
            '194J': self.tds_194j_rate,
            '194H': self.tds_194h_rate,
            '195': self.tds_195_rate,
            '194A': self.tds_194a_rate
        }
        return mapping.get(section, 0.0)
    
    def to_dict(self) -> dict:
        return {
            'tds_194c': self.tds_194c,
            'tds_194c_rate': self.tds_194c_rate,
            'tds_194i': self.tds_194i,
            'tds_194i_rate': self.tds_194i_rate,
            'tds_194j': self.tds_194j,
            'tds_194j_rate': self.tds_194j_rate,
            'tds_194h': self.tds_194h,
            'tds_194h_rate': self.tds_194h_rate,
            'tds_195': self.tds_195,
            'tds_195_rate': self.tds_195_rate,
            'tds_194a': self.tds_194a,
            'tds_194a_rate': self.tds_194a_rate
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TDSLedgerMapping':
        return cls(
            tds_194c=data.get('tds_194c', 'TDS Payable - 194C'),
            tds_194c_rate=data.get('tds_194c_rate', 2.0),
            tds_194i=data.get('tds_194i', 'TDS Payable - 194I'),
            tds_194i_rate=data.get('tds_194i_rate', 10.0),
            tds_194j=data.get('tds_194j', 'TDS Payable - 194J'),
            tds_194j_rate=data.get('tds_194j_rate', 10.0),
            tds_194h=data.get('tds_194h', 'TDS Payable - 194H'),
            tds_194h_rate=data.get('tds_194h_rate', 5.0),
            tds_195=data.get('tds_195', 'TDS Payable - 195'),
            tds_195_rate=data.get('tds_195_rate', 10.0),
            tds_194a=data.get('tds_194a', 'TDS Payable - 194A'),
            tds_194a_rate=data.get('tds_194a_rate', 10.0)
        )


@dataclass 
class CostCentre:
    """Cost centre configuration."""
    code: str
    name: str
    is_active: bool = True
    
    def to_dict(self) -> dict:
        return {
            'code': self.code,
            'name': self.name,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'CostCentre':
        return cls(
            code=data.get('code', ''),
            name=data.get('name', ''),
            is_active=data.get('is_active', True)
        )


@dataclass
class SalaryLedger:
    """Salary ledger configuration for payroll."""
    main_code: str
    main_name: str
    subcode: str = ""
    subcode_name: str = ""  # e.g., "Staff", "Management"
    is_active: bool = True
    
    @property
    def display_name(self) -> str:
        if self.subcode_name:
            return f"{self.main_name} - {self.subcode_name}"
        return self.main_name
    
    def to_dict(self) -> dict:
        return {
            'main_code': self.main_code,
            'main_name': self.main_name,
            'subcode': self.subcode,
            'subcode_name': self.subcode_name,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SalaryLedger':
        return cls(
            main_code=data.get('main_code', ''),
            main_name=data.get('main_name', ''),
            subcode=data.get('subcode', ''),
            subcode_name=data.get('subcode_name', ''),
            is_active=data.get('is_active', True)
        )


@dataclass
class DebitVoucherConfig:
    """
    Complete configuration for Debit Voucher system.
    Admin-only configurable.
    """
    
    # Supplier/Party ledgers
    suppliers: List[SupplierLedger] = field(default_factory=list)
    
    # Expense/Asset ledgers with subcodes
    expense_ledgers: List[ExpenseLedger] = field(default_factory=list)
    
    # GST configuration
    gst_mapping: GSTLedgerMapping = field(default_factory=GSTLedgerMapping)
    
    # TDS configuration
    tds_mapping: TDSLedgerMapping = field(default_factory=TDSLedgerMapping)
    
    # Cost centres
    cost_centres: List[CostCentre] = field(default_factory=list)
    
    # Salary ledgers for payroll
    salary_ledgers: List[SalaryLedger] = field(default_factory=list)
    
    # Last modified
    last_modified: datetime = field(default_factory=datetime.now)
    modified_by: str = "Admin"
    
    def get_active_suppliers(self) -> List[SupplierLedger]:
        return [s for s in self.suppliers if s.is_active]
    
    def get_active_expense_ledgers(self) -> List[ExpenseLedger]:
        return [e for e in self.expense_ledgers if e.is_active]
    
    def get_active_cost_centres(self) -> List[CostCentre]:
        return [c for c in self.cost_centres if c.is_active]
    
    def get_active_salary_ledgers(self) -> List[SalaryLedger]:
        return [s for s in self.salary_ledgers if s.is_active]
    
    def to_dict(self) -> dict:
        return {
            'suppliers': [s.to_dict() for s in self.suppliers],
            'expense_ledgers': [e.to_dict() for e in self.expense_ledgers],
            'gst_mapping': self.gst_mapping.to_dict(),
            'tds_mapping': self.tds_mapping.to_dict(),
            'cost_centres': [c.to_dict() for c in self.cost_centres],
            'salary_ledgers': [s.to_dict() for s in self.salary_ledgers],
            'last_modified': self.last_modified.isoformat(),
            'modified_by': self.modified_by
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'DebitVoucherConfig':
        last_modified = data.get('last_modified')
        if isinstance(last_modified, str):
            last_modified = datetime.fromisoformat(last_modified)
        
        return cls(
            suppliers=[SupplierLedger.from_dict(s) for s in data.get('suppliers', [])],
            expense_ledgers=[ExpenseLedger.from_dict(e) for e in data.get('expense_ledgers', [])],
            gst_mapping=GSTLedgerMapping.from_dict(data.get('gst_mapping', {})),
            tds_mapping=TDSLedgerMapping.from_dict(data.get('tds_mapping', {})),
            cost_centres=[CostCentre.from_dict(c) for c in data.get('cost_centres', [])],
            salary_ledgers=[SalaryLedger.from_dict(s) for s in data.get('salary_ledgers', [])],
            last_modified=last_modified or datetime.now(),
            modified_by=data.get('modified_by', 'Admin')
        )
    
    @classmethod
    def create_default(cls) -> 'DebitVoucherConfig':
        """Create default configuration with sample data."""
        return cls(
            suppliers=[
                SupplierLedger('SUP001', 'ABC Infotech', '29AABCU9603R1ZM', 'Karnataka'),
                SupplierLedger('SUP002', 'XYZ Services', '27AABCX1234R1ZM', 'Maharashtra', is_rcm_applicable=True),
                SupplierLedger('SUP003', 'Rajesh Kayal', '', 'West Bengal', default_tds_section='194J'),
                SupplierLedger('SUP004', 'Office Rent Ltd', '29AABCO1234R1ZM', 'Karnataka', default_tds_section='194I'),
            ],
            expense_ledgers=[
                ExpenseLedger('5201', 'Website Maintenance', 'WEB', 'AMC', 18.0, 'Operations - HO'),
                ExpenseLedger('5202', 'Software Subscription', 'SW', 'License', 18.0, 'Operations - HO'),
                ExpenseLedger('6101', 'Office Rent', 'RENT', 'HO', 18.0, 'Admin - HO'),
                ExpenseLedger('6102', 'Professional Fees', 'PROF', 'Consultancy', 18.0, 'Admin - HO'),
                ExpenseLedger('7101', 'Digital Marketing', 'MKT', 'Online', 18.0, 'Marketing'),
                ExpenseLedger('8301', 'Computer Equipment', 'IT', 'Hardware', 18.0, 'Admin - HO', is_asset=True),
            ],
            cost_centres=[
                CostCentre('HO', 'Head Office'),
                CostCentre('OPS-HO', 'Operations - HO'),
                CostCentre('ADMIN-HO', 'Admin - HO'),
                CostCentre('MKT', 'Marketing'),
                CostCentre('KENYA', 'Kenya Operations'),
                CostCentre('INDIA', 'India Operations'),
            ],
            salary_ledgers=[
                SalaryLedger('6201', 'Salary of Employees', 'STAFF', 'Staff'),
                SalaryLedger('6201', 'Salary of Employees', 'MGMT', 'Management'),
                SalaryLedger('6202', 'Contractor Payments', 'CONT', 'Contractors'),
            ]
        )
