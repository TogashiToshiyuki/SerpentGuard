# SerpentGuard demo fixtures

These small inputs are independently written for a public SerpentGuard demo. They
exercise only the documented subset, are freely redistributable with this repository,
and are not production reactor models. Every file repeats its purpose, expected
result, and geometry settings in `%` comments so it remains self-describing when
uploaded by itself.

| Order | Fixture | Purpose | Expected result | Geometry settings |
| ---: | --- | --- | --- | --- |
| 1 | `01_valid_minimal.inp` | Establish the clean local-analysis path. | No findings. | Not required. |
| 2 | `02_undefined_surface.inp` | Show a source-located blocking reference error. | SG004 ERROR. | Not required; the incomplete Cell is excluded if sampled. |
| 3 | `03_contradictory_region.inp` | Show deterministic region-expression review. | SG008 WARNING. | Not required. |
| 4 | `04_pwr_pin_cell.inp` | Show the limited Geometry view with fuel, clad, coolant, and outside regions. | No static findings; three material categories plus outside. | Universe `0`; `xmin=-0.75`, `xmax=0.75`, `ymin=-0.75`, `ymax=0.75`; resolution `121`. |
| 5 | `05_overlap_and_gap.inp` | Contrast the Diagnostic view with the material/cell Geometry view. | Supported overlap candidates and undefined-region candidates after sampling. | Universe `0`; `xmin=-0.8`, `xmax=0.8`, `ymin=-0.8`, `ymax=0.8`; resolution `121`. |
| 6 | `06_detector_issues.inp` | Show limited `det`/`ene` checks without physics judgment. | SG021, SG022, SG023, and SG024 ERROR findings. | Not required. |
| 7 | `07_ai_review.inp` | Produce a compact structured payload for the optional consent-gated AI explanation. | SG004 ERROR, SG007 INFO, and SG014 INFO. | Not required; use purpose `Explain the blocking preflight issue for a model author.` |

See [`docs/demo_script.md`](../../docs/demo_script.md) for the timed three-minute
sequence. The demo does not require a live OpenAI request: the local payload preview
and consent gate can be shown without an API key. If a live optional explanation is
used, configure the key and model only in the launch shell and never show them on
screen.
