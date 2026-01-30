"""Voucher Entry Tab - 4-Step Guided GST Voucher Creation.

Step 1: Method & Head Selection
Step 2: Voucher Settings & Tax Configuration
Step 3: Financial Details
Step 4: Confirm & Print
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QRadioButton, QButtonGroup,
    QPushButton, QGroupBox, QFrame, QMessageBox, QDoubleSpinBox,
    QDateEdit, QScrollArea, QSizePolicy, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QStackedWidget, QSpacerItem
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QFont
from datetime import datetime, date, timedelta

from models.voucher import Voucher, VoucherStatus
from models.account_head import VoucherType
from services.data_service import DataService
from services.voucher_config_service import get_voucher_config
from .styles import Styles


class StepHeader(QFrame):
    """Step header widget with number, title, and status."""
    
    def __init__(self, step_num: int, title: str, parent=None):
        super().__init__(parent)
        self.step_num = step_num
        self.title = title
        self._is_active = False
        self._is_complete = False
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # Step number circle
        self.num_label = QLabel(str(self.step_num))
        self.num_label.setFixedSize(28, 28)
        self.num_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.num_label)
        
        # Title
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.status_label)
        
        self._update_style()
    
    def set_active(self, active: bool):
        self._is_active = active
        self._update_style()
    
    def set_complete(self, complete: bool):
        self._is_complete = complete
        self._update_style()
    
    def _update_style(self):
        if self._is_complete:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: #E8F5E9;
                    border: 2px solid {Styles.SUCCESS};
                    border-radius: 6px;
                }}
            """)
            self.num_label.setStyleSheet(f"""
                background-color: {Styles.SUCCESS};
                color: white;
                border-radius: 14px;
                font-weight: bold;
                font-size: 13px;
            """)
            self.status_label.setText("✓ Complete")
            self.status_label.setStyleSheet(f"color: {Styles.SUCCESS}; font-size: 11px; font-weight: bold;")
        elif self._is_active:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: #E3F2FD;
                    border: 2px solid {Styles.PRIMARY};
                    border-radius: 6px;
                }}
            """)
            self.num_label.setStyleSheet(f"""
                background-color: {Styles.PRIMARY};
                color: white;
                border-radius: 14px;
                font-weight: bold;
                font-size: 13px;
            """)
            self.status_label.setText("● Current")
            self.status_label.setStyleSheet(f"color: {Styles.PRIMARY}; font-size: 11px; font-weight: bold;")
        else:
            self.setStyleSheet(f"""
                QFrame {{
                    background-color: {Styles.BG_SECONDARY};
                    border: 1px solid {Styles.BORDER_LIGHT};
                    border-radius: 6px;
                }}
            """)
            self.num_label.setStyleSheet(f"""
                background-color: {Styles.BORDER_MEDIUM};
                color: white;
                border-radius: 14px;
                font-weight: bold;
                font-size: 13px;
            """)
            self.status_label.setText("Pending")
            self.status_label.setStyleSheet(f"color: {Styles.TEXT_MUTED}; font-size: 11px;")


class VoucherEntryTab(QWidget):
    """4-Step Guided Voucher Entry with GST/TDS support."""
    
    voucher_saved = Signal(Voucher)
    
    def __init__(self, data_service: DataService, parent=None):
        super().__init__(parent)
        self.data_service = data_service
        self.config = get_voucher_config()
        
        self._current_step = 1
        self._voucher_type = "credit"
        self._step_data = {}
        self._voucher_sequence = 1
        
        self._setup_ui()
        self._connect_signals()
        self._update_step_visibility()
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Title Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Step Headers
        self.step_headers = []
        steps_container = QHBoxLayout()
        steps_container.setSpacing(8)
        
        step_titles = [
            "Method & Head",
            "Settings & Tax",
            "Financial Details",
            "Confirm & Print"
        ]
        
        for i, title in enumerate(step_titles, 1):
            header = StepHeader(i, title)
            self.step_headers.append(header)
            steps_container.addWidget(header)
        
        layout.addLayout(steps_container)
        
        # Stacked content for steps
        self.step_stack = QStackedWidget()
        
        # Create step content widgets
        self.step1_widget = self._create_step1()
        self.step2_widget = self._create_step2()
        self.step3_widget = self._create_step3()
        self.step4_widget = self._create_step4()
        
        self.step_stack.addWidget(self.step1_widget)
        self.step_stack.addWidget(self.step2_widget)
        self.step_stack.addWidget(self.step3_widget)
        self.step_stack.addWidget(self.step4_widget)
        
        layout.addWidget(self.step_stack, 1)
        
        # Navigation buttons
        nav_layout = self._create_navigation()
        layout.addLayout(nav_layout)
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
    
    def _create_header(self) -> QFrame:
        header = QFrame()
        header.setStyleSheet(f"""
            background-color: {Styles.SECONDARY};
            border-radius: 6px;
            padding: 10px;
        """)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 8, 12, 8)
        
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        
        title = QLabel("Create Voucher")
        title.setStyleSheet(f"color: {Styles.TEXT_LIGHT}; font-size: 18px; font-weight: bold;")
        title_layout.addWidget(title)
        
        subtitle = QLabel("4-Step Guided Entry with GST Auto-Calculation")
        subtitle.setStyleSheet(f"color: {Styles.TEXT_LIGHT}; font-size: 11px; opacity: 0.9;")
        title_layout.addWidget(subtitle)
        
        layout.addLayout(title_layout)
        layout.addStretch()
        
        # Voucher Type Toggle
        type_frame = QFrame()
        type_frame.setStyleSheet("""
            background-color: rgba(255,255,255,0.1);
            border-radius: 4px;
            padding: 4px;
        """)
        type_layout = QHBoxLayout(type_frame)
        type_layout.setContentsMargins(8, 4, 8, 4)
        type_layout.setSpacing(8)
        
        self.type_group = QButtonGroup(self)
        
        self.credit_radio = QRadioButton("CREDIT")
        self.credit_radio.setChecked(True)
        self.credit_radio.setStyleSheet(f"color: {Styles.TEXT_LIGHT}; font-weight: bold; font-size: 12px;")
        self.type_group.addButton(self.credit_radio, 0)
        type_layout.addWidget(self.credit_radio)
        
        self.debit_radio = QRadioButton("DEBIT")
        self.debit_radio.setStyleSheet(f"color: {Styles.TEXT_LIGHT}; font-weight: bold; font-size: 12px;")
        self.type_group.addButton(self.debit_radio, 1)
        type_layout.addWidget(self.debit_radio)
        
        layout.addWidget(type_frame)
        
        return header
    
    def _create_step1(self) -> QWidget:
        """Step 1: Method & Head Selection."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Recording Method (fixed to Manual)
        method_group = QGroupBox("Recording Method")
        method_layout = QHBoxLayout(method_group)
        method_layout.setContentsMargins(12, 16, 12, 12)
        
        self.method_label = QLabel("Manual Entry")
        self.method_label.setStyleSheet(f"""
            background-color: {Styles.PRIMARY};
            color: white;
            padding: 8px 20px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 13px;
        """)
        method_layout.addWidget(self.method_label)
        method_layout.addStretch()
        
        layout.addWidget(method_group)
        
        # Tally Accounting Head
        head_group = QGroupBox("Tally Accounting Head *")
        head_layout = QVBoxLayout(head_group)
        head_layout.setContentsMargins(12, 16, 12, 12)
        head_layout.setSpacing(8)
        
        self.tally_head_combo = QComboBox()
        self.tally_head_combo.setPlaceholderText("-- Select Accounting Head --")
        self.tally_head_combo.setMinimumHeight(36)
        self.tally_head_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 8px 12px;
                border: 1px solid {Styles.BORDER_MEDIUM};
                border-radius: 4px;
                font-size: 13px;
                background-color: {Styles.BG_CARD};
            }}
        """)
        head_layout.addWidget(self.tally_head_combo)
        
        self.head_info_label = QLabel("")
        self.head_info_label.setStyleSheet(f"color: {Styles.TEXT_MUTED}; font-size: 11px;")
        head_layout.addWidget(self.head_info_label)
        
        layout.addWidget(head_group)
        
        # Date Fields
        date_group = QGroupBox("Voucher Dates")
        date_layout = QVBoxLayout(date_group)
        date_layout.setContentsMargins(12, 16, 12, 12)
        date_layout.setSpacing(10)
        
        # Voucher Date
        vdate_row = QHBoxLayout()
        vdate_row.setSpacing(12)
        
        vdate_label = QLabel("Voucher Date:")
        vdate_label.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {Styles.SECONDARY};")
        vdate_label.setMinimumWidth(100)
        vdate_row.addWidget(vdate_label)
        
        self.voucher_date = QDateEdit()
        self.voucher_date.setDate(QDate.currentDate())
        self.voucher_date.setCalendarPopup(True)
        self.voucher_date.setDisplayFormat("dd-MMM-yyyy")
        self.voucher_date.setMinimumWidth(140)
        self.voucher_date.setFixedHeight(32)
        self.voucher_date.setStyleSheet(self._get_date_style())
        vdate_row.addWidget(self.voucher_date)
        
        self.vdate_error = QLabel("")
        self.vdate_error.setStyleSheet(f"color: {Styles.ERROR}; font-size: 11px;")
        vdate_row.addWidget(self.vdate_error)
        vdate_row.addStretch()
        
        date_layout.addLayout(vdate_row)
        
        # Period dates
        period_row = QHBoxLayout()
        period_row.setSpacing(12)
        
        from_label = QLabel("From Date:")
        from_label.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {Styles.SECONDARY};")
        from_label.setMinimumWidth(100)
        period_row.addWidget(from_label)
        
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("dd-MMM-yyyy")
        self.from_date.setMinimumWidth(130)
        self.from_date.setFixedHeight(30)
        self.from_date.setStyleSheet(self._get_date_style())
        period_row.addWidget(self.from_date)
        
        to_label = QLabel("To Date:")
        to_label.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {Styles.SECONDARY};")
        period_row.addWidget(to_label)
        
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)
        self.to_date.setDisplayFormat("dd-MMM-yyyy")
        self.to_date.setMinimumWidth(130)
        self.to_date.setFixedHeight(30)
        self.to_date.setStyleSheet(self._get_date_style())
        period_row.addWidget(self.to_date)
        
        self.period_error = QLabel("")
        self.period_error.setStyleSheet(f"color: {Styles.ERROR}; font-size: 11px;")
        period_row.addWidget(self.period_error)
        period_row.addStretch()
        
        date_layout.addLayout(period_row)
        
        # Date helper
        date_helper = QLabel("Voucher Date max 7 days backdated. Period auto-suggests 60 days range.")
        date_helper.setStyleSheet(f"color: {Styles.TEXT_MUTED}; font-size: 10px; font-style: italic;")
        date_layout.addWidget(date_helper)
        
        layout.addWidget(date_group)
        layout.addStretch()
        
        # Initialize with default dates
        self._set_default_dates()
        
        return widget
    
    def _create_step2(self) -> QWidget:
        """Step 2: Voucher Settings & Tax Configuration."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Settings Section
        settings_group = QGroupBox("Voucher Settings")
        settings_layout = QFormLayout(settings_group)
        settings_layout.setContentsMargins(12, 16, 12, 12)
        settings_layout.setSpacing(10)
        
        # Business Segment (NEW - Req 4)
        self.segment_combo = QComboBox()
        self.segment_combo.setMinimumHeight(32)
        self._populate_business_segments()
        settings_layout.addRow("Business Segment:", self.segment_combo)
        
        # Country
        self.country_combo = QComboBox()
        self.country_combo.setMinimumHeight(32)
        self._populate_countries()
        settings_layout.addRow("Country:", self.country_combo)
        
        self.country_note_label = QLabel("")
        self.country_note_label.setStyleSheet(f"color: {Styles.INFO}; font-size: 10px; font-style: italic;")
        settings_layout.addRow("", self.country_note_label)
        
        # Product
        self.product_combo = QComboBox()
        self.product_combo.setMinimumHeight(32)
        self._populate_products()
        settings_layout.addRow("Product:", self.product_combo)
        
        # Franchise (conditional)
        self.franchise_combo = QComboBox()
        self.franchise_combo.setMinimumHeight(32)
        self.franchise_combo.setEnabled(False)
        self._populate_franchises()
        settings_layout.addRow("Franchise:", self.franchise_combo)
        
        self.franchise_required_label = QLabel("")
        self.franchise_required_label.setStyleSheet(f"color: {Styles.WARNING}; font-size: 10px;")
        settings_layout.addRow("", self.franchise_required_label)
        
        # Voucher Code (auto-generated)
        self.voucher_code_display = QLineEdit()
        self.voucher_code_display.setReadOnly(True)
        self.voucher_code_display.setMinimumHeight(32)
        self.voucher_code_display.setStyleSheet(f"""
            background-color: {Styles.BG_SECONDARY};
            font-weight: bold;
            font-size: 13px;
        """)
        settings_layout.addRow("Voucher Code:", self.voucher_code_display)
        
        layout.addWidget(settings_group)
        
        # Tax Configuration Section
        tax_group = QGroupBox("Tax Configuration")
        tax_layout = QVBoxLayout(tax_group)
        tax_layout.setContentsMargins(12, 16, 12, 12)
        tax_layout.setSpacing(12)
        
        # Point of Supply
        pos_row = QHBoxLayout()
        pos_row.setSpacing(10)
        
        pos_label = QLabel("Point of Supply (State) *:")
        pos_label.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {Styles.SECONDARY};")
        pos_label.setMinimumWidth(160)
        pos_row.addWidget(pos_label)
        
        self.pos_combo = QComboBox()
        self.pos_combo.setMinimumWidth(200)
        self.pos_combo.setMinimumHeight(32)
        self._populate_pos_states()
        pos_row.addWidget(self.pos_combo)
        
        self.pos_indicator = QLabel("")
        self.pos_indicator.setStyleSheet("font-size: 11px; font-weight: bold;")
        pos_row.addWidget(self.pos_indicator)
        pos_row.addStretch()
        
        tax_layout.addLayout(pos_row)
        
        # RCM Indicator (NEW - Req 3)
        self.rcm_indicator = QLabel("")
        self.rcm_indicator.setStyleSheet(f"color: {Styles.ERROR}; font-size: 11px; font-weight: bold; padding-left: 160px;")
        tax_layout.addWidget(self.rcm_indicator)
        
        # GST Applicable
        gst_app_row = QHBoxLayout()
        gst_app_row.setSpacing(10)
        
        gst_app_label = QLabel("GST Applicable?:")
        gst_app_label.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {Styles.SECONDARY};")
        gst_app_label.setMinimumWidth(160)
        gst_app_row.addWidget(gst_app_label)
        
        self.gst_app_combo = QComboBox()
        self.gst_app_combo.setMinimumWidth(200)
        self.gst_app_combo.setMinimumHeight(32)
        self._populate_gst_app()
        gst_app_row.addWidget(self.gst_app_combo)
        gst_app_row.addStretch()
        
        tax_layout.addLayout(gst_app_row)
        
        # GST Type & Rate (auto-determined)
        self.gst_details_frame = QFrame()
        self.gst_details_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #E8F5E9;
                border: 1px solid {Styles.SUCCESS};
                border-radius: 4px;
                padding: 10px;
            }}
        """)
        gst_details_layout = QVBoxLayout(self.gst_details_frame)
        gst_details_layout.setContentsMargins(10, 8, 10, 8)
        gst_details_layout.setSpacing(8)
        
        self.gst_type_label = QLabel("GST Type: --")
        self.gst_type_label.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {Styles.SUCCESS};")
        gst_details_layout.addWidget(self.gst_type_label)
        
        # GST Rate row
        gst_rate_row = QHBoxLayout()
        gst_rate_row.setSpacing(10)
        
        rate_label = QLabel("Rate:")
        rate_label.setStyleSheet("font-size: 12px;")
        gst_rate_row.addWidget(rate_label)
        
        self.gst_rate_combo = QComboBox()
        self.gst_rate_combo.setMinimumWidth(100)
        self.gst_rate_combo.setMinimumHeight(30)
        self._populate_gst_rates()
        gst_rate_row.addWidget(self.gst_rate_combo)
        
        self.gst_split_label = QLabel("")
        self.gst_split_label.setStyleSheet(f"color: {Styles.TEXT_SECONDARY}; font-size: 11px;")
        gst_rate_row.addWidget(self.gst_split_label)
        gst_rate_row.addStretch()
        
        gst_details_layout.addLayout(gst_rate_row)
        
        tax_layout.addWidget(self.gst_details_frame)
        
        # TDS Section (Debit only)
        self.tds_frame = QFrame()
        self.tds_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #FFF3E0;
                border: 1px solid {Styles.WARNING};
                border-radius: 4px;
                padding: 10px;
            }}
        """)
        tds_layout = QVBoxLayout(self.tds_frame)
        tds_layout.setContentsMargins(10, 8, 10, 8)
        tds_layout.setSpacing(8)
        
        tds_title = QLabel("TDS / WHT Configuration (Debit Only)")
        tds_title.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {Styles.WARNING};")
        tds_layout.addWidget(tds_title)
        
        tds_row = QHBoxLayout()
        tds_row.setSpacing(10)
        
        tds_app_label = QLabel("TDS Applicable?:")
        tds_app_label.setStyleSheet("font-size: 12px;")
        tds_row.addWidget(tds_app_label)
        
        self.tds_app_combo = QComboBox()
        self.tds_app_combo.setMinimumWidth(150)
        self.tds_app_combo.setMinimumHeight(30)
        self._populate_tds_app()
        tds_row.addWidget(self.tds_app_combo)
        
        self.tds_rate_label = QLabel("Rate (%):")
        self.tds_rate_label.setStyleSheet("font-size: 12px;")
        tds_row.addWidget(self.tds_rate_label)
        
        self.tds_rate_spin = QDoubleSpinBox()
        self.tds_rate_spin.setRange(0, 30)
        self.tds_rate_spin.setDecimals(1)
        self.tds_rate_spin.setSuffix(" %")
        self.tds_rate_spin.setMinimumWidth(80)
        self.tds_rate_spin.setMinimumHeight(30)
        tds_row.addWidget(self.tds_rate_spin)
        
        tds_row.addStretch()
        tds_layout.addLayout(tds_row)
        
        # TDS Ledger Dropdown (NEW - Req 1)
        tds_ledger_row = QHBoxLayout()
        tds_ledger_row.setSpacing(10)
        
        tds_ledger_label = QLabel("TDS Tally Ledger:")
        tds_ledger_label.setStyleSheet("font-size: 12px;")
        tds_ledger_row.addWidget(tds_ledger_label)
        
        self.tds_ledger_combo = QComboBox()
        self.tds_ledger_combo.setMinimumWidth(350)
        self.tds_ledger_combo.setMinimumHeight(30)
        self._populate_tds_ledgers()
        tds_ledger_row.addWidget(self.tds_ledger_combo)
        tds_ledger_row.addStretch()
        
        tds_layout.addLayout(tds_ledger_row)
        
        tax_layout.addWidget(self.tds_frame)
        self.tds_frame.setVisible(False)  # Hidden for credit vouchers
        
        layout.addWidget(tax_group)
        layout.addStretch()
        
        return widget
    
    def _create_step3(self) -> QWidget:
        """Step 3: Financial Details.
        
        CREDIT: Amount = Total (inclusive), NO TDS/Expense fields
        DEBIT: Base Amount + GST calculated on top, WITH TDS/Expense fields
        """
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # === VENDOR SECTION (DEBIT ONLY) ===
        self.vendor_group = QGroupBox("Vendor / Party Details")
        vendor_layout = QFormLayout(self.vendor_group)
        vendor_layout.setContentsMargins(12, 16, 12, 12)
        vendor_layout.setSpacing(10)
        
        self.vendor_name_input = QLineEdit()
        self.vendor_name_input.setMinimumHeight(32)
        self.vendor_name_input.setPlaceholderText("Enter vendor/party name...")
        vendor_layout.addRow("Vendor Name:", self.vendor_name_input)
        
        self.vendor_group.setVisible(False)  # Hidden for Credit by default
        layout.addWidget(self.vendor_group)
        
        # === AMOUNT SECTION ===
        amount_group = QGroupBox("Financial Details")
        amount_layout = QVBoxLayout(amount_group)
        amount_layout.setContentsMargins(12, 16, 12, 12)
        amount_layout.setSpacing(12)
        
        # Expense Details Field (DEBIT ONLY - Part 1 Req 2)
        self.expense_details_row = QWidget()
        expense_row_layout = QHBoxLayout(self.expense_details_row)
        expense_row_layout.setContentsMargins(0, 0, 0, 0)
        expense_row_layout.setSpacing(10)
        
        expense_label = QLabel("Expense Details:")
        expense_label.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {Styles.SECONDARY};")
        expense_label.setMinimumWidth(180)
        expense_row_layout.addWidget(expense_label)
        
        self.expense_details_input = QLineEdit()
        self.expense_details_input.setMinimumHeight(32)
        self.expense_details_input.setPlaceholderText("e.g., Monthly AWS Hosting charges")
        expense_row_layout.addWidget(self.expense_details_input)
        
        self.expense_details_row.setVisible(False)  # Hidden for Credit by default
        amount_layout.addWidget(self.expense_details_row)
        
        # Enter Amount Row (Label changes based on type)
        enter_row = QHBoxLayout()
        enter_row.setSpacing(10)
        
        self.amount_label = QLabel("Amount (₹) *:")  # Default for Credit
        self.amount_label.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {Styles.SECONDARY};")
        self.amount_label.setMinimumWidth(180)
        enter_row.addWidget(self.amount_label)
        
        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(1, 99999999.99)
        self.amount_input.setDecimals(2)
        self.amount_input.setPrefix("₹ ")
        self.amount_input.setGroupSeparatorShown(True)
        self.amount_input.setMinimumWidth(180)
        self.amount_input.setMinimumHeight(40)
        self.amount_input.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            padding: 8px;
        """)
        enter_row.addWidget(self.amount_input)
        enter_row.addStretch()
        
        amount_layout.addLayout(enter_row)
        
        # Gross Amount (calculated display) - Shows Base + GST for Debit
        calc_row = QHBoxLayout()
        calc_row.setSpacing(10)
        
        calc_label = QLabel("Gross Amount (Incl. GST):")
        calc_label.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {Styles.SECONDARY};")
        calc_label.setMinimumWidth(180)
        calc_row.addWidget(calc_label)
        
        self.gross_display = QLineEdit()
        self.gross_display.setReadOnly(True)
        self.gross_display.setMinimumWidth(180)
        self.gross_display.setMinimumHeight(36)
        self.gross_display.setStyleSheet(f"""
            background-color: {Styles.BG_SECONDARY};
            font-size: 16px;
            font-weight: bold;
            color: {Styles.PRIMARY};
            padding: 8px;
            border-radius: 4px;
        """)
        calc_row.addWidget(self.gross_display)
        calc_row.addStretch()
        
        amount_layout.addLayout(calc_row)
        
        # Tax Breakup Display
        self.tax_breakup_frame = QFrame()
        self.tax_breakup_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Styles.BG_SECONDARY};
                border: 1px solid {Styles.BORDER_LIGHT};
                border-radius: 4px;
                padding: 10px;
            }}
        """)
        breakup_layout = QVBoxLayout(self.tax_breakup_frame)
        breakup_layout.setSpacing(6)
        
        breakup_title = QLabel("Tax Breakup (Auto-Calculated)")
        breakup_title.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {Styles.SECONDARY};")
        breakup_layout.addWidget(breakup_title)
        
        self.taxable_label = QLabel("Base Amount: ₹0.00")
        self.taxable_label.setStyleSheet("font-size: 12px;")
        breakup_layout.addWidget(self.taxable_label)
        
        self.gst_amount_label = QLabel("+ GST: ₹0.00")
        self.gst_amount_label.setStyleSheet("font-size: 12px;")
        breakup_layout.addWidget(self.gst_amount_label)
        
        self.tds_amount_label = QLabel("- TDS/WHT: ₹0.00")
        self.tds_amount_label.setStyleSheet("font-size: 12px;")
        breakup_layout.addWidget(self.tds_amount_label)
        
        self.net_amount_label = QLabel("Net Payable: ₹0.00")
        self.net_amount_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {Styles.PRIMARY};")
        breakup_layout.addWidget(self.net_amount_label)
        
        # RCM Journal Entry Preview (DEBIT + Foreign Country ONLY)
        self.rcm_journal_frame = QFrame()
        self.rcm_journal_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #FFEBEE;
                border: 1px solid {Styles.ERROR};
                border-radius: 4px;
                padding: 8px;
                margin-top: 8px;
            }}
        """)
        rcm_layout = QVBoxLayout(self.rcm_journal_frame)
        rcm_layout.setSpacing(4)
        
        rcm_title = QLabel("RCM Journal Entry (Foreign Country - Reverse Charge)")
        rcm_title.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {Styles.ERROR};")
        rcm_layout.addWidget(rcm_title)
        
        self.rcm_entries_label = QLabel("")
        self.rcm_entries_label.setStyleSheet("font-size: 11px; font-family: monospace;")
        rcm_layout.addWidget(self.rcm_entries_label)
        
        self.rcm_journal_frame.setVisible(False)
        breakup_layout.addWidget(self.rcm_journal_frame)
        
        amount_layout.addWidget(self.tax_breakup_frame)
        
        layout.addWidget(amount_group)
        
        # Narration Section
        narr_group = QGroupBox("Narration")
        narr_layout = QVBoxLayout(narr_group)
        narr_layout.setContentsMargins(12, 16, 12, 12)
        narr_layout.setSpacing(8)
        
        # Auto-generate button (DEBIT ONLY - Part 1 Req 3)
        self.auto_narration_row = QWidget()
        auto_btn_layout = QHBoxLayout(self.auto_narration_row)
        auto_btn_layout.setContentsMargins(0, 0, 0, 0)
        
        self.auto_narration_btn = QPushButton("Auto-Generate Narration")
        self.auto_narration_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.INFO};
                color: {Styles.TEXT_LIGHT};
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: #1976D2; }}
        """)
        self.auto_narration_btn.setFixedHeight(28)
        self.auto_narration_btn.clicked.connect(self._auto_generate_narration)
        auto_btn_layout.addWidget(self.auto_narration_btn)
        auto_btn_layout.addStretch()
        
        self.auto_narration_row.setVisible(False)  # Hidden for Credit
        narr_layout.addWidget(self.auto_narration_row)
        
        self.narration_edit = QTextEdit()
        self.narration_edit.setMaximumHeight(80)
        self.narration_edit.setPlaceholderText("Enter transaction description / narration...")
        self.narration_edit.setStyleSheet(f"""
            font-size: 13px;
            padding: 8px;
            border: 1px solid {Styles.BORDER_MEDIUM};
            border-radius: 4px;
        """)
        narr_layout.addWidget(self.narration_edit)
        
        layout.addWidget(narr_group)
        layout.addStretch()
        
        return widget
    
    def _create_step4(self) -> QWidget:
        """Step 4: Confirm & Print Preview."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Preview Section
        preview_group = QGroupBox("Voucher Preview")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(12, 16, 12, 12)
        preview_layout.setSpacing(10)
        
        # Header Info
        self.preview_header = QFrame()
        self.preview_header.setStyleSheet(f"""
            QFrame {{
                background-color: {Styles.BG_SECONDARY};
                border: 1px solid {Styles.BORDER_LIGHT};
                border-radius: 4px;
                padding: 10px;
            }}
        """)
        header_layout = QHBoxLayout(self.preview_header)
        header_layout.setSpacing(20)
        
        self.preview_vno = QLabel("Voucher No: --")
        self.preview_vno.setStyleSheet("font-weight: bold; font-size: 13px;")
        header_layout.addWidget(self.preview_vno)
        
        self.preview_vdate = QLabel("Date: --")
        self.preview_vdate.setStyleSheet("font-size: 12px;")
        header_layout.addWidget(self.preview_vdate)
        
        self.preview_method = QLabel("Method: Manual")
        self.preview_method.setStyleSheet("font-size: 12px;")
        header_layout.addWidget(self.preview_method)
        
        self.preview_pos = QLabel("POS: --")
        self.preview_pos.setStyleSheet("font-size: 12px;")
        header_layout.addWidget(self.preview_pos)
        
        header_layout.addStretch()
        
        preview_layout.addWidget(self.preview_header)
        
        # Ledger Table
        self.preview_table = QTableWidget()
        self.preview_table.setMinimumHeight(180)
        self.preview_table.setMaximumHeight(220)
        self.preview_table.setColumnCount(4)
        self.preview_table.setHorizontalHeaderLabels(["Ledger", "Dr Amount", "Cr Amount", "Type"])
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.preview_table.setStyleSheet("""
            QTableWidget {
                font-size: 12px;
            }
            QHeaderView::section {
                background-color: #E0E0E0;
                font-weight: bold;
                padding: 6px;
            }
        """)
        preview_layout.addWidget(self.preview_table)
        
        # Totals Row
        totals_row = QHBoxLayout()
        totals_row.addStretch()
        
        self.preview_total_dr = QLabel("Total Dr: ₹0.00")
        self.preview_total_dr.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {Styles.ERROR};")
        totals_row.addWidget(self.preview_total_dr)
        
        self.preview_total_cr = QLabel("Total Cr: ₹0.00")
        self.preview_total_cr.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {Styles.SUCCESS};")
        totals_row.addWidget(self.preview_total_cr)
        
        preview_layout.addLayout(totals_row)
        
        # Narration Display
        self.preview_narration = QLabel("Narration: --")
        self.preview_narration.setStyleSheet(f"""
            background-color: {Styles.BG_SECONDARY};
            padding: 8px;
            border-radius: 4px;
            font-size: 12px;
        """)
        self.preview_narration.setWordWrap(True)
        preview_layout.addWidget(self.preview_narration)
        
        layout.addWidget(preview_group)
        
        # Confirmation buttons
        confirm_row = QHBoxLayout()
        confirm_row.setSpacing(12)
        
        confirm_row.addStretch()
        
        self.edit_btn = QPushButton("Edit Details")
        self.edit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.SECONDARY};
                color: {Styles.TEXT_LIGHT};
                border: none;
                border-radius: 4px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Styles.SECONDARY_LIGHT}; }}
        """)
        self.edit_btn.setFixedHeight(40)
        confirm_row.addWidget(self.edit_btn)
        
        self.confirm_btn = QPushButton("CONFIRM & SAVE")
        self.confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.SUCCESS};
                color: {Styles.TEXT_LIGHT};
                border: none;
                border-radius: 4px;
                padding: 10px 30px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background-color: #43A047; }}
        """)
        self.confirm_btn.setFixedHeight(44)
        confirm_row.addWidget(self.confirm_btn)
        
        layout.addLayout(confirm_row)
        layout.addStretch()
        
        return widget
    
    def _create_navigation(self) -> QHBoxLayout:
        """Create navigation buttons."""
        layout = QHBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(0, 8, 0, 0)
        
        self.reset_btn = QPushButton("Reset All")
        self.reset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.ERROR};
                color: {Styles.TEXT_LIGHT};
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: #E53935; }}
        """)
        self.reset_btn.setFixedHeight(38)
        layout.addWidget(self.reset_btn)
        
        layout.addStretch()
        
        self.back_btn = QPushButton("← Back")
        self.back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.SECONDARY};
                color: {Styles.TEXT_LIGHT};
                border: none;
                border-radius: 4px;
                padding: 10px 24px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Styles.SECONDARY_LIGHT}; }}
            QPushButton:disabled {{ background-color: {Styles.BORDER_LIGHT}; color: {Styles.TEXT_MUTED}; }}
        """)
        self.back_btn.setFixedHeight(38)
        self.back_btn.setEnabled(False)
        layout.addWidget(self.back_btn)
        
        self.next_btn = QPushButton("Next →")
        self.next_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.PRIMARY};
                color: {Styles.TEXT_LIGHT};
                border: none;
                border-radius: 4px;
                padding: 10px 30px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background-color: {Styles.PRIMARY_DARK}; }}
            QPushButton:disabled {{ background-color: {Styles.BORDER_LIGHT}; color: {Styles.TEXT_MUTED}; }}
        """)
        self.next_btn.setFixedHeight(40)
        layout.addWidget(self.next_btn)
        
        return layout
    
    def _get_date_style(self) -> str:
        return f"""
            QDateEdit {{
                padding: 6px 10px;
                border: 1px solid {Styles.BORDER_MEDIUM};
                border-radius: 4px;
                background-color: {Styles.BG_CARD};
                color: {Styles.TEXT_PRIMARY};
                font-size: 13px;
            }}
            QDateEdit::drop-down {{
                width: 24px;
                border-left: 1px solid {Styles.BORDER_LIGHT};
                background-color: {Styles.PRIMARY};
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
        """
    
    def _connect_signals(self):
        """Connect all signals."""
        # Type change
        self.type_group.buttonClicked.connect(self._on_type_changed)
        
        # Navigation
        self.next_btn.clicked.connect(self._on_next)
        self.back_btn.clicked.connect(self._on_back)
        self.reset_btn.clicked.connect(self._reset_form)
        
        # Step 1
        self.tally_head_combo.currentIndexChanged.connect(self._on_head_changed)
        self.voucher_date.dateChanged.connect(self._on_voucher_date_changed)
        self.from_date.dateChanged.connect(self._validate_step1)
        self.to_date.dateChanged.connect(self._validate_step1)
        
        # Step 2
        self.product_combo.currentIndexChanged.connect(self._update_voucher_code)
        self.pos_combo.currentIndexChanged.connect(self._on_pos_changed)
        self.gst_app_combo.currentIndexChanged.connect(self._on_gst_app_changed)
        self.gst_rate_combo.currentIndexChanged.connect(self._update_gst_split)
        self.tds_app_combo.currentIndexChanged.connect(self._on_tds_app_changed)
        
        # Step 3
        self.amount_input.valueChanged.connect(self._calculate_tax_breakup)
        
        # Step 4
        self.edit_btn.clicked.connect(lambda: self._go_to_step(3))
        self.confirm_btn.clicked.connect(self._on_confirm)
    
    # === Populate Methods ===
    
    def _populate_tally_heads(self):
        """Populate tally heads based on voucher type."""
        self.tally_head_combo.clear()
        self.tally_head_combo.addItem("-- Select Accounting Head --", None)
        
        heads = self.config.get_tally_heads(self._voucher_type)
        for head in heads:
            self.tally_head_combo.addItem(f"{head.code} - {head.name}", head.code)
    
    def _populate_countries(self, exclude_india: bool = False):
        """Populate countries dropdown.
        
        Args:
            exclude_india: If True, exclude India from list (for International heads).
        """
        self.country_combo.clear()
        countries = self.config.get_countries(exclude_india=exclude_india)
        default_idx = 0
        for i, country in enumerate(countries):
            self.country_combo.addItem(country.name, country.code)
            if country.is_default:
                default_idx = i
        self.country_combo.setCurrentIndex(default_idx)
    
    def _populate_products(self):
        self.product_combo.clear()
        products = self.config.get_products()
        for product in products:
            self.product_combo.addItem(product.name, product.code)
    
    def _populate_franchises(self):
        self.franchise_combo.clear()
        self.franchise_combo.addItem("-- Not Required --", None)
        franchises = self.config.get_franchises()
        for franchise in franchises:
            self.franchise_combo.addItem(f"{franchise.code} - {franchise.name}", franchise.code)
    
    def _populate_pos_states(self):
        self.pos_combo.clear()
        states = self.config.get_pos_states()
        home_idx = 0
        for i, state in enumerate(states):
            suffix = " (Home State)" if state.is_home_state else ""
            self.pos_combo.addItem(f"{state.name}{suffix}", state.code)
            if state.is_home_state:
                home_idx = i
        self.pos_combo.setCurrentIndex(home_idx)
    
    def _populate_gst_app(self):
        self.gst_app_combo.clear()
        options = self.config.get_gst_applicable_options()
        for opt in options:
            self.gst_app_combo.addItem(opt.name, opt.code)
    
    def _populate_gst_rates(self):
        self.gst_rate_combo.clear()
        rates = self.config.get_gst_rates()
        default_rate = self.config.get_default_gst_rate()
        default_idx = 0
        for i, rate in enumerate(rates):
            self.gst_rate_combo.addItem(f"{rate}%", rate)
            if rate == default_rate:
                default_idx = i
        self.gst_rate_combo.setCurrentIndex(default_idx)
    
    def _populate_tds_app(self):
        self.tds_app_combo.clear()
        options = self.config.get_tds_applicable_options()
        for opt in options:
            self.tds_app_combo.addItem(opt.name, opt.code)
    
    def _populate_business_segments(self):
        """Populate business segments dropdown."""
        self.segment_combo.clear()
        segments = self.config.get_business_segments()
        for seg in segments:
            self.segment_combo.addItem(seg.name, seg.code)
    
    def _populate_tds_ledgers(self):
        """Populate TDS ledgers dropdown for Tally mapping."""
        self.tds_ledger_combo.clear()
        self.tds_ledger_combo.addItem("-- Select TDS Ledger --", None)
        ledgers = self.config.get_tds_ledgers()
        for ledger in ledgers:
            self.tds_ledger_combo.addItem(ledger.label, ledger.code)
    
    # === Event Handlers ===
    
    def _on_type_changed(self, button):
        """Handle voucher type change - STRICT LOGIC SEPARATION.
        
        CREDIT: Amount = Total, HIDE TDS/Expense Details
        DEBIT: Amount = Base (excl. GST), SHOW TDS/Expense Details
        """
        self._voucher_type = "credit" if button == self.credit_radio else "debit"
        self._populate_tally_heads()
        
        # === PART 1 LOGIC SEPARATION ===
        if self._voucher_type == "credit":
            # CREDIT: Hide TDS and Expense Details
            self.tds_frame.setVisible(False)
            self.expense_details_row.setVisible(False)
            self.vendor_group.setVisible(False)
            
            # Amount label = "AMOUNT" (static total)
            self.amount_label.setText("Amount (₹) *:")
            
            # Update calculation mode
            self._gst_is_additive = False  # For credit, amount is total
            
        else:  # DEBIT
            # DEBIT: Show TDS and Expense Details
            self.tds_frame.setVisible(True)
            self.expense_details_row.setVisible(True)
            self.vendor_group.setVisible(True)
            
            # Amount label = "Base Amount (excl. GST)"
            self.amount_label.setText("Base Amount (excl. GST) *:")
            
            # Update calculation mode  
            self._gst_is_additive = True  # For debit, GST calculated on top
        
        self._update_voucher_code()
        self._reset_form_for_type_change()
    
    def _on_head_changed(self, index):
        """Handle tally head selection."""
        head_code = self.tally_head_combo.currentData()
        if head_code:
            head = self.config.get_tally_head_by_code(head_code, self._voucher_type)
            if head:
                info_parts = []
                if head.gst_applicable:
                    info_parts.append("GST Applicable")
                else:
                    info_parts.append("No GST")
                if head.requires_franchise:
                    info_parts.append("Franchise Required")
                if head.tds_section:
                    info_parts.append(f"TDS: {head.tds_section}")
                
                self.head_info_label.setText(" | ".join(info_parts))
                
                # Enable/disable franchise
                self.franchise_combo.setEnabled(head.requires_franchise)
                if head.requires_franchise:
                    self.franchise_required_label.setText("Franchise selection is required for this head")
                else:
                    self.franchise_required_label.setText("")
                
                # Set GST default
                if not head.gst_applicable:
                    self.gst_app_combo.setCurrentIndex(1)  # No
                
                # Set TDS rate
                if head.tds_section and self._voucher_type == "debit":
                    rate = self.config.get_tds_rate_for_section(head.tds_section)
                    self.tds_rate_spin.setValue(rate)
                    # Auto-select TDS ledger based on section
                    self._auto_select_tds_ledger(head.tds_section)
                
                # === Location Logic (Req 5) ===
                # If Domestic head: Default to India
                # If International head: Remove India from list
                if head.is_domestic is True:
                    # Domestic: Default Country = India
                    self._populate_countries(exclude_india=False)
                    # Find India and select it
                    india_idx = self.country_combo.findData("356")
                    if india_idx >= 0:
                        self.country_combo.setCurrentIndex(india_idx)
                    self.country_note_label.setText("Domestic head: Country defaulted to India")
                elif head.is_domestic is False:
                    # International: Remove India from list
                    self._populate_countries(exclude_india=True)
                    self.country_note_label.setText("International head: India removed from list")
                else:
                    # No restriction
                    self._populate_countries(exclude_india=False)
                    self.country_note_label.setText("")
        else:
            self.head_info_label.setText("")
            self.franchise_required_label.setText("")
            self.country_note_label.setText("")
        
        self._validate_step1()
    
    def _auto_select_tds_ledger(self, section: str):
        """Auto-select TDS ledger based on section."""
        ledgers = self.config.get_tds_ledgers()
        for i, ledger in enumerate(ledgers):
            if ledger.section == section:
                self.tds_ledger_combo.setCurrentIndex(i + 1)  # +1 for placeholder
                return
    
    def _on_voucher_date_changed(self):
        """Handle voucher date change."""
        self._set_default_dates()
        self._validate_step1()
    
    def _set_default_dates(self):
        """Set default from/to dates based on voucher date."""
        vdate = self.voucher_date.date().toPython()
        rules = self.config.get_validation_rules()
        period_days = rules.get("periodSuggestDays", 60)
        
        from_date = vdate - timedelta(days=period_days)
        self.from_date.setDate(QDate(from_date.year, from_date.month, from_date.day))
        self.to_date.setDate(QDate(vdate.year, vdate.month, vdate.day))
    
    def _on_pos_changed(self, index):
        """Handle Point of Supply change - auto-determine GST type and RCM."""
        state_code = self.pos_combo.currentData()
        if state_code:
            gst_type = self.config.determine_gst_type(state_code)
            is_foreign = self.config.is_pos_foreign(state_code)
            
            if is_foreign:
                # Foreign Country: Apply RCM, use Output GST for Debit vouchers
                self.gst_type_label.setText("GST Type: RCM (Reverse Charge)")
                self.pos_indicator.setText("Foreign - RCM")
                self.pos_indicator.setStyleSheet(f"color: {Styles.ERROR}; font-size: 11px; font-weight: bold;")
                self.rcm_indicator.setText("RCM applies: Output GST will be used (Reverse Charge)")
                self.rcm_indicator.setVisible(True)
                # RCM uses CGST+SGST regardless of state
                self.gst_split_label.setText("(Output CGST + Output SGST)")
            elif gst_type == "CGST_SGST":
                self.gst_type_label.setText("GST Type: CGST + SGST (Intra-State)")
                self.pos_indicator.setText("Intra-State")
                self.pos_indicator.setStyleSheet(f"color: {Styles.SUCCESS}; font-size: 11px; font-weight: bold;")
                self.rcm_indicator.setText("")
                self.rcm_indicator.setVisible(False)
                self._update_gst_split()
            else:
                self.gst_type_label.setText("GST Type: IGST (Inter-State)")
                self.pos_indicator.setText("Inter-State")
                self.pos_indicator.setStyleSheet(f"color: {Styles.WARNING}; font-size: 11px; font-weight: bold;")
                self.rcm_indicator.setText("")
                self.rcm_indicator.setVisible(False)
                self._update_gst_split()
            
            # Store RCM flag for later
            self._is_rcm = is_foreign
        else:
            self.rcm_indicator.setText("")
            self.rcm_indicator.setVisible(False)
            self._is_rcm = False
        
        self._validate_step2()
    
    def _on_gst_app_changed(self, index):
        """Handle GST applicable change."""
        is_applicable = self.gst_app_combo.currentData() == "Y"
        self.gst_details_frame.setVisible(is_applicable)
        self._validate_step2()
    
    def _update_gst_split(self):
        """Update GST split display."""
        rate = self.gst_rate_combo.currentData()
        if rate:
            state_code = self.pos_combo.currentData()
            gst_type = self.config.determine_gst_type(state_code) if state_code else "CGST_SGST"
            
            if gst_type == "CGST_SGST":
                half = rate / 2
                self.gst_split_label.setText(f"(CGST: {half}% + SGST: {half}%)")
            else:
                self.gst_split_label.setText(f"(IGST: {rate}%)")
    
    def _on_tds_app_changed(self, index):
        """Handle TDS applicable change."""
        is_applicable = self.tds_app_combo.currentData() == "Y"
        self.tds_rate_label.setEnabled(is_applicable)
        self.tds_rate_spin.setEnabled(is_applicable)
        if not is_applicable:
            self.tds_rate_spin.setValue(0)
        self._validate_step2()
    
    def _update_voucher_code(self):
        """Update auto-generated voucher code."""
        product_code = self.product_combo.currentData() or "MISC"
        code = self.config.generate_voucher_code(
            self._voucher_type, product_code, self._voucher_sequence
        )
        self.voucher_code_display.setText(code)
    
    def _calculate_tax_breakup(self):
        """Calculate and display tax breakup.
        
        CREDIT: Amount is TOTAL (inclusive of GST). Extract base from total.
        DEBIT: Amount is BASE (excl. GST). GST calculated ON TOP.
        """
        input_amount = self.amount_input.value()
        
        gst_applicable = self.gst_app_combo.currentData() == "Y"
        gst_rate = self.gst_rate_combo.currentData() or 0
        
        if self._voucher_type == "credit":
            # CREDIT: Amount is TOTAL (inclusive)
            # Extract: Base = Total / (1 + GST%)
            if gst_applicable and gst_rate > 0:
                base_amount = input_amount / (1 + gst_rate / 100)
                gst_amount = input_amount - base_amount
            else:
                base_amount = input_amount
                gst_amount = 0
            gross = input_amount  # Total entered
            
        else:  # DEBIT
            # DEBIT: Amount is BASE (excl. GST)
            # Calculate: GST = Base * GST%, Gross = Base + GST
            base_amount = input_amount
            if gst_applicable and gst_rate > 0:
                gst_amount = base_amount * (gst_rate / 100)
                gross = base_amount + gst_amount
            else:
                gst_amount = 0
                gross = base_amount
        
        # TDS (DEBIT only) - calculated on base amount
        tds_amount = 0
        if self._voucher_type == "debit" and self.tds_app_combo.currentData() == "Y":
            tds_rate = self.tds_rate_spin.value()
            tds_amount = base_amount * (tds_rate / 100)
        
        # Net Payable calculation
        is_rcm = getattr(self, '_is_rcm', False)
        if is_rcm and self._voucher_type == "debit":
            # RCM (Foreign Country): Party gets Base - TDS
            # GST is paid separately via reverse charge mechanism
            net_payable = base_amount - tds_amount
        else:
            net_payable = gross - tds_amount
        
        # Update display
        self.gross_display.setText(f"₹ {gross:,.2f}")
        
        if self._voucher_type == "credit":
            self.taxable_label.setText(f"Taxable Amount: ₹{base_amount:,.2f}")
        else:
            self.taxable_label.setText(f"Base Amount: ₹{base_amount:,.2f}")
        
        state_code = self.pos_combo.currentData()
        is_foreign = self.config.is_pos_foreign(state_code) if state_code else False
        gst_type = "CGST_SGST" if is_foreign else (self.config.determine_gst_type(state_code) if state_code else "CGST_SGST")
        
        if gst_applicable and gst_amount > 0:
            if is_foreign and self._voucher_type == "debit":
                # RCM: Output GST (reverse charge)
                half = gst_amount / 2
                self.gst_amount_label.setText(f"+ Output CGST: ₹{half:,.2f} + Output SGST: ₹{half:,.2f} = ₹{gst_amount:,.2f}")
            elif gst_type == "CGST_SGST":
                half = gst_amount / 2
                prefix = "+" if self._voucher_type == "debit" else ""
                self.gst_amount_label.setText(f"{prefix} CGST: ₹{half:,.2f} + SGST: ₹{half:,.2f} = ₹{gst_amount:,.2f}")
            else:
                prefix = "+" if self._voucher_type == "debit" else ""
                self.gst_amount_label.setText(f"{prefix} IGST: ₹{gst_amount:,.2f}")
        else:
            self.gst_amount_label.setText("GST: ₹0.00")
        
        # TDS display (DEBIT only)
        if self._voucher_type == "debit":
            self.tds_amount_label.setVisible(True)
            self.tds_amount_label.setText(f"- TDS/WHT: ₹{tds_amount:,.2f}")
            
            # Show RCM Journal Entry Preview (DEBIT + Foreign only)
            if is_rcm and gst_applicable:
                self._update_rcm_journal_preview(base_amount, gst_amount, tds_amount, net_payable)
            else:
                self.rcm_journal_frame.setVisible(False)
        else:
            self.tds_amount_label.setVisible(False)
            self.rcm_journal_frame.setVisible(False)
        
        self.net_amount_label.setText(f"Net Payable: ₹{net_payable:,.2f}")
        
        # Store for preview
        self._step_data['taxable'] = base_amount
        self._step_data['gst_amount'] = gst_amount
        self._step_data['tds_amount'] = tds_amount
        self._step_data['net_payable'] = net_payable
        self._step_data['gross_amount'] = gross
        self._step_data['gst_type'] = gst_type
        self._step_data['is_rcm'] = is_rcm
    
    def _update_rcm_journal_preview(self, base: float, gst: float, tds: float, net: float):
        """Update RCM Journal Entry preview (Req 3)."""
        half_gst = gst / 2
        tds_applicable = self.tds_app_combo.currentData() == "Y" and tds > 0
        
        entries = []
        entries.append(f"Dr  Expense Ledger          ₹{base:>12,.2f}")
        entries.append(f"Cr  Output SGST             ₹{half_gst:>12,.2f}")
        entries.append(f"Cr  Output CGST             ₹{half_gst:>12,.2f}")
        
        if tds_applicable:
            # Condition A: WHT applicable
            entries.append(f"Cr  TDS Payable             ₹{tds:>12,.2f}")
            entries.append(f"Cr  Party A/C (Net)         ₹{net:>12,.2f}")
        else:
            # Condition B: No WHT
            entries.append(f"Cr  Party A/C               ₹{base:>12,.2f}")
        
        self.rcm_entries_label.setText("\n".join(entries))
        self.rcm_journal_frame.setVisible(True)
    
    # === Validation ===
    
    def _validate_step1(self) -> bool:
        """Validate Step 1 fields."""
        errors = []
        
        # Head selection
        if not self.tally_head_combo.currentData():
            errors.append("Select Tally Accounting Head")
        
        # Voucher date (max 7 days backdate)
        vdate = self.voucher_date.date().toPython()
        today = date.today()
        rules = self.config.get_validation_rules()
        max_backdate = rules.get("maxBackdateDays", 7)
        
        if vdate > today:
            self.vdate_error.setText("Future date not allowed")
            errors.append("Voucher date cannot be future")
        elif (today - vdate).days > max_backdate:
            self.vdate_error.setText(f"Max {max_backdate} days backdate")
            errors.append(f"Voucher date max {max_backdate} days backdated")
        else:
            self.vdate_error.setText("")
        
        # Period validation
        from_d = self.from_date.date().toPython()
        to_d = self.to_date.date().toPython()
        
        if from_d > to_d:
            self.period_error.setText("From > To invalid")
            errors.append("From date cannot be after To date")
        elif to_d > vdate:
            self.period_error.setText("To > Voucher invalid")
            errors.append("To date cannot be after Voucher date")
        else:
            self.period_error.setText("")
        
        return len(errors) == 0
    
    def _validate_step2(self) -> bool:
        """Validate Step 2 fields."""
        errors = []
        
        # POS required
        if not self.pos_combo.currentData():
            errors.append("Select Point of Supply")
        
        # Franchise if required
        head_code = self.tally_head_combo.currentData()
        if head_code:
            head = self.config.get_tally_head_by_code(head_code, self._voucher_type)
            if head and head.requires_franchise and not self.franchise_combo.currentData():
                errors.append("Franchise required for selected head")
        
        return len(errors) == 0
    
    def _validate_step3(self) -> bool:
        """Validate Step 3 fields."""
        errors = []
        
        amount = self.amount_input.value()
        rules = self.config.get_validation_rules()
        
        if amount < rules.get("minAmount", 1):
            errors.append("Amount must be greater than zero")
        
        if amount > rules.get("maxAmount", 99999999.99):
            errors.append("Amount exceeds maximum limit")
        
        return len(errors) == 0
    
    def _auto_generate_narration(self):
        """Auto-generate narration (Req 2).
        
        Format: [Expense Details] for the period [Start Date] to [End Date] 
                purchased from [Vendor Name] for product [Product Name] 
                under Business Segment [Segment Name], [Country]
        """
        expense_details = self.expense_details_input.text().strip() or "Expense"
        vendor_name = self.vendor_name_input.text().strip() or "Vendor"
        
        # Get dates from Step 1
        from_date = self._step_data.get('from_date', self.from_date.date().toPython())
        to_date = self._step_data.get('to_date', self.to_date.date().toPython())
        
        # Format dates
        from_str = from_date.strftime("%d-%b-%Y") if from_date else ""
        to_str = to_date.strftime("%d-%b-%Y") if to_date else ""
        
        # Get product and segment from Step 2
        product_name = self.product_combo.currentText() or "N/A"
        segment_name = self.segment_combo.currentText() or "N/A"
        country_name = self.country_combo.currentText() or "N/A"
        
        # Build narration
        narration = (
            f"{expense_details} for the period {from_str} to {to_str} "
            f"purchased from {vendor_name} for product {product_name} "
            f"under Business Segment {segment_name}, {country_name}"
        )
        
        self.narration_edit.setText(narration)
    
    # === Navigation ===
    
    def _on_next(self):
        """Move to next step if valid."""
        if self._current_step == 1:
            if self._validate_step1():
                self._save_step1_data()
                self._go_to_step(2)
            else:
                QMessageBox.warning(self, "Validation", "Please complete all required fields in Step 1.")
        
        elif self._current_step == 2:
            if self._validate_step2():
                self._save_step2_data()
                self._go_to_step(3)
            else:
                QMessageBox.warning(self, "Validation", "Please complete all required fields in Step 2.")
        
        elif self._current_step == 3:
            if self._validate_step3():
                self._save_step3_data()
                self._build_preview()
                self._go_to_step(4)
            else:
                QMessageBox.warning(self, "Validation", "Please enter a valid amount.")
    
    def _on_back(self):
        """Move to previous step."""
        if self._current_step > 1:
            self._go_to_step(self._current_step - 1)
    
    def _go_to_step(self, step: int):
        """Go to specific step."""
        self._current_step = step
        self._update_step_visibility()
    
    def _update_step_visibility(self):
        """Update UI based on current step."""
        self.step_stack.setCurrentIndex(self._current_step - 1)
        
        # Update headers
        for i, header in enumerate(self.step_headers, 1):
            header.set_active(i == self._current_step)
            header.set_complete(i < self._current_step)
        
        # Update nav buttons
        self.back_btn.setEnabled(self._current_step > 1)
        self.next_btn.setVisible(self._current_step < 4)
    
    def _save_step1_data(self):
        """Save Step 1 data."""
        self._step_data['head_code'] = self.tally_head_combo.currentData()
        self._step_data['head_name'] = self.tally_head_combo.currentText()
        self._step_data['voucher_date'] = self.voucher_date.date().toPython()
        self._step_data['from_date'] = self.from_date.date().toPython()
        self._step_data['to_date'] = self.to_date.date().toPython()
    
    def _save_step2_data(self):
        """Save Step 2 data."""
        self._step_data['segment'] = self.segment_combo.currentData()
        self._step_data['segment_name'] = self.segment_combo.currentText()
        self._step_data['country'] = self.country_combo.currentData()
        self._step_data['country_name'] = self.country_combo.currentText()
        self._step_data['product'] = self.product_combo.currentData()
        self._step_data['product_name'] = self.product_combo.currentText()
        self._step_data['franchise'] = self.franchise_combo.currentData()
        self._step_data['voucher_code'] = self.voucher_code_display.text()
        self._step_data['pos_state'] = self.pos_combo.currentData()
        self._step_data['pos_name'] = self.pos_combo.currentText()
        self._step_data['gst_applicable'] = self.gst_app_combo.currentData() == "Y"
        self._step_data['gst_rate'] = self.gst_rate_combo.currentData() or 0
        self._step_data['is_rcm'] = getattr(self, '_is_rcm', False)
        
        if self._voucher_type == "debit":
            self._step_data['tds_applicable'] = self.tds_app_combo.currentData() == "Y"
            self._step_data['tds_rate'] = self.tds_rate_spin.value()
            self._step_data['tds_ledger'] = self.tds_ledger_combo.currentData()
            self._step_data['tds_ledger_name'] = self.tds_ledger_combo.currentText()
        else:
            self._step_data['tds_applicable'] = False
            self._step_data['tds_rate'] = 0
            self._step_data['tds_ledger'] = None
        
        self._update_voucher_code()
    
    def _save_step3_data(self):
        """Save Step 3 data."""
        self._step_data['vendor_name'] = self.vendor_name_input.text().strip()
        self._step_data['expense_details'] = self.expense_details_input.text().strip()
        self._step_data['base_amount'] = self.amount_input.value()
        self._step_data['narration'] = self.narration_edit.toPlainText()
        self._calculate_tax_breakup()
    
    def _build_preview(self):
        """Build preview display."""
        # Header
        self.preview_vno.setText(f"Voucher No: {self._step_data.get('voucher_code', '--')}")
        self.preview_vdate.setText(f"Date: {self._step_data.get('voucher_date', '--')}")
        self.preview_pos.setText(f"POS: {self._step_data.get('pos_name', '--')}")
        
        # Build ledger table
        self.preview_table.setRowCount(0)
        
        taxable = self._step_data.get('taxable', 0)
        gst_amount = self._step_data.get('gst_amount', 0)
        tds_amount = self._step_data.get('tds_amount', 0)
        gst_type = self._step_data.get('gst_type', 'CGST_SGST')
        head_name = self._step_data.get('head_name', '')
        
        total_dr = 0
        total_cr = 0
        
        if self._voucher_type == "credit":
            # Credit voucher: Dr Party, Cr Income + GST
            # Main ledger (Credit)
            self._add_preview_row(head_name, "", f"₹{taxable:,.2f}", "Income")
            total_cr += taxable
            
            # GST ledgers (Credit)
            if self._step_data.get('gst_applicable') and gst_amount > 0:
                gst_ledgers = self.config.get_gst_ledgers()
                if gst_type == "CGST_SGST":
                    half = gst_amount / 2
                    self._add_preview_row(gst_ledgers.get('outputCgst', 'Output CGST'), "", f"₹{half:,.2f}", "GST")
                    self._add_preview_row(gst_ledgers.get('outputSgst', 'Output SGST'), "", f"₹{half:,.2f}", "GST")
                    total_cr += gst_amount
                else:
                    self._add_preview_row(gst_ledgers.get('outputIgst', 'Output IGST'), "", f"₹{gst_amount:,.2f}", "GST")
                    total_cr += gst_amount
            
            # Party (Debit)
            gross = self._step_data.get('gross_amount', 0)
            self._add_preview_row("Party / Customer A/c", f"₹{gross:,.2f}", "", "Party")
            total_dr += gross
        
        else:
            # Debit voucher: Dr Expense + GST, Cr Party, Cr TDS
            # Main ledger (Debit)
            self._add_preview_row(head_name, f"₹{taxable:,.2f}", "", "Expense")
            total_dr += taxable
            
            # GST ledgers (Debit - Input)
            if self._step_data.get('gst_applicable') and gst_amount > 0:
                gst_ledgers = self.config.get_gst_ledgers()
                if gst_type == "CGST_SGST":
                    half = gst_amount / 2
                    self._add_preview_row(gst_ledgers.get('inputCgst', 'Input CGST'), f"₹{half:,.2f}", "", "GST")
                    self._add_preview_row(gst_ledgers.get('inputSgst', 'Input SGST'), f"₹{half:,.2f}", "", "GST")
                    total_dr += gst_amount
                else:
                    self._add_preview_row(gst_ledgers.get('inputIgst', 'Input IGST'), f"₹{gst_amount:,.2f}", "", "GST")
                    total_dr += gst_amount
            
            # TDS (Credit)
            if self._step_data.get('tds_applicable') and tds_amount > 0:
                self._add_preview_row("TDS Payable", "", f"₹{tds_amount:,.2f}", "TDS")
                total_cr += tds_amount
            
            # Party (Credit)
            net = self._step_data.get('net_payable', 0)
            self._add_preview_row("Vendor / Party A/c", "", f"₹{net:,.2f}", "Party")
            total_cr += net
        
        # Totals
        self.preview_total_dr.setText(f"Total Dr: ₹{total_dr:,.2f}")
        self.preview_total_cr.setText(f"Total Cr: ₹{total_cr:,.2f}")
        
        # Narration
        narration = self._step_data.get('narration', '')
        self.preview_narration.setText(f"Narration: {narration if narration else '(No narration)'}")
        
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    
    def _add_preview_row(self, ledger: str, dr: str, cr: str, row_type: str):
        """Add row to preview table."""
        row = self.preview_table.rowCount()
        self.preview_table.insertRow(row)
        
        self.preview_table.setItem(row, 0, QTableWidgetItem(ledger))
        self.preview_table.setItem(row, 1, QTableWidgetItem(dr))
        self.preview_table.setItem(row, 2, QTableWidgetItem(cr))
        self.preview_table.setItem(row, 3, QTableWidgetItem(row_type))
    
    def _on_confirm(self):
        """Confirm and save voucher."""
        reply = QMessageBox.question(
            self, "Confirm Voucher",
            f"Save this {self._voucher_type.upper()} voucher?\n\n"
            f"Amount: ₹{self._step_data.get('gross_amount', 0):,.2f}\n"
            f"Voucher Code: {self._step_data.get('voucher_code', '')}",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                voucher = self._create_voucher()
                self.data_service.add_voucher(voucher)
                self._voucher_sequence += 1
                
                QMessageBox.information(
                    self, "Success",
                    f"Voucher saved successfully!\n\nCode: {voucher.voucher_id[:8]}..."
                )
                
                self.voucher_saved.emit(voucher)
                self._reset_form()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save voucher:\n{e}")
    
    def _create_voucher(self) -> Voucher:
        """Create Voucher object from step data."""
        from datetime import datetime as dt
        
        vtype = VoucherType.CREDIT if self._voucher_type == "credit" else VoucherType.DEBIT
        
        return Voucher(
            date=dt.combine(self._step_data['voucher_date'], dt.min.time()),
            voucher_type=vtype,
            account_code=self._step_data.get('head_code', ''),
            account_name=self._step_data.get('head_name', ''),
            amount=self._step_data.get('gross_amount', 0),
            segment=self._step_data.get('product', ''),
            narration=self._step_data.get('narration', ''),
            reference_id=self._step_data.get('voucher_code', ''),
            status=VoucherStatus.PENDING_REVIEW,
            source="Manual - 4 Step",
            from_date=self._step_data.get('from_date'),
            to_date=self._step_data.get('to_date')
        )
    
    def _reset_form(self):
        """Reset entire form."""
        self._current_step = 1
        self._step_data = {}
        self._is_rcm = False
        self._gst_is_additive = self._voucher_type == "debit"
        
        # Reset Step 1
        self._populate_tally_heads()
        self._set_default_dates()
        self.head_info_label.setText("")
        self.vdate_error.setText("")
        self.period_error.setText("")
        
        # Reset Step 2
        self.segment_combo.setCurrentIndex(0)
        self._populate_countries(exclude_india=False)
        self.country_note_label.setText("")
        self.product_combo.setCurrentIndex(0)
        self.franchise_combo.setCurrentIndex(0)
        self.franchise_combo.setEnabled(False)
        self.franchise_required_label.setText("")
        self.gst_app_combo.setCurrentIndex(0)
        self.tds_app_combo.setCurrentIndex(1)  # No
        self.tds_rate_spin.setValue(0)
        self.tds_ledger_combo.setCurrentIndex(0)
        self.rcm_indicator.setText("")
        self.rcm_indicator.setVisible(False)
        self._update_voucher_code()
        
        # Reset Step 3 - Apply type-specific visibility
        self._apply_type_specific_ui()
        self.vendor_name_input.clear()
        self.expense_details_input.clear()
        self.amount_input.setValue(0)
        self.narration_edit.clear()
        self.gross_display.setText("")
        self.taxable_label.setText("Taxable Amount: ₹0.00" if self._voucher_type == "credit" else "Base Amount: ₹0.00")
        self.gst_amount_label.setText("GST: ₹0.00")
        self.tds_amount_label.setText("- TDS/WHT: ₹0.00")
        self.net_amount_label.setText("Net Payable: ₹0.00")
        self.rcm_journal_frame.setVisible(False)
        
        # Reset Step 4
        self.preview_table.setRowCount(0)
        
        self._update_step_visibility()
    
    def _reset_form_for_type_change(self):
        """Reset form when voucher type changes - maintains current step."""
        self._step_data = {}
        self._is_rcm = False
        self._gst_is_additive = self._voucher_type == "debit"
        
        # Apply type-specific UI visibility
        self._apply_type_specific_ui()
        
        # Reset Step 1
        self._set_default_dates()
        self.head_info_label.setText("")
        
        # Reset Step 2
        self._populate_countries(exclude_india=False)
        self.country_note_label.setText("")
        self.franchise_combo.setCurrentIndex(0)
        self.franchise_combo.setEnabled(False)
        self.franchise_required_label.setText("")
        self.gst_app_combo.setCurrentIndex(0)
        self.tds_app_combo.setCurrentIndex(1)
        self.tds_rate_spin.setValue(0)
        self.tds_ledger_combo.setCurrentIndex(0)
        self.rcm_indicator.setText("")
        self.rcm_indicator.setVisible(False)
        
        # Reset Step 3
        self.vendor_name_input.clear()
        self.expense_details_input.clear()
        self.amount_input.setValue(0)
        self.narration_edit.clear()
        self.gross_display.setText("")
        self.taxable_label.setText("Taxable Amount: ₹0.00" if self._voucher_type == "credit" else "Base Amount: ₹0.00")
        self.gst_amount_label.setText("GST: ₹0.00")
        self.tds_amount_label.setText("- TDS/WHT: ₹0.00")
        self.net_amount_label.setText("Net Payable: ₹0.00")
        self.rcm_journal_frame.setVisible(False)
        
        # Reset Step 4
        self.preview_table.setRowCount(0)
        
        # Return to Step 1
        self._current_step = 1
        self._update_step_visibility()
    
    def _apply_type_specific_ui(self):
        """Apply Credit/Debit specific UI visibility.
        
        CREDIT: HIDE TDS frame, Expense Details, Vendor section, Auto-narration
        DEBIT: SHOW all above fields
        """
        is_debit = self._voucher_type == "debit"
        
        # Step 2: TDS Configuration
        self.tds_frame.setVisible(is_debit)
        
        # Step 3: Vendor, Expense Details, Auto-narration
        self.vendor_group.setVisible(is_debit)
        self.expense_details_row.setVisible(is_debit)
        self.auto_narration_row.setVisible(is_debit)
        self.tds_amount_label.setVisible(is_debit)
        
        # Update Amount label
        if is_debit:
            self.amount_label.setText("Base Amount (excl. GST) *:")
        else:
            self.amount_label.setText("Amount (₹) *:")
