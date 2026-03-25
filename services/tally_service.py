"""Tally Service - Generates Tally-compatible XML export files from DB Rows."""

from datetime import datetime
from typing import List, Dict, Any
from xml.etree import ElementTree as ET
from xml.dom import minidom

class TallyVoucherType:
    JOURNAL = "Journal"
    PURCHASE = "Purchase"
    PAYMENT = "Payment"
    RECEIPT = "Receipt"

class TallyXMLGenerator:
    """Generates Tally Prime compatible XML import files using flat PostgreSQL dicts."""
    
    def __init__(self, company_name: str = "iCare Life"):
        self.company_name = company_name
    
    def generate_xml(self, db_vouchers: List[Dict[str, Any]], output_path: str) -> str:
        root = self._create_envelope()
        request_data = root.find('.//REQUESTDATA')
        
        for v in db_vouchers:
            try:
                v_type = str(v.get('voucher_type', '')).upper()
                
                if v_type == 'JOURNAL':
                    self._add_journal_voucher(request_data, v)
                elif v_type == 'PURCHASE':
                    self._add_purchase_voucher(request_data, v)
                elif v_type == 'PAYROLL':
                    self._add_payroll_voucher(request_data, v)
                else:
                    self._add_simple_voucher(request_data, v)
            except Exception as e:
                print(f"Skipping voucher {v.get('voucher_no')} error: {e}")
        
        xml_string = self._prettify_xml(root)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_string)
        return output_path

    def _create_envelope(self) -> ET.Element:
        root = ET.Element('ENVELOPE')
        header = ET.SubElement(root, 'HEADER')
        ET.SubElement(header, 'TALLYREQUEST').text = 'Import Data'
        body = ET.SubElement(root, 'BODY')
        imp = ET.SubElement(body, 'IMPORTDATA')
        req = ET.SubElement(imp, 'REQUESTDESC')
        ET.SubElement(req, 'REPORTNAME').text = 'Vouchers'
        static = ET.SubElement(req, 'STATICVARIABLES')
        ET.SubElement(static, 'SVCURRENTCOMPANY').text = self.company_name
        ET.SubElement(imp, 'REQUESTDATA')
        return root

    def _add_journal_voucher(self, parent: ET.Element, voucher: Dict):
        tall_msg = ET.SubElement(parent, 'TALLYMESSAGE')
        vch = ET.SubElement(tall_msg, 'VOUCHER')
        vch.set('VCHTYPE', TallyVoucherType.JOURNAL)
        vch.set('ACTION', 'Create')
        self._add_common_fields(vch, voucher, TallyVoucherType.JOURNAL)
        
        # Example of handling Dr/Cr for Journal based on amount sign or separate query
        # Assuming DB provides flat positive amounts and an is_credit flag, or similar.
        amt = float(voucher.get('amount', 0))
        ledger = voucher.get('account_code', 'Unknown Ledger')

        row = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
        self._add_elem(row, 'LEDGERNAME', ledger)
        self._add_elem(row, 'ISDEEMEDPOSITIVE', 'Yes')
        self._add_elem(row, 'AMOUNT', str(-amt))

    def _add_payroll_voucher(self, parent: ET.Element, voucher: Dict):
        tall_msg = ET.SubElement(parent, 'TALLYMESSAGE')
        vch = ET.SubElement(tall_msg, 'VOUCHER')
        vch.set('VCHTYPE', TallyVoucherType.PAYMENT)
        vch.set('ACTION', 'Create')
        self._add_common_fields(vch, voucher, TallyVoucherType.PAYMENT)

        amt = float(voucher.get('amount', 0))
        
        # Dr Salary Ledger (Using Account Code / Ledger Name)
        dr = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
        self._add_elem(dr, 'LEDGERNAME', voucher.get('account_code', 'Salary Account'))
        self._add_elem(dr, 'ISDEEMEDPOSITIVE', 'Yes')
        self._add_elem(dr, 'AMOUNT', str(-amt))

        # Cr Party/Bank Ledger
        cr = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
        self._add_elem(cr, 'LEDGERNAME', voucher.get('reference_id', 'Bank Account'))
        self._add_elem(cr, 'ISDEEMEDPOSITIVE', 'No')
        self._add_elem(cr, 'AMOUNT', str(amt)) 

    def _add_purchase_voucher(self, parent: ET.Element, voucher: Dict):
        tall_msg = ET.SubElement(parent, 'TALLYMESSAGE')
        vch = ET.SubElement(tall_msg, 'VOUCHER')
        vch.set('VCHTYPE', TallyVoucherType.PURCHASE)
        vch.set('ACTION', 'Create')
        self._add_common_fields(vch, voucher, TallyVoucherType.PURCHASE)
        
        ref = voucher.get('reference_id')
        if ref: self._add_elem(vch, 'REFERENCE', ref)

        base_amt = float(voucher.get('amount', 0))
        gst_amt = float(voucher.get('gst_amount', 0))
        total_amt = base_amt + gst_amt

        # Cr Supplier (Total Amount)
        cr = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
        self._add_elem(cr, 'LEDGERNAME', voucher.get('account_code', 'Supplier'))
        self._add_elem(cr, 'ISDEEMEDPOSITIVE', 'No')
        self._add_elem(cr, 'AMOUNT', str(total_amt))

        # Dr Expense (Base Amount)
        dr = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
        self._add_elem(dr, 'LEDGERNAME', 'Purchase Account')
        self._add_elem(dr, 'ISDEEMEDPOSITIVE', 'Yes')
        self._add_elem(dr, 'AMOUNT', str(-base_amt))
        
        # Dr GST (Tax Amount)
        if gst_amt > 0:
            tax = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
            self._add_elem(tax, 'LEDGERNAME', 'GST Input')
            self._add_elem(tax, 'ISDEEMEDPOSITIVE', 'Yes')
            self._add_elem(tax, 'AMOUNT', str(-gst_amt))

    def _add_simple_voucher(self, parent: ET.Element, voucher: Dict):
        tall_msg = ET.SubElement(parent, 'TALLYMESSAGE')
        vch = ET.SubElement(tall_msg, 'VOUCHER')
        v_type = voucher.get('voucher_type', TallyVoucherType.JOURNAL)
        
        # Normalize DB Type to Tally Type
        if 'CREDIT' in v_type: tally_type = TallyVoucherType.RECEIPT
        elif 'DEBIT' in v_type: tally_type = TallyVoucherType.PAYMENT
        else: tally_type = TallyVoucherType.JOURNAL

        vch.set('VCHTYPE', tally_type)
        vch.set('ACTION', 'Create')
        self._add_common_fields(vch, voucher, tally_type)
        
        row = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
        self._add_elem(row, 'LEDGERNAME', voucher.get('account_code', 'Unknown'))
        
        amt = float(voucher.get('amount', 0))
        
        if tally_type == TallyVoucherType.RECEIPT:
            self._add_elem(row, 'ISDEEMEDPOSITIVE', 'No')
            self._add_elem(row, 'AMOUNT', str(amt))
        else:
            self._add_elem(row, 'ISDEEMEDPOSITIVE', 'Yes')
            self._add_elem(row, 'AMOUNT', str(-amt))

    def _add_common_fields(self, vch, voucher: Dict, type_name: str):
        v_date = voucher.get('voucher_date')
        if isinstance(v_date, str):
            try: v_date = datetime.strptime(v_date.split('T')[0], "%Y-%m-%d").date()
            except: v_date = datetime.now().date()
        elif not v_date: 
            v_date = datetime.now().date()
            
        self._add_elem(vch, 'DATE', v_date.strftime('%Y%m%d'))
        self._add_elem(vch, 'VOUCHERTYPENAME', type_name)
        self._add_elem(vch, 'VOUCHERNUMBER', str(voucher.get('voucher_no', '')))
        
        narration = str(voucher.get('narration', '')).strip()
        self._add_elem(vch, 'NARRATION', narration)

    def _add_elem(self, parent, tag, text):
        elem = ET.SubElement(parent, tag)
        elem.text = str(text)

    def _prettify_xml(self, elem):
        rough = ET.tostring(elem, 'utf-8')
        reparsed = minidom.parseString(rough)
        return reparsed.toprettyxml(indent="  ")

class TallyService:
    """Service Wrapper connected to DataProvider via UI context."""
    def __init__(self, company_name="iCare Life"):
        self.generator = TallyXMLGenerator(company_name)
        
    def export_vouchers(self, db_vouchers: List[Dict], output_path: str) -> str:
        return self.generator.generate_xml(db_vouchers, output_path)