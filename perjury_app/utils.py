import os
import json
import time
from typing import Any, Dict, List

# Base directory of the installed package
BASE_DIR = os.path.dirname(__file__)


def _compute_data_dir() -> str:
    """Determine the directory used for all data (tokens, blocks, settings, log).

    Priority:
    1. PERJURY_DATA_DIR environment variable
    2. APPHOST_DATA_DIR/perjury (when running under AppHost)
    3. Local package data/ folder
    """
    env_dir = os.environ.get("PERJURY_DATA_DIR")
    if env_dir:
        return env_dir

    apphost_dir = os.environ.get("APPHOST_DATA_DIR")
    if apphost_dir:
        return os.path.join(apphost_dir, "perjury")

    return os.path.join(BASE_DIR, "data")


DATA_DIR = _compute_data_dir()
BLOCKS_DIR = os.path.join(DATA_DIR, "blocks")
TOKENS_DIR = os.path.join(DATA_DIR, "tokens")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
GLOBAL_BLOCK_FILE = os.path.join(DATA_DIR, "global.json")
LOG_FILE = os.path.join(DATA_DIR, "log.json")
IMAGE_PATH = os.path.join(BASE_DIR, "image.png")


def ensure_dirs() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BLOCKS_DIR, exist_ok=True)
    os.makedirs(TOKENS_DIR, exist_ok=True)


def load_json(path: str, default: Any) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default


def save_json(path: str, data: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp, path)


def log_event(event: str, ip: str | None = None, extra: Dict[str, Any] | None = None) -> None:
    """Append a simple structured event to the log.json file."""
    extra = extra or {}
    entry = {
        "ts": time.time(),
        "event": event,
        "ip": ip or "",
        "extra": extra,
    }
    log: List[Dict[str, Any]] = load_json(LOG_FILE, default=[])
    log.append(entry)
    save_json(LOG_FILE, log)


def load_log() -> list[dict]:
    return load_json(LOG_FILE, default=[])


# --- Simple JSON-based i18n -------------------------------------------------

_LANG_CACHE: dict[str, dict[str, str]] = {}


def load_language(lang: str = "en") -> dict[str, str]:
    if lang in _LANG_CACHE:
        return _LANG_CACHE[lang]

    base_dir = BASE_DIR
    path = os.path.join(base_dir, "i18n", f"{lang}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}
    _LANG_CACHE[lang] = data
    return data


def t(key: str, lang: str = "en") -> str:
    """Translate a key using the loaded language dictionary."""
    data = load_language(lang)
    return data.get(key, f"[{key}]")
