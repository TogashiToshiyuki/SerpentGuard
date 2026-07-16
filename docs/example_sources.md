# Official example sources

Reviewed through 2026-07-16. The [Serpent official example collection](https://serpent.vtt.fi/mediawiki/index.php/Collection_of_example_input_files) is the primary source for this research. The linked Serpent documentation is used to confirm syntax that cannot be established safely from examples alone.

## Representative examples reviewed

| Official source | Why it was reviewed | Observed syntax relevant to the first parser |
| --- | --- | --- |
| [2D PWR pin-cell burnup example](https://serpent.vtt.fi/mediawiki/index.php/2D_PWR_pin-cell_burnup_example) | Small pin-cell model with a square outer boundary and compact material definitions. | `%` comments; `surf` with `sqc`; `cell` with `fill` and `outside`; `mat` headers followed by ZAID/fraction pairs; negative mass density and fractions. |
| [2D BWR fuel assembly geometry](https://serpent.vtt.fi/mediawiki/index.php/2D_BWR_fuel_assembly_geometry) | Representative 2D assembly with explicit surfaces, cells, and several materials. | `surf` with `sqc`; material-filled, `fill`, and `outside` cells; inline `%` comments; `mat` density `sum`; material options such as `burn`, `tmp`, `moder`, and `rgb`. |
| [2D VVER-440 fuel assembly geometry](https://serpent.vtt.fi/mediawiki/index.php/2D_VVER-440_fuel_assembly_geometry) | Assembly example that also defines an energy grid and detectors. | `surf` with `hexyc`; signed surface lists; `mat` compositions; `ene 1 3 1000 1E-9 12.0`; detectors that refer to the energy grid with `de 1`. |
| [3D BWR assembly transient example](https://serpent.vtt.fi/mediawiki/index.php/3D_PWR_assembly_transient_example) | Multi-file official example and an independent detector example. | Main inputs use `include pins`, `include geometry`, and `include materials`; the same page provides the three additional file bodies. It also contains detector cards and surfaces including `sqc`, `pz`, and `cuboid`. |

The VVER and transient examples confirm the `ene NAME 3 N EMIN EMAX` and
`det NAME ... de EGRID` relationship used by the limited detector milestone. Fixtures
remain independently written rather than copied from those models.

## Authoritative syntax references

- [General input](https://serpent.vtt.fi/docs/user_guide/general_input.html): confirms whitespace-separated input, case-insensitive card keywords, `%` comments, C-style `/* ... */` comment sections, and the fact that nested comment sections are unsupported.
- [Input syntax manual](https://serpent.vtt.fi/docs/syntax/index.html): confirms the card forms for `surf`, `cell`, `mat`, and `include`, and that a card ends when the next card begins.
- [Geometry guide](https://serpent.vtt.fi/docs/user_guide/geometry.html): confirms implicit intersection, `:` union, `-` surface complement, parentheses for precedence, and `#` cell complement.
- [Material guide](https://serpent.vtt.fi/docs/user_guide/materials.html): confirms the basic `mat NAME DENS ZAID FRAC ...` form and the sign convention for atomic and mass units.
- [CSG surface types](https://serpent.vtt.fi/docs/extra/csg_surfaces.html): confirms the parameter forms used in the fixtures: `cyl X0 Y0 R` and `sqc X0 Y0 D`.
- [Geometry plotting](https://serpent.vtt.fi/docs/user_guide/geometry_plotting.html):
  confirms that Serpent material colors are random unless the material definition
  includes `rgb R G B`, shows the option after material density, and documents RGB
  channels on the 0–255 scale. SerpentGuard parses only the exact narrow header form
  `mat NAME DENS rgb R G B`; other material-option combinations remain unsupported.
- [Detector guide](https://serpent.vtt.fi/docs/user_guide/detectors.html): confirms
  optional particle tokens, `de EGRID`, and uniform Cartesian detector meshes
  `dx XMIN XMAX NX`, `dy YMIN YMAX NY`, and `dz ZMIN ZMAX NZ`. It also confirms that
  omitted dimensions are integrated rather than proving that a particular binning
  choice is appropriate.
- [Input syntax manual](https://serpent.vtt.fi/docs/syntax/index.html#ene): confirms
  `ene` type 1 explicit boundaries and type 2/3 generated grids, including the number
  of bins and minimum/maximum energies.

### PBED and external geometry data

PBED research was repeated on 2026-07-15 against the current official Serpent 2
documentation (document version 0.20.0 for Serpent update 2.2.4) and the legacy
Serpent manual:

- [HTGR geometries](https://serpent.vtt.fi/docs/user_guide/geometry.html) defines
  `pbed UNI0 BGU "FILE" [ pow ]`. `UNI0` is the pebble-bed universe, `BGU` is
  the background universe, and `FILE` contains spherical sub-universe placements.
  Its example distribution uses one `X Y Z R UNI` record per line.
- [Input syntax manual: `pbed`](https://serpent.vtt.fi/docs/syntax/index.html#pbed)
  confirms the card arguments, the surrounding background universe, and the
  optional `pow` output request.
- [General input](https://serpent.vtt.fi/docs/user_guide/general_input.html)
  confirms that Serpent input strings containing whitespace, including paths, are
  enclosed in quotation marks. This describes the `pbed` card, not comment syntax
  inside the separate PBED distribution file.
- [Pebble-bed power distribution output](https://serpent.vtt.fi/docs/user_guide/other_output.html#pebble-bed-power-distribution-file)
  confirms that the first five output values reproduce the distribution input's
  coordinates, outer radius, and universe.
- [Legacy Serpent manual](https://serpent.vtt.fi/download/Serpent_manual.pdf),
  section 3.8.2, independently gives `pbed <u0> <uf> "<inputfile>" [<options>]`
  and one `<x> <y> <z> <r> <u>` record per particle or pebble.

Facts verified from those official sources:

- each supported PBED record has exactly five fields: center coordinates `X Y Z`,
  outer sphere radius `R`, and particle/pebble universe `UNI`;
- geometry lengths use Serpent's centimetre convention;
- the optional card token currently documented is `pow`;
- the distribution represents explicit spherical sub-universes, while space between
  them belongs to the background universe.

The official pages do not document comments, headers, delimiters other than
whitespace, or blank-record semantics in the PBED distribution file. SerpentGuard
therefore does not invent any PBED comment or header syntax.

## Private local structural validation

Two unpublished local research files were inspected only for the minimum structural
validation needed by Prompt 6B. They are intentionally not named or linked here.

Observed in the private sample:

- one `pbed` card used the documented four-token form: keyword, two universe tokens,
  and a quoted relative `.dat` target;
- the target name contained no directory separator and resolved beside the main
  input;
- no other supported external geometry reference was present;
- the referenced file contained 5,000 meaningful records, all with five numeric
  tokens, and no comment markers were observed in the inspected structure.

These observations agree with the official five-column PBED syntax. They do not
establish a general path-search rule, filename convention, numeric-only universe-name
requirement, or PBED comment syntax.

SerpentGuard-specific policy decisions (not claims about unrestricted Serpent
behavior):

- only relative `pbed` targets are resolved;
- uploaded targets must be present explicitly in the uploaded bundle;
- local targets must resolve canonically inside an explicitly authorized root;
- absolute targets and root escapes are rejected;
- PBED text must be UTF-8 and each non-blank data line must match the verified
  five-field form.

Unresolved questions are handled conservatively:

- the official PBED pages call `FILE` a file path but do not define its base-directory
  lookup rules for every runtime invocation;
- PBED distribution-file comment and header behavior is not documented in the
  reviewed sources;
- physical packing validity, allowed universe-name character sets, and behavior of
  duplicate placement records are outside this milestone.

## Include-file observation

The transient example demonstrates recursive input composition with three relative include targets. The syntax manual states `include "FILE"`, says processing returns to the original input after the included file is complete, and requires included files to contain complete cards. Include resolution is deliberately deferred; the first parser will preserve the card without reading the referenced file.

## Copyright and redistribution

No official input file has been copied into this repository. The repository fixtures are short, independently written cases that use generic names, original numeric values, and only the observed syntax patterns. Source links and high-level descriptions are retained for traceability.

The reviewed Wiki pages did not expose a clear redistribution licence for their input text through the available About or disclaimer links. Until redistribution terms are confirmed, official example bodies should remain external references rather than repository content.
