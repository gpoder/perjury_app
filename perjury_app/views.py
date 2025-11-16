import os
from datetime import datetime
from typing import Any, Dict

from flask import (
    Blueprint,
    Flask,
    abort,
    redirect,
    render_template,
    request,
    url_for,
    make_response,
)

from . import storage

def _client_ip() -> str:
    # Simple IP resolution, aware of reverse proxies
    fwd = request.headers.get("X-Forwarded-For", "")
    if fwd:
        # Use left-most IP
        return fwd.split(",")[0].strip()
    return request.remote_addr or "0.0.0.0"

def _no_cache_response(resp):
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp

def create_perjury_blueprint() -> Blueprint:
    bp = Blueprint("perjury", __name__, template_folder="templates", static_folder="static")

    @bp.after_request
    def add_no_cache_headers(resp):
        return _no_cache_response(resp)

    @bp.route("/")
    def index():
        return render_template("perjury/index.html")

    @bp.route("/view/<token>", methods=["GET", "POST"])
    def view_token(token: str):
        ip = _client_ip()
        settings = storage.load_settings()
        tokens = storage.load_tokens()
        blocks = storage.load_blocks()

        # IP already blocked?
        if ip in blocks:
            storage.append_log("blocked_ip_attempt", ip=ip, token=token)
            return render_template("perjury/blocked.html", ip=ip), 403

        # Global lockout?
        locked, until = storage.is_global_lockout(settings)
        if locked and settings.get("enable_global_lockout", True):
            storage.append_log("global_lockout_hit", ip=ip, token=token)
            return (
                render_template("perjury/lockout.html", until=until),
                423,
            )

        t = storage.get_token(tokens, token)
        if not t:
            storage.append_log("invalid_token", ip=ip, token=token)
            return render_template("perjury/invalid.html"), 404

        if t.get("used"):
            storage.append_log("reused_token_attempt", ip=ip, token=token)
            return render_template("perjury/already_used.html"), 410

        error = None

        if request.method == "POST":
            pin = (request.form.get("pin") or "").strip()
            if not pin:
                error = "PIN is required."
            elif pin != str(t.get("pin", "")):
                storage.append_log("wrong_pin", ip=ip, token=token)
                error = "Incorrect PIN."
            else:
                # Success: mark used, block IP, maybe trigger global lockout
                t["used"] = True
                t["used_at"] = datetime.utcnow().isoformat() + "Z"
                t["ip"] = ip
                tokens = storage.upsert_token(tokens, t)
                storage.save_tokens(tokens)

                if ip not in blocks:
                    blocks.append(ip)
                    storage.save_blocks(blocks)

                if settings.get("enable_global_lockout", True):
                    settings = storage.start_global_lockout(settings)
                    storage.save_settings(settings)

                storage.append_log("token_viewed", ip=ip, token=token)

                # Render one-time view
                view_seconds = int(settings.get("view_duration_seconds", 10))
                resp = make_response(
                    render_template(
                        "perjury/view.html",
                        token=t,
                        view_seconds=view_seconds,
                    )
                )
                return resp

        # GET or failed POST
        resp = make_response(
            render_template("perjury/pin_entry.html", token=t, error=error)
        )
        return resp

    @bp.route("/control/")
    def control_index():
        # NOTE: Protect this path at Nginx level (IP allow, basic auth, etc.)
        settings = storage.load_settings()
        tokens = storage.load_tokens()
        blocks = storage.load_blocks()
        return render_template(
            "perjury/control/index.html",
            settings=settings,
            tokens=tokens,
            blocks=blocks,
        )

    @bp.route("/control/settings", methods=["POST"])
    def control_settings():
        settings = storage.load_settings()
        view_seconds = request.form.get("view_duration_seconds", "").strip() or "10"
        lockout_minutes = request.form.get("global_lockout_minutes", "").strip() or "5"
        enable_lockout = bool(request.form.get("enable_global_lockout"))

        try:
            settings["view_duration_seconds"] = int(view_seconds)
        except ValueError:
            pass
        try:
            settings["global_lockout_minutes"] = int(lockout_minutes)
        except ValueError:
            pass
        settings["enable_global_lockout"] = enable_lockout

        storage.save_settings(settings)
        storage.append_log("settings_updated", **settings)
        return redirect(url_for("perjury.control_index"))

    @bp.route("/control/generate_token", methods=["POST"])
    def control_generate_token():
        tokens = storage.load_tokens()
        token_value = (request.form.get("token") or "").strip()
        pin_value = (request.form.get("pin") or "").strip()
        image_url = (request.form.get("image_url") or "").strip()

        if not token_value or not pin_value or not image_url:
            # In a real app, you'd flash a message; here we simply ignore and redirect
            return redirect(url_for("perjury.control_index"))

        token = {
            "token": token_value,
            "pin": pin_value,
            "image_url": image_url,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "used": False,
        }
        tokens = storage.upsert_token(tokens, token)
        storage.save_tokens(tokens)
        storage.append_log("token_created", token=token_value, image_url=image_url)
        return redirect(url_for("perjury.control_index"))

    @bp.route("/control/clear_blocks", methods=["POST"])
    def control_clear_blocks():
        storage.save_blocks([])
        storage.append_log("blocks_cleared")
        return redirect(url_for("perjury.control_index"))

    return bp

def create_app() -> Flask:
    app = Flask("perjury_standalone")
    bp = create_perjury_blueprint()
    app.register_blueprint(bp, url_prefix="/")
    return app
