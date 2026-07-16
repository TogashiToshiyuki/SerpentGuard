# Release readiness

Review date: 2026-07-16. Target: OpenAI Build Week, Developer tools track.

## Readiness decision

The local repository is **demo-ready at the code and documentation level**. There are
no known blocking test, lint, build, packaging, CLI, or local-startup failures. The
submission itself is not complete until the owner performs the manual Devpost actions,
records the qualifying `/feedback` Session ID, publishes the approved repository
state, and uploads the public video and screenshots.

No commit or push was made during this readiness pass.

## Specification review and resolved mismatches

| Observation | Resolution |
| --- | --- |
| `supported_syntax.md` still said detector/energy-grid parsing and AI explanations were unimplemented. | Corrected to the actual limited `det`/`ene` subset and optional consent-gated AI explanation. |
| `supported_checks.md` described all AI analysis as absent. | Clarified that deterministic checks remain local and authoritative while optional AI only explains their structured output. |
| AI output was forced to English even when the Japanese UI was selected. | Added a controlled English/Japanese output-language instruction. The fixed safety instruction and exact payload remain unchanged; language switching never sends a request. |
| Phase 8 architecture, demo, readiness, screenshot, and Devpost guidance was missing. | Added `architecture.md`, `demo_script.md`, this readiness report, and self-documenting demo fixtures. |
| The canonical specification lists SG012/SG013 and limited `include` handling as planned work. | Intentionally remains deferred because the current approved scope excludes general include resolution. PBED is the only resolved external-reference type. This is a documented scope difference, not silently implemented behavior. |
| The specification's AI response JSON is illustrative and differs in nested priority fields from the later implemented structured contract. | The implementation follows the later explicit milestone contract: required top-level summary, prioritized findings, explanation, suggested checks, confidence, and limitations. The typed schema and tests are the release contract. |
| The specification's proposed module tree differs from the implemented module names. | `architecture.md` maps actual responsibilities. Runtime boundaries are preserved without a broad cosmetic refactor. |

## Implemented features

- UTF-8 local preprocessing with newline/source-line preservation, percent comments,
  confirmed block comments, and safe parser recovery.
- Typed parsing for the exact documented `surf`, `cell`, `mat`, `ene`, and `det`
  subset; unknown-card preservation.
- Deterministic SG001–SG011, SG014–SG027 behavior where documented, including
  detector/energy-grid checks and sandboxed PBED resolution diagnostics.
- English/Japanese Streamlit presentation with canonical CLI/JSON values unchanged.
- Universe-local XY sampling, separate Material/Cell Geometry view and Diagnostic
  view, categorical legends, explicit completeness, boundary tolerance, and workload
  guards.
- Strict uploaded-bundle and authorized-local-root PBED resolver with size, record,
  encoding, ambiguity, and traversal controls; verified sphere slice/projection only.
- `AIReviewPayload` version `1.0`, local preview, fingerprint-bound consent, optional
  OpenAI structured explanation, safe failures, and selected-language response request.
- CLI help, text/JSON reports, stable exit codes, offline tests, and CI packaging checks.
- Seven self-documenting, synthetic demo fixtures under `examples/demo/`.

## Unsupported features

- Full Serpent grammar, exact Serpent lexer behavior, automatic input correction, or
  generated full replacement input.
- General `include` resolution, SG012/SG013, external references other than verified
  PBED, implicit directory search, or arbitrary local-file access.
- Surface types beyond `cyl`/`sqc`, nested Boolean CSG, cell complements, fill/pin/lat
  expansion, transforms, repeated geometry, or general 3D geometry.
- Definitive gap/overlap proof, Serpent-equivalent plotting, transport calculations,
  material physics, depletion, criticality, or safety validation.
- Complete detector syntax, detector response/normalization/statistics semantics, or
  purpose-dependent physics judgment.
- PBED particle-Universe/background expansion, packing validity, or proof of 3D
  non-overlap.
- Cloud deployment, authentication, multi-user state, database, or telemetry.

## Known bugs and risks

No blocking bug is known. Remaining risks are explicit limitations:

- Sampling can miss narrow gaps or overlaps between grid points.
- Unsupported or duplicate Cells make coverage incomplete and disable undefined-region
  claims for zero supported matches.
- Current supported surfaces are infinite in z; the reserved z value does not change
  their classification.
- Exact-name symbol matching is case-sensitive while the broader Serpent identifier
  behavior remains an open research question.
- The PBED grammar is intentionally strict UTF-8 `X Y Z R UNI`; alternate real-world
  formats are rejected rather than guessed.
- An AI response can still be incomplete or wrong. Language is requested, not used as
  a correctness signal, and deterministic findings remain authoritative.
- Live OpenAI behavior was not exercised in automated release verification; all API
  tests are mocked to prevent network calls in CI.
- One Windows symlink-escape test is skipped when the current account cannot create a
  test symlink. Canonical-path policy tests otherwise pass.
- The official challenge requires a project built with Codex using GPT-5.6. The owner
  must confirm the actual qualifying session/model metadata; this repository cannot
  prove it.

