import json
from collections.abc import Callable
from enum import StrEnum
from functools import wraps

from src.database.sql import DatabaseUnavailableError


def report_database_unavailable(fn: Callable[..., str]) -> Callable[..., str]:
    """Wrap a tool function so a paused/unavailable database is reported via
    this package's `{"error": ...}` JSON contract instead of raising and
    surfacing as an opaque "An error occurred invoking '<tool>'" from the
    MCP host.
    """

    @wraps(fn)
    def wrapper(*args, **kwargs) -> str:
        try:
            return fn(*args, **kwargs)
        except DatabaseUnavailableError as exc:
            return json.dumps({"error": str(exc)})

    return wrapper


def parse_enum_or_error(
    enum_cls: type[StrEnum], value: str | None
) -> tuple[StrEnum | None, str | None]:
    """Parse `value` into `enum_cls`, mirroring this package's `{"error": ...}`
    JSON contract instead of letting an invalid value raise ValueError.

    Returns (parsed_value, None) on success, or (None, json_error_string) if
    `value` isn't a valid member.
    """
    if value is None:
        return None, None
    try:
        return enum_cls(value), None
    except ValueError:
        valid = ", ".join(member.value for member in enum_cls)
        error = json.dumps({"error": f"Invalid value '{value}'. Must be one of: {valid}"})
        return None, error
