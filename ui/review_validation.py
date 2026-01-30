"""Review & Validation Tab - Review vouchers before export."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QFrame, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
    QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush

from models.voucher import Voucher, VoucherStatus
from models.account_head import VoucherType
from services.data_service import DataService
from .styles import Styles


class ReviewValidationTab(QWidget):
    """Review and validation screen for vouchers."""
    
    vouchers_approved = Signal(list)
    
    def __init__(self, data_service: DataService, parent=None):
        super().__init__(parent)
        self.data_service = data_service
        self._vouchers = []
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area
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
        
        # Summary Cards
        summary = self._create_summary_section()
        layout.addWidget(summary)
        
        # Validation Status
        validation = self._create_validation_section()
        layout.addWidget(validation)
        
        # Voucher Grid
        grid_section = self._create_grid_section()
        layout.addWidget(grid_section, 1)
        
        # Action Buttons
        buttons = self._create_buttons()
        layout.addLayout(buttons)
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
    
    def _create_header(self) -> QFrame:
        """Create the header section."""
        header = QFrame()
        header.setStyleSheet(Styles.get_header_style())
        layout = QHBoxLayout(header)
        
        title_section = QVBoxLayout()
        title = QLabel("Review & Validation")
        title.setStyleSheet(f"color: {Styles.TEXT_LIGHT}; font-size: 22px; font-weight: bold;")
        title_section.addWidget(title)
        
        subtitle = QLabel("Review all vouchers before exporting to Tally or MIS reports.")
        subtitle.setStyleSheet(f"color: {Styles.TEXT_LIGHT}; font-size: 13px;")
        title_section.addWidget(subtitle)
        
        layout.addLayout(title_section)
        layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄  Refresh Data")
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Styles.TEXT_LIGHT};
                color: {Styles.SECONDARY};
                padding: 12px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {Styles.BG_SECONDARY};
            }}
        """)
        layout.addWidget(self.refresh_btn)
        
        return header
    
    def _create_summary_section(self) -> QGroupBox:
        """Create the summary section with totals."""
        group = QGroupBox("TOTALS SUMMARY")
        layout = QHBoxLayout(group)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 25, 20, 20)
        
        # Total Debits Card
        debit_card = self._create_stat_card("Total Debits", "₹ 0.00", Styles.ERROR, "debit")
        self.debit_total_label = debit_card.findChild(QLabel, "value_label_debit")
        layout.addWidget(debit_card)
        
        # Total Credits Card
        credit_card = self._create_stat_card("Total Credits", "₹ 0.00", Styles.SUCCESS, "credit")
        self.credit_total_label = credit_card.findChild(QLabel, "value_label_credit")
        layout.addWidget(credit_card)
        
        # Difference Card
        diff_card = self._create_stat_card("Difference", "₹ 0.00", Styles.WARNING, "diff")
        self.diff_label = diff_card.findChild(QLabel, "value_label_diff")
        self.diff_card = diff_card
        layout.addWidget(diff_card)
        
        # Voucher Count Card
        count_card = self._create_stat_card("Total Vouchers", "0", Styles.INFO, "count")
        self.count_label = count_card.findChild(QLabel, "value_label_count")
        layout.addWidget(count_card)
        
        return group
    
    def _create_stat_card(self, title: str, value: str, color: str, suffix: str) -> QFrame:
        """Create a statistics card."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {Styles.BG_PRIMARY};
                border-left: 5px solid {color};
                border-radius: 8px;
                padding: 18px;
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {Styles.TEXT_SECONDARY}; font-size: 13px; font-weight: 600;")
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setObjectName(f"value_label_{suffix}")
        value_label.setStyleSheet(f"color: {Styles.TEXT_PRIMARY}; font-size: 26px; font-weight: bold;")
        layout.addWidget(value_label)
        
        return card
    
    def _create_validation_section(self) -> QGroupBox:
        """Create the validation status section."""
        group = QGroupBox("VALIDATION STATUS")
        layout = QHBoxLayout(group)
        layout.setContentsMargins(20, 25, 20, 20)
        
        self.validation_icon = QLabel("●")
        self.validation_icon.setStyleSheet(f"color: {Styles.TEXT_MUTED}; font-size: 20px;")
        layout.addWidget(self.validation_icon)
        
        self.validation_message = QLabel("Load vouchers to see validation status")
        self.validation_message.setStyleSheet(f"color: {Styles.TEXT_SECONDARY}; font-size: 14px;")
        layout.addWidget(self.validation_message)
        
        layout.addStretch()
        
        # Pending count
        self.pending_label = QLabel("Pending Review: ")
        self.pending_label.setStyleSheet(f"color: {Styles.TEXT_SECONDARY}; font-size: 14px;")
        layout.addWidget(self.pending_label)
        
        self.pending_count_label = QLabel("0")
        self.pending_count_label.setStyleSheet(f"color: {Styles.WARNING}; font-weight: bold; font-size: 16px;")
        layout.addWidget(self.pending_count_label)
        
        return group
    
    def _create_grid_section(self) -> QGroupBox:
        """Create the voucher grid section."""
        group = QGroupBox("VOUCHER LIST")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(20, 25, 20, 20)
        
        # Voucher Table
        self.voucher_table = QTableWidget()
        self.voucher_table.setMinimumHeight(350)
        self.voucher_table.setAlternatingRowColors(True)
        self.voucher_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.voucher_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.voucher_table.horizontalHeader().setStretchLastSection(True)
        
        headers = ["Date", "Type", "Account Code", "Account Name", "Amount", "Segment", "Status", "Source"]
        self.voucher_table.setColumnCount(len(headers))
        self.voucher_table.setHorizontalHeaderLabels(headers)
        
        layout.addWidget(self.voucher_table)
        
        return group
    
    def _create_buttons(self) -> QHBoxLayout:
        """Create action buttons."""
        layout = QHBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(0, 10, 0, 0)
        
        self.delete_btn = QPushButton("🗑️  Delete Selected")
        self.delete_btn.setProperty("class", "danger")
        self.delete_btn.setMinimumHeight(50)
        layout.addWidget(self.delete_btn)
        
        layout.addStretch()
        
        self.approve_all_btn = QPushButton("✓  Approve All Pending")
        self.approve_all_btn.setProperty("class", "success")
        self.approve_all_btn.setMinimumHeight(50)
        self.approve_all_btn.setMinimumWidth(220)
        layout.addWidget(self.approve_all_btn)
        
        return layout
    
    def _connect_signals(self):
        """Connect UI signals to handlers."""
        self.refresh_btn.clicked.connect(self.refresh_data)
        self.delete_btn.clicked.connect(self._on_delete_clicked)
        self.approve_all_btn.clicked.connect(self._on_approve_all_clicked)
    
    def refresh_data(self):
        """Refresh voucher data from data service."""
        self._vouchers = self.data_service.get_vouchers()
        self._update_table()
        self._update_summary()
        self._validate_vouchers()
    
    def _update_table(self):
        """Update the voucher table."""
        self.voucher_table.setRowCount(0)
        
        for voucher in self._vouchers:
            row_idx = self.voucher_table.rowCount()
            self.voucher_table.insertRow(row_idx)
            
            self.voucher_table.setItem(row_idx, 0, 
                QTableWidgetItem(voucher.date.strftime("%Y-%m-%d")))
            
            type_item = QTableWidgetItem(voucher.voucher_type.value)
            if voucher.voucher_type == VoucherType.DEBIT:
                type_item.setForeground(QBrush(QColor(Styles.ERROR)))
            else:
                type_item.setForeground(QBrush(QColor(Styles.SUCCESS)))
            type_item.setFont(type_item.font())
            self.voucher_table.setItem(row_idx, 1, type_item)
            
            self.voucher_table.setItem(row_idx, 2, QTableWidgetItem(voucher.account_code))
            
            name = voucher.account_name[:35] + "..." if len(voucher.account_name) > 35 else voucher.account_name
            self.voucher_table.setItem(row_idx, 3, QTableWidgetItem(name))
            
            amount_item = QTableWidgetItem(f"₹ {voucher.amount:,.2f}")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.voucher_table.setItem(row_idx, 4, amount_item)
            
            self.voucher_table.setItem(row_idx, 5, QTableWidgetItem(voucher.segment))
            
            status_item = QTableWidgetItem(voucher.status.value)
            if voucher.status == VoucherStatus.APPROVED:
                status_item.setForeground(QBrush(QColor(Styles.SUCCESS)))
            elif voucher.status == VoucherStatus.PENDING_REVIEW:
                status_item.setForeground(QBrush(QColor(Styles.WARNING)))
            elif voucher.status == VoucherStatus.REJECTED:
                status_item.setForeground(QBrush(QColor(Styles.ERROR)))
            self.voucher_table.setItem(row_idx, 6, status_item)
            
            self.voucher_table.setItem(row_idx, 7, QTableWidgetItem(voucher.source))
            
            self.voucher_table.item(row_idx, 0).setData(Qt.UserRole, voucher.voucher_id)
        
        self.voucher_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.voucher_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
    
    def _update_summary(self):
        """Update summary totals."""
        total_debits = sum(v.amount for v in self._vouchers if v.voucher_type == VoucherType.DEBIT)
        total_credits = sum(v.amount for v in self._vouchers if v.voucher_type == VoucherType.CREDIT)
        difference = abs(total_debits - total_credits)
        
        self.debit_total_label.setText(f"₹ {total_debits:,.2f}")
        self.credit_total_label.setText(f"₹ {total_credits:,.2f}")
        self.diff_label.setText(f"₹ {difference:,.2f}")
        self.count_label.setText(str(len(self._vouchers)))
        
        if difference > 0.01:
            self.diff_card.setStyleSheet(f"""
                QFrame {{
                    background-color: #FFEBEE;
                    border-left: 5px solid {Styles.ERROR};
                    border-radius: 8px;
                    padding: 18px;
                }}
            """)
            self.diff_label.setStyleSheet(f"color: {Styles.ERROR}; font-size: 26px; font-weight: bold;")
        else:
            self.diff_card.setStyleSheet(f"""
                QFrame {{
                    background-color: #E8F5E9;
                    border-left: 5px solid {Styles.SUCCESS};
                    border-radius: 8px;
                    padding: 18px;
                }}
            """)
            self.diff_label.setStyleSheet(f"color: {Styles.SUCCESS}; font-size: 26px; font-weight: bold;")
        
        pending = len([v for v in self._vouchers if v.status == VoucherStatus.PENDING_REVIEW])
        self.pending_count_label.setText(str(pending))
    
    def _validate_vouchers(self):
        """Validate vouchers and update status."""
        total_debits = sum(v.amount for v in self._vouchers if v.voucher_type == VoucherType.DEBIT)
        total_credits = sum(v.amount for v in self._vouchers if v.voucher_type == VoucherType.CREDIT)
        difference = abs(total_debits - total_credits)
        
        if len(self._vouchers) == 0:
            self.validation_icon.setText("○")
            self.validation_icon.setStyleSheet(f"color: {Styles.TEXT_MUTED}; font-size: 20px;")
            self.validation_message.setText("No vouchers to validate")
            self.validation_message.setStyleSheet(f"color: {Styles.TEXT_SECONDARY}; font-size: 14px;")
        elif difference > 0.01:
            self.validation_icon.setText("⚠")
            self.validation_icon.setStyleSheet(f"color: {Styles.ERROR}; font-size: 20px;")
            self.validation_message.setText(
                f"WARNING: Debits and Credits do not balance! Difference: ₹{difference:,.2f}"
            )
            self.validation_message.setStyleSheet(f"color: {Styles.ERROR}; font-weight: bold; font-size: 14px;")
        else:
            self.validation_icon.setText("✓")
            self.validation_icon.setStyleSheet(f"color: {Styles.SUCCESS}; font-size: 20px;")
            self.validation_message.setText("PASSED: Debits and Credits are balanced")
            self.validation_message.setStyleSheet(f"color: {Styles.SUCCESS}; font-weight: bold; font-size: 14px;")
    
    def _on_delete_clicked(self):
        """Handle delete selected button click."""
        selected_rows = set(item.row() for item in self.voucher_table.selectedItems())
        
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select vouchers to delete.")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete {len(selected_rows)} voucher(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            voucher_ids = []
            for row in selected_rows:
                voucher_id = self.voucher_table.item(row, 0).data(Qt.UserRole)
                voucher_ids.append(voucher_id)
            
            for vid in voucher_ids:
                self.data_service.delete_voucher(vid)
            
            QMessageBox.information(self, "Deleted", f"Deleted {len(voucher_ids)} voucher(s).")
            self.refresh_data()
    
    def _on_approve_all_clicked(self):
        """Handle approve all button click."""
        pending = [v for v in self._vouchers if v.status == VoucherStatus.PENDING_REVIEW]
        
        if not pending:
            QMessageBox.information(self, "No Pending", "No pending vouchers to approve.")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Approval",
            f"Are you sure you want to approve {len(pending)} voucher(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for voucher in pending:
                voucher.status = VoucherStatus.APPROVED
                self.data_service.update_voucher(voucher)
            
            QMessageBox.information(self, "Approved", f"Approved {len(pending)} voucher(s).")
            self.vouchers_approved.emit(pending)
            self.refresh_data()
    
    def showEvent(self, event):
        """Handle tab becoming visible."""
        super().showEvent(event)
        self.refresh_data()
