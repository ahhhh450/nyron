"""Exception types for the Nyron i18n localization foundation."""

from __future__ import annotations


class I18nError(Exception):
    """Base class for every localization-specific error."""


class LocaleError(I18nError):
    """A locale tag is blank, non-string, or syntactically invalid."""


class CatalogValidationError(I18nError):
    """A message catalog is malformed or contains invalid entries."""


class CatalogConflictError(I18nError):
    """A locale was registered twice with conflicting content."""


class MessageNotFoundError(I18nError):
    """Neither the requested locale nor the default locale has the key."""


class InterpolationError(I18nError):
    """Placeholder interpolation failed and refused to emit bad text."""
