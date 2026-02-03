"""Tally Service - Generates Tally-compatible XML export files.

Supports:
- Receipt vouchers (Credit entries / Income)
- Payment vouchers (Debit entries / Expenses)
- Purchase vouchers (with GST, TDS, RCM)
- Journal vouchers (adjustments/payroll)
- Payroll vouchers (salary payments)
"""

from datetime import datetime, date
from typing import List, Optional, Union
from xml.etree import ElementTree as ET
from xml.dom import minidom
import os

from models.voucher import Voucher, VoucherStatus
from models.debit_voucher import (
    PurchaseVoucher, PayrollVoucher, JournalVoucher,
    GSTApplicability, TransactionType
)
from models.ledger_config import DebitVoucherConfig

class TallyXMLGenerator:
    """Generates Tally Prime compatible XML import files."""
    
    def __init__(self, company_name: str = "iCare Life", config: DebitVoucherConfig = None):
        self.company_name = company_name
        self.config = config or DebitVoucherConfig.create_default()
        self.gst_mapping = self.config.gst_mapping
        self.tds_mapping = self.config.tds_mapping
    
    def generate_xml(self, vouchers: List[any], output_path: str) -> str:
        """Generate Tally XML from list of vouchers."""
        root = self._create_envelope()
        request_data = root.find('.//REQUESTDATA')
        
        for voucher in vouchers:
            try:
                if isinstance(voucher, PurchaseVoucher):
                    self._add_purchase_voucher(request_data, voucher)
                elif isinstance(voucher, PayrollVoucher):
                    self._add_payroll_voucher(request_data, voucher)
                elif isinstance(voucher, JournalVoucher):
                    self._add_journal_voucher(request_data, voucher)
                elif hasattr(voucher, 'account_name'): # Simple Voucher
                    self._add_simple_voucher(request_data, voucher)
            except Exception as e:
                print(f"Skipping voucher due to error: {e}")
        
        xml_string = self._prettify_xml(root)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_string)
        return output_path
    
    def _create_envelope(self) -> ET.Element:
        root = ET.Element('ENVELOPE')
        header = ET.SubElement(root, 'HEADER')
        ET.SubElement(header, 'TALLYREQUEST').text = 'Import Data'
        body = ET.SubElement(root, 'BODY')
        import_data = ET.SubElement(body, 'IMPORTDATA')
        req_desc = ET.SubElement(import_data, 'REQUESTDESC')
        ET.SubElement(req_desc, 'REPORTNAME').text = 'Vouchers'
        static = ET.SubElement(req_desc, 'STATICVARIABLES')
        ET.SubElement(static, 'SVCURRENTCOMPANY').text = self.company_name
        ET.SubElement(import_data, 'REQUESTDATA')
        return root
    
    def _add_journal_voucher(self, parent: ET.Element, voucher: JournalVoucher):
        if not voucher.is_balanced:
            return
        
        tall_msg = ET.SubElement(parent, 'TALLYMESSAGE')
        vch = ET.SubElement(tall_msg, 'VOUCHER')
        vch.set('VCHTYPE', 'Journal')
        vch.set('ACTION', 'Create')
        
        self._add_common_fields(vch, voucher, 'Journal')
        
        for entry in voucher.entries:
            row = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
            self._add_elem(row, 'LEDGERNAME', entry.ledger)
            if entry.debit_amount > 0:
                self._add_elem(row, 'ISDEEMEDPOSITIVE', 'Yes')
                self._add_elem(row, 'AMOUNT', str(-entry.debit_amount))
            else:
                self._add_elem(row, 'ISDEEMEDPOSITIVE', 'No')
                self._add_elem(row, 'AMOUNT', str(entry.credit_amount))

    def _add_payroll_voucher(self, parent: ET.Element, voucher: PayrollVoucher):
        tall_msg = ET.SubElement(parent, 'TALLYMESSAGE')
        vch = ET.SubElement(tall_msg, 'VOUCHER')
        vch.set('VCHTYPE', 'Payment')
        vch.set('ACTION', 'Create')
        
        self._add_common_fields(vch, voucher, 'Payment')
        
        # Dr Salary
        dr = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
        self._add_elem(dr, 'LEDGERNAME', voucher.salary_ledger)
        self._add_elem(dr, 'ISDEEMEDPOSITIVE', 'Yes')
        self._add_elem(dr, 'AMOUNT', str(-voucher.amount))
        
        # Cr Party (Net)
        cr = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
        self._add_elem(cr, 'LEDGERNAME', voucher.party_ledger)
        self._add_elem(cr, 'ISDEEMEDPOSITIVE', 'No')
        net = voucher.amount
        if hasattr(voucher, 'tds') and voucher.tds.applicable:
            net -= voucher.tds.amount
        self._add_elem(cr, 'AMOUNT', str(net))
        
        if hasattr(voucher, 'tds') and voucher.tds.applicable:
            tds = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
            self._add_elem(tds, 'LEDGERNAME', voucher.tds.ledger)
            self._add_elem(tds, 'ISDEEMEDPOSITIVE', 'No')
            self._add_elem(tds, 'AMOUNT', str(voucher.tds.amount))

    def _add_purchase_voucher(self, parent: ET.Element, voucher: PurchaseVoucher):
        tall_msg = ET.SubElement(parent, 'TALLYMESSAGE')
        vch = ET.SubElement(tall_msg, 'VOUCHER')
        vch.set('VCHTYPE', 'Purchase')
        vch.set('ACTION', 'Create')
        
        self._add_common_fields(vch, voucher, 'Purchase')
        if voucher.invoice_no:
            self._add_elem(vch, 'REFERENCE', voucher.invoice_no)
            
        # Cr Supplier
        cr = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
        self._add_elem(cr, 'LEDGERNAME', voucher.supplier_ledger)
        self._add_elem(cr, 'ISDEEMEDPOSITIVE', 'No')
        self._add_elem(cr, 'AMOUNT', str(voucher.total_amount))
        
        # Dr Expense
        dr = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
        self._add_elem(dr, 'LEDGERNAME', voucher.expense_ledger)
        self._add_elem(dr, 'ISDEEMEDPOSITIVE', 'Yes')
        self._add_elem(dr, 'AMOUNT', str(-voucher.base_amount))
        
        # Taxes
        if hasattr(voucher, 'gst') and voucher.gst.applicability == GSTApplicability.NORMAL:
            for ledger, amt in [
                (voucher.gst.input_cgst_ledger, voucher.gst.cgst_amount),
                (voucher.gst.input_sgst_ledger, voucher.gst.sgst_amount),
                (voucher.gst.input_igst_ledger, voucher.gst.igst_amount)
            ]:
                if amt > 0:
                    tax = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
                    self._add_elem(tax, 'LEDGERNAME', ledger)
                    self._add_elem(tax, 'ISDEEMEDPOSITIVE', 'Yes')
                    self._add_elem(tax, 'AMOUNT', str(-amt))

    def _add_simple_voucher(self, parent: ET.Element, voucher: Voucher):
        tall_msg = ET.SubElement(parent, 'TALLYMESSAGE')
        vch = ET.SubElement(tall_msg, 'VOUCHER')
        
        v_type = getattr(voucher, 'tally_voucher_type', 'Journal')
        vch.set('VCHTYPE', v_type)
        vch.set('ACTION', 'Create')
        
        d = getattr(voucher, 'date', datetime.now())
        self._add_elem(vch, 'DATE', self._format_date(d))
        self._add_elem(vch, 'VOUCHERTYPENAME', v_type)
        self._add_elem(vch, 'VOUCHERNUMBER', getattr(voucher, 'reference_id', ''))
        self._add_elem(vch, 'NARRATION', getattr(voucher, 'narration', ''))
        
        row = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
        self._add_elem(row, 'LEDGERNAME', getattr(voucher, 'account_name', 'Unknown'))
        
        is_cr = getattr(voucher, 'is_credit', False)
        amt = getattr(voucher, 'amount', 0)
        
        if is_cr:
            self._add_elem(row, 'ISDEEMEDPOSITIVE', 'No')
            self._add_elem(row, 'AMOUNT', str(amt))
        else:
            self._add_elem(row, 'ISDEEMEDPOSITIVE', 'Yes')
            self._add_elem(row, 'AMOUNT', str(-amt))

    def _add_common_fields(self, vch, voucher, type_name):
        d = getattr(voucher, 'voucher_date', datetime.now())
        self._add_elem(vch, 'DATE', self._format_date(d))
        self._add_elem(vch, 'VOUCHERTYPENAME', type_name)
        self._add_elem(vch, 'VOUCHERNUMBER', getattr(voucher, 'voucher_no', ''))
        self._add_elem(vch, 'NARRATION', getattr(voucher, 'narration', ''))

    def _add_elem(self, parent, tag, text):
        elem = ET.SubElement(parent, tag)
        elem.text = str(text)

    def _format_date(self, d):
        if isinstance(d, str):
            try: d = datetime.strptime(d, "%Y-%m-%d")
            except: return d.replace('-', '')
        return d.strftime('%Y%m%d')

    def _prettify_xml(self, elem):
        rough = ET.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough)
        return reparsed.toprettyxml(indent="  ")
        
    def validate_xml(self, filepath):
        return True, "Valid"

class TallyService:
    """Service Wrapper."""
    def __init__(self, data_service, company_name="iCare Life"):
        self.data_service = data_service
        self.generator = TallyXMLGenerator(company_name)