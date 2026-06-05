"""
Olist E-Commerce Analytics — 4-page Flask web app.

Run:
    pip install -r requirements.txt
    flask --app app run --debug
"""

from __future__ import annotations

import logging
import os
from logging.config import dictConfig

from flask import Flask, jsonify, redirect, render_template, url_for

from config import config_by_name
from database.connection import init_db
from routes import api_bp, main_bp


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)

    env = config_name or os.getenv("FLASK_ENV", "development")
    app.config.from_object(config_by_name.get(env, config_by_name["default"]))

    _configure_logging(app)
    if app.config.get("USE_MYSQL"):
        init_db(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_context_processors(app)

    @app.route("/health")
    def health():
        from services.data_loader import resolve_data_source

        with app.app_context():
            source = resolve_data_source()
        return jsonify({"status": "healthy", "environment": env, "data_source": source})

    return app


def _configure_logging(app: Flask) -> None:
    log_level = logging.DEBUG if app.debug else logging.INFO
    dictConfig(
        {
            "version": 1,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                }
            },
            "root": {"level": log_level, "handlers": ["console"]},
        }
    )


def _register_blueprints(app: Flask) -> None:
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(err):  # noqa: ARG001
        if _wants_json():
            return jsonify({"error": "Not found"}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(err):  # noqa: ARG001
        app.logger.exception("Unhandled error")
        if _wants_json():
            return jsonify({"error": "Internal server error"}), 500
        return render_template("errors/500.html"), 500


def _register_context_processors(app: Flask) -> None:
    @app.context_processor
    def inject_globals():
        return {"app_name": "Olist Analytics Platform"}


def _wants_json() -> bool:
    from flask import request

    return (
        request.path.startswith("/api/")
        or request.accept_mimetypes.best == "application/json"
    )


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
