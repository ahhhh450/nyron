"""Focused validation for the Nyron i18n localization foundation.

Covers the Task 150 validation checklist: built-in zh-CN/en-US resolution,
deterministic fallback, deterministic failure, named placeholder
interpolation in both languages, clear interpolation failure, malformed
catalog rejection, fail-closed conflict registration, idempotent identical
registration, and the synthetic third-locale extension proof.
"""

from __future__ import annotations

import unittest

from nyron_i18n import (
    CatalogConflictError,
    CatalogValidationError,
    InterpolationError,
    LocaleError,
    LocalizationService,
    MessageCatalog,
    MessageNotFoundError,
    builtin_catalogs,
    en_us_catalog,
    interpolate,
    normalize_locale_tag,
    with_builtin_catalogs,
    zh_cn_catalog,
)


class BuiltinCatalogTests(unittest.TestCase):
    def test_zh_cn_builtin_loads_and_resolves_chinese(self):
        service = with_builtin_catalogs(default_locale="zh-CN")
        self.assertEqual(service.get("common.ok", "zh-CN"), "确定")
        self.assertEqual(service.get("common.confirm", "zh-CN"), "确认")
        self.assertEqual(service.get("common.cancel", "zh-CN"), "取消")
        self.assertEqual(service.get("common.retry", "zh-CN"), "重试")
        self.assertEqual(service.get("locale.name.zh-CN", "zh-CN"), "简体中文")

    def test_en_us_builtin_loads_and_resolves_english(self):
        service = with_builtin_catalogs(default_locale="en-US")
        self.assertEqual(service.get("common.ok", "en-US"), "OK")
        self.assertEqual(service.get("common.confirm", "en-US"), "Confirm")
        self.assertEqual(service.get("common.cancel", "en-US"), "Cancel")
        self.assertEqual(service.get("common.retry", "en-US"), "Retry")
        self.assertEqual(service.get("locale.name.en-US", "en-US"), "English")

    def test_builtin_catalogs_share_the_same_key_set(self):
        zh = zh_cn_catalog()
        en = en_us_catalog()
        self.assertEqual(set(zh.messages), set(en.messages))
        self.assertEqual(zh.locale, "zh-CN")
        self.assertEqual(en.locale, "en-US")

    def test_import_has_no_registration_side_effect(self):
        # A fresh service starts empty; importing nyron_i18n must not have
        # registered anything into hidden global state.
        service = LocalizationService(default_locale="en-US")
        self.assertEqual(service.locales(), ())


class FallbackTests(unittest.TestCase):
    def setUp(self):
        self.service = with_builtin_catalogs(default_locale="en-US")

    def test_missing_locale_falls_back_to_default(self):
        # fr-FR is not registered; fall back to default en-US.
        self.assertEqual(self.service.get("common.ok", "fr-FR"), "OK")

    def test_missing_key_in_requested_locale_falls_back_to_default(self):
        # A registered locale that lacks a key falls back to the default.
        self.service.register(
            MessageCatalog(locale="th-TH", messages={"common.ok": "ตกลง"})
        )
        self.assertEqual(self.service.get("common.ok", "th-TH"), "ตกลง")
        self.assertEqual(self.service.get("common.cancel", "th-TH"), "Cancel")

    def test_missing_key_in_both_fails_deterministically(self):
        with self.assertRaises(MessageNotFoundError):
            self.service.get("common.does_not_exist", "zh-CN")
        with self.assertRaises(MessageNotFoundError):
            self.service.get("common.does_not_exist", "fr-FR")

    def test_default_locale_is_explicit_and_configurable(self):
        zh_default = with_builtin_catalogs(default_locale="zh-CN")
        self.assertEqual(zh_default.default_locale, "zh-CN")
        self.assertEqual(zh_default.get("common.ok"), "确定")

    def test_locale_tag_case_is_normalized(self):
        self.assertEqual(self.service.get("common.ok", "en-us"), "OK")
        self.assertEqual(self.service.get("common.ok", "ZH-cn"), "确定")


class InterpolationTests(unittest.TestCase):
    def setUp(self):
        self.service = with_builtin_catalogs(default_locale="en-US")

    def test_named_placeholder_interpolation_in_both_languages(self):
        self.assertEqual(
            self.service.format("common.greeting", "en-US", name="World"),
            "Hello, World",
        )
        self.assertEqual(
            self.service.format("common.greeting", "zh-CN", name="世界"),
            "你好，世界",
        )

    def test_missing_interpolation_value_fails_clearly(self):
        with self.assertRaises(InterpolationError):
            self.service.format("common.greeting", "zh-CN")

    def test_unexpected_interpolation_parameter_fails_clearly(self):
        with self.assertRaises(InterpolationError):
            self.service.format("common.greeting", "en-US", name="A", extra="B")

    def test_malformed_template_fails_clearly(self):
        with self.assertRaises(InterpolationError):
            interpolate("Hello {name", {"name": "World"})
        with self.assertRaises(InterpolationError):
            interpolate("Hello }", {})
        with self.assertRaises(InterpolationError):
            interpolate("Hello {na me}", {"na me": "X"})

    def test_non_string_interpolation_value_fails_clearly(self):
        with self.assertRaises(InterpolationError):
            interpolate("Hello {name}", {"name": 42})


