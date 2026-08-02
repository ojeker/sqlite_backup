"""Tests for the sqlite-backup command-line interface."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path


def run_command(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Run the module entry point without relying on an installed command."""
    return subprocess.run(
        [sys.executable, "-m", "sqlite_backup", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


def create_database(path: Path) -> None:
    """Create a small SQLite database used by command tests."""
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE entries (value TEXT NOT NULL)")
        connection.execute("INSERT INTO entries VALUES ('saved value')")


def test_help_describes_the_command() -> None:
    result = run_command("--help")

    assert result.returncode == 0
    assert "SOURCE_DATABASE" in result.stdout
    assert "DESTINATION_DATABASE" in result.stdout
    assert "--no-overwrite" in result.stdout
    assert "--integrity-check" in result.stdout
    assert "--retries COUNT" in result.stdout
    assert result.stderr == ""


def test_backup_preserves_schema_and_data(tmp_path: Path) -> None:
    source_database = tmp_path / "source.sqlite"
    destination_database = tmp_path / "backup.sqlite"
    create_database(source_database)

    result = run_command(str(source_database), str(destination_database))

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    with sqlite3.connect(destination_database) as connection:
        assert connection.execute("SELECT value FROM entries").fetchall() == [
            ("saved value",)
        ]


def test_backup_succeeds_while_source_connection_is_open(tmp_path: Path) -> None:
    source_database = tmp_path / "source.sqlite"
    destination_database = tmp_path / "backup.sqlite"
    create_database(source_database)

    open_connection = sqlite3.connect(source_database)
    try:
        result = run_command(str(source_database), str(destination_database))
    finally:
        open_connection.close()

    assert result.returncode == 0
    assert destination_database.is_file()


def test_no_overwrite_preserves_an_existing_destination(tmp_path: Path) -> None:
    source_database = tmp_path / "source.sqlite"
    destination_database = tmp_path / "backup.sqlite"
    create_database(source_database)
    destination_database.write_text("original destination")

    result = run_command(
        "--no-overwrite", str(source_database), str(destination_database)
    )

    assert result.returncode == 1
    assert destination_database.read_text() == "original destination"
    assert "destination already exists" in result.stderr


def test_existing_destination_is_replaced_by_default(tmp_path: Path) -> None:
    source_database = tmp_path / "source.sqlite"
    destination_database = tmp_path / "backup.sqlite"
    create_database(source_database)
    destination_database.write_text("original destination")

    result = run_command(str(source_database), str(destination_database))

    assert result.returncode == 0
    with sqlite3.connect(destination_database) as connection:
        assert connection.execute("SELECT value FROM entries").fetchall() == [
            ("saved value",)
        ]


def test_overwrite_is_not_a_supported_option(tmp_path: Path) -> None:
    source_database = tmp_path / "source.sqlite"
    destination_database = tmp_path / "backup.sqlite"
    create_database(source_database)

    result = run_command("--overwrite", str(source_database), str(destination_database))

    assert result.returncode == 2
    assert "unrecognized arguments: --overwrite" in result.stderr


def test_integrity_check_verifies_and_publishes_the_backup(tmp_path: Path) -> None:
    source_database = tmp_path / "source.sqlite"
    destination_database = tmp_path / "backup.sqlite"
    create_database(source_database)

    result = run_command(
        "--integrity-check", str(source_database), str(destination_database)
    )

    assert result.returncode == 0
    with sqlite3.connect(destination_database) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchall() == [("ok",)]


def test_negative_retry_count_is_an_argument_error(tmp_path: Path) -> None:
    source_database = tmp_path / "source.sqlite"
    destination_database = tmp_path / "backup.sqlite"
    create_database(source_database)

    result = run_command(
        "--retries", "-1", str(source_database), str(destination_database)
    )

    assert result.returncode == 2
    assert "non-negative integer" in result.stderr


def test_non_integer_retry_count_is_an_argument_error(tmp_path: Path) -> None:
    source_database = tmp_path / "source.sqlite"
    destination_database = tmp_path / "backup.sqlite"
    create_database(source_database)

    result = run_command(
        "--retries", "many", str(source_database), str(destination_database)
    )

    assert result.returncode == 2
    assert "non-negative integer" in result.stderr


def test_zero_retries_keeps_the_standard_backup_behavior(tmp_path: Path) -> None:
    source_database = tmp_path / "source.sqlite"
    destination_database = tmp_path / "backup.sqlite"
    create_database(source_database)

    result = run_command(
        "--retries", "0", str(source_database), str(destination_database)
    )

    assert result.returncode == 0
    assert destination_database.is_file()


def test_source_and_destination_must_differ(tmp_path: Path) -> None:
    source_database = tmp_path / "source.sqlite"
    create_database(source_database)

    result = run_command(str(source_database), str(source_database))

    assert result.returncode == 1
    assert "must be different" in result.stderr


def test_invalid_source_reports_an_operational_error(tmp_path: Path) -> None:
    destination_database = tmp_path / "backup.sqlite"

    result = run_command(str(tmp_path / "missing.sqlite"), str(destination_database))

    assert result.returncode == 1
    assert "source database" in result.stderr
    assert result.stdout == ""


def test_missing_destination_directory_reports_an_operational_error(tmp_path: Path) -> None:
    source_database = tmp_path / "source.sqlite"
    create_database(source_database)

    result = run_command(
        str(source_database), str(tmp_path / "missing-directory" / "backup.sqlite")
    )

    assert result.returncode == 1
    assert "destination directory does not exist" in result.stderr


def test_corrupt_source_reports_an_operational_error(tmp_path: Path) -> None:
    source_database = tmp_path / "corrupt.sqlite"
    destination_database = tmp_path / "backup.sqlite"
    source_database.write_text("not a SQLite database")

    result = run_command(str(source_database), str(destination_database))

    assert result.returncode == 1
    assert result.stdout == ""
    assert not destination_database.exists()


def test_invalid_arguments_use_exit_code_two() -> None:
    result = run_command("only-source.sqlite")

    assert result.returncode == 2
    assert "usage:" in result.stderr
