# Architecture

SerpentGuard is a local, single-user Python application. The deterministic core is
independent of Streamlit and has no database, authentication layer, cloud deployment,
or background service. The supported surface is intentionally smaller than Serpent.

## Component boundaries

| Component | Responsibility | Must not do |
| --- | --- | --- |
| `preprocessor.py` | Normalize newlines, remove supported comments while preserving line mapping, and diagnose unterminated block comments. | Log or transmit full source text. |
| `parser.py` and `models.py` | Build typed objects for the documented `surf`, `cell`, `mat`, `ene`, and `det` subset; preserve unknown cards and source locations. | Claim full Serpent compatibility or physics validity. |
| `analysis.py` | Build exact-name symbol tables and emit deterministic `Finding` objects. | Depend on UI language or AI output. |
| `geometry.py` | Sample one selected Universe in its local XY coordinates and retain compact canonical category grids. | Expand fills, lattices, transforms, or claim geometric proof. |
| `geometry_plot.py` | Render separate categorical Geometry and Diagnostic views with runtime font selection. | Mutate parsed or geometry results. |
| `references.py`, `pbed.py` | Resolve only verified PBED references in an explicit uploaded bundle or authorized root and parse strict placement records incrementally. | Scan directories, cross an authorized root, or expose backing paths. |
| `pbed_plot.py` | Render verified placement sphere slices or center projections. | Claim packing validity or full pebble-universe geometry. |
| `ai_payload.py` | Build and recursively audit versioned, allowlisted AI JSON. | Serialize raw source, comments, material composition, grids, paths, or secrets. |
| `ai_review.py` | Make one explicit structured Responses API request after all UI gates pass. | Read source files, retry automatically, or override deterministic findings. |
| `i18n.py` and `ui.py` | Localize presentation while retaining canonical rule IDs, severities, and objects. | Translate user input or write translated values into analysis models. |
| `app.py` | Orchestrate explicit user actions and store canonical results in Streamlit session state. | Duplicate parser, rule, geometry, or privacy logic. |
| `cli.py` | Expose local parse/static-check text and JSON reports with stable exit codes. | Resolve PBED, sample geometry, or call AI. |

## Primary data flow

```text
explicit input source
        |
        v
preprocess -> parse -> ParsedModel -> deterministic analysis -> AnalysisReport
                            |                         |
                            |                         +-> CLI / findings UI
                            +-> explicit geometry sample -> canonical grids -> plots
                            +-> explicit PBED resolver -> placement summaries -> plot

ParsedModel + AnalysisReport + limited optional summaries
        |
        v
allowlist + sanitization + recursive privacy audit
        |
        v
visible AIReviewPayload JSON -> consent -> explicit Generate -> structured explanation
```

Parser diagnostics and `Finding` objects remain language-neutral. The CLI and JSON
contract remain English/canonical. Streamlit derives English or Japanese labels when
rendering and does not rerun analysis merely because the language changes.

## Geometry views

One `GeometrySamplingResult` contains the selected Universe, sampling configuration,
coverage metadata, integer diagnostic classifications, and compact Cell/Material
category maps. The default Geometry view uses the unique supported match to show
occupancy by Material or Cell. The Diagnostic view separately shows normal,
supported-subset overlap, undefined (only with complete coverage), incomplete, and
boundary-indeterminate states. Unsupported Cells are excluded rather than guessed.

Current `cyl` and `sqc` surfaces extend indefinitely in z. PBED visualization is a
separate placement view and does not expand particle or background Universes. None of
these plots replaces Serpent's geometry plotter.

## External-reference boundary

Uploaded-bundle resolution sees only the explicitly uploaded logical names.
Local-project resolution sees only a main file and a separately authorized canonical
root; supporting content is not opened until the user confirms the preview. Absolute
PBED targets, root escapes, ambiguous names, unsupported encodings, and configured
size/record limits fail with sanitized diagnostics. General `include` resolution is
not implemented.

## AI privacy and language boundary

`AIReviewPayload` version `1.0` is the only eligible user message. The UI displays the
exact JSON, binds consent to its fingerprint, and calls OpenAI only after the enabled
Generate button is pressed. The optional response-language request is a controlled
system instruction based on the selected UI language; it does not modify the payload.
Fixed instructions prohibit invented source details, invented syntax, complete
validation claims, deterministic-error overrides, and full corrected input files.

The deterministic-only installation omits the OpenAI SDK. Importing the application
does not read API configuration or make a request. Authentication and network failures
do not remove local findings.

## Runtime and packaging

- Python 3.11 or newer, `src` package layout, Hatchling build backend.
- Streamlit, Pydantic, NumPy, and Matplotlib are base dependencies.
- `openai` is available only through the `ai` extra.
- pytest, Ruff, build, and pre-commit are development-only dependencies.
- GitHub Actions tests Python 3.11, lint, formatting, CLI help, and package build.

Exact syntax and rule boundaries are maintained in
[`supported_syntax.md`](supported_syntax.md) and
[`supported_checks.md`](supported_checks.md). Privacy details are maintained in
[`privacy.md`](privacy.md).
