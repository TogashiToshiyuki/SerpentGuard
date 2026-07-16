# Synthetic detector fixtures

These inputs are independently written, minimal syntax exercises. They are not copied
from an official example and do not represent a production reactor model. Official
examples and syntax pages are cited in `docs/example_sources.md`.

- `valid_detector.inp` demonstrates supported `ene`, `de`, `dx`, and `dy` forms plus
  one deliberately retained unsupported `dr` option.
- `invalid_detector.inp` contains independent deterministic preflight failures for
  duplicate names, an undefined energy grid, non-positive bins, and reversed bounds.
