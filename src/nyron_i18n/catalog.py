"""Catalog model, locale-tag normalization, and catalog validation.

The catalog is the only place where localized strings live: lookup and
fallback logic never contain per-language conditionals.  A catalog is a
small immutable mapping with a fixed shape::

    {"locale": "zh-CN", "messages": {"common.ok": "确定"}}

Equivalent data (any ``Mapping`` with exactly those two keys) is accepted
through :meth:`MessageCatalog.from_dict`, and ``from_json`` is a thin
convenience over ``json.loads`` for catalog files.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from .errors import CatalogValidationError, LocaleError

# Lightweight, deliberately non-BCP-47 tag grammar: one language subtag
# followed by zero or more alphanumeric subtags (region, script, ...).
_LOCALE_TAG_RE = re.compile(r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$")


def normalize_locale_tag(tag: str) -> str:
    """Validate and canonicalize a locale tag.

    The canonical form lowercases the language subtag and uppercases a
    two-letter alphabetic region subtag, so ``zh-cn`` and ``zh-CN`` both
    normalize to ``zh-CN``.  Any other subtag is lowercased.  Blank,
    non-string, or syntactically invalid tags raise :class:`LocaleError`.
    """
    if not isinstance(tag, str):
        raise LocaleError("locale tag must be a string")
    stripped = tag.strip()
    if not stripped:
        raise LocaleError("locale tag must not be blank")
    if not _LOCALE_TAG_RE.fullmatch(stripped):
        raise LocaleError(f"invalid locale tag: {tag!r}")
    parts = stripped.split("-")
    parts[0] = parts[0].lower()
    for index in range(1, len(parts)):
        part = parts[index]
        if len(part) == 2 and part.isalpha():
            parts[index] = part.upper()
        else:
            parts[index] = part.lower()
    return "-".join(parts)


@dataclass(frozen=True)
class MessageCatalog:
    """An immutable, validated catalog of messages for one locale.

    ``locale`` is normalized on construction; ``messages`` is copied and
    validated so later mutation of the caller's source mapping cannot
    affect the catalog.
    """

    locale: str
    messages: Mapping[str, str]

    def __post_init__(self) -> None:
        try:
            normalized_locale = normalize_locale_tag(self.locale)
        except LocaleError as exc:
            raise CatalogValidationError(str(exc)) from exc
        object.__setattr__(self, "locale", normalized_locale)

        raw_messages = self.messages
        if not isinstance(raw_messages, Mapping):
            raise CatalogValidationError("catalog 'messages' must be a mapping")
        cleaned: dict[str, str] = {}
        for key, value in raw_messages.items():
            if not isinstance(key, str) or not key:
                raise CatalogValidationError(
                    f"catalog message keys must be non-empty strings, "
                    f"got {key!r}"
                )
            if not isinstance(value, str):
                raise CatalogValidationError(
                    f"catalog message value for {key!r} must be a string, "
                    f"got {type(value).__name__}"
                )
            cleaned[key] = value
        object.__setattr__(self, "messages", cleaned)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "MessageCatalog":
        """Build a validated catalog from the canonical dict shape."""
        if not isinstance(data, Mapping):
            raise CatalogValidationError("catalog must be a mapping")
        unknown = set(data.keys()) - {"locale", "messages"}
        if unknown:
            raise CatalogValidationError(
                f"unexpected catalog top-level key(s): {sorted(unknown)}"
            )
        if "locale" not in data:
            raise CatalogValidationError("catalog is missing 'locale'")
        if "messages" not in data:
            raise CatalogValidationError("catalog is missing 'messages'")
        return cls(locale=data["locale"], messages=data["messages"])

    @classmethod
    def from_json(cls, text: str) -> "MessageCatalog":
        """Load a catalog from a JSON document string."""
        if not isinstance(text, str):
            raise CatalogValidationError("catalog JSON must be a string")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise CatalogValidationError(f"invalid catalog JSON: {exc}") from exc
        return cls.from_dict(data)
