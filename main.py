#!/usr/bin/env python3
"""
iCare Life - Accounting System

A pre-accounting desktop application for:
- Voucher entry with strict dropdown controls
- Bulk CSV import (Wix sales)
- Review and validation
- MIS report generation
- Tally XML export

Platform: Windows
UI Framework: PySide6
Data Storage: JSON (local/shared folder)

Copyright (c) 2025 iCare Life
"""

import sys
import os

# Add the app directory to Python path
app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.main_window import MainWindow


def main():
    """Application entry point."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Create application
    app = QApplication(sys.argv)
    
    # Set application info
    app.setApplicationName("iCare Accounting")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("iCare Life")
    app.setOrganizationDomain("icare.life")
    
    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Create and show main window
    window = MainWindow()
    window.showMaximized()
    
    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
