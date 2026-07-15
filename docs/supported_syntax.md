# First parser syntax boundary

## Status

This is a research and fixture contract only. No parser is implemented yet. The contract intentionally covers less than Serpent itself and must not be described as general Serpent input support.

## Confirmed lexical behavior

- Card keywords are case-insensitive. Original spelling and source locations should still be retained.
- A `%` character starts a comment that continues to the end of the line.
- `/*` starts a block comment and `*/` ends it; a block comment may span lines.
- Nested block comments are not supported by Serpent and will not be supported.
- An unterminated block comment is expected to produce `SG011`.
- Whitespace separates tokens in Serpent. For milestone one, every card keyword must be the first non-whitespace token on a logical line. Supporting multiple card starts on one physical line is deferred.
- Fixtures use ASCII only. Input encoding and newline-normalization policy remain open questions.

Comment removal must retain newline counts so later findings can report original line numbers. Comment text is not part of parsed card data.

## Milestone-one grammar

The notation below is a SerpentGuard subset, not the complete Serpent grammar.

```text
document          := (comment | blank | surf-card | cell-card | mat-card |
                      unknown-card)*

surf-card         := "surf" name surface-type number+
supported-surface := "cyl" number number number
                   | "sqc" number number number

cell-card         := "cell" name universe cell-fill region-term+
cell-fill         := name | "void" | "outside"
region-term       := name | "-" name

mat-card          := "mat" name density composition-line+
density           := number | "sum"
composition-line  := numeric-zaid number

unknown-card      := reserved-card-keyword raw-token*
```

`number` means a finite decimal or scientific-notation token with an optional sign. `name`, `universe`, and `surface-type` are retained as opaque non-whitespace tokens; the first parser will not claim to validate the complete Serpent identifier character set.

### `surf`

- Required fields: name, type, and numeric parameters.
- Structured support is limited to `cyl X0 Y0 R` and `sqc X0 Y0 D`.
- Parameter counts are exactly three for these two forms.
- Other surface types are known to exist but are preserved as unsupported raw cards in this milestone. Geometry evaluation is not performed.

### `cell`

- Required fields: cell name, universe, fill value, and at least one region term.
- A fill value may be a material name, `void`, or `outside`.
- A plain surface name selects its positive side; `-NAME` selects its complemented side.
- Adjacent region terms mean intersection. This is the only Boolean form supported in milestone one.
- `fill UNI`, union (`:`), parentheses, and cell complement (`#CELL`) are confirmed Serpent syntax but are deliberately out of scope.

### `mat`

- The supported header is exactly `mat NAME DENS`, where `DENS` is a finite number or `sum`.
- At least one composition pair is required by the milestone contract.
- Each supported composition line contains one numeric ZAID/library token, such as `92235.09c`, and one finite numeric fraction.
- Material header options (`moder`, `burn`, `vol`, `mass`, `tmp`, `tms`, `tft`, `rgb`, and others) are confirmed syntax but are not interpreted in milestone one. A material using them must be preserved as unsupported rather than partially validated.
- Element-symbol aliases, multiple composition pairs on one line, and mixing atomic and mass units are outside the first subset.

### Card boundaries and unknown cards

Serpent ends a card when the next reserved card keyword begins. The first parser plan therefore needs a versioned list of official reserved card keywords for boundary detection; it must not guess boundaries from blank lines.

Reserved cards other than `surf`, `cell`, and the limited `mat` form—including `include`, `det`, `ene`, `set`, `pin`, and `lat`—must be retained as `UnknownCard` records with keyword, raw tokens/text, and source location. They are expected to produce `SG014` and must never be silently treated as validated. Include files are not opened in this milestone.

## Explicitly deferred syntax

- Include-file resolution, missing-file checks, and include-cycle checks.
- `fill` universes, pins, nests, particles, and lattices.
- Cell union, grouping, and cell complements.
- Detector and energy-grid parsing.
- Material options and full nuclide alias syntax.
- Surface types other than `cyl` and `sqc`.
- Geometry evaluation, overlap checks, and undefined-region checks.
- Quoted strings and escape behavior.

## Open questions

1. Are user-defined object names case-sensitive for reference matching? Card keywords are confirmed case-insensitive, but the reviewed sources did not clearly settle object-name matching. Milestone code must preserve original case until this is resolved.
2. Which identifier characters are valid in current Serpent 2 object names, and are quoted names accepted for these three cards?
3. How are `%`, `/*`, and `*/` treated inside quoted strings?
4. How should an arbitrary non-reserved token encountered after a `mat` header be distinguished from a supported composition alias without implementing the full material grammar?
5. Which finding ID and severity should represent a recognized `surf` or `mat` card whose subtype/options are outside this limited subset? `SG014` currently names unsupported cards, not unsupported forms of supported cards.
6. Should union and parentheses enter the first parser before cell complement, or should all three remain a later region-expression milestone?
7. Include paths are documented relative to the original base input or working directory, but the safe local-file sandbox and traversal policy still needs a project decision before include resolution is implemented.

See [official example sources](example_sources.md) for the evidence behind these decisions.
