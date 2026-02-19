"""MasterData Model - Central configuration and data container."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
import json
import os

from .account_head import AccountHead, VoucherType
from .narration import Narration
from .segment import Segment


@dataclass
class MasterDataSettings:
    """Settings for master data governance."""
    is_frozen: bool = True  # Whether master data editing is locked
    admin_password: str = "Subudhi123"  # Default password
    last_modified: datetime = field(default_factory=datetime.now)
    modified_by: str = "System"

    # === NEW: Auto Backup Settings ===
    backup_directory: str = ""
    backup_retention_count: int = 5
    auto_backup_enabled: bool = True


@dataclass 
class MasterData:
    """
    Central container for all master data.
    
    This is the "brain" of the accounting system containing:
    - Account heads (Chart of Accounts)
    - Narration templates
    - Segments
    - System settings
    """
    
    account_heads: List[AccountHead] = field(default_factory=list)
    narrations: List[Narration] = field(default_factory=list)
    segments: List[Segment] = field(default_factory=list)
    settings: MasterDataSettings = field(default_factory=MasterDataSettings)
    vendors: List[dict] = field(default_factory=list)
    
    def get_account_heads_by_type(self, voucher_type: VoucherType) -> List[AccountHead]:
        """
        Get account heads filtered by voucher type.
        
        Args:
            voucher_type: VoucherType.DEBIT or VoucherType.CREDIT
            
        Returns:
            List of active account heads matching the type
        """
        return [
            head for head in self.account_heads 
            if head.voucher_type == voucher_type and head.is_active
        ]
    
    def get_debit_heads(self) -> List[AccountHead]:
        """Get all active debit account heads."""
        return self.get_account_heads_by_type(VoucherType.DEBIT)
    
    def get_credit_heads(self) -> List[AccountHead]:
        """Get all active credit account heads."""
        return self.get_account_heads_by_type(VoucherType.CREDIT)
    
    def get_account_by_code(self, code: str) -> Optional[AccountHead]:
        """Get account head by its 4-digit code."""
        for head in self.account_heads:
            if head.code == code:
                return head
        return None
    
    def get_narrations_for_account(self, account_code: str) -> List[Narration]:
        """Get narration templates for a specific account."""
        return [
            narr for narr in self.narrations 
            if narr.account_code == account_code and narr.is_active
        ]
    
    def get_segment_by_id(self, segment_id: str) -> Optional[Segment]:
        """Get segment by ID."""
        for seg in self.segments:
            if seg.segment_id == segment_id:
                return seg
        return None
    
    def get_active_segments(self) -> List[Segment]:
        """Get all active segments."""
        return [seg for seg in self.segments if seg.is_active]
    
    def to_dict(self) -> dict:
        """Convert master data to dictionary for serialization."""
        return {
            'account_heads': [head.to_dict() for head in self.account_heads],
            'narrations': [narr.to_dict() for narr in self.narrations],
            'segments': [seg.to_dict() for seg in self.segments],
            'vendors': self.vendors,
            'settings': {
                'is_frozen': self.settings.is_frozen,
                'admin_password': self.settings.admin_password,
                'last_modified': self.settings.last_modified.isoformat(),
                'modified_by': self.settings.modified_by,
                'backup_directory': getattr(self.settings, 'backup_directory', ''),
                'backup_retention_count': getattr(self.settings, 'backup_retention_count', 30),
                'auto_backup_enabled': getattr(self.settings, 'auto_backup_enabled', True)
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MasterData':
        """Create master data from dictionary."""
        account_heads = [
            AccountHead.from_dict(h) for h in data.get('account_heads', [])
        ]
        narrations = [
            Narration.from_dict(n) for n in data.get('narrations', [])
        ]
        segments = [
            Segment.from_dict(s) for s in data.get('segments', [])
        ]
        vendors = data.get('vendors', [])
        settings_data = data.get('settings', {})
        last_modified = settings_data.get('last_modified')
        if isinstance(last_modified, str):
            last_modified = datetime.fromisoformat(last_modified)
        else:
            last_modified = datetime.now()
        
        settings = MasterDataSettings(
            is_frozen=settings_data.get('is_frozen', True),
            admin_password=settings_data.get('admin_password', 'Subudhi123'),
            last_modified=last_modified,
            modified_by=settings_data.get('modified_by', 'System'),
            backup_directory=settings_data.get('backup_directory', ''),
            backup_retention_count=settings_data.get('backup_retention_count', 5),
            auto_backup_enabled=settings_data.get('auto_backup_enabled', True)
        )
        
        return cls(
            account_heads=account_heads,
            narrations=narrations,
            segments=segments,
            vendors=vendors,
            settings=settings
        )
    
    def save_to_json(self, filepath: str) -> None:
        """Save master data to JSON file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_json(cls, filepath: str) -> 'MasterData':
        """Load master data from JSON file."""
        if not os.path.exists(filepath):
            return cls.create_default()
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    @classmethod
    def create_default(cls) -> 'MasterData':
        """Create default master data with iCare COA."""
        # Default segments
        segments = Segment.get_default_segments()
        
        # Default account heads from the document
        account_heads = cls._get_default_account_heads()
        
        # Default narrations
        narrations = cls._get_default_narrations()
        
        return cls(
            account_heads=account_heads,
            narrations=narrations,
            segments=segments,
            settings=MasterDataSettings()
        )
    
    @staticmethod
    def _get_default_account_heads() -> List[AccountHead]:
        """Get default account heads from iCare COA."""
        return [
            # 1000 Series - Operating Sales (Credit)
            AccountHead('1101', VoucherType.CREDIT, 'Sales Income', 'Retail (Wix)', 'Online Cert - Basic', 'Retail', 'Wix Ord: [ID] - Basic Level'),
            AccountHead('1102', VoucherType.CREDIT, 'Sales Income', 'Retail (Wix)', 'Online Cert - Advanced', 'Retail', 'Wix Ord: [ID] - Advanced Level Training'),
            AccountHead('1103', VoucherType.CREDIT, 'Sales Income', 'Retail (Wix)', 'Masterclass', 'Retail', 'Wix Ord: [ID] - Special Webinar Access'),
            AccountHead('1201', VoucherType.CREDIT, 'Sales Income', 'Franchise-Kenya', 'Joining Fee', 'Kenya', 'One-time setup fee: Kenya Partner'),
            AccountHead('1202', VoucherType.CREDIT, 'Sales Income', 'Franchise-Kenya', 'Royalty Income', 'Kenya', 'Monthly Royalty share: Kenya Operations'),
            AccountHead('1203', VoucherType.CREDIT, 'Sales Income', 'Franchise-Kenya', 'Material Sales', 'Kenya', 'Dispatch of Practical Training Kits (Kenya)'),
            AccountHead('1301', VoucherType.CREDIT, 'Sales Income', 'Franchise-India', 'Joining Fee', 'India', 'One-time setup fee: India Partner'),
            AccountHead('1302', VoucherType.CREDIT, 'Sales Income', 'Franchise-India', 'Royalty Income', 'India', 'Monthly Royalty share: India Operations'),
            AccountHead('1401', VoucherType.CREDIT, 'Sales Income', 'Corporate', 'B2B Training', 'Corporate', 'Bulk Employee Certification - [Client Name]'),
            
            # 2000 Series - Other Income (Credit)
            AccountHead('2101', VoucherType.CREDIT, 'Other Income', 'Interest', 'Bank Interest', '', 'Bank Interest Savings/FD Interest Credit'),
            AccountHead('2201', VoucherType.CREDIT, 'Other Income', 'Forex', 'Realized Gain', '', 'Forex Gain on USD/KES conversion'),
            
            # 3000 Series - Loans/Liabilities (Credit)
            AccountHead('3101', VoucherType.CREDIT, 'Loans', 'Secured', 'HDFC OD', '', 'Withdrawal from Working Capital Limit'),
            AccountHead('3201', VoucherType.CREDIT, 'Loans', 'Director Loan', None, 'POOL', 'Funds introduced by Subudhi'),
            
            # 4000 Series - Asset Sales (Credit)
            AccountHead('4101', VoucherType.CREDIT, 'Asset Sale', 'Fixed Assets', 'IT Equipment', '', 'Sale of depreciated Laptops/PCs'),
            
            # 5000 Series - Direct Costs (Debit)
            AccountHead('5101', VoucherType.DEBIT, 'Direct Cost', 'Cert. Fees', 'Partner Board Fee', 'POOL', 'Payout to Certifying Body for Boards'),
            AccountHead('5102', VoucherType.DEBIT, 'Direct Cost', 'Material', 'Training Kits', '', 'Purchase of physical components for kits', True, True),
            AccountHead('5201', VoucherType.DEBIT, 'Direct Cost', 'Platform', 'Wix Subscription', 'POOL', 'Monthly Wix Store/Platform charges'),
            AccountHead('5202', VoucherType.DEBIT, 'Direct Cost', 'Platform', 'LMS Hosting', 'POOL', 'Server/Hosting for Online Learning Portal'),
            
            # 6000 Series - Fixed Overheads (Debit)
            AccountHead('6101', VoucherType.DEBIT, 'Admin Exp', 'Rent', 'Office Rent', 'POOL', 'Monthly Rent for Office Premises'),
            AccountHead('6102', VoucherType.DEBIT, 'Admin Exp', 'Utilities', 'Electricity/Web', 'POOL', 'Monthly Electricity & Internet bills'),
            AccountHead('6201', VoucherType.DEBIT, 'Personnel', 'Salary', 'Staff Salary', 'POOL', 'Monthly Salary Disbursement'),
            AccountHead('6301', VoucherType.DEBIT, 'Travel', 'International', 'Kenya Audit', 'POOL', 'Airfare/Stay for Kenya Partner Audit'),
            
            # 7000 Series - Marketing/Sales (Debit)
            AccountHead('7101', VoucherType.DEBIT, 'Marketing', 'Digital Ads', 'Facebook/Google', 'POOL', 'Ad spend for Online Sales Campaigns'),
            AccountHead('7201', VoucherType.DEBIT, 'Marketing', 'Collateral', 'Brand Material', '', 'Printing of Brochures and Certificates'),
            
            # 8000 Series - Finance/Assets (Debit)
            AccountHead('8101', VoucherType.DEBIT, 'Finance', 'Bank Charges', 'Processing Fee', '', 'Bank Charges for Wire/Forex Transfer'),
            AccountHead('8201', VoucherType.DEBIT, 'Repayment', 'Loan Principal', 'Loan EMI', '', 'Monthly Principal Repayment to Bank'),
            AccountHead('8301', VoucherType.DEBIT, 'Capital Exp', 'Assets', 'IT Hardware', '', 'Purchase of New Servers/Workstations'),
        ]
    
    @staticmethod
    def _get_default_narrations() -> List[Narration]:
        """Get default narration templates."""
        narrations = []
        narration_id = 1
        
        # Map of account codes to their narrations
        narration_map = {
            '1101': ['Wix Ord: [ID] - Basic Level', 'Online sale - Basic certification'],
            '1102': ['Wix Ord: [ID] - Advanced Level Training', 'Online sale - Advanced certification'],
            '1103': ['Wix Ord: [ID] - Special Webinar Access', 'Masterclass enrollment'],
            '1201': ['One-time setup fee: Kenya Partner', 'Kenya franchise joining fee received'],
            '1202': ['Monthly Royalty share: Kenya Operations', 'Kenya monthly royalty payment'],
            '1203': ['Dispatch of Practical Training Kits (Kenya)', 'Kenya training materials sale'],
            '1301': ['One-time setup fee: India Partner', 'India franchise joining fee received'],
            '1302': ['Monthly Royalty share: India Operations', 'India monthly royalty payment'],
            '1401': ['Bulk Employee Certification - [Client Name]', 'Corporate training sale'],
            '2101': ['Bank Interest Savings/FD Interest Credit', 'Interest income received'],
            '2201': ['Forex Gain on USD/KES conversion', 'Foreign exchange gain'],
            '3101': ['Withdrawal from Working Capital Limit', 'OD facility utilized'],
            '3201': ['Funds introduced by Subudhi', 'Director loan received'],
            '4101': ['Sale of depreciated Laptops/PCs', 'Asset disposal'],
            '5101': ['Payout to Certifying Body for Boards', 'Certification fees payment'],
            '5102': ['Purchase of physical components for kits', 'Training materials purchase'],
            '5201': ['Monthly Wix Store/Platform charges', 'Platform subscription payment'],
            '5202': ['Server/Hosting for Online Learning Portal', 'LMS hosting charges'],
            '6101': ['Monthly Rent for Office Premises', 'Office rent payment'],
            '6102': ['Monthly Electricity & Internet bills', 'Utility bills payment'],
            '6201': ['Monthly Salary Disbursement', 'Staff salaries payment'],
            '6301': ['Airfare/Stay for Kenya Partner Audit', 'Travel expense - Kenya audit'],
            '7101': ['Ad spend for Online Sales Campaigns', 'Digital marketing spend'],
            '7201': ['Printing of Brochures and Certificates', 'Marketing collateral purchase'],
            '8101': ['Bank Charges for Wire/Forex Transfer', 'Bank charges payment'],
            '8201': ['Monthly Principal Repayment to Bank', 'Loan EMI payment'],
            '8301': ['Purchase of New Servers/Workstations', 'IT equipment purchase'],
        }
        
        for code, templates in narration_map.items():
            for template in templates:
                has_placeholder = '[' in template and ']' in template
                placeholder_label = None
                if '[ID]' in template:
                    placeholder_label = 'Order/Reference ID'
                elif '[Client Name]' in template:
                    placeholder_label = 'Client Name'
                
                narrations.append(Narration(
                    narration_id=f'NARR_{narration_id:04d}',
                    account_code=code,
                    template=template,
                    has_placeholder=has_placeholder,
                    placeholder_label=placeholder_label
                ))
                narration_id += 1
        
        return narrations
