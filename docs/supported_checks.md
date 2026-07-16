# Supported checks

## Current implementation status

SerpentGuard performs deterministic preprocessing, limited syntactic parsing,
symbol-table analysis, limited detector/energy-grid checks, and user-triggered XY
geometry sampling of the supported parsed model. It does not perform detector-purpose
review or response physics validation. An optional consent-gated AI service can
explain the already-produced structured findings, but it does not create, suppress,
or change deterministic findings.

Findings use only `ERROR`, `WARNING`, `REVIEW`, or `INFO`. Each structured finding
contains a rule ID, title, message, source file and line when available, object type and
name when applicable, structured evidence, and a `high`, `medium`, or `low` confidence.
Evidence never contains the full raw input.

## Implemented rules

| Rule | Severity | Deterministic behavior |
| --- | --- | --- |
| SG001 | ERROR | Report an exact-name surface definition group containing more than one definition. |
| SG002 | ERROR | Report an exact-name cell definition group containing more than one definition. |
| SG003 | ERROR | Report an exact-name material definition group containing more than one definition. |
| SG004 | ERROR | Report a supported parsed cell surface reference with no exact-name parsed surface definition. |
| SG005 | ERROR | Report a material-filled supported cell with no exact-name parsed material definition; exclude `void` and `outside`. |
| SG006 | INFO | Report a parsed surface name not referenced by any supported parsed cell. |
| SG007 | INFO | Report a parsed material name not used by any supported material-filled cell. |
| SG008 | WARNING | Report both positive and negative forms of one surface within the same intersection term. |
| SG009 | WARNING | Report a repeated identical signed surface condition within one intersection term. |
| SG010 | REVIEW | Report a parsed cell exceeding a configured syntactic complexity threshold. |
| SG011 | ERROR | Convert an unterminated-block-comment preprocessing diagnostic into a finding. |
| SG014 | INFO | Convert an unsupported-card diagnostic into a finding without interpreting the card. |
| SG015 | ERROR | Convert malformed-card recovery or an input-level parser failure into a finding. |
| SG016 | ERROR | Report a missing PBED target from an explicit uploaded bundle or authorized local project. |
| SG017 | ERROR | Reject an absolute PBED target, canonical root escape, directory target, or other local-reference policy violation. |
| SG018 | ERROR | Report duplicate or ambiguous normalized supporting-file names. |
| SG019 | ERROR | Report an empty PBED file, unsupported encoding, blank or malformed record, non-finite coordinate, or non-positive radius; invalid records are excluded. |
| SG020 | ERROR | Reject an external file or PBED record stream that exceeds configured limits. |
| SG021 | ERROR | Report an exact-name detector definition group containing more than one definition. |
| SG022 | ERROR | Report a supported detector `de` reference with no exact-name parsed energy-grid definition. |
| SG023 | ERROR | Report a non-positive explicit or inferred energy-grid bin count or Cartesian detector-axis bin count. |
| SG024 | ERROR | Report `EMIN >= EMAX` for `ene` types 2/3 or `MIN >= MAX` for `dx`, `dy`, or `dz`. |
| SG025 | REVIEW | Report the product of supported detector mesh/energy bins when it exceeds the configured threshold. |
| SG026 | REVIEW | Report a detector XY rectangle completely outside one unambiguous supported root-geometry bounding box. |
| SG027 | INFO | Preserve a duplicate or unsupported detector option without interpreting it. |

SG008 and SG009 evaluate every union-separated intersection term independently. For
example, `-s : s` does not contradict itself because the two signs occur in separate
union branches. These static rules do not evaluate Boolean geometry; the separate
sampler below evaluates only the documented subset.

## Limited detector checks

Detector checks operate only on the parsed `de`, `dx`, `dy`, and `dz` subset. Exact
case is used for energy-grid names. SG025 multiplies the positive supported axis counts
and the uniquely resolved energy-grid bin count; it is skipped when a required factor
is undefined, ambiguous, non-positive, or has reversed limits. The default review
threshold is `1,000,000` total bins. This is a workload/review signal, not a claim that
the requested detector is physically inappropriate.

