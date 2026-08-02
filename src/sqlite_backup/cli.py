"""Command-line interface for sqlite-backup."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from sqlite_backup.backup import BackupError, create_backup


def non_negative_integer(value: str) -> int:
    """Parse a non-negative command-line integer."""
    try:
        parsed_value = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a non-negative integer") from error

    if parsed_value < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return parsed_value


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        prog="sqlite-backup",
        description="Create a safe online backup of a SQLite database.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing destination after a successful backup",
    )
    parser.add_argument(
        "--integrity-check",
        action="store_true",
        help="verify the completed temporary backup with SQLite before publishing",
    )
    parser.add_argument(
        "--retries",
        type=non_negative_integer,
        default=0,
        metavar="COUNT",
        help=(
            "retry busy or locked SQLite errors COUNT additional times "
            "(default: 0)"
        ),
    )
    parser.add_argument("source_database", type=Path, metavar="SOURCE_DATABASE")
    parser.add_argument(
        "destination_database", type=Path, metavar="DESTINATION_DATABASE"
    )
    return parser


def main(arguments: Sequence[str] | None = None) -> int:
    """Run the command and return its process exit code."""
    parser = build_parser()
    parsed_arguments = parser.parse_args(arguments)

    try:
        create_backup(
            source_database=parsed_arguments.source_database,
            destination_database=parsed_arguments.destination_database,
            overwrite=parsed_arguments.overwrite,
            integrity_check=parsed_arguments.integrity_check,
            retries=parsed_arguments.retries,
        )
    except BackupError as error:
        print(f"sqlite-backup: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
