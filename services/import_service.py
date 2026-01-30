"""Import Service - Handles CSV bulk import operations."""

import csv
import os
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from pathlib import Path

from models.voucher import Voucher, VoucherStatus
from models.account_head import VoucherType
from models.import_result import ImportResult, ImportStatus, ImportError


class ImportService:
    """
    Handles bulk import operations from CSV files.
    
    Supports:
    - Generic CSV import
    - Wix sales export parsing
    - Preview before confirmation
    """
    
    def __init__(self):
        """Initialize import service."""
        self._current_import: Optional[ImportResult] = None
    
    def parse_csv_preview(self, filepath: str, max_preview_rows: int = 10) -> ImportResult:
        """
        Parse CSV file and return preview data.
        
        Args:
            filepath: Path to CSV file
            max_preview_rows: Maximum rows to include in preview
            
        Returns:
            ImportResult with preview data populated
        """
        result = ImportResult(
            filename=os.path.basename(filepath),
            import_type='CSV',
            status=ImportStatus.PENDING
        )
        
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                # Try to detect delimiter
                sample = f.read(4096)
                f.seek(0)
                
                # Use csv.Sniffer to detect dialect
                try:
                    dialect = csv.Sniffer().sniff(sample)
                except csv.Error:
                    dialect = csv.excel
                
                reader = csv.DictReader(f, dialect=dialect)
                result.column_headers = reader.fieldnames or []
                
                # Read all rows for counting
                rows = list(reader)
                result.total_rows = len(rows)
                
                # Store preview data
                result.preview_data = rows[:max_preview_rows]
        
        except Exception as e:
            result.status = ImportStatus.FAILED
            result.add_error(0, 'FILE_READ_ERROR', str(e))
        
        self._current_import = result
        return result
    
    def parse_wix_csv(self, filepath: str) -> ImportResult:
        """
        Parse Wix sales export CSV file.
        
        Maps Wix columns to internal voucher structure:
        - Order ID -> reference_id
        - Date -> date
        - Total -> amount
        - Auto-assigns code 1101 (Retail Sales)
        - Auto-assigns segment "Retail"
        
        # BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        """
        result = ImportResult(
            filename=os.path.basename(filepath),
            import_type='Wix Export',
            status=ImportStatus.IN_PROGRESS
        )
        
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                result.column_headers = reader.fieldnames or []
                result.total_rows = 0
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is 1)
                    result.total_rows += 1
                    
                    try:
                        # TODO: Map Wix-specific column names
                        # Expected columns: Order ID, Date, Total Amount, Customer Name, etc.
                        
                        voucher = self._map_wix_row_to_voucher(row, row_num)
                        if voucher:
                            result.add_voucher(voucher)
                        else:
                            result.skipped_rows += 1
                    
                    except Exception as e:
                        result.add_error(row_num, 'PARSE_ERROR', str(e), raw_data=row)
            
            result.complete()
        
        except Exception as e:
            result.status = ImportStatus.FAILED
            result.add_error(0, 'FILE_READ_ERROR', str(e))
        
        self._current_import = result
        return result
    
    def _map_wix_row_to_voucher(self, row: Dict, row_num: int) -> Optional[Voucher]:
        """
        Map a single Wix CSV row to a Voucher.
        
        # BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        
        Expected Wix columns (may vary):
        - 'Order ID' or 'orderNumber'
        - 'Date' or 'dateCreated'
        - 'Total' or 'totals.total'
        - 'Item Name' or 'lineItems.name'
        """
        # TODO: Implement actual Wix column mapping based on export format
        
        # Try common column names
        order_id = row.get('Order ID') or row.get('orderNumber') or row.get('Order Number', '')
        
        # Try to parse date
        date_str = row.get('Date') or row.get('dateCreated') or row.get('Order Date', '')
        try:
            # Handle various date formats
            if date_str:
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S']:
                    try:
                        date = datetime.strptime(date_str.split('T')[0], fmt.split('T')[0])
                        break
                    except ValueError:
                        continue
                else:
                    date = datetime.now()
            else:
                date = datetime.now()
        except (ValueError, AttributeError):
            date = datetime.now()
        
        # Try to parse amount
        amount_str = row.get('Total') or row.get('totals.total') or row.get('Amount', '0')
        try:
            # Remove currency symbols and parse
            amount_str = str(amount_str).replace('$', '').replace(',', '').replace('₹', '').strip()
            amount = float(amount_str) if amount_str else 0.0
        except (ValueError, TypeError):
            amount = 0.0
        
        if amount <= 0:
            return None  # Skip zero/negative amounts
        
        # Create voucher with Wix defaults
        voucher = Voucher(
            date=date,
            voucher_type=VoucherType.CREDIT,  # Sales are credits
            account_code='1101',  # Retail Sales - Basic (default)
            account_name='Sales Income - Retail (Wix) - Online Cert - Basic',
            amount=amount,
            segment='Retail',
            narration=f'Wix Ord: {order_id} - Basic Level' if order_id else 'Wix Online Sale',
            reference_id=order_id,
            status=VoucherStatus.PENDING_REVIEW,
            source='Wix Import'
        )
        
        return voucher
    
    def import_generic_csv(self, filepath: str, column_mapping: Dict[str, str]) -> ImportResult:
        """
        Import generic CSV with custom column mapping.
        
        Args:
            filepath: Path to CSV file
            column_mapping: Dict mapping internal fields to CSV columns
                           e.g., {'amount': 'Total', 'date': 'Transaction Date'}
        
        # BUSINESS LOGIC TO BE IMPLEMENTED MANUALLY
        """
        result = ImportResult(
            filename=os.path.basename(filepath),
            import_type='CSV',
            status=ImportStatus.IN_PROGRESS
        )
        
        # TODO: Implement generic CSV import with column mapping
        result.status = ImportStatus.PENDING
        self._current_import = result
        return result
    
    def get_current_import(self) -> Optional[ImportResult]:
        """Get the current import operation."""
        return self._current_import
    
    def confirm_import(self) -> ImportResult:
        """
        Confirm and finalize the current import.
        
        Returns:
            Final ImportResult with status updated
        """
        if self._current_import:
            self._current_import.complete()
        return self._current_import
    
    def cancel_import(self) -> None:
        """Cancel the current import operation."""
        self._current_import = None
    
    def validate_csv_structure(self, filepath: str, required_columns: List[str]) -> Tuple[bool, List[str]]:
        """
        Validate that CSV has required columns.
        
        Args:
            filepath: Path to CSV file
            required_columns: List of required column names
            
        Returns:
            Tuple of (is_valid, missing_columns)
        """
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                headers = set(reader.fieldnames or [])
            
            missing = [col for col in required_columns if col not in headers]
            return (len(missing) == 0, missing)
        
        except Exception as e:
            return (False, [f'Error reading file: {e}'])
