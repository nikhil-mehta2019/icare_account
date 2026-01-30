# iCare Life Accounting System - PRD

## Original Problem Statement
Build an offline-first desktop accounting application using Python 3.11 and PySide6. The application is a pre-accounting system designed to prepare validated data for Tally import and MIS reporting. The final output should be a PyInstaller-ready project that can be packaged into a standalone .exe file.

## User Personas
- **Accountants**: Need to import bulk vouchers from CSV/Excel and validate them before Tally export
- **Admins**: Manage master data, configure import templates, and set up ledger mappings

## Core Requirements

### 1. Application Layout
- Desktop app with tabs: "Voucher Entry", "Bulk Import (CSV)", "Reports", "Admin / Settings", "Review & Export"
- Password-protected Admin/Settings tab (Password: `Subudhi123`)

### 2. Voucher Entry (4-Step Guided Flow)
- **Step 1:** Method & Head - Select Tally Accounting Head, set Voucher Date and Period (From/To)
- **Step 2:** Settings & Tax - Country, Product, Franchise (if required), Point of Supply, GST config
- **Step 3:** Financial Details - Amount entry with auto-calculated tax breakup
- **Step 4:** Confirm & Print - Preview ledger entries and save
- All dropdowns populated from Master Data config (voucher_config.json)

### 3. Bulk Import (Primary Feature)
- **Voucher Type Selector** (Credit/Debit) - MANDATORY first step
- **Tally Accounting Head** & **Point of Supply** selectors - aligns with manual entry workflow
- **Import Type** dynamically populated based on Voucher Type:
  - **Debit Types:** Purchase, Payroll, Journal
  - **Credit Types:** Wix Sales Export, Generic Credit CSV
- **Purchase Vouchers:** Full GST (CGST/SGST/IGST), TDS (194C/I/J), RCM support
- **Payroll Vouchers:** Simple salary payments with optional TDS
- **Journal Vouchers:** Multi-entry adjustments (must balance)

### 4. Review & Validation
- Display totals for debits and credits
- Highlight any difference
- List all vouchers

### 5. Reports
- MIS Excel generation (placeholder)
- Tally XML export (implemented)

### 6. Admin / Settings (Master Data Management)
- **Tally Accounting Heads**: CRUD operations, Credit/Debit type, franchise requirement flag
- **Countries**: CRUD, used for International vs Domestic classification
- **Products**: CRUD, used for voucher code generation and segment tagging
- **Franchises**: CRUD, required for certain Tally Heads
- **Point of Supply (States)**: CRUD, Home State flag for GST type determination
- **GST/TDS Configuration**: View rates and ledger names
- Password protection with edit windows (quarter-end periods)

### 7. GST Logic (POS-Driven)
- `isHomeState` flag on Point of Supply determines GST type automatically:
  - **Home State (Maharashtra)**: CGST + SGST (Intra-State)
  - **Other States**: IGST (Inter-State)
- Applied consistently across Voucher Entry and Bulk Import

## Architecture
```
/app/
├── main.py              # Entry point
├── requirements.txt     # Dependencies
├── build_exe.spec       # PyInstaller config
├── data/                # JSON data storage
│   ├── master_data.json
│   ├── vouchers.json
│   └── voucher_config.json  # Master config for all dropdowns
├── models/              # Data models
│   ├── debit_voucher.py # GST/TDS/RCM models
│   ├── ledger_config.py
│   └── ...
├── services/            # Business logic
│   ├── voucher_config_service.py  # Config management with CRUD
│   ├── debit_voucher_service.py
│   └── ...
└── ui/                  # PySide6 UI
    ├── main_window.py
    ├── voucher_entry.py  # 4-step guided flow
    ├── bulk_import.py    # With Tally Head & POS selectors
    ├── admin_settings.py # Master data management tabs
    ├── styles.py
    └── ...
```

## Tech Stack
- **Language:** Python 3.11
- **UI Framework:** PySide6 (Qt)
- **Data Storage:** Local JSON files
- **Data Processing:** Pandas
- **Packaging:** PyInstaller

---

## Implementation Status

### Completed (as of Dec 2025)
- [x] Project architecture (PySide6 desktop app)
- [x] All UI screens scaffolded
- [x] Data models (Voucher, DebitVoucher, GST/TDS configs)
- [x] Services layer with stubs
- [x] **4-Step Guided Voucher Entry** with JSON-driven config
- [x] **Voucher Entry Navigation Fix** - dropdowns now properly load from config
- [x] Voucher Type selector UI in Bulk Import (Credit/Debit)
- [x] **Tally Head & POS selectors in Bulk Import** - aligned with manual entry
- [x] Dynamic Import Type dropdown
- [x] Purchase voucher CSV import with GST/TDS/RCM
- [x] Payroll voucher CSV import
- [x] Journal voucher CSV import
- [x] GST calculation logic (Intra/Inter-state, RCM)
- [x] TDS calculation logic
- [x] Dropdown visibility fix (enhanced QComboBox styling)
- [x] **Period Dates (From/To)** in Voucher Entry and Bulk Import
- [x] **Date validation** - From <= To <= Voucher Date
- [x] **Compact UI styling** - reduced field heights, tighter spacing
- [x] **Purchase Voucher Validator** - Full validation for GST/TDS/RCM
- [x] **Tally XML Export Service** - Complete implementation for all voucher types
- [x] **Master Data Management UI** - Full CRUD for all master types
- [x] **Config Service Enhancement** - Support for both legacy and new JSON formats
- [x] **POS-Driven GST Logic** - Auto-determined based on isHomeState flag

