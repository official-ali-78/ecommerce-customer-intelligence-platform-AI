"""WSGI entry for Gunicorn / uWSGI / mod_wsgi."""

from app import create_app

app = create_app()
