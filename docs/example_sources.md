# Official example sources

Reviewed on 2026-07-15. The [Serpent official example collection](https://serpent.vtt.fi/mediawiki/index.php/Collection_of_example_input_files) is the primary source for this research. The linked Serpent documentation is used to confirm syntax that cannot be established safely from examples alone.

## Representative examples reviewed

| Official source | Why it was reviewed | Observed syntax relevant to the first parser |
| --- | --- | --- |
| [2D PWR pin-cell burnup example](https://serpent.vtt.fi/mediawiki/index.php/2D_PWR_pin-cell_burnup_example) | Small pin-cell model with a square outer boundary and compact material definitions. | `%` comments; `surf` with `sqc`; `cell` with `fill` and `outside`; `mat` headers followed by ZAID/fraction pairs; negative mass density and fractions. |
| [2D BWR fuel assembly geometry](https://serpent.vtt.fi/mediawiki/index.php/2D_BWR_fuel_assembly_geometry) | Representative 2D assembly with explicit surfaces, cells, and several materials. | `surf` with `sqc`; material-filled, `fill`, and `outside` cells; inline `%` comments; `mat` density `sum`; material options such as `burn`, `tmp`, `moder`, and `rgb`. |
| [2D VVER-440 fuel assembly geometry](https://serpent.vtt.fi/mediawiki/index.php/2D_VVER-440_fuel_assembly_geometry) | Assembly example that also defines an energy grid and detectors. | `surf` with `hexyc`; signed surface lists; `mat` compositions; `ene 1 3 1000 1E-9 12.0`; detectors that refer to the energy grid with `de 1`. |
| [3D BWR assembly transient example](https://serpent.vtt.fi/mediawiki/index.php/3D_PWR_assembly_transient_example) | Multi-file official example and an independent detector example. | Main inputs use `include pins`, `include geometry`, and `include materials`; the same page provides the three additional file bodies. It also contains detector cards and surfaces including `sqc`, `pz`, and `cuboid`. |

The VVER and transient examples confirm that `det`, `ene`, and `include` are real cards that the first parser must preserve as unsupported cards. They are research inputs, not milestone-one parsing targets.

## Authoritative syntax references

- [General input](https://serpent.vtt.fi/docs/user_guide/general_input.html): confirms whitespace-separated input, case-insensitive card keywords, `%` comments, C-style `/* ... */` comment sections, and the fact that nested comment sections are unsupported.
- [Input syntax manual](https://serpent.vtt.fi/docs/syntax/index.html): confirms the card forms for `surf`, `cell`, `mat`, and `include`, and that a card ends when the next card begins.
- [Geometry guide](https://serpent.vtt.fi/docs/user_guide/geometry.html): confirms implicit intersection, `:` union, `-` surface complement, parentheses for precedence, and `#` cell complement.
- [Material guide](https://serpent.vtt.fi/docs/user_guide/materials.html): confirms the basic `mat NAME DENS ZAID FRAC ...` form and the sign convention for atomic and mass units.
- [CSG surface types](https://serpent.vtt.fi/docs/extra/csg_surfaces.html): confirms the parameter forms used in the fixtures: `cyl X0 Y0 R` and `sqc X0 Y0 D`.

## Include-file observation

The transient example demonstrates recursive input composition with three relative include targets. The syntax manual states `include "FILE"`, says processing returns to the original input after the included file is complete, and requires included files to contain complete cards. Include resolution is deliberately deferred; the first parser will preserve the card without reading the referenced file.

## Copyright and redistribution

No official input file has been copied into this repository. The repository fixtures are short, independently written cases that use generic names, original numeric values, and only the observed syntax patterns. Source links and high-level descriptions are retained for traceability.

The reviewed Wiki pages did not expose a clear redistribution licence for their input text through the available About or disclaimer links. Until redistribution terms are confirmed, official example bodies should remain external references rather than repository content.
