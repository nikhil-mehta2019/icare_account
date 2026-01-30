"""Tally Service - Generates Tally-compatible XML export files.

Supports:
- Receipt vouchers (Credit entries / Income)
- Payment vouchers (Debit entries / Expenses)
- Purchase vouchers (with GST, TDS, RCM)
- Journal vouchers (adjustments)
- Payroll vouchers (salary payments)
"""

from datetime import datetime, date
from typing import List, Optional, Union
from xml.etree import ElementTree as ET
from xml.dom import minidom
import os

from models.voucher import Voucher, VoucherStatus
from models.account_head import VoucherType
from models.debit_voucher import (
    PurchaseVoucher, PayrollVoucher, JournalVoucher,
    GSTApplicability, TransactionType
)
from models.ledger_config import DebitVoucherConfig, GSTLedgerMapping, TDSLedgerMapping


class TallyXMLGenerator:
    """
    Generates Tally Prime compatible XML import files.
    
    XML Structure:
    <ENVELOPE>
      <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
      </HEADER>
      <BODY>
        <IMPORTDATA>
          <REQUESTDESC>
            <REPORTNAME>Vouchers</REPORTNAME>
            <STATICVARIABLES>
              <SVCURRENTCOMPANY>Company Name</SVCURRENTCOMPANY>
            </STATICVARIABLES>
          </REQUESTDESC>
          <REQUESTDATA>
            <TALLYMESSAGE>
              <VOUCHER>...</VOUCHER>
            </TALLYMESSAGE>
          </REQUESTDATA>
        </IMPORTDATA>
      </BODY>
    </ENVELOPE>
    """
    
    def __init__(self, company_name: str = "iCare Life", config: DebitVoucherConfig = None):
        """Initialize the XML generator."""
        self.company_name = company_name
        self.config = config or DebitVoucherConfig.create_default()
        self.gst_mapping = self.config.gst_mapping
        self.tds_mapping = self.config.tds_mapping
    
    def generate_xml(self, 
                     vouchers: List[Union[Voucher, PurchaseVoucher, PayrollVoucher, JournalVoucher]],
                     output_path: str,
                     start_date: datetime = None,
                     end_date: datetime = None) -> str:
        """
        Generate Tally XML import file from vouchers.
        
        Args:
            vouchers: List of vouchers (can be mixed types)
            output_path: Path for output XML file
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            Path to generated XML file
        """
        # Create root envelope
        root = self._create_envelope()
        
        # Get request data element
        request_data = root.find('.//REQUESTDATA')
        
        # Add vouchers based on type
        for voucher in vouchers:
            if isinstance(voucher, PurchaseVoucher):
                self._add_purchase_voucher(request_data, voucher)
            elif isinstance(voucher, PayrollVoucher):
                self._add_payroll_voucher(request_data, voucher)
            elif isinstance(voucher, JournalVoucher):
                self._add_journal_voucher(request_data, voucher)
            elif isinstance(voucher, Voucher):
                self._add_simple_voucher(request_data, voucher)
        
        # Format and save
        xml_string = self._prettify_xml(root)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(xml_string)
        
        return output_path
    
    def _create_envelope(self) -> ET.Element:
        """Create the XML envelope structure."""
        root = ET.Element('ENVELOPE')
        
        # Header
        header = ET.SubElement(root, 'HEADER')
        tally_request = ET.SubElement(header, 'TALLYREQUEST')
        tally_request.text = 'Import Data'
        
        # Body
        body = ET.SubElement(root, 'BODY')
        import_data = ET.SubElement(body, 'IMPORTDATA')
        
        # Request descriptor
        request_desc = ET.SubElement(import_data, 'REQUESTDESC')
        report_name = ET.SubElement(request_desc, 'REPORTNAME')
        report_name.text = 'Vouchers'
        
        static_vars = ET.SubElement(request_desc, 'STATICVARIABLES')
        company = ET.SubElement(static_vars, 'SVCURRENTCOMPANY')
        company.text = self.company_name
        
        # Request data (where vouchers go)
        ET.SubElement(import_data, 'REQUESTDATA')
        
        return root
    
    def _add_simple_voucher(self, parent: ET.Element, voucher: Voucher) -> None:
        """Add a simple Receipt/Payment voucher."""
        tall_msg = ET.SubElement(parent, 'TALLYMESSAGE')
        tall_msg.set('xmlns:UDF', 'TallyUDF')
        
        vch = ET.SubElement(tall_msg, 'VOUCHER')
        vch.set('VCHTYPE', voucher.tally_voucher_type)
        vch.set('ACTION', 'Create')
        vch.set('OBJVIEW', 'Accounting Voucher View')
        
        # Basic fields
        self._add_element(vch, 'DATE', self._format_date(voucher.date))
        self._add_element(vch, 'VOUCHERTYPENAME', voucher.tally_voucher_type)
        self._add_element(vch, 'NARRATION', voucher.narration)
        
        if voucher.reference_id:
            self._add_element(vch, 'REFERENCE', voucher.reference_id)
        
        # Period dates if available
        if hasattr(voucher, 'from_date') and voucher.from_date:
            self._add_element(vch, 'EFFECTIVEDATE', self._format_date(voucher.from_date))
        
        # Single ledger entry for simple vouchers
        ledger_entry = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
        self._add_element(ledger_entry, 'LEDGERNAME', voucher.account_name)
        self._add_element(ledger_entry, 'ISDEEMEDPOSITIVE', 'Yes' if voucher.is_credit else 'No')
        
        # Credits are negative in Tally
        amount = -voucher.amount if voucher.is_credit else voucher.amount
        self._add_element(ledger_entry, 'AMOUNT', str(amount))
    
    def _add_purchase_voucher(self, parent: ET.Element, voucher: PurchaseVoucher) -> None:
        """
        Add a Purchase voucher with GST, TDS, and RCM handling.
        
        Generates proper double-entry with:
        - Debit: Expense/Asset account
        - Debit: Input GST accounts (for normal GST)
        - Credit: Supplier account
        - Credit: TDS Payable (if applicable)
        - For RCM: Output GST entries as well
        """
        tall_msg = ET.SubElement(parent, 'TALLYMESSAGE')
        tall_msg.set('xmlns:UDF', 'TallyUDF')
        
        vch = ET.SubElement(tall_msg, 'VOUCHER')
        vch.set('VCHTYPE', 'Purchase')
        vch.set('ACTION', 'Create')
        vch.set('OBJVIEW', 'Accounting Voucher View')
        
        # Basic fields
        self._add_element(vch, 'DATE', self._format_date(voucher.voucher_date))
        self._add_element(vch, 'VOUCHERTYPENAME', 'Purchase')
        self._add_element(vch, 'VOUCHERNUMBER', voucher.voucher_no)
        self._add_element(vch, 'NARRATION', voucher.narration)
        self._add_element(vch, 'PARTYLEDGERNAME', voucher.supplier_ledger)
        
        if voucher.invoice_no:
            self._add_element(vch, 'REFERENCE', voucher.invoice_no)
        
        if voucher.invoice_date:
            self._add_element(vch, 'REFERENCEDATE', self._format_date(voucher.invoice_date))
        
        gst = voucher.gst
        tds = voucher.tds
        
        # === DEBIT ENTRIES ===
        
        # 1. Debit Expense/Asset account (Base Amount)
        expense_entry = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
        self._add_element(expense_entry, 'LEDGERNAME', voucher.expense_ledger)
        self._add_element(expense_entry, 'ISDEEMEDPOSITIVE', 'Yes')
        self._add_element(expense_entry, 'AMOUNT', str(-voucher.base_amount))  # Debit is negative
        
        if voucher.cost_centre:
            cc_alloc = ET.SubElement(expense_entry, 'CATEGORYALLOCATIONS.LIST')
            self._add_element(cc_alloc, 'CATEGORY', 'Primary Cost Category')
            self._add_element(cc_alloc, 'ISDEEMEDPOSITIVE', 'Yes')
            self._add_element(cc_alloc, 'COSTCENTREALLOCATIONS.LIST')
            cc = ET.SubElement(cc_alloc, 'COSTCENTREALLOCATIONS.LIST')
            self._add_element(cc, 'NAME', voucher.cost_centre)
            self._add_element(cc, 'AMOUNT', str(-voucher.base_amount))
        
        # 2. Debit Input GST accounts (for Normal GST)
        if gst.applicability == GSTApplicability.NORMAL:
            if gst.transaction_type == TransactionType.INTRA_STATE:
                # CGST
                if gst.cgst_amount > 0:
                    cgst_entry = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
                    self._add_element(cgst_entry, 'LEDGERNAME', gst.input_cgst_ledger or self.gst_mapping.input_cgst)
                    self._add_element(cgst_entry, 'ISDEEMEDPOSITIVE', 'Yes')
                    self._add_element(cgst_entry, 'AMOUNT', str(-gst.cgst_amount))
                
                # SGST
                if gst.sgst_amount > 0:
                    sgst_entry = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
                    self._add_element(sgst_entry, 'LEDGERNAME', gst.input_sgst_ledger or self.gst_mapping.input_sgst)
                    self._add_element(sgst_entry, 'ISDEEMEDPOSITIVE', 'Yes')
                    self._add_element(sgst_entry, 'AMOUNT', str(-gst.sgst_amount))
            
            elif gst.transaction_type == TransactionType.INTER_STATE:
                # IGST
                if gst.igst_amount > 0:
                    igst_entry = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
                    self._add_element(igst_entry, 'LEDGERNAME', gst.input_igst_ledger or self.gst_mapping.input_igst)
                    self._add_element(igst_entry, 'ISDEEMEDPOSITIVE', 'Yes')
                    self._add_element(igst_entry, 'AMOUNT', str(-gst.igst_amount))
        
        # 3. For RCM: Debit Input GST + Credit Output GST (same amount, net zero)
        elif gst.applicability == GSTApplicability.RCM:
            if gst.transaction_type == TransactionType.INTRA_STATE:
                # Debit Input CGST
                if gst.rcm_cgst_amount > 0:
                    rcm_cgst_in = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
                    self._add_element(rcm_cgst_in, 'LEDGERNAME', self.gst_mapping.input_cgst)
                    self._add_element(rcm_cgst_in, 'ISDEEMEDPOSITIVE', 'Yes')
                    self._add_element(rcm_cgst_in, 'AMOUNT', str(-gst.rcm_cgst_amount))
                    
                    # Credit Output CGST (RCM)
                    rcm_cgst_out = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
                    self._add_element(rcm_cgst_out, 'LEDGERNAME', gst.rcm_output_cgst_ledger or self.gst_mapping.output_cgst_rcm)
                    self._add_element(rcm_cgst_out, 'ISDEEMEDPOSITIVE', 'No')
                    self._add_element(rcm_cgst_out, 'AMOUNT', str(gst.rcm_cgst_amount))
                
                # Debit Input SGST
                if gst.rcm_sgst_amount > 0:
                    rcm_sgst_in = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
                    self._add_element(rcm_sgst_in, 'LEDGERNAME', self.gst_mapping.input_sgst)
                    self._add_element(rcm_sgst_in, 'ISDEEMEDPOSITIVE', 'Yes')
                    self._add_element(rcm_sgst_in, 'AMOUNT', str(-gst.rcm_sgst_amount))
                    
                    # Credit Output SGST (RCM)
                    rcm_sgst_out = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
                    self._add_element(rcm_sgst_out, 'LEDGERNAME', gst.rcm_output_sgst_ledger or self.gst_mapping.output_sgst_rcm)
                    self._add_element(rcm_sgst_out, 'ISDEEMEDPOSITIVE', 'No')
                    self._add_element(rcm_sgst_out, 'AMOUNT', str(gst.rcm_sgst_amount))
            
            elif gst.transaction_type == TransactionType.INTER_STATE:
                # Debit Input IGST
                if gst.rcm_igst_amount > 0:
                    rcm_igst_in = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
                    self._add_element(rcm_igst_in, 'LEDGERNAME', self.gst_mapping.input_igst)
                    self._add_element(rcm_igst_in, 'ISDEEMEDPOSITIVE', 'Yes')
                    self._add_element(rcm_igst_in, 'AMOUNT', str(-gst.rcm_igst_amount))
                    
                    # Credit Output IGST (RCM)
                    rcm_igst_out = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
                    self._add_element(rcm_igst_out, 'LEDGERNAME', gst.rcm_output_igst_ledger or self.gst_mapping.output_igst_rcm)
                    self._add_element(rcm_igst_out, 'ISDEEMEDPOSITIVE', 'No')
                    self._add_element(rcm_igst_out, 'AMOUNT', str(gst.rcm_igst_amount))
        
        # === CREDIT ENTRIES ===
        
        # 4. Credit Supplier account (Net Payable = Base + GST - TDS)
        supplier_entry = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
        self._add_element(supplier_entry, 'LEDGERNAME', voucher.supplier_ledger)
        self._add_element(supplier_entry, 'ISDEEMEDPOSITIVE', 'No')
        self._add_element(supplier_entry, 'AMOUNT', str(voucher.net_payable))  # Credit is positive
        
        # 5. Credit TDS Payable (if applicable)
        if tds.applicable and tds.amount > 0:
            tds_entry = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
            tds_ledger = tds.ledger or self.tds_mapping.get_ledger(tds.section.value)
            self._add_element(tds_entry, 'LEDGERNAME', tds_ledger)
            self._add_element(tds_entry, 'ISDEEMEDPOSITIVE', 'No')
            self._add_element(tds_entry, 'AMOUNT', str(tds.amount))  # Credit is positive
    
    def _add_payroll_voucher(self, parent: ET.Element, voucher: PayrollVoucher) -> None:
        """
        Add a Payroll voucher.
        
        Generates:
        - Debit: Salary account
        - Credit: Employee/Party account
        - Credit: TDS Payable (if applicable)
        """
        tall_msg = ET.SubElement(parent, 'TALLYMESSAGE')
        tall_msg.set('xmlns:UDF', 'TallyUDF')
        
        vch = ET.SubElement(tall_msg, 'VOUCHER')
        vch.set('VCHTYPE', 'Payment')
        vch.set('ACTION', 'Create')
        vch.set('OBJVIEW', 'Accounting Voucher View')
        
        # Basic fields
        self._add_element(vch, 'DATE', self._format_date(voucher.voucher_date))
        self._add_element(vch, 'VOUCHERTYPENAME', 'Payment')
        self._add_element(vch, 'VOUCHERNUMBER', voucher.voucher_no)
        self._add_element(vch, 'NARRATION', voucher.narration)
        
        if voucher.month_period:
            self._add_element(vch, 'REFERENCE', voucher.month_period)
        
        # Debit Salary account
        salary_entry = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
        self._add_element(salary_entry, 'LEDGERNAME', voucher.salary_ledger)
        self._add_element(salary_entry, 'ISDEEMEDPOSITIVE', 'Yes')
        self._add_element(salary_entry, 'AMOUNT', str(-voucher.amount))  # Debit is negative
        
        # Credit Employee/Party account
        party_entry = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
        self._add_element(party_entry, 'LEDGERNAME', voucher.party_ledger)
        self._add_element(party_entry, 'ISDEEMEDPOSITIVE', 'No')
        self._add_element(party_entry, 'AMOUNT', str(voucher.net_payable))  # Credit is positive
        
        # Credit TDS if applicable
        if voucher.tds.applicable and voucher.tds.amount > 0:
            tds_entry = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
            tds_ledger = voucher.tds.ledger or self.tds_mapping.get_ledger(voucher.tds.section.value)
            self._add_element(tds_entry, 'LEDGERNAME', tds_ledger)
            self._add_element(tds_entry, 'ISDEEMEDPOSITIVE', 'No')
            self._add_element(tds_entry, 'AMOUNT', str(voucher.tds.amount))
    
    def _add_journal_voucher(self, parent: ET.Element, voucher: JournalVoucher) -> None:
        """
        Add a Journal voucher with multiple entries.
        """
        tall_msg = ET.SubElement(parent, 'TALLYMESSAGE')
        tall_msg.set('xmlns:UDF', 'TallyUDF')
        
        vch = ET.SubElement(tall_msg, 'VOUCHER')
        vch.set('VCHTYPE', 'Journal')
        vch.set('ACTION', 'Create')
        vch.set('OBJVIEW', 'Accounting Voucher View')
        
        # Basic fields
        self._add_element(vch, 'DATE', self._format_date(voucher.voucher_date))
        self._add_element(vch, 'VOUCHERTYPENAME', 'Journal')
        self._add_element(vch, 'VOUCHERNUMBER', voucher.voucher_no)
        self._add_element(vch, 'NARRATION', voucher.narration)
        
        # Add all entries
        for entry in voucher.entries:
            ledger_entry = ET.SubElement(vch, 'ALLLEDGERENTRIES.LIST')
            self._add_element(ledger_entry, 'LEDGERNAME', entry.ledger)
            
            if entry.is_debit:
                self._add_element(ledger_entry, 'ISDEEMEDPOSITIVE', 'Yes')
                self._add_element(ledger_entry, 'AMOUNT', str(-entry.amount))  # Debit is negative
            else:
                self._add_element(ledger_entry, 'ISDEEMEDPOSITIVE', 'No')
                self._add_element(ledger_entry, 'AMOUNT', str(entry.amount))  # Credit is positive
    
    def _add_element(self, parent: ET.Element, tag: str, text: str) -> ET.Element:
        """Add a child element with text."""
        elem = ET.SubElement(parent, tag)
        elem.text = text
        return elem
    
    def _format_date(self, d: Union[datetime, date]) -> str:
        """Format date as Tally date (YYYYMMDD)."""
        if isinstance(d, datetime):
            return d.strftime('%Y%m%d')
        elif isinstance(d, date):
            return d.strftime('%Y%m%d')
        return str(d)
    
    def _prettify_xml(self, elem: ET.Element) -> str:
        """Return a pretty-printed XML string."""
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent='  ')
    
    def validate_xml(self, filepath: str) -> tuple:
        """
        Validate generated XML file.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            
            # Basic structure validation
            if root.tag != 'ENVELOPE':
                return (False, "Root element must be ENVELOPE")
            
            vouchers = root.findall('.//VOUCHER')
            if not vouchers:
                return (False, "No vouchers found in XML")
            
            # Validate each voucher has required elements
            for i, vch in enumerate(vouchers, 1):
                if vch.find('DATE') is None:
                    return (False, f"Voucher {i}: Missing DATE element")
                if vch.find('VOUCHERTYPENAME') is None:
                    return (False, f"Voucher {i}: Missing VOUCHERTYPENAME element")
                
                entries = vch.findall('ALLLEDGERENTRIES.LIST')
                if not entries:
                    return (False, f"Voucher {i}: No ledger entries")
            
            return (True, f"Valid XML with {len(vouchers)} voucher(s)")
        
        except ET.ParseError as e:
            return (False, f"XML Parse Error: {str(e)}")
        except Exception as e:
            return (False, f"Validation Error: {str(e)}")


class TallyService:
    """
    High-level Tally service for the application.
    Wraps TallyXMLGenerator with convenience methods.
    """
    
    def __init__(self, company_name: str = "iCare Life"):
        """Initialize Tally service."""
        self.company_name = company_name
        self.config = DebitVoucherConfig.create_default()
        self.generator = TallyXMLGenerator(company_name, self.config)
    
    def set_config(self, config: DebitVoucherConfig):
        """Update configuration."""
        self.config = config
        self.generator = TallyXMLGenerator(self.company_name, config)
    
    def export_vouchers(self, vouchers: List[Voucher], output_path: str) -> dict:
        """
        Export simple vouchers to Tally XML.
        
        Returns:
            dict with export results
        """
        try:
            # Filter by status
            exportable = [v for v in vouchers if v.status in 
                         [VoucherStatus.APPROVED, VoucherStatus.PENDING_REVIEW]]
            
            if not exportable:
                return {
                    'success': False,
                    'error': 'No exportable vouchers (need Approved or Pending Review status)',
                    'exported_count': 0
                }
            
            self.generator.generate_xml(exportable, output_path)
            is_valid, msg = self.generator.validate_xml(output_path)
            
            return {
                'success': is_valid,
                'filepath': output_path,
                'exported_count': len(exportable),
                'validation_message': msg
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'exported_count': 0
            }
    
    def export_purchase_vouchers(self, vouchers: List[PurchaseVoucher], output_path: str) -> dict:
        """Export purchase vouchers to Tally XML."""
        try:
            self.generator.generate_xml(vouchers, output_path)
            is_valid, msg = self.generator.validate_xml(output_path)
            
            return {
                'success': is_valid,
                'filepath': output_path,
                'exported_count': len(vouchers),
                'validation_message': msg
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'exported_count': 0
            }
    
    def export_payroll_vouchers(self, vouchers: List[PayrollVoucher], output_path: str) -> dict:
        """Export payroll vouchers to Tally XML."""
        try:
            self.generator.generate_xml(vouchers, output_path)
            is_valid, msg = self.generator.validate_xml(output_path)
            
            return {
                'success': is_valid,
                'filepath': output_path,
                'exported_count': len(vouchers),
                'validation_message': msg
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'exported_count': 0
            }
    
    def export_journal_vouchers(self, vouchers: List[JournalVoucher], output_path: str) -> dict:
        """Export journal vouchers to Tally XML."""
        try:
            # Validate all journals are balanced
            unbalanced = [v for v in vouchers if not v.is_balanced]
            if unbalanced:
                return {
                    'success': False,
                    'error': f'{len(unbalanced)} journal voucher(s) are not balanced',
                    'exported_count': 0
                }
            
            self.generator.generate_xml(vouchers, output_path)
            is_valid, msg = self.generator.validate_xml(output_path)
            
            return {
                'success': is_valid,
                'filepath': output_path,
                'exported_count': len(vouchers),
                'validation_message': msg
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'exported_count': 0
            }
    
    def generate_transfer_jv(self, old_head: str, new_head: str, 
                            amount: float, vdate: datetime = None) -> str:
        """
        Generate a Transfer Journal Voucher XML for renamed account heads.
        
        Returns XML string for the transfer JV.
        """
        if vdate is None:
            vdate = datetime.now()
        
        root = self.generator._create_envelope()
        request_data = root.find('.//REQUESTDATA')
        
        # Create journal voucher
        jv = JournalVoucher(
            voucher_no=f"TRF-{vdate.strftime('%Y%m%d')}-001",
            voucher_date=vdate,
            narration=f"Transfer from {old_head} to {new_head} - Head Rename"
        )
        jv.add_debit(new_head, amount)
        jv.add_credit(old_head, amount)
        
        self.generator._add_journal_voucher(request_data, jv)
        
        return self.generator._prettify_xml(root)
    
    def validate_xml(self, filepath: str) -> tuple:
        """Validate an XML file."""
        return self.generator.validate_xml(filepath)
