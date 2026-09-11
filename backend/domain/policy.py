"""Canonical nutrition policy and deterministic input normalization."""

import json
import re
from pathlib import Path

POLICY = json.loads(Path(__file__).with_name("nutrition_policy.json").read_text(encoding="utf-8"))
GOALS = POLICY["goals"]
CONDITIONS = POLICY["conditions"]
MODIFIERS = POLICY["modifiers"]


def normalized(value: str) -> str:
    return re.sub(r"[\s_()-]+", " ", value.strip().lower()).strip()


def resolve_condition(value: str) -> str:
    needle = normalized(value)
    for key, condition in CONDITIONS.items():
        if any(normalized(alias) == needle for alias in condition["aliases"]):
            return key
    raise ValueError("Unsupported health condition")


def resolve_goal(value: str) -> str:
    needle = normalized(value)
    for key, goal in GOALS.items():
        if needle in (normalized(key), normalized(goal["name"])):
            return key
    raise ValueError("Unsupported goal")


def condition_options():
    return [
        {key: condition[key] for key in ("key", "name", "description", "adjustment_label")}
        for condition in CONDITIONS.values()
    ]
