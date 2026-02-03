"""Review & Validation Tab - Review vouchers before export."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QFrame, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
    QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush
from datetime import datetime

from services.data_service import DataService
from .styles import Styles

class ReviewValidationTab(QWidget):
    """
    Review and validation screen for vouchers.
    Compatible with both legacy Voucher objects and new DebitVoucher types.
    """
    
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
        
        # Headers adjusted for compatibility
        headers = ["Date", "Type", "Voucher No", "Ledger / Particulars", "Amount", "Segment", "Status", "Source"]
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
        try:
            self._vouchers = self.data_service.get_vouchers()
            self._update_table()
            self._update_summary()
            self._validate_vouchers()
        except Exception as e:
            QMessageBox.critical(self, "Data Error", f"Failed to refresh data: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _get_voucher_attr(self, voucher, attr_name, default=None):
        """Helper to get attribute from object or dict."""
        if isinstance(voucher, dict):
            return voucher.get(attr_name, default)
        return getattr(voucher, attr_name, default)

    def _update_table(self):
        """Update the voucher table with compatibility for new and old models."""
        self.voucher_table.setRowCount(0)
        
        for voucher in self._vouchers:
            row_idx = self.voucher_table.rowCount()
            self.voucher_table.insertRow(row_idx)
            
            # --- 1. DATE ---
            # Try 'voucher_date' (new model) then 'date' (old model)
            v_date = self._get_voucher_attr(voucher, 'voucher_date')
            if not v_date:
                v_date = self._get_voucher_attr(voucher, 'date')
            
            date_str = ""
            if isinstance(v_date, str):
                date_str = v_date
            elif isinstance(v_date, datetime):
                date_str = v_date.strftime("%Y-%m-%d")
            self.voucher_table.setItem(row_idx, 0, QTableWidgetItem(date_str))
            
            # --- 2. TYPE ---
            v_type = self._get_voucher_attr(voucher, 'voucher_type', 'Unknown')
            # Handle Enum
            v_type_str = v_type.value if hasattr(v_type, 'value') else str(v_type)
            
            type_item = QTableWidgetItem(v_type_str)
            if "Debit" in v_type_str or "Purchase" in v_type_str or "Payroll" in v_type_str:
                type_item.setForeground(QBrush(QColor(Styles.ERROR)))
            else:
                type_item.setForeground(QBrush(QColor(Styles.SUCCESS)))
            self.voucher_table.setItem(row_idx, 1, type_item)
            
            # --- 3. VOUCHER NO / ACCOUNT CODE ---
            v_no = self._get_voucher_attr(voucher, 'voucher_no')
            if not v_no:
                v_no = self._get_voucher_attr(voucher, 'voucher_id', '') # Fallback
            self.voucher_table.setItem(row_idx, 2, QTableWidgetItem(str(v_no)))
            
            # --- 4. LEDGER / NAME ---
            name = "Unknown"
            if hasattr(voucher, 'supplier_ledger') and voucher.supplier_ledger:
                name = voucher.supplier_ledger
            elif hasattr(voucher, 'party_ledger') and voucher.party_ledger:
                name = voucher.party_ledger
            elif hasattr(voucher, 'entries') and voucher.entries:
                 name = "Multiple (Journal)"
            elif self._get_voucher_attr(voucher, 'account_name'):
                name = self._get_voucher_attr(voucher, 'account_name')
            
            # Dict fallback
            if name == "Unknown" and isinstance(voucher, dict):
                 name = voucher.get('supplier_ledger') or voucher.get('party_ledger') or voucher.get('account_name', 'Unknown')

            self.voucher_table.setItem(row_idx, 3, QTableWidgetItem(str(name)))
            
            # --- 5. AMOUNT ---
            amt = 0.0
            if hasattr(voucher, 'total_amount'): # Purchase property
                amt = voucher.total_amount
            elif hasattr(voucher, 'total_debit'): # Journal property
                amt = voucher.total_debit
            elif hasattr(voucher, 'amount'): # Payroll/Old
                amt = voucher.amount
            elif isinstance(voucher, dict):
                amt = voucher.get('amount', 0.0)
                
            amount_item = QTableWidgetItem(f"₹ {amt:,.2f}")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.voucher_table.setItem(row_idx, 4, amount_item)
            
            # --- 6. SEGMENT ---
            seg = ""
            if hasattr(voucher, 'business_unit') and voucher.business_unit:
                seg = voucher.business_unit
            elif hasattr(voucher, 'salary_subcode') and voucher.salary_subcode:
                 seg = voucher.salary_subcode
            elif hasattr(voucher, 'entries') and voucher.entries:
                # Try to find first non-empty subcode
                for e in voucher.entries:
                    if hasattr(e, 'subcode') and e.subcode:
                        seg = e.subcode
                        break
            elif self._get_voucher_attr(voucher, 'segment'):
                seg = self._get_voucher_attr(voucher, 'segment')
            
            self.voucher_table.setItem(row_idx, 5, QTableWidgetItem(str(seg)))
            
            # --- 7. STATUS ---
            status_val = self._get_voucher_attr(voucher, 'status', 'Draft')
            status_str = status_val.value if hasattr(status_val, 'value') else str(status_val)
            
            status_item = QTableWidgetItem(status_str)
            if "Approved" in status_str:
                status_item.setForeground(QBrush(QColor(Styles.SUCCESS)))
            elif "Pending" in status_str or "Imported" in status_str or "Draft" in status_str:
                status_item.setForeground(QBrush(QColor(Styles.WARNING)))
            self.voucher_table.setItem(row_idx, 6, status_item)
            
            # --- 8. SOURCE ---
            src = self._get_voucher_attr(voucher, 'source', 'Import')
            self.voucher_table.setItem(row_idx, 7, QTableWidgetItem(str(src)))
            
            # Store ID in user data (use voucher_no as ID if voucher_id missing)
            vid = self._get_voucher_attr(voucher, 'voucher_id')
            if not vid: vid = v_no
            self.voucher_table.item(row_idx, 0).setData(Qt.UserRole, vid)
        
        self.voucher_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.voucher_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
    
    def _update_summary(self):
        """Update summary totals."""
        total_debits = 0.0
        total_credits = 0.0
        
        for v in self._vouchers:
            # Determine amount
            amt = 0.0
            if hasattr(v, 'total_amount'): amt = v.total_amount
            elif hasattr(v, 'total_debit'): amt = v.total_debit
            elif hasattr(v, 'amount'): amt = v.amount
            elif isinstance(v, dict): amt = v.get('amount', 0.0)
            
            # Determine type (heuristic)
            v_type = self._get_voucher_attr(v, 'voucher_type', '')
            v_type_str = str(v_type).lower()
            
            if 'credit' in v_type_str or 'sales' in v_type_str:
                total_credits += amt
            else:
                # Purchase, Payroll, Journal (usually treated as expenses/debits in this context)
                total_debits += amt

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
        
        # Count pending
        pending_count = 0
        for v in self._vouchers:
            status = str(self._get_voucher_attr(v, 'status', '')).lower()
            if 'pending' in status or 'draft' in status or 'imported' in status:
                pending_count += 1
                
        self.pending_count_label.setText(str(pending_count))
    
    def _validate_vouchers(self):
        """Validate vouchers and update status."""
        # For now, simplistic validation
        if len(self._vouchers) == 0:
            self.validation_icon.setText("○")
            self.validation_icon.setStyleSheet(f"color: {Styles.TEXT_MUTED}; font-size: 20px;")
            self.validation_message.setText("No vouchers to validate")
            self.validation_message.setStyleSheet(f"color: {Styles.TEXT_SECONDARY}; font-size: 14px;")
        else:
            # Check if any Journal is unbalanced
            unbalanced_journals = 0
            for v in self._vouchers:
                if hasattr(v, 'is_balanced') and not v.is_balanced:
                    unbalanced_journals += 1
            
            if unbalanced_journals > 0:
                self.validation_icon.setText("⚠")
                self.validation_icon.setStyleSheet(f"color: {Styles.ERROR}; font-size: 20px;")
                self.validation_message.setText(
                    f"WARNING: {unbalanced_journals} Journal Voucher(s) are unbalanced!"
                )
                self.validation_message.setStyleSheet(f"color: {Styles.ERROR}; font-weight: bold; font-size: 14px;")
            else:
                self.validation_icon.setText("✓")
                self.validation_icon.setStyleSheet(f"color: {Styles.SUCCESS}; font-size: 20px;")
                self.validation_message.setText("PASSED: All vouchers look valid")
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
            # Find IDs to delete
            ids_to_delete = []
            for row in selected_rows:
                # We stored ID in the UserRole of column 0
                vid = self.voucher_table.item(row, 0).data(Qt.UserRole)
                if vid:
                    ids_to_delete.append(vid)
            
            # Pass to data service (bulk delete if supported, else loop)
            # Assuming data service has delete_voucher(id)
            if hasattr(self.data_service, 'delete_voucher'):
                for vid in ids_to_delete:
                    self.data_service.delete_voucher(vid)
            else:
                 QMessageBox.warning(self, "Error", "Data service does not support deletion.")
                 return
            
            # Reload
            self.refresh_data()
            QMessageBox.information(self, "Deleted", f"Deleted {len(ids_to_delete)} voucher(s).")
    
    def _on_approve_all_clicked(self):
        """Handle approve all button click. FIXED."""
        pending = []
        for v in self._vouchers:
            s = str(self._get_voucher_attr(v, 'status', '')).lower()
            if 'pending' in s or 'draft' in s or 'imported' in s:
                pending.append(v)
        
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
            count = 0
            for voucher in pending:
                # FIX: Explicitly set status to string 'Approved'
                if isinstance(voucher, dict):
                    voucher['status'] = "Approved"
                    count += 1
                elif hasattr(voucher, 'status'):
                    # Handle if status is an Enum, try to set value or string
                    try:
                         # Try string first
                         voucher.status = "Approved"
                         count += 1
                    except:
                         pass

            # FIX: Ensure changes are saved to file
            if hasattr(self.data_service, 'save_vouchers'):
                self.data_service.save_vouchers()
            else:
                 # Fallback if specific method exists
                 pass
            
            QMessageBox.information(self, "Approved", f"Approved {count} voucher(s).")
            self.vouchers_approved.emit(pending)
            self.refresh_data()
    
    def showEvent(self, event):
        """Handle tab becoming visible."""
        super().showEvent(event)
        self.refresh_data()