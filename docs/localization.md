# Nyron i18n — Localization Foundation

`src/nyron_i18n/` is a small, deterministic, catalog-driven localization
foundation. It lives outside `src/nyron_kernel/` and does not touch any
Kernel or Runtime primitive. It is localization infrastructure, not an LLM
machine-translation system.

## Current built-in locales

- `zh-CN` — Simplified Chinese
- `en-US` — English

## Quick start

```python
from nyron_i18n import with_builtin_catalogs

svc = with_builtin_catalogs(default_locale="en-US")

svc.get("common.ok")                      # "OK"
svc.get("common.ok", "zh-CN")             # "确定"
svc.format("common.greeting", "zh-CN", name="世界")  # "你好，世界"
```

## How to add a new locale

Add a locale without touching the core lookup/fallback algorithm: build a
catalog and register it on the service.

```python
from nyron_i18n import MessageCatalog, with_builtin_catalogs

svc = with_builtin_catalogs(default_locale="en-US")

svc.register(
    MessageCatalog(
        locale="th-TH",
        messages={
            "common.ok": "ตกลง",
            "common.cancel": "ยกเลิก",
        },
    )
)

svc.get("common.ok", "th-TH")     # "ตกลง"
svc.get("common.cancel", "th-TH") # "ยกเลิก"
```

Catalogs can also be loaded from data (`MessageCatalog.from_dict`) or from a
JSON document (`MessageCatalog.from_json`), so catalogs may live in files
later without changing the core API.

## Behavior

- Lookup is catalog-driven: no per-language conditionals exist in the core.
- Locale tags are normalized (`zh-cn` → `zh-CN`) via a lightweight grammar,
  not a full BCP-47 parser.
- Fallback is deterministic: requested locale, then the configured default
  locale, then a `MessageNotFoundError` when neither has the key.
- Named `{placeholder}` interpolation fails loudly on missing/unknown values
  and malformed templates instead of emitting corrupted text.
- Malformed catalogs and conflicting duplicate registrations are rejected.
- Importing the package performs no hidden global registration; each
  `LocalizationService` owns its own catalogs and explicit default locale.
