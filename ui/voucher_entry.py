"""Voucher Entry Tab - Manual Entry with Vendor Master & Invoice Details."""

from email import header
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QRadioButton, QButtonGroup,
    QPushButton, QGroupBox, QFrame, QMessageBox, QDoubleSpinBox,
    QDateEdit, QScrollArea, QSizePolicy, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QStackedWidget, QSpacerItem,QGridLayout
)

from PySide6.QtCore import Qt, Signal, QDate,QEvent
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtGui import QFont
from datetime import datetime, date, timedelta
from types import SimpleNamespace # Added for object creation

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
        layout.setSpacing(8)
        
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
        
        # Initial Population
        self._populate_voucher_types()
        # FIX: Force update of UI state based on default selections
        self._on_pos_changed(self.pos_combo.currentIndex())
        self._on_gst_app_changed(self.gst_app_combo.currentIndex())
        self._update_gst_split()
    
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)  # No gap between scroll and bottom bar

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Step Headers
        self.step_headers = []
        steps_container = QHBoxLayout()
        steps_container.setSpacing(6)
        
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
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        

        # === FIXED BOTTOM NAVIGATION BAR ===
        nav_container = QWidget()
        nav_container.setStyleSheet(f"""
            QWidget {{
                background-color: {Styles.BG_PRIMARY}; 
                border-top: 1px solid {Styles.BORDER_LIGHT};
            }}
        """)
        nav_layout = self._create_navigation()
        nav_layout.setContentsMargins(15, 10, 15, 10) # Fixed padding
        nav_container.setLayout(nav_layout)
        
        main_layout.addWidget(nav_container)
    
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
        self.credit_radio.setChecked(False)
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
        layout.setSpacing(5)
        layout.setContentsMargins(0,0,0,0)
        
        # === NEW LAYOUT: Single Group for Classification ===
        class_group = QGroupBox("Voucher Classification")
        class_layout = QGridLayout(class_group)
        class_layout.setContentsMargins(5, 5, 5, 5)
        class_layout.setHorizontalSpacing(10)
        class_layout.setVerticalSpacing(2)

        # Voucher Type
        type_label = QLabel("Voucher Type:")
        self.voucher_type_combo = QComboBox()
        self.voucher_type_combo.setMinimumWidth(150)
        self.voucher_type_combo.setFixedHeight(30)

        class_layout.addWidget(type_label, 0, 0)
        class_layout.addWidget(self.voucher_type_combo, 0, 1)

        # Tally Head
        head_label = QLabel("Tally Accounting Head: *")
        self.tally_head_combo = QComboBox()
        self.tally_head_combo.setPlaceholderText("-- Select Accounting Head --")
        self.tally_head_combo.setMinimumWidth(300)
        self.tally_head_combo.setFixedHeight(30)
        self.tally_head_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 8px 12px;
                border: 1px solid {Styles.BORDER_MEDIUM};
                border-radius: 4px;
                font-size: 13px;
                background-color: {Styles.BG_CARD};
            }}
        """)

        class_layout.addWidget(head_label, 0, 2)
        class_layout.addWidget(self.tally_head_combo, 0, 3)

        # Info label below head combo
        self.head_info_label = QLabel("")
        self.head_info_label.setStyleSheet(
            f"color: {Styles.TEXT_MUTED}; font-size: 11px;"
        )
        class_layout.addWidget(self.head_info_label, 1, 3)

        # Stretch so row doesn't expand awkwardly
        class_layout.setColumnStretch(4, 1)

        layout.addWidget(class_group)
        class_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        
        # === Date Fields Group (Unchanged) ===
        date_group = QGroupBox("Voucher Dates")
        date_layout = QVBoxLayout(date_group)
        date_layout.setContentsMargins(10, 6, 10, 6)
        date_layout.setSpacing(10)
        
        # Voucher Date
        vdate_row = QHBoxLayout()
        vdate_row.setSpacing(8)
        
        vdate_label = QLabel("Voucher Date:")
        vdate_label.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {Styles.SECONDARY};")
        vdate_label.setMinimumWidth(100)
        vdate_row.addWidget(vdate_label)
        
        self.voucher_date = QDateEdit()
        self.voucher_date.setDate(QDate.currentDate())
        self.voucher_date.setCalendarPopup(True)
        max_days = self.config.get_validation_rules().get("maxBackdateDays", 7)
        self.voucher_date.setMinimumDate(QDate.currentDate().addDays(-max_days))
        self.voucher_date.setMaximumDate(QDate.currentDate())
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
        period_row.setSpacing(8)
        
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
        date_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        
        self._set_default_dates()
        layout.setAlignment(Qt.AlignTop)
        return widget
    
    def _create_step2(self) -> QWidget:
        """Step 2: Voucher Settings & Tax Configuration."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Settings Section
        settings_group = QGroupBox("Voucher Settings")
        settings_layout = QFormLayout(settings_group)
        settings_layout.setContentsMargins(10, 6, 10, 6)
        settings_layout.setSpacing(10)
        
        # Business Segment
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
        tax_layout.setContentsMargins(10, 6, 10, 6)
        tax_layout.setSpacing(8)
        
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
        
        # RCM Indicator
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
        
        # TDS Ledger Dropdown
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
        """Step 3: Financial Details."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)

        FIELD_HEIGHT = 32
        LABEL_MIN_WIDTH = 110

        # ================= VENDOR SECTION =================
        self.vendor_group = QGroupBox("Vendor & Invoice Details")
        vendor_group_layout = QVBoxLayout(self.vendor_group)
        vendor_group_layout.setContentsMargins(10, 10, 10, 10)

        row_layout = QHBoxLayout()
        row_layout.setSpacing(8)
        row_layout.setContentsMargins(0, 4, 0, 4)

        lbl_vendor = QLabel("Vendor:")
        lbl_vendor.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {Styles.SECONDARY};")
        lbl_vendor.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_vendor.setMinimumWidth(LABEL_MIN_WIDTH)
        row_layout.addWidget(lbl_vendor)

        self.vendor_combo = QComboBox()
        self.vendor_combo.setEditable(True)
        self.vendor_combo.setMinimumWidth(340)
        self.vendor_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.vendor_combo.setFixedHeight(FIELD_HEIGHT)
        self.vendor_combo.setPlaceholderText("Select Vendor")
        self.vendor_combo.setInsertPolicy(QComboBox.NoInsert)
        self.vendor_combo.setMaxVisibleItems(20)
        self.vendor_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.vendor_combo.view().setMinimumWidth(500)

        line_edit = self.vendor_combo.lineEdit()
        def open_popup(event):
            self.vendor_combo.showPopup()
            QLineEdit.mousePressEvent(line_edit, event)
        line_edit.mousePressEvent = open_popup        

        self._populate_vendors()
        row_layout.addWidget(self.vendor_combo)

        lbl_inv = QLabel("Invoice No:")
        lbl_inv.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {Styles.SECONDARY};")
        lbl_inv.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_inv.setMinimumWidth(LABEL_MIN_WIDTH)
        row_layout.addWidget(lbl_inv)

        self.invoice_no_input = QLineEdit()
        self.invoice_no_input.setPlaceholderText("Inv #")
        self.invoice_no_input.setFixedWidth(120)
        self.invoice_no_input.setFixedHeight(FIELD_HEIGHT)
        row_layout.addWidget(self.invoice_no_input)

        lbl_date = QLabel("Date:")
        lbl_date.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {Styles.SECONDARY};")
        lbl_date.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_date.setMinimumWidth(LABEL_MIN_WIDTH)
        row_layout.addWidget(lbl_date)

        self.invoice_date_input = QDateEdit()
        self.invoice_date_input.setDate(QDate.currentDate())
        self.invoice_date_input.setCalendarPopup(True)
        self.invoice_date_input.setDisplayFormat("dd-MMM-yyyy")
        self.invoice_date_input.setFixedWidth(120)
        self.invoice_date_input.setFixedHeight(FIELD_HEIGHT)
        self.invoice_date_input.setStyleSheet(self._get_date_style())
        row_layout.addWidget(self.invoice_date_input)

        row_layout.addStretch()
        vendor_group_layout.addLayout(row_layout)

        self.vendor_group.setVisible(False)
        layout.addWidget(self.vendor_group)

        # ================= AMOUNT SECTION =================
        amount_group = QGroupBox("Financial Details")
        amount_layout = QVBoxLayout(amount_group)
        amount_layout.setContentsMargins(10, 6, 10, 6)
        amount_layout.setSpacing(8)

        self.expense_details_row = QWidget()
        expense_row_layout = QHBoxLayout(self.expense_details_row)
        expense_row_layout.setContentsMargins(0, 0, 0, 0)
        expense_row_layout.setSpacing(10)

        expense_label = QLabel("Expense Details:")
        expense_label.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {Styles.SECONDARY};")
        expense_label.setMinimumWidth(180)
        expense_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        expense_row_layout.addWidget(expense_label)

        self.expense_details_input = QLineEdit()
        self.expense_details_input.setMinimumHeight(FIELD_HEIGHT)
        self.expense_details_input.setPlaceholderText("e.g., Monthly AWS Hosting charges")
        expense_row_layout.addWidget(self.expense_details_input)

        self.expense_details_row.setVisible(False)
        amount_layout.addWidget(self.expense_details_row)

        enter_row = QHBoxLayout()
        enter_row.setSpacing(10)

        self.amount_label = QLabel("Amount (₹) *:")
        self.amount_label.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {Styles.SECONDARY};")
        self.amount_label.setMinimumWidth(180)
        self.amount_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        enter_row.addWidget(self.amount_label)

        self.amount_input = QDoubleSpinBox()
        self.amount_input.setRange(1, 99999999.99)
        self.amount_input.setDecimals(2)
        self.amount_input.setPrefix("₹ ")
        self.amount_input.setGroupSeparatorShown(True)
        self.amount_input.setMinimumWidth(180)
        self.amount_input.setMinimumHeight(38)
        self.amount_input.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            padding: 8px;
        """)
        enter_row.addWidget(self.amount_input)
        enter_row.addStretch()
        amount_layout.addLayout(enter_row)

        calc_row = QHBoxLayout()
        calc_row.setSpacing(10)

        calc_label = QLabel("Gross Amount (Incl. GST):")
        calc_label.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {Styles.SECONDARY};")
        calc_label.setMinimumWidth(180)
        calc_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
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
        breakup_layout.setSpacing(4)

        breakup_title = QLabel("Tax Breakup (Auto-Calculated)")
        breakup_title.setStyleSheet(
            f"font-weight: bold; font-size: 12px; color: {Styles.SECONDARY};"
        )
        breakup_layout.addWidget(breakup_title)

        self.taxable_label = QLabel("Base Amount: ₹0.00")
        breakup_layout.addWidget(self.taxable_label)

        self.gst_amount_label = QLabel("+ GST: ₹0.00")
        breakup_layout.addWidget(self.gst_amount_label)

        self.tds_amount_label = QLabel("- TDS/WHT: ₹0.00")
        breakup_layout.addWidget(self.tds_amount_label)

        self.net_amount_label = QLabel("Net Payable: ₹0.00")
        self.net_amount_label.setStyleSheet(
            f"font-weight: bold; font-size: 14px; color: {Styles.PRIMARY};"
        )
        breakup_layout.addWidget(self.net_amount_label)

        # --- RCM Frame ---
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
        rcm_title.setStyleSheet(
            f"font-weight: bold; font-size: 11px; color: {Styles.ERROR};"
        )
        rcm_layout.addWidget(rcm_title)

        self.rcm_entries_label = QLabel("")
        self.rcm_entries_label.setStyleSheet(
            "font-size: 11px; font-family: monospace;"
        )
        rcm_layout.addWidget(self.rcm_entries_label)

        self.rcm_journal_frame.setVisible(False)
        breakup_layout.addWidget(self.rcm_journal_frame)

        amount_layout.addWidget(self.tax_breakup_frame)
        layout.addWidget(amount_group)

        # ================= NARRATION =================
        narr_group = QGroupBox("Narration")
        narr_layout = QVBoxLayout(narr_group)
        narr_layout.setContentsMargins(10, 6, 10, 6)
        narr_layout.setSpacing(8)

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

        self.auto_narration_row.setVisible(False)
        narr_layout.addWidget(self.auto_narration_row)

        self.narration_edit = QTextEdit()
        self.narration_edit.setMaximumHeight(60)
        self.narration_edit.setPlaceholderText("Enter transaction description / narration...")
        self.narration_edit.setStyleSheet(f"""
            color: {Styles.PRIMARY};
            background-color: #ffffff;
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
        layout.setSpacing(8)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Preview Section
        preview_group = QGroupBox("Voucher Preview")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(10, 6, 10, 6)
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
        header = self.preview_table.horizontalHeader()

        header.setSectionResizeMode(0, QHeaderView.Stretch)          # Ledger expands
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents) # Dr
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # Cr
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # Type
        
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
        confirm_row.setSpacing(8)
        
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
            QPushButton:hover {{ background-color: {Styles.SUCCESS}; }}
        """)
        self.confirm_btn.setFixedHeight(44)
        confirm_row.addWidget(self.confirm_btn)
        
        layout.addLayout(confirm_row)
        layout.addStretch()
        
        return widget
    
    def _create_navigation(self) -> QHBoxLayout:
        """Create navigation buttons."""
        layout = QHBoxLayout()
        layout.setSpacing(8)
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
            QPushButton:hover {{ background-color: {Styles.ERROR}; }}
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
        #self.type_group.buttonClicked.connect(self._on_type_changed)
        self.credit_radio.toggled.connect(self._on_radio_toggled)
        self.debit_radio.toggled.connect(self._on_radio_toggled)
        
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
        """Populate countries dropdown."""
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
        """Populate TDS ledgers dropdown."""
        self.tds_ledger_combo.clear()
        self.tds_ledger_combo.addItem("-- Select TDS Ledger --", None)
        ledgers = self.config.get_tds_ledgers()
        for ledger in ledgers:
            self.tds_ledger_combo.addItem(ledger.label, ledger.code)

    def _populate_voucher_types(self):
        """Populate Voucher Type dropdown based on Credit/Debit selection."""
        self.voucher_type_combo.clear()
        if self._voucher_type == "credit":
            # Typical Credit voucher types
            self.voucher_type_combo.addItem("Receipt", "Receipt")
            self.voucher_type_combo.addItem("Sales", "Sales")
            self.voucher_type_combo.addItem("Credit Note", "Credit Note")
        else:
            # Typical Debit voucher types
            self.voucher_type_combo.addItem("Purchase", "Purchase")
            self.voucher_type_combo.addItem("Payment", "Payment")
            self.voucher_type_combo.addItem("Journal", "Journal")
            self.voucher_type_combo.addItem("Debit Note", "Debit Note")
            self.voucher_type_combo.addItem("Contra", "Contra")
            
    def _populate_vendors(self):
        """Populate Vendor Dropdown (Simulated for now)."""
        self.vendor_combo.clear()
        self.vendor_combo.addItem("-- Select or Enter Vendor Name --", None)
        
        # Load from Config Service
        vendors = self.config.get_all_vendors()
        for v in vendors:
            self.vendor_combo.addItem(v['name'], v['name'])
    
    # === Event Handlers ===
    
    def _on_type_changed(self, button):
        """Handle voucher type change (Debit/Credit) with full reset."""
        
        # 1. Determine New Type
        new_type = "credit" if button == self.credit_radio else "debit"
        
        # Optimization: If type is already selected, do nothing
        if self._voucher_type == new_type:
            return

        self._voucher_type = new_type
        
        # 2. Update UI Visibility based on Type
        if self._voucher_type == "credit":
            # CREDIT: Hide Debit-specific fields
            self.tds_frame.setVisible(False)
            self.expense_details_row.setVisible(False)
            self.vendor_group.setVisible(False)
            
            if hasattr(self, 'auto_narration_row'):
                self.auto_narration_row.setVisible(False)
            
            self.amount_label.setText("Gross Amount (incl. GST) (₹) *:")
            self._gst_is_additive = False 
        else:  
            # DEBIT: Show Debit-specific fields
            self.tds_frame.setVisible(True)
            self.expense_details_row.setVisible(True)
            self.vendor_group.setVisible(True)
            
            if hasattr(self, 'auto_narration_row'):
                self.auto_narration_row.setVisible(True)
            
            self.amount_label.setText("Base Amount (excl. GST) *:")
            self._gst_is_additive = True

        # 3. Refresh Dropdowns for the new type
        self._populate_voucher_types()
        self._populate_tally_heads()
        self._populate_vendors() 
        
        # 4. Perform Hard Reset (Clears all inputs and goes to Step 1)
        self._reset_form()
        
        # 5. Update Voucher Code
        self._update_voucher_code()
    
    def _on_head_changed(self, index):
        """Handle tally head selection."""
        head_code = self.tally_head_combo.currentData()
        if head_code:
            head = self.config.get_tally_head_by_code(head_code, self._voucher_type)
            if head:
                info_parts = []
                info_parts.append("GST Applicable" if head.gst_applicable else "No GST")
                if head.requires_franchise: info_parts.append("Franchise Required")
                if head.tds_section: info_parts.append(f"TDS: {head.tds_section}")
                
                self.head_info_label.setText(" | ".join(info_parts))
                self.franchise_combo.setEnabled(head.requires_franchise)
                if head.requires_franchise:
                    self.franchise_required_label.setText("Franchise selection is required for this head")
                else:
                    self.franchise_required_label.setText("")
                
                if not head.gst_applicable:
                    self.gst_app_combo.setCurrentIndex(1)  # No
                
                # Set TDS rate
                if head.tds_section and self._voucher_type == "debit":
                    rate = self.config.get_tds_rate_for_section(head.tds_section)
                    self.tds_rate_spin.setValue(rate)
                    self._auto_select_tds_ledger(head.tds_section)
                
                # Location Logic
                if head.is_domestic is True:
                    self._populate_countries(exclude_india=False)
                    idx = self.country_combo.findData("356")
                    if idx >= 0: self.country_combo.setCurrentIndex(idx)
                    self.country_note_label.setText("Domestic head: Country defaulted to India")
                elif head.is_domestic is False:
                    self._populate_countries(exclude_india=True)
                    self.country_note_label.setText("International head: India removed from list")
                else:
                    self._populate_countries(exclude_india=False)
                    self.country_note_label.setText("")
        else:
            self.head_info_label.setText("")
            self.franchise_required_label.setText("")
            self.country_note_label.setText("")
        
        self._validate_step1()
    
    def _auto_select_tds_ledger(self, section: str):
        ledgers = self.config.get_tds_ledgers()
        for i, ledger in enumerate(ledgers):
            if ledger.section == section:
                self.tds_ledger_combo.setCurrentIndex(i + 1)
                return
    
    def _on_voucher_date_changed(self):
        self._set_default_dates()
        self._validate_step1()
    
    def _set_default_dates(self):
        vdate = self.voucher_date.date().toPython()
        rules = self.config.get_validation_rules()
        period_days = rules.get("periodSuggestDays", 60)
        from_date = vdate - timedelta(days=period_days)
        self.from_date.setDate(QDate(from_date.year, from_date.month, from_date.day))
        self.to_date.setDate(QDate(vdate.year, vdate.month, vdate.day))
    
    def _on_pos_changed(self, index):
        state_code = self.pos_combo.currentData()
        if state_code:
            gst_type = self.config.determine_gst_type(state_code)
            is_foreign = self.config.is_pos_foreign(state_code)

            # CREDIT RULE:
            # - No RCM concept for sales.
            # - Domestic sales: GST can be applicable or not applicable.
            # - International sales: GST exempt (forced Not Applicable).
            if self._voucher_type == "credit":
                self.rcm_indicator.setVisible(False)
                self._is_rcm = False

                if is_foreign:
                    self.gst_type_label.setText("GST Type: Exempt (International Sales)")
                    self.pos_indicator.setText("International")
                    self.pos_indicator.setStyleSheet(f"color: {Styles.INFO}; font-size: 11px; font-weight: bold;")

                    # Force GST Not Applicable for international credit sales
                    self.gst_app_combo.setCurrentIndex(1)
                    self.gst_app_combo.setEnabled(False)
                    self.gst_details_frame.setVisible(False)
                    self.gst_split_label.setText("(GST Exempt)")
                elif gst_type == "CGST_SGST":
                    self.gst_type_label.setText("GST Type: CGST + SGST (Domestic Intra-State)")
                    self.pos_indicator.setText("Domestic - Intra-State")
                    self.pos_indicator.setStyleSheet(f"color: {Styles.SUCCESS}; font-size: 11px; font-weight: bold;")
                    self.gst_app_combo.setEnabled(True)
                    self._update_gst_split()
                else:
                    self.gst_type_label.setText("GST Type: IGST (Domestic Inter-State)")
                    self.pos_indicator.setText("Domestic - Inter-State")
                    self.pos_indicator.setStyleSheet(f"color: {Styles.WARNING}; font-size: 11px; font-weight: bold;")
                    self.gst_app_combo.setEnabled(True)
                    self._update_gst_split()

                self._on_gst_app_changed(self.gst_app_combo.currentIndex())
                self._validate_step2(show_message=False)
                return
            
            if is_foreign:
                self.gst_type_label.setText("GST Type: RCM (Reverse Charge)")
                self.pos_indicator.setText("Foreign - RCM")
                self.pos_indicator.setStyleSheet(f"color: {Styles.ERROR}; font-size: 11px; font-weight: bold;")
                self.rcm_indicator.setText("RCM applies: Output GST will be used (Reverse Charge)")
                self.rcm_indicator.setVisible(True)
                self.gst_split_label.setText("(Output CGST + Output SGST)")
            elif gst_type == "CGST_SGST":
                self.gst_type_label.setText("GST Type: CGST + SGST (Intra-State)")
                self.pos_indicator.setText("Intra-State")
                self.pos_indicator.setStyleSheet(f"color: {Styles.SUCCESS}; font-size: 11px; font-weight: bold;")
                self.rcm_indicator.setVisible(False)
                self._update_gst_split()
            else:
                self.gst_type_label.setText("GST Type: IGST (Inter-State)")
                self.pos_indicator.setText("Inter-State")
                self.pos_indicator.setStyleSheet(f"color: {Styles.WARNING}; font-size: 11px; font-weight: bold;")
                self.rcm_indicator.setVisible(False)
                self._update_gst_split()
            
            self._is_rcm = is_foreign
        else:
            self.rcm_indicator.setVisible(False)
            self._is_rcm = False
        
        self._validate_step2(show_message=False)
    
    def _on_gst_app_changed(self, index):
        is_applicable = self.gst_app_combo.currentData() == "Y"
        self.gst_details_frame.setVisible(is_applicable)
        self._validate_step2(show_message=False)
    
    def _update_gst_split(self):
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
        is_applicable = self.tds_app_combo.currentData() == "Y"
        self.tds_rate_label.setEnabled(is_applicable)
        self.tds_rate_spin.setEnabled(is_applicable)
        if not is_applicable: self.tds_rate_spin.setValue(0)
        self._validate_step2(show_message=False)
    
    def _update_voucher_code(self):
        product_code = self.product_combo.currentData() or "MISC"
        code = self.config.generate_voucher_code(
            self._voucher_type, product_code
        )
        self.voucher_code_display.setText(code)
    
    def _calculate_tax_breakup(self):
        input_amount = self.amount_input.value()
        gst_applicable = self.gst_app_combo.currentData() == "Y"
        gst_rate = self.gst_rate_combo.currentData() or 0
        
        if self._voucher_type == "credit":
            # CREDIT: Amount is TOTAL (inclusive)
            if gst_applicable and gst_rate > 0:
                base_amount = input_amount / (1 + gst_rate / 100)
                gst_amount = input_amount - base_amount
            else:
                base_amount = input_amount
                gst_amount = 0
            gross = input_amount
            
        else:  # DEBIT
            # DEBIT: Amount is BASE (excl. GST)
            base_amount = input_amount
            if gst_applicable and gst_rate > 0:
                gst_amount = base_amount * (gst_rate / 100)
                gross = base_amount + gst_amount
            else:
                gst_amount = 0
                gross = base_amount
        
        tds_amount = 0
        if self._voucher_type == "debit" and self.tds_app_combo.currentData() == "Y":
            tds_rate = self.tds_rate_spin.value()
            tds_amount = base_amount * (tds_rate / 100)
        
        is_rcm = getattr(self, '_is_rcm', False)
        if is_rcm and self._voucher_type == "debit":
            net_payable = base_amount - tds_amount
        else:
            net_payable = gross - tds_amount
        
        # Update display
        self.gross_display.setText(f"₹ {gross:,.2f}")
        self.taxable_label.setText(f"{'Base' if self._voucher_type=='debit' else 'Taxable'} Amount: ₹{base_amount:,.2f}")
        
        if gst_applicable and gst_amount > 0:
            self.gst_amount_label.setText(f"GST: ₹{gst_amount:,.2f}")
        else:
            self.gst_amount_label.setText("GST: ₹0.00")
        
        if self._voucher_type == "debit":
            self.tds_amount_label.setVisible(True)
            self.tds_amount_label.setText(f"- TDS/WHT: ₹{tds_amount:,.2f}")
            if is_rcm and gst_applicable:
                self._update_rcm_journal_preview(base_amount, gst_amount, tds_amount, net_payable)
            else:
                self.rcm_journal_frame.setVisible(False)
        else:
            self.tds_amount_label.setVisible(False)
            self.rcm_journal_frame.setVisible(False)
        
        self.net_amount_label.setText(f"Net Payable: ₹{net_payable:,.2f}")
        
        self._step_data.update({
            'taxable': base_amount, 'gst_amount': gst_amount,
            'tds_amount': tds_amount, 'net_payable': net_payable,
            'gross_amount': gross, 'is_rcm': is_rcm
        })
    
    def _update_rcm_journal_preview(self, base: float, gst: float, tds: float, net: float):
        half_gst = gst / 2
        entries = []
        entries.append(f"Dr  Expense Ledger          ₹{base:>12,.2f}")
        entries.append(f"Cr  Output SGST             ₹{half_gst:>12,.2f}")
        entries.append(f"Cr  Output CGST             ₹{half_gst:>12,.2f}")
        
        if tds > 0:
            entries.append(f"Cr  TDS Payable             ₹{tds:>12,.2f}")
            entries.append(f"Cr  Party A/C (Net)         ₹{net:>12,.2f}")
        else:
            entries.append(f"Cr  Party A/C               ₹{base:>12,.2f}")
        
        self.rcm_entries_label.setText("\n".join(entries))
        self.rcm_journal_frame.setVisible(True)
    
    # === Validation ===
    def _validate_step1(self) -> bool:
        if not self.tally_head_combo.currentData():
            return False
        return True

    def _is_b2b_segment(self, segment_code: str, segment_name: str) -> bool:
        """Treat Corporate segment as B2B for credit manual-entry routing."""
        code = (segment_code or "").strip().lower()
        name = (segment_name or "").strip().lower()
        return code == "corporate" or name == "corporate"
    
    def _validate_step2(self, show_message: bool = False) -> bool:
        if not self.pos_combo.currentData():
            return False

        if self._voucher_type == "credit":
            seg_code = self.segment_combo.currentData()
            seg_name = self.segment_combo.currentText()

            if not self._is_b2b_segment(seg_code, seg_name):
                if show_message:
                    QMessageBox.warning(
                        self,
                        "Routing Rule",
                        "Credit B2C transactions must be done through Bulk Import.\n"
                        "Only B2B (Corporate) credit transactions are allowed in manual entry."
                    )
                return False

        return True
    
    def _validate_step3(self) -> bool:
        amount = self.amount_input.value()
        if amount <= 0: 
            QMessageBox.warning(self, "Validation Error", "Amount must be greater than 0.")
            return False
            
        if self._voucher_type == "debit":
             vendor_text = self.vendor_combo.currentText().strip()
             
             # 1. Check if empty
             if not vendor_text or vendor_text == "-- Select or Enter Vendor Name --":
                 QMessageBox.warning(self, "Error", "Vendor Name is required")
                 return False
                 
             # 2. RESTRICT ADDITION: Check if exists in the list
             # We perform a case-insensitive check against the items in the dropdown
             found = False
             for i in range(self.vendor_combo.count()):
                 if self.vendor_combo.itemText(i).lower() == vendor_text.lower():
                     found = True
                     break
             
             if not found:
                 QMessageBox.warning(
                     self, 
                     "Restricted", 
                     "New vendors cannot be added here.\nPlease add them via 'Admin Settings > Vendor Master'."
                 )
                 return False

        return True
    
    def _auto_generate_narration(self):
        """Auto-generate narration based on available fields."""
        # Get dates
        from_str = self.from_date.date().toString("dd-MMM-yyyy")
        to_str = self.to_date.date().toString("dd-MMM-yyyy")
        period_str = f"for period {from_str} to {to_str}"
        
        # Get Invoice Info
        inv_no = self.invoice_no_input.text().strip()
        #inv_str = f"Inv:{inv_no}" if inv_no else ""

        # DEBIT FORMAT: [Expense] from [Vendor] [InvNo] [Period]
        exp = self.expense_details_input.text().strip() or "Expense"
        vnd = self.vendor_combo.currentText().strip()
        if not vnd or vnd.startswith("--"): vnd = "Vendor"
        
        self.narration_edit.setText(f"{exp} from {vnd} {period_str}")

    def _format_period_for_narration(self) -> str:
        """Return standardized period phrase for narration."""
        from_str = self.from_date.date().toString("dd-MMM-yyyy")
        to_str = self.to_date.date().toString("dd-MMM-yyyy")
        return f"for the period {from_str} to {to_str}"

    def _get_selected_franchise_name(self) -> str:
        """Return franchise name from master for selected franchise code."""
        franchise_code = self.franchise_combo.currentData()
        franchises = self.config.get_franchises()

        for franchise in franchises:
            if franchise.code == franchise_code:
                return franchise.name

        # Fallback for legacy display values like "CODE - Name"
        label = self.franchise_combo.currentText().strip()
        if " - " in label:
            return label.split(" - ", 1)[1].strip()

        return label

    def _generate_credit_manual_narration(self) -> str:
        """Generate credit narration as per business format."""
        free_text = self.narration_edit.toPlainText().strip() or "Sales billing"
        period_text = self._format_period_for_narration()

        franchise_name = self._get_selected_franchise_name()
        if not franchise_name or franchise_name.startswith("--"):
            franchise_name = "Franchisee"

        return f"{free_text}, {period_text} billed to {franchise_name}"
        
    
    # === Navigation ===
    def _on_next(self):
        if self._current_step == 1:
            if self._validate_step1():
                self._save_step1_data()
                self._go_to_step(2)
        elif self._current_step == 2:
            if self._validate_step2(show_message=True):
                self._save_step2_data()
                self._go_to_step(3)
        elif self._current_step == 3:
            if self._validate_step3():
                self._save_step3_data()
                self._build_preview()
                self._go_to_step(4)
    
    def _on_back(self):
        if self._current_step > 1: self._go_to_step(self._current_step - 1)
    
    def _go_to_step(self, step: int):
        self._current_step = step
        self._update_step_visibility()
    
    def _update_step_visibility(self):
        self.step_stack.setCurrentIndex(self._current_step - 1)
        for i, header in enumerate(self.step_headers, 1):
            header.set_active(i == self._current_step)
            header.set_complete(i < self._current_step)
        self.back_btn.setEnabled(self._current_step > 1)
        self.next_btn.setVisible(self._current_step < 4)
    
    def _save_step1_data(self):
        self._step_data['voucher_class'] = self.voucher_type_combo.currentText() # Save Voucher Type
        self._step_data['head_code'] = self.tally_head_combo.currentData()
        self._step_data['head_name'] = self.tally_head_combo.currentText()
        self._step_data['voucher_date'] = self.voucher_date.date().toPython()
        self._step_data['from_date'] = self.from_date.date().toPython()
        self._step_data['to_date'] = self.to_date.date().toPython()
    
    def _save_step2_data(self):
        self._step_data['segment'] = self.segment_combo.currentData()
        self._step_data['pos_name'] = self.pos_combo.currentText()
        self._step_data['voucher_code'] = self.voucher_code_display.text()
        self._step_data['gst_applicable'] = self.gst_app_combo.currentData() == "Y"
        self._step_data['tds_applicable'] = self.tds_app_combo.currentData() == "Y"
    
    def _save_step3_data(self):
        
        # self._populate_vendors()  # Refresh vendor list to include any new addition
        self._step_data['vendor_name'] = self.vendor_combo.currentText() # Get from Combo
        self._step_data['invoice_no'] = self.invoice_no_input.text()
        self._step_data['invoice_date'] = self.invoice_date_input.date().toPython()
        if self._voucher_type == "credit":
            self._step_data['narration'] = self._generate_credit_manual_narration()
        else:
            self._step_data['narration'] = self.narration_edit.toPlainText()
    
    def _build_preview(self):
        """Build the preview table and calculate totals."""
        self.preview_table.setRowCount(0)
        self.preview_vno.setText(f"Voucher No: {self._step_data.get('voucher_code', '--')}")
        self.preview_vdate.setText(f"Date: {self._step_data.get('voucher_date', '--')}")
        self.preview_pos.setText(f"POS: {self._step_data.get('pos_name', '--')}")
        
        # Get data
        taxable = self._step_data.get('taxable', 0.0)
        gst = self._step_data.get('gst_amount', 0.0)
        tds = self._step_data.get('tds_amount', 0.0)
        net = self._step_data.get('net_payable', 0.0)
        gross = self._step_data.get('gross_amount', 0.0)
        head_name = self._step_data.get('head_name', '')
        is_rcm = self._step_data.get('is_rcm', False)
        
        total_dr = 0.0
        total_cr = 0.0
        
        # === DEBIT VOUCHER PREVIEW ===
        if self._voucher_type == "debit":
             # 1. Dr Expense
             self._add_preview_row(head_name, f"₹{taxable:,.2f}", "", "Expense")
             total_dr += taxable
             
             # 2. Dr Input GST (Only if NOT RCM)
             if gst > 0 and not is_rcm:
                 self._add_preview_row("Input GST", f"₹{gst:,.2f}", "", "GST")
                 total_dr += gst
             
             # 3. Cr Vendor (Net Payable)
             vendor_display = self._step_data.get('vendor_name', 'Vendor / Party A/c')
             self._add_preview_row(vendor_display, "", f"₹{net:,.2f}", "Party")
             total_cr += net
             
             # 4. Cr TDS
             if tds > 0:
                 self._add_preview_row("TDS Payable", "", f"₹{tds:,.2f}", "TDS / WHT")
                 total_cr += tds
        
        # === CREDIT VOUCHER PREVIEW ===
        else: 
             # 1. Dr Party (Gross)
             franchise_name = self._get_selected_franchise_name() or "Party / Customer A/c"
             self._add_preview_row(franchise_name, f"₹{gross:,.2f}", "", "Party")
             total_dr += gross
             
             # 2. Cr Income
             self._add_preview_row(head_name, "", f"₹{taxable:,.2f}", "Income")
             total_cr += taxable
             
             # 3. Cr Output GST
             if gst > 0:
                 self._add_preview_row("Output GST", "", f"₹{gst:,.2f}", "GST")
                 total_cr += gst
                 
        self.preview_narration.setText(f"Narration: {self._step_data.get('narration', '')}")
        
        # === UPDATE TOTAL LABELS ===
        self.preview_total_dr.setText(f"Total Dr: ₹{total_dr:,.2f}")
        self.preview_total_cr.setText(f"Total Cr: ₹{total_cr:,.2f}")
        
        if abs(total_dr - total_cr) < 0.01:
            color = Styles.SUCCESS
        else:
            color = Styles.ERROR
            
        self.preview_total_dr.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {color};")
        self.preview_total_cr.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {color};")

    def _add_preview_row(self, ledger, dr, cr, row_type):
        row = self.preview_table.rowCount()
        self.preview_table.insertRow(row)
        self.preview_table.setItem(row, 0, QTableWidgetItem(ledger))
        self.preview_table.setItem(row, 1, QTableWidgetItem(dr))
        self.preview_table.setItem(row, 2, QTableWidgetItem(cr))
        self.preview_table.setItem(row, 3, QTableWidgetItem(row_type))

    def _on_confirm(self):
        try:
            vendor = self._step_data.get('vendor_name')
            inv_no = self._step_data.get('invoice_no')
            inv_date = self._step_data.get('invoice_date')
            
            if self._voucher_type == "credit":
                vendor = None
                inv_no = None
                inv_date = None

            v = Voucher(
                date=datetime.combine(self._step_data['voucher_date'], datetime.min.time()),
                voucher_type=VoucherType.CREDIT if self._voucher_type=="credit" else VoucherType.DEBIT,
                account_code=self._step_data.get('head_code'),
                amount=(self._step_data.get('taxable', 0) if self._voucher_type=="credit" else self._step_data.get('gross_amount', 0)),
                narration=self._step_data.get('narration', ''),
                reference_id=self._step_data.get('voucher_code', ''),
                status=VoucherStatus.PENDING_REVIEW,
                
                party_name=vendor,
                invoice_no=inv_no,
                invoice_date=inv_date
            )
            
            # === FIX FOR REVIEW TAB COMPATIBILITY ===
            # Explicitly save Tally Head Name for Review Screen
            v.tally_head = self._step_data.get('head_name')
            v.account_name = self._step_data.get('head_name')
            
            # Save breakdown for Pop-up Table
            v.base_amount = self._step_data.get('taxable', 0.0)
            v.net_payable = self._step_data.get('net_payable', 0.0)
            
            if self._voucher_type == "debit":
                v.expense_ledger = self._step_data.get('head_name')
                v.supplier_ledger = self._step_data.get('vendor_name')
            else:
                v.party_ledger = "Cash/Bank"
                v.expense_ledger = self._step_data.get('head_name') # Income ledger

            # Construct GST Object for Review Screen
            gst_amt = self._step_data.get('gst_amount', 0.0)
            if gst_amt > 0:
                v.gst = SimpleNamespace()
                v.gst.cgst_amount = gst_amt / 2 # simplified split
                v.gst.sgst_amount = gst_amt / 2
                v.gst.igst_amount = 0.0 
                # Note: Real app should check POS state here, but simplified is usually ok for view
            
            # Construct TDS Object for Review Screen
            tds_amt = self._step_data.get('tds_amount', 0.0)
            if tds_amt > 0:
                v.tds = SimpleNamespace()
                v.tds.amount = tds_amt
                v.tds.ledger_name = self.tds_ledger_combo.currentText()
            # ========================================
            
            self.data_service.add_voucher(v)
            QMessageBox.information(self, "Success", "Voucher saved successfully!")
            self.voucher_saved.emit(v)
            self._reset_form()
            
        except TypeError as e:
            QMessageBox.critical(self, "System Error", f"Model Mismatch: {str(e)}\nPlease check models/voucher.py")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")

    def _reset_form(self):
        """Completely reset the form to its initial state."""
        self._current_step = 1
        self._step_data = {}
        
        # 1. Reset Dropdowns
        self.tally_head_combo.setCurrentIndex(0)
        self.vendor_combo.setCurrentIndex(0)
        if hasattr(self, 'segment_combo'): self.segment_combo.setCurrentIndex(0)
        if hasattr(self, 'product_combo'): self.product_combo.setCurrentIndex(0)
        # Default GST to 'Yes' (index 0) and TDS to 'No' (index 1) usually
        if hasattr(self, 'gst_app_combo'): self.gst_app_combo.setCurrentIndex(0)
        if hasattr(self, 'tds_app_combo'): self.tds_app_combo.setCurrentIndex(1) 
        
        # 2. Clear Text Inputs
        self.invoice_no_input.clear()
        self.expense_details_input.clear()
        self.narration_edit.clear()
        
        # 3. Reset Numeric Inputs
        self.amount_input.setValue(0)
        if hasattr(self, 'tds_rate_spin'): self.tds_rate_spin.setValue(0)
        
        # 4. Reset Dates
        self.voucher_date.setDate(QDate.currentDate())
        self.invoice_date_input.setDate(QDate.currentDate())
        self._set_default_dates() # Resets 'From'/'To' period
        
        # 5. Clear Displays
        self.gross_display.clear()
        if hasattr(self, 'voucher_code_display'): 
             # Re-generate code for the clean form
             self._update_voucher_code()

        # 6. Force Navigation to Step 1
        self._go_to_step(1)
    
    def _reset_form_for_type_change(self):
        self._reset_form()

        
    def _populate_vendors(self):
        """Populate Vendor dropdown from Master Data."""
        self.vendor_combo.clear()
        self.vendor_combo.addItem("-- Select or Enter Vendor Name --", None)
        
        # Load from Config Service
        vendors = self.config.get_all_vendors()
        for v in vendors:
            self.vendor_combo.addItem(v['name'], v['name'])


    def showEvent(self, event):
        """Refresh data whenever the tab becomes visible."""
        super().showEvent(event)
        self._populate_vendors()
        self._populate_tally_heads()

    def _on_radio_toggled(self, checked):
        """Handle individual radio toggle."""
        if not checked: 
            return # Ignore the 'unchecked' event, only handle the one turning True
            
        # Identify which button triggered it
        sender = self.sender()
        self._on_type_changed(sender)   
