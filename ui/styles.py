"""
iCare Accounting - Style Definitions

Brand Colors based on iCare Life:
- Primary: Teal (#00A4A6) - Healthcare/trust
- Secondary: Deep Blue (#1E3A5F) - Professional
- Accent: Coral (#FF6B6B) - Call to action
- Success: Green (#4CAF50)
- Warning: Orange (#FF9800)
- Error: Red (#F44336)
- Background: Light Gray (#F5F7FA)
- Card: White (#FFFFFF)
- Text: Dark Gray (#2C3E50)

Admin Credentials:
- Password: Subudhi123
"""


class Styles:
    """Central style definitions for the application."""
    
    # Brand Colors
    PRIMARY = "#00A4A6"  # Teal
    PRIMARY_DARK = "#008B8D"
    PRIMARY_LIGHT = "#4DB8B9"
    
    SECONDARY = "#1E3A5F"  # Deep Blue
    SECONDARY_DARK = "#152A45"
    SECONDARY_LIGHT = "#2D5A8A"
    
    ACCENT = "#FF6B6B"  # Coral
    
    SUCCESS = "#4CAF50"
    WARNING = "#FF9800"
    ERROR = "#F44336"
    INFO = "#2196F3"
    
    # Background Colors
    BG_PRIMARY = "#F5F7FA"
    BG_SECONDARY = "#E8EDF2"
    BG_CARD = "#FFFFFF"
    BG_DARK = "#2C3E50"
    
    # Text Colors
    TEXT_PRIMARY = "#1A252F"  # Darker for better visibility
    TEXT_SECONDARY = "#4A5568"  # Darker secondary
    TEXT_LIGHT = "#FFFFFF"
    TEXT_MUTED = "#718096"
    
    # Border Colors
    BORDER_LIGHT = "#CBD5E0"
    BORDER_MEDIUM = "#A0AEC0"
    
    # Label Colors
    LABEL_COLOR = "#1A252F"  # Dark for form labels
    
    @classmethod
    def get_main_stylesheet(cls) -> str:
        """Get the main application stylesheet."""
        return f"""
            /* Main Window */
            QMainWindow {{
                background-color: {cls.BG_PRIMARY};
            }}
            
            /* Scroll Area */
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            
            QScrollArea > QWidget > QWidget {{
                background-color: transparent;
            }}
            
            /* Tab Widget */
            QTabWidget::pane {{
                border: 2px solid {cls.BORDER_LIGHT};
                background-color: {cls.BG_CARD};
                border-radius: 8px;
                padding: 5px;
            }}
            
            QTabWidget::tab-bar {{
                alignment: left;
            }}
            
            QTabBar::tab {{
                background-color: {cls.BG_SECONDARY};
                color: {cls.TEXT_PRIMARY};
                padding: 14px 28px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 600;
                font-size: 14px;
            }}
            
            QTabBar::tab:selected {{
                background-color: {cls.PRIMARY};
                color: {cls.TEXT_LIGHT};
            }}
            
            QTabBar::tab:hover:!selected {{
                background-color: {cls.PRIMARY_LIGHT};
                color: {cls.TEXT_LIGHT};
            }}
            
            /* Labels - Enhanced Visibility */
            QLabel {{
                color: {cls.LABEL_COLOR};
                font-size: 14px;
                font-weight: 500;
            }}
            
            QLabel[class="title"] {{
                font-size: 20px;
                font-weight: bold;
                color: {cls.SECONDARY};
            }}
            
            QLabel[class="subtitle"] {{
                font-size: 14px;
                color: {cls.TEXT_SECONDARY};
            }}
            
            QLabel[class="field-label"] {{
                font-size: 14px;
                font-weight: 600;
                color: {cls.SECONDARY};
                padding-bottom: 4px;
            }}
            
            /* Input Fields - Compact */
            QLineEdit, QSpinBox, QDoubleSpinBox {{
                padding: 8px 10px;
                border: 1px solid {cls.BORDER_MEDIUM};
                border-radius: 4px;
                background-color: {cls.BG_CARD};
                color: {cls.TEXT_PRIMARY};
                font-size: 13px;
                min-height: 18px;
            }}
            
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border-color: {cls.PRIMARY};
                border-width: 2px;
            }}
            
            QLineEdit:disabled {{
                background-color: {cls.BG_SECONDARY};
                color: {cls.TEXT_MUTED};
            }}
            
            /* ComboBox - Compact with visible dropdown */
            QComboBox {{
                padding: 8px 10px;
                padding-right: 32px;
                border: 1px solid {cls.BORDER_MEDIUM};
                border-radius: 4px;
                background-color: {cls.BG_CARD};
                color: {cls.TEXT_PRIMARY};
                font-size: 13px;
                min-height: 18px;
                selection-background-color: {cls.PRIMARY};
                selection-color: {cls.TEXT_LIGHT};
            }}
            
            QComboBox:focus {{
                border-color: {cls.PRIMARY};
            }}
            
            QComboBox:hover {{
                border-color: {cls.PRIMARY_LIGHT};
            }}
            
            QComboBox:disabled {{
                background-color: {cls.BG_SECONDARY};
                color: {cls.TEXT_MUTED};
            }}
            
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 28px;
                border-left: 1px solid {cls.BORDER_LIGHT};
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
                background-color: {cls.PRIMARY};
            }}
            
            QComboBox::down-arrow {{
                width: 0;
                height: 0;
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 8px solid {cls.TEXT_LIGHT};
            }}
            
            /* Dropdown List View - Compact */
            QComboBox QAbstractItemView {{
                background-color: {cls.BG_CARD};
                border: 1px solid {cls.BORDER_MEDIUM};
                border-radius: 4px;
                padding: 2px;
                outline: none;
            }}
            
            QComboBox QAbstractItemView::item {{
                padding: 8px 12px;
                min-height: 24px;
                color: {cls.TEXT_PRIMARY};
                background-color: {cls.BG_CARD};
                border-radius: 3px;
                margin: 1px 0px;
            }}
            
            QComboBox QAbstractItemView::item:selected {{
                background-color: {cls.PRIMARY};
                color: {cls.TEXT_LIGHT};
            }}
            
            QComboBox QAbstractItemView::item:hover {{
                background-color: {cls.PRIMARY_LIGHT};
                color: {cls.TEXT_LIGHT};
            }}
            
            /* Fix for QListView inside ComboBox - Compact */
            QComboBox QListView {{
                background-color: {cls.BG_CARD};
                color: {cls.TEXT_PRIMARY};
                selection-background-color: {cls.PRIMARY};
                selection-color: {cls.TEXT_LIGHT};
                outline: none;
                show-decoration-selected: 1;
            }}
            
            QComboBox QListView::item {{
                color: {cls.TEXT_PRIMARY};
                background-color: {cls.BG_CARD};
                padding: 6px 10px;
                min-height: 22px;
            }}
            
            QComboBox QListView::item:selected {{
                background-color: {cls.PRIMARY};
                color: {cls.TEXT_LIGHT};
            }}
            
            QComboBox QListView::item:hover {{
                background-color: {cls.PRIMARY_LIGHT};
                color: {cls.TEXT_LIGHT};
            }}
            
            /* Buttons - Compact */
            QPushButton {{
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 600;
                min-width: 100px;
            }}
            
            QPushButton[class="primary"] {{
                background-color: {cls.PRIMARY};
                color: {cls.TEXT_LIGHT};
            }}
            
            QPushButton[class="primary"]:hover {{
                background-color: {cls.PRIMARY_DARK};
            }}
            
            QPushButton[class="primary"]:pressed {{
                background-color: {cls.SECONDARY};
            }}
            
            QPushButton[class="secondary"] {{
                background-color: {cls.BG_SECONDARY};
                color: {cls.TEXT_PRIMARY};
                border: 2px solid {cls.BORDER_MEDIUM};
            }}
            
            QPushButton[class="secondary"]:hover {{
                background-color: {cls.BORDER_LIGHT};
                border-color: {cls.PRIMARY};
            }}
            
            QPushButton[class="success"] {{
                background-color: {cls.SUCCESS};
                color: {cls.TEXT_LIGHT};
            }}
            
            QPushButton[class="success"]:hover {{
                background-color: #43A047;
            }}
            
            QPushButton[class="danger"] {{
                background-color: {cls.ERROR};
                color: {cls.TEXT_LIGHT};
            }}
            
            QPushButton[class="danger"]:hover {{
                background-color: #E53935;
            }}
            
            QPushButton:disabled {{
                background-color: {cls.BORDER_LIGHT};
                color: {cls.TEXT_MUTED};
            }}
            
            /* Radio Buttons - Compact */
            QRadioButton {{
                color: {cls.TEXT_PRIMARY};
                font-size: 13px;
                font-weight: 500;
                spacing: 6px;
                padding: 4px;
            }}
            
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
            }}
            
            QRadioButton::indicator:checked {{
                background-color: {cls.PRIMARY};
                border: 2px solid {cls.PRIMARY_DARK};
                border-radius: 8px;
            }}
            
            QRadioButton::indicator:unchecked {{
                background-color: {cls.BG_CARD};
                border: 2px solid {cls.BORDER_MEDIUM};
                border-radius: 8px;
            }}
            
            QRadioButton::indicator:unchecked:hover {{
                border-color: {cls.PRIMARY};
            }}
            
            /* Group Box - Compact */
            QGroupBox {{
                font-weight: bold;
                font-size: 13px;
                color: {cls.SECONDARY};
                border: 1px solid {cls.BORDER_LIGHT};
                border-radius: 6px;
                margin-top: 12px;
                padding: 12px 10px 10px 10px;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 8px;
                background-color: {cls.BG_CARD};
                color: {cls.SECONDARY};
                font-size: 12px;
                font-weight: bold;
            }}
            
            /* Table Widget */
            QTableWidget {{
                background-color: {cls.BG_CARD};
                border: 2px solid {cls.BORDER_LIGHT};
                border-radius: 8px;
                gridline-color: {cls.BORDER_LIGHT};
                font-size: 13px;
            }}
            
            QTableWidget::item {{
                padding: 10px;
                color: {cls.TEXT_PRIMARY};
            }}
            
            QTableWidget::item:selected {{
                background-color: {cls.PRIMARY};
                color: {cls.TEXT_LIGHT};
            }}
            
            QHeaderView::section {{
                background-color: {cls.SECONDARY};
                color: {cls.TEXT_LIGHT};
                padding: 12px;
                border: none;
                font-weight: bold;
                font-size: 13px;
            }}
            
            /* Scroll Bars - More Visible */
            QScrollBar:vertical {{
                background-color: {cls.BG_SECONDARY};
                width: 14px;
                border-radius: 7px;
                margin: 2px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {cls.BORDER_MEDIUM};
                border-radius: 6px;
                min-height: 40px;
                margin: 2px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: {cls.PRIMARY};
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            
            QScrollBar:horizontal {{
                background-color: {cls.BG_SECONDARY};
                height: 14px;
                border-radius: 7px;
                margin: 2px;
            }}
            
            QScrollBar::handle:horizontal {{
                background-color: {cls.BORDER_MEDIUM};
                border-radius: 6px;
                min-width: 40px;
                margin: 2px;
            }}
            
            QScrollBar::handle:horizontal:hover {{
                background-color: {cls.PRIMARY};
            }}
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            
            /* Date Edit - Compact */
            QDateEdit {{
                padding: 6px 8px;
                border: 1px solid {cls.BORDER_MEDIUM};
                border-radius: 4px;
                background-color: {cls.BG_CARD};
                color: {cls.TEXT_PRIMARY};
                font-size: 12px;
                min-height: 16px;
            }}
            
            QDateEdit:focus {{
                border-color: {cls.PRIMARY};
            }}
            
            QDateEdit::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: center right;
                width: 24px;
                border-left: 1px solid {cls.BORDER_LIGHT};
                background-color: {cls.PRIMARY};
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
            
            /* Calendar Widget */
            QCalendarWidget {{
                background-color: {cls.BG_CARD};
            }}
            
            QCalendarWidget QToolButton {{
                color: {cls.TEXT_PRIMARY};
                background-color: {cls.BG_CARD};
                border: none;
                border-radius: 4px;
                padding: 6px;
                font-weight: bold;
            }}
            
            QCalendarWidget QToolButton:hover {{
                background-color: {cls.PRIMARY_LIGHT};
                color: {cls.TEXT_LIGHT};
            }}
            
            /* Message Box */
            QMessageBox {{
                background-color: {cls.BG_CARD};
            }}
            
            QMessageBox QLabel {{
                color: {cls.TEXT_PRIMARY};
                font-size: 14px;
            }}
            
            QMessageBox QPushButton {{
                background-color: {cls.PRIMARY};
                color: {cls.TEXT_LIGHT};
                padding: 10px 25px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                min-width: 80px;
                min-height: 35px;
            }}
            
            QMessageBox QPushButton:hover {{
                background-color: {cls.PRIMARY_DARK};
            }}
            
            QMessageBox QPushButton:focus {{
                border: 2px solid {cls.SECONDARY};
            }}
            
            /* Dialog Buttons */
            QDialogButtonBox QPushButton {{
                background-color: {cls.PRIMARY};
                color: {cls.TEXT_LIGHT};
                padding: 10px 25px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
                min-width: 80px;
                min-height: 35px;
            }}
            
            QDialogButtonBox QPushButton:hover {{
                background-color: {cls.PRIMARY_DARK};
            }}
            
            /* Progress Bar */
            QProgressBar {{
                border: 2px solid {cls.BORDER_LIGHT};
                border-radius: 8px;
                background-color: {cls.BG_SECONDARY};
                height: 20px;
                text-align: center;
                font-weight: bold;
            }}
            
            QProgressBar::chunk {{
                background-color: {cls.PRIMARY};
                border-radius: 6px;
            }}
            
            /* Status Bar */
            QStatusBar {{
                background-color: {cls.SECONDARY};
                color: {cls.TEXT_LIGHT};
                font-size: 13px;
                padding: 5px;
            }}
            
            /* Frame */
            QFrame[class="card"] {{
                background-color: {cls.BG_CARD};
                border: 2px solid {cls.BORDER_LIGHT};
                border-radius: 8px;
                padding: 20px;
            }}
            
            /* CheckBox */
            QCheckBox {{
                color: {cls.TEXT_PRIMARY};
                font-size: 14px;
                font-weight: 500;
                spacing: 10px;
            }}
            
            QCheckBox::indicator {{
                width: 22px;
                height: 22px;
                border-radius: 4px;
            }}
            
            QCheckBox::indicator:unchecked {{
                background-color: {cls.BG_CARD};
                border: 2px solid {cls.BORDER_MEDIUM};
            }}
            
            QCheckBox::indicator:checked {{
                background-color: {cls.PRIMARY};
                border: 2px solid {cls.PRIMARY_DARK};
            }}
        """
    
    @classmethod
    def get_header_style(cls) -> str:
        """Get header section style."""
        return f"""
            background-color: {cls.SECONDARY};
            padding: 20px;
            border-radius: 8px;
        """
    
    @classmethod
    def get_card_style(cls) -> str:
        """Get card container style."""
        return f"""
            background-color: {cls.BG_CARD};
            border: 2px solid {cls.BORDER_LIGHT};
            border-radius: 8px;
            padding: 20px;
        """
    
    @classmethod
    def get_form_label_style(cls) -> str:
        """Get style for form field labels."""
        return f"""
            color: {cls.SECONDARY};
            font-size: 14px;
            font-weight: 600;
            padding: 2px 0;
        """
    
    @classmethod 
    def get_summary_card_style(cls, variant: str = "default") -> str:
        """Get summary card style with color variants."""
        colors = {
            "default": cls.PRIMARY,
            "success": cls.SUCCESS,
            "warning": cls.WARNING,
            "error": cls.ERROR,
            "info": cls.INFO
        }
        color = colors.get(variant, cls.PRIMARY)
        
        return f"""
            background-color: {cls.BG_CARD};
            border-left: 5px solid {color};
            border-radius: 8px;
            padding: 20px;
        """
    
    @classmethod
    def get_compact_date_style(cls) -> str:
        """Get compact date picker style."""
        return f"""
            QDateEdit {{
                padding: 4px 6px;
                border: 1px solid {cls.BORDER_MEDIUM};
                border-radius: 4px;
                background-color: {cls.BG_CARD};
                color: {cls.TEXT_PRIMARY};
                font-size: 12px;
                min-width: 100px;
                max-height: 28px;
            }}
            QDateEdit:focus {{
                border-color: {cls.PRIMARY};
            }}
            QDateEdit::drop-down {{
                width: 20px;
                border-left: 1px solid {cls.BORDER_LIGHT};
                background-color: {cls.PRIMARY};
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
        """
    
    @classmethod
    def get_error_label_style(cls) -> str:
        """Get inline error label style."""
        return f"""
            color: {cls.ERROR};
            font-size: 11px;
            font-weight: 500;
            padding: 2px 0;
        """
    
    @classmethod
    def get_helper_text_style(cls) -> str:
        """Get helper text style."""
        return f"""
            color: {cls.TEXT_MUTED};
            font-size: 11px;
            font-weight: normal;
            font-style: italic;
        """
