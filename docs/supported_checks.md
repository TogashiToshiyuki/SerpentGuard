# Supported checks

## Current implementation status

No checks are implemented in Phase 0. This document records the planned deterministic scope from the canonical specification; it must not be read as a claim that the checks are currently available.

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

Detector consistency checks and sampling-based 2D overlap or undefined-region checks are also planned for later phases. They are not part of the current repository initialization.

## Planned syntax boundary

Initial full support is intended for a limited subset of `surf`, `cell`, and `mat`. Support for `include`, `det`, `ene`, and `set` is intended to be partial. `pin` and `lat` are initially recognition-only. Unsupported syntax must be reported rather than silently treated as validated.

See the [canonical specification](../serpentguard_implementation_spec.md) for the authoritative scope, severity definitions, and limitations.
