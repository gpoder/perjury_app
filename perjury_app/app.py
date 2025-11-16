from __future__ import annotations

from flask import Flask, Blueprint
from werkzeug.middleware.proxy_fix import ProxyFix

from .utils import ensure_dirs, t
from .settings import load_settings
from .routes.main_routes import main_bp
from .routes.admin_routes import admin_bp


def init_perjury() -> None:
    """Initialise data directories and settings.

    This is safe to call multiple times (idempotent).
    """
    ensure_dirs()
    load_settings()


def create_perjury_blueprint() -> Blueprint:
    """Create a blueprint that bundles the main + admin routes.

    This is the recommended entry point when mounting Perjury inside AppHost:

        perjury_bp = create_perjury_blueprint()
        app.register_blueprint(perjury_bp, url_prefix="/perjury")

    With the AppHost apps app mounted under /apps, this exposes:

        /apps/perjury/           (PIN page)
        /apps/perjury/image      (image view)
        /apps/perjury/control/   (admin panel)
    """
    init_perjury()

    perjury_bp = Blueprint("perjury", __name__)

    # Nest the existing blueprints
    perjury_bp.register_blueprint(main_bp)
    perjury_bp.register_blueprint(admin_bp)

    @perjury_bp.app_context_processor
    def inject_t():
        # Make the translation helper available in all templates as `t`
        return {"t": t}

    @perjury_bp.app_template_filter("timestamp")
    def timestamp_filter(value):
        import time as _time
        try:
            v = float(value)
            return _time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime(v))
        except Exception:
            return "-"

    return perjury_bp


def create_app() -> Flask:
    """Standalone WSGI application factory.

    Allows running Perjury on its own, e.g.:

        from perjury_app import create_app
        app = create_app()
    """
    init_perjury()

    app = Flask("perjury_app")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1)

    # Register blueprints at root level
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_t_ctx():
        return {"t": t}

    @app.template_filter("timestamp")
    def timestamp_filter(value):
        import time as _time
        try:
            v = float(value)
            return _time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime(v))
        except Exception:
            return "-"

    return app


# CLI / entry-point helper
def main() -> None:
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
