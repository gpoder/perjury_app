
from flask import (
    Blueprint,
    request,
    render_template,
    url_for,
    redirect,
    send_file,
    abort,
)
import os
import time
import secrets

from ..settings import SETTINGS
from ..blocks import is_blocked, is_ip_permanently_blocked, set_permanent_block, set_global_block, is_global_block_active
from ..tokens import create_token, validate_token
from ..utils import IMAGE_PATH, log_event

main_bp = Blueprint("main", __name__)

# in-memory redirect keys: {key: {"token": ..., "time": ...}}
REDIRECT_TOKENS = {}


@main_bp.route("/")
def home():
    ip = request.remote_addr or "unknown"
    view_key = request.args.get("view")

    # one-time view path
    if view_key and view_key in REDIRECT_TOKENS:
        data = REDIRECT_TOKENS.pop(view_key)
        token = data["token"]
        # cleanup stale keys
        now = time.time()
        for k in list(REDIRECT_TOKENS.keys()):
            if now - REDIRECT_TOKENS[k]["time"] > 30:
                REDIRECT_TOKENS.pop(k, None)

        image_url = url_for("main.serve_image", token=token) + f"?r={secrets.token_hex(4)}"
        display_ms = SETTINGS.get("DISPLAY_MS", 10000)
        log_event("view_image_page", ip=ip)
        return render_template(
            "image_view.html",
            image_url=image_url,
            display_ms=display_ms,
            display_seconds=display_ms // 1000,
        )

    # normal visit: enforce block logic
    if is_blocked(ip):
        if SETTINGS.get("LOCK_MODE") == "all_ip" and is_global_block_active():
            return "Access temporarily blocked for all clients.", 403
        return "Access denied. Your IP is permanently blocked.", 403

    # show PIN form
    return render_template("pin.html")


@main_bp.route("/login", methods=["POST"])
def login():
    from ..settings import SETTINGS

    posted_pin = request.form.get("pin", "")
    print("[LOGIN DEBUG] posted_pin:", repr(posted_pin))
    print("[LOGIN DEBUG] expected PIN:", repr(SETTINGS.get("PIN")))

    ip = request.remote_addr or "unknown"
    pin = request.form.get("pin", "")

    # global block check (for all_ip mode)
    if SETTINGS.get("LOCK_MODE") == "all_ip" and is_global_block_active():
        return "Access temporarily blocked for all clients.", 403

    if is_ip_permanently_blocked(ip):
        return "IP permanently blocked.", 403

    if pin != SETTINGS.get("PIN"):
        log_event("login_fail", ip=ip)
        return "Incorrect PIN.", 403

    log_event("login_success", ip=ip)

    # 1) create one-time token
    token = create_token(ip)

    # 2) permanently block this IP
    set_permanent_block(ip)

    # 3) if all_ip mode, set global block
    if SETTINGS.get("LOCK_MODE") == "all_ip":
        seconds = SETTINGS.get("TEMP_BLOCK_SECONDS", 300)
        set_global_block(seconds)

    # 4) redirect key for one-time view
    key = secrets.token_hex(8)
    REDIRECT_TOKENS[key] = {"token": token, "time": time.time()}

    return redirect(url_for("main.home", view=key))


@main_bp.route("/image/<token>")
def serve_image(token):
    ip = request.remote_addr or "unknown"
    debug = request.args.get("debug") == "1"

    result = validate_token(token, ip, allow_debug=debug)
    if result != "ok":
        abort(403, f"Token error: {result}")

    if not IMAGE_PATH or not os.path.exists(IMAGE_PATH):
        abort(500, "Image missing")

    return send_file(IMAGE_PATH, mimetype="image/png")


@main_bp.route("/debug")
def debug_view():
    from ..settings import SETTINGS
    key = request.args.get("key", "")
    if key != SETTINGS.get("DEBUG_KEY"):
        return "Invalid debug key", 403

    ip = request.remote_addr or "debug"
    token = create_token(ip, no_expiry=True)
    image_url = url_for("main.serve_image", token=token) + f"?debug=1&r={secrets.token_hex(4)}"

    log_event("debug_view", ip=ip)
    return f"<h1>[DEBUG]</h1><p>Bypasses lock logic.</p><img src='{image_url}'>"


@main_bp.route("/shutdown")
def shutdown():
    from ..settings import SETTINGS
    key = request.args.get("key", "")
    if key != SETTINGS.get("SHUTDOWN_KEY"):
        return "Invalid key", 403

    log_event("shutdown_requested", ip=request.remote_addr or "unknown")

    import threading, os as _os, time as _time

    def killer():
        _time.sleep(0.5)
        _os._exit(0)

    threading.Thread(target=killer, daemon=True).start()
    return "Shutting down..."


@main_bp.route("/whoami")
def whoami():
    return f"""<pre>
remote_addr     : {request.remote_addr}
X-Real-IP       : {request.headers.get('X-Real-IP')}
X-Forwarded-For : {request.headers.get('X-Forwarded-For')}
</pre>"""
