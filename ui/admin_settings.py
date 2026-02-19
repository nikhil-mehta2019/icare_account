"""Admin & Settings Tab - Password-protected Master Data Management.

ADMIN CREDENTIALS:
- Default Password: Subudhi123
- Only Admin can manage Master Data (Tally Heads, Countries, Products, Franchises, POS)
- Settings lock automatically
- Unlock only during Quarter-End windows (e.g., Mar 25 - Apr 10)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QFrame, QMessageBox,
    QLineEdit, QCheckBox, QTableWidget, QTabWidget,
    QTableWidgetItem, QHeaderView, QScrollArea, QFileDialog,
    QDoubleSpinBox, QComboBox, QFormLayout, QDialog, QDialogButtonBox,
    QSpinBox
)
from PySide6.QtCore import Qt, Signal
from datetime import datetime

from services.data_service import DataService
from services.voucher_config_service import get_voucher_config
from .styles import Styles


class MasterEditDialog(QDialog):
    """Generic dialog for adding/editing master data."""
    
    def __init__(self, title: str, fields: list, data: dict = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.fields = fields
        self.data = data or {}
        self.inputs = {}
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        for field in self.fields:
            key = field.get("key")
            label = field.get("label", key)
            field_type = field.get("type", "text")
            required = field.get("required", False)
            
            if required:
                label = f"{label} *"
            
            # 1. Create the styled label
            label_widget = QLabel(label + ":")
            label_widget.setStyleSheet("color: #333333; font-weight: bold;") # Force dark color

            if field_type == "text":
                input_widget = QLineEdit()
                input_widget.setText(str(self.data.get(key, "")))
                input_widget.setMinimumHeight(32)
            elif field_type == "bool":
                input_widget = QCheckBox()
                input_widget.setChecked(self.data.get(key, False))
            elif field_type == "combo":
                input_widget = QComboBox()
                for opt in field.get("options", []):
                    input_widget.addItem(opt.get("label", opt.get("value", "")), opt.get("value"))
                # Set current value
                current = self.data.get(key, "")
                idx = input_widget.findData(current)
                if idx >= 0:
                    input_widget.setCurrentIndex(idx)
                input_widget.setMinimumHeight(32)
            else:
                input_widget = QLineEdit()
                input_widget.setText(str(self.data.get(key, "")))
                input_widget.setMinimumHeight(32)
            
            self.inputs[key] = input_widget
            #form_layout.addRow(label + ":", input_widget)
            form_layout.addRow(label_widget, input_widget)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def get_data(self) -> dict:
        """Get the entered data."""
        result = {}
        for field in self.fields:
            key = field.get("key")
            widget = self.inputs.get(key)
            if isinstance(widget, QLineEdit):
                result[key] = widget.text()
            elif isinstance(widget, QCheckBox):
                result[key] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                result[key] = widget.currentData()
        return result


class AdminSettingsTab(QWidget):
    """Admin settings with password protection and Master Data Management."""
    
    settings_changed = Signal()
    
    # Default admin password
    DEFAULT_PASSWORD = "Subudhi123"
    
    def __init__(self, data_service: DataService, parent=None):
        super().__init__(parent)
        self.data_service = data_service
        self.config = get_voucher_config()
        self._is_authenticated = False
        
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
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Credentials Info Box
        creds_box = self._create_credentials_info()
        layout.addWidget(creds_box)
        
        # Authentication Section
        auth_section = self._create_auth_section()
        layout.addWidget(auth_section)
        
        # Settings Tabs (locked by default)
        self.settings_tabs = self._create_settings_tabs()
        layout.addWidget(self.settings_tabs)
        
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
        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 8, 12, 8)
        
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        title = QLabel("Admin / Master Data")
        title.setStyleSheet(f"color: {Styles.TEXT_LIGHT}; font-size: 16px; font-weight: bold;")
        title_layout.addWidget(title)
        
        subtitle = QLabel("Manage Tally Heads, Countries, Products, Franchises, Point of Supply")
        subtitle.setStyleSheet(f"color: {Styles.TEXT_LIGHT}; font-size: 11px;")
        title_layout.addWidget(subtitle)
        
        layout.addLayout(title_layout)
        layout.addStretch()
        
        # Lock Status Indicator
        self.lock_status = QLabel("LOCKED")
        self.lock_status.setStyleSheet(f"""
            color: {Styles.ERROR};
            font-weight: bold;
            font-size: 13px;
            padding: 8px 16px;
            background-color: rgba(244, 67, 54, 0.2);
            border-radius: 4px;
        """)
        layout.addWidget(self.lock_status)
        
        return header
    
    def _create_credentials_info(self) -> QFrame:
        """Create credentials information box - compact."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: #E3F2FD;
                border: 1px solid {Styles.INFO};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 6, 10, 6)
        
        title = QLabel("ADMIN:")
        title.setStyleSheet(f"color: {Styles.INFO}; font-size: 12px; font-weight: bold;")
        layout.addWidget(title)
        
        creds_text = QLabel(f"Password: <b>{self.DEFAULT_PASSWORD}</b> | Edit Windows: Mar 25-Apr 10, Jun 28-Jul 5, Sep 28-Oct 5, Dec 25-Jan 10")
        creds_text.setStyleSheet(f"color: {Styles.TEXT_PRIMARY}; font-size: 11px;")
        creds_text.setTextFormat(Qt.RichText)
        layout.addWidget(creds_text)
        layout.addStretch()
        
        return frame
    
    def _create_auth_section(self) -> QGroupBox:
        """Create the authentication section - compact."""
        group = QGroupBox("AUTHENTICATION")
        layout = QHBoxLayout(group)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 18, 12, 14)
        
        # Password Row
        pw_label = QLabel("PASSWORD:")
        pw_label.setStyleSheet(f"color: {Styles.SECONDARY}; font-size: 12px; font-weight: 600;")
        layout.addWidget(pw_label)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter admin password...")
        self.password_input.setFixedHeight(34)
        self.password_input.setMinimumWidth(180)
        self.password_input.setMaximumWidth(220)
        layout.addWidget(self.password_input)
        
        self.login_btn = QPushButton("Unlock")
        self.login_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.SUCCESS};
                color: {Styles.TEXT_LIGHT};
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 600;
                min-width: 90px;
            }}
            QPushButton:hover {{ background-color: #43A047; }}
        """)
        self.login_btn.setFixedHeight(34)
        layout.addWidget(self.login_btn)
        
        self.logout_btn = QPushButton("Lock")
        self.logout_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.SECONDARY};
                color: {Styles.TEXT_LIGHT};
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 600;
                min-width: 90px;
            }}
            QPushButton:hover {{ background-color: {Styles.SECONDARY_LIGHT}; }}
        """)
        self.logout_btn.setFixedHeight(34)
        self.logout_btn.setVisible(False)
        layout.addWidget(self.logout_btn)
        
        # Window Status
        self.window_status = QLabel("Checking...")
        self.window_status.setStyleSheet("font-weight: bold; font-size: 11px;")
        layout.addWidget(self.window_status)
        
        layout.addStretch()
        
        return group
    
    def _create_settings_tabs(self) -> QTabWidget:
        """Create tabbed settings interface."""
        tabs = QTabWidget()
        tabs.setEnabled(False)
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 2px solid {Styles.BORDER_LIGHT};
                border-radius: 6px;
                padding: 10px;
                background-color: {Styles.BG_CARD};
            }}
            QTabBar::tab {{
                padding: 10px 16px;
                margin-right: 4px;
                font-size: 12px;
                font-weight: 600;
                background-color: {Styles.BG_SECONDARY};
                color: {Styles.TEXT_PRIMARY};
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }}
            QTabBar::tab:selected {{
                background-color: {Styles.PRIMARY};
                color: {Styles.TEXT_LIGHT};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {Styles.PRIMARY_LIGHT};
                color: {Styles.TEXT_LIGHT};
            }}
        """)
        
        # Tab 1: Tally Accounting Heads
        tally_tab = self._create_tally_heads_tab()
        tabs.addTab(tally_tab, "Tally Heads")
        
        # Tab 2: Countries
        country_tab = self._create_countries_tab()
        tabs.addTab(country_tab, "Countries")
        
        # Tab 3: Products
        product_tab = self._create_products_tab()
        tabs.addTab(product_tab, "Products")
        
        # Tab 4: Franchises
        franchise_tab = self._create_franchises_tab()
        tabs.addTab(franchise_tab, "Franchises")
        
        # Tab 5: Point of Supply
        pos_tab = self._create_pos_tab()
        tabs.addTab(pos_tab, "Point of Supply")
        
        # Tab 6: GST/TDS Config
        tax_tab = self._create_tax_config_tab()
        tabs.addTab(tax_tab, "GST/TDS")

        # Tab 7: Vendors
        vendors_tab = self._create_vendors_tab()
        tabs.addTab(vendors_tab, "Vendors")

        # Tab 8: Backup Settings
        backup_tab = self._create_backup_tab()
        tabs.addTab(backup_tab, "Backup Config")
        
        return tabs
    
    def _create_master_table_toolbar(self, add_callback, edit_callback, delete_callback) -> QHBoxLayout:
        """Create standard toolbar for master data tables."""
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        
        add_btn = QPushButton("+ Add")
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.SUCCESS};
                color: {Styles.TEXT_LIGHT};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
                min-width: 70px;
            }}
            QPushButton:hover {{ background-color: #43A047; }}
        """)
        add_btn.setFixedHeight(32)
        add_btn.clicked.connect(add_callback)
        toolbar.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit")
        edit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.PRIMARY};
                color: {Styles.TEXT_LIGHT};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
                min-width: 70px;
            }}
            QPushButton:hover {{ background-color: {Styles.PRIMARY_DARK}; }}
        """)
        edit_btn.setFixedHeight(32)
        edit_btn.clicked.connect(edit_callback)
        toolbar.addWidget(edit_btn)
        
        delete_btn = QPushButton("Disable")
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.ERROR};
                color: {Styles.TEXT_LIGHT};
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: 600;
                min-width: 70px;
            }}
            QPushButton:hover {{ background-color: #E53935; }}
        """)
        delete_btn.setFixedHeight(32)
        delete_btn.clicked.connect(delete_callback)
        toolbar.addWidget(delete_btn)
        
        toolbar.addStretch()
        
        return toolbar
    
    def _create_tally_heads_tab(self) -> QWidget:
        """Create the Tally Accounting Heads management tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Info
        info = QLabel("Manage Tally Accounting Heads. These populate dropdowns in Voucher Entry.")
        info.setStyleSheet(Styles.get_helper_text_style())
        layout.addWidget(info)
        
        # Toolbar
        toolbar = self._create_master_table_toolbar(
            self._add_tally_head,
            self._edit_tally_head,
            self._disable_tally_head
        )
        layout.addLayout(toolbar)
        
        # Table
        self.tally_heads_table = QTableWidget()
        self.tally_heads_table.setMinimumHeight(280)
        self.tally_heads_table.setAlternatingRowColors(True)
        self.tally_heads_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.tally_heads_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        headers = ["Code", "Label", "Type", "Needs Franchise", "Active"]
        self.tally_heads_table.setColumnCount(len(headers))
        self.tally_heads_table.setHorizontalHeaderLabels(headers)
        self.tally_heads_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.tally_heads_table)
        
        return widget
    
    def _create_countries_tab(self) -> QWidget:
        """Create the Countries management tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)
        
        info = QLabel("Manage Countries for voucher entry. Used for International vs Domestic classification.")
        info.setStyleSheet(Styles.get_helper_text_style())
        layout.addWidget(info)
        
        toolbar = self._create_master_table_toolbar(
            self._add_country,
            self._edit_country,
            self._disable_country
        )
        layout.addLayout(toolbar)
        
        self.countries_table = QTableWidget()
        self.countries_table.setMinimumHeight(280)
        self.countries_table.setAlternatingRowColors(True)
        self.countries_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.countries_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        headers = ["Code", "Name", "Active"]
        self.countries_table.setColumnCount(len(headers))
        self.countries_table.setHorizontalHeaderLabels(headers)
        self.countries_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.countries_table)
        
        return widget
    
    def _create_products_tab(self) -> QWidget:
        """Create the Products management tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)
        
        info = QLabel("Manage Products. These generate unique voucher codes and segment tagging.")
        info.setStyleSheet(Styles.get_helper_text_style())
        layout.addWidget(info)
        
        toolbar = self._create_master_table_toolbar(
            self._add_product,
            self._edit_product,
            self._disable_product
        )
        layout.addLayout(toolbar)
        
        self.products_table = QTableWidget()
        self.products_table.setMinimumHeight(280)
        self.products_table.setAlternatingRowColors(True)
        self.products_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.products_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        headers = ["Code", "Name", "Active"]
        self.products_table.setColumnCount(len(headers))
        self.products_table.setHorizontalHeaderLabels(headers)
        self.products_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.products_table)
        
        return widget
    
    def _create_franchises_tab(self) -> QWidget:
        """Create the Franchises management tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)
        
        info = QLabel("Manage Franchises. Required for certain Tally Heads marked 'needsFranchise'.")
        info.setStyleSheet(Styles.get_helper_text_style())
        layout.addWidget(info)
        
        toolbar = self._create_master_table_toolbar(
            self._add_franchise,
            self._edit_franchise,
            self._disable_franchise
        )
        layout.addLayout(toolbar)
        
        self.franchises_table = QTableWidget()
        self.franchises_table.setMinimumHeight(280)
        self.franchises_table.setAlternatingRowColors(True)
        self.franchises_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.franchises_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        headers = ["Code", "Name", "Active"]
        self.franchises_table.setColumnCount(len(headers))
        self.franchises_table.setHorizontalHeaderLabels(headers)
        self.franchises_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.franchises_table)
        
        return widget
    
    def _create_pos_tab(self) -> QWidget:
        """Create the Point of Supply management tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(8, 8, 8, 8)
        
        info = QLabel("Manage Point of Supply (States). Home State determines CGST+SGST vs IGST.")
        info.setStyleSheet(Styles.get_helper_text_style())
        layout.addWidget(info)
        
        # Home State selector
        home_row = QHBoxLayout()
        home_row.setSpacing(10)
        
        home_label = QLabel("Home State:")
        home_label.setStyleSheet(f"font-weight: bold; color: {Styles.PRIMARY};")
        home_row.addWidget(home_label)
        
        self.home_state_combo = QComboBox()
        self.home_state_combo.setMinimumWidth(200)
        self.home_state_combo.setFixedHeight(32)
        home_row.addWidget(self.home_state_combo)
        
        self.save_home_btn = QPushButton("Set Home State")
        self.save_home_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.PRIMARY};
                color: {Styles.TEXT_LIGHT};
                border: none;
                border-radius: 4px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {Styles.PRIMARY_DARK}; }}
        """)
        self.save_home_btn.setFixedHeight(32)
        self.save_home_btn.clicked.connect(self._save_home_state)
        home_row.addWidget(self.save_home_btn)
        
        home_row.addStretch()
        layout.addLayout(home_row)
        
        toolbar = self._create_master_table_toolbar(
            self._add_pos,
            self._edit_pos,
            self._disable_pos
        )
        layout.addLayout(toolbar)
        
        self.pos_table = QTableWidget()
        self.pos_table.setMinimumHeight(250)
        self.pos_table.setAlternatingRowColors(True)
        self.pos_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.pos_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        headers = ["Code", "Name", "Home State", "Active"]
        self.pos_table.setColumnCount(len(headers))
        self.pos_table.setHorizontalHeaderLabels(headers)
        self.pos_table.horizontalHeader().setStretchLastSection(True)
        
        layout.addWidget(self.pos_table)
        
        return widget
    
    def _create_tax_config_tab(self) -> QWidget:
        """Create the GST/TDS configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # GST Rates Display
        gst_group = QGroupBox("GST RATES")
        gst_layout = QHBoxLayout(gst_group)
        gst_layout.setContentsMargins(12, 16, 12, 12)
        
        gst_rates = self.config.get_gst_rates()
        for rate in gst_rates:
            rate_label = QLabel(f"{rate}%")
            rate_label.setStyleSheet(f"""
                background-color: {Styles.PRIMARY};
                color: {Styles.TEXT_LIGHT};
                padding: 6px 14px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
            """)
            gst_layout.addWidget(rate_label)
        
        gst_layout.addStretch()
        layout.addWidget(gst_group)
        
        # TDS Rates Display
        tds_group = QGroupBox("TDS SECTIONS & RATES")
        tds_layout = QVBoxLayout(tds_group)
        tds_layout.setContentsMargins(12, 16, 12, 12)
        
        tds_table = QTableWidget()
        tds_table.setRowCount(7)
        tds_table.setColumnCount(3)
        tds_table.setHorizontalHeaderLabels(["Section", "Description", "Rate (%)"])
        tds_table.setAlternatingRowColors(True)
        tds_table.horizontalHeader().setStretchLastSection(True)
        tds_table.setMinimumHeight(200)
        tds_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        tds_data = self.config.get_tds_rates()
        row = 0
        for section, data in tds_data.items():
            tds_table.setItem(row, 0, QTableWidgetItem(section))
            tds_table.setItem(row, 1, QTableWidgetItem(data.get("name", "")))
            tds_table.setItem(row, 2, QTableWidgetItem(f"{data.get('rate', 0)}%"))
            row += 1
        
        tds_layout.addWidget(tds_table)
        layout.addWidget(tds_group)
        
        # GST Ledger Names
        ledger_group = QGroupBox("GST LEDGER NAMES (for Tally)")
        ledger_layout = QFormLayout(ledger_group)
        ledger_layout.setContentsMargins(12, 16, 12, 12)
        ledger_layout.setSpacing(8)
        
        gst_ledgers = self.config.get_gst_ledgers()
        for key, value in gst_ledgers.items():
            label = key.replace("input", "Input ").replace("output", "Output ").replace("Cgst", "CGST").replace("Sgst", "SGST").replace("Igst", "IGST")
            ledger_layout.addRow(f"{label}:", QLabel(value))
        
        layout.addWidget(ledger_group)
        layout.addStretch()
        
        return widget
    
    def _connect_signals(self):
        """Connect UI signals to handlers."""
        self.login_btn.clicked.connect(self._on_login_clicked)
        self.logout_btn.clicked.connect(self._on_logout_clicked)
        self.password_input.returnPressed.connect(self._on_login_clicked)
    
    def _update_ui_state(self):
        """Update UI based on authentication state."""
        if self._is_authenticated:
            self.lock_status.setText("UNLOCKED")
            self.lock_status.setStyleSheet(f"""
                color: {Styles.SUCCESS};
                font-weight: bold;
                font-size: 13px;
                padding: 8px 16px;
                background-color: rgba(76, 175, 80, 0.2);
                border-radius: 4px;
            """)
            self.login_btn.setVisible(False)
            self.logout_btn.setVisible(True)
            self.password_input.setVisible(False)
            self.settings_tabs.setEnabled(True)
            
            # Refresh all tables
            self._refresh_all_tables()
        else:
            self.lock_status.setText("LOCKED")
            self.lock_status.setStyleSheet(f"""
                color: {Styles.ERROR};
                font-weight: bold;
                font-size: 13px;
                padding: 8px 16px;
                background-color: rgba(244, 67, 54, 0.2);
                border-radius: 4px;
            """)
            self.login_btn.setVisible(True)
            self.logout_btn.setVisible(False)
            self.password_input.setVisible(True)
            self.settings_tabs.setEnabled(False)
        
        self._update_window_status()
    
    def _refresh_all_tables(self):
        """Refresh all master data tables."""
        self._refresh_tally_heads_table()
        self._refresh_countries_table()
        self._refresh_products_table()
        self._refresh_franchises_table()
        self._refresh_pos_table()
        self._refresh_vendors_table()
    
    def _refresh_tally_heads_table(self):
        """Refresh Tally Heads table."""
        self.tally_heads_table.setRowCount(0)
        heads = self.config.get_all_tally_heads_raw()
        
        for head in heads:
            row = self.tally_heads_table.rowCount()
            self.tally_heads_table.insertRow(row)
            
            self.tally_heads_table.setItem(row, 0, QTableWidgetItem(head.get("value", "")))
            self.tally_heads_table.setItem(row, 1, QTableWidgetItem(head.get("label", "")))
            self.tally_heads_table.setItem(row, 2, QTableWidgetItem(head.get("type", "")))
            self.tally_heads_table.setItem(row, 3, QTableWidgetItem("Yes" if head.get("needsFranchise") else "No"))
            self.tally_heads_table.setItem(row, 4, QTableWidgetItem("Yes" if head.get("isActive", True) else "No"))
            
            self.tally_heads_table.item(row, 0).setData(Qt.UserRole, head)
        
        self.tally_heads_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    
    def _refresh_countries_table(self):
        """Refresh Countries table."""
        self.countries_table.setRowCount(0)
        countries = self.config.get_all_countries_raw()
        
        for c in countries:
            row = self.countries_table.rowCount()
            self.countries_table.insertRow(row)
            
            self.countries_table.setItem(row, 0, QTableWidgetItem(c.get("value", "")))
            self.countries_table.setItem(row, 1, QTableWidgetItem(c.get("label", "")))
            self.countries_table.setItem(row, 2, QTableWidgetItem("Yes" if c.get("isActive", True) else "No"))
            
            self.countries_table.item(row, 0).setData(Qt.UserRole, c)
        
        self.countries_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    
    def _refresh_products_table(self):
        """Refresh Products table."""
        self.products_table.setRowCount(0)
        products = self.config.get_all_products_raw()
        
        for p in products:
            row = self.products_table.rowCount()
            self.products_table.insertRow(row)
            
            self.products_table.setItem(row, 0, QTableWidgetItem(p.get("value", "")))
            self.products_table.setItem(row, 1, QTableWidgetItem(p.get("label", "")))
            self.products_table.setItem(row, 2, QTableWidgetItem("Yes" if p.get("isActive", True) else "No"))
            
            self.products_table.item(row, 0).setData(Qt.UserRole, p)
        
        self.products_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    
    def _refresh_franchises_table(self):
        """Refresh Franchises table."""
        self.franchises_table.setRowCount(0)
        franchises = self.config.get_all_franchises_raw()
        
        for f in franchises:
            row = self.franchises_table.rowCount()
            self.franchises_table.insertRow(row)
            
            self.franchises_table.setItem(row, 0, QTableWidgetItem(f.get("value", "")))
            self.franchises_table.setItem(row, 1, QTableWidgetItem(f.get("label", "")))
            self.franchises_table.setItem(row, 2, QTableWidgetItem("Yes" if f.get("isActive", True) else "No"))
            
            self.franchises_table.item(row, 0).setData(Qt.UserRole, f)
        
        self.franchises_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    
    def _refresh_pos_table(self):
        """Refresh Point of Supply table."""
        self.pos_table.setRowCount(0)
        pos_list = self.config.get_all_pos_raw()
        
        # Also update home state combo
        self.home_state_combo.clear()
        current_home = self.config.home_state
        
        for p in pos_list:
            row = self.pos_table.rowCount()
            self.pos_table.insertRow(row)
            
            code = p.get("value", "")
            name = p.get("label", "")
            is_home = p.get("isHomeState", False)
            
            self.pos_table.setItem(row, 0, QTableWidgetItem(code))
            self.pos_table.setItem(row, 1, QTableWidgetItem(name))
            self.pos_table.setItem(row, 2, QTableWidgetItem("YES" if is_home else ""))
            self.pos_table.setItem(row, 3, QTableWidgetItem("Yes" if p.get("isActive", True) else "No"))
            
            if is_home:
                for col in range(4):
                    item = self.pos_table.item(row, col)
                    if item:
                        item.setBackground(Qt.lightGray)
            
            self.pos_table.item(row, 0).setData(Qt.UserRole, p)
            
            # Add to combo
            if p.get("isActive", True):
                self.home_state_combo.addItem(f"{name} ({code})", code)
                if code == current_home or name == current_home:
                    self.home_state_combo.setCurrentIndex(self.home_state_combo.count() - 1)
        
        self.pos_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    
    def _update_window_status(self):
        """Update the edit window status."""
        is_open = self._is_edit_window_open()
        
        if is_open:
            self.window_status.setText("EDIT WINDOW OPEN")
            self.window_status.setStyleSheet(f"color: {Styles.SUCCESS}; font-weight: bold; font-size: 11px;")
        else:
            self.window_status.setText("EDIT WINDOW CLOSED")
            self.window_status.setStyleSheet(f"color: {Styles.WARNING}; font-weight: bold; font-size: 11px;")
    
    def _is_edit_window_open(self) -> bool:
        """Check if currently in an edit window."""
        today = datetime.now()
        
        windows = [
            (3, 25, 31), (4, 1, 10),    # Mar-Apr
            (6, 28, 30), (7, 1, 5),      # Jun-Jul
            (9, 28, 30), (10, 1, 5),     # Sep-Oct
            (12, 25, 31), (1, 1, 10),    # Dec-Jan
        ]
        
        for month, start_day, end_day in windows:
            if today.month == month and start_day <= today.day <= end_day:
                return True
        
        # For development/testing, always allow
        return True
    
    def _on_login_clicked(self):
        """Handle login button click."""
        password = self.password_input.text()
        
        if password == self.DEFAULT_PASSWORD:
            self._is_authenticated = True
            self.password_input.clear()
            self._update_ui_state()
            QMessageBox.information(
                self, "Access Granted", 
                "Authentication successful!\nAdmin features unlocked."
            )
        else:
            QMessageBox.warning(self, "Access Denied", "Incorrect password.")
            self.password_input.clear()
            self.password_input.setFocus()
    
    def _on_logout_clicked(self):
        """Handle logout button click."""
        self._is_authenticated = False
        self._update_ui_state()
    
    # ============ TALLY HEADS CRUD ============
    
    def _add_tally_head(self):
        """Add a new Tally Head."""
        fields = [
            {"key": "value", "label": "Code", "type": "text", "required": True},
            {"key": "label", "label": "Name/Label", "type": "text", "required": True},
            {"key": "type", "label": "Type", "type": "combo", "options": [
                {"value": "CREDIT", "label": "CREDIT"},
                {"value": "DEBIT", "label": "DEBIT"}
            ], "required": True},
            {"key": "needsFranchise", "label": "Needs Franchise", "type": "bool"},
            {"key": "isActive", "label": "Active", "type": "bool"}
        ]
        
        dialog = MasterEditDialog("Add Tally Accounting Head", fields, {"isActive": True}, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if not data.get("value") or not data.get("label"):
                QMessageBox.warning(self, "Validation", "Code and Name are required.")
                return
            
            if self.config.add_tally_head(data):
                self._refresh_tally_heads_table()
                self.settings_changed.emit()
                QMessageBox.information(self, "Success", f"Tally Head '{data['value']}' added.")
            else:
                QMessageBox.critical(self, "Error", "Failed to save.")
    
    def _edit_tally_head(self):
        """Edit selected Tally Head."""
        selected = self.tally_heads_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Select a Tally Head to edit.")
            return
        
        row = selected[0].row()
        data = self.tally_heads_table.item(row, 0).data(Qt.UserRole)
        
        fields = [
            {"key": "value", "label": "Code", "type": "text", "required": True},
            {"key": "label", "label": "Name/Label", "type": "text", "required": True},
            {"key": "type", "label": "Type", "type": "combo", "options": [
                {"value": "CREDIT", "label": "CREDIT"},
                {"value": "DEBIT", "label": "DEBIT"}
            ], "required": True},
            {"key": "needsFranchise", "label": "Needs Franchise", "type": "bool"},
            {"key": "isActive", "label": "Active", "type": "bool"}
        ]
        
        dialog = MasterEditDialog("Edit Tally Accounting Head", fields, data, self)
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_data()
            if self.config.update_tally_head(data.get("value"), new_data):
                self._refresh_tally_heads_table()
                self.settings_changed.emit()
                QMessageBox.information(self, "Success", "Tally Head updated.")
            else:
                QMessageBox.critical(self, "Error", "Failed to update.")
    
    def _disable_tally_head(self):
        """Disable selected Tally Head."""
        selected = self.tally_heads_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Select a Tally Head to disable.")
            return
        
        row = selected[0].row()
        code = self.tally_heads_table.item(row, 0).text()
        
        reply = QMessageBox.question(
            self, "Confirm Disable",
            f"Disable Tally Head '{code}'?\n\nIt will no longer appear in dropdowns.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.config.delete_tally_head(code):
                self._refresh_tally_heads_table()
                self.settings_changed.emit()
                QMessageBox.information(self, "Success", f"Tally Head '{code}' disabled.")
    
    # ============ COUNTRIES CRUD ============
    
    def _add_country(self):
        """Add a new Country."""
        fields = [
            {"key": "value", "label": "Code", "type": "text", "required": True},
            {"key": "label", "label": "Name", "type": "text", "required": True},
            {"key": "isActive", "label": "Active", "type": "bool"}
        ]
        
        dialog = MasterEditDialog("Add Country", fields, {"isActive": True}, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if not data.get("value") or not data.get("label"):
                QMessageBox.warning(self, "Validation", "Code and Name are required.")
                return
            
            if self.config.add_country(data):
                self._refresh_countries_table()
                self.settings_changed.emit()
                QMessageBox.information(self, "Success", f"Country '{data['label']}' added.")
    
    def _edit_country(self):
        """Edit selected Country."""
        selected = self.countries_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Select a Country to edit.")
            return
        
        row = selected[0].row()
        data = self.countries_table.item(row, 0).data(Qt.UserRole)
        
        fields = [
            {"key": "value", "label": "Code", "type": "text", "required": True},
            {"key": "label", "label": "Name", "type": "text", "required": True},
            {"key": "isActive", "label": "Active", "type": "bool"}
        ]
        
        dialog = MasterEditDialog("Edit Country", fields, data, self)
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_data()
            if self.config.update_country(data.get("value"), new_data):
                self._refresh_countries_table()
                self.settings_changed.emit()
    
    def _disable_country(self):
        """Disable selected Country."""
        selected = self.countries_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Select a Country to disable.")
            return
        
        row = selected[0].row()
        code = self.countries_table.item(row, 0).text()
        data = self.countries_table.item(row, 0).data(Qt.UserRole)
        data["isActive"] = False
        
        if self.config.update_country(code, data):
            self._refresh_countries_table()
            self.settings_changed.emit()
    
    # ============ PRODUCTS CRUD ============
    
    def _add_product(self):
        """Add a new Product."""
        fields = [
            {"key": "value", "label": "Code", "type": "text", "required": True},
            {"key": "label", "label": "Name", "type": "text", "required": True},
            {"key": "isActive", "label": "Active", "type": "bool"}
        ]
        
        dialog = MasterEditDialog("Add Product", fields, {"isActive": True}, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if self.config.add_product(data):
                self._refresh_products_table()
                self.settings_changed.emit()
    
    def _edit_product(self):
        """Edit selected Product."""
        selected = self.products_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Select a Product to edit.")
            return
        
        row = selected[0].row()
        data = self.products_table.item(row, 0).data(Qt.UserRole)
        
        fields = [
            {"key": "value", "label": "Code", "type": "text", "required": True},
            {"key": "label", "label": "Name", "type": "text", "required": True},
            {"key": "isActive", "label": "Active", "type": "bool"}
        ]
        
        dialog = MasterEditDialog("Edit Product", fields, data, self)
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_data()
            if self.config.update_product(data.get("value"), new_data):
                self._refresh_products_table()
                self.settings_changed.emit()
    
    def _disable_product(self):
        """Disable selected Product."""
        selected = self.products_table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        code = self.products_table.item(row, 0).text()
        data = self.products_table.item(row, 0).data(Qt.UserRole)
        data["isActive"] = False
        
        if self.config.update_product(code, data):
            self._refresh_products_table()
            self.settings_changed.emit()
    
    # ============ FRANCHISES CRUD ============
    
    def _add_franchise(self):
        """Add a new Franchise."""
        fields = [
            {"key": "value", "label": "Code", "type": "text", "required": True},
            {"key": "label", "label": "Name", "type": "text", "required": True},
            {"key": "isActive", "label": "Active", "type": "bool"}
        ]
        
        dialog = MasterEditDialog("Add Franchise", fields, {"isActive": True}, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if self.config.add_franchise(data):
                self._refresh_franchises_table()
                self.settings_changed.emit()
    
    def _edit_franchise(self):
        """Edit selected Franchise."""
        selected = self.franchises_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Select a Franchise to edit.")
            return
        
        row = selected[0].row()
        data = self.franchises_table.item(row, 0).data(Qt.UserRole)
        
        fields = [
            {"key": "value", "label": "Code", "type": "text", "required": True},
            {"key": "label", "label": "Name", "type": "text", "required": True},
            {"key": "isActive", "label": "Active", "type": "bool"}
        ]
        
        dialog = MasterEditDialog("Edit Franchise", fields, data, self)
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_data()
            if self.config.update_franchise(data.get("value"), new_data):
                self._refresh_franchises_table()
                self.settings_changed.emit()
    
    def _disable_franchise(self):
        """Disable selected Franchise."""
        selected = self.franchises_table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        code = self.franchises_table.item(row, 0).text()
        data = self.franchises_table.item(row, 0).data(Qt.UserRole)
        data["isActive"] = False
        
        if self.config.update_franchise(code, data):
            self._refresh_franchises_table()
            self.settings_changed.emit()
    
    # ============ POINT OF SUPPLY CRUD ============
    
    def _add_pos(self):
        """Add a new Point of Supply."""
        fields = [
            {"key": "value", "label": "State Code", "type": "text", "required": True},
            {"key": "label", "label": "State Name", "type": "text", "required": True},
            {"key": "isHomeState", "label": "Is Home State", "type": "bool"},
            {"key": "isActive", "label": "Active", "type": "bool"}
        ]
        
        dialog = MasterEditDialog("Add Point of Supply", fields, {"isActive": True}, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if self.config.add_pos(data):
                self._refresh_pos_table()
                self.settings_changed.emit()
    
    def _edit_pos(self):
        """Edit selected Point of Supply."""
        selected = self.pos_table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "No Selection", "Select a State to edit.")
            return
        
        row = selected[0].row()
        data = self.pos_table.item(row, 0).data(Qt.UserRole)
        
        fields = [
            {"key": "value", "label": "State Code", "type": "text", "required": True},
            {"key": "label", "label": "State Name", "type": "text", "required": True},
            {"key": "isHomeState", "label": "Is Home State", "type": "bool"},
            {"key": "isActive", "label": "Active", "type": "bool"}
        ]
        
        dialog = MasterEditDialog("Edit Point of Supply", fields, data, self)
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.get_data()
            if self.config.update_pos(data.get("value"), new_data):
                self._refresh_pos_table()
                self.settings_changed.emit()
    
    def _disable_pos(self):
        """Disable selected Point of Supply."""
        selected = self.pos_table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        code = self.pos_table.item(row, 0).text()
        data = self.pos_table.item(row, 0).data(Qt.UserRole)
        data["isActive"] = False
        
        if self.config.update_pos(code, data):
            self._refresh_pos_table()
            self.settings_changed.emit()
    
    def _save_home_state(self):
        """Save the selected home state."""
        code = self.home_state_combo.currentData()
        if code:
            if self.config.set_home_state_code(code):
                self._refresh_pos_table()
                self.settings_changed.emit()
                QMessageBox.information(self, "Success", f"Home State set to '{code}'.\n\nGST will now calculate CGST+SGST for this state, IGST for others.")

    def _create_vendors_tab(self) -> QWidget:
            """Create the Vendors management tab."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setSpacing(10)
            layout.setContentsMargins(8, 8, 8, 8)
            
            info = QLabel("Manage Vendors. New vendors typed in Voucher Entry are auto-added here.")
            info.setStyleSheet(Styles.get_helper_text_style())
            layout.addWidget(info)
            
            toolbar = self._create_master_table_toolbar(
                self._add_vendor,
                self._edit_vendor,
                self._disable_vendor
            )
            layout.addLayout(toolbar)
            
            self.vendors_table = QTableWidget()
            self.vendors_table.setMinimumHeight(280)
            self.vendors_table.setAlternatingRowColors(True)
            self.vendors_table.setSelectionBehavior(QTableWidget.SelectRows)
            self.vendors_table.setEditTriggers(QTableWidget.NoEditTriggers)
            
            headers = ["Name", "GSTIN", "Contact", "Active"]
            self.vendors_table.setColumnCount(len(headers))
            self.vendors_table.setHorizontalHeaderLabels(headers)
            self.vendors_table.horizontalHeader().setStretchLastSection(True)
            
            layout.addWidget(self.vendors_table)
            
            return widget
    
    def _add_vendor(self):
        fields = [
            {"key": "name", "label": "Vendor Name", "type": "text", "required": True},
            {"key": "gstin", "label": "GSTIN", "type": "text"},
            {"key": "contact_person", "label": "Contact Person", "type": "text"},
            {"key": "isActive", "label": "Active", "type": "bool"}
        ]
        dialog = MasterEditDialog("Add Vendor", fields, {"isActive": True}, self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            if self.config.add_vendor(data):
                self._refresh_vendors_table()
                self.settings_changed.emit()

    def _edit_vendor(self):
        selected = self.vendors_table.selectedItems()
        if not selected: return
        row = selected[0].row()
        data = self.vendors_table.item(row, 0).data(Qt.UserRole)
        
        fields = [
            {"key": "name", "label": "Vendor Name", "type": "text", "required": True},
            {"key": "gstin", "label": "GSTIN", "type": "text"},
            {"key": "contact_person", "label": "Contact Person", "type": "text"},
            {"key": "isActive", "label": "Active", "type": "bool"}
        ]
        dialog = MasterEditDialog("Edit Vendor", fields, data, self)
        if dialog.exec() == QDialog.Accepted:
            if self.config.update_vendor(data["name"], dialog.get_data()):
                self._refresh_vendors_table()
                self.settings_changed.emit()

    def _disable_vendor(self):
        selected = self.vendors_table.selectedItems()
        if not selected: return
        row = selected[0].row()
        name = self.vendors_table.item(row, 0).text()
        if self.config.delete_vendor(name):
            self._refresh_vendors_table()
            self.settings_changed.emit()

    def _refresh_vendors_table(self):
        self.vendors_table.setRowCount(0)
        for v in self.config.get_all_vendors_raw():
            row = self.vendors_table.rowCount()
            self.vendors_table.insertRow(row)
            self.vendors_table.setItem(row, 0, QTableWidgetItem(v.get("name", "")))
            self.vendors_table.setItem(row, 1, QTableWidgetItem(v.get("gstin", "")))
            self.vendors_table.setItem(row, 2, QTableWidgetItem(v.get("contact_person", "")))
            self.vendors_table.setItem(row, 3, QTableWidgetItem("Yes" if v.get("isActive") else "No"))
            self.vendors_table.item(row, 0).setData(Qt.UserRole, v)

    
    def _create_backup_tab(self) -> QWidget:
        """Create the Backup Settings management tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        info = QLabel("Configure automatic backups. The system creates a ZIP backup after every successful voucher save or bulk import.")
        info.setStyleSheet(Styles.get_helper_text_style())
        info.setWordWrap(True)
        layout.addWidget(info)
        
        master = self.data_service.get_master_data()
        
        # 1. Enable Checkbox
        self.backup_enable_chk = QCheckBox("Enable Automatic Backups")
        self.backup_enable_chk.setChecked(getattr(master.settings, 'auto_backup_enabled', True))
        self.backup_enable_chk.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {Styles.PRIMARY};")
        layout.addWidget(self.backup_enable_chk)
        
        # 2. Directory Selector (WITH BROWSE BUTTON)
        dir_group = QGroupBox("Backup Location")
        dir_layout = QHBoxLayout(dir_group)
        dir_layout.setContentsMargins(10, 10, 10, 10)
        dir_layout.setSpacing(10)
        
        self.backup_dir_input = QLineEdit()
        self.backup_dir_input.setPlaceholderText("Default: [Local App Data]/iCareAccount/backups")
        self.backup_dir_input.setText(getattr(master.settings, 'backup_directory', ''))
        self.backup_dir_input.setReadOnly(True)
        self.backup_dir_input.setMinimumHeight(32)
        dir_layout.addWidget(self.backup_dir_input)
        
        # ---> THE BROWSE PATH BUTTON <---
        browse_btn = QPushButton("Browse Path")
        browse_btn.setMinimumHeight(32)
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.SECONDARY};
                color: white;
                border-radius: 4px;
                padding: 0 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {Styles.SECONDARY_LIGHT}; }}
        """)
        browse_btn.clicked.connect(self._browse_backup_dir)
        dir_layout.addWidget(browse_btn)
        
        clear_dir_btn = QPushButton("Use Default")
        clear_dir_btn.setMinimumHeight(32)
        clear_dir_btn.clicked.connect(lambda: self.backup_dir_input.clear())
        dir_layout.addWidget(clear_dir_btn)
        
        layout.addWidget(dir_group)
        
        # 3. Retention Settings (Days based)
        retention_row = QHBoxLayout()
        retention_label = QLabel("Keep backups for last N days:")
        retention_label.setStyleSheet("font-weight: 600;")
        
        self.backup_retention_spin = QSpinBox()
        self.backup_retention_spin.setRange(1, 365)
        self.backup_retention_spin.setValue(getattr(master.settings, 'backup_retention_days', 5))
        self.backup_retention_spin.setMinimumHeight(30)
        
        retention_row.addWidget(retention_label)
        retention_row.addWidget(self.backup_retention_spin)
        retention_row.addStretch()
        layout.addLayout(retention_row)
        
        # 4. Save Action
        save_row = QHBoxLayout()
        save_btn = QPushButton("Save Backup Configuration")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.SUCCESS};
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #43A047; }}
        """)
        save_btn.clicked.connect(self._save_backup_settings)
        save_row.addStretch()
        save_row.addWidget(save_btn)
        layout.addLayout(save_row)
        
        layout.addStretch()
        return widget
    
    def _browse_backup_dir(self):
        """Open a strict folder selection dialog."""
        options = QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        dir_path = QFileDialog.getExistingDirectory(
            self, 
            "Select Backup Directory", 
            "", 
            options=options
        )
        
        if dir_path:
            import os
            self.backup_dir_input.setText(os.path.normpath(dir_path))
            
    def _save_backup_settings(self):
        """Save the backup configuration to Master Data."""
        b_dir = self.backup_dir_input.text().strip()
        
        # Validate Directory if provided
        if b_dir:
            import os
            if not os.path.exists(b_dir):
                try:
                    os.makedirs(b_dir, exist_ok=True)
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Cannot create target directory:\n{e}")
                    return
            if not os.access(b_dir, os.W_OK):
                QMessageBox.warning(self, "Permission Denied", "Selected directory is not writable.")
                return

        try:
            master = self.data_service.get_master_data()
            master.settings.auto_backup_enabled = self.backup_enable_chk.isChecked()
            master.settings.backup_directory = b_dir
            master.settings.backup_retention_days = self.backup_retention_spin.value()
            self.data_service.save_master_data()
            
            QMessageBox.information(self, "Success", "Backup configuration updated and applied successfully!")
            self.settings_changed.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{e}")