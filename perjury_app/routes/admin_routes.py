
from flask import Blueprint, request, redirect, url_for, render_template
import os
import time

from ..settings import SETTINGS, save_settings
from ..utils import BLOCKS_DIR, load_json, log_event, load_log, GLOBAL_BLOCK_FILE
from ..blocks import block_file, clear_global_block

admin_bp = Blueprint("control", __name__, url_prefix="/control")

@admin_bp.before_request
def bypass_all_ip_blocks():
    # admin always allowed, key must still match
    return None

@admin_bp.route("/", methods=["GET", "POST"])
def admin_index():
    from ..settings import SETTINGS  # ensure we see the live SETTINGS

    admin_key = request.args.get("key", "")

    # 🔍 DEBUG: print and also echo in response if wrong
    print("[ADMIN DEBUG] args:", dict(request.args))
    print("[ADMIN DEBUG] admin_key:", repr(admin_key))
    print("[ADMIN DEBUG] expected:", repr(SETTINGS.get("ADMIN_KEY")))

    if admin_key != SETTINGS.get("ADMIN_KEY"):
        # TEMP: show mismatch clearly in the browser
        return (
            f"Forbidden (admin_key={admin_key!r}, expected={SETTINGS.get('ADMIN_KEY')!r})",
            403,
        )

    ip = request.remote_addr or "unknown"
    # ... keep the rest of the existing function below this ...

    if request.method == "POST":
        old = SETTINGS.copy()
        SETTINGS["PIN"] = request.form.get("PIN", SETTINGS["PIN"])
        SETTINGS["DEBUG_KEY"] = request.form.get("DEBUG_KEY", SETTINGS["DEBUG_KEY"])
        SETTINGS["SHUTDOWN_KEY"] = request.form.get("SHUTDOWN_KEY", SETTINGS["SHUTDOWN_KEY"])
        SETTINGS["ADMIN_KEY"] = request.form.get("ADMIN_KEY", SETTINGS["ADMIN_KEY"])

        for field in ("DISPLAY_MS", "TOKEN_TTL", "TEMP_BLOCK_SECONDS"):
            try:
                SETTINGS[field] = int(request.form.get(field, SETTINGS[field]))
            except (TypeError, ValueError):
                pass

        mode = request.form.get("LOCK_MODE", SETTINGS["LOCK_MODE"])
        if mode in ("all_ip", "single_ip"):
            SETTINGS["LOCK_MODE"] = mode

        save_settings()
        log_event("admin_update_settings", ip=ip, extra={"old": old, "new": SETTINGS})
        return redirect(url_for("control.admin_index") + f"?key={SETTINGS['ADMIN_KEY']}")

    # GET
    logs = load_log()
    logs = logs[-100:][::-1]

    blocked = []
    if os.path.isdir(BLOCKS_DIR):
        for fname in os.listdir(BLOCKS_DIR):
            if not fname.endswith(".json"):
                continue
            entry_ip = fname[:-5]
            data = load_json(os.path.join(BLOCKS_DIR, fname), default={})
            blocked.append({
                "ip": entry_ip,
                "permanent": bool(data.get("permanent")),
                "first_seen": data.get("first_seen"),
            })

    global_data = load_json(GLOBAL_BLOCK_FILE, default={})
    until = global_data.get("temp_block_until")
    global_until_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(until)) if until else "None"

    return render_template(
        "admin.html",
        ip=ip,
        settings=SETTINGS,
        blocked=blocked,
        logs=logs,
        global_until=global_until_str,
    )


@admin_bp.route("/delete_block")
def admin_delete_block():
    from ..settings import SETTINGS
    admin_key = request.args.get("key", "")
    if admin_key != SETTINGS.get("ADMIN_KEY"):
        return "Forbidden", 403

    target_ip = request.args.get("ip")
    if target_ip:
        path = block_file(target_ip)
        if os.path.exists(path):
            os.remove(path)
            log_event("admin_delete_block", ip=request.remote_addr or "unknown", extra={"target_ip": target_ip})

    return redirect(url_for("control.admin_index") + f"?key={SETTINGS['ADMIN_KEY']}")


@admin_bp.route("/clear_log")
def admin_clear_log():
    from ..settings import SETTINGS
    admin_key = request.args.get("key", "")
    if admin_key != SETTINGS.get("ADMIN_KEY"):
        return "Forbidden", 403

    from ..utils import save_log
    save_log([])
    log_event("admin_clear_log", ip=request.remote_addr or "unknown")
    return redirect(url_for("control.admin_index") + f"?key={SETTINGS['ADMIN_KEY']}")


@admin_bp.route("/clear_global")
def admin_clear_global_route():
    from ..settings import SETTINGS

    admin_key = request.args.get("key", "")

    if admin_key != SETTINGS.get("ADMIN_KEY"):
        return (
            f"Forbidden (admin_key={admin_key!r}, expected={SETTINGS.get('ADMIN_KEY')!r})",
            403,
        )

    clear_global_block()
    return redirect(url_for("control.admin_index") + f"?key={SETTINGS['ADMIN_KEY']}")

