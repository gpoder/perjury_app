
import os
import time

from .utils import BLOCKS_DIR, GLOBAL_BLOCK_FILE, load_json, save_json, log_event
from .settings import SETTINGS


def block_file(ip: str) -> str:
    return os.path.join(BLOCKS_DIR, f"{ip}.json")


def is_global_block_active() -> bool:
    data = load_json(GLOBAL_BLOCK_FILE, default={})
    return bool(data and data.get("temp_block_until", 0) > time.time())


def set_global_block(seconds: int):
    save_json(GLOBAL_BLOCK_FILE, {"temp_block_until": time.time() + seconds})
    log_event("set_global_block", extra={"seconds": seconds})


def clear_global_block():
    if os.path.exists(GLOBAL_BLOCK_FILE):
        os.remove(GLOBAL_BLOCK_FILE)
        log_event("clear_global_block")


def is_ip_permanently_blocked(ip: str) -> bool:
    data = load_json(block_file(ip), default={})
    return bool(data.get("permanent"))


def set_permanent_block(ip: str):
    path = block_file(ip)
    data = load_json(path, default={})
    data.update({
        "ip": ip,
        "first_seen": data.get("first_seen", time.time()),
        "permanent": True,
    })
    save_json(path, data)
    log_event("set_permanent_block", ip=ip)


def is_blocked(ip: str) -> bool:
    # If permanently blocked, always blocked
    if is_ip_permanently_blocked(ip):
        return True
    # In all_ip mode, global block applies to everyone
    if SETTINGS.get("LOCK_MODE") == "all_ip" and is_global_block_active():
        return True
    return False
