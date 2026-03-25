"""Backup Service - Handles asynchronous, thread-safe file backups."""
import os
import zipfile
import threading
import logging
import json
from datetime import datetime
from pathlib import Path

from models.financial_year import FinancialYear

# Configure centralized backup logger
backup_logger = logging.getLogger("BackupService")
backup_logger.setLevel(logging.INFO)
app_data = Path(os.getenv('LOCALAPPDATA', '')) / "iCareAccount"
app_data.mkdir(parents=True, exist_ok=True)
log_file = app_data / "backup.log"

handler = logging.FileHandler(log_file, encoding='utf-8')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not backup_logger.handlers:
    backup_logger.addHandler(handler)

class BackupService:
    """Asynchronous, non-blocking backup manager."""
    _backup_lock = threading.Lock()

    @classmethod
    def trigger_backup(cls, data_dir: str, backup_dir: str, retention_count: int = 30):
        """Fire and forget backup trigger executed safely in a background thread."""
        thread = threading.Thread(
            target=cls._perform_backup, 
            args=(data_dir, backup_dir, retention_count), 
            daemon=True
        )
        thread.start()

    @classmethod
    def _perform_backup(cls, data_dir: str, backup_dir: str, retention_count: int):
        """Execute safe ZIP compression and retention cleanup."""
        # Ensure single backup thread at a time to prevent disk I/O fighting
        with cls._backup_lock:
            try:
                # 1. Resolve and Validate Backup Directory
                if not backup_dir:
                    backup_dir = str(app_data / "backups")
                
                os.makedirs(backup_dir, exist_ok=True)
                if not os.access(backup_dir, os.W_OK):
                    backup_logger.error(f"Cannot write to backup directory: {backup_dir}")
                    return

                # 2. Setup Naming and Manifest
                now = datetime.now()
                fy = FinancialYear.from_date(now)
                timestamp = now.strftime("%Y%m%d_%H%M%S")
                filename = f"icare_backup_FY{fy.code}_{timestamp}.zip"
                backup_path = os.path.join(backup_dir, filename)

                data_p = Path(data_dir)
                
                # Only backup JSON core data files for safety and size
                files_to_backup = [f for f in os.listdir(data_dir) if f.endswith('.json')]
                
                # 3. Create ZIP securely
                with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for fname in files_to_backup:
                        fpath = data_p / fname
                        if fpath.exists():
                            zf.write(fpath, arcname=f"data/{fname}")
                    
                    # Store metadata for restore readiness
                    manifest = {
                        "timestamp": now.isoformat(),
                        "financial_year": fy.code,
                        "version": "1.0",
                        "files_included": files_to_backup
                    }
                    zf.writestr("manifest.json", json.dumps(manifest, indent=2))
                
                backup_logger.info(f"Backup created successfully: {filename}")

                # 4. Retention Management
                cls._cleanup_old_backups(backup_dir, retention_count)

            except Exception as e:
                backup_logger.error(f"Backup operation failed: {str(e)}", exc_info=True)

    @classmethod
    def _cleanup_old_backups(cls, backup_dir: str, retention_count: int):
        """Safely remove old backups ensuring only system-generated ZIPs are touched."""
        try:
            backups = []
            for fname in os.listdir(backup_dir):
                if fname.startswith("icare_backup_") and fname.endswith(".zip"):
                    backups.append(os.path.join(backup_dir, fname))
            
            # Sort by newest first based on file modified time
            backups.sort(key=os.path.getmtime, reverse=True)
            
            if len(backups) > retention_count:
                files_to_delete = backups[retention_count:]
                for f in files_to_delete:
                    os.remove(f)
                    backup_logger.info(f"Auto-deleted old backup to maintain retention: {os.path.basename(f)}")
        except Exception as e:
            backup_logger.error(f"Failed during cleanup of old backups: {str(e)}")