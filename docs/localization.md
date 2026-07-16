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

The selected Universe, coverage flags, supported/excluded Cell counts, workload
estimate, match counts, and classifications remain canonical language-neutral values.
The UI derives conservative complete/incomplete wording from those fields. Localized
severity or geometry labels are never written back into session-state results.

Prompt 6B applies the same boundary to external references. Canonical
`ExternalResolutionReport`, PBED placement data, and PBED slice results are stored
without translated text. Resolution status, sanitized diagnostic messages, table
headings, authorization wording, bounding-box captions, and placement-visualization
warnings are localized only when rendered. Language switching neither reopens a local
file nor reruns PBED parsing.

Optional AI explanations follow the language selected when Generate is explicitly
pressed. The selected language changes only a controlled system-level output-language
instruction; it does not modify the reviewed `AIReviewPayload` JSON or its privacy
fingerprint. The fixed AI safety instruction remains identical in both languages, and
language switching alone never makes a network request.

Matplotlib uses a separate runtime font check. Japanese mode validates required glyphs
in installed platform fonts and never downloads or bundles font files. If none passes,
the surrounding Streamlit UI remains Japanese, an actionable warning is shown, and
plot-internal labels fall back to English. Canonical geometry and PBED results are not
changed by this presentation fallback.

When adding UI text or a finding rule:

1. Add matching English and Japanese catalog entries.
2. Use structured evidence for dynamic finding text.
3. Keep canonical object names, file names, rule IDs, and severity values unchanged.
4. Extend localization completeness and rendering tests.
