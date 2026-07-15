"""Small, strict English/Japanese localization catalog for presentation code.

Fallback policy: resolve the requested language first, then English. If English does
not define the key, raise ``MissingTranslationError`` so missing UI text is caught in
development instead of exposing an internal key to users.
"""

from __future__ import annotations

from string import Formatter
from typing import Literal, TypeAlias

SupportedLanguage: TypeAlias = Literal["en", "ja"]

ENGLISH: SupportedLanguage = "en"
JAPANESE: SupportedLanguage = "ja"
DEFAULT_LANGUAGE: SupportedLanguage = ENGLISH
SUPPORTED_LANGUAGES: tuple[SupportedLanguage, ...] = (ENGLISH, JAPANESE)
LANGUAGE_SESSION_KEY = "serpentguard_interface_language"
LANGUAGE_DISPLAY_NAMES: dict[SupportedLanguage, str] = {
    ENGLISH: "English",
    JAPANESE: "日本語",
}


class TranslationError(Exception):
    """Base exception for localization catalog and formatting errors."""


class MissingTranslationError(TranslationError, KeyError):
    """Raised when a key is absent from both the requested language and English."""


class TranslationFormatError(TranslationError, ValueError):
    """Raised when placeholders are unsafe, missing, or unexpectedly supplied."""


