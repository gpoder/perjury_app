import json
import os
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

_lock = threading.Lock()

DEFAULT_SETTINGS: Dict[str, Any] = {
    "view_duration_seconds": 10,
    "enable_global_lockout": True,
    "global_lockout_minutes": 5,
}

def _base_dir() -> str:
    # Highest priority: explicit environment
    env_dir = os.environ.get("PERJURY_DATA_DIR")
    if env_dir:
        return env_dir
    # Next: AppHost data dir, if present
    apphost_dir = os.environ.get("APPHOST_DATA_DIR")
    if apphost_dir:
        return os.path.join(apphost_dir, "perjury")
    # Fallback: package-local data/
    return os.path.join(os.path.dirname(__file__), "data")

def ensure_data_layout() -> str:
    base = _base_dir()
    os.makedirs(base, exist_ok=True)
    return base

def _file_path(name: str) -> str:
    base = ensure_data_layout()
    return os.path.join(base, name)

def _read_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (IOError, json.JSONDecodeError):
        return default

def _write_json(path: str, data: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)

def load_settings() -> Dict[str, Any]:
    path = _file_path("settings.json")
    data = _read_json(path, {})
    merged = {**DEFAULT_SETTINGS, **data}
    return merged

def save_settings(settings: Dict[str, Any]) -> None:
    path = _file_path("settings.json")
    _write_json(path, settings)

def load_tokens() -> List[Dict[str, Any]]:
    path = _file_path("tokens.json")
    data = _read_json(path, {"tokens": []})
    return data.get("tokens", [])

def save_tokens(tokens: List[Dict[str, Any]]) -> None:
    path = _file_path("tokens.json")
    _write_json(path, {"tokens": tokens})

def load_blocks() -> List[str]:
    path = _file_path("blocks.json")
    data = _read_json(path, {"ips": []})
    return data.get("ips", [])

def save_blocks(ips: List[str]) -> None:
    path = _file_path("blocks.json")
    _write_json(path, {"ips": ips})

def append_log(event: str, **fields: Any) -> None:
    path = _file_path("log.json")
    log = _read_json(path, [])
    entry = {
        "time": datetime.utcnow().isoformat() + "Z",
        "event": event,
        **fields,
    }
    log.append(entry)
    _write_json(path, log)

def get_token(tokens: List[Dict[str, Any]], token_value: str) -> Optional[Dict[str, Any]]:
    for t in tokens:
        if t.get("token") == token_value:
            return t
    return None

def upsert_token(tokens: List[Dict[str, Any]], token: Dict[str, Any]) -> List[Dict[str, Any]]:
    existing = False
    for i, t in enumerate(tokens):
        if t.get("token") == token.get("token"):
            tokens[i] = token
            existing = True
            break
    if not existing:
        tokens.append(token)
    return tokens

def is_global_lockout(settings: Dict[str, Any]) -> Tuple[bool, Optional[datetime]]:
    until_str = settings.get("global_lockout_until")
    if not until_str:
        return False, None
    try:
        until = datetime.fromisoformat(until_str.replace("Z", ""))
    except Exception:
        return False, None
    now = datetime.utcnow()
    return now < until, until

def start_global_lockout(settings: Dict[str, Any]) -> Dict[str, Any]:
    minutes = int(settings.get("global_lockout_minutes", 5))
    until = datetime.utcnow() + timedelta(minutes=minutes)
    settings["global_lockout_until"] = until.isoformat() + "Z"
    return settings
