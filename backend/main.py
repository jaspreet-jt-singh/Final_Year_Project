"""Stable ASGI entrypoint. Run locally with python -m uvicorn backend.main:app."""

from backend.application import create_app
import logging

logging.basicConfig(level=logging.INFO)
app = create_app()