TRANSLATION_CATALOG: dict[SupportedLanguage, dict[str, str]] = {
    ENGLISH: {
        "language.selector": "Language",
        "page.title": "SerpentGuard",
        "app.title": "SerpentGuard",
        "app.warning": (
            "Experimental tool: SerpentGuard covers only a limited syntax subset "
            "and does not establish geometric, physical, reactor-safety, or "
            "criticality-safety validity. Review every finding independently."
        ),
        "app.local_notice": (
            "Analysis is local. Uploaded input is parsed in this Streamlit process "
            "and is not sent to an AI service."
        ),
        "section.upload": "1. Upload Serpent input",
        "section.purpose": "2. Analysis purpose",
        "section.run": "3. Run check",
        "section.summary": "4. Summary counts",
        "section.findings": "5. Findings table",
        "section.geometry": "6. Geometry plot",
        "section.ai": "7. AI explanation",
        "upload.main.label": "Main input file",
        "upload.main.help": (
            "Upload one UTF-8 Serpent input file for deterministic local analysis."
        ),
        "upload.supporting.label": "Supporting files (optional)",
        "upload.supporting.help": (
            "These files are accepted for workflow preparation only. Include "
            "resolution is not implemented, so they are not opened or analyzed."
        ),
        "upload.supporting.caption": (
            "{count} supporting file(s) selected. They will not be opened in this "
            "milestone."
        ),
        "purpose.label": "Purpose (optional)",
        "purpose.placeholder": (
            "For example: preflight review before a local Serpent run"
        ),
        "purpose.help": (
            "This note stays local and does not change deterministic findings in "
            "this milestone."
        ),
        "run.button": "Run check",
        "run.help": "Upload a main input file to enable deterministic analysis.",
        "run.spinner": "Parsing and running deterministic checks...",
        "summary.empty": (
            "Upload a main input file and press Run check to generate a summary."
        ),
        "summary.invalid_state": (
            "The stored analysis result is invalid. Please upload the file again."
        ),
        "summary.parser_unrecoverable": (
            "The uploaded file could not be parsed. Confirm that it is a readable "
            "UTF-8 text file, then run the check again."
        ),
        "summary.parser_recoverable": (
            "Parsing completed with recoverable syntax errors. Parsed counts may be "
            "incomplete; review SG011 and SG015 findings below."
        ),
        "metric.surfaces": "Surfaces",
        "metric.cells": "Cells",
        "metric.materials": "Materials",
        "metric.unknown_cards": "Unknown cards",
        "severity.ERROR": "ERROR",
        "severity.WARNING": "WARNING",
        "severity.REVIEW": "REVIEW",
        "severity.INFO": "INFO",
        "findings.before_run": "Findings will appear after Run check is pressed.",
        "findings.filter.severity": "Severity",
        "findings.filter.rule_id": "Rule ID",
        "findings.count": "Showing {shown} of {total} findings.",
        "findings.evidence_expander": "Evidence {number}: {rule_id} — {object_label}",
        "findings.no_filter_matches": "No findings match the selected filters.",
        "findings.none": (
            "No deterministic findings were produced for the supported subset."
        ),
        "findings.untranslated": "[Translation unavailable] {message}",
        "debug.expander": "Parsed model JSON (debugging)",
        "debug.caption": "Raw card text is omitted from this debugging view.",
        "geometry.before_run": (
            "Run the deterministic input check before configuring geometry sampling."
        ),
        "geometry.unavailable": (
            "Geometry sampling is unavailable because the stored parsed model is "
            "invalid or parsing failed unrecoverably."
        ),
        "geometry.intro": (
            "Confirm an XY sampling range, z coordinate, and square-grid resolution. "
            "Only supported cyl and sqc surfaces are evaluated."
        ),
        "geometry.warning.sampling": (
            "This check is sampling-based; it does not prove that the geometry is "
            "valid."
        ),
        "geometry.warning.narrow": (
            "Narrow gaps or overlaps between grid points may be missed."
        ),
        "geometry.warning.plotter": (
            "This check does not replace the Serpent geometry plotter."
        ),
        "geometry.form.z": "z coordinate",
        "geometry.form.xmin": "xmin",
        "geometry.form.xmax": "xmax",
        "geometry.form.ymin": "ymin",
        "geometry.form.ymax": "ymax",
        "geometry.form.resolution": "Grid resolution per axis",
        "geometry.form.resolution_help": (
            "The sampler evaluates resolution × resolution evenly spaced points, "
            "including the range endpoints."
        ),
        "geometry.form.tolerance": "Boundary tolerance",
        "geometry.form.tolerance_help": (
            "Points within this absolute signed-distance tolerance of a supported "
            "surface are classified as indeterminate."
        ),
        "geometry.form.submit": "Confirm range and sample geometry",
        "geometry.spinner": "Sampling the supported XY geometry...",
        "geometry.config_error": "Geometry sampling configuration error: {message}",
        "geometry.metric.overlap": "Overlap candidates",
        "geometry.metric.undefined": "Undefined candidates",
        "geometry.metric.normal": "Normal points",
        "geometry.metric.indeterminate": "Indeterminate points",
        "geometry.summary": (
            "Range: x=[{xmin}, {xmax}], y=[{ymin}, {ymax}], z={z}; grid: "
            "{resolution} × {resolution} ({total} points); boundary tolerance: "
            "{tolerance}."
        ),
        "geometry.cells": ("Evaluated cells: {included}; excluded cells: {excluded}."),
        "geometry.no_included_cells": (
            "No cell could be evaluated safely. All sample points are indeterminate."
        ),
        "geometry.plot.title": "Supported-cell classification at z={z}",
        "geometry.classification.undefined": "Undefined candidate",
        "geometry.classification.normal": "Normal",
        "geometry.classification.overlap": "Overlap candidate",
        "geometry.classification.indeterminate": "Indeterminate",
        "geometry.representatives.overlap": "Representative overlap candidates",
        "geometry.representatives.undefined": "Representative undefined candidates",
        "geometry.representatives.none": "No representative candidates to display.",
        "geometry.excluded.heading": "Excluded cells",
        "geometry.excluded.none": "No cells were excluded from sampling.",
        "geometry.table.x": "x",
        "geometry.table.y": "y",
        "geometry.table.cells": "Involved cells",
        "geometry.table.cell": "Cell",
        "geometry.table.file": "File",
        "geometry.table.line": "Line",
        "geometry.table.reason": "Reason",
        "geometry.reason.separator": "; ",
        "geometry.exclusion.unsupported_surface_type": (
            "Surface '{surface}' uses unsupported type '{surface_type}'."
        ),
        "geometry.exclusion.undefined_surface": "Surface '{surface}' is undefined.",
        "geometry.exclusion.ambiguous_surface": (
            "Surface '{surface}' has multiple definitions."
        ),
        "geometry.exclusion.invalid_surface_parameters": (
            "Surface '{surface}' has invalid parameters for type '{surface_type}'."
        ),
        "geometry.exclusion.unsupported_cell_syntax": (
            "The cell syntax is outside the supported geometry subset."
        ),
        "geometry.exclusion.empty_region": (
            "The cell has no evaluable region expression."
        ),
        "ai.placeholder": (
            "AI review is optional and has not been enabled in this milestone."
        ),
        "table.severity": "Severity",
        "table.rule_id": "Rule ID",
        "table.file": "File",
        "table.line": "Line",
        "table.object": "Object",
        "table.message": "Message",
        "object.surface": "surface",
        "object.cell": "cell",
        "object.material": "material",
        "object.card": "card",
        "object.comment": "comment",
        "object.input": "input",
        "finding.SG001.title": "Duplicate surface",
        "finding.SG001.message": (
            "Surface '{name}' is defined {definition_count} times in the parsed model."
        ),
        "finding.SG002.title": "Duplicate cell",
        "finding.SG002.message": (
            "Cell '{name}' is defined {definition_count} times in the parsed model."
        ),
        "finding.SG003.title": "Duplicate material",
        "finding.SG003.message": (
            "Material '{name}' is defined {definition_count} times in the parsed model."
        ),
        "finding.SG004.title": "Undefined surface reference",
        "finding.SG004.message": (
            "Cell '{cell}' references surface '{reference}', but no supported "
            "definition with that exact name was parsed."
        ),
        "finding.SG005.title": "Undefined material reference",
        "finding.SG005.message": (
            "Cell '{cell}' references material '{reference}', but no supported "
            "definition with that exact name was parsed."
        ),
        "finding.SG006.title": "Unused surface",
        "finding.SG006.message": (
            "Surface '{name}' is not referenced by any supported parsed cell."
        ),
        "finding.SG007.title": "Unused material",
        "finding.SG007.message": (
            "Material '{name}' is not referenced by any supported parsed cell."
        ),
        "finding.SG008.title": "Contradictory signed surface",
        "finding.SG008.message": (
            "Cell '{cell}' uses both signs of surface '{surface}' within intersection "
            "term {term} (positive: {positive_count}, negative: {negative_count})."
        ),
        "finding.SG009.title": "Duplicate region condition",
        "finding.SG009.message": (
            "Cell '{cell}' repeats signed condition '{condition}' {occurrences} times "
            "within intersection term {term}."
        ),
        "finding.SG010.title": "Excessively complex region expression",
        "finding.SG010.message": (
            "Cell '{cell}' exceeds the configured syntactic complexity threshold: "
            "{details}."
        ),
        "finding.SG010.detail.references": (
            "surface references {actual} (limit {limit})"
        ),
        "finding.SG010.detail.unions": "union operators {actual} (limit {limit})",
        "finding.SG011.title": "Unterminated block comment",
        "finding.SG011.message": (
            "The block comment beginning on line {opening_line} is not terminated "
            "before the end of the file."
        ),
        "finding.SG014.title": "Unsupported card",
        "finding.SG014.message": (
            "Card '{keyword}' is outside the implemented subset and was retained "
            "without interpretation."
        ),
        "finding.SG015.title": "Parser recovery used",
        "finding.SG015.message.PARSER_IO": "The local input file could not be read.",
        "finding.SG015.message.PARSER_ENCODING": (
            "The local input file is not valid UTF-8."
        ),
        "finding.SG015.message.PARSER001": (
            "A malformed surface card was retained without interpretation and "
            "parsing continued."
        ),
        "finding.SG015.message.PARSER002": (
            "A malformed cell card was retained without interpretation and parsing "
            "continued."
        ),
        "finding.SG015.message.PARSER003": (
            "A malformed material card was retained without interpretation and "
            "parsing continued."
        ),
    },
    JAPANESE: {
        "language.selector": "表示言語",
        "page.title": "SerpentGuard",
        "app.title": "SerpentGuard",
        "app.warning": (
            "実験的ツールです．SerpentGuardが対応する構文は限定的であり，幾何学的・"
            "物理的な妥当性，原子炉安全性，臨界安全性を保証しません．すべての検出事項を"
            "個別に確認してください．"
        ),
        "app.local_notice": (
            "解析はローカルで実行されます．アップロードした入力はこのStreamlitプロセス"
            "内で解析され，AIサービスには送信されません．"
        ),
        "section.upload": "1. Serpent入力のアップロード",
        "section.purpose": "2. 解析目的",
        "section.run": "3. 検査を実行",
        "section.summary": "4. 集計",
        "section.findings": "5. 検出事項一覧",
        "section.geometry": "6. 幾何形状プロット",
        "section.ai": "7. AIによる説明",
        "upload.main.label": "メイン入力ファイル",
        "upload.main.help": (
            "決定論的なローカル解析を行うUTF-8形式のSerpent入力ファイルを1つ"
            "アップロードしてください．"
        ),
        "upload.supporting.label": "補助ファイル（任意）",
        "upload.supporting.help": (
            "将来のinclude解決に備えて選択できます．このマイルストーンではinclude解決を"
            "実装していないため，ファイルの内容は開かず，解析にも使用しません．"
        ),
        "upload.supporting.caption": (
            "補助ファイルが{count}件選択されています．このマイルストーンでは内容を"
            "開きません．"
        ),
        "purpose.label": "解析目的（任意）",
        "purpose.placeholder": "例：ローカルでSerpentを実行する前の事前確認",
        "purpose.help": (
            "このメモはローカルに保持され，このマイルストーンの決定論的な検出結果には"
            "影響しません．"
        ),
        "run.button": "検査を実行",
        "run.help": (
            "メイン入力ファイルをアップロードすると，決定論的解析を実行できます．"
        ),
        "run.spinner": "構文解析と決定論的検査を実行しています...",
        "summary.empty": (
            "メイン入力ファイルをアップロードし，「検査を実行」を押すと集計を表示します．"
        ),
        "summary.invalid_state": (
            "保存されている解析結果が不正です．ファイルを再度アップロードしてください．"
        ),
        "summary.parser_unrecoverable": (
            "アップロードしたファイルを解析できませんでした．読み取り可能なUTF-8テキスト"
            "であることを確認し，もう一度検査を実行してください．"
        ),
        "summary.parser_recoverable": (
            "回復可能な構文エラーがありました．集計が不完全な可能性があります．下の"
            "SG011およびSG015の検出事項を確認してください．"
        ),
        "metric.surfaces": "Surface",
        "metric.cells": "Cell",
        "metric.materials": "Material",
        "metric.unknown_cards": "未対応カード",
        "severity.ERROR": "エラー",
        "severity.WARNING": "警告",
        "severity.REVIEW": "要確認",
        "severity.INFO": "情報",
        "findings.before_run": (
            "「検査を実行」を押すと，ここに検出事項が表示されます．"
        ),
        "findings.filter.severity": "重大度",
        "findings.filter.rule_id": "ルールID",
        "findings.count": "全{total}件中{shown}件の検出事項を表示しています．",
        "findings.evidence_expander": ("根拠情報 {number}：{rule_id} — {object_label}"),
        "findings.no_filter_matches": ("選択した条件に一致する検出事項はありません．"),
        "findings.none": "対応範囲内で決定論的な検出事項はありませんでした．",
        "findings.untranslated": "[日本語訳未対応] {message}",
        "debug.expander": "解析済みモデルJSON（デバッグ用）",
        "debug.caption": ("このデバッグ表示では，カードの生テキストを除外しています．"),
        "geometry.before_run": (
            "幾何形状サンプリングを設定する前に，決定論的な入力検査を実行してください．"
        ),
        "geometry.unavailable": (
            "保存された解析済みモデルが不正であるか，構文解析を継続できなかったため，"
            "幾何形状サンプリングを実行できません．"
        ),
        "geometry.intro": (
            "XYサンプリング範囲，z座標，正方格子の解像度を確認してください．"
            "評価対象は対応済みのcylおよびsqc Surfaceのみです．"
        ),
        "geometry.warning.sampling": (
            "この検査はサンプリングに基づくため，幾何形状の妥当性を証明するものでは"
            "ありません．"
        ),
        "geometry.warning.narrow": (
            "格子点間にある幅の狭い隙間や重なりを見落とす可能性があります．"
        ),
        "geometry.warning.plotter": (
            "この検査はSerpentのgeometry plotterを置き換えるものではありません．"
        ),
        "geometry.form.z": "z座標",
        "geometry.form.xmin": "xmin",
        "geometry.form.xmax": "xmax",
        "geometry.form.ymin": "ymin",
        "geometry.form.ymax": "ymax",
        "geometry.form.resolution": "各軸の格子解像度",
        "geometry.form.resolution_help": (
            "範囲の端点を含む等間隔の格子点を，各軸について指定した個数だけ評価します．"
        ),
        "geometry.form.tolerance": "境界許容差",
        "geometry.form.tolerance_help": (
            "対応済みSurfaceからの符号付き距離の絶対値がこの値以下の点は，判定不能として"
            "分類します．"
        ),
        "geometry.form.submit": "範囲を確認して幾何形状をサンプリング",
        "geometry.spinner": "対応範囲内のXY幾何形状をサンプリングしています...",
        "geometry.config_error": "幾何形状サンプリングの設定エラー：{message}",
        "geometry.metric.overlap": "重なり候補",
        "geometry.metric.undefined": "未定義領域候補",
        "geometry.metric.normal": "正常点",
        "geometry.metric.indeterminate": "判定不能点",
        "geometry.summary": (
            "範囲：x=[{xmin}, {xmax}]，y=[{ymin}, {ymax}]，z={z}；格子："
            "{resolution} × {resolution}（{total}点）；境界許容差：{tolerance}．"
        ),
        "geometry.cells": "評価対象Cell：{included}；除外Cell：{excluded}．",
        "geometry.no_included_cells": (
            "安全に評価できるCellがありません．すべてのサンプリング点を判定不能としました．"
        ),
        "geometry.plot.title": "z={z}における対応済みCellの分類",
        "geometry.classification.undefined": "未定義領域候補",
        "geometry.classification.normal": "正常",
        "geometry.classification.overlap": "重なり候補",
        "geometry.classification.indeterminate": "判定不能",
        "geometry.representatives.overlap": "重なり候補の代表点",
        "geometry.representatives.undefined": "未定義領域候補の代表点",
        "geometry.representatives.none": "表示できる代表候補点はありません．",
        "geometry.excluded.heading": "除外したCell",
        "geometry.excluded.none": "サンプリングから除外したCellはありません．",
        "geometry.table.x": "x",
        "geometry.table.y": "y",
        "geometry.table.cells": "関係するCell",
        "geometry.table.cell": "Cell",
        "geometry.table.file": "ファイル",
        "geometry.table.line": "行",
        "geometry.table.reason": "除外理由",
        "geometry.reason.separator": "；",
        "geometry.exclusion.unsupported_surface_type": (
            "Surface「{surface}」の型「{surface_type}」には対応していません．"
        ),
        "geometry.exclusion.undefined_surface": (
            "Surface「{surface}」が定義されていません．"
        ),
        "geometry.exclusion.ambiguous_surface": (
            "Surface「{surface}」が複数回定義されています．"
        ),
        "geometry.exclusion.invalid_surface_parameters": (
            "Surface「{surface}」の型「{surface_type}」に対するパラメータが不正です．"
        ),
        "geometry.exclusion.unsupported_cell_syntax": (
            "Cellの構文が幾何形状評価の対応範囲外です．"
        ),
        "geometry.exclusion.empty_region": ("Cellに評価可能な領域式がありません．"),
        "ai.placeholder": (
            "AIレビューは任意機能であり，このマイルストーンでは有効化されていません．"
        ),
        "table.severity": "重大度",
        "table.rule_id": "ルールID",
        "table.file": "ファイル",
        "table.line": "行",
        "table.object": "対象",
        "table.message": "メッセージ",
        "object.surface": "Surface",
        "object.cell": "Cell",
        "object.material": "Material",
        "object.card": "未対応カード",
        "object.comment": "コメント",
        "object.input": "入力",
        "finding.SG001.title": "Surfaceの重複定義",
        "finding.SG001.message": (
            "解析済みモデル内でSurface「{name}」が{definition_count}回定義されています．"
        ),
        "finding.SG002.title": "Cellの重複定義",
        "finding.SG002.message": (
            "解析済みモデル内でCell「{name}」が{definition_count}回定義されています．"
        ),
        "finding.SG003.title": "Materialの重複定義",
        "finding.SG003.message": (
            "解析済みモデル内でMaterial「{name}」が{definition_count}回定義されています．"
        ),
        "finding.SG004.title": "未定義Surface参照",
        "finding.SG004.message": (
            "Cell「{cell}」はSurface「{reference}」を参照していますが，同名の対応済み"
            "Surface定義を解析できませんでした．"
        ),
        "finding.SG005.title": "未定義Material参照",
        "finding.SG005.message": (
            "Cell「{cell}」はMaterial「{reference}」を参照していますが，同名の対応済み"
            "Material定義を解析できませんでした．"
        ),
        "finding.SG006.title": "未使用Surface",
        "finding.SG006.message": (
            "Surface「{name}」は，対応済みの解析対象Cellから参照されていません．"
        ),
        "finding.SG007.title": "未使用Material",
        "finding.SG007.message": (
            "Material「{name}」は，対応済みの解析対象Cellで使用されていません．"
        ),
        "finding.SG008.title": "Surface符号条件の矛盾",
        "finding.SG008.message": (
            "Cell「{cell}」のintersection項{term}に，Surface「{surface}」の正側条件"
            "{positive_count}件と負側条件{negative_count}件が同時に含まれています．"
        ),
        "finding.SG009.title": "領域条件の重複",
        "finding.SG009.message": (
            "Cell「{cell}」のintersection項{term}で，符号付き条件「{condition}」が"
            "{occurrences}回重複しています．"
        ),
        "finding.SG010.title": "過度に複雑な領域式",
        "finding.SG010.message": (
            "Cell「{cell}」は設定された構文複雑度のしきい値を超えています：{details}．"
        ),
        "finding.SG010.detail.references": ("Surface参照数{actual}（上限{limit}）"),
        "finding.SG010.detail.unions": "union演算子数{actual}（上限{limit}）",
        "finding.SG011.title": "未終了のブロックコメント",
        "finding.SG011.message": (
            "{opening_line}行目から始まるブロックコメントが，ファイル末尾までに終了して"
            "いません．"
        ),
        "finding.SG014.title": "未対応カード",
        "finding.SG014.message": (
            "カード「{keyword}」は現在の対応範囲外であるため，内容を解釈せず保持しました．"
        ),
        "finding.SG015.title": "パーサーリカバリ",
        "finding.SG015.message.PARSER_IO": (
            "ローカル入力ファイルを読み取れませんでした．"
        ),
        "finding.SG015.message.PARSER_ENCODING": (
            "ローカル入力ファイルが有効なUTF-8ではありません．"
        ),
        "finding.SG015.message.PARSER001": (
            "不正なSurfaceカードを未解釈のまま保持し，構文解析を継続しました．"
        ),
        "finding.SG015.message.PARSER002": (
            "不正なCellカードを未解釈のまま保持し，構文解析を継続しました．"
        ),
        "finding.SG015.message.PARSER003": (
            "不正なMaterialカードを未解釈のまま保持し，構文解析を継続しました．"
        ),
    },
}


