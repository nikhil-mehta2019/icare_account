"""Data Service - Handles all data persistence operations."""

import json
import os
from datetime import datetime
from typing import List, Optional, Any
from pathlib import Path

# Import models
from models.voucher import Voucher, VoucherStatus
from models.master_data import MasterData
from models.debit_voucher import (
    JournalVoucher, PurchaseVoucher, PayrollVoucher, 
    DebitVoucherType, GSTConfig, TDSConfig
)

class DataService:
    """
    Handles all data persistence operations.
    Robustly handles mixed Object/Dictionary data types.
    """
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            app_dir = Path(__file__).parent.parent
            data_dir = app_dir / 'data'
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.master_data_file = self.data_dir / 'master_data.json'
        self.vouchers_file = self.data_dir / 'vouchers.json'
        
        self._master_data: Optional[MasterData] = None
        self._vouchers: List[Any] = []
    
    def load_master_data(self) -> MasterData:
        if self._master_data is not None:
            return self._master_data
        
        if self.master_data_file.exists():
            self._master_data = MasterData.load_from_json(str(self.master_data_file))
        else:
            self._master_data = MasterData.create_default()
            self.save_master_data()
        return self._master_data
    
    def save_master_data(self) -> None:
        if self._master_data:
            self._master_data.save_to_json(str(self.master_data_file))
    
    def get_master_data(self) -> MasterData:
        return self.load_master_data()
    
    def reload_master_data(self) -> MasterData:
        self._master_data = None
        return self.load_master_data()
    
    def load_vouchers(self) -> List[Any]:
        """Load vouchers from JSON, intelligently converting to Objects."""
        if self._vouchers:
            return self._vouchers
        
        if self.vouchers_file.exists():
            try:
                with open(self.vouchers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert dicts to specific objects
                    self._vouchers = [self._dict_to_voucher(v) for v in data.get('vouchers', [])]
            except Exception as e:
                print(f"Error loading vouchers: {e}")
                self._vouchers = []
        else:
            self._vouchers = []
        
        return self._vouchers

    def _dict_to_voucher(self, data: dict) -> Any:
        """Factory method to convert dict to correct Voucher Object."""
        try:
            v_type = data.get('voucher_type')
            
            # New Models
            if v_type == 'Journal' or v_type == DebitVoucherType.JOURNAL.value:
                return JournalVoucher(**self._filter_args(JournalVoucher, data))
            elif v_type == 'Purchase' or v_type == DebitVoucherType.PURCHASE.value:
                if isinstance(data.get('gst'), dict): data['gst'] = GSTConfig(**data['gst'])
                if isinstance(data.get('tds'), dict): data['tds'] = TDSConfig(**data['tds'])
                return PurchaseVoucher(**self._filter_args(PurchaseVoucher, data))
            elif v_type == 'Payroll' or v_type == DebitVoucherType.PAYROLL.value:
                if isinstance(data.get('tds'), dict): data['tds'] = TDSConfig(**data['tds'])
                return PayrollVoucher(**self._filter_args(PayrollVoucher, data))
            
            # Legacy Model fallback
            return Voucher.from_dict(data)
        except Exception as e:
            print(f"Conversion error for voucher {data.get('voucher_no')}: {e}")
            return Voucher.from_dict(data)

    def _filter_args(self, cls, data):
        """Helper to safely pass arguments to dataclasses."""
        valid_fields = set(cls.__annotations__.keys())
        # Add parent class annotations if inheriting
        if hasattr(cls, '__post_init__'):
             # Simplistic approach: just pass everything and let the class ignore extra or handle strictness
             # For robustness, we try to match keys.
             # Better approach: check keys in data vs keys in __init__? Dataclasses use __init__.
             pass
        # Fallback: Just return data, assuming models ignore extra via **kwargs if implemented or strict match
        # Since standard dataclasses don't take **kwargs by default, we filter:
        # We need to know ALL fields including parent BaseVoucher
        from models.debit_voucher import BaseVoucher
        all_fields = set(BaseVoucher.__annotations__.keys()) | valid_fields
        return {k: v for k, v in data.items() if k in all_fields}

    def save_vouchers(self) -> None:
        """Save vouchers to JSON, handling both Objects and Dicts."""
        serialized_vouchers = []
        for v in self._vouchers:
            # FIX: Robust check for to_dict method
            if hasattr(v, 'to_dict'):
                serialized_vouchers.append(v.to_dict())
            elif isinstance(v, dict):
                serialized_vouchers.append(v)
            else:
                try:
                    serialized_vouchers.append(v.__dict__)
                except:
                    print(f"Failed to serialize voucher: {v}")

        data = {
            'vouchers': serialized_vouchers,
            'last_modified': datetime.now().isoformat()
        }
        
        with open(self.vouchers_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_vouchers(self) -> List[Any]:
        return self.load_vouchers()
    
    def add_voucher(self, voucher: Any) -> None:
        self.load_vouchers()
        self._vouchers.append(voucher)
        self.save_vouchers()
    
    def add_vouchers_bulk(self, vouchers: List[Any]) -> None:
        self.load_vouchers()
        # Accept the list as-is (Objects or Dicts), save_vouchers handles the rest
        self._vouchers.extend(vouchers)
        self.save_vouchers()
    
    def update_voucher(self, voucher: Any) -> bool:
        self.load_vouchers()
        
        # Get ID safely
        vid = getattr(voucher, 'voucher_id', None) or getattr(voucher, 'voucher_no', None)
        if isinstance(voucher, dict):
            vid = voucher.get('voucher_id') or voucher.get('voucher_no')

        for i, v in enumerate(self._vouchers):
            curr_id = getattr(v, 'voucher_id', getattr(v, 'voucher_no', None))
            if isinstance(v, dict):
                curr_id = v.get('voucher_id') or v.get('voucher_no')
            
            if curr_id == vid:
                self._vouchers[i] = voucher
                self.save_vouchers()
                return True
        return False
    
    def delete_voucher(self, voucher_id: str) -> bool:
        self.load_vouchers()
        original_count = len(self._vouchers)
        
        self._vouchers = [
            v for v in self._vouchers 
            if (getattr(v, 'voucher_id', getattr(v, 'voucher_no', '')) != voucher_id and 
                (v.get('voucher_id') if isinstance(v, dict) else '') != voucher_id)
        ]
        
        if len(self._vouchers) < original_count:
            self.save_vouchers()
            return True
        return False

    def get_vouchers_by_date_range(self, start: datetime, end: datetime) -> List[Any]:
        self.load_vouchers()
        res = []
        for v in self._vouchers:
            d = getattr(v, 'voucher_date', getattr(v, 'date', None))
            if isinstance(v, dict): d = v.get('voucher_date') or v.get('date')
            
            if not d: continue
            
            if isinstance(d, str):
                try: d = datetime.strptime(d, "%Y-%m-%d")
                except: continue
            
            # Compare datetime/date
            check = d.date() if isinstance(d, datetime) else d
            s = start.date() if isinstance(start, datetime) else start
            e = end.date() if isinstance(end, datetime) else end
            
            if s <= check <= e:
                res.append(v)
        return res
    
    def get_vouchers_by_status(self, status: VoucherStatus) -> List[Any]:
        self.load_vouchers()
        return [v for v in self._vouchers if (getattr(v, 'status', '') == status or (isinstance(v, dict) and v.get('status') == status))]
    
    def get_vouchers_by_segment(self, segment: str) -> List[Any]:
        self.load_vouchers()
        return [v for v in self._vouchers if (getattr(v, 'segment', '') == segment or (isinstance(v, dict) and v.get('segment') == segment))]
    
    def clear_vouchers(self) -> None:
        self._vouchers = []
        self.save_vouchers()