## Verification record

The following checks passed from the repository root using the project environment
unless noted:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m build
.\.venv\Scripts\serpentguard.exe --help
.\.venv\Scripts\serpentguard.exe check --help
```

Results:

- Ruff lint: passed.
- Ruff format check: 28 Python files already formatted.
- pytest: 200 passed, 1 platform-permission skip.
- Build: `serpentguard-0.1.0.tar.gz` and
  `serpentguard-0.1.0-py3-none-any.whl` built successfully.
- Streamlit: health endpoint returned HTTP 200; an in-app browser rendered the title,
  workflow, privacy notice, input modes, seven sections, and disabled pre-analysis
  controls without an exception.
- Japanese plotting font on the verification machine: Yu Gothic, with required glyph
  support detected.

Clean temporary environments outside the repository were created from the built wheel
and removed after verification:

- Deterministic-only wheel installation: package and Streamlit imported; `openai` was
  absent; CLI help passed.
- AI-extra wheel installation: package imported; `openai==2.45.0` installed through
  the declared extra; `check --help` passed.

Representative CLI fixture contracts:

| Fixture | Exit | Canonical rule IDs |
| --- | ---: | --- |
| `01_valid_minimal.inp` | 0 | none |
| `02_undefined_surface.inp` | 1 | SG004 |
| `03_contradictory_region.inp` | 0 | SG008 |
| `04_pwr_pin_cell.inp` | 0 | none |
| `05_overlap_and_gap.inp` | 0 | none; geometry test confirms overlap and undefined candidates |
| `06_detector_issues.inp` | 1 | SG021, SG022, SG023, SG024 |
| `07_ai_review.inp` | 1 | SG004, SG007, SG014 |

## Privacy and Git audit

- No private reference filename, research-directory marker, developer username path,
  or supplied private absolute path occurs in repository content.
- No generated build/cache/log/result artifact is tracked. `dist/`, virtual
  environments, caches, logs, Serpent outputs, and local/private input directories are
  ignored.
- The only tracked environment-like file is the intentionally empty `.env.example`.
  `.env` and `.streamlit/secrets.toml` are ignored.
- Key-pattern matches are limited to empty/example configuration, documented
  placeholders, and synthetic redaction-test values. No live credential was found.
- The one generic absolute Windows path is a synthetic `researcher` value used to test
  payload redaction; it contains no actual developer path.
- All added `.inp` files are under `examples/demo/`, self-identify as synthetic, and
  are not production reactor models. No private PBED file was added.
- `git diff --check` passed. The branch is `main`; `origin/main` matched HEAD before
  this uncommitted readiness work.

Repeat the audit immediately before staging, and inspect `git diff --cached` before
any authorized commit.

## Exact demo sequence

1. Open with the local/privacy disclaimer.
2. Show clean `01_valid_minimal.inp`.
3. Show SG004 on `02_undefined_surface.inp`.
4. Show SG008 on `03_contradictory_region.inp`.
5. Show Material Geometry and separate Diagnostic tabs with
   `04_pwr_pin_cell.inp`, Universe `0`, x/y `[-0.75, 0.75]`, resolution `121`.
6. Show both overlap and undefined candidates with `05_overlap_and_gap.inp`,
   Universe `0`, x/y `[-0.8, 0.8]`, resolution `121`.
7. Show detector SG021–SG024 with `06_detector_issues.inp`.
8. Show the structured preview, consent transition, and optional explicit Generate
   action with `07_ai_review.inp`.
9. End on deterministic findings and the limitation that neither plots nor AI replace
   Serpent or qualified review.

Exact timings and narration are in [`demo_script.md`](demo_script.md).

## Exact startup commands

Deterministic-only Windows setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install .
python -m streamlit run app.py
```

Development/demo setup with tests:

```powershell
python -m pip install --editable ".[dev]"
python -m streamlit run app.py
```

Optional AI extra (never commit the key):

```powershell
python -m pip install --editable ".[ai]"
$env:OPENAI_API_KEY = "your_api_key_here"
$env:SERPENTGUARD_OPENAI_MODEL = "a-model-available-to-your-project"
python -m streamlit run app.py
```

## Remaining manual Devpost actions

- Re-check the [live challenge requirements](https://openai.devpost.com/) and rules.
  As verified on 2026-07-16, the deadline is July 21, 2026 at 5:00 PM PDT.
- Confirm eligibility, choose Developer tools, and verify qualifying GPT-5.6/Codex
  usage honestly.
- Run `/feedback` in the Codex session containing the majority of core implementation
  and paste the returned Session ID in Devpost.
- Approve and publish the repository state. If private, share it with the testing
  addresses listed by the current challenge rules. No push was performed here.
- Record and publish the audio-narrated, public YouTube video at less than three
  minutes; add synthetic-data screenshots and repository URL.
- Add the project description, setup instructions, sample-data guidance, Codex usage
  story, known limitations, and disclaimer.
- Verify all links in Devpost's View page and submit before the deadline.

## Suggested commit message

```text
Prepare synthetic demo and release-readiness documentation
```
