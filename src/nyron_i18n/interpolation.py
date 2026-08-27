"""Deterministic named-placeholder interpolation.

Only ``{name}`` placeholders are supported, where ``name`` matches
``[A-Za-z_][A-Za-z0-9_.-]*``.  No format specifiers, nesting, or ``{{``
escaping are provided; this keeps the format tiny and safe.  Any malformed
template, missing value, non-string value, or unexpected parameter raises
:class:`InterpolationError` instead of silently producing corrupted text.
"""

from __future__ import annotations

import re
from typing import Mapping

from .errors import InterpolationError

_PLACEHOLDER_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*")


def interpolate(template: str, params: Mapping[str, str]) -> str:
    """Substitute ``{name}`` placeholders in ``template`` using ``params``.

    Missing placeholder values, unexpected parameters, non-string values,
    and malformed templates all raise :class:`InterpolationError`.
    """
    if not isinstance(template, str):
        raise InterpolationError("template must be a string")
    if not isinstance(params, Mapping):
        raise InterpolationError("params must be a mapping")

    for name, value in params.items():
        if not isinstance(name, str):
            raise InterpolationError("parameter names must be strings")
        if not isinstance(value, str):
            raise InterpolationError(
                f"value for parameter {name!r} must be a string, "
                f"got {type(value).__name__}"
            )

    output: list[str] = []
    used: set[str] = set()
    index = 0
    length = len(template)
    while index < length:
        char = template[index]
        if char == "{":
            close = template.find("}", index + 1)
            if close == -1:
                raise InterpolationError(
                    f"unterminated placeholder starting at index {index}"
                )
            name = template[index + 1 : close]
            if not _PLACEHOLDER_NAME_RE.fullmatch(name):
                raise InterpolationError(
                    f"invalid placeholder {template[index:close + 1]!r} "
                    f"at index {index}"
                )
            if name not in params:
                raise InterpolationError(
                    f"missing value for placeholder {name!r}"
                )
            output.append(params[name])
            used.add(name)
            index = close + 1
        elif char == "}":
            raise InterpolationError(f"unexpected '}}' at index {index}")
        else:
            output.append(char)
            index += 1

    extra = [name for name in params if name not in used]
    if extra:
        raise InterpolationError(
            f"unexpected interpolation parameter(s): {sorted(extra)}"
        )
    return "".join(output)