def translate(key: str, language: SupportedLanguage, **kwargs: object) -> str:
    """Translate one key with strict formatting and English fallback."""
    if language not in SUPPORTED_LANGUAGES:
        raise TranslationError(f"Unsupported language: {language!r}")

    template = TRANSLATION_CATALOG[language].get(key)
    if template is None:
        template = TRANSLATION_CATALOG[ENGLISH].get(key)
    if template is None:
        raise MissingTranslationError(
            f"Translation key {key!r} is missing from English and {language}."
        )
    return _safe_format(key, template, kwargs)


def language_display_name(language: SupportedLanguage) -> str:
    """Return the stable native label used by the language selector."""
    try:
        return LANGUAGE_DISPLAY_NAMES[language]
    except KeyError as error:
        raise TranslationError(f"Unsupported language: {language!r}") from error


def translation_keys(language: SupportedLanguage) -> frozenset[str]:
    """Expose catalog keys for completeness tests and development checks."""
    if language not in SUPPORTED_LANGUAGES:
        raise TranslationError(f"Unsupported language: {language!r}")
    return frozenset(TRANSLATION_CATALOG[language])


def _safe_format(key: str, template: str, kwargs: dict[str, object]) -> str:
    fields: set[str] = set()
    try:
        parsed_parts = list(Formatter().parse(template))
    except ValueError as error:
        raise TranslationFormatError(
            f"Translation {key!r} contains invalid braces."
        ) from error

    for _, field_name, format_spec, conversion in parsed_parts:
        if field_name is None:
            continue
        if not field_name.isidentifier() or format_spec or conversion:
            raise TranslationFormatError(
                f"Translation {key!r} uses an unsafe placeholder {field_name!r}."
            )
        fields.add(field_name)

    supplied = set(kwargs)
    missing = fields - supplied
    unexpected = supplied - fields
    if missing or unexpected:
        raise TranslationFormatError(
            f"Translation {key!r} placeholder mismatch; "
            f"missing={sorted(missing)}, unexpected={sorted(unexpected)}."
        )

    safe_values = {name: str(kwargs[name]) for name in fields}
    return template.format_map(safe_values)
