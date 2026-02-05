from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QMessageBox,
    QTableWidget, QTableWidgetItem, QFileDialog,
    QDateEdit, QScrollArea, QHeaderView
)
from PySide6.QtCore import Qt, Signal, QDate
from datetime import datetime, time
import os
import math

# Use the service that handles Journal Entries (Liabilities/Credits)
from services.debit_voucher_service import DebitVoucherImportService
from services.data_service import DataService
from models.import_result import ImportResult, ImportStatus
from .styles import Styles


class BulkImportTab(QWidget):
    """
    Bulk Import – Payroll Cost (Debit Only)
    
    Features:
    - Supports CSV and Excel (.xlsx)
    - Consolidated Journal Entry generation
    - Robust Preview with NaN handling
    """

    import_completed = Signal(ImportResult)

    def __init__(self, data_service: DataService, parent=None):
        super().__init__(parent)
        self.data_service = data_service
        self.import_service = DebitVoucherImportService()

        self._current_file = None
        self._import_result = None
        self._vouchers = []

        self._setup_ui()

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
        layout.addWidget(self._period_section())
        layout.addWidget(self._upload_section())
        layout.addWidget(self._preview_section())
        
        layout.addLayout(self._action_buttons())
        layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _header(self):
        label = QLabel("Bulk Import – Payroll Cost (Debit)")
        label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {Styles.SECONDARY};")
        return label

    def _period_section(self):
        group = QGroupBox("Period Details (Required)")
        layout = QHBoxLayout(group)

        self.voucher_date = QDateEdit(QDate.currentDate())
        self.from_date = QDateEdit(QDate.currentDate())
        self.to_date = QDateEdit(QDate.currentDate())

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
        layout.addStretch()

        return group

    def _upload_section(self):
        group = QGroupBox("Upload Payroll File")
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

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Payroll File",
            "",
            "Payroll Files (*.xlsx *.csv);;Excel Files (*.xlsx);;CSV Files (*.csv)" 
        )

        if not path:
            return

        self._current_file = path
        self.file_label.setText(os.path.basename(path))
        self.file_label.setStyleSheet(f"color: {Styles.TEXT_PRIMARY}; font-weight: bold;")
        self._parse_file(path)

    def _preview_section(self):
        group = QGroupBox("Preview (First 15 Rows)")
        layout = QVBoxLayout(group)

        self.preview_table = QTableWidget()
        # Full breakdown columns
        columns = [
            "Date", "Segment","Product Code", "Location", "Gross Amt", 
            "PF(Emp)", "PF(Empr)", 
            "ESIC(Emp)", "ESIC(Empr)", 
            "PT", "TDS", "Net Pay"
        ]
        self.preview_table.setColumnCount(len(columns))
        self.preview_table.setHorizontalHeaderLabels(columns)
        
        header = self.preview_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setMinimumHeight(250)
        
        layout.addWidget(self.preview_table)
        return group

    def _parse_file(self, path):
        try:
            # FIX: Convert QDate to datetime explicitly
            v_date = self.voucher_date.date().toPython()
            v_datetime = datetime.combine(v_date, time.min)

            vouchers, result = self.import_service.import_payroll_cost_csv(
                path, 
                v_datetime
            )

            self._vouchers = vouchers
            self._import_result = result
            
            # Check for failures
            if result.status == ImportStatus.FAILED:
                error_msg = result.errors[0]['message'] if result.errors else "Unknown Error"
                raise Exception(error_msg)

            self.import_btn.setEnabled(result.successful_rows > 0)
            self._populate_preview(result)

        except Exception as e:
            self.import_btn.setEnabled(False)
            self.preview_table.setRowCount(0)
            QMessageBox.critical(self, "Error", f"Failed to parse file: {str(e)}\n\nCheck if 'openpyxl' is installed if using Excel.")

    def _populate_preview(self, result):
        self.preview_table.setRowCount(0)
        
        if not result or not result.preview_data:
            return

        date_val = self.voucher_date.date().toString("dd-MMM-yyyy")

        # Robust string converter for NaN/None
        def safe_str(val):
            if val is None: return "0"
            if isinstance(val, float) and math.isnan(val): return "0"
            s = str(val).strip()
            return s if s else "0"

        for row in result.preview_data[:15]:
            r = self.preview_table.rowCount()
            self.preview_table.insertRow(r)

            # Helper to find keys case-insensitively
            def get_val(keys):
                for k in keys:
                    if k in row: return safe_str(row[k])
                    # Try stripped keys from the row
                    for row_k in row.keys():
                        if str(row_k).strip() == k: return safe_str(row[row_k])
                return "0"

            # 1. Date
            self.preview_table.setItem(r, 0, QTableWidgetItem(date_val))
            
            # 2. Segment
            segment = get_val(["Business Segment", "Segment"])
            self.preview_table.setItem(r, 1, QTableWidgetItem(segment))
            
            # 3. Product Code 
            self.preview_table.setItem(r, 2, QTableWidgetItem(get_val(["Product Code", "Product"])))

            # 4. Location
            self.preview_table.setItem(r, 3, QTableWidgetItem(get_val(["Location", "Loc"])))
            
            # 5. Gross Amount
            gross = get_val(["Amount", "Base Amount", "Gross"])
            self.preview_table.setItem(r, 4, QTableWidgetItem(gross))
            
            # 6. PF (Emp)
            pf_emp = get_val(["Employee Share of PF Payable", "PF Employee"])
            self.preview_table.setItem(r, 5, QTableWidgetItem(pf_emp))
            
            # 7. PF (Empr)
            pf_empr = get_val(["Employer Share of PF Payable", "PF Employer"])
            self.preview_table.setItem(r, 6, QTableWidgetItem(pf_empr))
            
            # 8. ESIC (Emp)
            esic_emp = get_val(["Employee Share of ESIC Payable", "ESIC Employee"])
            self.preview_table.setItem(r, 7, QTableWidgetItem(esic_emp))
            
            # 9. ESIC (Empr)
            esic_empr = get_val(["Employer Share of ESIC Payable", "ESIC Employer"])
            self.preview_table.setItem(r, 8, QTableWidgetItem(esic_empr))
            
            # 10. PT
            pt = get_val(["Professional Tax Payable", "PT"])
            self.preview_table.setItem(r, 9, QTableWidgetItem(pt))
            
            # 11. TDS
            tds = get_val(["TDS on Salary Payable - FY 2026-27", "TDS on Salary Payable", "TDS"])
            self.preview_table.setItem(r, 10, QTableWidgetItem(tds))
            
            # 12. Net Pay
            net = get_val(["Salary Payable", "Net Salary", "Net Payable"])
            self.preview_table.setItem(r, 11, QTableWidgetItem(net))

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
        if not self._vouchers:
            QMessageBox.warning(self, "No Data", "No payroll data to import.")
            return

        total_amt = sum(v.total_debit for v in self._vouchers)
        
        reply = QMessageBox.question(
            self,
            "Confirm Import",
            f"Import Payroll Journal Entry?\n\nTotal Cost: ₹{total_amt:,.2f}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # FIX: Ensure we send dictionaries if DataService expects them
            # Most simple JSON stores need dicts, not Python objects
            vouchers_payload = [v.to_dict() if hasattr(v, 'to_dict') else v for v in self._vouchers]
            
            self.data_service.add_vouchers_bulk(vouchers_payload)
            
            if self._import_result:
                self._import_result.complete(ImportStatus.COMPLETED)
                self.import_completed.emit(self._import_result)
            
            QMessageBox.information(self, "Success", "Payroll accounting entries imported successfully.")
            self._clear()

    def _clear(self):
        self.import_btn.setEnabled(False)
        self._current_file = None
        self._vouchers = []
        self._import_result = None
        self.file_label.setText("No file selected")
        self.file_label.setStyleSheet(f"color: {Styles.TEXT_MUTED}; font-style: italic;")
        self.preview_table.setRowCount(0)