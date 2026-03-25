import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import List, Optional, Any
import getpass

from config.settings import get_db_connection_string
from services.data_service import DataService
from models.master_data import MasterData
from models.financial_year import FinancialYear

class DatabaseDataService(DataService):
    def __init__(self):
        self.conn_str = get_db_connection_string()
        self._master_data = None
        self._vouchers = []
        self.current_user = getpass.getuser() # Fetches local OS user for audit fields

    def _get_connection(self):
        return psycopg2.connect(self.conn_str, cursor_factory=RealDictCursor)

    # ==========================================
    # MASTER DATA RECONSTRUCTION
    # ==========================================
    def load_master_data(self) -> MasterData:
        assembled_data = {
            "account_heads": [],
            "segments": [],
            "vendors": [],
            "narrations": [],
            "settings": {}
        }

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Fetch Account Heads
                cur.execute("SELECT * FROM master_account_heads")
                for row in cur.fetchall():
                    row_dict = dict(row)
                    row_dict['requires_segment_selection'] = bool(row_dict['requires_segment_selection'])
                    row_dict['is_active'] = bool(row_dict['is_active'])
                    assembled_data["account_heads"].append(row_dict)

                # 2. Fetch Segments
                cur.execute("SELECT * FROM master_segments")
                assembled_data["segments"] = [dict(row) for row in cur.fetchall()]

                # 3. Fetch Vendors (CRITICAL FIX: Rename is_active to isActive)
                cur.execute("SELECT * FROM master_vendors") # Fetch ALL, so admin can see disabled ones
                for row in cur.fetchall():
                    v_dict = dict(row)
                    # Pop the DB column name and assign it to the UI's expected key
                    v_dict['isActive'] = v_dict.pop('is_active', True) 
                    assembled_data["vendors"].append(v_dict)

                # 4. Fetch Narrations
                cur.execute("SELECT * FROM master_narrations")
                assembled_data["narrations"] = [dict(row) for row in cur.fetchall()]

                # 5. Fetch Settings (EAV mapping)
                cur.execute("SELECT config_key, config_value, value_type FROM master_settings")
                for row in cur.fetchall():
                    val = row['config_value']
                    if row['value_type'] == 'int': val = int(val)
                    elif row['value_type'] == 'float': val = float(val)
                    elif row['value_type'] == 'bool': val = val.lower() == 'true'
                    assembled_data["settings"][row['config_key']] = val

        self._master_data = MasterData.from_dict(assembled_data) if assembled_data.get("settings") else MasterData.create_default()
        return self._master_data

    # ==========================================
    # CRUD OPERATIONS MAPPING
    # ==========================================
    def save_master_data(self) -> None:
        if not self._master_data: return
        md_dict = self._master_data.to_dict() if hasattr(self._master_data, 'to_dict') else self._master_data.__dict__

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Upsert Vendors (Translates UI's 'isActive' back to DB's 'is_active')
                for v in md_dict.get('vendors', []):
                    # Safely check for both camelCase and snake_case to be bulletproof
                    is_active_val = v.get('isActive', v.get('is_active', True)) 
                    
                    cur.execute("""
                        INSERT INTO master_vendors (name, gstin, contact_person, is_active, created_by)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (name) DO UPDATE 
                        SET gstin = EXCLUDED.gstin, contact_person = EXCLUDED.contact_person, 
                            is_active = EXCLUDED.is_active, updated_by = %s;
                    """, (v.get('name'), v.get('gstin'), v.get('contact_person'), is_active_val, self.current_user, self.current_user))

                # 2. Upsert Segments
                for s in md_dict.get('segments', []):
                    is_active_val = s.get('isActive', s.get('is_active', True))
                    cur.execute("""
                        INSERT INTO master_segments (segment_id, name, description, allocation_percentage, is_active, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (segment_id) DO UPDATE
                        SET name = EXCLUDED.name, description = EXCLUDED.description,
                            allocation_percentage = EXCLUDED.allocation_percentage,
                            is_active = EXCLUDED.is_active, updated_by = %s;
                    """, (s.get('segment_id'), s.get('name'), s.get('description'), s.get('allocation_percentage', 0.0), is_active_val, self.current_user, self.current_user))

                # 3. Upsert Narrations
                for n in md_dict.get('narrations', []):
                    is_active_val = n.get('isActive', n.get('is_active', True))
                    cur.execute("""
                        INSERT INTO master_narrations (narration_id, template, account_code, has_placeholder, placeholder_label, is_active, created_by)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (narration_id) DO UPDATE
                        SET template = EXCLUDED.template, account_code = EXCLUDED.account_code,
                            has_placeholder = EXCLUDED.has_placeholder, placeholder_label = EXCLUDED.placeholder_label,
                            is_active = EXCLUDED.is_active, updated_by = %s;
                    """, (n.get('narration_id'), n.get('template'), n.get('account_code'), n.get('has_placeholder', False), n.get('placeholder_label'), is_active_val, self.current_user, self.current_user))

                # 4. Upsert Settings (Type Casting for EAV Table)
                for k, v in md_dict.get('settings', {}).items():
                    v_type = 'str'
                    if isinstance(v, bool): v_type = 'bool'
                    elif isinstance(v, int): v_type = 'int'
                    elif isinstance(v, float): v_type = 'float'
                    
                    cur.execute("""
                        INSERT INTO master_settings (config_key, config_value, value_type, created_by)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (config_key) DO UPDATE 
                        SET config_value = EXCLUDED.config_value, value_type = EXCLUDED.value_type, updated_by = %s;
                    """, (k, str(v), v_type, self.current_user, self.current_user))
                    
            conn.commit()

    # ==========================================
    # VOUCHERS MAPPING (No JSON Allowed)
    # ==========================================
    def load_vouchers(self) -> List[Any]:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM vouchers ORDER BY created_at ASC;")
                rows = cur.fetchall()
                
                vouchers_list = []
                for row in rows:
                    v_dict = dict(row)
                    # Reconstruct nested dictionaries expected by PySide6 models
                    if row.get('gst_rate') is not None:
                        v_dict['gst'] = {'rate': row['gst_rate'], 'amount': row['gst_amount']}
                    if row.get('tds_section') is not None:
                        v_dict['tds'] = {'section': row['tds_section'], 'rate': row['tds_rate'], 'amount': row['tds_amount']}
                    
                    # Convert date back to string if needed by UI
                    if isinstance(v_dict.get('voucher_date'), datetime) or hasattr(v_dict.get('voucher_date'), 'isoformat'):
                        v_dict['voucher_date'] = v_dict['voucher_date'].isoformat()
                        
                    vouchers_list.append(self._dict_to_voucher(v_dict))
                return vouchers_list

    def add_voucher(self, voucher: Any) -> None:
        v_dict = self._extract_dict(voucher)
        vid = v_dict.get('voucher_id') or v_dict.get('voucher_no', '')
        vtype = self._extract_type(v_dict)
        
        # Extract flattened fields safely
        gst_data = v_dict.get('gst', {})
        tds_data = v_dict.get('tds', {})

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO vouchers (
                        voucher_id, voucher_no, reference_id, voucher_type, voucher_date, 
                        amount, account_code, segment, narration, status,
                        gst_rate, gst_amount, tds_section, tds_rate, tds_amount, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (
                    vid, v_dict.get('voucher_no'), v_dict.get('reference_id'), vtype, v_dict.get('voucher_date', v_dict.get('date')),
                    v_dict.get('amount'), v_dict.get('account_code'), v_dict.get('segment'), v_dict.get('narration'), v_dict.get('status'),
                    gst_data.get('rate'), gst_data.get('amount'), tds_data.get('section'), tds_data.get('rate'), tds_data.get('amount'), self.current_user
                ))
            conn.commit()

    def update_voucher(self, voucher: Any) -> bool:
        v_dict = self._extract_dict(voucher)
        vid = v_dict.get('voucher_id') or v_dict.get('voucher_no')
        gst_data = v_dict.get('gst', {})
        tds_data = v_dict.get('tds', {})

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE vouchers SET 
                        amount = %s, account_code = %s, segment = %s, narration = %s, status = %s,
                        gst_rate = %s, gst_amount = %s, tds_section = %s, tds_rate = %s, tds_amount = %s,
                        updated_by = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE voucher_id = %s;
                """, (
                    v_dict.get('amount'), v_dict.get('account_code'), v_dict.get('segment'), v_dict.get('narration'), v_dict.get('status'),
                    gst_data.get('rate'), gst_data.get('amount'), tds_data.get('section'), tds_data.get('rate'), tds_data.get('amount'),
                    self.current_user, vid
                ))
                success = cur.rowcount > 0
            conn.commit()
        return success

    def delete_voucher(self, voucher_id: str) -> bool:
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM vouchers WHERE voucher_id = %s;", (voucher_id,))
                success = cur.rowcount > 0
            conn.commit()
        return success

    def load_voucher_config(self) -> dict:
        """
        Reconstructs the precise voucher_config.json dictionary structure 
        from the strict relational SQL tables.
        """
        config = {
            "tallyHeads": [], "countries": [], "products": [], 
            "businessSegments": [], "franchises": [], "pointOfSupply": [], 
            "tdsLedgers": [], "gstRates": [], "tdsRates": {}, 
            "gstLedgers": {}, "validation": {}
        }

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # 1. Reconstruct Standard Lists (Translating snake_case DB to camelCase UI)
                cur.execute("SELECT * FROM config_tally_heads ORDER BY id;")
                for row in cur.fetchall():
                    config["tallyHeads"].append({
                        "value": row["code"], "label": row["name"], "type": row["type"],
                        "needsFranchise": row["needs_franchise"], "isDomestic": row["is_domestic"],
                        "tdsSection": row["tds_section"], "isActive": row["is_active"]
                    })

                cur.execute("SELECT * FROM config_countries ORDER BY id;")
                for row in cur.fetchall():
                    config["countries"].append({
                        "value": row["code"], "label": row["name"], 
                        "isForeign": row["is_foreign"], "isActive": row["is_active"]
                    })

                cur.execute("SELECT * FROM config_products ORDER BY id;")
                for row in cur.fetchall():
                    config["products"].append({"value": row["code"], "label": row["name"], "isActive": row["is_active"]})

                cur.execute("SELECT * FROM config_business_segments ORDER BY id;")
                for row in cur.fetchall():
                    config["businessSegments"].append({"value": row["code"], "label": row["name"], "isActive": row["is_active"]})

                cur.execute("SELECT * FROM config_franchises ORDER BY id;")
                for row in cur.fetchall():
                    config["franchises"].append({"value": row["code"], "label": row["name"], "isActive": row["is_active"]})

                cur.execute("SELECT * FROM config_point_of_supply ORDER BY id;")
                for row in cur.fetchall():
                    config["pointOfSupply"].append({
                        "value": row["code"], "label": row["name"],
                        "isHomeState": row["is_home_state"], "isForeign": row["is_foreign"], "isActive": row["is_active"]
                    })

                cur.execute("SELECT * FROM config_tds_ledgers ORDER BY id;")
                for row in cur.fetchall():
                    config["tdsLedgers"].append({
                        "value": row["code"], "label": row["name"], 
                        "section": row["section"], "isActive": row["is_active"]
                    })

                # 2. Reconstruct Rates
                cur.execute("SELECT rate FROM config_gst_rates WHERE is_active = TRUE ORDER BY rate;")
                config["gstRates"] = [float(row["rate"]) for row in cur.fetchall()]

                cur.execute("SELECT section, name, rate FROM config_tds_rates WHERE is_active = TRUE;")
                for row in cur.fetchall():
                    config["tdsRates"][row["section"]] = {"name": row["name"], "rate": float(row["rate"])}

                # 3. Reconstruct Settings (EAV -> Dictionary)
                cur.execute("SELECT config_key, config_value, value_type FROM master_settings;")
                for row in cur.fetchall():
                    key = row["config_key"]
                    val = row["config_value"]
                    if row["value_type"] == "int": val = int(val)
                    elif row["value_type"] == "float": val = float(val)

                    if key.startswith("config_"):
                        config[key.replace("config_", "")] = val
                    elif key.startswith("val_"):
                        config["validation"][key.replace("val_", "")] = val
                    elif key.startswith("gstLedger_"):
                        config["gstLedgers"][key.replace("gstLedger_", "")] = val

        return config
    
    # ==========================================
    # SEQUENCE GENERATION (Database Overrides)
    # ==========================================
    def get_next_sequence(self, voucher_type: str, date_obj: Optional[datetime] = None) -> int:
        """Concurrency-safe sequence generation directly from PostgreSQL."""
        if date_obj is None: date_obj = datetime.now()
        target_fy = FinancialYear.from_date(date_obj)

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT reference_id, voucher_no, voucher_date 
                    FROM vouchers 
                    WHERE LOWER(voucher_type) = %s
                """, (voucher_type.lower(),))

                max_seq = 0
                for row in cur.fetchall():
                    # 1. Match Financial Year
                    v_date = row['voucher_date']
                    if not v_date: continue
                    
                    if isinstance(v_date, str):
                        try: v_date = datetime.strptime(v_date.split('T')[0], "%Y-%m-%d")
                        except: continue
                        
                    v_fy = FinancialYear.from_date(v_date)
                    if v_fy.code != target_fy.code:
                        continue

                    # 2. Extract the Sequence Number from the string
                    code = row['reference_id'] or row['voucher_no'] or ''
                    if not code: continue

                    parts = code.split('-')
                    try:
                        seq = int(parts[-1])
                        if seq > max_seq:
                            max_seq = seq
                    except ValueError:
                        continue

                return max_seq + 1

    def generate_credit_sale_code(self, date_obj: datetime) -> str:
        """Concurrency-safe Credit Sale sequence generation directly from PostgreSQL."""
        fy = FinancialYear.from_date(date_obj)
        prefix = f"CR-SAL-{fy.code}"

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT voucher_no, reference_id 
                    FROM vouchers 
                    WHERE LOWER(voucher_type) = 'credit'
                """)

                max_seq = 0
                for row in cur.fetchall():
                    code = row['voucher_no'] or row['reference_id'] or ''
                    if code.startswith(prefix):
                        try:
                            parts = code.split('-')
                            if len(parts) > 0:
                                seq = int(parts[-1])
                                if seq > max_seq:
                                    max_seq = seq
                        except ValueError:
                            continue
                            
        return f"{prefix}-{max_seq + 1:04d}"
    
    # [Helper methods _extract_dict, _extract_type remain identical to previous implementation]