class CatalogValidationTests(unittest.TestCase):
    def test_malformed_top_level_rejected(self):
        with self.assertRaises(CatalogValidationError):
            MessageCatalog.from_dict(["not", "a", "mapping"])
        with self.assertRaises(CatalogValidationError):
            MessageCatalog.from_dict({"locale": "zh-CN"})  # missing messages
        with self.assertRaises(CatalogValidationError):
            MessageCatalog.from_dict({"messages": {}})  # missing locale
        with self.assertRaises(CatalogValidationError):
            MessageCatalog.from_dict(
                {"locale": "zh-CN", "messages": {}, "extra": 1}
            )

    def test_blank_locale_rejected(self):
        with self.assertRaises(CatalogValidationError):
            MessageCatalog(locale="", messages={})
        with self.assertRaises(CatalogValidationError):
            MessageCatalog(locale="   ", messages={})

    def test_invalid_locale_tag_rejected(self):
        with self.assertRaises(CatalogValidationError):
            MessageCatalog(locale="not a locale!", messages={})

    def test_non_string_key_rejected(self):
        with self.assertRaises(CatalogValidationError):
            MessageCatalog(locale="zh-CN", messages={1: "x"})

    def test_non_string_value_rejected(self):
        with self.assertRaises(CatalogValidationError):
            MessageCatalog(locale="zh-CN", messages={"common.ok": 1})

    def test_invalid_json_rejected(self):
        with self.assertRaises(CatalogValidationError):
            MessageCatalog.from_json("{not valid json")

    def test_json_catalog_loads(self):
        catalog = MessageCatalog.from_json(
            '{"locale": "zh-CN", "messages": {"common.ok": "确定"}}'
        )
        self.assertEqual(catalog.locale, "zh-CN")
        self.assertEqual(catalog.messages["common.ok"], "确定")


class RegistrationConflictTests(unittest.TestCase):
    def test_conflicting_duplicate_registration_fails_closed(self):
        service = LocalizationService(default_locale="en-US")
        service.register(MessageCatalog(locale="zh-CN", messages={"a": "1"}))
        with self.assertRaises(CatalogConflictError):
            service.register(MessageCatalog(locale="zh-CN", messages={"a": "2"}))

    def test_identical_registration_is_idempotent(self):
        service = LocalizationService(default_locale="en-US")
        first = MessageCatalog(locale="zh-CN", messages={"a": "1"})
        second = MessageCatalog(locale="zh-CN", messages={"a": "1"})
        service.register(first)
        service.register(second)  # no exception; identical content
        self.assertEqual(service.locales(), ("zh-CN",))
        self.assertEqual(service.get("a", "zh-CN"), "1")

    def test_case_equivalent_duplicate_is_idempotent(self):
        service = LocalizationService(default_locale="en-US")
        service.register(MessageCatalog(locale="zh-CN", messages={"a": "1"}))
        service.register(MessageCatalog(locale="zh-cn", messages={"a": "1"}))
        self.assertEqual(service.locales(), ("zh-CN",))


class ExtensionTests(unittest.TestCase):
    def test_synthetic_third_locale_without_core_changes(self):
        # Adding a third locale requires only catalog data + registration;
        # the core lookup/fallback algorithm is untouched.
        service = with_builtin_catalogs(default_locale="en-US")
        service.register(
            MessageCatalog(
                locale="th-TH",
                messages={
                    "common.ok": "ตกลง",
                    "common.cancel": "ยกเลิก",
                },
            )
        )
        self.assertIn("th-TH", service.locales())
        self.assertTrue(service.has_locale("th-TH"))
        self.assertEqual(service.get("common.ok", "th-TH"), "ตกลง")
        self.assertEqual(service.get("common.cancel", "th-TH"), "ยกเลิก")
        # Missing key still falls back deterministically to the default.
        self.assertEqual(service.get("common.back", "th-TH"), "Back")

    def test_third_locale_via_from_dict(self):
        service = with_builtin_catalogs(default_locale="en-US")
        service.register(
            MessageCatalog.from_dict(
                {"locale": "ja-JP", "messages": {"common.ok": "OK"}}
            )
        )
        self.assertEqual(service.get("common.ok", "ja-JP"), "OK")

    def test_available_locales_are_reported(self):
        service = with_builtin_catalogs(default_locale="en-US")
        self.assertEqual(service.locales(), ("en-US", "zh-CN"))


class LocaleNormalizationTests(unittest.TestCase):
    def test_normalize_locale_tag(self):
        self.assertEqual(normalize_locale_tag("zh-cn"), "zh-CN")
        self.assertEqual(normalize_locale_tag("ZH-CN"), "zh-CN")
        self.assertEqual(normalize_locale_tag("en-US"), "en-US")
        self.assertEqual(normalize_locale_tag("  en-us  "), "en-US")

    def test_invalid_locale_tag_raises_locale_error(self):
        for bad in ("", "   ", "123", "zh!", "zh_CN", "en--US"):
            with self.assertRaises(LocaleError):
                normalize_locale_tag(bad)

    def test_service_lookup_with_invalid_locale_fails_clearly(self):
        service = with_builtin_catalogs(default_locale="en-US")
        with self.assertRaises(LocaleError):
            service.get("common.ok", "not a locale!")


if __name__ == "__main__":
    unittest.main()
