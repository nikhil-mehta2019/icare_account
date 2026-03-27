import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any
from psycopg2.extras import execute_values
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
        """Atomic, FY-aware sequence generation natively in PostgreSQL."""
        if date_obj is None:
            date_obj = datetime.now()
            
        fy = FinancialYear.from_date(date_obj)
        v_type = voucher_type.upper()
        p_code = product_code.upper()[:3] if product_code else 'GEN'
        
        query = """
            INSERT INTO voucher_sequences (voucher_type, product_code, financial_year, current_value)
            VALUES (%s, %s, %s, 1)
            ON CONFLICT (voucher_type, product_code, financial_year)
            DO UPDATE SET current_value = voucher_sequences.current_value + 1
            RETURNING current_value;
        """
        
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, (v_type, p_code, fy.code))
                next_val = cur.fetchone()['current_value']
                conn.commit()
                
                # Format: DB-PRO-2024-25-0001
                return f"DB-{p_code}-{fy.code}-{next_val:04d}"

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
    
    def add_vouchers_bulk(self, vouchers: list) -> int:
        """
        High-performance batch insert for bulk imports.
        Maps list of objects or dicts to the vouchers table.
        """
        query = """
            INSERT INTO vouchers (
                voucher_id, voucher_no, voucher_type, voucher_date, status, 
                account_code, segment, amount, narration, reference_id,
                gst_amount, tds_section, tds_amount, created_at, updated_at
            ) VALUES %s
        """
        
        values = []
        for v in vouchers:
            # Handle both objects (from models) and dictionaries
            is_dict = isinstance(v, dict)
            
            # Helper to get attributes/keys safely
            def get_val(obj, key, default=None):
                if is_dict: return obj.get(key, default)
                return getattr(obj, key, default)

            # Handle nested GST/TDS logic
            gst = get_val(v, 'gst')
            tds = get_val(v, 'tds')
            
            values.append((
                get_val(v, 'voucher_id') or get_val(v, 'reference_id', 'BULK-IMPORT'),
                get_val(v, 'voucher_no'),
                str(get_val(v, 'voucher_type', 'DEBIT')).split('.')[-1],
                get_val(v, 'date') or get_val(v, 'voucher_date'),
                get_val(v, 'status', 'Imported'),
                get_val(v, 'account_code'),
                get_val(v, 'segment'),
                get_val(v, 'amount', 0.0),
                get_val(v, 'narration', ''),
                get_val(v, 'reference_id'),
                getattr(gst, 'total_amount', 0.0) if hasattr(gst, 'total_amount') else 0.0,
                getattr(tds, 'section', None) if hasattr(tds, 'section') else None,
                getattr(tds, 'amount', 0.0) if hasattr(tds, 'amount') else 0.0,
                datetime.now(),
                datetime.now()
            ))

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, query, values, page_size=1000)
                conn.commit()
                return len(values)


    def delete_voucher(self, voucher_no: str):
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM vouchers WHERE voucher_no = %s", (voucher_no,))
                conn.commit()

    def get_vouchers_by_date_range(self, start_date, end_date):
        """Fetch vouchers within a specific date range from SQL."""
        query = "SELECT * FROM vouchers WHERE voucher_date BETWEEN %s AND %s ORDER BY voucher_date ASC"
        return self.execute_read(query, (start_date, end_date))

    def update_voucher(self, voucher) -> bool:
        """Fully PostgreSQL-driven update. Overwrites existing voucher details."""
        query = """
            UPDATE vouchers 
            SET 
                voucher_date = %s, status = %s, account_code = %s, segment = %s, 
                amount = %s, narration = %s, reference_id = %s,
                gst_amount = %s, cgst_amount = %s, sgst_amount = %s, igst_amount = %s, gst_rate = %s,
                tds_section = %s, tds_amount = %s, tds_rate = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE voucher_id = %s OR voucher_no = %s;
        """
        
        # Helper to safely extract properties from objects or dicts
        is_dict = isinstance(voucher, dict)
        def get_val(key, default=None):
            return voucher.get(key, default) if is_dict else getattr(voucher, key, default)

        # Extract nested tax data if it exists
        gst = get_val('gst')
        tds = get_val('tds')
        vid = get_val('voucher_id')
        vno = get_val('voucher_no')
        
        if not vid and not vno:
            raise ValueError("Cannot update voucher: Missing both voucher_id and voucher_no")

        values = (
            get_val('date') or get_val('voucher_date'),
            get_val('status', 'Saved'),
            get_val('account_code'),
            get_val('segment'),
            get_val('amount', 0.0),
            get_val('narration', ''),
            get_val('reference_id'),
            getattr(gst, 'total_amount', 0.0) if gst else 0.0,
            getattr(gst, 'cgst_amount', 0.0) if gst else 0.0,
            getattr(gst, 'sgst_amount', 0.0) if gst else 0.0,
            getattr(gst, 'igst_amount', 0.0) if gst else 0.0,
            getattr(gst, 'rate', 0.0) if gst else 0.0,
            getattr(tds, 'section', None) if tds else None,
            getattr(tds, 'amount', 0.0) if tds else 0.0,
            getattr(tds, 'rate', 0.0) if tds else 0.0,
            vid, vno
        )

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, values)
                rows_updated = cur.rowcount
                conn.commit()
                return rows_updated > 0

    def get_vouchers_by_status(self, status: str) -> List[Dict]:
        """Fetch vouchers natively filtered by status."""
        query = "SELECT * FROM vouchers WHERE status = %s ORDER BY voucher_date DESC"
        return self.execute_read(query, (status,))

    def get_vouchers_by_segment(self, segment: str) -> List[Dict]:
        """Fetch vouchers natively filtered by segment."""
        query = "SELECT * FROM vouchers WHERE segment = %s ORDER BY voucher_date DESC"
        return self.execute_read(query, (segment,))