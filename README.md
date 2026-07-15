# SerpentGuard

SerpentGuard is a small local Streamlit application planned to perform deterministic preflight checks on a limited subset of Serpent Monte Carlo input syntax. An optional AI feature may later explain structured findings, but raw Serpent input must never be sent to the AI.

## Project status

The project is currently in repository initialization (Phase 0). No parser, geometry checker, Streamlit application, or AI integration has been implemented yet.

The planned runtime is Python 3.11 or newer. The initial GitHub Actions workflow only confirms that Python is available and that the repository has its required bootstrap files.

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
