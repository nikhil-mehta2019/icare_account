"""Main Window - Application main window with tab navigation."""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QStatusBar, QFrame, QMessageBox, QPushButton
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QPixmap
from datetime import datetime
import os

from services.data_service import DataService
from .styles import Styles
from .voucher_entry import VoucherEntryTab
from .bulk_import import BulkImportTab
from .review_validation import ReviewValidationTab
from .reports import ReportsTab
from .admin_settings import AdminSettingsTab


class MainWindow(QMainWindow):
    """Main application window with tab-based navigation."""
    
    def __init__(self):
        super().__init__()
        
        # Initialize data service
        self.data_service = DataService()
        
        # Setup window
        self.setWindowTitle("iCare Life - Accounting System")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Apply stylesheet
        self.setStyleSheet(Styles.get_main_stylesheet())
        
        # Setup UI
        self._setup_ui()
        self._setup_status_bar()
        
        # Start status timer
        self._start_status_timer()
    
    def _setup_ui(self):
        """Set up the main user interface."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        
        # Create tabs
        self.voucher_tab = VoucherEntryTab(self.data_service)
        self.import_tab = BulkImportTab(self.data_service)
        self.review_tab = ReviewValidationTab(self.data_service)
        self.reports_tab = ReportsTab(self.data_service)
        self.admin_tab = AdminSettingsTab(self.data_service)
        
        # Add tabs
        self.tab_widget.addTab(self.voucher_tab, "Voucher Entry")
        self.tab_widget.addTab(self.import_tab, "Bulk Import (CSV)")
        self.tab_widget.addTab(self.review_tab, "Review & Export")
        self.tab_widget.addTab(self.reports_tab, "Reports")
        self.tab_widget.addTab(self.admin_tab, "Admin / Settings")
        
        layout.addWidget(self.tab_widget, 1)
        
        # Connect signals
        self._connect_signals()
    
    def _create_header(self) -> QFrame:
        """Create the application header."""
        header = QFrame()
        header.setFixedHeight(80)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {Styles.SECONDARY};
                border-bottom: 3px solid {Styles.PRIMARY};
            }}
        """)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # Logo and Title
        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        
        # Company Name
        company_label = QLabel("iCare Life")
        company_label.setStyleSheet(f"""
            color: {Styles.PRIMARY};
            font-size: 24px;
            font-weight: bold;
        """)
        title_layout.addWidget(company_label)
        
        # App Name
        app_label = QLabel("Accounting System - Pre-Tally Data Preparation")
        app_label.setStyleSheet(f"""
            color: {Styles.TEXT_LIGHT};
            font-size: 12px;
            opacity: 0.9;
        """)
        title_layout.addWidget(app_label)
        
        layout.addLayout(title_layout)
        layout.addStretch()
        
        # Info Section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        info_layout.setAlignment(Qt.AlignRight)
        
        # Date
        self.date_label = QLabel(datetime.now().strftime("%d %B %Y"))
        self.date_label.setStyleSheet(f"color: {Styles.TEXT_LIGHT}; font-size: 14px;")
        self.date_label.setAlignment(Qt.AlignRight)
        info_layout.addWidget(self.date_label)
        
        # Time
        self.time_label = QLabel(datetime.now().strftime("%H:%M:%S"))
        self.time_label.setStyleSheet(f"color: {Styles.PRIMARY}; font-size: 18px; font-weight: bold;")
        self.time_label.setAlignment(Qt.AlignRight)
        info_layout.addWidget(self.time_label)
        
        layout.addLayout(info_layout)
        
        # Close Button
        close_btn = QPushButton("✕  Exit")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.ERROR};
                color: {Styles.TEXT_LIGHT};
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: #E53935;
            }}
            QPushButton:pressed {{
                background-color: #C62828;
            }}
        """)
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)
        
        return header
    
    def _setup_status_bar(self):
        """Set up the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Permanent widgets
        self.voucher_count_label = QLabel("Vouchers: 0")
        self.status_bar.addPermanentWidget(self.voucher_count_label)
        
        self.data_status_label = QLabel("Ready")
        self.status_bar.addWidget(self.data_status_label)
        
        self._update_status_bar()
    
    def _connect_signals(self):
        """Connect signals between components."""
        # Voucher saved -> refresh review tab
        self.voucher_tab.voucher_saved.connect(self._on_voucher_saved)
        
        # Import completed -> refresh review tab
        self.import_tab.import_completed.connect(self._on_import_completed)
        
        # Settings changed -> reload master data
        self.admin_tab.settings_changed.connect(self._on_settings_changed)
        
        # Tab changed
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
    
    def _start_status_timer(self):
        """Start timer for status updates."""
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._update_time)
        self.status_timer.start(1000)  # Update every second
    
    def _update_time(self):
        """Update the time display."""
        self.time_label.setText(datetime.now().strftime("%H:%M:%S"))
    
    def _update_status_bar(self):
        """Update status bar information."""
        vouchers = self.data_service.get_vouchers()
        self.voucher_count_label.setText(f"Vouchers: {len(vouchers)}")
    
    def _on_voucher_saved(self, voucher):
        """Handle voucher saved event."""
        self._update_status_bar()
        self.data_status_label.setText(f"Voucher saved: {voucher.account_code}")
    
    def _on_import_completed(self, result):
        """Handle import completed event."""
        self._update_status_bar()
        self.data_status_label.setText(f"Import completed: {result.successful_rows} vouchers")
    
    def _on_settings_changed(self):
        """Handle settings changed event."""
        # Reload master data in voucher entry tab
        self.voucher_tab.master_data = self.data_service.reload_master_data()
        self.data_status_label.setText("Settings updated")
    
    def _on_tab_changed(self, index):
        """Handle tab change."""
        tab_names = ["Voucher Entry", "Bulk Import", "Review & Export", "Reports", "Admin"]
        if 0 <= index < len(tab_names):
            self.data_status_label.setText(f"Tab: {tab_names[index]}")
        
        # Refresh review tab when selected
        if index == 2:  # Review tab
            self.review_tab.refresh_data()
        
        self._update_status_bar()
    
    def closeEvent(self, event):
        """Handle window close event."""
        reply = QMessageBox.question(
            self,
            "Exit Application",
            "Are you sure you want to exit?\n\nAll unsaved data will be preserved.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
