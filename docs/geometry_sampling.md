# Geometry-sampling architecture

## Boundary and ownership

`src/serpentguard/geometry.py` owns the language-neutral numerical sampler and its
typed configuration, workload estimate, exclusions, and result metadata.
`src/serpentguard/geometry_plot.py` converts a canonical result into Matplotlib
figures without importing Streamlit. `app.py` owns input widgets, tabs, session state,
localized wording, and display only. Geometry sampling does not create or modify
`Finding`, `AnalysisReport`, parser, or CLI data.

## Universe-local preparation

`available_universes()` derives selector choices only from supported parsed Cells.
Each `GeometrySamplingConfig` requires one exact `target_universe`. Universe `0` is
preferred by `default_target_universe()` when present; otherwise the lexically first
available value is used. An unavailable target is rejected before sampling.

Only Cells whose canonical `Cell.universe` equals the target are prepared. Unsupported
retained Cell cards are associated with their tokenized Universe when available. A
malformed Cell whose Universe cannot be recovered is conservatively relevant to every
target Universe. Match counts are never shared between Universes.

The sampler evaluates the selected Universe in its own local coordinate system only.
It does not place or expand `fill`, pins, lattices, repeated geometry, transformations,
or nested Universes.

## Exclusion and completeness

A Cell is excluded when its complete region cannot be evaluated safely. Current
reasons include unsupported Cell syntax, empty regions, missing or unsupported Surface
definitions, ambiguous duplicate Surface definitions, malformed Surface parameters,
and duplicate Cell names.

Duplicate Cell names are grouped within the selected Universe. Every definition in a
same-Universe duplicate group is excluded, so duplicate definitions cannot create an
artificial geometric overlap. Equal names in different Universes are independent for
geometry preparation. SG002 remains unchanged as the static-analysis diagnostic.

`GeometrySamplingResult.coverage_complete` is true only when no selected-Universe Cell
was excluded. `undefined_detection_enabled` mirrors that conservative policy:

- complete coverage: zero matches is an undefined-region candidate;
- incomplete coverage: zero supported matches is indeterminate because an excluded
  Cell may cover the point;
- one supported match under incomplete coverage is not a global uniqueness claim;
- two or more definite supported matches remain a supported-subset overlap candidate.

The result retains supported match counts and records selected Universe,
supported/excluded Cell counts, incomplete-domain count, signed-reference count, and
the workload estimate. Translated labels are derived only while rendering.

The five-state diagnostic grid classifies zero or one supported match as incomplete
whenever coverage is incomplete. The raw supported match count is still retained, but
the point is not presented as a globally unique normal region.

## Canonical occupancy and separate views

For each point with exactly one definite supported match, the sampler retains the
matched prepared-Cell index. It derives compact `int32` Cell and material category
grids plus ordered, language-neutral category tables. Material and Cell names remain
exactly as parsed. No translated labels are written into the result, and strings are
not duplicated per grid point.

The default Geometry view renders one occupancy grid with nearest-neighbor discrete
colors and a categorical legend. The separate Diagnostic view renders normal,
supported-subset overlap, undefined candidate, incomplete/unsupported, and boundary-
indeterminate states. It uses a categorical legend rather than a continuous colorbar.
Equal XY aspect ratio and the requested bounds are retained in both views.

Application colors are deterministic for the ordered supported subset. Reserved
colors identify outside, void, unsupported, indeterminate, and undefined states. If a
material was parsed with the exact supported `rgb R G B` header option, the UI can use
that verified triplet; otherwise colors may differ from Serpent.

Matplotlib font selection is presentation-only. English has no Japanese-font
dependency. Japanese rendering validates installed platform candidates, preferring
Yu Gothic/Meiryo on Windows, Hiragino fonts on macOS, and Noto Sans CJK JP or Noto Sans
JP on Linux. No font is downloaded or redistributed. If validation fails, the UI
warns and uses English inside plots to avoid tofu glyphs.

## Numerical and workload policy

`cyl X0 Y0 R` and `sqc X0 Y0 D` use signed distance in XY. Values whose absolute
signed distance is at most `DEFAULT_BOUNDARY_TOLERANCE` (`1e-9`) are indeterminate.
Both supported forms extend indefinitely in z. The configuration retains z for future
surface types, but current classifications are explicitly z-invariant and the UI
disables the control.

Before grid coordinates or masks are allocated, the sampler estimates:

```text
grid_points * (evaluated_cells + signed_surface_references)
```

The default limit is `50,000,000` estimated operations. Excessive requests raise
`GeometryWorkloadError`. During accepted runs, match counts and uncertainty are updated
one Cell at a time; full-grid masks are not retained for every Cell. Representative
Cell names are reconstructed only for the small number of reported coordinates.

This remains uniform-grid sampling. Narrow gaps or overlaps can be missed, and the
result does not replace the Serpent geometry plotter.
