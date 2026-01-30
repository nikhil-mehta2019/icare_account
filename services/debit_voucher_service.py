"""Debit Voucher Import Service - Handles Purchase, Payroll, Journal imports."""

import csv
import os
from datetime import datetime
from typing import List, Optional, Dict, Tuple, Union
from pathlib import Path

from models.debit_voucher import (
    DebitVoucherType, GSTApplicability, TransactionType, TDSSection,
    GSTConfig, TDSConfig, PurchaseVoucher, PayrollVoucher, JournalVoucher, JournalEntry
)
from models.ledger_config import DebitVoucherConfig
from models.import_result import ImportResult, ImportStatus


class DebitVoucherImportService:
    """
    Service for importing Debit Vouchers from CSV/Excel files.
    
    Supports three categories:
    - Purchase: GST + TDS + RCM scenarios
    - Payroll: Simple salary payments
    - Journal: Adjustments and transfers
    """
    
    # Column mappings for Purchase voucher CSV
    PURCHASE_COLUMNS = {
        'gst_applicability': ['GST Applicability', 'GST Type', 'GST'],
        'transaction_type': ['Inter-State / Intra - State / Import', 'Transaction Type', 'State Type'],
        'voucher_no': ['Voucher No', 'Voucher Number', 'VoucherNo'],
        'voucher_date': ['Voucher Date (YYYYMMDD)', 'Voucher Date', 'Date'],
        'supplier_ledger': ['Supplier Ledger', 'Supplier', 'Party Ledger', 'Party'],
        'invoice_no': ['Invoice No', 'Invoice Number', 'Bill No'],
        'invoice_date': ['Invoice Date (YYYYMMDD)', 'Invoice Date', 'Bill Date'],
        'expense_ledger': ['Expense / Asset Ledger', 'Expense Ledger', 'Ledger'],
        'cost_centre': ['Cost Centre', 'Cost Center', 'Department'],
        'base_amount': ['Base Amount', 'Amount', 'Net Amount'],
        'cgst_amount': ['CGST Amount', 'CGST'],
        'sgst_amount': ['SGST Amount', 'SGST'],
        'igst_amount': ['IGST Amount', 'IGST'],
        'input_cgst_ledger': ['Input CGST Ledger'],
        'input_sgst_ledger': ['Input SGST Ledger'],
        'input_igst_ledger': ['Input IGST Ledger'],
        'rcm_cgst_amount': ['RCM CGST Amount', 'RCM CGST'],
        'rcm_sgst_amount': ['RCM SGST Amount', 'RCM SGST'],
        'rcm_igst_amount': ['RCM IGST Amount', 'RCM IGST'],
        'rcm_output_cgst_ledger': ['RCM Output CGST Ledger'],
        'rcm_output_sgst_ledger': ['RCM Output SGST Ledger'],
        'rcm_output_igst_ledger': ['RCM Output IGST Ledger'],
        'tds_ledger': ['TDS Ledger', 'TDS Account'],
        'tds_amount': ['TDS Amount', 'TDS'],
        'narration': ['Voucher Narration', 'Narration', 'Description'],
        'from_location': ['From', 'From Location'],
        'to_location': ['To', 'To Location'],
        'business_unit': ['Business Unit', 'BU'],
    }
    
    # Column mappings for Payroll voucher CSV
    PAYROLL_COLUMNS = {
        'voucher_no': ['Voucher No', 'Voucher Number'],
        'voucher_date': ['Voucher Date', 'Date', 'Payment Date'],
        'party_ledger': ['Party / Employee Ledger', 'Employee', 'Party', 'Name'],
        'employee_id': ['Employee ID', 'Emp ID', 'ID'],
        'salary_ledger': ['Salary Ledger', 'Ledger', 'Account'],
        'salary_subcode': ['Subcode', 'Category', 'Type'],
        'amount': ['Amount', 'Salary Amount', 'Net Salary'],
        'month_period': ['Month / Period', 'Period', 'Month', 'Pay Period'],
        'tds_amount': ['TDS Amount', 'TDS'],
        'narration': ['Narration', 'Description', 'Remarks'],
    }
    
    # Column mappings for Journal voucher CSV
    JOURNAL_COLUMNS = {
        'voucher_no': ['Voucher No', 'JV No', 'Journal No'],
        'voucher_date': ['Date', 'Voucher Date', 'JV Date'],
        'debit_ledger': ['Debit Ledger', 'Dr Ledger', 'Debit Account'],
        'debit_subcode': ['Debit Subcode', 'Dr Subcode'],
        'credit_ledger': ['Credit Ledger', 'Cr Ledger', 'Credit Account'],
        'credit_subcode': ['Credit Subcode', 'Cr Subcode'],
        'amount': ['Amount', 'Value'],
        'narration': ['Narration', 'Description', 'Particulars'],
    }
    
    def __init__(self, config: DebitVoucherConfig = None):
        """Initialize with optional configuration."""
        self.config = config or DebitVoucherConfig.create_default()
        self._current_result: Optional[ImportResult] = None
    
    def _find_column(self, headers: List[str], possible_names: List[str]) -> Optional[str]:
        """Find matching column name from headers."""
        for name in possible_names:
            if name in headers:
                return name
            # Case-insensitive match
            for header in headers:
                if header.lower().strip() == name.lower().strip():
                    return header
        return None
    
    def _parse_date(self, date_str: str) -> datetime:
        """Parse date from various formats."""
        if not date_str:
            return datetime.now()
        
        date_str = str(date_str).strip()
        
        # Try YYYYMMDD format first (Excel template format)
        if len(date_str) == 8 and date_str.isdigit():
            try:
                return datetime.strptime(date_str, '%Y%m%d')
            except ValueError:
                pass
        
        # Try common formats
        formats = ['%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']
        for fmt in formats:
            try:
                return datetime.strptime(date_str.split('T')[0].split(' ')[0], fmt)
            except ValueError:
                continue
        
        return datetime.now()
    
    def _parse_float(self, value: str) -> float:
        """Parse float from string, handling currency symbols."""
        if not value:
            return 0.0
        value = str(value).replace('₹', '').replace('$', '').replace(',', '').strip()
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def _parse_gst_applicability(self, value: str) -> GSTApplicability:
        """Parse GST applicability from string."""
        if not value:
            return GSTApplicability.NOT_APPLICABLE
        value = str(value).strip().upper()
        if 'RCM' in value:
            return GSTApplicability.RCM
        elif 'NORMAL' in value or 'YES' in value:
            return GSTApplicability.NORMAL
        return GSTApplicability.NOT_APPLICABLE
    
    def _parse_transaction_type(self, value: str) -> TransactionType:
        """Parse transaction type from string."""
        if not value:
            return TransactionType.NOT_APPLICABLE
        value = str(value).strip().upper()
        if 'INTER' in value:
            return TransactionType.INTER_STATE
        elif 'INTRA' in value:
            return TransactionType.INTRA_STATE
        elif 'IMPORT' in value:
            return TransactionType.IMPORT
        return TransactionType.NOT_APPLICABLE
    
    def _parse_tds_section(self, ledger_name: str) -> TDSSection:
        """Parse TDS section from ledger name."""
        if not ledger_name:
            return TDSSection.NONE
        ledger_name = str(ledger_name).upper()
        if '194C' in ledger_name:
            return TDSSection.TDS_194C
        elif '194I' in ledger_name:
            return TDSSection.TDS_194I
        elif '194J' in ledger_name:
            return TDSSection.TDS_194J
        elif '194H' in ledger_name:
            return TDSSection.TDS_194H
        elif '195' in ledger_name:
            return TDSSection.TDS_195
        elif '194A' in ledger_name:
            return TDSSection.TDS_194A
        return TDSSection.NONE
    
    def import_purchase_csv(self, filepath: str) -> Tuple[List[PurchaseVoucher], ImportResult]:
        """
        Import Purchase vouchers from CSV.
        
        Supports all GST/TDS/RCM scenarios:
        - Normal GST (Inter-State: IGST, Intra-State: CGST+SGST)
        - GST + TDS
        - RCM (Reverse Charge)
        - GST + TDS + RCM
        - Asset/Expense purchases
        - Non-GST purchases
        """
        vouchers = []
        result = ImportResult(
            filename=os.path.basename(filepath),
            import_type='Purchase Voucher',
            status=ImportStatus.IN_PROGRESS
        )
        
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                result.column_headers = headers
                
                # Map columns
                col_map = {}
                for field, possible_names in self.PURCHASE_COLUMNS.items():
                    col = self._find_column(headers, possible_names)
                    if col:
                        col_map[field] = col
                
                for row_num, row in enumerate(reader, start=2):
                    result.total_rows += 1
                    
                    try:
                        # Parse GST configuration
                        gst_applicability = self._parse_gst_applicability(
                            row.get(col_map.get('gst_applicability', ''), '')
                        )
                        transaction_type = self._parse_transaction_type(
                            row.get(col_map.get('transaction_type', ''), '')
                        )
                        
                        # Build GST config
                        gst = GSTConfig(
                            applicability=gst_applicability,
                            transaction_type=transaction_type,
                            input_cgst_ledger=row.get(col_map.get('input_cgst_ledger', ''), 'Input CGST'),
                            input_sgst_ledger=row.get(col_map.get('input_sgst_ledger', ''), 'Input SGST'),
                            input_igst_ledger=row.get(col_map.get('input_igst_ledger', ''), 'Input IGST'),
                            cgst_amount=self._parse_float(row.get(col_map.get('cgst_amount', ''), '0')),
                            sgst_amount=self._parse_float(row.get(col_map.get('sgst_amount', ''), '0')),
                            igst_amount=self._parse_float(row.get(col_map.get('igst_amount', ''), '0')),
                            rcm_output_cgst_ledger=row.get(col_map.get('rcm_output_cgst_ledger', ''), 'Output CGST (RCM)'),
                            rcm_output_sgst_ledger=row.get(col_map.get('rcm_output_sgst_ledger', ''), 'Output SGST (RCM)'),
                            rcm_output_igst_ledger=row.get(col_map.get('rcm_output_igst_ledger', ''), 'Output IGST (RCM)'),
                            rcm_cgst_amount=self._parse_float(row.get(col_map.get('rcm_cgst_amount', ''), '0')),
                            rcm_sgst_amount=self._parse_float(row.get(col_map.get('rcm_sgst_amount', ''), '0')),
                            rcm_igst_amount=self._parse_float(row.get(col_map.get('rcm_igst_amount', ''), '0')),
                        )
                        
                        # Parse TDS
                        tds_ledger = row.get(col_map.get('tds_ledger', ''), '')
                        tds_amount = self._parse_float(row.get(col_map.get('tds_amount', ''), '0'))
                        tds_section = self._parse_tds_section(tds_ledger)
                        
                        tds = TDSConfig(
                            applicable=tds_amount > 0,
                            section=tds_section,
                            ledger=tds_ledger,
                            amount=tds_amount
                        )
                        
                        # Create voucher
                        voucher = PurchaseVoucher(
                            voucher_no=row.get(col_map.get('voucher_no', ''), ''),
                            voucher_date=self._parse_date(row.get(col_map.get('voucher_date', ''), '')),
                            supplier_ledger=row.get(col_map.get('supplier_ledger', ''), ''),
                            invoice_no=row.get(col_map.get('invoice_no', ''), ''),
                            invoice_date=self._parse_date(row.get(col_map.get('invoice_date', ''), '')),
                            expense_ledger=row.get(col_map.get('expense_ledger', ''), ''),
                            cost_centre=row.get(col_map.get('cost_centre', ''), ''),
                            base_amount=self._parse_float(row.get(col_map.get('base_amount', ''), '0')),
                            gst=gst,
                            tds=tds,
                            narration=row.get(col_map.get('narration', ''), ''),
                            from_location=row.get(col_map.get('from_location', ''), ''),
                            to_location=row.get(col_map.get('to_location', ''), ''),
                            business_unit=row.get(col_map.get('business_unit', ''), ''),
                            status='Imported'
                        )
                        
                        # Validate
                        if voucher.base_amount > 0 and voucher.supplier_ledger:
                            vouchers.append(voucher)
                            result.successful_rows += 1
                        else:
                            result.add_error(row_num, 'VALIDATION', 'Missing base amount or supplier')
                    
                    except Exception as e:
                        result.add_error(row_num, 'PARSE_ERROR', str(e))
                
                # Store preview
                result.preview_data = [row for row in csv.DictReader(open(filepath, 'r', encoding='utf-8-sig'))][:10]
        
        except Exception as e:
            result.status = ImportStatus.FAILED
            result.add_error(0, 'FILE_ERROR', str(e))
        
        result.complete()
        self._current_result = result
        return vouchers, result
    
    def import_payroll_csv(self, filepath: str) -> Tuple[List[PayrollVoucher], ImportResult]:
        """Import Payroll vouchers from CSV."""
        vouchers = []
        result = ImportResult(
            filename=os.path.basename(filepath),
            import_type='Payroll Voucher',
            status=ImportStatus.IN_PROGRESS
        )
        
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                result.column_headers = headers
                
                col_map = {}
                for field, possible_names in self.PAYROLL_COLUMNS.items():
                    col = self._find_column(headers, possible_names)
                    if col:
                        col_map[field] = col
                
                for row_num, row in enumerate(reader, start=2):
                    result.total_rows += 1
                    
                    try:
                        tds_amount = self._parse_float(row.get(col_map.get('tds_amount', ''), '0'))
                        tds = TDSConfig(
                            applicable=tds_amount > 0,
                            amount=tds_amount
                        )
                        
                        voucher = PayrollVoucher(
                            voucher_no=row.get(col_map.get('voucher_no', ''), ''),
                            voucher_date=self._parse_date(row.get(col_map.get('voucher_date', ''), '')),
                            party_ledger=row.get(col_map.get('party_ledger', ''), ''),
                            employee_id=row.get(col_map.get('employee_id', ''), ''),
                            salary_ledger=row.get(col_map.get('salary_ledger', ''), ''),
                            salary_subcode=row.get(col_map.get('salary_subcode', ''), ''),
                            amount=self._parse_float(row.get(col_map.get('amount', ''), '0')),
                            month_period=row.get(col_map.get('month_period', ''), ''),
                            tds=tds,
                            narration=row.get(col_map.get('narration', ''), ''),
                            status='Imported'
                        )
                        
                        if voucher.amount > 0 and voucher.party_ledger:
                            vouchers.append(voucher)
                            result.successful_rows += 1
                        else:
                            result.add_error(row_num, 'VALIDATION', 'Missing amount or party')
                    
                    except Exception as e:
                        result.add_error(row_num, 'PARSE_ERROR', str(e))
                
                result.preview_data = [row for row in csv.DictReader(open(filepath, 'r', encoding='utf-8-sig'))][:10]
        
        except Exception as e:
            result.status = ImportStatus.FAILED
            result.add_error(0, 'FILE_ERROR', str(e))
        
        result.complete()
        self._current_result = result
        return vouchers, result
    
    def import_journal_csv(self, filepath: str) -> Tuple[List[JournalVoucher], ImportResult]:
        """Import Journal vouchers from CSV."""
        vouchers = []
        result = ImportResult(
            filename=os.path.basename(filepath),
            import_type='Journal Voucher',
            status=ImportStatus.IN_PROGRESS
        )
        
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                result.column_headers = headers
                
                col_map = {}
                for field, possible_names in self.JOURNAL_COLUMNS.items():
                    col = self._find_column(headers, possible_names)
                    if col:
                        col_map[field] = col
                
                # Group by voucher number
                voucher_groups: Dict[str, List[dict]] = {}
                
                for row in reader:
                    voucher_no = row.get(col_map.get('voucher_no', ''), '')
                    if voucher_no:
                        if voucher_no not in voucher_groups:
                            voucher_groups[voucher_no] = []
                        voucher_groups[voucher_no].append(row)
                
                result.total_rows = sum(len(rows) for rows in voucher_groups.values())
                
                for voucher_no, rows in voucher_groups.items():
                    try:
                        first_row = rows[0]
                        jv = JournalVoucher(
                            voucher_no=voucher_no,
                            voucher_date=self._parse_date(first_row.get(col_map.get('voucher_date', ''), '')),
                            narration=first_row.get(col_map.get('narration', ''), ''),
                            status='Imported'
                        )
                        
                        for row in rows:
                            amount = self._parse_float(row.get(col_map.get('amount', ''), '0'))
                            debit_ledger = row.get(col_map.get('debit_ledger', ''), '')
                            credit_ledger = row.get(col_map.get('credit_ledger', ''), '')
                            
                            if debit_ledger and amount > 0:
                                jv.add_debit(
                                    debit_ledger,
                                    amount,
                                    row.get(col_map.get('debit_subcode', ''), '')
                                )
                            
                            if credit_ledger and amount > 0:
                                jv.add_credit(
                                    credit_ledger,
                                    amount,
                                    row.get(col_map.get('credit_subcode', ''), '')
                                )
                        
                        if jv.entries and jv.is_balanced:
                            vouchers.append(jv)
                            result.successful_rows += len(rows)
                        else:
                            result.add_error(0, 'VALIDATION', f'Journal {voucher_no} is not balanced')
                            result.failed_rows += len(rows)
                    
                    except Exception as e:
                        result.add_error(0, 'PARSE_ERROR', str(e))
                        result.failed_rows += len(rows)
                
                result.preview_data = [row for row in csv.DictReader(open(filepath, 'r', encoding='utf-8-sig'))][:10]
        
        except Exception as e:
            result.status = ImportStatus.FAILED
            result.add_error(0, 'FILE_ERROR', str(e))
        
        result.complete()
        self._current_result = result
        return vouchers, result
    
    def import_csv(self, filepath: str, voucher_type: DebitVoucherType) -> Tuple[List, ImportResult]:
        """
        Import CSV based on voucher type.
        
        Args:
            filepath: Path to CSV file
            voucher_type: Type of debit voucher (Purchase, Payroll, Journal)
        """
        if voucher_type == DebitVoucherType.PURCHASE:
            return self.import_purchase_csv(filepath)
        elif voucher_type == DebitVoucherType.PAYROLL:
            return self.import_payroll_csv(filepath)
        elif voucher_type == DebitVoucherType.JOURNAL:
            return self.import_journal_csv(filepath)
        else:
            result = ImportResult(
                filename=os.path.basename(filepath),
                import_type='Unknown',
                status=ImportStatus.FAILED
            )
            result.add_error(0, 'TYPE_ERROR', f'Unknown voucher type: {voucher_type}')
            return [], result
    
    def get_template_columns(self, voucher_type: DebitVoucherType) -> List[str]:
        """Get required column headers for template."""
        if voucher_type == DebitVoucherType.PURCHASE:
            return [
                'GST Applicability', 'Inter-State / Intra - State / Import',
                'Voucher No', 'Voucher Date (YYYYMMDD)', 'Supplier Ledger',
                'Invoice No', 'Invoice Date (YYYYMMDD)', 'Expense / Asset Ledger',
                'Cost Centre', 'Base Amount', 'Input CGST Ledger', 'CGST Amount',
                'Input SGST Ledger', 'SGST Amount', 'Input IGST Ledger', 'IGST Amount',
                'RCM Output CGST Ledger', 'RCM CGST Amount', 'RCM Output SGST Ledger',
                'RCM SGST Amount', 'RCM Output IGST Ledger', 'RCM IGST Amount',
                'TDS Ledger', 'TDS Amount', 'Voucher Narration'
            ]
        elif voucher_type == DebitVoucherType.PAYROLL:
            return [
                'Voucher No', 'Voucher Date', 'Party / Employee Ledger',
                'Employee ID', 'Salary Ledger', 'Subcode', 'Amount',
                'Month / Period', 'TDS Amount', 'Narration'
            ]
        elif voucher_type == DebitVoucherType.JOURNAL:
            return [
                'Voucher No', 'Date', 'Debit Ledger', 'Debit Subcode',
                'Credit Ledger', 'Credit Subcode', 'Amount', 'Narration'
            ]
        return []
