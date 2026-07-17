# Supported syntax

## Status

The deterministic parser and first symbol-table milestone are implemented. The parser
deliberately covers less than Serpent and must not be described as general Serpent
input support. Parsing, static checks, and the optional XY geometry sampler are local
and offline. Limited detector/energy-grid parsing and checks are implemented. The
optional AI service can explain only a reviewed structured payload after consent; it
does not parse input or change deterministic results. No transport-physics analysis
occurs.

## Input and lexical behavior

- Files passed to the CLI are read as UTF-8. Invalid UTF-8 produces
  `PARSER_ENCODING`; an unreadable file produces `PARSER_IO`.
- CRLF and bare CR newlines are normalized to LF before parsing.
- Source file names and inclusive one-based line spans are retained on parsed objects,
  unknown cards, and parser diagnostics.
- Card keywords are matched case-insensitively. Object names and their original case
  are preserved; the current symbol table matches them exactly and case-sensitively.
- A `%` character begins a comment through the end of its line.
- `/*` begins a block comment and `*/` ends it. Block comments may span lines and do
  not nest. An unterminated block comment produces `SG011` at its opening line.
- Comment contents are replaced with spaces during preprocessing. Newline and
  character counts remain stable, and comments do not become parsed card data.
- A card keyword must be the first non-whitespace token on a logical line. A keyword
  appearing in a comment or later on another card's line is not a definition.
- Multiple card starts on one physical line, quoted strings, and escape processing
  are not supported.

The parser does not log input text. Parsed models retain only each card's local raw
span where needed for local inspection and unknown-card preservation. The CLI prints
counts and structured finding messages, never raw card or file contents.

## Implemented grammar

This notation describes the SerpentGuard subset, not the complete Serpent grammar.

```text
document          := (comment | blank | surf-card | cell-card | mat-card |
                      ene-card | det-card | pbed-card | unknown-card)*

surf-card         := "surf" name supported-surface
supported-surface := "cyl" number number number
                   | "sqc" number number number

cell-card         := "cell" name universe cell-fill intersection
cell-fill         := name | "void" | "outside"
intersection      := region-term+ (":" region-term+)*
region-term       := name | "-" name

mat-card          := "mat" name density ["rgb" rgb-channel rgb-channel rgb-channel]
                     composition-line+
density           := number | "sum"
rgb-channel       := integer from 0 through 255
composition-line  := numeric-zaid number

ene-card          := "ene" name "1" boundary boundary*
                   | "ene" name ("2" | "3") integer number number

det-card          := "det" name [particle] detector-option*
particle          := "n" | "p" | "g"
detector-option   := "de" name
                   | ("dx" | "dy" | "dz") number number integer
                   | unsupported-detector-option

unknown-card      := card-keyword raw-token*

pbed-card         := "pbed" universe background-universe quoted-relative-path
                     ["pow"]
pbed-record       := number number number positive-number universe
```

`number` is accepted when Python can parse it as a finite floating-point value,
including ordinary decimal and scientific notation. Names and universes are opaque,
non-whitespace tokens. The parser does not claim to validate Serpent's full identifier
rules.

### `surf`

- A supported card occupies exactly one meaningful line.
- `cyl X0 Y0 R` and `sqc X0 Y0 D` each require exactly three finite numbers.
- Other surface types are retained as `UnknownCard` with `SG014 INFO`.
- Bad field counts or malformed numeric parameters are retained as `UnknownCard` with
  `PARSER001 ERROR`.
- Static parsing does not assign geometry meaning. The separate geometry sampler
  accepts only a positive third parameter and evaluates `cyl X0 Y0 R` as a circle
  centered at `(X0, Y0)` with radius `R`, and `sqc X0 Y0 D` as an axis-aligned square
  centered at `(X0, Y0)` with half-width `D`.

### `cell`

- A supported card occupies exactly one meaningful line and has a cell name,
  universe, fill value, and one or more region terms.
- A fill value is an opaque material name, `void`, or `outside`.
- A plain surface name represents its positive side; `-NAME` represents its negative
  side. Signed and unsigned reference lists are extracted in source order.
- Adjacent region terms form an implicit intersection. `:` separates shallow union
  branches, including when it is attached to neighboring references such as `-a:b`.
  The parser stores both the flattened references and each intersection term.
- `fill`, parentheses, cell complement (`#`), a leading `+`, empty union branches, and
  other non-subset region forms make the whole card an `UnknownCard` with `SG014 INFO`.
- Missing fields produce `PARSER002 ERROR`.
- The static analyzer checks exact-name references, duplicate signed conditions, and
  contradictory signs independently within each union branch.
- For geometry sampling only, a negative reference selects signed distance less than
  zero (inside), and a positive reference selects signed distance greater than zero
  (outside). Adjacent references are intersected and `:` branches are unioned.
