# First parser syntax boundary

## Status

The deterministic parser and first symbol-table milestone are implemented. The parser
deliberately covers less than Serpent and must not be described as general Serpent
input support. Parsing, static checks, and the optional XY geometry sampler are local
and offline; no detector, physics, or AI analysis occurs.

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
                      unknown-card)*

surf-card         := "surf" name supported-surface
supported-surface := "cyl" number number number
                   | "sqc" number number number

cell-card         := "cell" name universe cell-fill intersection
cell-fill         := name | "void" | "outside"
intersection      := region-term+ (":" region-term+)*
region-term       := name | "-" name

mat-card          := "mat" name density composition-line+
density           := number | "sum"
composition-line  := numeric-zaid number

unknown-card      := card-keyword raw-token*
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

### `mat`

- The header is exactly `mat NAME DENS`, where `DENS` is a finite number or `sum`.
- At least one following composition line is required.
- Each composition line is exactly a numeric ZAID/library token such as `92235.09c`
  followed by one finite fraction.
- Header options and aliases are not partially interpreted. A header with extra
  options becomes an `UnknownCard` with `SG014 INFO`.
- A missing field, invalid density, invalid ZAID/fraction pair, or absent composition
  produces `PARSER003 ERROR` and retains the card as unknown.
- Material normalization and physical meaning are not checked.

### Card boundaries and unknown cards

The scanner uses a frozen first-milestone list of known Serpent card keywords to find
the next card boundary. This is a pragmatic boundary mechanism, not a complete Serpent
lexer. Reserved cards outside the supported subset, including `include`, `det`, `ene`,
`set`, `pin`, and `lat`, are retained as `UnknownCard` with raw local span, tokens,
location, and `SG014 INFO`. An otherwise unrecognized line-start token is also retained
as a one-line unknown card.

Include cards are never opened in this milestone. This avoids path traversal,
out-of-scope file disclosure, include cycles, and ambiguity about the allowed upload
set until an explicit local-file sandbox policy is designed.

## Explicitly unsupported

- Include resolution, missing-include checks, and include-cycle checks.
- `fill` universes, pins, nests, particles, lattices, and transforms.
- Parenthesized grouping and cell complements.
- Detector and energy-grid parsing.
- Material options and full nuclide alias syntax.
- Surface types other than `cyl` and `sqc`.
- Surface geometry beyond `cyl` and `sqc`, lattice or universe expansion,
  transformations, cell complements, nested Boolean grouping, and 3D visualization.
- Quoted-string-aware comment handling.
- AI calls or explanations.

## Open questions for later milestones

1. Are user object names case-sensitive for reference matching?
2. Which identifier characters and quoted-name forms should be accepted?
3. How should comment markers inside quoted strings be handled?
4. Which additional material aliases can be distinguished safely from card boundaries?
5. What explicit root, traversal, symlink, size, cycle, and upload-set policy should
   govern local include resolution?

See [official example sources](example_sources.md) for the research behind the subset.
