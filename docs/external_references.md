# External-reference and PBED architecture

## Security boundary

`src/serpentguard/references.py` owns source documents, normalized logical names,
PBED-card extraction, resolution policy, uploaded-bundle matching, authorized-root
resolution, and sanitized resolution reports. `src/serpentguard/pbed.py` owns the
incremental five-field PBED reader and typed placement data. Neither module imports
Streamlit or performs network access.

Backing bytes or canonical local paths are private implementation details of source
documents and are excluded from object representations. Public reports contain only
normalized logical names, byte counts, record counts, status, and structured
diagnostics. Absolute paths and raw source/PBED text are not serializable report fields.

## Uploaded bundle

The bundle consists only of the explicitly uploaded main document and supporting
documents. Names are normalized with Windows-style relative path rules and compared
case-insensitively. No filesystem lookup supplements a missing upload. Duplicate
normalized names make a reference ambiguous. Resolution reports identify both used
and unused supporting names.

## Authorized local project

The caller supplies a main path and an independent authorized root. Both are resolved
canonically and the main file must be inside the root. Resolving a PBED target follows
these steps:

1. reject an absolute target;
2. combine the relative target with the main document's directory;
3. resolve the candidate canonically, following symlinks/junctions where the platform
   exposes them;
4. verify the canonical target remains under the canonical authorized root;
5. verify it is a regular file and enforce the byte limit;
6. read supporting content only after explicit caller authorization.

Entering an absolute main path grants access only to that file after the separate root
check; it does not authorize siblings, parents, or a wider user directory. The resolver
never searches a drive or infers a root.

## PBED parsing and visualization boundary

The PBED reader streams UTF-8 lines, validates exactly five fields on every physical
data line, keeps only typed valid placements, and records sanitized diagnostics for
excluded records. Blank lines are rejected because blank-record semantics were not
verified. Configurable
file-size and record-count limits are checked before or during parsing. It does not log
raw lines or build a second full-file text copy.

The visualization helper provides two explicitly labeled modes: mathematically
correct sphere cross-sections at an explicit z plane, and an XY center projection
using the documented outer radius. Placements are grouped by verified Universe with
one collection and legend entry per Universe rather than per record. It does not
expand referenced particle universes, evaluate the background universe, test physical
packing, or claim that the projection proves absence of 3D overlap. Existing
`cyl`/`sqc` geometry sampling remains a separate operation with unchanged semantics.

Browser upload controls commonly expose only basenames. The core bundle resolver can
match explicit logical relative names, but a subdirectory reference may require
authorized-local-project mode when the browser does not preserve relative paths.
Canonical resolution detects normal symlink and Windows junction escapes where the
platform exposes them; as with ordinary pathname APIs, it cannot make a mutable
filesystem race-free.

## Dependency scope

Only one dependency edge type exists in Prompt 6B: a main Serpent `pbed` card to one
PBED distribution file. PBED files are not recursively scanned for references, so
cycles are not possible in the supported graph. `include` and every other external
reference family remain unsupported.
