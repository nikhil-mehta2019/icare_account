"""Debit Voucher Import Service - Handles Purchase, Payroll, Journal imports."""

import csv
import os
import math
import pandas as pd  # Required for Excel support
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
    """
    
    # Existing Mappings...
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
    
    PAYROLL_COST_COLUMNS = {
        'segment': ['Business Segment', 'Segment'],
        'product': ['Product Code'],
        'location': ['Location'],
        'amount': ['Amount', 'Base Amount'],  # Base Gross Salary
        'emp_pf': ['Employee Share of PF Payable'],
        'employer_pf': ['Employer Share of PF Payable'],
        'emp_esic': ['Employee Share of ESIC Payable'],
        'employer_esic': ['Employer Share of ESIC Payable'],
        'pt': ['Professional Tax Payable'],
        'tds': ['TDS on Salary Payable - FY 2026-27', 'TDS on Salary Payable', 'TDS'],
        'net_payable': ['Salary Payable', 'Net Payable']
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
        
        if isinstance(date_str, datetime):
            return date_str
            
        date_str = str(date_str).strip()
        
        if len(date_str) == 8 and date_str.isdigit():
            try:
                return datetime.strptime(date_str, '%Y%m%d')
            except ValueError:
                pass
        
        formats = ['%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']
        for fmt in formats:
            try:
                return datetime.strptime(date_str.split('T')[0].split(' ')[0], fmt)
            except ValueError:
                continue
        
        return datetime.now()
    
    def _parse_float(self, value: Union[str, float, int]) -> float:
        """Parse float from string or number, handling currency symbols and NaN."""
        if value is None:
            return 0.0
        
        if isinstance(value, float):
            if math.isnan(value):
                return 0.0
            return value
            
        if isinstance(value, int):
            return float(value)
            
        value = str(value).replace('₹', '').replace('$', '').replace(',', '').strip()
        if not value:
            return 0.0
            
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    # ... (Keep existing _parse_gst_applicability, _parse_transaction_type, _parse_tds_section helpers) ...
    def _parse_gst_applicability(self, value: str) -> GSTApplicability:
        if not value: return GSTApplicability.NOT_APPLICABLE
        value = str(value).strip().upper()
        if 'RCM' in value: return GSTApplicability.RCM
        elif 'NORMAL' in value or 'YES' in value: return GSTApplicability.NORMAL
        return GSTApplicability.NOT_APPLICABLE
    
    def _parse_transaction_type(self, value: str) -> TransactionType:
        if not value: return TransactionType.NOT_APPLICABLE
        value = str(value).strip().upper()
        if 'INTER' in value: return TransactionType.INTER_STATE
        elif 'INTRA' in value: return TransactionType.INTRA_STATE
        elif 'IMPORT' in value: return TransactionType.IMPORT
        return TransactionType.NOT_APPLICABLE
    
    def _parse_tds_section(self, ledger_name: str) -> TDSSection:
        if not ledger_name: return TDSSection.NONE
        ledger_name = str(ledger_name).upper()
        if '194C' in ledger_name: return TDSSection.TDS_194C
        elif '194I' in ledger_name: return TDSSection.TDS_194I
        elif '194J' in ledger_name: return TDSSection.TDS_194J
        elif '194H' in ledger_name: return TDSSection.TDS_194H
        elif '195' in ledger_name: return TDSSection.TDS_195
        elif '194A' in ledger_name: return TDSSection.TDS_194A
        return TDSSection.NONE

    # ... (Keep existing import_purchase_csv, import_payroll_csv, import_journal_csv methods AS IS) ...
    # Placeholder for brevity - ensure you keep the full code for these methods from previous versions
    def import_purchase_csv(self, filepath: str) -> Tuple[List[PurchaseVoucher], ImportResult]:
        return [], ImportResult("x", "x", ImportStatus.FAILED) # Placeholder
    
    def import_payroll_csv(self, filepath: str) -> Tuple[List[PayrollVoucher], ImportResult]:
         return [], ImportResult("x", "x", ImportStatus.FAILED) # Placeholder

    def import_journal_csv(self, filepath: str) -> Tuple[List[JournalVoucher], ImportResult]:
         return [], ImportResult("x", "x", ImportStatus.FAILED) # Placeholder

    def _process_payroll_rows(self, rows: List[Dict], result: ImportResult, voucher_date: datetime) -> List[JournalVoucher]:
        """Helper to process normalized rows for payroll cost."""
        vouchers = []
        
        col_map = {}
        if not rows:
            return []
            
        headers = list(rows[0].keys())
        result.column_headers = headers
        
        # Map columns
        for field, possible_names in self.PAYROLL_COST_COLUMNS.items():
            col = self._find_column(headers, possible_names)
            if col:
                col_map[field] = col
        
        # CRITICAL VALIDATION: Ensure required columns exist
        if 'segment' not in col_map or 'amount' not in col_map:
            missing = []
            if 'segment' not in col_map: missing.append("Business Segment")
            if 'amount' not in col_map: missing.append("Amount")
            result.status = ImportStatus.FAILED
            result.add_error(0, 'VALIDATION', f"Missing required columns: {', '.join(missing)}")
            return []

        # Create Consolidated JV
        jv = JournalVoucher(
            voucher_no=f"PAYROLL-{voucher_date.strftime('%b%Y').upper()}",
            voucher_date=voucher_date,
            narration=f"Payroll Cost for {voucher_date.strftime('%B %Y')}",
            status='Imported'
        )

        credits_map = {
            "Employee Share of PF Payable": 0.0,
            "Employer Share of PF Payable": 0.0,
            "Employee Share of ESIC Payable": 0.0,
            "Employer Share of ESIC Payable": 0.0,
            "Professional Tax Payable": 0.0,
            "TDS on Salary Payable": 0.0,
            "Salary Payable": 0.0
        }
        
        has_rows = False

        for row_num, row in enumerate(rows, start=1):
            # Skip empty rows or accounting entry footer
            segment_val = row.get(col_map.get('segment'), '')
            if not segment_val:
                continue
                
            # Stop if we hit the "Accounting Entry" section in data
            first_col = list(row.values())[0]
            if str(first_col).strip().startswith("Accounting Entry"):
                break
                
            has_rows = True
            result.total_rows += 1
            
            try:
                base_amount = self._parse_float(row.get(col_map.get('amount', ''), '0'))
                employer_pf = self._parse_float(row.get(col_map.get('employer_pf', ''), '0'))
                employer_esic = self._parse_float(row.get(col_map.get('employer_esic', ''), '0'))
                
                total_cost_debit = base_amount + employer_pf + employer_esic
                
                segment = str(row.get(col_map.get('segment', ''), ''))
                jv.add_debit(
                    ledger="Salary & Wages",
                    amount=total_cost_debit,
                    subcode=segment
                )
                
                credits_map["Employee Share of PF Payable"] += self._parse_float(row.get(col_map.get('emp_pf', ''), '0'))
                credits_map["Employer Share of PF Payable"] += employer_pf
                credits_map["Employee Share of ESIC Payable"] += self._parse_float(row.get(col_map.get('emp_esic', ''), '0'))
                credits_map["Employer Share of ESIC Payable"] += employer_esic
                credits_map["Professional Tax Payable"] += self._parse_float(row.get(col_map.get('pt', ''), '0'))
                credits_map["TDS on Salary Payable"] += self._parse_float(row.get(col_map.get('tds', ''), '0'))
                credits_map["Salary Payable"] += self._parse_float(row.get(col_map.get('net_payable', ''), '0'))
                
                result.successful_rows += 1
                
            except Exception as e:
                result.add_error(row_num, 'PARSE_ERROR', str(e))
        
        if has_rows:
            for ledger, amount in credits_map.items():
                if amount > 0:
                    jv.add_credit(ledger, amount)
            vouchers.append(jv)
        else:
            result.status = ImportStatus.FAILED
            result.add_error(0, 'NO_DATA', "No valid data rows found in file")
            
        return vouchers

    def import_payroll_cost_csv(self, filepath: str, voucher_date: datetime) -> Tuple[List[JournalVoucher], ImportResult]:
        """Import Payroll Cost from CSV or Excel."""
        result = ImportResult(
            filename=os.path.basename(filepath),
            import_type='Payroll Cost',
            status=ImportStatus.IN_PROGRESS
        )
        
        ext = os.path.splitext(filepath)[1].lower()
        rows = []
        preview_data = []
        
        try:
            if ext in ['.xlsx', '.xls']:
                # Read Excel
                df = pd.read_excel(filepath)
                df = df.dropna(how='all') 
                rows = df.to_dict('records')
                preview_data = rows[:10]
                
            else:
                # Read CSV
                with open(filepath, 'r', encoding='utf-8-sig') as f:
                    lines = f.readlines()
                    data_lines = []
                    for line in lines:
                        if "Accounting Entry" in line:
                            break
                        if line.strip():
                            data_lines.append(line)
                    
                    reader = csv.DictReader(data_lines)
                    rows = list(reader)
                    preview_data = rows[:10]

            vouchers = self._process_payroll_rows(rows, result, voucher_date)
            result.preview_data = preview_data
            result.complete()
            self._current_result = result
            return vouchers, result
            
        except Exception as e:
            result.status = ImportStatus.FAILED
            result.add_error(0, 'FILE_ERROR', str(e))
            result.complete()
            self._current_result = result
            return [], result
            
    def import_csv(self, filepath: str, voucher_type: DebitVoucherType) -> Tuple[List, ImportResult]:
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
        if voucher_type == DebitVoucherType.PURCHASE:
            return list(self.PURCHASE_COLUMNS.keys()) # Simplified return for template
        elif voucher_type == DebitVoucherType.PAYROLL:
            return list(self.PAYROLL_COLUMNS.keys())
        elif voucher_type == DebitVoucherType.JOURNAL:
            return list(self.JOURNAL_COLUMNS.keys())
        return []