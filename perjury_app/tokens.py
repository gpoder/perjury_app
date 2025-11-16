
import os
import time
import secrets

from .utils import TOKENS_DIR, load_json, save_json, log_event
from .settings import SETTINGS


def token_file(token: str) -> str:
    return os.path.join(TOKENS_DIR, f"{token}.json")


def create_token(ip: str, no_expiry: bool = False) -> str:
    t = secrets.token_hex(16)
    ttl = SETTINGS.get("TOKEN_TTL", 15)
    save_json(token_file(t), {
        "token": t,
        "ip": ip,
        "expires_at": 9999999999 if no_expiry else (time.time() + ttl),
        "used": False,
    })
    log_event("create_token", ip=ip, extra={"token": t, "no_expiry": no_expiry})
    return t


def validate_token(token: str, ip: str, allow_debug: bool = False) -> str:
    data = load_json(token_file(token), default={})
    if not data:
        return "invalid"
    if data.get("used"):
        return "used"
    if not allow_debug and data.get("ip") != ip:
        return "ip_mismatch"
    if time.time() > data.get("expires_at", 0):
        return "expired"

    data["used"] = True
    save_json(token_file(token), data)
    log_event("use_token", ip=ip, extra={"token": token, "debug": allow_debug})
    return "ok"
