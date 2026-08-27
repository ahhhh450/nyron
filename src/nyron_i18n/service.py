"""Deterministic, catalog-driven localization service.

A :class:`LocalizationService` owns an explicit, per-instance locale ->
catalog map plus an explicit default locale.  Nothing is stored in a
process-global registry, and importing this module has no registration
side effects.
"""

from __future__ import annotations

from .catalog import MessageCatalog, normalize_locale_tag
from .errors import CatalogConflictError, MessageNotFoundError
from .interpolation import interpolate


class LocalizationService:
    """Resolve localized messages with deterministic lookup and fallback."""

    def __init__(self, default_locale: str = "en-US") -> None:
        self._default_locale = normalize_locale_tag(default_locale)
        self._catalogs: dict[str, MessageCatalog] = {}

    @property
    def default_locale(self) -> str:
        """The normalized default locale used for fallback."""
        return self._default_locale

    def locales(self) -> tuple[str, ...]:
        """Return the registered locale tags, sorted for determinism."""
        return tuple(sorted(self._catalogs))

    def has_locale(self, locale: str) -> bool:
        """Return whether ``locale`` is registered (after normalization)."""
        return normalize_locale_tag(locale) in self._catalogs

    def register(self, catalog: MessageCatalog) -> None:
        """Register a catalog, failing closed on conflicting duplicates.

        Re-registering the same locale with semantically identical content
        is a no-op (idempotent).  Re-registering the same locale with
        different content raises :class:`CatalogConflictError`.
        """
        if not isinstance(catalog, MessageCatalog):
            raise TypeError("register() requires a MessageCatalog")
        existing = self._catalogs.get(catalog.locale)
        if existing is not None:
            if existing.messages == catalog.messages:
                return
            raise CatalogConflictError(
                f"locale {catalog.locale!r} is already registered with "
                f"different content"
            )
        self._catalogs[catalog.locale] = catalog

    def get(self, key: str, locale: str | None = None) -> str:
        """Resolve ``key`` for ``locale`` (default locale when omitted).

        Deterministic fallback: the requested locale is tried first; if it
        is unregistered or lacks the key, the default locale is tried.
        Raises :class:`MessageNotFoundError` when neither supplies the key.
        """
        if not isinstance(key, str):
            raise TypeError("message key must be a string")
        if not key:
            raise ValueError("message key must not be empty")

        requested = (
            self._default_locale if locale is None else normalize_locale_tag(locale)
        )

        catalog = self._catalogs.get(requested)
        if catalog is not None and key in catalog.messages:
            return catalog.messages[key]

        if requested != self._default_locale:
            default_catalog = self._catalogs.get(self._default_locale)
            if default_catalog is not None and key in default_catalog.messages:
                return default_catalog.messages[key]

        raise MessageNotFoundError(
            f"message key {key!r} not found for locale {requested!r} "
            f"(default {self._default_locale!r})"
        )

    def format(self, key: str, locale: str | None = None, **params: str) -> str:
        """Resolve ``key`` and interpolate the named ``params`` into it."""
        template = self.get(key, locale)
        return interpolate(template, params)