SG026 is deliberately conservative and REVIEW-only. It runs only when Universe `0`
contains an `outside` Cell with one positive reference to one uniquely defined
supported `cyl` or `sqc` surface, yielding an unambiguous XY bounding box. Both `dx`
and `dy` must be valid, and the detector rectangle must be disjoint from that box.
The check is disabled when a retained transformation card is present. No z bound is
inferred because the supported surfaces are infinite in z.

Unsupported detector options are retained with option-level locations and SG027 INFO.
Malformed selected options use SG015 ERROR. SerpentGuard does not judge response
selection, axial-binning suitability, statistics, normalization, or analysis purpose.

## Limited XY geometry sampling

Geometry sampling is a separate language-independent numerical operation, not a
`Finding` rule and not part of CLI exit status. In the Streamlit interface, the user
must select one parsed Universe and explicitly confirm `xmin`, `xmax`, `ymin`, `ymax`,
and a square-grid resolution before sampling starts. Range endpoints are included.
Universe `0` is the deterministic default when present; otherwise the lexically first
available parsed Universe is selected and disclosed.

Cells are grouped by their exact `universe` value before geometry preparation. Match
counts never cross Universe boundaries. The selected Universe is evaluated only in
its local coordinate system: `fill`, pin, lattice, repeated-geometry, transformation,
and nested-Universe expansion are not implemented.

Only parsed Cells whose complete region expression uses one unambiguous, valid `cyl`
or `sqc` definition are evaluated. A Cell with unsupported syntax, an undefined,
duplicate, unsupported, or malformed Surface, or an empty region is listed as excluded
and is never approximated. Same-name Cell definitions within the selected Universe are
all excluded, preventing duplicate definitions from becoming artificial full-region
overlaps. Same names in different Universes are independent for geometry preparation.
SG002 remains the canonical static-analysis finding.

Each point is classified as:

- undefined-region candidate when zero supported Cells match and coverage is complete;
- normal when exactly one supported Cell matches and coverage is complete;
- overlap candidate when two or more supported Cells match;
- incomplete/unsupported when coverage is incomplete and fewer than two definite
  supported Cells match;
- boundary-indeterminate when a supported surface lies within the configured absolute
  boundary tolerance and fewer than two definite supported Cells match.

Coverage is complete only when every parsed Cell in the selected Universe is evaluated.
If any Cell is excluded, `undefined_detection_enabled` is false, zero-match points are
indeterminate, and one-match points mean only one supported-subset match—not global
uniqueness. Definite overlap among two or more evaluated Cells is still reported as a
supported-subset overlap candidate. Result metadata records the selected Universe,
coverage state, supported/excluded Cell counts, and incomplete-domain point count.

The code default for boundary tolerance is `1e-9`; the interface exposes it explicitly.
The result includes a Matplotlib classification plot, point counts, deterministic
representative coordinates, involved cell names for overlap candidates, excluded-cell
reasons, and the confirmed Universe, range, and resolution. The canonical z value is
reserved for future extension, but the UI disables it and explicitly states that the
currently supported infinite-z `cyl` and `sqc` forms are z-invariant.

Before allocating the grid, the sampler estimates workload as grid points multiplied
by the sum of evaluated Cell count and signed Surface-reference count. Requests above
the code-configured default limit of `50,000,000` estimated operations are rejected.
The default 100 × 100 grid remains usable. Full-grid Cell masks are processed and
discarded incrementally rather than retained for every Cell.

This is a sampling aid, not a geometric proof. Narrow gaps or overlaps between grid
points may be missed, and the check does not replace the Serpent geometry plotter.

