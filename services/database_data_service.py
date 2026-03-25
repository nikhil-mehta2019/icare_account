import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any
from models.financial_year import FinancialYear
from datetime import datetime

class DatabaseDataService:
    """Strictly handles raw SQL operations. No JSON compilation."""
    
    def __init__(self):
        # Update with your actual credentials
        self.conn_string = "dbname=icare_db user=postgres password=admin123 host=localhost"

    def _get_connection(self):
        return psycopg2.connect(self.conn_string, cursor_factory=RealDictCursor)

    def execute_read(self, query: str, params: tuple = ()) -> List[Dict]:
        """Generic flat read for multiple rows."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchall()

    def execute_read_one(self, query: str, params: tuple = ()) -> Dict:
        """Generic single flat read for one row (used for counts/lookups)."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return cur.fetchone()

    # --- Master Data ---
    def get_vendors(self) -> List[Dict]:
        """Fetch ALL vendors for UI dropdowns."""
        query = "SELECT id, name, gstin, contact_person FROM master_vendors ORDER BY name"
        return self.execute_read(query)

    def get_business_segments(self) -> List[Dict]:
        """Fetch ALL business segments for UI dropdowns."""
        query = "SELECT id, code, name FROM config_business_segments ORDER BY name"
        return self.execute_read(query)
        
    def get_point_of_supply_states(self) -> List[Dict]:
        """Fetch ALL POS states for UI dropdowns."""
        query = "SELECT id, code, name, is_home_state, is_foreign FROM config_point_of_supply"
        return self.execute_read(query)

    # --- Sequences & Counting ---
    def get_voucher_count(self) -> int:
        """Count total vouchers in DB for the MainWindow status bar."""
        row = self.execute_read_one("SELECT COUNT(*) as count FROM vouchers")
        return row['count'] if row else 0

    def generate_next_voucher_sequence(self, voucher_type: str, product_code: str, date_obj: datetime = None) -> str:
        """Generate generic voucher sequence dynamically based on Financial Year."""
        if date_obj is None:
            date_obj = datetime.now()
            
        fy = FinancialYear.from_date(date_obj)
        
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                seq_name = f"seq_{voucher_type}_{product_code}".lower()
                cur.execute(f"SELECT nextval('{seq_name}')")
                next_val = cur.fetchone()['nextval']
                return f"DB-{product_code[:3].upper()}-{fy.code}-{next_val:04d}"

    def generate_credit_sale_code(self, date_obj: datetime) -> str:
        """Generate sequential code for sales dynamically based on Financial Year."""
        fy = FinancialYear.from_date(date_obj)
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT nextval('seq_sales_voucher')")
                next_val = cur.fetchone()['nextval']
                return f"CR-SAL-{fy.code}-{next_val:04d}"

    # --- Persistence ---
    def add_voucher(self, voucher) -> None:
        """
        Transactional insert into the wide vouchers table.
        Maps the UI Voucher object properties directly to PostgreSQL columns.
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # We must include voucher_id in the column list to satisfy the NOT NULL constraint
                cur.execute("""
                    INSERT INTO vouchers (
                        voucher_id, voucher_no, voucher_type, voucher_date, status, 
                        account_code, segment, amount, narration, reference_id,
                        gst_amount, tds_section, tds_amount, created_at, updated_at
                    ) VALUES (
                        %s, %s, %s, %s, %s, 
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                """, (
                    # Use reference_id as voucher_id if explicit ID is missing
                    getattr(voucher, 'voucher_id', None) or getattr(voucher, 'reference_id', 'AUTO-GEN'),
                    voucher.voucher_no, 
                    str(getattr(voucher, 'voucher_type', 'UNKNOWN')).split('.')[-1], 
                    voucher.date, 
                    getattr(voucher, 'status', 'Saved'), 
                    getattr(voucher, 'account_code', None), 
                    getattr(voucher, 'segment', None), 
                    getattr(voucher, 'amount', 0.0), 
                    voucher.narration, 
                    getattr(voucher, 'reference_id', None),
                    getattr(voucher.gst, 'total_amount', 0.0) if hasattr(voucher, 'gst') and voucher.gst else 0.0, 
                    getattr(voucher.tds, 'section', None) if hasattr(voucher, 'tds') and voucher.tds else None, 
                    getattr(voucher.tds, 'amount', 0.0) if hasattr(voucher, 'tds') and voucher.tds else 0.0
                ))
                conn.commit()