# Supported checks

## Current implementation status

SerpentGuard performs deterministic preprocessing, limited syntactic parsing,
symbol-table analysis, and user-triggered XY geometry sampling of the supported parsed
model. It does not perform detector review, physics validation, or AI analysis.

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

SG008 and SG009 evaluate every union-separated intersection term independently. For
example, `-s : s` does not contradict itself because the two signs occur in separate
union branches. These static rules do not evaluate Boolean geometry; the separate
sampler below evaluates only the documented subset.

## Limited XY geometry sampling

Geometry sampling is a separate language-independent numerical operation, not a
`Finding` rule and not part of CLI exit status. In the Streamlit interface, the user
must explicitly confirm `xmin`, `xmax`, `ymin`, `ymax`, a z coordinate, and a square
grid resolution before sampling starts. Range endpoints are included.

Only parsed cells whose complete region expression uses one unambiguous, valid `cyl`
or `sqc` definition are evaluated. A cell with an unsupported, undefined, duplicate,
or malformed surface—or unsupported cell syntax—is listed as excluded and is never
approximated. The reported classifications therefore describe the included supported
cells. If no cells can be evaluated, every grid point is indeterminate.

Each point is classified as:

- undefined-region candidate when zero included cells match;
- normal when exactly one included cell matches;
- overlap candidate when two or more included cells match;
- indeterminate when a supported surface lies within the configured absolute boundary
  tolerance, or no cell can be evaluated.

The code default for boundary tolerance is `1e-9`; the interface exposes it explicitly.
The result includes a Matplotlib classification plot, point counts, deterministic
representative coordinates, involved cell names for overlap candidates, excluded-cell
reasons, and the confirmed range and resolution. z is recorded for the selected XY
slice, while the currently supported infinite-z `cyl` and `sqc` forms are invariant in
z.

This is a sampling aid, not a geometric proof. Narrow gaps or overlaps between grid
points may be missed, and the check does not replace the Serpent geometry plotter.

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
| Malformed `surf`, `cell`, or `mat` retained as unknown | SG015 ERROR, recoverable |
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

- SG012 missing include and SG013 include cycle, pending a safe include sandbox.
- Additional surface types, lattice/universe expansion, transformations, nested CSG,
  adaptive sampling, and 3D geometry visualization.
- Detector and energy-grid semantic review.
- Material physics, normalization, temperature, depletion, or purpose-dependent review.
- AI calls or explanations.

See [supported syntax](supported_syntax.md) for the parser boundary and the
[canonical specification](../serpentguard_implementation_spec.md) for the long-term
roadmap.
