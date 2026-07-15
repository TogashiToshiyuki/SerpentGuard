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
        "geometry.no_universes": (
            "No universe containing a supported parsed Cell is available for "
            "geometry sampling."
        ),
        "geometry.intro": (
            "Select one universe and confirm an XY range and square-grid resolution. "
            "Only supported cyl and sqc surfaces are evaluated."
        ),
        "geometry.local_coordinates": (
            "The selected universe is evaluated only in its own local coordinate "
            "system. fill, pin, lat, transformations, and nested universes are not "
            "expanded."
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
        "geometry.form.universe": "Universe",
        "geometry.universe.defaulted": (
            "Universe 0 was not found. The initial deterministic selection is "
            "universe '{universe}'."
        ),
        "geometry.form.z": "z coordinate",
        "geometry.form.z_help": (
            "Inactive for the current subset: cyl and sqc extend indefinitely in z. "
            "The stored value is reserved for future surface support."
        ),
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
        "geometry.workload.help": (
            "Requests above the code-configured workload limit of {limit} estimated "
            "operations are rejected before grid allocation."
        ),
        "geometry.spinner": "Sampling the supported XY geometry...",
        "geometry.config_error": "Geometry sampling configuration error: {message}",
        "geometry.workload_error": (
            "Sampling was rejected by the workload guard: {operations} estimated "
            "operations exceeds the limit {limit} (grid points: {points}, evaluated "
            "cells: {cells}, signed references: {references}). Reduce the resolution "
            "or simplify the selected universe."
        ),
        "geometry.metric.overlap": "Overlap candidates",
        "geometry.metric.overlap_incomplete": "Supported-subset overlaps",
        "geometry.metric.undefined": "Undefined candidates",
        "geometry.metric.normal": "Normal points",
        "geometry.metric.normal_incomplete": "Single supported-cell matches",
        "geometry.metric.indeterminate": "Indeterminate points",
        "geometry.summary": (
            "Selected universe: {universe}; range: x=[{xmin}, {xmax}], "
            "y=[{ymin}, {ymax}]; grid: {resolution} × {resolution} ({total} points); "
            "boundary tolerance: {tolerance}; stored inactive z: {z}."
        ),
        "geometry.cells": (
            "Evaluated cells: {included}; excluded cells: {excluded}; signed surface "
            "references: {references}; estimated workload: {workload}."
        ),
        "geometry.universe.selected": (
            "Universe '{universe}' was sampled independently in its local coordinate "
            "system."
        ),
        "geometry.coverage.complete": (
            "All parsed Cells in the selected universe are supported; undefined-"
            "region candidate detection is enabled."
        ),
        "geometry.coverage.incomplete": (
            "Incomplete selected universe: {excluded} Cell definition(s) were "
            "excluded. Results describe only the supported subset and do not prove "
            "complete coverage."
        ),
        "geometry.undefined.disabled": (
            "Undefined-region detection is disabled because excluded Cells may cover "
            "zero-match points. {count} such point(s) are classified as "
            "indeterminate."
        ),
        "geometry.duplicate.warning": (
            "Duplicate Cell definitions in this universe were all excluded. SG002 "
            "remains the canonical static-analysis finding."
        ),
        "geometry.no_included_cells": (
            "No cell could be evaluated safely. All sample points are indeterminate."
        ),
        "geometry.view.geometry": "Geometry view",
        "geometry.view.diagnostic": "Diagnostic view",
        "geometry.color_by.label": "Geometry colors",
        "geometry.color_by.material": "Color by material",
        "geometry.color_by.cell": "Color by cell",
        "geometry.color.serpent_rgb": "Use Serpent RGB colors",
        "geometry.color.application_note": (
            "Application colors are deterministic but may differ from Serpent's plot."
        ),
        "geometry.font.warning": (
            "No Japanese-capable Matplotlib font was found. Plot text is shown in "
            "English to prevent missing glyphs. Install Noto Sans CJK JP (Linux) or "
            "enable Yu Gothic/Meiryo (Windows), then restart the application."
        ),
        "geometry.plot.geometry_title": "Universe {universe}: limited geometry view",
        "geometry.plot.diagnostic_title": (
            "Universe {universe}: diagnostic classification view"
        ),
        "geometry.category.outside": "Outside",
        "geometry.category.void": "Void",
        "geometry.category.unsupported": "Unsupported / incomplete",
        "geometry.category.indeterminate": "Indeterminate",
        "geometry.category.undefined": "Undefined region",
        "geometry.classification.incomplete": "Incomplete / unsupported",
        "geometry.classification.boundary": "Boundary-indeterminate",
        "geometry.diagnostic.caption": (
            "This diagnostic map shows preflight classifications, not material or "
            "Cell identity."
        ),
        "geometry.plot.title": (
            "Universe {universe}: supported-cell XY classification (z-invariant subset)"
        ),
        "geometry.classification.undefined": "Undefined candidate",
        "geometry.classification.undefined_disabled": "Undefined disabled",
        "geometry.classification.normal": "Normal",
        "geometry.classification.normal_incomplete": "One supported-cell match",
        "geometry.classification.overlap": "Overlap candidate",
        "geometry.classification.overlap_incomplete": "Supported-subset overlap",
        "geometry.classification.indeterminate": "Indeterminate",
        "geometry.representatives.overlap": "Representative overlap candidates",
        "geometry.representatives.overlap_incomplete": (
            "Representative supported-subset overlaps"
        ),
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
        "geometry.exclusion.duplicate_cell_name": (
            "Cell name '{cell}' has {count} definitions in the selected universe; "
            "every definition was excluded."
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
        "geometry.no_universes": (
            "対応済みとして解析されたCellを含むUniverseがないため，幾何形状サンプリング"
            "を実行できません．"
        ),
        "geometry.intro": (
            "Universeを1つ選択し，XYサンプリング範囲と正方格子の解像度を確認して"
            "ください．評価対象は対応済みのcylおよびsqc Surfaceのみです．"
        ),
        "geometry.local_coordinates": (
            "選択したUniverseを，そのローカル座標系内だけで評価します．fill，pin，lat，"
            "座標変換，入れ子のUniverseは展開しません．"
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
        "geometry.form.universe": "Universe",
        "geometry.universe.defaulted": (
            "Universe 0が見つからないため，決定論的な初期選択をUniverse「{universe}」"
            "としました．"
        ),
        "geometry.form.z": "z座標",
        "geometry.form.z_help": (
            "現在の対応範囲では無効です．cylとsqcはz方向に無限に延びるため，保存された"
            "値は結果に影響せず，将来のSurface対応用に予約されています．"
        ),
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
        "geometry.workload.help": (
            "推定演算回数がコードで設定された上限{limit}を超える要求は，格子を確保する前"
            "に拒否します．"
        ),
        "geometry.spinner": "対応範囲内のXY幾何形状をサンプリングしています...",
        "geometry.config_error": "幾何形状サンプリングの設定エラー：{message}",
        "geometry.workload_error": (
            "計算量ガードによりサンプリングを拒否しました．推定演算回数{operations}が"
            "上限{limit}を超えています（格子点：{points}，評価対象Cell：{cells}，符号付き"
            "Surface参照：{references}）．解像度を下げるか，選択したUniverseを簡略化して"
            "ください．"
        ),
        "geometry.metric.overlap": "重なり候補",
        "geometry.metric.overlap_incomplete": "対応済み部分集合の重なり",
        "geometry.metric.undefined": "未定義領域候補",
        "geometry.metric.normal": "正常点",
        "geometry.metric.normal_incomplete": "対応済みCellが1つ一致した点",
        "geometry.metric.indeterminate": "判定不能点",
        "geometry.summary": (
            "選択したUniverse：{universe}；範囲：x=[{xmin}, {xmax}]，"
            "y=[{ymin}, {ymax}]；格子：{resolution} × {resolution}（{total}点）；"
            "境界許容差：{tolerance}；保存された無効なz値：{z}．"
        ),
        "geometry.cells": (
            "評価対象Cell：{included}；除外Cell：{excluded}；符号付きSurface参照："
            "{references}；推定演算回数：{workload}．"
        ),
        "geometry.universe.selected": (
            "Universe「{universe}」を独立したローカル座標系でサンプリングしました．"
        ),
        "geometry.coverage.complete": (
            "選択したUniverse内の解析済みCellはすべて対応済みです．未定義領域候補の検出"
            "を有効にしています．"
        ),
        "geometry.coverage.incomplete": (
            "選択したUniverseは不完全です．{excluded}件のCell定義を除外しました．結果は"
            "対応済み部分集合のみを表し，Universe全体の被覆を保証しません．"
        ),
        "geometry.undefined.disabled": (
            "除外したCellが一致数0の点を占める可能性があるため，未定義領域の検出を無効"
            "にしました．該当する{count}点を判定不能として分類します．"
        ),
        "geometry.duplicate.warning": (
            "このUniverse内で重複したCell定義はすべて除外しました．静的解析ではSG002が"
            "引き続き正式な検出事項です．"
        ),
        "geometry.no_included_cells": (
            "安全に評価できるCellがありません．すべてのサンプリング点を判定不能としました．"
        ),
        "geometry.view.geometry": "体系図",
        "geometry.view.diagnostic": "診断図",
        "geometry.color_by.label": "体系図の色分け",
        "geometry.color_by.material": "Material別に色分け",
        "geometry.color_by.cell": "Cell別に色分け",
        "geometry.color.serpent_rgb": "SerpentのRGB色を使用",
        "geometry.color.application_note": (
            "アプリケーション色は決定的に割り当てますが，Serpentのplotとは異なる場合があります．"
        ),
        "geometry.font.warning": (
            "Matplotlibで利用できる日本語フォントが見つかりません．文字化けを防ぐため，"
            "プロット内の文字だけ英語で表示します．LinuxではNoto Sans CJK JPを導入し，"
            "WindowsではYu GothicまたはMeiryoを有効にしてから，"
            "アプリを再起動してください．"
        ),
        "geometry.plot.geometry_title": "Universe {universe}：限定的な体系図",
        "geometry.plot.diagnostic_title": "Universe {universe}：診断分類図",
        "geometry.category.outside": "外部領域",
        "geometry.category.void": "Void",
        "geometry.category.unsupported": "未対応／不完全領域",
        "geometry.category.indeterminate": "判定不能",
        "geometry.category.undefined": "未定義領域",
        "geometry.classification.incomplete": "不完全／未対応",
        "geometry.classification.boundary": "境界上の判定不能",
        "geometry.diagnostic.caption": (
            "この診断図は検査分類を示すものであり，MaterialやCellの識別図ではありません．"
        ),
        "geometry.plot.title": (
            "Universe {universe}：対応済みCellのXY分類（z不変の対応範囲）"
        ),
        "geometry.classification.undefined": "未定義領域候補",
        "geometry.classification.undefined_disabled": "未定義領域検出は無効",
        "geometry.classification.normal": "正常",
        "geometry.classification.normal_incomplete": "対応済みCellが1つ一致",
        "geometry.classification.overlap": "重なり候補",
        "geometry.classification.overlap_incomplete": "対応済み部分集合の重なり",
        "geometry.classification.indeterminate": "判定不能",
        "geometry.representatives.overlap": "重なり候補の代表点",
        "geometry.representatives.overlap_incomplete": (
            "対応済み部分集合における重なりの代表点"
        ),
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
        "geometry.exclusion.duplicate_cell_name": (
            "選択したUniverse内でCell名「{cell}」が{count}回定義されているため，すべての"
            "定義を除外しました．"
        ),
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

# Prompt 6B keeps the large established catalog stable while extending it as one
# explicit, centralized block. Existing keys listed here are intentional wording
# updates now that supporting files are resolved instead of ignored.
_EXTERNAL_REFERENCE_TRANSLATIONS: dict[SupportedLanguage, dict[str, str]] = {
    ENGLISH: {
        "section.upload": "1. Select input source",
        "source.mode.label": "Input mode",
        "source.mode.uploaded_bundle": "Uploaded file bundle",
        "source.mode.local_project": "Authorized local project",
        "upload.supporting.help": (
            "Upload only PBED files explicitly referenced by the main input. "
            "SerpentGuard resolves them by normalized relative name; other files "
            "remain unused."
        ),
        "upload.supporting.caption": (
            "{count} supporting file(s) selected. Referenced PBED files will be read "
            "only after Run check is pressed."
        ),
        "local.main.label": "Main local input path",
        "local.main.help": (
            "Enter the explicit main file. Its absolute location is used only by "
            "this local process and is not included in normalized reports."
        ),
        "local.root.label": "Authorized local root",
        "local.root.help": (
            "External files may resolve only inside this independently authorized "
            "directory after canonical path checks. No directory is scanned."
        ),
        "run.help.upload": "Upload a main input file to enable local analysis.",
        "run.help.local": (
            "Enter both the main local input and authorized root to enable preview."
        ),
        "run.spinner": (
            "Parsing, running deterministic checks, and resolving authorized "
            "references..."
        ),
        "reference.heading": "External references",
        "reference.before_run": (
            "External-reference resolution will appear after Run check is pressed."
        ),
        "reference.intro": (
            "Only verified PBED references are resolved. Include files and every "
            "other external-reference type remain unsupported."
        ),
        "reference.none": "No supported PBED reference was found in the main input.",
        "reference.summary": "{count} supported external reference(s) found.",
        "reference.table.source": "Source file",
        "reference.table.type": "Reference type",
        "reference.table.target": "Relative target",
        "reference.table.status": "Resolution status",
        "reference.table.size": "File size (bytes)",
        "reference.table.records": "Record count",
        "reference.status.resolved": "Resolved",
        "reference.status.pending_authorization": "Awaiting authorization",
        "reference.status.missing": "Missing",
        "reference.status.rejected": "Rejected",
        "reference.status.ambiguous": "Ambiguous",
        "reference.status.invalid": "Invalid PBED data",
        "reference.status.limit_exceeded": "Limit exceeded",
        "reference.target.absolute": "[absolute path rejected]",
        "reference.target.invalid": "[invalid path rejected]",
        "reference.unused": "Unused supporting files ({count})",
        "reference.local.pending": (
            "The table is a metadata preview. Supporting-file contents have not "
            "been read. Confirm explicitly to open the listed in-root PBED files."
        ),
        "reference.local.confirm": "Authorize and read supporting PBED files",
        "reference.local.spinner": "Reading the explicitly authorized PBED files...",
        "reference.local.error": "Local source policy error: {message}",
        "reference.policy.BUNDLE_DOCUMENT_LIMIT": (
            "The uploaded bundle exceeds the configured document-count limit."
        ),
        "reference.policy.MAIN_FILE_SIZE_LIMIT": (
            "The main input exceeds the configured byte limit."
        ),
        "reference.policy.INVALID_RELATIVE_PATH": (
            "A supplied source name is not a safe relative path."
        ),
        "reference.policy.PATH_TRAVERSAL": (
            "A supplied source name escapes the explicit bundle root."
        ),
        "reference.policy.EMPTY_RELATIVE_PATH": (
            "A supplied source name resolves to an empty path."
        ),
        "reference.policy.INVALID_WINDOWS_NAME": (
            "A supplied source name contains a Windows-invalid path component."
        ),
        "reference.policy.LOCAL_SOURCE_MISSING": (
            "The selected local file or root does not exist or cannot be resolved."
        ),
        "reference.policy.LOCAL_MAIN_NOT_FILE": (
            "The selected local main input is not a regular file."
        ),
        "reference.policy.LOCAL_ROOT_NOT_DIRECTORY": (
            "The authorized local root is not a directory."
        ),
        "reference.policy.MAIN_OUTSIDE_ROOT": (
            "The main input is outside the authorized local root."
        ),
        "reference.policy.MAIN_READ_FAILED": (
            "The selected main input could not be read."
        ),
        "reference.diagnostic.label": "{rule_id} / {code} / {location}",
        "reference.diagnostic.display": "{label}: {message}",
        "reference.diagnostic.MAIN_ENCODING": (
            "External references could not be extracted because the main input is "
            "not valid UTF-8."
        ),
        "reference.diagnostic.PBED_CARD_SYNTAX": (
            "The PBED card is outside the supported one-line quoted-path form and "
            "was not resolved."
        ),
        "reference.diagnostic.DUPLICATE_BUNDLE_NAME": (
            "Multiple supporting uploads have the same normalized Windows name."
        ),
        "reference.diagnostic.REFERENCE_MISSING": (
            "The referenced PBED file is not present in the allowed set."
        ),
        "reference.diagnostic.ABSOLUTE_REFERENCE_REJECTED": (
            "Absolute external references are rejected by the local sandbox policy."
        ),
        "reference.diagnostic.INVALID_REFERENCE_PATH": (
            "The external reference path is invalid or escapes the explicit root."
        ),
        "reference.diagnostic.REFERENCE_OUTSIDE_ROOT": (
            "The canonical target escapes the authorized local root."
        ),
        "reference.diagnostic.REFERENCE_NOT_FILE": (
            "The resolved target is not a regular file."
        ),
        "reference.diagnostic.REFERENCE_READ_FAILED": (
            "The authorized PBED target could not be read."
        ),
        "reference.diagnostic.AMBIGUOUS_BUNDLE_REFERENCE": (
            "The PBED target matches multiple uploads after normalized "
            "case-insensitive comparison."
        ),
        "reference.diagnostic.PBED_FILE_SIZE_LIMIT": (
            "The PBED file exceeds the configured byte limit and was not read."
        ),
        "reference.diagnostic.PBED_RECORD_LIMIT": (
            "The PBED record limit was exceeded; parsing stopped safely."
        ),
        "reference.diagnostic.PBED_COLUMN_COUNT": (
            "A PBED record does not contain exactly five fields and was excluded."
        ),
        "reference.diagnostic.PBED_BLANK_LINE": (
            "A blank PBED data line is outside the verified record subset and was "
            "excluded."
        ),
        "reference.diagnostic.PBED_NUMERIC_VALUE": (
            "A PBED record contains a malformed or non-finite coordinate/radius and "
            "was excluded."
        ),
        "reference.diagnostic.PBED_NON_POSITIVE_RADIUS": (
            "A PBED record has a non-positive outer radius and was excluded."
        ),
        "reference.diagnostic.PBED_ENCODING": (
            "The PBED file is not valid UTF-8 and parsing stopped."
        ),
        "reference.diagnostic.PBED_EMPTY": (
            "The PBED file contains no placement records."
        ),
        "pbed.heading": "PBED placement visualization",
        "pbed.summary": (
            "Valid placements: {valid}; excluded malformed records: {invalid}."
        ),
        "pbed.bounding_box": (
            "Outer-sphere bounding box [cm]: x=[{xmin}, {xmax}], "
            "y=[{ymin}, {ymax}], z=[{zmin}, {zmax}]."
        ),
        "pbed.no_bounding_box": "No valid PBED placement bounding box is available.",
        "pbed.slice.target": "Resolved PBED target",
        "pbed.view.mode": "PBED placement view",
        "pbed.view.slice": "Exact z-plane sphere cross sections",
        "pbed.view.projection": "XY center projection",
        "pbed.slice.z": "PBED XY-slice z [cm]",
        "pbed.slice.run": "Render PBED placement slice",
        "pbed.projection.run": "Render PBED center projection",
        "pbed.slice.summary": (
            "{intersecting} of {total} verified placement spheres intersect z={z} cm."
        ),
        "pbed.slice.title": "PBED placement cross-section at z={z} cm",
        "pbed.projection.title": "PBED XY center projection",
        "pbed.projection.summary": (
            "Projected {total} verified sphere center(s). This projection does not "
            "prove absence of 3D overlap."
        ),
        "pbed.universe": "Universe",
        "pbed.slice.none": "No verified placement sphere intersects this z plane.",
        "pbed.slice.warning": (
            "This plot shows placement-sphere cross-sections only. It does not expand "
            "particle universes, validate packing, or prove three-dimensional "
            "non-overlap."
        ),
        "pbed.slice.limit": (
            "The slice contains {count} circles, above the display limit {limit}; "
            "the typed result is retained but the Matplotlib plot is skipped."
        ),
    },
    JAPANESE: {
        "section.upload": "1. 入力元の選択",
        "source.mode.label": "入力モード",
        "source.mode.uploaded_bundle": "アップロードしたファイル一式",
        "source.mode.local_project": "許可したローカルプロジェクト",
        "upload.supporting.help": (
            "メイン入力から明示的に参照されるPBEDファイルだけをアップロードしてください。"
            "SerpentGuardは正規化した相対名で解決し，それ以外は未使用として扱います。"
        ),
        "upload.supporting.caption": (
            "補助ファイルを{count}件選択しました。参照されたPBEDファイルは，"
            "［検査を実行］を押した後にだけ読み取ります。"
        ),
        "local.main.label": "ローカルのメイン入力パス",
        "local.main.help": (
            "対象のメインファイルを明示してください。絶対パスはこのローカルプロセス"
            "内だけで使用し，正規化レポートには含めません。"
        ),
        "local.root.label": "許可するローカルルート",
        "local.root.help": (
            "外部ファイルは，正規パスを確認した後，この明示的に許可したディレクトリ"
            "内だけで解決します。ディレクトリ全体の走査は行いません。"
        ),
        "run.help.upload": (
            "ローカル解析を有効にするにはメイン入力をアップロードしてください。"
        ),
        "run.help.local": (
            "プレビューを有効にするには，メイン入力と許可ルートの両方を入力してください。"
        ),
        "run.spinner": "構文解析，決定論的検査，許可済み参照の解決を実行しています...",
        "reference.heading": "外部参照",
        "reference.before_run": (
            "［検査を実行］を押すと，外部参照の解決結果を表示します。"
        ),
        "reference.intro": (
            "検証済みのPBED参照だけを解決します。includeファイルとその他の外部参照形式"
            "には対応していません。"
        ),
        "reference.none": "メイン入力に対応済みのPBED参照はありません。",
        "reference.summary": "対応済みの外部参照が{count}件見つかりました。",
        "reference.table.source": "参照元ファイル",
        "reference.table.type": "参照形式",
        "reference.table.target": "相対参照先",
        "reference.table.status": "解決状態",
        "reference.table.size": "ファイルサイズ（byte）",
        "reference.table.records": "レコード数",
        "reference.status.resolved": "解決済み",
        "reference.status.pending_authorization": "許可待ち",
        "reference.status.missing": "見つかりません",
        "reference.status.rejected": "拒否",
        "reference.status.ambiguous": "候補が複数あります",
        "reference.status.invalid": "PBEDデータが不正",
        "reference.status.limit_exceeded": "上限超過",
        "reference.target.absolute": "［絶対パスを拒否］",
        "reference.target.invalid": "［不正なパスを拒否］",
        "reference.unused": "未使用の補助ファイル（{count}件）",
        "reference.local.pending": (
            "この表はメタデータのプレビューです。補助ファイルの内容はまだ読み取って"
            "いません。表示された許可ルート内のPBEDファイルを開くには明示的に確認してください。"
        ),
        "reference.local.confirm": "補助PBEDファイルの読取りを許可",
        "reference.local.spinner": (
            "明示的に許可されたPBEDファイルを読み取っています..."
        ),
        "reference.local.error": "ローカル入力のポリシーエラー：{message}",
        "reference.policy.BUNDLE_DOCUMENT_LIMIT": (
            "アップロードしたファイル数が設定上限を超えています。"
        ),
        "reference.policy.MAIN_FILE_SIZE_LIMIT": (
            "メイン入力が設定済みサイズ上限を超えています。"
        ),
        "reference.policy.INVALID_RELATIVE_PATH": (
            "指定されたファイル名は安全な相対パスではありません。"
        ),
        "reference.policy.PATH_TRAVERSAL": (
            "指定されたファイル名が明示的なファイル一式のルート外へ出ています。"
        ),
        "reference.policy.EMPTY_RELATIVE_PATH": (
            "指定されたファイル名を正規化すると空のパスになります。"
        ),
        "reference.policy.INVALID_WINDOWS_NAME": (
            "指定されたファイル名にWindowsで使用できないパス要素があります。"
        ),
        "reference.policy.LOCAL_SOURCE_MISSING": (
            "選択したローカルファイルまたはルートが存在しないか，解決できません。"
        ),
        "reference.policy.LOCAL_MAIN_NOT_FILE": (
            "選択したローカルのメイン入力は通常ファイルではありません。"
        ),
        "reference.policy.LOCAL_ROOT_NOT_DIRECTORY": (
            "許可したローカルルートはディレクトリではありません。"
        ),
        "reference.policy.MAIN_OUTSIDE_ROOT": (
            "メイン入力が許可したローカルルートの外にあります。"
        ),
        "reference.policy.MAIN_READ_FAILED": (
            "選択したメイン入力を読み取れませんでした。"
        ),
        "reference.diagnostic.label": "{rule_id} / {code} / {location}",
        "reference.diagnostic.display": "{label}：{message}",
        "reference.diagnostic.MAIN_ENCODING": (
            "メイン入力が有効なUTF-8ではないため，外部参照を抽出できませんでした。"
        ),
        "reference.diagnostic.PBED_CARD_SYNTAX": (
            "PBEDカードが，対応する1行・引用符付きパス形式ではないため解決しませんでした。"
        ),
        "reference.diagnostic.DUPLICATE_BUNDLE_NAME": (
            "複数の補助ファイルが，Windows名の正規化後に同じ名前になります。"
        ),
        "reference.diagnostic.REFERENCE_MISSING": (
            "参照されたPBEDファイルが許可されたファイル集合にありません。"
        ),
        "reference.diagnostic.ABSOLUTE_REFERENCE_REJECTED": (
            "ローカルサンドボックスポリシーにより絶対パスの外部参照を拒否しました。"
        ),
        "reference.diagnostic.INVALID_REFERENCE_PATH": (
            "外部参照パスが不正であるか，明示されたルートの外へ出ています。"
        ),
        "reference.diagnostic.REFERENCE_OUTSIDE_ROOT": (
            "参照先の正規パスが，許可されたローカルルートの外へ出ています。"
        ),
        "reference.diagnostic.REFERENCE_NOT_FILE": (
            "解決した参照先は通常ファイルではありません。"
        ),
        "reference.diagnostic.REFERENCE_READ_FAILED": (
            "許可されたPBED参照先を読み取れませんでした。"
        ),
        "reference.diagnostic.AMBIGUOUS_BUNDLE_REFERENCE": (
            "大文字・小文字を区別せず正規化して比較すると，PBED参照先が複数の"
            "アップロードに一致します。"
        ),
        "reference.diagnostic.PBED_FILE_SIZE_LIMIT": (
            "PBEDファイルが設定済みサイズ上限を超えたため読み取りませんでした。"
        ),
        "reference.diagnostic.PBED_RECORD_LIMIT": (
            "PBEDレコード数が上限を超えたため，安全に構文解析を停止しました。"
        ),
        "reference.diagnostic.PBED_COLUMN_COUNT": (
            "PBEDレコードが正確に5フィールドではないため除外しました。"
        ),
        "reference.diagnostic.PBED_BLANK_LINE": (
            "空のPBEDデータ行は検証済みレコード形式の対象外であるため除外しました。"
        ),
        "reference.diagnostic.PBED_NUMERIC_VALUE": (
            "PBEDレコードに不正または非有限の座標・半径があるため除外しました。"
        ),
        "reference.diagnostic.PBED_NON_POSITIVE_RADIUS": (
            "PBEDレコードの外半径が正ではないため除外しました。"
        ),
        "reference.diagnostic.PBED_ENCODING": (
            "PBEDファイルが有効なUTF-8ではないため構文解析を停止しました。"
        ),
        "reference.diagnostic.PBED_EMPTY": ("PBEDファイルに配置レコードがありません。"),
        "pbed.heading": "PBED配置の可視化",
        "pbed.summary": "有効な配置：{valid}件，除外した不正レコード：{invalid}件。",
        "pbed.bounding_box": (
            "外接球の境界ボックス［cm］：x=[{xmin}, {xmax}]，"
            "y=[{ymin}, {ymax}]，z=[{zmin}, {zmax}]。"
        ),
        "pbed.no_bounding_box": "有効なPBED配置の境界ボックスはありません。",
        "pbed.slice.target": "解決済みPBED参照先",
        "pbed.view.mode": "PBED配置の表示方法",
        "pbed.view.slice": "z平面における球の正確な断面",
        "pbed.view.projection": "球中心のXY投影",
        "pbed.slice.z": "PBEDのXY断面 z［cm］",
        "pbed.slice.run": "PBED配置断面を描画",
        "pbed.projection.run": "PBED球中心の投影を描画",
        "pbed.slice.summary": (
            "検証済み配置球{total}個のうち{intersecting}個がz={z} cmと交差します。"
        ),
        "pbed.slice.title": "z={z} cmにおけるPBED配置断面",
        "pbed.projection.title": "PBED球中心のXY投影",
        "pbed.projection.summary": (
            "検証済み球中心{total}件を投影しました．この投影は3次元的な重なりがないことを証明しません．"
        ),
        "pbed.universe": "Universe",
        "pbed.slice.none": "このz平面と交差する検証済み配置球はありません。",
        "pbed.slice.warning": (
            "この図は配置球の断面だけを表示します。粒子Universeの展開，充填状態の検証，"
            "3次元で重なりがないことの証明は行いません。"
        ),
        "pbed.slice.limit": (
            "断面の円が{count}個あり表示上限{limit}個を超えています。型付き結果は保持しますが，"
            "Matplotlib描画は省略します。"
        ),
    },
}

for _language, _entries in _EXTERNAL_REFERENCE_TRANSLATIONS.items():
    TRANSLATION_CATALOG[_language].update(_entries)


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
