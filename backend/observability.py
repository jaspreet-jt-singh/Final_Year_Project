"""Allowlisted operational events. Never serialize request/provider payloads."""

import json
import logging
from contextvars import ContextVar

request_id = ContextVar("request_id", default="background")
logger = logging.getLogger("food.operations")


def event(name: str, **fields):
    allowed = {"method", "route", "status", "duration_ms", "provider", "outcome", "error_type"}
    logger.info(
        json.dumps(
            {
                "event": name,
                "request_id": request_id.get(),
                **{key: value for key, value in fields.items() if key in allowed},
            }
        )
    )
