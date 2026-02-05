"""Voucher Configuration Service - JSON-driven configuration for voucher entry."""

import json
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from models.master_data import MasterData
from services.data_service import DataService

@dataclass
class TallyHead:
    """Tally accounting head configuration."""
    code: str
    name: str
    requires_franchise: bool = False
    gst_applicable: bool = True
    tds_section: str = ""
    is_domestic: Optional[bool] = None  # None means no restriction, True = domestic only, False = international only


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


@dataclass
class PartyOption:
    """Party/Vendor option."""
    code: str
    name: str
    gstin: str = ""
    state: str = ""
    default_tds: str = ""


class VoucherConfigService:
    """
    Service to load and manage voucher configuration from JSON.
    All dropdown values and conditional logic are driven from config.
    """
    
    CONFIG_PATH = "data/voucher_config.json"
    
    def __init__(self):
        """Initialize the configuration service."""
        self._config: Dict = {}
        self._loaded = False
        self.master_data = None
        self.data_service = DataService()
        self.load_config()
    
    def load_config(self) -> bool:
        """Load configuration from JSON file."""
        try:
            # Try multiple paths
            paths_to_try = [
                self.CONFIG_PATH,
                os.path.join(os.path.dirname(__file__), '..', self.CONFIG_PATH),
                os.path.join(os.path.dirname(__file__), '..', 'data', 'voucher_config.json'),
            ]
            
            for path in paths_to_try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        self._config = json.load(f)
                    self.master_data = MasterData.from_dict(self._config)
                    self._loaded = True
                    return True
            
                # Create default config if not found
                self._config = self._get_default_config()
                self.master_data = MasterData.from_dict(self._config)
                self.data_service._master_data = self.master_data
                self._loaded = True
                return True
            
            # Create default config if not found
            self._config = self._get_default_config()
            self.master_data = MasterData.from_dict(self._config)
            self.data_service._master_data = self.master_data
            self._loaded = True
            return True
            
        except Exception as e:
            print(f"Error loading voucher config: {e}")
            self._config = self._get_default_config()
            self.master_data = MasterData()
            self._loaded = True
            return False
    
    def _get_default_config(self) -> Dict:
        """Return minimal default configuration."""
        return {
            "homeState": "Maharashtra",
            "tallyHeads": {"credit": [], "debit": []},
            "countrySelect": [{"code": "IN", "name": "India", "isDefault": True}],
            "productSelect": [{"code": "MISC", "name": "Miscellaneous", "prefix": "MSC"}],
            "franchiseSelect": [],
            "posSelect": [{"code": "MH", "name": "Maharashtra", "isHomeState": True}],
            
            # === 4. ADD NEW VENDORS LIST HERE ===
            "vendors": [], 
            # ====================================
            
            "gstApp": [
                {"code": "Y", "name": "Yes", "value": True},
                {"code": "N", "name": "No", "value": False}
            ],
            "gstRates": [5.0, 12.0, 18.0, 28.0],
            "defaultGstRate": 18.0,
            "tdsApp": [
                {"code": "Y", "name": "Yes", "value": True},
                {"code": "N", "name": "No", "value": False}
            ],
            "tdsRates": {},
            "partySelect": {"credit": [], "debit": []},
            "validation": {
                "maxBackdateDays": 7,
                "periodSuggestDays": 60,
                "minAmount": 1.0,
                "maxAmount": 99999999.99
            }
        }
    
    @property
    def home_state(self) -> str:
        """Get home state for GST calculation."""
        return self._config.get("homeState", "Maharashtra")
    
    def get_tally_heads(self, voucher_type: str) -> List[TallyHead]:
        """Get tally heads for voucher type (credit/debit)."""
        all_heads = self._config.get("tallyHeads", [])
        
        # Handle both flat array with type field and nested dict formats
        if isinstance(all_heads, list):
            # New format: flat array with "type" field
            heads_data = [
                h for h in all_heads 
                if h.get("type", "").upper() == voucher_type.upper() and h.get("isActive", True)
            ]
            return [
                TallyHead(
                    code=h.get("value", h.get("code", "")),
                    name=h.get("label", h.get("name", "")),
                    requires_franchise=h.get("needsFranchise", h.get("requiresFranchise", False)),
                    gst_applicable=h.get("gstApplicable", True),
                    tds_section=h.get("tdsSection", ""),
                    is_domestic=h.get("isDomestic", None)
                )
                for h in heads_data
            ]
        else:
            # Legacy format: nested dict {credit: [], debit: []}
            heads_data = all_heads.get(voucher_type.lower(), [])
            return [
                TallyHead(
                    code=h.get("code", ""),
                    name=h.get("name", ""),
                    requires_franchise=h.get("requiresFranchise", False),
                    gst_applicable=h.get("gstApplicable", True),
                    tds_section=h.get("tdsSection", ""),
                    is_domestic=h.get("isDomestic", None)
                )
                for h in heads_data
            ]
    
    def get_tally_head_by_code(self, code: str, voucher_type: str) -> Optional[TallyHead]:
        """Get specific tally head by code."""
        heads = self.get_tally_heads(voucher_type)
        for head in heads:
            if head.code == code:
                return head
        return None
    
    def get_tally_head_raw(self, code: str, voucher_type: str) -> Optional[Dict]:
        """Get raw tally head dict by code."""
        all_heads = self._config.get("tallyHeads", [])
        for h in all_heads:
            if h.get("value") == code and h.get("type", "").upper() == voucher_type.upper():
                return h
        return None
    
    def get_countries(self, exclude_india: bool = False) -> List[DropdownOption]:
        """Get country list.
        
        Args:
            exclude_india: If True, exclude India from the list (for International heads).
        """
        # Support both 'countries' and 'countrySelect' keys
        data = self._config.get("countries", self._config.get("countrySelect", []))
        result = []
        for c in data:
            if not c.get("isActive", True):
                continue
            if exclude_india and c.get("value") == "356":
                continue  # Skip India
            result.append(DropdownOption(
                code=c.get("value", c.get("code", "")),
                name=c.get("label", c.get("name", "")),
                is_default=c.get("isDefault", False),
                extra={"isForeign": c.get("isForeign", False)}
            ))
        return result
    
    def get_products(self) -> List[DropdownOption]:
        """Get product list."""
        # Support both 'products' and 'productSelect' keys
        data = self._config.get("products", self._config.get("productSelect", []))
        return [
            DropdownOption(
                code=p.get("value", p.get("code", "")),
                name=p.get("label", p.get("name", "")),
                extra={"prefix": p.get("prefix", p.get("value", "")[:3])}
            )
            for p in data if p.get("isActive", True)
        ]
    
    def get_franchises(self) -> List[DropdownOption]:
        """Get franchise list."""
        # Support both 'franchises' and 'franchiseSelect' keys
        data = self._config.get("franchises", self._config.get("franchiseSelect", []))
        return [
            DropdownOption(
                code=f.get("value", f.get("code", "")),
                name=f.get("label", f.get("name", "")),
                extra={"state": f.get("state", "")}
            )
            for f in data if f.get("isActive", True)
        ]
    
    def get_pos_states(self) -> List[StateOption]:
        """Get Point of Supply states."""
        # Support both 'pointOfSupply' and 'posSelect' keys
        data = self._config.get("pointOfSupply", self._config.get("posSelect", []))
        return [
            StateOption(
                code=s.get("value", s.get("code", "")),
                name=s.get("label", s.get("name", "")),
                is_home_state=s.get("isHomeState", False),
                is_foreign=s.get("isForeign", False)
            )
            for s in data if s.get("isActive", True)
        ]
    
    def get_business_segments(self) -> List[DropdownOption]:
        """Get business segments list."""
        data = self._config.get("businessSegments", [])
        if not data:
            # Default segments
            data = [
                {"value": "RETAIL", "label": "Retail"},
                {"value": "FRANCHISE", "label": "Franchise"},
                {"value": "PLACEMENT", "label": "Placement"},
                {"value": "HOMECARE", "label": "Homecare"}
            ]
        return [
            DropdownOption(
                code=s.get("value", ""),
                name=s.get("label", "")
            )
            for s in data if s.get("isActive", True)
        ]
    
    def get_tds_ledgers(self) -> List[TDSLedger]:
        """Get TDS ledger options for Tally mapping."""
        data = self._config.get("tdsLedgers", [])
        if not data:
            # Default TDS ledgers
            data = [
                {"value": "TDS_194C", "label": "TDS Payable on Contract – FY 2025-26", "section": "194C"},
                {"value": "TDS_194J", "label": "TDS Payable on Professional Services – FY 2025-26", "section": "194J"},
                {"value": "TDS_194I", "label": "TDS Payable on Rent – FY 2025-26", "section": "194I"},
                {"value": "TDS_194H", "label": "TDS Payable – FY 2025-26", "section": "194H"},
                {"value": "TDS_195", "label": "TDS Payable u/s 195 – FY 2025-26", "section": "195"}
            ]
        return [
            TDSLedger(
                code=t.get("value", ""),
                label=t.get("label", ""),
                section=t.get("section", "")
            )
            for t in data if t.get("isActive", True)
        ]
    
    def is_pos_foreign(self, pos_code: str) -> bool:
        """Check if Point of Supply is Foreign Country."""
        data = self._config.get("pointOfSupply", [])
        for s in data:
            if s.get("value") == pos_code:
                return s.get("isForeign", False)
        return False
    
    def get_gst_applicable_options(self) -> List[DropdownOption]:
        """Get GST applicable options."""
        data = self._config.get("gstApp", [])
        if not data:
            # Default options
            data = [
                {"code": "Y", "name": "Yes - GST Applicable", "value": True},
                {"code": "N", "name": "No - Exempt/Non-GST", "value": False}
            ]
        return [
            DropdownOption(
                code=g.get("code", ""),
                name=g.get("name", ""),
                extra={"value": g.get("value", False)}
            )
            for g in data
        ]
    
    def get_tds_applicable_options(self) -> List[DropdownOption]:
        """Get TDS applicable options."""
        data = self._config.get("tdsApp", [])
        if not data:
            # Default options
            data = [
                {"code": "Y", "name": "Yes - TDS Applicable", "value": True},
                {"code": "N", "name": "No - Not Applicable", "value": False}
            ]
        return [
            DropdownOption(
                code=t.get("code", ""),
                name=t.get("name", ""),
                extra={"value": t.get("value", False)}
            )
            for t in data
        ]
    
    def get_gst_rates(self) -> List[float]:
        """Get available GST rates."""
        return self._config.get("gstRates", [5.0, 12.0, 18.0, 28.0])
    
    def get_default_gst_rate(self) -> float:
        """Get default GST rate."""
        return self._config.get("defaultGstRate", 18.0)
    
    def get_tds_rates(self) -> Dict[str, Dict]:
        """Get TDS rates by section."""
        return self._config.get("tdsRates", {})
    
    def get_tds_rate_for_section(self, section: str) -> float:
        """Get TDS rate for specific section."""
        rates = self.get_tds_rates()
        # Handle both "194C" and "194C" style keys
        clean_section = section.replace(" ", "").upper()
        for key, val in rates.items():
            if key.replace(" ", "").upper() == clean_section:
                return val.get("rate", 0.0)
        return 0.0
    
    def get_parties(self, voucher_type: str) -> List[PartyOption]:
        """Get party/vendor list for voucher type."""
        data = self._config.get("partySelect", {}).get(voucher_type.lower(), [])
        return [
            PartyOption(
                code=p.get("code", ""),
                name=p.get("name", ""),
                gstin=p.get("gstin", ""),
                state=p.get("state", ""),
                default_tds=p.get("defaultTds", "")
            )
            for p in data
        ]
    
    def get_gst_ledgers(self) -> Dict[str, str]:
        """Get GST ledger names."""
        return self._config.get("gstLedgers", {
            "inputCgst": "Input CGST",
            "inputSgst": "Input SGST",
            "inputIgst": "Input IGST",
            "outputCgst": "Output CGST",
            "outputSgst": "Output SGST",
            "outputIgst": "Output IGST"
        })
    
    def get_validation_rules(self) -> Dict:
        """Get validation rules."""
        return self._config.get("validation", {
            "maxBackdateDays": 7,
            "periodSuggestDays": 60,
            "minAmount": 1.0,
            "maxAmount": 99999999.99
        })
    
    def is_home_state(self, state_code: str) -> bool:
        """Check if state is home state."""
        states = self.get_pos_states()
        for state in states:
            if state.code == state_code:
                return state.is_home_state
        return False
    
    def determine_gst_type(self, pos_state_code: str) -> str:
        """
        Determine GST type based on Point of Supply.
        
        Returns:
            'CGST_SGST' for home state (intra-state)
            'IGST' for other states (inter-state)
        """
        if self.is_home_state(pos_state_code):
            return "CGST_SGST"
        return "IGST"
    
    def generate_voucher_code(self, voucher_type: str, product_code: str, 
                              sequence_num: int = 1) -> str:
        """Generate voucher code based on format."""
        now = datetime.now()
        
        # Get product prefix
        products = self.get_products()
        prefix = "MSC"
        for p in products:
            if p.code == product_code:
                prefix = p.extra.get("prefix", "MSC")
                break
        
        if voucher_type.lower() == "credit":
            return f"CR-{prefix}-{now.year}{now.month:02d}-{sequence_num:04d}"
        else:
            return f"DB-{prefix}-{now.year}{now.month:02d}-{sequence_num:04d}"
    
    # ============ MASTER DATA MANAGEMENT ============
    
    def save_config(self) -> bool:
        """Save current configuration to JSON file."""
       # Save both to local config file AND via DataService
        try:
            self._config["lastModified"] = datetime.now().strftime("%Y-%m-%d")
            # Update master_data object from _config dict
            if self.master_data:
                # Basic sync - for full robustness update individual fields
                self.data_service.save_master_data()
            
            with open(self.CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def get_all_tally_heads_raw(self) -> List[Dict]:
        """Get all tally heads in raw format for admin editing."""
        return self._config.get("tallyHeads", [])
    
    def add_tally_head(self, head_data: Dict) -> bool:
        """Add a new tally accounting head."""
        if "tallyHeads" not in self._config:
            self._config["tallyHeads"] = []
        self._config["tallyHeads"].append(head_data)
        return self.save_config()
    
    def update_tally_head(self, code: str, head_data: Dict) -> bool:
        """Update an existing tally head by code."""
        heads = self._config.get("tallyHeads", [])
        for i, h in enumerate(heads):
            if h.get("value") == code:
                self._config["tallyHeads"][i] = head_data
                return self.save_config()
        return False
    
    def delete_tally_head(self, code: str) -> bool:
        """Delete a tally head (set isActive to False)."""
        heads = self._config.get("tallyHeads", [])
        for h in heads:
            if h.get("value") == code:
                h["isActive"] = False
                return self.save_config()
        return False
    
    def get_all_countries_raw(self) -> List[Dict]:
        """Get all countries in raw format."""
        return self._config.get("countries", [])
    
    def add_country(self, country_data: Dict) -> bool:
        """Add a new country."""
        if "countries" not in self._config:
            self._config["countries"] = []
        self._config["countries"].append(country_data)
        return self.save_config()
    
    def update_country(self, code: str, country_data: Dict) -> bool:
        """Update an existing country."""
        countries = self._config.get("countries", [])
        for i, c in enumerate(countries):
            if c.get("value") == code:
                self._config["countries"][i] = country_data
                return self.save_config()
        return False
    
    def get_all_products_raw(self) -> List[Dict]:
        """Get all products in raw format."""
        return self._config.get("products", [])
    
    def add_product(self, product_data: Dict) -> bool:
        """Add a new product."""
        if "products" not in self._config:
            self._config["products"] = []
        self._config["products"].append(product_data)
        return self.save_config()
    
    def update_product(self, code: str, product_data: Dict) -> bool:
        """Update an existing product."""
        products = self._config.get("products", [])
        for i, p in enumerate(products):
            if p.get("value") == code:
                self._config["products"][i] = product_data
                return self.save_config()
        return False
    
    def get_all_franchises_raw(self) -> List[Dict]:
        """Get all franchises in raw format."""
        return self._config.get("franchises", [])
    
    def add_franchise(self, franchise_data: Dict) -> bool:
        """Add a new franchise."""
        if "franchises" not in self._config:
            self._config["franchises"] = []
        self._config["franchises"].append(franchise_data)
        return self.save_config()
    
    def update_franchise(self, code: str, franchise_data: Dict) -> bool:
        """Update an existing franchise."""
        franchises = self._config.get("franchises", [])
        for i, f in enumerate(franchises):
            if f.get("value") == code:
                self._config["franchises"][i] = franchise_data
                return self.save_config()
        return False
    
    def get_all_pos_raw(self) -> List[Dict]:
        """Get all Point of Supply states in raw format."""
        return self._config.get("pointOfSupply", [])
    
    def add_pos(self, pos_data: Dict) -> bool:
        """Add a new Point of Supply."""
        if "pointOfSupply" not in self._config:
            self._config["pointOfSupply"] = []
        self._config["pointOfSupply"].append(pos_data)
        return self.save_config()
    
    def update_pos(self, code: str, pos_data: Dict) -> bool:
        """Update an existing Point of Supply."""
        pos_list = self._config.get("pointOfSupply", [])
        for i, p in enumerate(pos_list):
            if p.get("value") == code:
                self._config["pointOfSupply"][i] = pos_data
                return self.save_config()
        return False
    
    def set_home_state_code(self, state_code: str) -> bool:
        """Set the home state for GST calculations."""
        self._config["homeState"] = state_code
        # Also update isHomeState flag in pointOfSupply
        pos_list = self._config.get("pointOfSupply", [])
        for p in pos_list:
            p["isHomeState"] = (p.get("value") == state_code)
        return self.save_config()


# ==========================================
    #               VENDOR MANAGMENT
    # ==========================================

    def get_all_vendors(self) -> List[dict]:
        """Get all active vendors."""
        if not self.master_data:
            return []
        # Return sorted by name
        return sorted(
            [v for v in self.master_data.vendors if v.get("isActive", True)],
            key=lambda x: x.get("name", "")
        )

    def get_all_vendors_raw(self) -> List[dict]:
        """Get all vendors including inactive."""
        return self.master_data.vendors if self.master_data else []

    def add_vendor(self, data: dict) -> bool:
        """Add a new vendor."""
        if not self.master_data: 
            return False
        
        # Check duplicate
        name = data.get("name", "").strip()
        if any(v.get("name", "").lower() == name.lower() for v in self.master_data.vendors):
            return False # Duplicate
            
        new_vendor = {
            "name": name,
            "gstin": data.get("gstin", ""),
            "contact_person": data.get("contact_person", ""),
            "isActive": True
        }
        self.master_data.vendors.append(new_vendor)
        self.data_service.save_master_data()
        return True

    def update_vendor(self, original_name: str, data: dict) -> bool:
        """Update an existing vendor."""
        if not self.master_data: return False
        
        for i, v in enumerate(self.master_data.vendors):
            if v.get("name") == original_name:
                self.master_data.vendors[i].update(data)
                self.data_service.save_master_data()
                return True
        return False

    def delete_vendor(self, name: str) -> bool:
        """Soft delete (disable) a vendor."""
        if not self.master_data: return False
        
        for i, v in enumerate(self.master_data.vendors):
            if v.get("name") == name:
                self.master_data.vendors[i]["isActive"] = False
                self.data_service.save_master_data()
                return True
        return False

# Singleton instance
_config_service = None

def get_voucher_config() -> VoucherConfigService:
    """Get singleton voucher config service."""
    global _config_service
    if _config_service is None:
        _config_service = VoucherConfigService()
    return _config_service
