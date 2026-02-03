from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QMessageBox,
    QTableWidget, QTableWidgetItem, QFileDialog,
    QDateEdit, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QDate
from services.payroll_import_service import PayrollImportService
import os

from services.debit_voucher_service import DebitVoucherImportService
from services.data_service import DataService
from models.import_result import ImportResult, ImportStatus
from .styles import Styles


class BulkImportTab(QWidget):
    """
    Bulk Import – Payroll Cost (Debit Only)

    Scope:
    - Payroll cost only
    - Debit vouchers only
    - No GST / TDS
    - No Point of Supply
    - No Import Format selection
    """

    import_completed = Signal(ImportResult)

    def __init__(self, data_service: DataService, parent=None):
        super().__init__(parent)
        self.data_service = data_service
        self.import_service = PayrollImportService()

        self._current_file = None
        self._import_result = None
        self._vouchers = []

        self._setup_ui()

    # ---------------------------------------------------------------------
    # UI SETUP
    # ---------------------------------------------------------------------

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)

        layout.addWidget(self._header())
        layout.addWidget(self._period_section())
        layout.addWidget(self._upload_section())
        layout.addWidget(self._preview_section())
        layout.addLayout(self._action_buttons())

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _header(self):
        label = QLabel("Bulk Import – Payroll Cost (Debit)")
        label.setStyleSheet("font-size:16px; font-weight:bold;")
        return label

    # ---------------------------------------------------------------------
    # PERIOD
    # ---------------------------------------------------------------------

    def _period_section(self):
        group = QGroupBox("Period Details (Required)")
        layout = QHBoxLayout(group)

        self.voucher_date = QDateEdit(QDate.currentDate())
        self.from_date = QDateEdit(QDate.currentDate())
        self.to_date = QDateEdit(QDate.currentDate())

        for d in (self.voucher_date, self.from_date, self.to_date):
            d.setCalendarPopup(True)
            d.setDisplayFormat("dd-MMM-yyyy")

        layout.addWidget(QLabel("Voucher Date"))
        layout.addWidget(self.voucher_date)
        layout.addWidget(QLabel("From"))
        layout.addWidget(self.from_date)
        layout.addWidget(QLabel("To"))
        layout.addWidget(self.to_date)
        layout.addStretch()

        return group

    # ---------------------------------------------------------------------
    # UPLOAD
    # ---------------------------------------------------------------------

    def _upload_section(self):
        group = QGroupBox("Upload Payroll File")
        layout = QHBoxLayout(group)

        self.file_label = QLabel("No file selected")
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setEnabled(True)
        self.browse_btn.setMinimumWidth(100)
        self.browse_btn.clicked.connect(self._browse_file)
        self.browse_btn.setStyleSheet("""
				QPushButton {
				background-color: #0AA6A6;
				color: white;
				padding: 6px 16px;
				border-radius: 4px;
				font-weight: 600;
			}
			QPushButton:hover {
			background-color: #088F8F;
			}
		""")
        layout.addWidget(self.file_label, 1)
        layout.addWidget(self.browse_btn)
        

        return group

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Payroll File",
            "",
            "Excel (*.xlsx);;CSV (*.csv)"
        )

        if not path:
            return

        self._current_file = path
        self.file_label.setText(os.path.basename(path))
        self._parse_file(path)

    # ---------------------------------------------------------------------
    # PREVIEW
    # ---------------------------------------------------------------------

    def _preview_section(self):
        group = QGroupBox("Preview (First 15 Rows)")
        layout = QVBoxLayout(group)

        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(4)
        self.preview_table.setHorizontalHeaderLabels(
            ["Date", "Employee / Ledger", "Segment", "Amount"]
        )
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.preview_table)
        return group

    def _parse_file(self, path):
        print("DEBUG import_excel signature:", self.import_service.import_excel.__code__.co_argcount)

        try:
            self.import_btn.setEnabled(True)
            vouchers, result = self.import_service.import_excel(path , self.voucher_date.date().toPython())

            self._vouchers = vouchers
            self._import_result = result

            self._populate_preview(result.preview_data)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _populate_preview(self, rows):
        self.preview_table.setRowCount(0)

        for row in rows[:15]:
            r = self.preview_table.rowCount()
            self.preview_table.insertRow(r)

            self.preview_table.setItem(r, 0, QTableWidgetItem(str(row.get("Date", ""))))
            self.preview_table.setItem(r, 1, QTableWidgetItem(str(
                row.get("Employee Name") or row.get("Ledger") or ""
            )))
            self.preview_table.setItem(r, 2, QTableWidgetItem(str(row.get("Business Segment", ""))))
            self.preview_table.setItem(r, 3, QTableWidgetItem(str(row.get("Amount", ""))))

    # ---------------------------------------------------------------------
    # ACTIONS
    # ---------------------------------------------------------------------

    def _action_buttons(self):
        layout = QHBoxLayout()

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear)

        self.import_btn = QPushButton("Confirm Import")
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self._confirm_import)

        layout.addWidget(clear_btn)
        layout.addStretch()
        layout.addWidget(self.import_btn)
        
        return layout

    def _confirm_import(self):
        if not self._vouchers:
            QMessageBox.warning(self, "No Data", "No payroll data to import.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Import",
            f"Import {len(self._vouchers)} payroll entries?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.data_service.add_vouchers_bulk(self._vouchers)
            self._import_result.complete(ImportStatus.COMPLETED)
            self.import_completed.emit(self._import_result)
            QMessageBox.information(self, "Success", "Payroll import completed.")
            self._clear()

    def _clear(self):
        self.import_btn.setEnabled(False)
        self._current_file = None
        self._vouchers = []
        self._import_result = None
        self.file_label.setText("No file selected")
        self.preview_table.setRowCount(0)
