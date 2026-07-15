"""Command-line entry point for the SerpentGuard foundation."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence


def _check_placeholder(_: argparse.Namespace) -> int:
    """Report that deterministic checks are not implemented yet."""
    print(
        "Serpent input checks are not implemented in the foundation phase.",
        file=sys.stderr,
    )
    return 2


def build_parser() -> argparse.ArgumentParser:
    """Build the SerpentGuard command-line parser."""
    parser = argparse.ArgumentParser(
        prog="serpentguard",
        description=(
            "Local deterministic preflight checks for a limited subset of "
            "Serpent input syntax."
        ),
    )
    subparsers = parser.add_subparsers(dest="command")

    check_parser = subparsers.add_parser(
        "check",
        help="Placeholder for deterministic checks (not implemented yet).",
        description=(
            "Placeholder command for future deterministic checks. "
            "No Serpent input is processed in the foundation phase."
        ),
    )
    check_parser.set_defaults(handler=_check_placeholder)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the SerpentGuard command-line interface."""
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return int(handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
