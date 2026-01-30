"""Data Service - Handles all data persistence operations."""

import json
import os
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from models.voucher import Voucher, VoucherStatus
from models.master_data import MasterData
from models.account_head import AccountHead, VoucherType


class DataService:
    """
    Handles all data persistence operations.
    
    Data is stored in JSON files in the local data directory.
    Supports Excel export for sharing/backup.
    """
    
    def __init__(self, data_dir: str = None):
        """
        Initialize data service.
        
        Args:
            data_dir: Path to data directory. Defaults to ./data
        """
        if data_dir is None:
            # Get the directory where the app is running
            app_dir = Path(__file__).parent.parent
            data_dir = app_dir / 'data'
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.master_data_file = self.data_dir / 'master_data.json'
        self.vouchers_file = self.data_dir / 'vouchers.json'
        
        # Initialize data
        self._master_data: Optional[MasterData] = None
        self._vouchers: List[Voucher] = []
    
    def load_master_data(self) -> MasterData:
        """Load master data from JSON file."""
        if self._master_data is not None:
            return self._master_data
        
        if self.master_data_file.exists():
            self._master_data = MasterData.load_from_json(str(self.master_data_file))
        else:
            # Create default master data
            self._master_data = MasterData.create_default()
            self.save_master_data()
        
        return self._master_data
    
    def save_master_data(self) -> None:
        """Save master data to JSON file."""
        if self._master_data:
            self._master_data.save_to_json(str(self.master_data_file))
    
    def get_master_data(self) -> MasterData:
        """Get current master data (loads if not cached)."""
        return self.load_master_data()
    
    def reload_master_data(self) -> MasterData:
        """Force reload master data from file."""
        self._master_data = None
        return self.load_master_data()
    
    def load_vouchers(self) -> List[Voucher]:
        """Load vouchers from JSON file."""
        if self._vouchers:
            return self._vouchers
        
        if self.vouchers_file.exists():
            with open(self.vouchers_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._vouchers = [Voucher.from_dict(v) for v in data.get('vouchers', [])]
        else:
            self._vouchers = []
        
        return self._vouchers
    
    def save_vouchers(self) -> None:
        """Save vouchers to JSON file."""
        data = {
            'vouchers': [v.to_dict() for v in self._vouchers],
            'last_modified': datetime.now().isoformat()
        }
        with open(self.vouchers_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_vouchers(self) -> List[Voucher]:
        """Get all vouchers."""
        return self.load_vouchers()
    
    def add_voucher(self, voucher: Voucher) -> None:
        """Add a new voucher."""
        self.load_vouchers()  # Ensure loaded
        self._vouchers.append(voucher)
        self.save_vouchers()
    
    def add_vouchers_bulk(self, vouchers: List[Voucher]) -> None:
        """Add multiple vouchers at once."""
        self.load_vouchers()  # Ensure loaded
        self._vouchers.extend(vouchers)
        self.save_vouchers()
    
    def update_voucher(self, voucher: Voucher) -> bool:
        """Update an existing voucher."""
        self.load_vouchers()
        for i, v in enumerate(self._vouchers):
            if v.voucher_id == voucher.voucher_id:
                self._vouchers[i] = voucher
                self.save_vouchers()
                return True
        return False
    
    def delete_voucher(self, voucher_id: str) -> bool:
        """Delete a voucher by ID."""
        self.load_vouchers()
        for i, v in enumerate(self._vouchers):
            if v.voucher_id == voucher_id:
                del self._vouchers[i]
                self.save_vouchers()
                return True
        return False
    
    def get_voucher_by_id(self, voucher_id: str) -> Optional[Voucher]:
        """Get voucher by ID."""
        self.load_vouchers()
        for v in self._vouchers:
            if v.voucher_id == voucher_id:
                return v
        return None
    
    def get_vouchers_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Voucher]:
        """Get vouchers within a date range."""
        self.load_vouchers()
        return [
            v for v in self._vouchers
            if start_date <= v.date <= end_date
        ]
    
    def get_vouchers_by_status(self, status: VoucherStatus) -> List[Voucher]:
        """Get vouchers by status."""
        self.load_vouchers()
        return [v for v in self._vouchers if v.status == status]
    
    def get_vouchers_by_segment(self, segment: str) -> List[Voucher]:
        """Get vouchers by segment."""
        self.load_vouchers()
        return [v for v in self._vouchers if v.segment == segment]
    
    def clear_vouchers(self) -> None:
        """Clear all vouchers (use with caution)."""
        self._vouchers = []
        self.save_vouchers()
    
    def export_to_excel(self, filepath: str) -> bool:
        """
        Export vouchers to Excel file.
        
        # BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        """
        # TODO: Implement Excel export using openpyxl
        pass
    
    def import_from_excel(self, filepath: str) -> bool:
        """
        Import master data from Excel file.
        
        # BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        """
        # TODO: Implement Excel import
        pass
