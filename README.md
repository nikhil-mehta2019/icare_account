# iCare Life - Accounting System

A pre-accounting desktop application built with Python 3.11 and PySide6.

## 🔐 ADMIN CREDENTIALS

```
Password: Subudhi123
```

- Only Subudhi can add/edit Account Heads
- Master Settings lock automatically
- Unlock only during Quarter-End windows (Mar 25-Apr 10, Jun 28-Jul 5, Sep 28-Oct 5, Dec 25-Jan 10)

---

## Overview

This application prepares validated accounting data for:
- Tally import (XML export)
- MIS (Management Information System) reporting

## Features

### 1. Voucher Entry
- Strict dropdown-only inputs (no manual typing for account heads/narrations)
- Dynamic filtering: Debit selection shows only Debit heads, Credit shows Credit heads
- Automatic segment tagging
- Amount validation (numeric only)

### 2. Bulk Import (CSV)
- Upload CSV files (e.g., Wix sales export)
- Preview grid with row count and sample data
- Automatic voucher generation from CSV

### 3. Review & Validation
- Total Debits vs Credits comparison
- Difference highlighting (mismatch detection)
- Voucher approval workflow

### 4. Reports
- Date range picker with quick select (This Month, Last Month, This Quarter)
- MIS Excel export (Segmental Profitability Report)
- Tally XML export

### 5. Admin / Settings
- Password-protected access (Default: `Subudhi123`)
- Master data lock toggle
- Quarter-end edit window governance
- Export master data to JSON

## Technical Stack

- **Platform**: Windows
- **UI Framework**: PySide6 (Qt for Python)
- **Data Storage**: JSON files (local/shared folder)
- **Reports**: Excel (openpyxl/XlsxWriter), XML (lxml)

## Project Structure

```
icare-accounting/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── build_exe.spec          # PyInstaller configuration
├── data/                   # Data storage
│   ├── master_data.json    # Account heads, narrations, segments
│   └── vouchers.json       # Saved vouchers
├── models/                 # Data models
│   ├── voucher.py
│   ├── account_head.py
│   ├── narration.py
│   ├── segment.py
│   ├── master_data.py
│   └── import_result.py
├── services/               # Business logic
│   ├── data_service.py
│   ├── import_service.py
│   ├── allocation_service.py
│   ├── tally_service.py
│   └── mis_service.py
├── ui/                     # PySide6 UI components
│   ├── styles.py
│   ├── main_window.py
│   ├── voucher_entry.py
│   ├── bulk_import.py
│   ├── review_validation.py
│   ├── reports.py
│   └── admin_settings.py
└── resources/              # Application resources
    └── (logo, icons)
```

## Installation

### Development Setup

```bash
# Create virtual environment
python -m venv venv
venv\\Scripts\\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

### Building Executable

```bash
# Install PyInstaller
pip install pyinstaller

# Build .exe
pyinstaller build_exe.spec

# Output will be in dist/iCareAccounting/
```

## Chart of Accounts (COA) Structure

The system uses a 4-digit coding system:

| Range | Type | Category |
|-------|------|----------|
| 1000-1999 | Credit | Operating Sales |
| 2000-2999 | Credit | Other Income |
| 3000-3999 | Credit | Loans/Liabilities |
| 4000-4999 | Credit | Asset Sales |
| 5000-5999 | Debit | Direct Costs |
| 6000-6999 | Debit | Fixed Overheads |
| 7000-7999 | Debit | Marketing/Sales |
| 8000-8999 | Debit | Finance/Assets |

## Segments

- **Retail**: Direct Wix sales
- **Kenya**: Kenya franchise operations
- **India**: India franchise operations
- **Corporate**: B2B training sales
- **POOL**: Shared costs (allocated pro-rata based on sales)

## Business Logic Implementation Status

### Implemented ✅
- Data persistence (JSON)
- Voucher CRUD operations
- CSV import parsing
- Basic validation
- Tally XML structure generation
- MIS Excel export structure

### Stub Methods (Marked for Manual Implementation) 🔧
- `AllocatePoolCosts()` - Full POOL cost distribution logic
- `GenerateTallyXml()` - Final Tally XML schema per requirements
- `CalculateMIS()` - Complete segmental profitability calculations
- Account head add/edit/delete dialogs
- Transfer JV generation for account renames

## UI Features

- **Scroll support** on all tabs for smaller screens
- **Clear labels** with high-contrast styling
- **Visible dropdown arrows** with teal accent color
- **iCare brand colors**: Teal (#00A4A6) primary, Deep Blue (#1E3A5F) secondary
- **Responsive layout** that adapts to window size

## Notes

- Users cannot type in Account Head or Narration fields (dropdown only)
- Edit windows are limited to quarter-end periods (configurable)
- All data is stored locally in JSON format
- The application is offline-first (no internet required)

## License

Proprietary - iCare Life
