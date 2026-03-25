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

# Singleton instance
_config_service = None
def get_voucher_config() -> VoucherConfigService:
    global _config_service
    if _config_service is None:
        _config_service = VoucherConfigService()
    return _config_service