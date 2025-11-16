
from .utils import SETTINGS_FILE, ensure_dirs, load_json, save_json

DEFAULT_SETTINGS = {
    "PIN": "1234",
    "SHUTDOWN_KEY": "letmein123",
    "DEBUG_KEY": "debug123",
    "ADMIN_KEY": "admin123",
    "TOKEN_TTL": 15,
    "TEMP_BLOCK_SECONDS": 300,
    "DISPLAY_MS": 10000,
    "LOCK_MODE": "all_ip",
}

SETTINGS = {}  # populated by load_settings()


def load_settings():
    global SETTINGS
    ensure_dirs()
    raw = load_json(SETTINGS_FILE, default={})
    merged = DEFAULT_SETTINGS.copy()
    merged.update(raw or {})

    # normalise types
    try:
        merged["TOKEN_TTL"] = int(merged.get("TOKEN_TTL", DEFAULT_SETTINGS["TOKEN_TTL"]))
    except Exception:
        merged["TOKEN_TTL"] = DEFAULT_SETTINGS["TOKEN_TTL"]

    try:
        merged["TEMP_BLOCK_SECONDS"] = int(merged.get("TEMP_BLOCK_SECONDS", DEFAULT_SETTINGS["TEMP_BLOCK_SECONDS"]))
    except Exception:
        merged["TEMP_BLOCK_SECONDS"] = DEFAULT_SETTINGS["TEMP_BLOCK_SECONDS"]

    try:
        merged["DISPLAY_MS"] = int(merged.get("DISPLAY_MS", DEFAULT_SETTINGS["DISPLAY_MS"]))
    except Exception:
        merged["DISPLAY_MS"] = DEFAULT_SETTINGS["DISPLAY_MS"]

    if merged.get("LOCK_MODE") not in ("all_ip", "single_ip"):
        merged["LOCK_MODE"] = "all_ip"

    SETTINGS = merged
    return SETTINGS


def save_settings():
    ensure_dirs()
    save_json(SETTINGS_FILE, SETTINGS)
