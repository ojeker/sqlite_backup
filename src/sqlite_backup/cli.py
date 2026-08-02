"""Command-line interface for sqlite-backup."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from sqlite_backup.backup import BackupError, create_backup


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
        )
    except BackupError as error:
        print(f"sqlite-backup: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
