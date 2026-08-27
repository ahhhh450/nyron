"""Built-in zh-CN and en-US message catalogs.

Importing this module only defines immutable catalog data; it performs no
registration and mutates no global state.  Callers build a
:class:`LocalizationService` and register catalogs explicitly, or use
:func:`with_builtin_catalogs`.
"""

from __future__ import annotations

from .catalog import MessageCatalog
from .service import LocalizationService

_ZH_CN_MESSAGES: dict[str, str] = {
    "common.ok": "确定",
    "common.confirm": "确认",
    "common.cancel": "取消",
    "common.yes": "是",
    "common.no": "否",
    "common.back": "返回",
    "common.loading": "加载中",
    "common.error": "错误",
    "common.retry": "重试",
    "common.greeting": "你好，{name}",
    "locale.name.zh-CN": "简体中文",
    "locale.name.en-US": "英语",
}

_EN_US_MESSAGES: dict[str, str] = {
    "common.ok": "OK",
    "common.confirm": "Confirm",
    "common.cancel": "Cancel",
    "common.yes": "Yes",
    "common.no": "No",
    "common.back": "Back",
    "common.loading": "Loading",
    "common.error": "Error",
    "common.retry": "Retry",
    "common.greeting": "Hello, {name}",
    "locale.name.zh-CN": "Simplified Chinese",
    "locale.name.en-US": "English",
}


def zh_cn_catalog() -> MessageCatalog:
    """Return the built-in ``zh-CN`` catalog."""
    return MessageCatalog(locale="zh-CN", messages=_ZH_CN_MESSAGES)


def en_us_catalog() -> MessageCatalog:
    """Return the built-in ``en-US`` catalog."""
    return MessageCatalog(locale="en-US", messages=_EN_US_MESSAGES)


def builtin_catalogs() -> tuple[MessageCatalog, MessageCatalog]:
    """Return both built-in catalogs, in a stable order."""
    return (zh_cn_catalog(), en_us_catalog())


def with_builtin_catalogs(default_locale: str = "en-US") -> LocalizationService:
    """Return a service pre-registered with both built-in catalogs.

    ``default_locale`` is explicit and configurable; the returned service is
    a fresh instance and no process-global state is touched.
    """
    service = LocalizationService(default_locale=default_locale)
    for catalog in builtin_catalogs():
        service.register(catalog)
    return service
