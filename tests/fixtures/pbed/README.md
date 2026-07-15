# Synthetic PBED fixtures

Every file in this directory is independently written for SerpentGuard tests. The
coordinates, names, and dimensions are arbitrary and do not describe a production
reactor, unpublished research geometry, or a physically valid pebble packing.

- `valid/` is a small relative PBED reference with three synthetic spheres.
- `missing/` references a deliberately absent supporting file.
- `malformed/` contains one valid record and independently invented malformed records.
- `traversal/` attempts to leave the explicit bundle/root.
- `absolute/` uses a fictitious absolute Windows target that must be redacted and
  rejected.
- `unicode/` verifies an independently chosen Japanese supporting filename.

Record-limit and duplicate-name cases are generated directly in tests so no large or
ambiguous fixture files are stored in the repository.
