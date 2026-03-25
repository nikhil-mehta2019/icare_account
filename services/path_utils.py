import os
import sys
import shutil
import logging
from pathlib import Path

# Setup basic file logging for windowed app debugging
log_dir = Path(os.getenv('LOCALAPPDATA', os.path.expanduser('~'))) / "iCareAccount" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(log_dir / 'app.log'),
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_user_data_dir() -> Path:
    """Returns the persistent, user-writable data directory."""
    app_data = Path(os.getenv('LOCALAPPDATA', os.path.expanduser('~'))) / "iCareAccount" / "data"
    app_data.mkdir(parents=True, exist_ok=True)
    return app_data

def get_bundled_path(relative_path: str) -> Path:
    """Returns the path to bundled read-only assets (handles PyInstaller _MEIPASS)."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(os.path.abspath("."))
    return base_path / relative_path

def ensure_persistent_file(filename: str, default_relative_path: str) -> Path:
    """
    Ensures a file exists in the user data dir. 
    If not, copies the default from the bundle.
    Returns the path to the persistent file.
    """
    persistent_file = get_user_data_dir() / filename
    
    if not persistent_file.exists():
        bundled_file = get_bundled_path(default_relative_path)
        try:
            if bundled_file.exists():
                shutil.copy2(bundled_file, persistent_file)
            else:
                # If no bundled file exists, create an empty one or let the caller handle it
                pass
        except Exception as e:
            logging.error(f"Failed to copy default {filename} to persistent storage: {e}")
            
    return persistent_file