The default Geometry view is separate from this diagnostic classification map. It
uses compact categorical grids to show uniquely matched supported regions by exact
Material or Cell name. Overlap, incomplete, undefined, and boundary states never
masquerade as normal material occupancy. Both plots use discrete legends and preserve
equal XY aspect ratio; neither changes `Finding` objects or CLI behavior.

## Sandboxed PBED external references

SG016–SG020 belong to the external-reference report, not the existing core
`AnalysisReport`. This preserves current CLI, JSON, static-analysis exit codes, and
Finding localization. Reference diagnostics use the same canonical severities and
stable rule identifiers, include only logical relative names and record/line numbers,
and never include raw PBED records or absolute backing paths.

An uploaded bundle is resolved only against explicitly supplied names. An authorized
local project requires a separate canonical root and explicit authorization before
supporting-file content is read. Absolute references, root escapes, canonical symlink
or junction escapes, missing targets, directory targets, ambiguous bundle names,
unsupported UTF-8, byte limits, record limits, empty data, blank lines, and invalid
five-field PBED records are deterministic failures. A file that disappears or becomes
unreadable after preview produces a sanitized SG017 diagnostic rather than exposing a
backing path.

Valid placements may be summarized and visualized. The PBED XY slice uses the
officially verified spherical interpretation: a sphere centered at `(x, y, zc)` with
outer radius `r` intersects a selected plane `z` with radius
`sqrt(r^2 - (z - zc)^2)`. This is a placement visualization only. Projected or sliced
circles do not prove three-dimensional non-overlap, packing validity, transport
correctness, or valid nested-universe geometry.

## Symbol and confidence policy

Definitions are retained in lists under an exact, case-preserved symbol-table key so
duplicate definitions are never discarded. Until Serpent object-name case behavior is
resolved for this subset, `Fuel` and `fuel` are different keys; this limitation is
included in every report.

Undefined-reference and unused-object findings describe only the supported parsed
model. Their confidence is reduced from `high` to `medium` when an unsupported
`include` or relevant unsupported `cell`, `surf`, or `mat` form could hide a definition
or reference. Severity does not change: unused objects remain informational.

## SG010 defaults

Complexity is a manual-review signal, not an invalid-physics claim. The default
deterministic limits are:

- no more than 20 signed surface references per cell;
- no more than 4 union operators per cell.

The analyzer accepts an explicit `AnalysisConfig` for tests or later application
configuration. Parentheses are still unsupported by the parser, so parenthesis depth
is not yet included in SG010.

## Parser integration and exit codes

Parser diagnostics are converted as follows:

| Parser diagnostic | Finding |
| --- | --- |
| Unterminated block comment | SG011 ERROR |
| Unsupported card/form | SG014 INFO |
| Malformed `surf`, `cell`, `mat`, or `ene`, or malformed selected `det` option | SG015 ERROR, recoverable |
| Unreadable file or invalid UTF-8 | SG015 ERROR, unrecoverable |

CLI exit codes are:

- `0`: no ERROR finding;
- `1`: one or more ERROR findings after a recoverable parse;
- `2`: parsing could not begin because the local file was unreadable or not UTF-8.

Text output groups findings by severity. JSON output is available with:

```powershell
serpentguard check examples/valid_minimal.inp --format json
```

## Explicitly deferred

- SG012 missing include and SG013 include cycle; Prompt 6B resolves `pbed` data only.
- Additional surface types, lattice/universe expansion, transformations, nested CSG,
  adaptive sampling, and 3D geometry visualization.
- Detector responses, time bins, non-Cartesian meshes, transformations, statistics,
  normalization, and purpose-dependent review.
- Material physics, normalization, temperature, depletion, or purpose-dependent review.
- AI-based detector judgment, AI-generated deterministic findings, automatic calls,
  and corrected-input generation.

See [supported syntax](supported_syntax.md) for the parser boundary and the
[canonical specification](../serpentguard_implementation_spec.md) for the long-term
roadmap.
