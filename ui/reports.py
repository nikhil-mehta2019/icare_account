"""Reports Tab - MIS and Tally export interface."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QFrame, QMessageBox,
    QDateEdit, QFileDialog, QProgressBar, QScrollArea
)
from PySide6.QtCore import Qt, QDate
from datetime import datetime
import os

from services.data_service import DataService
from services.tally_service import TallyService
from services.mis_service import MISService
from .styles import Styles


class ReportsTab(QWidget):
    """Reports generation interface for MIS Excel and Tally XML."""
    
    def __init__(self, data_service: DataService, parent=None):
        super().__init__(parent)
        self.data_service = data_service
        self.tally_service = TallyService()
        self.mis_service = MISService()
        
        self._setup_ui()
        self._connect_signals()
    
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
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Date Range Section
        date_section = self._create_date_section()
        layout.addWidget(date_section)
        
        # Export Options
        export_section = self._create_export_section()
        layout.addWidget(export_section)
        
        # Progress Section
        progress_section = self._create_progress_section()
        layout.addWidget(progress_section)
        
        layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
    
    def _create_header(self) -> QFrame:
        """Create the header section."""
        header = QFrame()
        header.setStyleSheet(Styles.get_header_style())
        layout = QVBoxLayout(header)
        
        title = QLabel("Reports & Export")
        title.setStyleSheet(f"color: {Styles.TEXT_LIGHT}; font-size: 22px; font-weight: bold;")
        layout.addWidget(title)
        
        subtitle = QLabel("Generate MIS reports and export data for Tally import.")
        subtitle.setStyleSheet(f"color: {Styles.TEXT_LIGHT}; font-size: 13px;")
        layout.addWidget(subtitle)
        
        return header
    
    def _create_date_section(self) -> QGroupBox:
        """Create the date range selection section."""
        group = QGroupBox("REPORT PERIOD")
        layout = QVBoxLayout(group)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 25, 20, 20)
        
        # Date row
        date_row = QHBoxLayout()
        date_row.setSpacing(30)
        
        # Start Date
        start_layout = QVBoxLayout()
        start_label = QLabel("FROM DATE:")
        start_label.setStyleSheet(Styles.get_form_label_style())
        start_layout.addWidget(start_label)
        
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("dd-MMM-yyyy")
        self.start_date.setMinimumHeight(45)
        self.start_date.setMinimumWidth(200)
        start_layout.addWidget(self.start_date)
        date_row.addLayout(start_layout)
        
        # End Date
        end_layout = QVBoxLayout()
        end_label = QLabel("TO DATE:")
        end_label.setStyleSheet(Styles.get_form_label_style())
        end_layout.addWidget(end_label)
        
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("dd-MMM-yyyy")
        self.end_date.setMinimumHeight(45)
        self.end_date.setMinimumWidth(200)
        end_layout.addWidget(self.end_date)
        date_row.addLayout(end_layout)
        
        date_row.addStretch()
        layout.addLayout(date_row)
        
        # Quick Select Buttons
        quick_layout = QVBoxLayout()
        quick_label = QLabel("QUICK SELECT:")
        quick_label.setStyleSheet(Styles.get_form_label_style())
        quick_layout.addWidget(quick_label)
        
        quick_btns = QHBoxLayout()
        quick_btns.setSpacing(15)
        
        self.this_month_btn = QPushButton("This Month")
        self.this_month_btn.setProperty("class", "secondary")
        self.this_month_btn.setMinimumHeight(45)
        quick_btns.addWidget(self.this_month_btn)
        
        self.last_month_btn = QPushButton("Last Month")
        self.last_month_btn.setProperty("class", "secondary")
        self.last_month_btn.setMinimumHeight(45)
        quick_btns.addWidget(self.last_month_btn)
        
        self.this_quarter_btn = QPushButton("This Quarter")
        self.this_quarter_btn.setProperty("class", "secondary")
        self.this_quarter_btn.setMinimumHeight(45)
        quick_btns.addWidget(self.this_quarter_btn)
        
        quick_btns.addStretch()
        quick_layout.addLayout(quick_btns)
        layout.addLayout(quick_layout)
        
        return group
    
    def _create_export_section(self) -> QGroupBox:
        """Create the export options section."""
        group = QGroupBox("EXPORT OPTIONS")
        layout = QHBoxLayout(group)
        layout.setSpacing(25)
        layout.setContentsMargins(20, 25, 20, 20)
        
        # MIS Excel Export Card
        mis_card = self._create_export_card(
            "📊  MIS Report (Excel)",
            "Generate segmental profitability report with Gross Profit analysis across Retail, Kenya, India segments.",
            "Export MIS Excel",
            Styles.SUCCESS
        )
        self.export_mis_btn = mis_card.findChild(QPushButton)
        layout.addWidget(mis_card)
        
        # Tally XML Export Card
        tally_card = self._create_export_card(
            "📁  Tally Export (XML)",
            "Generate Tally-compatible XML file for voucher import. Creates Receipt and Payment vouchers.",
            "Export Tally XML",
            Styles.PRIMARY
        )
        self.export_tally_btn = tally_card.findChild(QPushButton)
        layout.addWidget(tally_card)
        
        return group
    
    def _create_export_card(self, title: str, description: str, 
                           button_text: str, color: str) -> QFrame:
        """Create an export option card."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Styles.BG_PRIMARY};
                border-left: 5px solid {color};
                border-radius: 8px;
                padding: 25px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(15)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {Styles.SECONDARY}; font-size: 18px; font-weight: bold;")
        layout.addWidget(title_label)
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"color: {Styles.TEXT_SECONDARY}; font-size: 13px; line-height: 1.4;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        layout.addStretch()
        
        export_btn = QPushButton(button_text)
        export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                padding: 14px 28px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)
        export_btn.setMinimumHeight(50)
        layout.addWidget(export_btn)
        
        return card
    
    def _create_progress_section(self) -> QGroupBox:
        """Create the progress section."""
        group = QGroupBox("EXPORT STATUS")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 25, 20, 20)
        layout.setSpacing(15)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(25)
        layout.addWidget(self.progress_bar)
        
        # Status frame for better visibility
        status_frame = QFrame()
        status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {Styles.BG_SECONDARY};
                border: 2px solid {Styles.BORDER_LIGHT};
                border-radius: 8px;
                padding: 15px;
            }}
        """)
        status_layout = QHBoxLayout(status_frame)
        
        status_icon = QLabel("●")
        status_icon.setStyleSheet(f"color: {Styles.INFO}; font-size: 16px;")
        status_layout.addWidget(status_icon)
        self.status_icon = status_icon
        
        self.status_label = QLabel("Ready to export • Select date range and click export button")
        self.status_label.setStyleSheet(f"color: {Styles.TEXT_PRIMARY}; font-size: 14px; font-weight: 500;")
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label, 1)
        
        layout.addWidget(status_frame)
        
        return group
    
    def _connect_signals(self):
        """Connect UI signals to handlers."""
        self.this_month_btn.clicked.connect(self._set_this_month)
        self.last_month_btn.clicked.connect(self._set_last_month)
        self.this_quarter_btn.clicked.connect(self._set_this_quarter)
        self.export_mis_btn.clicked.connect(self._export_mis)
        self.export_tally_btn.clicked.connect(self._export_tally)
    
    def _set_this_month(self):
        """Set date range to this month."""
        today = QDate.currentDate()
        self.start_date.setDate(QDate(today.year(), today.month(), 1))
        self.end_date.setDate(today)
    
    def _set_last_month(self):
        """Set date range to last month."""
        today = QDate.currentDate()
        last_month = today.addMonths(-1)
        self.start_date.setDate(QDate(last_month.year(), last_month.month(), 1))
        self.end_date.setDate(QDate(last_month.year(), last_month.month(), last_month.daysInMonth()))
    
    def _set_this_quarter(self):
        """Set date range to this quarter."""
        today = QDate.currentDate()
        quarter_start_month = ((today.month() - 1) // 3) * 3 + 1
        self.start_date.setDate(QDate(today.year(), quarter_start_month, 1))
        self.end_date.setDate(today)
    
    def _export_mis(self):
        """Export MIS report to Excel."""
        start = datetime.combine(self.start_date.date().toPython(), datetime.min.time())
        end = datetime.combine(self.end_date.date().toPython(), datetime.max.time())
        
        default_name = f"MIS_Report_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.xlsx"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save MIS Report", default_name, "Excel Files (*.xlsx);;All Files (*)"
        )
        
        if not filepath:
            return
        
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.status_icon.setText("⏳")
            self.status_icon.setStyleSheet(f"color: {Styles.INFO}; font-size: 16px;")
            self.status_label.setText("Generating MIS report...")
            self.status_label.setStyleSheet(f"color: {Styles.INFO}; font-size: 14px; font-weight: 500;")
            
            vouchers = self.data_service.get_vouchers_by_date_range(start, end)
            mis_data = self.mis_service.calculate_mis(vouchers, start, end)
            result = self.mis_service.export_mis_excel(mis_data, filepath)
            
            self.progress_bar.setVisible(False)
            
            if result:
                self.status_icon.setText("✓")
                self.status_icon.setStyleSheet(f"color: {Styles.SUCCESS}; font-size: 16px;")
                self.status_label.setText(f"MIS report saved: {os.path.basename(filepath)}")
                self.status_label.setStyleSheet(f"color: {Styles.SUCCESS}; font-weight: bold; font-size: 14px;")
                
                QMessageBox.information(
                    self, "Export Successful",
                    f"MIS report exported successfully!\n\nFile: {filepath}"
                )
            else:
                self.status_icon.setText("⚠")
                self.status_icon.setStyleSheet(f"color: {Styles.WARNING}; font-size: 16px;")
                self.status_label.setText("Export completed with warnings")
                self.status_label.setStyleSheet(f"color: {Styles.WARNING}; font-size: 14px; font-weight: 500;")
        
        except Exception as e:
            self.progress_bar.setVisible(False)
            self.status_icon.setText("✗")
            self.status_icon.setStyleSheet(f"color: {Styles.ERROR}; font-size: 16px;")
            self.status_label.setText(f"Error: {str(e)}")
            self.status_label.setStyleSheet(f"color: {Styles.ERROR}; font-size: 14px; font-weight: 500;")
            QMessageBox.critical(self, "Error", f"Failed to export MIS report:\n{e}")
    
    def _export_tally(self):
        """Export Tally XML file."""
        start = datetime.combine(self.start_date.date().toPython(), datetime.min.time())
        end = datetime.combine(self.end_date.date().toPython(), datetime.max.time())
        
        default_name = f"Tally_Import_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.xml"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save Tally XML", default_name, "XML Files (*.xml);;All Files (*)"
        )
        
        if not filepath:
            return
        
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.status_icon.setText("⏳")
            self.status_icon.setStyleSheet(f"color: {Styles.INFO}; font-size: 16px;")
            self.status_label.setText("Generating Tally XML...")
            self.status_label.setStyleSheet(f"color: {Styles.INFO}; font-size: 14px; font-weight: 500;")
            
            vouchers = self.data_service.get_vouchers_by_date_range(start, end)
            
            if not vouchers:
                self.progress_bar.setVisible(False)
                self.status_icon.setText("⚠")
                self.status_icon.setStyleSheet(f"color: {Styles.WARNING}; font-size: 16px;")
                self.status_label.setText("No vouchers found for selected period")
                self.status_label.setStyleSheet(f"color: {Styles.WARNING}; font-size: 14px; font-weight: 500;")
                QMessageBox.warning(self, "No Data", "No vouchers found for the selected date range.")
                return
            
            result = self.tally_service.generate_tally_xml(vouchers, filepath, start, end)
            
            self.progress_bar.setVisible(False)
            
            if result:
                self.status_icon.setText("✓")
                self.status_icon.setStyleSheet(f"color: {Styles.SUCCESS}; font-size: 16px;")
                self.status_label.setText(f"Tally XML saved: {os.path.basename(filepath)}")
                self.status_label.setStyleSheet(f"color: {Styles.SUCCESS}; font-weight: bold; font-size: 14px;")
                
                QMessageBox.information(
                    self, "Export Successful",
                    f"Tally XML exported successfully!\n\n"
                    f"Vouchers: {len(vouchers)}\n"
                    f"File: {filepath}"
                )
        
        except Exception as e:
            self.progress_bar.setVisible(False)
            self.status_icon.setText("✗")
            self.status_icon.setStyleSheet(f"color: {Styles.ERROR}; font-size: 16px;")
            self.status_label.setText(f"Error: {str(e)}")
            self.status_label.setStyleSheet(f"color: {Styles.ERROR}; font-size: 14px; font-weight: 500;")
            QMessageBox.critical(self, "Error", f"Failed to export Tally XML:\n{e}")
