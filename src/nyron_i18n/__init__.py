"""Nyron i18n — small, deterministic, catalog-driven localization foundation.

This package lives outside ``nyron_kernel`` and does not touch any Kernel
or Runtime primitive.  It is localization infrastructure, not an LLM
machine-translation system.
"""

from __future__ import annotations

from .builtins import (
    builtin_catalogs,
    en_us_catalog,
    with_builtin_catalogs,
    zh_cn_catalog,
)
from .catalog import MessageCatalog, normalize_locale_tag
from .errors import (
    CatalogConflictError,
    CatalogValidationError,
    I18nError,
    InterpolationError,
    LocaleError,
    MessageNotFoundError,
)
from .interpolation import interpolate
from .service import LocalizationService

__all__ = [
    "CatalogConflictError",
    "CatalogValidationError",
    "I18nError",
    "InterpolationError",
    "LocaleError",
    "LocalizationService",
    "MessageCatalog",
    "MessageNotFoundError",
    "builtin_catalogs",
    "en_us_catalog",
    "interpolate",
    "normalize_locale_tag",
    "with_builtin_catalogs",
    "zh_cn_catalog",
]
