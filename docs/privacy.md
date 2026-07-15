# Privacy

SerpentGuard performs deterministic analysis locally. The optional AI explanation feature is not implemented and must remain optional in later phases.

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
- Private external geometry data may instead be stored under `local_reference_data/`
  or `private_references/`; both are ignored by Git.
- Add only sanitized, redistributable fixtures to `examples/`.
- Inspect `git diff --cached` before every commit, especially before publishing the repository.
- If a secret is ever staged or committed, remove it from history and rotate it immediately; adding it to `.gitignore` afterward is not sufficient.

See the [canonical specification](../serpentguard_implementation_spec.md) for the authoritative privacy requirements.

## Sandboxed external references

PBED support has two local-only modes. Uploaded bundles resolve only among explicitly
uploaded files. Authorized local projects require a separate root and canonicalize
the main file and every target; absolute targets, targets outside the root, and
canonical symlink/junction escapes are rejected where the operating system exposes
them. The resolver does not scan directories or infer a broader root from an absolute
main path.

Normalized reports contain logical relative names, statuses, byte/record counts,
bounding summaries, and sanitized diagnostics. They do not serialize backing absolute
paths or raw input/PBED records. Backing bytes and canonical paths are also excluded
from object representations. Local paths entered by a user remain runtime session
state only and must never be placed in a future AI payload.

The unpublished reference pair used during Prompt 6B was read locally only for minimal
structural validation. Neither file, its filename, its absolute path, research
coordinates, material data, nor source excerpt is redistributed in this repository.
All committed PBED fixtures are independently written synthetic data and are not
production reactor models.
