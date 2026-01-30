"""Bulk Import Tab - CSV file import interface with period dates and Voucher Type routing."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QFrame, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QProgressBar, QComboBox, QScrollArea, QButtonGroup, QRadioButton,
    QDateEdit
)
from PySide6.QtCore import Qt, Signal, QDate
from datetime import date
import os

from models.import_result import ImportResult, ImportStatus
from models.debit_voucher import DebitVoucherType
from services.import_service import ImportService
from services.debit_voucher_service import DebitVoucherImportService
from services.data_service import DataService
from services.voucher_config_service import get_voucher_config
from .styles import Styles


class BulkImportTab(QWidget):
    """
    Bulk CSV import interface with mandatory Voucher Type and Period selection.
    
    Flow: Voucher Type → Period Dates → Import Type → Upload File → Preview → Import
    """
    
    import_completed = Signal(ImportResult)
    
    def __init__(self, data_service: DataService, parent=None):
        super().__init__(parent)
        self.data_service = data_service
        self.import_service = ImportService()
        self.debit_import_service = DebitVoucherImportService()
        self.config = get_voucher_config()
        
        self._current_filepath = None
        self._current_result = None
        self._imported_vouchers = []
        self._selected_voucher_type = None  # 'Credit' or 'Debit'
        self._selected_import_type = None
        self._selected_tally_head = None
        self._selected_pos = None
        
        self._setup_ui()
        self._connect_signals()
        self._update_ui_state()
    
    def _setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Step 1: Voucher Type Selection (MANDATORY)
        voucher_type_section = self._create_voucher_type_section()
        layout.addWidget(voucher_type_section)
        
        # Step 2: Period Dates (MANDATORY for Bulk)
        period_section = self._create_period_section()
        layout.addWidget(period_section)
        
        # Step 2.5: Tally Head & Point of Supply (MANDATORY - aligns with manual entry)
        accounting_section = self._create_accounting_section()
        layout.addWidget(accounting_section)
        
        # Step 3: Import Type Selection (Depends on Voucher Type)
        import_type_section = self._create_import_type_section()
        layout.addWidget(import_type_section)
        
        # Step 4: File Upload
        upload_section = self._create_upload_section()
        layout.addWidget(upload_section)
        
        # Summary Section
        summary_section = self._create_summary_section()
        layout.addWidget(summary_section)
        
        # Preview Section
        preview_section = self._create_preview_section()
        layout.addWidget(preview_section)
        
        # Action Buttons
        buttons = self._create_buttons()
        layout.addLayout(buttons)
        
        layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
    
    def _create_header(self) -> QFrame:
        """Create the header section."""
        header = QFrame()
        header.setStyleSheet(f"""
            background-color: {Styles.SECONDARY};
            padding: 10px;
            border-radius: 6px;
        """)
        layout = QVBoxLayout(header)
        layout.setSpacing(3)
        layout.setContentsMargins(10, 8, 10, 8)
        
        title = QLabel("Bulk Import - CSV")
        title.setStyleSheet(f"color: {Styles.TEXT_LIGHT}; font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        subtitle = QLabel("Import vouchers from CSV. Select Type → Period → Format → Upload")
        subtitle.setStyleSheet(f"color: {Styles.TEXT_LIGHT}; font-size: 11px;")
        layout.addWidget(subtitle)
        
        return header
    
    def _create_voucher_type_section(self) -> QGroupBox:
        """Create the Voucher Type selection section (Step 1 - MANDATORY)."""
        group = QGroupBox("STEP 1: VOUCHER TYPE (Required)")
        group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 12px;
                color: {Styles.SECONDARY};
                border: 2px solid {Styles.PRIMARY};
                border-radius: 6px;
                margin-top: 10px;
                padding: 10px 8px 8px 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 6px;
                background-color: {Styles.BG_CARD};
                color: {Styles.PRIMARY};
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        
        layout = QHBoxLayout(group)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 14, 10, 10)
        
        instruction = QLabel("Select type:")
        instruction.setStyleSheet(f"color: {Styles.TEXT_PRIMARY}; font-size: 12px;")
        layout.addWidget(instruction)
        
        # Radio buttons for Credit/Debit
        self.voucher_type_group = QButtonGroup(self)
        
        # Credit option
        credit_frame = QFrame()
        credit_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Styles.BG_SECONDARY};
                border: 1px solid {Styles.BORDER_LIGHT};
                border-radius: 4px;
                padding: 8px;
            }}
            QFrame:hover {{
                border-color: {Styles.SUCCESS};
            }}
        """)
        credit_layout = QVBoxLayout(credit_frame)
        credit_layout.setSpacing(2)
        credit_layout.setContentsMargins(8, 6, 8, 6)
        
        self.credit_radio = QRadioButton("CREDIT")
        self.credit_radio.setStyleSheet(f"""
            QRadioButton {{
                font-size: 13px;
                font-weight: bold;
                color: {Styles.SUCCESS};
            }}
        """)
        credit_layout.addWidget(self.credit_radio)
        
        credit_desc = QLabel("Income / Sales")
        credit_desc.setStyleSheet(f"color: {Styles.TEXT_SECONDARY}; font-size: 10px;")
        credit_layout.addWidget(credit_desc)
        
        self.voucher_type_group.addButton(self.credit_radio, 0)
        layout.addWidget(credit_frame)
        
        # Debit option
        debit_frame = QFrame()
        debit_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Styles.BG_SECONDARY};
                border: 1px solid {Styles.BORDER_LIGHT};
                border-radius: 4px;
                padding: 8px;
            }}
            QFrame:hover {{
                border-color: {Styles.ERROR};
            }}
        """)
        debit_layout = QVBoxLayout(debit_frame)
        debit_layout.setSpacing(2)
        debit_layout.setContentsMargins(8, 6, 8, 6)
        
        self.debit_radio = QRadioButton("DEBIT")
        self.debit_radio.setStyleSheet(f"""
            QRadioButton {{
                font-size: 13px;
                font-weight: bold;
                color: {Styles.ERROR};
            }}
        """)
        debit_layout.addWidget(self.debit_radio)
        
        debit_desc = QLabel("Expenses / Purchases")
        debit_desc.setStyleSheet(f"color: {Styles.TEXT_SECONDARY}; font-size: 10px;")
        debit_layout.addWidget(debit_desc)
        
        self.voucher_type_group.addButton(self.debit_radio, 1)
        layout.addWidget(debit_frame)
        
        layout.addStretch()
        
        # Status indicator
        self.voucher_type_status = QLabel("⚠ Select voucher type")
        self.voucher_type_status.setStyleSheet(f"color: {Styles.WARNING}; font-size: 11px; font-weight: bold;")
        layout.addWidget(self.voucher_type_status)
        
        return group
    
    def _create_period_section(self) -> QGroupBox:
        """Create the Period Dates section (Step 2 - MANDATORY for Bulk)."""
        group = QGroupBox("STEP 2: PERIOD DATES (Required)")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 14, 10, 10)
        
        # Date row
        date_row = QHBoxLayout()
        date_row.setSpacing(12)
        
        # Voucher Date
        vdate_label = QLabel("Voucher Date:")
        vdate_label.setStyleSheet(f"color: {Styles.SECONDARY}; font-size: 11px; font-weight: 600;")
        date_row.addWidget(vdate_label)
        
        self.voucher_date_edit = QDateEdit()
        self.voucher_date_edit.setDate(QDate.currentDate())
        self.voucher_date_edit.setCalendarPopup(True)
        self.voucher_date_edit.setDisplayFormat("dd-MMM-yyyy")
        self.voucher_date_edit.setMinimumWidth(120)
        self.voucher_date_edit.setFixedHeight(30)
        self.voucher_date_edit.setStyleSheet(f"""
            QDateEdit {{
                padding: 4px 8px;
                border: 1px solid {Styles.BORDER_MEDIUM};
                border-radius: 4px;
                background-color: {Styles.BG_CARD};
                color: {Styles.TEXT_PRIMARY};
                font-size: 12px;
            }}
            QDateEdit::drop-down {{
                width: 22px;
                border-left: 1px solid {Styles.BORDER_LIGHT};
                background-color: {Styles.PRIMARY};
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
        """)
        date_row.addWidget(self.voucher_date_edit)
        
        # Separator
        sep = QLabel("|")
        sep.setStyleSheet(f"color: {Styles.BORDER_MEDIUM}; font-size: 14px;")
        date_row.addWidget(sep)
        
        # From Date
        from_label = QLabel("From:")
        from_label.setStyleSheet(f"color: {Styles.TEXT_SECONDARY}; font-size: 12px;")
        date_row.addWidget(from_label)
        
        self.from_date_edit = QDateEdit()
        self.from_date_edit.setDate(QDate.currentDate())
        self.from_date_edit.setCalendarPopup(True)
        self.from_date_edit.setDisplayFormat("dd-MMM-yyyy")
        self.from_date_edit.setMinimumWidth(115)
        self.from_date_edit.setFixedHeight(28)
        self.from_date_edit.setStyleSheet(f"""
            QDateEdit {{
                padding: 4px 6px;
                border: 1px solid {Styles.BORDER_MEDIUM};
                border-radius: 4px;
                background-color: {Styles.BG_CARD};
                color: {Styles.TEXT_PRIMARY};
                font-size: 12px;
            }}
            QDateEdit::drop-down {{
                width: 20px;
                border-left: 1px solid {Styles.BORDER_LIGHT};
                background-color: {Styles.PRIMARY};
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
        """)
        date_row.addWidget(self.from_date_edit)
        
        # To Date
        to_label = QLabel("To:")
        to_label.setStyleSheet(f"color: {Styles.TEXT_SECONDARY}; font-size: 12px;")
        date_row.addWidget(to_label)
        
        self.to_date_edit = QDateEdit()
        self.to_date_edit.setDate(QDate.currentDate())
        self.to_date_edit.setCalendarPopup(True)
        self.to_date_edit.setDisplayFormat("dd-MMM-yyyy")
        self.to_date_edit.setMinimumWidth(115)
        self.to_date_edit.setFixedHeight(28)
        self.to_date_edit.setStyleSheet(f"""
            QDateEdit {{
                padding: 4px 6px;
                border: 1px solid {Styles.BORDER_MEDIUM};
                border-radius: 4px;
                background-color: {Styles.BG_CARD};
                color: {Styles.TEXT_PRIMARY};
                font-size: 12px;
            }}
            QDateEdit::drop-down {{
                width: 20px;
                border-left: 1px solid {Styles.BORDER_LIGHT};
                background-color: {Styles.PRIMARY};
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
        """)
        date_row.addWidget(self.to_date_edit)
        
        # Error label
        self.period_error = QLabel("")
        self.period_error.setStyleSheet(Styles.get_error_label_style())
        self.period_error.setVisible(False)
        date_row.addWidget(self.period_error)
        
        date_row.addStretch()
        layout.addLayout(date_row)
        
        # Helper text
        helper = QLabel("Bulk imports always represent a period summary. Both dates are mandatory.")
        helper.setStyleSheet(Styles.get_helper_text_style())
        layout.addWidget(helper)
        
        return group
    
    def _create_accounting_section(self) -> QGroupBox:
        """Create the Tally Head & Point of Supply section (Step 2.5)."""
        group = QGroupBox("STEP 2.5: ACCOUNTING CLASSIFICATION (Required)")
        group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                font-size: 12px;
                color: {Styles.SECONDARY};
                border: 2px solid {Styles.INFO};
                border-radius: 6px;
                margin-top: 10px;
                padding: 10px 8px 8px 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 6px;
                background-color: {Styles.BG_CARD};
                color: {Styles.INFO};
                font-size: 11px;
                font-weight: bold;
            }}
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 14, 10, 10)
        
        # Row 1: Tally Accounting Head
        head_row = QHBoxLayout()
        head_row.setSpacing(10)
        
        head_label = QLabel("Tally Accounting Head:")
        head_label.setStyleSheet(f"color: {Styles.SECONDARY}; font-size: 11px; font-weight: 600;")
        head_label.setMinimumWidth(140)
        head_row.addWidget(head_label)
        
        self.bulk_tally_head_combo = QComboBox()
        self.bulk_tally_head_combo.setPlaceholderText("-- Select Accounting Head --")
        self.bulk_tally_head_combo.setMinimumWidth(280)
        self.bulk_tally_head_combo.setFixedHeight(32)
        self.bulk_tally_head_combo.setEnabled(False)
        head_row.addWidget(self.bulk_tally_head_combo)
        
        self.head_info_label = QLabel("")
        self.head_info_label.setStyleSheet(f"color: {Styles.TEXT_MUTED}; font-size: 10px;")
        head_row.addWidget(self.head_info_label)
        head_row.addStretch()
        
        layout.addLayout(head_row)
        
        # Row 2: Point of Supply
        pos_row = QHBoxLayout()
        pos_row.setSpacing(10)
        
        pos_label = QLabel("Point of Supply (State):")
        pos_label.setStyleSheet(f"color: {Styles.SECONDARY}; font-size: 11px; font-weight: 600;")
        pos_label.setMinimumWidth(140)
        pos_row.addWidget(pos_label)
        
        self.bulk_pos_combo = QComboBox()
        self.bulk_pos_combo.setPlaceholderText("-- Select State --")
        self.bulk_pos_combo.setMinimumWidth(200)
        self.bulk_pos_combo.setFixedHeight(32)
        self.bulk_pos_combo.setEnabled(False)
        pos_row.addWidget(self.bulk_pos_combo)
        
        self.pos_gst_indicator = QLabel("")
        self.pos_gst_indicator.setStyleSheet("font-size: 11px; font-weight: bold;")
        pos_row.addWidget(self.pos_gst_indicator)
        pos_row.addStretch()
        
        layout.addLayout(pos_row)
        
        # Helper
        helper = QLabel("Same classification used for all vouchers in this import. GST type auto-determined by Point of Supply.")
        helper.setStyleSheet(Styles.get_helper_text_style())
        layout.addWidget(helper)
        
        return group
    
    def _create_import_type_section(self) -> QGroupBox:
        """Create the Import Type selection section (Step 3)."""
        group = QGroupBox("STEP 3: IMPORT FORMAT")
        layout = QHBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(10, 14, 10, 10)
        
        label = QLabel("Format:")
        label.setStyleSheet(f"color: {Styles.SECONDARY}; font-size: 11px; font-weight: 600;")
        layout.addWidget(label)
        
        self.import_type_combo = QComboBox()
        self.import_type_combo.setPlaceholderText("-- First select Voucher Type --")
        self.import_type_combo.setMinimumWidth(250)
        self.import_type_combo.setFixedHeight(30)
        self.import_type_combo.setEnabled(False)
        layout.addWidget(self.import_type_combo)
        
        # Info label
        self.import_type_info = QLabel("")
        self.import_type_info.setStyleSheet(f"color: {Styles.TEXT_MUTED}; font-size: 10px;")
        self.import_type_info.setWordWrap(True)
        layout.addWidget(self.import_type_info, 1)
        
        return group
    
    def _create_upload_section(self) -> QGroupBox:
        """Create the file upload section (Step 4)."""
        group = QGroupBox("STEP 4: UPLOAD FILE")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 14, 10, 10)
        
        # File Selection Row
        file_row = QHBoxLayout()
        file_row.setSpacing(10)
        
        file_label = QLabel("File:")
        file_label.setStyleSheet(f"color: {Styles.SECONDARY}; font-size: 11px; font-weight: 600;")
        file_row.addWidget(file_label)
        
        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setStyleSheet(f"""
            color: {Styles.TEXT_MUTED}; 
            font-style: italic;
            font-size: 12px;
            padding: 6px 10px;
            background-color: {Styles.BG_SECONDARY};
            border-radius: 4px;
        """)
        self.file_path_label.setMinimumWidth(250)
        file_row.addWidget(self.file_path_label, 1)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.PRIMARY};
                color: {Styles.TEXT_LIGHT};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Styles.PRIMARY_DARK}; }}
            QPushButton:disabled {{ background-color: {Styles.BORDER_LIGHT}; color: {Styles.TEXT_MUTED}; }}
        """)
        self.browse_btn.setFixedHeight(34)
        self.browse_btn.setFixedWidth(110)
        self.browse_btn.setEnabled(False)
        file_row.addWidget(self.browse_btn)
        
        layout.addLayout(file_row)
        
        # Disabled reason label
        self.upload_disabled_label = QLabel("⚠ Complete Steps 1-3 and set valid period dates")
        self.upload_disabled_label.setStyleSheet(f"color: {Styles.WARNING}; font-size: 10px;")
        layout.addWidget(self.upload_disabled_label)
        
        return group
    
    def _create_summary_section(self) -> QFrame:
        """Create the import summary section - compact one-line format."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Styles.BG_CARD};
                border: 1px solid {Styles.BORDER_LIGHT};
                border-radius: 6px;
                padding: 8px 12px;
            }}
        """)
        
        layout = QHBoxLayout(frame)
        layout.setSpacing(15)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Title
        title = QLabel("SUMMARY:")
        title.setStyleSheet(f"color: {Styles.SECONDARY}; font-size: 11px; font-weight: bold;")
        layout.addWidget(title)
        
        # Voucher Type indicator
        self.summary_voucher_type = self._create_inline_stat("Type:", "-", Styles.INFO)
        layout.addWidget(self.summary_voucher_type)
        
        # Period indicator
        self.summary_period = self._create_inline_stat("Period:", "-", Styles.INFO)
        layout.addWidget(self.summary_period)
        
        # Total Rows
        self.total_rows_label = self._create_inline_stat("Rows:", "0", Styles.INFO)
        layout.addWidget(self.total_rows_label)
        
        # Valid Rows
        self.valid_rows_label = self._create_inline_stat("Valid:", "0", Styles.SUCCESS)
        layout.addWidget(self.valid_rows_label)
        
        # Errors
        self.error_rows_label = self._create_inline_stat("Errors:", "0", Styles.ERROR)
        layout.addWidget(self.error_rows_label)
        
        # Total Amount
        self.total_amount_label = self._create_inline_stat("Amount:", "₹0", Styles.PRIMARY)
        layout.addWidget(self.total_amount_label)
        
        layout.addStretch()
        
        return frame
    
    def _create_inline_stat(self, label: str, value: str, color: str) -> QFrame:
        """Create an inline stat display."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Styles.BG_SECONDARY};
                border-left: 2px solid {color};
                border-radius: 3px;
                padding: 4px 8px;
            }}
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"color: {Styles.TEXT_SECONDARY}; font-size: 10px;")
        layout.addWidget(label_widget)
        
        value_widget = QLabel(value)
        value_widget.setObjectName("stat_value")
        value_widget.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
        layout.addWidget(value_widget)
        
        return frame
    
    def _create_preview_section(self) -> QGroupBox:
        """Create the data preview section (Step 5) with validation.
        
        PART 2: Preview Grid with color-coded validation.
        - Green: Valid rows
        - Red: Invalid Business Segment or missing Place of Supply
        """
        group = QGroupBox("STEP 5: PREVIEW & VALIDATION")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 14, 10, 10)
        
        # Preview Info
        self.preview_info = QLabel("Upload a file to see preview")
        self.preview_info.setStyleSheet(f"color: {Styles.TEXT_SECONDARY}; font-size: 11px; padding: 4px 0;")
        layout.addWidget(self.preview_info)
        
        # CSV Schema Helper
        self.schema_helper = QLabel("")
        self.schema_helper.setStyleSheet(f"""
            color: {Styles.INFO};
            font-size: 10px;
            padding: 6px 10px;
            background-color: #E3F2FD;
            border: 1px solid {Styles.INFO};
            border-radius: 4px;
        """)
        self.schema_helper.setWordWrap(True)
        self.schema_helper.setVisible(False)
        layout.addWidget(self.schema_helper)
        
        # Preview Table - Functional grid with validation
        self.preview_table = QTableWidget()
        self.preview_table.setMinimumHeight(220)
        self.preview_table.setMaximumHeight(300)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        self.preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.preview_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # Set up columns: Date, Party, Segment, Amount, Tax, Total, Status
        headers = ["Date", "Party/Customer", "Segment", "State", "Amount", "Tax", "Total", "Status"]
        self.preview_table.setColumnCount(len(headers))
        self.preview_table.setHorizontalHeaderLabels(headers)
        
        layout.addWidget(self.preview_table)
        
        # Validation Legend
        legend_row = QHBoxLayout()
        legend_row.setSpacing(16)
        
        legend_title = QLabel("Validation:")
        legend_title.setStyleSheet("font-size: 10px; font-weight: bold;")
        legend_row.addWidget(legend_title)
        
        green_legend = QLabel("● Valid")
        green_legend.setStyleSheet(f"color: {Styles.SUCCESS}; font-size: 10px;")
        legend_row.addWidget(green_legend)
        
        red_legend = QLabel("● Invalid Segment/Missing State")
        red_legend.setStyleSheet(f"color: {Styles.ERROR}; font-size: 10px;")
        legend_row.addWidget(red_legend)
        
        legend_row.addStretch()
        layout.addLayout(legend_row)
        
        return group
    
    def _create_buttons(self) -> QHBoxLayout:
        """Create action buttons."""
        layout = QHBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(0, 12, 0, 0)
        
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.SECONDARY};
                color: {Styles.TEXT_LIGHT};
                border: none;
                border-radius: 4px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: 600;
                min-width: 100px;
            }}
            QPushButton:hover {{ background-color: {Styles.SECONDARY_LIGHT}; }}
        """)
        self.clear_btn.setFixedHeight(38)
        layout.addWidget(self.clear_btn)
        
        layout.addStretch()
        
        self.confirm_btn = QPushButton("Confirm Import")
        self.confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.SUCCESS};
                color: {Styles.TEXT_LIGHT};
                border: none;
                border-radius: 4px;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: 700;
                min-width: 150px;
            }}
            QPushButton:hover {{ background-color: #43A047; }}
            QPushButton:disabled {{ background-color: {Styles.BORDER_LIGHT}; color: {Styles.TEXT_MUTED}; }}
        """)
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.setFixedHeight(40)
        self.confirm_btn.setFixedWidth(180)
        layout.addWidget(self.confirm_btn)
        
        return layout
    
    def _connect_signals(self):
        """Connect UI signals to handlers."""
        self.voucher_type_group.buttonClicked.connect(self._on_voucher_type_changed)
        self.import_type_combo.currentIndexChanged.connect(self._on_import_type_changed)
        self.browse_btn.clicked.connect(self._on_browse_clicked)
        self.clear_btn.clicked.connect(self._clear_import)
        self.confirm_btn.clicked.connect(self._on_confirm_clicked)
        
        # Accounting section signals
        self.bulk_tally_head_combo.currentIndexChanged.connect(self._on_tally_head_changed)
        self.bulk_pos_combo.currentIndexChanged.connect(self._on_pos_changed)
        
        # Date validation signals
        self.voucher_date_edit.dateChanged.connect(self._on_date_changed)
        self.from_date_edit.dateChanged.connect(self._on_date_changed)
        self.to_date_edit.dateChanged.connect(self._on_date_changed)
    
    def _validate_dates(self) -> bool:
        """Validate period dates and show inline errors."""
        self.period_error.setVisible(False)
        
        voucher_date = self.voucher_date_edit.date().toPython()
        from_date = self.from_date_edit.date().toPython()
        to_date = self.to_date_edit.date().toPython()
        
        # From Date > To Date
        if from_date > to_date:
            self.period_error.setText("From Date cannot be later than To Date")
            self.period_error.setVisible(True)
            return False
        
        # To Date > Voucher Date
        if to_date > voucher_date:
            self.period_error.setText("Period end cannot be after voucher date")
            self.period_error.setVisible(True)
            return False
        
        return True
    
    def _on_date_changed(self):
        """Handle date change - re-validate and clear file if changed after selection."""
        self._validate_dates()
        
        # If file was already selected, clear it when dates change
        if self._current_filepath:
            self._clear_file_selection()
            self.upload_disabled_label.setText("Dates changed - please re-upload file")
            self.upload_disabled_label.setVisible(True)
        
        self._update_ui_state()
        self._update_period_summary()
    
    def _update_period_summary(self):
        """Update period display in summary."""
        period_val = self.summary_period.findChild(QLabel, "stat_value")
        if period_val:
            from_str = self.from_date_edit.date().toString("dd-MMM")
            to_str = self.to_date_edit.date().toString("dd-MMM")
            period_val.setText(f"{from_str} to {to_str}")
    
    def _update_ui_state(self):
        """Update UI elements based on current state."""
        voucher_type_selected = self._selected_voucher_type is not None
        import_type_selected = self.import_type_combo.currentIndex() > 0 if self.import_type_combo.count() > 0 else False
        tally_head_selected = self.bulk_tally_head_combo.currentIndex() > 0 if self.bulk_tally_head_combo.count() > 0 else False
        pos_selected = self.bulk_pos_combo.currentIndex() >= 0 if self.bulk_pos_combo.count() > 0 else False
        dates_valid = self._validate_dates()
        
        # Update accounting selectors
        self.bulk_tally_head_combo.setEnabled(voucher_type_selected)
        self.bulk_pos_combo.setEnabled(voucher_type_selected)
        
        # Update import type combo
        self.import_type_combo.setEnabled(voucher_type_selected and tally_head_selected and pos_selected)
        
        # Update browse button - requires all selections AND valid dates
        can_browse = voucher_type_selected and tally_head_selected and pos_selected and import_type_selected and dates_valid
        self.browse_btn.setEnabled(can_browse)
        
        # Update status labels
        if not voucher_type_selected:
            self.voucher_type_status.setText("Select voucher type")
            self.voucher_type_status.setStyleSheet(f"color: {Styles.WARNING}; font-size: 11px; font-weight: bold;")
            self.upload_disabled_label.setText("Complete Steps 1-3 and set valid period dates")
            self.upload_disabled_label.setVisible(True)
        elif not tally_head_selected or not pos_selected:
            self.voucher_type_status.setText(f"{self._selected_voucher_type}")
            self.voucher_type_status.setStyleSheet(f"color: {Styles.SUCCESS}; font-size: 11px; font-weight: bold;")
            self.upload_disabled_label.setText("Select Tally Head and Point of Supply in Step 2.5")
            self.upload_disabled_label.setVisible(True)
        elif not dates_valid:
            self.voucher_type_status.setText(f"{self._selected_voucher_type}")
            self.voucher_type_status.setStyleSheet(f"color: {Styles.SUCCESS}; font-size: 11px; font-weight: bold;")
            self.upload_disabled_label.setText("Fix period date errors before uploading")
            self.upload_disabled_label.setVisible(True)
        elif not import_type_selected:
            self.voucher_type_status.setText(f"{self._selected_voucher_type}")
            self.voucher_type_status.setStyleSheet(f"color: {Styles.SUCCESS}; font-size: 11px; font-weight: bold;")
            self.upload_disabled_label.setText("Select Import Format in Step 3")
            self.upload_disabled_label.setVisible(True)
        else:
            self.voucher_type_status.setText(f"{self._selected_voucher_type}")
            self.voucher_type_status.setStyleSheet(f"color: {Styles.SUCCESS}; font-size: 11px; font-weight: bold;")
            self.upload_disabled_label.setVisible(False)
        
        # Update summary voucher type
        type_val = self.summary_voucher_type.findChild(QLabel, "stat_value")
        if type_val:
            if self._selected_voucher_type:
                type_val.setText(self._selected_voucher_type)
                color = Styles.SUCCESS if self._selected_voucher_type == "Credit" else Styles.ERROR
                type_val.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
            else:
                type_val.setText("-")
    
    def _on_voucher_type_changed(self, button):
        """Handle voucher type selection change - clear dates."""
        if button == self.credit_radio:
            self._selected_voucher_type = "Credit"
            self._populate_credit_import_types()
            self._populate_tally_heads("credit")
            
            # Show CREDIT schema hint (Part 2)
            self.schema_helper.setText(
                "CREDIT CSV Schema: Date, Invoice No, Customer Name, Place of Supply (State), Business Segment, Amount (Total Taxable)"
            )
            self.schema_helper.setVisible(True)
            
        elif button == self.debit_radio:
            self._selected_voucher_type = "Debit"
            self._populate_debit_import_types()
            self._populate_tally_heads("debit")
            
            # Show DEBIT schema hint (Part 2)
            self.schema_helper.setText(
                "DEBIT CSV Schema: Date, Vendor Name, Place of Supply, Business Segment, Expense Details, TDS Category, Base Amount"
            )
            self.schema_helper.setVisible(True)
        
        # Populate POS states (same for both types)
        self._populate_pos_states()
        
        # Reset dates when switching voucher type
        self.voucher_date_edit.setDate(QDate.currentDate())
        self.from_date_edit.setDate(QDate.currentDate())
        self.to_date_edit.setDate(QDate.currentDate())
        self.period_error.setVisible(False)
        
        # Clear any existing import
        self._clear_file_selection()
        self._update_ui_state()
        self._update_period_summary()
    
    def _populate_tally_heads(self, voucher_type: str):
        """Populate Tally Accounting Heads dropdown."""
        self.bulk_tally_head_combo.clear()
        self.bulk_tally_head_combo.addItem("-- Select Accounting Head --", None)
        
        heads = self.config.get_tally_heads(voucher_type)
        for head in heads:
            self.bulk_tally_head_combo.addItem(f"{head.code} - {head.name}", head.code)
    
    def _populate_pos_states(self):
        """Populate Point of Supply dropdown."""
        self.bulk_pos_combo.clear()
        
        states = self.config.get_pos_states()
        home_idx = 0
        for i, state in enumerate(states):
            suffix = " (Home State)" if state.is_home_state else ""
            self.bulk_pos_combo.addItem(f"{state.name}{suffix}", state.code)
            if state.is_home_state:
                home_idx = i
        
        # Select home state by default
        self.bulk_pos_combo.setCurrentIndex(home_idx)
        self._on_pos_changed(home_idx)
    
    def _on_tally_head_changed(self, index):
        """Handle Tally Head selection change."""
        head_code = self.bulk_tally_head_combo.currentData()
        self._selected_tally_head = head_code
        
        if head_code:
            head = self.config.get_tally_head_by_code(head_code, self._selected_voucher_type.lower() if self._selected_voucher_type else "credit")
            if head:
                info_parts = []
                if head.requires_franchise:
                    info_parts.append("Franchise Required")
                if head.gst_applicable:
                    info_parts.append("GST Applicable")
                if head.tds_section:
                    info_parts.append(f"TDS: {head.tds_section}")
                
                self.head_info_label.setText(" | ".join(info_parts) if info_parts else "")
        else:
            self.head_info_label.setText("")
        
        self._update_ui_state()
    
    def _on_pos_changed(self, index):
        """Handle Point of Supply selection change."""
        state_code = self.bulk_pos_combo.currentData()
        self._selected_pos = state_code
        
        if state_code:
            gst_type = self.config.determine_gst_type(state_code)
            
            if gst_type == "CGST_SGST":
                self.pos_gst_indicator.setText("Intra-State (CGST + SGST)")
                self.pos_gst_indicator.setStyleSheet(f"color: {Styles.SUCCESS}; font-size: 11px; font-weight: bold;")
            else:
                self.pos_gst_indicator.setText("Inter-State (IGST)")
                self.pos_gst_indicator.setStyleSheet(f"color: {Styles.WARNING}; font-size: 11px; font-weight: bold;")
        else:
            self.pos_gst_indicator.setText("")
        
        self._update_ui_state()
    
    def _populate_credit_import_types(self):
        """Populate import types for Credit vouchers."""
        self.import_type_combo.clear()
        self.import_type_combo.addItem("-- Select Format --", None)
        self.import_type_combo.addItem("Wix Sales Export", "wix")
        self.import_type_combo.addItem("Generic Credit CSV", "generic_credit")
        
        self.import_type_info.setText("Credit: Sales, Income, Receipts")
    
    def _populate_debit_import_types(self):
        """Populate import types for Debit vouchers."""
        self.import_type_combo.clear()
        self.import_type_combo.addItem("-- Select Format --", None)
        self.import_type_combo.addItem("Purchase (GST+TDS+RCM)", "purchase")
        self.import_type_combo.addItem("Payroll (Salary)", "payroll")
        self.import_type_combo.addItem("Journal (Adjustments)", "journal")
        
        self.import_type_info.setText("Debit: Purchases, Payroll, Journal")
    
    def _on_import_type_changed(self, index):
        """Handle import type selection change."""
        self._selected_import_type = self.import_type_combo.currentData()
        self._clear_file_selection()
        self._update_ui_state()
        
        # Update info text based on selection
        if self._selected_import_type == "wix":
            self.import_type_info.setText("Wix: Order ID, Date, Amount")
        elif self._selected_import_type == "generic_credit":
            self.import_type_info.setText("Generic: Date, Amount, Account, Narration")
        elif self._selected_import_type == "purchase":
            self.import_type_info.setText("Purchase: GST, TDS, RCM scenarios")
        elif self._selected_import_type == "payroll":
            self.import_type_info.setText("Payroll: Salary payments + TDS")
        elif self._selected_import_type == "journal":
            self.import_type_info.setText("Journal: Must balance (Dr = Cr)")
    
    def _on_browse_clicked(self):
        """Handle browse button click."""
        # Re-validate dates before allowing file selection
        if not self._validate_dates():
            QMessageBox.warning(
                self, "Invalid Dates",
                "Please fix the period date errors before uploading a file."
            )
            return
        
        if not self._selected_voucher_type or not self._selected_import_type:
            QMessageBox.warning(
                self, "Selection Required",
                "Please select Voucher Type and Import Format before uploading."
            )
            return
        
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            f"Select {self._selected_voucher_type} CSV File",
            "",
            "CSV Files (*.csv);;Excel Files (*.xlsx);;All Files (*)"
        )
        
        if filepath:
            self._current_filepath = filepath
            self.file_path_label.setText(os.path.basename(filepath))
            self.file_path_label.setStyleSheet(f"""
                color: {Styles.TEXT_PRIMARY}; 
                font-style: normal;
                font-size: 12px;
                font-weight: 600;
                padding: 6px 10px;
                background-color: {Styles.BG_SECONDARY};
                border-radius: 4px;
            """)
            self._parse_file(filepath)
    
    def _parse_file(self, filepath: str):
        """Parse the selected CSV file based on voucher type and import type."""
        try:
            if self._selected_voucher_type == "Credit":
                self._parse_credit_file(filepath)
            elif self._selected_voucher_type == "Debit":
                self._parse_debit_file(filepath)
            else:
                raise ValueError("No voucher type selected")
        except Exception as e:
            QMessageBox.critical(
                self, "Parse Error",
                f"Failed to parse file:\n{str(e)}\n\n"
                "Please ensure file matches selected format."
            )
            self._clear_file_selection()
    
    def _parse_credit_file(self, filepath: str):
        """Parse Credit voucher file."""
        if self._selected_import_type == "wix":
            self._current_result = self.import_service.parse_wix_csv(filepath)
            self._imported_vouchers = self._current_result.vouchers if self._current_result else []
        else:
            self._current_result = self.import_service.parse_csv_preview(filepath)
            self._imported_vouchers = []
        
        self._validate_and_update_preview()
    
    def _parse_debit_file(self, filepath: str):
        """Parse Debit voucher file based on import type."""
        if self._selected_import_type == "purchase":
            vouchers, result = self.debit_import_service.import_purchase_csv(filepath)
            self._imported_vouchers = vouchers
            self._current_result = result
        elif self._selected_import_type == "payroll":
            vouchers, result = self.debit_import_service.import_payroll_csv(filepath)
            self._imported_vouchers = vouchers
            self._current_result = result
        elif self._selected_import_type == "journal":
            vouchers, result = self.debit_import_service.import_journal_csv(filepath)
            self._imported_vouchers = vouchers
            self._current_result = result
        else:
            raise ValueError(f"Unknown import type: {self._selected_import_type}")
        
        self._validate_and_update_preview()
    
    def _validate_and_update_preview(self):
        """Validate parsed data and update preview."""
        if not self._current_result:
            return
        
        if self._current_result.total_rows == 0:
            QMessageBox.warning(
                self, "Empty File",
                "The file appears empty or has no valid data rows."
            )
            return
        
        if self._current_result.successful_rows == 0 and self._current_result.total_rows > 0:
            QMessageBox.warning(
                self, "Template Mismatch",
                f"File does not match {self._selected_voucher_type} / "
                f"{self.import_type_combo.currentText().strip()} format.\n\n"
                f"Errors: {self._current_result.failed_rows}"
            )
        
        self._update_preview()
        self._update_summary()
    
    def _update_preview(self):
        """Update the preview table with validation highlighting.
        
        PART 2: Preview Grid (Step 5)
        - Columns: Date, Party, Segment, State, Amount, Tax, Total, Status
        - Red: Invalid Business Segment or missing Place of Supply
        - Green: Valid rows
        """
        from PySide6.QtGui import QColor, QBrush
        
        if not self._current_result:
            return
        
        result = self._current_result
        
        # Define valid Business Segments
        VALID_SEGMENTS = {"RETAIL", "FRANCHISE", "PLACEMENT", "HOMECARE", 
                         "Retail", "Franchise", "Placement", "Homecare"}
        
        self.preview_table.clear()
        self.preview_table.setRowCount(0)
        
        # Standard columns for validation preview
        headers = ["Date", "Party/Customer", "Segment", "State", "Amount", "Tax", "Total", "Status"]
        self.preview_table.setColumnCount(len(headers))
        self.preview_table.setHorizontalHeaderLabels(headers)
        
        valid_count = 0
        invalid_count = 0
        
        if result.preview_data:
            # Parse from generic preview data
            for row_data in result.preview_data[:15]:  # Show up to 15 rows
                row_idx = self.preview_table.rowCount()
                self.preview_table.insertRow(row_idx)
                
                # Extract fields (handle various column names)
                date_val = row_data.get("Date", row_data.get("date", ""))
                party_val = row_data.get("Customer Name", row_data.get("Vendor Name", 
                           row_data.get("customer_name", row_data.get("vendor_name", ""))))
                segment_val = row_data.get("Business Segment", row_data.get("Segment", 
                             row_data.get("business_segment", row_data.get("segment", ""))))
                state_val = row_data.get("Place of Supply", row_data.get("State", 
                           row_data.get("place_of_supply", row_data.get("state", ""))))
                amount_val = row_data.get("Amount", row_data.get("Base Amount", 
                            row_data.get("amount", row_data.get("base_amount", 0))))
                
                # Calculate tax (18% default)
                try:
                    amt = float(str(amount_val).replace(",", "").replace("₹", ""))
                except (ValueError, TypeError):
                    amt = 0
                
                gst_rate = self.config.default_gst_rate
                if self._selected_voucher_type == "Credit":
                    # Credit: amount is total, extract tax
                    base = amt / (1 + gst_rate / 100)
                    tax = amt - base
                    total = amt
                else:
                    # Debit: amount is base, add tax
                    base = amt
                    tax = base * (gst_rate / 100)
                    total = base + tax
                
                # Validate row
                is_segment_valid = str(segment_val).upper() in {s.upper() for s in VALID_SEGMENTS} or not segment_val
                is_state_valid = bool(state_val) and str(state_val).strip() != ""
                
                if is_segment_valid and is_state_valid:
                    status = "Valid"
                    is_valid = True
                    valid_count += 1
                else:
                    issues = []
                    if not is_segment_valid:
                        issues.append("Invalid Segment")
                    if not is_state_valid:
                        issues.append("Missing State")
                    status = ", ".join(issues)
                    is_valid = False
                    invalid_count += 1
                
                # Set cell values
                self.preview_table.setItem(row_idx, 0, QTableWidgetItem(str(date_val)))
                self.preview_table.setItem(row_idx, 1, QTableWidgetItem(str(party_val)[:25]))
                self.preview_table.setItem(row_idx, 2, QTableWidgetItem(str(segment_val)))
                self.preview_table.setItem(row_idx, 3, QTableWidgetItem(str(state_val)))
                self.preview_table.setItem(row_idx, 4, QTableWidgetItem(f"₹{amt:,.0f}"))
                self.preview_table.setItem(row_idx, 5, QTableWidgetItem(f"₹{tax:,.0f}"))
                self.preview_table.setItem(row_idx, 6, QTableWidgetItem(f"₹{total:,.0f}"))
                self.preview_table.setItem(row_idx, 7, QTableWidgetItem(status))
                
                # Apply row coloring
                if is_valid:
                    row_color = QColor(232, 245, 233)  # Light green
                    status_color = QColor(46, 125, 50)  # Dark green
                else:
                    row_color = QColor(255, 235, 238)  # Light red
                    status_color = QColor(198, 40, 40)  # Dark red
                
                for col in range(8):
                    item = self.preview_table.item(row_idx, col)
                    if item:
                        if col == 7:  # Status column
                            item.setForeground(QBrush(status_color))
                        item.setBackground(QBrush(row_color))
        
        elif self._imported_vouchers:
            # Parse from voucher objects
            for v in self._imported_vouchers[:15]:
                row_idx = self.preview_table.rowCount()
                self.preview_table.insertRow(row_idx)
                
                # Extract based on voucher type
                if hasattr(v, 'supplier_ledger'):
                    party = v.supplier_ledger
                elif hasattr(v, 'party_ledger'):
                    party = v.party_ledger
                else:
                    party = getattr(v, 'customer', '')
                
                date_val = v.voucher_date.strftime("%d-%b-%Y") if hasattr(v, 'voucher_date') else ""
                segment = getattr(v, 'segment', getattr(v, 'business_segment', ''))
                state = getattr(v, 'state', getattr(v, 'place_of_supply', ''))
                amount = getattr(v, 'base_amount', getattr(v, 'amount', 0))
                tax = getattr(v, 'total_gst_amount', getattr(v, 'gst_amount', 0))
                total = getattr(v, 'gross_amount', getattr(v, 'net_payable', amount + tax))
                
                # Validate
                is_segment_valid = str(segment).upper() in {s.upper() for s in VALID_SEGMENTS} or not segment
                is_state_valid = bool(state)
                
                if is_segment_valid and is_state_valid:
                    status = "Valid"
                    is_valid = True
                    valid_count += 1
                else:
                    issues = []
                    if not is_segment_valid:
                        issues.append("Invalid Segment")
                    if not is_state_valid:
                        issues.append("Missing State")
                    status = ", ".join(issues)
                    is_valid = False
                    invalid_count += 1
                
                self.preview_table.setItem(row_idx, 0, QTableWidgetItem(str(date_val)))
                self.preview_table.setItem(row_idx, 1, QTableWidgetItem(str(party)[:25]))
                self.preview_table.setItem(row_idx, 2, QTableWidgetItem(str(segment)))
                self.preview_table.setItem(row_idx, 3, QTableWidgetItem(str(state)))
                self.preview_table.setItem(row_idx, 4, QTableWidgetItem(f"₹{amount:,.0f}"))
                self.preview_table.setItem(row_idx, 5, QTableWidgetItem(f"₹{tax:,.0f}"))
                self.preview_table.setItem(row_idx, 6, QTableWidgetItem(f"₹{total:,.0f}"))
                self.preview_table.setItem(row_idx, 7, QTableWidgetItem(status))
                
                # Apply coloring
                if is_valid:
                    row_color = QColor(232, 245, 233)
                    status_color = QColor(46, 125, 50)
                else:
                    row_color = QColor(255, 235, 238)
                    status_color = QColor(198, 40, 40)
                
                for col in range(8):
                    item = self.preview_table.item(row_idx, col)
                    if item:
                        if col == 7:
                            item.setForeground(QBrush(status_color))
                        item.setBackground(QBrush(row_color))
        
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        
        total = result.total_rows
        shown = min(15, total)
        self.preview_info.setText(f"Showing {shown} of {total} rows | Valid: {valid_count} | Invalid: {invalid_count}")
    
    def _update_summary(self):
        """Update the summary stats."""
        if not self._current_result:
            return
        
        result = self._current_result
        
        # Calculate total amount
        total_amount = 0.0
        if self._selected_voucher_type == "Credit" and hasattr(result, 'vouchers'):
            total_amount = sum(v.amount for v in result.vouchers) if result.vouchers else 0.0
        elif self._imported_vouchers:
            if self._selected_import_type == "purchase":
                total_amount = sum(v.base_amount for v in self._imported_vouchers)
            elif self._selected_import_type == "payroll":
                total_amount = sum(v.amount for v in self._imported_vouchers)
            elif self._selected_import_type == "journal":
                total_amount = sum(v.total_debit for v in self._imported_vouchers)
        
        # Update labels
        total_val = self.total_rows_label.findChild(QLabel, "stat_value")
        valid_val = self.valid_rows_label.findChild(QLabel, "stat_value")
        error_val = self.error_rows_label.findChild(QLabel, "stat_value")
        amount_val = self.total_amount_label.findChild(QLabel, "stat_value")
        
        if total_val:
            total_val.setText(str(result.total_rows))
        if valid_val:
            valid_val.setText(str(result.successful_rows))
        if error_val:
            error_val.setText(str(result.failed_rows))
        if amount_val:
            if total_amount >= 100000:
                amount_val.setText(f"₹{total_amount/100000:.1f}L")
            else:
                amount_val.setText(f"₹{total_amount:,.0f}")
        
        self.confirm_btn.setEnabled(result.successful_rows > 0)
    
    def _on_confirm_clicked(self):
        """Handle confirm import button click."""
        # Final date validation
        if not self._validate_dates():
            QMessageBox.warning(self, "Invalid Dates", "Please fix date errors before importing.")
            return
        
        if not self._current_result:
            QMessageBox.warning(self, "No Data", "No data to import.")
            return
        
        voucher_count = 0
        if self._selected_voucher_type == "Credit":
            voucher_count = len(self._current_result.vouchers) if self._current_result.vouchers else 0
        else:
            voucher_count = len(self._imported_vouchers)
        
        if voucher_count == 0:
            QMessageBox.warning(self, "No Valid Data", "No valid vouchers to import.")
            return
        
        period_str = f"{self.from_date_edit.date().toString('dd-MMM')} to {self.to_date_edit.date().toString('dd-MMM')}"
        
        reply = QMessageBox.question(
            self,
            "Confirm Import",
            f"Import {voucher_count} {self._selected_voucher_type} vouchers?\n\n"
            f"Type: {self._selected_voucher_type}\n"
            f"Format: {self.import_type_combo.currentText().strip()}\n"
            f"Period: {period_str}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if self._selected_voucher_type == "Credit":
                    self.data_service.add_vouchers_bulk(self._current_result.vouchers)
                
                self._current_result.complete(ImportStatus.COMPLETED)
                
                QMessageBox.information(
                    self, "Import Successful",
                    f"Imported {voucher_count} vouchers!\nPeriod: {period_str}"
                )
                
                self.import_completed.emit(self._current_result)
                self._clear_import()
            
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to import: {e}")
    
    def _clear_file_selection(self):
        """Clear only file selection, keep voucher type and dates."""
        self._current_filepath = None
        self._current_result = None
        self._imported_vouchers = []
        
        self.file_path_label.setText("No file selected")
        self.file_path_label.setStyleSheet(f"""
            color: {Styles.TEXT_MUTED}; 
            font-style: italic;
            font-size: 12px;
            padding: 6px 10px;
            background-color: {Styles.BG_SECONDARY};
            border-radius: 4px;
        """)
        
        self.preview_table.clear()
        self.preview_table.setRowCount(0)
        self.preview_table.setColumnCount(0)
        self.preview_info.setText("Upload a file to see preview")
        
        # Reset summary
        for label in [self.total_rows_label, self.valid_rows_label, self.error_rows_label]:
            val = label.findChild(QLabel, "stat_value")
            if val:
                val.setText("0")
        
        amount_val = self.total_amount_label.findChild(QLabel, "stat_value")
        if amount_val:
            amount_val.setText("₹0")
        
        self.confirm_btn.setEnabled(False)
    
    def _clear_import(self):
        """Clear everything and reset to initial state."""
        self._selected_voucher_type = None
        self._selected_import_type = None
        self._selected_tally_head = None
        self._selected_pos = None
        self._current_filepath = None
        self._current_result = None
        self._imported_vouchers = []
        
        # Reset radio buttons
        self.voucher_type_group.setExclusive(False)
        self.credit_radio.setChecked(False)
        self.debit_radio.setChecked(False)
        self.voucher_type_group.setExclusive(True)
        
        # Reset dates
        self.voucher_date_edit.setDate(QDate.currentDate())
        self.from_date_edit.setDate(QDate.currentDate())
        self.to_date_edit.setDate(QDate.currentDate())
        self.period_error.setVisible(False)
        
        # Reset accounting selectors
        self.bulk_tally_head_combo.clear()
        self.bulk_tally_head_combo.setPlaceholderText("-- Select Accounting Head --")
        self.bulk_pos_combo.clear()
        self.bulk_pos_combo.setPlaceholderText("-- Select State --")
        self.head_info_label.setText("")
        self.pos_gst_indicator.setText("")
        
        # Reset import type
        self.import_type_combo.clear()
        self.import_type_combo.setPlaceholderText("-- First select Voucher Type --")
        self.import_type_info.setText("")
        
        # Clear file selection
        self._clear_file_selection()
        
        # Reset period summary
        period_val = self.summary_period.findChild(QLabel, "stat_value")
        if period_val:
            period_val.setText("-")
        
        # Update UI state
        self._update_ui_state()
