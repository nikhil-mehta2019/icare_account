from unittest import result
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QMessageBox,
    QTableWidget, QTableWidgetItem, QFileDialog,
    QDateEdit, QScrollArea, QHeaderView, QLineEdit,
    QRadioButton, QComboBox
)
from PySide6.QtCore import Qt, Signal, QDate
from datetime import datetime, time
import os
import math

from services.debit_voucher_service import DebitVoucherImportService
from services.import_service import ImportService
from services.data_service import DataService
from services.voucher_config_service import get_voucher_config
from models.import_result import ImportResult, ImportStatus
from .styles import Styles


class BulkImportTab(QWidget):
    """
    Bulk Import – Supports Payroll Cost (Debit) & B2C Sales (Credit)
    """

    import_completed = Signal(ImportResult)

    def __init__(self, data_service: DataService, parent=None):
        super().__init__(parent)
        self.data_service = data_service
        self.config = get_voucher_config()
        
        # Services
        self.payroll_import_service = DebitVoucherImportService()
        self.sales_import_service = ImportService()

        # State
        self.import_mode = "payroll"  # 'payroll' or 'sales'
        self._current_file = None
        self._import_result = None
        self._vouchers = []

        self._setup_ui()
        self._setup_preview_columns() # Initialize table headers

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 10, 10, 10)

        layout.addWidget(self._header())
        layout.addWidget(self._type_section())          # NEW: Type Toggle
        layout.addWidget(self._period_section())
        layout.addWidget(self._sales_settings_section()) # NEW: Sales Settings
        layout.addWidget(self._upload_section())
        layout.addWidget(self._preview_section())
        
        layout.addLayout(self._action_buttons())
        layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _header(self):
        self.header_label = QLabel("Bulk Import – Payroll Cost (Debit)")
        self.header_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {Styles.SECONDARY};")
        return self.header_label

    def _type_section(self):
        group = QGroupBox("Import Type")
        layout = QHBoxLayout(group)
        
        self.payroll_radio = QRadioButton("Payroll Cost (Debit)")
        self.sales_radio = QRadioButton("B2C Sales (Credit)")
        self.payroll_radio.setChecked(True)
        
        self.payroll_radio.toggled.connect(self._on_type_changed)
        
        layout.addWidget(self.payroll_radio)
        layout.addWidget(self.sales_radio)
        layout.addStretch()
        return group

    def _period_section(self):
        group = QGroupBox("Period Details (Required)")
        layout = QHBoxLayout(group)

        self.voucher_date = QDateEdit(QDate.currentDate())
        self.from_date = QDateEdit(QDate.currentDate())
        self.to_date = QDateEdit(QDate.currentDate())
        
        # Remarks field (Used mainly for Payroll)
        self.remarks_label = QLabel("Details/Remarks:")
        self.import_remarks = QLineEdit()
        self.import_remarks.setPlaceholderText("e.g., Nanavati Team")
        self.import_remarks.setMinimumWidth(150)

        for d in (self.voucher_date, self.from_date, self.to_date):
            d.setCalendarPopup(True)
            d.setDisplayFormat("dd-MMM-yyyy")
            d.setStyleSheet(Styles.get_compact_date_style())

        layout.addWidget(QLabel("Voucher Date:"))
        layout.addWidget(self.voucher_date)
        layout.addSpacing(20)
        layout.addWidget(QLabel("From:"))
        layout.addWidget(self.from_date)
        layout.addWidget(QLabel("To:"))
        layout.addWidget(self.to_date)
        
        layout.addSpacing(20)
        layout.addWidget(self.remarks_label)
        layout.addWidget(self.import_remarks)
        
        layout.addStretch()
        return group

    def _sales_settings_section(self):
        self.sales_group = QGroupBox("Sales Accounting Configuration")
        layout = QHBoxLayout(self.sales_group)
        
        self.income_head_combo = QComboBox()
        self.income_head_combo.setMinimumWidth(250)
        self._populate_income_heads()
        
        self.bank_head_combo = QComboBox()
        self.bank_head_combo.setEditable(True)
        self.bank_head_combo.addItems(["HDFC Bank", "ICICI Bank", "SBI Bank", "Cash"])
        self.bank_head_combo.setMinimumWidth(200)
        
        layout.addWidget(QLabel("Operating Income Head:"))
        layout.addWidget(self.income_head_combo)
        layout.addSpacing(20)
        layout.addWidget(QLabel("Bank/Cash Account (Dr):"))
        layout.addWidget(self.bank_head_combo)
        layout.addStretch()
        
        self.sales_group.setVisible(False)  # Hidden by default
        return self.sales_group

    def _upload_section(self):
        group = QGroupBox("Upload File")
        layout = QHBoxLayout(group)

        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet(f"color: {Styles.TEXT_MUTED}; font-style: italic;")
        
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setMinimumWidth(100)
        self.browse_btn.clicked.connect(self._browse_file)
        self.browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.PRIMARY};
                color: white;
                padding: 6px 16px;
                border: none;
                border-radius: 4px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Styles.PRIMARY_DARK}; }}
        """)
        
        layout.addWidget(self.file_label, 1)
        layout.addWidget(self.browse_btn)

        return group

    def _preview_section(self):
        group = QGroupBox("Preview (First 15 Rows)")
        layout = QVBoxLayout(group)

        self.preview_table = QTableWidget()
        header = self.preview_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setMinimumHeight(250)
        
        layout.addWidget(self.preview_table)
        return group

    # === DYNAMIC UI HANDLERS ===

    def _populate_income_heads(self):
        self.income_head_combo.clear()
        self.income_head_combo.addItem("-- Select Operating Income Head --", None)
        try:
            heads = self.config.get_tally_heads("credit")
            for head in heads:
                self.income_head_combo.addItem(f"{head.code} - {head.name}", head.code)
        except Exception:
            pass

    def _on_type_changed(self):
        self._clear() # Clear state when switching modes
        
        if self.payroll_radio.isChecked():
            self.import_mode = "payroll"
            self.header_label.setText("Bulk Import – Payroll Cost (Debit)")
            self.sales_group.setVisible(False)
            self.remarks_label.setVisible(True)
            self.import_remarks.setVisible(True)
        else:
            self.import_mode = "sales"
            self.header_label.setText("Bulk Import – B2C Sales (Credit)")
            self.sales_group.setVisible(True)
            self.remarks_label.setVisible(False)
            self.import_remarks.setVisible(False)
            
        self._setup_preview_columns()

    def _setup_preview_columns(self):
        if self.import_mode == "payroll":
            columns = [
                "Date", "Segment", "Product Code", "Location", "Gross Amt", 
                "PF(Emp)", "PF(Empr)", "ESIC(Emp)", "ESIC(Empr)", 
                "PT", "TDS", "Net Pay"
            ]
        else:
            columns = [
                "Segment", "Narration", "Gross Amt", 
                "Base Amt", "CGST", "SGST", "IGST"
            ]
            
        self.preview_table.setColumnCount(len(columns))
        self.preview_table.setHorizontalHeaderLabels(columns)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            "",
            "CSV/Excel Files (*.csv *.xlsx);;All Files (*.*)" 
        )

        if not path:
            return

        self._current_file = path
        self.file_label.setText(os.path.basename(path))
        self.file_label.setStyleSheet(f"color: {Styles.TEXT_PRIMARY}; font-weight: bold;")
        self._parse_file(path)

    # === PARSING LOGIC ===

    def _parse_file(self, path):
        try:
            v_date = self.voucher_date.date().toPython()
            v_datetime = datetime.combine(v_date, time.min)

            if self.import_mode == "payroll":
                # === PAYROLL LOGIC (Untouched) ===
                vouchers, result = self.payroll_import_service.import_payroll_cost_csv(
                    path, 
                    v_datetime,
                    remarks=self.import_remarks.text()
                )
                self._vouchers = vouchers
                self._import_result = result
            else:
                # === B2C SALES LOGIC (New) ===
                income_code = self.income_head_combo.currentData()
                if not income_code:
                    raise Exception("Please select an Operating Income Head before importing.")
                
                bank_name = self.bank_head_combo.currentText().strip()
                if not bank_name:
                    raise Exception("Please select or enter a Bank/Cash Account before importing.")

                global_data = {
                    'from_date': self.from_date.date().toPython(),
                    'to_date': self.to_date.date().toPython(),
                    'income_head_code': income_code,
                    'income_head_name': self.income_head_combo.currentText().split(' - ')[-1],
                    'bank_head_name': bank_name
                }
                
                result = self.sales_import_service.parse_sales_csv(path, global_data)
                self._import_result = result
                self._vouchers = result.vouchers

            # Common Error Handling
            if result.status == ImportStatus.FAILED:
                if result.errors:
                    err = result.errors[0]
                    error_msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                else:
                    error_msg = "Unknown Error"
                raise Exception(error_msg)

            self.import_btn.setEnabled(result.successful_rows > 0)
            self._populate_preview(result)

        except Exception as e:
            self.import_btn.setEnabled(False)
            self.preview_table.setRowCount(0)
            QMessageBox.critical(self, "Error", f"Failed to parse file: {str(e)}")

    def _populate_preview(self, result):
        self.preview_table.setRowCount(0)
        if not result:
            return

        if self.import_mode == "payroll":
            self._populate_payroll_preview(result)
        else:
            self._populate_sales_preview(result)

    def _populate_sales_preview(self, result):
        """Populate preview directly from the generated Sales Vouchers."""
        for v in result.vouchers[:15]:
            r = self.preview_table.rowCount()
            self.preview_table.insertRow(r)
            
            self.preview_table.setItem(r, 0, QTableWidgetItem(v.segment))
            self.preview_table.setItem(r, 1, QTableWidgetItem(v.narration))
            self.preview_table.setItem(r, 2, QTableWidgetItem(f"{v.amount:,.2f}"))
            self.preview_table.setItem(r, 3, QTableWidgetItem(f"{v.base_amount:,.2f}"))
            self.preview_table.setItem(r, 4, QTableWidgetItem(f"{getattr(v, 'cgst_amount', 0):,.2f}"))
            self.preview_table.setItem(r, 5, QTableWidgetItem(f"{getattr(v, 'sgst_amount', 0):,.2f}"))
            self.preview_table.setItem(r, 6, QTableWidgetItem(f"{getattr(v, 'igst_amount', 0):,.2f}"))

    def _populate_payroll_preview(self, result):
        """Preserved Payroll Preview Logic."""
        if not result.preview_data: return
        date_val = self.voucher_date.date().toString("dd-MMM-yyyy")

        def safe_str(val):
            if val is None: return "0"
            if isinstance(val, float) and math.isnan(val): return "0"
            s = str(val).strip()
            return s if s else "0"

        for row in result.preview_data[:15]:
            r = self.preview_table.rowCount()
            self.preview_table.insertRow(r)

            def get_val(keys):
                for k in keys:
                    if k in row: return safe_str(row[k])
                    for row_k in row.keys():
                        if str(row_k).strip() == k: return safe_str(row[row_k])
                return "0"

            self.preview_table.setItem(r, 0, QTableWidgetItem(date_val))
            self.preview_table.setItem(r, 1, QTableWidgetItem(get_val(["Business Segment", "Segment"])))
            self.preview_table.setItem(r, 2, QTableWidgetItem(get_val(["Product Code", "Product"])))
            self.preview_table.setItem(r, 3, QTableWidgetItem(get_val(["Location", "Loc"])))
            self.preview_table.setItem(r, 4, QTableWidgetItem(get_val(["Amount", "Base Amount", "Gross"])))
            self.preview_table.setItem(r, 5, QTableWidgetItem(get_val(["Employee Share of PF Payable", "PF Employee"])))
            self.preview_table.setItem(r, 6, QTableWidgetItem(get_val(["Employer Share of PF Payable", "PF Employer"])))
            self.preview_table.setItem(r, 7, QTableWidgetItem(get_val(["Employee Share of ESIC Payable", "ESIC Employee"])))
            self.preview_table.setItem(r, 8, QTableWidgetItem(get_val(["Employer Share of ESIC Payable", "ESIC Employer"])))
            self.preview_table.setItem(r, 9, QTableWidgetItem(get_val(["Professional Tax Payable", "PT"])))
            self.preview_table.setItem(r, 10, QTableWidgetItem(get_val(["TDS on Salary Payable - FY 2026-27", "TDS on Salary Payable", "TDS"])))
            self.preview_table.setItem(r, 11, QTableWidgetItem(get_val(["Salary Payable", "Net Salary", "Net Payable"])))

    # === ACTION BUTTONS ===

    def _action_buttons(self):
        layout = QHBoxLayout()

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.SECONDARY};
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }}
        """)
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

    def _confirm_import(self):
        # 1. Validation checks based on mode
        if self.import_mode == "payroll":
            remarks = self.import_remarks.text().strip()
            if not remarks:
                QMessageBox.warning(self, "Validation", "Details/Remarks are required for Payroll.")
                self.import_remarks.setFocus()
                return

        if not self._vouchers:
            QMessageBox.warning(self, "No Data", "No valid data to import.")
            return

        total_amt = sum(getattr(v, 'amount', getattr(v, 'total_debit', 0.0)) for v in self._vouchers)
        
        reply = QMessageBox.question(
            self,
            "Confirm Import",
            f"Import {len(self._vouchers)} entries?\n\nTotal Gross: ₹{total_amt:,.2f}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                v_date_obj = datetime.combine(self.voucher_date.date().toPython(), time.min)

                # === Get Base Sequence ONCE for the batch ===
                if self.import_mode == "sales":
                    base_v_no = self.data_service.generate_credit_sale_code(v_date_obj)
                    # Extract prefix (e.g., 'CR-SAL-202602') and starting number (e.g., 2)
                    prefix = "-".join(base_v_no.split('-')[:-1])
                    seq_num = int(base_v_no.split('-')[-1])

                for v in self._vouchers:
                    # Sync voucher date with UI selection
                    v.date = v_date_obj
                    
                    if self.import_mode == "payroll":
                        v.narration = self.import_remarks.text().strip()
                    else:
                        # === CRITICAL: Ensure Strict Sequential ID for Sales ===
                        v_no = f"{prefix}-{seq_num:04d}"
                        v.voucher_no = v_no
                        v.reference_id = v_no
                        seq_num += 1  # Increment for the next row

                # Convert and Save
                vouchers_payload = [v.to_dict() if hasattr(v, 'to_dict') else v for v in self._vouchers]
                self.data_service.add_vouchers_bulk(vouchers_payload)
                
                if self._import_result:
                    self._import_result.complete(ImportStatus.COMPLETED)
                    self.import_completed.emit(self._import_result)
                
                mode_str = "B2C Sales" if self.import_mode == "sales" else "Payroll"
                QMessageBox.information(self, "Success", f"{mode_str} entries imported securely.")
                self._clear()
                
            except Exception as e:
                QMessageBox.critical(self, "Import Error", f"Failed to save vouchers: {str(e)}")

    def _clear(self):
        self.import_btn.setEnabled(False)
        self._current_file = None
        self._vouchers = []
        self._import_result = None
        self.file_label.setText("No file selected")
        self.file_label.setStyleSheet(f"color: {Styles.TEXT_MUTED}; font-style: italic;")
        self.preview_table.setRowCount(0)