from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from services.data_provider import DataProvider

@dataclass
class TallyHead:
    """Tally accounting head configuration."""
    code: str
    name: str
    type: str = ""
    requires_franchise: bool = False
    gst_applicable: bool = True
    tds_section: str = ""
    is_domestic: Optional[bool] = None  
    is_b2b: Optional[bool] = None       

@dataclass
class DropdownOption:
    """Generic dropdown option."""
    code: str
    name: str
    is_default: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)

@dataclass 
class StateOption:
    """Point of Supply state option."""
    code: str
    name: str
    is_home_state: bool = False
    is_foreign: bool = False

@dataclass
class TDSLedger:
    """TDS Ledger option for Tally mapping."""
    code: str
    label: str
    section: str

class VoucherConfigService:
    """Stateless service for fetching UI configurations directly from PostgreSQL."""
    
    def __init__(self):
        self.db = DataProvider.get_service()

    def get_tally_heads(self, voucher_type: str) -> List[TallyHead]:
        """Query DB for all tally heads by type."""
        query = """
            SELECT code, name, type, tds_section, is_domestic, needs_franchise as requires_franchise 
            FROM config_tally_heads 
            WHERE type ILIKE %s
        """
        rows = self.db.execute_read(query, (voucher_type,))
        return [TallyHead(**row) for row in rows]

    def get_gst_rates(self) -> List[float]:
        """Fetch all active GST rates."""
        query = "SELECT rate FROM config_gst_rates ORDER BY rate ASC"
        rows = self.db.execute_read(query)
        # Ensure conversion to float for every row
        rates = [float(r['rate']) for r in rows]
        if 0.0 not in rates: rates.insert(0, 0.0)
        return rates

    def get_products(self) -> List[DropdownOption]:
        """Fetch products for UI dropdowns."""
        rows = self.db.execute_read("SELECT code, name FROM config_products")
        return [DropdownOption(code=r['code'], name=r['name']) for r in rows]

    def get_franchises(self) -> List[DropdownOption]:
        """Fetch franchises for UI dropdowns."""
        rows = self.db.execute_read("SELECT code, name FROM config_franchises")
        return [DropdownOption(code=r['code'], name=r['name']) for r in rows]

    def get_tds_ledgers(self) -> List[TDSLedger]:
        """Fetch TDS ledgers for Tally mapping."""
        rows = self.db.execute_read("SELECT code, name, section FROM config_tds_ledgers")
        return [TDSLedger(code=r['code'], label=r['name'], section=r['section']) for r in rows]

    def get_gst_applicable_options(self) -> List[DropdownOption]:
        """Standard GST application status options."""
        return [
            DropdownOption(code="Y", name="Yes - GST Applicable"),
            DropdownOption(code="N", name="No - Exempt/Non-GST"),
            DropdownOption(code="LUT", name="Zero rated under LUT")
        ]

    def get_tds_applicable_options(self) -> List[DropdownOption]:
        """Standard TDS application status options."""
        return [
            DropdownOption(code="Y", name="Yes - TDS Applicable"),
            DropdownOption(code="N", name="No - Not Applicable")
        ]

    # ==========================================
    # RESTORED UI HELPER METHODS
    # ==========================================

    def get_validation_rules(self) -> Dict[str, Any]:
        """Return UI validation rules (fallback to defaults if not in DB)."""
        return {
            "maxBackdateDays": 7,
            "periodSuggestDays": 60
        }

    def get_tally_head_by_code(self, head_code: str, voucher_type: str) -> Optional[TallyHead]:
        """Find a specific tally head by code."""
        heads = self.get_tally_heads(voucher_type)
        for h in heads:
            if h.code == head_code:
                return h
        return None

    def get_countries(self, exclude_india: bool = False) -> List[DropdownOption]:
        """Return list of countries."""
        countries = [
            DropdownOption(code="356", name="India", is_default=True),
            DropdownOption(code="840", name="United States"),
            DropdownOption(code="826", name="United Kingdom"),
            DropdownOption(code="784", name="United Arab Emirates"),
            DropdownOption(code="702", name="Singapore")
        ]
        if exclude_india:
            return [c for c in countries if c.code != "356"]
        return countries

    def get_default_gst_rate(self) -> float:
        return 18.0

    def determine_gst_type(self, state_code: str) -> str:
        """Determine if a state is home state (CGST/SGST) or Inter-state (IGST)."""
        query = "SELECT is_home_state FROM config_point_of_supply WHERE code = %s"
        row = self.db.execute_read_one(query, (state_code,))
        return "CGST_SGST" if (row and row.get('is_home_state')) else "IGST"

    def is_pos_foreign(self, state_code: str) -> bool:
        """Check if POS is a foreign country."""
        query = "SELECT is_foreign FROM config_point_of_supply WHERE code = %s"
        row = self.db.execute_read_one(query, (state_code,))
        return row.get('is_foreign', False) if row else False

    def get_tds_rate_for_section(self, section: str) -> float:
        """Fetch the default TDS rate for a given section."""
        # Wrap in try/except just in case the 'rate' column isn't in your tds_ledgers table yet
        try:
            query = "SELECT rate FROM config_tds_ledgers WHERE section = %s LIMIT 1"
            row = self.db.execute_read_one(query, (section,))
            return float(row['rate']) if row and row.get('rate') else 0.0
        except Exception:
            rates = {"194J": 10.0, "194C": 1.0, "194I": 10.0}
            return rates.get(section, 0.0)

    def generate_voucher_code(self, voucher_type: str, product_code: str) -> str:
        """Route sequence generation directly to the PostgreSQL Database Service."""
        return self.db.generate_next_voucher_sequence(voucher_type, product_code)

    def get_tds_rates(self) -> dict:
        """Fetch TDS sections and rates from DB or fallback."""
        return {
            "194J": {"name": "Fees for Professional/Tech Services", "rate": 10.0},
            "194C": {"name": "Payment to Contractors", "rate": 1.0},
            "194I": {"name": "Rent", "rate": 10.0},
            "194H": {"name": "Commission or Brokerage", "rate": 5.0}
        }

    def get_gst_ledgers(self) -> dict:
        """Fetch standard GST ledger mapping."""
        return {
            "inputCgst": "Input CGST A/c",
            "inputSgst": "Input SGST A/c",
            "inputIgst": "Input IGST A/c",
            "outputCgst": "Output CGST A/c",
            "outputSgst": "Output SGST A/c",
            "outputIgst": "Output IGST A/c"
        }

    # ==========================================
    # ADMIN / MASTER DATA 'RAW' METHODS
    # ==========================================

    @property
    def home_state(self) -> str:
        """Fetch the current home state code for the Admin POS UI."""
        query = "SELECT code FROM config_point_of_supply WHERE is_home_state = true LIMIT 1"
        row = self.db.execute_read_one(query)
        return row['code'] if row else ""

    def get_all_tally_heads_raw(self) -> list:
       # Changed 'requires_franchise' to 'needs_franchise' to match the DB exactly
        query = "SELECT code, name, type, needs_franchise, is_active FROM config_tally_heads"
        rows = self.db.execute_read(query)
        return [{
            "value": r['code'], 
            "label": r['name'], 
            "type": r['type'], 
            "needsFranchise": r['needs_franchise'], # Mapped to the correct DB column
            "isActive": r['is_active']
        } for r in rows]

    def get_all_countries_raw(self) -> list:
        query = "SELECT code, name, is_active FROM config_countries"
        rows = self.db.execute_read(query)
        return [{"value": r['code'], "label": r['name'], "isActive": r['is_active']} for r in rows]

    def get_all_products_raw(self) -> list:
        query = "SELECT code, name, is_active FROM config_products"
        rows = self.db.execute_read(query)
        return [{"value": r['code'], "label": r['name'], "isActive": r['is_active']} for r in rows]

    def get_all_franchises_raw(self) -> list:
        query = "SELECT code, name, is_active FROM config_franchises"
        rows = self.db.execute_read(query)
        return [{"value": r['code'], "label": r['name'], "isActive": r['is_active']} for r in rows]

    def get_all_pos_raw(self) -> list:
        query = "SELECT code, name, is_home_state, is_active FROM config_point_of_supply"
        rows = self.db.execute_read(query)
        return [{
            "value": r['code'], 
            "label": r['name'], 
            "isHomeState": r['is_home_state'], 
            "isActive": r['is_active']
        } for r in rows]

    def get_all_vendors_raw(self) -> list:
        query = "SELECT name, gstin, contact_person, is_active FROM master_vendors"
        rows = self.db.execute_read(query)
        return [{
            "name": r['name'], 
            "gstin": r.get('gstin', ''), 
            "contact_person": r.get('contact_person', ''), 
            "isActive": r['is_active']
        } for r in rows]

    def add_vendor(self, data: dict) -> bool:
        """Add a new vendor to config_vendors."""
        query = """
            INSERT INTO config_vendors (name, gstin, contact_person, is_active)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (name) DO NOTHING
        """
        try:
            with self.db._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (
                        data.get('name'), 
                        data.get('gstin', ''), 
                        data.get('contact_person', ''),
                        data.get('isActive', True)
                    ))
                    conn.commit()
                    return cur.rowcount > 0
        except Exception:
            return False

    def update_vendor(self, old_name: str, data: dict) -> bool:
        """Update an existing vendor in master_vendors."""
        query = """
            UPDATE master_vendors 
            SET name = %s, gstin = %s, contact_person = %s, is_active = %s
            WHERE name = %s
        """
        try:
            with self.db._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (
                        data.get('name'), 
                        data.get('gstin', ''), 
                        data.get('contact_person', ''),
                        data.get('isActive', True),
                        old_name
                    ))
                    conn.commit()
                    return cur.rowcount > 0
        except Exception:
            return False

    def delete_vendor(self, name: str) -> bool:
        """Soft-delete (disable) a vendor in master_vendors."""
        query = "UPDATE master_vendors SET is_active = false WHERE name = %s"
        try:
            with self.db._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (name,))
                    conn.commit()
                    return cur.rowcount > 0
        except Exception:
            return False

    def add_tally_head(self, data: dict) -> bool:
        """Add a new tally head to config_tally_heads."""
        query = """
            INSERT INTO config_tally_heads (code, name, type, needs_franchise, is_active)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (code) DO NOTHING
        """
        try:
            with self.db._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (
                        data.get('value'), 
                        data.get('label'), 
                        data.get('type'),
                        data.get('needsFranchise', False),
                        data.get('isActive', True)
                    ))
                    conn.commit()
                    return cur.rowcount > 0
        except Exception:
            return False

    def update_tally_head(self, old_code: str, data: dict) -> bool:
        """Update an existing tally head in config_tally_heads."""
        query = """
            UPDATE config_tally_heads 
            SET code = %s, name = %s, type = %s, needs_franchise = %s, is_active = %s
            WHERE code = %s
        """
        try:
            with self.db._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (
                        data.get('value'), 
                        data.get('label'), 
                        data.get('type'),
                        data.get('needsFranchise', False),
                        data.get('isActive', True),
                        old_code
                    ))
                    conn.commit()
                    return cur.rowcount > 0
        except Exception:
            return False

    def delete_tally_head(self, code: str) -> bool:
        """Soft-delete (disable) a tally head in config_tally_heads."""
        query = "UPDATE config_tally_heads SET is_active = false WHERE code = %s"
        try:
            with self.db._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (code,))
                    conn.commit()
                    return cur.rowcount > 0
        except Exception:
            return False

    # ============ COUNTRY CRUD ============
    def add_country(self, data: dict) -> bool:
        query = "INSERT INTO config_countries (code, name, is_active) VALUES (%s, %s, %s) ON CONFLICT (code) DO NOTHING"
        return self._execute_write(query, (data.get('value'), data.get('label'), data.get('isActive', True)))

    def update_country(self, old_code: str, data: dict) -> bool:
        query = "UPDATE config_countries SET code = %s, name = %s, is_active = %s WHERE code = %s"
        return self._execute_write(query, (data.get('value'), data.get('label'), data.get('isActive', True), old_code))

    def delete_country(self, code: str) -> bool:
        query = "UPDATE config_countries SET is_active = false WHERE code = %s"
        return self._execute_write(query, (code,))

    # ============ PRODUCT CRUD ============
    def add_product(self, data: dict) -> bool:
        query = "INSERT INTO config_products (code, name, is_active) VALUES (%s, %s, %s) ON CONFLICT (code) DO NOTHING"
        return self._execute_write(query, (data.get('value'), data.get('label'), data.get('isActive', True)))

    def update_product(self, old_code: str, data: dict) -> bool:
        query = "UPDATE config_products SET code = %s, name = %s, is_active = %s WHERE code = %s"
        return self._execute_write(query, (data.get('value'), data.get('label'), data.get('isActive', True), old_code))

    def delete_product(self, code: str) -> bool:
        query = "UPDATE config_products SET is_active = false WHERE code = %s"
        return self._execute_write(query, (code,))

    # ============ FRANCHISE CRUD ============
    def add_franchise(self, data: dict) -> bool:
        query = "INSERT INTO config_franchises (code, name, is_active) VALUES (%s, %s, %s) ON CONFLICT (code) DO NOTHING"
        return self._execute_write(query, (data.get('value'), data.get('label'), data.get('isActive', True)))

    def update_franchise(self, old_code: str, data: dict) -> bool:
        query = "UPDATE config_franchises SET code = %s, name = %s, is_active = %s WHERE code = %s"
        return self._execute_write(query, (data.get('value'), data.get('label'), data.get('isActive', True), old_code))

    def delete_franchise(self, code: str) -> bool:
        query = "UPDATE config_franchises SET is_active = false WHERE code = %s"
        return self._execute_write(query, (code,))

    # ============ POINT OF SUPPLY (POS) CRUD ============
    def add_pos(self, data: dict) -> bool:
        query = "INSERT INTO config_point_of_supply (code, name, is_home_state, is_active) VALUES (%s, %s, %s, %s) ON CONFLICT (code) DO NOTHING"
        return self._execute_write(query, (data.get('value'), data.get('label'), data.get('isHomeState', False), data.get('isActive', True)))

    def update_pos(self, old_code: str, data: dict) -> bool:
        query = "UPDATE config_point_of_supply SET code = %s, name = %s, is_home_state = %s, is_active = %s WHERE code = %s"
        return self._execute_write(query, (data.get('value'), data.get('label'), data.get('isHomeState', False), data.get('isActive', True), old_code))

    def set_home_state_code(self, code: str) -> bool:
        """Sets a specific state as the Home State and resets others."""
        try:
            with self.db._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE config_point_of_supply SET is_home_state = false")
                    cur.execute("UPDATE config_point_of_supply SET is_home_state = true WHERE code = %s", (code,))
                    conn.commit()
                    return True
        except Exception:
            return False

    # ============ INTERNAL HELPER ============
    def _execute_write(self, query: str, params: tuple) -> bool:
        """Helper to execute SQL write operations."""
        try:
            with self.db._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                    conn.commit()
                    return cur.rowcount > 0
        except Exception as e:
            print(f"Database Write Error: {e}")
            return False

# Singleton instance
_config_service = None
def get_voucher_config() -> VoucherConfigService:
    global _config_service
    if _config_service is None:
        _config_service = VoucherConfigService()
    return _config_service