### NEW - Completed (Latest Session - Logic Separation Update)

**PART 1: VoucherEntryTab.py (Manual Entry)**
- [x] **Dynamic UI Logic (_on_type_changed)**:
  - CREDIT: Amount label = "Amount (₹)", HIDE TDS/Expense Details, Vendor section
  - DEBIT: Amount label = "Base Amount (excl. GST)", SHOW TDS/Expense/Vendor fields
  - Country validation based on Domestic (default India) / International (remove India)

- [x] **TDS Category Dropdown (DEBIT ONLY)**: 
  - TDS Payable on Contract – FY 2025-26
  - TDS Payable on Professional Services – FY 2025-26
  - TDS Payable on Rent – FY 2025-26
  - TDS Payable – FY 2025-26
  - TDS Payable u/s 195 – FY 2025-26

- [x] **Expense Details Field (DEBIT ONLY)**: Free-text for auto-narration

- [x] **Auto-Narration (DEBIT ONLY)**: Format: `{Expense Details} for the period {Start} to {End} purchased from {Vendor} for product {Product} under Business Segment {Segment}, {Country}`

- [x] **RCM Logic (Foreign Country - DEBIT ONLY)**:
  - Triggers when POS = "Foreign Country"
  - Journal Entry with WHT: Dr Expense, Cr Output SGST, Cr Output CGST, Cr TDS, Cr Party (Net)
  - Journal Entry without WHT: Dr Expense, Cr Output SGST, Cr Output CGST, Cr Party (Base)
  - RCM Preview panel shows exact accounting entries

- [x] **Calculation Logic Separation**:
  - CREDIT: Amount = Total (inclusive), Extract: Base = Total / (1 + GST%)
  - DEBIT: Amount = Base (exclusive), Calculate: Gross = Base + GST

**PART 2: BulkImportTab.py (CSV Import)**
- [x] **Global Tally Head Selection (Step 2.5)**: Applied to all rows in file
- [x] **CSV Schema Hints**: Shows expected columns based on Credit/Debit type
- [x] **Credit Schema**: Date, Invoice No, Customer Name, Place of Supply, Business Segment, Amount (Total)
- [x] **Debit Schema**: Date, Vendor Name, Place of Supply, Business Segment, Expense Details, TDS Category, Base Amount
- [x] **Preview Grid with Validation (Step 5)**:
  - Columns: Date, Party, Segment, State, Amount, Tax, Total, Status
  - Green highlight: Valid rows
  - Red highlight: Invalid Business Segment or missing Place of Supply
  - Validation checks for VALID_SEGMENTS = {Retail, Franchise, Placement, Homecare}

### In Progress
- None

### Pending (P0 - High Priority)
- [ ] End-to-end testing with actual CSV files
- [ ] Save/Load complete master config state

### Pending (P1 - Medium Priority)
- [ ] MIS Excel export implementation
- [ ] Main Code/Subcode integration in exports
- [ ] Supplier/Party ledger management

### Backlog (P2 - Future)
- [ ] Full accounting logic (AllocatePoolCosts, CalculateMIS)
- [ ] Final Tally XML schema (needs user validation)
- [ ] PyInstaller packaging and .exe generation

---

## Known Issues
1. **Cannot visually test GUI** - Environment is headless, only logic/syntax testing possible
2. **Core business logic stubbed** - Intentionally left as stubs per user request

## Admin Credentials
- **Password:** `Subudhi123`

## Reference Documents
- `Accounting System.docx` - System specification
- `Tally_Import_Only_Purchase_GST_TDS_RCM_With_Validations.xlsx` - Purchase import rules

## Key Data Schemas

### voucher_config.json Structure
```json
{
  "version": "2.0",
  "homeState": "Maharashtra",
  "tallyHeads": [
    {"value": "1A1", "label": "Direct Income", "type": "CREDIT", "needsFranchise": true, "isActive": true}
  ],
  "countries": [{"value": "356", "label": "India", "isActive": true}],
  "products": [{"value": "101", "label": "Eldercare", "isActive": true}],
  "franchises": [{"value": "01", "label": "Franchisee A", "isActive": true}],
  "pointOfSupply": [{"value": "MH", "label": "Maharashtra", "isHomeState": true, "isActive": true}],
  "gstRates": [0, 5, 12, 18, 28],
  "tdsRates": {"194C": {"name": "Contractors", "rate": 2.0}}
}
```
