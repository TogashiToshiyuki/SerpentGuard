# Examples

This directory contains small, independently written SerpentGuard fixtures. They are parser and finding contracts, not complete transport models and not substitutes for validation with Serpent.

## Fixture inventory

| Fixture | Purpose | Expected findings |
| --- | --- | --- |
| `valid_minimal.inp` | Supported `cyl`, `sqc`, `cell`, `mat`, `%`, and block-comment subset. | None |
| `duplicate_surface.inp` | Repeats one surface name. | SG001 ERROR; both definitions remain in the symbol table. |
| `undefined_surface.inp` | References one surface that is not defined. | SG004 ERROR. |
| `contradictory_cell.inp` | Uses both signs of one surface in an implicit intersection. | SG008 WARNING. |
| `unknown_card.inp` | Uses an official `set` card that milestone one does not support. | SG014 INFO; raw card preserved |

Each fixture header records its source inspiration, intentional simplification, and expected finding. See [the source review](../docs/example_sources.md) and [syntax boundary](../docs/supported_syntax.md).

## Contribution policy

Before adding a fixture:

1. Remove confidential or identifying content and absolute local paths.
2. Confirm that redistribution is permitted and document its source and license when applicable.
3. Keep the fixture to the minimum syntax needed for the intended test.
4. Record the expected deterministic finding or clean result.
5. Review the staged diff before committing.

No official example input body is copied here. Redistribution terms for the reviewed Wiki inputs were not clear, so official examples remain linked external research sources. Fixture text and numeric values are independently authored.

Do not place unpublished research inputs here. Use the ignored `local_inputs/` or `private_inputs/` directory instead.