- Geometry sampling filters parsed Cells by their exact, canonical `universe` value
  before evaluation. Exactly one Universe is sampled per run in its own local
  coordinate system; match counts are never combined across Universes.
- Same-name Cell definitions are considered geometry duplicates only within the
  selected Universe. Every same-Universe duplicate definition is excluded from the
  sampler. SG002 remains the canonical static-analysis finding.

### Geometry completeness policy

The geometry sampler reports undefined-region candidates only when every parsed Cell
definition assigned to the selected Universe can be evaluated. A selected-Universe
Cell is excluded when it has unsupported syntax, a missing/unsupported/ambiguous/
malformed Surface, an empty region, or a duplicate name.

If any Cell is excluded, the Universe is marked incomplete. A point with zero
supported Cell matches is then indeterminate—not an undefined-region candidate—because
an excluded Cell may cover it. A single supported match means only that one evaluated
Cell matched; it is not a claim of global uniqueness. Two or more supported matches
remain a supported-subset overlap candidate, with the incomplete-domain limitation
attached to the result.

In the current five-state diagnostic grid, incomplete coverage is rendered
conservatively: both zero-match and one-supported-match points are classified as
`incomplete`, while the supported match count remains available as metadata. This
prevents a partly evaluated point from masquerading as a globally normal material.

The accepted three-parameter `cyl` and `sqc` forms extend indefinitely in z. The
canonical geometry configuration retains a reserved z value, but changing it has no
effect on current classifications. No z-dependent geometry is implied.

### `mat`

- The header is exactly `mat NAME DENS` or `mat NAME DENS rgb R G B`, where `DENS`
  is a finite number or `sum` and each RGB channel is an integer from 0 through 255.
- The optional RGB triplet is retained for material-color rendering. This deliberately
  narrow implementation does not search for `rgb` among other material options.
- At least one following composition line is required.
- Each composition line is exactly a numeric ZAID/library token such as `92235.09c`
  followed by one finite fraction.
- Other header options, option orders, and aliases are not partially interpreted. A
  header with extra unsupported options becomes an `UnknownCard` with `SG014 INFO`.
- A missing field, invalid density, invalid ZAID/fraction pair, or absent composition
  produces `PARSER003 ERROR` and retains the card as unknown.
- Material normalization and physical meaning are not checked.

### Geometry and diagnostic views

Sampling stores compact integer category grids and ordered lookup tables; it does not
store one translated string at every grid point. The Geometry view uses the unique
matched supported Cell to display categories by exact material or Cell name. `void`,
`outside`, unsupported/incomplete, undefined, and indeterminate states remain explicit
categories. Overlap and boundary-uncertain points are not assigned a normal material.

The separate Diagnostic view displays normal supported points, supported-subset
overlaps, undefined candidates (complete coverage only), incomplete/unsupported
points, and boundary-indeterminate points. Both views use nearest-neighbor discrete
rendering and one selected Universe. They are limited SerpentGuard visualizations and
do not replace Serpent's geometry plotter.

### `ene`

The parser supports only the three formats confirmed by the current official syntax:

- `ene NAME 1 E1 E2 ...` retains a finite explicit boundary list. Officially, the
  list may be ascending or descending. The inferred bin count is one less than the
  number of boundaries; fewer than two boundaries produces SG023.
- `ene NAME 2 N EMIN EMAX` describes a uniform grid.
- `ene NAME 3 N EMIN EMAX` describes a log-uniform grid.

`N` must be a syntactic base-10 integer, while energies must be finite numbers. A
non-positive `N` is parsed so SG023 can report it. For types 2 and 3, `EMIN >= EMAX`
produces SG024. Other numeric grid types are retained as `UnknownCard`/SG014 rather
than being assigned undocumented behavior. Malformed supported forms produce
`PARSER004`/SG015.

### `det`

The first detector subset supports only:

- an exact detector name and optional particle token `n`, `p`, or `g`;
- `de EGRID`, retaining an exact-case energy-grid reference;
- `dx XMIN XMAX NX`, `dy YMIN YMAX NY`, and `dz ZMIN ZMAX NZ`, retaining finite
  Cartesian limits and an integer bin count.

Options are recognized as whitespace-separated option tokens, including across
lines. Each selected option may occur once. Repeated selected options and documented
but unsupported options (`dr`, `dm`, `dc`, `du`, `dn`, `dh`, `ds`, `dt`, and the
other official `d*` families) are stored in `Detector.unsupported_options` and produce
SG027 INFO. Their arguments are not interpreted. A malformed selected option produces
`PARSER005`/SG015 while the detector and option tokens remain locally inspectable.

This is not complete detector syntax. SerpentGuard does not interpret responses,
materials, Cells, surfaces, detector flags, transformations, special detector modes,
files, time bins, or purpose-dependent questions. In particular, it does not decide
whether axial or energy binning is appropriate for a user's analysis.

### `pbed` external placement data

