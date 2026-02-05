"""Review & Validation Tab - Review vouchers before export."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QGroupBox, QFrame, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
    QAbstractItemView, QDialog, QFormLayout, QTextEdit, QLineEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QFont
from datetime import datetime

from services.data_service import DataService
from .styles import Styles

# --- NEW CLASS: Voucher Detail Pop-up ---
class VoucherDetailDialog(QDialog):
    """Pop-up window to view full voucher details with Accounting Entry Table."""
    def __init__(self, voucher, parent=None):
        super().__init__(parent)
        
        # Robust Title
        v_id = self._get_safe_val(voucher, 'voucher_id') or self._get_safe_val(voucher, 'voucher_no')
        self.setWindowTitle(f"Voucher Details - {v_id}")
        self.setMinimumSize(850, 700)
        
        # Styles: White Background, Blue Text
        self.setStyleSheet(f"""
            QDialog {{ background-color: white; }}
            QWidget {{ background-color: white; color: {Styles.PRIMARY}; }}
            
            QLabel {{
                color: {Styles.PRIMARY};
                font-weight: bold;
                font-size: 13px;
            }}
            
            QLineEdit {{ 
                background-color: white; 
                color: {Styles.PRIMARY}; 
                border: 1px solid #ccc; 
                border-radius: 4px; 
                padding: 6px;
            }}
            
            QTextEdit {{
                background-color: white; 
                color: {Styles.PRIMARY};
                border: 1px solid #ccc; 
                border-radius: 4px; 
                padding: 6px;
            }}
            
            QTableWidget {{
                background-color: white; 
                color: {Styles.PRIMARY};
                gridline-color: #e0e0e0; 
                border: 1px solid #ccc;
            }}
            
            QHeaderView::section {{
                background-color: #f8f9fa; 
                color: {Styles.PRIMARY};
                font-weight: bold; 
                border: 1px solid #ddd; 
                padding: 6px;
            }}
            
            QPushButton {{ 
                background-color: {Styles.SECONDARY}; 
                color: white; 
                border-radius: 4px; 
                padding: 8px 16px; 
                font-weight: bold; 
            }}
            QPushButton:hover {{ background-color: #333; }}
        """)
        
        layout = QVBoxLayout(self)
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;") 
        
        content_widget = QWidget()
        form_layout = QVBoxLayout(content_widget)
        form_layout.setSpacing(15)
        form_layout.setContentsMargins(20, 20, 20, 20)
        
        # --- SECTION 1: Header Info ---
        header_group = QGroupBox("General Information")
        header_group.setStyleSheet(f"QGroupBox {{ border: 1px solid #ddd; margin-top: 10px; }} QGroupBox::title {{ color: {Styles.PRIMARY}; top: -10px; left: 10px; }}")
        header_layout = QFormLayout(header_group)
        header_layout.setSpacing(10)

        # Parsing Logic for Product/Location from Narration (Payroll)
        narration_text = (
            self._get_safe_val(voucher, 'narration') or 
            self._get_safe_val(voucher, 'remarks') or 
            self._get_safe_val(voucher, 'description') or 
            self._get_safe_val(voucher, 'notes')
        )
        
        product = ""
        location = ""
        if narration_text.startswith("Payroll |"):
            parts = narration_text.split("|")
            if len(parts) > 2:
                product = parts[1].strip()
                location = parts[2].strip()

        # Display Fields
        def add_row(label, value):
            field = QLineEdit(str(value))
            field.setReadOnly(True)
            header_layout.addRow(QLabel(label + ":"), field)

        add_row("Voucher ID", v_id)
        
        v_date = self._get_safe_val(voucher, 'voucher_date')
        if not v_date: v_date = self._get_safe_val(voucher, 'date')
        add_row("Date", v_date)
        
        v_type = self._get_safe_val(voucher, 'voucher_type')
        add_row("Type", v_type)
        
        if product: add_row("Product", product)
        if location: add_row("Location", location)

        # Account Logic (FIX: prioritize tally_head for Manual Entries)
        acc_name = "Unknown"
        if hasattr(voucher, 'tally_head') and voucher.tally_head: acc_name = voucher.tally_head
        elif hasattr(voucher, 'supplier_ledger') and voucher.supplier_ledger: acc_name = voucher.supplier_ledger
        elif hasattr(voucher, 'party_ledger') and voucher.party_ledger: acc_name = voucher.party_ledger
        elif hasattr(voucher, 'entries') and voucher.entries: acc_name = "Multi-Entry Journal"
        elif hasattr(voucher, 'ledger_name') and voucher.ledger_name: acc_name = voucher.ledger_name
        else: acc_name = self._get_safe_val(voucher, 'account_name', 'Unknown')
        add_row("Account", acc_name)
        
        form_layout.addWidget(header_group)

        # --- SECTION 2: Accounting Entry Table ---
        lbl_table = QLabel("Accounting Entry")
        lbl_table.setStyleSheet(f"font-size: 15px; text-decoration: underline; margin-top: 10px;")
        form_layout.addWidget(lbl_table)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Ledger", "Dr. Amount", "Cr. Amount"])
        
        # Read-only Table
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)     
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        self.table.setMinimumHeight(250)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(f"alternate-background-color: #f9f9f9; background-color: white; color: {Styles.PRIMARY};")
        
        # Populate Table Logic
        self._populate_accounting_table(voucher, narration_text)
        form_layout.addWidget(self.table)

        # --- SECTION 3: Full Narration ---
        lbl_narr = QLabel("Narration")
        form_layout.addWidget(lbl_narr)
        
        narr_box = QTextEdit(narration_text)
        narr_box.setReadOnly(True)
        narr_box.setMaximumHeight(60)
        # Force Text Color for Narration Box
        narr_box.setStyleSheet(f"color: {Styles.PRIMARY}; background-color: white; border: 1px solid #ccc;")
        form_layout.addWidget(narr_box)

        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # Close Button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumHeight(40)
        layout.addWidget(close_btn)

    def _populate_accounting_table(self, voucher, narration):
        """
        Parses data to build the Ledger | Dr | Cr table.
        FIX: Prioritizes 'tally_head' attribute for displaying Selected Tally Head.
        """
        rows = []
        
        # Helper to get float amount safely
        def get_amt(attr, obj=voucher):
            if isinstance(obj, dict): val = obj.get(attr, 0)
            else: val = getattr(obj, attr, 0)
            try: return float(val) if val else 0.0
            except: return 0.0

        main_amount = get_amt('amount') or get_amt('total_amount')
        
        # Clean narration for display
        clean_narr = " ".join(narration.split()) if narration else ""
        narr_suffix = f"\n({clean_narr})" if clean_narr else ""

        # --- CASE 1: BULK IMPORT (Payroll String) ---
        if "Payroll |" in narration or "PF(Emp):" in narration:
            
            def get_val(key):
                try:
                    start = narration.find(key)
                    if start == -1: return 0.0
                    sub = narration[start + len(key):]
                    val_str = sub.split('|')[0].strip()
                    return float(val_str) if val_str else 0.0
                except:
                    return 0.0

            pf_emp = get_val("PF(Emp):")
            pf_empr = get_val("PF(Empr):")
            esic_emp = get_val("ESIC(Emp):")
            esic_empr = get_val("ESIC(Empr):")
            pt = get_val("PT:")
            tds = get_val("TDS:")
            
            total_debit = main_amount + pf_emp + pf_empr + esic_emp + esic_empr + pt + tds
            
            rows.append((f"Salary & Wages{narr_suffix}", total_debit, 0))
            
            if pf_emp > 0.01: rows.append((f"Employee Share of PF Payable{narr_suffix}", 0, pf_emp))
            if pf_empr > 0.01: rows.append((f"Employer Share of PF Payable{narr_suffix}", 0, pf_empr))
            if esic_emp > 0.01: rows.append((f"Employee Share of ESIC Payable{narr_suffix}", 0, esic_emp))
            if esic_empr > 0.01: rows.append((f"Employer Share of ESIC Payable{narr_suffix}", 0, esic_empr))
            if pt > 0.01: rows.append((f"Professional Tax Payable{narr_suffix}", 0, pt))
            if tds > 0.01: rows.append((f"TDS on Salary Payable - FY 2026-27{narr_suffix}", 0, tds))
            
            rows.append((f"Salary Payable{narr_suffix}", 0, abs(float(main_amount))))

        # --- CASE 2: MANUAL PURCHASE VOUCHER ---
        elif hasattr(voucher, 'supplier_ledger') and hasattr(voucher, 'expense_ledger'):
            base = get_amt('base_amount') or main_amount
            
            # FIX: Check for 'tally_head' first, then 'expense_ledger'
            exp_name = getattr(voucher, 'tally_head', '') or getattr(voucher, 'expense_ledger', '') or 'Expense Account'
            rows.append((f"{exp_name}{narr_suffix}", base, 0))
            
            if hasattr(voucher, 'gst') and voucher.gst:
                cgst = get_amt('cgst_amount', voucher.gst)
                sgst = get_amt('sgst_amount', voucher.gst)
                igst = get_amt('igst_amount', voucher.gst)
                if cgst: rows.append((f"Input CGST{narr_suffix}", cgst, 0))
                if sgst: rows.append((f"Input SGST{narr_suffix}", sgst, 0))
                if igst: rows.append((f"Input IGST{narr_suffix}", igst, 0))

            tds_amt = 0
            if hasattr(voucher, 'tds') and voucher.tds:
                tds_amt = get_amt('amount', voucher.tds)
                if tds_amt > 0.01:
                    ledger = getattr(voucher.tds, 'ledger_name', 'TDS Payable')
                    rows.append((f"{ledger}{narr_suffix}", 0, tds_amt))
            
            # Check for name, fallback to 'Supplier'
            supp_name = getattr(voucher, 'supplier_ledger', '') or 'Supplier Account'
            rows.append((f"{supp_name}{narr_suffix}", 0, abs(float(main_amount))))

        # --- CASE 3: MANUAL JOURNAL ---
        elif (hasattr(voucher, 'entries') and voucher.entries) or (isinstance(voucher, dict) and 'entries' in voucher):
            entries = voucher.entries if hasattr(voucher, 'entries') else voucher['entries']
            for e in entries:
                if isinstance(e, dict):
                    # FIX: Check for tally_head in dict keys
                    lbl = e.get('tally_head') or e.get('ledger') or e.get('ledger_name') or 'Unknown Ledger'
                    dr = float(e.get('debit_amount', 0))
                    cr = float(e.get('credit_amount', 0))
                else:
                    # FIX: Check for tally_head attribute
                    lbl = getattr(e, 'tally_head', None) or getattr(e, 'ledger', None) or getattr(e, 'ledger_name', None) or 'Unknown Ledger'
                    dr = float(getattr(e, 'debit_amount', 0))
                    cr = float(getattr(e, 'credit_amount', 0))
                
                rows.append((f"{lbl}{narr_suffix}", dr, cr))

        # --- CASE 4: SIMPLE MANUAL ---
        else:
            # FIX: Check for tally_head, ledger_name, account_name
            acc_name = getattr(voucher, 'tally_head', '') or self._get_safe_val(voucher, 'ledger_name') or self._get_safe_val(voucher, 'account_name') or 'General Ledger'
            v_type = self._get_safe_val(voucher, 'voucher_type').lower()
            
            if 'debit' in v_type or 'payment' in v_type or 'purchase' in v_type:
                rows.append((f"{acc_name}{narr_suffix}", main_amount, 0))
                rows.append((f"Bank/Cash/Party{narr_suffix}", 0, main_amount))
            elif 'credit' in v_type or 'receipt' in v_type:
                rows.append((f"Bank/Cash/Party{narr_suffix}", main_amount, 0))
                rows.append((f"{acc_name}{narr_suffix}", 0, main_amount))
            else:
                rows.append((f"{acc_name}{narr_suffix}", main_amount, 0))
                rows.append((f"Suspense{narr_suffix}", 0, main_amount))

        # Render Rows
        self.table.setRowCount(len(rows))
        for i, (ledger, dr, cr) in enumerate(rows):
            # FIX: Explicitly set FOREGROUND COLOR to ensure it is visible
            text_color = QBrush(QColor(Styles.PRIMARY)) # Blue
            
            # Ledger with Word Wrap (Read Only)
            ledger_item = QTableWidgetItem(str(ledger))
            ledger_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            ledger_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable) 
            ledger_item.setForeground(text_color) 
            self.table.setItem(i, 0, ledger_item)
            
            # Format Numbers
            dr_txt = f"{dr:,.2f}" if dr > 0.01 else ""
            cr_txt = f"{cr:,.2f}" if cr > 0.01 else ""
            
            dr_item = QTableWidgetItem(dr_txt)
            dr_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            dr_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            dr_item.setForeground(text_color) 
            
            cr_item = QTableWidgetItem(cr_txt)
            cr_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            cr_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            cr_item.setForeground(text_color) 

            self.table.setItem(i, 1, dr_item)
            self.table.setItem(i, 2, cr_item)
        
        self.table.resizeRowsToContents()

    def _get_safe_val(self, obj, attr, default=""):
        """Helper to safely get attributes from Object or Dict."""
        if isinstance(obj, dict):
            return str(obj.get(attr, default))
        val = getattr(obj, attr, default)
        if hasattr(val, 'value'): return str(val.value)
        return str(val)

# --- MAIN TAB CLASS ---
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
        group = QGroupBox("VOUCHER LIST (Double-click for details)")
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
        
        # FIX: Connect Double Click
        self.voucher_table.cellDoubleClicked.connect(self._open_voucher_detail)
    
    # FIX: Open Detail Dialog Logic
    def _open_voucher_detail(self, row, column):
        """Open popup with voucher details."""
        item = self.voucher_table.item(row, 0)
        if not item: return
        
        # Retrieve the FULL voucher object stored in UserRole
        voucher = item.data(Qt.UserRole)
        
        if voucher:
            dlg = VoucherDetailDialog(voucher, self)
            dlg.exec()

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
            
            # --- 4. LEDGER / NAME (FIX: Prioritize tally_head) ---
            name = "Unknown"
            if hasattr(voucher, 'tally_head') and voucher.tally_head:
                name = voucher.tally_head
            elif hasattr(voucher, 'supplier_ledger') and voucher.supplier_ledger:
                name = voucher.supplier_ledger
            elif hasattr(voucher, 'party_ledger') and voucher.party_ledger:
                name = voucher.party_ledger
            elif hasattr(voucher, 'entries') and voucher.entries:
                 name = "Multiple (Journal)"
            elif hasattr(voucher, 'ledger_name') and voucher.ledger_name:
                name = voucher.ledger_name
            elif self._get_voucher_attr(voucher, 'account_name'):
                name = self._get_voucher_attr(voucher, 'account_name')
            
            # Dict fallback
            if name == "Unknown" and isinstance(voucher, dict):
                 name = voucher.get('tally_head') or voucher.get('supplier_ledger') or voucher.get('party_ledger') or voucher.get('ledger_name') or voucher.get('account_name', 'Unknown')

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
            
            # FIX: Store FULL OBJECT in Column 0 for Pop-up
            self.voucher_table.item(row_idx, 0).setData(Qt.UserRole, voucher)
        
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
                # FIX: Retrieve FULL VOUCHER, then get ID
                voucher = self.voucher_table.item(row, 0).data(Qt.UserRole)
                
                # Extract ID safely
                vid = self._get_voucher_attr(voucher, 'voucher_id')
                if not vid:
                    vid = self._get_voucher_attr(voucher, 'voucher_no')
                
                if vid:
                    ids_to_delete.append(vid)
            
            # Pass to data service (bulk delete if supported, else loop)
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
                    try:
                         voucher.status = "Approved"
                         count += 1
                    except:
                         pass

            # FIX: Ensure changes are saved to file
            if hasattr(self.data_service, 'save_vouchers'):
                self.data_service.save_vouchers()
            else:
                 pass
            
            QMessageBox.information(self, "Approved", f"Approved {count} voucher(s).")
            self.vouchers_approved.emit(pending)
            self.refresh_data()
    
    def showEvent(self, event):
        """Handle tab becoming visible."""
        super().showEvent(event)
        self.refresh_data()