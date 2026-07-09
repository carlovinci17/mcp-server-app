import json
from enum import StrEnum


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