PBED support is deliberately separate from the core `ParsedModel`: the existing
parser still retains the `pbed` input card as an `UnknownCard`/SG014 so CLI and JSON
behavior remain backward-compatible. The external-reference layer recognizes only
the officially documented form:

```text
pbed UNI0 BGU "FILE" [ pow ]
```

The supported card must occupy one meaningful line, matching the private structural
observation without generalizing to every whitespace arrangement Serpent may accept.
`UNI0` and `BGU` are preserved as opaque universe tokens. `FILE` must be quoted and
must be a relative file path under the selected resolution policy. Quoted paths may
contain spaces, consistent with the official general-input rules. The optional token,
when present, must be `pow`.

The resolved UTF-8 PBED distribution is read incrementally. Every physical data line
must contain exactly:

```text
X Y Z R UNI
```

`X`, `Y`, and `Z` are finite sphere-center coordinates in centimetres. `R` is a
finite, strictly positive outer sphere radius in centimetres. `UNI` is preserved as
an opaque non-whitespace universe token. Malformed records are excluded and diagnosed;
they never create placement geometry. The reader enforces configurable byte and
record limits and does not retain raw lines.

The PBED distribution-file sources reviewed do not document comments, headers, or
blank-record semantics. Accordingly, blank lines and lines containing anything other
than five fields are malformed; Serpent input `%` and `/* ... */` comment rules are
not projected onto PBED data. A final line terminator by itself does not create an
additional record.

Supported resolution modes are:

- **Uploaded bundle:** normalize relative names within the explicitly uploaded set,
  compare them case-insensitively using Windows path semantics, reject duplicate or
  ambiguous names, and report unused supporting uploads.
- **Authorized local project:** canonicalize the main file, authorized root, and each
  target before access. The main file and target must be regular files inside that
  root. Absolute targets, traversal/root escapes, and canonical symlink or junction
  escapes are rejected. Supporting content is not read until explicit authorization.

No directory, drive, or home-folder scanning is performed. Backslashes and mixed
separators are normalized for policy checks; `.` is collapsed; `..` is allowed only
when the final normalized and canonical target remains inside the authorized root.
Windows comparisons are case-insensitive, and Unicode path components and quoted
spaces are preserved. Windows-invalid characters, reserved device names, and trailing
spaces/dots in path components are rejected early.

The typed PBED result includes source-relative name, valid placements, one-based
record/line indexes, valid and malformed record counts, sphere-extent bounding box,
and sanitized diagnostics. It never serializes an absolute backing path or full raw
file content.

### Card boundaries and unknown cards

The scanner uses a frozen first-milestone list of known Serpent card keywords to find
the next card boundary. This is a pragmatic boundary mechanism, not a complete Serpent
lexer. Supported `det` and `ene` cards use only the narrow forms above. Reserved cards
outside the supported subset, including `include`, `set`, `pin`, and `lat`, are
retained as `UnknownCard` with raw local span, tokens, location, and `SG014 INFO`. An
otherwise unrecognized alphabetic line-start token is also retained as a one-line
unknown card instead of being absorbed into the preceding supported definition.
`surf` and `cell` are always bounded to their documented single line. Ambiguous
numeric continuation lines still follow the current card because SerpentGuard does
not claim a complete lexer.

Include cards remain unopened. Prompt 6B resolves only verified `pbed` external
placement files through the explicit uploaded-bundle or authorized-root policy.

## Explicitly unsupported

- Include resolution, missing-include checks, and include-cycle checks.
- External-reference cards other than `pbed`.
- PBED comments, headers, alternate column counts, binary files, implicit path search,
  physical packing validation, and pebble/universe CSG expansion.
- `fill` universes, pins, nests, particles, lattices, and transforms.
- Universe expansion or placement: a selected Universe is evaluated only in its own
  local coordinates.
- Parenthesized grouping and cell complements.
- Detector options and energy-grid forms beyond the explicitly documented subset;
  detector response physics and purpose-dependent judgment.
- Material options and full nuclide alias syntax.
- Surface types other than `cyl` and `sqc`.
- Surface geometry beyond `cyl` and `sqc`, lattice or universe expansion,
  transformations, cell complements, nested Boolean grouping, and 3D visualization.
- Quoted-string-aware comment handling.
- Automatic AI calls, raw-input transmission, AI-based deterministic rules, input
  rewriting, and any AI claim of complete physical validation.

## Open questions for later milestones

1. Are user object names case-sensitive for reference matching?
2. Which identifier characters and quoted-name forms should be accepted?
3. How should comment markers inside quoted strings be handled?
4. Which additional material aliases can be distinguished safely from card boundaries?
5. Should a later include resolver reuse the PBED sandbox while retaining Serpent's
   documented original-base-file/current-working-directory include semantics?
6. Does any supported Serpent release accept comments or headers inside PBED placement
   files, and if so, what exact grammar applies?

See [official example sources](example_sources.md) for the research behind the subset.
