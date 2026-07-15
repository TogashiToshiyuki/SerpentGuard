# SerpentGuard

SerpentGuard is a small local Streamlit application planned to perform deterministic preflight checks on a limited subset of Serpent Monte Carlo input syntax. An optional AI feature may later explain structured findings, but raw Serpent input must never be sent to the AI.

## Project status

The Python project foundation is present: a `src` package, placeholder Streamlit page, placeholder command-line interface, tests, linting, packaging, and CI. No parser, geometry checker, detector checker, or AI integration has been implemented.

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

Start the placeholder Streamlit page:

```powershell
python -m streamlit run app.py
```

Inspect the placeholder CLI:

```powershell
serpentguard --help
serpentguard check --help
```

If a local application-control policy blocks generated console-script shims, use
the equivalent module commands:

```powershell
python -m serpentguard.cli --help
python -m serpentguard.cli check --help
```

The `check` command does not accept or process Serpent input yet.

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
- [Supported-check roadmap](docs/supported_checks.md)
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
- It will support only a limited subset of Serpent syntax.
- It does not guarantee that a model is geometrically or physically correct.
- Planned geometry checks are sampling-based and may miss narrow overlaps or gaps.
- It does not replace Serpent's own input validation or geometry plotter.
- Future AI-generated explanations may be incomplete or incorrect.
- All findings and suggested changes must be reviewed by a qualified user.
- The tool must not be used as the sole basis for reactor-safety or criticality-safety decisions.

## License

This project is licensed under the [MIT License](LICENSE).
