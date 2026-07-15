# Privacy

SerpentGuard is intended to perform deterministic analysis locally. The optional AI explanation feature is not implemented in Phase 0 and must remain optional in later phases.

## Data that must stay local

Raw Serpent input must not be sent to an AI service. This includes:

- complete input or include-file contents;
- comments and free-form source text;
- complete material, isotope, geometry, or detector definitions;
- absolute file paths, user names, environment variables, and API keys;
- Serpent output files or nuclear-data-library locations.

Raw input and API keys must also be excluded from normal application logs and Git history.

## Permitted future AI payload

Only a deliberately constructed, user-previewed payload of structured findings may be sent, and only after an explicit user action. It may contain rule identifiers, severity, short generated finding messages, object type or name, relative line numbers, model counts, aggregate geometry-sampling statistics, analysis purpose, and stated limitations.

The payload generator must be tested to ensure that source text is absent. AI failure must never prevent local deterministic findings from being displayed.

## Local repository handling

- Store secrets in `.env` or `.streamlit/secrets.toml`; both are ignored by Git.
- Store unpublished inputs under `local_inputs/` or `private_inputs/`; both are ignored by Git.
- Add only sanitized, redistributable fixtures to `examples/`.
- Inspect `git diff --cached` before every commit, especially before publishing the repository.
- If a secret is ever staged or committed, remove it from history and rotate it immediately; adding it to `.gitignore` afterward is not sufficient.

See the [canonical specification](../serpentguard_implementation_spec.md) for the authoritative privacy requirements.
