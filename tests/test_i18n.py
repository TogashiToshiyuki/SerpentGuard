"""Tests for the strict two-language localization catalog."""

from __future__ import annotations

import ast
from pathlib import Path
from string import Formatter

import pytest

from serpentguard.i18n import (
    ENGLISH,
    JAPANESE,
    TRANSLATION_CATALOG,
    MissingTranslationError,
    TranslationFormatError,
    translate,
    translation_keys,
)


def test_representative_static_ui_translation() -> None:
    assert translate("run.button", ENGLISH) == "Run check"
    assert translate("run.button", JAPANESE) == "検査を実行"
    assert translate("section.geometry", ENGLISH) == "6. Geometry plot"
    assert translate("section.geometry", JAPANESE) == "6. 幾何形状プロット"
    assert translate("source.mode.uploaded_bundle", ENGLISH) == ("Uploaded file bundle")
    assert translate("source.mode.uploaded_bundle", JAPANESE) == (
        "アップロードしたファイル一式"
    )
    assert translate("reference.status.resolved", JAPANESE) == "解決済み"
    assert translate("ai.level.medium", ENGLISH) == "Medium"
    assert translate("ai.level.medium", JAPANESE) == "中"


def test_all_literal_app_translation_keys_exist_in_english() -> None:
    tree = ast.parse(Path("app.py").read_text(encoding="utf-8"))
    used_keys: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        if not isinstance(node.args[0], ast.Constant) or not isinstance(
            node.args[0].value, str
        ):
            continue
        function_name = node.func.id if isinstance(node.func, ast.Name) else None
        if function_name in {"t", "translate"}:
            used_keys.add(node.args[0].value)

    assert used_keys
    assert used_keys <= translation_keys(ENGLISH)


def test_english_keys_have_japanese_text_and_matching_placeholders() -> None:
    assert translation_keys(ENGLISH) == translation_keys(JAPANESE)
    for key in translation_keys(ENGLISH):
        english_fields = _fields(TRANSLATION_CATALOG[ENGLISH][key])
        japanese_fields = _fields(TRANSLATION_CATALOG[JAPANESE][key])
        assert japanese_fields == english_fields, key


def test_placeholder_interpolation_is_safe_in_both_languages() -> None:
    assert translate("upload.supporting.caption", ENGLISH, count=2).startswith(
        "2 supporting"
    )
    assert "2件" in translate("upload.supporting.caption", JAPANESE, count=2)
    assert "{user_value}" in translate(
        "findings.untranslated",
        JAPANESE,
        message="{user_value}",
    )

    with pytest.raises(TranslationFormatError, match="placeholder mismatch"):
        translate("upload.supporting.caption", ENGLISH)


def test_missing_requested_language_falls_back_to_english(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(TRANSLATION_CATALOG[JAPANESE], "run.button")

    assert translate("run.button", JAPANESE) == "Run check"


def test_completely_unknown_translation_key_raises_clear_error() -> None:
    with pytest.raises(MissingTranslationError, match="missing from English"):
        translate("does.not.exist", JAPANESE)


def _fields(template: str) -> set[str]:
    return {
        field_name
        for _, field_name, _, _ in Formatter().parse(template)
        if field_name is not None
    }
