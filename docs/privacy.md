# Privacy

SerpentGuard performs deterministic analysis locally. A local, privacy-preserving AI
payload preview and optional OpenAI explanation are implemented. The API feature is
off unless its optional dependency and environment settings are present, and no API
request occurs automatically. Parser, static-analysis, geometry, detector, and PBED
work remain local and do not depend on the AI result.

## Data that must stay local

Raw Serpent input must not be sent to an AI service. This includes:

- complete input or include-file contents;
- comments and free-form source text;
- complete material, isotope, geometry, or detector definitions;
- absolute file paths, user names, environment variables, and API keys;
- Serpent output files or nuclear-data-library locations.

Raw input and API keys must also be excluded from normal application logs and Git history.

## Implemented AI payload contract

`AIReviewPayload` schema version `1.0` is the only JSON contract eligible for an
AI explanation. It is constructed by an explicit allowlist rather than by
serializing `ParsedModel`, `AnalysisReport`, or `GeometrySamplingResult` wholesale.
The preview can contain only:

- the user-entered analysis purpose after conservative sanitization;
- aggregate counts for supported parsed object types and parser diagnostics;
- findings selected by the current local severity/rule filters, bounded to 100;
- rule ID, canonical severity, short title/message, sanitized source leaf name,
  relative line number, object type/name, bounded structured evidence, and confidence;
- aggregate geometry sampling bounds, resolution, universe, completeness flags, and
  classification counts, but no grid arrays or representative coordinates;
- at most 50 detector summaries containing only detector name, particle type, energy
  grid reference names, supported Cartesian mesh numbers, and unsupported option names;
- stated deterministic-analysis and payload-truncation limitations.

The payload never includes raw input/card text, comments, include/PBED contents,
material compositions or isotope lists, region expressions, geometry category arrays,
full detector cards, absolute paths, environment variables, or credentials.

## Sanitization and consent

All untrusted strings are length-bounded. Absolute Windows, UNC, and POSIX paths are
reduced to a source leaf name where appropriate or replaced by a redaction marker.
Secret-like values and evidence fields named like API keys, tokens, passwords,
authorization data, raw/source text, comments, or compositions are removed. A final
recursive privacy audit rejects a payload if a prohibited field, absolute path,
secret-like value, or Serpent-card-like string remains.

The analysis-purpose field is not a source-input channel. Percent-comment text and
block-comment text are removed; text resembling a Serpent card is replaced rather
than forwarded. This conservative policy may omit legitimate prose that resembles an
input card.

Streamlit shows the complete versioned JSON before the send action. The consent
checkbox states: “I have reviewed the data shown above and agree to send this JSON for
AI explanation.” Consent is bound to a fingerprint of the visible JSON and is cleared
when analysis, finding filters, or geometry statistics change. The Generate button is
disabled until consent is selected. Pressing that enabled button is the only Streamlit
path that may call the OpenAI API.

The OpenAI Responses API request uses `store=False`, a separately supplied fixed system
instruction, and the exact reviewed `AIReviewPayload` JSON as its only user input. The
SDK's automatic retries are disabled, so each Generate press issues at most one API
request. The system instruction prohibits invented line numbers and syntax,
complete-validation
claims, overriding deterministic errors, deterministic treatment of purpose-dependent
questions, and full corrected input files. Structured response validation requires
`summary`, `prioritized_findings`, `explanation`, `suggested_checks`, `confidence`, and
`limitations`; prioritized rule IDs not present in the payload are rejected.

The optional client reads `OPENAI_API_KEY` and `SERPENTGUARD_OPENAI_MODEL` from the
process environment only when the user presses Generate. No model name is hard-coded.
`SERPENTGUARD_OPENAI_TIMEOUT_SECONDS` may set a bounded timeout. Keys are never placed
in the payload, application session state, exception messages, or logs. See the README
for process-environment setup; never commit a populated key file.

Authentication, timeout, rate-limit, connection, refusal, incomplete-output, and
schema-validation failures are displayed as sanitized messages. A failed AI request
removes no local deterministic findings and does not weaken their severity.

Local deterministic findings do not depend on payload construction and remain
available if payload validation fails or the optional AI feature is unavailable.

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
state only and must never be placed in an AI payload.

The unpublished reference pair used during Prompt 6B was read locally only for minimal
structural validation. Neither file, its filename, its absolute path, research
coordinates, material data, nor source excerpt is redistributed in this repository.
All committed PBED fixtures are independently written synthetic data and are not
production reactor models.
