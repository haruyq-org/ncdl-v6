import os
import sys
from pathlib import Path

APP_NAME = "ncdl"

def is_frozen() -> bool:
    return getattr(sys, "frozen", False)

def get_project_dir() -> Path:
    return Path(__file__).resolve().parents[2]

def get_resource_dir() -> Path:
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)

    return get_project_dir()

def get_app_dir() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent

    return get_project_dir()

def get_config_dir() -> Path:
    if os.name == "nt":
        base_dir = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    return base_dir / APP_NAME

def get_data_dir() -> Path:
    if os.name == "nt":
        base_dir = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    return base_dir / APP_NAME
