# Supported checks

## Current implementation status

No parser or deterministic checks are implemented. This document records the fixture contract and planned findings for the first parser milestone; it must not be read as a claim that the checks are currently available.

## First parser milestone

| Rule | Proposed severity | Planned behavior | Fixture |
| --- | --- | --- | --- |
| SG001 | ERROR | Report each repeated surface name without discarding either definition. | `duplicate_surface.inp` |
| SG002 | ERROR | Report each repeated cell name in the same parsed input. | Planned later |
| SG003 | ERROR | Report each repeated material name. | Planned later |
| SG004 | ERROR | Report a signed cell-region surface reference with no parsed definition. | `undefined_surface.inp` |
| SG005 | ERROR | Report a material-filled cell whose material has no parsed definition; exclude `void` and `outside`. | Planned later |
| SG008 | WARNING | Report both signs of the same surface within one implicit intersection. | `contradictory_cell.inp` |
| SG009 | WARNING | Report a repeated identical signed surface term within one implicit intersection. | Planned later |
| SG011 | ERROR | Report a block comment that reaches end-of-file without `*/`. | Planned later |
| SG014 | INFO | Preserve and report a reserved but unsupported card; do not interpret it. | `unknown_card.inp` |
| SG015 | REVIEW | Report parser recovery whenever malformed supported syntax is skipped or retained only as raw text. | Planned later |

`valid_minimal.inp` is expected to produce none of the milestone findings above. These expectations are documentation only until parser and rule code is implemented.

## Planned static checks

| Rule | Planned finding |
| --- | --- |
| SG001 | Duplicate surface |
| SG002 | Duplicate cell |
| SG003 | Duplicate material |
| SG004 | Undefined surface reference |
| SG005 | Undefined material reference |
| SG006 | Unused surface |
| SG007 | Unused material |
| SG008 | Contradictory signed surface |
| SG009 | Duplicate region condition |
| SG010 | Excessively complex region expression |
| SG011 | Unterminated block comment |
| SG012 | Missing include file |
| SG013 | Include cycle |
| SG014 | Unsupported card |
| SG015 | Parser recovery used |

SG006, SG007, and SG010 require later symbol-table or complexity-policy work. SG012 and SG013 require safe include resolution. Detector consistency checks and sampling-based 2D overlap or undefined-region checks remain later phases.

## Planned syntax boundary

The exact proposed subset is defined in [supported syntax](supported_syntax.md). `include`, `det`, `ene`, `set`, `pin`, and `lat` are retained as unsupported cards only. Unsupported syntax must be reported rather than silently treated as validated.

See the [canonical specification](../serpentguard_implementation_spec.md) for the authoritative scope, severity definitions, and limitations.
