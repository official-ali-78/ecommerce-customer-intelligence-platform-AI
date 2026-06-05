"""SQLAlchemy database extension and session management."""

from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def init_db(app) -> None:
    """Bind SQLAlchemy to the Flask app."""
    db.init_app(app)

    @app.teardown_appcontext
    def shutdown_session(exception=None):  # noqa: ARG001
        db.session.remove()
