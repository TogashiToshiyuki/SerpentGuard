# Localization architecture

The local Streamlit interface supports exactly English (`en`) and Japanese (`ja`).
English is the default. The selected language is stored under the stable Streamlit
session-state key `serpentguard_interface_language`.

## Boundaries

- `src/serpentguard/i18n.py` owns supported-language constants, native language names,
  the translation catalog, strict placeholder formatting, and fallback behavior.
- `src/serpentguard/ui.py` renders canonical `Finding` data for presentation. Japanese
  rule messages are reconstructed from rule IDs and structured evidence, not by
  rewriting English prose.
- `app.py` selects translations and renders them. It stores only canonical
  `ParsedModel`, `AnalysisReport`, and language-neutral `GeometrySamplingResult`
  objects in session state.
- Parsing, symbol-table analysis, CLI text, JSON reports, rule IDs, and severity values
  are language-independent.

Severity and rule filters always retain canonical values such as `ERROR` and `SG004`.
Streamlit uses display formatting to show labels such as `エラー` without placing the
translated label into analysis or filter logic.

## Fallback and development policy

Translation lookup first checks the requested language and then English. If the key is
also absent from English, `MissingTranslationError` is raised so the omission is caught
during development. Templates accept only simple named placeholders; missing, extra,
or unsafe placeholders raise `TranslationFormatError`.

All active finding rules have explicit Japanese presentation. If a future rule lacks
the structured evidence needed for safe Japanese rendering, the UI shows its original
English message with a subtle `[日本語訳未対応]` marker. The canonical `Finding` is never
modified.

Geometry controls, warnings, classifications, representative-point tables, and
excluded-cell reasons are localized in the presentation layer. Surface, Cell, file,
and user-defined object names remain canonical. Switching language redraws an existing
geometry result without rerunning the sampler.

When adding UI text or a finding rule:

1. Add matching English and Japanese catalog entries.
2. Use structured evidence for dynamic finding text.
3. Keep canonical object names, file names, rule IDs, and severity values unchanged.
4. Extend localization completeness and rendering tests.
