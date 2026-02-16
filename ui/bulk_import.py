from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QMessageBox,
    QTableWidget, QTableWidgetItem, QFileDialog,
    QDateEdit, QScrollArea, QHeaderView, QLineEdit,
    QComboBox, QStackedWidget, QFrame
)
from PySide6.QtCore import Qt, Signal, QDate
from datetime import datetime, time, timedelta
import os
import math
import csv

# Services & Models
from services.debit_voucher_service import DebitVoucherImportService
from services.data_service import DataService
from services.voucher_config_service import get_voucher_config
from models.import_result import ImportResult, ImportStatus
from models.voucher import Voucher, VoucherStatus
from models.account_head import VoucherType
from .styles import Styles
from types import SimpleNamespace

class BulkImportTab(QWidget):
    """
    Unified Bulk Import Tab
    Modes:
    1. Payroll Cost (Debit) - Existing logic
    2. Sales Income (Credit) - New logic per functional spec
    """

    import_completed = Signal(ImportResult)

    def __init__(self, data_service: DataService, parent=None):
        super().__init__(parent)
        self.data_service = data_service
        self.config = get_voucher_config()
        self.payroll_service = DebitVoucherImportService()

        self._current_file = None
        self._import_result = None
        self._vouchers = []
        self._mode = "PAYROLL" # PAYROLL or SALES

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        # 1. Header with Mode Switch
        layout.addWidget(self._create_header_section())

        # 2. Configuration Section (Dynamic)
        layout.addWidget(self._create_config_section())

        # 3. Upload Section
        layout.addWidget(self._create_upload_section())

        # 4. Preview Section
        layout.addWidget(self._create_preview_section())
        
        # 5. Actions
        layout.addLayout(self._create_action_buttons())
        layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
        # Initialize State
        self._update_ui_for_mode()

    def _create_header_section(self):
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel("Import Mode:")
        label.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {Styles.SECONDARY};")
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Payroll Cost (Debit)", "PAYROLL")
        self.mode_combo.addItem("Sales Income (Credit)", "SALES")
        self.mode_combo.setMinimumWidth(200)
        self.mode_combo.setStyleSheet("""
            QComboBox { padding: 6px; font-weight: bold; }
        """)
        
        layout.addWidget(label)
        layout.addWidget(self.mode_combo)
        layout.addStretch()
        return frame

    def _create_config_section(self):
        group = QGroupBox("Import Configuration")
        layout = QGridLayout(group) if 'QGridLayout' in globals() else QVBoxLayout(group)
        if not isinstance(layout, QVBoxLayout): # Fallback if QGridLayout import missing
             from PySide6.QtWidgets import QGridLayout
             layout = QGridLayout(group)

        # --- Common Fields ---
        self.voucher_date = QDateEdit(QDate.currentDate())
        self.from_date = QDateEdit(QDate.currentDate())
        self.to_date = QDateEdit(QDate.currentDate())
        
        for d in (self.voucher_date, self.from_date, self.to_date):
            d.setCalendarPopup(True)
            d.setDisplayFormat("dd-MMM-yyyy")
            d.setStyleSheet(Styles.get_compact_date_style())

        layout.addWidget(QLabel("Voucher Date:"), 0, 0)
        layout.addWidget(self.voucher_date, 0, 1)
        layout.addWidget(QLabel("Period From:"), 0, 2)
        layout.addWidget(self.from_date, 0, 3)
        layout.addWidget(QLabel("Period To:"), 0, 4)
        layout.addWidget(self.to_date, 0, 5)

        # --- Payroll Specific (Row 1) ---
        self.lbl_remarks = QLabel("Narration Remark:")
        self.import_remarks = QLineEdit()
        self.import_remarks.setPlaceholderText("e.g. Nanavati Team")
        
        layout.addWidget(self.lbl_remarks, 1, 0)
        layout.addWidget(self.import_remarks, 1, 1, 1, 2)

        # --- Sales Specific (Row 2) ---
        self.lbl_income = QLabel("Income Head:")
        self.income_combo = QComboBox()
        self.income_combo.setPlaceholderText("Select Income Ledger")
        
        self.lbl_bank = QLabel("Bank Account:")
        self.bank_combo = QComboBox()
        self.bank_combo.setPlaceholderText("Select Bank Ledger")

        layout.addWidget(self.lbl_income, 1, 0) # Overlaps row 1 (switched via visibility)
        layout.addWidget(self.income_combo, 1, 1, 1, 2)
        layout.addWidget(self.lbl_bank, 1, 3)
        layout.addWidget(self.bank_combo, 1, 4, 1, 2)

        # Populate Combos
        self._populate_sales_combos()

        return group

    def _create_upload_section(self):
        group = QGroupBox("File Upload")
        layout = QHBoxLayout(group)

        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet(f"color: {Styles.TEXT_MUTED}; font-style: italic;")
        
        self.browse_btn = QPushButton("Browse File")
        self.browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.PRIMARY};
                color: white;
                padding: 6px 16px;
                border: none;
                border-radius: 4px;
            }}
        """)
        self.browse_btn.clicked.connect(self._browse_file)
        
        layout.addWidget(self.file_label, 1)
        layout.addWidget(self.browse_btn)
        return group

    def _create_preview_section(self):
        group = QGroupBox("Data Preview")
        layout = QVBoxLayout(group)

        self.preview_table = QTableWidget()
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setMinimumHeight(250)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        layout.addWidget(self.preview_table)
        return group

    def _create_action_buttons(self):
        layout = QHBoxLayout()

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear)

        self.import_btn = QPushButton("Confirm Import")
        self.import_btn.setEnabled(False)
        self.import_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.SUCCESS};
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:disabled {{ background-color: {Styles.BORDER_LIGHT}; }}
        """)
        self.import_btn.clicked.connect(self._confirm_import)

        layout.addWidget(clear_btn)
        layout.addStretch()
        layout.addWidget(self.import_btn)
        return layout

    def _connect_signals(self):
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)

    def _populate_sales_combos(self):
        """Populate Tally Heads for Sales mode."""
        self.income_combo.clear()
        self.bank_combo.clear()

        # Income Heads (Credit)
        heads = self.config.get_tally_heads("credit")
        for h in heads:
            self.income_combo.addItem(f"{h.name} ({h.code})", h.code)

        # Bank Accounts (Usually Debit, but could be specific heads)
        # For now, we list all Tally Heads or specific Bank heads if config supports it.
        # Assuming Bank is a Tally Head. Ideally config should have 'Bank' category.
        # We will list all DEBIT heads as potential Bank/Asset accounts for now.
        bank_heads = self.config.get_tally_heads("debit")
        for h in bank_heads:
             self.bank_combo.addItem(f"{h.name} ({h.code})", h.code)

    def _on_mode_changed(self):
        self._mode = self.mode_combo.currentData()
        self._update_ui_for_mode()
        self._clear() # Reset file on mode switch

    def _update_ui_for_mode(self):
        is_sales = (self._mode == "SALES")

        # Toggle Visibility
        self.lbl_remarks.setVisible(not is_sales)
        self.import_remarks.setVisible(not is_sales)

        self.lbl_income.setVisible(is_sales)
        self.income_combo.setVisible(is_sales)
        self.lbl_bank.setVisible(is_sales)
        self.bank_combo.setVisible(is_sales)

        # Update Headers
        if is_sales:
            cols = ["Date", "Segment", "Product", "Location", "Amt (Taxable)", "SGST", "CGST", "IGST", "Total"]
        else:
            cols = ["Date", "Segment", "Product", "Location", "Gross", "PF(Emp)", "PF(Empr)", "ESIC", "PT", "TDS", "Net"]
        
        self.preview_table.setColumnCount(len(cols))
        self.preview_table.setHorizontalHeaderLabels(cols)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Excel/CSV (*.xlsx *.csv)")
        if not path: return

        self._current_file = path
        self.file_label.setText(os.path.basename(path))
        self.file_label.setStyleSheet(f"color: {Styles.TEXT_PRIMARY}; font-weight: bold;")
        
        if self._mode == "PAYROLL":
            self._parse_payroll_file(path)
        else:
            self._parse_sales_file(path)

    def _parse_payroll_file(self, path):
        # Existing Logic Delegate
        try:
            v_date = self.voucher_date.date().toPython()
            v_datetime = datetime.combine(v_date, time.min)
            
            vouchers, result = self.payroll_service.import_payroll_cost_csv(
                path, v_datetime, remarks=self.import_remarks.text()
            )
            
            self._vouchers = vouchers
            self._import_result = result
            
            if result.status == ImportStatus.FAILED:
                raise Exception(result.errors[0] if result.errors else "Unknown Error")
                
            self.import_btn.setEnabled(True)
            self._populate_preview(result.preview_data)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            self._clear()

    def _parse_sales_file(self, path):
        # New Sales Logic
        try:
            # Simple CSV Reader for now (can expand to Excel like payroll service)
            data = []
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)
            
            if not data: raise Exception("Empty file")

            preview_data = []
            self._vouchers = []
            
            # Common Data
            v_date = self.voucher_date.date().toPython()
            from_d = self.from_date.date().toString("dd-MMM-yyyy")
            to_d = self.to_date.date().toString("dd-MMM-yyyy")
            income_head_code = self.income_combo.currentData()
            income_head_name = self.income_combo.currentText().split("(")[0].strip()
            bank_head_name = self.bank_combo.currentText().split("(")[0].strip()

            if not income_head_code or not self.bank_combo.currentData():
                 raise Exception("Please select Income Head and Bank Account first.")

            for row in data:
                # 1. Map Columns (Flexible)
                def get_val(keys):
                    for k in keys:
                        if k in row and row[k]: return row[k].strip()
                    return "0"

                segment = get_val(["Business Segment", "Segment"])
                product = get_val(["Product Code", "Product"])
                loc = get_val(["Location", "Loc"])
                
                # Amounts
                amt = float(get_val(["Amount", "Taxable"]).replace(",","") or 0)
                sgst = float(get_val(["SGST"]).replace(",","") or 0)
                cgst = float(get_val(["CGST"]).replace(",","") or 0)
                igst = float(get_val(["IGST"]).replace(",","") or 0)
                total = amt + sgst + cgst + igst

                # 2. Narration Logic
                # "(International/Domestic B2C Billing), (for the period)"
                is_domestic = (igst == 0) # Simple inference or use Location
                type_str = "Domestic" if is_domestic else "International"
                narration = f"{type_str} B2C Billing, for period {from_d} to {to_d}"

                # 3. Create Voucher Object
                # Sales Spec: Bank Dr, To Income Cr, To GST Cr
                v = Voucher(
                    date=datetime.combine(v_date, time.min),
                    voucher_type=VoucherType.CREDIT,
                    account_code=income_head_code,
                    account_name=income_head_name, # Income Head
                    amount=amt, # Base Amount
                    narration=narration,
                    reference_id=self.config.generate_voucher_code("credit", product or "MISC"),
                    status=VoucherStatus.PENDING_REVIEW,
                    party_ledger=bank_head_name # Debtor (Bank)
                )
                
                # Attach Tax Data
                v.gst = SimpleNamespace()
                v.gst.cgst_amount = cgst
                v.gst.sgst_amount = sgst
                v.gst.igst_amount = igst
                
                # Store for Bulk Save
                self._vouchers.append(v)
                
                # Preview Row
                preview_data.append({
                    "Date": self.voucher_date.date().toString("dd-MMM"),
                    "Segment": segment, "Product": product, "Location": loc,
                    "Amt (Taxable)": amt, "SGST": sgst, "CGST": cgst, "IGST": igst, "Total": total
                })

            self.import_btn.setEnabled(True)
            self._populate_preview(preview_data)

        except Exception as e:
            QMessageBox.critical(self, "Sales Import Error", str(e))
            self._clear()

    def _populate_preview(self, data):
        self.preview_table.setRowCount(0)
        cols = [self.preview_table.horizontalHeaderItem(i).text() for i in range(self.preview_table.columnCount())]
        
        for row_data in data[:20]: # Show first 20
            r = self.preview_table.rowCount()
            self.preview_table.insertRow(r)
            for i, col_name in enumerate(cols):
                val = str(row_data.get(col_name, ""))
                if col_name in ["Date", "Segment", "Product", "Location"]:
                    self.preview_table.setItem(r, i, QTableWidgetItem(val))
                else:
                    # Numbers
                    try:
                        f_val = float(val)
                        self.preview_table.setItem(r, i, QTableWidgetItem(f"{f_val:,.2f}"))
                    except:
                        self.preview_table.setItem(r, i, QTableWidgetItem(val))

    def _confirm_import(self):
        if not self._vouchers: return
        
        total = sum([v.amount for v in self._vouchers])
        reply = QMessageBox.question(self, "Confirm", f"Import {len(self._vouchers)} vouchers?\nTotal Base Amount: ₹{total:,.2f}", QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                # Payload conversion
                payload = [v.to_dict() if hasattr(v, 'to_dict') else v for v in self._vouchers]
                self.data_service.add_vouchers_bulk(payload)
                QMessageBox.information(self, "Success", "Import Successful!")
                self._clear()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Save failed: {e}")

    def _clear(self):
        self.import_btn.setEnabled(False)
        self._current_file = None
        self._vouchers = []
        self.file_label.setText("No file selected")
        self.preview_table.setRowCount(0)