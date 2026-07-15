# SerpentGuard

SerpentGuard is a small local Streamlit application for deterministic preflight checks on a limited subset of Serpent Monte Carlo input syntax. An optional AI feature may later explain structured findings, but raw Serpent input must never be sent to the AI.

## Project status

The local parser, deterministic static analyzer, bilingual Streamlit interface, and a deliberately limited 2D geometry sampler are implemented for a narrow `surf`, `cell`, and `mat` subset. The interface accepts one main input, records an optional analysis purpose, runs each check only after explicit user action, and provides summary counts, filterable findings, evidence, privacy-conscious parsed-model debugging data, and an XY sampling plot. Supporting files can be selected for future include handling but are not opened. No detector checker, include resolution, physics review, or AI integration has been implemented.

The supported runtime is Python 3.11 or newer. SerpentGuard has no database and is intended to run locally rather than as an externally deployed server.

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

The OpenAI Python SDK is declared only as an optional future dependency. It is not installed by the command above and is not imported or called by the application. If a later phase requires it, install the `ai` extra explicitly with `python -m pip install --editable ".[ai]"`.

## Run locally

Start the local Streamlit interface:

```powershell
streamlit run app.py
```

The equivalent module command is `python -m streamlit run app.py`.

The interface supports English and Japanese (`日本語`), with English as the default.
Use the language selector above the page title to switch languages. Switching redraws
presentation text only: uploaded files, canonical findings, parsed results, and active
finding filters are preserved, and deterministic analysis is not rerun automatically.

After running the input check, confirm `xmin`, `xmax`, `ymin`, `ymax`, the XY grid
resolution, and a z coordinate in the Geometry plot section. Geometry sampling is a
separate explicit action. It evaluates only the documented `cyl` and `sqc` surface
subset; unsupported cells are listed and excluded rather than approximated.

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
severity, or a structured JSON report. Geometry sampling is available only in the
local Streamlit interface; the CLI does not run geometry, detector, physics, or AI
checks, follow include files, or print raw input. Exit status is 0 without ERROR, 1
with a recoverable ERROR, and 2 when the local input cannot be parsed at all.

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
- [Localization architecture](docs/localization.md)
- [Privacy policy](docs/privacy.md)
- [Example-file policy](examples/README.md)

## Privacy and local files

Keep unpublished Serpent inputs under `local_inputs/` or `private_inputs/`; both directories are ignored by Git. Environment files, Streamlit secrets, credentials, private keys, virtual environments, caches, and common Serpent output files are also ignored.

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
- It does not replace Serpent's own input validation or geometry plotter.
- Future AI-generated explanations may be incomplete or incorrect.
- All findings and suggested changes must be reviewed by a qualified user.
- The tool must not be used as the sole basis for reactor-safety or criticality-safety decisions.

## License

This project is licensed under the [MIT License](LICENSE).
