"""Reading numeric settings from the environment without letting a typo stop monitoring."""

import logging
import os

log = logging.getLogger(__name__)


def env_float(name: str, default: float, env=None) -> float:
    """A positive number from the environment, or ``default`` if unset or invalid."""
    raw = (env if env is not None else os.environ).get(name)
    if raw in (None, ""):
        return default
    try:
        value = float(raw)
    except ValueError:
        value = -1.0
    if not 0 < value < float("inf"):
        log.warning("Ignoring %s=%r: expected a positive number, using %s", name, raw, default)
        return default
    return value
