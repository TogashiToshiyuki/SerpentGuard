# SerpentGuard

SerpentGuard is a small local Streamlit application for deterministic preflight checks on a limited subset of Serpent Monte Carlo input syntax. An optional OpenAI feature can explain only the reviewed structured payload; raw Serpent input must never be sent to the AI.

## Project status

The local parser, deterministic static analyzer, limited detector/energy-grid checks,
bilingual Streamlit interface, deliberately limited 2D geometry sampler, and sandboxed
PBED placement-file support are implemented. A versioned, privacy-preserving AI review
payload can be previewed locally and optionally sent to OpenAI only after explicit
consent and a Generate action. The interface accepts either an explicit uploaded bundle
or an authorized local project, records an optional analysis purpose, runs each check
only after explicit user action, and provides summary counts, filterable findings,
evidence, privacy-conscious debugging data, dependency status, and local plots. No
detector-purpose/response-physics review or general include resolution is implemented.

The supported runtime is Python 3.11 or newer. SerpentGuard has no database and is intended to run locally rather than as an externally deployed server.

## Demo video

Watch the public, audio-narrated demonstration:
[SerpentGuard Devpost Final](https://youtu.be/9TfTaqHja2Q). The video uses only
the independently written synthetic fixtures under `examples/demo/`; none of the
shown inputs is a production reactor model.

## Built with Codex and GPT-5.6

SerpentGuard was developed for the OpenAI Build Week Developer Tools track with
Codex using GPT-5.6. The work was organized into inspect-first milestones: establish
the parser and deterministic finding contract, add the bilingual workflow and limited
geometry sampler, harden external-reference and privacy boundaries, integrate the
optional structured AI explanation, and complete a release audit.

Codex accelerated repository inspection, cross-module implementation and refactoring,
test generation, failure-driven corrections, documentation, and the final privacy and
release-readiness review. GPT-5.6 helped reason across the parser, typed models,
analysis rules, Streamlit state, geometry sampling, privacy allowlist, and tests while
keeping their contracts aligned.

The developer made the central product and safety decisions: deterministic analysis
remains local and authoritative; the supported syntax is deliberately narrow;
unsupported cases are rejected or disclosed rather than guessed; raw input must never
enter the AI payload; and any optional AI request requires visible payload preview,
explicit consent, and an explicit Generate action. Codex output was reviewed rather
than accepted as authority, with behavior verified through automated tests, manual
demo checks, and documented limitations.

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux, activate it with `source .venv/bin/activate` instead.

Install the application and development tools:

```powershell
python -m pip install --upgrade pip
python -m pip install --editable ".[dev]"
```

The deterministic application works without the optional OpenAI SDK. To enable AI
explanations in a development installation, install both extras:

```powershell
python -m pip install --editable ".[dev,ai]"
```

## Optional OpenAI explanation

Configure the key and model in the shell that starts Streamlit. Never place a real key
in source code, `.env.example`, Git, screenshots, or an issue report.

PowerShell:

```powershell
$env:OPENAI_API_KEY = "your_api_key_here"
$env:SERPENTGUARD_OPENAI_MODEL = "a-model-available-to-your-project"
$env:SERPENTGUARD_OPENAI_TIMEOUT_SECONDS = "30"
```

macOS or Linux:

```bash
export OPENAI_API_KEY="your_api_key_here"
export SERPENTGUARD_OPENAI_MODEL="a-model-available-to-your-project"
export SERPENTGUARD_OPENAI_TIMEOUT_SECONDS="30"
```

SerpentGuard intentionally has no hard-coded model default. Select a model available
to your OpenAI project that supports the Responses API and structured outputs. See the
[official structured-output guide](https://developers.openai.com/api/docs/guides/structured-outputs)
and [API-key quickstart](https://developers.openai.com/api/docs/quickstart).

The application reads these values only from the process environment. It does not
automatically load `.env`, `.env.example`, or Streamlit secrets; `.env.example`
documents variable names only. The optional API request occurs only after local
analysis, visible payload preview, checkbox consent, and an explicit Generate button
press. The request uses `store=False` and sends the `AIReviewPayload` JSON as its only
user input. Local static findings remain visible if authentication, timeout,
rate-limit, network, partial-output, or schema validation fails.

## Run locally

Start the local Streamlit interface:

```powershell
streamlit run app.py
```

The equivalent module command is `python -m streamlit run app.py`.

For the complete public-demo sequence, use only the synthetic fixtures under
[`examples/demo/`](examples/demo/) and follow the timed
[`docs/demo_script.md`](docs/demo_script.md) walkthrough.

For a redistributable geometry demo, upload
`examples/demo/04_pwr_pin_cell.inp`, run the deterministic check, sample
Universe `0` over approximately `x,y = [-0.75, 0.75]`, and open the Geometry view.
The fixture is independently written and is not a production reactor model.

For the redistributable detector demo, upload
`tests/fixtures/detectors/valid_detector.inp`. The parser recognizes `ene` types 1–3
and only detector options `de`, `dx`, `dy`, and `dz`; the fixture's `dr` option is
intentionally retained and reported as SG027 INFO.

The interface supports English and Japanese (`日本語`), with English as the default.
Use the language selector above the page title to switch languages. Switching redraws
presentation text only: uploaded files, canonical findings, parsed results, and active
finding filters are preserved, and deterministic analysis is not rerun automatically.
When Generate is explicitly pressed, the optional AI response is requested in the
currently selected interface language. This language instruction does not alter the
previewed payload or weaken its fixed safety requirements.

Choose one input mode at the top of the application:

- **Uploaded file bundle:** upload one main input and only the supporting files you
  intend to make available. Supporting files remain local. After Run check, only a
  file referenced by the supported PBED card may be opened and parsed locally, using
  its normalized, case-insensitive Windows-style name. Unreferenced uploads are
  reported as unused; general `include` resolution is not implemented.
- **Authorized local project:** enter one main file and an independent authorized
  root. SerpentGuard first reads the main file and previews canonical in-root targets.
  Supporting PBED content is opened only after a second explicit authorization action.
  Absolute references and targets escaping the authorized root are rejected.

The local resolver never scans a drive, home directory, or project tree. Absolute
backing paths are not stored in normalized reference reports. No source or placement
data is sent over the network.

Prompt 6B supports only the documented one-line card
`pbed UNI0 BGU "FILE" [pow]` and UTF-8 placement records of exactly
`X Y Z R UNI`. Coordinates and the positive outer sphere radius are interpreted in
centimetres. The PBED section reports valid/excluded records and the outer-sphere
bounding box. It offers either the exact cross-section of each verified placement
sphere at the selected z plane or an explicitly labeled XY center projection. These
are placement visualizations, not packing-validity or definitive 3D-overlap checks.

After running the input check, select exactly one parsed Universe and confirm `xmin`,
`xmax`, `ymin`, `ymax`, and the XY grid resolution in the Geometry plot section.
Universe `0` is preferred when available. Geometry sampling is a separate explicit
action and evaluates the selected Universe only in its own local coordinate system. It
does not expand `fill`, pins, lattices, transformations, or nested Universes.

The default **Geometry view** displays the uniquely matched supported region by
Material or Cell with a discrete categorical legend. The separate **Diagnostic view**
shows normal, overlap, undefined, incomplete, and boundary-uncertain sample states.
Both preserve equal XY scale and use nearest-neighbor rendering. This is a limited
SerpentGuard visualization; it is not an exact replacement for Serpent's plotter.
Application colors may differ from Serpent. When the exact supported
`mat NAME DENS rgb R G B` form is present, material coloring can use that verified
triplet.

Japanese Matplotlib text uses an installed Japanese-capable font (Yu Gothic or Meiryo
is preferred on Windows). On Linux, installing Noto Sans CJK JP is recommended. Fonts
are not downloaded or bundled. If no candidate passes glyph validation, the app shows
an actionable warning and falls back to English inside the plot instead of silently
rendering square glyphs.

The current `cyl` and `sqc` subset is invariant in z, so the reserved z control is
disabled and does not affect results. Unsupported, ambiguous, malformed, and duplicate
Cell definitions are listed and excluded rather than approximated. When any selected-
Universe Cell is excluded, undefined-region detection is disabled: zero supported
matches are shown as indeterminate because an excluded Cell may occupy that space.

Inspect the CLI and parse a local UTF-8 fixture:

```powershell
serpentguard --help
serpentguard check --help
serpentguard check examples/valid_minimal.inp
serpentguard check examples/valid_minimal.inp --format json
```

If a local application-control policy blocks generated console-script shims, use
the equivalent module commands:

```powershell
python -m serpentguard.cli --help
python -m serpentguard.cli check --help
python -m serpentguard.cli check examples/valid_minimal.inp
python -m serpentguard.cli check examples/valid_minimal.inp --format json
```

The `check` command prints parsed object counts and source-located findings grouped by
severity, or a structured JSON report. Limited deterministic detector checks run in
both the CLI and Streamlit interface. Geometry sampling remains Streamlit-only. The
CLI does not perform detector-purpose/response-physics review, AI checks, or include
resolution, and it does not print raw input. Exit status is 0 without ERROR, 1 with a
recoverable ERROR, and 2 when the local input cannot be parsed at all.

## Development checks

Run the same checks used by CI:

```powershell
ruff check .
ruff format --check .
pytest
python -m build
```

Optional local Git hooks can be enabled after installing the development tools:

```powershell
pre-commit install
```

## Documentation

- [Canonical implementation specification](serpentguard_implementation_spec.md)
- [Specification index](docs/specification.md)
- [Implemented syntax boundary](docs/supported_syntax.md)
- [Supported checks and roadmap](docs/supported_checks.md)
- [Geometry-sampling architecture](docs/geometry_sampling.md)
- [External-reference and PBED architecture](docs/external_references.md)
- [Localization architecture](docs/localization.md)
- [Privacy policy](docs/privacy.md)
- [Architecture](docs/architecture.md)
- [Three-minute demo script](docs/demo_script.md)
- [Release-readiness and Devpost checklist](docs/release_readiness.md)
- [Example-file policy](examples/README.md)

## Privacy and local files

Keep unpublished Serpent inputs under `local_inputs/`, `private_inputs/`,
`local_reference_data/`, or `private_references/`; these directories are ignored by
Git. Environment files, Streamlit secrets, credentials, private keys, virtual
environments, caches, and common Serpent output files are also ignored.

Before staging changes, review them with:

```bash
git status --short --untracked-files=all
git check-ignore -v <path>
```

Only sanitized, redistributable fixtures should be added under `examples/`.

## Important limitations

- SerpentGuard is an experimental assistant.
- It supports only a limited subset of Serpent syntax.
- It does not guarantee that a model is geometrically or physically correct.
- Geometry checks are sampling-based and may miss narrow overlaps or gaps between
  grid points.
- Geometry sampling supports only `cyl` and `sqc`, shallow unions, and implicit
  intersections on an XY slice; it does not expand lattices or transformations.
- Geometry sampling is Universe-local. It never combines match counts across
  Universes and does not expand repeated or nested geometry.
- Undefined-region candidates are reported only when every parsed Cell in the
  selected Universe is supported and unambiguous.
- Same-name duplicate Cells in one selected Universe are all excluded; they are not
  treated as overlapping geometry.
- A workload guard rejects excessive combinations of grid points, evaluated Cells,
  and signed Surface references before grid allocation.
- The supported surfaces extend indefinitely in z, so changing canonical z values
  does not currently change classifications.
- External resolution supports PBED placement files only; `include`, external source,
  interface, mesh, data-library, and other reference types remain unopened.
- The PBED reader accepts only strict UTF-8 five-field records. Comments, headers,
  alternate columns, binary formats, and blank data records are unsupported.
- PBED placement circles do not expand particle universes or the background universe
  and do not establish physical packing, valid transport geometry, or 3D non-overlap.
- Browser upload controls generally preserve only file basenames. A main card that
  references a subdirectory may require local-project mode unless the upload client
  supplies matching logical relative names.
- Canonical path checks detect ordinary symlink and junction escapes where supported
  by the platform, but cannot eliminate every filesystem time-of-check/time-of-use
  race against a concurrently modified local project.
- It does not replace Serpent's own input validation or geometry plotter.
- The AI payload preview contains only allowlisted summaries. Its consent-gated
  Generate button is the only Streamlit path that may call the OpenAI API.
- AI-generated explanations may be incomplete or incorrect and never override local
  deterministic findings.
- All findings and suggested changes must be reviewed by a qualified user.
- The tool must not be used as the sole basis for reactor-safety or criticality-safety decisions.

## License

This project is licensed under the [MIT License](LICENSE).

Official Serpent examples are linked only as research sources and are not
redistributed under this project license. Repository fixtures are independently
written; source citations and the unresolved upstream redistribution terms are
documented in [`docs/example_sources.md`](docs/example_sources.md) and
[`examples/README.md`](examples/README.md).
