"""Import Service - Handles CSV bulk import operations."""

import csv
import os
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from pathlib import Path

from models.voucher import Voucher, VoucherStatus
from models.account_head import VoucherType
from models.import_result import ImportResult, ImportStatus, ImportError
from services.voucher_config_service import get_voucher_config

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

    def _is_international_location(self, loc: str) -> bool:
        """
        Helper to robustly determine if a location is International.
        Checks against Indian states; if not matched, assumes International.
        """
        if not loc:
            return False
        loc = str(loc).lower().strip()
        
        # 1. Check for Domestic (Indian) States & Keywords
        domestic_indicators = [
            'india', 'andaman', 'andhra', 'arunachal', 'assam', 'bihar', 
            'chandigarh', 'chhattisgarh', 'dadra', 'daman', 'delhi', 'goa', 
            'gujarat', 'haryana', 'himachal', 'jammu', 'kashmir', 'jharkhand', 
            'karnataka', 'kerala', 'ladakh', 'lakshadweep', 'madhya', 
            'maharashtra', 'manipur', 'meghalaya', 'mizoram', 'nagaland', 
            'odisha', 'puducherry', 'punjab', 'rajasthan', 'sikkim', 'tamil', 
            'telangana', 'tripura', 'uttar', 'uttarakhand', 'bengal', 'pune', 'mumbai'
        ]
        
        if any(state in loc for state in domestic_indicators):
            return False
            
        # 2. Explicit International Keywords
        international_keywords = [
            'international', 'foreign', 'export', 'outside india', 
            'row', 'global', 'overseas', 'usa', 'uk', 'london', 'america'
        ]
        
        if any(kw in loc for kw in international_keywords):
            return True
            
        # 3. Fallback: If it's not an Indian state, classify as International
        return True

    def parse_sales_csv(self, filepath: str, global_data: Dict) -> ImportResult:
        result = ImportResult(
            filename=os.path.basename(filepath),
            import_type='B2C Sales Import',
            status=ImportStatus.IN_PROGRESS
        )
        
        required_globals = ['from_date', 'to_date', 'income_head_code', 'bank_head_name']
        missing_globals = [g for g in required_globals if not global_data.get(g)]
        if missing_globals:
            result.status = ImportStatus.FAILED
            result.add_error(0, 'MISSING_GLOBALS', f"Missing required global fields: {', '.join(missing_globals)}")
            self._current_import = result
            return result

        required_columns = ['Business Segment', 'Product Code', 'Location', 'Amount', 'SGST', 'CGST', 'IGST']
        is_valid, missing = self.validate_csv_structure(filepath, required_columns)
        
        if not is_valid:
            result.status = ImportStatus.FAILED
            result.add_error(0, 'VALIDATION_ERROR', f"Missing required columns: {', '.join(missing)}")
            self._current_import = result
            return result

        try:
            config = get_voucher_config()
            head = config.get_tally_head_by_code(global_data.get('income_head_code', ''), "credit")
            if head:
                classification = config.classify_head(head)
                if classification == "B2B":
                    result.status = ImportStatus.FAILED
                    result.add_error(0, 'RULE_VIOLATION', "Strict Enforcement: B2B transactions must be entered through manual entry.")
                    self._current_import = result
                    return result
                elif classification == "UNKNOWN":
                    result.status = ImportStatus.FAILED
                    result.add_error(0, 'RULE_VIOLATION', "Unable to determine transaction type from accounting head. Please check configuration.")
                    self._current_import = result
                    return result
        except Exception as e:
            pass # Fallback to normal execution if config service is somehow unavailable

        try:
            from_date = global_data['from_date']
            to_date = global_data['to_date']
            income_head_code = global_data['income_head_code']
            income_head_name = global_data.get('income_head_name', 'Operating Income')
            bank_head_name = global_data['bank_head_name']

            fd = from_date.strftime('%d-%b-%Y') if hasattr(from_date, 'strftime') else str(from_date)
            td = to_date.strftime('%d-%b-%Y') if hasattr(to_date, 'strftime') else str(to_date)
            period_str = f"for the period {fd} to {td}"

            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                result.column_headers = reader.fieldnames or []
                
                b2b_column_names = [col for col in result.column_headers if col.lower() in ['gstin', 'franchisee', 'b2b', 'customer gstin', 'party code']]
                
                result.total_rows = 0

                for row_num, row in enumerate(reader, start=2):
                    result.total_rows += 1
                    try:
                        is_b2b = any(str(row.get(col, '')).strip() for col in b2b_column_names)
                        if is_b2b:
                            result.add_error(row_num, 'B2C_ONLY_ERROR', "B2B identifiers (GSTIN/Franchisee) found. Bulk import is strictly for B2C.", raw_data=row)
                            continue

                        amount = float(row.get('Amount', 0) or 0)
                        sgst = float(row.get('SGST', 0) or 0)
                        cgst = float(row.get('CGST', 0) or 0)
                        igst = float(row.get('IGST', 0) or 0)

                        if amount <= 0:
                            result.skipped_rows += 1
                            continue

                        is_international = self._is_international_location(row.get('Location', ''))
                        
                        if is_international:
                            if cgst > 0 or sgst > 0 or igst > 0:
                                if hasattr(result, 'warnings'):
                                    result.warnings.append(f"Row {row_num}: International sales are GST exempt. Provided GST values ignored.")
                                cgst = sgst = igst = 0.0
                        
                        gst_total = cgst + sgst + igst

                        if round(amount, 2) < round(gst_total, 2):
                            result.add_error(row_num, 'AMOUNT_MISMATCH', f"Gross Amount ({amount}) cannot be less than Total GST ({gst_total}).", raw_data=row)
                            continue

                        base_amount = amount - gst_total

                        billing_type = "International" if is_international else "Domestic"
                        narration = f"{billing_type} B2C Billing, {period_str}"

                        v = Voucher(
                            date=datetime.now(),
                            voucher_type=VoucherType.CREDIT,
                            account_code=income_head_code,
                            amount=amount,
                            segment=row.get('Business Segment', ''),
                            narration=narration,
                            status=VoucherStatus.PENDING_REVIEW,
                            source='B2C Bulk Import',
                            from_date=from_date,
                            to_date=to_date,
                            cgst_amount=cgst,
                            sgst_amount=sgst,
                            igst_amount=igst
                        )

                        v.party_ledger = bank_head_name
                        v.expense_ledger = income_head_name
                        v.account_name = income_head_name
                        v.tally_head = income_head_name
                        
                        v.base_amount = base_amount
                        v.net_payable = amount

                        result.add_voucher(v)

                    except ValueError as ve:
                         result.add_error(row_num, 'DATA_ERROR', f"Invalid number format: {ve}", raw_data=row)
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
