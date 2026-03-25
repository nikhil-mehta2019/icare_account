import sys
import os
import json
import psycopg2

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config.settings import get_db_connection_string
from services.path_utils import get_user_data_dir

def clean_migrate_master_data():
    conn_str = get_db_connection_string()
    try:
        conn = psycopg2.connect(conn_str)
        cur = conn.cursor()
        print("Connected to PostgreSQL successfully.")
    except Exception as e:
        print(f"FAILED to connect to DB: {e}")
        return

    # 1. TRUNCATE EXISTING TABLES (Clean Slate & Reset IDs)
    print("Truncating existing master tables...")
    cur.execute("""
        TRUNCATE TABLE 
            master_vendors, 
            master_segments, 
            master_account_heads, 
            master_settings 
        RESTART IDENTITY CASCADE;
    """)
    conn.commit()
    print("Tables truncated successfully.")

    # 2. READ JSON DATA
    data_dir = get_user_data_dir()
    master_file = data_dir / 'master_data.json'
    
    if not master_file.exists():
        print(f"Could not find {master_file}")
        cur.close()
        conn.close()
        return

    with open(master_file, 'r', encoding='utf-8') as f:
        m_data = json.load(f)

        # 3. INSERT VENDORS
        vendors = m_data.get('vendors', [])
        v_count = 0
        for v in vendors:
            name = v.get('name', '').strip()
            if not name: continue
            cur.execute("""
                INSERT INTO master_vendors (name, gstin, contact_person, is_active, created_by, updated_by)
                VALUES (%s, %s, %s, %s, 'Migration', 'Migration');
            """, (name, v.get('gstin', ''), v.get('contact_person', ''), v.get('isActive', True)))
            v_count += 1
        print(f"Inserted {v_count} Vendors.")

        # 4. INSERT SEGMENTS
        segments = m_data.get('segments', [])
        s_count = 0
        for s in segments:
            cur.execute("""
                INSERT INTO master_segments (segment_id, name, description, allocation_percentage, is_active, created_by, updated_by)
                VALUES (%s, %s, %s, %s, %s, 'Migration', 'Migration');
            """, (s.get('segment_id'), s.get('name'), s.get('description'), s.get('allocation_percentage', 0.0), s.get('is_active', True)))
            s_count += 1
        print(f"Inserted {s_count} Segments.")

        # 5. INSERT ACCOUNT HEADS
        heads = m_data.get('account_heads', [])
        h_count = 0
        for a in heads:
            cur.execute("""
                INSERT INTO master_account_heads (code, voucher_type, main_head, sub_head, sub_sub_head, segment_tag, usual_narration, requires_segment_selection, is_active, created_by, updated_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'Migration', 'Migration');
            """, (a.get('code'), a.get('voucher_type'), a.get('main_head'), a.get('sub_head'), a.get('sub_sub_head'), a.get('segment_tag'), a.get('usual_narration'), a.get('requires_segment_selection', False), a.get('is_active', True)))
            h_count += 1
        print(f"Inserted {h_count} Account Heads.")

        # 6. INSERT SETTINGS (EAV format)
        settings = m_data.get('settings', {})
        set_count = 0
        for k, v in settings.items():
            v_type = 'str'
            if isinstance(v, bool): v_type = 'bool'
            elif isinstance(v, int): v_type = 'int'
            elif isinstance(v, float): v_type = 'float'
            
            cur.execute("""
                INSERT INTO master_settings (config_key, config_value, value_type, created_by, updated_by)
                VALUES (%s, %s, %s, 'Migration', 'Migration');
            """, (k, str(v), v_type))
            set_count += 1
        print(f"Inserted {set_count} Settings configurations.")

    conn.commit()
    print("\nSUCCESS! Clean migration complete. Database is now in sync with JSON.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    clean_migrate_master_data()